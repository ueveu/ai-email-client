"""
Service for secure storage and management of user credentials using the system keyring.
"""

import keyring
import json
from typing import Dict, Optional, List
from pathlib import Path
import os
from utils.logger import logger
from cryptography.fernet import Fernet
from base64 import b64encode, b64decode

class CredentialService:
    """Service for securely managing user credentials using the system keyring."""
    
    # Constants for keyring service names
    KEYRING_SERVICE = "ai_email_assistant"
    MASTER_KEY_NAME = "master_encryption_key"
    
    def __init__(self):
        """Initialize the credential service."""
        self._ensure_master_key()
        self._fernet = None  # Lazy initialization of encryption
    
    def _ensure_master_key(self):
        """Ensure master encryption key exists in the keyring."""
        master_key = keyring.get_password(self.KEYRING_SERVICE, self.MASTER_KEY_NAME)
        if not master_key:
            # Generate new master key
            master_key = Fernet.generate_key().decode()
            keyring.set_password(self.KEYRING_SERVICE, self.MASTER_KEY_NAME, master_key)
    
    @property
    def fernet(self) -> Fernet:
        """Get or create the Fernet instance for encryption/decryption."""
        if self._fernet is None:
            master_key = keyring.get_password(self.KEYRING_SERVICE, self.MASTER_KEY_NAME)
            self._fernet = Fernet(master_key.encode())
        return self._fernet
    
    def store_account_credentials(self, 
                                email: str, 
                                credentials: Dict,
                                provider: Optional[str] = None):
        """
        Securely store email account credentials.
        
        Args:
            email (str): Email address as the identifier
            credentials (Dict): Dictionary containing credentials (password, tokens, etc.)
            provider (str, optional): Email provider name
        """
        try:
            # Encrypt credentials
            creds_json = json.dumps(credentials)
            encrypted_creds = self.fernet.encrypt(creds_json.encode())
            
            # Store in keyring
            keyring.set_password(
                self.KEYRING_SERVICE,
                f"email_{email}",
                b64encode(encrypted_creds).decode()
            )
            
            # Store metadata separately
            self._store_account_metadata(email, provider)
            
            logger.info(f"Stored credentials for {email}")
            
        except Exception as e:
            logger.error(f"Error storing credentials for {email}: {str(e)}")
            raise
    
    def get_account_credentials(self, email: str) -> Optional[Dict]:
        """
        Retrieve credentials for an email account.
        
        Args:
            email (str): Email address to get credentials for
            
        Returns:
            Dict: Decrypted credentials dictionary or None if not found
        """
        try:
            encrypted_creds = keyring.get_password(self.KEYRING_SERVICE, f"email_{email}")
            if not encrypted_creds:
                return None
            
            # Decrypt credentials
            decrypted_json = self.fernet.decrypt(b64decode(encrypted_creds))
            return json.loads(decrypted_json)
            
        except Exception as e:
            logger.error(f"Error retrieving credentials for {email}: {str(e)}")
            return None
    
    def delete_account_credentials(self, email: str):
        """
        Delete stored credentials for an email account.
        
        Args:
            email (str): Email address to delete credentials for
        """
        try:
            keyring.delete_password(self.KEYRING_SERVICE, f"email_{email}")
            self._delete_account_metadata(email)
            logger.info(f"Deleted credentials for {email}")
            
        except Exception as e:
            logger.error(f"Error deleting credentials for {email}: {str(e)}")
            raise
    
    def update_account_credentials(self,
                                 email: str,
                                 credentials: Dict,
                                 provider: Optional[str] = None):
        """
        Update stored credentials for an email account.
        
        Args:
            email (str): Email address to update credentials for
            credentials (Dict): New credentials dictionary
            provider (str, optional): Email provider name
        """
        try:
            self.delete_account_credentials(email)
            self.store_account_credentials(email, credentials, provider)
            logger.info(f"Updated credentials for {email}")
            
        except Exception as e:
            logger.error(f"Error updating credentials for {email}: {str(e)}")
            raise
    
    def list_accounts(self) -> List[Dict]:
        """
        Get list of stored email accounts with metadata.
        
        Returns:
            List[Dict]: List of account information dictionaries
        """
        try:
            accounts = []
            metadata = self._load_account_metadata()
            
            for email, info in metadata.items():
                account_info = {
                    'email': email,
                    'provider': info.get('provider', 'unknown'),
                    'last_used': info.get('last_used'),
                    'has_credentials': bool(self.get_account_credentials(email))
                }
                accounts.append(account_info)
            
            return accounts
            
        except Exception as e:
            logger.error(f"Error listing accounts: {str(e)}")
            return []
    
    def _store_account_metadata(self, email: str, provider: Optional[str] = None):
        """Store non-sensitive account metadata."""
        try:
            metadata_path = self._get_metadata_path()
            metadata = self._load_account_metadata()
            
            metadata[email] = {
                'provider': provider,
                'last_used': str(datetime.now())
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
                
        except Exception as e:
            logger.error(f"Error storing account metadata: {str(e)}")
    
    def _delete_account_metadata(self, email: str):
        """Delete account metadata."""
        try:
            metadata_path = self._get_metadata_path()
            metadata = self._load_account_metadata()
            
            if email in metadata:
                del metadata[email]
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f)
                    
        except Exception as e:
            logger.error(f"Error deleting account metadata: {str(e)}")
    
    def _load_account_metadata(self) -> Dict:
        """Load account metadata from file."""
        try:
            metadata_path = self._get_metadata_path()
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            return {}
            
        except Exception as e:
            logger.error(f"Error loading account metadata: {str(e)}")
            return {}
    
    def _get_metadata_path(self) -> str:
        """Get path to metadata file."""
        data_dir = Path.home() / '.ai_email_assistant' / 'data'
        data_dir.mkdir(parents=True, exist_ok=True)
        return str(data_dir / 'account_metadata.json')
    
    def verify_credentials(self, email: str) -> bool:
        """
        Verify that credentials exist and are valid for an account.
        
        Args:
            email (str): Email address to verify
            
        Returns:
            bool: True if credentials exist and are valid
        """
        try:
            creds = self.get_account_credentials(email)
            return bool(creds)  # Basic verification
            
        except Exception as e:
            logger.error(f"Error verifying credentials for {email}: {str(e)}")
            return False 