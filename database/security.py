"""
Security and compliance framework for GDPR and SOC2

This module provides comprehenshensive and security utilities for:
- GDPR compliance (data privacy, consent, retentions)
- SOC2 compliance (access controls, audit logging, encryption standards)
- PII data handling (identification, classification, protection)
- Data encryption (at rest and in transit)
"""

from sqlalchemy import column, event
from enum import Enum as PyEnum
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union, Literal, TypeVar
import hashlib
from base64 import urlsafe_b64decode, urlsafe_b64encode
from os import getenv
from secrets import token_bytes
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# =======================================
# Constants used across this module
# =======================================
HASH_SALT = getenv("HASH_SALT", "default_salt")

# asserting that the required salt is set
if HASH_SALT == "default_salt":
    raise EnvironmentError(
        "HASH_SALT environment variable must be set for security module."
    )


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
    sensitvity: DataSensitivity = DataSensitivity.CONFIDENTIAL,
    encryption: EncryptionType = EncryptionType.AT_REST,
    pii: bool = False,
    gdpr_relevant: bool = False,
    gdpr_category: Optional[GDPRDataCategory] = None,
    soc2_critical: bool = False,
    mask_in_logs: bool = True,
    requires_consents: bool = False,
    retention_period: Optional[DataRetentionPeriod] = None,
    anonymize_on_deletion: bool = False,
    **kwargs,
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
        **kwargs,
    }


# =======================================
# Data Masking Utilities
# =======================================


def mask_sensitive_data(value: str, visible_chars: int = 4) -> str:
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


def anonymize_email(user_id: int) -> str:
    """
    Generates an anonymized email address for a user based on their user ID.

    Args:
        user_id (int): The user ID.

    Returns:
        str: The anonymized email address.
    """
    return f"user{user_id}@anonymized.alethic.ai"


def anonymize_name() -> str:
    """
    Returns a generic anonymized name.

    Returns:
        str: The anonymized name.
    """
    return "Anonymized User"


def hash_for_analytics(value: str, salt: str = HASH_SALT) -> str:
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


# =======================================
# Compliance Mixin Classes
# =======================================
GT = TypeVar("GT", bound="GDPRComplianceMixin")


class GDPRComplianceMixin:
    """
    Mixin for GDPR-compliant models.

    Provides methods for handling data subject requests,
    data retention, and anonymization.
    """

    @classmethod
    def get_pii_fields(cls: GT) -> List[str]:
        """
        Returns a list of PII fields in the model.

        Returns:
            List[str]: List of PII field names.
        """
        pii_fields = []
        for column in cls.__tble__.columns:
            if hasattr(column.info, "pii") and column.info.get("pii"):
                pii_fields.append(column.name)
        return pii_fields

    @classmethod
    def get_gdpr_relevant_fields(cls: GT) -> List[str]:
        """
        Returns a list of GDPR-relevant fields in the model.

        Returns:
            List[str]: List of GDPR-relevant field names.
        """
        gdpr_fields = []
        for column in cls.__table__.columns:
            if (
                hasattr(column, "info")
                and hasattr(column.info, "gdpr_relevant")
                and column.info.get("gdpr_relevant")
            ):
                gdpr_fields.append(column.name)
        return gdpr_fields

    @classmethod
    def get_fields_by_category(cls: GT, category: GDPRDataCategory) -> List[str]:
        """
        Returns a list of fields in the model for a given GDPR data category.

        Args:
            category (GDPRDataCategory): The GDPR data category.
        Returns:
            List[str]: List of field names in the given category.
        """
        category_fields = []
        for column in cls.__table__.columns:
            if (
                hasattr(column.info, "gdpr_category")
                and column.info.get("gdpr_category") == category.value
            ):
                category_fields.append(column.name)
        return category_fields

    def export_gdpr_data(self: GT, mask_sensitive: bool = True) -> Dict[str, Any]:
        """
        Exports GDPR-relevant data for the instance.

        Args:
            mask_sensitive (bool): Whether to mask sensitive data.
        Returns:
            Dict[str, Any]: The exported GDPR data.
        """
        gdpr_fields = self.get_gdpr_relevant_fields()
        result_data = {}

        for field in gdpr_fields:
            value = getattr(self, field, None)

            if mask_sensitive and hasattr(self.__table__.columns[field], "info"):
                column_info = self.__table__.columns[field].info
                if column_info.get("sensitivity") == DataSensitivity.RESTRICTED.value:
                    if "email" in field:
                        value = mask_email(value)
                    elif "phone" in field:
                        value = mask_phone(value)
                    elif "ip" in field:
                        value = mask_ip_address(value)
                    else:
                        value = mask_sensitive_data(value)
            result_data[field] = value

        return result_data

    def anonymize_gdpr_data(self: GT) -> None:
        """
        Anonymize GDPR data for right to erasure compliance.
        Keeps record for audit purposes but removes PII.
        """
        pii_fields = self.get_pii_fields()

        for field in pii_fields:
            column = self.__table__.columns[field]
            if hasattr(column, "info") and column.info.get("anonymize_on_deletion"):
                if "email" in field.lower():
                    setattr(self, field, anonymize_email(self.id))
                elif "name" in field.lower():
                    setattr(self, field, anonymize_name())
                elif field in ["phone", "phone_number"]:
                    setattr(self, field, None)
                else:
                    setattr(self, field, None)


ST = TypeVar("ST", bound="SOC2ComplianceMixin")


class SOC2ComplianceMixin:
    """
    Mixin for SOC2-compliant models.

    Provides methods for handling:
    - Data classification
    - Access logging
    - Change tracking
    - Encryption verification
    """

    @classmethod
    def get_sensitive_fields(cls: ST) -> Dict[str, str]:
        """
        Returns a dictionary of sensitive fields and their sensitivity levels.

        Returns:
            Dict[str, str]: Dictionary of field names and sensitivity levels.
        """
        sensitive_fields = {}
        for column in cls.__table__.columns:
            if hasattr(column, "info") and hasattr(column.info, "sensitivity"):
                sensitivity = column.info.get("sensitivity")
                if sensitivity and sensitivity != DataSensitivity.PUBLIC.value:
                    sensitive_fields[column.name] = sensitivity
        return sensitive_fields

    @classmethod
    def get_encrypted_fields(cls: ST) -> Dict[str, str]:
        """
        Returns a dictionary of fields and their encryption types.

        Returns:
            Dict[str, str]: Dictionary of field names and encryption types.
        """
        encrypted_fields = {}
        for column in cls.__table__.columns:
            if hasattr(column, "info") and hasattr(column.info, "encryption"):
                encryption = column.info.get("encryption")
                if encryption and encryption != EncryptionType.NONE.value:
                    encrypted_fields[column.name] = encryption
        return encrypted_fields

    @classmethod
    def get_soc2_critical_fields(cls: ST) -> List[str]:
        """
        Returns a list of SOC2-critical fields in the model.

        Returns:
            List[str]: List of SOC2-critical field names.
        """
        critical_fields = []
        for column in cls.__table__.columns:
            if (
                hasattr(column, "info")
                and hasattr(column.info, "soc2_critical")
                and column.info.get("soc2_critical")
            ):
                critical_fields.append(column.name)
        return critical_fields

    def to_dict_masked(self: ST, mask_sensitive: bool = True) -> Dict[str, Any]:
        """
        Converts model to dictionaly, masking sensitive fields if specified.

        Args:
            mask_sensitive (bool): Whether to mask sensitive fields.
        Returns:
            Dict[str, Any]: The model data as a dictionary.
        """
        result_data = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if mask_sensitive and hasattr(column, "info"):
                column_info = column.info
                if column_info.get("mask_in_logs") and value:
                    if "@" in str(value):
                        value = mask_email(str(value))
                    elif "phone" in column.name.lower():
                        value = mask_phone(str(value))
                    elif "ip" in column.name.lower():
                        value = mask_ip_address(str(value))
                    else:
                        value = mask_sensitive_data(str(value))
            result_data[column.name] = value
        return result_data


class ComplianceMixin(GDPRComplianceMixin, SOC2ComplianceMixin):
    """
    Mixin combining GDPR and SOC2 compliance features.
    """

    pass


# =======================================
# Consent Management
# =======================================
class ConsentRecord:
    """
    Represents a user consent record for GDPR compliance.
    """

    def __init__(
        self,
        user_id: int,
        consent_type: ConsentType,
        granted: bool,
    ):
        self.user_id = user_id
        self.consent_type = consent_type
        self.granted = granted
        self.granted_at = datetime.now(timezone.utc) if granted else None
        self.revoked_at = None if granted else datetime.now(timezone.utc)

    def revoke_consent(self) -> None:
        """
        Revoke the consent.
        """
        self.granted = False
        self.revoked_at = datetime.now(timezone.utc)


# =======================================
# Data Retention Utilities
# =======================================
def get_retention_date(period: DataRetentionPeriod) -> datetime:
    """
    Calculate the data retention date based on the retention period.
    Args:
        period (DataRetentionPeriod): The data retention period.
    Returns:
        datetime: The calculated retention date.
    """
    retention_mapping = {
        DataRetentionPeriod.ONE_MONTH: timedelta(days=30),
        DataRetentionPeriod.THREE_MONTHS: timedelta(days=90),
        DataRetentionPeriod.SIX_MONTHS: timedelta(days=180),
        DataRetentionPeriod.ONE_YEAR: timedelta(days=365),
        DataRetentionPeriod.TWO_YEARS: timedelta(days=730),
        DataRetentionPeriod.THREE_YEARS: timedelta(days=1095),
        DataRetentionPeriod.FIVE_YEARS: timedelta(days=1825),
        DataRetentionPeriod.SEVEN_YEARS: timedelta(days=2555),
        DataRetentionPeriod.INDEFINITE: None,
    }
    delta = retention_mapping.get(period)
    if delta is None:
        return None

    return datetime.now(timezone.utc) + delta

def should_retain(created_at: datetime, period: DataRetentionPeriod) -> bool:
    """
    Determine if data should be retained based on its creation date and retention period.

    Args:
        created_at (datetime): The creation date of the data.
        period (DataRetentionPeriod): The data retention period.

    Returns:
        bool: True if data should be retained, False if it can be deleted.
    """
    expiration = get_retention_date(period)
    if expiration is None:
        return True  # Indefinite retention

    return datetime.now(timezone.utc) < (created_at + (expiration - datetime.now(timezone.utc)))

# =======================================
# Cryptographic Utilities
# =======================================
class CryptoUtils:
    """
    Utility class for data encryption and decryption, hashing, and key management.
    """

    _NONCE_LENGTH = 12  # AES-GCM recommended nonce size

    @staticmethod
    def _normalize_key(key: bytes | str | None) -> bytes:
        """
        Accept raw 32-byte keys or their URL-safe base64 encoding and return raw bytes.
        """
        if key is None:
            raise ValueError("Encryption key must be provided")

        if isinstance(key, bytes):
            key_bytes_candidate = key
        else:
            key_bytes_candidate = key.encode("utf-8")

        # Accept already-raw 32 byte keys
        if len(key_bytes_candidate) == 32:
            return key_bytes_candidate

        # Accept URL-safe base64-encoded keys
        try:
            decoded = urlsafe_b64decode(key_bytes_candidate)
        except Exception:
            decoded = None

        if decoded and len(decoded) == 32:
            return decoded

        raise ValueError(
            "Encryption key must be 32 bytes (AES-256) or its URL-safe base64 encoding"
        )

    @staticmethod
    def encrypt(value:str, key: bytes | str | None = None)-> str:
        """
        Encrypts a value using AES-256-GCM.

        Args:
            value: Plain text value to encrypt
            key: 32-byte AES key (raw bytes or URL-safe base64 encoded)
            
        Returns:
            URL-safe base64 encoded ciphertext containing nonce + ciphertext + tag
        """
        if value is None:
            return None
        key_bytes = CryptoUtils._normalize_key(key)
        try:
            aesgcm = AESGCM(key_bytes)
            nonce = token_bytes(CryptoUtils._NONCE_LENGTH)
            ciphertext = aesgcm.encrypt(nonce, value.encode("utf-8"), None)
            token = urlsafe_b64encode(nonce + ciphertext)
            return token.decode("utf-8")
        except InvalidTag as e:
            raise ValueError("Invalid encryption key") from e
        except Exception as e:
            raise ValueError("Encryption failed") from e

    @staticmethod
    def decrypt(token: str, key: bytes | str | None = None) -> str | None:
        """
        Decrypts an AES-256-GCM encrypted value.

        Args:
            token: URL-safe base64 string containing nonce + ciphertext + tag
            key: 32-byte AES key (raw bytes or URL-safe base64 encoded)

        Returns:
            Decrypted plaintext string or None
        """
        if token is None:
            return None
        key_bytes = CryptoUtils._normalize_key(key)
        try:
            raw = urlsafe_b64decode(token.encode("utf-8"))
            if len(raw) <= CryptoUtils._NONCE_LENGTH:
                raise ValueError("Invalid encrypted payload")
            nonce = raw[: CryptoUtils._NONCE_LENGTH]
            ciphertext = raw[CryptoUtils._NONCE_LENGTH :]
            aesgcm = AESGCM(key_bytes)
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode("utf-8")
        except (InvalidTag, ValueError, TypeError) as e:
            raise ValueError("Invalid or corrupted encrypted value") from e
        except Exception as e:
            raise ValueError("Decryption failed") from e

    @staticmethod
    def generate_key() -> bytes:
        """
        Generates a new AES-256-GCM key.

        Returns:
            bytes: The generated key.
        """
        key = AESGCM.generate_key(bit_length=256)
        return urlsafe_b64encode(key)

    @staticmethod
    def hash_value(value:str, algorithm:str = "sha256")-> str:
        """
        Hashes a value using the specified algorithm.

        Args:
            value: The value to hash
            algorithm: The hashing algorithm (e.g., 'sha256', 'md5')

        Returns:
            The hexadecimal hash string
        """
        hasher = hashlib.new(algorithm)
        hasher.update(value.encode('utf-8'))
        return hasher.hexdigest()

# =======================================
# Audit Trail Decorator
# =======================================

def audit_changes(model_class):
    """
    Decorator to automatically log changes for SOC2 Compliance.
    """