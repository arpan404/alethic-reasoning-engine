from pathlib import Path
from sqlalchemy import select
from database.models.applications import Applications
from lib.s3 import get_file_from_s3


async def get_applicant_resume(application_id: int) -> Path:
    """
    Returns the resume of the applicant with the given application id.

    Args:
        application_id (int): The id of the application.

    Returns:
        Path: The path to the resume of the applicant.
    """
    try:
        stmt = select(Applications).where(Applications.id == application_id)
        result = await session.execute(stmt)
        application = result.scalar_one_or_none()
        if application is None:
            raise ValueError(f"Application not found for id {application_id}")
        resume_file_name = application.resume
        if resume_file_name is None:
            raise ValueError(f"Resume not found for application {application_id}")

        # stmt to get the actual file info from the table
        stmt = select(File).where(File.name == resume_file_name)
        result = await session.execute(stmt)
        file = result.scalar_one_or_none()
        if file is None:
            raise ValueError(f"File not found for name {resume_file_name}")

        resume_file = await get_file_from_s3("resume", file.key)
        return resume_file

    except Exception as e:
        raise ValueError(f"Error getting resume for application {application_id}: {e}")


async def get_resume_text(resume_file: Path) -> str:
    """
    Returns the text of the resume file.

    Args:
        resume_file (Path): The path to the resume file.

    Returns:
        str: The text of the resume file.
    """
    try:
        return resume_file.read_text()
    except Exception as e:
        raise ValueError(f"Error getting resume text: {e}")
