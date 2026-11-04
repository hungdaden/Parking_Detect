import cv2
import sys
import subprocess
import re
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QApplication
from ui.theme import set_titlebar_theme


def get_macos_camera_list():
    """
    Truy vấn danh sách camera trên macOS bằng metadata phần cứng (system_profiler),
    không mở luồng video capture ngầm nên KHÔNG làm kích hoạt màn hình iPhone (Continuity Camera).
    """
    cameras = []
    try:
        cmd = ['system_profiler', 'SPCameraDataType', '-detailLevel', 'mini']
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=2)
        current_cam = None
        current_model = ''
        for line in out.splitlines():
            m = re.match(r'^\s{4}([^\n:]+):\s*$', line)
            if m:
                if current_cam and current_cam.lower() != 'camera':
                    cameras.append((current_cam, current_model))
                current_cam = m.group(1).strip()
                current_model = ''
                continue
            m_model = re.match(r'^\s+Model ID:\s*(.+)$', line)
            if m_model:
                current_model = m_model.group(1).strip()
        if current_cam and current_cam.lower() != 'camera':
            cameras.append((current_cam, current_model))
    except Exception as e:
        print("Lỗi đọc danh sách camera qua system_profiler:", e)

    if not cameras:
        # Fallback an toàn: chỉ liệt kê Camera 0 mặc định (FaceTime)
        cameras = [("FaceTime HD Camera", "Built-in")]
    else:
        # Trên macOS AVFoundation: Apple luôn ưu tiên thiết bị Continuity Camera (iPhone)
        # ở Index 0, và đẩy FaceTime HD Camera (Built-in) xuống Index 1.
        # Ngược lại, system_profiler lại liệt kê Built-in trước. Do đó ta cần sắp xếp
        # đưa iPhone lên Index 0 và FaceTime về Index 1 để khớp 100% với OpenCV.
        cameras.sort(key=lambda c: 0 if ("iphone" in f"{c[0]} {c[1]}".lower() or "ipad" in f"{c[0]} {c[1]}".lower()) else 1)

    result = []
    for idx, (cam_name, model_id) in enumerate(cameras):
        info_str = f"{cam_name} {model_id}".lower()
        if "facetime" in info_str or "built-in" in info_str:
            label = f"💻 {cam_name} [Camera {idx}]"
        elif "iphone" in info_str or "ipad" in info_str:
            label = f"📱 {cam_name} [Camera {idx}]"
        else:
            label = f"📷 {cam_name} [Camera {idx}]"
        result.append((idx, label))
    return result


def choose_webcam_dialog(parent_ui):
    """
    Hiển thị dialog liệt kê các camera khả dụng và cho người dùng chọn.
    """
    dialog = QDialog(parent_ui)
    dialog.setWindowTitle("Chọn Camera")
    dialog.resize(380, 240)
    layout = QVBoxLayout(dialog)

    layout.addWidget(QLabel("Đang tìm các camera khả dụng..."))
    QApplication.processEvents()

    available_cameras = []
    if sys.platform == 'win32':
        # Windows: Use DirectShow via pygrabber for named device listing
        try:
            from pygrabber.dshow_graph import FilterGraph
            graph = FilterGraph()
            devices = graph.get_input_devices()
            for idx, name in enumerate(devices):
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(idx)
                if cap.isOpened():
                    available_cameras.append((idx, name))
                    cap.release()
        except Exception as e:
            print("Pygrabber camera list error:", e)
            for i in range(5):
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available_cameras.append((i, f"Camera {i}"))
                    cap.release()
    elif sys.platform == 'darwin':
        # macOS: Dùng system_profiler metadata để không kết nối ngầm gây bật màn hình iPhone
        available_cameras = get_macos_camera_list()
    else:
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
    print(f"[CameraDialog] Người dùng đã chọn: Camera Index = {idx} ({name})")
    clean_name = name.split("(")[0].split("[")[0].strip().replace("💻 ", "").replace("📱 ", "").replace("📷 ", "")
    parent_ui.entry_video.setText(f"{clean_name} (Index {idx})")
    parent_ui.btn_webcam.setText(f"📷 {clean_name} [{idx}]")
    parent_ui.entry_start.setEnabled(False)
    parent_ui.entry_end.setEnabled(False)
    # Giữ lại polygons nếu đã có (hoặc người dùng đã chọn preset)
    dialog.accept()
