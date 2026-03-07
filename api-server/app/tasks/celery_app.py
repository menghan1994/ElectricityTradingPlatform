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
    include=["app.tasks.import_tasks", "app.tasks.market_data_tasks", "app.tasks.prediction_tasks"],
    beat_schedule={
        "fetch-market-data-periodic": {
            "task": "app.tasks.market_data_tasks.fetch_market_data_periodic",
            "schedule": crontab(hour="7,12,17", minute=0),
        },
        "check-prediction-models-health": {
            "task": "app.tasks.prediction_tasks.check_prediction_models_health",
            "schedule": crontab(minute="*/5"),
        },
        "fetch-prediction-data-periodic": {
            "task": "app.tasks.prediction_tasks.fetch_prediction_data_for_all_models",
            "schedule": crontab(hour="6,12", minute=0),
        },
    },
)
