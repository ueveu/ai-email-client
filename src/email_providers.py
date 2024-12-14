import re
import webbrowser
import json
import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from urllib.parse import urlencode, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from utils.logger import logger
from utils.error_handler import handle_errors
from security.credential_manager import CredentialManager

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth2 callback requests."""
    
    def do_GET(self):
        """Handle GET request with OAuth code."""
        try:
            # Parse the authorization code from query parameters
            query_components = parse_qs(self.path.split('?')[1])
            code = query_components['code'][0]
            
            # Store the code for the main application to use
            self.server.oauth_code = code
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authentication successful! You can close this window.")
            
        except Exception as e:
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authentication failed! Please try again.")
            logger.error(f"OAuth callback error: {str(e)}")

class Provider(Enum):
    """Supported email providers."""
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    YAHOO = "yahoo"
    CUSTOM = "custom"

@dataclass
class ProviderConfig:
    """Configuration for an email provider."""
    name: str
    imap_server: str
    imap_port: int
    imap_ssl: bool
    smtp_server: str
    smtp_port: int
    smtp_ssl: bool
    oauth_supported: bool
    setup_url: str
    app_password_url: Optional[str] = None
    help_url: Optional[str] = None
    oauth_scopes: Optional[List[str]] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    token_url: Optional[str] = None
    redirect_uri: Optional[str] = None

class EmailProviders:
    """
    Manages email provider configurations and authentication flows.
    """
    
    # Default redirect URI for OAuth
    DEFAULT_REDIRECT_URI = "http://localhost:8080"
    
    # Provider configurations
    PROVIDERS = {
        Provider.GMAIL: ProviderConfig(
            name="Gmail",
            imap_server="imap.gmail.com",
            imap_port=993,
            imap_ssl=True,
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            smtp_ssl=True,
            oauth_supported=True,
            setup_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            app_password_url="https://myaccount.google.com/apppasswords",
            help_url="https://support.google.com/mail/answer/185833",
            oauth_scopes=[
                "https://mail.google.com/",
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.readonly"
            ],
            redirect_uri=DEFAULT_REDIRECT_URI,
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
        ),
        Provider.OUTLOOK: ProviderConfig(
            name="Outlook",
            imap_server="outlook.office365.com",
            imap_port=993,
            imap_ssl=True,
            smtp_server="smtp.office365.com",
            smtp_port=587,
            smtp_ssl=True,
            oauth_supported=True,
            setup_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
            app_password_url="https://account.microsoft.com/security",
            help_url="https://support.microsoft.com/account-billing/using-app-passwords-with-apps-that-don-t-support-two-step-verification-5896ed9b-4263-e681-128a-a6f2979a7944",
            oauth_scopes=[
                "offline_access",
                "https://outlook.office.com/IMAP.AccessAsUser.All",
                "https://outlook.office.com/SMTP.Send"
            ]
        ),
        Provider.YAHOO: ProviderConfig(
            name="Yahoo Mail",
            imap_server="imap.mail.yahoo.com",
            imap_port=993,
            imap_ssl=True,
            smtp_server="smtp.mail.yahoo.com",
            smtp_port=587,
            smtp_ssl=True,
            oauth_supported=True,
            setup_url="https://api.login.yahoo.com/oauth2/request_auth",
            app_password_url="https://login.yahoo.com/account/security/app-passwords",
            help_url="https://help.yahoo.com/kb/generate-third-party-passwords-sln15241.html"
        )
    }
    
    @classmethod
    def start_oauth_server(cls) -> Tuple[HTTPServer, str]:
        """
        Start local server to handle OAuth callback.
        
        Returns:
            Tuple[HTTPServer, str]: Server instance and authorization code
        """
        server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
        server.oauth_code = None
        return server, server.oauth_code
    
    @classmethod
    @handle_errors
    def authenticate_gmail(cls, email: str) -> Dict:
        """
        Perform Gmail OAuth2 authentication flow.
        
        Args:
            email (str): Gmail address to authenticate
        
        Returns:
            Dict: OAuth tokens and credentials
        """
        config = cls.get_provider_config(Provider.GMAIL)
        if not config.client_id or not config.client_secret:
            raise ValueError("Gmail OAuth credentials not configured")
        
        # Start local server for OAuth callback
        server, _ = cls.start_oauth_server()
        
        # Generate authorization URL
        auth_params = {
            'client_id': config.client_id,
            'redirect_uri': config.redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(config.oauth_scopes),
            'access_type': 'offline',
            'prompt': 'consent',
            'login_hint': email
        }
        auth_url = f"{config.setup_url}?{urlencode(auth_params)}"
        
        # Open browser for authentication
        webbrowser.open(auth_url)
        
        try:
            # Wait for callback
            server.handle_request()
            auth_code = server.oauth_code
            
            if not auth_code:
                raise ValueError("No authorization code received")
            
            # Exchange code for tokens
            token_data = {
                'client_id': config.client_id,
                'client_secret': config.client_secret,
                'code': auth_code,
                'redirect_uri': config.redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(config.token_url, data=token_data)
            response.raise_for_status()
            
            tokens = response.json()
            
            # Store tokens securely
            credential_manager = CredentialManager()
            credential_manager.store_oauth_tokens(email, tokens)
            
            return tokens
            
        finally:
            server.server_close()
    
    @classmethod
    def refresh_gmail_token(cls, email: str, refresh_token: str) -> Dict:
        """
        Refresh Gmail OAuth2 access token.
        
        Args:
            email (str): Gmail address
            refresh_token (str): OAuth refresh token
        
        Returns:
            Dict: New OAuth tokens
        """
        config = cls.get_provider_config(Provider.GMAIL)
        
        token_data = {
            'client_id': config.client_id,
            'client_secret': config.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(config.token_url, data=token_data)
        response.raise_for_status()
        
        tokens = response.json()
        tokens['refresh_token'] = refresh_token  # Keep existing refresh token
        
        # Update stored tokens
        credential_manager = CredentialManager()
        credential_manager.store_oauth_tokens(email, tokens)
        
        return tokens
    
    @classmethod
    def detect_provider(cls, email: str) -> Provider:
        """
        Detect email provider from email address.
        
        Args:
            email (str): Email address
        
        Returns:
            Provider: Detected provider or CUSTOM if unknown
        """
        email = email.lower()
        
        if re.match(r".*@gmail\.com$", email):
            return Provider.GMAIL
        elif re.match(r".*@(outlook\.com|hotmail\.com|live\.com)$", email):
            return Provider.OUTLOOK
        elif re.match(r".*@yahoo\.(com|co\.[a-z]{2})$", email):
            return Provider.YAHOO
        
        return Provider.CUSTOM
    
    @classmethod
    def get_provider_config(cls, provider: Provider) -> ProviderConfig:
        """
        Get configuration for a provider.
        
        Args:
            provider (Provider): Email provider
        
        Returns:
            ProviderConfig: Provider configuration
        """
        return cls.PROVIDERS.get(provider)
    
    @classmethod
    def get_config_for_email(cls, email: str) -> Optional[ProviderConfig]:
        """
        Get configuration for an email address.
        
        Args:
            email (str): Email address
        
        Returns:
            Optional[ProviderConfig]: Provider configuration if detected
        """
        provider = cls.detect_provider(email)
        return cls.get_provider_config(provider)
    
    @classmethod
    def open_provider_setup(cls, provider: Provider, email: Optional[str] = None):
        """
        Open provider's setup/login page in default browser.
        
        Args:
            provider (Provider): Email provider
            email (str, optional): Pre-fill email address
        """
        config = cls.get_provider_config(provider)
        if not config:
            return
        
        url = config.setup_url
        if email and provider == Provider.GMAIL:
            params = {
                'identifier': email,
                'service': 'mail'
            }
            url = f"{url}?{urlencode(params)}"
        elif email and provider == Provider.OUTLOOK:
            params = {
                'login_hint': email,
                'response_type': 'code',
                'prompt': 'login'
            }
            url = f"{url}?{urlencode(params)}"
        
        webbrowser.open(url)
    
    @classmethod
    def open_app_password_setup(cls, provider: Provider):
        """
        Open provider's app password setup page.
        
        Args:
            provider (Provider): Email provider
        """
        config = cls.get_provider_config(provider)
        if config and config.app_password_url:
            webbrowser.open(config.app_password_url)
    
    @classmethod
    def open_help(cls, provider: Provider):
        """
        Open provider's help page.
        
        Args:
            provider (Provider): Email provider
        """
        config = cls.get_provider_config(provider)
        if config and config.help_url:
            webbrowser.open(config.help_url) 