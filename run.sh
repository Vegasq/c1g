#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Pulling latest changes..."
git pull

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Installing dependencies..."
venv/bin/pip install -q pygame-ce pytmx

exec venv/bin/python game.py "$@"
