#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Pulling latest changes..."
git pull

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Installing pygame..."
    venv/bin/pip install pygame
fi

exec venv/bin/python game.py "$@"
