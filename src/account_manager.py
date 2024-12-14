"""
Manages email accounts and their configurations.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from utils.logger import logger
from utils.error_handler import ErrorCollection, handle_errors, collect_errors
from security.credential_manager import CredentialManager
from email_providers import EmailProviders, Provider

class AccountManager:
    """Manages email accounts and their configurations."""
    
    def __init__(self):
        """Initialize account manager."""
        self.credential_manager = CredentialManager()
        self.config_dir = Path.home() / '.ai_email_assistant' / 'config'
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.accounts_file = self.config_dir / 'accounts.json'
        self._load_accounts()
    
    def _load_accounts(self):
        """Load accounts from file."""
        try:
            if self.accounts_file.exists():
                with open(self.accounts_file, 'r') as f:
                    self.accounts = json.load(f)
            else:
                self.accounts = {}
        except Exception as e:
            logger.error(f"Error loading accounts: {str(e)}")
            self.accounts = {}
    
    def _save_accounts(self):
        """Save accounts to file."""
        try:
            with open(self.accounts_file, 'w') as f:
                json.dump(self.accounts, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving accounts: {str(e)}")
    
    def get_all_accounts(self) -> List[Dict]:
        """
        Get all configured email accounts.
        
        Returns:
            List[Dict]: List of all account configurations
        """
        try:
            return [
                {
                    'email': email,
                    **account_data
                }
                for email, account_data in self.accounts.items()
            ]
        except Exception as e:
            logger.error(f"Error getting all accounts: {str(e)}")
            return []
    
    def add_account(self, account_data: Dict) -> bool:
        """
        Add a new email account.
        
        Args:
            account_data (Dict): Account configuration
            
        Returns:
            bool: True if account was added successfully
        """
        try:
            email = account_data['email']
            self.accounts[email] = account_data
            self._save_accounts()
            logger.info(f"Added account: {email}")
            return True
        except Exception as e:
            logger.error(f"Error adding account: {str(e)}")
            return False
    
    def get_account(self, email: str) -> Optional[Dict]:
        """
        Get account configuration.
        
        Args:
            email (str): Email address
            
        Returns:
            Optional[Dict]: Account configuration if found
        """
        return self.accounts.get(email)
    
    def update_account(self, email: str, account_data: Dict) -> bool:
        """
        Update an existing account.
        
        Args:
            email (str): Email address
            account_data (Dict): New account configuration
            
        Returns:
            bool: True if account was updated successfully
        """
        try:
            if email in self.accounts:
                self.accounts[email] = account_data
                self._save_accounts()
                logger.info(f"Updated account: {email}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating account: {str(e)}")
            return False
    
    def remove_account(self, email: str) -> bool:
        """
        Remove an email account.
        
        Args:
            email (str): Email address
            
        Returns:
            bool: True if account was removed successfully
        """
        try:
            if email in self.accounts:
                del self.accounts[email]
                self._save_accounts()
                
                # Remove credentials
                self.credential_manager.delete_account_credentials(email)
                
                logger.info(f"Removed account: {email}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing account: {str(e)}")
            return False
    
    def list_accounts(self) -> List[Dict]:
        """
        Get list of all accounts.
        
        Returns:
            List[Dict]: List of account configurations
        """
        return list(self.accounts.values())
    
    def get_account_credentials(self, email: str) -> Optional[Dict]:
        """
        Get account credentials.
        
        Args:
            email (str): Email address
            
        Returns:
            Optional[Dict]: Account credentials if found
        """
        return self.credential_manager.get_account_credentials(email)
    
    def store_account_credentials(self, email: str, credentials: Dict) -> bool:
        """
        Store account credentials.
        
        Args:
            email (str): Email address
            credentials (Dict): Credentials to store
            
        Returns:
            bool: True if credentials were stored successfully
        """
        try:
            account = self.get_account(email)
            if not account:
                return False
            
            provider = EmailProviders.detect_provider(email)
            self.credential_manager.store_account_credentials(email, credentials, provider.value)
            return True
        except Exception as e:
            logger.error(f"Error storing credentials: {str(e)}")
            return False 