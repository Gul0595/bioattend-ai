"""Tests for the attendance service and endpoints."""
import pytest
from datetime import date, datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Employee, Shift
from app.services.attendance_service import record_check_in, record_check_out, get_today_summary
import time


@pytest.mark.asyncio
async def test_check_in_creates_log(db: AsyncSession):
    # Create a shift
    shift = Shift(
        name="Test Shift",
        start_time=datetime.now(timezone.utc).replace(hour=8, minute=0).time(),
        end_time=datetime.now(timezone.utc).replace(hour=17, minute=0).time(),
        grace_minutes=15,
        overtime_after_minutes=30,
    )
    db.add(shift)

    emp = Employee(
        employee_id=f"SRV{int(time.time())}",
        first_name="Service",
        last_name="Test",
        email=f"service_{int(time.time())}@test.com",
        shift=shift,
    )
    db.add(emp)
    await db.flush()

    log = await record_check_in(db, emp, method="manual")
    assert log is not None
    assert log.check_in is not None
    assert log.employee_id == emp.id
    assert log.method == "manual"
    assert log.date == date.today()


@pytest.mark.asyncio
async def test_check_out_after_check_in(db: AsyncSession):
    shift = Shift(
        name="CO Shift",
        start_time=datetime.now(timezone.utc).replace(hour=8, minute=0).time(),
        end_time=datetime.now(timezone.utc).replace(hour=17, minute=0).time(),
        grace_minutes=15,
        overtime_after_minutes=30,
    )
    db.add(shift)

    emp = Employee(
        employee_id=f"CO{int(time.time())}",
        first_name="Checkout",
        last_name="Test",
        email=f"co_{int(time.time())}@test.com",
        shift=shift,
    )
    db.add(emp)
    await db.flush()

    await record_check_in(db, emp, method="manual")
    log = await record_check_out(db, emp, method="manual")

    assert log.check_out is not None
    assert log.work_hours >= 0


@pytest.mark.asyncio
async def test_today_summary(db: AsyncSession):
    summary = await get_today_summary(db)
    assert "total_employees" in summary
    assert "present_today" in summary
    assert "absent_today" in summary
    assert "attendance_rate" in summary


@pytest.mark.asyncio
async def test_attendance_today_endpoint(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/attendance/today", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_attendance_today_summary_endpoint(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/attendance/today-summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_employees" in data
    assert "attendance_rate" in data


@pytest.mark.asyncio
async def test_manual_attendance_endpoint(client: AsyncClient, auth_headers: dict):
    # Create employee first
    emp_payload = {
        "employee_id": f"MAN{int(time.time())}",
        "first_name": "Manual",
        "last_name": "Test",
        "email": f"manual_{int(time.time())}@bioattend.app",
    }
    emp_resp = await client.post("/api/v1/employees", json=emp_payload, headers=auth_headers)
    emp_id = emp_resp.json()["id"]

    today = date.today().isoformat()
    resp = await client.post("/api/v1/attendance/manual", json={
        "employee_id": emp_id,
        "date": today,
        "status": "present",
        "notes": "Manual test entry",
    }, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "present"
