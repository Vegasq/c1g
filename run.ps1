$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "Pulling latest changes..."
git pull

if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv venv
}

Write-Host "Installing dependencies..."
venv\Scripts\pip install -q pygame-ce pytmx

& venv\Scripts\python game.py @args
