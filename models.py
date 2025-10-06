"""
Database models for the Hospital Management System.
All models are created using SQLAlchemy ORM.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """
    User model representing all users in the system (Admin, Doctor, Patient).
    Uses a single table with a role discriminator field.
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'doctor', 'patient'
    contact = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    doctor_profile = db.relationship('DoctorProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    appointments_as_patient = db.relationship('Appointment', foreign_keys='Appointment.patient_id', backref='patient', lazy='dynamic')
    appointments_as_doctor = db.relationship('Appointment', foreign_keys='Appointment.doctor_id', backref='doctor', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify the user's password against the hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class DoctorProfile(db.Model):
    """
    Extended profile information for doctors.
    Linked to User model via one-to-one relationship.
    """
    __tablename__ = 'doctor_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    specialization = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text)
    phone = db.Column(db.String(20))
    
    # Relationships
    availability = db.relationship('DoctorAvailability', backref='doctor_profile', cascade='all, delete-orphan', lazy='dynamic')
    
    def __repr__(self):
        return f'<DoctorProfile {self.specialization}>'


class DoctorAvailability(db.Model):
    """
    Represents available time slots for doctors.
    Each record is a specific date/time when the doctor is available.
    """
    __tablename__ = 'doctor_availability'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor_profiles.doctor_id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.String(10), nullable=False)  # Format: "HH:MM"
    is_booked = db.Column(db.Boolean, default=False)
    
    # Composite index to quickly find available slots
    __table_args__ = (
        db.Index('idx_doctor_date_time', 'doctor_id', 'date', 'time'),
    )
    
    def __repr__(self):
        return f'<DoctorAvailability Doctor {self.doctor_id} on {self.date} at {self.time}>'


class Appointment(db.Model):
    """
    Represents an appointment between a patient and a doctor.
    Includes treatment information recorded by the doctor.
    """
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    time = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Booked')  # 'Booked', 'Completed', 'Cancelled'
    
    # Treatment information (filled by doctor when marking as completed)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite unique constraint to prevent double booking
    __table_args__ = (
        db.Index('idx_doctor_date_time_status', 'doctor_id', 'date', 'time', 'status'),
    )
    
    def __repr__(self):
        return f'<Appointment {self.id} - {self.status}>'
