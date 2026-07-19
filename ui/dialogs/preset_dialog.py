from datetime import datetime
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import Qt

from ui.theme import set_titlebar_theme
from data.preset_manager import PresetManager


def show_save_preset_dialog(parent_ui):
    """
    Hộp thoại đặt tên và lưu preset khoanh vùng.
    """
    dialog = QDialog(parent_ui)
    dialog.setWindowTitle("Lưu Preset Khoanh Vùng")
    dialog.resize(350, 180)
    layout = QVBoxLayout(dialog)

    lbl = QLabel("ĐẶT TÊN PRESET")
    lbl.setObjectName("HeaderLabel")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl)

    layout.addWidget(QLabel(f"Đã vẽ {len(parent_ui.polygons)} ô đỗ. Nhập tên:"))

    name_entry = QLineEdit(f"Preset_{datetime.now().strftime('%d%m_%H%M')}")
    layout.addWidget(name_entry)

    btn_save = QPushButton("Lưu Preset")
    btn_save.setObjectName("SuccessBtn")
    layout.addWidget(btn_save)

    def on_save():
        name = name_entry.text().strip()
        if not name:
            return
        try:
            PresetManager.save_preset(name, parent_ui.polygons)
            parent_ui.current_preset_name = name
            parent_ui.refresh_preset_list()
            QMessageBox.information(dialog, "Thành công", f"Đã lưu preset '{name}'!")
            dialog.accept()
        except Exception as e:
            QMessageBox.critical(dialog, "Lỗi", f"Không thể lưu preset: {e}")

    btn_save.clicked.connect(on_save)
    set_titlebar_theme(dialog, parent_ui.is_dark_mode)
    parent_ui.fade_in(dialog)
    dialog.exec()
