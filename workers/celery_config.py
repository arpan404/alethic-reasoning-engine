"""Celery configuration for async task processing."""

from kombu import Exchange, Queue
from os import environ

# Broker configuration (Redis)
REDIS_HOST = environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(environ.get("REDIS_PORT", 6379))
REDIS_DB = int(environ.get("REDIS_DB", 0))

broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB + 1}"

# Task routing and serialization
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"
timezone = "UTC"
enable_utc = True

# Task execution settings
task_track_started = True
task_time_limit = 30 * 60  # 30 minutes hard limit
task_soft_time_limit = 25 * 60  # 25 minutes soft limit

# Worker settings
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000

# Queue configuration with routing
default_exchange = Exchange("kie", type="direct")
default_queue_name = "default"
task_queues = (
    Queue("default", exchange=default_exchange, routing_key="default"),
    Queue("document_processing", exchange=default_exchange, routing_key="documents"),
    Queue("s3_operations", exchange=default_exchange, routing_key="s3"),
)

# Task routing
task_routes = {
    "jobs.documents.*": {"queue": "document_processing"},
    "jobs.s3.*": {"queue": "s3_operations"},
}

# Result backend settings
result_expires = 3600  # Results expire after 1 hour
