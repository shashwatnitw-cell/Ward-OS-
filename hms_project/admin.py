"""Admin blueprint: dashboards and CRUD for doctors/patients/appointments.

Admin-only access enforced via @roles_required('admin').
"""
from __future__ import annotations

from datetime import date
from typing import List

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_login import login_required

from werkzeug.security import generate_password_hash

from models import db, User, DoctorProfile, DoctorAvailability, Appointment
from utils import roles_required, next_seven_days, parse_times_csv


class DoctorForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired()])
    specialization = StringField("Specialization", validators=[DataRequired()])
    phone = StringField("Phone")
    bio = TextAreaField("Bio")
    # availability input as CSV times (HH:MM) applied to next 7 days
    availability_times = StringField(
        "Daily Time Slots (CSV, e.g. 09:00, 10:00, 14:30)", validators=[Length(max=200)]
    )
    submit = SubmitField("Save")


admin_bp = Blueprint("admin", __name__, template_folder="templates")


@admin_bp.route("/dashboard")
@login_required
@roles_required("admin")
def dashboard():
    total_doctors = User.query.filter_by(role="doctor").count()
    total_patients = User.query.filter_by(role="patient").count()
    total_appointments = Appointment.query.count()
    upcoming = Appointment.query.filter(Appointment.status != "Cancelled").count()
    return render_template(
        "admin/dashboard.html",
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments,
        upcoming=upcoming,
    )


@admin_bp.route("/doctors")
@login_required
@roles_required("admin")
def doctors_list():
    q = request.args.get("q", "").strip().lower()
    query = (
        DoctorProfile.query.join(User, User.id == DoctorProfile.doctor_id)
        .order_by(User.name.asc())
    )
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(User.name.ilike(like), DoctorProfile.specialization.ilike(like))
        )
    doctors = query.all()
    return render_template("admin/doctors_list.html", doctors=doctors, q=q)


@admin_bp.route("/doctors/new", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def doctors_new():
    form = DoctorForm()
    if form.validate_on_submit():
        # Create user with doctor role
        email = form.email.data.lower()
        if User.query.filter_by(email=email).first():
            flash("Email already exists", "warning")
        else:
            user = User(
                name=form.name.data,
                email=email,
                role="doctor",
                password_hash=generate_password_hash("ChangeMe123!"),
            )
            db.session.add(user)
            db.session.flush()

            profile = DoctorProfile(
                doctor_id=user.id,
                specialization=form.specialization.data,
                phone=form.phone.data,
                bio=form.bio.data,
            )
            db.session.add(profile)
            db.session.flush()

            # Seed availability for next 7 days based on provided daily times
            slots = parse_times_csv(form.availability_times.data)
            for d in next_seven_days():
                for t in slots:
                    db.session.add(
                        DoctorAvailability(doctor_id=user.id, date=d, time=t, is_booked=False)
                    )
            db.session.commit()
            flash("Doctor created with initial availability.", "success")
            return redirect(url_for("admin.doctors_list"))
    return render_template("admin/doctor_form.html", form=form, mode="new")


@admin_bp.route("/doctors/<int:doctor_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def doctors_edit(doctor_id: int):
    user = User.query.get_or_404(doctor_id)
    if not user.is_doctor():
        flash("User is not a doctor", "danger")
        return redirect(url_for("admin.doctors_list"))
    profile = user.doctor_profile
    form = DoctorForm(obj=profile)
    form.name.data = user.name
    form.email.data = user.email
    if form.validate_on_submit():
        user.name = form.name.data
        user.email = form.email.data.lower()
        profile.specialization = form.specialization.data
        profile.phone = form.phone.data
        profile.bio = form.bio.data
        db.session.commit()
        flash("Doctor updated", "success")
        return redirect(url_for("admin.doctors_list"))
    return render_template("admin/doctor_form.html", form=form, mode="edit")


@admin_bp.route("/doctors/<int:doctor_id>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def doctors_delete(doctor_id: int):
    user = User.query.get_or_404(doctor_id)
    if user.is_admin():
        flash("Cannot delete admin", "danger")
    else:
        db.session.delete(user)
        db.session.commit()
        flash("Doctor deleted", "info")
    return redirect(url_for("admin.doctors_list"))


@admin_bp.route("/appointments")
@login_required
@roles_required("admin")
def appointments_view():
    status = request.args.get("status")
    q = Appointment.query
    if status:
        q = q.filter_by(status=status)
    q = q.order_by(Appointment.date.desc(), Appointment.time.desc())
    appts = q.all()
    return render_template("admin/appointments.html", appointments=appts, status=status)


@admin_bp.route("/patients")
@login_required
@roles_required("admin")
def patients_list():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role="patient")
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.name.ilike(like), User.email.ilike(like)))
    patients = query.order_by(User.created_at.desc()).all()
    return render_template("admin/patients.html", patients=patients, q=q)


@admin_bp.route("/patients/<int:patient_id>")
@login_required
@roles_required("admin")
def patient_detail(patient_id: int):
    patient = User.query.get_or_404(patient_id)
    if not patient.is_patient():
        flash("Not a patient", "warning")
        return redirect(url_for("admin.patients_list"))
    history = (
        Appointment.query.filter_by(patient_id=patient_id)
        .order_by(Appointment.date.desc(), Appointment.time.desc())
        .all()
    )
    return render_template("admin/patient_detail.html", patient=patient, history=history)
