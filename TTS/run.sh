#!/usr/bin/env bash
# run.sh - Launcher for the TTS API server (OmniVoice backend)
# Equivalent of run.bat for Linux/macOS

set -e  # exit on first error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="venv"
REQ_FILE="requirements.txt"

echo "======================================================================"
echo " TTS API Server (OmniVoice backend) - Launcher"
echo "======================================================================"

# 1) Check python3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.10+."
    exit 1
fi

# 2) Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in ./$VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

# 3) Activate virtual environment
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 4) Upgrade pip and install requirements
if [ -f "$REQ_FILE" ] && [ -s "$REQ_FILE" ]; then
    echo "Installing dependencies from $REQ_FILE ..."
    pip install --upgrade pip > /dev/null
    pip install -r "$REQ_FILE"
else
    echo "WARNING: $REQ_FILE not found or empty."
    echo "         Skipping dependency install - make sure fastapi, uvicorn,"
    echo "         soundfile, torch and the omnivoice package are installed manually."
fi

# 5) Optional environment variables (uncomment / edit as needed)
# export TTS_PORT=8002
# export TTS_API_KEY="your-secret-key"
# export OMNIVOICE_REF_AUDIO="/path/to/ref.wav"
# export TTS_AUDIO_DIR="/path/to/tts_audio"

# 6) Run the server
echo "----------------------------------------------------------------------"
echo "Starting server..."
echo "----------------------------------------------------------------------"
python3 main.py

# Alternative (equivalent), if you prefer running uvicorn directly with reload:
# uvicorn main:app --host 0.0.0.0 --port "${TTS_PORT:-8002}" --reload