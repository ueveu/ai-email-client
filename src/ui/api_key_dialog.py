from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                            QLineEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

class ApiKeyDialog(QDialog):
    """
    Dialog for entering the Gemini API key.
    Shows information about where to get the key and validates input.
    """
    
    API_URL = "https://makersuite.google.com/app/apikey"
    
    @classmethod
    def show_instruction_dialog(cls, parent=None):
        """Show instructions about getting a Gemini API key."""
        msg = QMessageBox(parent)
        msg.setWindowTitle("Welcome to AI Email Assistant")
        msg.setIcon(QMessageBox.Icon.Information)
        
        # Set detailed instructions
        instructions = (
            "<h3>Welcome to AI Email Assistant!</h3>"
            "<p>To use the AI features of this application, you need a Google Gemini API key.</p>"
            "<p><b>How to get your API key:</b></p>"
            "<ol>"
            "<li>Visit the <a href='https://makersuite.google.com/app/apikey'>Google AI Studio</a></li>"
            "<li>Sign in with your Google account</li>"
            "<li>Click on 'Create API Key'</li>"
            "<li>Copy your new API key</li>"
            "</ol>"
            "<p>The API key will be stored securely on your system.</p>"
        )
        
        msg.setText(instructions)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        # Make the dialog wider
        msg.setMinimumWidth(400)
        
        return msg.exec()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gemini API Key Required")
        self.setModal(True)
        self.setup_ui()
        
        # Store the entered API key
        self.api_key = None
    
    def setup_ui(self):
        """Set up the dialog's user interface."""
        layout = QVBoxLayout(self)
        
        # Add explanation text
        info_text = (
            "To use the AI Email Assistant, you need a Google Gemini API key. "
            "This key is used to generate AI-powered email replies."
        )
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Add link to get API key
        link_text = (
            'You can get your API key from the '
            '<a href="https://makersuite.google.com/app/apikey">Google AI Studio</a>.'
        )
        link_label = QLabel(link_text)
        link_label.setOpenExternalLinks(True)
        link_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(link_label)
        
        # Add API key input
        layout.addSpacing(10)
        layout.addWidget(QLabel("Enter your API key:"))
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Paste your API key here")
        layout.addWidget(self.key_input)
        
        # Add show/hide password checkbox
        show_button = QPushButton("Show")
        show_button.setCheckable(True)
        show_button.toggled.connect(self.toggle_key_visibility)
        layout.addWidget(show_button)
        
        # Add buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.validate_and_accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Set minimum size
        self.setMinimumWidth(400)
    
    def toggle_key_visibility(self, checked):
        """Toggle the visibility of the API key."""
        self.key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self.sender().setText("Hide" if checked else "Show")
    
    def validate_and_accept(self):
        """Validate the API key before accepting."""
        key = self.key_input.text().strip()
        
        if not key:
            QMessageBox.warning(
                self,
                "Validation Error",
                "Please enter your API key."
            )
            return
        
        # Basic format validation (Gemini API keys are typically long strings)
        if len(key) < 20:
            QMessageBox.warning(
                self,
                "Validation Error",
                "The API key appears to be invalid. Please check and try again."
            )
            return
        
        self.api_key = key
        self.accept()
    
    @classmethod
    def get_api_key(cls, parent=None) -> str:
        """
        Show the dialog and return the entered API key.
        
        Returns:
            str: The entered API key or None if cancelled
        """
        dialog = cls(parent)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            return dialog.api_key
        return None 