"""Utility helpers for role-based access control and misc helpers."""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import abort
from flask_login import current_user, login_required as flask_login_required


login_required = flask_login_required  # re-export for convenience


def roles_required(*allowed_roles: str) -> Callable:
    """Decorator to enforce role-based access control.

    Usage:
        @app.route('/admin')
        @roles_required('admin')
        def admin_only():
            ...
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        @flask_login_required
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in allowed_roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapper

    return decorator
