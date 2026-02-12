#!/bin/bash
# PythonAnywhere deployment script
# Run this in the PythonAnywhere Bash console

set -e

echo "=== Cloning repository ==="
cd ~
rm -rf claude-test-stock-check-a1
git clone https://github.com/devie/claude-test-stock-check-a1.git
cd claude-test-stock-check-a1

echo "=== Creating virtual environment ==="
python3.12 -m venv .venv
source .venv/bin/activate

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Done! ==="
echo ""
echo "Now configure the Web App in the PythonAnywhere dashboard:"
echo "  Source code:    /home/YOUR_USERNAME/claude-test-stock-check-a1"
echo "  Virtualenv:    /home/YOUR_USERNAME/claude-test-stock-check-a1/.venv"
echo "  WSGI file:     edit to import from wsgi.py"
