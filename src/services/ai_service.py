"""
AI Service module for handling email analysis and reply generation using Google's Gemini API.
"""

import google.generativeai as genai
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from utils.logger import logger
from .reply_learning_service import ReplyLearningService

class AIService:
    """
    Service class for AI-powered email analysis and reply generation.
    Handles communication with Gemini API and maintains conversation context.
    """
    
    def __init__(self):
        """Initialize the AI service with API configuration."""
        load_dotenv()  # Load environment variables
        
        # Configure Gemini API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Initialize conversation history and learning service
        self.conversation_history = []
        self.learning_service = ReplyLearningService()
    
    def analyze_email_content(self, email_content: str, subject: str) -> Dict:
        """
        Analyze email content and extract key information.
        
        Args:
            email_content (str): The body of the email to analyze
            subject (str): The subject of the email
            
        Returns:
            Dict: Analysis results including sentiment, key points, and tone
        """
        try:
            prompt = f"""
            Analyze this email with subject: "{subject}"
            
            Content:
            {email_content}
            
            Please provide:
            1. Overall sentiment (positive, negative, neutral)
            2. Key points or requests
            3. Tone of the message (formal, informal, urgent, etc.)
            4. Any action items mentioned
            5. Context type (business, personal, technical, etc.)
            
            Format the response as JSON.
            """
            
            response = self.model.generate_content(prompt)
            analysis = eval(response.text)  # Convert string response to dict
            
            # Store context type for learning
            if 'context_type' in analysis:
                self.current_context_type = analysis['context_type']
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing email content: {str(e)}")
            return {
                "error": str(e),
                "sentiment": "unknown",
                "key_points": [],
                "tone": "unknown",
                "action_items": [],
                "context_type": "unknown"
            }
    
    def generate_reply_suggestions(self, 
                                 email_content: str,
                                 subject: str,
                                 context: Optional[List[Dict]] = None,
                                 tone: Optional[str] = None) -> List[Dict]:
        """
        Generate multiple reply suggestions for an email.
        
        Args:
            email_content (str): The content of the email to reply to
            subject (str): The subject of the email
            context (List[Dict], optional): Previous emails in the conversation
            tone (str, optional): Desired tone for the reply
            
        Returns:
            List[Dict]: List of reply suggestions with variations
        """
        try:
            # Analyze email to get context type if not already set
            if not hasattr(self, 'current_context_type'):
                analysis = self.analyze_email_content(email_content, subject)
                self.current_context_type = analysis.get('context_type', 'unknown')
            
            # Get preferred tone for this context if none specified
            if not tone:
                tone = self.learning_service.get_preferred_tone(self.current_context_type)
            
            # Get common patterns for this context
            greetings = self.learning_service.get_common_patterns('greeting', limit=3)
            closings = self.learning_service.get_common_patterns('closing', limit=3)
            common_phrases = self.learning_service.get_common_patterns('phrase', limit=5)
            
            # Build conversation context
            conversation_context = ""
            if context:
                conversation_context = "Previous messages in conversation:\n"
                for msg in context:
                    conversation_context += f"From: {msg['from']}\n"
                    conversation_context += f"Content: {msg['content']}\n\n"
            
            tone_instruction = ""
            if tone:
                tone_instruction = f"Use a {tone} tone in the responses."
            
            # Include learned patterns in prompt
            patterns_instruction = ""
            if greetings or closings or common_phrases:
                patterns_instruction = "Consider using these common patterns:\n"
                if greetings:
                    patterns_instruction += f"Greetings: {', '.join(greetings)}\n"
                if closings:
                    patterns_instruction += f"Closings: {', '.join(closings)}\n"
                if common_phrases:
                    patterns_instruction += f"Phrases: {', '.join(common_phrases)}\n"
            
            prompt = f"""
            Generate three different reply suggestions for this email:
            
            Subject: {subject}
            
            Email Content:
            {email_content}
            
            {conversation_context}
            
            {tone_instruction}
            {patterns_instruction}
            
            Generate three different responses with varying styles:
            1. Professional and concise
            2. Friendly and detailed
            3. Balanced and diplomatic
            
            For each response, provide:
            - The complete reply text
            - Style description
            - Tone analysis
            
            Format the response as a list of JSON objects.
            """
            
            response = self.model.generate_content(prompt)
            suggestions = eval(response.text)  # Convert string response to list of dicts
            
            # Update conversation history
            self.conversation_history.append({
                "role": "incoming",
                "content": email_content,
                "subject": subject
            })
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating reply suggestions: {str(e)}")
            return [{
                "reply_text": "Error generating reply suggestions",
                "style": "error",
                "tone": "neutral",
                "error": str(e)
            }]
    
    def adjust_reply_tone(self, reply_text: str, desired_tone: str) -> str:
        """
        Adjust the tone of a reply while maintaining its core message.
        
        Args:
            reply_text (str): Original reply text
            desired_tone (str): Desired tone (e.g., 'more formal', 'more casual', etc.)
            
        Returns:
            str: Adjusted reply text
        """
        try:
            # Get common patterns for maintaining consistency
            greetings = self.learning_service.get_common_patterns('greeting', limit=2)
            closings = self.learning_service.get_common_patterns('closing', limit=2)
            
            patterns_instruction = ""
            if greetings or closings:
                patterns_instruction = "Try to maintain these patterns if present:\n"
                if greetings:
                    patterns_instruction += f"Greetings: {', '.join(greetings)}\n"
                if closings:
                    patterns_instruction += f"Closings: {', '.join(closings)}\n"
            
            prompt = f"""
            Adjust the tone of this reply to be {desired_tone}, while keeping the same message:
            
            Original Reply:
            {reply_text}
            
            {patterns_instruction}
            
            Please provide only the adjusted text without any explanations.
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error adjusting reply tone: {str(e)}")
            return reply_text  # Return original text if adjustment fails
    
    def learn_from_selection(self, selected_reply: str, context: Dict):
        """
        Learn from user's reply selection to improve future suggestions.
        
        Args:
            selected_reply (str): The reply text that was selected by the user
            context (Dict): Context information about the email and conversation
        """
        try:
            # Add selected reply to conversation history
            self.conversation_history.append({
                "role": "outgoing",
                "content": selected_reply,
                "context": context
            })
            
            # Store in learning service
            self.learning_service.store_selected_reply(
                email_context=context,
                selected_reply=selected_reply,
                tone=context.get('tone'),
                style=context.get('style')
            )
            
        except Exception as e:
            logger.error(f"Error learning from selection: {str(e)}")
    
    def get_learning_stats(self) -> Dict:
        """Get statistics about the learning data."""
        return self.learning_service.get_learning_stats()