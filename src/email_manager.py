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
        self.current_folder = None
    
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
    
    def fetch_emails(self, folder=None, limit=50, offset=0):
        """
        Fetch emails from the specified folder.
        
        Args:
            folder (str, optional): Email folder to fetch from. If None, uses current folder
            limit (int): Maximum number of emails to fetch
            offset (int): Number of emails to skip from the start
        
        Returns:
            list: List of email data dictionaries
        """
        if folder and folder != self.current_folder:
            if not self.select_folder(folder):
                return []
        elif not self.current_folder:
            if not self.select_folder('INBOX'):
                return []
        
        try:
            _, messages = self.imap_connection.search(None, "ALL")
            email_list = []
            
            # Get message numbers and apply offset and limit
            message_numbers = messages[0].split()
            message_numbers.reverse()  # Reverse to get newest first
            start_index = offset
            end_index = min(offset + limit, len(message_numbers))
            
            for num in message_numbers[start_index:end_index]:
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
                    "message_id": num,
                    "folder": self.current_folder
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