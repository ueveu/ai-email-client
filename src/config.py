"""
Configuration management for the application.
"""

from typing import Dict, List, Optional
import json
import os
from utils.logger import logger

class Config:
    """Configuration management class."""
    
    def __init__(self):
        """Initialize configuration."""
        self.settings_file = "config.json"
        self.settings = {}
        self.accounts = []
        self.load()
    
    def load(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    self.settings = data.get("settings", {})
                    self.accounts = data.get("accounts", [])
                logger.debug("Configuration loaded successfully")
            else:
                logger.debug("No configuration file found, using defaults")
                self._save_settings()
                
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            self.settings = {}
            self.accounts = []
    
    def _save_settings(self, settings=None):
        """
        Save settings to file.
        
        Args:
            settings (dict, optional): Settings to save. If None, saves self.settings
        """
        try:
            settings_to_save = settings if settings is not None else self.settings
            logger.debug(f"Saving settings to {self.settings_file}")
            with open(self.settings_file, "w", encoding='utf-8') as f:
                json.dump(settings_to_save, f, indent=4)
            logger.debug("Settings saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            raise
    
    def save(self):
        """
        Save all configuration changes to file.
        
        Returns:
            bool: True if saved successfully
        """
        try:
            data = {
                "settings": self.settings,
                "accounts": self.accounts
            }
            with open(self.settings_file, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def get_accounts(self) -> List[Dict]:
        """
        Get list of configured email accounts.
        
        Returns:
            List[Dict]: List of account configurations
        """
        return self.accounts
    
    def get_account(self, email: str) -> Optional[Dict]:
        """
        Get configuration for a specific account.
        
        Args:
            email: Email address of the account
            
        Returns:
            Optional[Dict]: Account configuration if found
        """
        for account in self.accounts:
            if account['email'] == email:
                return account
        return None
    
    def add_account(self, account: Dict):
        """
        Add a new account configuration.
        
        Args:
            account: Account configuration to add
        """
        if not self.get_account(account['email']):
            self.accounts.append(account)
            self.save()
    
    def update_account(self, email: str, account_data: Dict):
        """
        Update an existing account configuration.
        
        Args:
            email: Email address of the account to update
            account_data: New account configuration
        """
        for i, account in enumerate(self.accounts):
            if account['email'] == email:
                self.accounts[i] = account_data
                self.save()
                break
    
    def remove_account(self, email: str):
        """
        Remove an account configuration.
        
        Args:
            email: Email address of the account to remove
        """
        self.accounts = [a for a in self.accounts if a['email'] != email]
        self.save()
    
    def get_setting(self, key: str, default=None):
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if setting not found
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value):
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        self.settings[key] = value
        self.save()
    
    def remove_setting(self, key: str):
        """
        Remove a setting.
        
        Args:
            key: Setting key to remove
        """
        if key in self.settings:
            del self.settings[key]
            self.save()