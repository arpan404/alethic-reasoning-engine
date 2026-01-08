"""
Enhanced Security and Compliance Framework for GDPR and SOC 2

This module provides comprehensive security utilities for:
- GDPR compliance (data privacy, consent, retention)
- SOC 2 compliance (access control, audit trails, encryption)
- PII protection and encryption
- Data classification and handling
"""

from sqlalchemy import String, Boolean, JSON, DateTime, func, Text, event
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum as PyEnum
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import hashlib
import json
from sqlalchemy.orm import object_session
from cryptography.fernet import Fernet
from cryptography.fernet import Fernet
from cryptography.fernet import Fernet


# ============================================================================
# GDPR Compliance Enums
# ============================================================================


class DataSensitivity(str, PyEnum):
    """Data sensitivity classification for SOC 2."""

    PUBLIC = "public"  # Can be shared freely
    INTERNAL = "internal"  # Internal use only
    CONFIDENTIAL = "confidential"  # Restricted access
    RESTRICTED = "restricted"  # Highly restricted (PII, PHI, financial)


class EncryptionType(str, PyEnum):
    """Encryption requirements."""

    NONE = "none"
    AT_REST = "at_rest"  # Encrypted in database
    IN_TRANSIT = "in_transit"  # Encrypted during transmission
    END_TO_END = "end_to_end"  # Encrypted at rest and in transit


class GDPRDataCategory(str, PyEnum):
    """GDPR data categories."""

    IDENTITY = "identity"  # Name, email, phone
    CONTACT = "contact"  # Address, location
    BIOMETRIC = "biometric"  # Face, voice, fingerprint
    BEHAVIORAL = "behavioral"  # Activity, preferences
    FINANCIAL = "financial"  # Payment info, salary
    HEALTH = "health"  # Medical information
    PROFESSIONAL = "professional"  # Work history, skills
    TECHNICAL = "technical"  # IP address, cookies


class ConsentType(str, PyEnum):
    """Types of consent for GDPR."""

    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PROFILING = "profiling"
    DATA_SHARING = "data_sharing"
    AI_PROCESSING = "ai_processing"


class DataRetentionPeriod(str, PyEnum):
    """Standard retention periods."""

    DAYS_30 = "30_days"
    DAYS_90 = "90_days"
    MONTHS_6 = "6_months"
    YEAR_1 = "1_year"
    YEARS_2 = "2_years"
    YEARS_5 = "5_years"
    YEARS_7 = "7_years"  # Tax/legal requirements
    INDEFINITE = "indefinite"


# ============================================================================
# Column Security Metadata
# ============================================================================


def compliance_column(
    sensitivity: DataSensitivity = DataSensitivity.CONFIDENTIAL,
    encryption: EncryptionType = EncryptionType.AT_REST,
    pii: bool = False,
    gdpr_relevant: bool = False,
    gdpr_category: Optional[GDPRDataCategory] = None,
    soc2_critical: bool = False,
    mask_in_logs: bool = True,
    requires_consent: bool = False,
    retention_period: Optional[DataRetentionPeriod] = None,
    anonymize_on_delete: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """
    Mark a column with comprehensive compliance metadata.

    GDPR Requirements:
    - pii: Personally Identifiable Information
    - gdpr_relevant: Subject to GDPR rights (access, erasure, portability)
    - gdpr_category: Type of personal data
    - requires_consent: Needs explicit user consent
    - retention_period: How long to keep the data
    - anonymize_on_delete: Anonymize instead of hard delete

    SOC 2 Requirements:
    - sensitivity: Data classification level
    - encryption: Encryption requirements
    - soc2_critical: Critical for SOC 2 audit
    - mask_in_logs: Prevent logging sensitive data

    Usage:
        email: Mapped[str] = mapped_column(
            String(255),
            info=compliance_column(
                sensitivity=DataSensitivity.RESTRICTED,
                pii=True,
                gdpr_relevant=True,
                gdpr_category=GDPRDataCategory.IDENTITY,
                requires_consent=True,
                retention_period=DataRetentionPeriod.YEARS_2
            )
        )
    """
    return {
        # SOC 2
        "sensitivity": sensitivity.value,
        "encryption": encryption.value,
        "soc2_critical": soc2_critical,
        "mask_in_logs": mask_in_logs,
        # GDPR
        "pii": pii,
        "gdpr_relevant": gdpr_relevant,
        "gdpr_category": gdpr_category.value if gdpr_category else None,
        "requires_consent": requires_consent,
        "retention_period": retention_period.value if retention_period else None,
        "anonymize_on_delete": anonymize_on_delete,
        **kwargs,
    }


# ============================================================================
# Data Masking Utilities
# ============================================================================


def mask_sensitive_data(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive data for logging/display."""
    if not value or len(value) <= visible_chars:
        return "****"
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def mask_email(email: str) -> str:
    """Mask email address for logging."""
    if not email or "@" not in email:
        return "****"

    local, domain = email.split("@", 1)
    if len(local) <= 1:
        masked_local = "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 1)

    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """Mask phone number."""
    if not phone:
        return "****"
    # Keep last 4 digits
    return "*" * (len(phone) - 4) + phone[-4:] if len(phone) > 4 else "****"


def mask_ip_address(ip: str) -> str:
    """Mask IP address (GDPR requirement)."""
    if not ip:
        return "****"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.***. ***"
    return "****"


# ============================================================================
# Anonymization Utilities
# ============================================================================


def anonymize_email(user_id: int) -> str:
    """Generate anonymized email for GDPR deletion."""
    return f"deleted_{user_id}@anonymized.local"


def anonymize_name() -> str:
    """Generate anonymized name."""
    return "Deleted User"


def hash_for_analytics(value: str, salt: str = "") -> str:
    """One-way hash for analytics while preserving privacy."""
    return hashlib.sha256(f"{value}{salt}".encode()).hexdigest()


# ============================================================================
# Compliance Mixin Classes
# ============================================================================


class GDPRCompliantMixin:
    """
    Mixin for GDPR-compliant models.

    Provides methods for:
    - Identifying PII fields
    - Data export (right to access)
    - Data anonymization (right to erasure)
    - Data portability
    """

    @classmethod
    def get_pii_fields(cls) -> List[str]:
        """Get list of PII fields."""
        pii_fields = []
        for column in cls.__table__.columns:
            if hasattr(column, "info") and column.info.get("pii"):
                pii_fields.append(column.name)
        return pii_fields

    @classmethod
    def get_gdpr_fields(cls) -> List[str]:
        """Get list of GDPR-relevant fields."""
        gdpr_fields = []
        for column in cls.__table__.columns:
            if hasattr(column, "info") and column.info.get("gdpr_relevant"):
                gdpr_fields.append(column.name)
        return gdpr_fields

    @classmethod
    def get_fields_by_category(cls, category: GDPRDataCategory) -> List[str]:
        """Get fields by GDPR category."""
        fields = []
        for column in cls.__table__.columns:
            if (
                hasattr(column, "info")
                and column.info.get("gdpr_category") == category.value
            ):
                fields.append(column.name)
        return fields

    def export_gdpr_data(self, mask_sensitive: bool = False) -> Dict[str, Any]:
        """
        Export data for GDPR right to access.

        Args:
            mask_sensitive: Whether to mask highly sensitive fields

        Returns:
            Dictionary of GDPR-relevant data
        """
        gdpr_fields = self.get_gdpr_fields()
        result = {}

        for field in gdpr_fields:
            value = getattr(self, field, None)

            if mask_sensitive and hasattr(self.__table__.columns[field], "info"):
                info = self.__table__.columns[field].info
                if info.get("sensitivity") == DataSensitivity.RESTRICTED.value:
                    if "@" in str(value):
                        value = mask_email(str(value))
                    else:
                        value = mask_sensitive_data(str(value))

            result[field] = value

        return result

    def anonymize_gdpr_data(self):
        """
        Anonymize GDPR data for right to erasure.
        Keeps record for audit but removes PII.
        """
        pii_fields = self.get_pii_fields()

        for field in pii_fields:
            column = self.__table__.columns[field]
            if hasattr(column, "info"):
                info = column.info

                # Check if field should be anonymized
                if info.get("anonymize_on_delete", False):
                    if "email" in field.lower():
                        setattr(self, field, anonymize_email(self.id))
                    elif "name" in field.lower():
                        setattr(self, field, anonymize_name())
                    elif field in ["phone", "ip_address"]:
                        setattr(self, field, None)
                    else:
                        setattr(self, field, None)


class SOC2CompliantMixin:
    """
    Mixin for SOC 2-compliant models.

    Provides methods for:
    - Data classification
    - Access logging
    - Change tracking
    - Encryption verification
    """

    @classmethod
    def get_sensitive_fields(cls) -> Dict[str, str]:
        """Get fields with their sensitivity levels."""
        sensitive = {}
        for column in cls.__table__.columns:
            if hasattr(column, "info"):
                sensitivity = column.info.get("sensitivity")
                if sensitivity and sensitivity != DataSensitivity.PUBLIC.value:
                    sensitive[column.name] = sensitivity
        return sensitive

    @classmethod
    def get_encrypted_fields(cls) -> List[str]:
        """Get fields requiring encryption."""
        encrypted = []
        for column in cls.__table__.columns:
            if hasattr(column, "info"):
                encryption = column.info.get("encryption")
                if encryption and encryption != EncryptionType.NONE.value:
                    encrypted.append(column.name)
        return encrypted

    @classmethod
    def get_soc2_critical_fields(cls) -> List[str]:
        """Get SOC 2 critical fields."""
        critical = []
        for column in cls.__table__.columns:
            if hasattr(column, "info") and column.info.get("soc2_critical"):
                critical.append(column.name)
        return critical

    def to_dict_masked(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """
        Convert model to dictionary with optional masking.

        Args:
            mask_sensitive: Whether to mask sensitive fields

        Returns:
            Dictionary representation with masked sensitive data
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)

            if mask_sensitive and hasattr(column, "info"):
                info = column.info
                if info.get("mask_in_logs") and value:
                    if "@" in str(value):
                        value = mask_email(str(value))
                    elif "phone" in column.name.lower():
                        value = mask_phone(str(value))
                    elif "ip" in column.name.lower():
                        value = mask_ip_address(str(value))
                    else:
                        value = mask_sensitive_data(str(value))

            result[column.name] = value

        return result


class ComplianceMixin(GDPRCompliantMixin, SOC2CompliantMixin):
    """Combined GDPR and SOC 2 compliance mixin."""

    pass


# ============================================================================
# Consent Management
# ============================================================================


class ConsentRecord:
    """Track user consent for GDPR compliance."""

    def __init__(self, user_id: int, consent_type: ConsentType, granted: bool):
        self.user_id = user_id
        self.consent_type = consent_type
        self.granted = granted
        self.granted_at = datetime.utcnow() if granted else None
        self.revoked_at = None if granted else datetime.utcnow()

    def revoke(self):
        """Revoke consent."""
        self.granted = False
        self.revoked_at = datetime.utcnow()


# ============================================================================
# Data Retention Utilities
# ============================================================================


def get_retention_date(period: DataRetentionPeriod) -> datetime:
    """Calculate retention expiration date."""
    now = datetime.utcnow()

    retention_map = {
        DataRetentionPeriod.DAYS_30: timedelta(days=30),
        DataRetentionPeriod.DAYS_90: timedelta(days=90),
        DataRetentionPeriod.MONTHS_6: timedelta(days=180),
        DataRetentionPeriod.YEAR_1: timedelta(days=365),
        DataRetentionPeriod.YEARS_2: timedelta(days=730),
        DataRetentionPeriod.YEARS_5: timedelta(days=1825),
        DataRetentionPeriod.YEARS_7: timedelta(days=2555),
    }

    delta = retention_map.get(period)
    if delta:
        return now + delta
    return None  # Indefinite


def should_retain(created_at: datetime, retention_period: DataRetentionPeriod) -> bool:
    """Check if data should still be retained."""
    if retention_period == DataRetentionPeriod.INDEFINITE:
        return True

    expiration = get_retention_date(retention_period)
    if expiration:
        return datetime.utcnow() < (created_at + (expiration - datetime.utcnow()))
    return True


# ============================================================================
# Audit Trail Decorator
# ============================================================================


def audit_changes(model_class):
    """
    Decorator to automatically log changes for SOC 2 compliance.

    Usage:
        @audit_changes
        class User(Base, ComplianceMixin):
            ...
    """

    @event.listens_for(model_class, "before_update")
    def receive_before_update(mapper, connection, target):
        """Log changes to audit trail for SOC 2 compliance."""
        # Get the current state and committed state

        session = object_session(target)
        if not session:
            return

        # Get changed attributes
        changes = {}
        for column in mapper.columns:
            current_value = getattr(target, column.name)
            committed_value = session.get_committed_state(target).get(column.name)

            if current_value != committed_value:
                # Mask sensitive data in audit log
                if hasattr(column, "info") and column.info.get("mask_in_logs"):
                    if "@" in str(committed_value or ""):
                        old_value = mask_email(str(committed_value))
                        new_value = mask_email(str(current_value))
                    elif "phone" in column.name.lower():
                        old_value = mask_phone(str(committed_value or ""))
                        new_value = mask_phone(str(current_value or ""))
                    else:
                        old_value = mask_sensitive_data(str(committed_value or ""))
                        new_value = mask_sensitive_data(str(current_value or ""))
                else:
                    old_value = committed_value
                    new_value = current_value

                changes[column.name] = {
                    "old": old_value,
                    "new": new_value,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        # Store audit trail (integrate with your audit logging system)
        if changes:
            audit_entry = {
                "entity_type": model_class.__name__,
                "entity_id": getattr(target, "id", None),
                "action": "UPDATE",
                "changes": changes,
                "timestamp": datetime.utcnow().isoformat(),
            }
            # TODO: Save audit_entry to audit_logs table or external audit service

    return model_class


# ============================================================================
# Encryption Helpers
# ============================================================================


class EncryptionHelper:
    """Helper for field-level encryption using Fernet symmetric encryption."""

    @staticmethod
    def encrypt(value: str, key: bytes) -> str:
        """
        Encrypt a value using Fernet (symmetric encryption).

        Args:
            value: Plain text value to encrypt
            key: Encryption key (32 bytes for Fernet)

        Returns:
            Base64-encoded encrypted value
        """
        if not value:
            return value

        try:
            cipher = Fernet(key)
            encrypted = cipher.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}")

    @staticmethod
    def decrypt(encrypted_value: str, key: bytes) -> str:
        """
        Decrypt a Fernet-encrypted value.

        Args:
            encrypted_value: Base64-encoded encrypted value
            key: Encryption key (32 bytes for Fernet)

        Returns:
            Decrypted plain text value
        """
        if not encrypted_value:
            return encrypted_value

        try:
            cipher = Fernet(key)
            decrypted = cipher.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    @staticmethod
    def generate_key() -> bytes:
        """Generate a new Fernet encryption key."""
        return Fernet.generate_key()

    @staticmethod
    def hash_value(value: str, algorithm: str = "sha256") -> str:
        """
        One-way hash for searchable encryption.

        Args:
            value: Value to hash
            algorithm: Hash algorithm (sha256, sha512, etc.)

        Returns:
            Hexadecimal hash digest
        """
        if not value:
            return value
        return hashlib.new(algorithm, value.encode()).hexdigest()


# ============================================================================
# Compliance Validation
# ============================================================================


def validate_compliance(model_class) -> Dict[str, List[str]]:
    """
    Validate a model's compliance configuration.

    Returns:
        Dictionary of compliance issues by category
    """
    issues = {"gdpr": [], "soc2": [], "encryption": []}

    # Check for PII without GDPR markers
    for column in model_class.__table__.columns:
        if hasattr(column, "info"):
            info = column.info

            # PII should have GDPR markers
            if info.get("pii") and not info.get("gdpr_relevant"):
                issues["gdpr"].append(f"{column.name}: PII field missing GDPR marker")

            # Restricted data should be encrypted
            if info.get("sensitivity") == DataSensitivity.RESTRICTED.value:
                if info.get("encryption") == EncryptionType.NONE.value:
                    issues["encryption"].append(
                        f"{column.name}: Restricted data not encrypted"
                    )

            # GDPR data should have retention period
            if info.get("gdpr_relevant") and not info.get("retention_period"):
                issues["gdpr"].append(
                    f"{column.name}: GDPR data missing retention period"
                )

    return issues
