"""
Database creation and seeding script for the Hospital Management System.
This script programmatically creates the SQLite database, all tables,
and populates them with sample data for testing.
"""
import os
from datetime import datetime, timedelta
from app import create_app
from models import db, User, DoctorProfile, DoctorAvailability, Appointment


def create_database():
    """
    Create the database and all tables.
    """
    app = create_app()
    
    with app.app_context():
        # Drop all existing tables (if any) and create fresh ones
        db.drop_all()
        db.create_all()
        
        print("✓ Database tables created successfully!")
        
        # Seed initial data
        seed_data()
        
        print("\n" + "="*60)
        print("DATABASE SETUP COMPLETE!")
        print("="*60)
        print("\nDefault Login Credentials:")
        print("-" * 60)
        print("\nADMIN ACCOUNT:")
        print("  Email:    admin@hospital.com")
        print("  Password: admin123")
        print("  ⚠️  WARNING: Change this password immediately in production!")
        
        print("\nDOCTOR ACCOUNTS:")
        print("  1. Dr. Sarah Johnson (Cardiology)")
        print("     Email:    sarah.johnson@hospital.com")
        print("     Password: doctor123")
        print("\n  2. Dr. Michael Chen (Neurology)")
        print("     Email:    michael.chen@hospital.com")
        print("     Password: doctor123")
        
        print("\nPATIENT ACCOUNTS:")
        print("  1. John Smith")
        print("     Email:    john.smith@email.com")
        print("     Password: patient123")
        print("\n  2. Emma Wilson")
        print("     Email:    emma.wilson@email.com")
        print("     Password: patient123")
        
        print("\n" + "="*60)
        print("NEXT STEPS:")
        print("="*60)
        print("1. Run the development server:")
        print("   python app.py")
        print("\n2. Open your browser and navigate to:")
        print("   http://localhost:5000")
        print("\n3. Login with any of the credentials above")
        print("="*60 + "\n")


def seed_data():
    """
    Populate the database with sample data.
    """
    print("\nSeeding database with sample data...")
    
    # 1. Create Admin User
    print("  → Creating admin user...")
    admin = User(
        email='admin@hospital.com',
        name='Hospital Administrator',
        role='admin',
        contact='+1-555-0001'
    )
    admin.set_password('admin123')
    db.session.add(admin)
    
    # 2. Create Doctor Users with Profiles
    print("  → Creating doctor users...")
    
    # Doctor 1: Dr. Sarah Johnson (Cardiology)
    doctor1 = User(
        email='sarah.johnson@hospital.com',
        name='Dr. Sarah Johnson',
        role='doctor',
        contact='+1-555-0101'
    )
    doctor1.set_password('doctor123')
    db.session.add(doctor1)
    db.session.flush()
    
    doctor1_profile = DoctorProfile(
        doctor_id=doctor1.id,
        specialization='Cardiology',
        bio='Board-certified cardiologist with 15 years of experience in treating heart conditions.',
        phone='+1-555-0101'
    )
    db.session.add(doctor1_profile)
    
    # Doctor 2: Dr. Michael Chen (Neurology)
    doctor2 = User(
        email='michael.chen@hospital.com',
        name='Dr. Michael Chen',
        role='doctor',
        contact='+1-555-0102'
    )
    doctor2.set_password('doctor123')
    db.session.add(doctor2)
    db.session.flush()
    
    doctor2_profile = DoctorProfile(
        doctor_id=doctor2.id,
        specialization='Neurology',
        bio='Specialist in neurological disorders with expertise in stroke and epilepsy treatment.',
        phone='+1-555-0102'
    )
    db.session.add(doctor2_profile)
    
    # 3. Create Patient Users
    print("  → Creating patient users...")
    
    patient1 = User(
        email='john.smith@email.com',
        name='John Smith',
        role='patient',
        contact='+1-555-0201'
    )
    patient1.set_password('patient123')
    db.session.add(patient1)
    
    patient2 = User(
        email='emma.wilson@email.com',
        name='Emma Wilson',
        role='patient',
        contact='+1-555-0202'
    )
    patient2.set_password('patient123')
    db.session.add(patient2)
    
    db.session.flush()
    
    # 4. Create Doctor Availability (next 7 days, 9 AM - 5 PM hourly slots)
    print("  → Creating doctor availability slots...")
    
    today = datetime.now().date()
    
    for doctor_id in [doctor1.id, doctor2.id]:
        for day_offset in range(7):
            date = today + timedelta(days=day_offset)
            
            # Create hourly slots from 9 AM to 4 PM (8 slots per day)
            for hour in range(9, 17):
                time_slot = f"{hour:02d}:00"
                
                availability = DoctorAvailability(
                    doctor_id=doctor_id,
                    date=date,
                    time=time_slot,
                    is_booked=False
                )
                db.session.add(availability)
    
    db.session.flush()
    
    # 5. Create Sample Appointments
    print("  → Creating sample appointments...")
    
    # Appointment 1: John Smith with Dr. Sarah Johnson (tomorrow at 10:00)
    tomorrow = today + timedelta(days=1)
    appt1 = Appointment(
        patient_id=patient1.id,
        doctor_id=doctor1.id,
        date=tomorrow,
        time='10:00',
        status='Booked'
    )
    db.session.add(appt1)
    
    # Mark slot as booked
    slot1 = DoctorAvailability.query.filter_by(
        doctor_id=doctor1.id,
        date=tomorrow,
        time='10:00'
    ).first()
    if slot1:
        slot1.is_booked = True
    
    # Appointment 2: Emma Wilson with Dr. Michael Chen (day after tomorrow at 14:00)
    day_after_tomorrow = today + timedelta(days=2)
    appt2 = Appointment(
        patient_id=patient2.id,
        doctor_id=doctor2.id,
        date=day_after_tomorrow,
        time='14:00',
        status='Booked'
    )
    db.session.add(appt2)
    
    # Mark slot as booked
    slot2 = DoctorAvailability.query.filter_by(
        doctor_id=doctor2.id,
        date=day_after_tomorrow,
        time='14:00'
    ).first()
    if slot2:
        slot2.is_booked = True
    
    # Appointment 3: Past completed appointment with treatment notes
    past_date = today - timedelta(days=5)
    appt3 = Appointment(
        patient_id=patient1.id,
        doctor_id=doctor1.id,
        date=past_date,
        time='11:00',
        status='Completed',
        diagnosis='Hypertension - Stage 1',
        prescription='Lisinopril 10mg once daily, follow low-sodium diet',
        notes='Patient shows good compliance. Schedule follow-up in 3 months.'
    )
    db.session.add(appt3)
    
    # Commit all changes
    db.session.commit()
    print("  ✓ Sample data created successfully!")


if __name__ == '__main__':
    """
    Run this script to create and seed the database.
    Usage: python create_db.py
    """
    # Check if database already exists
    db_path = 'hms.db'
    if os.path.exists(db_path):
        response = input(f"\n⚠️  Database '{db_path}' already exists. Overwrite? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Database creation cancelled.")
            exit(0)
        else:
            os.remove(db_path)
            print(f"✓ Existing database removed.")
    
    create_database()
