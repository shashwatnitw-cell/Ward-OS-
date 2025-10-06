"""
Authentication blueprint for the Hospital Management System.
Handles login, logout, and patient registration.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from models import db, User
from wtforms import Form, StringField, PasswordField, validators
from email_validator import validate_email, EmailNotValidError

auth = Blueprint('auth', __name__, url_prefix='')


class LoginForm(Form):
    """Form for user login."""
    email = StringField('Email', [
        validators.DataRequired(message='Email is required'),
        validators.Email(message='Invalid email address')
    ])
    password = PasswordField('Password', [
        validators.DataRequired(message='Password is required')
    ])


class RegisterForm(Form):
    """Form for patient registration."""
    name = StringField('Full Name', [
        validators.DataRequired(message='Name is required'),
        validators.Length(min=2, max=100, message='Name must be between 2 and 100 characters')
    ])
    email = StringField('Email', [
        validators.DataRequired(message='Email is required'),
        validators.Email(message='Invalid email address')
    ])
    contact = StringField('Contact Number', [
        validators.DataRequired(message='Contact number is required'),
        validators.Length(min=10, max=20, message='Contact must be between 10 and 20 characters')
    ])
    password = PasswordField('Password', [
        validators.DataRequired(message='Password is required'),
        validators.Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', [
        validators.DataRequired(message='Please confirm your password'),
        validators.EqualTo('password', message='Passwords must match')
    ])


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Display login form and handle authentication.
    Accessible to all users (admin, doctor, patient).
    """
    if request.method == 'POST':
        form = LoginForm(request.form)
        
        if form.validate():
            email = form.email.data.strip().lower()
            password = form.password.data
            
            # Find user by email
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                login_user(user)
                flash(f'Welcome back, {user.name}!', 'success')
                
                # Redirect based on role
                if user.role == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user.role == 'doctor':
                    return redirect(url_for('doctor.dashboard'))
                else:  # patient
                    return redirect(url_for('patient.dashboard'))
            else:
                flash('Invalid email or password. Please try again.', 'danger')
        else:
            # Display validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    flash(error, 'danger')
    
    return render_template('auth/login.html')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """
    Display patient registration form and handle new patient creation.
    Only patients can self-register; doctors and admins are created by admin.
    """
    if request.method == 'POST':
        form = RegisterForm(request.form)
        
        if form.validate():
            email = form.email.data.strip().lower()
            
            # Check if email already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('An account with this email already exists. Please login.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Create new patient user
            new_patient = User(
                email=email,
                name=form.name.data.strip(),
                contact=form.contact.data.strip(),
                role='patient'
            )
            new_patient.set_password(form.password.data)
            
            try:
                db.session.add(new_patient)
                db.session.commit()
                flash('Registration successful! Please login with your credentials.', 'success')
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred during registration. Please try again.', 'danger')
        else:
            # Display validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    flash(error, 'danger')
    
    return render_template('auth/register.html')


@auth.route('/logout')
@login_required
def logout():
    """
    Log out the current user and redirect to login page.
    """
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
