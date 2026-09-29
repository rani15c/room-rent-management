from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import os

import requests
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from sqlalchemy import func

from .extensions import db
from .models import Lease, Owner, Payment, Room, Student

main = Blueprint("main", __name__)


def razorpay_credentials():
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret or key_id.startswith("rzp_test_your"):
        return None
    return key_id, key_secret


def money(value):
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


@main.app_template_filter("money")
def money_filter(value):
    return f"Rs. {money(value):,.2f}"


@main.route("/")
def dashboard():
    stats = {
        "students": Student.query.count(),
        "rooms": Room.query.count(),
        "available": Room.query.filter_by(status="available").count(),
        "revenue": db.session.query(func.coalesce(func.sum(Payment.amount), 0)).filter_by(status="paid").scalar(),
    }
    recent_payments = Payment.query.order_by(Payment.payment_date.desc(), Payment.id.desc()).limit(5).all()
    return render_template("dashboard.html", stats=stats, recent_payments=recent_payments)


@main.route("/owners", methods=["GET", "POST"])
def owners():
    if request.method == "POST":
        owner = Owner(
            name=request.form["name"].strip(),
            phone=request.form["phone"].strip(),
            email=request.form.get("email", "").strip(),
            address=request.form.get("address", "").strip(),
        )
        db.session.add(owner)
        db.session.commit()
        flash("Owner added successfully.", "success")
        return redirect(url_for("main.owners"))
    return render_template("owners.html", owners=Owner.query.order_by(Owner.name).all())


@main.route("/rooms", methods=["GET", "POST"])
def rooms():
    if request.method == "POST":
        room = Room(
            room_number=request.form["room_number"].strip(),
            title=request.form["title"].strip(),
            location=request.form["location"].strip(),
            monthly_rent=money(request.form["monthly_rent"]),
            capacity=int(request.form.get("capacity", 1)),
            amenities=request.form.get("amenities", "").strip(),
            owner_id=int(request.form["owner_id"]),
        )
        db.session.add(room)
        db.session.commit()
        flash("Room added successfully.", "success")
        return redirect(url_for("main.rooms"))
    return render_template("rooms.html", rooms=Room.query.order_by(Room.status, Room.location).all(), owners=Owner.query.order_by(Owner.name).all())


@main.route("/students", methods=["GET", "POST"])
def students():
    if request.method == "POST":
        student = Student(
            name=request.form["name"].strip(),
            phone=request.form["phone"].strip(),
            email=request.form["email"].strip(),
            college=request.form.get("college", "").strip(),
            emergency_contact=request.form.get("emergency_contact", "").strip(),
        )
        db.session.add(student)
        db.session.commit()
        flash("Student added successfully.", "success")
        return redirect(url_for("main.students"))
    return render_template("students.html", students=Student.query.order_by(Student.name).all())


@main.route("/leases", methods=["GET", "POST"])
def leases():
    if request.method == "POST":
        room = db.get_or_404(Room, int(request.form["room_id"]))
        lease = Lease(
            student_id=int(request.form["student_id"]),
            room_id=room.id,
            start_date=date.fromisoformat(request.form["start_date"]),
            security_deposit=money(request.form.get("security_deposit")),
        )
        room.status = "occupied"
        db.session.add(lease)
        db.session.commit()
        flash("Lease created and room marked occupied.", "success")
        return redirect(url_for("main.leases"))
    active_leases = Lease.query.order_by(Lease.status, Lease.start_date.desc()).all()
    return render_template("leases.html", leases=active_leases, students=Student.query.order_by(Student.name).all(), rooms=Room.query.filter_by(status="available").order_by(Room.location).all())


@main.route("/payments", methods=["GET", "POST"])
def payments():
    if request.method == "POST":
        payment = Payment(
            lease_id=int(request.form["lease_id"]),
            amount=money(request.form["amount"]),
            payment_month=request.form["payment_month"],
            payment_date=date.fromisoformat(request.form["payment_date"]),
            method=request.form["method"],
            transaction_reference=request.form.get("transaction_reference", "").strip(),
        )
        db.session.add(payment)
        db.session.commit()
        flash("Payment recorded successfully.", "success")
        return redirect(url_for("main.payments"))
    payments = Payment.query.order_by(Payment.payment_date.desc(), Payment.id.desc()).all()
    leases = Lease.query.filter_by(status="active").order_by(Lease.id.desc()).all()
    return render_template(
        "payments.html",
        payments=payments,
        leases=leases,
        today=date.today().isoformat(),
        razorpay_key_id=os.getenv("RAZORPAY_KEY_ID", ""),
        online_payments_enabled=razorpay_credentials() is not None,
    )


@main.post("/payments/create-order")
def create_payment_order():
    credentials = razorpay_credentials()
    if credentials is None:
        return jsonify(error="Online payments are not configured. Add Razorpay keys to .env."), 503

    lease = db.get_or_404(Lease, request.form.get("lease_id", type=int))
    amount = money(request.form.get("amount"))
    payment_month = request.form.get("payment_month", "")
    if amount <= 0 or not payment_month:
        return jsonify(error="Enter a valid amount and payment month."), 400

    key_id, key_secret = credentials
    response = requests.post(
        "https://api.razorpay.com/v1/orders",
        auth=(key_id, key_secret),
        json={
            "amount": int(amount * 100),
            "currency": "INR",
            "receipt": f"lease-{lease.id}-{payment_month}",
            "notes": {"lease_id": str(lease.id), "payment_month": payment_month},
        },
        timeout=15,
    )
    if not response.ok:
        return jsonify(error="Razorpay could not create the payment order."), 502
    order = response.json()
    payment = Payment(
        lease_id=lease.id,
        amount=amount,
        payment_month=payment_month,
        payment_date=date.today(),
        method="Razorpay",
        status="created",
        gateway_order_id=order["id"],
    )
    db.session.add(payment)
    db.session.commit()
    return jsonify(order_id=order["id"], amount=int(amount * 100), currency="INR", key_id=os.getenv("RAZORPAY_KEY_ID"))


@main.post("/payments/verify")
def verify_payment():
    credentials = razorpay_credentials()
    if credentials is None:
        return jsonify(error="Online payments are not configured."), 503

    order_id = request.form.get("razorpay_order_id", "")
    payment_id = request.form.get("razorpay_payment_id", "")
    signature = request.form.get("razorpay_signature", "")
    payment = Payment.query.filter_by(gateway_order_id=order_id).first_or_404()
    _, key_secret = credentials
    expected_signature = hmac.new(
        key_secret.encode(),
        f"{order_id}|{payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        return jsonify(error="Payment verification failed."), 400

    payment.gateway_payment_id = payment_id
    payment.gateway_signature = signature
    payment.transaction_reference = payment_id
    payment.status = "paid"
    payment.payment_date = date.today()
    db.session.commit()
    return jsonify(message="Payment verified successfully.")
