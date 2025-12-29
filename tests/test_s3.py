"""Tests for S3 operations."""

import pytest
from io import BytesIO
from unittest.mock import patch, AsyncMock, MagicMock
import asyncio

from moto import mock_aws
import boto3

from lib import s3 as s3_module


@pytest.mark.asyncio
async def test_get_file_from_s3_with_mock():
    """Test get_file_from_s3 with mocked aioboto3 client."""
    test_data = b"Hello, World!"

    mock_response = AsyncMock()
    mock_response.__getitem__.return_value.read = AsyncMock(return_value=test_data)

    mock_client = AsyncMock()
    mock_client.get_object = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("lib.s3.aioboto3.Session") as mock_session:
        mock_session.return_value.client.return_value = mock_client
        with patch.dict(
            "os.environ",
            {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_REGION": "us-east-1",
            },
        ):
            result = await s3_module.get_file_from_s3("test-bucket", "test.txt")
            assert isinstance(result, BytesIO)
            assert result.read() == test_data


@pytest.mark.asyncio
async def test_get_file_from_s3_missing_bucket():
    """Test retrieval fails with missing bucket name."""
    with patch.dict(
        "os.environ",
        {
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_REGION": "us-east-1",
        },
    ):
        with pytest.raises(AssertionError, match="Bucket name must be provided"):
            await s3_module.get_file_from_s3("", "test.txt")


@pytest.mark.asyncio
async def test_get_file_from_s3_missing_key():
    """Test retrieval fails with missing key."""
    with patch.dict(
        "os.environ",
        {
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_REGION": "us-east-1",
        },
    ):
        with pytest.raises(AssertionError, match="Key must be provided"):
            await s3_module.get_file_from_s3("test-bucket", "")


@pytest.mark.asyncio
async def test_cache_file_from_s3_with_mock(tmp_path):
    """Test cache_file_from_s3 with mocked aioboto3 client."""
    test_data = b"Test data for caching"

    mock_response = AsyncMock()
    mock_response.__getitem__.return_value.read = AsyncMock(return_value=test_data)

    mock_client = AsyncMock()
    mock_client.get_object = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    cache_path = tmp_path / "cached_file.txt"

    with patch("lib.s3.aioboto3.Session") as mock_session:
        mock_session.return_value.client.return_value = mock_client
        with patch.dict(
            "os.environ",
            {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_REGION": "us-east-1",
            },
        ):
            await s3_module.cache_file_from_s3(
                "test-bucket", "test.txt", str(cache_path)
            )
            assert cache_path.exists()
            assert cache_path.read_bytes() == test_data


@pytest.mark.asyncio
async def test_cache_file_from_s3_missing_params():
    """Test caching fails with missing parameters."""
    with patch.dict(
        "os.environ",
        {
            "AWS_ACCESS_KEY_ID": "testing",
            "AWS_SECRET_ACCESS_KEY": "testing",
            "AWS_REGION": "us-east-1",
        },
    ):
        with pytest.raises(AssertionError, match="Cache path must be provided"):
            await s3_module.cache_file_from_s3("bucket", "key", "")


@pytest.mark.asyncio
async def test_delete_file_from_s3_with_mock():
    """Test delete_file_from_s3 with mocked aioboto3 client."""
    mock_client = AsyncMock()
    mock_client.delete_object = AsyncMock(return_value={})
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("lib.s3.aioboto3.Session") as mock_session:
        mock_session.return_value.client.return_value = mock_client
        with patch.dict(
            "os.environ",
            {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_REGION": "us-east-1",
            },
        ):
            await s3_module.delete_file_from_s3("test-bucket", "test.txt")
            mock_client.delete_object.assert_called_once_with(
                Bucket="test-bucket", Key="test.txt"
            )
