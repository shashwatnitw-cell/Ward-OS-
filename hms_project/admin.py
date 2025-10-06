"""
Admin blueprint for hospital management system administration
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from models import db, User, DoctorProfile, DoctorAvailability, Appointment, Treatment, get_appointment_stats, get_doctors_by_specialization
from utils import admin_required, validate_email, validate_password, validate_phone, sanitize_input, FlashMessage, get_time_slots, get_next_7_days, parse_date, parse_time, get_available_specializations

# Create blueprint
admin = Blueprint('admin', __name__, url_prefix='/admin')

@admin.route('/dashboard')
@admin_required
def dashboard():
    """
    Admin dashboard with system overview and statistics
    """
    # Get statistics
    stats = get_appointment_stats()
    
    # Get recent appointments
    recent_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(5).all()
    
    # Get doctors by specialization count
    specialization_counts = {}
    doctors = User.query.filter_by(role='doctor', is_active=True).join(DoctorProfile).all()
    for doctor in doctors:
        spec = doctor.doctor_profile.specialization
        specialization_counts[spec] = specialization_counts.get(spec, 0) + 1
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_appointments=recent_appointments,
                         specialization_counts=specialization_counts)

@admin.route('/doctors')
@admin_required
def doctors_list():
    """
    List all doctors with search and filter capabilities
    """
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    specialization = request.args.get('specialization', '')
    
    # Build query
    query = db.session.query(User).join(DoctorProfile).filter(User.role == 'doctor')
    
    if search:
        query = query.filter(User.name.ilike(f'%{search}%'))
    
    if specialization:
        query = query.filter(DoctorProfile.specialization.ilike(f'%{specialization}%'))
    
    # Paginate results
    doctors = query.paginate(
        page=page, 
        per_page=10, 
        error_out=False
    )
    
    specializations = get_available_specializations()
    
    return render_template('admin/doctors_list.html', 
                         doctors=doctors, 
                         search=search, 
                         specialization=specialization,
                         specializations=specializations)

@admin.route('/doctors/new', methods=['GET', 'POST'])
@admin_required
def add_doctor():
    """
    Add new doctor with profile and initial availability
    """
    if request.method == 'POST':
        # Get form data
        name = sanitize_input(request.form.get('name', ''))
        email = sanitize_input(request.form.get('email', '').lower())
        password = request.form.get('password', '')
        specialization = sanitize_input(request.form.get('specialization', ''))
        bio = sanitize_input(request.form.get('bio', ''))
        phone = sanitize_input(request.form.get('phone', ''))
        experience_years = request.form.get('experience_years', type=int)
        
        # Validate input
        errors = []
        
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters long.')
        
        if not email:
            errors.append('Email is required.')
        elif not validate_email(email):
            errors.append('Please enter a valid email address.')
        else:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                errors.append('An account with this email already exists.')
        
        if not password:
            errors.append('Password is required.')
        else:
            is_valid, message = validate_password(password)
            if not is_valid:
                errors.append(message)
        
        if not specialization:
            errors.append('Specialization is required.')
        
        if phone and not validate_phone(phone):
            errors.append('Please enter a valid phone number.')
        
        if experience_years is not None and (experience_years < 0 or experience_years > 50):
            errors.append('Experience years must be between 0 and 50.')
        
        if errors:
            for error in errors:
                FlashMessage.error(error)
            return render_template('admin/add_doctor.html', 
                                 specializations=get_available_specializations())
        
        try:
            # Create doctor user
            doctor = User(
                name=name,
                email=email,
                role='doctor',
                contact=phone
            )
            doctor.set_password(password)
            
            db.session.add(doctor)
            db.session.flush()  # Get the doctor ID
            
            # Create doctor profile
            profile = DoctorProfile(
                doctor_id=doctor.id,
                specialization=specialization,
                bio=bio,
                phone=phone,
                experience_years=experience_years
            )
            
            db.session.add(profile)
            
            # Create initial availability (next 7 days, 9 AM to 5 PM)
            time_slots = get_time_slots()
            next_days = get_next_7_days()
            
            for day in next_days:
                # Skip weekends for initial availability
                if day.weekday() < 5:  # Monday = 0, Sunday = 6
                    for time_slot in time_slots:
                        availability = DoctorAvailability(
                            doctor_id=doctor.id,
                            date=day,
                            time=time_slot,
                            is_booked=False
                        )
                        db.session.add(availability)
            
            db.session.commit()
            
            FlashMessage.success(f'Doctor {name} has been added successfully!')
            return redirect(url_for('admin.doctors_list'))
            
        except Exception as e:
            db.session.rollback()
            FlashMessage.error('An error occurred while adding the doctor. Please try again.')
    
    return render_template('admin/add_doctor.html', 
                         specializations=get_available_specializations())

@admin.route('/doctors/<int:doctor_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_doctor(doctor_id):
    """
    Edit doctor information and profile
    """
    doctor = User.query.filter_by(id=doctor_id, role='doctor').first_or_404()
    
    if request.method == 'POST':
        # Get form data
        name = sanitize_input(request.form.get('name', ''))
        email = sanitize_input(request.form.get('email', '').lower())
        specialization = sanitize_input(request.form.get('specialization', ''))
        bio = sanitize_input(request.form.get('bio', ''))
        phone = sanitize_input(request.form.get('phone', ''))
        experience_years = request.form.get('experience_years', type=int)
        is_active = request.form.get('is_active') == 'on'
        
        # Validate input
        errors = []
        
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters long.')
        
        if not email:
            errors.append('Email is required.')
        elif not validate_email(email):
            errors.append('Please enter a valid email address.')
        else:
            existing_user = User.query.filter(User.email == email, User.id != doctor_id).first()
            if existing_user:
                errors.append('An account with this email already exists.')
        
        if not specialization:
            errors.append('Specialization is required.')
        
        if phone and not validate_phone(phone):
            errors.append('Please enter a valid phone number.')
        
        if experience_years is not None and (experience_years < 0 or experience_years > 50):
            errors.append('Experience years must be between 0 and 50.')
        
        if errors:
            for error in errors:
                FlashMessage.error(error)
            return render_template('admin/edit_doctor.html', 
                                 doctor=doctor, 
                                 specializations=get_available_specializations())
        
        try:
            # Update doctor user
            doctor.name = name
            doctor.email = email
            doctor.contact = phone
            doctor.is_active = is_active
            
            # Update doctor profile
            if not doctor.doctor_profile:
                profile = DoctorProfile(doctor_id=doctor.id)
                db.session.add(profile)
                doctor.doctor_profile = profile
            
            doctor.doctor_profile.specialization = specialization
            doctor.doctor_profile.bio = bio
            doctor.doctor_profile.phone = phone
            doctor.doctor_profile.experience_years = experience_years
            
            db.session.commit()
            
            FlashMessage.success(f'Doctor {name} has been updated successfully!')
            return redirect(url_for('admin.doctors_list'))
            
        except Exception as e:
            db.session.rollback()
            FlashMessage.error('An error occurred while updating the doctor. Please try again.')
    
    return render_template('admin/edit_doctor.html', 
                         doctor=doctor, 
                         specializations=get_available_specializations())

@admin.route('/doctors/<int:doctor_id>/delete', methods=['POST'])
@admin_required
def delete_doctor(doctor_id):
    """
    Deactivate doctor (soft delete)
    """
    doctor = User.query.filter_by(id=doctor_id, role='doctor').first_or_404()
    
    try:
        # Check if doctor has active appointments
        active_appointments = Appointment.query.filter_by(
            doctor_id=doctor_id, 
            status='Booked'
        ).count()
        
        if active_appointments > 0:
            FlashMessage.warning(f'Cannot delete Dr. {doctor.name} - they have {active_appointments} active appointments.')
            return redirect(url_for('admin.doctors_list'))
        
        # Soft delete (deactivate)
        doctor.is_active = False
        db.session.commit()
        
        FlashMessage.success(f'Dr. {doctor.name} has been deactivated successfully!')
        
    except Exception as e:
        db.session.rollback()
        FlashMessage.error('An error occurred while deleting the doctor. Please try again.')
    
    return redirect(url_for('admin.doctors_list'))

@admin.route('/patients')
@admin_required
def patients_list():
    """
    List all patients with search capabilities
    """
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    # Build query
    query = User.query.filter_by(role='patient')
    
    if search:
        query = query.filter(User.name.ilike(f'%{search}%'))
    
    # Paginate results
    patients = query.paginate(
        page=page, 
        per_page=10, 
        error_out=False
    )
    
    return render_template('admin/patients_list.html', 
                         patients=patients, 
                         search=search)

@admin.route('/patients/<int:patient_id>')
@admin_required
def patient_detail(patient_id):
    """
    View patient profile and appointment history
    """
    patient = User.query.filter_by(id=patient_id, role='patient').first_or_404()
    
    # Get patient's appointments
    appointments = Appointment.query.filter_by(patient_id=patient_id)\
        .order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    
    # Get appointment statistics
    total_appointments = len(appointments)
    completed_appointments = len([a for a in appointments if a.status == 'Completed'])
    cancelled_appointments = len([a for a in appointments if a.status == 'Cancelled'])
    upcoming_appointments = len([a for a in appointments if a.status == 'Booked'])
    
    stats = {
        'total': total_appointments,
        'completed': completed_appointments,
        'cancelled': cancelled_appointments,
        'upcoming': upcoming_appointments
    }
    
    return render_template('admin/patient_detail.html', 
                         patient=patient, 
                         appointments=appointments,
                         stats=stats)

@admin.route('/appointments')
@admin_required
def appointments_list():
    """
    List all appointments with filtering options
    """
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    date_filter = request.args.get('date', '')
    doctor_id = request.args.get('doctor_id', type=int)
    
    # Build query
    query = Appointment.query
    
    if status:
        query = query.filter_by(status=status)
    
    if date_filter:
        try:
            filter_date = parse_date(date_filter)
            query = query.filter_by(date=filter_date)
        except ValueError:
            FlashMessage.error('Invalid date format.')
    
    if doctor_id:
        query = query.filter_by(doctor_id=doctor_id)
    
    # Order by date and time
    query = query.order_by(Appointment.date.desc(), Appointment.time.desc())
    
    # Paginate results
    appointments = query.paginate(
        page=page, 
        per_page=15, 
        error_out=False
    )
    
    # Get doctors for filter dropdown
    doctors = User.query.filter_by(role='doctor', is_active=True).all()
    
    return render_template('admin/appointments_list.html', 
                         appointments=appointments,
                         status=status,
                         date_filter=date_filter,
                         doctor_id=doctor_id,
                         doctors=doctors)

@admin.route('/appointments/<int:appointment_id>')
@admin_required
def appointment_detail(appointment_id):
    """
    View detailed appointment information
    """
    appointment = Appointment.query.get_or_404(appointment_id)
    
    return render_template('admin/appointment_detail.html', 
                         appointment=appointment)

@admin.route('/reports')
@admin_required
def reports():
    """
    Generate system reports and analytics
    """
    # Get date range from request
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        # Default to last 30 days
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    else:
        try:
            start_date = parse_date(start_date)
            end_date = parse_date(end_date)
        except ValueError:
            FlashMessage.error('Invalid date format.')
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
    
    # Get appointments in date range
    appointments = Appointment.query.filter(
        Appointment.date >= start_date,
        Appointment.date <= end_date
    ).all()
    
    # Calculate statistics
    total_appointments = len(appointments)
    completed = len([a for a in appointments if a.status == 'Completed'])
    cancelled = len([a for a in appointments if a.status == 'Cancelled'])
    booked = len([a for a in appointments if a.status == 'Booked'])
    
    # Appointments by specialization
    specialization_stats = {}
    for appointment in appointments:
        if appointment.doctor.doctor_profile:
            spec = appointment.doctor.doctor_profile.specialization
            if spec not in specialization_stats:
                specialization_stats[spec] = {'total': 0, 'completed': 0}
            specialization_stats[spec]['total'] += 1
            if appointment.status == 'Completed':
                specialization_stats[spec]['completed'] += 1
    
    # Daily appointment counts
    daily_counts = {}
    for appointment in appointments:
        day = appointment.date.strftime('%Y-%m-%d')
        daily_counts[day] = daily_counts.get(day, 0) + 1
    
    report_data = {
        'start_date': start_date,
        'end_date': end_date,
        'total_appointments': total_appointments,
        'completed': completed,
        'cancelled': cancelled,
        'booked': booked,
        'completion_rate': (completed / total_appointments * 100) if total_appointments > 0 else 0,
        'specialization_stats': specialization_stats,
        'daily_counts': daily_counts
    }
    
    return render_template('admin/reports.html', report=report_data)

# API endpoint for dashboard data
@admin.route('/api/dashboard-data')
@admin_required
def dashboard_data():
    """
    API endpoint to get dashboard data as JSON
    """
    stats = get_appointment_stats()
    return jsonify(stats)