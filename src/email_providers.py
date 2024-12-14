import re
import webbrowser
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, List
from urllib.parse import urlencode

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

class EmailProviders:
    """
    Manages email provider configurations and authentication flows.
    """
    
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
            setup_url="https://accounts.google.com/signin/v2/identifier",
            app_password_url="https://myaccount.google.com/apppasswords",
            help_url="https://support.google.com/mail/answer/185833",
            oauth_scopes=[
                "https://mail.google.com/",
                "https://www.googleapis.com/auth/gmail.modify",
                "https://www.googleapis.com/auth/gmail.compose"
            ]
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
            setup_url="https://login.live.com/login.srf",
            app_password_url="https://account.live.com/proofs/AppPassword",
            help_url="https://support.microsoft.com/en-us/account-billing/using-app-passwords-with-apps-that-don-t-support-two-step-verification-5896ed9b-4263-e681-128a-a6f2979a7944",
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
            setup_url="https://login.yahoo.com",
            app_password_url="https://login.yahoo.com/account/security/app-passwords",
            help_url="https://help.yahoo.com/kb/generate-third-party-passwords-sln15241.html"
        )
    }
    
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