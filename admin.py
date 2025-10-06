"""
Admin blueprint for the Hospital Management System.
Handles admin-only operations: CRUD for doctors/patients, view all appointments.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, DoctorProfile, DoctorAvailability, Appointment
from utils import roles_required, validate_date_format, validate_time_format
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from datetime import datetime, timedelta

admin = Blueprint('admin', __name__, url_prefix='/admin')


class DoctorForm(Form):
    """Form for creating/editing doctor profiles."""
    name = StringField('Full Name', [
        validators.DataRequired(message='Name is required'),
        validators.Length(min=2, max=100)
    ])
    email = StringField('Email', [
        validators.DataRequired(message='Email is required'),
        validators.Email(message='Invalid email address')
    ])
    contact = StringField('Contact Number', [
        validators.DataRequired(message='Contact number is required')
    ])
    specialization = StringField('Specialization', [
        validators.DataRequired(message='Specialization is required'),
        validators.Length(min=2, max=100)
    ])
    bio = TextAreaField('Biography')
    password = PasswordField('Password', [
        validators.Optional(),
        validators.Length(min=6, message='Password must be at least 6 characters')
    ])


@admin.route('/dashboard')
@login_required
@roles_required('admin')
def dashboard():
    """
    Admin dashboard showing summary statistics.
    Displays: total doctors, total patients, total appointments.
    """
    # Count statistics
    total_doctors = User.query.filter_by(role='doctor').count()
    total_patients = User.query.filter_by(role='patient').count()
    total_appointments = Appointment.query.count()
    
    # Upcoming appointments (next 7 days)
    today = datetime.now().date()
    next_week = today + timedelta(days=7)
    upcoming_appointments = Appointment.query.filter(
        Appointment.date >= today,
        Appointment.date <= next_week,
        Appointment.status == 'Booked'
    ).count()
    
    # Recent appointments
    recent_appointments = Appointment.query.order_by(
        Appointment.created_at.desc()
    ).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_doctors=total_doctors,
                         total_patients=total_patients,
                         total_appointments=total_appointments,
                         upcoming_appointments=upcoming_appointments,
                         recent_appointments=recent_appointments)


@admin.route('/doctors')
@login_required
@roles_required('admin')
def doctors_list():
    """
    List all doctors with search functionality.
    Supports search by name or specialization.
    """
    search = request.args.get('search', '').strip()
    
    query = User.query.filter_by(role='doctor')
    
    if search:
        query = query.join(DoctorProfile).filter(
            db.or_(
                User.name.ilike(f'%{search}%'),
                DoctorProfile.specialization.ilike(f'%{search}%')
            )
        )
    
    doctors = query.all()
    
    return render_template('admin/doctors_list.html', doctors=doctors, search=search)


@admin.route('/doctors/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def add_doctor():
    """
    Create a new doctor profile with initial availability.
    """
    if request.method == 'POST':
        form = DoctorForm(request.form)
        
        if form.validate():
            email = form.email.data.strip().lower()
            
            # Check if email already exists
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash('A user with this email already exists.', 'danger')
                return render_template('admin/doctor_form.html', form=form, edit=False)
            
            # Create doctor user
            doctor = User(
                email=email,
                name=form.name.data.strip(),
                contact=form.contact.data.strip(),
                role='doctor'
            )
            
            # Set password (default or provided)
            password = form.password.data if form.password.data else 'doctor123'
            doctor.set_password(password)
            
            db.session.add(doctor)
            db.session.flush()  # Get doctor.id
            
            # Create doctor profile
            profile = DoctorProfile(
                doctor_id=doctor.id,
                specialization=form.specialization.data.strip(),
                bio=form.bio.data.strip() if form.bio.data else '',
                phone=form.contact.data.strip()
            )
            
            db.session.add(profile)
            
            # Create availability for next 7 days (9 AM to 5 PM, hourly slots)
            today = datetime.now().date()
            for day_offset in range(7):
                date = today + timedelta(days=day_offset)
                for hour in range(9, 17):  # 9 AM to 4 PM (last slot at 4 PM)
                    time_slot = f"{hour:02d}:00"
                    availability = DoctorAvailability(
                        doctor_id=doctor.id,
                        date=date,
                        time=time_slot,
                        is_booked=False
                    )
                    db.session.add(availability)
            
            try:
                db.session.commit()
                flash(f'Doctor {doctor.name} added successfully!', 'success')
                return redirect(url_for('admin.doctors_list'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while adding the doctor.', 'danger')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(error, 'danger')
    
    form = DoctorForm()
    return render_template('admin/doctor_form.html', form=form, edit=False)


@admin.route('/doctors/<int:doctor_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def edit_doctor(doctor_id):
    """
    Edit an existing doctor's profile.
    """
    doctor = User.query.filter_by(id=doctor_id, role='doctor').first_or_404()
    
    if request.method == 'POST':
        form = DoctorForm(request.form)
        
        if form.validate():
            # Update basic user info
            doctor.name = form.name.data.strip()
            doctor.contact = form.contact.data.strip()
            
            # Update password if provided
            if form.password.data:
                doctor.set_password(form.password.data)
            
            # Update doctor profile
            if doctor.doctor_profile:
                doctor.doctor_profile.specialization = form.specialization.data.strip()
                doctor.doctor_profile.bio = form.bio.data.strip() if form.bio.data else ''
                doctor.doctor_profile.phone = form.contact.data.strip()
            
            try:
                db.session.commit()
                flash(f'Doctor {doctor.name} updated successfully!', 'success')
                return redirect(url_for('admin.doctors_list'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while updating the doctor.', 'danger')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(error, 'danger')
    
    # Pre-populate form with existing data
    form = DoctorForm(data={
        'name': doctor.name,
        'email': doctor.email,
        'contact': doctor.contact,
        'specialization': doctor.doctor_profile.specialization if doctor.doctor_profile else '',
        'bio': doctor.doctor_profile.bio if doctor.doctor_profile else ''
    })
    
    return render_template('admin/doctor_form.html', form=form, edit=True, doctor=doctor)


@admin.route('/doctors/<int:doctor_id>/delete', methods=['POST'])
@login_required
@roles_required('admin')
def delete_doctor(doctor_id):
    """
    Delete a doctor profile.
    """
    doctor = User.query.filter_by(id=doctor_id, role='doctor').first_or_404()
    
    try:
        # Check if doctor has any appointments
        appointment_count = Appointment.query.filter_by(doctor_id=doctor_id).count()
        
        if appointment_count > 0:
            flash(f'Cannot delete doctor {doctor.name} as they have {appointment_count} appointment(s) in the system.', 'warning')
        else:
            db.session.delete(doctor)
            db.session.commit()
            flash(f'Doctor {doctor.name} deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the doctor.', 'danger')
    
    return redirect(url_for('admin.doctors_list'))


@admin.route('/patients')
@login_required
@roles_required('admin')
def patients_list():
    """
    List all patients with search functionality.
    """
    search = request.args.get('search', '').strip()
    
    query = User.query.filter_by(role='patient')
    
    if search:
        query = query.filter(
            db.or_(
                User.name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    patients = query.all()
    
    return render_template('admin/patients_list.html', patients=patients, search=search)


@admin.route('/patients/<int:patient_id>')
@login_required
@roles_required('admin')
def patient_detail(patient_id):
    """
    View detailed patient profile and appointment history.
    """
    patient = User.query.filter_by(id=patient_id, role='patient').first_or_404()
    
    # Get all appointments for this patient
    appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(
        Appointment.date.desc(),
        Appointment.time.desc()
    ).all()
    
    return render_template('admin/patient_detail.html', patient=patient, appointments=appointments)


@admin.route('/appointments')
@login_required
@roles_required('admin')
def appointments_list():
    """
    List all appointments with filtering by status and date.
    """
    status_filter = request.args.get('status', '').strip()
    date_filter = request.args.get('date', '').strip()
    
    query = Appointment.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    if date_filter and validate_date_format(date_filter):
        date_obj = datetime.strptime(date_filter, '%Y-%m-%d').date()
        query = query.filter_by(date=date_obj)
    
    appointments = query.order_by(
        Appointment.date.desc(),
        Appointment.time.desc()
    ).all()
    
    return render_template('admin/appointments_list.html',
                         appointments=appointments,
                         status_filter=status_filter,
                         date_filter=date_filter)
