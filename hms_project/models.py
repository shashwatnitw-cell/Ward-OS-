"""Database models for the Hospital Management System.

The project uses a single ``User`` table with a ``role`` column that can be
one of: ``admin``, ``doctor``, ``patient``. Additional doctor details live in
``DoctorProfile`` and time slots in ``DoctorAvailability``. Appointments and
TreatmentRecords capture the care lifecycle.

All relationships are modeled with SQLAlchemy ORM and are compatible with
SQLite. The ``Appointment`` model enforces double-booking prevention via a
composite uniqueness constraint on (doctor_id, date, time, status) for active
statuses at the application layer; additionally, an index helps lookups.
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin


db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin | doctor | patient
    contact = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Backrefs
    doctor_profile = db.relationship("DoctorProfile", uselist=False, back_populates="user")
    patient_appointments = db.relationship(
        "Appointment", foreign_keys="Appointment.patient_id", back_populates="patient"
    )
    doctor_appointments = db.relationship(
        "Appointment", foreign_keys="Appointment.doctor_id", back_populates="doctor"
    )

    def is_admin(self) -> bool:
        return self.role == "admin"

    def is_doctor(self) -> bool:
        return self.role == "doctor"

    def is_patient(self) -> bool:
        return self.role == "patient"


class DoctorProfile(db.Model):
    __tablename__ = "doctor_profiles"

    id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    specialization = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.Text)
    phone = db.Column(db.String(50))

    user = db.relationship("User", back_populates="doctor_profile")
    availability = db.relationship(
        "DoctorAvailability", back_populates="doctor", cascade="all, delete-orphan"
    )


class DoctorAvailability(db.Model):
    __tablename__ = "doctor_availability"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctor_profiles.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.String(5), nullable=False)  # HH:MM 24h format
    is_booked = db.Column(db.Boolean, default=False, nullable=False)

    doctor = db.relationship("DoctorProfile", back_populates="availability")

    __table_args__ = (
        db.UniqueConstraint("doctor_id", "date", "time", name="uq_doctor_slot"),
    )


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(20), default="Booked", nullable=False)  # Booked|Completed|Cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Treatment fields (filled when completed)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    recorded_by_doctor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    recorded_at = db.Column(db.DateTime)

    patient = db.relationship("User", foreign_keys=[patient_id], back_populates="patient_appointments")
    doctor = db.relationship("User", foreign_keys=[doctor_id], back_populates="doctor_appointments")

    __table_args__ = (
        db.Index("ix_doctor_date_time", "doctor_id", "date", "time"),
    )

    def mark_completed(
        self,
        diagnosis: str,
        prescription: str,
        notes: Optional[str],
        recorded_by_doctor_id: int,
    ) -> None:
        self.status = "Completed"
        self.diagnosis = diagnosis
        self.prescription = prescription
        self.notes = notes
        self.recorded_by_doctor_id = recorded_by_doctor_id
        self.recorded_at = datetime.utcnow()


def available_slots_for_doctor(doctor_profile_id: int, on_date: Optional[date] = None):
    """Return unbooked availability rows for a doctor.

    If ``on_date`` is provided, filter to that date only; otherwise return all
    unbooked future slots.
    """
    query = DoctorAvailability.query.filter_by(doctor_id=doctor_profile_id, is_booked=False)
    if on_date is not None:
        query = query.filter(DoctorAvailability.date == on_date)
    return query.order_by(DoctorAvailability.date.asc(), DoctorAvailability.time.asc()).all()
