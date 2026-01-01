"""Document processing tasks."""

from io import BytesIO
from pathlib import Path
from celery import shared_task
import logging

from lib import document_parser

logger = logging.getLogger(__name__)


@shared_task(name="jobs.documents.extract_pdf_text", bind=True, max_retries=3)
def extract_pdf_text(self, file_data: bytes, file_name: str = "document.pdf") -> dict:
    """
    Extract text from a PDF file.

    Args:
        file_data (bytes): Raw PDF file data
        file_name (str): Optional file name for logging

    Returns:
        dict: Extraction result with status and extracted text
    """
    try:
        logger.info(f"Starting PDF extraction for {file_name}")
        stream = BytesIO(file_data)

        # Use the sync version since Celery runs in separate process
        text = document_parser._extract_pdf_text_sync(stream)

        logger.info(f"Successfully extracted text from {file_name}")
        return {
            "status": "success",
            "file_name": file_name,
            "text": text,
            "char_count": len(text),
        }
    except Exception as exc:
        logger.error(f"Error extracting PDF {file_name}: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2**self.request.retries)


@shared_task(name="jobs.documents.extract_docx_text", bind=True, max_retries=3)
def extract_docx_text(self, file_data: bytes, file_name: str = "document.docx") -> dict:
    """
    Extract text from a DOCX file.

    Args:
        file_data (bytes): Raw DOCX file data
        file_name (str): Optional file name for logging

    Returns:
        dict: Extraction result with status and extracted text
    """
    try:
        logger.info(f"Starting DOCX extraction for {file_name}")
        stream = BytesIO(file_data)

        # Use the sync version since Celery runs in separate process
        text = document_parser._extract_docx_text_sync(stream)

        logger.info(f"Successfully extracted text from {file_name}")
        return {
            "status": "success",
            "file_name": file_name,
            "text": text,
            "char_count": len(text),
        }
    except Exception as exc:
        logger.error(f"Error extracting DOCX {file_name}: {exc}")
        raise self.retry(exc=exc, countdown=2**self.request.retries)


@shared_task(name="jobs.documents.convert_pdf_to_images", bind=True, max_retries=3)
def convert_pdf_to_images(self, file_path: Path) -> dict:
    """
    Convert a PDF document to images.

    Args:
        file_path (Path): Path to the PDF document

    Returns:
        dict: Conversion result with status and image paths
    """
    try:
        logger.info(f"Starting image conversion for {file_path}")
        match file_path.suffix:
            case ".pdf":
                images = document_parser.extract_images_from_pdf(file_path)
            case _:
                raise ValueError(f"Unsupported file type: {file_path.suffix}")

    except Exception as exc:
        logger.error(f"Error converting PDF to images: {exc}")
        raise self.retry(exc=exc, countdown=2**self.request.retries)
