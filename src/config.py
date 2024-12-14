import os
from pathlib import Path
from dotenv import load_dotenv
import json
from security import CredentialManager

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Configuration management for the application.
    Handles settings, API keys, and account data.
    """
    
    def __init__(self):
        """Initialize configuration with default values."""
        self.app_dir = Path.home() / ".ai-email-assistant"
        self.accounts_file = self.app_dir / "accounts.json"
        self.settings_file = self.app_dir / "settings.json"
        
        # Create application directory if it doesn't exist
        self.app_dir.mkdir(exist_ok=True)
        
        # Initialize credential manager
        self.credential_manager = CredentialManager()
        
        # Load or create configuration files
        self.settings = self._load_settings()
        self.accounts = self._load_accounts()
        
        # Store API key securely if provided in environment
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.credential_manager.store_api_key("gemini", api_key)
    
    def _load_settings(self):
        """Load application settings from file."""
        default_settings = {
            "default_email": "",
            "theme": "light",
            "max_emails_to_fetch": 50
        }
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    return {**default_settings, **json.load(f)}
            except:
                return default_settings
        else:
            self._save_settings(default_settings)
            return default_settings
    
    def _save_settings(self, settings):
        """Save settings to file."""
        with open(self.settings_file, "w") as f:
            json.dump(settings, f, indent=4)
    
    def _load_accounts(self):
        """Load email accounts from file."""
        if self.accounts_file.exists():
            try:
                with open(self.accounts_file, "r") as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_accounts(self):
        """Save email accounts to file."""
        with open(self.accounts_file, "w") as f:
            json.dump(self.accounts, f, indent=4)
    
    def add_account(self, account_data):
        """
        Add a new email account.
        
        Args:
            account_data (dict): Email account configuration
        """
        # Extract credentials for secure storage
        credentials = {
            "password": account_data.pop("password", ""),
            "oauth_token": account_data.pop("oauth_token", ""),
            "oauth_refresh_token": account_data.pop("oauth_refresh_token", "")
        }
        
        # Store credentials securely
        self.credential_manager.store_email_credentials(
            account_data["email"],
            credentials
        )
        
        # Store non-sensitive account data
        self.accounts.append(account_data)
        self._save_accounts()
    
    def remove_account(self, email):
        """
        Remove an email account.
        
        Args:
            email (str): Email address to remove
        """
        # Remove credentials
        self.credential_manager.delete_email_credentials(email)
        
        # Remove account data
        self.accounts = [acc for acc in self.accounts if acc["email"] != email]
        self._save_accounts()
    
    def update_account(self, email, account_data):
        """
        Update an existing email account.
        
        Args:
            email (str): Email address to update
            account_data (dict): New account configuration
        """
        # Extract and store credentials
        if "password" in account_data or "oauth_token" in account_data:
            credentials = {
                "password": account_data.pop("password", ""),
                "oauth_token": account_data.pop("oauth_token", ""),
                "oauth_refresh_token": account_data.pop("oauth_refresh_token", "")
            }
            self.credential_manager.store_email_credentials(email, credentials)
        
        # Update account data
        for i, account in enumerate(self.accounts):
            if account["email"] == email:
                self.accounts[i] = account_data
                break
        self._save_accounts()
    
    def get_account(self, email):
        """
        Get account data for a specific email.
        
        Args:
            email (str): Email address to look up
        
        Returns:
            dict: Account configuration or None if not found
        """
        # Get account data
        for account in self.accounts:
            if account["email"] == email:
                # Get credentials
                credentials = self.credential_manager.get_email_credentials(email)
                if credentials:
                    # Merge account data with credentials
                    return {**account, **credentials}
                return account
        return None
    
    def get_api_key(self, api_name="gemini"):
        """
        Get API key from secure storage.
        
        Args:
            api_name (str): Name of the API
        
        Returns:
            str: API key or None if not found
        """
        return self.credential_manager.get_api_key(api_name)
    
    def update_settings(self, settings):
        """
        Update application settings.
        
        Args:
            settings (dict): New settings to apply
        """
        self.settings.update(settings)
        self._save_settings(self.settings) 