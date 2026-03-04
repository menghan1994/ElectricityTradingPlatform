from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "electricity_trading",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    include=["app.tasks.import_tasks", "app.tasks.market_data_tasks"],
    beat_schedule={
        "fetch-market-data-periodic": {
            "task": "app.tasks.market_data_tasks.fetch_market_data_periodic",
            "schedule": crontab(hour="7,12,17", minute=0),
        },
    },
)
