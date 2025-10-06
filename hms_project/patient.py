"""Patient blueprint: dashboard, search, book, cancel, reschedule, view.

Patient-only access enforced via @roles_required('patient').
"""
from __future__ import annotations

from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import SelectField, HiddenField, SubmitField
from wtforms.validators import DataRequired
from flask_login import login_required, current_user

from models import db, User, DoctorProfile, DoctorAvailability, Appointment
from utils import roles_required


patient_bp = Blueprint("patient", __name__, template_folder="templates")


class BookForm(FlaskForm):
    doctor_id = HiddenField(validators=[DataRequired()])
    slot_id = SelectField("Select Slot", validators=[DataRequired()], coerce=int)
    submit = SubmitField("Book Appointment")


@patient_bp.route("/dashboard")
@login_required
@roles_required("patient")
def dashboard():
    upcoming = (
        Appointment.query.filter_by(patient_id=current_user.id)
        .filter(Appointment.status == "Booked")
        .order_by(Appointment.date.asc(), Appointment.time.asc())
        .all()
    )
    past = (
        Appointment.query.filter_by(patient_id=current_user.id)
        .filter(Appointment.status != "Booked")
        .order_by(Appointment.date.desc(), Appointment.time.desc())
        .all()
    )
    specializations = [p.specialization for p in DoctorProfile.query.distinct(DoctorProfile.specialization)]
    return render_template("patient/dashboard.html", upcoming=upcoming, past=past, specializations=specializations)


@patient_bp.route("/doctors")
@login_required
@roles_required("patient")
def search_doctors():
    spec = request.args.get("specialization", "").strip()
    q = DoctorProfile.query.join(User, User.id == DoctorProfile.doctor_id)
    if spec:
        q = q.filter(DoctorProfile.specialization.ilike(f"%{spec}%"))
    doctors = q.order_by(User.name.asc()).all()
    return render_template("patient/search_doctors.html", doctors=doctors, spec=spec)


@patient_bp.route("/doctors/<int:doctor_id>/book", methods=["GET", "POST"])
@login_required
@roles_required("patient")
def book_doctor(doctor_id: int):
    doctor_user = User.query.get_or_404(doctor_id)
    if not doctor_user.is_doctor():
        flash("Not a doctor", "danger")
        return redirect(url_for("patient.search_doctors"))

    available_slots = (
        DoctorAvailability.query.filter_by(doctor_id=doctor_id, is_booked=False)
        .order_by(DoctorAvailability.date.asc(), DoctorAvailability.time.asc())
        .all()
    )
    form = BookForm()
    form.doctor_id.data = str(doctor_id)
    form.slot_id.choices = [(s.id, f"{s.date} {s.time}") for s in available_slots]
    if form.validate_on_submit():
        slot = DoctorAvailability.query.get(form.slot_id.data)
        if not slot or slot.doctor_id != doctor_id or slot.is_booked:
            flash("Selected slot is no longer available.", "danger")
            return redirect(url_for("patient.book_doctor", doctor_id=doctor_id))
        # double-booking prevention: check existing appointment
        conflict = (
            Appointment.query.filter_by(doctor_id=doctor_id, date=slot.date, time=slot.time)
            .filter(Appointment.status.in_(["Booked", "Completed"]))
            .first()
        )
        if conflict:
            flash("That slot has just been booked. Please choose another.", "warning")
            return redirect(url_for("patient.book_doctor", doctor_id=doctor_id))
        # create appointment and mark slot booked
        appt = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_id,
            date=slot.date,
            time=slot.time,
            status="Booked",
        )
        slot.is_booked = True
        db.session.add(appt)
        db.session.commit()
        flash("Appointment booked!", "success")
        return redirect(url_for("patient.dashboard"))
    return render_template("patient/book_appointment.html", doctor=doctor_user, form=form)


@patient_bp.route("/appointments/<int:appointment_id>")
@login_required
@roles_required("patient")
def appointment_detail(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.patient_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("patient.dashboard"))
    return render_template("patient/appointment_detail.html", appt=appt)


@patient_bp.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@login_required
@roles_required("patient")
def cancel_appointment(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.patient_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("patient.dashboard"))
    appt.status = "Cancelled"
    # free up slot if modeled
    slot = (
        DoctorAvailability.query.filter_by(doctor_id=appt.doctor_id, date=appt.date, time=appt.time)
        .first()
    )
    if slot:
        slot.is_booked = False
    db.session.commit()
    flash("Appointment cancelled.", "info")
    return redirect(url_for("patient.dashboard"))


class RescheduleForm(FlaskForm):
    slot_id = SelectField("New Slot", validators=[DataRequired()], coerce=int)
    submit = SubmitField("Reschedule")


@patient_bp.route("/appointments/<int:appointment_id>/reschedule", methods=["POST"])
@login_required
@roles_required("patient")
def reschedule(appointment_id: int):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.patient_id != current_user.id:
        flash("Unauthorized", "danger")
        return redirect(url_for("patient.dashboard"))

    # Build choices for current doctor
    available_slots = (
        DoctorAvailability.query.filter_by(doctor_id=appt.doctor_id, is_booked=False)
        .order_by(DoctorAvailability.date.asc(), DoctorAvailability.time.asc())
        .all()
    )
    form = RescheduleForm()
    form.slot_id.choices = [(s.id, f"{s.date} {s.time}") for s in available_slots]

    # Validate submitted slot
    if form.validate_on_submit():
        new_slot = DoctorAvailability.query.get(form.slot_id.data)
        if not new_slot or new_slot.is_booked or new_slot.doctor_id != appt.doctor_id:
            flash("Invalid slot selected.", "danger")
            return redirect(url_for("patient.dashboard"))
        # conflict check
        conflict = (
            Appointment.query.filter_by(
                doctor_id=appt.doctor_id, date=new_slot.date, time=new_slot.time
            )
            .filter(Appointment.status.in_(["Booked", "Completed"]))
            .first()
        )
        if conflict:
            flash("Selected slot is already booked.", "warning")
            return redirect(url_for("patient.dashboard"))
        # free old slot and book new
        old_slot = (
            DoctorAvailability.query.filter_by(
                doctor_id=appt.doctor_id, date=appt.date, time=appt.time
            ).first()
        )
        if old_slot:
            old_slot.is_booked = False
        appt.date = new_slot.date
        appt.time = new_slot.time
        new_slot.is_booked = True
        db.session.commit()
        flash("Appointment rescheduled.", "success")
    else:
        flash("Invalid reschedule request.", "danger")
    return redirect(url_for("patient.dashboard"))
