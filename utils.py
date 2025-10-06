"""
Utility functions and decorators for the Hospital Management System.
Includes role-based authorization and helper functions.
"""
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def roles_required(*roles):
    """
    Decorator to restrict access to routes based on user role.
    Usage: @roles_required('admin', 'doctor')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def format_date(date_obj):
    """
    Format a date object to a readable string.
    Args:
        date_obj: datetime.date object
    Returns:
        str: Formatted date string (e.g., "January 15, 2024")
    """
    if not date_obj:
        return ''
    return date_obj.strftime('%B %d, %Y')


def format_time(time_str):
    """
    Format a time string to 12-hour format with AM/PM.
    Args:
        time_str: Time string in HH:MM format
    Returns:
        str: Formatted time string (e.g., "2:30 PM")
    """
    if not time_str:
        return ''
    try:
        from datetime import datetime
        time_obj = datetime.strptime(time_str, '%H:%M')
        return time_obj.strftime('%I:%M %p')
    except:
        return time_str


def validate_date_format(date_str):
    """
    Validate that a date string is in YYYY-MM-DD format.
    Args:
        date_str: Date string to validate
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        from datetime import datetime
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except:
        return False


def validate_time_format(time_str):
    """
    Validate that a time string is in HH:MM format.
    Args:
        time_str: Time string to validate
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        from datetime import datetime
        datetime.strptime(time_str, '%H:%M')
        return True
    except:
        return False


def check_appointment_conflict(doctor_id, date, time, appointment_id=None):
    """
    Check if there's a conflicting appointment for the given doctor, date, and time.
    Args:
        doctor_id: Doctor's user ID
        date: Appointment date
        time: Appointment time
        appointment_id: Current appointment ID (for rescheduling, to exclude from check)
    Returns:
        bool: True if conflict exists, False otherwise
    """
    from models import Appointment, db
    
    query = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == date,
        Appointment.time == time,
        Appointment.status.in_(['Booked', 'Completed'])
    )
    
    # Exclude current appointment when rescheduling
    if appointment_id:
        query = query.filter(Appointment.id != appointment_id)
    
    return query.first() is not None


def get_available_slots(doctor_id, date):
    """
    Get available time slots for a doctor on a specific date.
    Args:
        doctor_id: Doctor's user ID
        date: Date to check availability
    Returns:
        list: List of available time slots
    """
    from models import DoctorAvailability, Appointment, db
    
    # Get all slots for this doctor on this date
    all_slots = DoctorAvailability.query.filter_by(
        doctor_id=doctor_id,
        date=date
    ).all()
    
    # Filter out booked slots
    available = []
    for slot in all_slots:
        if not slot.is_booked:
            # Double-check against appointments table
            conflict = check_appointment_conflict(doctor_id, date, slot.time)
            if not conflict:
                available.append(slot.time)
    
    return sorted(available)
