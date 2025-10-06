# Hospital Management System (HMS)

A comprehensive web-based Hospital Management System built with Flask, featuring role-based access control for Admins, Doctors, and Patients.

## 🏥 Features

### Admin Features
- Dashboard with system statistics
- CRUD operations for doctors
- View and manage all patients
- View all appointments with filtering
- Search functionality for doctors and patients

### Doctor Features
- Personal dashboard with appointment overview
- View today's and upcoming appointments
- Mark appointments as completed with treatment details
- View patient medical history
- Manage availability for the next 7 days

### Patient Features
- Search doctors by specialization
- Book appointments with available time slots
- Reschedule existing appointments
- Cancel appointments
- View appointment history and treatment details

## 🛠️ Tech Stack

- **Backend**: Flask 2.3.3 (Python)
- **Database**: SQLite (programmatically created)
- **ORM**: SQLAlchemy
- **Authentication**: Flask-Login
- **Forms**: WTForms with CSRF protection
- **Frontend**: HTML5, CSS3, Bootstrap 5 (CSS only, **NO JavaScript**)
- **Password Security**: Werkzeug password hashing

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## 🚀 Installation & Setup

### 1. Clone or Extract the Project

```bash
cd hms_project
```

### 2. Create Virtual Environment

**On Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Database

Run the database creation script to programmatically create the SQLite database and seed it with sample data:

```bash
python create_db.py
```

This will:
- Create `hms.db` SQLite database
- Create all necessary tables
- Seed the database with sample admin, doctors, patients, and appointments
- Display all default login credentials

### 5. Run the Application

```bash
python app.py
```

Or use Flask's built-in command:

```bash
flask run
```

The application will be available at: **http://localhost:5000**

## 🔐 Default Login Credentials

### Admin Account
- **Email**: `admin@hospital.com`
- **Password**: `admin123`
- ⚠️ **WARNING**: Change this password immediately in production!

### Doctor Accounts

**Doctor 1 - Dr. Sarah Johnson (Cardiology)**
- **Email**: `sarah.johnson@hospital.com`
- **Password**: `doctor123`

**Doctor 2 - Dr. Michael Chen (Neurology)**
- **Email**: `michael.chen@hospital.com`
- **Password**: `doctor123`

### Patient Accounts

**Patient 1 - John Smith**
- **Email**: `john.smith@email.com`
- **Password**: `patient123`

**Patient 2 - Emma Wilson**
- **Email**: `emma.wilson@email.com`
- **Password**: `patient123`

## 📂 Project Structure

```
hms_project/
├── app.py                      # Flask application factory
├── config.py                   # Configuration settings
├── create_db.py                # Database creation & seeding script
├── models.py                   # SQLAlchemy database models
├── utils.py                    # Helper functions & decorators
├── auth.py                     # Authentication blueprint
├── admin.py                    # Admin blueprint
├── doctor.py                   # Doctor blueprint
├── patient.py                  # Patient blueprint
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── project_report_template.md  # Project report template
├── hms.db                      # SQLite database (created by create_db.py)
├── templates/
│   ├── base.html              # Base template
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── admin/
│   │   ├── dashboard.html
│   │   ├── doctors_list.html
│   │   ├── doctor_form.html
│   │   ├── patients_list.html
│   │   ├── patient_detail.html
│   │   └── appointments_list.html
│   ├── doctor/
│   │   ├── dashboard.html
│   │   ├── appointment_detail.html
│   │   ├── complete_appointment.html
│   │   ├── patient_history.html
│   │   ├── availability.html
│   │   └── appointments_list.html
│   └── patient/
│       ├── dashboard.html
│       ├── search_doctors.html
│       ├── book_appointment.html
│       ├── appointment_detail.html
│       └── reschedule_appointment.html
└── static/
    └── css/
        └── styles.css         # Custom CSS styles
```

## 📊 Database Schema (ER Diagram)

### Tables and Relationships

```
┌─────────────────────┐
│       Users         │
├─────────────────────┤
│ id (PK)             │
│ email (UNIQUE)      │
│ password_hash       │
│ name                │
│ role                │
│ contact             │
│ created_at          │
└──────────┬──────────┘
           │
           │ 1:1
           │
┌──────────▼──────────┐
│  DoctorProfile      │
├─────────────────────┤
│ id (PK)             │
│ doctor_id (FK)      │
│ specialization      │
│ bio                 │
│ phone               │
└──────────┬──────────┘
           │
           │ 1:N
           │
┌──────────▼──────────┐
│ DoctorAvailability  │
├─────────────────────┤
│ id (PK)             │
│ doctor_id (FK)      │
│ date                │
│ time                │
│ is_booked           │
└─────────────────────┘

┌─────────────────────┐
│   Appointments      │
├─────────────────────┤
│ id (PK)             │
│ patient_id (FK)     │────┐
│ doctor_id (FK)      │────┤
│ date                │    │
│ time                │    │
│ status              │    │
│ diagnosis           │    │
│ prescription        │    │
│ notes               │    │
│ created_at          │    │
│ updated_at          │    │
└─────────────────────┘    │
                           │
                           │ N:1
                           │
              ┌────────────▼──────────┐
              │   (to Users table)    │
              └───────────────────────┘
```

### Key Relationships
- **Users** ↔ **DoctorProfile**: One-to-one (only for users with role='doctor')
- **DoctorProfile** ↔ **DoctorAvailability**: One-to-many
- **Users** ↔ **Appointments**: One-to-many (both as patient and doctor)

### Constraints
- **Unique Email**: Each user must have a unique email address
- **Appointment Conflict Prevention**: Index on (doctor_id, date, time, status) prevents double booking
- **Cascade Deletion**: Deleting a doctor also deletes their profile and availability

## 🔗 Routes & Endpoints

### Public Routes
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/login` | Display login form |
| POST | `/login` | Authenticate user |
| GET | `/register` | Display patient registration form |
| POST | `/register` | Create new patient account |
| GET | `/logout` | Logout current user |

### Admin Routes (Protected: admin-only)
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/admin/dashboard` | Admin dashboard with statistics |
| GET | `/admin/doctors` | List all doctors with search |
| GET | `/admin/doctors/new` | Display add doctor form |
| POST | `/admin/doctors/new` | Create new doctor |
| GET | `/admin/doctors/<id>/edit` | Display edit doctor form |
| POST | `/admin/doctors/<id>/edit` | Update doctor |
| POST | `/admin/doctors/<id>/delete` | Delete doctor |
| GET | `/admin/patients` | List all patients with search |
| GET | `/admin/patients/<id>` | View patient details & history |
| GET | `/admin/appointments` | List all appointments with filters |

### Doctor Routes (Protected: doctor-only)
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/doctor/dashboard` | Doctor dashboard |
| GET | `/doctor/appointments/<id>` | View appointment details |
| GET | `/doctor/appointments/<id>/complete` | Display treatment form |
| POST | `/doctor/appointments/<id>/complete` | Mark appointment complete |
| GET | `/doctor/patient/<id>/history` | View patient history |
| GET | `/doctor/availability` | Manage availability |
| POST | `/doctor/availability` | Add new time slot |
| GET | `/doctor/appointments` | List all doctor's appointments |

### Patient Routes (Protected: patient-only)
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/patient/dashboard` | Patient dashboard |
| GET | `/patient/doctors` | Search doctors by specialization |
| GET | `/patient/doctors/<id>/book` | Display booking form |
| POST | `/patient/book` | Create appointment |
| POST | `/patient/appointments/<id>/cancel` | Cancel appointment |
| GET | `/patient/appointments/<id>/reschedule` | Display reschedule form |
| POST | `/patient/appointments/<id>/reschedule` | Reschedule appointment |
| GET | `/patient/appointments/<id>` | View appointment details |

## ✅ Manual Test Plan

### Test 1: Database Creation
1. Run `python create_db.py`
2. Verify `hms.db` file is created
3. Confirm seeded credentials are printed

### Test 2: Admin Functionality
1. Login as admin (`admin@hospital.com` / `admin123`)
2. View dashboard - verify statistics are displayed
3. Add a new doctor with specialization
4. Search for doctor by name
5. Edit doctor information
6. View all appointments and apply filters
7. View patient details and history

### Test 3: Doctor Functionality
1. Login as doctor (`sarah.johnson@hospital.com` / `doctor123`)
2. View today's appointments
3. Click on an appointment to view details
4. Mark a booked appointment as completed
5. Fill in diagnosis, prescription, and notes
6. View patient history
7. Add new availability slot for tomorrow

### Test 4: Patient Functionality
1. Register a new patient account
2. Login as new patient
3. Search doctors by specialization (e.g., "Cardiology")
4. Book an appointment with an available doctor
5. View appointment on dashboard
6. Reschedule the appointment to a different time
7. Cancel the appointment

### Test 5: Double-Booking Prevention
1. Login as Patient 1 and book a slot (e.g., tomorrow at 10:00 AM with Dr. Johnson)
2. Logout and login as Patient 2
3. Attempt to book the same slot (tomorrow at 10:00 AM with Dr. Johnson)
4. Verify error message is displayed and booking fails

### Test 6: Role-Based Access Control
1. Login as patient
2. Manually try to access `/admin/dashboard`
3. Verify 403 Forbidden error is shown
4. Try accessing `/doctor/dashboard`
5. Verify 403 Forbidden error is shown

## 🐛 Troubleshooting

### Database Already Exists Error
If you see "Database already exists" when running `create_db.py`:
- Type `yes` to overwrite the existing database, or
- Manually delete `hms.db` file and run the script again

### Port Already in Use
If port 5000 is already in use:
```bash
flask run --port 5001
```

### Import Errors
Make sure the virtual environment is activated and all dependencies are installed:
```bash
pip install -r requirements.txt
```

## 🔒 Security Features

- **Password Hashing**: All passwords are hashed using Werkzeug's secure hashing
- **CSRF Protection**: All forms include CSRF tokens via Flask-WTF
- **Role-Based Access**: Decorators enforce role-based route protection
- **Session Security**: HTTP-only cookies with same-site protection
- **Input Validation**: Server-side validation for all form inputs

## 📝 Notes

- **No JavaScript**: The entire application is built without any JavaScript, using only server-side rendering and HTML5 form features
- **Bootstrap CSS Only**: Uses Bootstrap 5 CSS for styling, without Bootstrap JavaScript components
- **Responsive Design**: Mobile-friendly interface using Bootstrap's grid system
- **Database**: SQLite is used for simplicity; for production, migrate to PostgreSQL or MySQL

## 🎯 Future Enhancements

- Email notifications for appointments
- PDF report generation for prescriptions
- Multi-file medical record uploads
- Appointment reminders
- Advanced search with filters
- Analytics and reporting dashboard
- Export data to CSV/Excel

## 📄 License

This project is created for educational purposes.

## 👨‍💻 Developer Notes

- Follow PEP 8 style guidelines
- Use descriptive commit messages
- Test all features before deployment
- Keep dependencies minimal and updated
- Document any changes to the database schema

---

**Built with ❤️ using Flask and Python**
