"""Admin blueprint: manage doctors, patients, and appointments.

Admin-only access enforced via roles_required('admin'). No JavaScript.
"""
from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_wtf import FlaskForm

from models import db, User, DoctorProfile, DoctorAvailability, Appointment
from utils import roles_required


admin_bp = Blueprint("admin", __name__)


class DoctorForm(FlaskForm):
    name = StringField("Doctor Name", validators=[DataRequired(), Length(min=2, max=120)])
    specialization = StringField("Specialization", validators=[DataRequired(), Length(max=120)])
    contact = StringField("Contact", validators=[Length(max=120)])
    bio = TextAreaField("Bio", validators=[Length(max=1000)])
    submit = SubmitField("Save")


class DeleteForm(FlaskForm):
    submit = SubmitField("Delete")


@admin_bp.route("/dashboard")
@roles_required("admin")
def dashboard():
    total_doctors = User.query.filter_by(role="doctor").count()
    total_patients = User.query.filter_by(role="patient").count()
    total_appointments = Appointment.query.count()
    upcoming = Appointment.query.filter(Appointment.status == "Booked").count()
    return render_template(
        "admin/dashboard.html",
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments,
        upcoming=upcoming,
    )


@admin_bp.route("/doctors")
@roles_required("admin")
def doctors_list():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role="doctor")
    if q:
        like = f"%{q.lower()}%"
        query = query.join(DoctorProfile, DoctorProfile.id == User.id).filter(
            (User.name.ilike(like)) | (DoctorProfile.specialization.ilike(like))
        )
    doctors = query.order_by(User.name.asc()).all()
    delete_form = DeleteForm()
    return render_template("admin/doctors_list.html", doctors=doctors, q=q, delete_form=delete_form)


@admin_bp.route("/doctors/new", methods=["GET", "POST"])
@roles_required("admin")
def doctor_new():
    form = DoctorForm()
    if form.validate_on_submit():
        # Create user with doctor role
        temp_password = "Doctor123!"  # For demo; doctor should reset in real system
        user = User(name=form.name.data, email=f"{form.name.data.replace(' ', '').lower()}@example.com",
                    contact=form.contact.data, role="doctor", password_hash="")
        from werkzeug.security import generate_password_hash

        user.password_hash = generate_password_hash(temp_password)
        db.session.add(user)
        db.session.flush()  # get id

        profile = DoctorProfile(id=user.id, specialization=form.specialization.data, bio=form.bio.data)
        db.session.add(profile)
        db.session.commit()
        flash("Doctor created.", "success")
        return redirect(url_for("admin.doctors_list"))
    return render_template("admin/doctors_list.html", form=form, create=True, doctors=[])


@admin_bp.route("/doctors/<int:id>/edit", methods=["GET", "POST"])
@roles_required("admin")
def doctor_edit(id: int):
    user = User.query.filter_by(id=id, role="doctor").first_or_404()
    profile = user.doctor_profile
    form = DoctorForm(obj=user)
    if request.method == "GET" and profile:
        form.specialization.data = profile.specialization
        form.bio.data = profile.bio
    if form.validate_on_submit():
        user.name = form.name.data
        user.contact = form.contact.data
        if not profile:
            profile = DoctorProfile(id=user.id, specialization=form.specialization.data, bio=form.bio.data)
            db.session.add(profile)
        else:
            profile.specialization = form.specialization.data
            profile.bio = form.bio.data
        db.session.commit()
        flash("Doctor updated.", "success")
        return redirect(url_for("admin.doctors_list"))
    return render_template("admin/doctors_list.html", form=form, edit=True, doctor=user, doctors=[])


@admin_bp.route("/doctors/<int:id>/delete", methods=["POST"])
@roles_required("admin")
def doctor_delete(id: int):
    form = DeleteForm()
    if not form.validate_on_submit():
        flash("Invalid request.", "danger")
        return redirect(url_for("admin.doctors_list"))
    user = User.query.filter_by(id=id, role="doctor").first_or_404()
    # Deleting the user will cascade delete profile and availability due to FK cascade
    db.session.delete(user)
    db.session.commit()
    flash("Doctor deleted.", "info")
    return redirect(url_for("admin.doctors_list"))


@admin_bp.route("/appointments")
@roles_required("admin")
def appointments_list():
    status = request.args.get("status")
    query = Appointment.query
    if status:
        query = query.filter_by(status=status)
    appointments = query.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template("admin/dashboard.html", appointments=appointments)


@admin_bp.route("/patients")
@roles_required("admin")
def patients_list():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role="patient")
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(User.name.ilike(like))
    patients = query.order_by(User.name.asc()).all()
    return render_template("admin/dashboard.html", patients=patients, q=q)


@admin_bp.route("/patients/<int:id>")
@roles_required("admin")
def patient_detail(id: int):
    patient = User.query.filter_by(id=id, role="patient").first_or_404()
    history = Appointment.query.filter_by(patient_id=patient.id).order_by(
        Appointment.date.desc(), Appointment.time.desc()
    ).all()
    return render_template("admin/dashboard.html", patient=patient, history=history)
