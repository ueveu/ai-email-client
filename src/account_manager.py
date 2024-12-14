import json
from pathlib import Path
from typing import List, Dict, Optional
from utils.logger import logger
from utils.error_handler import ErrorCollection, handle_errors, collect_errors
from security.credential_manager import CredentialManager
from email_providers import EmailProviders

class AccountManager:
    """Manages email account configurations and credentials."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".ai-email-assistant"
        self.accounts_file = self.config_dir / "accounts.json"
        self.credential_manager = CredentialManager()
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """Ensure configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.accounts_file.exists():
            self.accounts_file.write_text('{"accounts": []}')
    
    @handle_errors
    def add_account(self, account_data: Dict, error_collection: Optional[ErrorCollection] = None) -> bool:
        """
        Add a new email account.
        
        Args:
            account_data (Dict): Account configuration data
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            bool: True if account was added successfully
        """
        try:
            # Validate account data
            @collect_errors(error_collection, "Validate Account Data")
            def validate():
                return self._validate_account_data(account_data)
            if not validate():
                return False
            
            # Load existing accounts
            @collect_errors(error_collection, "Load Accounts")
            def load():
                return self._load_accounts()
            accounts = load()
            if accounts is None:
                return False
            
            # Check for duplicate
            email = account_data['email']
            if any(acc['email'] == email for acc in accounts):
                if error_collection:
                    error_collection.add(f"Account {email} already exists")
                return False
            
            # Store credentials securely
            @collect_errors(error_collection, "Store Credentials")
            def store_creds():
                if 'password' in account_data:
                    self.credential_manager.store_password(
                        email,
                        account_data['password']
                    )
                if 'oauth_tokens' in account_data:
                    self.credential_manager.store_oauth_tokens(
                        email,
                        account_data['oauth_tokens']
                    )
                return True
            if not store_creds():
                return False
            
            # Remove sensitive data before saving
            account_data = account_data.copy()
            account_data.pop('password', None)
            account_data.pop('oauth_tokens', None)
            
            # Add account
            accounts.append(account_data)
            
            # Save updated accounts
            @collect_errors(error_collection, "Save Accounts")
            def save():
                return self._save_accounts(accounts)
            return save()
            
        except Exception as e:
            if error_collection:
                error_collection.add(f"Failed to add account: {str(e)}")
            logger.logger.error(f"Failed to add account: {str(e)}")
            return False
    
    @handle_errors
    def update_account(self, email: str, updates: Dict, error_collection: Optional[ErrorCollection] = None) -> bool:
        """
        Update an existing email account.
        
        Args:
            email (str): Email address of account to update
            updates (Dict): Updated account data
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            bool: True if account was updated successfully
        """
        try:
            # Load existing accounts
            @collect_errors(error_collection, "Load Accounts")
            def load():
                return self._load_accounts()
            accounts = load()
            if accounts is None:
                return False
            
            # Find account
            account = next((acc for acc in accounts if acc['email'] == email), None)
            if not account:
                if error_collection:
                    error_collection.add(f"Account {email} not found")
                return False
            
            # Update credentials if provided
            @collect_errors(error_collection, "Update Credentials")
            def update_creds():
                if 'password' in updates:
                    self.credential_manager.store_password(
                        email,
                        updates['password']
                    )
                if 'oauth_tokens' in updates:
                    self.credential_manager.store_oauth_tokens(
                        email,
                        updates['oauth_tokens']
                    )
                return True
            if not update_creds():
                return False
            
            # Remove sensitive data before saving
            updates = updates.copy()
            updates.pop('password', None)
            updates.pop('oauth_tokens', None)
            
            # Update account data
            account.update(updates)
            
            # Save updated accounts
            @collect_errors(error_collection, "Save Accounts")
            def save():
                return self._save_accounts(accounts)
            return save()
            
        except Exception as e:
            if error_collection:
                error_collection.add(f"Failed to update account: {str(e)}")
            logger.logger.error(f"Failed to update account: {str(e)}")
            return False
    
    @handle_errors
    def remove_account(self, email: str, error_collection: Optional[ErrorCollection] = None) -> bool:
        """
        Remove an email account.
        
        Args:
            email (str): Email address of account to remove
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            bool: True if account was removed successfully
        """
        try:
            # Load existing accounts
            @collect_errors(error_collection, "Load Accounts")
            def load():
                return self._load_accounts()
            accounts = load()
            if accounts is None:
                return False
            
            # Find account
            if not any(acc['email'] == email for acc in accounts):
                if error_collection:
                    error_collection.add(f"Account {email} not found")
                return False
            
            # Remove credentials
            @collect_errors(error_collection, "Remove Credentials")
            def remove_creds():
                self.credential_manager.remove_credentials(email)
                return True
            if not remove_creds():
                return False
            
            # Remove account
            accounts = [acc for acc in accounts if acc['email'] != email]
            
            # Save updated accounts
            @collect_errors(error_collection, "Save Accounts")
            def save():
                return self._save_accounts(accounts)
            return save()
            
        except Exception as e:
            if error_collection:
                error_collection.add(f"Failed to remove account: {str(e)}")
            logger.logger.error(f"Failed to remove account: {str(e)}")
            return False
    
    @handle_errors
    def get_account(self, email: str, error_collection: Optional[ErrorCollection] = None) -> Optional[Dict]:
        """
        Get account configuration.
        
        Args:
            email (str): Email address of account
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            Optional[Dict]: Account configuration if found
        """
        try:
            # Load accounts
            @collect_errors(error_collection, "Load Accounts")
            def load():
                return self._load_accounts()
            accounts = load()
            if accounts is None:
                return None
            
            # Find account
            account = next((acc.copy() for acc in accounts if acc['email'] == email), None)
            if not account:
                if error_collection:
                    error_collection.add(f"Account {email} not found")
                return None
            
            # Get credentials
            @collect_errors(error_collection, "Get Credentials")
            def get_creds():
                # Get password if not OAuth
                if not EmailProviders.is_oauth_provider(account.get('provider')):
                    password = self.credential_manager.get_password(email)
                    if password:
                        account['password'] = password
                
                # Get OAuth tokens if OAuth provider
                if EmailProviders.is_oauth_provider(account.get('provider')):
                    tokens = self.credential_manager.get_oauth_tokens(email)
                    if tokens:
                        account['oauth_tokens'] = tokens
                return True
            get_creds()
            
            return account
            
        except Exception as e:
            if error_collection:
                error_collection.add(f"Failed to get account: {str(e)}")
            logger.logger.error(f"Failed to get account: {str(e)}")
            return None
    
    @handle_errors
    def list_accounts(self, error_collection: Optional[ErrorCollection] = None) -> List[Dict]:
        """
        List all email accounts.
        
        Args:
            error_collection (ErrorCollection, optional): Collection to store multiple errors
            
        Returns:
            List[Dict]: List of account configurations
        """
        try:
            # Load accounts
            @collect_errors(error_collection, "Load Accounts")
            def load():
                return self._load_accounts()
            accounts = load()
            
            return accounts or []
            
        except Exception as e:
            if error_collection:
                error_collection.add(f"Failed to list accounts: {str(e)}")
            logger.logger.error(f"Failed to list accounts: {str(e)}")
            return []
    
    def _validate_account_data(self, account_data: Dict) -> bool:
        """Validate account configuration data."""
        required_fields = ['email', 'imap_server', 'smtp_server']
        return all(field in account_data for field in required_fields)
    
    def _load_accounts(self) -> Optional[List[Dict]]:
        """Load accounts from configuration file."""
        try:
            data = json.loads(self.accounts_file.read_text())
            return data.get('accounts', [])
        except Exception as e:
            logger.logger.error(f"Failed to load accounts: {str(e)}")
            return None
    
    def _save_accounts(self, accounts: List[Dict]) -> bool:
        """Save accounts to configuration file."""
        try:
            data = {'accounts': accounts}
            self.accounts_file.write_text(json.dumps(data, indent=2))
            return True
        except Exception as e:
            logger.logger.error(f"Failed to save accounts: {str(e)}")
            return False 