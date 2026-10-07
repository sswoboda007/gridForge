# -*- coding: utf-8 -*-
# flaskApp.py
"""
Provides the local development server entrypoint for GridForge Command Cloud.

This script matches the repository validation command and starts the Flask app on
a local interface using PORT when provided.

Author: @seanl
Version: 0001
Creation Date: 10/07/2026
Last Updated: 10/07/2026
"""

from __future__ import annotations

# 1) Standard library imports (alphabetized)
import os

# 2) Third-party imports (alphabetized)

# 3) Application-specific imports (alphabetized)
from main import app


def runLocalServer() -> None:
    """
    Starts the local Flask development server.

    Returns:
        None.
    """
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))


if __name__ == "__main__":
    runLocalServer()
