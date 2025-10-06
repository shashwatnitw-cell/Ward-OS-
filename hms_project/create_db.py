#!/usr/bin/env python3
"""
Database creation and seeding script for Hospital Management System
Run this script to create the SQLite database and populate it with sample data
"""

import os
import sys
from datetime import datetime, date, time, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, DoctorProfile, DoctorAvailability, Appointment, Treatment
from utils import get_time_slots, get_next_7_days

def create_database():
    """Create all database tables"""
    print("Creating database tables...")
    db.create_all()
    print("✓ Database tables created successfully!")

def seed_admin_user():
    """Create default admin user"""
    print("Creating admin user...")
    
    # Check if admin already exists
    admin = User.query.filter_by(email='admin@hms.com').first()
    if admin:
        print("⚠ Admin user already exists!")
        return admin
    
    admin = User(
        name='System Administrator',
        email='admin@hms.com',
        role='admin',
        contact='555-0100'
    )
    admin.set_password('admin123')
    
    db.session.add(admin)
    db.session.commit()
    
    print("✓ Admin user created successfully!")
    print(f"   Email: admin@hms.com")
    print(f"   Password: admin123")
    print("   ⚠ IMPORTANT: Change this password in production!")
    
    return admin

def seed_doctors():
    """Create sample doctors with profiles and availability"""
    print("Creating sample doctors...")
    
    doctors_data = [
        {
            'name': 'Dr. Sarah Johnson',
            'email': 'sarah.johnson@hms.com',
            'password': 'doctor123',
            'contact': '555-0201',
            'specialization': 'Cardiology',
            'bio': 'Experienced cardiologist with 15 years of practice. Specializes in heart disease prevention and treatment.',
            'experience_years': 15
        },
        {
            'name': 'Dr. Michael Chen',
            'email': 'michael.chen@hms.com',
            'password': 'doctor123',
            'contact': '555-0202',
            'specialization': 'Pediatrics',
            'bio': 'Board-certified pediatrician dedicated to providing comprehensive care for children and adolescents.',
            'experience_years': 12
        },
        {
            'name': 'Dr. Emily Rodriguez',
            'email': 'emily.rodriguez@hms.com',
            'password': 'doctor123',
            'contact': '555-0203',
            'specialization': 'Dermatology',
            'bio': 'Dermatologist specializing in skin cancer detection, cosmetic procedures, and general dermatology.',
            'experience_years': 8
        }
    ]
    
    created_doctors = []
    
    for doctor_data in doctors_data:
        # Check if doctor already exists
        existing_doctor = User.query.filter_by(email=doctor_data['email']).first()
        if existing_doctor:
            print(f"⚠ Doctor {doctor_data['name']} already exists!")
            created_doctors.append(existing_doctor)
            continue
        
        # Create doctor user
        doctor = User(
            name=doctor_data['name'],
            email=doctor_data['email'],
            role='doctor',
            contact=doctor_data['contact']
        )
        doctor.set_password(doctor_data['password'])
        
        db.session.add(doctor)
        db.session.flush()  # Get the doctor ID
        
        # Create doctor profile
        profile = DoctorProfile(
            doctor_id=doctor.id,
            specialization=doctor_data['specialization'],
            bio=doctor_data['bio'],
            phone=doctor_data['contact'],
            experience_years=doctor_data['experience_years']
        )
        
        db.session.add(profile)
        created_doctors.append(doctor)
        
        print(f"✓ Created doctor: {doctor_data['name']} ({doctor_data['specialization']})")
    
    db.session.commit()
    return created_doctors

def seed_doctor_availability(doctors):
    """Create availability slots for doctors"""
    print("Creating doctor availability slots...")
    
    time_slots = get_time_slots()
    next_days = get_next_7_days()
    
    for doctor in doctors:
        if doctor.role != 'doctor':
            continue
            
        # Check if availability already exists
        existing_availability = DoctorAvailability.query.filter_by(doctor_id=doctor.id).first()
        if existing_availability:
            print(f"⚠ Availability for Dr. {doctor.name} already exists!")
            continue
        
        slots_created = 0
        
        for day in next_days:
            # Skip weekends for some doctors (make it realistic)
            if day.weekday() >= 5 and doctor.id % 2 == 0:  # Some doctors don't work weekends
                continue
            
            # Create morning and afternoon slots
            for time_slot in time_slots:
                # Skip lunch hours (12:00-13:00) for some realism
                if time_slot.hour == 12:
                    continue
                
                availability = DoctorAvailability(
                    doctor_id=doctor.id,
                    date=day,
                    time=time_slot,
                    is_booked=False
                )
                
                db.session.add(availability)
                slots_created += 1
        
        print(f"✓ Created {slots_created} availability slots for Dr. {doctor.name}")
    
    db.session.commit()

def seed_patients():
    """Create sample patients"""
    print("Creating sample patients...")
    
    patients_data = [
        {
            'name': 'John Smith',
            'email': 'john.smith@email.com',
            'password': 'patient123',
            'contact': '555-1001'
        },
        {
            'name': 'Mary Johnson',
            'email': 'mary.johnson@email.com',
            'password': 'patient123',
            'contact': '555-1002'
        },
        {
            'name': 'Robert Davis',
            'email': 'robert.davis@email.com',
            'password': 'patient123',
            'contact': '555-1003'
        }
    ]
    
    created_patients = []
    
    for patient_data in patients_data:
        # Check if patient already exists
        existing_patient = User.query.filter_by(email=patient_data['email']).first()
        if existing_patient:
            print(f"⚠ Patient {patient_data['name']} already exists!")
            created_patients.append(existing_patient)
            continue
        
        patient = User(
            name=patient_data['name'],
            email=patient_data['email'],
            role='patient',
            contact=patient_data['contact']
        )
        patient.set_password(patient_data['password'])
        
        db.session.add(patient)
        created_patients.append(patient)
        
        print(f"✓ Created patient: {patient_data['name']}")
    
    db.session.commit()
    return created_patients

def seed_sample_appointments(doctors, patients):
    """Create sample appointments and treatments"""
    print("Creating sample appointments...")
    
    if not doctors or not patients:
        print("⚠ No doctors or patients available for creating appointments!")
        return
    
    # Create some past completed appointments with treatments
    past_appointments_data = [
        {
            'patient': patients[0],  # John Smith
            'doctor': doctors[0],    # Dr. Sarah Johnson
            'days_ago': 30,
            'time': time(10, 0),
            'diagnosis': 'Hypertension monitoring',
            'prescription': 'Lisinopril 10mg daily, follow-up in 3 months',
            'notes': 'Blood pressure well controlled. Patient advised on diet and exercise.'
        },
        {
            'patient': patients[1],  # Mary Johnson
            'doctor': doctors[1],    # Dr. Michael Chen
            'days_ago': 15,
            'time': time(14, 30),
            'diagnosis': 'Annual pediatric checkup',
            'prescription': 'Multivitamin daily, updated vaccination schedule',
            'notes': 'Child is developing normally. All vaccinations up to date.'
        },
        {
            'patient': patients[2],  # Robert Davis
            'doctor': doctors[2],    # Dr. Emily Rodriguez
            'days_ago': 7,
            'time': time(11, 0),
            'diagnosis': 'Skin lesion examination',
            'prescription': 'Topical corticosteroid cream, follow-up in 2 weeks',
            'notes': 'Benign skin condition. Patient educated on proper skin care.'
        }
    ]
    
    for appt_data in past_appointments_data:
        appointment_date = date.today() - timedelta(days=appt_data['days_ago'])
        
        # Check if appointment already exists
        existing_appointment = Appointment.query.filter_by(
            patient_id=appt_data['patient'].id,
            doctor_id=appt_data['doctor'].id,
            date=appointment_date,
            time=appt_data['time']
        ).first()
        
        if existing_appointment:
            print(f"⚠ Appointment between {appt_data['patient'].name} and {appt_data['doctor'].name} already exists!")
            continue
        
        # Create appointment
        appointment = Appointment(
            patient_id=appt_data['patient'].id,
            doctor_id=appt_data['doctor'].id,
            date=appointment_date,
            time=appt_data['time'],
            status='Completed'
        )
        
        db.session.add(appointment)
        db.session.flush()  # Get appointment ID
        
        # Create treatment record
        treatment = Treatment(
            appointment_id=appointment.id,
            diagnosis=appt_data['diagnosis'],
            prescription=appt_data['prescription'],
            notes=appt_data['notes'],
            recorded_by_doctor_id=appt_data['doctor'].id
        )
        
        db.session.add(treatment)
        
        print(f"✓ Created completed appointment: {appt_data['patient'].name} with {appt_data['doctor'].name}")
    
    # Create some upcoming appointments
    upcoming_appointments_data = [
        {
            'patient': patients[0],  # John Smith
            'doctor': doctors[1],    # Dr. Michael Chen
            'days_ahead': 3,
            'time': time(9, 30)
        },
        {
            'patient': patients[1],  # Mary Johnson
            'doctor': doctors[2],    # Dr. Emily Rodriguez
            'days_ahead': 5,
            'time': time(15, 0)
        }
    ]
    
    for appt_data in upcoming_appointments_data:
        appointment_date = date.today() + timedelta(days=appt_data['days_ahead'])
        
        # Check if appointment already exists
        existing_appointment = Appointment.query.filter_by(
            patient_id=appt_data['patient'].id,
            doctor_id=appt_data['doctor'].id,
            date=appointment_date,
            time=appt_data['time']
        ).first()
        
        if existing_appointment:
            print(f"⚠ Upcoming appointment between {appt_data['patient'].name} and {appt_data['doctor'].name} already exists!")
            continue
        
        # Check if doctor has availability at this time
        availability_slot = DoctorAvailability.query.filter_by(
            doctor_id=appt_data['doctor'].id,
            date=appointment_date,
            time=appt_data['time'],
            is_booked=False
        ).first()
        
        if availability_slot:
            # Create appointment
            appointment = Appointment(
                patient_id=appt_data['patient'].id,
                doctor_id=appt_data['doctor'].id,
                date=appointment_date,
                time=appt_data['time'],
                status='Booked'
            )
            
            # Mark slot as booked
            availability_slot.is_booked = True
            
            db.session.add(appointment)
            
            print(f"✓ Created upcoming appointment: {appt_data['patient'].name} with {appt_data['doctor'].name}")
        else:
            print(f"⚠ No availability slot found for {appt_data['doctor'].name} on {appointment_date} at {appt_data['time']}")
    
    db.session.commit()

def print_summary():
    """Print summary of created data"""
    print("\n" + "="*60)
    print("DATABASE SETUP COMPLETE!")
    print("="*60)
    
    # Count records
    admin_count = User.query.filter_by(role='admin').count()
    doctor_count = User.query.filter_by(role='doctor').count()
    patient_count = User.query.filter_by(role='patient').count()
    appointment_count = Appointment.query.count()
    availability_count = DoctorAvailability.query.count()
    
    print(f"📊 SUMMARY:")
    print(f"   • Admins: {admin_count}")
    print(f"   • Doctors: {doctor_count}")
    print(f"   • Patients: {patient_count}")
    print(f"   • Appointments: {appointment_count}")
    print(f"   • Availability Slots: {availability_count}")
    
    print(f"\n🔑 DEFAULT LOGIN CREDENTIALS:")
    print(f"   Admin:")
    print(f"     Email: admin@hms.com")
    print(f"     Password: admin123")
    
    print(f"\n   Sample Doctor:")
    print(f"     Email: sarah.johnson@hms.com")
    print(f"     Password: doctor123")
    
    print(f"\n   Sample Patient:")
    print(f"     Email: john.smith@email.com")
    print(f"     Password: patient123")
    
    print(f"\n🚀 NEXT STEPS:")
    print(f"   1. Run: python app.py")
    print(f"   2. Open: http://localhost:5000")
    print(f"   3. Login with credentials above")
    print(f"   4. ⚠ CHANGE DEFAULT PASSWORDS!")
    
    print("\n" + "="*60)

def main():
    """Main function to set up the database"""
    print("Hospital Management System - Database Setup")
    print("="*50)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Create database and tables
            create_database()
            
            # Seed data
            admin = seed_admin_user()
            doctors = seed_doctors()
            seed_doctor_availability(doctors)
            patients = seed_patients()
            seed_sample_appointments(doctors, patients)
            
            # Print summary
            print_summary()
            
        except Exception as e:
            print(f"❌ Error during database setup: {str(e)}")
            db.session.rollback()
            sys.exit(1)

if __name__ == '__main__':
    main()