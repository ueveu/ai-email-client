import keyring
import json
from pathlib import Path
from typing import Dict, Optional
from utils.logger import logger
from utils.error_handler import ErrorCollection, handle_errors, collect_errors

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
            logger.logger.error(f"Failed to store password: {str(e)}")
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
            logger.logger.error(f"Failed to get password: {str(e)}")
            return None
    
    @handle_errors
    def store_oauth_tokens(self, email: str, tokens: Dict, error_collection: Optional[ErrorCollection] = None) -> bool:
        """
        Store OAuth tokens securely.
        
        Args:
            email (str): Email address
            tokens (Dict): OAuth tokens to store
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            bool: True if tokens were stored successfully
        """
        try:
            token_file = self.oauth_dir / f"{email}.json"
            
            @collect_errors(error_collection, "Store OAuth Tokens")
            def store():
                token_file.write_text(json.dumps(tokens))
                return True
            return store()
            
        except Exception as e:
            if error_collection:
                error_collection.add(f"Failed to store OAuth tokens: {str(e)}")
            logger.logger.error(f"Failed to store OAuth tokens: {str(e)}")
            return False
    
    @handle_errors
    def get_oauth_tokens(self, email: str, error_collection: Optional[ErrorCollection] = None) -> Optional[Dict]:
        """
        Retrieve stored OAuth tokens.
        
        Args:
            email (str): Email address
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            Optional[Dict]: OAuth tokens if found
        """
        try:
            token_file = self.oauth_dir / f"{email}.json"
            if not token_file.exists():
                if error_collection:
                    error_collection.add(f"No OAuth tokens found for {email}")
                return None
            
            @collect_errors(error_collection, "Get OAuth Tokens")
            def get():
                return json.loads(token_file.read_text())
            return get()
            
        except Exception as e:
            if error_collection:
                error_collection.add(f"Failed to get OAuth tokens: {str(e)}")
            logger.logger.error(f"Failed to get OAuth tokens: {str(e)}")
            return None
    
    @handle_errors
    def remove_credentials(self, email: str, error_collection: Optional[ErrorCollection] = None) -> bool:
        """
        Remove all stored credentials for an email account.
        
        Args:
            email (str): Email address
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            bool: True if all credentials were removed successfully
        """
        success = True
        
        # Remove password
        @collect_errors(error_collection, "Remove Password")
        def remove_pass():
            try:
                keyring.delete_password(self.service_name, email)
                return True
            except keyring.errors.PasswordDeleteError:
                # Ignore if password doesn't exist
                return True
        if not remove_pass():
            success = False
        
        # Remove OAuth tokens
        @collect_errors(error_collection, "Remove OAuth Tokens")
        def remove_oauth():
            token_file = self.oauth_dir / f"{email}.json"
            if token_file.exists():
                token_file.unlink()
            return True
        if not remove_oauth():
            success = False
        
        return success
    
    @handle_errors
    def clear_all_credentials(self, error_collection: Optional[ErrorCollection] = None) -> bool:
        """
        Remove all stored credentials.
        
        Args:
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            bool: True if all credentials were cleared successfully
        """
        try:
            # Clear OAuth tokens
            @collect_errors(error_collection, "Clear OAuth Tokens")
            def clear_oauth():
                for token_file in self.oauth_dir.glob("*.json"):
                    token_file.unlink()
                return True
            oauth_success = clear_oauth()
            
            # Clear passwords (implementation depends on keyring backend)
            # Note: This is a best-effort operation as some keyring backends
            # don't support listing or bulk deletion
            password_success = True
            
            return oauth_success and password_success
            
        except Exception as e:
            if error_collection:
                error_collection.add(f"Failed to clear all credentials: {str(e)}")
            logger.logger.error(f"Failed to clear all credentials: {str(e)}")
            return False