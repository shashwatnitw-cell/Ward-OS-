"""
Database models for the Hospital Management System
"""
from datetime import datetime, date, time
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and basic user information"""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'doctor', 'patient'
    contact = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    doctor_profile = db.relationship('DoctorProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    patient_appointments = db.relationship('Appointment', foreign_keys='Appointment.patient_id', backref='patient')
    doctor_appointments = db.relationship('Appointment', foreign_keys='Appointment.doctor_id', backref='doctor')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def is_doctor(self):
        """Check if user is doctor"""
        return self.role == 'doctor'
    
    def is_patient(self):
        """Check if user is patient"""
        return self.role == 'patient'
    
    def __repr__(self):
        return f'<User {self.email}>'

class DoctorProfile(db.Model):
    """Extended profile information for doctors"""
    
    __tablename__ = 'doctor_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    specialization = db.Column(db.String(100), nullable=False)
    bio = db.Column(db.Text)
    phone = db.Column(db.String(20))
    experience_years = db.Column(db.Integer)
    
    # Relationships
    availability_slots = db.relationship('DoctorAvailability', backref='doctor_profile', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<DoctorProfile {self.user.name} - {self.specialization}>'

class DoctorAvailability(db.Model):
    """Doctor availability slots for appointment booking"""
    
    __tablename__ = 'doctor_availability'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    is_booked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent duplicate slots
    __table_args__ = (UniqueConstraint('doctor_id', 'date', 'time', name='unique_doctor_slot'),)
    
    def __repr__(self):
        return f'<Availability {self.doctor_id} - {self.date} {self.time}>'

class Appointment(db.Model):
    """Appointment bookings between patients and doctors"""
    
    __tablename__ = 'appointments'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Booked')  # 'Booked', 'Completed', 'Cancelled'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    treatment = db.relationship('Treatment', backref='appointment', uselist=False, cascade='all, delete-orphan')
    
    # Unique constraint to prevent double booking
    __table_args__ = (UniqueConstraint('doctor_id', 'date', 'time', name='unique_appointment_slot'),)
    
    def is_past(self):
        """Check if appointment is in the past"""
        appointment_datetime = datetime.combine(self.date, self.time)
        return appointment_datetime < datetime.now()
    
    def can_be_cancelled(self):
        """Check if appointment can be cancelled"""
        return self.status == 'Booked' and not self.is_past()
    
    def can_be_rescheduled(self):
        """Check if appointment can be rescheduled"""
        return self.status == 'Booked' and not self.is_past()
    
    def __repr__(self):
        return f'<Appointment {self.id} - {self.patient.name} with {self.doctor.name}>'

class Treatment(db.Model):
    """Treatment records and notes for completed appointments"""
    
    __tablename__ = 'treatments'
    
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=False, unique=True)
    diagnosis = db.Column(db.Text)
    prescription = db.Column(db.Text)
    notes = db.Column(db.Text)
    recorded_by_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    recorded_by = db.relationship('User', foreign_keys=[recorded_by_doctor_id])
    
    def __repr__(self):
        return f'<Treatment for Appointment {self.appointment_id}>'

# Helper functions for database operations

def get_available_slots(doctor_id, target_date=None):
    """Get available appointment slots for a doctor on a specific date or next 7 days"""
    from datetime import timedelta
    
    if target_date:
        # Get slots for specific date
        available_slots = DoctorAvailability.query.filter_by(
            doctor_id=doctor_id,
            date=target_date,
            is_booked=False
        ).order_by(DoctorAvailability.time).all()
    else:
        # Get slots for next 7 days
        today = date.today()
        end_date = today + timedelta(days=7)
        available_slots = DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.date >= today,
            DoctorAvailability.date <= end_date,
            DoctorAvailability.is_booked == False
        ).order_by(DoctorAvailability.date, DoctorAvailability.time).all()
    
    return available_slots

def check_appointment_conflict(doctor_id, appointment_date, appointment_time, exclude_appointment_id=None):
    """Check if there's a conflicting appointment for the given doctor, date, and time"""
    query = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == appointment_date,
        Appointment.time == appointment_time,
        Appointment.status.in_(['Booked', 'Completed'])
    )
    
    if exclude_appointment_id:
        query = query.filter(Appointment.id != exclude_appointment_id)
    
    return query.first() is not None

def get_doctors_by_specialization(specialization=None):
    """Get doctors filtered by specialization"""
    query = db.session.query(User).join(DoctorProfile).filter(User.role == 'doctor', User.is_active == True)
    
    if specialization:
        query = query.filter(DoctorProfile.specialization.ilike(f'%{specialization}%'))
    
    return query.all()

def get_appointment_stats():
    """Get appointment statistics for admin dashboard"""
    total_doctors = User.query.filter_by(role='doctor', is_active=True).count()
    total_patients = User.query.filter_by(role='patient', is_active=True).count()
    total_appointments = Appointment.query.count()
    pending_appointments = Appointment.query.filter_by(status='Booked').count()
    completed_appointments = Appointment.query.filter_by(status='Completed').count()
    
    return {
        'total_doctors': total_doctors,
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'completed_appointments': completed_appointments
    }