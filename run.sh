#!/usr/bin/env bash
# Start Interviewer. Sets everything up the first time.
set -e
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
    echo "First run: creating the virtual environment..."
    python3 -m venv .venv
    echo "Installing dependencies, this takes a few minutes..."
    .venv/bin/python -m pip install --quiet --upgrade pip
    .venv/bin/python -m pip install --quiet -r requirements.txt
fi

if [ ! -f ".env" ]; then
    echo
    echo "No .env file yet, so there's no API key to use."
    echo "  1. cp .env.example .env"
    echo "  2. open .env and put your key after ANTHROPIC_API_KEY="
    echo "     (get one at https://console.anthropic.com)"
    echo
    exit 1
fi

echo "Starting Interviewer. Press Ctrl+C to stop it."
.venv/bin/python -m streamlit run app.py
