# Project Report Template — Hospital Management System (HMS)

Student Details
- Name:
- Email:
- Institution:
- Date:

Project Overview
- Title: Hospital Management System (Flask, No JavaScript)
- Objective: Implement Admin, Doctor, Patient roles with secure booking workflow
- Scope: Auth, role dashboards, availability, booking, treatment records

AI Use Disclosure
- Tools used: GPT-based assistant for scaffolding and code generation
- What it produced: initial project structure, models, routes, templates, docs
- What I edited/validated: configuration, forms validation, seed data, README

Frameworks & Libraries
- Flask, Jinja2
- Flask-SQLAlchemy (SQLite)
- Flask-Login
- Flask-WTF/WTForms

ER Diagram (ASCII)
```
users (id PK) --1:1--> doctor_profiles (doctor_id PK/FK)
     |                    |
     |                    +--1:N-- doctor_availability (id PK, doctor_id FK, date, time, is_booked)
     |
     +--1:N-- appointments (id PK, patient_id FK -> users.id, doctor_id FK -> users.id,
                            date, time, status, diagnosis, prescription, notes,
                            recorded_by_doctor_id FK -> users.id)
```

Routes Summary
- Auth: /login, /register, /logout
- Admin: /admin/dashboard, /admin/doctors (+new/edit/delete), /admin/appointments, /admin/patients, /admin/patients/<id>
- Doctor: /doctor/dashboard, /doctor/appointments/<id>, /doctor/appointments/<id>/complete, /doctor/availability
- Patient: /patient/dashboard, /patient/doctors, /patient/doctors/<doctor_id>/book, /patient/appointments/<id>, /patient/appointments/<id>/cancel, /patient/appointments/<id>/reschedule
- API: /api/doctors (GET)

Build & Run
- Create venv, `pip install -r requirements.txt`
- `python create_db.py` to create/seed DB
- `flask run` to start the app

Video Link
- URL:
