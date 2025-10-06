"""
Doctor blueprint for the Hospital Management System.
Handles doctor-specific operations: view appointments, mark complete, manage availability.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, DoctorProfile, DoctorAvailability, Appointment
from utils import roles_required, validate_date_format, validate_time_format
from wtforms import Form, TextAreaField, validators
from datetime import datetime, timedelta

doctor = Blueprint('doctor', __name__, url_prefix='/doctor')


class TreatmentForm(Form):
    """Form for recording treatment details when marking appointment as complete."""
    diagnosis = TextAreaField('Diagnosis', [
        validators.DataRequired(message='Diagnosis is required')
    ])
    prescription = TextAreaField('Prescription', [
        validators.DataRequired(message='Prescription is required')
    ])
    notes = TextAreaField('Additional Notes', [
        validators.Optional()
    ])


@doctor.route('/dashboard')
@login_required
@roles_required('doctor')
def dashboard():
    """
    Doctor dashboard showing today's appointments and upcoming week.
    """
    today = datetime.now().date()
    
    # Today's appointments
    todays_appointments = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.date == today,
        Appointment.status.in_(['Booked', 'Completed'])
    ).order_by(Appointment.time).all()
    
    # Upcoming appointments (next 7 days, excluding today)
    next_week = today + timedelta(days=7)
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.date > today,
        Appointment.date <= next_week,
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).all()
    
    # Statistics
    total_appointments = Appointment.query.filter_by(
        doctor_id=current_user.id
    ).count()
    
    completed_appointments = Appointment.query.filter_by(
        doctor_id=current_user.id,
        status='Completed'
    ).count()
    
    pending_appointments = Appointment.query.filter_by(
        doctor_id=current_user.id,
        status='Booked'
    ).count()
    
    return render_template('doctor/dashboard.html',
                         todays_appointments=todays_appointments,
                         upcoming_appointments=upcoming_appointments,
                         total_appointments=total_appointments,
                         completed_appointments=completed_appointments,
                         pending_appointments=pending_appointments)


@doctor.route('/appointments/<int:appointment_id>')
@login_required
@roles_required('doctor')
def appointment_detail(appointment_id):
    """
    View details of a specific appointment.
    Only accessible if the appointment belongs to the current doctor.
    """
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        doctor_id=current_user.id
    ).first_or_404()
    
    return render_template('doctor/appointment_detail.html', appointment=appointment)


@doctor.route('/appointments/<int:appointment_id>/complete', methods=['GET', 'POST'])
@login_required
@roles_required('doctor')
def complete_appointment(appointment_id):
    """
    Mark an appointment as completed and record treatment details.
    """
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        doctor_id=current_user.id
    ).first_or_404()
    
    # Check if already completed
    if appointment.status == 'Completed':
        flash('This appointment has already been marked as completed.', 'info')
        return redirect(url_for('doctor.appointment_detail', appointment_id=appointment_id))
    
    # Check if cancelled
    if appointment.status == 'Cancelled':
        flash('Cannot complete a cancelled appointment.', 'warning')
        return redirect(url_for('doctor.dashboard'))
    
    if request.method == 'POST':
        form = TreatmentForm(request.form)
        
        if form.validate():
            # Update appointment with treatment details
            appointment.diagnosis = form.diagnosis.data.strip()
            appointment.prescription = form.prescription.data.strip()
            appointment.notes = form.notes.data.strip() if form.notes.data else ''
            appointment.status = 'Completed'
            appointment.updated_at = datetime.utcnow()
            
            try:
                db.session.commit()
                flash('Appointment marked as completed successfully!', 'success')
                return redirect(url_for('doctor.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while updating the appointment.', 'danger')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(error, 'danger')
    
    form = TreatmentForm()
    return render_template('doctor/complete_appointment.html', appointment=appointment, form=form)


@doctor.route('/patient/<int:patient_id>/history')
@login_required
@roles_required('doctor')
def patient_history(patient_id):
    """
    View complete appointment history for a patient.
    Shows all past appointments and treatments.
    """
    patient = User.query.filter_by(id=patient_id, role='patient').first_or_404()
    
    # Get all appointments between this doctor and patient
    appointments = Appointment.query.filter_by(
        doctor_id=current_user.id,
        patient_id=patient_id
    ).order_by(
        Appointment.date.desc(),
        Appointment.time.desc()
    ).all()
    
    return render_template('doctor/patient_history.html',
                         patient=patient,
                         appointments=appointments)


@doctor.route('/availability', methods=['GET', 'POST'])
@login_required
@roles_required('doctor')
def manage_availability():
    """
    Manage doctor's availability for the next 7 days.
    Allows adding new time slots.
    """
    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        time_str = request.form.get('time', '').strip()
        
        # Validate inputs
        if not validate_date_format(date_str):
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
        elif not validate_time_format(time_str):
            flash('Invalid time format. Please use HH:MM (24-hour format).', 'danger')
        else:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            
            # Check if date is in valid range (today to next 7 days)
            if date_obj < today or date_obj > today + timedelta(days=7):
                flash('Date must be within the next 7 days.', 'danger')
            else:
                # Check if slot already exists
                existing = DoctorAvailability.query.filter_by(
                    doctor_id=current_user.id,
                    date=date_obj,
                    time=time_str
                ).first()
                
                if existing:
                    flash('This time slot already exists in your availability.', 'warning')
                else:
                    # Add new availability slot
                    new_slot = DoctorAvailability(
                        doctor_id=current_user.id,
                        date=date_obj,
                        time=time_str,
                        is_booked=False
                    )
                    
                    try:
                        db.session.add(new_slot)
                        db.session.commit()
                        flash('Availability slot added successfully!', 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash('An error occurred while adding the slot.', 'danger')
    
    # Get current availability for next 7 days
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    
    availability = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == current_user.id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= next_week
    ).order_by(DoctorAvailability.date, DoctorAvailability.time).all()
    
    # Group by date
    availability_by_date = {}
    for slot in availability:
        date_key = slot.date.strftime('%Y-%m-%d')
        if date_key not in availability_by_date:
            availability_by_date[date_key] = []
        availability_by_date[date_key].append(slot)
    
    return render_template('doctor/availability.html',
                         availability_by_date=availability_by_date,
                         today=today,
                         next_week=next_week)


@doctor.route('/appointments')
@login_required
@roles_required('doctor')
def appointments_list():
    """
    List all appointments for the current doctor with filtering options.
    """
    status_filter = request.args.get('status', '').strip()
    
    query = Appointment.query.filter_by(doctor_id=current_user.id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    appointments = query.order_by(
        Appointment.date.desc(),
        Appointment.time.desc()
    ).all()
    
    return render_template('doctor/appointments_list.html',
                         appointments=appointments,
                         status_filter=status_filter)
