import cv2
import numpy as np
import time
import os
import sys
import re
import math
import concurrent.futures

from ultralytics import YOLO
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QImage

from logic.alpr_utils import preprocess_license_plate


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def _compute_vehicle_slot_overlap(box, polygons):
    """
    Tính toán tỉ lệ overlap giữa Bounding Box xe [x1, y1, x2, y2] và danh sách các polygon ô đỗ.
    Khử nhiễu góc nghiêng camera chéo (Perspective Distortion) bằng cách tính diện tích
    trên phân vùng chân xe / bánh xe tiếp xúc mặt đường (Ground Contact Footprint - 40% chiều cao dưới của xe).
    Trả về: (total_overlap_ratio, max_single_slot_ratio, secondary_slot_ratio, primary_slot_id)
    """
    x1, y1, x2, y2 = [int(v) for v in box]
    box_w = max(1, x2 - x1)
    box_h = max(1, y2 - y1)

    # Ground Contact Footprint: Lấy 40% chiều cao phía dưới xe (vệt bánh xe tiếp xúc mặt đường)
    footprint_y1 = y1 + int(box_h * 0.60)
    footprint_h = max(1, y2 - footprint_y1)
    box_area = float(box_w * footprint_h)

    box_mask = np.ones((footprint_h, box_w), dtype=np.uint8)

    total_overlap_pixels = 0
    slot_ratios = []

    for idx, poly in enumerate(polygons):
        if not poly or len(poly) < 3:
            continue
        local_poly = np.array([[pt[0] - x1, pt[1] - footprint_y1] for pt in poly], dtype=np.int32)
        slot_mask = np.zeros((footprint_h, box_w), dtype=np.uint8)
        cv2.fillPoly(slot_mask, [local_poly], 1)

        overlap_px = np.count_nonzero(slot_mask & box_mask)
        ratio = float(overlap_px) / box_area
        if ratio > 0:
            slot_ratios.append((ratio, idx + 1))

        total_overlap_pixels += overlap_px

    slot_ratios.sort(key=lambda item: item[0], reverse=True)

    max_single_slot_ratio = slot_ratios[0][0] if slot_ratios else 0.0
    primary_slot_id = slot_ratios[0][1] if slot_ratios else 1
    secondary_slot_ratio = slot_ratios[1][0] if len(slot_ratios) > 1 else 0.0

    total_overlap_ratio = min(1.0, float(total_overlap_pixels) / box_area)
    return total_overlap_ratio, max_single_slot_ratio, secondary_slot_ratio, primary_slot_id


class DetectionWorker(QObject):
    """Worker class chạy trong thread riêng biệt để xử lý nhận diện YOLOv8, debounce ô đỗ và ALPR EasyOCR."""

    on_error = pyqtSignal(str)
    on_finished = pyqtSignal()
    show_checkin_signal = pyqtSignal()
    frame_signal = pyqtSignal(QImage)

    def __init__(self, app_logic, screen_w, screen_h):
        super().__init__()
        self.app = app_logic
        self.screen_w = screen_w
        self.screen_h = screen_h
        self._is_running = True
        self._cv_window_open = False

        self.plate_cascade = None
        self.reader = None
        self.frame_count = 0
        self.recent_plates = {}

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.ocr_future = None
        self.alpr_result_text = ""
        self.alpr_result_time = 0.0

    def _process_alpr(self, crop_img):
        try:
            if self.reader is None:
                return
            processed_img = preprocess_license_plate(crop_img)
            res = self.reader.readtext(processed_img, allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            if res:
                result_list: list = list(res)
                result_list.sort(key=lambda x: x[0][0][1])
                combined_text = "".join([str(x[1]) for x in result_list]).upper()
                raw_text = combined_text.replace("-", "").replace(".", "").replace(" ", "")
                if len(raw_text) < 7:
                    return

                c_to_d = {'O': '0', 'D': '0', 'I': '1', 'S': '5', 'G': '6', 'B': '8', 'A': '4', 'Z': '2', 'T': '7'}
                d_to_c = {'0': 'D', '1': 'I', '2': 'Z', '4': 'A', '5': 'S', '6': 'G', '7': 'T', '8': 'B'}

                chars1 = list(raw_text)
                for i in [0, 1]:
                    if i < len(chars1) and chars1[i] in c_to_d:
                        chars1[i] = c_to_d[chars1[i]]
                if len(chars1) > 2 and chars1[2] in d_to_c:
                    chars1[2] = d_to_c[chars1[2]]
                for i in range(3, len(chars1)):
                    if chars1[i] in c_to_d:
                        chars1[i] = c_to_d[chars1[i]]
                processed_text1 = "".join(chars1)

                chars2 = list(raw_text)
                if len(chars2) >= 8:
                    for i in [0, 1]:
                        if chars2[i] in c_to_d:
                            chars2[i] = c_to_d[chars2[i]]
                    if chars2[2] in d_to_c:
                        chars2[2] = d_to_c[chars2[2]]
                    if chars2[3] in ['I', 'O', 'D']:
                        chars2[3] = c_to_d[chars2[3]]
                    for i in range(4, len(chars2)):
                        if chars2[i] in c_to_d:
                            chars2[i] = c_to_d[chars2[i]]
                processed_text2 = "".join(chars2)

                pattern1 = re.compile(r"^(\d{2}[A-Z])(\d{4,5})$")
                pattern2 = re.compile(r"^(\d{2}[A-Z][A-Z0-9])(\d{4,5})$")

                match1 = pattern1.match(processed_text1)
                match2 = pattern2.match(processed_text2)

                final_text = ""
                if match1 and len(match1.group(2)) == 5:
                    final_text = match1.group(1) + "-" + match1.group(2)
                elif match2:
                    final_text = match2.group(1) + "-" + match2.group(2)
                elif match1:
                    final_text = match1.group(1) + "-" + match1.group(2)

                if final_text:
                    current_time = time.time()
                    if final_text not in self.recent_plates or (current_time - self.recent_plates.get(final_text, 0) > 60):
                        self.recent_plates[final_text] = current_time
                        success, encoded_image = cv2.imencode('.jpg', crop_img)
                        if success:
                            self.app.db.record_license_plate(final_text, encoded_image.tobytes())
                            self.alpr_result_text = final_text
                            self.alpr_result_time = current_time
        except Exception as e:
            print("OCR Error:", e)

    def run(self):
        try:
            model = YOLO(resource_path('yolov8m.pt'))
        except Exception as e:
            self.on_error.emit(f"Gặp sự cố khi khởi tạo model YOLO: {e}")
            return

        is_webcam = self.app.is_webcam

        if is_webcam:
            cap = cv2.VideoCapture(self.app.webcam_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
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
            except Exception:
                start_sec, end_sec = 0.0, float('inf')
            cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
        else:
            start_sec, end_sec = 0.0, float('inf')

        fps = cap.get(cv2.CAP_PROP_FPS)
        delay = int(1000 / fps) if fps > 0 else 30

        self.app.prev_poly_status = [False] * len(self.app.polygons)

        debounce_counters = [0] * len(self.app.polygons)
        confirmed_status = [False] * len(self.app.polygons)

        if self.app.polygons:
            self.app.db.reset_slot_status(len(self.app.polygons))

        polygons_copy = [poly[:] for poly in self.app.polygons]
        preset_name = self.app.current_preset_name
        self._cv_window_open = False

        tracked_vehicles = {}
        next_track_id = 1

        while cap.isOpened() and self._is_running:
            if not is_webcam:
                current_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                if current_msec > end_sec * 1000:
                    break

            start_time_proc = time.time()

            ret, frame = cap.read()
            if not ret:
                break

            self.app.last_raw_frame = frame.copy()

            results = model.predict(frame, stream=True, verbose=False, classes=[2, 5, 7])

            car_centers = []
            detected_vehicles = []
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy() if hasattr(box.xyxy[0], 'cpu') else box.xyxy[0]
                        cx = int((x1 + x2) / 2)
                        cy = int(y2 - (y2 - y1) * 0.3)
                        car_centers.append((cx, cy))
                        box_list = [float(x1), float(y1), float(x2), float(y2)]
                        detected_vehicles.append((box_list, cx, cy))

            curr_time = time.time()
            misparked_enabled = getattr(self.app, 'misparked_enabled', True)
            misparked_delay_sec = float(getattr(self.app, 'misparked_delay_sec', 10))

            updated_tracked_keys = set()
            for vbox, vcx, vcy in detected_vehicles:
                bx1, by1, bx2, by2 = int(vbox[0]), int(vbox[1]), int(vbox[2]), int(vbox[3])
                best_id = None
                best_dist = 60.0

                for tid, tdata in tracked_vehicles.items():
                    if tid in updated_tracked_keys:
                        continue
                    dist = math.hypot(vcx - tdata['last_cx'], vcy - tdata['last_cy'])
                    if dist < best_dist:
                        best_dist = dist
                        best_id = tid

                if best_id is None:
                    best_id = next_track_id
                    next_track_id += 1
                    tracked_vehicles[best_id] = {
                        'last_cx': vcx,
                        'last_cy': vcy,
                        'pos_history': [],
                        'stationary_start': None,
                        'reported_db': False,
                        'last_seen': curr_time
                    }

                tdata = tracked_vehicles[best_id]
                updated_tracked_keys.add(best_id)

                # Calculate frame-to-frame move BEFORE updating last_cx/last_cy
                frame_move = math.hypot(vcx - tdata['last_cx'], vcy - tdata['last_cy'])
                tdata['last_cx'] = vcx
                tdata['last_cy'] = vcy
                tdata['last_seen'] = curr_time

                pos_history = tdata.get('pos_history', [])

                # Reset history if significant movement is detected between frames
                if frame_move >= 2.0:
                    pos_history = []
                    tdata['stationary_start'] = None
                    tdata['reported_db'] = False

                pos_history.append((curr_time, vcx, vcy))
                pos_history = [p for p in pos_history if curr_time - p[0] <= 1.0]
                tdata['pos_history'] = pos_history

                history_time_span = curr_time - pos_history[0][0] if pos_history else 0.0
                max_displacement = max(math.hypot(vcx - px, vcy - py) for _, px, py in pos_history) if pos_history else 0.0

                if max_displacement > 4.0:
                    # Rolling window displacement exceeds threshold -> clear history & reset timer
                    pos_history = [(curr_time, vcx, vcy)]
                    tdata['pos_history'] = pos_history
                    tdata['stationary_start'] = None
                    tdata['reported_db'] = False
                    is_stopped_completely = False
                else:
                    is_stopped_completely = (history_time_span >= 0.3)

                if not is_stopped_completely:
                    tdata['stationary_start'] = None
                    tdata['reported_db'] = False
                else:
                    if tdata['stationary_start'] is None:
                        tdata['stationary_start'] = curr_time

                stat_duration = 0.0
                is_misparked_active = False

                if misparked_enabled and polygons_copy:
                    is_center_in_any_slot = False
                    for poly in polygons_copy:
                        if poly and len(poly) >= 3:
                            poly_np = np.array(poly, np.int32)
                            if cv2.pointPolygonTest(poly_np, (vcx, vcy), False) >= 0:
                                is_center_in_any_slot = True
                                break

                    tot_ratio, max_ratio, sec_ratio, primary_slot = _compute_vehicle_slot_overlap(vbox, polygons_copy)
                    # Vehicle is misplaced IF:
                    # 1) Center is NOT inside any slot AND overlaps slot space (tot_ratio >= 0.15), OR
                    # 2) Center IS inside a slot, BUT a portion of the car extends into ANOTHER slot (sec_ratio >= 0.15)!
                    is_misplaced = (tot_ratio >= 0.15) and ((not is_center_in_any_slot) or (sec_ratio >= 0.15))

                    if not is_misplaced:
                        tdata['stationary_start'] = None
                        tdata['reported_db'] = False
                        tdata['is_misparked_active'] = False
                    else:
                        if is_stopped_completely and tdata['stationary_start'] is not None:
                            stat_duration = curr_time - tdata['stationary_start']
                            bx1, by1, bx2, by2 = int(vbox[0]), int(vbox[1]), int(vbox[2]), int(vbox[3])
                            if stat_duration >= misparked_delay_sec:
                                is_misparked_active = True
                                tdata['is_misparked_active'] = True
                                cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 0, 255), 3)
                                label_text = f"DO SAI VI TRI ({int(stat_duration)}s)"
                                (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                                cv2.rectangle(frame, (bx1, max(0, by1 - 25)), (bx1 + tw + 10, max(25, by1)), (0, 0, 255), -1)
                                cv2.putText(frame, label_text, (bx1 + 5, max(18, by1 - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                                if not tdata['reported_db']:
                                    vid_str = f"V-{best_id:03d}"
                                    self.app.db.record_misparked_event(slot_id=primary_slot, vehicle_id=vid_str, preset_name=preset_name)
                                    tdata['reported_db'] = True
                            else:
                                tdata['is_misparked_active'] = False
                                if getattr(self.app, 'show_stationary_timer', True):
                                    label_text = f"Dang dung ({int(stat_duration)}s/{int(misparked_delay_sec)}s)"
                                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 255, 255), 2)
                                    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                                    cv2.rectangle(frame, (bx1, max(0, by1 - 22)), (bx1 + tw + 10, max(22, by1)), (0, 200, 200), -1)
                                    cv2.putText(frame, label_text, (bx1 + 5, max(16, by1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                        else:
                            tdata['is_misparked_active'] = False

                if getattr(self.app, 'show_vehicle_bbox', True) and not is_misparked_active:
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (200, 200, 200), 1)
                if getattr(self.app, 'show_vehicle_center', True):
                    cv2.circle(frame, (vcx, vcy), 4, (0, 255, 255), -1)

            stale_keys = [k for k, v in tracked_vehicles.items() if curr_time - v['last_seen'] > 3.0]
            for k in stale_keys:
                del tracked_vehicles[k]

            self.app.current_misparked_count = sum(1 for v in tracked_vehicles.values() if v.get('is_misparked_active', False))

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

                if getattr(self.app, 'show_slot_numbers', True):
                    cv2.putText(frame, str(idx + 1), (pcx - 8, pcy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            if len(current_status) == len(confirmed_status):
                curr_debounce_sec = float(getattr(self.app, 'debounce_delay_sec', 0.5))
                target_debounce_frames = max(1, int((fps if fps > 0 else 30) * curr_debounce_sec))
                for idx in range(len(current_status)):
                    if current_status[idx] != confirmed_status[idx]:
                        debounce_counters[idx] += 1
                        if debounce_counters[idx] >= target_debounce_frames:
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
            self.app.last_frame = frame.copy()

            if getattr(self.app, 'alpr_enabled', False):
                self.frame_count += 1
                h, w = frame.shape[:2]
                box_w, box_h = int(w * 0.5), int(h * 0.3)
                px = int((w - box_w) / 2)
                py = int((h - box_h) / 2)

                cv2.rectangle(frame, (px, py), (px + box_w, py + box_h), (0, 255, 0), 2)
                cv2.putText(frame, "DUA BIEN SO VAO DAY", (px, py - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame, "ALPR: ON", (w - 120, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                if time.time() - getattr(self, 'alpr_result_time', 0) < 3:
                    cv2.putText(frame, f"Da doc: {self.alpr_result_text}", (px, py + box_h + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                if self.frame_count % 15 == 0:
                    if self.reader is None:
                        if getattr(self.app, 'alpr_reader', None) is not None:
                            self.reader = self.app.alpr_reader
                        else:
                            try:
                                import easyocr  # type: ignore
                                self.app.alpr_reader = easyocr.Reader(['en'], gpu=True)
                                self.reader = self.app.alpr_reader
                            except Exception as e:
                                print("Lỗi khởi tạo ALPR:", e)

                    if self.reader is not None and (self.ocr_future is None or self.ocr_future.done()):
                        plate_crop = frame[py:py + box_h, px:px + box_w].copy()
                        self.ocr_future = self.executor.submit(self._process_alpr, plate_crop)

            # Dynamic Display Handling (Embedded vs Popup Window)
            if self.app.show_video_embedded:
                if self._cv_window_open:
                    try:
                        cv2.destroyWindow("Video Detection")
                    except Exception:
                        pass
                    self._cv_window_open = False

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                fh, fw, fch = rgb_frame.shape
                bytes_per_line = fch * fw
                qimg = QImage(bytes(rgb_frame.data), fw, fh, bytes_per_line, QImage.Format.Format_RGB888)
                self.frame_signal.emit(qimg.copy())

                elapsed = int((time.time() - start_time_proc) * 1000)
                wait_time = max(1, delay - elapsed)
                time.sleep(wait_time / 1000.0)
            else:
                if not self._cv_window_open or cv2.getWindowProperty("Video Detection", cv2.WND_PROP_VISIBLE) < 1:
                    w = int(self.screen_w * 2 / 3)
                    h = self.screen_h - 100
                    cv2.namedWindow("Video Detection", cv2.WINDOW_NORMAL)
                    cv2.resizeWindow("Video Detection", w, h)
                    cv2.moveWindow("Video Detection", 0, 0)
                    self._cv_window_open = True

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
        if self._cv_window_open:
            try:
                cv2.destroyWindow("Video Detection")
            except Exception:
                pass
            self._cv_window_open = False

        self.executor.shutdown(wait=False)
        self.on_finished.emit()

    def stop(self):
        self._is_running = False
        self.executor.shutdown(wait=False)
