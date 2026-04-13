import cv2
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox
from ultralytics import YOLO
import time

class ParkingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ứng dụng Nhận diện Bãi đỗ xe")
        self.root.geometry("650x450")
        
        # status agru
        self.video_path = tk.StringVar()
        self.start_time = tk.DoubleVar(value=0.0)
        self.end_time = tk.DoubleVar(value=0.0)
        self.full_video = tk.BooleanVar(value=True)
        
        self.polygons = [] # ve
        self.current_polygon = [] # dang ve do
        
        # UI
        self.setup_ui()
        
    def setup_ui(self):
        # Tiêu đề đây
        lbl_title = tk.Label(self.root, text="HỆ THỐNG NHẬN DIỆN BÃI ĐỖ XE", font=("Arial", 16, "bold"), fg="#2c3e50")
        lbl_title.pack(pady=20)
        
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
        frame_actions.pack(pady=20)
        
        tk.Button(frame_actions, text="1. Khoanh Vùng Đỗ Xe", width=25, height=2, bg="#3498db", fg="white", font=("Arial", 11, "bold"), command=self.draw_regions).grid(row=0, column=0, padx=15)
        tk.Button(frame_actions, text="2. Bắt Đầu Nhận Diện", width=25, height=2, bg="#e74c3c", fg="white", font=("Arial", 11, "bold"), command=self.run_detection).grid(row=0, column=1, padx=15)
        
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
            self.toggle_entries()
            self.polygons = [] # Reset vùng vẽ
            
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
            messagebox.showerror("Lỗi", "Vui lòng chọn video trước bằng nút Duyệt File!")
            return

        cap = cv2.VideoCapture(self.video_path.get())
        if not cap.isOpened():
            messagebox.showerror("Lỗi", "Không thể mở video!")
            return

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
            model = YOLO('yolov8m.pt') 
        except Exception as e:
            messagebox.showerror("Lỗi YOLO Model", f"Gặp sự cố khi khởi tạo model: {e}")
            return
        
        cap = cv2.VideoCapture(self.video_path.get())
        start_sec, end_sec = self.get_start_end(cap)
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        delay = int(1000 / fps) if fps > 0 else 30
        
        cap.set(cv2.CAP_PROP_POS_MSEC, start_sec * 1000)
        
        while cap.isOpened():
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
                    
                    # Chúng ta ước tính khối tâm của chiếc xe. 
                    # Kéo dịch nhẹ tâm xuống dưới do camera thường bắt xiên
                    cx = int((x1 + x2) / 2)
                    cy = int(y2 - (y2 - y1) * 0.3)
                    
                    car_centers.append((cx, cy))
                    
                    # Vẽ bounding box nhẹ màu xám lên các xe
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (200, 200, 200), 1)
                    cv2.circle(frame, (cx, cy), 4, (0, 255, 255), -1)
            
            # Xử lý vùng đỗ kiểm tra có nằm đè lên đa giác không
            occupied_count = 0
            for poly in self.polygons:
                poly_np = np.array(poly, np.int32)
                is_occupied = False
                for cx, cy in car_centers:
                    if cv2.pointPolygonTest(poly_np, (cx, cy), False) >= 0:
                        is_occupied = True
                        break
                
                if is_occupied:
                    # Màu đỏ nếu bị chiếm 
                    cv2.polylines(frame, [poly_np], True, (0, 0, 255), 3)
                    occupied_count += 1
                else:
                    # Màu xanh nếu trống
                    cv2.polylines(frame, [poly_np], True, (0, 255, 0), 3)
            
            # Thông tin UI trên ảnh
            cv2.putText(frame, "'Q' for stop", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, f"Trang thai: {occupied_count}/{len(self.polygons)} cho", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
                
            cv2.imshow("Video Detection", frame)
            
            elapsed = int((time.time() - start_time_proc) * 1000)
            wait_time = max(1, delay - elapsed)
            
            # Điều khiển tốc độ chạy video tương ứng với FPS thực (normal speed)
            if cv2.waitKey(wait_time) & 0xFF == ord('q'):
                break
                
        cap.release()
        cv2.destroyWindow("Video Detection")

if __name__ == "__main__":
    root = tk.Tk()
    app = ParkingApp(root)
    root.mainloop()
