"""Create and seed the SQLite database for the HMS app.

Run:
  python create_db.py

This will create hms.db in the project folder, create all tables, and seed:
- 1 admin user (email: admin@hms.local / password: Admin@12345)
- 2 doctors with profiles and availability for the next 7 days
- 2 patients
- Sample appointments
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

from app import create_app
from models import db, User, DoctorProfile, DoctorAvailability, Appointment


ADMIN_EMAIL = "admin@hms.local"
ADMIN_PASSWORD = "Admin@12345"  # Change after first login


def ensure_availability_for_week(profile_id: int, start: date, timeslots=None):
    if timeslots is None:
        timeslots = ["09:00", "10:00", "11:00", "14:00", "15:00"]
    for i in range(7):
        d = start + timedelta(days=i)
        for t in timeslots:
            slot = DoctorAvailability(doctor_id=profile_id, date=d, time=t)
            try:
                db.session.add(slot)
                db.session.flush()
            except Exception:
                db.session.rollback()
                # slot exists; ignore
                continue


def main():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Admin
        admin = User(
            name="Administrator",
            email=ADMIN_EMAIL,
            role="admin",
            contact="",
            password_hash=generate_password_hash(ADMIN_PASSWORD),
        )
        db.session.add(admin)
        db.session.flush()

        # Doctors
        doc1 = User(
            name="Dr. Alice Hart",
            email="alice.hart@hms.local",
            role="doctor",
            contact="+1000000001",
            password_hash=generate_password_hash("Doctor@12345"),
        )
        doc2 = User(
            name="Dr. Brian Cole",
            email="brian.cole@hms.local",
            role="doctor",
            contact="+1000000002",
            password_hash=generate_password_hash("Doctor@12345"),
        )
        db.session.add_all([doc1, doc2])
        db.session.flush()

        prof1 = DoctorProfile(id=doc1.id, specialization="Cardiology", bio="Heart specialist")
        prof2 = DoctorProfile(id=doc2.id, specialization="Dermatology", bio="Skin specialist")
        db.session.add_all([prof1, prof2])
        db.session.flush()

        today = date.today()
        ensure_availability_for_week(prof1.id, today)
        ensure_availability_for_week(prof2.id, today)

        # Patients
        pat1 = User(
            name="John Doe",
            email="john.doe@hms.local",
            role="patient",
            contact="+2000000001",
            password_hash=generate_password_hash("Patient@12345"),
        )
        pat2 = User(
            name="Jane Smith",
            email="jane.smith@hms.local",
            role="patient",
            contact="+2000000002",
            password_hash=generate_password_hash("Patient@12345"),
        )
        db.session.add_all([pat1, pat2])
        db.session.flush()

        # Sample appointment: first slot for doc1
        first_slot = (
            DoctorAvailability.query.filter_by(doctor_id=prof1.id, is_booked=False)
            .order_by(DoctorAvailability.date.asc(), DoctorAvailability.time.asc())
            .first()
        )
        if first_slot:
            first_slot.is_booked = True
            appt = Appointment(
                patient_id=pat1.id,
                doctor_id=doc1.id,
                date=first_slot.date,
                time=first_slot.time,
                status="Booked",
            )
            db.session.add(appt)

        db.session.commit()

        print("Database created and seeded.")
        print("Admin login:")
        print(f"  Email: {ADMIN_EMAIL}")
        print(f"  Password: {ADMIN_PASSWORD} (CHANGE THIS AFTER FIRST LOGIN)")
        print("Doctor accounts: alice.hart@hms.local / Doctor@12345; brian.cole@hms.local / Doctor@12345")
        print("Patient accounts: john.doe@hms.local / Patient@12345; jane.smith@hms.local / Patient@12345")


if __name__ == "__main__":
    main()
