from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QTabWidget, QMenuBar)
from .email_accounts_tab import EmailAccountsTab
from .email_analysis_tab import EmailAnalysisTab

class MainWindow(QMainWindow):
    """
    Main application window that contains all UI elements and manages
    the overall application layout.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Email Assistant")
        self.setMinimumSize(800, 600)
        
        # Create the central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Initialize UI components
        self.setup_menu_bar()
        self.setup_tabs()
    
    def setup_menu_bar(self):
        """Creates the application menu bar with basic options."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("Settings")
        file_menu.addSeparator()
        file_menu.addAction("Exit")
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction("About")
    
    def setup_tabs(self):
        """Creates the main tab widget with different sections of the application."""
        self.tab_widget = QTabWidget()
        
        # Add tabs for different functionalities
        self.email_accounts_tab = EmailAccountsTab()
        self.email_analysis_tab = EmailAnalysisTab()
        
        self.tab_widget.addTab(self.email_accounts_tab, "Email Accounts")
        self.tab_widget.addTab(self.email_analysis_tab, "Email Analysis")
        
        self.layout.addWidget(self.tab_widget) 