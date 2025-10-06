"""
Doctor blueprint for appointment management and patient care
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta, time
from models import db, User, DoctorProfile, DoctorAvailability, Appointment, Treatment, get_available_slots, check_appointment_conflict
from utils import doctor_required, sanitize_input, FlashMessage, get_time_slots, get_next_7_days, parse_date, parse_time, format_date, format_time

# Create blueprint
doctor = Blueprint('doctor', __name__, url_prefix='/doctor')

@doctor.route('/dashboard')
@doctor_required
def dashboard():
    """
    Doctor dashboard showing today's appointments and quick stats
    """
    today = date.today()
    
    # Get today's appointments
    todays_appointments = Appointment.query.filter_by(
        doctor_id=current_user.id,
        date=today
    ).order_by(Appointment.time).all()
    
    # Get upcoming appointments (next 7 days)
    end_date = today + timedelta(days=7)
    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.date > today,
        Appointment.date <= end_date,
        Appointment.status == 'Booked'
    ).order_by(Appointment.date, Appointment.time).limit(5).all()
    
    # Get recent completed appointments
    recent_completed = Appointment.query.filter_by(
        doctor_id=current_user.id,
        status='Completed'
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).limit(5).all()
    
    # Calculate statistics
    total_patients = db.session.query(Appointment.patient_id).filter_by(
        doctor_id=current_user.id
    ).distinct().count()
    
    total_appointments = Appointment.query.filter_by(doctor_id=current_user.id).count()
    completed_appointments = Appointment.query.filter_by(
        doctor_id=current_user.id, 
        status='Completed'
    ).count()
    
    pending_appointments = Appointment.query.filter_by(
        doctor_id=current_user.id, 
        status='Booked'
    ).count()
    
    stats = {
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'pending_appointments': pending_appointments,
        'todays_appointments': len(todays_appointments)
    }
    
    return render_template('doctor/dashboard.html',
                         todays_appointments=todays_appointments,
                         upcoming_appointments=upcoming_appointments,
                         recent_completed=recent_completed,
                         stats=stats)

@doctor.route('/appointments')
@doctor_required
def appointments_list():
    """
    List all doctor's appointments with filtering
    """
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    date_filter = request.args.get('date', '')
    
    # Build query
    query = Appointment.query.filter_by(doctor_id=current_user.id)
    
    if status:
        query = query.filter_by(status=status)
    
    if date_filter:
        try:
            filter_date = parse_date(date_filter)
            query = query.filter_by(date=filter_date)
        except ValueError:
            FlashMessage.error('Invalid date format.')
    
    # Order by date and time (most recent first)
    query = query.order_by(Appointment.date.desc(), Appointment.time.desc())
    
    # Paginate results
    appointments = query.paginate(
        page=page, 
        per_page=10, 
        error_out=False
    )
    
    return render_template('doctor/appointments_list.html',
                         appointments=appointments,
                         status=status,
                         date_filter=date_filter)

@doctor.route('/appointments/<int:appointment_id>')
@doctor_required
def appointment_detail(appointment_id):
    """
    View detailed appointment information
    """
    appointment = Appointment.query.filter_by(
        id=appointment_id, 
        doctor_id=current_user.id
    ).first_or_404()
    
    return render_template('doctor/appointment_detail.html', 
                         appointment=appointment)

@doctor.route('/appointments/<int:appointment_id>/complete', methods=['GET', 'POST'])
@doctor_required
def complete_appointment(appointment_id):
    """
    Mark appointment as completed and add treatment notes
    """
    appointment = Appointment.query.filter_by(
        id=appointment_id, 
        doctor_id=current_user.id,
        status='Booked'
    ).first_or_404()
    
    if request.method == 'POST':
        # Get form data
        diagnosis = sanitize_input(request.form.get('diagnosis', ''))
        prescription = sanitize_input(request.form.get('prescription', ''))
        notes = sanitize_input(request.form.get('notes', ''))
        
        # Validate input
        if not diagnosis:
            FlashMessage.error('Diagnosis is required.')
            return render_template('doctor/complete_appointment.html', 
                                 appointment=appointment)
        
        try:
            # Update appointment status
            appointment.status = 'Completed'
            appointment.updated_at = datetime.utcnow()
            
            # Create or update treatment record
            treatment = Treatment.query.filter_by(appointment_id=appointment.id).first()
            if not treatment:
                treatment = Treatment(
                    appointment_id=appointment.id,
                    recorded_by_doctor_id=current_user.id
                )
                db.session.add(treatment)
            
            treatment.diagnosis = diagnosis
            treatment.prescription = prescription
            treatment.notes = notes
            treatment.recorded_at = datetime.utcnow()
            
            db.session.commit()
            
            FlashMessage.success('Appointment completed successfully!')
            return redirect(url_for('doctor.appointment_detail', appointment_id=appointment.id))
            
        except Exception as e:
            db.session.rollback()
            FlashMessage.error('An error occurred while completing the appointment. Please try again.')
    
    return render_template('doctor/complete_appointment.html', 
                         appointment=appointment)

@doctor.route('/patients/<int:patient_id>/history')
@doctor_required
def patient_history(patient_id):
    """
    View patient's complete medical history with this doctor
    """
    patient = User.query.filter_by(id=patient_id, role='patient').first_or_404()
    
    # Get all appointments between this doctor and patient
    appointments = Appointment.query.filter_by(
        doctor_id=current_user.id,
        patient_id=patient_id
    ).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    
    # Check if doctor has treated this patient
    if not appointments:
        FlashMessage.warning('No appointment history found with this patient.')
        return redirect(url_for('doctor.dashboard'))
    
    # Get completed appointments with treatments
    completed_appointments = [a for a in appointments if a.status == 'Completed' and a.treatment]
    
    return render_template('doctor/patient_history.html',
                         patient=patient,
                         appointments=appointments,
                         completed_appointments=completed_appointments)

@doctor.route('/availability', methods=['GET', 'POST'])
@doctor_required
def manage_availability():
    """
    Manage doctor's availability for the next 7 days
    """
    if request.method == 'POST':
        # Get selected dates and times
        selected_slots = request.form.getlist('availability_slots')
        
        try:
            # Get next 7 days
            next_days = get_next_7_days()
            
            # Remove existing availability for next 7 days (that are not booked)
            DoctorAvailability.query.filter(
                DoctorAvailability.doctor_id == current_user.id,
                DoctorAvailability.date.in_(next_days),
                DoctorAvailability.is_booked == False
            ).delete(synchronize_session=False)
            
            # Add new availability slots
            time_slots = get_time_slots()
            
            for slot in selected_slots:
                try:
                    date_str, time_str = slot.split('_')
                    slot_date = parse_date(date_str)
                    slot_time = parse_time(time_str)
                    
                    # Check if slot already exists and is booked
                    existing_slot = DoctorAvailability.query.filter_by(
                        doctor_id=current_user.id,
                        date=slot_date,
                        time=slot_time
                    ).first()
                    
                    if not existing_slot:
                        availability = DoctorAvailability(
                            doctor_id=current_user.id,
                            date=slot_date,
                            time=slot_time,
                            is_booked=False
                        )
                        db.session.add(availability)
                    elif not existing_slot.is_booked:
                        existing_slot.is_booked = False
                
                except (ValueError, AttributeError):
                    continue
            
            db.session.commit()
            FlashMessage.success('Availability updated successfully!')
            
        except Exception as e:
            db.session.rollback()
            FlashMessage.error('An error occurred while updating availability. Please try again.')
    
    # Get current availability for next 7 days
    next_days = get_next_7_days()
    current_availability = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == current_user.id,
        DoctorAvailability.date.in_(next_days)
    ).all()
    
    # Organize availability by date and time
    availability_dict = {}
    for slot in current_availability:
        date_key = slot.date.strftime('%Y-%m-%d')
        if date_key not in availability_dict:
            availability_dict[date_key] = {}
        time_key = slot.time.strftime('%H:%M')
        availability_dict[date_key][time_key] = {
            'available': True,
            'booked': slot.is_booked
        }
    
    # Get all possible time slots
    time_slots = get_time_slots()
    
    return render_template('doctor/manage_availability.html',
                         next_days=next_days,
                         time_slots=time_slots,
                         availability_dict=availability_dict)

@doctor.route('/schedule')
@doctor_required
def schedule():
    """
    View doctor's schedule for the next 7 days
    """
    next_days = get_next_7_days()
    
    # Get appointments for next 7 days
    appointments = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.date.in_(next_days),
        Appointment.status.in_(['Booked', 'Completed'])
    ).order_by(Appointment.date, Appointment.time).all()
    
    # Get availability for next 7 days
    availability = DoctorAvailability.query.filter(
        DoctorAvailability.doctor_id == current_user.id,
        DoctorAvailability.date.in_(next_days)
    ).all()
    
    # Organize schedule by date
    schedule_dict = {}
    for day in next_days:
        date_key = day.strftime('%Y-%m-%d')
        schedule_dict[date_key] = {
            'date': day,
            'appointments': [],
            'available_slots': [],
            'total_slots': 0
        }
    
    # Add appointments to schedule
    for appointment in appointments:
        date_key = appointment.date.strftime('%Y-%m-%d')
        if date_key in schedule_dict:
            schedule_dict[date_key]['appointments'].append(appointment)
    
    # Add availability to schedule
    for slot in availability:
        date_key = slot.date.strftime('%Y-%m-%d')
        if date_key in schedule_dict:
            schedule_dict[date_key]['total_slots'] += 1
            if not slot.is_booked:
                schedule_dict[date_key]['available_slots'].append(slot)
    
    return render_template('doctor/schedule.html',
                         schedule_dict=schedule_dict,
                         next_days=next_days)

@doctor.route('/patients')
@doctor_required
def patients_list():
    """
    List all patients who have appointments with this doctor
    """
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    # Get unique patients who have appointments with this doctor
    query = db.session.query(User).join(Appointment, User.id == Appointment.patient_id)\
        .filter(Appointment.doctor_id == current_user.id)\
        .distinct()
    
    if search:
        query = query.filter(User.name.ilike(f'%{search}%'))
    
    # Paginate results
    patients = query.paginate(
        page=page, 
        per_page=10, 
        error_out=False
    )
    
    # Get appointment counts for each patient
    patient_stats = {}
    for patient in patients.items:
        total_appointments = Appointment.query.filter_by(
            doctor_id=current_user.id,
            patient_id=patient.id
        ).count()
        
        completed_appointments = Appointment.query.filter_by(
            doctor_id=current_user.id,
            patient_id=patient.id,
            status='Completed'
        ).count()
        
        patient_stats[patient.id] = {
            'total': total_appointments,
            'completed': completed_appointments
        }
    
    return render_template('doctor/patients_list.html',
                         patients=patients,
                         search=search,
                         patient_stats=patient_stats)

# API endpoints for AJAX requests

@doctor.route('/api/appointments/today')
@doctor_required
def api_todays_appointments():
    """
    API endpoint to get today's appointments
    """
    today = date.today()
    appointments = Appointment.query.filter_by(
        doctor_id=current_user.id,
        date=today
    ).order_by(Appointment.time).all()
    
    appointments_data = []
    for appointment in appointments:
        appointments_data.append({
            'id': appointment.id,
            'patient_name': appointment.patient.name,
            'time': appointment.time.strftime('%I:%M %p'),
            'status': appointment.status
        })
    
    return jsonify(appointments_data)

@doctor.route('/api/availability/<date_str>')
@doctor_required
def api_availability_for_date(date_str):
    """
    API endpoint to get availability for a specific date
    """
    try:
        target_date = parse_date(date_str)
        available_slots = get_available_slots(current_user.id, target_date)
        
        slots_data = []
        for slot in available_slots:
            slots_data.append({
                'time': slot.time.strftime('%H:%M'),
                'display_time': slot.time.strftime('%I:%M %p'),
                'is_booked': slot.is_booked
            })
        
        return jsonify(slots_data)
        
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400