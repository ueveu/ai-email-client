import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import ssl
from email_cache import EmailCache
from email_threading import ThreadManager
from email_attachments import AttachmentManager
from email_providers import EmailProviders, Provider
from services.credential_service import CredentialService
import os
import mimetypes
from utils.logger import logger
from utils.error_handler import ErrorCollection, handle_errors, collect_errors
from PyQt6.QtCore import QSettings
from typing import Optional, List, Dict
import base64
import re
from utils.imap_utf7 import encode_utf7, decode_utf7
from email import header
from PyQt6.QtWidgets import QMessageBox

class EmailManager:
    """Manager for email operations and account handling."""
    
    def __init__(self, credential_service, operation_service):
        """
        Initialize the email manager.
        
        Args:
            credential_service: Service for managing credentials
            operation_service: Service for managing operations
        """
        self.credential_service = credential_service
        self.operation_service = operation_service
        self.imap_connection = None
        self.smtp_connection = None
        self.current_account = None
        self.cache = EmailCache()
        
    def initialize_account(self, account_data: dict, credentials: dict) -> bool:
        """
        Initialize an email account.
        
        Args:
            account_data: Account configuration data
            credentials: Account credentials
            
        Returns:
            bool: True if initialized successfully
        """
        try:
            logger.debug(f"Initializing account: {account_data.get('email')}")
            
            # Store account data
            self.current_account = account_data
            
            # Connect to servers
            logger.debug("Connecting to IMAP server...")
            if not self.connect_imap(credentials):
                logger.error("Failed to connect to IMAP server")
                return False
            
            logger.debug("Connecting to SMTP server...")
            if not self.connect_smtp(credentials):
                logger.error("Failed to connect to SMTP server")
                return False
            
            # Initialize cache for this account
            logger.debug("Initializing email cache...")
            self.cache.initialize_account(account_data['email'])
            
            logger.debug("Account initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing account: {str(e)}")
            return False
    
    def connect_imap(self, credentials: dict) -> bool:
        """
        Connect to IMAP server.
        
        Args:
            credentials: Account credentials
            
        Returns:
            bool: True if connected successfully
        """
        try:
            # Disconnect existing connection if any
            self.disconnect_imap()
            
            # Get server settings
            server = self.current_account['imap_server']
            port = self.current_account['imap_port']
            use_ssl = self.current_account.get('imap_ssl', True)
            
            # Create connection
            if use_ssl:
                self.imap_connection = imaplib.IMAP4_SSL(server, port)
            else:
                self.imap_connection = imaplib.IMAP4(server, port)
            
            # Authenticate
            if credentials['type'] == 'oauth':
                auth_string = self._get_oauth_string(
                    self.current_account['email'],
                    credentials['tokens']['access_token']
                )
                self.imap_connection.authenticate('XOAUTH2', lambda _: auth_string)
            else:
                self.imap_connection.login(
                    self.current_account['email'],
                    credentials['password']
                )
            
            logger.debug("Successfully connected to IMAP server")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to IMAP server: {str(e)}")
            return False
    
    def connect_smtp(self, credentials: dict) -> bool:
        """
        Connect to SMTP server.
        
        Args:
            credentials: Account credentials
            
        Returns:
            bool: True if connected successfully
        """
        try:
            # Disconnect existing connection if any
            self.disconnect_smtp()
            
            # Get server settings
            server = self.current_account['smtp_server']
            port = self.current_account['smtp_port']
            use_ssl = self.current_account.get('smtp_ssl', True)
            
            # Create connection
            if use_ssl:
                self.smtp_connection = smtplib.SMTP(server, port)
                self.smtp_connection.starttls()
            else:
                self.smtp_connection = smtplib.SMTP(server, port)
            
            # Authenticate
            if credentials['type'] == 'oauth':
                auth_string = base64.b64encode(
                    self._get_oauth_string(
                        self.current_account['email'],
                        credentials['tokens']['access_token']
                    )
                )
                self.smtp_connection.ehlo()
                self.smtp_connection.docmd('AUTH', 'XOAUTH2 ' + auth_string.decode())
            else:
                self.smtp_connection.login(
                    self.current_account['email'],
                    credentials['password']
                )
            
            logger.debug("Successfully connected to SMTP server")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to SMTP server: {str(e)}")
            return False
    
    def disconnect_imap(self):
        """Disconnect from IMAP server."""
        try:
            if self.imap_connection:
                self.imap_connection.logout()
                self.imap_connection = None
        except Exception as e:
            logger.error(f"Error disconnecting from IMAP server: {str(e)}")
    
    def disconnect_smtp(self):
        """Disconnect from SMTP server."""
        try:
            if self.smtp_connection:
                self.smtp_connection.quit()
                self.smtp_connection = None
        except Exception as e:
            logger.error(f"Error disconnecting from SMTP server: {str(e)}")
    
    def _get_oauth_string(self, email: str, access_token: str) -> bytes:
        """
        Get OAuth authentication string.
        
        Args:
            email: Email address
            access_token: OAuth access token
            
        Returns:
            bytes: OAuth authentication string
        """
        auth_string = f"user={email}\x01auth=Bearer {access_token}\x01\x01"
        return auth_string.encode('utf-8')
    
    def fetch_emails(self, folder: str, limit: int = 50) -> List[Dict]:
        """
        Fetch emails from a folder.
        
        Args:
            folder: Folder name to fetch from
            limit: Maximum number of emails to fetch
            
        Returns:
            List[Dict]: List of email data dictionaries
        """
        try:
            logger.debug(f"Fetching emails from folder: {folder}")
            
            if not self.imap_connection:
                logger.error("No IMAP connection available")
                return []
            
            # Handle folder name
            if isinstance(folder, dict) and 'raw_name' in folder:
                folder = folder['raw_name']
            
            # Quote folder name for IMAP command
            quoted_name = f'"{folder}"'
            if not quoted_name.startswith('"'):
                quoted_name = f'"{quoted_name}"'
            
            # Select the folder
            try:
                self.imap_connection.select(quoted_name)
            except Exception as e:
                logger.error(f"Error selecting folder: {str(e)}")
                return []
            
            # Search for all emails in the folder
            try:
                _, message_numbers = self.imap_connection.search(None, 'ALL')
            except Exception as e:
                logger.error(f"Error searching folder: {str(e)}")
                return []
            
            # Get the list of message IDs
            message_ids = message_numbers[0].split()
            
            # Fetch the most recent emails first (up to limit)
            emails = []
            for msg_id in reversed(message_ids[:limit]):
                try:
                    # Fetch email data
                    _, msg_data = self.imap_connection.fetch(msg_id, '(RFC822 FLAGS)')
                    if not msg_data or not msg_data[0]:
                        continue
                    
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    # Decode email subject
                    subject, encoding = header.decode_header(email_message['subject'])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or 'utf-8', errors='replace')
                    
                    # Get flags
                    flags = []
                    if len(msg_data) > 1 and b'FLAGS' in msg_data[1]:
                        flag_data = msg_data[1].decode('utf-8', errors='replace')
                        flags = [f.strip() for f in flag_data[flag_data.find('(')+1:flag_data.find(')')].split()]
                    
                    # Parse email data
                    email_data = {
                        'id': msg_id.decode(),
                        'subject': subject or 'No Subject',
                        'from': email_message['from'],
                        'date': email_message['date'],
                        'text': self._get_email_text(email_message),
                        'html': self._get_email_html(email_message),
                        'attachments': self._get_attachments(email_message),
                        'flags': flags
                    }
                    
                    emails.append(email_data)
                    
                except Exception as e:
                    logger.error(f"Error fetching email {msg_id}: {str(e)}")
                    continue
            
            logger.debug(f"Fetched {len(emails)} emails from folder")
            return emails
            
        except Exception as e:
            logger.error(f"Error fetching emails: {str(e)}")
            return []
            
    def _get_email_text(self, email_message) -> str:
        """
        Extract text content from email message.
        
        Args:
            email_message: Email message object
            
        Returns:
            str: Plain text content of the email
        """
        text = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        decoded_text = part.get_payload(decode=True)
                        if decoded_text:
                            text += decoded_text.decode('utf-8', errors='replace')
                    except (UnicodeDecodeError, AttributeError) as e:
                        logger.warning(f"Error decoding text part: {str(e)}")
                        continue
        else:
            if email_message.get_content_type() == "text/plain":
                try:
                    decoded_text = email_message.get_payload(decode=True)
                    if decoded_text:
                        text = decoded_text.decode('utf-8', errors='replace')
                except (UnicodeDecodeError, AttributeError) as e:
                    logger.warning(f"Error decoding text content: {str(e)}")
        return text
        
    def _get_email_html(self, email_message) -> str:
        """
        Extract HTML content from email message.
        
        Args:
            email_message: Email message object
            
        Returns:
            str: HTML content of the email
        """
        html = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/html":
                    try:
                        decoded_html = part.get_payload(decode=True)
                        if decoded_html:
                            html += decoded_html.decode('utf-8', errors='replace')
                    except (UnicodeDecodeError, AttributeError) as e:
                        logger.warning(f"Error decoding HTML part: {str(e)}")
                        continue
        else:
            if email_message.get_content_type() == "text/html":
                try:
                    decoded_html = email_message.get_payload(decode=True)
                    if decoded_html:
                        html = decoded_html.decode('utf-8', errors='replace')
                except (UnicodeDecodeError, AttributeError) as e:
                    logger.warning(f"Error decoding HTML content: {str(e)}")
        return html
        
    def _get_attachments(self, email_message) -> List[Dict]:
        """Extract attachments from email message."""
        attachments = []
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                
                filename = part.get_filename()
                if filename:
                    attachments.append({
                        'filename': filename,
                        'content_type': part.get_content_type(),
                        'content': part.get_payload(decode=True)
                    })
        return attachments
    
    def list_folders(self) -> List[Dict]:
        """
        List all folders in the email account.
        
        Returns:
            List[Dict]: List of folder information dictionaries
        """
        try:
            logger.debug("Listing folders")
            
            if not self.imap_connection:
                logger.error("No IMAP connection available")
                return []
            
            # List all folders
            _, folder_list = self.imap_connection.list()
            
            folders = []
            for folder_info in folder_list:
                try:
                    # Parse folder information
                    decoded = folder_info.decode('utf-8', errors='replace')
                    
                    # Extract folder attributes and name
                    match = re.match(r'\((.*?)\) "(.*?)" "(.*?)"$', decoded.strip())
                    if not match:
                        continue
                        
                    flags, delimiter, raw_name = match.groups()
                    
                    # Decode folder name using custom IMAP UTF-7
                    name = decode_utf7(raw_name)
                    
                    # Create folder info dictionary
                    folder_data = {
                        'name': name,
                        'flags': [f.strip() for f in flags.split()],
                        'delimiter': delimiter,
                        'raw_name': raw_name  # Keep raw name for IMAP commands
                    }
                    
                    folders.append(folder_data)
                    
                except Exception as e:
                    logger.error(f"Error parsing folder info: {str(e)}")
                    continue
            
            return folders
        except Exception as e:
            logger.error(f"Error listing folders: {str(e)}")
            return []
            
    def get_folder_status(self, folder_name: str) -> Optional[Dict]:
        """
        Get status information for a folder.
        
        Args:
            folder_name: Name of the folder
            
        Returns:
            Optional[Dict]: Folder status information or None if error
        """
        try:
            if not self.imap_connection:
                logger.error("No IMAP connection available")
                return None
            
            # Use raw folder name if available (from list_folders)
            if isinstance(folder_name, dict) and 'raw_name' in folder_name:
                folder_name = folder_name['raw_name']
            
            # Quote folder name for IMAP command
            quoted_name = f'"{folder_name}"'
            if not quoted_name.startswith('"'):
                quoted_name = f'"{quoted_name}"'
            
            # Get status using STATUS command
            _, data = self.imap_connection.status(
                quoted_name,
                '(MESSAGES UNSEEN)'
            )
            
            if not data or not data[0]:
                return None
            
            # Parse status response
            status_str = data[0].decode('utf-8', errors='replace')
            messages = 0
            unseen = 0
            
            # Extract counts using string parsing
            if 'MESSAGES' in status_str:
                messages_start = status_str.find('MESSAGES') + 9
                messages_end = status_str.find(' ', messages_start)
                if messages_end == -1:
                    messages_end = status_str.find(')', messages_start)
                if messages_end != -1:
                    messages = int(status_str[messages_start:messages_end])
            
            if 'UNSEEN' in status_str:
                unseen_start = status_str.find('UNSEEN') + 7
                unseen_end = status_str.find(' ', unseen_start)
                if unseen_end == -1:
                    unseen_end = status_str.find(')', unseen_start)
                if unseen_end != -1:
                    unseen = int(status_str[unseen_start:unseen_end])
            
            return {
                'messages': messages,
                'unseen': unseen
            }
            
        except Exception as e:
            logger.error(f"Error getting folder status: {str(e)}")
            return None
    
    def set_active_account(self, account_data: dict) -> bool:
        """
        Set the active email account.
        
        Args:
            account_data: Account configuration data
            
        Returns:
            bool: True if account was set successfully
        """
        try:
            # Get credentials for the account
            email = account_data['email']
            credentials = self.credential_service.get_email_credentials(email)
            if not credentials:
                logger.error(f"No credentials found for {email}")
                return False
            
            # Initialize the account
            return self.initialize_account(account_data, credentials)
            
        except Exception as e:
            logger.error(f"Error setting active account: {str(e)}")
            return False
    
    def mark_read(self, message_id: str, folder: str = 'INBOX') -> bool:
        """
        Mark an email as read.
        
        Args:
            message_id: Message ID to mark as read
            folder: Folder containing the message
            
        Returns:
            bool: True if marked successfully
        """
        try:
            if not self.imap_connection:
                logger.error("No IMAP connection available")
                return False
            
            # Select the folder
            self.imap_connection.select(folder)
            
            # Add the \Seen flag
            self.imap_connection.store(message_id, '+FLAGS', '\\Seen')
            
            logger.debug(f"Marked message {message_id} as read")
            return True
            
        except Exception as e:
            logger.error(f"Error marking email as read: {str(e)}")
            return False
    
    def connect(self):
        """Connect to the email server with enhanced error handling and retry logic."""
        try:
            logger.debug("Connecting to IMAP server...")
            
            if not self.credentials:
                logger.error("No credentials available")
                raise ValueError("No credentials available for connection")

            # Get server settings
            imap_host = self.credentials.get('imap_server')
            imap_port = self.credentials.get('imap_port', 993)
            use_ssl = self.credentials.get('imap_ssl', True)
            
            # Establish IMAP connection
            if use_ssl:
                self.imap_connection = imaplib.IMAP4_SSL(imap_host, imap_port)
            else:
                self.imap_connection = imaplib.IMAP4(imap_host, imap_port)
            
            # Handle OAuth authentication
            if 'oauth_tokens' in self.credentials:
                auth_string = self._build_oauth_string(
                    self.email,
                    self.credentials['oauth_tokens']['access_token']
                )
                self.imap_connection.authenticate('XOAUTH2', lambda x: auth_string)
            else:
                # Standard password authentication
                password = self.credential_service.get_account_credentials(self.email)
                if not password:
                    raise ValueError("No password available for authentication")
                self.imap_connection.login(self.email, password['password'])
            
            logger.info("Successfully connected to IMAP server")
            return True
            
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if "AUTHENTICATIONFAILED" in error_msg:
                logger.error("Authentication failed - invalid credentials")
                self.notify_authentication_error()
            else:
                logger.error(f"IMAP error: {error_msg}")
            return False
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return False

    def notify_authentication_error(self):
        """Notify the user about authentication failure and provide guidance."""
        if hasattr(self, 'notification_service'):
            self.notification_service.show_notification(
                "Authentication Failed",
                "Please check your email and password/app password in the account settings.",
                NotificationType.ERROR
            )

    def handle_authentication_error(self):
        """Handle authentication errors and guide users through fixes."""
        try:
            provider = EmailProviders.detect_provider(self.email)
            
            if provider == Provider.GMAIL:
                message = (
                    "Gmail authentication failed. Please ensure:\n\n"
                    "1. You are using OAuth authentication\n"
                    "2. Your Google Account has IMAP enabled\n"
                    "3. You have granted the necessary permissions\n\n"
                    "Would you like to reconfigure this account?"
                )
            else:
                message = (
                    f"Authentication failed for {self.email}. Please ensure:\n\n"
                    "1. Your email address is correct\n"
                    "2. Your password/app password is correct\n"
                    "3. IMAP is enabled for your account\n\n"
                    "Would you like to reconfigure this account?"
                )
            
            # Show error dialog with guidance
            response = QMessageBox.question(
                None,
                "Authentication Failed",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if response == QMessageBox.StandardButton.Yes:
                # Show account configuration dialog
                from ui.email_account_dialog import EmailAccountDialog
                dialog = EmailAccountDialog(parent=None)
                dialog.email_input.setText(self.email)
                if dialog.exec():
                    # Retry connection with new credentials
                    self.connect()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling authentication: {str(e)}")
            return False