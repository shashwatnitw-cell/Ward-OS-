# Hospital Management System (HMS) — Flask (No JavaScript)

A full Flask web application implementing an HMS with three roles: Admin, Doctor, and Patient. The UI is server-rendered with Jinja2, HTML, CSS, and Bootstrap (CSS only). No JavaScript is used anywhere.

## Features
- Authentication (login/logout) and patient registration
- Role-based access (admin/doctor/patient)
- Admin: dashboard stats, manage doctors (create/edit/delete with initial availability), view patients, view appointments
- Doctor: dashboard for today's and upcoming appointments, mark appointment Completed with diagnosis/prescription/notes, manage availability for the next 7 days
- Patient: dashboard, search doctors by specialization, book/reschedule/cancel appointments, view appointment details and completed treatment
- Server-side enforcement against double booking
- Minimal JSON API: `GET /api/doctors` returns doctors list

## Tech Stack
- Flask, Jinja2
- Flask-SQLAlchemy, SQLite
- Flask-Login
- Flask-WTF/WTForms for CSRF-secure forms
- Bootstrap 5 CSS for styling (no JS)

## Project Structure
```
hms_project/
├─ app.py
├─ config.py
├─ create_db.py
├─ requirements.txt
├─ README.md
├─ models.py
├─ auth.py
├─ admin.py
├─ doctor.py
├─ patient.py
├─ utils.py
├─ templates/
│  ├─ base.html
│  ├─ auth/
│  │  ├─ login.html
│  │  ├─ register.html
│  ├─ admin/
│  │  ├─ dashboard.html
│  │  ├─ doctors_list.html
│  │  ├─ doctor_form.html
│  │  ├─ appointments.html
│  │  ├─ patients.html
│  │  ├─ patient_detail.html
│  ├─ doctor/
│  │  ├─ dashboard.html
│  │  ├─ appointment_detail.html
│  │  ├─ availability.html
│  ├─ patient/
│  │  ├─ dashboard.html
│  │  ├─ search_doctors.html
│  │  ├─ book_appointment.html
│  │  ├─ appointment_detail.html
├─ static/
│  └─ css/
│     └─ styles.css
```

## Setup & Run (Linux/Windows)
1. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```
2. Install dependencies
```bash
pip install -r requirements.txt
```
3. Create the database and seed data
```bash
python create_db.py
```
4. Run the development server
```bash
export FLASK_APP=app:create_app
flask run  # Windows PowerShell: $env:FLASK_APP="app:create_app"; flask run
```

## Seeded Accounts
- Admin: `admin@hms.local` / `Admin#12345` (CHANGE AFTER FIRST LOGIN)
- Doctors (password `ChangeMe123!`): `alice.heart@hms.local`, `bob.bones@hms.local`
- Patients (password `Patient#123`): `peter@hms.local`, `paula@hms.local`

## ER Diagram (ASCII)
```
users (id PK) --1:1--> doctor_profiles (doctor_id PK/FK)
     |                    |
     |                    +--1:N-- doctor_availability (id PK, doctor_id FK, date, time, is_booked, UNIQUE(doctor_id,date,time))
     |
     +--1:N-- appointments (id PK, patient_id FK -> users.id, doctor_id FK -> users.id,
                            date, time, status, diagnosis, prescription, notes,
                            recorded_by_doctor_id FK -> users.id)
```

## Business Rules
- Unique booking per `(doctor_id, date, time)` for active appointments (Booked/Completed)
- Booking pulls from `doctor_availability` slots not marked booked; upon booking, the slot is marked `is_booked=True`
- Rescheduling frees the old slot and books the new one

## Routes
- Auth
  - GET/POST `/login`
  - GET/POST `/register` (patient)
  - GET `/logout`
- Admin (admin-only)
  - GET `/admin/dashboard`
  - GET `/admin/doctors`, GET/POST `/admin/doctors/new`, GET/POST `/admin/doctors/<id>/edit`, POST `/admin/doctors/<id>/delete`
  - GET `/admin/appointments`
  - GET `/admin/patients`, GET `/admin/patients/<id>`
- Doctor (doctor-only)
  - GET `/doctor/dashboard`
  - GET `/doctor/appointments/<appointment_id>`, POST `/doctor/appointments/<appointment_id>/complete`
  - GET/POST `/doctor/availability`
- Patient (patient-only)
  - GET `/patient/dashboard`
  - GET `/patient/doctors`, GET/POST `/patient/doctors/<doctor_id>/book`, GET `/patient/appointments/<id>`
  - POST `/patient/appointments/<id>/cancel`, POST `/patient/appointments/<id>/reschedule`
- API
  - GET `/api/doctors`

## Testing Checklist
- Run `python create_db.py` then `flask run`
- Login as Admin
  - View dashboard counts
  - Create a new Doctor with initial availability
  - Edit a Doctor and see the change
  - View Patients and a Patient's detail page
  - View Appointments and filter by status
- As Patient
  - Register a new account and login
  - Search doctors by specialization
  - Book an available slot; verify it appears on dashboard
  - Attempt to book the same slot from another patient — expect failure message
  - Cancel the appointment — slot becomes available again
  - Reschedule to a different slot — verify changes
- As Doctor
  - Login and view today's appointments
  - Open an appointment and complete it with diagnosis/prescription
  - Update availability for next 7 days

## Assumptions
- Time slots are 15-minute granularity; admin/doctor forms accept any `HH:MM` where minutes ∈ {00,15,30,45}
- Availability management writes a uniform set of times across the next 7 days for simplicity

## Notes
- No JavaScript is included anywhere. All flows are server-rendered with redirects.
- SQLite file is created at `hms.db` by default; set `DATABASE_URL` to override.
