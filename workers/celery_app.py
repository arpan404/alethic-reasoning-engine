"""Celery app factory."""

from celery import Celery
from .celery_config import *  # noqa: F401, F403

celery_app = Celery("kie")
celery_app.config_from_object("workers.celery_config")
celery_app.autodiscover_tasks(["workers.tasks"])
