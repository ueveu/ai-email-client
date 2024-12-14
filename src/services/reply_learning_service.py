"""
Service for storing and analyzing user-selected email replies to improve AI suggestions.
"""

import sqlite3
from typing import List, Dict, Optional
import json
from datetime import datetime
from pathlib import Path
from utils.logger import logger

class ReplyLearningService:
    """Service for learning from user's reply selections to improve future suggestions."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the learning service.
        
        Args:
            db_path (str, optional): Path to the SQLite database file
        """
        if not db_path:
            # Create database in user's data directory
            data_dir = Path.home() / '.ai_email_assistant' / 'data'
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / 'reply_learning.db')
            
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Table for storing selected replies
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS selected_replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_context TEXT NOT NULL,  -- JSON string of email context
                    selected_reply TEXT NOT NULL,
                    original_suggestion TEXT,     -- Original AI suggestion if modified
                    tone TEXT,
                    style TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Table for storing reply patterns
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS reply_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,   -- e.g., 'greeting', 'closing', 'phrase'
                    pattern_text TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_used DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Table for tone preferences
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS tone_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    context_type TEXT NOT NULL,   -- e.g., 'formal', 'casual', 'business'
                    preferred_tone TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_used DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error initializing learning database: {str(e)}")
            raise
    
    def store_selected_reply(self, 
                           email_context: Dict,
                           selected_reply: str,
                           original_suggestion: Optional[str] = None,
                           tone: Optional[str] = None,
                           style: Optional[str] = None):
        """
        Store a user-selected reply for learning.
        
        Args:
            email_context (Dict): Context of the email being replied to
            selected_reply (str): The reply text selected/customized by the user
            original_suggestion (str, optional): The original AI suggestion if modified
            tone (str, optional): The tone of the reply
            style (str, optional): The style of the reply
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                INSERT INTO selected_replies 
                (email_context, selected_reply, original_suggestion, tone, style)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    json.dumps(email_context),
                    selected_reply,
                    original_suggestion,
                    tone,
                    style
                ))
                
                # Extract and store patterns
                self._extract_and_store_patterns(cursor, selected_reply)
                
                # Update tone preferences
                if tone and email_context.get('context_type'):
                    self._update_tone_preference(
                        cursor,
                        email_context['context_type'],
                        tone
                    )
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error storing selected reply: {str(e)}")
    
    def _extract_and_store_patterns(self, cursor: sqlite3.Cursor, reply_text: str):
        """Extract and store common patterns from the reply."""
        # Extract greeting
        greeting = self._extract_greeting(reply_text)
        if greeting:
            self._store_pattern(cursor, 'greeting', greeting)
        
        # Extract closing
        closing = self._extract_closing(reply_text)
        if closing:
            self._store_pattern(cursor, 'closing', closing)
        
        # Extract common phrases
        phrases = self._extract_common_phrases(reply_text)
        for phrase in phrases:
            self._store_pattern(cursor, 'phrase', phrase)
    
    def _store_pattern(self, cursor: sqlite3.Cursor, pattern_type: str, pattern_text: str):
        """Store or update a reply pattern."""
        cursor.execute("""
        INSERT INTO reply_patterns (pattern_type, pattern_text, frequency, last_used)
        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT (pattern_type, pattern_text) DO UPDATE SET
            frequency = frequency + 1,
            last_used = CURRENT_TIMESTAMP
        """)
    
    def _update_tone_preference(self, 
                              cursor: sqlite3.Cursor,
                              context_type: str,
                              tone: str):
        """Update tone preferences for a given context type."""
        cursor.execute("""
        INSERT INTO tone_preferences (context_type, preferred_tone, frequency, last_used)
        VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT (context_type, preferred_tone) DO UPDATE SET
            frequency = frequency + 1,
            last_used = CURRENT_TIMESTAMP
        """, (context_type, tone))
    
    def get_preferred_tone(self, context_type: str) -> Optional[str]:
        """Get the preferred tone for a given context type."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT preferred_tone
                FROM tone_preferences
                WHERE context_type = ?
                ORDER BY frequency DESC, last_used DESC
                LIMIT 1
                """, (context_type,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Error getting preferred tone: {str(e)}")
            return None
    
    def get_common_patterns(self, pattern_type: str, limit: int = 5) -> List[str]:
        """Get commonly used patterns of a specific type."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT pattern_text
                FROM reply_patterns
                WHERE pattern_type = ?
                ORDER BY frequency DESC, last_used DESC
                LIMIT ?
                """, (pattern_type, limit))
                
                return [row[0] for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting common patterns: {str(e)}")
            return []
    
    def _extract_greeting(self, text: str) -> Optional[str]:
        """Extract greeting pattern from text."""
        # Simple extraction of first line if it looks like a greeting
        lines = text.strip().split('\n')
        if lines and any(word in lines[0].lower() 
                        for word in ['hi', 'hello', 'dear', 'good']):
            return lines[0]
        return None
    
    def _extract_closing(self, text: str) -> Optional[str]:
        """Extract closing pattern from text."""
        # Simple extraction of last non-empty line if it looks like a closing
        lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
        if lines and any(word in lines[-1].lower() 
                        for word in ['regards', 'best', 'sincerely', 'thanks']):
            return lines[-1]
        return None
    
    def _extract_common_phrases(self, text: str) -> List[str]:
        """Extract common phrases from text."""
        # This is a simplified implementation
        # In a real application, this would use more sophisticated NLP techniques
        common_phrases = []
        
        # Look for common business phrases
        phrases_to_check = [
            "I hope this email finds you well",
            "Thank you for your prompt response",
            "I look forward to hearing from you",
            "Please let me know if you have any questions",
            "I appreciate your time"
        ]
        
        for phrase in phrases_to_check:
            if phrase.lower() in text.lower():
                common_phrases.append(phrase)
        
        return common_phrases
    
    def get_learning_stats(self) -> Dict:
        """Get statistics about the learning data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Total replies analyzed
                cursor.execute("SELECT COUNT(*) FROM selected_replies")
                stats['total_replies'] = cursor.fetchone()[0]
                
                # Most common tones
                cursor.execute("""
                SELECT tone, COUNT(*) as count
                FROM selected_replies
                WHERE tone IS NOT NULL
                GROUP BY tone
                ORDER BY count DESC
                LIMIT 5
                """)
                stats['common_tones'] = dict(cursor.fetchall())
                
                # Most common patterns
                cursor.execute("""
                SELECT pattern_type, COUNT(*) as count
                FROM reply_patterns
                GROUP BY pattern_type
                """)
                stats['pattern_counts'] = dict(cursor.fetchall())
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting learning stats: {str(e)}")
            return {
                'error': str(e),
                'total_replies': 0,
                'common_tones': {},
                'pattern_counts': {}
            } 