"""
Dialog for customizing AI-generated email replies.
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QPushButton, QComboBox, QTextEdit, QDialogButtonBox)
from PyQt6.QtCore import Qt
from utils.logger import logger

class ReplyCustomizationDialog(QDialog):
    """Dialog for customizing and adjusting AI-generated replies."""
    
    def __init__(self, reply_text: str, ai_service, parent=None):
        """
        Initialize the customization dialog.
        
        Args:
            reply_text (str): The initial reply text to customize
            ai_service: The AI service instance for tone adjustment
            parent (QWidget): Parent widget
        """
        super().__init__(parent)
        self.reply_text = reply_text
        self.ai_service = ai_service
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the UI components."""
        self.setWindowTitle("Customize Reply")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # Tone adjustment controls
        tone_layout = QHBoxLayout()
        
        tone_label = QLabel("Adjust Tone:")
        self.tone_combo = QComboBox()
        self.tone_combo.addItems([
            "More formal", "More casual", "More direct",
            "More diplomatic", "More empathetic", "More professional"
        ])
        
        apply_tone_btn = QPushButton("Apply Tone")
        apply_tone_btn.clicked.connect(self.adjust_tone)
        
        tone_layout.addWidget(tone_label)
        tone_layout.addWidget(self.tone_combo)
        tone_layout.addWidget(apply_tone_btn)
        tone_layout.addStretch()
        
        layout.addLayout(tone_layout)
        
        # Reply text editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.reply_text)
        layout.addWidget(self.text_edit)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def adjust_tone(self):
        """Adjust the tone of the current reply text."""
        try:
            current_text = self.text_edit.toPlainText()
            desired_tone = self.tone_combo.currentText()
            
            adjusted_text = self.ai_service.adjust_reply_tone(
                current_text,
                desired_tone
            )
            
            self.text_edit.setPlainText(adjusted_text)
            
        except Exception as e:
            logger.error(f"Error adjusting reply tone: {str(e)}")
    
    def get_customized_text(self) -> str:
        """Get the customized reply text."""
        return self.text_edit.toPlainText() 