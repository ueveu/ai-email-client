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
        
        # Create application directory and files if they don't exist
        self.app_dir.mkdir(parents=True, exist_ok=True)
        if not self.accounts_file.exists():
            self._save_accounts([])  # Create empty accounts file
        if not self.settings_file.exists():
            self._save_settings(self._get_default_settings())
        
        # Initialize accounts list
        self.accounts = []
        
        # Load configuration files
        self.settings = self._load_settings()
        self._load_accounts()  # Load accounts into self.accounts
        
        logger.info("Configuration initialized")
    
    def _get_default_settings(self):
        """Get default application settings."""
        return {
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
            "google_client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "google_client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "default_email": "",
            "theme": "light",
            "max_emails_to_fetch": 50,
            "start_minimized": False,
            "check_updates": True,
            "auto_connect": True,
            "notifications": {
                "enabled": True,
                "sound": True
            }
        }
    
    def _load_settings(self):
        """Load application settings from file."""
        default_settings = self._get_default_settings()
        
        try:
            if self.settings_file.exists():
                with open(self.settings_file, "r", encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all required settings exist
                    return {**default_settings, **loaded_settings}
            else:
                self._save_settings(default_settings)
                return default_settings
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
            return default_settings
    
    def _save_settings(self, settings):
        """Save settings to file."""
        try:
            with open(self.settings_file, "w", encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            logger.debug("Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            raise
    
    def _load_accounts(self):
        """Load accounts from file."""
        try:
            logger.debug(f"Loading accounts from {self.accounts_file}")
            with open(self.accounts_file, "r", encoding='utf-8') as f:
                self.accounts = json.load(f)
            logger.debug(f"Loaded {len(self.accounts)} accounts")
        except FileNotFoundError:
            logger.debug("No accounts file found, creating empty file")
            self.accounts = []
            self._save_accounts(self.accounts)
        except json.JSONDecodeError:
            logger.error("Invalid accounts file format, creating new file")
            self.accounts = []
            self._save_accounts(self.accounts)
        except Exception as e:
            logger.error(f"Error loading accounts: {str(e)}")
            self.accounts = []
    
    def _save_accounts(self, accounts=None):
        """
        Save accounts to file.
        
        Args:
            accounts (list, optional): List of accounts to save. If None, saves self.accounts
        """
        try:
            accounts_to_save = accounts if accounts is not None else self.accounts
            logger.debug(f"Saving {len(accounts_to_save)} accounts to {self.accounts_file}")
            with open(self.accounts_file, "w", encoding='utf-8') as f:
                json.dump(accounts_to_save, f, indent=4)
            logger.debug("Accounts saved successfully")
        except Exception as e:
            logger.error(f"Error saving accounts: {str(e)}")
            raise
    
    def get_accounts(self):
        """
        Get list of configured email accounts.
        
        Returns:
            list: List of account configurations
        """
        if not self.accounts:
            self._load_accounts()  # Reload accounts if empty
        logger.debug(f"Returning {len(self.accounts)} accounts")
        return self.accounts
    
    def add_account(self, account_data):
        """
        Add a new email account.
        
        Args:
            account_data (dict): Email account configuration
        """
        # Validate required fields
        required_fields = ['email', 'imap_server', 'imap_port', 'smtp_server', 'smtp_port']
        if not all(field in account_data for field in required_fields):
            raise ValueError("Missing required account fields")
            
        # Check for duplicate email
        if any(acc['email'] == account_data['email'] for acc in self.accounts):
            raise ValueError(f"Account {account_data['email']} already exists")
        
        logger.debug(f"Adding account: {account_data['email']}")
        self.accounts.append(account_data)
        self._save_accounts()
        logger.info(f"Added account: {account_data['email']}")
    
    def remove_account(self, email):
        """
        Remove an email account.
        
        Args:
            email (str): Email address to remove
        """
        original_count = len(self.accounts)
        self.accounts = [acc for acc in self.accounts if acc["email"] != email]
        
        if len(self.accounts) == original_count:
            logger.warning(f"Account {email} not found for removal")
            return
        
        self._save_accounts()
        logger.info(f"Removed account: {email}")
    
    def update_account(self, email, account_data):
        """
        Update an existing email account.
        
        Args:
            email (str): Email address to update
            account_data (dict): New account configuration
        """
        # Validate required fields
        required_fields = ['email', 'imap_server', 'imap_port', 'smtp_server', 'smtp_port']
        if not all(field in account_data for field in required_fields):
            raise ValueError("Missing required account fields")
        
        updated = False
        for i, account in enumerate(self.accounts):
            if account["email"] == email:
                self.accounts[i] = account_data
                updated = True
                break
                
        if not updated:
            raise ValueError(f"Account {email} not found")
            
        self._save_accounts()
        logger.info(f"Updated account: {email}")
    
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
        logger.debug(f"Account {email} not found")
        return None
    
    def update_settings(self, settings):
        """
        Update application settings.
        
        Args:
            settings (dict): New settings to apply
        """
        # Merge with existing settings
        self.settings.update(settings)
        self._save_settings(self.settings)
        logger.info("Updated application settings") 