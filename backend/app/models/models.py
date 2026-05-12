"""
BioAttend Ultimate — SQLAlchemy ORM Models
Best of both worlds:
  - UUID primary keys (FULL project)
  - Rich field set from PRO (leave, holiday, audit log, overtime)
  - Async-compatible (no sync relations that break async)
  - pgvector ARRAY for face embeddings (FULL project)
"""
from __future__ import annotations

import uuid
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, Float, ForeignKey,
    Integer, String, Text, Time, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# ─── Enumerations ─────────────────────────────────────────────────────────────

class UserRole(str, PyEnum):
    admin    = "admin"
    hr       = "hr"
    manager  = "manager"
    employee = "employee"
    viewer   = "viewer"


class AttendanceStatus(str, PyEnum):
    present  = "present"
    absent   = "absent"
    late     = "late"
    half_day = "half_day"
    on_leave = "on_leave"
    holiday  = "holiday"


class LeaveType(str, PyEnum):
    casual    = "casual"
    sick      = "sick"
    earned    = "earned"
    maternity = "maternity"
    paternity = "paternity"
    unpaid    = "unpaid"


class LeaveStatus(str, PyEnum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name       = Column(String(255), nullable=False)
    role            = Column(Enum(UserRole), default=UserRole.employee, nullable=False)
    is_active       = Column(Boolean, default=True)
    is_verified     = Column(Boolean, default=False)
    last_login      = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    employee    = relationship("Employee", back_populates="user", uselist=False, lazy="selectin")
    audit_logs  = relationship("AuditLog", back_populates="user", lazy="noload")


# ─── Department ───────────────────────────────────────────────────────────────

class Department(Base):
    __tablename__ = "departments"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(100), unique=True, nullable=False)
    code        = Column(String(20), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    manager_id  = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=True)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    employees = relationship(
        "Employee", back_populates="department",
        foreign_keys="Employee.department_id", lazy="noload"
    )
    manager = relationship("Employee", foreign_keys=[manager_id], lazy="noload")


# ─── Shift ────────────────────────────────────────────────────────────────────

class Shift(Base):
    __tablename__ = "shifts"

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name                   = Column(String(100), nullable=False)
    start_time             = Column(Time, nullable=False)
    end_time               = Column(Time, nullable=False)
    grace_minutes          = Column(Integer, default=15)
    overtime_after_minutes = Column(Integer, default=30)
    is_active              = Column(Boolean, default=True)
    created_at             = Column(DateTime(timezone=True), server_default=func.now())

    employees       = relationship("Employee", back_populates="shift", lazy="noload")
    attendance_logs = relationship("AttendanceLog", back_populates="shift", lazy="noload")


# ─── Employee ─────────────────────────────────────────────────────────────────

class Employee(Base):
    __tablename__ = "employees"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id   = Column(String(50), unique=True, index=True, nullable=False)
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    shift_id      = Column(UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=True)

    first_name      = Column(String(100), nullable=False)
    last_name       = Column(String(100), nullable=False)
    email           = Column(String(255), unique=True, index=True, nullable=False)
    phone           = Column(String(20), nullable=True)
    designation     = Column(String(100), nullable=True)
    date_of_joining = Column(Date, nullable=True)
    date_of_birth   = Column(Date, nullable=True)

    # Biometric — AES-256-GCM encrypted embedding (stored as base64 text)
    # Decrypt with app.services.encryption_service.decrypt_embedding()
    face_embedding        = Column(Text, nullable=True)
    face_image_url        = Column(String(500), nullable=True)
    fingerprint_id        = Column(String(100), nullable=True)  # ZKTeco device ID
    biometric_enrolled    = Column(Boolean, default=False)
    biometric_enrolled_at = Column(DateTime(timezone=True), nullable=True)

    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user            = relationship("User", back_populates="employee", lazy="selectin")
    department      = relationship("Department", back_populates="employees",
                                   foreign_keys=[department_id], lazy="selectin")
    shift           = relationship("Shift", back_populates="employees", lazy="selectin")
    attendance_logs = relationship("AttendanceLog", back_populates="employee", lazy="noload")
    leave_requests  = relationship("LeaveRequest", back_populates="employee", lazy="noload")
    leave_balances  = relationship("LeaveBalance", back_populates="employee", lazy="noload")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


# ─── Attendance Log ───────────────────────────────────────────────────────────

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    shift_id    = Column(UUID(as_uuid=True), ForeignKey("shifts.id"), nullable=True)
    date        = Column(Date, nullable=False, index=True)

    check_in  = Column(DateTime(timezone=True), nullable=True)
    check_out = Column(DateTime(timezone=True), nullable=True)

    work_hours     = Column(Float, default=0.0)
    overtime_hours = Column(Float, default=0.0)

    status            = Column(Enum(AttendanceStatus), default=AttendanceStatus.present)
    method            = Column(String(20), default="face")   # face | fingerprint | manual
    check_out_method  = Column(String(20), nullable=True)
    device_id         = Column(String(100), nullable=True)

    check_in_image_url  = Column(String(500), nullable=True)
    check_in_location   = Column(String(255), nullable=True)
    check_out_location  = Column(String(255), nullable=True)

    face_match_score = Column(Float, nullable=True)
    is_late          = Column(Boolean, default=False)
    late_minutes     = Column(Integer, default=0)
    early_out        = Column(Boolean, default=False)
    early_out_minutes= Column(Integer, default=0)

    notes      = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", back_populates="attendance_logs", lazy="selectin")
    shift    = relationship("Shift", back_populates="attendance_logs", lazy="selectin")


# ─── Leave Request ────────────────────────────────────────────────────────────

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    leave_type  = Column(Enum(LeaveType), nullable=False)
    start_date  = Column(Date, nullable=False)
    end_date    = Column(Date, nullable=False)
    days        = Column(Float, nullable=False)
    reason      = Column(Text, nullable=True)
    status      = Column(Enum(LeaveStatus), default=LeaveStatus.pending)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", back_populates="leave_requests", lazy="selectin")
    approver = relationship("User", foreign_keys=[approved_by], lazy="selectin")


# ─── Holiday ──────────────────────────────────────────────────────────────────

class Holiday(Base):
    __tablename__ = "holidays"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name        = Column(String(100), nullable=False)
    date        = Column(Date, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_optional = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


# ─── Audit Log ────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action      = Column(String(100), nullable=False)
    resource    = Column(String(100), nullable=True)
    resource_id = Column(String(50), nullable=True)
    details     = Column(Text, nullable=True)          # JSON string
    ip_address  = Column(String(50), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs", lazy="noload")


# ─── Leave Balance ────────────────────────────────────────────────────────────

class LeaveBalance(Base):
    """
    Annual leave entitlement + used days per employee per year.
    Created automatically when an employee is created (via seed or route).
    Deducted automatically when a LeaveRequest is approved.
    """
    __tablename__ = "leave_balances"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    year        = Column(Integer, nullable=False)
    leave_type  = Column(Enum(LeaveType), nullable=False)

    entitled    = Column(Float, default=0.0)   # total days entitled this year
    used        = Column(Float, default=0.0)   # days consumed (approved leaves)
    pending     = Column(Float, default=0.0)   # days in pending requests
    carried_fwd = Column(Float, default=0.0)   # carried forward from last year

    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    employee = relationship("Employee", back_populates="leave_balances", lazy="selectin")

    @property
    def available(self) -> float:
        return max(0.0, self.entitled + self.carried_fwd - self.used - self.pending)

    from sqlalchemy import UniqueConstraint
    __table_args__ = (
        UniqueConstraint("employee_id", "year", "leave_type", name="uq_leave_balance"),
    )


# ─── Geofence Zone ────────────────────────────────────────────────────────────

class GeofenceZone(Base):
    """
    Office/branch location for check-in geofencing.
    Attendance is only accepted when the device is within radius_meters of (lat, lng).
    """
    __tablename__ = "geofence_zones"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name           = Column(String(100), nullable=False)
    latitude       = Column(Float, nullable=False)
    longitude      = Column(Float, nullable=False)
    radius_meters  = Column(Integer, default=100)   # default 100m radius
    is_active      = Column(Boolean, default=True)
    bypass_kiosk   = Column(Boolean, default=True)  # kiosk devices exempt (they're on-premises)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())


# ─── Password Reset Token ─────────────────────────────────────────────────────

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False)  # SHA-256 of token
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used       = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", lazy="selectin")
