from datetime import date, timedelta
from typing import Annotated, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser
from app.core.database import get_db
from app.models import AttendanceLog, AttendanceStatus, Department, Employee
from app.services.attendance_service import get_today_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def dashboard_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
):
    return await get_today_summary(db)


@router.get("/attendance-trend")
async def attendance_trend(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
    days: int = Query(30, ge=7, le=90),
):
    end = date.today()
    start = end - timedelta(days=days)

    result = await db.execute(
        select(
            AttendanceLog.date,
            func.count().label("total"),
            func.sum(func.cast(AttendanceLog.is_late == True, type_=db.bind.dialect.INTEGER if hasattr(db, 'bind') else func.cast(AttendanceLog.is_late, type_=None))).label("late"),
        )
        .where(and_(AttendanceLog.date >= start, AttendanceLog.date <= end))
        .group_by(AttendanceLog.date)
        .order_by(AttendanceLog.date)
    )
    rows = result.all()

    # Simpler approach
    result2 = await db.execute(
        select(AttendanceLog.date, AttendanceLog.status, AttendanceLog.is_late)
        .where(and_(AttendanceLog.date >= start, AttendanceLog.date <= end))
        .order_by(AttendanceLog.date)
    )
    all_logs = result2.all()

    from collections import defaultdict
    by_date: dict = defaultdict(lambda: {"present": 0, "late": 0, "absent": 0, "on_leave": 0})
    for row in all_logs:
        d = str(row.date)
        s = row.status.value if row.status else "present"
        by_date[d][s] = by_date[d].get(s, 0) + 1
        if row.is_late:
            by_date[d]["late"] = by_date[d].get("late", 0)

    trend = [
        {"date": d, **counts}
        for d, counts in sorted(by_date.items())
    ]
    return trend


@router.get("/department-breakdown")
async def department_breakdown(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
):
    today = date.today()

    dept_result = await db.execute(
        select(Department).where(Department.is_active == True)
    )
    departments = dept_result.scalars().all()

    breakdown = []
    for dept in departments:
        emp_count_result = await db.execute(
            select(func.count()).select_from(Employee).where(
                and_(Employee.department_id == dept.id, Employee.is_active == True)
            )
        )
        total = emp_count_result.scalar_one()

        present_result = await db.execute(
            select(func.count()).select_from(AttendanceLog)
            .join(Employee, AttendanceLog.employee_id == Employee.id)
            .where(
                and_(
                    Employee.department_id == dept.id,
                    AttendanceLog.date == today,
                    AttendanceLog.check_in.isnot(None),
                )
            )
        )
        present = present_result.scalar_one()

        breakdown.append({
            "department": dept.name,
            "total": total,
            "present": present,
            "absent": max(0, total - present),
            "rate": round(present / total * 100, 1) if total else 0,
        })

    return breakdown


@router.get("/recent-activity")
async def recent_activity(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
):
    today = date.today()
    result = await db.execute(
        select(AttendanceLog)
        .where(AttendanceLog.date == today)
        .order_by(AttendanceLog.check_in.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return [
        {
            "employee_id": str(l.employee_id),
            "action": "check_out" if l.check_out else "check_in",
            "time": (l.check_out or l.check_in).isoformat() if (l.check_out or l.check_in) else None,
            "method": l.method,
            "is_late": l.is_late,
        }
        for l in logs
    ]
