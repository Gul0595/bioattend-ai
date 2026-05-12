from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "bioattend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.workers.tasks.generate_attendance_report": {"queue": "reports"},
        "app.workers.tasks.send_late_notifications": {"queue": "notifications"},
        "app.workers.tasks.mark_absent_employees": {"queue": "attendance"},
    },
    beat_schedule={
        # Every day at 10 PM: mark absent employees who never checked in
        "mark-absent-daily": {
            "task": "app.workers.tasks.mark_absent_employees",
            "schedule": 79200.0,  # 22:00
        },
        # Every morning at 9 AM: send late notifications
        "late-notifications": {
            "task": "app.workers.tasks.send_late_notifications",
            "schedule": 32400.0,  # 09:00
        },
    },
)
