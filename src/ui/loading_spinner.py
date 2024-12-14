"""
Loading spinner widget for visual feedback during long-running operations.
Provides a modern, animated loading indicator that can be centered on its parent widget.
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QPaintEvent
from typing import Optional

class LoadingSpinner(QWidget):
    """A loading spinner widget that shows an animated spinning circle."""
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        center_on_parent: bool = True
    ) -> None:
        """
        Initialize the loading spinner.
        
        Args:
            parent: Optional parent widget
            center_on_parent: Whether to center the spinner on its parent
        """
        super().__init__(parent)
        
        # Configuration
        self.angle: float = 0
        self.timer: QTimer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.angular_speed: float = 5
        self.size: int = 40
        self.line_width: int = 3
        self.inner_radius: int = 10
        self.color: QColor = QColor(0, 120, 212)  # Modern blue color
        self.num_lines: int = 12
        self.line_length: int = 8
        
        # Widget properties
        self.setFixedSize(self.size, self.size)
        if parent and center_on_parent:
            self.move_to_center()
        
        # Hide by default
        self.hide()
    
    def move_to_center(self) -> None:
        """Center the spinner on its parent widget."""
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.center().y() - self.height() // 2
            )
    
    def start(self) -> None:
        """Start the spinning animation."""
        self.show()
        if not self.timer.isActive():
            self.timer.start(50)  # Update every 50ms
    
    def stop(self) -> None:
        """Stop the spinning animation."""
        self.timer.stop()
        self.hide()
    
    def rotate(self) -> None:
        """Rotate the spinner by the angular speed."""
        self.angle = (self.angle + self.angular_speed) % 360
        self.update()
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Paint the spinner with fading lines.
        
        Args:
            event: Paint event
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calculate center point
        center = self.rect().center()
        
        # Draw lines with varying opacity
        for i in range(self.num_lines):
            # Calculate angle for this line
            line_angle = self.angle + (i * (360 / self.num_lines))
            
            # Calculate opacity (fade based on angle difference from current angle)
            angle_diff = (i * (360 / self.num_lines)) % 360
            opacity = 1.0 - (angle_diff / 360)
            
            # Set color with opacity
            color = QColor(self.color)
            color.setAlphaF(opacity)
            
            # Set pen
            pen = QPen(color)
            pen.setWidth(self.line_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
            # Calculate line positions
            start_x = center.x() + self.inner_radius * \
                     self._cos_deg(line_angle)
            start_y = center.y() + self.inner_radius * \
                     self._sin_deg(line_angle)
            end_x = center.x() + (self.inner_radius + self.line_length) * \
                   self._cos_deg(line_angle)
            end_y = center.y() + (self.inner_radius + self.line_length) * \
                   self._sin_deg(line_angle)
            
            # Draw line
            painter.drawLine(
                int(start_x), int(start_y),
                int(end_x), int(end_y)
            )
    
    def sizeHint(self) -> QSize:
        """
        Return the recommended size for the widget.
        
        Returns:
            QSize with the recommended dimensions
        """
        return QSize(self.size, self.size)
    
    def _sin_deg(self, angle: float) -> float:
        """
        Calculate sine of angle in degrees.
        
        Args:
            angle: Angle in degrees
            
        Returns:
            Sine value of the angle
        """
        from math import sin, pi
        return sin(angle * pi / 180)
    
    def _cos_deg(self, angle: float) -> float:
        """
        Calculate cosine of angle in degrees.
        
        Args:
            angle: Angle in degrees
            
        Returns:
            Cosine value of the angle
        """
        from math import cos, pi
        return cos(angle * pi / 180)