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
from dotenv import load_dotenv
from utils.logger import logger
from utils.error_handler import handle_errors
from services.credential_service import CredentialService
from abc import ABC, abstractmethod

# Load environment variables from .env file
load_dotenv()

@dataclass
class Provider:
    """Email provider configuration."""
    name: str
    domain: str
    imap_server: str
    imap_port: int
    imap_ssl: bool
    smtp_server: str
    smtp_port: int
    smtp_ssl: bool
    oauth_enabled: bool = False

class EmailProviders:
    """Known email providers and their configurations."""
    
    GMAIL = Provider(
        name="Gmail",
        domain="gmail.com",
        imap_server="imap.gmail.com",
        imap_port=993,
        imap_ssl=True,
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        smtp_ssl=True,
        oauth_enabled=True
    )
    
    OUTLOOK = Provider(
        name="Outlook",
        domain="outlook.com",
        imap_server="outlook.office365.com",
        imap_port=993,
        imap_ssl=True,
        smtp_server="smtp.office365.com",
        smtp_port=587,
        smtp_ssl=True,
        oauth_enabled=True
    )
    
    YAHOO = Provider(
        name="Yahoo",
        domain="yahoo.com",
        imap_server="imap.mail.yahoo.com",
        imap_port=993,
        imap_ssl=True,
        smtp_server="smtp.mail.yahoo.com",
        smtp_port=587,
        smtp_ssl=True,
        oauth_enabled=False
    )
    
    @staticmethod
    def detect_provider(email: str) -> Provider:
        """
        Detect email provider from email address.
        
        Args:
            email (str): Email address
            
        Returns:
            Provider: Provider configuration if found, None otherwise
        """
        if not email or '@' not in email:
            return None
            
        domain = email.split('@')[1].lower()
        
        # Check for known providers
        if domain == EmailProviders.GMAIL.domain:
            return EmailProviders.GMAIL
        elif domain in [EmailProviders.OUTLOOK.domain, "hotmail.com"]:
            return EmailProviders.OUTLOOK
        elif domain == EmailProviders.YAHOO.domain:
            return EmailProviders.YAHOO
        
        # Return None for unknown providers
        return None

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth2 callback requests."""
    
    def do_GET(self):
        """Handle GET request with OAuth code."""
        try:
            # Parse the query parameters
            query_components = parse_qs(self.path.split('?')[1])
            
            # Check for error response
            if 'error' in query_components:
                error = query_components['error'][0]
                error_msg = f"OAuth Error: {error}"
                if 'error_description' in query_components:
                    error_msg += f" - {query_components['error_description'][0]}"
                logger.error(error_msg)
                
                # Store the error
                self.server.oauth_error = error_msg
                self.server.oauth_code = None
                
                # Send error response to browser
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                error_html = f"""
                <html><body>
                <h2>Authentication Failed</h2>
                <p>{error_msg}</p>
                <p>Please check the application logs and verify your OAuth configuration.</p>
                <p>You can close this window.</p>
                </body></html>
                """
                self.wfile.write(error_html.encode())
                return
            
            # Handle successful authentication
            code = query_components['code'][0]
            self.server.oauth_code = code
            self.server.oauth_error = None
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            success_html = """
            <html><body>
            <h2>Authentication Successful!</h2>
            <p>You can close this window and return to the application.</p>
            </body></html>
            """
            self.wfile.write(success_html.encode())
            
        except Exception as e:
            error_msg = f"OAuth callback error: {str(e)}"
            logger.error(error_msg)
            self.server.oauth_error = error_msg
            self.server.oauth_code = None
            
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Authentication failed! Please check the application logs and try again.")

class EmailProvider(ABC):
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def validate_credentials(self):
        pass
  