"""
BioAttend Ultimate — Pydantic Schemas
"""
from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Department ───────────────────────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentOut(BaseModel):
    id: UUID
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Shift ────────────────────────────────────────────────────────────────────

class ShiftCreate(BaseModel):
    name: str
    start_time: time
    end_time: time
    grace_minutes: int = 15
    overtime_after_minutes: int = 30


class ShiftOut(BaseModel):
    id: UUID
    name: str
    start_time: time
    end_time: time
    grace_minutes: int
    overtime_after_minutes: int
    is_active: bool

    model_config = {"from_attributes": True}


# ─── Employee ─────────────────────────────────────────────────────────────────

class EmployeeCreate(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    designation: Optional[str] = None
    department_id: Optional[UUID] = None
    shift_id: Optional[UUID] = None
    date_of_joining: Optional[date] = None
    date_of_birth: Optional[date] = None
    fingerprint_id: Optional[str] = None
    # Optionally create a linked user account
    create_user: bool = False
    password: Optional[str] = None
    role: str = "employee"


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    designation: Optional[str] = None
    department_id: Optional[UUID] = None
    shift_id: Optional[UUID] = None
    fingerprint_id: Optional[str] = None
    is_active: Optional[bool] = None


class EmployeeOut(BaseModel):
    id: UUID
    employee_id: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: Optional[str] = None
    designation: Optional[str] = None
    department: Optional[DepartmentOut] = None
    shift: Optional[ShiftOut] = None
    date_of_joining: Optional[date] = None
    date_of_birth: Optional[date] = None
    face_image_url: Optional[str] = None
    fingerprint_id: Optional[str] = None
    biometric_enrolled: bool
    biometric_enrolled_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Attendance ───────────────────────────────────────────────────────────────

class FaceCheckInRequest(BaseModel):
    """For kiosk / edge device sending base64 image."""
    image_base64: str
    device_id: Optional[str] = None
    location: Optional[str] = None


class ManualAttendanceRequest(BaseModel):
    employee_id: UUID
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: str = "present"
    notes: Optional[str] = None


class AttendanceOut(BaseModel):
    id: UUID
    employee_id: UUID
    employee_name: Optional[str] = None
    date: date
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    work_hours: float
    overtime_hours: float
    status: str
    method: str
    is_late: bool
    late_minutes: int
    early_out: bool
    face_match_score: Optional[float] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class AttendanceSummary(BaseModel):
    total_days: int
    present: int
    absent: int
    late: int
    half_day: int
    on_leave: int
    holidays: int
    average_work_hours: float
    total_overtime_hours: float
    attendance_percentage: float


# ─── Leave ────────────────────────────────────────────────────────────────────

class LeaveCreate(BaseModel):
    employee_id: UUID
    leave_type: str
    start_date: date
    end_date: date
    reason: Optional[str] = None


class LeaveAction(BaseModel):
    status: str  # approved | rejected
    rejection_reason: Optional[str] = None


class LeaveOut(BaseModel):
    id: UUID
    employee_id: UUID
    employee_name: Optional[str] = None
    leave_type: str
    start_date: date
    end_date: date
    days: float
    reason: Optional[str] = None
    status: str
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_employees: int
    present_today: int
    absent_today: int
    late_today: int
    on_leave_today: int
    checked_in_now: int
    attendance_rate: float
