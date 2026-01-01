"""Worker script to run Celery workers."""

import sys
import logging
from celery_app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

if __name__ == "__main__":
    # Start worker with default queue
    app.worker_main(
        argv=[
            "worker",
            "--loglevel=info",
            "--concurrency=4",
            "-Q",
            "default,document_processing,s3_operations",
        ]
    )
