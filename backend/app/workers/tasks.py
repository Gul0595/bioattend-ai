"""
BioAttend Ultimate — Celery Tasks (Fully Implemented)
All notification tasks are now real, not placeholders.
"""
from __future__ import annotations
import logging
from datetime import date
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, queue="reports")
def generate_attendance_report(self, employee_ids: list[str], start_date: str, end_date: str):
    try:
        import csv, io, uuid as _uuid
        from pathlib import Path
        from sqlalchemy import create_engine, and_
        from sqlalchemy.orm import Session
        from app.core.config import settings
        from app.models import AttendanceLog, Employee
        from uuid import UUID

        sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
        engine = create_engine(sync_url)
        start = date.fromisoformat(start_date)
        end   = date.fromisoformat(end_date)

        with Session(engine) as db:
            rows = []
            for eid in employee_ids:
                emp = db.query(Employee).filter(Employee.id == UUID(eid)).first()
                if not emp:
                    continue
                logs = db.query(AttendanceLog).filter(
                    and_(AttendanceLog.employee_id == UUID(eid),
                         AttendanceLog.date >= start, AttendanceLog.date <= end)
                ).order_by(AttendanceLog.date).all()
                for l in logs:
                    rows.append({
                        "Employee ID":  emp.employee_id,
                        "Name":         emp.full_name,
                        "Department":   emp.department.name if emp.department else "",
                        "Date":         str(l.date),
                        "Check In":     l.check_in.strftime("%H:%M:%S") if l.check_in else "",
                        "Check Out":    l.check_out.strftime("%H:%M:%S") if l.check_out else "",
                        "Work Hours":   round(l.work_hours or 0, 2),
                        "Overtime":     round(l.overtime_hours or 0, 2),
                        "Status":       l.status.value if l.status else "",
                        "Late":         "Yes" if l.is_late else "No",
                        "Late Minutes": l.late_minutes or 0,
                        "Method":       l.method or "",
                    })

        buf = io.StringIO()
        if rows:
            w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)

        filename = f"attendance_{start_date}_to_{end_date}_{_uuid.uuid4().hex[:8]}.csv"
        path = Path(settings.LOCAL_STORAGE_PATH) / "reports" / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(buf.getvalue(), encoding="utf-8")

        logger.info("Report ready: %s (%d rows)", filename, len(rows))
        return {"status": "done", "download_url": f"/storage/reports/{filename}",
                "filename": filename, "rows": len(rows)}

    except Exception as exc:
        logger.error("Report failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(queue="attendance")
def mark_absent_employees():
    """Mark no-show employees absent and send daily HR summary."""
    from sqlalchemy import create_engine, and_
    from sqlalchemy.orm import Session
    from app.core.config import settings
    from app.models import AttendanceLog, AttendanceStatus, Employee, User, UserRole

    today = date.today()
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_url)

    absent_names = []
    total = present = on_leave = late_count = 0

    with Session(engine) as db:
        all_active = db.query(Employee).filter(Employee.is_active == True).all()
        total = len(all_active)

        for emp in all_active:
            log = db.query(AttendanceLog).filter(
                and_(AttendanceLog.employee_id == emp.id, AttendanceLog.date == today)
            ).first()
            if not log:
                db.add(AttendanceLog(employee_id=emp.id, date=today,
                                     status=AttendanceStatus.absent, method="system"))
                absent_names.append(emp.full_name)
            elif log.status == AttendanceStatus.on_leave:
                on_leave += 1
            elif log.check_in:
                present += 1
                if log.is_late:
                    late_count += 1
        db.commit()

        hr_users = db.query(User).filter(
            and_(User.role == UserRole.hr, User.is_active == True)
        ).all()

    import asyncio

    async def _summaries():
        from app.services.notification_service import send_daily_summary
        for hr in hr_users:
            await send_daily_summary(
                hr_email=hr.email, report_date=today, total=total,
                present=present, absent=len(absent_names),
                late=late_count, on_leave=on_leave, absent_names=absent_names,
            )

    asyncio.run(_summaries())
    logger.info("Absent marking: %d absent on %s", len(absent_names), today)
    return {"date": str(today), "absent": len(absent_names), "present": present}


@celery_app.task(queue="notifications")
def send_late_notifications():
    """Send late alerts to managers at 9:30 AM."""
    from sqlalchemy import create_engine, and_
    from sqlalchemy.orm import Session
    from app.core.config import settings
    from app.models import AttendanceLog, Employee

    today = date.today()
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    sent = 0

    with Session(engine) as db:
        late_logs = db.query(AttendanceLog).filter(
            and_(AttendanceLog.date == today, AttendanceLog.is_late == True,
                 AttendanceLog.check_in.isnot(None))
        ).all()

        import asyncio

        async def _notify():
            nonlocal sent
            from app.services.notification_service import notify_late_checkin
            for log in late_logs:
                emp = db.query(Employee).filter(Employee.id == log.employee_id).first()
                if not emp or not emp.department or not emp.department.manager:
                    continue
                mgr = emp.department.manager
                if not mgr.user or not mgr.user.email:
                    continue
                ok = await notify_late_checkin(
                    manager_email=mgr.user.email, employee_name=emp.full_name,
                    employee_id=emp.employee_id, check_in_time=log.check_in,
                    late_minutes=log.late_minutes or 0,
                    shift_name=emp.shift.name if emp.shift else "General",
                )
                if ok:
                    sent += 1

        asyncio.run(_notify())

    logger.info("Late notifications: %d sent", sent)
    return {"sent": sent, "date": str(today)}
