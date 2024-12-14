import keyring
import json
from utils.logger import logger
from utils.error_handler import handle_errors

class CredentialManager:
    """Manages secure storage and retrieval of credentials."""
    
    # Service names for different credential types
    EMAIL_SERVICE = "ai_email_client_email"
    OAUTH_SERVICE = "ai_email_client_oauth"
    API_SERVICE = "ai_email_client_api"
    
    @handle_errors
    def store_email_credentials(self, email: str, credentials: dict):
        """
        Store email account credentials securely.
        
        Args:
            email (str): Email address
            credentials (dict): Credentials to store
        """
        try:
            # Store credentials as JSON string
            keyring.set_password(
                self.EMAIL_SERVICE,
                email,
                json.dumps(credentials)
            )
            logger.logger.info(f"Stored credentials for {email}")
        except Exception as e:
            logger.error(f"Failed to store credentials: {str(e)}")
            raise
    
    @handle_errors
    def get_email_credentials(self, email: str) -> dict:
        """
        Retrieve email account credentials.
        
        Args:
            email (str): Email address
        
        Returns:
            dict: Retrieved credentials or None if not found
        """
        try:
            credentials_json = keyring.get_password(self.EMAIL_SERVICE, email)
            if credentials_json:
                return json.loads(credentials_json)
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {str(e)}")
        return None
    
    @handle_errors
    def delete_email_credentials(self, email: str):
        """
        Delete email account credentials.
        
        Args:
            email (str): Email address
        """
        try:
            keyring.delete_password(self.EMAIL_SERVICE, email)
            logger.logger.info(f"Deleted credentials for {email}")
        except Exception as e:
            logger.error(f"Failed to delete credentials: {str(e)}")
            raise
    
    @handle_errors
    def store_oauth_tokens(self, email: str, tokens: dict):
        """
        Store OAuth tokens securely.
        
        Args:
            email (str): Email address
            tokens (dict): OAuth tokens including access_token, refresh_token, etc.
        """
        try:
            keyring.set_password(
                self.OAUTH_SERVICE,
                email,
                json.dumps(tokens)
            )
            logger.logger.info(f"Stored OAuth tokens for {email}")
        except Exception as e:
            logger.error(f"Failed to store OAuth tokens: {str(e)}")
            raise
    
    @handle_errors
    def get_oauth_tokens(self, email: str) -> dict:
        """
        Retrieve OAuth tokens.
        
        Args:
            email (str): Email address
        
        Returns:
            dict: OAuth tokens or None if not found
        """
        try:
            tokens_json = keyring.get_password(self.OAUTH_SERVICE, email)
            if tokens_json:
                return json.loads(tokens_json)
        except Exception as e:
            logger.error(f"Failed to retrieve OAuth tokens: {str(e)}")
        return None
    
    @handle_errors
    def delete_oauth_tokens(self, email: str):
        """
        Delete OAuth tokens.
        
        Args:
            email (str): Email address
        """
        try:
            keyring.delete_password(self.OAUTH_SERVICE, email)
            logger.logger.info(f"Deleted OAuth tokens for {email}")
        except Exception as e:
            logger.error(f"Failed to delete OAuth tokens: {str(e)}")
            raise
    
    @handle_errors
    def store_api_key(self, service: str, api_key: str):
        """
        Store API key securely.
        
        Args:
            service (str): Service name
            api_key (str): API key to store
        """
        try:
            keyring.set_password(self.API_SERVICE, service, api_key)
            logger.logger.info(f"Stored API key for {service}")
        except Exception as e:
            logger.error(f"Failed to store API key: {str(e)}")
            raise
    
    @handle_errors
    def get_api_key(self, service: str) -> str:
        """
        Retrieve API key.
        
        Args:
            service (str): Service name
        
        Returns:
            str: API key or None if not found
        """
        try:
            return keyring.get_password(self.API_SERVICE, service)
        except Exception as e:
            logger.error(f"Failed to retrieve API key: {str(e)}")
            return None
    
    @handle_errors
    def delete_api_key(self, service: str):
        """
        Delete API key.
        
        Args:
            service (str): Service name
        """
        try:
            keyring.delete_password(self.API_SERVICE, service)
            logger.logger.info(f"Deleted API key for {service}")
        except Exception as e:
            logger.error(f"Failed to delete API key: {str(e)}")
            raise