import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import ssl

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
        self._current_folder = "INBOX"
    
    def connect_imap(self):
        """
        Establish IMAP connection with the email server.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
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
            return True
        except Exception as e:
            print(f"IMAP connection error: {str(e)}")
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
    
    def fetch_emails(self, folder="INBOX", limit=50):
        """
        Fetch emails from the specified folder.
        
        Args:
            folder (str): Email folder to fetch from
            limit (int): Maximum number of emails to fetch
        
        Returns:
            list: List of email data dictionaries
        """
        if not self.imap_connection:
            if not self.connect_imap():
                return []
        
        try:
            self.imap_connection.select(folder)
            _, messages = self.imap_connection.search(None, "ALL")
            email_list = []
            
            # Get the last 'limit' messages
            message_numbers = messages[0].split()
            start_index = max(0, len(message_numbers) - limit)
            
            for num in message_numbers[start_index:]:
                _, msg_data = self.imap_connection.fetch(num, "(RFC822)")
                email_message = email.message_from_bytes(msg_data[0][1])
                
                # Extract email data
                subject = email.header.decode_header(email_message["subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                from_addr = email.header.decode_header(email_message["from"])[0][0]
                if isinstance(from_addr, bytes):
                    from_addr = from_addr.decode()
                
                date_str = email_message["date"]
                date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                
                # Get email body
                body = ""
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode()
                            break
                else:
                    body = email_message.get_payload(decode=True).decode()
                
                email_list.append({
                    "subject": subject,
                    "from": from_addr,
                    "date": date,
                    "body": body,
                    "message_id": num
                })
            
            return email_list
        except Exception as e:
            print(f"Error fetching emails: {str(e)}")
            return []
    
    def send_email(self, to_addr, subject, body):
        """
        Send an email using the configured SMTP settings.
        
        Args:
            to_addr (str): Recipient email address
            subject (str): Email subject
            body (str): Email body text
        
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
            
            msg.attach(MIMEText(body, "plain"))
            
            self.smtp_connection.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
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
    
    def get_folders(self) -> list:
        """
        Get list of available email folders.
        
        Returns:
            list: List of folder names and their hierarchical structure
        """
        if not self.imap_connection:
            if not self.connect_imap():
                return []
        
        try:
            # List all folders
            response = self.imap_connection.list()
            folders = []
            
            for folder_data in response[1]:
                # Parse folder data
                flags, delimiter, name = self.imap_connection.list_response(folder_data)
                
                # Convert folder name from bytes to string if needed
                if isinstance(name, bytes):
                    name = name.decode()
                
                # Create folder info dictionary
                folder_info = {
                    "name": name,
                    "flags": flags,
                    "has_children": "\\HasChildren" in flags,
                    "selectable": "\\Noselect" not in flags
                }
                folders.append(folder_info)
            
            return folders
        except Exception as e:
            print(f"Error getting folders: {str(e)}")
            return []
    
    def select_folder(self, folder_name: str) -> bool:
        """
        Select an email folder to work with.
        
        Args:
            folder_name (str): Name of the folder to select
        
        Returns:
            bool: True if folder was selected successfully
        """
        if not self.imap_connection:
            if not self.connect_imap():
                return False
        
        try:
            result = self.imap_connection.select(folder_name)
            if result[0] == "OK":
                self._current_folder = folder_name
                return True
            return False
        except Exception as e:
            print(f"Error selecting folder: {str(e)}")
            return False
    
    def create_folder(self, folder_name: str) -> bool:
        """
        Create a new email folder.
        
        Args:
            folder_name (str): Name of the folder to create
        
        Returns:
            bool: True if folder was created successfully
        """
        if not self.imap_connection:
            if not self.connect_imap():
                return False
        
        try:
            result = self.imap_connection.create(folder_name)
            return result[0] == "OK"
        except Exception as e:
            print(f"Error creating folder: {str(e)}")
            return False
    
    def delete_folder(self, folder_name: str) -> bool:
        """
        Delete an email folder.
        
        Args:
            folder_name (str): Name of the folder to delete
        
        Returns:
            bool: True if folder was deleted successfully
        """
        if not self.imap_connection:
            if not self.connect_imap():
                return False
        
        try:
            result = self.imap_connection.delete(folder_name)
            return result[0] == "OK"
        except Exception as e:
            print(f"Error deleting folder: {str(e)}")
            return False
    
    def rename_folder(self, old_name: str, new_name: str) -> bool:
        """
        Rename an email folder.
        
        Args:
            old_name (str): Current folder name
            new_name (str): New folder name
        
        Returns:
            bool: True if folder was renamed successfully
        """
        if not self.imap_connection:
            if not self.connect_imap():
                return False
        
        try:
            result = self.imap_connection.rename(old_name, new_name)
            return result[0] == "OK"
        except Exception as e:
            print(f"Error renaming folder: {str(e)}")
            return False
    
    def get_folder_status(self, folder_name: str) -> dict:
        """
        Get status information for a folder.
        
        Args:
            folder_name (str): Name of the folder
        
        Returns:
            dict: Folder status information (message count, unread count, etc.)
        """
        if not self.imap_connection:
            if not self.connect_imap():
                return {}
        
        try:
            result = self.imap_connection.status(
                folder_name,
                "(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)"
            )
            
            if result[0] == "OK":
                # Parse status response
                status_data = result[1][0].decode()
                status = {}
                
                # Extract values using string manipulation
                # Example format: "folder_name (MESSAGES 123 RECENT 0 UIDNEXT 1234 ...)"
                parts = status_data.split("(")[1].strip(")").split()
                
                for i in range(0, len(parts), 2):
                    key = parts[i].lower()
                    value = int(parts[i + 1])
                    status[key] = value
                
                return status
            return {}
        except Exception as e:
            print(f"Error getting folder status: {str(e)}")
            return {} 