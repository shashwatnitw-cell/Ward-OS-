# Hospital Management System (HMS)

A comprehensive web-based Hospital Management System built with Flask, providing role-based access for Administrators, Doctors, and Patients.

## 🏥 Features

### Admin Features
- **Dashboard**: System overview with statistics and recent activities
- **Doctor Management**: Add, edit, and manage doctor profiles
- **Patient Management**: View and manage patient accounts
- **Appointment Management**: Monitor all appointments across the system
- **Reports**: Generate system analytics and reports

### Doctor Features
- **Dashboard**: Personal overview with today's appointments and statistics
- **Appointment Management**: View, complete appointments, and add treatment notes
- **Patient History**: Access complete medical history of treated patients
- **Schedule Management**: View weekly schedule and upcoming appointments
- **Availability Management**: Set and update available time slots

### Patient Features
- **Dashboard**: Personal health overview and upcoming appointments
- **Doctor Search**: Find doctors by specialization with availability
- **Appointment Booking**: Book appointments with available time slots
- **Appointment Management**: View, reschedule, or cancel appointments
- **Medical History**: Access complete treatment records and prescriptions

## 🛠 Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, Bootstrap 5 (CSS only - no JavaScript)
- **Authentication**: Flask-Login with role-based access control
- **Forms**: Flask-WTF with CSRF protection
- **Security**: Werkzeug password hashing

## 📋 Requirements

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

## 🚀 Installation & Setup

### 1. Clone or Extract the Project
```bash
# If using git
git clone <repository-url>
cd hms_project

# Or extract the ZIP file and navigate to the directory
cd hms_project
```

### 2. Create Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Database and Seed Data
```bash
python create_db.py
```

This will:
- Create the SQLite database (`hms.db`)
- Create all necessary tables
- Seed the database with sample data including:
  - Admin account
  - Sample doctors with different specializations
  - Sample patients
  - Sample appointments and medical records
  - Doctor availability for the next 7 days

### 5. Run the Application
```bash
python app.py
```

The application will be available at: `http://localhost:5000`

## 🔐 Default Login Credentials

After running `create_db.py`, use these credentials to test the system:

### Administrator
- **Email**: `admin@hms.com`
- **Password**: `admin123`

### Sample Doctor
- **Email**: `sarah.johnson@hms.com`
- **Password**: `doctor123`

### Sample Patient
- **Email**: `john.smith@email.com`
- **Password**: `patient123`

> ⚠️ **Important**: Change these default passwords in a production environment!

## 📊 Database Schema

### Core Tables

#### Users
- `id` (Primary Key)
- `email` (Unique)
- `password_hash`
- `name`
- `role` ('admin', 'doctor', 'patient')
- `contact`
- `created_at`
- `is_active`

#### DoctorProfile
- `id` (Primary Key)
- `doctor_id` (Foreign Key → Users.id)
- `specialization`
- `bio`
- `phone`
- `experience_years`

#### DoctorAvailability
- `id` (Primary Key)
- `doctor_id` (Foreign Key → Users.id)
- `date`
- `time`
- `is_booked`
- Unique constraint: (doctor_id, date, time)

#### Appointments
- `id` (Primary Key)
- `patient_id` (Foreign Key → Users.id)
- `doctor_id` (Foreign Key → Users.id)
- `date`
- `time`
- `status` ('Booked', 'Completed', 'Cancelled')
- `created_at`
- `updated_at`
- Unique constraint: (doctor_id, date, time)

#### Treatment
- `id` (Primary Key)
- `appointment_id` (Foreign Key → Appointments.id)
- `diagnosis`
- `prescription`
- `notes`
- `recorded_by_doctor_id` (Foreign Key → Users.id)
- `recorded_at`

### Entity Relationship Diagram (ASCII)
```
Users (1) ←→ (0..1) DoctorProfile
Users (1) ←→ (0..*) DoctorAvailability
Users (1) ←→ (0..*) Appointments [as patient]
Users (1) ←→ (0..*) Appointments [as doctor]
Appointments (1) ←→ (0..1) Treatment
```

## 🛣 API Routes

### Authentication Routes (`/auth`)
- `GET/POST /auth/login` - User login
- `GET/POST /auth/register` - Patient registration
- `GET /auth/logout` - User logout
- `GET /auth/profile` - View user profile
- `GET/POST /auth/change-password` - Change password

### Admin Routes (`/admin`) - Admin Only
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/doctors` - List all doctors
- `GET/POST /admin/doctors/new` - Add new doctor
- `GET/POST /admin/doctors/<id>/edit` - Edit doctor
- `POST /admin/doctors/<id>/delete` - Deactivate doctor
- `GET /admin/patients` - List all patients
- `GET /admin/patients/<id>` - View patient details
- `GET /admin/appointments` - List all appointments
- `GET /admin/reports` - System reports

### Doctor Routes (`/doctor`) - Doctor Only
- `GET /doctor/dashboard` - Doctor dashboard
- `GET /doctor/appointments` - List doctor's appointments
- `GET /doctor/appointments/<id>` - View appointment details
- `GET/POST /doctor/appointments/<id>/complete` - Complete appointment
- `GET /doctor/patients/<id>/history` - Patient medical history
- `GET/POST /doctor/availability` - Manage availability
- `GET /doctor/schedule` - View weekly schedule
- `GET /doctor/patients` - List doctor's patients

### Patient Routes (`/patient`) - Patient Only
- `GET /patient/dashboard` - Patient dashboard
- `GET /patient/doctors` - Search doctors
- `GET /patient/doctors/<id>` - View doctor profile
- `GET/POST /patient/doctors/<id>/book` - Book appointment
- `GET /patient/appointments` - List patient's appointments
- `GET /patient/appointments/<id>` - View appointment details
- `POST /patient/appointments/<id>/cancel` - Cancel appointment
- `GET/POST /patient/appointments/<id>/reschedule` - Reschedule appointment
- `GET /patient/medical-history` - View medical history

## 🔒 Security Features

1. **Password Security**: Werkzeug password hashing
2. **Session Management**: Flask-Login with secure sessions
3. **CSRF Protection**: Flask-WTF CSRF tokens
4. **Role-Based Access**: Decorators enforce role permissions
5. **Input Validation**: Server-side validation for all forms
6. **SQL Injection Prevention**: SQLAlchemy ORM parameterized queries

## 🧪 Testing the Application

### Manual Testing Checklist

1. **Admin Functions**:
   - [ ] Login as admin
   - [ ] Add a new doctor with specialization
   - [ ] Edit doctor information
   - [ ] View all patients and appointments
   - [ ] Generate reports

2. **Doctor Functions**:
   - [ ] Login as doctor
   - [ ] View today's appointments
   - [ ] Complete an appointment with diagnosis/prescription
   - [ ] Manage availability for next 7 days
   - [ ] View patient medical history

3. **Patient Functions**:
   - [ ] Register new patient account
   - [ ] Search doctors by specialization
   - [ ] Book an available appointment slot
   - [ ] View appointment details
   - [ ] Reschedule/cancel appointment
   - [ ] View medical history

4. **Double-Booking Prevention**:
   - [ ] Try booking the same time slot with different patients
   - [ ] Verify error message and alternative suggestions

## 🐛 Troubleshooting

### Common Issues

1. **Database not found error**:
   ```bash
   python create_db.py
   ```

2. **Import errors**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Permission denied errors**:
   - Ensure virtual environment is activated
   - Check file permissions

4. **Port already in use**:
   - Change port in `app.py` or kill existing process

### Development Mode

To run in development mode with debug enabled:
```bash
export FLASK_ENV=development  # On Windows: set FLASK_ENV=development
python app.py
```

## 📁 Project Structure

```
hms_project/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── create_db.py          # Database creation and seeding script
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── models.py            # SQLAlchemy models
├── auth.py              # Authentication blueprint
├── admin.py             # Admin blueprint
├── doctor.py            # Doctor blueprint
├── patient.py           # Patient blueprint
├── utils.py             # Utility functions and decorators
├── templates/           # Jinja2 templates
│   ├── base.html
│   ├── auth/
│   ├── admin/
│   ├── doctor/
│   ├── patient/
│   └── errors/
└── static/
    └── css/
        └── styles.css   # Custom CSS styles
```

## 🎨 UI/UX Features

- **Responsive Design**: Bootstrap 5 grid system
- **Modern Interface**: Clean, professional medical theme
- **Role-based Navigation**: Different navigation for each user role
- **Flash Messages**: User feedback for all actions
- **Form Validation**: Client and server-side validation
- **Accessibility**: Semantic HTML and ARIA labels
- **No JavaScript**: Pure server-side rendering

## 📈 Future Enhancements

- Email notifications for appointments
- SMS reminders
- Prescription management
- Billing and insurance
- Medical imaging integration
- Telemedicine features
- Mobile app
- Advanced reporting and analytics

## 📄 License

This project is created for educational purposes. Please ensure compliance with healthcare regulations (HIPAA, etc.) before using in production.

## 👥 Support

For issues or questions:
1. Check this README for common solutions
2. Review the code comments and docstrings
3. Test with the provided sample data
4. Verify all dependencies are installed correctly

---

**Note**: This is a demonstration system. For production use, implement additional security measures, data encryption, audit logging, and compliance with healthcare regulations.