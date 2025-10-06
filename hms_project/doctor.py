"""Doctor blueprint: dashboard, appointment details, complete visit, and availability management.

No JavaScript; forms post back to server.
"""
from __future__ import annotations

from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import DateField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length

from models import db, User, Appointment, DoctorProfile, DoctorAvailability
from utils import roles_required


doctor_bp = Blueprint("doctor", __name__)


class CompleteAppointmentForm(FlaskForm):
    diagnosis = TextAreaField("Diagnosis", validators=[DataRequired(), Length(max=5000)])
    prescription = TextAreaField("Prescription", validators=[DataRequired(), Length(max=5000)])
    notes = TextAreaField("Notes", validators=[Length(max=5000)])
    submit = SubmitField("Mark Completed")


class AvailabilityForm(FlaskForm):
    date = DateField("Date (YYYY-MM-DD)", format="%Y-%m-%d", validators=[DataRequired()])
    time = StringField("Time (HH:MM)", validators=[DataRequired(), Length(min=5, max=5)])
    submit = SubmitField("Add Slot")


@doctor_bp.route("/dashboard")
@roles_required("doctor")
def dashboard():
    # We have current_user via flask-login
    from flask_login import current_user

    today = date.today()
    upcoming = (
        Appointment.query.filter_by(doctor_id=current_user.id)
        .filter(Appointment.date >= today)
        .order_by(Appointment.date.asc(), Appointment.time.asc())
        .all()
    )
    todays = [a for a in upcoming if a.date == today]
    return render_template("doctor/dashboard.html", todays=todays, upcoming=upcoming)


@doctor_bp.route("/appointments/<int:appointment_id>")
@roles_required("doctor")
def appointment_detail(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    return render_template("doctor/appointment_detail.html", appointment=appt, form=CompleteAppointmentForm())


@doctor_bp.route("/appointments/<int:appointment_id>/complete", methods=["POST"])
@roles_required("doctor")
def appointment_complete(appointment_id: int):
    from flask_login import current_user

    appt = Appointment.query.get_or_404(appointment_id)
    form = CompleteAppointmentForm()
    if form.validate_on_submit():
        appt.mark_completed(
            diagnosis=form.diagnosis.data,
            prescription=form.prescription.data,
            notes=form.notes.data,
            recorded_by_doctor_id=current_user.id,
        )
        db.session.commit()
        flash("Appointment marked as completed.", "success")
        return redirect(url_for("doctor.appointment_detail", appointment_id=appointment_id))
    flash("Please correct errors in the form.", "danger")
    return render_template("doctor/appointment_detail.html", appointment=appt, form=form)


@doctor_bp.route("/patient/<int:patient_id>/history")
@roles_required("doctor")
def patient_history(patient_id: int):
    history = Appointment.query.filter_by(patient_id=patient_id).order_by(
        Appointment.date.desc(), Appointment.time.desc()
    ).all()
    return render_template("doctor/appointment_detail.html", history=history)


@doctor_bp.route("/availability", methods=["GET", "POST"])
@roles_required("doctor")
def availability():
    from flask_login import current_user

    form = AvailabilityForm()
    if form.validate_on_submit():
        # Add slot, enforce unique constraint
        profile = current_user.doctor_profile
        if not profile:
            profile = DoctorProfile(id=current_user.id, specialization="General")
            db.session.add(profile)
            db.session.flush()
        slot = DoctorAvailability(doctor_id=profile.id, date=form.date.data, time=form.time.data)
        try:
            db.session.add(slot)
            db.session.commit()
            flash("Slot added.", "success")
        except Exception:
            db.session.rollback()
            flash("Slot already exists.", "warning")
    # Show next 7 days availability
    start = date.today()
    end = start + timedelta(days=7)
    profile = current_user.doctor_profile
    pid = profile.id if profile else None
    slots = []
    if pid is not None:
        slots = (
            DoctorAvailability.query.filter_by(doctor_id=pid)
            .filter(DoctorAvailability.date >= start, DoctorAvailability.date <= end)
            .order_by(DoctorAvailability.date.asc(), DoctorAvailability.time.asc())
            .all()
        )
    return render_template("doctor/dashboard.html", availability=slots, form=form)
