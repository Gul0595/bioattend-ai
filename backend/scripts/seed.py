"""
BioAttend Ultimate — Seed Script
Creates an admin user, departments, shifts, and sample employees.

Usage:
    cd backend
    python -m scripts.seed
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.security import hash_password
from app.models import Department, Employee, Shift, User, UserRole
from datetime import date, time


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        from app.core.database import Base
        from app.models import *  # noqa
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        # ── Admin user ────────────────────────────────────────────────────────
        from sqlalchemy import select
        existing = await db.execute(select(User).where(User.email == "admin@bioattend.app"))
        if not existing.scalar_one_or_none():
            admin = User(
                email="admin@bioattend.app",
                hashed_password=hash_password("Admin@1234"),
                full_name="System Administrator",
                role=UserRole.admin,
                is_active=True,
                is_verified=True,
            )
            db.add(admin)
            await db.flush()
            print(f"✅ Admin created: admin@bioattend.app / Admin@1234")
        else:
            print("ℹ️  Admin already exists")

        # ── Departments ───────────────────────────────────────────────────────
        dept_data = [
            {"name": "Engineering",     "code": "ENG",  "description": "Software & hardware engineering"},
            {"name": "Human Resources", "code": "HR",   "description": "People operations"},
            {"name": "Finance",         "code": "FIN",  "description": "Accounts and finance"},
            {"name": "Operations",      "code": "OPS",  "description": "Business operations"},
            {"name": "Sales",           "code": "SALES","description": "Sales and business development"},
        ]
        depts = {}
        for d in dept_data:
            existing = await db.execute(select(Department).where(Department.code == d["code"]))
            dept = existing.scalar_one_or_none()
            if not dept:
                dept = Department(**d)
                db.add(dept)
                await db.flush()
                print(f"✅ Department: {d['name']}")
            depts[d["code"]] = dept

        # ── Shifts ────────────────────────────────────────────────────────────
        shift_data = [
            {"name": "Morning",   "start_time": time(8, 0),  "end_time": time(17, 0), "grace_minutes": 15, "overtime_after_minutes": 30},
            {"name": "General",   "start_time": time(9, 0),  "end_time": time(18, 0), "grace_minutes": 15, "overtime_after_minutes": 30},
            {"name": "Afternoon", "start_time": time(14, 0), "end_time": time(23, 0), "grace_minutes": 15, "overtime_after_minutes": 30},
            {"name": "Night",     "start_time": time(22, 0), "end_time": time(6, 0),  "grace_minutes": 15, "overtime_after_minutes": 30},
        ]
        shifts = {}
        for s in shift_data:
            existing = await db.execute(select(Shift).where(Shift.name == s["name"]))
            shift = existing.scalar_one_or_none()
            if not shift:
                shift = Shift(**s)
                db.add(shift)
                await db.flush()
                print(f"✅ Shift: {s['name']}")
            shifts[s["name"]] = shift

        # ── Sample employees ──────────────────────────────────────────────────
        employees_data = [
            {"employee_id": "EMP001", "first_name": "Aisha",  "last_name": "Sharma",   "email": "aisha@bioattend.app",  "designation": "Senior Engineer",   "dept": "ENG",  "shift": "General"},
            {"employee_id": "EMP002", "first_name": "Rohan",  "last_name": "Verma",    "email": "rohan@bioattend.app",  "designation": "HR Manager",        "dept": "HR",   "shift": "General"},
            {"employee_id": "EMP003", "first_name": "Priya",  "last_name": "Kapoor",   "email": "priya@bioattend.app",  "designation": "Finance Analyst",   "dept": "FIN",  "shift": "Morning"},
            {"employee_id": "EMP004", "first_name": "Karan",  "last_name": "Mehta",    "email": "karan@bioattend.app",  "designation": "DevOps Engineer",   "dept": "ENG",  "shift": "Morning"},
            {"employee_id": "EMP005", "first_name": "Nidhi",  "last_name": "Singh",    "email": "nidhi@bioattend.app",  "designation": "Sales Executive",   "dept": "SALES","shift": "General"},
        ]

        for e in employees_data:
            existing = await db.execute(select(Employee).where(Employee.employee_id == e["employee_id"]))
            if not existing.scalar_one_or_none():
                emp = Employee(
                    employee_id=e["employee_id"],
                    first_name=e["first_name"],
                    last_name=e["last_name"],
                    email=e["email"],
                    designation=e["designation"],
                    department_id=depts[e["dept"]].id,
                    shift_id=shifts[e["shift"]].id,
                    date_of_joining=date(2023, 1, 15),
                    is_active=True,
                )
                db.add(emp)
                print(f"✅ Employee: {e['first_name']} {e['last_name']}")

        await db.commit()
        print("\n🎉 Seed complete!")
        print("   Login: admin@bioattend.app / Admin@1234")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
