import os
from pathlib import Path
from dotenv import load_dotenv
import json
from utils.logger import logger

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
        
        # Initialize accounts list
        self.accounts = []
        
        # Load or create configuration files
        self.settings = self._load_settings()
        self._load_accounts()  # Load accounts into self.accounts
        
        logger.logger.info("Configuration initialized")
    
    def _load_settings(self):
        """Load application settings from file."""
        default_settings = {
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
            "default_email": "",
            "theme": "light",
            "max_emails_to_fetch": 50
        }
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    return {**default_settings, **json.load(f)}
            except Exception as e:
                logger.log_error(e, {'context': 'Loading settings'})
                return default_settings
        else:
            self._save_settings(default_settings)
            return default_settings
    
    def _save_settings(self, settings):
        """Save settings to file."""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            logger.log_error(e, {'context': 'Saving settings'})
    
    def _load_accounts(self):
        """Load accounts from file."""
        if self.accounts_file.exists():
            try:
                logger.logger.debug(f"Loading accounts from {self.accounts_file}")
                with open(self.accounts_file, "r") as f:
                    self.accounts = json.load(f)
                logger.logger.debug(f"Loaded {len(self.accounts)} accounts")
            except Exception as e:
                logger.log_error(e, {'context': 'Loading accounts'})
                self.accounts = []
        else:
            logger.logger.debug("No accounts file found, starting with empty list")
            self.accounts = []
    
    def _save_accounts(self):
        """Save accounts to file."""
        try:
            logger.logger.debug(f"Saving {len(self.accounts)} accounts to {self.accounts_file}")
            with open(self.accounts_file, "w") as f:
                json.dump(self.accounts, f, indent=4)
            logger.logger.debug("Accounts saved successfully")
        except Exception as e:
            logger.log_error(e, {'context': 'Saving accounts'})
            raise
    
    def get_accounts(self):
        """
        Get list of configured email accounts.
        
        Returns:
            list: List of account configurations
        """
        logger.logger.debug(f"Returning {len(self.accounts)} accounts")
        return self.accounts
    
    def add_account(self, account_data):
        """
        Add a new email account.
        
        Args:
            account_data (dict): Email account configuration
        """
        logger.logger.debug(f"Adding account: {account_data['email']}")
        self.accounts.append(account_data)
        self._save_accounts()
        logger.logger.info(f"Added account: {account_data['email']}")
    
    def remove_account(self, email):
        """
        Remove an email account.
        
        Args:
            email (str): Email address to remove
        """
        self.accounts = [acc for acc in self.accounts if acc["email"] != email]
        self._save_accounts()
        logger.logger.info(f"Removed account: {email}")
    
    def update_account(self, email, account_data):
        """
        Update an existing email account.
        
        Args:
            email (str): Email address to update
            account_data (dict): New account configuration
        """
        for i, account in enumerate(self.accounts):
            if account["email"] == email:
                self.accounts[i] = account_data
                break
        self._save_accounts()
        logger.logger.info(f"Updated account: {email}")
    
    def get_account(self, email):
        """
        Get account data for a specific email.
        
        Args:
            email (str): Email address to look up
        
        Returns:
            dict: Account configuration or None if not found
        """
        for account in self.accounts:
            if account["email"] == email:
                return account
        return None
    
    def update_settings(self, settings):
        """
        Update application settings.
        
        Args:
            settings (dict): New settings to apply
        """
        self.settings.update(settings)
        self._save_settings(self.settings)
        logger.logger.info("Updated application settings") 