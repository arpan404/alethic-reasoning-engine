"""Example usage of Celery tasks."""
import asyncio
from io import BytesIO
from jobs.documents import extract_pdf_text, extract_docx_text
from jobs.s3 import download_file, cache_file, delete_file


async def example_document_extraction():
    """Example: Extract text from documents using Celery."""
    print("=== Document Extraction Example ===")
    
    # Example PDF data (minimal PDF)
    pdf_data = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\nxref\ntrailer<</Size 3/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    
    # Submit task to queue
    task = extract_pdf_text.delay(pdf_data, "example.pdf")
    print(f"Task ID: {task.id}")
    print(f"Task Status: {task.status}")
    
    # Wait for result (with timeout)
    try:
        result = task.get(timeout=10)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")


async def example_s3_operations():
    """Example: Download file from S3 using Celery."""
    print("\n=== S3 Operations Example ===")
    
    # Submit task to queue
    task = download_file.delay("my-bucket", "path/to/file.txt")
    print(f"Task ID: {task.id}")
    print(f"Queued for processing...")
    
    # You can check status later
    # result = task.get()


if __name__ == "__main__":
    print("Celery Tasks Examples")
    print("Make sure Redis and Celery worker are running!")
    print("\nTo run worker: python worker.py")
    print("To submit tasks: python -c 'from examples import example_document_extraction; example_document_extraction()'")
