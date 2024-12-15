import base64
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from utils.logger import logger

class Crypto:
    """Utility class for encryption and decryption."""
    
    def __init__(self):
        """Initialize the crypto utility."""
        self._fernet = None
        self._key_file = Path.home() / '.ai_email_assistant' / 'crypto' / 'key.bin'
        self._initialize_key()
    
    def _initialize_key(self):
        """Initialize encryption key."""
        try:
            # Create key directory if needed
            self._key_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load or generate key
            if self._key_file.exists():
                with open(self._key_file, 'rb') as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                with open(self._key_file, 'wb') as f:
                    f.write(key)
            
            self._fernet = Fernet(key)
            
        except Exception as e:
            logger.error(f"Error initializing crypto key: {str(e)}")
            raise
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.
        
        Args:
            data: String to encrypt
            
        Returns:
            str: Encrypted data as base64 string
        """
        try:
            encrypted = self._fernet.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {str(e)}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt a string.
        
        Args:
            encrypted_data: Base64 encoded encrypted string
            
        Returns:
            str: Decrypted string
        """
        try:
            encrypted = base64.b64decode(encrypted_data)
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            raise 