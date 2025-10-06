"""
Patient blueprint for appointment booking and medical records
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from models import db, User, DoctorProfile, DoctorAvailability, Appointment, Treatment, get_available_slots, check_appointment_conflict, get_doctors_by_specialization
from utils import patient_required, sanitize_input, FlashMessage, get_next_7_days, parse_date, parse_time, format_date, format_time, get_available_specializations, validate_phone

# Create blueprint
patient = Blueprint('patient', __name__, url_prefix='/patient')

@patient.route('/dashboard')
@patient_required
def dashboard():
    """
    Patient dashboard showing appointments and quick actions
    """
    # Get upcoming appointments
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        Appointment.date >= date.today(),
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).limit(5).all()
    
    # Get recent completed appointments
    recent_completed = Appointment.query.filter_by(
        patient_id=current_user.id,
        status='Completed'
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).limit(5).all()
    
    # Calculate statistics
    total_appointments = Appointment.query.filter_by(patient_id=current_user.id).count()
    completed_appointments = Appointment.query.filter_by(
        patient_id=current_user.id, 
        status='Completed'
    ).count()
    
    cancelled_appointments = Appointment.query.filter_by(
        patient_id=current_user.id, 
        status='Cancelled'
    ).count()
    
    # Get unique doctors visited
    doctors_visited = db.session.query(Appointment.doctor_id).filter_by(
        patient_id=current_user.id
    ).distinct().count()
    
    stats = {
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'cancelled_appointments': cancelled_appointments,
        'doctors_visited': doctors_visited,
        'upcoming_appointments': len(upcoming_appointments)
    }
    
    # Get available specializations for quick booking
    specializations = get_available_specializations()
    
    return render_template('patient/dashboard.html',
                         upcoming_appointments=upcoming_appointments,
                         recent_completed=recent_completed,
                         stats=stats,
                         specializations=specializations)

@patient.route('/doctors')
@patient_required
def search_doctors():
    """
    Search and browse doctors by specialization
    """
    specialization = request.args.get('specialization', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = db.session.query(User).join(DoctorProfile).filter(
        User.role == 'doctor',
        User.is_active == True
    )
    
    if specialization:
        query = query.filter(DoctorProfile.specialization.ilike(f'%{specialization}%'))
    
    if search:
        query = query.filter(User.name.ilike(f'%{search}%'))
    
    # Order by name
    query = query.order_by(User.name)
    
    # Paginate results
    doctors = query.paginate(
        page=page, 
        per_page=6, 
        error_out=False
    )
    
    # Get availability for each doctor (next 7 days)
    doctor_availability = {}
    for doctor in doctors.items:
        available_slots = get_available_slots(doctor.id)
        doctor_availability[doctor.id] = len(available_slots)
    
    specializations = get_available_specializations()
    
    return render_template('patient/search_doctors.html',
                         doctors=doctors,
                         specialization=specialization,
                         search=search,
                         specializations=specializations,
                         doctor_availability=doctor_availability)

@patient.route('/doctors/<int:doctor_id>')
@patient_required
def doctor_profile(doctor_id):
    """
    View doctor profile and available appointment slots
    """
    doctor = User.query.filter_by(id=doctor_id, role='doctor', is_active=True).first_or_404()
    
    # Get available slots for next 7 days
    available_slots = get_available_slots(doctor_id)
    
    # Organize slots by date
    slots_by_date = {}
    for slot in available_slots:
        date_key = slot.date.strftime('%Y-%m-%d')
        if date_key not in slots_by_date:
            slots_by_date[date_key] = {
                'date': slot.date,
                'slots': []
            }
        slots_by_date[date_key]['slots'].append(slot)
    
    # Get patient's appointment history with this doctor
    appointment_history = Appointment.query.filter_by(
        patient_id=current_user.id,
        doctor_id=doctor_id
    ).order_by(Appointment.date.desc()).limit(5).all()
    
    return render_template('patient/doctor_profile.html',
                         doctor=doctor,
                         slots_by_date=slots_by_date,
                         appointment_history=appointment_history)

@patient.route('/doctors/<int:doctor_id>/book', methods=['GET', 'POST'])
@patient_required
def book_appointment(doctor_id):
    """
    Book an appointment with a specific doctor
    """
    doctor = User.query.filter_by(id=doctor_id, role='doctor', is_active=True).first_or_404()
    
    if request.method == 'POST':
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        
        # Validate input
        if not appointment_date or not appointment_time:
            FlashMessage.error('Please select both date and time for the appointment.')
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
        
        try:
            # Parse date and time
            appt_date = parse_date(appointment_date)
            appt_time = parse_time(appointment_time)
            
            # Validate date is in the future
            if appt_date < date.today():
                FlashMessage.error('Cannot book appointments in the past.')
                return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
            
            # Check if slot is available
            availability_slot = DoctorAvailability.query.filter_by(
                doctor_id=doctor_id,
                date=appt_date,
                time=appt_time,
                is_booked=False
            ).first()
            
            if not availability_slot:
                FlashMessage.error('Selected time slot is not available.')
                return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
            
            # Check for appointment conflicts
            if check_appointment_conflict(doctor_id, appt_date, appt_time):
                FlashMessage.error('This time slot is already booked.')
                return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
            
            # Check if patient already has an appointment at the same time
            patient_conflict = Appointment.query.filter(
                Appointment.patient_id == current_user.id,
                Appointment.date == appt_date,
                Appointment.time == appt_time,
                Appointment.status == 'Booked'
            ).first()
            
            if patient_conflict:
                FlashMessage.error('You already have an appointment at this time.')
                return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
            
            # Create appointment
            appointment = Appointment(
                patient_id=current_user.id,
                doctor_id=doctor_id,
                date=appt_date,
                time=appt_time,
                status='Booked'
            )
            
            # Mark availability slot as booked
            availability_slot.is_booked = True
            
            db.session.add(appointment)
            db.session.commit()
            
            FlashMessage.success(f'Appointment booked successfully with Dr. {doctor.name} on {format_date(appt_date)} at {format_time(appt_time)}!')
            return redirect(url_for('patient.appointments'))
            
        except ValueError as e:
            FlashMessage.error('Invalid date or time format.')
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
        except Exception as e:
            db.session.rollback()
            FlashMessage.error('An error occurred while booking the appointment. Please try again.')
            return redirect(url_for('patient.book_appointment', doctor_id=doctor_id))
    
    # Get available slots for next 7 days
    available_slots = get_available_slots(doctor_id)
    
    # Organize slots by date
    slots_by_date = {}
    for slot in available_slots:
        date_key = slot.date.strftime('%Y-%m-%d')
        if date_key not in slots_by_date:
            slots_by_date[date_key] = {
                'date': slot.date,
                'display_date': format_date(slot.date),
                'slots': []
            }
        slots_by_date[date_key]['slots'].append({
            'time': slot.time,
            'display_time': format_time(slot.time),
            'value': slot.time.strftime('%H:%M')
        })
    
    return render_template('patient/book_appointment.html',
                         doctor=doctor,
                         slots_by_date=slots_by_date)

@patient.route('/appointments')
@patient_required
def appointments():
    """
    View all patient appointments
    """
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    # Build query
    query = Appointment.query.filter_by(patient_id=current_user.id)
    
    if status:
        query = query.filter_by(status=status)
    
    # Order by date and time (most recent first)
    query = query.order_by(Appointment.date.desc(), Appointment.time.desc())
    
    # Paginate results
    appointments = query.paginate(
        page=page, 
        per_page=10, 
        error_out=False
    )
    
    return render_template('patient/appointments.html',
                         appointments=appointments,
                         status=status)

@patient.route('/appointments/<int:appointment_id>')
@patient_required
def appointment_detail(appointment_id):
    """
    View detailed appointment information and treatment notes
    """
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=current_user.id
    ).first_or_404()
    
    return render_template('patient/appointment_detail.html',
                         appointment=appointment)

@patient.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
@patient_required
def cancel_appointment(appointment_id):
    """
    Cancel a booked appointment
    """
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=current_user.id,
        status='Booked'
    ).first_or_404()
    
    # Check if appointment can be cancelled (not in the past)
    if not appointment.can_be_cancelled():
        FlashMessage.error('This appointment cannot be cancelled.')
        return redirect(url_for('patient.appointment_detail', appointment_id=appointment_id))
    
    try:
        # Update appointment status
        appointment.status = 'Cancelled'
        appointment.updated_at = datetime.utcnow()
        
        # Free up the availability slot
        availability_slot = DoctorAvailability.query.filter_by(
            doctor_id=appointment.doctor_id,
            date=appointment.date,
            time=appointment.time
        ).first()
        
        if availability_slot:
            availability_slot.is_booked = False
        
        db.session.commit()
        
        FlashMessage.success('Appointment cancelled successfully.')
        
    except Exception as e:
        db.session.rollback()
        FlashMessage.error('An error occurred while cancelling the appointment. Please try again.')
    
    return redirect(url_for('patient.appointments'))

@patient.route('/appointments/<int:appointment_id>/reschedule', methods=['GET', 'POST'])
@patient_required
def reschedule_appointment(appointment_id):
    """
    Reschedule a booked appointment
    """
    appointment = Appointment.query.filter_by(
        id=appointment_id,
        patient_id=current_user.id,
        status='Booked'
    ).first_or_404()
    
    # Check if appointment can be rescheduled
    if not appointment.can_be_rescheduled():
        FlashMessage.error('This appointment cannot be rescheduled.')
        return redirect(url_for('patient.appointment_detail', appointment_id=appointment_id))
    
    if request.method == 'POST':
        new_date = request.form.get('new_date')
        new_time = request.form.get('new_time')
        
        # Validate input
        if not new_date or not new_time:
            FlashMessage.error('Please select both new date and time.')
            return redirect(url_for('patient.reschedule_appointment', appointment_id=appointment_id))
        
        try:
            # Parse new date and time
            appt_date = parse_date(new_date)
            appt_time = parse_time(new_time)
            
            # Validate date is in the future
            if appt_date < date.today():
                FlashMessage.error('Cannot reschedule to a past date.')
                return redirect(url_for('patient.reschedule_appointment', appointment_id=appointment_id))
            
            # Check if new slot is available
            availability_slot = DoctorAvailability.query.filter_by(
                doctor_id=appointment.doctor_id,
                date=appt_date,
                time=appt_time,
                is_booked=False
            ).first()
            
            if not availability_slot:
                FlashMessage.error('Selected time slot is not available.')
                return redirect(url_for('patient.reschedule_appointment', appointment_id=appointment_id))
            
            # Check for appointment conflicts (excluding current appointment)
            if check_appointment_conflict(appointment.doctor_id, appt_date, appt_time, appointment.id):
                FlashMessage.error('This time slot is already booked.')
                return redirect(url_for('patient.reschedule_appointment', appointment_id=appointment_id))
            
            # Free up old slot
            old_availability = DoctorAvailability.query.filter_by(
                doctor_id=appointment.doctor_id,
                date=appointment.date,
                time=appointment.time
            ).first()
            
            if old_availability:
                old_availability.is_booked = False
            
            # Update appointment
            appointment.date = appt_date
            appointment.time = appt_time
            appointment.updated_at = datetime.utcnow()
            
            # Mark new slot as booked
            availability_slot.is_booked = True
            
            db.session.commit()
            
            FlashMessage.success(f'Appointment rescheduled successfully to {format_date(appt_date)} at {format_time(appt_time)}!')
            return redirect(url_for('patient.appointment_detail', appointment_id=appointment_id))
            
        except ValueError:
            FlashMessage.error('Invalid date or time format.')
        except Exception as e:
            db.session.rollback()
            FlashMessage.error('An error occurred while rescheduling the appointment. Please try again.')
    
    # Get available slots for rescheduling
    available_slots = get_available_slots(appointment.doctor_id)
    
    # Organize slots by date
    slots_by_date = {}
    for slot in available_slots:
        date_key = slot.date.strftime('%Y-%m-%d')
        if date_key not in slots_by_date:
            slots_by_date[date_key] = {
                'date': slot.date,
                'display_date': format_date(slot.date),
                'slots': []
            }
        slots_by_date[date_key]['slots'].append({
            'time': slot.time,
            'display_time': format_time(slot.time),
            'value': slot.time.strftime('%H:%M')
        })
    
    return render_template('patient/reschedule_appointment.html',
                         appointment=appointment,
                         slots_by_date=slots_by_date)

@patient.route('/medical-history')
@patient_required
def medical_history():
    """
    View complete medical history and treatment records
    """
    # Get all completed appointments with treatments
    completed_appointments = Appointment.query.filter_by(
        patient_id=current_user.id,
        status='Completed'
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    
    # Group by doctor for better organization
    history_by_doctor = {}
    for appointment in completed_appointments:
        doctor_id = appointment.doctor_id
        if doctor_id not in history_by_doctor:
            history_by_doctor[doctor_id] = {
                'doctor': appointment.doctor,
                'appointments': []
            }
        history_by_doctor[doctor_id]['appointments'].append(appointment)
    
    return render_template('patient/medical_history.html',
                         completed_appointments=completed_appointments,
                         history_by_doctor=history_by_doctor)

@patient.route('/profile')
@patient_required
def profile():
    """
    View and edit patient profile
    """
    return render_template('patient/profile.html', user=current_user)

@patient.route('/profile/edit', methods=['GET', 'POST'])
@patient_required
def edit_profile():
    """
    Edit patient profile information
    """
    if request.method == 'POST':
        name = sanitize_input(request.form.get('name', ''))
        contact = sanitize_input(request.form.get('contact', ''))
        
        # Validate input
        errors = []
        
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters long.')
        
        if contact and not validate_phone(contact):
            errors.append('Please enter a valid phone number.')
        
        if errors:
            for error in errors:
                FlashMessage.error(error)
            return render_template('patient/edit_profile.html')
        
        try:
            # Update profile
            current_user.name = name
            current_user.contact = contact
            
            db.session.commit()
            
            FlashMessage.success('Profile updated successfully!')
            return redirect(url_for('patient.profile'))
            
        except Exception as e:
            db.session.rollback()
            FlashMessage.error('An error occurred while updating profile. Please try again.')
    
    return render_template('patient/edit_profile.html')

# API endpoints for AJAX requests

@patient.route('/api/doctors/<int:doctor_id>/availability')
@patient_required
def api_doctor_availability(doctor_id):
    """
    API endpoint to get doctor's availability
    """
    available_slots = get_available_slots(doctor_id)
    
    slots_data = {}
    for slot in available_slots:
        date_key = slot.date.strftime('%Y-%m-%d')
        if date_key not in slots_data:
            slots_data[date_key] = []
        
        slots_data[date_key].append({
            'time': slot.time.strftime('%H:%M'),
            'display_time': format_time(slot.time)
        })
    
    return jsonify(slots_data)

@patient.route('/api/appointments/upcoming')
@patient_required
def api_upcoming_appointments():
    """
    API endpoint to get upcoming appointments
    """
    upcoming = Appointment.query.filter(
        Appointment.patient_id == current_user.id,
        Appointment.date >= date.today(),
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).limit(5).all()
    
    appointments_data = []
    for appointment in upcoming:
        appointments_data.append({
            'id': appointment.id,
            'doctor_name': f"Dr. {appointment.doctor.name}",
            'specialization': appointment.doctor.doctor_profile.specialization if appointment.doctor.doctor_profile else '',
            'date': format_date(appointment.date),
            'time': format_time(appointment.time),
            'can_cancel': appointment.can_be_cancelled(),
            'can_reschedule': appointment.can_be_rescheduled()
        })
    
    return jsonify(appointments_data)