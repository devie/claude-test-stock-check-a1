"""
PythonAnywhere WSGI configuration.
Copy the contents of this file into the WSGI config file
on PythonAnywhere dashboard (Web tab -> WSGI configuration file).
Replace YOUR_USERNAME with your PythonAnywhere username.
"""

import sys
from pathlib import Path

project_home = '/home/YOUR_USERNAME/claude-test-stock-check-a1'
if project_home not in sys.path:
    sys.path.insert(0, project_home)
sys.path.insert(0, str(Path(project_home) / 'src'))

from stock_checker.app import app as application  # noqa
