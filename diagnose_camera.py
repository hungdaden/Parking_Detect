#!/usr/bin/env python3
"""
diagnose_camera.py — Chẩn đoán toàn diện Camera trên macOS
Chạy bằng lệnh:
    source venv/bin/activate
    python diagnose_camera.py
"""

import sys
import time
import subprocess
import numpy as np
import cv2

print("=" * 60)
print("  🔍 CHẨN ĐOÁN CAMERA TRÊN MACOS")
print("=" * 60)
print(f"Python: {sys.version}")
print(f"OpenCV: {cv2.__version__}")
print(f"Platform: {sys.platform}")

# 1. Quét phần cứng bằng system_profiler
print("\n--- 1. Quét phần cứng Camera (system_profiler) ---")
try:
    cmd = ['system_profiler', 'SPCameraDataType', '-detailLevel', 'mini']
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=3)
    if out.strip():
        for line in out.splitlines():
            if line.strip():
                print(f"  {line.strip()}")
    else:
        print("  ⚠️ system_profiler không trả về camera nào.")
except Exception as e:
    print(f"  Lỗi system_profiler: {e}")

# 2. Thử từng Camera Index với các backend khác nhau
print("\n--- 2. Quét các Camera Index trong OpenCV ---")
found_working_cam = None

for idx in range(4):
    print(f"\n👉 Kiểm tra Camera Index {idx}:")
    
    # Thử với backend mặc định (CAP_ANY)
    cap = cv2.VideoCapture(idx)
    opened = cap.isOpened()
    backend_name = cap.getBackendName() if opened else "None"
    print(f"   [Default / {backend_name}] isOpened: {opened}")
    
    if opened:
        # Đọc thử một vài frame
        bright_values = []
        for f_i in range(10):
            ret, frame = cap.read()
            if ret and frame is not None:
                mean_b = float(np.mean(frame))
                bright_values.append(mean_b)
            time.sleep(0.05)
        
        if bright_values:
            max_b = max(bright_values)
            avg_b = sum(bright_values) / len(bright_values)
            h, w = frame.shape[:2]
            print(f"   Kích thước: {w}x{h}, Độ sáng trung bình: {avg_b:.1f}, Cao nhất: {max_b:.1f}")
            if max_b > 5.0:
                print(f"   🎉 CAMERA NÀY HOẠT ĐỘNG TỐT! (Hình ảnh rõ ràng)")
                found_working_cam = idx
            else:
                print(f"   ⚠️ Frame toàn màu đen (độ sáng: {avg_b:.2f})")
        else:
            print(f"   ❌ Không đọc được frame nào (ret=False)")
        cap.release()

    # Thử thêm với CAP_AVFOUNDATION nếu default fail
    if not opened or (bright_values and max(bright_values) <= 5.0):
        cap_av = cv2.VideoCapture(idx, cv2.CAP_AVFOUNDATION)
        opened_av = cap_av.isOpened()
        print(f"   [CAP_AVFOUNDATION] isOpened: {opened_av}")
        if opened_av:
            bright_av = []
            for f_i in range(10):
                ret, frame = cap_av.read()
                if ret and frame is not None:
                    bright_av.append(float(np.mean(frame)))
                time.sleep(0.05)
            if bright_av:
                max_av = max(bright_av)
                print(f"   [CAP_AVFOUNDATION] Độ sáng cao nhất: {max_av:.1f}")
                if max_av > 5.0 and found_working_cam is None:
                    print(f"   🎉 CAP_AVFOUNDATION HOẠT ĐỘNG TỐT với index {idx}!")
                    found_working_cam = idx
            cap_av.release()

print("\n" + "=" * 60)
if found_working_cam is not None:
    print(f"  ✅ Camera hoạt động tốt nhất là: INDEX {found_working_cam}")
    print(f"  Vui lòng chọn Camera này trong ứng dụng!")
else:
    print("  ❌ TẤT CẢ CAMERA ĐỀU TRẢ VỀ KHUNG HÌNH ĐEN.")
    print("  Điều này có nghĩa là:")
    print("  1. Quyền Camera của tiến trình này chưa được hệ điều hành macOS cấp phát.")
    print("  2. Bạn cần cấp quyền cho Terminal/IDE và khởi động lại.")
print("=" * 60)

