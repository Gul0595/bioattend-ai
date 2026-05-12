"""
BioAttend Ultimate — Async Attendance Service
Best of both:
  - Async SQLAlchemy (FULL)
  - Shift-aware late/overtime calculations (PRO)
  - Half-day detection (PRO)
  - Monthly summary (FULL structure, PRO fields)
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AttendanceLog, AttendanceStatus, Employee, Holiday, Shift


async def record_check_in(
    db: AsyncSession,
    employee: Employee,
    method: str = "face",
    image_url: Optional[str] = None,
    face_score: Optional[float] = None,
    location: Optional[str] = None,
    device_id: Optional[str] = None,
) -> AttendanceLog:
    now = datetime.now(timezone.utc)
    today = now.date()

    # Fetch or create today's log
    result = await db.execute(
        select(AttendanceLog).where(
            and_(AttendanceLog.employee_id == employee.id, AttendanceLog.date == today)
        )
    )
    log = result.scalar_one_or_none()

    if log and log.check_in:
        return log  # Already checked in

    # Determine lateness vs shift schedule
    is_late = False
    late_minutes = 0
    shift: Optional[Shift] = employee.shift

    if shift:
        scheduled_start = datetime.combine(today, shift.start_time).replace(tzinfo=timezone.utc)
        grace_end = scheduled_start + timedelta(minutes=shift.grace_minutes)
        if now > grace_end:
            is_late = True
            late_minutes = int((now - scheduled_start).total_seconds() / 60)

    status = AttendanceStatus.late if is_late else AttendanceStatus.present

    if log:
        log.check_in = now
        log.method = method
        log.check_in_image_url = image_url
        log.face_match_score = face_score
        log.check_in_location = location
        log.device_id = device_id
        log.is_late = is_late
        log.late_minutes = late_minutes
        log.status = status
        if shift:
            log.shift_id = shift.id
    else:
        log = AttendanceLog(
            employee_id=employee.id,
            shift_id=shift.id if shift else None,
            date=today,
            check_in=now,
            method=method,
            check_in_image_url=image_url,
            face_match_score=face_score,
            check_in_location=location,
            device_id=device_id,
            is_late=is_late,
            late_minutes=late_minutes,
            status=status,
        )
        db.add(log)

    await db.flush()
    await db.refresh(log)
    return log


async def record_check_out(
    db: AsyncSession,
    employee: Employee,
    method: str = "face",
    location: Optional[str] = None,
    device_id: Optional[str] = None,
) -> AttendanceLog:
    today = date.today()
    result = await db.execute(
        select(AttendanceLog).where(
            and_(AttendanceLog.employee_id == employee.id, AttendanceLog.date == today)
        )
    )
    log = result.scalar_one_or_none()

    if not log or not log.check_in:
        raise ValueError("No check-in record found for today")

    now = datetime.now(timezone.utc)
    log.check_out = now
    log.check_out_method = method
    log.check_out_location = location

    duration_hours = (now - log.check_in).total_seconds() / 3600
    log.work_hours = round(duration_hours, 2)

    # Overtime calculation
    shift: Optional[Shift] = employee.shift
    if shift:
        shift_hours = (
            datetime.combine(today, shift.end_time) - datetime.combine(today, shift.start_time)
        ).total_seconds() / 3600
        ot_threshold = shift_hours + (shift.overtime_after_minutes / 60)
        if duration_hours > ot_threshold:
            log.overtime_hours = round(duration_hours - shift_hours, 2)

        # Early out detection
        scheduled_end = datetime.combine(today, shift.end_time).replace(tzinfo=timezone.utc)
        if now < scheduled_end:
            log.early_out = True
            log.early_out_minutes = int((scheduled_end - now).total_seconds() / 60)

    # Half-day rule
    if log.work_hours < 4:
        log.status = AttendanceStatus.half_day

    await db.flush()
    await db.refresh(log)
    return log


async def get_today_summary(db: AsyncSession) -> dict:
    today = date.today()

    total = (await db.execute(
        select(func.count()).select_from(Employee).where(Employee.is_active == True)
    )).scalar_one()

    present = (await db.execute(
        select(func.count()).select_from(AttendanceLog).where(
            and_(AttendanceLog.date == today, AttendanceLog.check_in.isnot(None))
        )
    )).scalar_one()

    late = (await db.execute(
        select(func.count()).select_from(AttendanceLog).where(
            and_(AttendanceLog.date == today, AttendanceLog.is_late == True)
        )
    )).scalar_one()

    checked_in_now = (await db.execute(
        select(func.count()).select_from(AttendanceLog).where(
            and_(
                AttendanceLog.date == today,
                AttendanceLog.check_in.isnot(None),
                AttendanceLog.check_out.is_(None),
            )
        )
    )).scalar_one()

    on_leave = (await db.execute(
        select(func.count()).select_from(AttendanceLog).where(
            and_(AttendanceLog.date == today, AttendanceLog.status == AttendanceStatus.on_leave)
        )
    )).scalar_one()

    absent = max(0, total - present - on_leave)
    rate = round((present / total * 100), 1) if total else 0.0

    return {
        "total_employees": total,
        "present_today": present,
        "absent_today": absent,
        "late_today": late,
        "on_leave_today": on_leave,
        "checked_in_now": checked_in_now,
        "attendance_rate": rate,
    }


async def get_monthly_summary(
    db: AsyncSession,
    employee_id: UUID,
    year: int,
    month: int,
) -> dict:
    from calendar import monthrange
    _, days_in_month = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, days_in_month)

    result = await db.execute(
        select(AttendanceLog).where(
            and_(
                AttendanceLog.employee_id == employee_id,
                AttendanceLog.date >= start,
                AttendanceLog.date <= end,
            )
        )
    )
    logs = result.scalars().all()

    # Count holidays in range
    h_result = await db.execute(
        select(func.count()).select_from(Holiday).where(
            and_(Holiday.date >= start, Holiday.date <= end, Holiday.is_optional == False)
        )
    )
    holidays = h_result.scalar_one()

    present   = sum(1 for l in logs if l.status == AttendanceStatus.present)
    late      = sum(1 for l in logs if l.is_late)
    half_day  = sum(1 for l in logs if l.status == AttendanceStatus.half_day)
    on_leave  = sum(1 for l in logs if l.status == AttendanceStatus.on_leave)
    absent    = days_in_month - holidays - present - late - half_day - on_leave
    avg_hrs   = sum(l.work_hours or 0 for l in logs) / max(len(logs), 1)
    total_ot  = sum(l.overtime_hours or 0 for l in logs)
    pct       = round((present + late) / max(days_in_month - holidays, 1) * 100, 1)

    return {
        "total_days": days_in_month,
        "present": present,
        "absent": max(0, absent),
        "late": late,
        "half_day": half_day,
        "on_leave": on_leave,
        "holidays": holidays,
        "average_work_hours": round(avg_hrs, 2),
        "total_overtime_hours": round(total_ot, 2),
        "attendance_percentage": pct,
    }
