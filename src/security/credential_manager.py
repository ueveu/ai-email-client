import keyring
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
from utils.logger import logger
from utils.error_handler import handle_errors, collect_errors, ErrorCollection

class CredentialManager:
    """Manages secure storage and retrieval of email credentials."""
    
    def __init__(self):
        self.service_name = "ai-email-assistant"
        self.oauth_dir = Path.home() / ".ai-email-assistant" / "oauth"
        self.oauth_dir.mkdir(parents=True, exist_ok=True)
    
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
                keyring.set_password(self.service_name, email, password)
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
                return keyring.get_password(self.service_name, email)
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
            tokens['stored_at'] = datetime.now().isoformat()
            if 'expires_in' in tokens:
                expires_at = datetime.now() + timedelta(seconds=int(tokens['expires_in']))
                tokens['expires_at'] = expires_at.isoformat()
            
            token_file.write_text(json.dumps(tokens))
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
    def update_token_expiry(self, email: str, expires_in: int) -> bool:
        """
        Update the expiry time for OAuth tokens.
        
        Args:
            email (str): Email address
            expires_in (int): Seconds until token expires
            
        Returns:
            bool: True if update was successful
        """
        try:
            token_file = self.oauth_dir / f"{email}.json"
            if not token_file.exists():
                logger.error(f"No OAuth tokens found for {email}")
                return False
            
            tokens = json.loads(token_file.read_text())
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            tokens['expires_at'] = expires_at.isoformat()
            tokens['stored_at'] = datetime.now().isoformat()
            token_file.write_text(json.dumps(tokens))
            return True
            
        except Exception as e:
            logger.error(f"Failed to update token expiry: {str(e)}")
            return False
    
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
            keyring.set_password(self.service_name, email, json.dumps(credentials))
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
                return None
            return json.loads(creds_json)
            
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
        
        # Remove email credentials
        try:
            keyring.delete_password(self.service_name, email)
        except keyring.errors.PasswordDeleteError:
            # Ignore if password doesn't exist
            pass
        
        # Remove OAuth tokens
        token_file = self.oauth_dir / f"{email}.json"
        if token_file.exists():
            try:
                token_file.unlink()
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
                token_file.unlink()
        except Exception as e:
            logger.error(f"Failed to clear OAuth tokens: {str(e)}")
            success = False
        
        return success
    
    @handle_errors
    def verify_credentials(self, email: str) -> bool:
        """
        Verify if credentials exist for an email account.
        
        Args:
            email (str): Email address
            
        Returns:
            bool: True if valid credentials exist
        """
        # Check for OAuth tokens
        tokens = self.get_oauth_tokens(email)
        if tokens and 'access_token' in tokens:
            return True
        
        # Check for password
        credentials = self.get_email_credentials(email)
        if credentials and 'password' in credentials:
            return True
        
        return False