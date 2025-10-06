# Hospital Management System (Flask, No JavaScript)

A complete, runnable Hospital Management System (HMS) built with Flask, Jinja2, Bootstrap CSS only (no JS), and SQLite. Supports three roles: Admin, Doctor, and Patient.

## Quickstart

1. Create and activate a virtual environment
   - Linux/macOS
     ```bash
     python3 -m venv .venv && source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```bash
     py -3 -m venv .venv; .\.venv\Scripts\Activate.ps1
     ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
3. Create and seed the SQLite database
   ```bash
   python create_db.py
   ```
4. Run the development server
   ```bash
   export FLASK_APP=app.py
   flask run
   ```
   Windows (PowerShell):
   ```powershell
   $env:FLASK_APP="app.py"; flask run
   ```

Visit http://127.0.0.1:5000

## Seeded Accounts

- Admin: `admin@hms.local` / `Admin@12345` (please change after first login)
- Doctors: `alice.hart@hms.local` / `Doctor@12345`, `brian.cole@hms.local` / `Doctor@12345`
- Patients: `john.doe@hms.local` / `Patient@12345`, `jane.smith@hms.local` / `Patient@12345`

## Features

- Admin
  - Dashboard with counts
  - Manage doctors (create, edit, delete, search)
  - View all appointments and patients
- Doctor
  - Dashboard with today/upcoming appointments
  - Complete appointments with diagnosis & prescription
  - Manage availability for the next 7 days
- Patient
  - Registration & login
  - Search doctors by specialization
  - Book, cancel, and reschedule appointments
  - View appointment details and history

## ER Diagram (ASCII)

```
User (id, email, password_hash, name, role, contact, created_at)
 1 ── 1 DoctorProfile (id->users.id, specialization, bio, phone)
 1 ── * DoctorAvailability (id, doctor_id->doctor_profiles.id, date, time, is_booked)
User 1 ── * Appointment (* patient_id)
User 1 ── * Appointment (* doctor_id)
Appointment (id, patient_id, doctor_id, date, time, status, created_at, updated_at,
             diagnosis, prescription, notes, recorded_by_doctor_id, recorded_at)
```

- Unique slot per doctor enforced in `DoctorAvailability (doctor_id, date, time)`
- Double-booking prevented server-side before creating/rescheduling appointments

## Routes Overview

- Auth: `/login` (GET/POST), `/register` (GET/POST), `/logout`
- Admin: `/admin/dashboard`, `/admin/doctors`, `/admin/doctors/new` (GET/POST),
  `/admin/doctors/<id>/edit` (GET/POST), `/admin/doctors/<id>/delete` (POST),
  `/admin/appointments`, `/admin/patients`, `/admin/patients/<id>`
- Doctor: `/doctor/dashboard`, `/doctor/appointments/<appointment_id>`,
  `/doctor/appointments/<appointment_id>/complete` (POST),
  `/doctor/patient/<patient_id>/history`, `/doctor/availability` (GET/POST)
- Patient: `/patient/dashboard`, `/patient/doctors`,
  `/patient/doctors/<doctor_id>/book`, `/patient/book` (POST),
  `/patient/appointments/<id>`, `/patient/appointments/<id>/cancel` (POST),
  `/patient/appointments/<id>/reschedule` (POST)
- Optional API: `/patient/api/doctors` returns JSON list of doctors

## Notes & Assumptions

- Time granularity is 60-minute slots (`HH:MM`).
- CSRF protection via Flask-WTF. All POST forms include CSRF token.
- No JavaScript is used; all interactions are standard form submissions.
- SQLite database file is created at `hms.db` in project root.

## Testing Checklist

- Run `python create_db.py`
- Login as Admin; view dashboard and doctors list; add/edit/delete a doctor
- Register a new patient; login; search by specialization; book a slot
- Attempt to book the same slot with another account — should fail
- Login as Doctor; view today's appointments; open one and mark Completed
- Reschedule and cancellation flows from Patient dashboard

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
├─ templates/
│  ├─ base.html
│  ├─ auth/
│  │  ├─ login.html
│  │  ├─ register.html
│  ├─ admin/
│  │  ├─ dashboard.html
│  │  ├─ doctors_list.html
│  ├─ doctor/
│  │  ├─ dashboard.html
│  │  ├─ appointment_detail.html
│  ├─ patient/
│  │  ├─ dashboard.html
│  │  ├─ search_doctors.html
│  │  ├─ book_appointment.html
├─ static/
│  ├─ css/
│  │  └─ styles.css
└─ utils.py
```

If you cannot view the ER image, the ASCII above reflects the schema.
