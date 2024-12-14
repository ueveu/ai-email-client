import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from utils.logger import logger
from utils.error_handler import handle_errors

class EmailCache:
    """
    Manages email caching for offline access using SQLite.
    Stores email content, metadata, and attachments.
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize the email cache.
        
        Args:
            cache_dir (str, optional): Directory to store cache files
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".ai-email-assistant" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.cache_dir / "email_cache.db"
        self.attachment_dir = self.cache_dir / "attachments"
        self.attachment_dir.mkdir(exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create emails table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS emails (
                    message_id TEXT PRIMARY KEY,
                    account_email TEXT NOT NULL,
                    folder TEXT NOT NULL,
                    subject TEXT,
                    sender TEXT,
                    recipients TEXT,
                    date TEXT,
                    body TEXT,
                    has_attachments BOOLEAN,
                    metadata TEXT,
                    last_updated TEXT,
                    flags TEXT,
                    UNIQUE(message_id, account_email)
                )
            """)
            
            # Create attachments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    content_type TEXT,
                    size INTEGER,
                    local_path TEXT,
                    last_updated TEXT,
                    FOREIGN KEY(message_id) REFERENCES emails(message_id)
                    ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_account_folder ON emails(account_email, folder)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON emails(date)")
            
            conn.commit()
    
    @handle_errors
    def cache_email(self, account_email: str, folder: str, email_data: Dict):
        """
        Cache an email and its attachments.
        
        Args:
            account_email (str): Email account the message belongs to
            folder (str): Folder name
            email_data (dict): Email data including attachments
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Prepare email data
            message_id = email_data['message_id']
            now = datetime.now().isoformat()
            
            # Store email metadata
            cursor.execute("""
                INSERT OR REPLACE INTO emails (
                    message_id, account_email, folder, subject, sender,
                    recipients, date, body, has_attachments, metadata,
                    last_updated, flags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message_id,
                account_email,
                folder,
                email_data.get('subject', ''),
                email_data.get('from', ''),
                json.dumps(email_data.get('recipients', [])),
                email_data.get('date', ''),
                email_data.get('body', ''),
                bool(email_data.get('attachments', [])),
                json.dumps(email_data.get('metadata', {})),
                now,
                json.dumps(email_data.get('flags', []))
            ))
            
            # Handle attachments
            if 'attachments' in email_data:
                for attachment in email_data['attachments']:
                    # Save attachment to file system
                    filename = attachment['filename']
                    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
                    local_path = self.attachment_dir / f"{message_id}_{safe_filename}"
                    
                    with open(local_path, 'wb') as f:
                        f.write(attachment['content'])
                    
                    # Store attachment metadata
                    cursor.execute("""
                        INSERT OR REPLACE INTO attachments (
                            message_id, filename, content_type, size,
                            local_path, last_updated
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        message_id,
                        filename,
                        attachment.get('content_type', 'application/octet-stream'),
                        len(attachment['content']),
                        str(local_path),
                        now
                    ))
            
            conn.commit()
    
    @handle_errors
    def get_cached_emails(self, account_email: str, folder: str, 
                         limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Retrieve cached emails for a folder.
        
        Args:
            account_email (str): Email account
            folder (str): Folder name
            limit (int): Maximum number of emails to return
            offset (int): Number of emails to skip
        
        Returns:
            list: List of cached email data
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get emails
            cursor.execute("""
                SELECT * FROM emails
                WHERE account_email = ? AND folder = ?
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            """, (account_email, folder, limit, offset))
            
            emails = []
            for row in cursor.fetchall():
                email_data = dict(row)
                
                # Convert JSON strings back to objects
                email_data['recipients'] = json.loads(email_data['recipients'])
                email_data['metadata'] = json.loads(email_data['metadata'])
                email_data['flags'] = json.loads(email_data['flags'])
                
                # Get attachments if any
                if email_data['has_attachments']:
                    cursor.execute("""
                        SELECT * FROM attachments
                        WHERE message_id = ?
                    """, (email_data['message_id'],))
                    
                    attachments = []
                    for att_row in cursor.fetchall():
                        attachment = dict(att_row)
                        # Load attachment content if needed
                        with open(attachment['local_path'], 'rb') as f:
                            attachment['content'] = f.read()
                        attachments.append(attachment)
                    
                    email_data['attachments'] = attachments
                
                emails.append(email_data)
            
            return emails
    
    @handle_errors
    def clear_old_cache(self, days: int = 30):
        """
        Clear cached emails older than specified days.
        
        Args:
            days (int): Number of days to keep in cache
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get attachments to delete
            cursor.execute("""
                SELECT local_path FROM attachments
                WHERE message_id IN (
                    SELECT message_id FROM emails
                    WHERE last_updated < ?
                )
            """, (cutoff_date,))
            
            # Delete attachment files
            for (local_path,) in cursor.fetchall():
                try:
                    os.remove(local_path)
                except OSError:
                    pass
            
            # Delete old records
            cursor.execute("DELETE FROM emails WHERE last_updated < ?", (cutoff_date,))
            conn.commit()
    
    @handle_errors
    def get_cache_size(self) -> Dict:
        """
        Get cache size information.
        
        Returns:
            dict: Cache size information
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get database stats
            cursor.execute("SELECT COUNT(*) FROM emails")
            email_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM attachments")
            attachment_count = cursor.fetchone()[0]
            
            # Calculate sizes
            db_size = os.path.getsize(self.db_path)
            attachment_size = sum(
                os.path.getsize(f) for f in self.attachment_dir.glob('*')
                if f.is_file()
            )
            
            return {
                'email_count': email_count,
                'attachment_count': attachment_count,
                'database_size': db_size,
                'attachment_size': attachment_size,
                'total_size': db_size + attachment_size
            }
    
    def clear_cache(self):
        """Clear all cached data."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM emails")
            conn.commit()
        
        # Delete all attachment files
        for file in self.attachment_dir.glob('*'):
            try:
                os.remove(file)
            except OSError:
                pass 