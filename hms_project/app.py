"""Flask application factory and blueprint registration for HMS.

No JavaScript is used anywhere; all views are server-rendered.
"""
from __future__ import annotations

from datetime import date
from flask import Flask, redirect, url_for, jsonify
from flask_login import LoginManager, current_user

from config import Config
from models import db, User, DoctorProfile

# Blueprints are imported lazily to avoid circular imports

def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from auth import auth_bp
    from admin import admin_bp
    from doctor import doctor_bp
    from patient import patient_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(doctor_bp, url_prefix="/doctor")
    app.register_blueprint(patient_bp, url_prefix="/patient")

    # Index route: send users to their dashboards
    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        if current_user.role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        return redirect(url_for("patient.dashboard"))

    # Minimal JSON API: list doctors
    @app.get("/api/doctors")
    def api_doctors():
        profiles = DoctorProfile.query.join(User, User.id == DoctorProfile.doctor_id).all()
        return jsonify([p.to_dict() for p in profiles])

    return app


# Enable running via `python app.py`
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
