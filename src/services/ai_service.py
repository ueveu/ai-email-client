"""
AI Service module for handling email analysis and reply generation using Google's Gemini API.
"""

import google.generativeai as genai
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
from utils.logger import logger

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
        
        # Initialize conversation history
        self.conversation_history = []
    
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
            
            Format the response as JSON.
            """
            
            response = self.model.generate_content(prompt)
            return eval(response.text)  # Convert string response to dict
            
        except Exception as e:
            logger.error(f"Error analyzing email content: {str(e)}")
            return {
                "error": str(e),
                "sentiment": "unknown",
                "key_points": [],
                "tone": "unknown",
                "action_items": []
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
            
            prompt = f"""
            Generate three different reply suggestions for this email:
            
            Subject: {subject}
            
            Email Content:
            {email_content}
            
            {conversation_context}
            
            {tone_instruction}
            
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
            prompt = f"""
            Adjust the tone of this reply to be {desired_tone}, while keeping the same message:
            
            Original Reply:
            {reply_text}
            
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
        # Add selected reply to conversation history
        self.conversation_history.append({
            "role": "outgoing",
            "content": selected_reply,
            "context": context
        })
        
        # Note: In a future implementation, this method could be enhanced to:
        # 1. Store successful replies in a database
        # 2. Analyze patterns in selected replies
        # 3. Adjust suggestion algorithms based on user preferences
        # 4. Train a local model on user's writing style 