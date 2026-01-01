"""Tests for document parsing utilities."""

import pytest
from io import BytesIO
from docx import Document

from lib import document_parser as dp_module
from tests.conftest import _create_minimal_pdf, _create_test_docx


@pytest.mark.asyncio
async def test_extract_text_from_pdf_stream_with_simple_pdf():
    """Test PDF text extraction from a simple BytesIO stream."""
    pdf_data = _create_minimal_pdf("Hello World")
    stream = BytesIO(pdf_data)

    result = await dp_module.extract_text_from_pdf_stream(stream)
    assert isinstance(result, str)
    assert "Hello" in result or len(result) > 0


@pytest.mark.asyncio
async def test_extract_text_from_pdf_stream_with_bytes():
    """Test PDF extraction accepts raw bytes."""
    pdf_data = _create_minimal_pdf("Test PDF")
    result = await dp_module.extract_text_from_pdf_stream(pdf_data)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_extract_text_from_pdf_stream_empty_pdf():
    """Test extraction from empty PDF returns empty string."""
    pdf_data = _create_minimal_pdf("")
    result = await dp_module.extract_text_from_pdf_stream(pdf_data)
    assert result == ""


@pytest.mark.asyncio
async def test_extract_text_from_pdf_stream_closed_stream():
    """Test extraction fails with closed stream."""
    stream = BytesIO(b"test")
    stream.close()

    with pytest.raises(ValueError, match="file_stream is closed"):
        await dp_module.extract_text_from_pdf_stream(stream)


@pytest.mark.asyncio
async def test_extract_text_from_docx_stream_simple():
    """Test DOCX text extraction with simple paragraphs."""
    docx_stream = _create_test_docx("Hello", "World", paragraphs_only=True)

    result = await dp_module.extract_text_from_docx_stream(docx_stream)
    assert "Hello" in result
    assert "World" in result


@pytest.mark.asyncio
async def test_extract_text_from_docx_stream_with_tables():
    """Test DOCX extraction includes table cells."""
    docx_stream = _create_test_docx("Paragraph", "Table Cell", paragraphs_only=False)

    result = await dp_module.extract_text_from_docx_stream(docx_stream)
    assert "Paragraph" in result
    assert "Table" in result or "Cell" in result


@pytest.mark.asyncio
async def test_extract_text_from_docx_stream_with_bytes():
    """Test DOCX extraction accepts raw bytes."""
    docx_stream = _create_test_docx("Test", "Data", paragraphs_only=True)
    docx_bytes = docx_stream.getvalue()

    result = await dp_module.extract_text_from_docx_stream(docx_bytes)
    assert isinstance(result, str)
    assert "Test" in result


@pytest.mark.asyncio
async def test_extract_text_from_docx_stream_closed_stream():
    """Test extraction fails with closed stream."""
    stream = BytesIO(b"test")
    stream.close()

    with pytest.raises(ValueError, match="file_stream is closed"):
        await dp_module.extract_text_from_docx_stream(stream)


@pytest.mark.asyncio
async def test_extract_text_from_docx_empty():
    """Test extraction from empty DOCX returns empty string."""
    # Create a minimal valid DOCX file
    stream = BytesIO()
    doc = Document()
    doc.save(stream)
    stream.seek(0)

    result = await dp_module.extract_text_from_docx_stream(stream)
    assert result == ""


def test_normalize_text_basic():
    """Test whitespace normalization."""
    chunks = ["Hello", "  World  ", "Test"]
    result = dp_module._normalize_text(chunks)
    assert result == "Hello\nWorld\nTest"


def test_normalize_text_collapse_blank_lines():
    """Test that multiple blank lines are collapsed."""
    chunks = ["Line1", "", "", "", "Line2"]
    result = dp_module._normalize_text(chunks)
    assert "\n\n\n" not in result
    assert "Line1" in result
    assert "Line2" in result


def test_normalize_text_empty():
    """Test normalization with empty input."""
    result = dp_module._normalize_text([])
    assert result == ""


def test_prepare_stream_with_bytes():
    """Test stream preparation converts bytes to BytesIO."""
    data = b"test data"
    stream = dp_module._prepare_stream(data)
    assert isinstance(stream, BytesIO)
    assert stream.tell() == 0
    assert stream.read() == data


def test_prepare_stream_with_bytearray():
    """Test stream preparation handles bytearray."""
    data = bytearray(b"test data")
    stream = dp_module._prepare_stream(data)
    assert isinstance(stream, BytesIO)
    assert stream.tell() == 0


def test_prepare_stream_with_bytesio():
    """Test stream preparation leaves BytesIO as-is."""
    original = BytesIO(b"test")
    original.seek(5)
    stream = dp_module._prepare_stream(original)
    assert stream is original
    assert stream.tell() == 0


def test_prepare_stream_closed_stream():
    """Test stream preparation raises on closed stream."""
    stream = BytesIO(b"test")
    stream.close()
    with pytest.raises(ValueError, match="file_stream is closed"):
        dp_module._prepare_stream(stream)


def test_extract_images_from_pdf_no_images(temp_output_dir):
    """Test image extraction from PDF with no images."""
    pdf_data = _create_minimal_pdf("Text only PDF")
    stream = BytesIO(pdf_data)

    result = dp_module.extract_images_from_pdf(stream, output_dir=temp_output_dir)
    assert isinstance(result, list)
    assert len(result) == 0


def test_extract_images_from_pdf_creates_output_dir(temp_output_dir):
    """Test that output directory is created if it doesn't exist."""
    import os
    from pathlib import Path

    pdf_data = _create_minimal_pdf("Test PDF")
    stream = BytesIO(pdf_data)

    # Use a subdirectory that doesn't exist yet
    output_path = Path(temp_output_dir) / "new_subdir"
    assert not output_path.exists()

    result = dp_module.extract_images_from_pdf(stream, output_dir=str(output_path))

    # Directory should be created even if no images were extracted
    assert output_path.exists()
    assert output_path.is_dir()


def test_extract_images_from_pdf_default_dir():
    """Test that default output directory is used when not specified."""
    import shutil
    from pathlib import Path

    pdf_data = _create_minimal_pdf("Test PDF")
    stream = BytesIO(pdf_data)

    try:
        result = dp_module.extract_images_from_pdf(stream)
        assert isinstance(result, list)
        # Default directory should be created
        assert Path("extracted_images").exists()
    finally:
        # Cleanup default directory if it was created
        if Path("extracted_images").exists():
            shutil.rmtree("extracted_images")
