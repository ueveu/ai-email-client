import re
from typing import List, Dict, Optional
from datetime import datetime
from email.utils import parseaddr, getaddresses
from utils.logger import logger
from utils.error_handler import handle_errors

class EmailThread:
    """Represents a conversation thread containing related emails."""
    
    def __init__(self, root_email: Dict):
        """
        Initialize a thread with a root email.
        
        Args:
            root_email (dict): The first email in the thread
        """
        self.root_email = root_email
        self.emails = [root_email]
        self.participants = self._extract_participants(root_email)
        self.subject = self._clean_subject(root_email['subject'])
        self.last_updated = root_email['date']
        self.message_ids = {root_email['message_id']}
        self.references = set()
        
        # Extract references from root email
        if 'metadata' in root_email and 'headers' in root_email['metadata']:
            headers = root_email['metadata']['headers']
            self._add_references(headers.get('References', ''))
            self._add_references(headers.get('In-Reply-To', ''))
    
    def _clean_subject(self, subject: str) -> str:
        """Remove Re:, Fwd:, etc. from subject."""
        clean = re.sub(r'^(?:Re|Fwd|Fw|FWD|RE|FW):\s*', '', subject, flags=re.IGNORECASE)
        return clean.strip()
    
    def _extract_participants(self, email_data: Dict) -> set:
        """Extract all email addresses from an email."""
        participants = {email_data['from']}
        
        for recipient_type in ['to', 'cc', 'bcc']:
            if recipient_type in email_data['recipients']:
                participants.update(email_data['recipients'][recipient_type])
        
        return participants
    
    def _add_references(self, refs: str):
        """Add message ID references from email headers."""
        if refs:
            # Split on whitespace and add each reference
            self.references.update(ref.strip() for ref in refs.split())
    
    def add_email(self, email_data: Dict) -> bool:
        """
        Add an email to the thread if it belongs.
        
        Args:
            email_data (dict): Email data to potentially add to thread
        
        Returns:
            bool: True if email was added to thread, False otherwise
        """
        if email_data['message_id'] in self.message_ids:
            return False
        
        # Check if email belongs in thread
        headers = email_data['metadata']['headers']
        
        # Check references
        refs = set()
        refs.update(ref.strip() for ref in headers.get('References', '').split())
        refs.update(ref.strip() for ref in headers.get('In-Reply-To', '').split())
        
        # Check if this email references any in our thread
        if not (refs & (self.message_ids | self.references)):
            # No direct reference, check subject and participants
            if (self._clean_subject(email_data['subject']) != self.subject or
                not (self._extract_participants(email_data) & self.participants)):
                return False
        
        # Add email to thread
        self.emails.append(email_data)
        self.message_ids.add(email_data['message_id'])
        self.references.update(refs)
        self.participants.update(self._extract_participants(email_data))
        
        # Update last_updated if this email is newer
        if email_data['date'] > self.last_updated:
            self.last_updated = email_data['date']
        
        return True
    
    def get_sorted_emails(self) -> List[Dict]:
        """Get thread emails sorted by date."""
        return sorted(self.emails, key=lambda x: x['date'])

class ThreadManager:
    """Manages email threading for a set of emails."""
    
    def __init__(self):
        """Initialize thread manager."""
        self.threads = []
    
    @handle_errors
    def process_emails(self, emails: List[Dict]) -> List[EmailThread]:
        """
        Process a list of emails into conversation threads.
        
        Args:
            emails (list): List of email data dictionaries
        
        Returns:
            list: List of EmailThread objects
        """
        # Sort emails by date (oldest first)
        sorted_emails = sorted(emails, key=lambda x: x['date'])
        
        # Process each email
        for email_data in sorted_emails:
            # Try to add to existing thread
            added = False
            for thread in self.threads:
                if thread.add_email(email_data):
                    added = True
                    break
            
            # Create new thread if not added to existing one
            if not added:
                self.threads.append(EmailThread(email_data))
        
        # Sort threads by last update time
        self.threads.sort(key=lambda x: x.last_updated, reverse=True)
        return self.threads
    
    def get_thread_for_email(self, message_id: str) -> Optional[EmailThread]:
        """
        Find the thread containing a specific email.
        
        Args:
            message_id (str): Message ID to find
        
        Returns:
            Optional[EmailThread]: Thread containing the email, or None
        """
        for thread in self.threads:
            if message_id in thread.message_ids:
                return thread
        return None
    
    def get_thread_count(self) -> int:
        """Get number of threads."""
        return len(self.threads)
    
    def get_threads_by_subject(self, subject: str) -> List[EmailThread]:
        """
        Find threads by subject.
        
        Args:
            subject (str): Subject to search for
        
        Returns:
            list: List of matching threads
        """
        clean_subject = re.sub(r'^(?:Re|Fwd|Fw|FWD|RE|FW):\s*', '', subject, flags=re.IGNORECASE).strip()
        return [thread for thread in self.threads if thread.subject == clean_subject]
    
    def get_threads_by_participant(self, email_address: str) -> List[EmailThread]:
        """
        Find threads involving a specific participant.
        
        Args:
            email_address (str): Participant's email address
        
        Returns:
            list: List of matching threads
        """
        return [thread for thread in self.threads if email_address in thread.participants] 