"""
Email provider configurations and utilities.
"""

from dataclasses import dataclass
from typing import Optional
import re

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
    def detect_provider(email: str) -> Optional[Provider]:
        """
        Detect email provider from email address.
        
        Args:
            email: Email address
            
        Returns:
            Optional[Provider]: Provider configuration if found
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
  