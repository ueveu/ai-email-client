import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, BinaryIO
from datetime import datetime
from utils.logger import logger
from utils.error_handler import handle_errors

class Attachment:
    """Represents an email attachment with its metadata and content."""
    
    def __init__(self, filename: str, content_type: str, content: bytes):
        """
        Initialize an attachment.
        
        Args:
            filename (str): Original filename of the attachment
            content_type (str): MIME type of the attachment
            content (bytes): Raw content of the attachment
        """
        self.filename = filename
        self.content_type = content_type
        self.content = content
        self.size = len(content)
        self.hash = hashlib.sha256(content).hexdigest()
    
    def save(self, directory: str) -> str:
        """
        Save the attachment to disk.
        
        Args:
            directory (str): Directory to save the attachment in
        
        Returns:
            str: Path to the saved file
        """
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        # Generate safe filename
        safe_filename = self._get_safe_filename(directory)
        filepath = os.path.join(directory, safe_filename)
        
        # Save file
        with open(filepath, 'wb') as f:
            f.write(self.content)
        
        return filepath
    
    def _get_safe_filename(self, directory: str) -> str:
        """Generate a safe, unique filename for the attachment."""
        # Get base filename and extension
        name, ext = os.path.splitext(self.filename)
        if not ext and self.content_type:
            # Try to get extension from content type
            ext = mimetypes.guess_extension(self.content_type) or ''
        
        # Create safe base filename
        safe_name = "".join(c for c in name if c.isalnum() or c in ('-', '_'))
        safe_name = safe_name or 'attachment'
        
        # Add first 8 chars of hash for uniqueness
        unique_name = f"{safe_name}_{self.hash[:8]}{ext}"
        
        # Ensure filename is unique in directory
        counter = 1
        final_name = unique_name
        while os.path.exists(os.path.join(directory, final_name)):
            final_name = f"{safe_name}_{self.hash[:8]}_{counter}{ext}"
            counter += 1
        
        return final_name

class AttachmentManager:
    """Manages email attachments including storage and retrieval."""
    
    def __init__(self, base_directory: str = "attachments"):
        """
        Initialize attachment manager.
        
        Args:
            base_directory (str): Base directory for storing attachments
        """
        self.base_directory = base_directory
        self._ensure_base_directory()
    
    def _ensure_base_directory(self):
        """Create base directory if it doesn't exist."""
        os.makedirs(self.base_directory, exist_ok=True)
    
    def _get_account_directory(self, email_account: str) -> str:
        """Get directory for specific email account."""
        # Create safe directory name from email
        safe_name = "".join(c for c in email_account if c.isalnum() or c in ('-', '_', '.'))
        return os.path.join(self.base_directory, safe_name)
    
    @handle_errors
    def save_attachments(self, email_account: str, message_id: str, 
                        attachments: List[Dict]) -> List[Dict]:
        """
        Save attachments from an email.
        
        Args:
            email_account (str): Email account the attachments belong to
            message_id (str): ID of the email message
            attachments (list): List of attachment dictionaries
        
        Returns:
            list: List of saved attachment information
        """
        # Create account-specific directory
        account_dir = self._get_account_directory(email_account)
        message_dir = os.path.join(account_dir, message_id)
        
        saved_attachments = []
        for att_data in attachments:
            try:
                attachment = Attachment(
                    att_data['filename'],
                    att_data['content_type'],
                    att_data['content']
                )
                
                filepath = attachment.save(message_dir)
                
                saved_attachments.append({
                    'filename': attachment.filename,
                    'content_type': attachment.content_type,
                    'size': attachment.size,
                    'hash': attachment.hash,
                    'filepath': filepath
                })
                
            except Exception as e:
                logger.error(f"Error saving attachment {att_data['filename']}: {str(e)}")
                continue
        
        return saved_attachments
    
    def get_attachment_path(self, email_account: str, message_id: str, 
                          filename: str) -> Optional[str]:
        """
        Get path to a saved attachment.
        
        Args:
            email_account (str): Email account the attachment belongs to
            message_id (str): ID of the email message
            filename (str): Name of the attachment file
        
        Returns:
            Optional[str]: Path to attachment if found, None otherwise
        """
        message_dir = os.path.join(self._get_account_directory(email_account), message_id)
        if not os.path.exists(message_dir):
            return None
        
        # Look for file matching name pattern
        for file in os.listdir(message_dir):
            if file.startswith(filename.split('.')[0]):
                return os.path.join(message_dir, file)
        
        return None
    
    def cleanup_old_attachments(self, max_age_days: int = 30):
        """
        Remove attachments older than specified age.
        
        Args:
            max_age_days (int): Maximum age in days for attachments
        """
        try:
            current_time = datetime.now().timestamp()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            for root, dirs, files in os.walk(self.base_directory):
                for file in files:
                    filepath = os.path.join(root, file)
                    if (current_time - os.path.getctime(filepath)) > max_age_seconds:
                        os.remove(filepath)
                
                # Remove empty directories
                for dir in dirs:
                    dirpath = os.path.join(root, dir)
                    if not os.listdir(dirpath):
                        os.rmdir(dirpath)
                        
        except Exception as e:
            logger.error(f"Error cleaning up attachments: {str(e)}")
    
    def get_storage_info(self) -> Dict:
        """
        Get information about attachment storage.
        
        Returns:
            dict: Storage statistics including total size and count
        """
        total_size = 0
        total_files = 0
        
        for root, _, files in os.walk(self.base_directory):
            for file in files:
                filepath = os.path.join(root, file)
                total_size += os.path.getsize(filepath)
                total_files += 1
        
        return {
            'total_size': total_size,
            'total_files': total_files,
            'base_directory': self.base_directory
        } 