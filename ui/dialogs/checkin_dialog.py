from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFrame, QPushButton, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QScreen

from ui.theme import set_titlebar_theme
from logic.overlay_logic import generate_guidance_map_pixmap


def create_single_guidance_dialog(parent_ui, slot_id, target_screen: QScreen | None = None):
    """
    Tạo một cửa sổ Hướng dẫn xe vào ô đỗ kích thước lớn với sơ đồ trực quan.
    """
    dialog = QDialog(parent_ui)
    dialog.setWindowTitle(f"Hướng Dẫn Xe Vào Ô Số {slot_id}")
    
    # Check target screen resolution if available to adapt max dimensions
    target_w, target_h = 1920, 1080
    if target_screen is not None:
        target_w = target_screen.geometry().width()
        target_h = target_screen.geometry().height()

    dialog_min_w = min(1050, int(target_w * 0.85))
    dialog_min_h = min(720, int(target_h * 0.85))
    dialog.setMinimumSize(dialog_min_w, dialog_min_h)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(30, 25, 30, 25)
    layout.setSpacing(18)

    # Header Icon & Title
    lbl_icon = QLabel("🚗 HƯỚNG DẪN ĐỖ XE VÀO Ô TRỐNG")
    lbl_icon.setFont(QFont('Segoe UI', 18, QFont.Weight.Bold))
    lbl_icon.setStyleSheet("color: #10B981;")
    lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl_icon)

    # Guidance Title
    lbl_guidance = QLabel(f"👉 VUI LÒNG DI CHUYỂN VÀO:  🅿️ Ô SỐ {slot_id}")
    lbl_guidance.setFont(QFont('Segoe UI', 18, QFont.Weight.Bold))
    lbl_guidance.setStyleSheet("color: #7B68EE;")
    lbl_guidance.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl_guidance)

    # Image Card displaying the Parking Slots Map with Highlighted Slot
    card = QFrame()
    card.setObjectName("CardFrame")
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(15, 15, 15, 15)

    lbl_img_map = QLabel()
    lbl_img_map.setAlignment(Qt.AlignmentFlag.AlignCenter)
    img_w = max(800, dialog_min_w - 60)
    img_h = max(460, dialog_min_h - 220)
    lbl_img_map.setMinimumSize(img_w, img_h)

    last_raw = getattr(parent_ui, 'last_raw_frame', None)
    last_fr = getattr(parent_ui, 'last_frame', None)
    pixmap = generate_guidance_map_pixmap(slot_id, parent_ui.polygons, parent_ui.last_poly_status, last_raw, last_fr)

    scaled_pixmap = pixmap.scaled(
        img_w + 40, img_h + 40,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )
    lbl_img_map.setPixmap(scaled_pixmap)
    card_layout.addWidget(lbl_img_map)

    layout.addWidget(card)

    lbl_sub = QLabel("(Sơ đồ vị trí trực quan)")
    lbl_sub.setObjectName("SubHeaderLabel")
    lbl_sub.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
    lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl_sub)

    # Confirm Button
    btn_ok = QPushButton("✅ Check-In Thành Công")
    btn_ok.setObjectName("SuccessBtn")
    btn_ok.setFont(QFont('Segoe UI', 13, QFont.Weight.Bold))
    btn_ok.setMinimumHeight(48)
    btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_ok.clicked.connect(dialog.accept)
    layout.addWidget(btn_ok)

    set_titlebar_theme(dialog, getattr(parent_ui, 'is_dark_mode', False))
    return dialog


def position_dialog_on_screen(dialog: QDialog, target_screen: QScreen):
    """
    Vị trí hóa và căn giữa cửa sổ dialog trên màn hình (QScreen) chỉ định.
    """
    if target_screen is None:
        return

    dialog.show()
    handle = dialog.windowHandle()
    if handle is not None:
        handle.setScreen(target_screen)

    screen_geo = target_screen.geometry()
    dialog_geo = dialog.geometry()

    center_x = screen_geo.x() + (screen_geo.width() - dialog_geo.width()) // 2
    center_y = screen_geo.y() + (screen_geo.height() - dialog_geo.height()) // 2

    dialog.move(center_x, center_y)


def show_checkin_guidance_dialog(parent_ui, slot_id, target_screen_indices=None):
    """
    Hiển thị hộp thoại hướng dẫn xe vào ô đỗ với kích thước lớn trên (các) màn hình được chọn.
    Nếu đang có hộp thoại hướng dẫn hiện sẵn, tự động đóng hộp thoại cũ và mở hộp thoại mới thay thế.
    """
    # Đóng tất cả dialog hướng dẫn xe đang hiện trước đó
    if not hasattr(parent_ui, '_active_guidance_dialogs'):
        parent_ui._active_guidance_dialogs = []

    if parent_ui._active_guidance_dialogs:
        for old_dlg in list(parent_ui._active_guidance_dialogs):
            try:
                old_dlg.close()
            except Exception:
                pass
        parent_ui._active_guidance_dialogs.clear()

    all_screens = QApplication.screens()
    created_dialogs = []

    if not all_screens:
        dlg = create_single_guidance_dialog(parent_ui, slot_id)
        if hasattr(parent_ui, 'fade_in'):
            parent_ui.fade_in(dlg)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        created_dialogs.append(dlg)
    else:
        # Determine targeted QScreen objects
        valid_screens = []
        if target_screen_indices is not None:
            for idx in target_screen_indices:
                if 0 <= idx < len(all_screens):
                    valid_screens.append(all_screens[idx])

        if not valid_screens:
            primary = QApplication.primaryScreen()
            valid_screens = [primary] if primary else [all_screens[0]]

        # If single screen selected
        if len(valid_screens) == 1:
            dlg = create_single_guidance_dialog(parent_ui, slot_id, valid_screens[0])
            position_dialog_on_screen(dlg, valid_screens[0])
            if hasattr(parent_ui, 'fade_in'):
                parent_ui.fade_in(dlg)
            dlg.raise_()
            dlg.activateWindow()
            created_dialogs.append(dlg)
        else:
            # If multiple screens selected, open on all target screens simultaneously
            dialogs = []
            for scr in valid_screens:
                dlg = create_single_guidance_dialog(parent_ui, slot_id, scr)
                dialogs.append(dlg)
                created_dialogs.append(dlg)

            def close_all():
                for d in dialogs:
                    try:
                        d.close()
                    except Exception:
                        pass

            for idx, dlg in enumerate(dialogs):
                scr = valid_screens[idx]
                dlg.accepted.connect(close_all)
                dlg.rejected.connect(close_all)
                position_dialog_on_screen(dlg, scr)
                if hasattr(parent_ui, 'fade_in'):
                    parent_ui.fade_in(dlg)
                dlg.raise_()
                dlg.activateWindow()

    parent_ui._active_guidance_dialogs.extend(created_dialogs)


