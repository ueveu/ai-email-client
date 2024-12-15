"""
Email caching system for offline access.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from utils.logger import logger
from utils.error_handler import handle_errors

class EmailCache:
    """Handles caching of emails for offline access."""
    
    def __init__(self, cache_dir: str = "cache"):
        """Initialize email cache."""
        self.cache_dir = cache_dir
        self.db_path = os.path.join(cache_dir, "email_cache.db")
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for email caching."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create emails table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS emails (
                        message_id TEXT PRIMARY KEY,
                        account TEXT NOT NULL,
                        folder TEXT NOT NULL,
                        subject TEXT,
                        sender TEXT,
                        recipients TEXT,
                        date TEXT,
                        content TEXT,
                        html_content TEXT,
                        flags TEXT,
                        has_attachments INTEGER,
                        attachment_info TEXT,
                        last_updated TEXT
                    )
                """)
                
                # Create attachments table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS attachments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_id TEXT,
                        filename TEXT,
                        content_type TEXT,
                        data BLOB,
                        size INTEGER,
                        FOREIGN KEY (message_id) REFERENCES emails (message_id)
                    )
                """)
                
                # Create index for faster lookups
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_account_folder ON emails (account, folder)")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize cache database: {str(e)}")
            raise
    
    @handle_errors
    def cache_email(self, email_data: Dict) -> bool:
        """
        Cache an email and its attachments.
        
        Args:
            email_data: Dictionary containing email data
            
        Returns:
            bool: True if caching was successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Prepare email data for insertion
                email_record = {
                    'message_id': email_data['message_id'],
                    'account': email_data['account'],
                    'folder': email_data['folder'],
                    'subject': email_data.get('subject'),
                    'sender': email_data.get('from'),
                    'recipients': json.dumps(email_data.get('to', [])),
                    'date': email_data.get('date'),
                    'content': email_data.get('text'),
                    'html_content': email_data.get('html'),
                    'flags': json.dumps(email_data.get('flags', [])),
                    'has_attachments': 1 if email_data.get('attachments') else 0,
                    'attachment_info': json.dumps(email_data.get('attachments', [])),
                    'last_updated': datetime.now().isoformat()
                }
                
                # Insert or update email record
                cursor.execute("""
                    INSERT OR REPLACE INTO emails (
                        message_id, account, folder, subject, sender, recipients,
                        date, content, html_content, flags, has_attachments,
                        attachment_info, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, tuple(email_record.values()))
                
                # Cache attachments if present
                if email_data.get('attachments'):
                    for attachment in email_data['attachments']:
                        if attachment.get('data'):  # Only cache if we have the actual data
                            cursor.execute("""
                                INSERT OR REPLACE INTO attachments (
                                    message_id, filename, content_type, data, size
                                ) VALUES (?, ?, ?, ?, ?)
                            """, (
                                email_data['message_id'],
                                attachment['filename'],
                                attachment['content_type'],
                                attachment['data'],
                                len(attachment['data'])
                            ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache email: {str(e)}")
            return False
    
    @handle_errors
    def get_cached_email(self, message_id: str) -> Optional[Dict]:
        """
        Retrieve a cached email by its message ID.
        
        Args:
            message_id: The email's message ID
            
        Returns:
            Dict: Email data if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get email data
                cursor.execute("""
                    SELECT * FROM emails WHERE message_id = ?
                """, (message_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Convert row to dictionary
                columns = [desc[0] for desc in cursor.description]
                email_data = dict(zip(columns, row))
                
                # Parse JSON fields
                email_data['recipients'] = json.loads(email_data['recipients'])
                email_data['flags'] = json.loads(email_data['flags'])
                email_data['attachment_info'] = json.loads(email_data['attachment_info'])
                
                # Get attachments if present
                if email_data['has_attachments']:
                    cursor.execute("""
                        SELECT filename, content_type, data, size
                        FROM attachments
                        WHERE message_id = ?
                    """, (message_id,))
                    
                    attachments = []
                    for att_row in cursor.fetchall():
                        attachments.append({
                            'filename': att_row[0],
                            'content_type': att_row[1],
                            'data': att_row[2],
                            'size': att_row[3]
                        })
                    email_data['attachments'] = attachments
                
                return email_data
                
        except Exception as e:
            logger.error(f"Failed to retrieve cached email: {str(e)}")
            return None
    
    @handle_errors
    def get_cached_emails(self, account: str, folder: str, limit: int = 50) -> List[Dict]:
        """
        Get cached emails for an account and folder.
        
        Args:
            account: Email account
            folder: Folder name
            limit: Maximum number of emails to return
            
        Returns:
            List[Dict]: List of cached emails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM emails 
                    WHERE account = ? AND folder = ?
                    ORDER BY date DESC
                    LIMIT ?
                """, (account, folder, limit))
                
                emails = []
                for row in cursor.fetchall():
                    columns = [desc[0] for desc in cursor.description]
                    email_data = dict(zip(columns, row))
                    
                    # Parse JSON fields
                    email_data['recipients'] = json.loads(email_data['recipients'])
                    email_data['flags'] = json.loads(email_data['flags'])
                    email_data['attachment_info'] = json.loads(email_data['attachment_info'])
                    
                    emails.append(email_data)
                
                return emails
                
        except Exception as e:
            logger.error(f"Failed to retrieve cached emails: {str(e)}")
            return []
    
    @handle_errors
    def clear_cache(self, account: Optional[str] = None, folder: Optional[str] = None):
        """
        Clear email cache.
        
        Args:
            account: Optional account to clear cache for
            folder: Optional folder to clear cache for
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if account and folder:
                    # Clear specific folder
                    cursor.execute("""
                        DELETE FROM attachments 
                        WHERE message_id IN (
                            SELECT message_id FROM emails 
                            WHERE account = ? AND folder = ?
                        )
                    """, (account, folder))
                    
                    cursor.execute("""
                        DELETE FROM emails 
                        WHERE account = ? AND folder = ?
                    """, (account, folder))
                    
                elif account:
                    # Clear entire account
                    cursor.execute("""
                        DELETE FROM attachments 
                        WHERE message_id IN (
                            SELECT message_id FROM emails 
                            WHERE account = ?
                        )
                    """, (account,))
                    
                    cursor.execute("DELETE FROM emails WHERE account = ?", (account,))
                    
                else:
                    # Clear all cache
                    cursor.execute("DELETE FROM attachments")
                    cursor.execute("DELETE FROM emails")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
            raise
    
    @handle_errors
    def get_cache_size(self) -> Dict:
        """
        Get cache size information.
        
        Returns:
            Dict: Cache size information
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get email count
                cursor.execute("SELECT COUNT(*) FROM emails")
                email_count = cursor.fetchone()[0]
                
                # Get attachment count and total size
                cursor.execute("""
                    SELECT COUNT(*), COALESCE(SUM(size), 0)
                    FROM attachments
                """)
                att_count, att_size = cursor.fetchone()
                
                # Get database file size
                db_size = os.path.getsize(self.db_path)
                
                return {
                    'email_count': email_count,
                    'attachment_count': att_count,
                    'attachment_size': att_size,
                    'database_size': db_size
                }
                
        except Exception as e:
            logger.error(f"Failed to get cache size: {str(e)}")
            return {
                'email_count': 0,
                'attachment_count': 0,
                'attachment_size': 0,
                'database_size': 0
            }
    
    def cleanup_old_cache(self, days: int = 30):
        """
        Remove cached emails older than specified days.
        
        Args:
            days: Number of days to keep in cache
        """
        try:
            cutoff_date = (datetime.now() - datetime.timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old attachments
                cursor.execute("""
                    DELETE FROM attachments 
                    WHERE message_id IN (
                        SELECT message_id FROM emails 
                        WHERE last_updated < ?
                    )
                """, (cutoff_date,))
                
                # Delete old emails
                cursor.execute("""
                    DELETE FROM emails 
                    WHERE last_updated < ?
                """, (cutoff_date,))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to cleanup old cache: {str(e)}")
            raise