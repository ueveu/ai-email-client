"""Email reply generation using AI providers."""

from typing import List, Dict, Optional
from datetime import datetime
import logging

class ReplyGenerator:
    """Generates AI-powered email replies using configured providers."""
    
    def __init__(self, ai_provider):
        """
        Initialize the reply generator.
        
        Args:
            ai_provider: The AI provider instance to use for generation
        """
        self.provider = ai_provider
        
    def generate_reply(self, email_data: Dict, context: Optional[List[Dict]] = None) -> List[str]:
        """
        Generate reply suggestions for an email.
        
        Args:
            email_data: Dictionary containing email information
                Required keys: subject, body, from_email, date
            context: Optional list of previous emails in the conversation
        
        Returns:
            List of suggested replies
        """
        try:
            # Construct system instruction
            system_instruction = (
                "You are an AI email assistant helping to write email replies. "
                "Generate a professional and appropriate response to the email. "
                "Consider the context and maintain a suitable tone. "
                "The reply should be clear, concise, and address all key points."
            )
            
            # Build the prompt
            prompt = self._build_prompt(email_data, context)
            
            # Get response from provider
            response = self.provider.get_response(system_instruction, prompt)
            
            # Split into multiple suggestions if provider returned multiple
            suggestions = [s.strip() for s in response.split("---") if s.strip()]
            
            return suggestions if suggestions else [response]
            
        except Exception as e:
            logging.error(f"Error generating reply: {str(e)}")
            return ["Error generating reply suggestions. Please try again."]
    
    def _build_prompt(self, email_data: Dict, context: Optional[List[Dict]] = None) -> str:
        """Build the prompt for the AI provider."""
        prompt_parts = [
            "Please help me write a reply to this email:\n",
            f"Subject: {email_data['subject']}",
            f"From: {email_data['from_email']}",
            f"Date: {email_data['date'].strftime('%Y-%m-%d %H:%M:%S')}\n",
            "Content:",
            email_data['body'],
            "\n"
        ]
        
        if context:
            prompt_parts.extend([
                "\nPrevious conversation context:",
                *[self._format_context_email(e) for e in context],
                "\n"
            ])
        
        prompt_parts.extend([
            "Please generate a professional reply that:",
            "1. Addresses all key points from the email",
            "2. Maintains an appropriate and professional tone",
            "3. Is clear and concise",
            "4. Includes a proper greeting and closing",
            "\nGenerate the reply:"
        ])
        
        return "\n".join(prompt_parts)
    
    def _format_context_email(self, email: Dict) -> str:
        """Format a context email for the prompt."""
        return (
            f"\nOn {email['date'].strftime('%Y-%m-%d %H:%M:%S')}, "
            f"{email['from_email']} wrote:\n"
            f"{email['body']}"
        )
    
    def analyze_sentiment(self, email_content: str) -> Dict:
        """
        Analyze the sentiment and tone of an email.
        
        Args:
            email_content: The email content to analyze
        
        Returns:
            Dictionary containing sentiment analysis results
        """
        try:
            system_instruction = (
                "You are an AI email assistant analyzing email sentiment and tone. "
                "Provide a brief analysis including overall sentiment (positive/negative/neutral), "
                "tone (formal/informal/urgent/friendly), and key emotional indicators."
            )
            
            prompt = f"Please analyze the sentiment and tone of this email:\n\n{email_content}"
            
            response = self.provider.get_response(system_instruction, prompt)
            
            return {
                "analysis": response,
                "success": True
            }
        except Exception as e:
            logging.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "analysis": "Error analyzing email sentiment",
                "success": False,
                "error": str(e)
            } 