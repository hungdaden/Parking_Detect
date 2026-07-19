from PyQt6.QtWidgets import QFrame
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QCursor


class HoverSidebarFrame(QFrame):
    """Hover Docked Sidebar Overlay Widget với animation mở rộng / thu gọn tự động."""

    def __init__(self, parent=None, collapsed_width=60, expanded_width=230):
        super().__init__(parent)
        self.collapsed_w = collapsed_width
        self.expanded_w = expanded_width
        self.is_expanded = False
        self.anim = None

        self.leave_timer = QTimer(self)
        self.leave_timer.setSingleShot(True)
        self.leave_timer.timeout.connect(self.check_and_collapse)

        self.setObjectName("SidebarFrame")
        self.setMouseTracking(True)

    def enterEvent(self, a0):
        self.leave_timer.stop()
        self.expand_sidebar()
        super().enterEvent(a0)

    def leaveEvent(self, a0):
        self.leave_timer.start(180)
        super().leaveEvent(a0)

    def check_and_collapse(self):
        global_pos = QCursor.pos()
        local_pos = self.mapFromGlobal(global_pos)
        if self.rect().contains(local_pos):
            return
        self.collapse_sidebar()

    def expand_sidebar(self):
        if self.is_expanded and (self.anim is None or self.anim.state() != QPropertyAnimation.State.Running):
            return
        self.is_expanded = True
        self.raise_()
        self.animate_to_width(self.expanded_w)

    def collapse_sidebar(self):
        if not self.is_expanded and (self.anim is None or self.anim.state() != QPropertyAnimation.State.Running):
            return
        self.is_expanded = False
        self.animate_to_width(self.collapsed_w)

    def animate_to_width(self, target_w):
        if self.anim:
            self.anim.stop()
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(220)
        current_geo = self.geometry()
        target_geo = QRect(0, 0, target_w, current_geo.height())
        self.anim.setStartValue(current_geo)
        self.anim.setEndValue(target_geo)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

    def set_handle_theme(self, is_dark):
        pass
