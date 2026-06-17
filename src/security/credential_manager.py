"""
Secure Credential Management
Handles sensitive data securely without storing plain text
"""

import logging
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from cryptography.fernet import Fernet
import json

logger = logging.getLogger(__name__)


class CredentialType(str, Enum):
    """Types of credentials"""
    PIN = "pin"
    PASSWORD = "password"
    API_KEY = "api_key"
    VAULT_REFERENCE = "vault_reference"
    PHONE_UNLOCK = "phone_unlock"


@dataclass
class CredentialAlias:
    """Reference to a credential without storing it"""
    alias_id: str
    credential_type: CredentialType
    vault_ref: str  # Reference to external vault
    created_at: str
    expires_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alias_id": self.alias_id,
            "credential_type": self.credential_type.value,
            "vault_ref": self.vault_ref,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


@dataclass
class VaultReference:
    """Reference to credential in external vault"""
    vault_id: str
    service: str  # e.g., "aws_secrets", "vault", "1password"
    path: str     # Path to secret in vault
    key: Optional[str] = None  # Key within secret
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "vault_id": self.vault_id,
            "service": self.service,
            "path": self.path,
            "key": self.key,
        }


class SecretManager:
    """Manages credentials securely"""
    
    def __init__(self, vault_service=None):
        """
        Initialize secret manager
        
        Args:
            vault_service: External vault service (AWS Secrets, Vault, etc.)
        """
        self.vault_service = vault_service
        self.encryption_key = None
        self.cipher = None

    def _ensure_cipher(self) -> Fernet:
        if self.cipher is None:
            self.encryption_key = self._get_encryption_key()
            self.cipher = Fernet(self.encryption_key)

        return self.cipher
    
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key"""
        key_path = os.environ.get("CREDENTIAL_KEY_PATH")
        
        if key_path and os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        
        # Use environment variable as fallback
        key_str = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
        if key_str:
            return key_str.encode()
        
        raise RuntimeError("No credential encryption key found")
    
    def create_vault_reference(
        self,
        service: str,
        path: str,
        key: Optional[str] = None,
    ) -> VaultReference:
        """
        Create reference to credential in external vault
        
        Args:
            service: Vault service (aws_secrets, vault, 1password, etc.)
            path: Path to secret
            key: Key within secret (optional)
            
        Returns:
            VaultReference
        """
        import uuid
        
        ref = VaultReference(
            vault_id=str(uuid.uuid4()),
            service=service,
            path=path,
            key=key,
        )
        
        logger.info(f"Created vault reference: {ref.vault_id}")
        return ref
    
    async def resolve_credential(self, vault_ref: VaultReference) -> str:
        """
        Resolve credential from vault
        
        Args:
            vault_ref: Vault reference
            
        Returns:
            Decrypted credential value
        """
        if not self.vault_service:
            raise RuntimeError("No vault service configured")
        
        try:
            # Get from vault service
            secret = await self.vault_service.get_secret(
                service=vault_ref.service,
                path=vault_ref.path,
                key=vault_ref.key,
            )
            
            logger.info(f"Retrieved credential from vault: {vault_ref.vault_id}")
            return secret
        
        except Exception as e:
            logger.error(f"Error resolving credential: {e}")
            raise
    
    def encrypt_temporary(self, data: str) -> str:
        """
        Temporarily encrypt data for in-memory storage
        This should only be used for temporary storage during execution
        """
        encrypted = self._ensure_cipher().encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt_temporary(self, encrypted_data: str) -> str:
        """
        Decrypt temporarily stored data
        """
        try:
            decrypted = self._ensure_cipher().decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise
    
    async def log_secret_access(
        self,
        user_id: str,
        credential_type: CredentialType,
        workflow_id: str,
        success: bool,
    ) -> None:
        """
        Log secret access for audit trail
        
        Args:
            user_id: User accessing secret
            credential_type: Type of credential
            workflow_id: Associated workflow
            success: Whether access was successful
        """
        logger.warning(
            f"Secret access: user={user_id}, type={credential_type.value}, "
            f"workflow={workflow_id}, success={success}"
        )
    
    def has_key(self, key: str) -> bool:
        """Check if a secret key exists"""
        return key in self.vault_service.list_keys() if self.vault_service else False


class CredentialManager:
    """Manages credential aliases"""
    
    def __init__(self, secret_manager: SecretManager, session=None):
        self.secret_manager = secret_manager
        self.session = session
        self.aliases: Dict[str, CredentialAlias] = {}
    
    async def create_alias(
        self,
        credential_type: CredentialType,
        service: str,
        path: str,
        alias_name: Optional[str] = None,
    ) -> CredentialAlias:
        """
        Create credential alias
        
        Args:
            credential_type: Type of credential
            service: Vault service
            path: Path in vault
            alias_name: Optional human-readable alias
            
        Returns:
            CredentialAlias
        """
        import uuid
        from datetime import datetime
        
        vault_ref = self.secret_manager.create_vault_reference(service, path)
        
        alias = CredentialAlias(
            alias_id=str(uuid.uuid4()),
            credential_type=credential_type,
            vault_ref=vault_ref.vault_id,
            created_at=datetime.utcnow().isoformat(),
        )
        
        self.aliases[alias.alias_id] = alias
        logger.info(f"Created credential alias: {alias.alias_id}")
        
        return alias
    
    async def get_credential(self, alias_id: str) -> Optional[str]:
        """
        Get credential by alias (from vault)
        
        Args:
            alias_id: Credential alias ID
            
        Returns:
            Decrypted credential
        """
        if alias_id not in self.aliases:
            raise ValueError(f"Unknown credential alias: {alias_id}")
        
        alias = self.aliases[alias_id]
        
        # Get vault reference
        vault_ref = VaultReference(
            vault_id=alias.vault_ref,
            service=alias.credential_type.value,
            path=alias.vault_ref,
        )
        
        # Resolve from vault
        return await self.secret_manager.resolve_credential(vault_ref)


class PINProcessor:
    """Temporary PIN processing without storage"""
    
    def __init__(self, secret_manager: SecretManager):
        self.secret_manager = secret_manager
        self.temp_pin: Optional[str] = None
        self.pin_encrypted: Optional[str] = None
    
    def accept_pin(self, pin: str) -> None:
        """
        Accept PIN for current workflow
        Immediately encrypts and forgets plain text
        
        Args:
            pin: PIN (will be encrypted)
        """
        self.pin_encrypted = self.secret_manager.encrypt_temporary(pin)
        # Explicit: Never store plain text
        logger.info("PIN received and encrypted, plain text discarded")
    
    def get_encrypted_pin(self) -> Optional[str]:
        """Get encrypted PIN for temporary use"""
        return self.pin_encrypted
    
    def use_pin_once(self) -> str:
        """Get PIN once for immediate use, then clear"""
        if not self.pin_encrypted:
            raise RuntimeError("No PIN available")
        
        pin = self.secret_manager.decrypt_temporary(self.pin_encrypted)
        self.clear()
        return pin
    
    def clear(self) -> None:
        """Clear all PIN data"""
        self.temp_pin = None
        self.pin_encrypted = None
        logger.info("PIN cleared from memory")


# Global instances
secret_manager = None
credential_manager = None


def get_secret_manager(vault_service=None) -> SecretManager:
    """Get or create secret manager"""
    global secret_manager
    if secret_manager is None:
        secret_manager = SecretManager(vault_service)
    return secret_manager


def get_credential_manager(session=None) -> CredentialManager:
    """Get or create credential manager"""
    global credential_manager
    if credential_manager is None:
        secret_mgr = get_secret_manager()
        credential_manager = CredentialManager(secret_mgr, session)
    return credential_manager
