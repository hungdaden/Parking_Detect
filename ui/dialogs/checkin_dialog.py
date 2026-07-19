from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFrame, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.theme import set_titlebar_theme
from logic.overlay_logic import generate_guidance_map_pixmap


def show_checkin_guidance_dialog(parent_ui, slot_id):
    """
    Hiển thị hộp thoại hướng dẫn xe vào ô đỗ với sơ đồ vị trí ô đỗ được highlight.
    """
    dialog = QDialog(parent_ui)
    dialog.setWindowTitle(f"Hướng Dẫn Xe Vào Ô Số {slot_id}")
    dialog.setMinimumWidth(560)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(25, 20, 25, 20)
    layout.setSpacing(15)

    # Header Icon & Title
    lbl_icon = QLabel("🚗 HƯỚNG DẪN ĐỖ XE VÀO Ô TRỐNG")
    lbl_icon.setFont(QFont('Segoe UI', 15, QFont.Weight.Bold))
    lbl_icon.setStyleSheet("color: #10B981;")
    lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl_icon)

    # Guidance Title
    lbl_guidance = QLabel(f"👉 VUI LÒNG DI CHUYỂN VÀO:  🅿️ Ô SỐ {slot_id}")
    lbl_guidance.setFont(QFont('Segoe UI', 14, QFont.Weight.Bold))
    lbl_guidance.setStyleSheet("color: #7B68EE;")
    lbl_guidance.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl_guidance)

    # Image Card displaying the Parking Slots Map with Highlighted Slot
    card = QFrame()
    card.setObjectName("CardFrame")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(10, 10, 10, 10)

    lbl_img_map = QLabel()
    lbl_img_map.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_img_map.setMinimumSize(500, 300)

    last_raw = getattr(parent_ui, 'last_raw_frame', None)
    last_fr = getattr(parent_ui, 'last_frame', None)
    pixmap = generate_guidance_map_pixmap(slot_id, parent_ui.polygons, parent_ui.last_poly_status, last_raw, last_fr)

    scaled_pixmap = pixmap.scaled(
        520, 320,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )
    lbl_img_map.setPixmap(scaled_pixmap)
    card_layout.addWidget(lbl_img_map)

    layout.addWidget(card)

    lbl_sub = QLabel("(Sơ đồ vị trí trực quan giúp định hướng xe vào đỗ)")
    lbl_sub.setObjectName("SubHeaderLabel")
    lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl_sub)

    # Confirm Button
    btn_ok = QPushButton("✅ Check-In Thành Công")
    btn_ok.setObjectName("SuccessBtn")
    btn_ok.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
    btn_ok.setMinimumHeight(42)
    btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_ok.clicked.connect(dialog.accept)
    layout.addWidget(btn_ok)

    set_titlebar_theme(dialog, parent_ui.is_dark_mode)
    parent_ui.fade_in(dialog)
    dialog.exec()
