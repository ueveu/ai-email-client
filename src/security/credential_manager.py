import keyring
import json
from typing import Optional, Dict
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class CredentialManager:
    """
    Manages secure storage and retrieval of credentials using the system keyring
    and additional encryption.
    """
    
    # Service names for keyring
    EMAIL_SERVICE = "ai_email_assistant_email"
    API_SERVICE = "ai_email_assistant_api"
    
    # Salt file for encryption key derivation
    SALT_FILE = Path(__file__).parent / ".salt"
    
    def __init__(self):
        """Initialize the credential manager."""
        self._fernet = None
        self._ensure_encryption_key()
    
    def _ensure_encryption_key(self):
        """Ensure encryption key exists and initialize Fernet."""
        # Create or load salt
        if not self.SALT_FILE.exists():
            salt = os.urandom(16)
            self.SALT_FILE.write_bytes(salt)
        else:
            salt = self.SALT_FILE.read_bytes()
        
        # Generate encryption key using system-specific data
        system_data = self._get_system_specific_data()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(system_data.encode()))
        self._fernet = Fernet(key)
    
    def _get_system_specific_data(self) -> str:
        """
        Get system-specific data for key derivation.
        This helps tie the encryption to the specific system.
        """
        # Use machine-specific data that's relatively stable
        import platform
        system_info = [
            platform.node(),  # Computer network name
            platform.machine(),  # Machine type
            platform.processor(),  # Processor type
            platform.system(),  # OS name
        ]
        return ":".join(system_info)
    
    def store_email_credentials(self, email: str, credentials: Dict[str, str]):
        """
        Securely store email account credentials.
        
        Args:
            email (str): Email address as identifier
            credentials (dict): Dictionary containing credentials
        """
        # Encrypt credentials before storing
        encrypted_data = self._fernet.encrypt(json.dumps(credentials).encode())
        keyring.set_password(self.EMAIL_SERVICE, email, encrypted_data.decode())
    
    def get_email_credentials(self, email: str) -> Optional[Dict[str, str]]:
        """
        Retrieve email account credentials.
        
        Args:
            email (str): Email address as identifier
        
        Returns:
            dict: Dictionary containing credentials or None if not found
        """
        try:
            encrypted_data = keyring.get_password(self.EMAIL_SERVICE, email)
            if encrypted_data:
                decrypted_data = self._fernet.decrypt(encrypted_data.encode())
                return json.loads(decrypted_data)
        except Exception as e:
            print(f"Error retrieving credentials: {str(e)}")
        return None
    
    def delete_email_credentials(self, email: str):
        """
        Delete email account credentials.
        
        Args:
            email (str): Email address as identifier
        """
        try:
            keyring.delete_password(self.EMAIL_SERVICE, email)
        except keyring.errors.PasswordDeleteError:
            pass  # Ignore if credentials don't exist
    
    def store_api_key(self, api_name: str, api_key: str):
        """
        Securely store API key.
        
        Args:
            api_name (str): Name of the API (e.g., 'gemini')
            api_key (str): The API key to store
        """
        encrypted_key = self._fernet.encrypt(api_key.encode())
        keyring.set_password(self.API_SERVICE, api_name, encrypted_key.decode())
    
    def get_api_key(self, api_name: str) -> Optional[str]:
        """
        Retrieve API key.
        
        Args:
            api_name (str): Name of the API (e.g., 'gemini')
        
        Returns:
            str: The API key or None if not found
        """
        try:
            encrypted_key = keyring.get_password(self.API_SERVICE, api_name)
            if encrypted_key:
                return self._fernet.decrypt(encrypted_key.encode()).decode()
            return None
        except Exception as e:
            print(f"Error retrieving API key: {str(e)}")
            return None
    
    def clear_api_key(self, api_name: str):
        """
        Clear the stored API key.
        
        Args:
            api_name (str): Name of the API to clear
        """
        try:
            keyring.delete_password(self.API_SERVICE, api_name)
        except keyring.errors.PasswordDeleteError:
            pass  # Key doesn't exist, which is fine
    
    def delete_api_key(self, api_name: str):
        """
        Delete API key.
        
        Args:
            api_name (str): Name of the API
        """
        try:
            keyring.delete_password(self.API_SERVICE, api_name)
        except keyring.errors.PasswordDeleteError:
            pass  # Ignore if key doesn't exist 