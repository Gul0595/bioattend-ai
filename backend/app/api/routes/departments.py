from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminOnly, CurrentUser, HROrAbove
from app.core.database import get_db
from app.models import Department, Shift
from app.schemas.schemas import (
    DepartmentCreate, DepartmentOut, DepartmentUpdate,
    ShiftCreate, ShiftOut,
)

dept_router  = APIRouter(prefix="/departments", tags=["Departments"])
shift_router = APIRouter(prefix="/shifts", tags=["Shifts"])


# ─── Departments ──────────────────────────────────────────────────────────────

@dept_router.get("/", response_model=List[DepartmentOut])
async def list_departments(db: Annotated[AsyncSession, Depends(get_db)], _: CurrentUser):
    result = await db.execute(select(Department).where(Department.is_active == True).order_by(Department.name))
    return result.scalars().all()


@dept_router.post("/", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    body: DepartmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: HROrAbove,
):
    dept = Department(**body.model_dump())
    db.add(dept)
    await db.flush()
    await db.refresh(dept)
    return dept


@dept_router.put("/{dept_id}", response_model=DepartmentOut)
async def update_department(
    dept_id: UUID,
    body: DepartmentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: HROrAbove,
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(dept, k, v)
    await db.flush()
    await db.refresh(dept)
    return dept


@dept_router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    dept_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminOnly,
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    dept.is_active = False
    await db.flush()


# ─── Shifts ───────────────────────────────────────────────────────────────────

@shift_router.get("/", response_model=List[ShiftOut])
async def list_shifts(db: Annotated[AsyncSession, Depends(get_db)], _: CurrentUser):
    result = await db.execute(select(Shift).where(Shift.is_active == True).order_by(Shift.name))
    return result.scalars().all()


@shift_router.post("/", response_model=ShiftOut, status_code=status.HTTP_201_CREATED)
async def create_shift(
    body: ShiftCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: HROrAbove,
):
    shift = Shift(**body.model_dump())
    db.add(shift)
    await db.flush()
    await db.refresh(shift)
    return shift


@shift_router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shift(
    shift_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminOnly,
):
    result = await db.execute(select(Shift).where(Shift.id == shift_id))
    shift = result.scalar_one_or_none()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    shift.is_active = False
    await db.flush()
