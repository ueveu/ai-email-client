from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QBrush
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
import os
import sys

def generate_app_icon(save_path: str, size: int = 64) -> None:
    """
    Generate a simple application icon.
    
    Args:
        save_path: Path to save the icon
        size: Icon size in pixels
    """
    # Create a square icon
    icon = QPixmap(size, size)
    icon.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(icon)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Draw background circle
    painter.setBrush(QBrush(QColor("#2196F3")))  # Material Blue
    painter.setPen(Qt.PenStyle.NoPen)
    margin = size // 32
    painter.drawEllipse(margin, margin, size - 2*margin, size - 2*margin)
    
    # Draw text
    painter.setPen(QColor("white"))
    font = QFont("Arial", size // 3, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(icon.rect(), Qt.AlignmentFlag.AlignCenter, "AI")
    
    painter.end()
    
    # Save the icon
    icon.save(save_path)
    print(f"Generated icon: {save_path}")

if __name__ == "__main__":
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Generate icons in different sizes
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    sizes = [16, 32, 64, 128, 256]
    for size in sizes:
        icon_path = os.path.join(assets_dir, f"app_icon_{size}.png")
        generate_app_icon(icon_path, size)
    
    # Create the default app icon
    generate_app_icon(os.path.join(assets_dir, "app_icon.png"), 64) 