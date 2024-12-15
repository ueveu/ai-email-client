"""
Service for secure storage and management of user credentials using the system keyring.
"""

import keyring
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
from utils.logger import logger
from utils.error_handler import handle_errors, collect_errors, ErrorCollection
import sys
import os

class CredentialService:
    """Manages secure storage and retrieval of email credentials."""
    
    def __init__(self):
        """Initialize credential service."""
        self.service_name = "ai-email-assistant"
        self.oauth_dir = Path.home() / ".ai-email-assistant" / "oauth"
        self.oauth_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize keyring backend
        self._initialize_keyring()
    
    def _initialize_keyring(self):
        """Initialize the appropriate keyring backend."""
        try:
            # Check if we're on Windows
            if sys.platform == 'win32':
                try:
                    # Try to import Windows-specific backend
                    from keyring.backends import Windows
                    kr = Windows.WinVaultKeyring()
                    keyring.set_keyring(kr)
                    logger.info("Using Windows Credential Manager for secure storage")
                except Exception as e:
                    logger.error(f"Failed to initialize Windows keyring: {str(e)}")
                    self._use_fallback_keyring()
            else:
                # Let keyring choose the best backend for the platform
                kr = keyring.get_keyring()
                logger.info(f"Using {kr.__class__.__name__} for secure storage")
        except Exception as e:
            logger.error(f"Error initializing keyring: {str(e)}")
            self._use_fallback_keyring()
    
    def _use_fallback_keyring(self):
        """Use a fallback keyring backend if the preferred one fails."""
        try:
            from keyring.backends import fail
            kr = fail.Keyring()
            keyring.set_keyring(kr)
            logger.warning("Using fallback keyring - credentials will not be secure!")
        except Exception as e:
            logger.error(f"Failed to initialize fallback keyring: {str(e)}")
    
    @handle_errors
    def store_password(self, email: str, password: str, error_collection: Optional[ErrorCollection] = None) -> bool:
        """
        Store email password securely.
        
        Args:
            email (str): Email address
            password (str): Password to store
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            bool: True if password was stored successfully
        """
        try:
            @collect_errors(error_collection, "Store Password")
            def store():
                credentials = {
                    'type': 'password',
                    'password': password
                }
                keyring.set_password(self.service_name, email, json.dumps(credentials))
                logger.debug(f"Stored password for {email}")
                return True
            return store()
            
        except Exception as e:
            if error_collection:
                error_collection.add(f"Failed to store password: {str(e)}")
            logger.error(f"Failed to store password: {str(e)}")
            return False
    
    @handle_errors
    def get_password(self, email: str, error_collection: Optional[ErrorCollection] = None) -> Optional[str]:
        """
        Retrieve stored email password.
        
        Args:
            email (str): Email address
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            Optional[str]: Password if found
        """
        try:
            @collect_errors(error_collection, "Get Password")
            def get():
                creds_json = keyring.get_password(self.service_name, email)
                if not creds_json:
                    logger.debug(f"No password found for {email}")
                    return None
                credentials = json.loads(creds_json)
                return credentials.get('password') if credentials.get('type') == 'password' else None
            return get()
            
        except Exception as e:
            if error_collection:
                error_collection.add(f"Failed to get password: {str(e)}")
            logger.error(f"Failed to get password: {str(e)}")
            return None
    
    @handle_errors
    def store_oauth_tokens(self, email: str, tokens: Dict) -> bool:
        """
        Store OAuth tokens securely.
        
        Args:
            email (str): Email address
            tokens (Dict): OAuth tokens to store
            
        Returns:
            bool: True if tokens were stored successfully
        """
        try:
            token_file = self.oauth_dir / f"{email}.json"
            
            # Add timestamp and expiry info
            tokens['type'] = 'oauth'
            tokens['stored_at'] = datetime.now().isoformat()
            if 'expires_in' in tokens:
                expires_at = datetime.now() + timedelta(seconds=int(tokens['expires_in']))
                tokens['expires_at'] = expires_at.isoformat()
            
            token_file.write_text(json.dumps(tokens))
            logger.debug(f"Stored OAuth tokens for {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store OAuth tokens: {str(e)}")
            return False
    
    @handle_errors
    def get_oauth_tokens(self, email: str) -> Optional[Dict]:
        """
        Retrieve stored OAuth tokens.
        
        Args:
            email (str): Email address
            
        Returns:
            Optional[Dict]: OAuth tokens if found
        """
        try:
            token_file = self.oauth_dir / f"{email}.json"
            if not token_file.exists():
                logger.debug(f"No OAuth tokens found for {email}")
                return None
            
            tokens = json.loads(token_file.read_text())
            
            # Check token expiry
            if 'expires_at' in tokens:
                expires_at = datetime.fromisoformat(tokens['expires_at'])
                if datetime.now() >= expires_at:
                    logger.info(f"OAuth tokens expired for {email}")
                    return None
            
            return tokens
            
        except Exception as e:
            logger.error(f"Failed to get OAuth tokens: {str(e)}")
            return None
    
    @handle_errors
    def store_email_credentials(self, email: str, credentials: Dict) -> bool:
        """
        Store email credentials securely.
        
        Args:
            email (str): Email address
            credentials (Dict): Credentials to store
            
        Returns:
            bool: True if credentials were stored successfully
        """
        try:
            # Ensure credentials have a type field
            if 'access_token' in credentials:
                credentials['type'] = 'oauth'
            elif 'password' in credentials:
                credentials['type'] = 'password'
            else:
                raise ValueError("Invalid credentials format: missing type identifier")
            
            # Store in Windows Credential Manager
            keyring.set_password(self.service_name, email, json.dumps(credentials))
            logger.debug(f"Stored credentials for {email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store email credentials: {str(e)}")
            return False
    
    @handle_errors
    def get_email_credentials(self, email: str) -> Optional[Dict]:
        """
        Retrieve stored email credentials.
        
        Args:
            email (str): Email address
            
        Returns:
            Optional[Dict]: Credentials if found
        """
        try:
            creds_json = keyring.get_password(self.service_name, email)
            if not creds_json:
                logger.debug(f"No credentials found for {email}")
                return None
            
            credentials = json.loads(creds_json)
            logger.debug(f"Retrieved credentials for {email}")
            return credentials
            
        except Exception as e:
            logger.error(f"Failed to get email credentials: {str(e)}")
            return None
    
    @handle_errors
    def remove_credentials(self, email: str) -> bool:
        """
        Remove all stored credentials for an email account.
        
        Args:
            email (str): Email address
            
        Returns:
            bool: True if all credentials were removed successfully
        """
        success = True
        
        # Remove email credentials from keyring
        try:
            keyring.delete_password(self.service_name, email)
            logger.debug(f"Removed credentials for {email} from keyring")
        except keyring.errors.PasswordDeleteError:
            # Ignore if password doesn't exist
            pass
        except Exception as e:
            logger.error(f"Failed to remove credentials from keyring: {str(e)}")
            success = False
        
        # Remove OAuth tokens
        token_file = self.oauth_dir / f"{email}.json"
        if token_file.exists():
            try:
                token_file.unlink()
                logger.debug(f"Removed OAuth tokens for {email}")
            except Exception as e:
                logger.error(f"Failed to remove OAuth tokens: {str(e)}")
                success = False
        
        return success
    
    @handle_errors
    def clear_all_credentials(self) -> bool:
        """
        Remove all stored credentials.
        
        Returns:
            bool: True if all credentials were cleared successfully
        """
        success = True
        
        # Clear OAuth tokens
        try:
            for token_file in self.oauth_dir.glob("*.json"):
                try:
                    token_file.unlink()
                    logger.debug(f"Removed OAuth token file: {token_file}")
                except Exception as e:
                    logger.error(f"Failed to remove OAuth token file {token_file}: {str(e)}")
                    success = False
        except Exception as e:
            logger.error(f"Failed to clear OAuth tokens: {str(e)}")
            success = False
        
        return success