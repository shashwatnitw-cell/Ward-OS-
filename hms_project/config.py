"""Application configuration for the HMS Flask app.

This module provides a single ``Config`` class which is used by the Flask
application to configure core settings such as the SQLite database location
and secret key. The values are intentionally simple and file‑system friendly
so that the project can run out-of-the-box on Linux/Windows without any
additional setup.
"""
from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "hms.db"


class Config:
    """Default runtime configuration.

    - Uses SQLite file in the project directory (``hms.db``)
    - Disables SQLALCHEMY_TRACK_MODIFICATIONS for performance
    - Provides a development secret key (change in production!)
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me-please")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{DB_PATH}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = None  # CSRF tokens remain valid for the session
