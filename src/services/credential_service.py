"""
Service for managing secure storage and retrieval of email credentials.
"""

import keyring
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
from utils.logger import logger
from utils.error_handler import handle_errors
from email_providers import EmailProviders, Provider
import sys
import webbrowser
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtCore import QUrl
import requests

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
                    keyring.set_keyring(Windows.WinVaultKeyring())
                except ImportError:
                    logger.warning("Windows keyring backend not available")
            
            # Test keyring
            test_key = "test_key"
            test_value = "test_value"
            keyring.set_password(self.service_name, test_key, test_value)
            retrieved = keyring.get_password(self.service_name, test_key)
            keyring.delete_password(self.service_name, test_key)
            
            if retrieved != test_value:
                raise Exception("Keyring test failed")
                
            logger.debug("Keyring initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing keyring: {str(e)}")
            raise
    
    def store_email_credentials(self, email: str, credentials: Dict) -> bool:
        """
        Store email credentials securely.
        
        Args:
            email: Email address
            credentials: Credentials to store
            
        Returns:
            bool: True if stored successfully
        """
        try:
            # Store credentials in keyring
            keyring.set_password(
                self.service_name,
                email,
                json.dumps(credentials)
            )
            
            logger.debug(f"Stored credentials for {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing credentials: {str(e)}")
            return False
    
    def get_email_credentials(self, email: str) -> Optional[Dict]:
        """
        Get email credentials.
        
        Args:
            email: Email address
            
        Returns:
            Optional[Dict]: Credentials if found
        """
        try:
            # Get credentials from keyring
            stored = keyring.get_password(self.service_name, email)
            if not stored:
                return None
            
            return json.loads(stored)
            
        except Exception as e:
            logger.error(f"Error getting credentials: {str(e)}")
            return None
    
    def delete_email_credentials(self, email: str) -> bool:
        """
        Delete email credentials.
        
        Args:
            email: Email address
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            # Delete credentials from keyring
            keyring.delete_password(self.service_name, email)
            
            logger.debug(f"Deleted credentials for {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting credentials: {str(e)}")
            return False
    
    def update_email_credentials(self, email: str, credentials: Dict) -> bool:
        """
        Update email credentials.
        
        Args:
            email: Email address
            credentials: New credentials
            
        Returns:
            bool: True if updated successfully
        """
        try:
            # Delete old credentials first
            self.delete_email_credentials(email)
            
            # Store new credentials
            return self.store_email_credentials(email, credentials)
            
        except Exception as e:
            logger.error(f"Error updating credentials: {str(e)}")
            return False
    
    def start_oauth_flow(self, provider: Provider) -> Optional[Dict]:
        """
        Start OAuth authentication flow for the given provider.
        
        Args:
            provider: Email provider to authenticate with
            
        Returns:
            Optional[Dict]: OAuth credentials if successful
        """
        try:
            if provider == EmailProviders.GMAIL:
                # Google OAuth configuration
                client_id = "YOUR_CLIENT_ID"  # Replace with your OAuth client ID
                client_secret = "YOUR_CLIENT_SECRET"  # Replace with your OAuth client secret
                redirect_uri = "http://localhost:8080"
                scope = "https://mail.google.com/"
                
                # Build authorization URL
                auth_url = (
                    "https://accounts.google.com/o/oauth2/v2/auth?"
                    f"client_id={client_id}&"
                    f"redirect_uri={redirect_uri}&"
                    "response_type=code&"
                    f"scope={scope}&"
                    "access_type=offline&"
                    "prompt=consent"
                )
                
                # Open browser for authentication
                webbrowser.open(auth_url)
                
                # Get authorization code from user
                auth_code = QMessageBox.getText(
                    None,
                    "Enter Authorization Code",
                    "Please enter the authorization code from the browser:"
                )[0]
                
                if not auth_code:
                    raise Exception("No authorization code provided")
                
                # Exchange authorization code for tokens
                token_url = "https://oauth2.googleapis.com/token"
                data = {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": auth_code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
                
                response = requests.post(token_url, data=data)
                if response.status_code != 200:
                    raise Exception(f"Token exchange failed: {response.text}")
                
                tokens = response.json()
                
                # Get user email
                userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
                headers = {"Authorization": f"Bearer {tokens['access_token']}"}
                response = requests.get(userinfo_url, headers=headers)
                if response.status_code != 200:
                    raise Exception(f"Failed to get user info: {response.text}")
                
                user_info = response.json()
                email = user_info.get("email")
                
                if not email:
                    raise Exception("Could not get user email")
                
                # Store credentials
                credentials = {
                    "email": email,
                    "access_token": tokens["access_token"],
                    "refresh_token": tokens.get("refresh_token"),
                    "token_type": tokens["token_type"],
                    "expires_in": tokens["expires_in"],
                    "scope": tokens["scope"],
                    "provider": provider.name,
                    "timestamp": datetime.now().isoformat()
                }
                
                return credentials
                
            elif provider == EmailProviders.OUTLOOK:
                # TODO: Implement Outlook OAuth
                raise Exception("Outlook OAuth not implemented yet")
                
            else:
                raise Exception(f"OAuth not supported for provider: {provider.name}")
            
        except Exception as e:
            logger.error(f"OAuth error: {str(e)}")
            QMessageBox.critical(
                None,
                "OAuth Error",
                f"OAuth authentication failed: {str(e)}"
            )
            return None