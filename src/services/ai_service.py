"""
Service for AI-powered features using Google's Gemini API.
"""

import google.generativeai as genai
from typing import List, Dict, Optional, Set
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
            self.api_key_service.store_api_key('gemini', api_key)
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
            sentiment_history = []
            topics = set()
            
            for email in history:
                # Add participants
                participants.add(email.get('from', ''))
                for recipient in email.get('recipients', {}).get('to', []):
                    participants.add(recipient)
                
                # Track subject evolution
                subjects.append(email.get('subject', ''))
                
                # Analyze sentiment
                sentiment = self.analyze_sentiment(email.get('body', ''))
                sentiment_history.append({
                    'from': email.get('from', ''),
                    'date': email.get('date', ''),
                    'sentiment': sentiment
                })
                
                # Extract topics
                email_topics = self._extract_topics(email.get('body', ''))
                topics.update(email_topics)
                
                # Add to conversation data
                conversation_data.append({
                    'from': email.get('from', ''),
                    'date': email.get('date', ''),
                    'content': email.get('body', ''),
                    'subject': email.get('subject', ''),
                    'sentiment': sentiment,
                    'topics': email_topics
                })
            
            # Prepare prompt for comprehensive analysis
            prompt = self._build_analysis_prompt(conversation_data)
            
            # Generate analysis
            response = self.model.generate_content(prompt)
            if not response.text:
                return {}
            
            # Parse insights from response
            insights = self._parse_conversation_insights(response.text)
            
            # Add metadata and advanced analytics
            insights.update({
                'participant_count': len(participants),
                'participants': list(participants),
                'thread_length': len(history),
                'subject_evolution': subjects,
                'time_span': self._calculate_time_span(history),
                'sentiment_analysis': self._analyze_sentiment_trends(sentiment_history),
                'topic_analysis': self._analyze_topics(topics, conversation_data),
                'conversation_dynamics': self._analyze_conversation_dynamics(conversation_data)
            })
            
            logger.info("Generated comprehensive conversation analysis")
            return insights
            
        except Exception as e:
            logger.error(f"Error analyzing conversation history: {str(e)}")
            return {}
    
    def _build_analysis_prompt(self, conversation_data: List[Dict]) -> str:
        """Build comprehensive analysis prompt."""
        prompt = (
            "Perform a detailed analysis of this email conversation. "
            "Analyze the following aspects:\\n"
            "1. Key discussion points and their evolution\\n"
            "2. Tone patterns and emotional undertones\\n"
            "3. Participant dynamics and roles\\n"
            "4. Decision points and action items\\n"
            "5. Areas of agreement and disagreement\\n"
            "6. Communication style and effectiveness\\n\\n"
            "Conversation History:\\n"
        )
        
        for email in conversation_data:
            prompt += (
                f"\\nFrom: {email['from']}\\n"
                f"Date: {email['date']}\\n"
                f"Subject: {email['subject']}\\n"
                f"Sentiment: {self._format_sentiment(email['sentiment'])}\\n"
                f"Topics: {', '.join(email['topics'])}\\n"
                f"Content:\\n{email['content']}\\n"
                f"{'-' * 40}\\n"
            )
        
        return prompt
    
    def _format_sentiment(self, sentiment: Dict) -> str:
        """Format sentiment data for prompt."""
        if not sentiment:
            return "Neutral"
        
        parts = []
        if 'positivity' in sentiment:
            parts.append(f"Positivity: {sentiment['positivity']:.2f}")
        if 'negativity' in sentiment:
            parts.append(f"Negativity: {sentiment['negativity']:.2f}")
        if 'formality' in sentiment:
            parts.append(f"Formality: {sentiment['formality']:.2f}")
        if 'urgency' in sentiment:
            parts.append(f"Urgency: {sentiment['urgency']:.2f}")
        
        return " | ".join(parts) if parts else "Neutral"
    
    def _extract_topics(self, text: str) -> Set[str]:
        """Extract main topics from text using Gemini."""
        try:
            prompt = (
                "Extract the main topics discussed in this text. "
                "Return only the topic keywords, separated by commas:\\n\\n"
                f"{text}"
            )
            
            response = self.model.generate_content(prompt)
            if not response.text:
                return set()
            
            # Split response into topics and clean
            topics = {
                topic.strip().lower()
                for topic in response.text.split(',')
                if topic.strip()
            }
            
            return topics
            
        except Exception as e:
            logger.error(f"Error extracting topics: {str(e)}")
            return set()
    
    def _analyze_sentiment_trends(self, sentiment_history: List[Dict]) -> Dict:
        """Analyze sentiment trends over the conversation."""
        try:
            if not sentiment_history:
                return {}
            
            # Calculate overall trends
            sentiment_trends = {
                'overall_tone': self._calculate_overall_tone(sentiment_history),
                'tone_shifts': self._detect_tone_shifts(sentiment_history),
                'participant_tones': self._analyze_participant_tones(sentiment_history)
            }
            
            return sentiment_trends
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment trends: {str(e)}")
            return {}
    
    def _calculate_overall_tone(self, sentiment_history: List[Dict]) -> str:
        """Calculate the overall tone of the conversation."""
        try:
            # Calculate average sentiment scores
            total_pos = 0
            total_neg = 0
            total_formal = 0
            count = 0
            
            for entry in sentiment_history:
                sentiment = entry.get('sentiment', {})
                if sentiment:
                    total_pos += sentiment.get('positivity', 0)
                    total_neg += sentiment.get('negativity', 0)
                    total_formal += sentiment.get('formality', 0)
                    count += 1
            
            if count == 0:
                return "Neutral"
            
            avg_pos = total_pos / count
            avg_neg = total_neg / count
            avg_formal = total_formal / count
            
            # Determine overall tone
            if avg_pos > 0.6:
                return "Very Positive"
            elif avg_pos > 0.4:
                return "Positive"
            elif avg_neg > 0.6:
                return "Very Negative"
            elif avg_neg > 0.4:
                return "Negative"
            else:
                return "Neutral"
            
        except Exception as e:
            logger.error(f"Error calculating overall tone: {str(e)}")
            return "Neutral"
    
    def _detect_tone_shifts(self, sentiment_history: List[Dict]) -> List[Dict]:
        """Detect significant shifts in tone during the conversation."""
        try:
            shifts = []
            prev_sentiment = None
            
            for i, entry in enumerate(sentiment_history):
                current = entry.get('sentiment', {})
                if not current or not prev_sentiment:
                    prev_sentiment = current
                    continue
                
                # Calculate sentiment change
                pos_change = abs(
                    current.get('positivity', 0) - 
                    prev_sentiment.get('positivity', 0)
                )
                neg_change = abs(
                    current.get('negativity', 0) - 
                    prev_sentiment.get('negativity', 0)
                )
                
                # Detect significant shifts (threshold: 0.3)
                if pos_change > 0.3 or neg_change > 0.3:
                    shifts.append({
                        'position': i,
                        'from_email': entry['from'],
                        'date': entry['date'],
                        'change_magnitude': max(pos_change, neg_change),
                        'direction': 'positive' if pos_change > neg_change else 'negative'
                    })
                
                prev_sentiment = current
            
            return shifts
            
        except Exception as e:
            logger.error(f"Error detecting tone shifts: {str(e)}")
            return []
    
    def _analyze_participant_tones(self, sentiment_history: List[Dict]) -> Dict:
        """Analyze tone patterns for each participant."""
        try:
            participant_tones = {}
            
            for entry in sentiment_history:
                participant = entry['from']
                sentiment = entry.get('sentiment', {})
                
                if participant not in participant_tones:
                    participant_tones[participant] = {
                        'entries': [],
                        'average_sentiment': {}
                    }
                
                participant_tones[participant]['entries'].append(sentiment)
            
            # Calculate averages for each participant
            for participant, data in participant_tones.items():
                entries = data['entries']
                if not entries:
                    continue
                
                avg_sentiment = {}
                for key in ['positivity', 'negativity', 'formality', 'urgency']:
                    values = [
                        entry.get(key, 0) 
                        for entry in entries 
                        if key in entry
                    ]
                    if values:
                        avg_sentiment[key] = sum(values) / len(values)
                
                data['average_sentiment'] = avg_sentiment
            
            return participant_tones
            
        except Exception as e:
            logger.error(f"Error analyzing participant tones: {str(e)}")
            return {}
    
    def _analyze_topics(self, topics: Set[str], conversation_data: List[Dict]) -> Dict:
        """Analyze topic patterns and evolution."""
        try:
            topic_analysis = {
                'main_topics': list(topics),
                'topic_frequency': {},
                'topic_flow': []
            }
            
            # Calculate topic frequency
            for email in conversation_data:
                email_topics = email.get('topics', set())
                for topic in email_topics:
                    if topic not in topic_analysis['topic_frequency']:
                        topic_analysis['topic_frequency'][topic] = 0
                    topic_analysis['topic_frequency'][topic] += 1
            
            # Analyze topic flow
            for email in conversation_data:
                topic_analysis['topic_flow'].append({
                    'date': email.get('date', ''),
                    'from': email.get('from', ''),
                    'topics': list(email.get('topics', set()))
                })
            
            return topic_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing topics: {str(e)}")
            return {}
    
    def _analyze_conversation_dynamics(self, conversation_data: List[Dict]) -> Dict:
        """Analyze conversation dynamics and patterns."""
        try:
            dynamics = {
                'response_patterns': self._analyze_response_patterns(conversation_data),
                'participation_balance': self._analyze_participation(conversation_data),
                'conversation_flow': self._analyze_flow(conversation_data)
            }
            
            return dynamics
            
        except Exception as e:
            logger.error(f"Error analyzing conversation dynamics: {str(e)}")
            return {}
    
    def _analyze_response_patterns(self, conversation_data: List[Dict]) -> Dict:
        """Analyze patterns in how participants respond to each other."""
        try:
            patterns = {
                'average_response_time': None,
                'response_times': [],
                'response_lengths': []
            }
            
            prev_email = None
            for email in conversation_data:
                if prev_email and email.get('date') and prev_email.get('date'):
                    # Calculate response time
                    response_time = email['date'] - prev_email['date']
                    patterns['response_times'].append({
                        'from': email['from'],
                        'to': prev_email['from'],
                        'time': response_time.total_seconds()
                    })
                
                # Track response lengths
                patterns['response_lengths'].append({
                    'from': email['from'],
                    'length': len(email.get('content', ''))
                })
                
                prev_email = email
            
            # Calculate average response time
            if patterns['response_times']:
                avg_time = sum(
                    rt['time'] for rt in patterns['response_times']
                ) / len(patterns['response_times'])
                patterns['average_response_time'] = avg_time
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error analyzing response patterns: {str(e)}")
            return {}
    
    def _analyze_participation(self, conversation_data: List[Dict]) -> Dict:
        """Analyze participation balance among participants."""
        try:
            participation = {
                'message_count': {},
                'content_length': {},
                'initiator': conversation_data[0]['from'] if conversation_data else None,
                'most_active': None
            }
            
            for email in conversation_data:
                sender = email['from']
                
                # Count messages
                if sender not in participation['message_count']:
                    participation['message_count'][sender] = 0
                participation['message_count'][sender] += 1
                
                # Track content length
                if sender not in participation['content_length']:
                    participation['content_length'][sender] = 0
                participation['content_length'][sender] += len(email.get('content', ''))
            
            # Determine most active participant
            if participation['message_count']:
                participation['most_active'] = max(
                    participation['message_count'].items(),
                    key=lambda x: x[1]
                )[0]
            
            return participation
            
        except Exception as e:
            logger.error(f"Error analyzing participation: {str(e)}")
            return {}
    
    def _analyze_flow(self, conversation_data: List[Dict]) -> List[Dict]:
        """Analyze the flow and structure of the conversation."""
        try:
            flow = []
            
            for i, email in enumerate(conversation_data):
                flow_entry = {
                    'position': i + 1,
                    'from': email['from'],
                    'type': self._determine_email_type(email, conversation_data[:i]),
                    'contributes_new_topic': self._has_new_topics(
                        email.get('topics', set()),
                        conversation_data[:i]
                    )
                }
                flow.append(flow_entry)
            
            return flow
            
        except Exception as e:
            logger.error(f"Error analyzing flow: {str(e)}")
            return []
    
    def _determine_email_type(self, email: Dict, previous_emails: List[Dict]) -> str:
        """Determine the type/role of an email in the conversation."""
        try:
            if not previous_emails:
                return "conversation_start"
            
            # Check if it's a reply
            subject = email.get('subject', '').lower()
            if subject.startswith('re:'):
                return "reply"
            elif subject.startswith('fwd:'):
                return "forward"
            
            # Check content patterns
            content = email.get('content', '').lower()
            if any(q in content for q in ['?', 'could you', 'would you']):
                return "question"
            elif any(w in content for w in ['thanks', 'thank you']):
                return "acknowledgment"
            elif len(content.split()) < 20:
                return "brief_response"
            
            return "detailed_response"
            
        except Exception as e:
            logger.error(f"Error determining email type: {str(e)}")
            return "unknown"
    
    def _has_new_topics(self, current_topics: Set[str], previous_emails: List[Dict]) -> bool:
        """Check if email introduces new topics."""
        try:
            previous_topics = set()
            for email in previous_emails:
                previous_topics.update(email.get('topics', set()))
            
            return bool(current_topics - previous_topics)
            
        except Exception as e:
            logger.error(f"Error checking for new topics: {str(e)}")
            return False
    
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
    
    def analyze_email(self, email_text: str) -> Dict:
        """
        Analyze email content and generate insights.
        
        Args:
            email_text: Email content to analyze
            
        Returns:
            Dict: Analysis results including reply suggestions
        """
        try:
            logger.debug("Generating AI analysis...")
            
            if not self.model:
                return {
                    'reply_suggestions': 'AI analysis not available - Gemini API key not configured'
                }
            
            # Generate analysis prompt
            prompt = f"""
            Analyze this email and provide:
            1. A brief summary
            2. Key points or action items
            3. Suggested reply options
            4. Tone analysis
            
            Email content:
            {email_text}
            """
            
            # Generate analysis
            response = self.model.generate_content(prompt)
            
            if not response.text:
                return {
                    'reply_suggestions': 'Failed to generate analysis'
                }
            
            return {
                'reply_suggestions': response.text
            }
            
        except Exception as e:
            logger.error(f"Error analyzing email: {str(e)}")
            return {
                'reply_suggestions': f'Error generating analysis: {str(e)}'
            }
    
    def generate_reply(self, email_text: str, style: str = 'professional') -> Optional[str]:
        """
        Generate an email reply.
        
        Args:
            email_text: Original email content
            style: Desired reply style (professional, casual, formal)
            
        Returns:
            Optional[str]: Generated reply or None if error
        """
        try:
            if not self.model:
                return None
            
            # Generate reply prompt
            prompt = f"""
            Generate a {style} reply to this email:
            
            Original email:
            {email_text}
            
            Reply should be:
            - Clear and concise
            - Maintain appropriate tone
            - Address all points
            - Include proper greeting and closing
            """
            
            # Generate reply
            response = self.model.generate_content(prompt)
            
            return response.text if response.text else None
            
        except Exception as e:
            logger.error(f"Error generating reply: {str(e)}")
            return None