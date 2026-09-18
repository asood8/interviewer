"""Thin wrapper around the Claude API for structured (Pydantic) responses."""

import os

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

MODEL = os.getenv("INTERVIEWER_MODEL", "claude-opus-5")

_client: anthropic.Anthropic | None = None


class LLMError(Exception):
    """A user-facing error from a Claude call."""


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def system_blocks(profile_text: str, instructions: str) -> list[dict]:
    """Profile first and cached, so question generation and grading share the cached prefix."""
    return [
        {"type": "text", "text": profile_text, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": instructions},
    ]


def ask_structured[T: BaseModel](system: list[dict], user: str, schema: type[T], effort: str = "high") -> T:
    try:
        response = _get_client().beta.messages.parse(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": effort},
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
        )
    except anthropic.AuthenticationError as e:
        raise LLMError("Invalid API key. Check ANTHROPIC_API_KEY in your .env file.") from e
    except anthropic.RateLimitError as e:
        raise LLMError("Rate limited by the API. Wait a moment and try again.") from e
    except anthropic.APIConnectionError as e:
        raise LLMError("Couldn't reach the Claude API. Check your internet connection.") from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"Claude API error ({e.status_code}): {e.message}") from e
    except anthropic.AnthropicError as e:
        # e.g. no credentials configured at all
        raise LLMError(str(e)) from e

    if response.stop_reason == "refusal":
        raise LLMError("Claude declined to answer this request. Try again or rephrase.")
    if response.stop_reason == "max_tokens":
        raise LLMError("Claude's response was cut off. Try again.")
    if response.parsed_output is None:
        raise LLMError("Claude returned a response that couldn't be parsed. Try again.")
    return response.parsed_output
