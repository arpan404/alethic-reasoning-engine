"""S3 operation tasks."""
from celery import shared_task
from io import BytesIO
import asyncio
import logging

from lib import s3

logger = logging.getLogger(__name__)


@shared_task(name="jobs.s3.download_file", bind=True, max_retries=3)
def download_file(self, bucket_name: str, key: str) -> dict:
    """
    Download file from S3 asynchronously.

    Args:
        bucket_name (str): S3 bucket name
        key (str): S3 object key

    Returns:
        dict: Result with status and file metadata
    """
    try:
        logger.info(f"Downloading {key} from {bucket_name}")
        
        # Run async function in sync context
        result = asyncio.run(s3.get_file_from_s3(bucket_name, key))
        file_bytes = result.getvalue()
        
        logger.info(f"Successfully downloaded {key} ({len(file_bytes)} bytes)")
        return {
            "status": "success",
            "bucket": bucket_name,
            "key": key,
            "size_bytes": len(file_bytes),
        }
    except Exception as exc:
        logger.error(f"Error downloading {key}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@shared_task(name="jobs.s3.cache_file", bind=True, max_retries=3)
def cache_file(self, bucket_name: str, key: str, cache_path: str) -> dict:
    """
    Download and cache file from S3.

    Args:
        bucket_name (str): S3 bucket name
        key (str): S3 object key
        cache_path (str): Local cache path

    Returns:
        dict: Result with status and file info
    """
    try:
        logger.info(f"Caching {key} to {cache_path}")
        
        # Run async function in sync context
        asyncio.run(s3.cache_file_from_s3(bucket_name, key, cache_path))
        
        logger.info(f"Successfully cached {key} to {cache_path}")
        return {
            "status": "success",
            "bucket": bucket_name,
            "key": key,
            "cache_path": cache_path,
        }
    except Exception as exc:
        logger.error(f"Error caching {key}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@shared_task(name="jobs.s3.delete_file", bind=True, max_retries=3)
def delete_file(self, bucket_name: str, key: str) -> dict:
    """
    Delete file from S3.

    Args:
        bucket_name (str): S3 bucket name
        key (str): S3 object key

    Returns:
        dict: Result with status
    """
    try:
        logger.info(f"Deleting {key} from {bucket_name}")
        
        # Run async function in sync context
        asyncio.run(s3.delete_file_from_s3(bucket_name, key))
        
        logger.info(f"Successfully deleted {key}")
        return {
            "status": "success",
            "bucket": bucket_name,
            "key": key,
        }
    except Exception as exc:
        logger.error(f"Error deleting {key}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
