"""
Security and compliance framework for GDPR and SOC2

This module provides comprehnessive and security utilities for:
- GDPR compliance (data privacy, consent, retentions)
- SOC2 compliance (access controls, audit logging, encryption standards)
- PII data handling (identification, classification, protection)
- Data encryption (at rest and in transit)
"""

from sqlalchemy import event
from enum import Enum as PyEnum
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Literal
import hashlib


# =======================================
# GDPR Compliance Enums
# =======================================


class DataSensitivity(str, PyEnum):
    """Data sensitivity classification for SOC2 compliance."""

    PUBLIC = "public"  # can be shared freely
    INTERNAL = "internal"  # only used internally
    CONFIDENTIAL = "confidential"  # restricted access
    RESTRICTED = "restricted"  # highly sensitive (PII, PHI, financial data)


class EncryptionType(str, PyEnum):
    """Encryption requirements for data."""

    NONE = "none"
    AT_REST = "at_rest"  # encrypted when stored
    IN_TRANSIT = "in_transit"  # encrypted during transmission
    E2E = "end_to_end"  # encrypted at rest and in transit


class GDPRDataCategory(str, PyEnum):
    """Categories of personal data under GDPR."""

    IDENTITY = "identity"  # Name, email, phone
    CONTACT = "contact"  # Address, location
    BIOMETRIC = "biometric"  # Face, voice, fingerprint
    BEHAVIORAL = "behavioral"  # Activity, preferences
    FINANCIAL = "financial"  # Payment info, salary
    HEALTH = "health"  # Medical information
    PROFESSIONAL = "professional"  # Work history, skills
    TECHNICAL = "technical"  # IP address, cookies


class ConsentType(str, PyEnum):
    """
    Types of constent for GDPR compliance.
    """

    MARKETING = "marketing"  # consent for marketing communications
    ANALYTICS = "analytics"  # consent for data analytics
    PROFILING = "profiling"  # consent for profiling activities
    DATA_SHARING = "data_sharing"  # consent for sharing data with third parties
    AI_PROCESSING = "ai_processing"  # consent for AI/ML processing


class DataRetentionPeriod(str, PyEnum):
    """Data retention periods for GDPR compliance."""

    ONE_MONTH = "1_month"
    THREE_MONTHS = "3_months"
    SIX_MONTHS = "6_months"
    ONE_YEAR = "1_year"
    TWO_YEARS = "2_years"
    THREE_YEARS = "3_years"
    FIVE_YEARS = "5_years"
    SEVEN_YEARS = "7_years"
    INDEFINITE = "indefinite"  # until user requests deletion


# =======================================
# Column Security Metadata
# =======================================
