"""
Celery application + beat schedule configuration.
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "callflow",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.call_tasks",
        "app.tasks.reminder_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Beat schedule — reminder sweeps every 15 minutes
    beat_schedule={
        "send-reminders-every-15-min": {
            "task": "app.tasks.reminder_tasks.send_due_reminders",
            "schedule": crontab(minute="*/15"),
        },
        "retry-callbacks-every-hour": {
            "task": "app.tasks.call_tasks.retry_scheduled_callbacks",
            "schedule": crontab(minute=0),
        },
    },
)
