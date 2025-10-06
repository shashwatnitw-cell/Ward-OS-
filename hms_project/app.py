"""
Hospital Management System - Main Flask Application
"""
import os
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, current_user
from models import db, User
from config import config

# Import blueprints
from auth import auth
from admin import admin
from doctor import doctor
from patient import patient

def create_app(config_name=None):
    """
    Application factory pattern for creating Flask app
    
    Args:
        config_name: Configuration to use ('development', 'production', or None for default)
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app.config.from_object(config.get(config_name, config['default']))
    
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
        """Load user for Flask-Login"""
        return User.query.get(int(user_id))
    
    # Register blueprints
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(doctor)
    app.register_blueprint(patient)
    
    # Main routes
    @app.route('/')
    def index():
        """
        Main landing page - redirect to appropriate dashboard based on user role
        """
        if current_user.is_authenticated:
            if current_user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif current_user.role == 'doctor':
                return redirect(url_for('doctor.dashboard'))
            elif current_user.role == 'patient':
                return redirect(url_for('patient.dashboard'))
        
        return redirect(url_for('auth.login'))
    
    @app.route('/about')
    def about():
        """About page with system information"""
        return render_template('about.html')
    
    @app.route('/contact')
    def contact():
        """Contact page"""
        return render_template('contact.html')
    
    # Error handlers
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors"""
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors"""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handle 500 Internal Server errors"""
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    # Context processors
    @app.context_processor
    def inject_user():
        """Make current_user available in all templates"""
        return {'current_user': current_user}
    
    @app.context_processor
    def utility_processor():
        """Inject utility functions into templates"""
        from utils import format_date, format_time, get_user_display_name, get_appointment_status_class
        
        return {
            'format_date': format_date,
            'format_time': format_time,
            'get_user_display_name': get_user_display_name,
            'get_appointment_status_class': get_appointment_status_class
        }
    
    # CLI commands
    @app.cli.command()
    def init_db():
        """Initialize the database"""
        db.create_all()
        print('Database initialized!')
    
    @app.cli.command()
    def seed_db():
        """Seed the database with sample data"""
        from create_db import main as seed_main
        seed_main()
    
    return app

def main():
    """
    Main function to run the application in development mode
    """
    app = create_app()
    
    # Check if database exists, if not, create it
    if not os.path.exists('hms.db'):
        print("Database not found. Please run 'python create_db.py' first to set up the database.")
        return
    
    # Run the application
    print("Starting Hospital Management System...")
    print("Open your browser and go to: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )

if __name__ == '__main__':
    main()