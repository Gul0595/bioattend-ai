from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import AdminOnly, CurrentUser, HROrAbove
from app.core.database import get_db
from app.core.security import hash_password
from app.models import Employee, User, UserRole
from app.schemas.schemas import EmployeeCreate, EmployeeOut, EmployeeUpdate
from app.services import face_service, storage_service

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("/", response_model=List[EmployeeOut])
async def list_employees(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
    department_id: Optional[UUID] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = True,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    stmt = select(Employee)

    if is_active is not None:
        stmt = stmt.where(Employee.is_active == is_active)

    if department_id:
        stmt = stmt.where(Employee.department_id == department_id)

    if search:
        q = f"%{search}%"

        from sqlalchemy import or_

        stmt = stmt.where(
            or_(
                Employee.first_name.ilike(q),
                Employee.last_name.ilike(q),
                Employee.employee_id.ilike(q),
                Employee.email.ilike(q),
            )
        )

    stmt = (
        stmt.offset((page - 1) * per_page)
        .limit(per_page)
        .order_by(Employee.first_name)
    )

    result = await db.execute(stmt)

    return result.scalars().all()


@router.post("/", response_model=EmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_employee(
    body: EmployeeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: HROrAbove,
):
    existing = await db.execute(
        select(Employee).where(
            (Employee.employee_id == body.employee_id)
            | (Employee.email == body.email)
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Employee ID or email already exists"
        )

    user = None

    if body.create_user and body.password:
        user = User(
            email=body.email,
            hashed_password=hash_password(body.password),
            full_name=f"{body.first_name} {body.last_name}",
            role=UserRole(body.role),
        )

        db.add(user)

        await db.flush()

    emp = Employee(
        employee_id=body.employee_id,
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        designation=body.designation,
        department_id=body.department_id,
        shift_id=body.shift_id,
        date_of_joining=body.date_of_joining,
        date_of_birth=body.date_of_birth,
        fingerprint_id=body.fingerprint_id,
        user_id=user.id if user else None,
    )

    db.add(emp)

    await db.commit()
    await db.refresh(emp)

    # Initialize leave balances
    from app.api.routes.leaves import _ensure_balances
    await _ensure_balances(
        db,
        emp.id,
        __import__("datetime").date.today().year
    )

    # Welcome email
    if emp.email:
        import asyncio
        from app.services.notification_service import send_welcome_email

        asyncio.create_task(
            send_welcome_email(
                email=emp.email,
                name=emp.full_name,
                employee_id=emp.employee_id,
                temp_password=body.password if body.create_user else None,
            )
        )

    return emp


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(
    employee_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: CurrentUser,
):
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )

    emp = result.scalar_one_or_none()

    if not emp:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    return emp


@router.put("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: UUID,
    body: EmployeeUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: HROrAbove,
):
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )

    emp = result.scalar_one_or_none()

    if not emp:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(emp, field, value)

    await db.commit()
    await db.refresh(emp)

    return emp


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_employee(
    employee_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: AdminOnly,
):
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )

    emp = result.scalar_one_or_none()

    if not emp:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    emp.is_active = False

    await db.commit()


@router.post("/{employee_id}/enroll-face", response_model=dict)
async def enroll_face(
    employee_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: HROrAbove,
    file: UploadFile = File(...),
):
    # Find employee
    result = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )

    emp = result.scalar_one_or_none()

    if not emp:
        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    # Read uploaded image
    image_bytes = await file.read()

    # Validate image size
    if len(image_bytes) > (settings_face_max_mb() * 1024 * 1024):
        raise HTTPException(
            status_code=413,
            detail="Image too large"
        )

    # Generate face embedding
    embedding = face_service.extract_embedding(image_bytes)

    if embedding is None:
        raise HTTPException(
            status_code=422,
            detail="No face detected in the image. Please use a clear frontal photo."
        )

    from datetime import datetime, timezone
    from app.services.encryption_service import encrypt_embedding
    import asyncio

    # Upload image
    image_url = storage_service.upload_image(
        image_bytes,
        folder="faces"
    )

    # Encrypt embedding
    encrypted_embedding = encrypt_embedding(embedding)

    # Save biometric info
    emp.face_embedding = encrypted_embedding
    emp.face_image_url = image_url
    emp.biometric_enrolled = True
    emp.biometric_enrolled_at = datetime.now(timezone.utc)

    # Commit changes
    await db.commit()
    await db.refresh(emp)

    # Notify employee
    from app.services.notification_service import notify_face_enrolled

    asyncio.create_task(
        notify_face_enrolled(
            emp.email,
            emp.full_name
        )
    )

    return {
        "success": True,
        "message": "Face enrolled and encrypted successfully",
        "employee_id": str(emp.id),
        "employee_name": emp.full_name,
        "image_url": image_url,
    }


def settings_face_max_mb() -> int:
    from app.core.config import settings
    return settings.MAX_FACE_IMAGE_SIZE_MB