from PyQt6.QtWidgets import QCheckBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QBrush


class ToggleSwitch(QCheckBox):
    """Custom Horizontal Toggle Switch Widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(54, 28)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle()
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark = False
        if self.window() and hasattr(self.window(), 'is_dark_mode'):
            is_dark = getattr(self.window(), 'is_dark_mode', False)

        if self.isChecked():
            track_color = QColor("#8B5CF6") if is_dark else QColor("#7B68EE")
            thumb_x = 28
        else:
            track_color = QColor("#33374D") if is_dark else QColor("#CBD5E1")
            thumb_x = 4

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(0, 0, 54, 28, 14, 14)

        # White thumb knob
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(thumb_x, 4, 20, 20)
        painter.end()
