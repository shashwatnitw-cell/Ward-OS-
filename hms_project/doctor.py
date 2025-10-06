"""Doctor blueprint: dashboard, appointment detail, complete visit, availability.

Doctor-only access enforced via @roles_required('doctor').
"""
from __future__ import annotations

from datetime import date
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, StringField
from wtforms.validators import DataRequired, Length
from flask_login import login_required, current_user

from models import db, User, Appointment, DoctorAvailability
from utils import roles_required, next_seven_days, parse_times_csv


doctor_bp = Blueprint("doctor", __name__, template_folder="templates")


class CompleteForm(FlaskForm):
    diagnosis = TextAreaField("Diagnosis", validators=[DataRequired()])
    prescription = TextAreaField("Prescription", validators=[DataRequired()])
    notes = TextAreaField("Notes")
    submit = SubmitField("Mark Completed")


class AvailabilityForm(FlaskForm):
    slots = StringField(
        "Daily Time Slots (CSV, e.g. 09:00, 10:00)", validators=[Length(max=200)]
    )
    submit = SubmitField("Update Next 7 Days")


@doctor_bp.route("/dashboard")
@login_required
@roles_required("doctor")
def dashboard():
    today = date.today()
    upcoming = (
        Appointment.query.filter_by(doctor_id=current_user.id)
        .filter(Appointment.status != "Cancelled")
        .order_by(Appointment.date.asc(), Appointment.time.asc())
        .all()
    )
    todays = [a for a in upcoming if a.date == today]
    return render_template("doctor/dashboard.html", todays=todays, upcoming=upcoming)


@doctor_bp.route("/appointments/<int:appointment_id>")
@login_required
@roles_required("doctor")
def appointment_detail(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("doctor.dashboard"))
    form = CompleteForm()
    return render_template("doctor/appointment_detail.html", appt=appt, form=form)


@doctor_bp.route("/appointments/<int:appointment_id>/complete", methods=["POST"])
@login_required
@roles_required("doctor")
def appointment_complete(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.doctor_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("doctor.dashboard"))
    form = CompleteForm()
    if form.validate_on_submit():
        appt.mark_completed(
            doctor_user_id=current_user.id,
            diagnosis=form.diagnosis.data,
            prescription=form.prescription.data,
            notes=form.notes.data,
        )
        db.session.commit()
        flash("Appointment marked as completed.", "success")
        return redirect(url_for("doctor.appointment_detail", appointment_id=appt.id))
    # if invalid, re-render detail
    return render_template("doctor/appointment_detail.html", appt=appt, form=form)


@doctor_bp.route("/availability", methods=["GET", "POST"])
@login_required
@roles_required("doctor")
def availability():
    form = AvailabilityForm()
    # Load current slots for next 7 days
    days = next_seven_days()
    slots = (
        DoctorAvailability.query.filter(
            DoctorAvailability.doctor_id == current_user.id,
            DoctorAvailability.date >= days[0],
            DoctorAvailability.date <= days[-1],
        )
        .order_by(DoctorAvailability.date.asc(), DoctorAvailability.time.asc())
        .all()
    )
    if form.validate_on_submit():
        # Remove existing future slots and recreate using provided daily list
        for s in slots:
            db.session.delete(s)
        db.session.flush()
        for d in days:
            for t in parse_times_csv(form.slots.data):
                db.session.add(
                    DoctorAvailability(doctor_id=current_user.id, date=d, time=t, is_booked=False)
                )
        db.session.commit()
        flash("Availability updated for the next 7 days.", "success")
        return redirect(url_for("doctor.availability"))
    return render_template("doctor/availability.html", form=form, slots=slots)
