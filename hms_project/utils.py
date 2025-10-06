"""Utility helpers: role checks and small utilities."""
from __future__ import annotations

from datetime import date, timedelta
from functools import wraps
from typing import Iterable, List

from flask import abort
from flask_login import current_user


def roles_required(*roles: Iterable[str]):
    """Decorator to ensure the current user has one of the required roles.

    Usage:
        @login_required
        @roles_required('admin')
        def admin_view():
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapper

    return decorator


def next_seven_days(start: date | None = None) -> List[date]:
    """Return a list of the next 7 dates starting from today (or given start)."""
    base = start or date.today()
    return [base + timedelta(days=i) for i in range(7)]


def parse_times_csv(times_csv: str) -> List[str]:
    """Parse a comma/space separated list of HH:MM strings and normalize.

    Returns a list like ['09:00', '10:30'] with basic format validation.
    """
    times_csv = times_csv or ""
    raw = [t.strip() for t in times_csv.replace("\n", ",").split(",") if t.strip()]
    normalized: List[str] = []
    for token in raw:
        if len(token) == 5 and token[2] == ":":
            hh, mm = token.split(":", 1)
            if hh.isdigit() and mm.isdigit():
                hh_i, mm_i = int(hh), int(mm)
                if 0 <= hh_i <= 23 and mm_i in (0, 15, 30, 45):
                    normalized.append(f"{hh_i:02d}:{mm_i:02d}")
    return list(dict.fromkeys(normalized))  # de-duplicate preserving order
