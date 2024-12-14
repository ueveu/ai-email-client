"""
Service for secure management of API keys.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta
import secrets
from base64 import b64encode, b64decode
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import keyring
from utils.logger import logger
from utils.error_handler import handle_errors

class APIKeyService:
    """Service for securely managing API keys."""
    
    KEYRING_SERVICE = "ai_email_assistant_api"
    ENCRYPTION_KEY_NAME = "api_key_encryption_key"
    ACCESS_LOG_FILE = "api_access.log"
    RATE_LIMIT_WINDOW = timedelta(minutes=5)
    MAX_REQUESTS = 100  # Maximum requests per window
    
    def __init__(self):
        """Initialize the API key service."""
        self.config_dir = Path.home() / '.ai_email_assistant' / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.access_log_path = self.config_dir / self.ACCESS_LOG_FILE
        self._fernet = None
        self._access_counts = {}  # Track API access for rate limiting
        
        # Initialize encryption
        self._ensure_encryption_key()
    
    def _ensure_encryption_key(self):
        """Ensure encryption key exists in the keyring."""
        key = keyring.get_password(self.KEYRING_SERVICE, self.ENCRYPTION_KEY_NAME)
        if not key:
            # Generate a new encryption key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=secrets.token_bytes(32),
                iterations=600000,
                backend=default_backend()
            )
            key = b64encode(kdf.derive(secrets.token_bytes(32))).decode()
            keyring.set_password(self.KEYRING_SERVICE, self.ENCRYPTION_KEY_NAME, key)
    
    @property
    def fernet(self) -> Fernet:
        """Get or create the Fernet instance for encryption/decryption."""
        if self._fernet is None:
            key = keyring.get_password(self.KEYRING_SERVICE, self.ENCRYPTION_KEY_NAME)
            if not key:
                raise ValueError("Encryption key not found")
            self._fernet = Fernet(key.encode())
        return self._fernet
    
    def _log_access(self, api_name: str, action: str):
        """
        Log API key access with rate limiting.
        
        Args:
            api_name (str): Name of the API
            action (str): Action being performed
        
        Raises:
            ValueError: If rate limit is exceeded
        """
        now = datetime.now()
        
        # Clean up old access counts
        self._access_counts = {
            k: v for k, v in self._access_counts.items()
            if now - v['timestamp'] <= self.RATE_LIMIT_WINDOW
        }
        
        # Check rate limit
        if api_name in self._access_counts:
            access = self._access_counts[api_name]
            if access['count'] >= self.MAX_REQUESTS:
                raise ValueError(f"Rate limit exceeded for {api_name}")
            access['count'] += 1
        else:
            self._access_counts[api_name] = {
                'timestamp': now,
                'count': 1
            }
        
        # Log access
        log_entry = {
            'timestamp': now.isoformat(),
            'api_name': api_name,
            'action': action
        }
        
        try:
            with open(self.access_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to log API access: {str(e)}")
    
    @handle_errors
    def store_api_key(self, api_name: str, api_key: str) -> bool:
        """
        Securely store an API key.
        
        Args:
            api_name (str): Name of the API
            api_key (str): API key to store
            
        Returns:
            bool: True if key was stored successfully
        """
        try:
            # Encrypt the API key
            encrypted_key = self.fernet.encrypt(api_key.encode())
            
            # Store in keyring
            keyring.set_password(
                f"{self.KEYRING_SERVICE}_{api_name}",
                "api_key",
                b64encode(encrypted_key).decode()
            )
            
            self._log_access(api_name, "store")
            logger.info(f"Stored API key for {api_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store API key for {api_name}: {str(e)}")
            return False
    
    @handle_errors
    def get_api_key(self, api_name: str) -> Optional[str]:
        """
        Retrieve an API key.
        
        Args:
            api_name (str): Name of the API
            
        Returns:
            Optional[str]: Decrypted API key if found
        """
        try:
            # Get encrypted key from keyring
            encrypted_key = keyring.get_password(
                f"{self.KEYRING_SERVICE}_{api_name}",
                "api_key"
            )
            
            if not encrypted_key:
                return None
            
            # Decrypt the key
            decrypted_key = self.fernet.decrypt(b64decode(encrypted_key))
            
            self._log_access(api_name, "retrieve")
            return decrypted_key.decode()
            
        except Exception as e:
            logger.error(f"Failed to get API key for {api_name}: {str(e)}")
            return None
    
    @handle_errors
    def delete_api_key(self, api_name: str) -> bool:
        """
        Delete an API key.
        
        Args:
            api_name (str): Name of the API
            
        Returns:
            bool: True if key was deleted successfully
        """
        try:
            keyring.delete_password(
                f"{self.KEYRING_SERVICE}_{api_name}",
                "api_key"
            )
            
            self._log_access(api_name, "delete")
            logger.info(f"Deleted API key for {api_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete API key for {api_name}: {str(e)}")
            return False
    
    @handle_errors
    def rotate_encryption_key(self) -> bool:
        """
        Rotate the encryption key and re-encrypt all API keys.
        
        Returns:
            bool: True if rotation was successful
        """
        try:
            # Store old Fernet instance
            old_fernet = self.fernet
            
            # Generate new encryption key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=secrets.token_bytes(32),
                iterations=600000,
                backend=default_backend()
            )
            new_key = b64encode(kdf.derive(secrets.token_bytes(32))).decode()
            
            # Create new Fernet instance
            new_fernet = Fernet(new_key.encode())
            
            # Get all API keys
            api_keys = {}
            for service in keyring.get_keyring().get_preferred_collection().get_all_items():
                if service.get_service_name().startswith(self.KEYRING_SERVICE) and \
                   service.get_service_name() != self.KEYRING_SERVICE:
                    api_name = service.get_service_name().replace(f"{self.KEYRING_SERVICE}_", "")
                    encrypted_key = service.get_password()
                    if encrypted_key:
                        # Decrypt with old key
                        decrypted_key = old_fernet.decrypt(b64decode(encrypted_key))
                        # Re-encrypt with new key
                        new_encrypted_key = new_fernet.encrypt(decrypted_key)
                        api_keys[api_name] = b64encode(new_encrypted_key).decode()
            
            # Store new encryption key
            keyring.set_password(self.KEYRING_SERVICE, self.ENCRYPTION_KEY_NAME, new_key)
            
            # Update all API keys with new encryption
            for api_name, encrypted_key in api_keys.items():
                keyring.set_password(
                    f"{self.KEYRING_SERVICE}_{api_name}",
                    "api_key",
                    encrypted_key
                )
            
            # Reset Fernet instance
            self._fernet = None
            
            logger.info("API key encryption key rotated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rotate API key encryption: {str(e)}")
            return False
    
    def get_access_logs(self, api_name: Optional[str] = None) -> list:
        """
        Get API access logs.
        
        Args:
            api_name (str, optional): Filter logs by API name
            
        Returns:
            list: List of log entries
        """
        logs = []
        try:
            if self.access_log_path.exists():
                with open(self.access_log_path, 'r') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            if not api_name or entry['api_name'] == api_name:
                                logs.append(entry)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Failed to read access logs: {str(e)}")
        
        return logs 