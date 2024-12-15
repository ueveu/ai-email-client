"""
Service for secure storage and management of user credentials using the system keyring.
"""

import keyring
import json
from typing import Dict, Optional, List
from pathlib import Path
import os
from datetime import datetime, timedelta
from utils.logger import logger
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend
import base64
from base64 import b64encode, b64decode
import secrets
import hashlib
from utils.crypto import Crypto

class CredentialService:
    """Service for securely managing user credentials using the system keyring."""
    
    # Constants for keyring service names
    KEYRING_SERVICE = "ai_email_assistant"
    MASTER_KEY_NAME = "master_encryption_key"
    KEY_VERSION_NAME = "key_version"
    SALT_NAME = "encryption_salt"
    TOKEN_REFRESH_THRESHOLD = timedelta(minutes=5)  # Refresh tokens 5 minutes before expiry
    KEY_ROTATION_INTERVAL = timedelta(days=30)  # Rotate keys every 30 days
    PBKDF2_ITERATIONS = 600000  # Increased from 100000
    
    # Service names for keyring
    OAUTH_SERVICE = 'ai_email_assistant_oauth'
    PASSWORD_SERVICE = 'ai_email_assistant_password'
    
    def __init__(self):
        """Initialize the credential service."""
        self.crypto = Crypto()
        
        # Ensure data directories exist
        self.data_dir = Path.home() / '.ai_email_assistant'
        self.cred_dir = self.data_dir / 'credentials'
        self.oauth_dir = self.data_dir / 'oauth'
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cred_dir.mkdir(parents=True, exist_ok=True)
        self.oauth_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug("Initialized credential service")
        
        self._ensure_master_key()
        self._fernet = None  # Lazy initialization of encryption
        
        # Ensure data directory exists
        self.data_dir = Path.home() / '.ai_email_assistant' / 'credentials'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if key rotation is needed
        self._check_key_rotation()
    
    def _generate_salt(self) -> bytes:
        """Generate a cryptographically secure salt."""
        return secrets.token_bytes(32)  # Increased from 16 bytes
    
    def _derive_key(self, master_key: str, salt: bytes) -> bytes:
        """
        Derive encryption key using both PBKDF2 and Scrypt for additional security.
        
        Args:
            master_key (str): Master key to derive from
            salt (bytes): Salt for key derivation
            
        Returns:
            bytes: Derived key
        """
        # First derive with PBKDF2
        pbkdf2 = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.PBKDF2_ITERATIONS,
            backend=default_backend()
        )
        intermediate_key = pbkdf2.derive(master_key.encode())
        
        # Then with Scrypt for memory-hardness
        scrypt = Scrypt(
            salt=salt,
            length=32,
            n=2**14,  # CPU/memory cost
            r=8,      # Block size
            p=1,      # Parallelization factor
            backend=default_backend()
        )
        final_key = scrypt.derive(intermediate_key)
        
        return base64.urlsafe_b64encode(final_key)
    
    def _ensure_master_key(self):
        """Ensure master encryption key exists and is properly versioned."""
        master_key = keyring.get_password(self.KEYRING_SERVICE, self.MASTER_KEY_NAME)
        key_version = keyring.get_password(self.KEYRING_SERVICE, self.KEY_VERSION_NAME)
        
        if not master_key or not key_version:
            # Generate new master key with version
            master_key = secrets.token_urlsafe(32)
            key_version = datetime.now().isoformat()
            
            # Store with version
            keyring.set_password(self.KEYRING_SERVICE, self.MASTER_KEY_NAME, master_key)
            keyring.set_password(self.KEYRING_SERVICE, self.KEY_VERSION_NAME, key_version)
            
            # Generate and store new salt
            salt = self._generate_salt()
            keyring.set_password(self.KEYRING_SERVICE, self.SALT_NAME, b64encode(salt).decode())
    
    def _check_key_rotation(self):
        """Check if key rotation is needed and perform if necessary."""
        try:
            key_version = keyring.get_password(self.KEYRING_SERVICE, self.KEY_VERSION_NAME)
            if key_version:
                last_rotation = datetime.fromisoformat(key_version)
                if datetime.now() - last_rotation >= self.KEY_ROTATION_INTERVAL:
                    self._rotate_keys()
        except Exception as e:
            logger.error(f"Error checking key rotation: {str(e)}")
    
    def _rotate_keys(self):
        """Perform key rotation and re-encrypt all credentials."""
        try:
            # Store old key and Fernet instance
            old_fernet = self.fernet
            
            # Generate new master key and salt
            new_master_key = secrets.token_urlsafe(32)
            new_salt = self._generate_salt()
            new_version = datetime.now().isoformat()
            
            # Create new Fernet instance
            new_key = self._derive_key(new_master_key, new_salt)
            new_fernet = Fernet(new_key)
            
            # Re-encrypt all credentials
            for cred_file in self.data_dir.glob("*.enc"):
                try:
                    # Read and decrypt with old key
                    with open(cred_file, 'rb') as f:
                        encrypted_data = f.read()
                    decrypted_data = old_fernet.decrypt(encrypted_data)
                    
                    # Re-encrypt with new key
                    new_encrypted_data = new_fernet.encrypt(decrypted_data)
                    
                    # Write back
                    with open(cred_file, 'wb') as f:
                        f.write(new_encrypted_data)
                except Exception as e:
                    logger.error(f"Error rotating key for {cred_file}: {str(e)}")
                    continue
            
            # Store new master key and version
            keyring.set_password(self.KEYRING_SERVICE, self.MASTER_KEY_NAME, new_master_key)
            keyring.set_password(self.KEYRING_SERVICE, self.KEY_VERSION_NAME, new_version)
            keyring.set_password(self.KEYRING_SERVICE, self.SALT_NAME, b64encode(new_salt).decode())
            
            # Reset Fernet instance
            self._fernet = None
            
            logger.info("Key rotation completed successfully")
            
        except Exception as e:
            logger.error(f"Error during key rotation: {str(e)}")
            raise
    
    @property
    def fernet(self) -> Fernet:
        """Get or create the Fernet instance for encryption/decryption."""
        if self._fernet is None:
            try:
                master_key = keyring.get_password(self.KEYRING_SERVICE, self.MASTER_KEY_NAME)
                salt = b64decode(keyring.get_password(self.KEYRING_SERVICE, self.SALT_NAME))
                
                if not master_key or not salt:
                    raise ValueError("Missing master key or salt")
                
                # Derive key using enhanced key derivation
                key = self._derive_key(master_key, salt)
                self._fernet = Fernet(key)
                
            except Exception as e:
                logger.error(f"Error initializing Fernet: {str(e)}")
                raise
        
        return self._fernet
    
    def _get_credential_path(self, email: str) -> Path:
        """Get the path for storing credentials for an email account."""
        # Use SHA-256 hash of email for filename
        email_hash = hashlib.sha256(email.encode()).hexdigest()
        return self.data_dir / f"{email_hash}.enc"
    
    def store_account_credentials(self, email: str, credentials: dict, provider: str = None) -> bool:
        """
        Store credentials for an email account.
        
        Args:
            email: Email address
            credentials: Credentials dictionary (either OAuth tokens or password)
            provider: Optional provider name
            
        Returns:
            bool: True if stored successfully
        """
        try:
            if 'access_token' in credentials:
                # Store OAuth tokens
                self.store_oauth_tokens(email, credentials)
                logger.info(f"Stored credentials for {email}")
                return True
            elif 'password' in credentials:
                # Store password
                self.store_password(email, credentials['password'])
                logger.info(f"Stored credentials for {email}")
                return True
            else:
                logger.error(f"Invalid credentials format for {email}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing credentials for {email}: {str(e)}")
            return False
    
    def get_account_credentials(self, email: str) -> Optional[Dict]:
        """
        Retrieve credentials for an email account.
        
        Args:
            email (str): Email address to get credentials for
            
        Returns:
            Dict: Decrypted credentials dictionary or None if not found
        """
        try:
            cred_path = self._get_credential_path(email)
            if not cred_path.exists():
                return None
            
            # Read and decrypt credentials from file
            with open(cred_path, 'rb') as f:
                encrypted_creds = f.read()
            
            # Decrypt credentials
            decrypted_json = self.fernet.decrypt(encrypted_creds)
            credentials = json.loads(decrypted_json)
            
            # Check OAuth token expiry
            if 'access_token' in credentials and 'expires_at' in credentials:
                expires_at = datetime.fromisoformat(credentials['expires_at'])
                if datetime.now() + self.TOKEN_REFRESH_THRESHOLD >= expires_at:
                    logger.info(f"OAuth token for {email} needs refresh")
                    credentials['needs_refresh'] = True
            
            return credentials
            
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
            cred_path = self._get_credential_path(email)
            if cred_path.exists():
                cred_path.unlink()
            self._delete_account_metadata(email)
            logger.info(f"Deleted credentials for {email}")
            
        except Exception as e:
            logger.error(f"Error deleting credentials for {email}: {str(e)}")
            raise
    
    def _store_account_metadata(self, email: str, provider: Optional[str] = None):
        """Store non-sensitive account metadata."""
        try:
            metadata_path = self._get_metadata_path()
            metadata = self._load_account_metadata()
            
            metadata[email] = {
                'provider': provider,
                'last_used': datetime.now().isoformat()
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
        return str(self.data_dir / 'account_metadata.json')
    
    def verify_credentials(self, email: str) -> bool:
        """
        Verify that credentials exist and are valid for an account.
        
        Args:
            email (str): Email address to verify
            
        Returns:
            bool: True if credentials exist and are valid
        """
        try:
            credentials = self.get_account_credentials(email)
            if not credentials:
                return False
            
            # For OAuth accounts, check if tokens need refresh
            if 'access_token' in credentials:
                return not credentials.get('needs_refresh', False)
            
            # For password-based accounts, just check if password exists
            return 'password' in credentials
            
        except Exception as e:
            logger.error(f"Error verifying credentials for {email}: {str(e)}")
            return False
    
    def get_email_credentials(self, email: str) -> Optional[dict]:
        """
        Get credentials for an email account.
        
        Args:
            email: Email address
            
        Returns:
            dict: Credentials dictionary or None if not found
        """
        try:
            # Check if we have OAuth tokens
            oauth_tokens = self.get_oauth_tokens(email)
            if oauth_tokens:
                return {
                    'type': 'oauth',
                    'tokens': oauth_tokens
                }
            
            # Check for stored password
            password = self.get_password(email)
            if password:
                return {
                    'type': 'password',
                    'password': password
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting credentials for {email}: {str(e)}")
            return None
    
    def get_oauth_tokens(self, email: str) -> Optional[dict]:
        """Get OAuth tokens for an email account."""
        try:
            # Get token file path
            token_file = self.oauth_dir / f"{email}.json"
            if not token_file.exists():
                return None
            
            # Read and decrypt tokens
            with open(token_file, 'r') as f:
                encrypted_data = f.read()
            
            # Decrypt and parse tokens
            decrypted_data = self.crypto.decrypt(encrypted_data)
            return json.loads(decrypted_data)
            
        except Exception as e:
            logger.error(f"Error getting OAuth tokens for {email}: {str(e)}")
            return None
    
    def store_oauth_tokens(self, email: str, tokens: dict) -> bool:
        """Store OAuth tokens for an email account."""
        try:
            # Encrypt tokens
            encrypted_data = self.crypto.encrypt(json.dumps(tokens))
            
            # Store in file
            token_file = self.oauth_dir / f"{email}.json"
            with open(token_file, 'w') as f:
                f.write(encrypted_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing OAuth tokens for {email}: {str(e)}")
            return False
    
    def get_password(self, email: str) -> Optional[str]:
        """Get password for an email account."""
        try:
            # Get password file path
            pass_file = self.cred_dir / f"{email}.pwd"
            if not pass_file.exists():
                return None
            
            # Read and decrypt password
            with open(pass_file, 'r') as f:
                encrypted_data = f.read()
            
            return self.crypto.decrypt(encrypted_data)
            
        except Exception as e:
            logger.error(f"Error getting password for {email}: {str(e)}")
            return None
    
    def store_password(self, email: str, password: str) -> bool:
        """Store password for an email account."""
        try:
            # Encrypt password
            encrypted_data = self.crypto.encrypt(password)
            
            # Store in file
            pass_file = self.cred_dir / f"{email}.pwd"
            with open(pass_file, 'w') as f:
                f.write(encrypted_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing password for {email}: {str(e)}")
            return False
    
    def update_token_expiry(self, email: str, expires_in: int):
        """
        Update the expiry time for OAuth tokens.
        
        Args:
            email (str): Email address of the account
            expires_in (int): Number of seconds until token expires
        """
        try:
            # Get existing credentials
            credentials = self.get_account_credentials(email)
            if not credentials:
                logger.error(f"No credentials found for {email}")
                return
            
            # Update expiry times
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            credentials['expires_at'] = expires_at.isoformat()
            credentials['expires_in'] = expires_in
            credentials['_metadata']['last_modified'] = datetime.now().isoformat()
            
            # Re-encrypt and store updated credentials
            creds_json = json.dumps(credentials)
            encrypted_creds = self.fernet.encrypt(creds_json.encode())
            
            cred_path = self._get_credential_path(email)
            with open(cred_path, 'wb') as f:
                f.write(encrypted_creds)
            
            logger.debug(f"Updated token expiry for {email}")
            
        except Exception as e:
            logger.error(f"Error updating token expiry for {email}: {str(e)}")
            raise 