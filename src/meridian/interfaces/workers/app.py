import os

try:
    from celery import Celery
except ModuleNotFoundError:
    Celery = None


class _CeleryTaskStub:
    def __init__(self, func):
        self._func = func

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def delay(self, *args, **kwargs):
        raise RuntimeError("Celery is not available in this environment")


class _CeleryAppStub:
    def task(self, **_kwargs):
        def decorator(func):
            return _CeleryTaskStub(func)

        return decorator

# Using SQLite for completely free, zero-dependency local broker/backend instead of Docker+Redis
broker_url = os.environ.get("CELERY_BROKER_URL", "sqla+sqlite:///celery_broker.db")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "db+sqlite:///celery_results.db")

if Celery is None:
    celery_app = _CeleryAppStub()
else:
    celery_app = Celery(
        "meridian_worker",
        broker=broker_url,
        backend=backend_url,
        include=["src.meridian.interfaces.workers.tasks"]
    )
