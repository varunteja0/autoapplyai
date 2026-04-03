from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "autoapplyai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=3,

    # Rate limiting
    task_default_rate_limit="10/m",

    # Result expiration (24 hours)
    result_expires=86400,

    # Concurrency
    worker_concurrency=4,

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
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.workers.tasks"])
