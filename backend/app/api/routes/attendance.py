from datetime import date
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import CurrentUser, HROrAbove, get_current_user
from app.core.database import get_db
from app.models import AttendanceLog, AttendanceStatus, Employee, User
from app.schemas.schemas import (
    AttendanceOut, AttendanceSummary,
    FaceCheckInRequest, ManualAttendanceRequest,
)
from app.services import face_service, storage_service
from app.services.liveness_service import check_liveness
from app.services.attendance_service import (
    get_monthly_summary, get_today_summary,
    record_check_in, record_check_out,
)
from app.services.encryption_service import decrypt_embedding

router = APIRouter(prefix="/attendance", tags=["Attendance"])


# ─── Kiosk: Base64 face check-in/out (combined action) ────────────────────────

@router.post("/face-checkin", response_model=dict)
async def face_checkin_base64(
    payload: FaceCheckInRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Primary kiosk endpoint. Accepts base64 image, auto-identifies employee,
    and toggles check-in / check-out intelligently.
    No auth required — called by edge device.
    """

    image_bytes = storage_service.base64_to_bytes(payload.image_base64)

    # ── LIVENESS CHECK ────────────────────────────────────────────────────────
    liveness = check_liveness(image_bytes)

    if not liveness.is_live:
        return {
            "success": False,
            "liveness_failed": True,
            "message": "Liveness check failed — please show your REAL FACE to the camera.",
            "liveness_confidence": liveness.confidence,
            "reason": liveness.reason,
        }

    # ── GEOFENCE CHECK ────────────────────────────────────────────────────────
    from app.services.geofence_service import check_geofence

    geo = await check_geofence(
        db,
        client_lat=payload.latitude,
        client_lon=payload.longitude,
        is_kiosk=payload.is_kiosk,
    )

    if not geo.allowed:
        return {
            "success": False,
            "geofence_failed": True,
            "message": geo.reason,
            "distance_m": geo.distance_m,
        }

    # Build employee gallery
    result = await db.execute(
        select(Employee).where(
            Employee.is_active == True,
            Employee.face_embedding.isnot(None),
        )
    )

    employees = result.scalars().all()

    gallery = [
        {
            "employee_id": emp.id,
            "embedding": decrypt_embedding(emp.face_embedding),
        }
        for emp in employees
    ]

    matched_id, confidence = face_service.match_face(
        image_bytes,
        gallery,
    )

    if matched_id is None:
        return {
            "success": False,
            "message": "Face not recognized. Please contact HR.",
            "confidence": confidence,
        }

    emp_result = await db.execute(
        select(Employee).where(Employee.id == matched_id)
    )

    emp = emp_result.scalar_one()

    today = date.today()

    log_result = await db.execute(
        select(AttendanceLog).where(
            and_(
                AttendanceLog.employee_id == emp.id,
                AttendanceLog.date == today,
            )
        )
    )

    existing_log = log_result.scalar_one_or_none()

    if existing_log and existing_log.check_in and existing_log.check_out:
        return {
            "success": False,
            "message": "Already completed attendance for today.",
            "employee": emp.full_name,
        }

    image_url = storage_service.upload_image(
        image_bytes,
        folder="checkins"
    )

    # AUTO CHECK-OUT
    if existing_log and existing_log.check_in and not existing_log.check_out:

        log = await record_check_out(
            db,
            emp,
            method="face",
            location=payload.location,
            device_id=payload.device_id,
        )

        return {
            "success": True,
            "action": "check_out",
            "employee_id": emp.employee_id,
            "employee_name": emp.full_name,
            "time": log.check_out.isoformat(),
            "work_hours": log.work_hours,
            "confidence": confidence,
        }

    # CHECK-IN
    else:

        log = await record_check_in(
            db,
            emp,
            method="face",
            image_url=image_url,
            face_score=confidence,
            location=payload.location,
            device_id=payload.device_id,
        )

        # Notify manager if late
        if (
            log.is_late
            and emp.department
            and emp.department.manager
            and emp.department.manager.user
        ):

            import asyncio
            from app.services.notification_service import notify_late_checkin

            shift_name = emp.shift.name if emp.shift else "General"

            asyncio.create_task(
                notify_late_checkin(
                    manager_email=emp.department.manager.user.email,
                    employee_name=emp.full_name,
                    employee_id=emp.employee_id,
                    check_in_time=log.check_in,
                    late_minutes=log.late_minutes,
                    shift_name=shift_name,
                )
            )

        return {
            "success": True,
            "action": "check_in",
            "employee_id": emp.employee_id,
            "employee_name": emp.full_name,
            "time": log.check_in.isoformat(),
            "is_late": log.is_late,
            "late_minutes": log.late_minutes,
            "confidence": confidence,
            "liveness_confidence": liveness.confidence,
        }


# ─── File upload face check-in ────────────────────────────────────────────────

@router.post("/face-checkin-upload", response_model=dict)
async def face_checkin_upload(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    device_id: Optional[str] = Query(None),
    action: str = Query("auto", description="auto | checkin | checkout"),
):
    """
    Alternative kiosk endpoint using multipart/form-data upload.
    """

    image_bytes = await file.read()

    # ── LIVENESS CHECK ────────────────────────────────────────────────────────
    liveness = check_liveness(image_bytes)

    if not liveness.is_live:
        raise HTTPException(
            status_code=400,
            detail=f"Liveness failed: {liveness.reason}"
        )

    # Load employees
    result = await db.execute(
        select(Employee).where(
            Employee.is_active == True,
            Employee.face_embedding.isnot(None),
        )
    )

    employees = result.scalars().all()

    gallery = [
        {
            "employee_id": emp.id,
            "embedding": decrypt_embedding(emp.face_embedding),
        }
        for emp in employees
    ]

    matched_id, confidence = face_service.match_face(
        image_bytes,
        gallery,
    )

    if matched_id is None:
        raise HTTPException(
            status_code=404,
            detail="No matching employee found"
        )

    emp_result = await db.execute(
        select(Employee).where(Employee.id == matched_id)
    )

    emp = emp_result.scalar_one()

    today = date.today()

    log_result = await db.execute(
        select(AttendanceLog).where(
            and_(
                AttendanceLog.employee_id == emp.id,
                AttendanceLog.date == today,
            )
        )
    )

    existing = log_result.scalar_one_or_none()

    # CHECK-OUT
    if (
        action == "checkout"
        or (
            action == "auto"
            and existing
            and existing.check_in
            and not existing.check_out
        )
    ):

        log = await record_check_out(
            db,
            emp,
            method="face",
            device_id=device_id,
        )

        return {
            "matched": True,
            "employee_id": emp.employee_id,
            "check_out": log.check_out.isoformat(),
            "work_hours": log.work_hours,
            "confidence": confidence,
        }

    # CHECK-IN
    else:

        image_url = storage_service.upload_image(
            image_bytes,
            folder="checkins"
        )

        log = await record_check_in(
            db,
            emp,
            method="face",
            image_url=image_url,
            face_score=confidence,
            device_id=device_id,
        )

        return {
            "matched": True,
            "employee_id": emp.employee_id,
            "check_in": log.check_in.isoformat(),
            "is_late": log.is_late,
            "late_minutes": log.late_minutes,
            "confidence": confidence,
        }