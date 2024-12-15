"""
Manages email accounts and their configurations.
"""

from typing import List, Dict, Optional
from utils.logger import logger
from utils.error_handler import ErrorCollection, handle_errors, collect_errors
from security.credential_manager import CredentialManager
from email_providers import EmailProviders, Provider
from config import Config

class AccountManager:
    """Manages email accounts and their configurations."""
    
    def __init__(self):
        """Initialize account manager."""
        self.credential_manager = CredentialManager()
        self.config = Config()
    
    def get_all_accounts(self) -> List[Dict]:
        """
        Get all configured email accounts.
        
        Returns:
            List[Dict]: List of all account configurations
        """
        try:
            return self.config.get_accounts()
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
            self.config.add_account(account_data)
            logger.info(f"Added account: {account_data['email']}")
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
        return self.config.get_account(email)
    
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
            self.config.update_account(email, account_data)
            logger.info(f"Updated account: {email}")
            return True
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
            # Remove from config
            self.config.remove_account(email)
            
            # Remove credentials
            self.credential_manager.remove_credentials(email)
            
            logger.info(f"Removed account: {email}")
            return True
        except Exception as e:
            logger.error(f"Error removing account: {str(e)}")
            return False
    
    def list_accounts(self) -> List[Dict]:
        """
        Get list of all accounts.
        
        Returns:
            List[Dict]: List of account configurations
        """
        return self.config.get_accounts()
    
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
            
            self.credential_manager.store_email_credentials(email, credentials)
            return True
        except Exception as e:
            logger.error(f"Error storing credentials: {str(e)}")
            return False 