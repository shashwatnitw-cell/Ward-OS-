"""
Authentication blueprint for login, logout, and patient registration
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from models import db, User
from utils import validate_email, validate_password, validate_phone, sanitize_input, FlashMessage

# Create blueprint
auth = Blueprint('auth', __name__, url_prefix='/auth')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route
    Handles both GET (display form) and POST (process login)
    """
    # Redirect if already logged in
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif current_user.role == 'patient':
            return redirect(url_for('patient.dashboard'))
    
    if request.method == 'POST':
        email = sanitize_input(request.form.get('email', '').lower())
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'
        
        # Validate input
        if not email or not password:
            FlashMessage.error('Please enter both email and password.')
            return render_template('auth/login.html')
        
        if not validate_email(email):
            FlashMessage.error('Please enter a valid email address.')
            return render_template('auth/login.html')
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember_me)
            FlashMessage.success(f'Welcome back, {user.name}!')
            
            # Redirect to appropriate dashboard
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor.dashboard'))
            elif user.role == 'patient':
                return redirect(url_for('patient.dashboard'))
        else:
            FlashMessage.error('Invalid email or password.')
    
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """
    Patient registration route
    Only allows patient registration (doctors are added by admin)
    """
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('patient.dashboard'))
    
    if request.method == 'POST':
        # Get form data
        name = sanitize_input(request.form.get('name', ''))
        email = sanitize_input(request.form.get('email', '').lower())
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        contact = sanitize_input(request.form.get('contact', ''))
        
        # Validate input
        errors = []
        
        if not name or len(name) < 2:
            errors.append('Name must be at least 2 characters long.')
        
        if not email:
            errors.append('Email is required.')
        elif not validate_email(email):
            errors.append('Please enter a valid email address.')
        else:
            # Check if email already exists
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                errors.append('An account with this email already exists.')
        
        if not password:
            errors.append('Password is required.')
        else:
            is_valid, message = validate_password(password)
            if not is_valid:
                errors.append(message)
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if contact and not validate_phone(contact):
            errors.append('Please enter a valid phone number.')
        
        if errors:
            for error in errors:
                FlashMessage.error(error)
            return render_template('auth/register.html')
        
        try:
            # Create new patient user
            user = User(
                name=name,
                email=email,
                role='patient',
                contact=contact
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            FlashMessage.success('Registration successful! You can now log in.')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            FlashMessage.error('An error occurred during registration. Please try again.')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    """User logout route"""
    user_name = current_user.name
    logout_user()
    FlashMessage.info(f'Goodbye, {user_name}!')
    return redirect(url_for('auth.login'))

@auth.route('/profile')
@login_required
def profile():
    """View user profile"""
    return render_template('auth/profile.html', user=current_user)

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate input
        if not current_password:
            FlashMessage.error('Current password is required.')
            return render_template('auth/change_password.html')
        
        if not current_user.check_password(current_password):
            FlashMessage.error('Current password is incorrect.')
            return render_template('auth/change_password.html')
        
        if not new_password:
            FlashMessage.error('New password is required.')
            return render_template('auth/change_password.html')
        
        is_valid, message = validate_password(new_password)
        if not is_valid:
            FlashMessage.error(message)
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            FlashMessage.error('New passwords do not match.')
            return render_template('auth/change_password.html')
        
        if current_password == new_password:
            FlashMessage.error('New password must be different from current password.')
            return render_template('auth/change_password.html')
        
        try:
            # Update password
            current_user.set_password(new_password)
            db.session.commit()
            
            FlashMessage.success('Password changed successfully!')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            FlashMessage.error('An error occurred while changing password. Please try again.')
    
    return render_template('auth/change_password.html')

# Error handlers for auth blueprint
@auth.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@auth.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return render_template('errors/500.html'), 500