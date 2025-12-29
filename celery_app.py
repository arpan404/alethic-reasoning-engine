"""Celery app factory."""
from celery import Celery
from celery_config import *  # noqa: F401, F403

app = Celery("kie")
app.config_from_object("celery_config")
app.autodiscover_tasks(["jobs"])
