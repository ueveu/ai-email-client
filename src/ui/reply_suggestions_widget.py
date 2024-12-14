"""
Widget for displaying and managing AI-generated email reply suggestions.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QComboBox, QTextEdit, QFrame,
                           QScrollArea, QSizePolicy, QMessageBox)
from PyQt6.QtCore import pyqtSignal, Qt
from services.ai_service import AIService
from utils.logger import logger

class ReplySuggestionWidget(QWidget):
    """Widget that displays AI-generated reply suggestions with customization options."""
    
    reply_selected = pyqtSignal(str)  # Emitted when a reply is selected
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ai_service = AIService()
        self.current_suggestions = []
        self.current_email_context = None  # Store current email context
        self.setup_ui()
        
        # Initialize stats
        self.update_learning_stats()
    
    def setup_ui(self):
        """Set up the UI components."""
        main_layout = QVBoxLayout(self)
        
        # Stats section
        self.stats_label = QLabel()
        self.stats_label.setWordWrap(True)
        main_layout.addWidget(self.stats_label)
        
        # Controls section
        controls_layout = QHBoxLayout()
        
        # Tone selection
        tone_label = QLabel("Tone:")
        self.tone_combo = QComboBox()
        self.tone_combo.addItems([
            "Professional", "Friendly", "Formal", "Casual",
            "Diplomatic", "Direct", "Empathetic"
        ])
        self.tone_combo.currentTextChanged.connect(self.on_tone_changed)
        
        controls_layout.addWidget(tone_label)
        controls_layout.addWidget(self.tone_combo)
        controls_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("↻ Refresh Suggestions")
        refresh_btn.clicked.connect(self.refresh_suggestions)
        controls_layout.addWidget(refresh_btn)
        
        main_layout.addLayout(controls_layout)
        
        # Suggestions scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.suggestions_container = QWidget()
        self.suggestions_layout = QVBoxLayout(self.suggestions_container)
        scroll_area.setWidget(self.suggestions_container)
        
        main_layout.addWidget(scroll_area)
    
    def update_learning_stats(self):
        """Update the displayed learning statistics."""
        try:
            stats = self.ai_service.get_learning_stats()
            
            stats_text = f"Learning Stats: {stats['total_replies']} replies analyzed\n"
            
            if stats['common_tones']:
                stats_text += "Common tones: "
                tone_items = [f"{tone}({count})" 
                            for tone, count in stats['common_tones'].items()]
                stats_text += ", ".join(tone_items)
            
            self.stats_label.setText(stats_text)
            
        except Exception as e:
            logger.error(f"Error updating learning stats: {str(e)}")
            self.stats_label.setText("Learning stats unavailable")
    
    def set_email_context(self, email_content: str, subject: str, context: dict):
        """
        Set the current email context for generating replies.
        
        Args:
            email_content (str): The content of the email to reply to
            subject (str): The subject of the email
            context (dict): Additional context about the email
        """
        self.current_email_content = email_content
        self.current_subject = subject
        self.current_email_context = context
        
        # Try to set appropriate tone based on context
        try:
            analysis = self.ai_service.analyze_email_content(email_content, subject)
            if 'context_type' in analysis:
                preferred_tone = self.ai_service.learning_service.get_preferred_tone(
                    analysis['context_type']
                )
                if preferred_tone:
                    index = self.tone_combo.findText(preferred_tone)
                    if index >= 0:
                        self.tone_combo.setCurrentIndex(index)
        except Exception as e:
            logger.error(f"Error setting email context: {str(e)}")
    
    def on_reply_selected(self, suggestion: dict):
        """
        Handle reply selection and learn from it.
        
        Args:
            suggestion (dict): The selected suggestion data
        """
        try:
            # Learn from selection
            if self.current_email_context:
                context = {
                    **self.current_email_context,
                    'tone': suggestion.get('tone'),
                    'style': suggestion.get('style')
                }
                self.ai_service.learn_from_selection(
                    suggestion['reply_text'],
                    context
                )
            
            # Update stats
            self.update_learning_stats()
            
            # Emit selected text
            self.reply_selected.emit(suggestion['reply_text'])
            
        except Exception as e:
            logger.error(f"Error handling reply selection: {str(e)}")
            QMessageBox.warning(
                self,
                "Learning Error",
                "Failed to learn from selection, but reply was copied."
            )
    
    def display_suggestions(self, suggestions):
        """
        Display the provided reply suggestions.
        
        Args:
            suggestions (List[Dict]): List of reply suggestions to display
        """
        self.clear_suggestions()
        self.current_suggestions = suggestions
        
        for i, suggestion in enumerate(suggestions):
            suggestion_frame = QFrame()
            suggestion_frame.setFrameStyle(QFrame.Shape.StyledPanel)
            suggestion_frame.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Maximum
            )
            
            frame_layout = QVBoxLayout(suggestion_frame)
            
            # Style and tone info
            info_layout = QHBoxLayout()
            style_label = QLabel(f"Style: {suggestion['style']}")
            tone_label = QLabel(f"Tone: {suggestion['tone']}")
            
            info_layout.addWidget(style_label)
            info_layout.addWidget(tone_label)
            info_layout.addStretch()
            
            # Reply text
            text_edit = QTextEdit()
            text_edit.setPlainText(suggestion['reply_text'])
            text_edit.setReadOnly(True)
            text_edit.setMaximumHeight(150)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            select_btn = QPushButton("Use This Reply")
            select_btn.clicked.connect(
                lambda checked, s=suggestion: 
                self.on_reply_selected(s)
            )
            
            customize_btn = QPushButton("Customize")
            customize_btn.clicked.connect(
                lambda checked, text=suggestion['reply_text']:
                self.customize_reply(text)
            )
            
            button_layout.addWidget(customize_btn)
            button_layout.addWidget(select_btn)
            button_layout.addStretch()
            
            # Add all components to frame
            frame_layout.addLayout(info_layout)
            frame_layout.addWidget(text_edit)
            frame_layout.addLayout(button_layout)
            
            self.suggestions_layout.addWidget(suggestion_frame)
        
        # Add stretch at the end
        self.suggestions_layout.addStretch()
    
    def customize_reply(self, reply_text: str):
        """
        Open a dialog to customize the selected reply.
        
        Args:
            reply_text (str): The reply text to customize
        """
        from .reply_customization_dialog import ReplyCustomizationDialog
        dialog = ReplyCustomizationDialog(reply_text, self.ai_service, self)
        if dialog.exec():
            customized_text = dialog.get_customized_text()
            
            # Learn from customization
            if self.current_email_context:
                context = {
                    **self.current_email_context,
                    'tone': self.tone_combo.currentText(),
                    'customized': True
                }
                self.ai_service.learn_from_selection(
                    customized_text,
                    context
                )
            
            self.update_learning_stats()
            self.reply_selected.emit(customized_text)
    
    def clear_suggestions(self):
        """Clear all current suggestions from the display."""
        while self.suggestions_layout.count():
            child = self.suggestions_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def generate_suggestions(self, email_content: str, subject: str, context=None):
        """
        Generate and display new reply suggestions.
        
        Args:
            email_content (str): Content of the email to reply to
            subject (str): Subject of the email
            context (List[Dict], optional): Previous conversation context
        """
        try:
            tone = self.tone_combo.currentText()
            suggestions = self.ai_service.generate_reply_suggestions(
                email_content=email_content,
                subject=subject,
                context=context,
                tone=tone
            )
            self.display_suggestions(suggestions)
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            self.display_error(str(e))
    
    def on_tone_changed(self, new_tone: str):
        """
        Handle tone selection changes.
        
        Args:
            new_tone (str): The newly selected tone
        """
        # If we have current suggestions, adjust their tone
        if self.current_suggestions:
            try:
                adjusted_suggestions = []
                for suggestion in self.current_suggestions:
                    adjusted_text = self.ai_service.adjust_reply_tone(
                        suggestion['reply_text'],
                        new_tone
                    )
                    adjusted_suggestions.append({
                        'reply_text': adjusted_text,
                        'style': suggestion['style'],
                        'tone': new_tone
                    })
                self.display_suggestions(adjusted_suggestions)
                
            except Exception as e:
                logger.error(f"Error adjusting tone: {str(e)}")
    
    def refresh_suggestions(self):
        """Refresh the current suggestions with the selected tone."""
        if hasattr(self, 'current_email_content') and hasattr(self, 'current_subject'):
            self.generate_suggestions(
                self.current_email_content,
                self.current_subject,
                getattr(self, 'current_context', None)
            )
    
    def display_error(self, error_message: str):
        """
        Display an error message in the suggestions area.
        
        Args:
            error_message (str): The error message to display
        """
        self.clear_suggestions()
        
        error_frame = QFrame()
        error_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        
        error_layout = QVBoxLayout(error_frame)
        error_label = QLabel(f"⚠️ Error: {error_message}")
        error_label.setWordWrap(True)
        error_layout.addWidget(error_label)
        
        self.suggestions_layout.addWidget(error_frame)
        self.suggestions_layout.addStretch() 