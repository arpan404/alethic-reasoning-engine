"""S3 storage utilities for file operations."""

import asyncio
import aioboto3
from io import BytesIO
from os import environ
from pathlib import Path
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def _get_credentials() -> dict:
    """Lazily load AWS credentials to avoid import-time failures."""
    access_key = environ.get("AWS_ACCESS_KEY_ID")
    secret_key = environ.get("AWS_SECRET_ACCESS_KEY")
    region = environ.get("AWS_REGION")

    assert access_key, "AWS_ACCESS_KEY_ID not set in environment"
    assert secret_key, "AWS_SECRET_ACCESS_KEY not set in environment"
    assert region, "AWS_REGION not set in environment"

    return {
        "aws_access_key_id": access_key,
        "aws_secret_access_key": secret_key,
        "region_name": region,
    }


class S3Storage:
    """S3 storage handler for async operations."""
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize S3 storage.
        
        Args:
            bucket_name: S3 bucket name (uses env var if not provided)
        """
        self.bucket_name = bucket_name or environ.get("AWS_S3_BUCKET")
        if not self.bucket_name:
            raise ValueError("S3 bucket name not provided and AWS_S3_BUCKET not set")
        
        self.credentials = _get_credentials()
    
    async def upload(
        self,
        file_data: bytes | BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload file to S3.
        
        Args:
            file_data: File data (bytes or file-like object)
            key: S3 object key (path)
            content_type: MIME type of the file
            metadata: Optional metadata dictionary
            
        Returns:
            S3 object key
        """
        session = aioboto3.Session(**self.credentials)
        async with session.client("s3") as client:
            upload_args = {
                "Bucket": self.bucket_name,
                "Key": key,
            }
            
            if content_type:
                upload_args["ContentType"] = content_type
            
            if metadata:
                upload_args["Metadata"] = metadata
            
            if isinstance(file_data, bytes):
                upload_args["Body"] = file_data
            else:
                upload_args["Body"] = file_data.read()
            
            await client.put_object(**upload_args)
            
            logger.info(f"Uploaded file to S3: {self.bucket_name}/{key}")
            return key
    
    async def download(self, key: str) -> bytes:
        """
        Download file from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            File contents as bytes
        """
        session = aioboto3.Session(**self.credentials)
        async with session.client("s3") as client:
            response = await client.get_object(Bucket=self.bucket_name, Key=key)
            
            async with response["Body"] as stream:
                data = await stream.read()
            
            logger.info(f"Downloaded file from S3: {self.bucket_name}/{key}")
            return data
    
    async def delete(self, key: str) -> bool:
        """
        Delete file from S3.
        
        Args:
            key: S3 object key
            
        Returns:
            True if deleted successfully
        """
        session = aioboto3.Session(**self.credentials)
        async with session.client("s3") as client:
            await client.delete_object(Bucket=self.bucket_name, Key=key)
            
            logger.info(f"Deleted file from S3: {self.bucket_name}/{key}")
            return True
    
    async def exists(self, key: str) -> bool:
        """
        Check if file exists in S3.
        
        Args:
            key: S3 object key
            
        Returns:
            True if file exists
        """
        session = aioboto3.Session(**self.credentials)
        async with session.client("s3") as client:
            try:
                await client.head_object(Bucket=self.bucket_name, Key=key)
                return True
            except:
                return False
    
    async def get_size(self, key: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            key: S3 object key
            
        Returns:
            File size in bytes
        """
        session = aioboto3.Session(**self.credentials)
        async with session.client("s3") as client:
            response = await client.head_object(Bucket=self.bucket_name, Key=key)
            return response["ContentLength"]
    
    async def list_files(self, prefix: str = "") -> list[str]:
        """
        List files in S3 bucket with optional prefix.
        
        Args:
            prefix: Optional prefix to filter files
            
        Returns:
            List of S3 object keys
        """
        session = aioboto3.Session(**self.credentials)
        async with session.client("s3") as client:
            paginator = client.get_paginator("list_objects_v2")
            
            files = []
            async for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix
            ):
                if "Contents" in page:
                    files.extend([obj["Key"] for obj in page["Contents"]])
            
            return files
    
    async def get_presigned_url(
        self,
        key: str,
        expiration: int = 3600,
        operation: str = "get_object"
    ) -> str:
        """
        Generate presigned URL for file access.
        
        Args:
            key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            operation: S3 operation (get_object or put_object)
            
        Returns:
            Presigned URL
        """
        session = aioboto3.Session(**self.credentials)
        async with session.client("s3") as client:
            url = await client.generate_presigned_url(
                operation,
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration
            )
            
            return url
    
    async def copy(
        self,
        source_key: str,
        dest_key: str,
        source_bucket: Optional[str] = None
    ) -> str:
        """
        Copy file within S3.
        
        Args:
            source_key: Source S3 object key
            dest_key: Destination S3 object key
            source_bucket: Source bucket (uses same bucket if not provided)
            
        Returns:
            Destination S3 object key
        """
        source_bucket = source_bucket or self.bucket_name
        copy_source = {"Bucket": source_bucket, "Key": source_key}
        
        session = aioboto3.Session(**self.credentials)
        async with session.client("s3") as client:
            await client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_key
            )
            
            logger.info(f"Copied S3 file: {source_bucket}/{source_key} -> {self.bucket_name}/{dest_key}")
            return dest_key
    
    async def move(
        self,
        source_key: str,
        dest_key: str,
        source_bucket: Optional[str] = None
    ) -> str:
        """
        Move file within S3.
        
        Args:
            source_key: Source S3 object key
            dest_key: Destination S3 object key
            source_bucket: Source bucket (uses same bucket if not provided)
            
        Returns:
            Destination S3 object key
        """
        # Copy to destination
        await self.copy(source_key, dest_key, source_bucket)
        
        # Delete source
        await self.delete(source_key)
        
        return dest_key


async def download_s3_file(
    bucket_name: str,
    key: str,
    output_dir: Path,
):
    """
    Download file from S3 and save it to the specified output directory.

    Args:
        bucket_name (str): Name of the S3 bucket
        key (str): Key of the file in the S3 bucket
        output_dir (Path): Directory to save the downloaded file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / Path(key).name

    session = aioboto3.Session(**_get_credentials())
    async with session.client("s3") as client:
        response = await client.get_object(Bucket=bucket_name, Key=key)

        async with response["Body"] as stream:
            with open(file_path, "wb") as f:
                while chunk := await stream.read(8192):
                    f.write(chunk)

    return file_path


async def cache_file_from_s3(bucket_name: str, key: str, cache_path: str) -> None:
    """
    Download file from S3 and cache it locally.

    Args:
        bucket_name (str): Name of the S3 bucket
        key (str): Key of the file in the S3 bucket
        cache_path (str): Local path to cache the file
    """
    assert bucket_name, "Bucket name must be provided"
    assert key, "Key must be provided"
    assert cache_path, "Cache path must be provided"

    session = aioboto3.Session(**_get_credentials())
    async with session.client("s3") as client:
        response = await client.get_object(Bucket=bucket_name, Key=key)
        body_bytes = await response["Body"].read()

    await asyncio.to_thread(_write_bytes, cache_path, body_bytes)


def _write_bytes(path: str, data: bytes) -> None:
    with open(path, "wb") as f:
        f.write(data)


async def delete_file_from_s3(bucket_name: str, key: str) -> None:
    """
    Delete file from S3.

    Args:
        bucket_name (str): Name of the S3 bucket
        key (str): Key of the file in the S3 bucket
    """
    assert bucket_name, "Bucket name must be provided"
    assert key, "Key must be provided"

    session = aioboto3.Session(**_get_credentials())
    async with session.client("s3") as client:
        await client.delete_object(Bucket=bucket_name, Key=key)
