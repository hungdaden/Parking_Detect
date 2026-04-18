import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from ultralytics import YOLO
import time

class ParkingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ứng dụng Nhận diện Bãi đỗ xe")
        self.root.geometry("750x480")
        
        # status agru
        self.video_path = tk.StringVar()
        self.start_time = tk.DoubleVar(value=0.0)
        self.end_time = tk.DoubleVar(value=0.0)
        self.full_video = tk.BooleanVar(value=True)
        self.is_webcam = tk.BooleanVar(value=False)
        self.webcam_index = 0
        self.detection_active = False
        self.last_poly_status = []  # True = occupied, False = empty
        
        self.polygons = [] # ve
        self.current_polygon = [] # dang ve do
        
        # UI
        self.setup_ui()
        
    def setup_ui(self):
        # Frame trên cùng chứa tiêu đề + nút Check In
        frame_top = tk.Frame(self.root)
        frame_top.pack(fill='x', padx=20, pady=(15, 5))
        
        # Tiêu đề đây
        lbl_title = tk.Label(frame_top, text="HỆ THỐNG NHẬN DIỆN BÃI ĐỖ XE", font=("Arial", 16, "bold"), fg="#2c3e50")
        lbl_title.pack(side='left', expand=True)
        
        # Nút Check In góc trên phải
        self.btn_checkin = tk.Button(frame_top, text="Check In", width=10, bg="#95a5a6", fg="white", font=("Arial", 9, "bold"), state='disabled', command=self.show_checkin_popup)
        self.btn_checkin.pack(side='right')
        
        # Frame chọn file
        frame_file = tk.Frame(self.root)
        frame_file.pack(fill='x', padx=30, pady=10)
        
        tk.Label(frame_file, text="Đường dẫn Video:").pack(side='top', anchor='w')
        tk.Entry(frame_file, textvariable=self.video_path, width=70, state='readonly').pack(side='left', pady=5)
        tk.Button(frame_file, text="Duyệt File...", command=self.browse_file, bg="#bdc3c7").pack(side='left', padx=10)
        
        # Frame cấu hình thời gian
        frame_time = tk.LabelFrame(self.root, text=" Cấu hình Thời gian chạy video ", font=("Arial", 10, "bold"))
        frame_time.pack(fill='x', padx=30, pady=15, ipadx=10, ipady=10)
        
        self.chk_full = tk.Checkbutton(frame_time, text="Chạy toàn bộ video (Full video)", variable=self.full_video, command=self.toggle_entries)
        self.chk_full.grid(row=0, column=0, columnspan=4, sticky='w', padx=5, pady=5)
        
        tk.Label(frame_time, text="Giây Bắt Đầu:").grid(row=1, column=0, sticky='e', padx=5)
        self.entry_start = tk.Entry(frame_time, textvariable=self.start_time, width=15, state='disabled')
        self.entry_start.grid(row=1, column=1, sticky='w')
        
        tk.Label(frame_time, text="Giây Kết Thúc:").grid(row=1, column=2, sticky='e', padx=20)
        self.entry_end = tk.Entry(frame_time, textvariable=self.end_time, width=15, state='disabled')
        self.entry_end.grid(row=1, column=3, sticky='w')
        
        # Các nút chức năng chính
        frame_actions = tk.Frame(self.root)
        frame_actions.pack(pady=30)
        
        self.btn_webcam = tk.Button(frame_actions, text="Sử Dụng Webcam", width=20, height=2, bg="#f39c12", fg="white", font=("Arial", 11, "bold"), command=self.toggle_webcam_button)
        self.btn_webcam.grid(row=0, column=2, padx=10)
        
        tk.Button(frame_actions, text="Khoanh Vùng Đỗ Xe", width=20, height=2, bg="#3498db", fg="white", font=("Arial", 11, "bold"), command=self.draw_regions).grid(row=0, column=0, padx=10)
        
        tk.Button(frame_actions, text="Bắt Đầu Nhận Diện", width=20, height=2, bg="#e74c3c", fg="white", font=("Arial", 11, "bold"), command=self.run_detection).grid(row=0, column=1, padx=10)
        
        # Hướng dẫn
        lbl_info = tk.Label(self.root, text="Hướng dẫn vẽ: Click Chuột Trái để chọn điểm, Chuột Phải để khép kín ô.\nNhấn phím Z (hoặc Backspace) để hoàn tác nét vẽ lỗi. Nhấn C để xóa toàn bộ.\nKhi vẽ xong toàn bộ các bãi đỗ, bấm phím SPACE (khoảng trắng) để lưu lại.", fg="#7f8c8d", justify="center")
        lbl_info.pack(side='bottom', pady=20)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.avi *.mkv *.mov")])
        if file_path:
            self.video_path.set(file_path)
            # Reset chỗ chọn thời gian
            self.start_time.set(0.0)
            self.end_time.set(0.0)
            self.full_video.set(True)
            self.is_webcam.set(False)
            try:
                self.btn_webcam.config(bg="#f39c12", text="Sử Dụng Webcam")
            except:
                pass
            self.toggle_entries()
            self.polygons = [] # Reset vùng vẽ

    def choose_webcam(self):
        top = tk.Toplevel(self.root)
        top.title("Chọn Camera")
        top.geometry("300x200")
        top.transient(self.root)
        top.grab_set()

        lbl_status = tk.Label(top, text="Đang tìm các camera khả dụng...")
        lbl_status.pack(pady=10)
        top.update()

        available_cameras = []
        for i in range(5):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
                
        for widget in top.winfo_children():
            widget.destroy()
            
        def on_close():
            self.is_webcam.set(False)
            self.video_path.set("")
            self.chk_full.config(state='normal')
            self.btn_webcam.config(bg="#f39c12", text="Sử Dụng Webcam")
            top.destroy()
            
        if not available_cameras:
            tk.Label(top, text="Không tìm thấy Camera nào!").pack(pady=20)
            tk.Button(top, text="Đóng", command=on_close).pack()
            top.protocol("WM_DELETE_WINDOW", on_close)
            return

        tk.Label(top, text="Vui lòng chọn Camera:").pack(pady=10)
        
        selected_cam = tk.IntVar(value=available_cameras[0])
        for cam in available_cameras:
            tk.Radiobutton(top, text=f"Camera {cam}", variable=selected_cam, value=cam).pack(anchor='w', padx=100)
            
        def on_select():
            self.webcam_index = selected_cam.get()
            self.video_path.set(f"Camera {self.webcam_index} (Webcam)")
            self.full_video.set(True)
            self.chk_full.config(state='disabled')
            self.toggle_entries()
            self.polygons = []
            self.btn_webcam.config(bg="#27ae60", text=f"Đang Mở Cam {self.webcam_index}")
            top.destroy()
            
        tk.Button(top, text="Xác nhận", command=on_select, bg="#3498db", fg="white").pack(pady=15)
        top.protocol("WM_DELETE_WINDOW", on_close)

    def toggle_webcam_button(self):
        new_state = not self.is_webcam.get()
        self.is_webcam.set(new_state)
        if new_state:
            self.choose_webcam()
        else:
            self.video_path.set("")
            self.chk_full.config(state='normal')
            self.btn_webcam.config(bg="#f39c12", text="Sử Dụng Webcam")
            
    def toggle_entries(self):
        if self.full_video.get():
            self.entry_start.config(state='disabled')
            self.entry_end.config(state='disabled')
        else:
            self.entry_start.config(state='normal')
            self.entry_end.config(state='normal')

    def get_start_end(self, cap):
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if fps <= 0: fps = 30
        duration = total_frames / fps
        
        if self.full_video.get():
            return 0.0, duration
        else:
            start = self.start_time.get()
            end = self.end_time.get()
            if end <= 0 or end > duration:
                end = duration
            return start, end

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Chấm một điểm mới
            self.current_polygon.append((x, y))
        elif event == cv2.EVENT_RBUTTONDOWN:
            # Khép kín một mảng điểm thành đa giác
            if len(self.current_polygon) > 2:
                self.polygons.append(self.current_polygon.copy())
                self.current_polygon = []

    def draw_regions(self):
        if not self.video_path.get():
            messagebox.showerror("Lỗi", "Vui lòng chọn video trước bằng nút Duyệt File hoặc chọn Webcam!")
            return

        src = self.webcam_index if self.is_webcam.get() else self.video_path.get()
        cap = cv2.VideoCapture(src)
        if not cap.isOpened():
            messagebox.showerror("Lỗi", "Không thể mở video hoặc Webcam!")
            return

        if not self.is_webcam.get():
            start_sec, _ = self.get_start_end(cap)
            cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
            
        ret, frame = cap.read()
        if not ret:
            messagebox.showerror("Lỗi", "Không thể đọc khung hình từ video tại mốc thời gian bắt đầu. Thử chọn thời điểm khác.")
            cap.release()
            return
            
        temp_frame = frame.copy()
        
        cv2.namedWindow('Draw Parking Regions', cv2.WINDOW_NORMAL)
        # Giữ tỉ lệ hình ảnh vừa màn hình nếu video quá to
        cv2.resizeWindow('Draw Parking Regions', frame.shape[1], frame.shape[0])
        cv2.setMouseCallback('Draw Parking Regions', self.mouse_callback)

        while True:
            display = temp_frame.copy()
            
            # Vẽ các vùng đã hoàn thành
            for poly in self.polygons:
                cv2.polylines(display, [np.array(poly)], True, (255, 0, 0), 2)
                # Đánh dấu id đa giác
                cx = int(sum(p[0] for p in poly) / len(poly))
                cy = int(sum(p[1] for p in poly) / len(poly))
                cv2.circle(display, (cx, cy), 3, (255, 0, 0), -1)
                
            # Vẽ vùng đang vẽ (dùng màu đỏ chờ)
            if len(self.current_polygon) > 0:
                for i in range(len(self.current_polygon)):
                    cv2.circle(display, self.current_polygon[i], 3, (0, 0, 255), -1)
                    if i > 0:
                        cv2.line(display, self.current_polygon[i-1], self.current_polygon[i], (0, 0, 255), 2)

            cv2.imshow('Draw Parking Regions', display)
            key = cv2.waitKey(20) & 0xFF
            
            # Phím tắt
            if key == ord(' ') or key == 13 or key == ord('q'): # Space, Enter, q
                break
            elif key == ord('c'): # Bấm C để xóa trắng vẽ lại từ đầu
                self.polygons.clear()
                self.current_polygon.clear()
            elif key == ord('z') or key == 8: # z or Backspace
                if len(self.current_polygon) > 0:
                    self.current_polygon.pop()
                elif len(self.polygons) > 0:
                    self.polygons.pop()
                
        cv2.destroyWindow('Draw Parking Regions')
        cap.release()

    def show_checkin_popup(self):
        if not self.detection_active or not self.is_webcam.get():
            messagebox.showinfo("Check In", "Chức năng Check In chỉ hoạt động khi đang nhận diện bằng Webcam.")
            return
        
        status = self.last_poly_status
        if not status:
            messagebox.showinfo("Check In", "Chưa có dữ liệu nhận diện. Vui lòng đợi...")
            return
        
        top = tk.Toplevel(self.root)
        top.title("Check In - Tình trạng Bãi đỗ")
        top.geometry("420x500")
        top.transient(self.root)
        top.configure(bg="#ecf0f1")
        
        # Header
        tk.Label(top, text="TÌNH TRẠNG BÃI ĐỖ XE", font=("Arial", 14, "bold"), fg="#2c3e50", bg="#ecf0f1").pack(pady=(15, 5))
        
        empty_slots = [i + 1 for i, occupied in enumerate(status) if not occupied]
        occupied_slots = [i + 1 for i, occupied in enumerate(status) if occupied]
        total = len(status)
        
        summary_text = f"Trống: {len(empty_slots)}/{total}   |   Đã đỗ: {len(occupied_slots)}/{total}"
        tk.Label(top, text=summary_text, font=("Arial", 11), fg="#34495e", bg="#ecf0f1").pack(pady=5)
        
        frame_list = tk.Frame(top, bg="#ecf0f1")
        frame_list.pack(fill='both', expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(frame_list, bg="#ecf0f1", highlightthickness=0)
        scrollbar = tk.Scrollbar(frame_list, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="#ecf0f1")
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        for idx in range(total):
            slot_num = idx + 1
            is_occ = status[idx]
            
            row_frame = tk.Frame(scroll_frame, bg="white", bd=1, relief='groove')
            row_frame.pack(fill='x', pady=2, padx=5)
            
            if is_occ:
                icon = "🔴"
                text = f"  Ô {slot_num}:  Đã có xe"
                color = "#e74c3c"
            else:
                icon = "🟢"
                text = f"  Ô {slot_num}:  Còn trống"
                color = "#27ae60"
            
            tk.Label(row_frame, text=icon, font=("Arial", 12), bg="white").pack(side='left', padx=(10, 0))
            tk.Label(row_frame, text=text, font=("Arial", 11, "bold"), fg=color, bg="white", anchor='w').pack(side='left', fill='x', expand=True, pady=8)
        
        # Thông báo hướng dẫn
        msg_frame = tk.Frame(top, bg="#ecf0f1")
        msg_frame.pack(fill='x', padx=20, pady=(0, 15))
        
        if empty_slots:
            guide_text = f"✅ Vui lòng tiến vào Ô {empty_slots[0]} để đỗ xe."
            if len(empty_slots) > 1:
                other = ", ".join(str(s) for s in empty_slots[1:])
                guide_text += f"\nCác ô trống khác: {other}"
            guide_color = "#27ae60"
        else:
            guide_text = "⛔ Bãi đỗ đã đầy. Vui lòng quay lại sau."
            guide_color = "#e74c3c"
        
        tk.Label(msg_frame, text=guide_text, font=("Arial", 11, "bold"), fg=guide_color, bg="#ecf0f1", justify='center', wraplength=380).pack(pady=5)
        
        def close_and_refocus():
            top.destroy()
            try:
                cv2.setWindowProperty("Video Detection", cv2.WND_PROP_TOPMOST, 1)
                cv2.setWindowProperty("Video Detection", cv2.WND_PROP_TOPMOST, 0)
            except:
                pass
        
        tk.Button(top, text="Đóng", command=close_and_refocus, bg="#3498db", fg="white", font=("Arial", 10, "bold"), width=12).pack(pady=(0, 15))
        top.protocol("WM_DELETE_WINDOW", close_and_refocus)

    def run_detection(self):
        if not self.video_path.get():
            messagebox.showerror("Lỗi", "Vui lòng chọn video trước!")
            return
            
        if not self.polygons:
            res = messagebox.askyesno("Cảnh báo", "Bạn chưa khoanh vùng nhận diện bãi đỗ nào!\nVideo sẽ chạy nhưng không hiện chỗ trống đậu xe. Bạn có muốn tiếp tục chạy luôn không?")
            if not res:
                return

        try:
            # Load mô hình YOLO 
            model = YOLO('yolov8n.pt')
        except Exception as e:
            messagebox.showerror("Lỗi YOLO Model", f"Gặp sự cố khi khởi tạo model: {e}")
            return
        
        src = self.webcam_index if self.is_webcam.get() else self.video_path.get()
        cap = cv2.VideoCapture(src)
        
        if not self.is_webcam.get():
            start_sec, end_sec = self.get_start_end(cap)
            cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
        else:
            start_sec, end_sec = 0.0, float('inf')
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        delay = int(1000 / fps) if fps > 0 else 30
        
        # Kích hoạt trạng thái detection và nút Check In (chỉ webcam)
        self.detection_active = True
        if self.is_webcam.get():
            self.btn_checkin.config(state='normal', bg="#27ae60")
            # Fullscreen cho webcam
            cv2.namedWindow("Video Detection", cv2.WND_PROP_FULLSCREEN)
            cv2.setWindowProperty("Video Detection", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        
        while cap.isOpened():
            if not self.is_webcam.get():
                current_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                if current_msec > end_sec * 1000:
                    break
                
            start_time_proc = time.time()
            
            ret, frame = cap.read()
            if not ret:
                break
                
            # Dự đoán (Classes: 2 là car, 5 là bus, 7 là truck)
            results = model.predict(frame, stream=True, verbose=False, classes=[2, 5, 7])
            
            car_centers = []
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0]
                    
                    # Chúng ta ước tính khối tâm của chiếc xe (cái chấm ấy)
                    # Kéo dịch nhẹ tâm xuống dưới do camera thường bắt chéo
                    cx = int((x1 + x2) / 2)
                    cy = int(y2 - (y2 - y1) * 0.3)
                    
                    car_centers.append((cx, cy))
                    
                    # Vẽ bounding box nhẹ màu xám lên các xe
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (200, 200, 200), 1)
                    cv2.circle(frame, (cx, cy), 4, (0, 255, 255), -1)
            
            # Xử lý vùng đỗ kiểm tra có nằm đè lên đa giác không
            occupied_count = 0
            current_status = []
            for idx, poly in enumerate(self.polygons):
                poly_np = np.array(poly, np.int32)
                is_occupied = False
                for cx, cy in car_centers:
                    if cv2.pointPolygonTest(poly_np, (cx, cy), False) >= 0:
                        is_occupied = True
                        break
                
                current_status.append(is_occupied)
                
                # Tính tâm đa giác để đánh số
                pcx = int(sum(p[0] for p in poly) / len(poly))
                pcy = int(sum(p[1] for p in poly) / len(poly))
                
                if is_occupied:
                    # Màu đỏ nếu bị chiếm 
                    cv2.polylines(frame, [poly_np], True, (0, 0, 255), 3)
                    occupied_count += 1
                else:
                    # Màu xanh nếu trống
                    cv2.polylines(frame, [poly_np], True, (0, 255, 0), 3)
                
                # Đánh số ô đỗ lên video
                cv2.putText(frame, str(idx + 1), (pcx - 8, pcy + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            self.last_poly_status = current_status
            
            cv2.putText(frame, "'Q' stop | 'I' Check In", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, f"Trang thai: {occupied_count}/{len(self.polygons)} cho", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
                
            cv2.imshow("Video Detection", frame)
            
            elapsed = int((time.time() - start_time_proc) * 1000)
            wait_time = max(1, delay - elapsed)
            
            # Điều khiển tốc độ chạy video tương ứng với FPS thực (normal speed) tại không muốn delay
            key = cv2.waitKey(wait_time) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('i') and self.is_webcam.get():
                self.show_checkin_popup()
            
            # Giữ cho Tkinter vẫn phản hồi (nút Check In, giao diện chính)
            try:
                self.root.update()
            except:
                pass
                
        cap.release()
        cv2.destroyWindow("Video Detection")
        
        # Reset trạng thái
        self.detection_active = False
        self.btn_checkin.config(state='disabled', bg="#95a5a6")
        self.last_poly_status = []

if __name__ == "__main__":
    root = tk.Tk()
    app = ParkingApp(root)
    root.mainloop()
