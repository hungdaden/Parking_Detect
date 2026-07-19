import cv2
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QApplication
from ui.theme import set_titlebar_theme


def choose_webcam_dialog(parent_ui):
    """
    Hiển thị dialog liệt kê các camera khả dụng và cho người dùng chọn.
    """
    dialog = QDialog(parent_ui)
    dialog.setWindowTitle("Chọn Camera")
    dialog.resize(320, 220)
    layout = QVBoxLayout(dialog)

    layout.addWidget(QLabel("Đang tìm các camera khả dụng..."))
    QApplication.processEvents()

    available_cameras = []
    try:
        from pygrabber.dshow_graph import FilterGraph
        graph = FilterGraph()
        devices = graph.get_input_devices()
        for idx, name in enumerate(devices):
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                available_cameras.append((idx, name))
                cap.release()
    except Exception as e:
        print("Pygrabber camera list error:", e)
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append((i, f"Camera {i}"))
                cap.release()

    for i in reversed(range(layout.count())):
        item = layout.itemAt(i)
        if item is not None and item.widget() is not None:
            item.widget().setParent(None)  # type: ignore

    if not available_cameras:
        layout.addWidget(QLabel("Không tìm thấy camera nào."))
        btn = QPushButton("Đóng")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
    else:
        layout.addWidget(QLabel("Chọn một camera khả dụng:"))
        for cam_idx, cam_name in available_cameras:
            btn = QPushButton(cam_name)
            btn.clicked.connect(lambda checked, idx=cam_idx, name=cam_name: _set_webcam(parent_ui, idx, name, dialog))
            layout.addWidget(btn)

    set_titlebar_theme(dialog, parent_ui.is_dark_mode)
    parent_ui.fade_in(dialog)
    dialog.exec()


def _set_webcam(parent_ui, idx, name, dialog):
    parent_ui.webcam_index = idx
    parent_ui.is_webcam = True
    parent_ui.video_path = ""
    parent_ui.entry_video.setText(name)
    parent_ui.btn_webcam.setText(f"📷 {name}")
    parent_ui.entry_start.setEnabled(False)
    parent_ui.entry_end.setEnabled(False)
    parent_ui.polygons = []
    dialog.accept()
