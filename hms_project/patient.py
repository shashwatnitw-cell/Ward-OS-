"""Patient blueprint: dashboard, search doctors, book/cancel/reschedule appointments.

All operations are server-rendered, POST-redirect-GET, and validated on the
server to prevent double booking.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import DateField, HiddenField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

from models import db, User, DoctorProfile, DoctorAvailability, Appointment
from utils import roles_required


patient_bp = Blueprint("patient", __name__)


class SearchForm(FlaskForm):
    specialization = StringField("Specialization")
    submit = SubmitField("Search")


class BookForm(FlaskForm):
    doctor_id = HiddenField(validators=[DataRequired()])  # User.id of doctor
    slot = SelectField("Available Slots", validators=[DataRequired()])  # value = YYYY-MM-DD|HH:MM
    submit = SubmitField("Book Appointment")


class RescheduleForm(FlaskForm):
    slot = SelectField("New Slot", validators=[DataRequired()])
    submit = SubmitField("Reschedule")


@patient_bp.route("/dashboard")
@roles_required("patient")
def dashboard():
    # Available specializations for discovery
    specs = [s[0] for s in db.session.query(DoctorProfile.specialization).distinct().all()]

    upcoming = (
        Appointment.query.filter_by(patient_id=current_user.id)
        .filter(Appointment.status == "Booked")
        .order_by(Appointment.date.asc(), Appointment.time.asc())
        .all()
    )
    history = (
        Appointment.query.filter_by(patient_id=current_user.id)
        .filter(Appointment.status != "Booked")
        .order_by(Appointment.date.desc(), Appointment.time.desc())
        .all()
    )
    return render_template("patient/dashboard.html", specializations=specs, upcoming=upcoming, history=history)


@patient_bp.route("/doctors")
@roles_required("patient")
def doctors_search():
    form = SearchForm(request.args)
    q = form.specialization.data.strip() if form.specialization.data else ""
    query = User.query.filter_by(role="doctor")
    if q:
        like = f"%{q.lower()}%"
        query = query.join(DoctorProfile).filter(DoctorProfile.specialization.ilike(like))
    doctors = query.order_by(User.name.asc()).all()
    return render_template("patient/search_doctors.html", form=form, doctors=doctors)


@patient_bp.route("/doctors/<int:doctor_id>/book")
@roles_required("patient")
def book_page(doctor_id: int):
    doctor = User.query.filter_by(id=doctor_id, role="doctor").first_or_404()
    profile = doctor.doctor_profile
    form = BookForm()
    form.doctor_id.data = str(doctor.id)

    # Build slot choices for next 7 days
    start = date.today()
    end = start + timedelta(days=7)
    slots = (
        DoctorAvailability.query.filter_by(doctor_id=profile.id, is_booked=False)
        .filter(DoctorAvailability.date >= start, DoctorAvailability.date <= end)
        .order_by(DoctorAvailability.date.asc(), DoctorAvailability.time.asc())
        .all()
    )
    form.slot.choices = [
        (f"{s.date.isoformat()}|{s.time}", f"{s.date.isoformat()} at {s.time}") for s in slots
    ]
    return render_template("patient/book_appointment.html", form=form, doctor=doctor)


@patient_bp.route("/book", methods=["POST"])
@roles_required("patient")
def book():
    form = BookForm()
    if not form.validate_on_submit():
        flash("Invalid booking form.", "danger")
        return redirect(url_for("patient.dashboard"))
    doctor = User.query.filter_by(id=int(form.doctor_id.data), role="doctor").first_or_404()
    profile = doctor.doctor_profile
    parts = form.slot.data.split("|")
    slot_date, slot_time = parts[0], parts[1]

    # Validate availability slot exists and not booked
    slot = DoctorAvailability.query.filter_by(
        doctor_id=profile.id, date=date.fromisoformat(slot_date), time=slot_time
    ).first()
    if not slot or slot.is_booked:
        flash("Selected slot is no longer available.", "warning")
        return redirect(url_for("patient.book_page", doctor_id=doctor.id))

    # Double-booking prevention: ensure no other active appointment for this slot
    conflict = (
        Appointment.query.filter_by(doctor_id=doctor.id, date=slot.date, time=slot.time)
        .filter(Appointment.status.in_(["Booked", "Completed"]))
        .first()
    )
    if conflict:
        flash("This time is already booked. Please choose another slot.", "danger")
        return redirect(url_for("patient.book_page", doctor_id=doctor.id))

    appt = Appointment(
        patient_id=current_user.id,
        doctor_id=doctor.id,
        date=slot.date,
        time=slot.time,
        status="Booked",
    )
    slot.is_booked = True
    db.session.add(appt)
    db.session.commit()
    flash("Appointment booked successfully.", "success")
    return redirect(url_for("patient.dashboard"))


@patient_bp.route("/appointments/<int:appointment_id>")
@roles_required("patient")
def appointment_detail(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.patient_id != current_user.id:
        abort(403)

    form = None
    if appt.status == "Booked":
        # Build reschedule choices from unbooked availability for this doctor (next 7 days)
        form = RescheduleForm()
        start = date.today()
        end = start + timedelta(days=7)
        profile = appt.doctor.doctor_profile
        slots = (
            DoctorAvailability.query.filter_by(doctor_id=profile.id, is_booked=False)
            .filter(DoctorAvailability.date >= start, DoctorAvailability.date <= end)
            .order_by(DoctorAvailability.date.asc(), DoctorAvailability.time.asc())
            .all()
        )
        form.slot.choices = [
            (f"{s.date.isoformat()}|{s.time}", f"{s.date.isoformat()} at {s.time}") for s in slots
            if not (s.date == appt.date and s.time == appt.time)
        ]

    return render_template("patient/appointment_detail.html", appointment=appt, form=form)


@patient_bp.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@roles_required("patient")
def cancel(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.patient_id != current_user.id:
        abort(403)
    if appt.status == "Booked":
        # Free the slot if we track it
        profile_id = appt.doctor.doctor_profile.id
        slot = DoctorAvailability.query.filter_by(
            doctor_id=profile_id, date=appt.date, time=appt.time
        ).first()
        if slot:
            slot.is_booked = False
        appt.status = "Cancelled"
        db.session.commit()
        flash("Appointment cancelled.", "info")
    return redirect(url_for("patient.dashboard"))


@patient_bp.route("/appointments/<int:appointment_id>/reschedule", methods=["POST"])
@roles_required("patient")
def reschedule(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.patient_id != current_user.id or appt.status != "Booked":
        abort(403)

    doctor = appt.doctor
    profile = doctor.doctor_profile

    # Expect slot value submitted as YYYY-MM-DD|HH:MM
    slot_value = request.form.get("slot")
    if not slot_value:
        flash("Please select a new slot.", "warning")
        return redirect(url_for("patient.appointment_detail", appointment_id=appointment_id))
    sd, st = slot_value.split("|")
    new_date = date.fromisoformat(sd)
    new_time = st

    # Validate the new slot exists and is not booked
    new_slot = DoctorAvailability.query.filter_by(
        doctor_id=profile.id, date=new_date, time=new_time
    ).first()
    if not new_slot or new_slot.is_booked:
        flash("Selected new slot is not available.", "danger")
        return redirect(url_for("patient.appointment_detail", appointment_id=appointment_id))

    # Double booking check
    conflict = (
        Appointment.query.filter_by(doctor_id=doctor.id, date=new_date, time=new_time)
        .filter(Appointment.status.in_(["Booked", "Completed"]))
        .first()
    )
    if conflict:
        flash("That time is already booked.", "danger")
        return redirect(url_for("patient.appointment_detail", appointment_id=appointment_id))

    # Free old slot
    old_profile_id = doctor.doctor_profile.id
    old_slot = DoctorAvailability.query.filter_by(
        doctor_id=old_profile_id, date=appt.date, time=appt.time
    ).first()
    if old_slot:
        old_slot.is_booked = False

    # Reserve new slot
    new_slot.is_booked = True
    appt.date = new_date
    appt.time = new_time
    db.session.commit()
    flash("Appointment rescheduled.", "success")
    return redirect(url_for("patient.dashboard"))


# --- Minimal API (optional) -------------------------------------------------

@patient_bp.route("/api/doctors")
def api_doctors():
    docs = (
        db.session.query(User.id, User.name, DoctorProfile.specialization)
        .join(DoctorProfile, DoctorProfile.id == User.id)
        .filter(User.role == "doctor")
        .all()
    )
    return jsonify([
        {"id": d.id, "name": d.name, "specialization": d.specialization} for d in docs
    ])
