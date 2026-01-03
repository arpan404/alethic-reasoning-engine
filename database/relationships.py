"""
Comprehensive relationship definitions for all database models.

This module adds SQLAlchemy relationships to existing models without modifying
the original model files extensively. Import this after all models are defined.

Usage:
    from database.models import *
    from database.relationships import setup_relationships
    
    setup_relationships()
"""

from sqlalchemy.orm import relationship
from database.models.users import User, UserProfile, UserSession, UserPreference
from database.models.organizations import Organization, OrganizationUsers, OrganizationSettings
from database.models.files import File
from database.models.jobs import Job, JobDepartment, JobRequirement, JobLocation
from database.models.candidates import (
    Candidate, CandidateEducation, CandidateExperience, 
    CandidateSkill, CandidateCertification
)
from database.models.applications import (
    Applications, ApplicationNotes, ApplicationTags, ApplicationActivities
)


def setup_relationships():
    """
    Set up all SQLAlchemy relationships across models.
    Call this function after all models are imported.
    """
    
    # Organization relationships
    if not hasattr(Organization, 'users'):
        Organization.users = relationship(
            "OrganizationUsers",
            back_populates="organization",
            cascade="all, delete-orphan"
        )
        Organization.settings = relationship(
            "OrganizationSettings",
            back_populates="organization",
            uselist=False,
            cascade="all, delete-orphan"
        )
        Organization.jobs = relationship(
            "Job",
            back_populates="organization",
            cascade="all, delete-orphan"
        )
        Organization.files = relationship(
            "File",
            foreign_keys="File.organization_id",
            back_populates="organization"
        )
    
    # OrganizationUsers relationships
    if not hasattr(OrganizationUsers, 'user'):
        OrganizationUsers.user = relationship(
            "User",
            foreign_keys="OrganizationUsers.user_id",
            back_populates="organization_memberships"
        )
        OrganizationUsers.organization = relationship(
            "Organization",
            back_populates="users"
        )
    
    # OrganizationSettings relationships
    if not hasattr(OrganizationSettings, 'organization'):
        OrganizationSettings.organization = relationship(
            "Organization",
            back_populates="settings"
        )
    
    # File relationships
    if not hasattr(File, 'organization'):
        File.organization = relationship(
            "Organization",
            foreign_keys="File.organization_id",
            back_populates="files"
        )
        File.uploader = relationship(
            "User",
            foreign_keys="File.uploaded_by"
        )
    
    # Job relationships
    if not hasattr(Job, 'organization'):
        Job.organization = relationship(
            "Organization",
            back_populates="jobs"
        )
        Job.department = relationship(
            "JobDepartment",
            back_populates="jobs"
        )
        Job.requirements = relationship(
            "JobRequirement",
            back_populates="job",
            cascade="all, delete-orphan"
        )
        Job.locations = relationship(
            "JobLocation",
            back_populates="job",
            cascade="all, delete-orphan"
        )
        Job.applications = relationship(
            "Applications",
            back_populates="job"
        )
    
    # JobDepartment relationships
    if not hasattr(JobDepartment, 'jobs'):
        JobDepartment.jobs = relationship(
            "Job",
            back_populates="department"
        )
    
    # JobRequirement relationships
    if not hasattr(JobRequirement, 'job'):
        JobRequirement.job = relationship(
            "Job",
            back_populates="requirements"
        )
    
    # JobLocation relationships
    if not hasattr(JobLocation, 'job'):
        JobLocation.job = relationship(
            "Job",
            back_populates="locations"
        )
    
    # Candidate relationships
    if not hasattr(Candidate, 'education'):
        Candidate.education = relationship(
            "CandidateEducation",
            back_populates="candidate",
            cascade="all, delete-orphan"
        )
        Candidate.experience = relationship(
            "CandidateExperience",
            back_populates="candidate",
            cascade="all, delete-orphan"
        )
        Candidate.skills = relationship(
            "CandidateSkill",
            back_populates="candidate",
            cascade="all, delete-orphan"
        )
        Candidate.certifications = relationship(
            "CandidateCertification",
            back_populates="candidate",
            cascade="all, delete-orphan"
        )
        Candidate.applications = relationship(
            "Applications",
            back_populates="candidate"
        )
    
    # Candidate detail relationships
    if not hasattr(CandidateEducation, 'candidate'):
        CandidateEducation.candidate = relationship(
            "Candidate",
            back_populates="education"
        )
    
    if not hasattr(CandidateExperience, 'candidate'):
        CandidateExperience.candidate = relationship(
            "Candidate",
            back_populates="experience"
        )
    
    if not hasattr(CandidateSkill, 'candidate'):
        CandidateSkill.candidate = relationship(
            "Candidate",
            back_populates="skills"
        )
    
    if not hasattr(CandidateCertification, 'candidate'):
        CandidateCertification.candidate = relationship(
            "Candidate",
            back_populates="certifications"
        )
    
    # Application relationships
    if not hasattr(Applications, 'job'):
        Applications.job = relationship(
            "Job",
            back_populates="applications"
        )
        Applications.candidate = relationship(
            "Candidate",
            back_populates="applications"
        )
        Applications.notes = relationship(
            "ApplicationNotes",
            back_populates="application",
            cascade="all, delete-orphan"
        )
        Applications.tags = relationship(
            "ApplicationTags",
            back_populates="application",
            cascade="all, delete-orphan"
        )
        Applications.activities = relationship(
            "ApplicationActivities",
            back_populates="application",
            cascade="all, delete-orphan"
        )
    
    # Application detail relationships
    if not hasattr(ApplicationNotes, 'application'):
        ApplicationNotes.application = relationship(
            "Applications",
            back_populates="notes"
        )
    
    if not hasattr(ApplicationTags, 'application'):
        ApplicationTags.application = relationship(
            "Applications",
            back_populates="tags"
        )
    
    if not hasattr(ApplicationActivities, 'application'):
        ApplicationActivities.application = relationship(
            "Applications",
            back_populates="activities"
        )


# Relationship cascade behaviors documentation
CASCADE_BEHAVIORS = {
    "all, delete-orphan": "Delete child records when parent is deleted, and when removed from collection",
    "all, delete": "Delete child records when parent is deleted",
    "save-update": "Cascade save and update operations only",
    "delete": "Cascade delete operations only",
    "SET NULL": "Set foreign key to NULL when parent is deleted (ondelete='SET NULL')",
}

# Security notes for relationships
SECURITY_NOTES = """
Relationship Security Considerations:

1. **Lazy Loading**: Default is 'select' which prevents N+1 queries
2. **Cascade Deletes**: Use 'all, delete-orphan' carefully to prevent accidental data loss
3. **Back Populates**: Always use back_populates for bidirectional relationships
4. **Foreign Key Constraints**: All relationships have proper ondelete behaviors

PII Protection in Relationships:
- User -> UserProfile: Contains PII, handle with care
- User -> UserSession: Contains IP addresses (PII)
- Candidate -> All details: Contains extensive PII
- Applications -> Candidate: Links to PII data

GDPR Compliance:
- When deleting users, cascade to sessions, profiles, preferences
- Candidate data should be anonymized, not deleted (for compliance)
- Application data retention follows organization policies
"""
