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
from security.credential_manager import CredentialManager
import os
import mimetypes
from utils.logger import logger
from utils.error_handler import ErrorCollection, handle_errors, collect_errors

class EmailManager:
    """
    Manages email operations including connection handling,
    email fetching, and sending using IMAP and SMTP protocols.
    """
    
    def __init__(self, account_data):
        """
        Initialize email manager with account settings.
        
        Args:
            account_data (dict): Email account configuration
        """
        self.account_data = account_data
        self.imap_connection = None
        self.smtp_connection = None
        self.current_folder = None
        self.credential_manager = CredentialManager()
        
        # Initialize managers
        self.cache = EmailCache()
        self.thread_manager = ThreadManager()
        self.attachment_manager = AttachmentManager()
    
    def connect_imap(self):
        """
        Establish IMAP connection with the email server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.logger.debug(f"Connecting to IMAP server: {self.account_data['imap_server']}")
            
            # Check if this is a Gmail account
            provider = EmailProviders.detect_provider(self.account_data['email'])
            if provider == Provider.GMAIL:
                logger.logger.debug("Gmail account detected, using OAuth")
                return self._connect_gmail_imap()
            
            # Standard password authentication
            if self.account_data['imap_ssl']:
                self.imap_connection = imaplib.IMAP4_SSL(
                    self.account_data['imap_server'],
                    self.account_data['imap_port']
                )
            else:
                self.imap_connection = imaplib.IMAP4(
                    self.account_data['imap_server'],
                    self.account_data['imap_port']
                )
            
            self.imap_connection.login(
                self.account_data['email'],
                self.account_data['password']
            )
            logger.logger.debug("IMAP connection successful")
            return True
            
        except Exception as e:
            logger.logger.error(f"IMAP connection error: {str(e)}")
            return False
    
    def _connect_gmail_imap(self):
        """
        Establish IMAP connection for Gmail using OAuth2.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.logger.debug("Attempting Gmail IMAP connection with OAuth")
            
            # Get OAuth tokens
            tokens = self.credential_manager.get_oauth_tokens(self.account_data['email'])
            if not tokens:
                logger.logger.error("No OAuth tokens found")
                return False
            
            # Check if we need to refresh the token
            if 'access_token' not in tokens:
                logger.logger.error("No access token in OAuth tokens")
                return False
            
            # Connect with OAuth
            self.imap_connection = imaplib.IMAP4_SSL(
                self.account_data['imap_server'],
                self.account_data['imap_port']
            )
            
            # Authenticate with OAuth2
            auth_string = f'user={self.account_data["email"]}\1auth=Bearer {tokens["access_token"]}\1\1'
            self.imap_connection.authenticate('XOAUTH2', lambda x: auth_string)
            
            logger.logger.debug("Gmail IMAP connection successful")
            return True
            
        except imaplib.IMAP4.error as e:
            if 'Invalid credentials' in str(e):
                logger.logger.warning("OAuth token expired, attempting refresh")
                try:
                    # Refresh token
                    if 'refresh_token' in tokens:
                        new_tokens = EmailProviders.refresh_gmail_token(
                            self.account_data['email'],
                            tokens['refresh_token']
                        )
                        if new_tokens:
                            # Try connection again with new token
                            auth_string = f'user={self.account_data["email"]}\1auth=Bearer {new_tokens["access_token"]}\1\1'
                            self.imap_connection.authenticate('XOAUTH2', lambda x: auth_string)
                            logger.logger.debug("Gmail IMAP connection successful after token refresh")
                            return True
                except Exception as refresh_error:
                    logger.logger.error(f"Token refresh failed: {str(refresh_error)}")
            
            logger.logger.error(f"Gmail IMAP connection error: {str(e)}")
            return False
            
        except Exception as e:
            logger.logger.error(f"Gmail IMAP connection error: {str(e)}")
            return False
    
    def connect_smtp(self):
        """
        Establish SMTP connection with the email server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.account_data['smtp_ssl']:
                self.smtp_connection = smtplib.SMTP_SSL(
                    self.account_data['smtp_server'],
                    self.account_data['smtp_port']
                )
            else:
                self.smtp_connection = smtplib.SMTP(
                    self.account_data['smtp_server'],
                    self.account_data['smtp_port']
                )
                self.smtp_connection.starttls()
            
            self.smtp_connection.login(
                self.account_data['email'],
                self.account_data['password']
            )
            return True
        except Exception as e:
            print(f"SMTP connection error: {str(e)}")
            return False
    
    def list_folders(self):
        """
        List all available email folders/mailboxes.
        
        Returns:
            list: List of folder names and their attributes
                 Each item is a dict with 'name' and 'attributes' keys
        """
        if not self.imap_connection:
            if not self.connect_imap():
                return []
        
        try:
            # List all folders including those in other character sets
            _, folder_list = self.imap_connection.list()
            folders = []
            
            for folder_data in folder_list:
                # Decode the folder data
                decoded_data = folder_data.decode()
                # Parse the folder attributes and name
                attributes = decoded_data.split('(')[1].split(')')[0].split()
                # Extract folder name, handling quoted names
                name_start = decoded_data.find('"/"') + 3
                if name_start == 2:  # If not found, try without quotes
                    name_start = decoded_data.rfind(' ') + 1
                name = decoded_data[name_start:].strip('"')
                
                # Convert folder name from modified UTF-7 if necessary
                try:
                    name = bytes(name, 'utf-7').decode('utf-7')
                except:
                    pass  # Keep original name if conversion fails
                
                folders.append({
                    'name': name,
                    'attributes': attributes
                })
            
            return sorted(folders, key=lambda x: x['name'])
        except Exception as e:
            print(f"Error listing folders: {str(e)}")
            return []
    
    def select_folder(self, folder_name):
        """
        Select a folder/mailbox for subsequent operations.
        
        Args:
            folder_name (str): Name of the folder to select
        
        Returns:
            bool: True if folder was selected successfully, False otherwise
        """
        if not self.imap_connection:
            if not self.connect_imap():
                return False
        
        try:
            result, data = self.imap_connection.select(folder_name)
            if result == 'OK':
                self.current_folder = folder_name
                return True
            return False
        except Exception as e:
            print(f"Error selecting folder {folder_name}: {str(e)}")
            return False
    
    def get_folder_status(self, folder_name):
        """
        Get status information for a folder.
        
        Args:
            folder_name (str): Name of the folder
        
        Returns:
            dict: Folder status information including message counts
        """
        if not self.imap_connection:
            if not self.connect_imap():
                return None
        
        try:
            result, data = self.imap_connection.status(
                folder_name,
                "(MESSAGES UNSEEN RECENT)"
            )
            if result != 'OK':
                return None
            
            # Parse status data
            status_data = data[0].decode()
            status = {}
            
            # Extract counts using string manipulation
            for item in ['MESSAGES', 'UNSEEN', 'RECENT']:
                start = status_data.find(item) + len(item) + 1
                end = status_data.find(' ', start)
                if end == -1:  # If it's the last item
                    end = status_data.find(')', start)
                count = int(status_data[start:end])
                status[item.lower()] = count
            
            return status
        except Exception as e:
            print(f"Error getting folder status: {str(e)}")
            return None
    
    def fetch_emails(self, folder=None, limit=50, offset=0, use_cache=True, thread=True):
        """
        Fetch emails from the specified folder.
        
        Args:
            folder (str, optional): Email folder to fetch from. If None, uses current folder
            limit (int): Maximum number of emails to fetch
            offset (int): Number of emails to skip from the start
            use_cache (bool): Whether to use cached emails when offline
            thread (bool): Whether to group emails into conversation threads
        
        Returns:
            list: List of email data dictionaries or EmailThread objects
        """
        logger.logger.debug(f"Fetching emails from folder: {folder}, limit: {limit}, offset: {offset}, use_cache: {use_cache}, thread: {thread}")
        
        # Fetch emails as before
        emails = self._fetch_emails_base(folder, limit, offset, use_cache)
        logger.logger.debug(f"Fetched {len(emails)} base emails")
        
        # Return threaded or unthreaded emails based on parameter
        if thread:
            logger.logger.debug("Threading emails")
            self.thread_manager.process_emails(emails)
            threads = self.thread_manager.threads
            logger.logger.debug(f"Created {len(threads)} email threads")
            return threads
        return emails
    
    def _fetch_emails_base(self, folder=None, limit=50, offset=0, use_cache=True):
        """Base method for fetching emails without threading."""
        logger.logger.debug(f"Base fetch - folder: {folder}, current folder: {self.current_folder}")
        
        if folder and folder != self.current_folder:
            logger.logger.debug(f"Selecting new folder: {folder}")
            if not self.select_folder(folder):
                logger.logger.error(f"Failed to select folder: {folder}")
                return []
        elif not self.current_folder:
            logger.logger.debug("No current folder, selecting INBOX")
            if not self.select_folder('INBOX'):
                logger.logger.error("Failed to select INBOX")
                return []
        
        try:
            if not self.imap_connection and use_cache:
                # Return cached emails if offline
                logger.logger.info(f"Using cached emails for {folder}")
                cached_emails = self.cache.get_cached_emails(
                    self.account_data['email'],
                    folder,
                    limit,
                    offset
                )
                logger.logger.debug(f"Retrieved {len(cached_emails)} cached emails")
                return cached_emails
            
            if not self.imap_connection:
                logger.logger.debug("No IMAP connection, attempting to connect")
                if not self.connect_imap():
                    logger.logger.error("Failed to establish IMAP connection")
                    return []
            
            logger.logger.debug("Searching for messages")
            _, messages = self.imap_connection.search(None, "ALL")
            email_list = []
            
            # Get message numbers and apply offset and limit
            message_numbers = messages[0].split()
            message_numbers.reverse()  # Reverse to get newest first
            start_index = offset
            end_index = min(offset + limit, len(message_numbers))
            
            logger.logger.debug(f"Processing messages {start_index} to {end_index} of {len(message_numbers)}")
            
            for num in message_numbers[start_index:end_index]:
                try:
                    logger.logger.debug(f"Fetching message {num}")
                    _, msg_data = self.imap_connection.fetch(num, "(RFC822)")
                    email_message = email.message_from_bytes(msg_data[0][1])
                    
                    # Extract email data
                    email_data = self._parse_email_message(email_message, num)
                    email_data['folder'] = self.current_folder
                    
                    # Cache the email
                    if use_cache:
                        self.cache.cache_email(
                            self.account_data['email'],
                            self.current_folder,
                            email_data
                        )
                    
                    email_list.append(email_data)
                    logger.logger.debug(f"Successfully processed message {num}")
                except Exception as e:
                    logger.logger.error(f"Error processing message {num}: {str(e)}")
                    continue
            
            logger.logger.debug(f"Successfully fetched {len(email_list)} emails")
            return email_list
            
        except Exception as e:
            logger.logger.error(f"Error in _fetch_emails_base: {str(e)}")
            if use_cache:
                # Try to get cached emails on error
                logger.logger.info("Attempting to retrieve cached emails after error")
                cached_emails = self.cache.get_cached_emails(
                    self.account_data['email'],
                    folder,
                    limit,
                    offset
                )
                logger.logger.debug(f"Retrieved {len(cached_emails)} cached emails after error")
                return cached_emails
            return []
    
    def _parse_email_message(self, email_message, message_id):
        """Parse email message into a dictionary format."""
        # Extract basic metadata
        subject = email.header.decode_header(email_message["subject"])[0][0]
        if isinstance(subject, bytes):
            subject = subject.decode()
        
        from_addr = email.header.decode_header(email_message["from"])[0][0]
        if isinstance(from_addr, bytes):
            from_addr = from_addr.decode()
        
        date_str = email_message["date"]
        date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        
        # Extract recipients
        recipients = {
            'to': self._get_addresses(email_message.get_all('to', [])),
            'cc': self._get_addresses(email_message.get_all('cc', [])),
            'bcc': self._get_addresses(email_message.get_all('bcc', []))
        }
        
        # Get email body and attachments
        body = ""
        attachments = []
        
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                elif part.get_content_maintype() != 'multipart':
                    # Handle attachment
                    filename = part.get_filename()
                    if filename:
                        attachments.append({
                            'filename': filename,
                            'content_type': part.get_content_type(),
                            'content': part.get_payload(decode=True)
                        })
        else:
            body = email_message.get_payload(decode=True).decode()
        
        # Save attachments and get their info
        if attachments:
            attachments = self.attachment_manager.save_attachments(
                self.account_data['email'],
                str(message_id),
                attachments
            )
        
        # Get flags/status
        flags = []
        if hasattr(email_message, 'flags'):
            flags = [str(flag) for flag in email_message.flags]
        
        return {
            "message_id": message_id,
            "subject": subject,
            "from": from_addr,
            "recipients": recipients,
            "date": date,
            "body": body,
            "attachments": attachments,
            "flags": flags,
            "metadata": {
                "headers": dict(email_message.items()),
                "content_type": email_message.get_content_type()
            }
        }
    
    def _get_addresses(self, address_list):
        """Extract email addresses from address list."""
        if not address_list:
            return []
        
        addresses = []
        for addr in address_list:
            if isinstance(addr, str):
                addresses.append(addr)
            else:
                _, addr = email.utils.parseaddr(addr)
                if addr:
                    addresses.append(addr)
        return addresses
    
    def clear_old_cache(self, days=30):
        """Clear old cached emails."""
        self.cache.clear_old_cache(days)
    
    def get_cache_info(self):
        """Get cache size and statistics."""
        return self.cache.get_cache_size()
    
    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear_cache()
    
    def send_email(self, to_addr, subject, body, cc=None, bcc=None, attachments=None):
        """
        Send an email using the configured SMTP settings.
        
        Args:
            to_addr (str): Recipient email addresses (comma-separated)
            subject (str): Email subject
            body (str): Email body text
            cc (str, optional): CC recipients (comma-separated)
            bcc (str, optional): BCC recipients (comma-separated)
            attachments (list, optional): List of attachment file paths
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.smtp_connection:
            if not self.connect_smtp():
                return False
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.account_data["email"]
            msg["To"] = to_addr
            msg["Subject"] = subject
            
            if cc:
                msg["Cc"] = cc
            if bcc:
                msg["Bcc"] = bcc
            
            msg.attach(MIMEText(body, "plain"))
            
            # Add attachments if any
            if attachments:
                for filepath in attachments:
                    try:
                        with open(filepath, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            
                        encoders.encode_base64(part)
                        
                        # Set filename in header
                        filename = os.path.basename(filepath)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{filename}"'
                        )
                        
                        # Try to guess content type
                        content_type, _ = mimetypes.guess_type(filepath)
                        if content_type:
                            main_type, sub_type = content_type.split('/', 1)
                            part.set_type(content_type)
                        
                        msg.attach(part)
                    except Exception as e:
                        logger.error(f"Error attaching file {filepath}: {str(e)}")
                        continue
            
            # Build recipient list
            recipients = []
            recipients.extend(addr.strip() for addr in to_addr.split(','))
            if cc:
                recipients.extend(addr.strip() for addr in cc.split(','))
            if bcc:
                recipients.extend(addr.strip() for addr in bcc.split(','))
            
            # Send the email
            self.smtp_connection.send_message(msg, to_addrs=recipients)
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def close_connections(self):
        """Close all active email connections."""
        if self.imap_connection:
            try:
                self.imap_connection.close()
                self.imap_connection.logout()
            except:
                pass
        
        if self.smtp_connection:
            try:
                self.smtp_connection.quit()
            except:
                pass 
    
    def get_thread_for_email(self, message_id):
        """
        Get the conversation thread for a specific email.
        
        Args:
            message_id (str): Message ID to find thread for
        
        Returns:
            EmailThread: Thread containing the email, or None
        """
        return self.thread_manager.get_thread_for_email(message_id)
    
    def get_threads_by_subject(self, subject):
        """
        Find conversation threads by subject.
        
        Args:
            subject (str): Subject to search for
        
        Returns:
            list: List of matching threads
        """
        return self.thread_manager.get_threads_by_subject(subject)
    
    def get_threads_by_participant(self, email_address):
        """
        Find conversation threads involving a specific participant.
        
        Args:
            email_address (str): Participant's email address
        
        Returns:
            list: List of matching threads
        """
        return self.thread_manager.get_threads_by_participant(email_address)
    
    def get_attachment_path(self, message_id, filename):
        """
        Get the path to a saved attachment.
        
        Args:
            message_id (str): ID of the email message
            filename (str): Name of the attachment file
        
        Returns:
            str: Path to the attachment if found, None otherwise
        """
        return self.attachment_manager.get_attachment_path(
            self.account_data['email'],
            str(message_id),
            filename
        )
    
    def cleanup_old_attachments(self, max_age_days=30):
        """Clean up attachments older than specified age."""
        self.attachment_manager.cleanup_old_attachments(max_age_days)
    
    def get_attachment_storage_info(self):
        """Get information about attachment storage."""
        return self.attachment_manager.get_storage_info()
    
    def create_folder(self, folder_name: str) -> bool:
        """
        Create a new email folder/mailbox.
        
        Args:
            folder_name (str): Name of the folder to create
            
        Returns:
            bool: True if folder was created successfully, False otherwise
        """
        logger.logger.debug(f"Creating folder: {folder_name}")
        if not self.imap_connection:
            if not self.connect_imap():
                return False
        
        try:
            result = self.imap_connection.create(folder_name)
            success = result[0] == 'OK'
            if success:
                logger.logger.info(f"Created folder: {folder_name}")
            else:
                logger.logger.error(f"Failed to create folder: {folder_name}")
            return success
        except Exception as e:
            logger.logger.error(f"Error creating folder {folder_name}: {str(e)}")
            return False
    
    def delete_folder(self, folder_name: str) -> bool:
        """
        Delete an email folder/mailbox.
        
        Args:
            folder_name (str): Name of the folder to delete
            
        Returns:
            bool: True if folder was deleted successfully, False otherwise
        """
        logger.logger.debug(f"Deleting folder: {folder_name}")
        if not self.imap_connection:
            if not self.connect_imap():
                return False
        
        try:
            # First, select a different folder if the current one is being deleted
            if self.current_folder == folder_name:
                self.select_folder('INBOX')
            
            result = self.imap_connection.delete(folder_name)
            success = result[0] == 'OK'
            if success:
                logger.logger.info(f"Deleted folder: {folder_name}")
            else:
                logger.logger.error(f"Failed to delete folder: {folder_name}")
            return success
        except Exception as e:
            logger.logger.error(f"Error deleting folder {folder_name}: {str(e)}")
            return False
    
    def rename_folder(self, old_name: str, new_name: str) -> bool:
        """
        Rename an email folder/mailbox.
        
        Args:
            old_name (str): Current folder name
            new_name (str): New folder name
            
        Returns:
            bool: True if folder was renamed successfully, False otherwise
        """
        logger.logger.debug(f"Renaming folder from {old_name} to {new_name}")
        if not self.imap_connection:
            if not self.connect_imap():
                return False
        
        try:
            result = self.imap_connection.rename(old_name, new_name)
            success = result[0] == 'OK'
            if success:
                # Update current folder if it was renamed
                if self.current_folder == old_name:
                    self.current_folder = new_name
                logger.logger.info(f"Renamed folder from {old_name} to {new_name}")
            else:
                logger.logger.error(f"Failed to rename folder from {old_name} to {new_name}")
            return success
        except Exception as e:
            logger.logger.error(f"Error renaming folder {old_name} to {new_name}: {str(e)}")
            return False
    
    def move_email(self, message_id: str, target_folder: str) -> bool:
        """
        Move an email message to another folder.
        
        Args:
            message_id (str): ID of the message to move
            target_folder (str): Name of the target folder
            
        Returns:
            bool: True if move was successful, False otherwise
        """
        logger.logger.debug(f"Moving message {message_id} to folder {target_folder}")
        
        if not self.imap_connection:
            if not self.connect_imap():
                return False
        
        try:
            # Copy message to target folder
            result = self.imap_connection.copy(message_id, target_folder)
            if result[0] != 'OK':
                logger.logger.error(f"Failed to copy message to {target_folder}")
                return False
            
            # Mark original for deletion
            self.imap_connection.store(message_id, '+FLAGS', '\\Deleted')
            
            # Expunge to remove deleted messages
            self.imap_connection.expunge()
            
            logger.logger.info(f"Successfully moved message {message_id} to {target_folder}")
            return True
            
        except Exception as e:
            logger.logger.error(f"Error moving message {message_id} to {target_folder}: {str(e)}")
            return False
    
    def mark_email(self, message_id: str, flag: str, value: bool = True) -> bool:
        """
        Mark or unmark an email with a specific flag.
        
        Args:
            message_id (str): ID of the message to mark
            flag (str): Flag to set (e.g. '\Seen' for read, '\Flagged' for flagged)
            value (bool): True to add flag, False to remove it
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        logger.logger.debug(f"{'Setting' if value else 'Removing'} flag {flag} for message {message_id}")
        
        if not self.imap_connection:
            if not self.connect_imap():
                return False
        
        try:
            # Add or remove flag
            operation = '+FLAGS' if value else '-FLAGS'
            result = self.imap_connection.store(message_id, operation, flag)
            
            success = result[0] == 'OK'
            if success:
                logger.logger.info(
                    f"Successfully {'set' if value else 'removed'} flag {flag} "
                    f"for message {message_id}"
                )
            else:
                logger.logger.error(
                    f"Failed to {'set' if value else 'remove'} flag {flag} "
                    f"for message {message_id}"
                )
            return success
            
        except Exception as e:
            logger.logger.error(
                f"Error {'setting' if value else 'removing'} flag {flag} "
                f"for message {message_id}: {str(e)}"
            )
            return False
    
    def mark_read(self, message_id: str) -> bool:
        """
        Mark an email as read.
        
        Args:
            message_id (str): ID of the message to mark
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.mark_email(message_id, '\\Seen', True)
    
    def mark_unread(self, message_id: str) -> bool:
        """
        Mark an email as unread.
        
        Args:
            message_id (str): ID of the message to mark
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.mark_email(message_id, '\\Seen', False)
    
    def mark_flagged(self, message_id: str) -> bool:
        """
        Flag an email.
        
        Args:
            message_id (str): ID of the message to flag
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.mark_email(message_id, '\\Flagged', True)
    
    def mark_unflagged(self, message_id: str) -> bool:
        """
        Remove flag from an email.
        
        Args:
            message_id (str): ID of the message to unflag
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.mark_email(message_id, '\\Flagged', False)
    
    def sync_folders(self) -> bool:
        """
        Synchronize folders with the server.
        
        Returns:
            bool: True if sync was successful, False otherwise
        """
        logger.logger.debug("Starting folder synchronization")
        
        if not self.imap_connection:
            if not self.connect_imap():
                logger.logger.error("Failed to connect to IMAP server")
                return False
        
        try:
            # List all folders
            folders = self.list_folders()
            
            # Get status for each folder
            for folder in folders:
                status = self.get_folder_status(folder['name'])
                if status:
                    folder['status'] = status
            
            logger.logger.debug(f"Synchronized {len(folders)} folders")
            return True
            
        except Exception as e:
            logger.logger.error(f"Error synchronizing folders: {str(e)}")
            return False
    
    def get_folder_hierarchy(self) -> dict:
        """
        Get folder hierarchy with status information.
        
        Returns:
            dict: Folder hierarchy with status information
        """
        folders = self.list_folders()
        hierarchy = {}
        
        for folder in folders:
            path_parts = folder['name'].split('/')
            current = hierarchy
            
            for i, part in enumerate(path_parts):
                if i == len(path_parts) - 1:
                    # Leaf folder - add with status
                    status = self.get_folder_status(folder['name'])
                    current[part] = {
                        'name': folder['name'],
                        'attributes': folder['attributes'],
                        'status': status
                    }
                else:
                    # Create intermediate path
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        
        return hierarchy
    
    def ensure_special_folders(self) -> bool:
        """
        Ensure all special folders exist.
        
        Returns:
            bool: True if all special folders exist or were created
        """
        special_folders = ['Sent', 'Drafts', 'Trash', 'Spam', 'Archive']
        existing_folders = {f['name'] for f in self.list_folders()}
        
        success = True
        for folder in special_folders:
            if folder not in existing_folders:
                if not self.create_folder(folder):
                    logger.logger.error(f"Failed to create special folder: {folder}")
                    success = False
        
        return success
    
    @handle_errors
    def test_all_connections(self, account_data, error_collection=None):
        """Test both IMAP and SMTP connections with error collection."""
        results = {'imap': False, 'smtp': False}
        
        @collect_errors(error_collection, "IMAP Connection")
        def test_imap():
            with self._create_imap_connection(account_data) as imap:
                results['imap'] = True
                return True
        
        @collect_errors(error_collection, "SMTP Connection")
        def test_smtp():
            with self._create_smtp_connection(account_data) as smtp:
                results['smtp'] = True
                return True
        
        test_imap()
        test_smtp()
        
        return results
    
    @handle_errors
    def sync_emails(self, account_id, folder="INBOX", error_collection=None):
        """Synchronize emails with error collection."""
        account = self.get_account(account_id)
        if not account:
            error_collection.add(f"Account {account_id} not found")
            return
        
        try:
            with self._create_imap_connection(account) as imap:
                # Select the folder
                @collect_errors(error_collection, f"Select Folder: {folder}")
                def select_folder():
                    imap.select(folder)
                select_folder()
                
                # Search for emails
                @collect_errors(error_collection, "Search Emails")
                def search_emails():
                    return imap.search(None, "ALL")[1][0].split()
                email_ids = search_emails()
                
                if not email_ids:
                    return []
                
                # Fetch email data
                emails = []
                for email_id in email_ids:
                    @collect_errors(error_collection, f"Fetch Email {email_id}")
                    def fetch_email():
                        email_data = self._fetch_email_data(imap, email_id)
                        if email_data:
                            emails.append(email_data)
                    fetch_email()
                
                return emails
                
        except Exception as e:
            error_collection.add(f"Failed to sync emails: {str(e)}")
            return []
    
    @handle_errors
    def send_email(self, account_id, email_data, error_collection=None):
        """Send email with error collection."""
        account = self.get_account(account_id)
        if not account:
            error_collection.add(f"Account {account_id} not found")
            return False
        
        try:
            with self._create_smtp_connection(account) as smtp:
                # Prepare email
                @collect_errors(error_collection, "Prepare Email")
                def prepare_email():
                    return self._prepare_email_message(account, email_data)
                msg = prepare_email()
                
                if not msg:
                    return False
                
                # Send email
                @collect_errors(error_collection, "Send Email")
                def send():
                    smtp.send_message(msg)
                send()
                
                return True
                
        except Exception as e:
            error_collection.add(f"Failed to send email: {str(e)}")
            return False
    
    @handle_errors
    def move_email(self, account_id, message_id, target_folder, error_collection=None):
        """Move email to another folder with error collection."""
        account = self.get_account(account_id)
        if not account:
            error_collection.add(f"Account {account_id} not found")
            return False
        
        try:
            with self._create_imap_connection(account) as imap:
                # Copy email
                @collect_errors(error_collection, f"Copy to {target_folder}")
                def copy_email():
                    imap.copy(message_id, target_folder)
                copy_email()
                
                # Delete from source
                @collect_errors(error_collection, "Delete from source")
                def delete_email():
                    imap.store(message_id, '+FLAGS', '\\Deleted')
                    imap.expunge()
                delete_email()
                
                return True
                
        except Exception as e:
            error_collection.add(f"Failed to move email: {str(e)}")
            return False