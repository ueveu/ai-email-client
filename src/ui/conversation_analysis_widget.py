"""
Widget for displaying conversation analysis insights with visualizations.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                           QLabel, QScrollArea, QFrame, QPushButton,
                           QTreeWidget, QTreeWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from datetime import datetime
from typing import Dict, List
from utils.logger import logger

class ConversationAnalysisWidget(QWidget):
    """Widget for displaying conversation analysis insights with visualizations."""
    
    # Signal emitted when user clicks on a data point
    data_point_clicked = pyqtSignal(dict)  # Emits data about the clicked point
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.analysis_data = {}
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI components."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Overview tab
        overview_tab = QWidget()
        overview_layout = QVBoxLayout(overview_tab)
        
        # Key metrics
        metrics_frame = QFrame()
        metrics_frame.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        metrics_layout = QHBoxLayout(metrics_frame)
        
        self.participant_count_label = QLabel("Participants: 0")
        self.thread_length_label = QLabel("Messages: 0")
        self.time_span_label = QLabel("Duration: N/A")
        self.overall_tone_label = QLabel("Tone: Neutral")
        
        metrics_layout.addWidget(self.participant_count_label)
        metrics_layout.addWidget(self.thread_length_label)
        metrics_layout.addWidget(self.time_span_label)
        metrics_layout.addWidget(self.overall_tone_label)
        
        overview_layout.addWidget(metrics_frame)
        
        # Key points
        self.key_points_tree = QTreeWidget()
        self.key_points_tree.setHeaderLabels(["Key Discussion Points"])
        overview_layout.addWidget(self.key_points_tree)
        
        self.tab_widget.addTab(overview_tab, "Overview")
        
        layout.addWidget(self.tab_widget)
    
    def update_analysis(self, analysis_data: Dict):
        """
        Update the widget with new analysis data.
        
        Args:
            analysis_data: Dictionary containing analysis results
        """
        try:
            self.analysis_data = analysis_data
            
            # Update overview metrics
            self.participant_count_label.setText(f"Participants: {analysis_data.get('participant_count', 0)}")
            self.thread_length_label.setText(f"Messages: {analysis_data.get('thread_length', 0)}")
            
            time_span = analysis_data.get('time_span', {})
            if time_span.get('duration'):
                duration_str = self._format_duration(time_span['duration'])
                self.time_span_label.setText(f"Duration: {duration_str}")
            
            sentiment = analysis_data.get('sentiment_analysis', {})
            if sentiment:
                self.overall_tone_label.setText(f"Tone: {sentiment.get('overall_tone', 'Neutral')}")
            
            # Update key points
            self.key_points_tree.clear()
            for point in analysis_data.get('key_points', []):
                QTreeWidgetItem(self.key_points_tree, [point])
            
        except Exception as e:
            logger.error(f"Error updating analysis visualization: {str(e)}")
    
    def _format_duration(self, duration) -> str:
        """
        Format timedelta into readable string.
        
        Args:
            duration: timedelta object
            
        Returns:
            Formatted duration string
        """
        try:
            total_seconds = int(duration.total_seconds())
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            
            parts = []
            if days > 0:
                parts.append(f"{days}d")
            if hours > 0:
                parts.append(f"{hours}h")
            if minutes > 0:
                parts.append(f"{minutes}m")
            
            return " ".join(parts) if parts else "< 1m"
            
        except Exception as e:
            logger.error(f"Error formatting duration: {str(e)}")
            return "N/A" 