from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QLinearGradient


class ClickUpRangeSlider(QWidget):
    """
    ClickUp-style Dual Handle Range Slider Widget for selecting start and end seconds.
    Features:
    - Left handle (Start Second) & Right handle (End Second)
    - Click & drag left/right handle or drag the middle range bar
    - Sleek ClickUp gradient styling (#7B68EE / #8B5CF6 / #6366F1)
    - Dark mode & Light mode support
    - Emits valuesChanged(int low, int high) signal
    """
    valuesChanged = pyqtSignal(int, int)

    def __init__(self, minimum=0, maximum=100, low_val=0, high_val=100, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._minimum = max(0, int(minimum))
        self._maximum = max(self._minimum + 1, int(maximum))
        self._low_val = max(self._minimum, min(int(low_val), self._maximum))
        self._high_val = max(self._low_val, min(int(high_val), self._maximum))

        self._active_handle = None  # None, 'low', 'high', 'bar'
        self._hover_handle = None   # None, 'low', 'high', 'bar'
        self._drag_start_x = 0
        self._drag_start_low = 0
        self._drag_start_high = 0

        self.setMouseTracking(True)

    # --- Properties ---
    def minimum(self):
        return self._minimum

    def maximum(self):
        return self._maximum

    def lowValue(self):
        return self._low_val

    def highValue(self):
        return self._high_val

    def setRange(self, minimum, maximum):
        self._minimum = max(0, int(minimum))
        self._maximum = max(self._minimum + 1, int(maximum))
        self._low_val = max(self._minimum, min(self._low_val, self._maximum))
        self._high_val = max(self._low_val, min(self._high_val, self._maximum))
        self.update()

    def setLowValue(self, val):
        val = int(val)
        val = max(self._minimum, min(val, self._high_val))
        if val != self._low_val:
            self._low_val = val
            self.update()
            self.valuesChanged.emit(self._low_val, self._high_val)

    def setHighValue(self, val):
        val = int(val)
        val = max(self._low_val, min(val, self._maximum))
        if val != self._high_val:
            self._high_val = val
            self.update()
            self.valuesChanged.emit(self._low_val, self._high_val)

    def setValues(self, low, high):
        low = int(low)
        high = int(high)
        low = max(self._minimum, min(low, self._maximum))
        high = max(low, min(high, self._maximum))
        if low != self._low_val or high != self._high_val:
            self._low_val = low
            self._high_val = high
            self.update()
            self.valuesChanged.emit(self._low_val, self._high_val)

    # --- Geometry Helpers ---
    def _track_rect(self):
        margin = 16
        track_h = 10
        y = (self.height() - track_h) / 2
        return QRectF(margin, y, max(1, self.width() - 2 * margin), track_h)

    def _val_to_x(self, val):
        rect = self._track_rect()
        rng = self._maximum - self._minimum
        if rng <= 0:
            return rect.left()
        ratio = (val - self._minimum) / rng
        return rect.left() + ratio * rect.width()

    def _x_to_val(self, x):
        rect = self._track_rect()
        if rect.width() <= 0:
            return self._minimum
        ratio = (x - rect.left()) / rect.width()
        ratio = max(0.0, min(1.0, ratio))
        return round(self._minimum + ratio * (self._maximum - self._minimum))

    # --- Event Handlers ---
    def mousePressEvent(self, a0):
        if not self.isEnabled() or a0 is None or a0.button() != Qt.MouseButton.LeftButton:
            return

        x = a0.position().x()
        low_x = self._val_to_x(self._low_val)
        high_x = self._val_to_x(self._high_val)
        handle_radius = 14

        dist_low = abs(x - low_x)
        dist_high = abs(x - high_x)

        if dist_low <= handle_radius and dist_low <= dist_high:
            self._active_handle = 'low'
        elif dist_high <= handle_radius:
            self._active_handle = 'high'
        elif low_x < x < high_x:
            self._active_handle = 'bar'
            self._drag_start_x = x
            self._drag_start_low = self._low_val
            self._drag_start_high = self._high_val
        else:
            if dist_low < dist_high:
                self._active_handle = 'low'
                self.setLowValue(self._x_to_val(x))
            else:
                self._active_handle = 'high'
                self.setHighValue(self._x_to_val(x))

        self.update()

    def mouseMoveEvent(self, a0):
        if not self.isEnabled() or a0 is None:
            return

        x = a0.position().x()
        low_x = self._val_to_x(self._low_val)
        high_x = self._val_to_x(self._high_val)
        handle_radius = 14

        dist_low = abs(x - low_x)
        dist_high = abs(x - high_x)
        if dist_low <= handle_radius and dist_low <= dist_high:
            self._hover_handle = 'low'
        elif dist_high <= handle_radius:
            self._hover_handle = 'high'
        elif low_x < x < high_x:
            self._hover_handle = 'bar'
        else:
            self._hover_handle = None

        if self._active_handle == 'low':
            new_val = self._x_to_val(x)
            self.setLowValue(min(new_val, self._high_val))
        elif self._active_handle == 'high':
            new_val = self._x_to_val(x)
            self.setHighValue(max(new_val, self._low_val))
        elif self._active_handle == 'bar':
            rect = self._track_rect()
            dx_val = int(round((x - self._drag_start_x) / rect.width() * (self._maximum - self._minimum)))
            span = self._drag_start_high - self._drag_start_low
            new_low = max(self._minimum, min(self._drag_start_low + dx_val, self._maximum - span))
            new_high = new_low + span
            self.setValues(new_low, new_high)

        self.update()

    def mouseReleaseEvent(self, a0):
        self._active_handle = None
        self.update()

    def leaveEvent(self, a0):
        self._hover_handle = None
        self.update()

    # --- Painting ---
    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark = False
        if self.window() and hasattr(self.window(), 'is_dark_mode'):
            is_dark = getattr(self.window(), 'is_dark_mode', False)

        is_enabled = self.isEnabled()
        rect = self._track_rect()
        low_x = self._val_to_x(self._low_val)
        high_x = self._val_to_x(self._high_val)

        # 1. Background Track
        if not is_enabled:
            track_bg = QColor("#222430") if is_dark else QColor("#F1F5F9")
        else:
            track_bg = QColor("#1E1E2E") if is_dark else QColor("#E2E8F0")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_bg))
        painter.drawRoundedRect(rect, 5, 5)

        # 2. Selected Active Range Track (ClickUp Purple/Indigo)
        if is_enabled:
            active_rect = QRectF(low_x, rect.top(), max(0, high_x - low_x), rect.height())
            gradient = QLinearGradient(active_rect.topLeft(), active_rect.topRight())
            if is_dark:
                gradient.setColorAt(0.0, QColor("#6366F1"))
                gradient.setColorAt(1.0, QColor("#8B5CF6"))
            else:
                gradient.setColorAt(0.0, QColor("#7B68EE"))
                gradient.setColorAt(1.0, QColor("#6366F1"))

            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(active_rect, 5, 5)

        # 3. Handle Thumbs
        if is_enabled:
            for handle_type, val, h_x in [('low', self._low_val, low_x), ('high', self._high_val, high_x)]:
                is_active = (self._active_handle == handle_type)
                is_hover = (self._hover_handle == handle_type)

                r = 11 if (is_active or is_hover) else 9
                center = QPointF(h_x, rect.center().y())

                # Outer Glow Ring on Hover / Drag
                if is_active or is_hover:
                    glow_color = QColor(139, 92, 246, 100) if is_dark else QColor(123, 104, 238, 80)
                    painter.setBrush(QBrush(glow_color))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(center, r + 4, r + 4)

                # Thumb Circle
                border_color = QColor("#8B5CF6") if is_dark else QColor("#7B68EE")
                painter.setPen(QPen(border_color, 2.5))
                painter.setBrush(QBrush(QColor("#FFFFFF")))
                painter.drawEllipse(center, r, r)

                # Inner Accent Dot
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(border_color))
                painter.drawEllipse(center, 3.5, 3.5)

        painter.end()
