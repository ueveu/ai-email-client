from abc import ABC, abstractmethod
from typing import List, Optional
import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                           QPushButton, QComboBox, QWidget, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
import webbrowser
import logging
import time

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

class AIProviderSetting(ABC):
    """Base class for AI provider settings."""
    
    def __init__(self, name: str, display_name: str = None, default_value: str = None, description: str = None):
        self.name = name
        self.display_name = display_name if display_name else name
        self.default_value = default_value if default_value else ""
        self.description = description if description else ""
        
    @abstractmethod
    def render_to_layout(self, layout: QVBoxLayout):
        pass
        
    @abstractmethod
    def set_value(self, value):
        pass
        
    @abstractmethod
    def get_value(self):
        pass

class TextSetting(AIProviderSetting):
    """Text input setting for AI providers."""
    
    def __init__(self, name: str, display_name: str = None, default_value: str = None, 
                 description: str = None, is_password: bool = False, validator=None):
        super().__init__(name, display_name, default_value, description)
        self.internal_value = default_value
        self.input = None
        self.is_password = is_password
        self.validator = validator
        self.progress_bar = None
        
    def render_to_layout(self, layout: QVBoxLayout):
        """Render the setting UI."""
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Input row
        row_layout = QHBoxLayout()
        label = QLabel(self.display_name)
        label.setStyleSheet("font-size: 12px;")
        row_layout.addWidget(label)
        
        self.input = QLineEdit(self.internal_value)
        if self.is_password:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        self.input.setStyleSheet("""
            font-size: 12px;
            padding: 5px;
        """)
        self.input.setPlaceholderText(self.description)
        
        row_layout.addWidget(self.input)
        
        if self.is_password:
            show_button = QPushButton("Show")
            show_button.setCheckable(True)
            show_button.toggled.connect(self._toggle_password_visibility)
            show_button.setStyleSheet("""
                QPushButton {
                    background-color: #f8f9fa;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #e9ecef;
                }
            """)
            row_layout.addWidget(show_button)
        
        container_layout.addLayout(row_layout)
        
        # Add progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 4px;
                text-align: center;
                margin-top: 4px;
            }
            QProgressBar::chunk {
                background-color: #4285f4;
                border-radius: 3px;
            }
        """)
        self.progress_bar.hide()
        container_layout.addWidget(self.progress_bar)
        
        layout.addWidget(container)
        
    def _toggle_password_visibility(self, checked):
        """Toggle password visibility."""
        self.input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.sender().setText("Hide" if checked else "Show")
        
    def set_value(self, value):
        """Set the setting value."""
        self.internal_value = value
        if self.input:
            self.input.setText(value)
            
    def get_value(self):
        """Get the setting value."""
        return self.input.text() if self.input else self.internal_value
    
    def show_progress(self, show: bool = True, text: str = None):
        """Show or hide the progress bar."""
        if self.progress_bar:
            if show:
                self.progress_bar.setFormat(text if text else "%p%")
                self.progress_bar.setValue(0)
                self.progress_bar.show()
            else:
                self.progress_bar.hide()
    
    def update_progress(self, value: int, text: str = None):
        """Update progress bar value."""
        if self.progress_bar and self.progress_bar.isVisible():
            self.progress_bar.setValue(value)
            if text:
                self.progress_bar.setFormat(text)

class DropdownSetting(AIProviderSetting):
    """Dropdown selection setting for AI providers."""
    
    def __init__(self, name: str, display_name: str = None, default_value: str = None, 
                 description: str = None, options: list = None):
        super().__init__(name, display_name, default_value, description)
        self.options = options if options else []
        self.internal_value = default_value
        self.dropdown = None
        
    def render_to_layout(self, layout: QVBoxLayout):
        row_layout = QHBoxLayout()
        label = QLabel(self.display_name)
        label.setStyleSheet("font-size: 12px;")
        row_layout.addWidget(label)
        
        self.dropdown = QComboBox()
        self.dropdown.setStyleSheet("""
            font-size: 12px;
            padding: 5px;
        """)
        
        for option, value in self.options:
            self.dropdown.addItem(option, value)
            
        # Set current value
        index = self.dropdown.findData(self.internal_value)
        if index != -1:
            self.dropdown.setCurrentIndex(index)
            
        row_layout.addWidget(self.dropdown)
        layout.addLayout(row_layout)
        
    def set_value(self, value):
        self.internal_value = value
        if self.dropdown:
            index = self.dropdown.findData(value)
            if index != -1:
                self.dropdown.setCurrentIndex(index)
                
    def get_value(self):
        return self.dropdown.currentData() if self.dropdown else self.internal_value

class AIProvider(ABC):
    """Base class for AI providers."""
    
    def __init__(self, app, provider_name: str, settings: List[AIProviderSetting], 
                 description: str = None, logo: str = "generic", 
                 button_text: str = "Go to URL", button_action: callable = None):
        self.provider_name = provider_name
        self.settings = settings
        self.app = app
        self.description = description if description else "An unfinished AI provider!"
        self.logo = logo
        self.button_text = button_text
        self.button_action = button_action
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        
    @abstractmethod
    def get_response(self, system_instruction: str, prompt: str) -> str:
        """Get response from the AI provider."""
        pass
        
    def load_config(self, config: dict):
        """Load configuration into provider's memory."""
        for setting in self.settings:
            if setting.name in config:
                setattr(self, setting.name, config[setting.name])
                setting.set_value(config[setting.name])
            else:
                setattr(self, setting.name, setting.default_value)
        self.after_load()
        
    def save_config(self):
        """Save provider's memory to config."""
        config = {}
        for setting in self.settings:
            config[setting.name] = setting.get_value()
            
        self.app.config["providers"][self.provider_name] = config
        self.app.save_config()
        
    @abstractmethod
    def after_load(self):
        """Called after settings are loaded."""
        pass
        
    @abstractmethod
    def before_load(self):
        """Called before settings are loaded."""
        pass
        
    @abstractmethod
    def cancel(self):
        """Cancel current request."""
        pass
    
    def validate_settings(self) -> Optional[str]:
        """
        Validate all settings.
        
        Returns:
            str: Error message if validation fails, None if successful
        """
        return None

class GeminiProvider(AIProvider):
    """Gemini AI provider implementation."""
    
    def __init__(self, app):
        """Initialize the Gemini provider."""
        self.close_requested = False
        self.model = None
        
        settings = [
            TextSetting(
                name="api_key",
                display_name="API Key",
                description="Paste your Gemini API key here",
                is_password=True,
                validator=self._validate_api_key
            ),
            DropdownSetting(
                name="model_name",
                display_name="Model",
                default_value="gemini-1.5-flash-latest",
                description="Select Gemini model to use",
                options=[
                    ("Gemini 1.5 Flash 8B (fast)", "gemini-1.5-flash-8b-latest"),
                    ("Gemini 1.5 Flash (fast & more intelligent, recommended)", "gemini-1.5-flash-latest"),
                    ("Gemini 1.5 Pro (very intelligent, but slower & lower rate limit)", "gemini-1.5-pro-latest")
                ]
            )
        ]
        
        super().__init__(
            app=app,
            provider_name="Gemini 1.5 Flash (Recommended)",
            settings=settings,
            description=(
                "• Gemini 1.5 Flash is a powerful AI model that has a free tier available.\n"
                "• Writing Tools needs an \"API key\" to connect to Gemini on your behalf.\n"
                "• Simply click Get API Key button below, copy your API key, and paste it below.\n"
                "• Note: With the free tier of the Gemini API, Google may anonymize & store "
                "the text that you send for Gemini's improvement."
            ),
            logo="gemini",
            button_text="Get API Key",
            button_action=lambda: webbrowser.open("https://makersuite.google.com/app/apikey")
        )
    
    def _validate_api_key(self, api_key: str) -> Optional[str]:
        """
        Validate the API key by making a test request.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            str: Error message if validation fails, None if successful
        """
        if not api_key:
            return "API key is required"
            
        if len(api_key) < 20:
            return "API key appears to be too short"
            
        # Show progress during validation
        api_key_setting = next(s for s in self.settings if s.name == "api_key")
        api_key_setting.show_progress(True, "Validating API key...")
        
        try:
            # Configure Gemini with the new key
            genai.configure(api_key=api_key)
            
            # Try to create model
            api_key_setting.update_progress(33, "Creating model...")
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash-latest",
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=1000,
                    temperature=0.5
                )
            )
            
            # Try a test request
            api_key_setting.update_progress(66, "Testing connection...")
            response = model.generate_content("Test")
            if not response or not response.text:
                raise ValidationError("API test failed - no response")
                
            api_key_setting.update_progress(100, "Validation successful!")
            QTimer.singleShot(1000, lambda: api_key_setting.show_progress(False))
            return None
            
        except Exception as e:
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg:
                return "Invalid API key. Please check and try again."
            elif "PERMISSION_DENIED" in error_msg:
                return "API key doesn't have permission to access the model."
            elif "QUOTA_EXCEEDED" in error_msg:
                return "API quota exceeded. Please try again later."
            else:
                return f"Error validating API key: {error_msg}"
        finally:
            QTimer.singleShot(1000, lambda: api_key_setting.show_progress(False))
    
    def validate_settings(self) -> Optional[str]:
        """Validate all provider settings."""
        # Validate API key
        api_key = next(s for s in self.settings if s.name == "api_key").get_value()
        return self._validate_api_key(api_key)
    
    def get_response(self, system_instruction: str, prompt: str) -> str:
        """Get response from Gemini model with retry logic."""
        self.close_requested = False
        retries = 0
        
        while retries < self.max_retries and not self.close_requested:
            try:
                response = self.model.generate_content(
                    contents=[system_instruction, prompt],
                    generation_config=genai.types.GenerationConfig(
                        candidate_count=1,
                        max_output_tokens=1000,
                        temperature=0.5
                    ),
                    safety_settings={
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                    }
                )
                
                if response.prompt_feedback.block_reason:
                    logging.warning('Response was blocked due to safety settings')
                    return "The generated content was blocked due to safety settings."
                
                return response.text
                
            except Exception as e:
                retries += 1
                if retries < self.max_retries and not self.close_requested:
                    logging.warning(f"Retry {retries}/{self.max_retries} after error: {str(e)}")
                    time.sleep(self.retry_delay)
                else:
                    logging.error(f"Error generating response after {retries} retries: {str(e)}")
                    return f"Error generating response: {str(e)}"
    
    def after_load(self):
        """Initialize Gemini model after loading settings."""
        try:
            # Validate API key first
            error = self.validate_settings()
            if error:
                logging.error(f"Error validating settings: {error}")
                self.model = None
                return
                
            # Initialize model
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=1000,
                    temperature=0.5
                ),
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            
        except Exception as e:
            logging.error(f"Error initializing Gemini model: {str(e)}")
            self.model = None
    
    def before_load(self):
        """Clean up before loading new settings."""
        self.model = None
    
    def cancel(self):
        """Cancel current request."""
        self.close_requested = True 