"""
Patient blueprint for the Hospital Management System.
Handles patient-specific operations: search doctors, book/reschedule/cancel appointments.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, DoctorProfile, DoctorAvailability, Appointment
from utils import roles_required, check_appointment_conflict, get_available_slots, validate_date_format
from datetime import datetime, timedelta

patient = Blueprint('patient', __name__, url_prefix='/patient')


@patient.route('/dashboard')
@login_required
@roles_required('patient')
def dashboard():
    """
    Patient dashboard showing upcoming appointments and quick access to features.
    """
    today = datetime.now().date()
    
    # Upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        Appointment.date >= today,
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).all()
    
    # Past appointments (completed or cancelled)
    past_appointments = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        db.or_(
            Appointment.date < today,
            Appointment.status.in_(['Completed', 'Cancelled'])
        )
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).limit(5).all()
    
    # Get available specializations
    specializations = db.session.query(DoctorProfile.specialization).distinct().all()
    specializations = [s[0] for s in specializations]
    
    return render_template('patient/dashboard.html',
                         upcoming_appointments=upcoming_appointments,
                         past_appointments=past_appointments,
                         specializations=specializations)


@patient.route('/doctors')
@login_required
@roles_required('patient')
def search_doctors():
    """
    Search and browse doctors by specialization.
    Shows available slots for the next 7 days.
    """
    specialization = request.args.get('specialization', '').strip()
    search = request.args.get('search', '').strip()
    
    query = User.query.filter_by(role='doctor').join(DoctorProfile)
    
    if specialization:
        query = query.filter(DoctorProfile.specialization.ilike(f'%{specialization}%'))
    
    if search:
        query = query.filter(
            db.or_(
                User.name.ilike(f'%{search}%'),
                DoctorProfile.specialization.ilike(f'%{search}%')
            )
        )
    
    doctors = query.all()
    
    # Get all available specializations for the filter
    all_specializations = db.session.query(DoctorProfile.specialization).distinct().all()
    all_specializations = [s[0] for s in all_specializations]
    
    # For each doctor, get available slots count for next 7 days
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    
    doctor_availability = {}
    for doc in doctors:
        available_slots = DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == doc.id,
            DoctorAvailability.date >= today,
            DoctorAvailability.date <= next_week,
            DoctorAvailability.is_booked == False
        ).count()
        doctor_availability[doc.id] = available_slots
    
    return render_template('patient/search_doctors.html',
                         doctors=doctors,
                         specializations=all_specializations,
                         selected_specialization=specialization,
                         search=search,
                         doctor_availability=doctor_availability)


@patient.route('/doctors/<int:doctor_id>/book', methods=['GET', 'POST'])
@login_required
@roles_required('patient')
def book_appointment(doctor_id):
    """
    Book an appointment with a specific doctor.
    Shows available slots and handles booking with double-booking prevention.
    """
    doctor = User.query.filter_by(id=doctor_id, role='doctor').first_or_404()
    
    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        time_str = request.form.get('time', '').strip()
        
        # Validate inputs
        if not date_str or not time_str:
            flash('Please select both date and time.', 'danger')
        elif not validate_date_format(date_str):
            flash('Invalid date format.', 'danger')
        else:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Check for conflicts
            if check_appointment_conflict(doctor_id, date_obj, time_str):
                flash('This time slot is no longer available. Please choose another slot.', 'warning')
                
                # Show available alternatives
                available = get_available_slots(doctor_id, date_obj)
                if available:
                    flash(f'Available slots for {date_str}: {", ".join(available)}', 'info')
            else:
                # Create appointment
                new_appointment = Appointment(
                    patient_id=current_user.id,
                    doctor_id=doctor_id,
                    date=date_obj,
                    time=time_str,
                    status='Booked'
                )
                
                # Mark slot as booked
                slot = DoctorAvailability.query.filter_by(
                    doctor_id=doctor_id,
                    date=date_obj,
                    time=time_str
                ).first()
                
                if slot:
                    slot.is_booked = True
                
                try:
                    db.session.add(new_appointment)
                    db.session.commit()
                    flash('Appointment booked successfully!', 'success')
                    return redirect(url_for('patient.dashboard'))
                except Exception as e:
                    db.session.rollback()
                    flash('An error occurred while booking the appointment.', 'danger')
    
    # Get available slots for next 7 days
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    
    availability = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= next_week,
        DoctorAvailability.is_booked == False
    ).order_by(DoctorAvailability.date, DoctorAvailability.time).all()
    
    # Group by date
    availability_by_date = {}
    for slot in availability:
        # Double-check for conflicts
        if not check_appointment_conflict(doctor_id, slot.date, slot.time):
            date_key = slot.date.strftime('%Y-%m-%d')
            if date_key not in availability_by_date:
                availability_by_date[date_key] = []
            availability_by_date[date_key].append(slot.time)
    
    return render_template('patient/book_appointment.html',
                         doctor=doctor,
                         availability_by_date=availability_by_date)


@patient.route('/appointments/<int:appointment_id>')
@login_required
@roles_required('patient')
def appointment_detail(appointment_id):
    """
    View details of a specific appointment.
    Shows treatment notes if completed.
    """
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=current_user.id
    ).first_or_404()
    
    return render_template('patient/appointment_detail.html', appointment=appointment)


@patient.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@login_required
@roles_required('patient')
def cancel_appointment(appointment_id):
    """
    Cancel a booked appointment.
    """
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=current_user.id
    ).first_or_404()
    
    if appointment.status == 'Cancelled':
        flash('This appointment is already cancelled.', 'info')
    elif appointment.status == 'Completed':
        flash('Cannot cancel a completed appointment.', 'warning')
    else:
        # Update appointment status
        appointment.status = 'Cancelled'
        appointment.updated_at = datetime.utcnow()
        
        # Free up the slot
        slot = DoctorAvailability.query.filter_by(
            doctor_id=appointment.doctor_id,
            date=appointment.date,
            time=appointment.time
        ).first()
        
        if slot:
            slot.is_booked = False
        
        try:
            db.session.commit()
            flash('Appointment cancelled successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while cancelling the appointment.', 'danger')
    
    return redirect(url_for('patient.dashboard'))


@patient.route('/appointments/<int:appointment_id>/reschedule', methods=['GET', 'POST'])
@login_required
@roles_required('patient')
def reschedule_appointment(appointment_id):
    """
    Reschedule an existing appointment to a new date/time.
    """
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=current_user.id
    ).first_or_404()
    
    if appointment.status != 'Booked':
        flash('Only booked appointments can be rescheduled.', 'warning')
        return redirect(url_for('patient.dashboard'))
    
    if request.method == 'POST':
        new_date_str = request.form.get('date', '').strip()
        new_time_str = request.form.get('time', '').strip()
        
        # Validate inputs
        if not new_date_str or not new_time_str:
            flash('Please select both date and time.', 'danger')
        elif not validate_date_format(new_date_str):
            flash('Invalid date format.', 'danger')
        else:
            new_date_obj = datetime.strptime(new_date_str, '%Y-%m-%d').date()
            
            # Check for conflicts (excluding current appointment)
            if check_appointment_conflict(appointment.doctor_id, new_date_obj, new_time_str, appointment.id):
                flash('This time slot is not available. Please choose another slot.', 'warning')
                
                # Show available alternatives
                available = get_available_slots(appointment.doctor_id, new_date_obj)
                if available:
                    flash(f'Available slots for {new_date_str}: {", ".join(available)}', 'info')
            else:
                # Free up old slot
                old_slot = DoctorAvailability.query.filter_by(
                    doctor_id=appointment.doctor_id,
                    date=appointment.date,
                    time=appointment.time
                ).first()
                
                if old_slot:
                    old_slot.is_booked = False
                
                # Update appointment
                appointment.date = new_date_obj
                appointment.time = new_time_str
                appointment.updated_at = datetime.utcnow()
                
                # Mark new slot as booked
                new_slot = DoctorAvailability.query.filter_by(
                    doctor_id=appointment.doctor_id,
                    date=new_date_obj,
                    time=new_time_str
                ).first()
                
                if new_slot:
                    new_slot.is_booked = True
                
                try:
                    db.session.commit()
                    flash('Appointment rescheduled successfully!', 'success')
                    return redirect(url_for('patient.dashboard'))
                except Exception as e:
                    db.session.rollback()
                    flash('An error occurred while rescheduling the appointment.', 'danger')
    
    # Get available slots for next 7 days
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    
    doctor = appointment.doctor
    
    availability = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.date >= today,
        DoctorAvailability.date <= next_week,
        DoctorAvailability.is_booked == False
    ).order_by(DoctorAvailability.date, DoctorAvailability.time).all()
    
    # Group by date
    availability_by_date = {}
    for slot in availability:
        # Double-check for conflicts (excluding current appointment)
        if not check_appointment_conflict(doctor.id, slot.date, slot.time, appointment.id):
            date_key = slot.date.strftime('%Y-%m-%d')
            if date_key not in availability_by_date:
                availability_by_date[date_key] = []
            availability_by_date[date_key].append(slot.time)
    
    return render_template('patient/reschedule_appointment.html',
                         appointment=appointment,
                         availability_by_date=availability_by_date)
