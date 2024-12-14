import google.generativeai as genai
from typing import List, Dict

class AIReplyGenerator:
    """
    Handles the generation of email replies using the Gemini API.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the AI reply generator.
        
        Args:
            api_key (str): Google API key for accessing Gemini
        """
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def generate_reply(self, email_data: Dict, conversation_history: List[Dict] = None) -> List[str]:
        """
        Generate reply suggestions for an email.
        
        Args:
            email_data (dict): Current email data including subject and body
            conversation_history (list): List of previous emails in the conversation
        
        Returns:
            list: List of suggested replies
        """
        # Construct the prompt
        prompt = self._construct_prompt(email_data, conversation_history)
        
        try:
            # Generate multiple responses
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'top_k': 40,
                    'top_p': 0.95,
                    'candidate_count': 3,
                }
            )
            
            # Extract and format replies
            replies = []
            for candidate in response.candidates:
                reply = candidate.text.strip()
                # Clean up the response
                if reply.startswith('"') and reply.endswith('"'):
                    reply = reply[1:-1]
                replies.append(reply)
            
            return replies
        except Exception as e:
            print(f"Error generating replies: {str(e)}")
            return ["Error generating reply. Please try again."]
    
    def _construct_prompt(self, email_data: Dict, conversation_history: List[Dict] = None) -> str:
        """
        Construct the prompt for the AI model.
        
        Args:
            email_data (dict): Current email data
            conversation_history (list): Previous emails in the conversation
        
        Returns:
            str: Formatted prompt for the AI model
        """
        prompt = [
            "Generate a professional email reply to the following email.",
            "Consider the context and maintain an appropriate tone.",
            "\nOriginal Email:",
            f"Subject: {email_data['subject']}",
            f"From: {email_data['from']}",
            f"\nContent:\n{email_data['body']}\n"
        ]
        
        if conversation_history:
            prompt.append("\nPrevious conversation context:")
            for email in conversation_history:
                prompt.extend([
                    f"\nDate: {email['date']}",
                    f"From: {email['from']}",
                    f"Content: {email['body']}\n"
                ])
        
        prompt.extend([
            "\nPlease generate a clear, concise, and professional reply.",
            "The reply should:",
            "1. Address the main points of the email",
            "2. Maintain a professional and appropriate tone",
            "3. Be clear and concise",
            "4. Include a proper greeting and closing",
            "\nGenerate the reply:"
        ])
        
        return "\n".join(prompt)
    
    def analyze_sentiment(self, email_content: str) -> Dict:
        """
        Analyze the sentiment and tone of an email.
        
        Args:
            email_content (str): Email content to analyze
        
        Returns:
            dict: Sentiment analysis results
        """
        prompt = [
            "Analyze the following email content for tone and sentiment.",
            "Provide a brief analysis including:",
            "1. Overall sentiment (positive/negative/neutral)",
            "2. Tone (formal/informal/urgent/friendly)",
            "3. Key emotional indicators",
            f"\nEmail content:\n{email_content}"
        ]
        
        try:
            response = self.model.generate_content("\n".join(prompt))
            return {
                "analysis": response.text,
                "success": True
            }
        except Exception as e:
            return {
                "analysis": "Error analyzing sentiment",
                "success": False,
                "error": str(e)
            } 