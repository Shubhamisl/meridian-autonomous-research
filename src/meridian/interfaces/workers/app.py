import os
from celery import Celery

# Using SQLite for completely free, zero-dependency local broker/backend instead of Docker+Redis
broker_url = os.environ.get("CELERY_BROKER_URL", "sqla+sqlite:///celery_broker.db")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "db+sqlite:///celery_results.db")

celery_app = Celery(
    "meridian_worker",
    broker=broker_url,
    backend=backend_url,
    include=["src.meridian.interfaces.workers.tasks"]
)
