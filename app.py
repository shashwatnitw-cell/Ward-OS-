"""
Main Flask application for the Hospital Management System.
Initializes the app, database, login manager, and registers blueprints.
"""
from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from models import db, User
from config import Config

# Import blueprints
from auth import auth
from admin import admin
from doctor import doctor
from patient import patient


def create_app(config_class=Config):
    """
    Application factory pattern.
    Creates and configures the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login."""
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(doctor)
    app.register_blueprint(patient)
    
    # Root route - redirect to appropriate dashboard based on user role
    @app.route('/')
    def index():
        """
        Root route that redirects users to their role-specific dashboard.
        If not logged in, redirects to login page.
        """
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'doctor':
                return redirect(url_for('doctor.dashboard'))
            elif current_user.role == 'patient':
                return redirect(url_for('patient.dashboard'))
        return redirect(url_for('auth.login'))
    
    # Error handlers
    @app.errorhandler(403)
    def forbidden(e):
        """Handle 403 Forbidden errors."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>403 - Forbidden</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="row justify-content-center">
                    <div class="col-md-6 text-center">
                        <h1 class="display-1">403</h1>
                        <h2>Access Forbidden</h2>
                        <p class="lead">You do not have permission to access this page.</p>
                        <a href="/" class="btn btn-primary">Go to Dashboard</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """, 403
    
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 Not Found errors."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>404 - Not Found</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="row justify-content-center">
                    <div class="col-md-6 text-center">
                        <h1 class="display-1">404</h1>
                        <h2>Page Not Found</h2>
                        <p class="lead">The page you are looking for does not exist.</p>
                        <a href="/" class="btn btn-primary">Go to Dashboard</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """, 404
    
    @app.errorhandler(500)
    def internal_error(e):
        """Handle 500 Internal Server errors."""
        db.session.rollback()
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>500 - Server Error</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="row justify-content-center">
                    <div class="col-md-6 text-center">
                        <h1 class="display-1">500</h1>
                        <h2>Internal Server Error</h2>
                        <p class="lead">Something went wrong on our end. Please try again later.</p>
                        <a href="/" class="btn btn-primary">Go to Dashboard</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """, 500
    
    # Template filters
    @app.template_filter('format_date')
    def format_date_filter(date_obj):
        """Format date for templates."""
        from utils import format_date
        return format_date(date_obj)
    
    @app.template_filter('format_time')
    def format_time_filter(time_str):
        """Format time for templates."""
        from utils import format_time
        return format_time(time_str)
    
    return app


# Create the application instance
app = create_app()


if __name__ == '__main__':
    """
    Run the Flask development server.
    For production, use a WSGI server like Gunicorn.
    """
    app.run(debug=True, host='0.0.0.0', port=5000)
