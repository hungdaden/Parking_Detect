import cv2
import numpy as np
from PyQt6.QtWidgets import QMessageBox
from ui.dialogs.preset_dialog import show_save_preset_dialog


def execute_draw_window(parent_ui):
    """
    Mở cửa sổ OpenCV tương tác để vẽ các vùng đỗ xe (polygons).
    """
    if parent_ui.is_webcam:
        cap = cv2.VideoCapture(parent_ui.webcam_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(parent_ui.webcam_index)
    else:
        cap = cv2.VideoCapture(parent_ui.video_path)

    if not parent_ui.is_webcam:
        try:
            start_sec = float(parent_ui.entry_start.text())
            cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
        except Exception:
            pass
    else:
        for _ in range(20):
            cap.read()

    ret, frame = cap.read()
    if not ret:
        QMessageBox.critical(parent_ui, "Lỗi", "Không thể đọc khung hình từ video.")
        cap.release()
        return

    temp_frame = frame.copy()
    cv2.namedWindow('Draw Parking Regions', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Draw Parking Regions', frame.shape[1], frame.shape[0])

    parent_ui.current_polygon = []

    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            parent_ui.current_polygon.append((x, y))
        elif event == cv2.EVENT_RBUTTONDOWN:
            if len(parent_ui.current_polygon) > 2:
                parent_ui.polygons.append(parent_ui.current_polygon.copy())
                parent_ui.current_polygon = []

    cv2.setMouseCallback('Draw Parking Regions', mouse_callback)

    while True:
        display = temp_frame.copy()
        for i, poly in enumerate(parent_ui.polygons):
            cv2.polylines(display, [np.array(poly)], True, (255, 0, 0), 2)
            cx = int(sum(p[0] for p in poly) / len(poly))
            cy = int(sum(p[1] for p in poly) / len(poly))
            cv2.putText(display, str(i + 1), (cx - 8, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        if parent_ui.current_polygon:
            for i in range(len(parent_ui.current_polygon)):
                cv2.circle(display, parent_ui.current_polygon[i], 3, (0, 0, 255), -1)
                if i > 0:
                    cv2.line(display, parent_ui.current_polygon[i - 1], parent_ui.current_polygon[i], (0, 0, 255), 2)

        cv2.imshow('Draw Parking Regions', display)
        key = cv2.waitKey(20) & 0xFF

        if key == ord(' ') or key == 13 or key == ord('q'):
            break
        elif key == ord('c'):
            parent_ui.polygons.clear()
            parent_ui.current_polygon.clear()
        elif key == ord('z') or key == 8:
            if parent_ui.current_polygon:
                parent_ui.current_polygon.pop()
            elif parent_ui.polygons:
                parent_ui.polygons.pop()

    cv2.destroyWindow('Draw Parking Regions')
    cap.release()

    if parent_ui.polygons:
        show_save_preset_dialog(parent_ui)
