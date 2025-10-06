"""Flask application entrypoint for the HMS project.

This module wires together configuration, database initialization, flask-login,
blueprints, and Jinja template globals. It intentionally avoids JavaScript and
uses Bootstrap CSS only.
"""
from __future__ import annotations

from datetime import date

from flask import Flask, redirect, render_template, url_for
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect, generate_csrf

from config import Config
from models import db, User


login_manager = LoginManager()
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id: str):  # pragma: no cover - small adapter
    return User.query.get(int(user_id))


# --- Application Factory ----------------------------------------------------

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    CSRFProtect(app)

    # Register blueprints
    from auth import auth_bp
    from admin import admin_bp
    from doctor import doctor_bp
    from patient import patient_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doctor_bp, url_prefix="/doctor")
    app.register_blueprint(patient_bp, url_prefix="/patient")

    # Index route - redirect by role
    @app.context_processor
    def inject_csrf_token():  # Provides csrf_token() in templates for non-WTForms
        return dict(csrf_token=generate_csrf)

    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.is_authenticated:
            if getattr(current_user, "is_admin")():
                return redirect(url_for("admin.dashboard"))
            if getattr(current_user, "is_doctor")():
                return redirect(url_for("doctor.dashboard"))
            return redirect(url_for("patient.dashboard"))
        return redirect(url_for("auth.login"))

    # Health check
    @app.route("/health")
    def health():
        return {"status": "ok", "today": date.today().isoformat()}

    return app


if __name__ == "__main__":  # pragma: no cover
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
