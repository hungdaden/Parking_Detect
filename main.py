import cv2
import numpy as np
import time
import os
import json
import sys
from datetime import datetime

from ultralytics import YOLO

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox, 
    QListWidget, QFrame, QDialog, QScrollArea, QGridLayout,
    QGraphicsOpacityEffect, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette
import threading

from db_manager import ParkingDB

PRESETS_DIR = "presets"
if not os.path.exists(PRESETS_DIR):
    os.makedirs(PRESETS_DIR)

# ================= THEMES =================

LIGHT_THEME = """
QWidget {
    background-color: #f5f6fa;
    color: #2f3640;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QMainWindow {
    background-color: #f5f6fa;
}
QFrame#MainFrame {
    background-color: #ffffff;
    border-radius: 10px;
    border: 1px solid #dcdde1;
}
QPushButton {
    background-color: #3498db;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 15px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2980b9;
}
QPushButton:disabled {
    background-color: #bdc3c7;
    color: #ecf0f1;
}
QPushButton#CheckInBtn {
    background-color: #27ae60;
}
QPushButton#CheckInBtn:hover {
    background-color: #2ecc71;
}
QPushButton#CheckInBtn:disabled {
    background-color: #95a5a6;
}
QPushButton#DangerBtn {
    background-color: #e74c3c;
}
QPushButton#DangerBtn:hover {
    background-color: #c0392b;
}
QPushButton#SuccessBtn {
    background-color: #2ecc71;
}
QPushButton#SuccessBtn:hover {
    background-color: #27ae60;
}
QLineEdit {
    padding: 5px;
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    background-color: #ffffff;
    color: #2c3e50;
}
QListWidget {
    background-color: #ffffff;
    border: 1px solid #bdc3c7;
    border-radius: 4px;
}
QListWidget::item:selected {
    background-color: #3498db;
    color: white;
}
QLabel#HeaderLabel {
    font-size: 18px;
    font-weight: bold;
    color: #2c3e50;
}
QLabel#SubHeaderLabel {
    font-size: 12px;
    color: #7f8c8d;
}
QTableWidget {
    font-size: 14px;
    font-weight: bold;
}
QHeaderView::section {
    font-size: 14px;
    font-weight: bold;
    background-color: #ecf0f1;
}
"""

DARK_THEME = """
QWidget {
    background-color: #1e272e;
    color: #f5f6fa;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QMainWindow {
    background-color: #1e272e;
}
QFrame#MainFrame {
    background-color: #2f3640;
    border-radius: 10px;
    border: 1px solid #353b48;
}
QPushButton {
    background-color: #0984e3;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 15px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #74b9ff;
}
QPushButton:disabled {
    background-color: #7f8fa6;
    color: #dcdde1;
}
QPushButton#CheckInBtn {
    background-color: #00b894;
}
QPushButton#CheckInBtn:hover {
    background-color: #55efc4;
}
QPushButton#CheckInBtn:disabled {
    background-color: #7f8fa6;
}
QPushButton#DangerBtn {
    background-color: #d63031;
}
QPushButton#DangerBtn:hover {
    background-color: #ff7675;
}
QPushButton#SuccessBtn {
    background-color: #00b894;
}
QPushButton#SuccessBtn:hover {
    background-color: #55efc4;
}
QLineEdit {
    padding: 5px;
    border: 1px solid #7f8fa6;
    border-radius: 4px;
    background-color: #353b48;
    color: #f5f6fa;
}
QListWidget {
    background-color: #353b48;
    border: 1px solid #7f8fa6;
    border-radius: 4px;
    color: #f5f6fa;
}
QListWidget::item:selected {
    background-color: #0984e3;
    color: white;
}
QLabel#HeaderLabel {
    font-size: 18px;
    font-weight: bold;
    color: #00a8ff;
}
QLabel#SubHeaderLabel {
    font-size: 12px;
    color: #b2bec3;
}
QTableWidget {
    font-size: 14px;
    font-weight: bold;
}
QHeaderView::section {
    font-size: 14px;
    font-weight: bold;
    background-color: #2f3640;
}
"""

# ================= THREADING =================

class DetectionWorker(QObject):
    # Signals
    on_error = pyqtSignal(str)
    on_finished = pyqtSignal()
    show_checkin_signal = pyqtSignal()
    
    def __init__(self, app_logic, screen_w, screen_h):
        super().__init__()
        self.app = app_logic
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._is_running = True
        
    def run(self):
        try:
            model = YOLO('yolov8n.pt')
        except Exception as e:
            self.on_error.emit(f"Gặp sự cố khi khởi tạo model YOLO: {e}")
            return
            
        is_webcam = self.app.is_webcam
        
        if is_webcam:
            cap = cv2.VideoCapture(self.app.webcam_index)
        else:
            cap = cv2.VideoCapture(self.app.video_path)
            
        if not cap.isOpened():
            self.on_error.emit(f"Không thể kết nối với Camera số {self.app.webcam_index}." if is_webcam else "Không thể đọc đường dẫn video.")
            self.on_finished.emit()
            return
        
        if not is_webcam:
            try:
                start_sec = float(self.app.entry_start.text())
                end_sec = float(self.app.entry_end.text()) if float(self.app.entry_end.text()) > 0 else float('inf')
            except:
                start_sec, end_sec = 0.0, float('inf')
            cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
        else:
            start_sec, end_sec = 0.0, float('inf')
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        delay = int(1000 / fps) if fps > 0 else 30
        
        self.app.prev_poly_status = [False] * len(self.app.polygons)
        
        DEBOUNCE_THRESHOLD = 10
        debounce_counters = [0] * len(self.app.polygons)
        confirmed_status = [False] * len(self.app.polygons)
        
        if self.app.polygons:
            self.app.db.reset_slot_status(len(self.app.polygons))
            
        polygons_copy = [poly[:] for poly in self.app.polygons]
        preset_name = self.app.current_preset_name
        
        if is_webcam:
            w = int(self.screen_w * 2 / 3)
            h = self.screen_h - 100
            cv2.namedWindow("Video Detection", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Video Detection", w, h)
            cv2.moveWindow("Video Detection", 0, 0)
            
        while cap.isOpened() and self._is_running:
            if not is_webcam:
                current_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                if current_msec > end_sec * 1000:
                    break
                    
            start_time_proc = time.time()
            
            ret, frame = cap.read()
            if not ret:
                break
                
            results = model.predict(frame, stream=True, verbose=False, classes=[2, 5, 7])
            
            car_centers = []
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    cx = int((x1 + x2) / 2)
                    cy = int(y2 - (y2 - y1) * 0.3)
                    car_centers.append((cx, cy))
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (200, 200, 200), 1)
                    cv2.circle(frame, (cx, cy), 4, (0, 255, 255), -1)
                    
            occupied_count = 0
            current_status = []
            for idx, poly in enumerate(polygons_copy):
                poly_np = np.array(poly, np.int32)
                is_occupied = False
                for cx, cy in car_centers:
                    if cv2.pointPolygonTest(poly_np, (cx, cy), False) >= 0:
                        is_occupied = True
                        break
                
                current_status.append(is_occupied)
                pcx = int(sum(p[0] for p in poly) / len(poly))
                pcy = int(sum(p[1] for p in poly) / len(poly))
                
                if is_occupied:
                    cv2.polylines(frame, [poly_np], True, (0, 0, 255), 3)
                    occupied_count += 1
                else:
                    cv2.polylines(frame, [poly_np], True, (0, 255, 0), 3)
                
                cv2.putText(frame, str(idx + 1), (pcx - 8, pcy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
            if len(current_status) == len(confirmed_status):
                for idx in range(len(current_status)):
                    if current_status[idx] != confirmed_status[idx]:
                        debounce_counters[idx] += 1
                        if debounce_counters[idx] >= DEBOUNCE_THRESHOLD:
                            slot_id = idx + 1
                            if current_status[idx] and not confirmed_status[idx]:
                                self.app.db.record_vehicle_in(slot_id, preset_name)
                            elif not current_status[idx] and confirmed_status[idx]:
                                self.app.db.record_vehicle_out(slot_id, preset_name)
                            confirmed_status[idx] = current_status[idx]
                            debounce_counters[idx] = 0
                    else:
                        debounce_counters[idx] = 0
                        
            self.app.last_poly_status = current_status
            
            cv2.putText(frame, "'Q' stop | 'I' Check In", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f"Trang thai: {occupied_count}/{len(polygons_copy)} cho", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            
            cv2.imshow("Video Detection", frame)
            
            elapsed = int((time.time() - start_time_proc) * 1000)
            wait_time = max(1, delay - elapsed)
            
            key = cv2.waitKey(wait_time) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('i') and is_webcam:
                self.show_checkin_signal.emit()
                
        cap.release()
        try:
            cv2.destroyWindow("Video Detection")
        except:
            pass
            
        self.on_finished.emit()

    def stop(self):
        self._is_running = False


# ================= MAIN UI =================

class ParkingAppUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # State
        self.db = ParkingDB()
        self.polygons = []
        self.current_polygon = []
        self.current_preset_name = ""
        self.video_path = ""
        self.is_webcam = False
        self.webcam_index = 0
        
        self.detection_active = False
        self.last_poly_status = []
        self.prev_poly_status = []
        
        self.is_dark_mode = False # Default to light mode
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Parking Vehicle Detection")
        self.resize(700, 450)
        
        # Central widget & Layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header Controls
        header_layout = QHBoxLayout()
        self.toggle_theme_btn = QPushButton("🌞 Chế độ Sáng")
        self.toggle_theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.toggle_theme_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        header_layout.addStretch()
        
        self.btn_dashboard = QPushButton("📊 Báo Cáo")
        self.btn_dashboard.clicked.connect(self.show_dashboard)
        header_layout.addWidget(self.btn_dashboard)
        
        self.btn_checkin = QPushButton("✅ Check In")
        self.btn_checkin.setObjectName("CheckInBtn")
        self.btn_checkin.clicked.connect(self.show_checkin_popup)
        self.btn_checkin.setEnabled(False)
        header_layout.addWidget(self.btn_checkin)
        
        main_layout.addLayout(header_layout)
        
        # Main Frame Box
        frame_main = QFrame()
        frame_main.setObjectName("MainFrame")
        frame_layout = QVBoxLayout(frame_main)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        frame_layout.setSpacing(15)
        
        lbl_title = QLabel("PARKING DETECTION SETTINGS")
        lbl_title.setObjectName("HeaderLabel")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_layout.addWidget(lbl_title)
        
        # Video settings
        v_layout1 = QHBoxLayout()
        v_layout1.addWidget(QLabel("Video/Camera:"))
        self.entry_video = QLineEdit()
        self.entry_video.setReadOnly(True)
        v_layout1.addWidget(self.entry_video)
        
        self.btn_browse = QPushButton("Duyệt File")
        self.btn_browse.clicked.connect(self.browse_file)
        v_layout1.addWidget(self.btn_browse)
        
        self.btn_webcam = QPushButton("Sử Dụng Camera")
        self.btn_webcam.clicked.connect(self.choose_webcam)
        v_layout1.addWidget(self.btn_webcam)
        
        frame_layout.addLayout(v_layout1)
        
        # Time settings
        v_layout2 = QHBoxLayout()
        v_layout2.addWidget(QLabel("Thời điểm bắt đầu (giây):"))
        self.entry_start = QLineEdit("0")
        v_layout2.addWidget(self.entry_start)
        
        v_layout2.addWidget(QLabel("Thời điểm kết thúc (giây):"))
        self.entry_end = QLineEdit("0")
        v_layout2.addWidget(self.entry_end)
        
        frame_layout.addLayout(v_layout2)
        
        lbl_hint = QLabel("0 = chạy hết video")
        lbl_hint.setObjectName("SubHeaderLabel")
        frame_layout.addWidget(lbl_hint)
        
        # Action Buttons
        v_layout3 = QHBoxLayout()
        self.btn_mark = QPushButton("Khoanh Vùng Đỗ Xe")
        self.btn_mark.clicked.connect(self.start_draw_regions)
        v_layout3.addWidget(self.btn_mark)
        
        self.btn_detect = QPushButton("BẮT ĐẦU NHẬN DIỆN")
        self.btn_detect.setObjectName("SuccessBtn")
        self.btn_detect.clicked.connect(self.start_detection)
        v_layout3.addWidget(self.btn_detect)
        
        frame_layout.addLayout(v_layout3)
        main_layout.addWidget(frame_main)
        main_layout.addStretch()
        
        self.apply_theme()
        
    def fade_in(self, widget):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(400)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()
        widget.anim = anim
        
    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        if self.is_dark_mode:
            self.toggle_theme_btn.setText("🌞 Chế độ Sáng")
        else:
            self.toggle_theme_btn.setText("🌙 Chế độ Tối")
            
    def apply_theme(self):
        theme = DARK_THEME if self.is_dark_mode else LIGHT_THEME
        self.setStyleSheet(theme)
        if hasattr(self, 'dash') and self.dash.isVisible():
            self.dash.setStyleSheet(theme)
        if hasattr(self, '_checkin_dialog') and self._checkin_dialog.isVisible():
            self._checkin_dialog.setStyleSheet(theme)
        
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn Video", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if file_path:
            self.video_path = file_path
            self.entry_video.setText(file_path)
            self.entry_start.setText("0")
            self.entry_end.setText("0")
            self.is_webcam = False
            self.btn_webcam.setText("Sử Dụng Camera")
            self.polygons = []
            
    def choose_webcam(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Chọn Camera")
        dialog.resize(300, 200)
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Đang tìm các camera khả dụng..."))
        # Force UI update
        QApplication.processEvents()
        
        available_cameras = []
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
                
        # clear loading
        for i in reversed(range(layout.count())): 
            layout.itemAt(i).widget().setParent(None)
            
        if not available_cameras:
            layout.addWidget(QLabel("Không tìm thấy camera nào."))
            btn = QPushButton("Đóng")
            btn.clicked.connect(dialog.accept)
            layout.addWidget(btn)
        else:
            layout.addWidget(QLabel("Chọn một camera:"))
            for cam_idx in available_cameras:
                btn = QPushButton(f"Camera {cam_idx}")
                btn.clicked.connect(lambda checked, idx=cam_idx: self.set_webcam(idx, dialog))
                layout.addWidget(btn)
                
        self.fade_in(dialog)
        dialog.exec()
        
    def set_webcam(self, idx, dialog):
        self.webcam_index = idx
        self.is_webcam = True
        self.video_path = ""
        self.entry_video.setText(f"Webcam {idx}")
        self.btn_webcam.setText(f"Đang Chọn Camera {idx}")
        self.entry_start.setEnabled(False)
        self.entry_end.setEnabled(False)
        self.polygons = []
        dialog.accept()

    def get_preset_list(self):
        files = [f for f in os.listdir(PRESETS_DIR) if f.endswith('.json')]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(PRESETS_DIR, x)), reverse=True)
        return [f.replace('.json', '') for f in files]

    def start_draw_regions(self):
        if not self.video_path and not self.is_webcam:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn video trước bằng nút Duyệt File hoặc chọn Camera!")
            return
            
        presets = self.get_preset_list()
        if not presets:
            self.execute_draw()
            return
            
        self.show_preset_dialog(presets)
        
    def show_preset_dialog(self, presets):
        dialog = QDialog(self)
        dialog.setWindowTitle("Chọn Preset hoặc Vẽ mới")
        dialog.resize(400, 350)
        layout = QVBoxLayout(dialog)
        
        lbl = QLabel("CHỌN VÙNG ĐỖ XE")
        lbl.setObjectName("HeaderLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        
        layout.addWidget(QLabel("Chọn preset có sẵn hoặc vẽ mới:"))
        
        lw = QListWidget()
        lw.addItems(presets)
        layout.addWidget(lw)
        
        btn_layout = QHBoxLayout()
        
        btn_load = QPushButton("Tải Preset")
        btn_load.setObjectName("SuccessBtn")
        btn_draw = QPushButton("Vẽ Mới")
        btn_del = QPushButton("Xóa Preset")
        btn_del.setObjectName("DangerBtn")
        
        btn_layout.addWidget(btn_load)
        btn_layout.addWidget(btn_draw)
        btn_layout.addWidget(btn_del)
        layout.addLayout(btn_layout)
        
        def on_load():
            item = lw.currentItem()
            if not item:
                QMessageBox.warning(dialog, "Chưa chọn", "Vui lòng chọn một preset từ danh sách.")
                return
            self.load_preset(item.text())
            dialog.accept()
            
        def on_draw():
            dialog.accept()
            self.execute_draw()
            
        def on_del():
            item = lw.currentItem()
            if not item:
                QMessageBox.warning(dialog, "Chưa chọn", "Vui lòng chọn một preset.")
                return
            name = item.text()
            rep = QMessageBox.question(dialog, "Xác nhận", f"Bạn có chắc muốn xóa preset '{name}'?")
            if rep == QMessageBox.StandardButton.Yes:
                p = os.path.join(PRESETS_DIR, name + ".json")
                if os.path.exists(p): os.remove(p)
                lw.takeItem(lw.row(item))
                
        btn_load.clicked.connect(on_load)
        btn_draw.clicked.connect(on_draw)
        btn_del.clicked.connect(on_del)
        
        self.fade_in(dialog)
        dialog.exec()
        
    def load_preset(self, name):
        p = os.path.join(PRESETS_DIR, name + ".json")
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.polygons = [list(map(tuple, poly)) for poly in data.get("polygons", [])]
            self.current_preset_name = name
            QMessageBox.information(self, "Thành công", f"Đã tải preset '{name}' với {len(self.polygons)} ô đỗ.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi tải preset: {e}")

    def execute_draw(self):
        # Implement raw OpenCV drawing logic with blocking waitKey
        if self.is_webcam:
            cap = cv2.VideoCapture(self.webcam_index)
        else:
            cap = cv2.VideoCapture(self.video_path)
        
        if not self.is_webcam:
            try:
                start_sec = float(self.entry_start.text())
                cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
            except:
                pass
                
        ret, frame = cap.read()
        if not ret:
            QMessageBox.critical(self, "Lỗi", "Không thể đọc khung hình từ video.")
            cap.release()
            return
            
        temp_frame = frame.copy()
        cv2.namedWindow('Draw Parking Regions', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Draw Parking Regions', frame.shape[1], frame.shape[0])
        
        self.current_polygon = []
        
        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                self.current_polygon.append((x, y))
            elif event == cv2.EVENT_RBUTTONDOWN:
                if len(self.current_polygon) > 2:
                    self.polygons.append(self.current_polygon.copy())
                    self.current_polygon = []
                    
        cv2.setMouseCallback('Draw Parking Regions', mouse_callback)
        
        while True:
            display = temp_frame.copy()
            for i, poly in enumerate(self.polygons):
                cv2.polylines(display, [np.array(poly)], True, (255, 0, 0), 2)
                cx = int(sum(p[0] for p in poly) / len(poly))
                cy = int(sum(p[1] for p in poly) / len(poly))
                cv2.putText(display, str(i + 1), (cx - 8, cy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            
            if self.current_polygon:
                for i in range(len(self.current_polygon)):
                    cv2.circle(display, self.current_polygon[i], 3, (0, 0, 255), -1)
                    if i > 0:
                        cv2.line(display, self.current_polygon[i-1], self.current_polygon[i], (0, 0, 255), 2)
                        
            cv2.imshow('Draw Parking Regions', display)
            key = cv2.waitKey(20) & 0xFF
            
            if key == ord(' ') or key == 13 or key == ord('q'):
                break
            elif key == ord('c'):
                self.polygons.clear()
                self.current_polygon.clear()
            elif key == ord('z') or key == 8:
                if self.current_polygon: self.current_polygon.pop()
                elif self.polygons: self.polygons.pop()
                
        cv2.destroyWindow('Draw Parking Regions')
        cap.release()
        
        if self.polygons:
            self.show_save_preset_dialog()
            
    def show_save_preset_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Lưu Preset")
        dialog.resize(350, 180)
        layout = QVBoxLayout(dialog)
        
        lbl = QLabel("ĐẶT TÊN PRESET")
        lbl.setObjectName("HeaderLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        
        layout.addWidget(QLabel(f"Đã vẽ {len(self.polygons)} ô đỗ. Nhập tên:"))
        
        name_entry = QLineEdit(f"Preset_{datetime.now().strftime('%d%m_%H%M')}")
        layout.addWidget(name_entry)
        
        btn_save = QPushButton("Lưu")
        btn_save.setObjectName("SuccessBtn")
        layout.addWidget(btn_save)
        
        def on_save():
            name = name_entry.text().strip()
            if not name: return
            data = {
                "name": name,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "polygons": [list(map(list, poly)) for poly in self.polygons]
            }
            p = os.path.join(PRESETS_DIR, name + ".json")
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.current_preset_name = name
            QMessageBox.information(dialog, "Thành công", f"Đã lưu preset '{name}'!")
            dialog.accept()
            
        btn_save.clicked.connect(on_save)
        self.fade_in(dialog)
        dialog.exec()
        
    def start_detection(self):
        if self.detection_active: return
        
        if not self.video_path and not self.is_webcam:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn video trước!")
            return
        
        if not self.polygons:
            res = QMessageBox.question(self, "Cảnh báo", "Bạn chưa khoanh vùng nhận diện bãi đỗ nào!\nVideo sẽ chạy nhưng không hiện chỗ trống đậu xe. Bạn có muốn tiếp tục chạy luôn không?")
            if res == QMessageBox.StandardButton.No:
                return
            
        screen = QApplication.primaryScreen().geometry()
        self.worker = DetectionWorker(self, screen.width(), screen.height())
        self.worker.on_error.connect(lambda e: QMessageBox.critical(self, "Lỗi", e))
        self.worker.show_checkin_signal.connect(self.show_checkin_popup)
        self.worker.on_finished.connect(self._on_detection_finished)
        
        self.detection_active = True
        self.btn_detect.setText("ĐANG CHẠY...")
        self.btn_detect.setEnabled(False)
        self.btn_checkin.setEnabled(self.is_webcam)
        
        # Use python threading to avoid Qt Event Loop deadlock with cv2 UI functions
        t = threading.Thread(target=self.worker.run, daemon=True)
        t.start()
        
    def _on_detection_finished(self):
        self.detection_active = False
        self.btn_detect.setText("BẮT ĐẦU NHẬN DIỆN")
        self.btn_detect.setEnabled(True)
        self.btn_checkin.setEnabled(False)
        
    def show_checkin_popup(self):
        if not self.detection_active or not self.is_webcam:
            QMessageBox.information(self, "Check In", "Chỉ hoạt động khi đang dùng Camera.")
            return
            
        status = self.last_poly_status
        if not status:
            QMessageBox.information(self, "Check In", "Chưa có dữ liệu. Vui lòng đợi...")
            return
            
        dialog = QDialog() # Independent window
        dialog.setWindowTitle("Check In")
        dialog.resize(420, 500)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        
        lbl = QLabel("TÌNH TRẠNG BÃI ĐỖ XE")
        lbl.setObjectName("HeaderLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        
        empty_slots = [i+1 for i, occ in enumerate(status) if not occ]
        occ_slots = [i+1 for i, occ in enumerate(status) if occ]
        tot = len(status)
        
        layout.addWidget(QLabel(f"Trống: {len(empty_slots)}/{tot}   |   Đã đỗ: {len(occ_slots)}/{tot}"))
        
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        w = QWidget()
        wl = QVBoxLayout(w)
        
        for idx in range(tot):
            slot = idx + 1
            is_occ = status[idx]
            
            f = QFrame()
            f.setObjectName("MainFrame") # Reuse border style
            fl = QHBoxLayout(f)
            
            if is_occ:
                txt = f"🔴  Ô {slot}:  Đã có xe"
                col = "#e74c3c"
            else:
                txt = f"🟢  Ô {slot}:  Còn trống"
                col = "#27ae60"
                
            l = QLabel(txt)
            l.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 14px;")
            fl.addWidget(l)
            wl.addWidget(f)
            
        wl.addStretch()
        sa.setWidget(w)
        layout.addWidget(sa)
        
        if empty_slots:
            g = f"✅ Vui lòng tiến vào Ô {empty_slots[0]}."
            c = "#27ae60"
        else:
            g = "⛔ Bãi đỗ đã đầy."
            c = "#e74c3c"
            
        glbl = QLabel(g)
        glbl.setStyleSheet(f"color: {c}; font-weight: bold; font-size: 14px;")
        glbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(glbl)
        
        def on_close():
            dialog.accept()
            try:
                cv2.setWindowProperty("Video Detection", cv2.WND_PROP_TOPMOST, 1)
                cv2.setWindowProperty("Video Detection", cv2.WND_PROP_TOPMOST, 0)
            except: pass

        btn = QPushButton("Đóng")
        btn.clicked.connect(on_close)
        layout.addWidget(btn)
        
        self._checkin_dialog = dialog
        self.fade_in(dialog)
        dialog.show()

    def show_dashboard(self):
        self.dash = QDialog()
        self.dash.setWindowTitle("📊 Báo Cáo & Thống Kê")
        self.dash.resize(600, 580)
        self.dash.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(self.dash)
        
        lbl = QLabel("BÁO CÁO & THỐNG KÊ")
        lbl.setObjectName("HeaderLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)
        
        # Thống kê hôm nay
        self.f_stats = QFrame()
        self.f_stats.setObjectName("MainFrame")
        sl = QHBoxLayout(self.f_stats)
        
        self.lbl_in = QLabel("Lượt vào: 0")
        self.lbl_out = QLabel("Lượt ra: 0")
        self.lbl_occ = QLabel("Đang đỗ: 0")
        for l in [self.lbl_in, self.lbl_out, self.lbl_occ]:
            l.setStyleSheet("font-size: 14px; font-weight: bold; color: #2980b9;" if not self.is_dark_mode else "font-size: 14px; font-weight: bold; color: #00a8ff;")
            sl.addWidget(l)
            
        layout.addWidget(QLabel("Thống kê hôm nay"))
        layout.addWidget(self.f_stats)
        
        # Thống kê theo ô
        layout.addWidget(QLabel("Thống kê theo Ô đỗ"))
        self.table_slot = QTableWidget()
        self.table_slot.setMinimumHeight(150)
        layout.addWidget(self.table_slot)
        
        # Lịch sử
        layout.addWidget(QLabel("Lịch sử gần nhất"))
        self.table_hist = QTableWidget()
        self.table_hist.setMinimumHeight(150)
        layout.addWidget(self.table_hist)
        
        btn_clear = QPushButton("🗑️ Xóa Báo Cáo")
        btn_clear.setObjectName("DangerBtn")
        btn_clear.clicked.connect(self._clear_dashboard)
        layout.addWidget(btn_clear)
        
        self.timer = QTimer(self.dash)
        self.timer.timeout.connect(self._refresh_dashboard)
        self.timer.start(1500)
        
        self._refresh_dashboard()
        self.fade_in(self.dash)
        self.dash.show()
        
    def _clear_dashboard(self):
        rep = QMessageBox.question(self.dash, "Xác nhận", "Xóa toàn bộ dữ liệu báo cáo?")
        if rep == QMessageBox.StandardButton.Yes:
            self.db.clear_all_data()
            self._refresh_dashboard()
            
    def _refresh_dashboard(self):
        try:
            stats = self.db.get_today_stats()
            self.lbl_in.setText(f"🚗 Lượt vào: {stats['total_in']}")
            self.lbl_out.setText(f"🚙 Lượt ra: {stats['total_out']}")
            self.lbl_occ.setText(f"🅿️ Đang đỗ: {stats['currently_occupied']}")
            
            def centered_item(text):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return item
                
            # Rebuild slots
            summary = self.db.get_slot_summary()
            self.table_slot.setRowCount(len(summary))
            self.table_slot.setColumnCount(3)
            self.table_slot.setHorizontalHeaderLabels(["Ô đỗ", "Lượt vào", "Lượt ra"])
            self.table_slot.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            
            for r, row in enumerate(summary):
                self.table_slot.setItem(r, 0, centered_item(f"Ô {row['slot_id']}"))
                self.table_slot.setItem(r, 1, centered_item(str(row['total_in'])))
                self.table_slot.setItem(r, 2, centered_item(str(row['total_out'])))
            
            # Rebuild history
            hist = self.db.get_history(15)
            self.table_hist.setRowCount(len(hist))
            self.table_hist.setColumnCount(4)
            self.table_hist.setHorizontalHeaderLabels(["Thời gian", "Ô đỗ", "Xe", "Sự kiện"])
            self.table_hist.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            
            for r, ev in enumerate(hist):
                ts = ev["timestamp"][11:19] if len(ev["timestamp"])>11 else ""
                txt = "VÀO" if ev["event_type"] == "IN" else "RA"
                
                self.table_hist.setItem(r, 0, centered_item(ts))
                self.table_hist.setItem(r, 1, centered_item(f"Ô {ev['slot_id']}"))
                self.table_hist.setItem(r, 2, centered_item(ev["vehicle_id"] or ""))
                
                item_event = centered_item(txt)
                item_event.setForeground(QColor("#27ae60" if ev["event_type"] == "IN" else "#e67e22"))
                font = item_event.font()
                font.setBold(True)
                item_event.setFont(font)
                self.table_hist.setItem(r, 3, item_event)
            
        except Exception as e:
            print("Refresh err", e)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Enable High DPI scaling
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        
    window = ParkingAppUI()
    window.show()
    sys.exit(app.exec())
