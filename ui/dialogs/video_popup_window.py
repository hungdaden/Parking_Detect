"""
video_popup_window.py — Cửa sổ Pop-up độc lập hiển thị luồng Camera nhận diện
Sử dụng PyQt6 native, hoàn toàn tương thích với macOS (Cocoa) và Windows,
không bị xung đột thread hay deadlock như OpenCV cv2.imshow.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap, QImage, QKeyEvent
from ui.theme import resource_path, set_titlebar_theme


class VideoPopupWindow(QWidget):
    """Cửa sổ Pop-up độc lập hiển thị luồng video nhận diện xe."""

    def __init__(self, parent_ui):
        super().__init__()
        self.parent_ui = parent_ui
        self.setWindowTitle("Parking Detect — Luồng Camera Nhận Diện (Cửa sổ riêng)")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.resize(1120, 680)
        self.setMinimumSize(640, 400)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header bar với các nút thao tác nhanh
        header_bar = QHBoxLayout()
        self.lbl_title = QLabel("📺 Luồng Camera Trực Tiếp (Pop-up Mode)")
        self.lbl_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #7B68EE;")
        header_bar.addWidget(self.lbl_title)

        header_bar.addStretch()

        self.lbl_shortcuts = QLabel("Phím tắt: [Q] hoặc [Esc] để quay về In-App | [I] Check-in nhanh")
        self.lbl_shortcuts.setStyleSheet("color: #888; font-size: 11px;")
        header_bar.addWidget(self.lbl_shortcuts)

        self.btn_dock = QPushButton("📥 Xem trong App")
        self.btn_dock.setToolTip("Thu nhỏ luồng video về màn hình chính")
        self.btn_dock.clicked.connect(self.dock_back_to_app)
        header_bar.addWidget(self.btn_dock)

        layout.addLayout(header_bar)

        # Video Display Label
        self.lbl_video = QLabel("Đang chờ khung hình...")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setStyleSheet(
            "background-color: #0d1117; border-radius: 8px; border: 1px solid #30363d;"
        )
        layout.addWidget(self.lbl_video, stretch=1)

        set_titlebar_theme(self, parent_ui.is_dark_mode)

    def update_frame(self, qimg: QImage):
        """Cập nhật frame video lên label hiển thị."""
        if qimg.isNull():
            return
        target_size = self.lbl_video.size()
        if target_size.width() <= 10 or target_size.height() <= 10:
            target_size = self.lbl_video.minimumSize()
        pixmap = QPixmap.fromImage(qimg)
        scaled_pixmap = pixmap.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_video.setPixmap(scaled_pixmap)

    def dock_back_to_app(self):
        """Chuyển chế độ hiển thị về nhúng trong App."""
        self.hide()
        if hasattr(self.parent_ui, 'show_video_embedded'):
            self.parent_ui.show_video_embedded = True
        if hasattr(self.parent_ui, 'switch_settings_view'):
            self.parent_ui.switch_settings_view.setChecked(True)
        if hasattr(self.parent_ui, 'lbl_mode_status'):
            self.parent_ui.lbl_mode_status.setText("Trực tiếp trong App (Embedded Mode)")
        if hasattr(self.parent_ui, 'lbl_video_mode_tag'):
            self.parent_ui.lbl_video_mode_tag.setText("[ Embedded Mode ]")
        self.parent_ui.save_app_config()

    def closeEvent(self, event):
        """Khi người dùng bấm nút X đóng cửa sổ: tự động chuyển về chế độ In-App."""
        self.dock_back_to_app()
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):
        """Xử lý các phím tắt khi người dùng thao tác trên cửa sổ Pop-up."""
        key = event.key()
        if key in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
            self.dock_back_to_app()
        elif key == Qt.Key.Key_I:
            if hasattr(self.parent_ui, 'perform_checkin_action'):
                self.parent_ui.perform_checkin_action()
        else:
            super().keyPressEvent(event)

