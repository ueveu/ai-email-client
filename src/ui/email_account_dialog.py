from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QLineEdit, QSpinBox, QCheckBox, QPushButton,
                           QFormLayout, QMessageBox, QCompleter, QListWidget,
                           QInputDialog)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from config import Config
import google.generativeai as genai
import os

class SmartLineEdit(QLineEdit):
    """LineEdit with AI-powered suggestions."""
    
    def __init__(self, parent=None, suggestion_type=""):
        super().__init__(parent)
        self.suggestion_type = suggestion_type
        self.suggestion_list = QListWidget(parent)
        self.suggestion_list.setWindowFlags(Qt.WindowType.Popup)
        self.suggestion_list.setFocusProxy(self)
        self.suggestion_list.installEventFilter(self)
        self.suggestion_list.itemClicked.connect(self._on_item_clicked)
        
        # Setup suggestion timer to avoid too many API calls
        self.suggestion_timer = QTimer()
        self.suggestion_timer.setSingleShot(True)
        self.suggestion_timer.timeout.connect(self.get_suggestions)
        
        self.textChanged.connect(self.on_text_changed)
        
        # Initialize Gemini API
        self._init_gemini()
    
    def _init_gemini(self):
        """Initialize Gemini API with the correct API key."""
        try:
            # First try environment variable
            api_key = os.getenv("GEMINI_API_KEY")
            
            # If not in environment, try config
            if not api_key:
                config = Config()
                api_key = config.get_api_key("gemini")
            
            if api_key:
                genai.configure(api_key=api_key)
                try:
                    self.model = genai.GenerativeModel('gemini-pro')
                    # Test the API key with a simple prompt
                    response = self.model.generate_content("Test")
                    if not response:
                        print("Warning: Gemini API test failed - no response")
                        self.model = None
                except Exception as e:
                    print(f"Warning: Gemini API test failed: {str(e)}")
                    self.model = None
                    
                    # If the API key is invalid, clear it from config
                    if "API_KEY_INVALID" in str(e):
                        config = Config()
                        config.clear_api_key("gemini")
                        
                        # Show error message
                        QMessageBox.critical(
                            self.parent(),
                            "Invalid API Key",
                            "The Gemini API key appears to be invalid.\n\n"
                            "Please check your API key and enter it again."
                        )
            else:
                print("Warning: No Gemini API key found")
                self.model = None
                
                # Show dialog to get API key
                key, ok = QInputDialog.getText(
                    self.parent(),
                    "Gemini API Key Required",
                    "Please enter your Gemini API key:\n\n"
                    "You can get your API key from:\n"
                    "https://makersuite.google.com/app/apikey",
                    QLineEdit.EchoMode.Password
                )
                if ok and key:
                    config = Config()
                    config.set_api_key(key, "gemini")
                    # Try initializing again
                    self._init_gemini()
        except Exception as e:
            print(f"Error initializing Gemini API: {str(e)}")
            self.model = None
    
    def on_text_changed(self, text):
        """Handle text changes and trigger suggestions."""
        if len(text) > 2 and self.model:  # Only suggest after 3 characters and if model is available
            self.suggestion_timer.start(500)  # Wait 500ms before making API call
    
    def get_suggestions(self):
        """Get suggestions from Gemini API."""
        if not self.model:
            return
            
        text = self.text()
        if not text:
            self.suggestion_list.hide()
            return
        
        try:
            # Create prompt based on suggestion type
            if self.suggestion_type == "email":
                prompt = f"Suggest email server settings for the email address: {text}\n" \
                        f"Format: IMAP server, IMAP port, SMTP server, SMTP port\n" \
                        f"Only include common providers like Gmail, Outlook, Yahoo, etc."
            elif self.suggestion_type == "imap":
                prompt = f"What is the IMAP server and port for {text}?\n" \
                        f"Format: server:port"
            elif self.suggestion_type == "smtp":
                prompt = f"What is the SMTP server and port for {text}?\n" \
                        f"Format: server:port"
            else:
                return
            
            response = self.model.generate_content(prompt)
            suggestions = self._parse_suggestions(response.text, self.suggestion_type)
            
            if suggestions:
                self.show_suggestions(suggestions)
        except Exception as e:
            print(f"Error getting suggestions: {str(e)}")
            self.suggestion_list.hide()
    
    def _parse_suggestions(self, response_text: str, suggestion_type: str) -> list:
        """Parse the AI response into a list of suggestions."""
        suggestions = []
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if suggestion_type == "email":
                # Parse email provider settings
                if ":" in line or "," in line:
                    parts = line.replace(":", ",").split(",")
                    if len(parts) >= 4:
                        suggestions.append({
                            "display": f"{parts[0].strip()} ({parts[1].strip()})",
                            "imap_server": parts[0].strip(),
                            "imap_port": parts[1].strip(),
                            "smtp_server": parts[2].strip(),
                            "smtp_port": parts[3].strip()
                        })
            else:
                # Parse server:port format
                if ":" in line:
                    server, port = line.split(":", 1)
                    suggestions.append({
                        "display": line.strip(),
                        "server": server.strip(),
                        "port": port.strip()
                    })
        
        return suggestions
    
    def show_suggestions(self, suggestions):
        """Show the suggestion list."""
        self.suggestion_list.clear()
        
        for suggestion in suggestions:
            self.suggestion_list.addItem(suggestion["display"])
            # Store the full suggestion data
            self.suggestion_list.item(self.suggestion_list.count() - 1).setData(
                Qt.ItemDataRole.UserRole,
                suggestion
            )
        
        if self.suggestion_list.count() > 0:
            # Position the suggestion list below the line edit
            pos = self.mapToGlobal(self.rect().bottomLeft())
            self.suggestion_list.move(pos)
            self.suggestion_list.setFixedWidth(max(self.width(), 300))
            self.suggestion_list.show()
        else:
            self.suggestion_list.hide()
    
    @pyqtSlot(QListWidget)
    def complete_suggestion(self, item):
        """Complete the selected suggestion."""
        suggestion = item.data(Qt.ItemDataRole.UserRole)
        
        if self.suggestion_type == "email":
            # Emit signal to update all fields
            self.parent().apply_email_suggestion(suggestion)
        else:
            # Update just this field
            if "server" in suggestion:
                self.setText(suggestion["server"])
                # Update port if available
                if "port" in suggestion:
                    port_input = self.parent().findChild(QSpinBox, f"{self.suggestion_type}_port")
                    if port_input:
                        try:
                            port_input.setValue(int(suggestion["port"]))
                        except ValueError:
                            pass
        
        self.suggestion_list.hide()
    
    def _on_item_clicked(self, item):
        """Handle item click in suggestion list."""
        self.complete_suggestion(item)

class EmailAccountDialog(QDialog):
    """Dialog for adding or editing email account settings."""
    
    def __init__(self, parent=None, account_data=None):
        """
        Initialize the dialog.
        
        Args:
            parent: Parent widget
            account_data (dict): Existing account data for editing
        """
        super().__init__(parent)
        self.account_data = account_data or {}
        self.setWindowTitle("Email Account Settings")
        self.setModal(True)
        self.setup_ui()
        
        if account_data:
            self.load_account_data()
    
    def setup_ui(self):
        """Set up the dialog's user interface."""
        layout = QVBoxLayout(self)
        
        # Create form layout for input fields
        form = QFormLayout()
        
        # Email account details with AI suggestions
        self.email_input = SmartLineEdit(self, "email")
        self.email_input.setPlaceholderText("your.email@example.com")
        form.addRow("Email Address:", self.email_input)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Your Name")
        form.addRow("Display Name:", self.name_input)
        
        # Password field
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self.password_input)
        
        # Show password checkbox
        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(self.toggle_password_visibility)
        form.addRow("", self.show_password)
        
        # IMAP settings with AI suggestions
        form.addRow(QLabel("\nIMAP Settings"))
        
        self.imap_server = SmartLineEdit(self, "imap")
        self.imap_server.setObjectName("imap_server")
        self.imap_server.setPlaceholderText("imap.example.com")
        form.addRow("IMAP Server:", self.imap_server)
        
        self.imap_port = QSpinBox()
        self.imap_port.setObjectName("imap_port")
        self.imap_port.setRange(1, 65535)
        self.imap_port.setValue(993)
        form.addRow("IMAP Port:", self.imap_port)
        
        self.imap_ssl = QCheckBox("Use SSL/TLS")
        self.imap_ssl.setChecked(True)
        form.addRow("", self.imap_ssl)
        
        # SMTP settings with AI suggestions
        form.addRow(QLabel("\nSMTP Settings"))
        
        self.smtp_server = SmartLineEdit(self, "smtp")
        self.smtp_server.setObjectName("smtp_server")
        self.smtp_server.setPlaceholderText("smtp.example.com")
        form.addRow("SMTP Server:", self.smtp_server)
        
        self.smtp_port = QSpinBox()
        self.smtp_port.setObjectName("smtp_port")
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        form.addRow("SMTP Port:", self.smtp_port)
        
        self.smtp_ssl = QCheckBox("Use SSL/TLS")
        self.smtp_ssl.setChecked(True)
        form.addRow("", self.smtp_ssl)
        
        # Add form to main layout
        layout.addLayout(form)
        
        # Add preset buttons for common email providers
        preset_layout = QHBoxLayout()
        gmail_btn = QPushButton("Gmail")
        outlook_btn = QPushButton("Outlook")
        yahoo_btn = QPushButton("Yahoo")
        
        gmail_btn.clicked.connect(lambda: self.load_preset("gmail"))
        outlook_btn.clicked.connect(lambda: self.load_preset("outlook"))
        yahoo_btn.clicked.connect(lambda: self.load_preset("yahoo"))
        
        preset_layout.addWidget(gmail_btn)
        preset_layout.addWidget(outlook_btn)
        preset_layout.addWidget(yahoo_btn)
        
        layout.addLayout(preset_layout)
        
        # Add buttons
        button_box = QHBoxLayout()
        save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        
        save_button.clicked.connect(self.validate_and_accept)
        cancel_button.clicked.connect(self.reject)
        
        button_box.addWidget(save_button)
        button_box.addWidget(cancel_button)
        
        layout.addLayout(button_box)
        
        # Set minimum width
        self.setMinimumWidth(400)
    
    def toggle_password_visibility(self, show):
        """Toggle password field visibility."""
        self.password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password
        )
    
    def load_preset(self, provider):
        """Load preset settings for common email providers."""
        presets = {
            "gmail": {
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "imap_ssl": True,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_ssl": True
            },
            "outlook": {
                "imap_server": "outlook.office365.com",
                "imap_port": 993,
                "imap_ssl": True,
                "smtp_server": "smtp.office365.com",
                "smtp_port": 587,
                "smtp_ssl": True
            },
            "yahoo": {
                "imap_server": "imap.mail.yahoo.com",
                "imap_port": 993,
                "imap_ssl": True,
                "smtp_server": "smtp.mail.yahoo.com",
                "smtp_port": 587,
                "smtp_ssl": True
            }
        }
        
        if provider in presets:
            preset = presets[provider]
            self.imap_server.setText(preset["imap_server"])
            self.imap_port.setValue(preset["imap_port"])
            self.imap_ssl.setChecked(preset["imap_ssl"])
            self.smtp_server.setText(preset["smtp_server"])
            self.smtp_port.setValue(preset["smtp_port"])
            self.smtp_ssl.setChecked(preset["smtp_ssl"])
    
    def load_account_data(self):
        """Load existing account data into the form."""
        self.email_input.setText(self.account_data.get("email", ""))
        self.name_input.setText(self.account_data.get("name", ""))
        self.imap_server.setText(self.account_data.get("imap_server", ""))
        self.imap_port.setValue(self.account_data.get("imap_port", 993))
        self.imap_ssl.setChecked(self.account_data.get("imap_ssl", True))
        self.smtp_server.setText(self.account_data.get("smtp_server", ""))
        self.smtp_port.setValue(self.account_data.get("smtp_port", 587))
        self.smtp_ssl.setChecked(self.account_data.get("smtp_ssl", True))
        
        # Don't load password - require user to enter it again for security
    
    def validate_and_accept(self):
        """Validate form data before accepting."""
        # Check required fields
        if not self.email_input.text():
            QMessageBox.warning(self, "Validation Error", "Email address is required.")
            return
        
        if not self.imap_server.text():
            QMessageBox.warning(self, "Validation Error", "IMAP server is required.")
            return
        
        if not self.smtp_server.text():
            QMessageBox.warning(self, "Validation Error", "SMTP server is required.")
            return
        
        if not self.password_input.text():
            QMessageBox.warning(self, "Validation Error", "Password is required.")
            return
        
        self.accept()
    
    def get_account_data(self) -> dict:
        """
        Get the account data from the form.
        
        Returns:
            dict: Account configuration data
        """
        return {
            "email": self.email_input.text(),
            "name": self.name_input.text(),
            "password": self.password_input.text(),
            "imap_server": self.imap_server.text(),
            "imap_port": self.imap_port.value(),
            "imap_ssl": self.imap_ssl.isChecked(),
            "smtp_server": self.smtp_server.text(),
            "smtp_port": self.smtp_port.value(),
            "smtp_ssl": self.smtp_ssl.isChecked()
        }
    
    def apply_email_suggestion(self, suggestion):
        """Apply email provider settings from suggestion."""
        self.imap_server.setText(suggestion["imap_server"])
        try:
            self.imap_port.setValue(int(suggestion["imap_port"]))
        except ValueError:
            pass
        
        self.smtp_server.setText(suggestion["smtp_server"])
        try:
            self.smtp_port.setValue(int(suggestion["smtp_port"]))
        except ValueError:
            pass