from celery import Celery

from app.core.redis_sonfig import get_redis_url


def make_celery(app_name: str = "ticket_fast_api") -> Celery:
    redis_url = get_redis_url()
    celery = Celery(app_name, broker=redis_url, backend=redis_url)
    celery.conf.task_serializer = "json"
    celery.conf.result_serializer = "json"
    celery.conf.accept_content = ["json"]
    celery.conf.result_persistent = False
    celery.conf.task_track_started = True
    return celery


celery_app = make_celery()
