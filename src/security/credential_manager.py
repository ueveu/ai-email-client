import keyring
import json
from pathlib import Path
from cryptography.fernet import Fernet
from base64 import b64encode, b64decode

class CredentialManager:
    """
    Manages secure storage and retrieval of email credentials
    using system keyring and encryption.
    """
    
    def __init__(self):
        """Initialize the credential manager."""
        self.app_name = "AIEmailAssistant"
        self.key_file = Path.home() / ".ai-email-assistant" / "encryption.key"
        self._ensure_encryption_key()
    
    def _ensure_encryption_key(self):
        """Ensure encryption key exists or create a new one."""
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.key_file.exists():
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
        
        # Load the key
        with open(self.key_file, 'rb') as f:
            self.key = f.read()
        
        self.fernet = Fernet(self.key)
    
    def _encrypt(self, data):
        """
        Encrypt data.
        
        Args:
            data (str): Data to encrypt
        
        Returns:
            str: Encrypted data in base64 format
        """
        return b64encode(
            self.fernet.encrypt(data.encode())
        ).decode()
    
    def _decrypt(self, encrypted_data):
        """
        Decrypt data.
        
        Args:
            encrypted_data (str): Encrypted data in base64 format
        
        Returns:
            str: Decrypted data
        """
        return self.fernet.decrypt(
            b64decode(encrypted_data.encode())
        ).decode()
    
    def store_email_credentials(self, email, credentials):
        """
        Store email credentials securely.
        
        Args:
            email (str): Email address
            credentials (dict): Credentials to store
        """
        # Encrypt credentials
        encrypted_data = self._encrypt(json.dumps(credentials))
        
        # Store in system keyring
        keyring.set_password(self.app_name, email, encrypted_data)
    
    def get_email_credentials(self, email):
        """
        Retrieve email credentials.
        
        Args:
            email (str): Email address
        
        Returns:
            dict: Credentials or None if not found
        """
        # Get from system keyring
        encrypted_data = keyring.get_password(self.app_name, email)
        if not encrypted_data:
            return None
        
        try:
            # Decrypt and parse
            decrypted_data = self._decrypt(encrypted_data)
            return json.loads(decrypted_data)
        except:
            return None
    
    def delete_email_credentials(self, email):
        """
        Delete email credentials.
        
        Args:
            email (str): Email address
        """
        try:
            keyring.delete_password(self.app_name, email)
        except keyring.errors.PasswordDeleteError:
            pass  # Already deleted or not found 