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
        """Initialize SQLite database with required tables."""
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
                    recipients TEXT,  -- JSON array
                    date TEXT,
                    body TEXT,
                    has_attachments BOOLEAN,
                    metadata TEXT,    -- JSON object
                    last_updated TEXT,
                    flags TEXT        -- JSON array
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
                    local_path TEXT NOT NULL,
                    last_updated TEXT,
                    FOREIGN KEY (message_id) REFERENCES emails(message_id)
                        ON DELETE CASCADE
                )
            """)
            
            # Create accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    email TEXT PRIMARY KEY,
                    last_sync TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_emails_account
                ON emails(account_email, folder)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_emails_date
                ON emails(last_updated)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_attachments_message
                ON attachments(message_id)
            """)
            
            conn.commit()
    
    @handle_errors
    def get_cached_emails(self, account_email: str, folder: str,
                         limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Retrieve cached emails for an account and folder.
        
        Args:
            account_email (str): Email account to get emails for
            folder (str): Folder name
            limit (int): Maximum number of emails to return
            offset (int): Number of emails to skip
        
        Returns:
            List[Dict]: List of cached email data
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get emails
            cursor.execute("""
                SELECT message_id, subject, sender, recipients, date,
                       body, has_attachments, metadata, flags
                FROM emails
                WHERE account_email = ? AND folder = ?
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            """, (account_email, folder, limit, offset))
            
            emails = []
            for row in cursor.fetchall():
                # Get attachments for this email
                cursor.execute("""
                    SELECT filename, content_type, size, local_path
                    FROM attachments
                    WHERE message_id = ?
                """, (row[0],))
                
                attachments = []
                for att_row in cursor.fetchall():
                    attachments.append({
                        'filename': att_row[0],
                        'content_type': att_row[1],
                        'size': att_row[2],
                        'local_path': att_row[3]
                    })
                
                # Build email data dictionary
                email_data = {
                    'message_id': row[0],
                    'subject': row[1],
                    'from': row[2],
                    'recipients': json.loads(row[3]),
                    'date': datetime.fromisoformat(row[4]),
                    'body': row[5],
                    'has_attachments': bool(row[6]),
                    'metadata': json.loads(row[7]),
                    'flags': json.loads(row[8]),
                    'attachments': attachments
                }
                
                emails.append(email_data)
            
            return emails
    
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
    
    def get_email_by_message_id(self, account_email: str, message_id: str) -> Optional[Dict]:
        """
        Get a cached email by its message ID.
        
        Args:
            account_email (str): Email account to search in
            message_id (str): Message ID to find
            
        Returns:
            Optional[Dict]: Email data if found in cache, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get email data
                cursor.execute("""
                    SELECT message_id, subject, sender, recipients, date,
                           body, has_attachments, metadata, flags
                    FROM emails
                    WHERE account_email = ? AND message_id = ?
                """, (account_email, message_id))
                
                row = cursor.fetchone()
                if not row:
                    logger.debug(f"No cached email found with message ID: {message_id}")
                    return None
                
                # Get attachments for this email
                cursor.execute("""
                    SELECT filename, content_type, size, local_path
                    FROM attachments
                    WHERE message_id = ?
                """, (message_id,))
                
                attachments = []
                for att_row in cursor.fetchall():
                    attachments.append({
                        'filename': att_row[0],
                        'content_type': att_row[1],
                        'size': att_row[2],
                        'local_path': att_row[3]
                    })
                
                # Build email data dictionary
                email_data = {
                    'message_id': row[0],
                    'subject': row[1],
                    'from': row[2],
                    'recipients': json.loads(row[3]),
                    'date': datetime.fromisoformat(row[4]),
                    'body': row[5],
                    'has_attachments': bool(row[6]),
                    'metadata': json.loads(row[7]),
                    'flags': json.loads(row[8]),
                    'attachments': attachments
                }
                
                logger.debug(f"Found cached email with message ID: {message_id}")
                return email_data
                
        except Exception as e:
            logger.error(f"Error getting cached email by message ID: {str(e)}")
            return None
    
    def initialize_account(self, email: str):
        """
        Initialize cache for an email account.
        
        Args:
            email: Email address to initialize cache for
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create account-specific tables if needed
                cursor.execute("""
                    INSERT OR IGNORE INTO accounts (email, last_sync)
                    VALUES (?, datetime('now'))
                """, (email,))
                
                conn.commit()
                
            logger.debug(f"Initialized cache for account: {email}")
            
        except Exception as e:
            logger.error(f"Error initializing account cache: {str(e)}")
            raise