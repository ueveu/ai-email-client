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
from email_providers import EmailProviders
import sys
import os
from config import Config

class CredentialService:
    """Manages secure storage and retrieval of email credentials."""
    
    def __init__(self):
        """Initialize credential service."""
        self.service_name = "ai-email-assistant"
        self.oauth_dir = Path.home() / ".ai-email-assistant" / "oauth"
        self.oauth_dir.mkdir(parents=True, exist_ok=True)
        self.config = Config()  # Initialize config to access OAuth credentials
        
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
            # Validate credentials format
            if not isinstance(credentials, dict):
                raise ValueError("Invalid credentials format: not a dictionary")
            
            if 'type' not in credentials:
                raise ValueError("Invalid credentials format: missing type identifier")
            
            if credentials['type'] not in ['oauth', 'password']:
                raise ValueError(f"Invalid credentials type: {credentials['type']}")
            
            # For OAuth credentials, validate tokens
            if credentials['type'] == 'oauth':
                if 'tokens' not in credentials:
                    raise ValueError("Invalid OAuth credentials: missing tokens")
                if not isinstance(credentials['tokens'], dict):
                    raise ValueError("Invalid OAuth credentials: tokens not a dictionary")
                if 'access_token' not in credentials['tokens']:
                    raise ValueError("Invalid OAuth credentials: missing access token")
            
            # For password credentials, validate password
            if credentials['type'] == 'password':
                if 'password' not in credentials:
                    raise ValueError("Invalid password credentials: missing password")
            
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
    
    @handle_errors
    def start_oauth_flow(self, provider) -> Optional[Dict]:
        """
        Start OAuth authentication flow.
        
        Args:
            provider: Email provider configuration
            
        Returns:
            Optional[Dict]: OAuth tokens if successful
        """
        try:
            if provider == EmailProviders.GMAIL:
                return self._start_google_oauth()
            elif provider == EmailProviders.OUTLOOK:
                return self._start_microsoft_oauth()
            else:
                raise ValueError(f"OAuth not supported for {provider.name}")
                
        except Exception as e:
            logger.error(f"OAuth flow failed: {str(e)}")
            return None
    
    def _start_google_oauth(self) -> Optional[Dict]:
        """Start Google OAuth flow."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.oauth2.credentials import Credentials
            import pickle
            from pathlib import Path
            import google.auth.transport.requests
            import requests
            
            # Google OAuth configuration
            SCOPES = [
                'openid',
                'https://mail.google.com/',
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.compose',
                'https://www.googleapis.com/auth/gmail.send',
                'https://www.googleapis.com/auth/userinfo.email'
            ]
            
            # Get client configuration from settings
            client_id = self.config.settings.get('google_client_id')
            client_secret = self.config.settings.get('google_client_secret')
            
            if not client_id or not client_secret:
                logger.error("Google OAuth credentials missing in configuration")
                raise ValueError("Google OAuth credentials not configured. Please check your .env file.")
            
            logger.debug(f"Using client_id: {client_id[:8]}... for Google OAuth")
            
            # Load client configuration
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost:8080", "http://localhost:8080/"]
                }
            }
            
            try:
                # First try without trailing slash
                try:
                    logger.info("Attempting OAuth flow with http://localhost:8080...")
                    flow = InstalledAppFlow.from_client_config(
                        client_config,
                        SCOPES,
                        redirect_uri='http://localhost:8080'
                    )
                    creds = flow.run_local_server(
                        port=8080,
                        success_message='The authentication flow has completed. You may close this window.',
                        open_browser=True,
                        authorization_prompt_message="Please visit this URL to authorize this application:"
                    )
                except Exception as e:
                    if "redirect_uri_mismatch" in str(e).lower():
                        logger.warning(f"First OAuth attempt failed, trying with trailing slash: {str(e)}")
                        # Try again with trailing slash
                        flow = InstalledAppFlow.from_client_config(
                            client_config,
                            SCOPES,
                            redirect_uri='http://localhost:8080/'
                        )
                        creds = flow.run_local_server(
                            port=8080,
                            success_message='The authentication flow has completed. You may close this window.',
                            open_browser=True,
                            authorization_prompt_message="Please visit this URL to authorize this application:"
                        )
                    else:
                        raise
                
                logger.info("OAuth flow completed successfully")
                
            except Exception as oauth_error:
                logger.error(f"OAuth flow failed: {str(oauth_error)}")
                raise ValueError(f"OAuth authentication failed: {str(oauth_error)}")
            
            try:
                # Get user email with better error handling
                session = requests.Session()
                session.verify = True
                
                auth_req = google.auth.transport.requests.Request(session=session)
                
                if creds.expired and creds.refresh_token:
                    logger.debug("Refreshing expired credentials")
                    creds.refresh(auth_req)
                
                userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
                headers = {
                    'Authorization': f'Bearer {creds.token}'
                }
                response = requests.get(userinfo_url, headers=headers)
                
                if response.status_code != 200:
                    logger.error(f"Failed to get user info: {response.status_code} - {response.text}")
                    raise Exception(f"Failed to get user email: {response.status_code}")
                
                email = response.json().get('email')
                if not email:
                    raise ValueError("Email not found in Google user info response")
                
                logger.info(f"Successfully authenticated Google account: {email}")
                
            except Exception as user_info_error:
                logger.error(f"Failed to get user info: {str(user_info_error)}")
                raise ValueError(f"Failed to get user information: {str(user_info_error)}")
            
            # Create tokens dictionary with expiry handling
            expiry_timestamp = creds.expiry.timestamp() if creds.expiry else (datetime.now() + timedelta(hours=1)).timestamp()
            expires_in = expiry_timestamp - datetime.now().timestamp()
            
            tokens = {
                'type': 'oauth',
                'email': email,
                'access_token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes,
                'expires_in': expires_in
            }
            
            # Create final credentials structure
            credentials = {
                'type': 'oauth',
                'email': email,
                'tokens': tokens
            }
            
            logger.debug(f"OAuth tokens generated successfully for {email}")
            return credentials
            
        except Exception as e:
            logger.error(f"Google OAuth failed: {str(e)}")
            raise ValueError(f"Google OAuth authentication failed: {str(e)}")
    
    def _start_microsoft_oauth(self) -> Optional[Dict]:
        """Start Microsoft OAuth flow."""
        try:
            import msal
            
            # Microsoft OAuth configuration
            CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
            CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
            AUTHORITY = "https://login.microsoftonline.com/common"
            SCOPE = [
                'https://outlook.office.com/IMAP.AccessAsUser.All',
                'https://outlook.office.com/SMTP.Send',
                'offline_access',
                'User.Read',
                'email'
            ]
            
            # Create MSAL app
            app = msal.PublicClientApplication(
                CLIENT_ID,
                authority=AUTHORITY
            )
            
            # Start device code flow
            flow = app.initiate_device_flow(scopes=SCOPE)
            if "user_code" not in flow:
                raise Exception("Failed to start device code flow")
            
            # Show instructions to user
            print(flow["message"])
            
            # Wait for user to complete authentication
            result = app.acquire_token_by_device_flow(flow)
            if "access_token" not in result:
                raise Exception(result.get("error_description", "Failed to get access token"))
            
            # Get user email
            import requests
            graph_url = "https://graph.microsoft.com/v1.0/me"
            headers = {
                'Authorization': f'Bearer {result["access_token"]}'
            }
            response = requests.get(graph_url, headers=headers)
            if response.status_code == 200:
                email = response.json().get('userPrincipalName')
            else:
                raise Exception("Failed to get user email from Microsoft")
            
            # Create tokens dictionary
            tokens = {
                'type': 'oauth',
                'email': email,
                'access_token': result['access_token'],
                'refresh_token': result.get('refresh_token'),
                'expires_in': result['expires_in'],
                'scope': result['scope']
            }
            
            return tokens
            
        except Exception as e:
            logger.error(f"Microsoft OAuth failed: {str(e)}")
            raise