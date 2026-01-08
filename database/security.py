"""
Security and compliance framework for GDPR and SOC2

This module provides comprehenshensive and security utilities for:
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
from os import getenv
# =======================================
# Constants used across this module
# =======================================
HASH_SALT = getenv("HASH_SALT", "default_salt")

# asserting that the required salt is set
if HASH_SALT == "default_salt":
    raise EnvironmentError("HASH_SALT environment variable must be set for security module.")


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

def compliance_column(
    sensitvity: DataSensitivity= DataSensitivity.CONFIDENTIAL,
    encryption: EncryptionType = EncryptionType.AT_REST,
    pii: bool = False,
    gdpr_relevant: bool = False,
    gdpr_category: Optional[GDPRDataCategory] = None,
    soc2_critical: bool = False,
    mask_in_logs: bool = True,
    requires_consents: bool = False,
    retention_period: Optional[DataRetentionPeriod] = None,
    anonymize_on_deletion: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Mark a column with compliance metadata.

    GDPR Requirements:
    - pii: Whether the column contains personally identifiable information.
    - gdpr_relevant: Whether the column is subject to GDPR rights(access, erasure, portability).
    - gdpr_category: The GDPR data category of the column.
    - requires_consents: Whether processing this data requires user consent.
    - retention_period: The data retention period for this column.
    - anonymize_on_deletion: Whether to anonymize data instead of deleting it.

    SOC2 Requirements:
    - sensitvity: The data sensitivity classification.
    - encryption: The encryption requirements for the column.
    - soc2_critical: Whether the column is critical for SOC2 compliance.
    - mask_in_logs: Whether to mask this column in logs and error messages.

    Usage: 
        email: Mapped[str] = mapped_column(
            String(255), 
            info = compliance_column(
                    sensitvity=DataSensitivity.CONFIDENTIAL,
                    encryption=EncryptionType.AT_REST,
                    pii=True,
                    gdpr_relevant=True,
                    gdpr_category=GDPRDataCategory.IDENTITY,
                    soc2_critical=True,
                    mask_in_logs=True,
                    requires_consents=True,
                    retention_period=DataRetentionPeriod.THREE_YEARS,
                    anonymize_on_deletion=True
                )
        )
    """
    return {
        # SOC2 Metadata
        "sensitivity": sensitvity.value,
        "encryption": encryption.value,
        "soc2_critical": soc2_critical,
        "mask_in_logs": mask_in_logs,

        # GDPR Metadata
        "pii": pii,
        "gdpr_relevant": gdpr_relevant,
        "gdpr_category": gdpr_category.value if gdpr_category else None,
        "requires_consents": requires_consents,
        "retention_period": retention_period.value if retention_period else None,
        "anonymize_on_deletion": anonymize_on_deletion,
        **kwargs
    }


# =======================================
# Data Masking Utilities
# =======================================

def mask_sensitive_data(value:str, visible_chars: int = 4) -> str:
    """
    Masks sensitive data by showing only the last `visible_chars` characters.

    Args:
        value (str): The sensitive data to mask.
        visible_chars (int): Number of characters to leave visible at the end.

    Returns:
        str: The masked data.
    """
    if not value or len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]

def mask_email(email: str) -> str:
    """
    Masks an email address by showing only the first character of the local part
    and the domain. It is useful for logging or displaying email addresses
    without exposing the full address.

    Args:
        email (str): The email address to mask.

    Returns:
        str: The masked email address.
    """
    try:
        local_part, domain = email.split("@")
        if len(local_part) <= 1:
            masked_local = "*"
        else:
            masked_local = local_part[0] + "*" * (len(local_part) - 1)
        return f"{masked_local}@{domain}"
    except Exception:
        return mask_sensitive_data(email)

def mask_phone(phone: str) -> str:
    """
    Masks a phone number by showing only the last 4 digits.

    Args:
        phone (str): The phone number to mask.

    Returns:
        str: The masked phone number.
    """
    if not phone or len(phone) < 4:
        return "*" * len(phone)
    
    return mask_sensitive_data(phone, visible_chars=4)

def mask_ip_address(ip: str) -> str:
    """
    Masks an IP address by replacing the last octet with '*'.

    Args:
        ip (str): The IP address to mask.

    Returns:
        str: The masked IP address.
    """
    try:
        parts = ip.split(".")
        if len(parts) != 4:
            return mask_sensitive_data(ip)
        parts[-1] = "*"
        return ".".join(parts)
    except Exception:
        return mask_sensitive_data(ip)
    

# =======================================
# Anonymization Utilities
# =======================================

def anonymize_email(user_id:int)-> str:
    """
    Generates an anonymized email address for a user based on their user ID.

    Args:
        user_id (int): The user ID.

    Returns:
        str: The anonymized email address.
    """
    return f"user{user_id}@anonymized.alethic.ai"

def anonymize_name()-> str:
    """
    Returns a generic anonymized name.

    Returns:
        str: The anonymized name.
    """
    return "Anonymized User"

def hash_for_analytics(value:str, salt:str= HASH_SALT) -> str:
    """
    Hashes a value with a static salt for anonymized analytics.

    Args:
        value (str): The value to hash.
        salt (str): The static salt to use.

    Returns:
        str: The hashed value.
    """
    hasher = hashlib.sha256()
    hasher.update(f"{salt}{value}".encode("utf-8"))
    return hasher.hexdigest()