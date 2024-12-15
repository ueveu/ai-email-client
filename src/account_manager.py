"""
Manages email accounts and their configurations.
"""

from typing import List, Dict, Optional
from utils.logger import logger
from utils.error_handler import ErrorCollection, handle_errors, collect_errors
from security.credential_manager import CredentialManager
from email_providers import EmailProviders, Provider
from config import Config
from services.credential_service import CredentialService

class AccountManager:
    """Manages email accounts and their configurations."""
    
    def __init__(self, credential_service: CredentialService):
        """
        Initialize account manager.
        
        Args:
            credential_service: Service for managing credentials
        """
        self.credential_service = credential_service
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
        Remove an account.
        
        Args:
            email (str): Email address
            
        Returns:
            bool: True if account was removed successfully
        """
        try:
            # Remove credentials first
            self.credential_service.delete_email_credentials(email)
            
            # Remove account configuration
            self.config.remove_account(email)
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
        return self.credential_service.get_email_credentials(email)
    
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
            
            self.credential_service.store_email_credentials(email, credentials)
            return True
        except Exception as e:
            logger.error(f"Error storing credentials: {str(e)}")
            return False
    
    def save_changes(self) -> bool:
        """
        Save any pending changes to the configuration.
        
        Returns:
            bool: True if changes were saved successfully
        """
        try:
            self.config.save()
            logger.info("Account configuration changes saved")
            return True
        except Exception as e:
            logger.error(f"Error saving account changes: {str(e)}")
            return False 