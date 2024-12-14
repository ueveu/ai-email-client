"""
Loading spinner widget for indicating background operations.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRect, QSize
from PyQt6.QtGui import QPainter, QColor, QPen

class LoadingSpinner(QWidget):
    """Widget that shows an animated loading spinner."""
    
    def __init__(self, parent=None, center_on_parent=True):
        super().__init__(parent)
        
        # Widget configuration
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Spinner properties
        self.center_on_parent = center_on_parent
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.steps = 12
        self.delay = 80
        self.dots = []
        self.current_dot = 0
        self.size = 32
        self.width = 3
        self.color = QColor(61, 174, 233)  # Default blue color
        
        # Initialize dots
        for i in range(self.steps):
            self.dots.append(1.0 - (i / self.steps))
        
        # Set size
        self.setFixedSize(self.size + 2, self.size + 2)
        
        # Hide initially
        self.hide()
    
    def rotate(self):
        """Rotate the spinner by one step."""
        self.angle = (self.angle + 360 / self.steps) % 360
        self.update()
    
    def start(self):
        """Start the spinner animation."""
        self.angle = 0
        self.show()
        self.raise_()
        self.timer.start(self.delay)
        
        if self.center_on_parent and self.parentWidget():
            self._center_on_parent()
    
    def stop(self):
        """Stop the spinner animation."""
        self.timer.stop()
        self.hide()
    
    def set_color(self, color: QColor):
        """Set the spinner color."""
        self.color = color
        self.update()
    
    def set_size(self, size: int):
        """Set the spinner size."""
        self.size = size
        self.setFixedSize(size + 2, size + 2)
        self.update()
    
    def set_width(self, width: int):
        """Set the line width of the spinner."""
        self.width = width
        self.update()
    
    def _center_on_parent(self):
        """Center the spinner on its parent widget."""
        if self.parentWidget():
            parent_rect = self.parentWidget().rect()
            self.move(
                parent_rect.center() - self.rect().center()
            )
    
    def paintEvent(self, event):
        """Paint the spinner."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate center and radius
        width = self.width
        center = QRect(0, 0, self.size, self.size).center()
        radius = (self.size - width) / 2
        
        # Draw dots
        painter.translate(center.x(), center.y())
        painter.rotate(self.angle)
        
        for i in range(self.steps):
            # Set opacity for current dot
            color = QColor(self.color)
            color.setAlphaF(self.dots[i])
            
            pen = QPen(color)
            pen.setWidth(width)
            painter.setPen(pen)
            
            # Draw dot
            painter.drawLine(0, radius, 0, radius - width)
            painter.rotate(360 / self.steps)
    
    def showEvent(self, event):
        """Handle show event."""
        if self.center_on_parent:
            self._center_on_parent()
    
    def resizeEvent(self, event):
        """Handle resize event."""
        if self.center_on_parent:
            self._center_on_parent() 