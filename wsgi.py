"""WSGI entry point for production deployment."""

import sys
from pathlib import Path

# Add src/ to Python path so stock_checker is importable
sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_checker.app import app  # noqa: E402

if __name__ == "__main__":
    app.run()
