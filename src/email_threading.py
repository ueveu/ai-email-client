"""
Email threading and conversation management.
"""

import re
from typing import List, Dict, Optional, Set
from datetime import datetime
from email.utils import parseaddr, getaddresses
from utils.logger import logger
from utils.error_handler import handle_errors

class EmailThread:
    """Represents a conversation thread of related emails."""
    
    def __init__(self, initial_email: Dict):
        """
        Initialize thread with first email.
        
        Args:
            initial_email (Dict): First email in the thread
        """
        self.emails = [initial_email]
        self.subject = self._clean_subject(initial_email['subject'])
        self.participants = self._extract_participants(initial_email)
        self.message_ids = {initial_email['message_id']}
        self.last_updated = initial_email['date']
        self.references = self._extract_references(initial_email)
    
    def _clean_subject(self, subject: str) -> str:
        """Remove Re:, Fwd:, etc. from subject."""
        return re.sub(r'^(?:Re|Fwd|Fw|FWD|RE|FW):\s*', '', subject, flags=re.IGNORECASE).strip()
    
    def _extract_participants(self, email_data: Dict) -> Set[str]:
        """Extract all email addresses involved in the email."""
        participants = set()
        
        # Add sender
        _, sender = parseaddr(email_data['from'])
        if sender:
            participants.add(sender.lower())
        
        # Add all recipients
        for recipient_type in ['to', 'cc', 'bcc']:
            if recipient_type in email_data['recipients']:
                for addr in email_data['recipients'][recipient_type]:
                    _, email = parseaddr(addr)
                    if email:
                        participants.add(email.lower())
        
        return participants
    
    def _extract_references(self, email_data: Dict) -> Set[str]:
        """Extract message IDs from References and In-Reply-To headers."""
        references = set()
        
        # Get message IDs from headers
        headers = email_data.get('metadata', {}).get('headers', {})
        
        # Add References
        if 'References' in headers:
            refs = headers['References'].split()
            references.update(ref.strip('<>') for ref in refs)
        
        # Add In-Reply-To
        if 'In-Reply-To' in headers:
            reply_to = headers['In-Reply-To'].strip('<>')
            if reply_to:
                references.add(reply_to)
        
        return references
    
    def matches_subject(self, subject: str) -> bool:
        """Check if a subject matches this thread."""
        return self._clean_subject(subject) == self.subject
    
    def has_participant(self, email_address: str) -> bool:
        """Check if an email address is part of this thread."""
        return email_address.lower() in self.participants
    
    def is_related(self, email_data: Dict) -> bool:
        """
        Check if an email belongs to this thread.
        
        Args:
            email_data (Dict): Email data to check
        
        Returns:
            bool: True if email belongs to this thread
        """
        # Check message ID references
        message_id = email_data['message_id']
        if message_id in self.references:
            return True
        
        # Check if this email references any messages in the thread
        email_refs = self._extract_references(email_data)
        if self.message_ids & email_refs:
            return True
        
        # Check subject (excluding Re:, Fwd:, etc.)
        if self.matches_subject(email_data['subject']):
            # If subject matches, check for participant overlap
            email_participants = self._extract_participants(email_data)
            return bool(self.participants & email_participants)
        
        return False
    
    def add_email(self, email_data: Dict) -> bool:
        """
        Add an email to the thread if related.
        
        Args:
            email_data (Dict): Email data to add
        
        Returns:
            bool: True if email was added
        """
        if not self.is_related(email_data):
            return False
        
        # Add email
        self.emails.append(email_data)
        self.message_ids.add(email_data['message_id'])
        self.participants.update(self._extract_participants(email_data))
        self.references.update(self._extract_references(email_data))
        
        # Update last_updated if this email is newer
        if email_data['date'] > self.last_updated:
            self.last_updated = email_data['date']
        
        # Sort emails by date
        self.emails.sort(key=lambda x: x['date'])
        return True
    
    def get_email_count(self) -> int:
        """Get number of emails in thread."""
        return len(self.emails)
    
    def get_latest_email(self) -> Dict:
        """Get the most recent email in the thread."""
        return max(self.emails, key=lambda x: x['date'])
    
    def get_first_email(self) -> Dict:
        """Get the first email in the thread."""
        return min(self.emails, key=lambda x: x['date'])
    
    def get_participant_count(self) -> int:
        """Get number of unique participants."""
        return len(self.participants)
    
    def get_time_span(self) -> float:
        """Get time span of thread in hours."""
        if len(self.emails) < 2:
            return 0.0
        
        start = min(email['date'] for email in self.emails)
        end = max(email['date'] for email in self.emails)
        return (end - start).total_seconds() / 3600

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
        return [thread for thread in self.threads if thread.has_participant(email_address)] 