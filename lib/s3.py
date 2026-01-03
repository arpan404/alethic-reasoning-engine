import asyncio
import aioboto3
from io import BytesIO
from os import environ


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
