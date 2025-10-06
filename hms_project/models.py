"""Database models for the Hospital Management System (HMS).

This module defines:
- User: unified user table with role field ('admin'|'doctor'|'patient')
- DoctorProfile: one-to-one profile for doctors
- DoctorAvailability: normalized, per-slot availability for the next 7 days
- Appointment: patient-doctor appointments with lifecycle status

All write operations should be validated server-side in blueprints.
"""
from __future__ import annotations

from datetime import datetime, date
from typing import List, Dict

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

# SQLAlchemy instance (initialized in app factory)
db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' | 'doctor' | 'patient'
    contact = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    doctor_profile = db.relationship(
        "DoctorProfile", uselist=False, back_populates="user", cascade="all, delete-orphan"
    )

    doctor_appointments = db.relationship(
        "Appointment",
        foreign_keys="Appointment.doctor_id",
        back_populates="doctor",
        cascade="all, delete-orphan",
    )
    patient_appointments = db.relationship(
        "Appointment",
        foreign_keys="Appointment.patient_id",
        back_populates="patient",
        cascade="all, delete-orphan",
    )

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_doctor(self) -> bool:
        return self.role == "doctor"

    def is_patient(self) -> bool:
        return self.role == "patient"

    def __repr__(self) -> str:  # pragma: no cover - for debugging
        return f"<User {self.id} {self.email} {self.role}>"


class DoctorProfile(db.Model):
    __tablename__ = "doctor_profiles"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    specialization = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.Text)
    phone = db.Column(db.String(30))

    user = db.relationship("User", back_populates="doctor_profile")
    availability = db.relationship(
        "DoctorAvailability",
        back_populates="doctor_profile",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> Dict:
        return {
            "id": self.doctor_id,
            "name": self.user.name if self.user else None,
            "email": self.user.email if self.user else None,
            "specialization": self.specialization,
            "phone": self.phone,
            "bio": self.bio,
        }

    def __repr__(self) -> str:  # pragma: no cover - for debugging
        return f"<DoctorProfile doctor_id={self.doctor_id} specialization={self.specialization}>"


class DoctorAvailability(db.Model):
    __tablename__ = "doctor_availability"
    __table_args__ = (
        UniqueConstraint("doctor_id", "date", "time", name="uq_doctor_date_time"),
    )

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor_profiles.doctor_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=False)  # 'HH:MM'
    is_booked = db.Column(db.Boolean, default=False, nullable=False)

    doctor_profile = db.relationship("DoctorProfile", back_populates="availability")

    def label(self) -> str:
        return f"{self.date.isoformat()} {self.time}"


class Appointment(db.Model):
    __tablename__ = "appointments"
    __table_args__ = (
        db.Index("idx_appointments_doctor_dt", "doctor_id", "date", "time"),
    )

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=False)  # 'HH:MM'
    status = db.Column(db.String(20), nullable=False, default="Booked")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # optional treatment fields (present after completion)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    recorded_by_doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    recorded_at = db.Column(db.DateTime)

    patient = db.relationship("User", foreign_keys=[patient_id], back_populates="patient_appointments")
    doctor = db.relationship("User", foreign_keys=[doctor_id], back_populates="doctor_appointments")

    def mark_completed(self, doctor_user_id: int, diagnosis: str, prescription: str, notes: str) -> None:
        self.status = "Completed"
        self.diagnosis = diagnosis
        self.prescription = prescription
        self.notes = notes
        self.recorded_by_doctor_id = doctor_user_id
        self.recorded_at = datetime.utcnow()

    @property
    def is_future(self) -> bool:
        return datetime.combine(self.date, datetime.strptime(self.time, "%H:%M").time()) >= datetime.utcnow()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Appointment id={self.id} d={self.date} t={self.time} status={self.status}>"
