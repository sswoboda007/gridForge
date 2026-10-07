# -*- coding: utf-8 -*-
# main.py
"""
Provides the production-style Flask entrypoint for GridForge Command Cloud.

Cloud runtimes can import the module-level Flask app, while direct execution can
start a basic local server using the configured PORT environment variable.

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
from gridforge import createApp

app = createApp()


def runServer() -> None:
    """
    Starts the Flask development server for direct module execution.

    Returns:
        None.
    """
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))


if __name__ == "__main__":
    runServer()
