"""Script to create and seed the SQLite DB for HMS.

Run: python create_db.py
This will:
- create hms.db
- add one admin, 2 doctors with availability for next 7 days, 2 patients
- create a couple of appointments
"""
from __future__ import annotations

from datetime import date

from werkzeug.security import generate_password_hash

from app import create_app
from models import db, User, DoctorProfile, DoctorAvailability, Appointment
from utils import next_seven_days


ADMIN_EMAIL = "admin@hms.local"
ADMIN_PASSWORD = "Admin#12345"  # change after first login


def seed():
    # Clear and create tables
    db.drop_all()
    db.create_all()

    # Admin
    admin = User(
        name="System Admin",
        email=ADMIN_EMAIL,
        role="admin",
        password_hash=generate_password_hash(ADMIN_PASSWORD),
    )
    db.session.add(admin)

    # Doctors
    d1 = User(
        name="Dr. Alice Heart",
        email="alice.heart@hms.local",
        role="doctor",
        password_hash=generate_password_hash("ChangeMe123!"),
    )
    d2 = User(
        name="Dr. Bob Bones",
        email="bob.bones@hms.local",
        role="doctor",
        password_hash=generate_password_hash("ChangeMe123!"),
    )
    db.session.add_all([d1, d2])
    db.session.flush()

    p1 = DoctorProfile(doctor_id=d1.id, specialization="Cardiology", phone="+1-555-1000", bio="Heart specialist")
    p2 = DoctorProfile(doctor_id=d2.id, specialization="Orthopedics", phone="+1-555-2000", bio="Bone specialist")
    db.session.add_all([p1, p2])

    # Patients
    u1 = User(
        name="Peter Patient",
        email="peter@hms.local",
        role="patient",
        password_hash=generate_password_hash("Patient#123"),
        contact="+1-555-3000",
    )
    u2 = User(
        name="Paula Patient",
        email="paula@hms.local",
        role="patient",
        password_hash=generate_password_hash("Patient#123"),
        contact="+1-555-4000",
    )
    db.session.add_all([u1, u2])
    db.session.flush()

    # Availability next 7 days at 09:00 and 14:00
    for d in next_seven_days():
        for t in ("09:00", "14:00"):
            db.session.add(DoctorAvailability(doctor_id=d1.id, date=d, time=t))
            db.session.add(DoctorAvailability(doctor_id=d2.id, date=d, time=t))

    db.session.commit()

    # Sample appointments using first day slots
    first_day = next_seven_days()[0]
    ap1 = Appointment(patient_id=u1.id, doctor_id=d1.id, date=first_day, time="09:00", status="Booked")
    ap2 = Appointment(patient_id=u2.id, doctor_id=d2.id, date=first_day, time="14:00", status="Booked")
    db.session.add_all([ap1, ap2])

    # mark corresponding slots as booked
    for ap in (ap1, ap2):
        slot = DoctorAvailability.query.filter_by(
            doctor_id=ap.doctor_id, date=ap.date, time=ap.time
        ).first()
        if slot:
            slot.is_booked = True

    db.session.commit()

    print("Database created and seeded.")
    print("Admin login:")
    print(f"  Email: {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print("Doctor accounts (password ChangeMe123!):")
    print("  alice.heart@hms.local, bob.bones@hms.local")
    print("Patient accounts (password Patient#123):")
    print("  peter@hms.local, paula@hms.local")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed()
