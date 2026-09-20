"""Reading a project's code so questions can be grounded in what was actually built."""

import re
import subprocess
from pathlib import Path

from interviewer.profile import DATA_DIR

CLONE_DIR = DATA_DIR / "repos"

# Caps, so one project can't swamp the prompt.
MAX_DIGEST_CHARS = 20_000
MAX_README_CHARS = 6_000
MAX_FILE_CHARS = 4_000
MAX_LISTED_FILES = 200
MAX_FILE_BYTES = 200_000

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "env", "__pycache__", ".pytest_cache",
    ".mypy_cache", "dist", "build", "out", "target", ".next", ".nuxt", "vendor", ".idea", ".vscode",
    "migrations", "coverage", ".terraform",
}
SOURCE_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".go", ".rb", ".rs", ".c", ".h", ".cpp", ".hpp",
    ".cs", ".php", ".swift", ".m", ".scala", ".sh", ".sql", ".html", ".css", ".scss", ".vue", ".svelte",
}
CONFIG_NAMES = {
    "package.json", "requirements.txt", "pyproject.toml", "go.mod", "cargo.toml", "pom.xml",
    "build.gradle", "gemfile", "dockerfile", "docker-compose.yml", "schema.sql", "makefile",
}
# Files worth showing first: entry points and the pieces interviewers ask about.
KEY_STEMS = ("main", "app", "server", "index", "cli", "api", "routes", "models", "schema", "db", "database")


class RepoError(Exception):
    """A user-facing problem reading a repository."""


def is_url(source: str) -> bool:
    return bool(re.match(r"(https?://|git@)", source.strip()))


def _slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", text.strip()).strip("-").lower() or "repo"


def _git(*args: str, cwd: Path | None = None) -> None:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=300,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip().splitlines()
        raise RepoError(message[-1] if message else "git failed")


def clone_or_update(url: str, project_id: str) -> Path:
    """Shallow-clone the repo into data/repos (or fetch the latest if it's already there)."""
    target = CLONE_DIR / f"{project_id}-{_slug(url.rsplit('/', 1)[-1].removesuffix('.git'))}"
    if (target / ".git").exists():
        _git("fetch", "--depth", "1", "origin", cwd=target)
        _git("reset", "--hard", "FETCH_HEAD", cwd=target)
    else:
        CLONE_DIR.mkdir(parents=True, exist_ok=True)
        _git("clone", "--depth", "1", url, str(target))
    return target


def _read(path: Path, limit: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise RepoError(f"Couldn't read {path.name}: {e}") from e
    return text[:limit] + ("\n... (truncated)" if len(text) > limit else "")


def _collect(root: Path) -> tuple[list[Path], Path | None]:
    files: list[Path] = []
    readme: Path | None = None
    for path in sorted(root.rglob("*")):
        parents = path.relative_to(root).parts[:-1]
        if not path.is_file() or any(p in SKIP_DIRS or p.startswith(".") for p in parents):
            continue
        name = path.name.lower()
        if readme is None and name.startswith("readme"):
            readme = path
        elif path.suffix.lower() in SOURCE_SUFFIXES or name in CONFIG_NAMES:
            if path.stat().st_size <= MAX_FILE_BYTES:
                files.append(path)
    return files, readme


def _rank(path: Path, root: Path) -> tuple[int, int]:
    """Entry points first, then bigger files. Lower sorts first."""
    stem = path.stem.lower()
    depth = len(path.relative_to(root).parts)
    key = 0 if stem in KEY_STEMS else 1 if any(stem.startswith(s) for s in KEY_STEMS) else 2
    return key + depth // 4, -path.stat().st_size


def digest(source: str, project_id: str) -> str:
    """A compact, readable summary of a repository: tree, README, and the most important files."""
    source = source.strip()
    root = clone_or_update(source, project_id) if is_url(source) else Path(source).expanduser()
    if not root.is_dir():
        raise RepoError(f"No such folder: {root}")

    files, readme = _collect(root)
    if not files and not readme:
        raise RepoError("No source files found in that repository.")

    parts = [f"Source: {source}"]
    listed = sorted(f.relative_to(root).as_posix() for f in files)[:MAX_LISTED_FILES]
    parts.append("Files:\n" + "\n".join(listed) + (f"\n... and {len(files) - len(listed)} more" if len(files) > len(listed) else ""))
    if readme:
        parts.append(f"--- {readme.name} ---\n{_read(readme, MAX_README_CHARS)}")

    used = sum(len(p) for p in parts)
    for path in sorted(files, key=lambda f: _rank(f, root)):
        if used >= MAX_DIGEST_CHARS:
            break
        block = f"--- {path.relative_to(root).as_posix()} ---\n{_read(path, min(MAX_FILE_CHARS, MAX_DIGEST_CHARS - used))}"
        parts.append(block)
        used += len(block)
    return "\n\n".join(parts)
