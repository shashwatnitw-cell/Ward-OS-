"""
Utility functions and decorators for the Hospital Management System
"""
from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user
from datetime import datetime, date, time, timedelta
import re

def login_required_role(roles):
    """
    Decorator to require login and specific role(s)
    
    Args:
        roles: string or list of strings representing allowed roles
    """
    if isinstance(roles, str):
        roles = [roles]
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if current_user.role not in roles:
                abort(403)  # Forbidden
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to require admin role"""
    return login_required_role('admin')(f)

def doctor_required(f):
    """Decorator to require doctor role"""
    return login_required_role('doctor')(f)

def patient_required(f):
    """Decorator to require patient role"""
    return login_required_role('patient')(f)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """
    Validate password strength
    
    Requirements:
    - At least 6 characters long
    - Contains at least one letter and one number
    """
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, "Password is valid"

def validate_phone(phone):
    """Validate phone number format"""
    if not phone:
        return True  # Phone is optional
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's 10 digits (US format) or 11 digits (with country code)
    return len(digits_only) in [10, 11]

def format_date(date_obj):
    """Format date for display"""
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d').date()
        except ValueError:
            return date_obj
    
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    if isinstance(date_obj, date):
        return date_obj.strftime('%B %d, %Y')
    
    return str(date_obj)

def format_time(time_obj):
    """Format time for display"""
    if isinstance(time_obj, str):
        try:
            time_obj = datetime.strptime(time_obj, '%H:%M:%S').time()
        except ValueError:
            try:
                time_obj = datetime.strptime(time_obj, '%H:%M').time()
            except ValueError:
                return time_obj
    
    if isinstance(time_obj, datetime):
        time_obj = time_obj.time()
    
    if isinstance(time_obj, time):
        return time_obj.strftime('%I:%M %p')
    
    return str(time_obj)

def get_next_7_days():
    """Get list of next 7 days starting from today"""
    today = date.today()
    return [today + timedelta(days=i) for i in range(7)]

def get_time_slots():
    """Get standard appointment time slots"""
    slots = []
    # Generate slots from 9 AM to 5 PM, every hour
    for hour in range(9, 17):
        slots.append(time(hour, 0))
        slots.append(time(hour, 30))
    return slots

def parse_date(date_string):
    """Parse date string in various formats"""
    if not date_string:
        return None
    
    formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt).date()
        except ValueError:
            continue
    
    raise ValueError(f"Invalid date format: {date_string}")

def parse_time(time_string):
    """Parse time string in various formats"""
    if not time_string:
        return None
    
    formats = ['%H:%M:%S', '%H:%M', '%I:%M %p', '%I:%M%p']
    
    for fmt in formats:
        try:
            return datetime.strptime(time_string, fmt).time()
        except ValueError:
            continue
    
    raise ValueError(f"Invalid time format: {time_string}")

def is_business_day(date_obj):
    """Check if date is a business day (Monday-Friday)"""
    return date_obj.weekday() < 5

def is_business_hours(time_obj):
    """Check if time is within business hours (9 AM - 5 PM)"""
    return time(9, 0) <= time_obj <= time(17, 0)

def get_available_specializations():
    """Get list of available medical specializations"""
    return [
        'General Medicine',
        'Cardiology',
        'Dermatology',
        'Endocrinology',
        'Gastroenterology',
        'Neurology',
        'Oncology',
        'Orthopedics',
        'Pediatrics',
        'Psychiatry',
        'Radiology',
        'Surgery',
        'Urology'
    ]

def sanitize_input(text):
    """Basic input sanitization"""
    if not text:
        return ''
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Replace multiple spaces with single space
    text = re.sub(r'\s+', ' ', text)
    
    return text

def generate_appointment_reference():
    """Generate unique appointment reference number"""
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"APT{timestamp}"

class FlashMessage:
    """Helper class for consistent flash messages"""
    
    @staticmethod
    def success(message):
        flash(message, 'success')
    
    @staticmethod
    def error(message):
        flash(message, 'danger')
    
    @staticmethod
    def warning(message):
        flash(message, 'warning')
    
    @staticmethod
    def info(message):
        flash(message, 'info')

def paginate_query(query, page, per_page=10):
    """
    Paginate a SQLAlchemy query
    
    Args:
        query: SQLAlchemy query object
        page: Current page number
        per_page: Items per page
    
    Returns:
        Pagination object
    """
    return query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

def get_user_display_name(user):
    """Get display name for user"""
    if user.role == 'doctor' and hasattr(user, 'doctor_profile') and user.doctor_profile:
        return f"Dr. {user.name}"
    return user.name

def calculate_age(birth_date):
    """Calculate age from birth date"""
    if not birth_date:
        return None
    
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def format_phone_display(phone):
    """Format phone number for display"""
    if not phone:
        return ''
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11:
        return f"+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    
    return phone

def get_appointment_status_class(status):
    """Get CSS class for appointment status"""
    status_classes = {
        'Booked': 'badge bg-primary',
        'Completed': 'badge bg-success',
        'Cancelled': 'badge bg-danger'
    }
    return status_classes.get(status, 'badge bg-secondary')

def is_valid_future_date(date_obj):
    """Check if date is in the future (or today)"""
    if isinstance(date_obj, str):
        try:
            date_obj = parse_date(date_obj)
        except ValueError:
            return False
    
    return date_obj >= date.today()

def get_error_message(form):
    """Extract first error message from WTForm"""
    for field, errors in form.errors.items():
        if errors:
            return f"{field}: {errors[0]}"
    return "Please check your input and try again."