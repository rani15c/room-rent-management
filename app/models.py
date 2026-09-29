from datetime import date, datetime

from .extensions import db


class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.String(250))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    rooms = db.relationship("Room", back_populates="owner", cascade="all, delete-orphan")


class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    location = db.Column(db.String(160), nullable=False)
    monthly_rent = db.Column(db.Numeric(10, 2), nullable=False)
    capacity = db.Column(db.Integer, default=1, nullable=False)
    amenities = db.Column(db.String(250))
    status = db.Column(db.String(20), default="available", nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey("owner.id"), nullable=False)
    owner = db.relationship("Owner", back_populates="rooms")
    leases = db.relationship("Lease", back_populates="room", cascade="all, delete-orphan")


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    college = db.Column(db.String(160))
    emergency_contact = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    leases = db.relationship("Lease", back_populates="student", cascade="all, delete-orphan")


class Lease(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date)
    security_deposit = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    student = db.relationship("Student", back_populates="leases")
    room = db.relationship("Room", back_populates="leases")
    payments = db.relationship("Payment", back_populates="lease", cascade="all, delete-orphan")


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lease_id = db.Column(db.Integer, db.ForeignKey("lease.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_month = db.Column(db.String(7), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=date.today)
    method = db.Column(db.String(30), nullable=False)
    transaction_reference = db.Column(db.String(100))
    status = db.Column(db.String(20), default="paid", nullable=False)
    gateway_order_id = db.Column(db.String(100), unique=True)
    gateway_payment_id = db.Column(db.String(100), unique=True)
    gateway_signature = db.Column(db.String(255))
    lease = db.relationship("Lease", back_populates="payments")
