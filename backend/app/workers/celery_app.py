from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "autoapplyai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.application_tasks",
        "app.workers.tasks.scraping_tasks",
        "app.workers.tasks.ai_tasks",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task execution — optimized for high throughput
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=2,

    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=3,

    # Rate limiting — 10K apps/day ≈ ~7/min sustained, burst higher
    task_default_rate_limit="20/m",

    # Result expiration (24 hours)
    result_expires=86400,

    # Concurrency (overridden per worker via CLI)
    worker_concurrency=8,

    # Max memory per child — restart children to avoid browser memory leaks
    worker_max_memory_per_child=512_000,  # 512MB

    # Task routes for different queues
    task_routes={
        "app.workers.tasks.application_tasks.*": {"queue": "applications"},
        "app.workers.tasks.scraping_tasks.*": {"queue": "scraping"},
        "app.workers.tasks.ai_tasks.*": {"queue": "ai"},
    },

    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-stale-applications": {
            "task": "app.workers.tasks.application_tasks.cleanup_stale_applications",
            "schedule": 3600.0,  # Every hour
        },
        "auto-apply-pending-jobs": {
            "task": "app.workers.tasks.application_tasks.auto_apply_all_pending",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        "reset-daily-counters": {
            "task": "app.workers.tasks.application_tasks.reset_daily_counters",
            "schedule": crontab(hour=0, minute=0),  # Midnight UTC
        },
    },
)
