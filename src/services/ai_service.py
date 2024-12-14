"""
Service for AI-powered features using Google's Gemini API.
"""

import google.generativeai as genai
from typing import List, Dict, Optional
import json
from pathlib import Path
from datetime import datetime
import os
from utils.logger import logger
from services.api_key_service import APIKeyService

class AIService:
    """Service for AI-powered features using Gemini."""
    
    def __init__(self):
        """Initialize the AI service."""
        self.api_key_service = APIKeyService()
        self.model = None
        self.learning_data_path = Path.home() / ".ai-email-assistant" / "learning"
        self.learning_data_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize Gemini
        self._initialize_gemini()
        
        # Load learning data
        self.learning_data = self._load_learning_data()
    
    def _initialize_gemini(self):
        """Initialize Gemini API with API key."""
        try:
            api_key = self.api_key_service.get_api_key('gemini')
            if not api_key:
                logger.warning("No Gemini API key found")
                return
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            logger.info("Gemini API initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Gemini API: {str(e)}")
            self.model = None
    
    def _load_learning_data(self) -> Dict:
        """Load learning data from file."""
        try:
            data_file = self.learning_data_path / "learning_data.json"
            if data_file.exists():
                with open(data_file, 'r') as f:
                    return json.load(f)
            
            # Initialize new learning data
            return {
                'user_preferences': {},
                'common_phrases': {},
                'tone_patterns': {},
                'response_feedback': []
            }
            
        except Exception as e:
            logger.error(f"Error loading learning data: {str(e)}")
            return {}
    
    def _save_learning_data(self):
        """Save learning data to file."""
        try:
            data_file = self.learning_data_path / "learning_data.json"
            with open(data_file, 'w') as f:
                json.dump(self.learning_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving learning data: {str(e)}")
    
    def generate_reply(
        self,
        email_content: str,
        context: Optional[Dict] = None,
        tone: Optional[str] = None,
        num_suggestions: int = 3
    ) -> List[str]:
        """
        Generate email reply suggestions with enhanced context awareness.
        
        Args:
            email_content: Content of the email to reply to
            context: Additional context (e.g., conversation history)
            tone: Desired tone of the reply
            num_suggestions: Number of suggestions to generate
            
        Returns:
            List of reply suggestions
        """
        if not self.model:
            logger.error("Gemini API not initialized")
            return []
        
        try:
            # Analyze conversation history if provided
            history_analysis = {}
            if context and 'conversation_history' in context:
                history = context.get('conversation_history', [])
                if isinstance(history, list):
                    history_analysis = self.analyze_conversation_history(history)
            
            # Build enhanced prompt
            prompt = self._build_reply_prompt(
                email_content,
                context,
                tone,
                history_analysis
            )
            
            # Generate replies
            responses = []
            for _ in range(num_suggestions):
                response = self.model.generate_content(prompt)
                if response.text:
                    responses.append(response.text.strip())
            
            logger.info(f"Generated {len(responses)} reply suggestions")
            return responses
            
        except Exception as e:
            logger.error(f"Error generating reply: {str(e)}")
            return []
    
    def _build_reply_prompt(
        self,
        email_content: str,
        context: Optional[Dict] = None,
        tone: Optional[str] = None,
        history_analysis: Optional[Dict] = None
    ) -> str:
        """Build enhanced prompt for reply generation."""
        prompt_parts = [
            "Generate a professional email reply to the following email:",
            f"\nOriginal Email:\n{email_content}\n"
        ]
        
        # Add conversation history analysis if available
        if history_analysis:
            if history_analysis.get('key_points'):
                prompt_parts.append(
                    "\nKey Discussion Points:\n" +
                    "\n".join(f"- {point}" for point in history_analysis['key_points'])
                )
            
            if history_analysis.get('tone_patterns'):
                prompt_parts.append(
                    "\nConversation Tone Patterns:\n" +
                    "\n".join(f"- {pattern}" for pattern in history_analysis['tone_patterns'])
                )
            
            if history_analysis.get('suggested_approach'):
                prompt_parts.append(
                    f"\nSuggested Approach:\n{history_analysis['suggested_approach']}"
                )
        
        # Add context if provided
        if context:
            if 'relationship' in context:
                prompt_parts.append(f"\nRelationship: {context['relationship']}")
            
            if 'conversation_history' in context:
                prompt_parts.append(
                    "\nConversation History:\n" + context['conversation_history']
                )
        
        # Add tone instruction
        if tone:
            prompt_parts.append(f"\nUse a {tone} tone in the reply.")
        
        # Add learned preferences
        if 'user_preferences' in self.learning_data:
            prefs = self.learning_data['user_preferences']
            if prefs:
                prompt_parts.append(
                    "\nConsider these preferences:\n" +
                    "\n".join(f"- {p}" for p in prefs)
                )
        
        prompt_parts.append("\nReply:")
        return "\n".join(prompt_parts)
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with sentiment analysis results
        """
        if not self.model:
            logger.error("Gemini API not initialized")
            return {}
        
        try:
            prompt = (
                "Analyze the sentiment of the following text. "
                "Provide scores for: positivity (0-1), negativity (0-1), "
                "formality (0-1), and urgency (0-1).\n\n"
                f"Text: {text}"
            )
            
            response = self.model.generate_content(prompt)
            if not response.text:
                return {}
            
            # Parse scores from response
            scores = {}
            for line in response.text.split('\n'):
                if ':' in line:
                    key, value = line.split(':')
                    try:
                        scores[key.strip().lower()] = float(value.strip())
                    except:
                        continue
            
            return scores
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {}
    
    def learn_from_selection(
        self,
        selected_reply: str,
        context: Dict,
        feedback: Optional[str] = None
    ):
        """
        Learn from user's reply selection.
        
        Args:
            selected_reply: The reply the user selected
            context: Context of the selection
            feedback: Optional user feedback
        """
        try:
            # Add to response feedback
            feedback_entry = {
                'timestamp': datetime.now().isoformat(),
                'selected_reply': selected_reply,
                'context': context,
                'feedback': feedback
            }
            self.learning_data['response_feedback'].append(feedback_entry)
            
            # Update tone patterns
            if 'tone' in context:
                tone = context['tone']
                if tone not in self.learning_data['tone_patterns']:
                    self.learning_data['tone_patterns'][tone] = []
                self.learning_data['tone_patterns'][tone].append(selected_reply)
            
            # Extract and store common phrases
            words = selected_reply.split()
            for i in range(len(words) - 2):
                phrase = ' '.join(words[i:i+3])
                if phrase not in self.learning_data['common_phrases']:
                    self.learning_data['common_phrases'][phrase] = 0
                self.learning_data['common_phrases'][phrase] += 1
            
            # Save learning data
            self._save_learning_data()
            logger.info("Updated learning data with user selection")
            
        except Exception as e:
            logger.error(f"Error learning from selection: {str(e)}")
    
    def get_learning_stats(self) -> Dict:
        """
        Get statistics about learned data.
        
        Returns:
            Dict containing learning statistics
        """
        try:
            stats = {
                'total_replies': len(self.learning_data.get('response_feedback', [])),
                'common_tones': {},
                'pattern_counts': {
                    'phrases': len(self.learning_data.get('common_phrases', {})),
                    'preferences': len(self.learning_data.get('user_preferences', {})),
                    'tone_patterns': len(self.learning_data.get('tone_patterns', {}))
                }
            }
            
            # Count tone usage
            for feedback in self.learning_data.get('response_feedback', []):
                tone = feedback.get('context', {}).get('tone')
                if tone:
                    if tone not in stats['common_tones']:
                        stats['common_tones'][tone] = 0
                    stats['common_tones'][tone] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting learning stats: {str(e)}")
            return {}
    
    def clear_learning_data(self):
        """Clear all learning data."""
        try:
            self.learning_data = {
                'user_preferences': {},
                'common_phrases': {},
                'tone_patterns': {},
                'response_feedback': []
            }
            self._save_learning_data()
            logger.info("Cleared learning data")
            
        except Exception as e:
            logger.error(f"Error clearing learning data: {str(e)}")
    
    def update_api_key(self, api_key: str):
        """
        Update the Gemini API key.
        
        Args:
            api_key: New API key
        """
        try:
            self.api_key_service.save_api_key('gemini', api_key)
            self._initialize_gemini()
            logger.info("Updated Gemini API key")
            
        except Exception as e:
            logger.error(f"Error updating API key: {str(e)}")
    
    def test_api_key(self, api_key: str) -> bool:
        """
        Test if an API key is valid.
        
        Args:
            api_key: API key to test
            
        Returns:
            bool: True if key is valid
        """
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Test.")
            return bool(response.text)
            
        except Exception as e:
            logger.error(f"API key test failed: {str(e)}")
            return False
    
    def analyze_conversation_history(self, history: List[Dict]) -> Dict:
        """
        Analyze conversation history to provide context for AI replies.
        
        Args:
            history: List of email data dictionaries in chronological order
            
        Returns:
            Dict containing analysis results
        """
        if not self.model:
            logger.error("Gemini API not initialized")
            return {}
        
        try:
            # Extract key information from history
            conversation_data = []
            participants = set()
            subjects = []
            
            for email in history:
                # Add participants
                participants.add(email.get('from', ''))
                for recipient in email.get('recipients', {}).get('to', []):
                    participants.add(recipient)
                
                # Track subject evolution
                subjects.append(email.get('subject', ''))
                
                # Add to conversation data
                conversation_data.append({
                    'from': email.get('from', ''),
                    'date': email.get('date', ''),
                    'content': email.get('body', ''),
                    'subject': email.get('subject', '')
                })
            
            # Prepare prompt for analysis
            prompt = (
                "Analyze this email conversation and provide insights. "
                "Focus on key points, tone patterns, and important context.\n\n"
                "Conversation History:\n"
            )
            
            for email in conversation_data:
                prompt += f"\nFrom: {email['from']}\nDate: {email['date']}"
                prompt += f"\nSubject: {email['subject']}\n{email['content']}\n"
            
            # Generate analysis
            response = self.model.generate_content(prompt)
            if not response.text:
                return {}
            
            # Parse insights from response
            insights = self._parse_conversation_insights(response.text)
            
            # Add metadata
            insights.update({
                'participant_count': len(participants),
                'participants': list(participants),
                'thread_length': len(history),
                'subject_evolution': subjects,
                'time_span': self._calculate_time_span(history)
            })
            
            logger.info("Generated conversation analysis")
            return insights
            
        except Exception as e:
            logger.error(f"Error analyzing conversation history: {str(e)}")
            return {}
    
    def _parse_conversation_insights(self, analysis_text: str) -> Dict:
        """Parse AI-generated conversation analysis into structured data."""
        insights = {
            'key_points': [],
            'tone_patterns': [],
            'context_notes': [],
            'suggested_approach': None
        }
        
        try:
            # Split analysis into sections
            sections = analysis_text.split('\n\n')
            current_section = None
            
            for line in analysis_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Detect section headers
                if line.lower().startswith('key points:'):
                    current_section = 'key_points'
                elif line.lower().startswith('tone:'):
                    current_section = 'tone_patterns'
                elif line.lower().startswith('context:'):
                    current_section = 'context_notes'
                elif line.lower().startswith('suggested approach:'):
                    current_section = 'suggested_approach'
                elif current_section:
                    # Add content to appropriate section
                    if current_section == 'suggested_approach':
                        insights[current_section] = line
                    else:
                        insights[current_section].append(line)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error parsing conversation insights: {str(e)}")
            return insights
    
    def _calculate_time_span(self, history: List[Dict]) -> Dict:
        """Calculate the time span of the conversation."""
        try:
            dates = [
                email.get('date') for email in history 
                if isinstance(email.get('date'), datetime)
            ]
            
            if not dates:
                return {'duration': None, 'start': None, 'end': None}
            
            start_date = min(dates)
            end_date = max(dates)
            duration = end_date - start_date
            
            return {
                'duration': duration,
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating time span: {str(e)}")
            return {'duration': None, 'start': None, 'end': None}