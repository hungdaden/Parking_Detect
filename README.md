### **English below**

# Phần Mềm Quản Lý Bãi Đỗ Xe (Parking Detect)

Phần mềm hỗ trợ nhận diện và quản lý chỗ trống trong bãi đỗ xe tự động sử dụng mô hình AI (YOLOv8).

## Hướng dẫn Cài đặt và Sử dụng

### 1. Dành cho Người dùng (Sử dụng trực tiếp file EXE)
Phần mềm đã được đóng gói thành file thực thi `.exe`, bạn có thể chạy ngay trên hệ điều hành Windows mà không cần cài đặt Python hay các thư viện phức tạp.

**Các bước thực hiện:**
1. Mở thư mục chứa bản build của ứng dụng (thường nằm trong thư mục `dist\ParkingDetect_App`).
2. Tìm và chạy trực tiếp file **`Parking Detect.exe`**.
3. Ứng dụng sẽ tự động nạp mô hình AI và cơ sở dữ liệu để sẵn sàng hoạt động.

*(Mẹo: Bạn có thể click chuột phải vào file `Parking Detect.exe` -> chọn **Send to** -> **Desktop (create shortcut)** để tạo lối tắt nhanh trên màn hình chính, hoặc sử dụng shortcut đã được tạo sẵn nếu có).*

---

### 2. Dành cho Nhà phát triển (Cài đặt từ mã nguồn)
Nếu bạn muốn chạy ứng dụng từ mã nguồn (source code) để chỉnh sửa, phát triển thêm hoặc tự build lại file `.exe`, hãy làm theo các bước sau:

**Yêu cầu hệ thống:**
- Hệ điều hành: Windows
- Python 3.8 trở lên (khuyến nghị Python 3.10 hoặc 3.11)

**Bước 1: Cài đặt thư viện**
Mở Terminal (Command Prompt hoặc PowerShell) tại thư mục mã nguồn và chạy lệnh sau để cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```

*(Lưu ý: Nếu máy tính có Card đồ họa rời (NVIDIA), bạn có thể cài đặt thêm phiên bản PyTorch hỗ trợ CUDA để tăng đáng kể tốc độ nhận diện của AI).*

**Bước 2: Chạy ứng dụng**
Để chạy ứng dụng trực tiếp từ mã nguồn:
```bash
python main.py
```

**Bước 3: Đóng gói ứng dụng ra file .exe**
Dự án đã có sẵn script tự động hóa quá trình build. Để tạo file `.exe` mới nhất, chỉ cần chạy lệnh:
```bash
python build_exe.py
```
Script này sẽ tự động:
- Dọn dẹp các file cache của bản build cũ (thư mục `build` và `dist`).
- Đóng gói mã nguồn cùng các file dữ liệu (`yolov8m.pt`, thư mục `presets`, `icon.ico`).
- Xuất file `.exe` hoàn chỉnh tại `dist\ParkingDetect_App`.
- Tự động tạo một lối tắt (Shortcut) ra màn hình Desktop cho bạn.

---

### Lưu ý khi sử dụng
- Nếu gặp lỗi "File in use" hoặc "Permission denied" khi đang build app, hãy đảm bảo rằng bạn đã tắt hoàn toàn ứng dụng (không còn chạy ngầm) trước khi chạy lệnh build.
- Thông tin về các cấu hình vùng đỗ xe được lưu tự động trong thư mục `presets`, không nên xóa thư mục này nếu bạn muốn giữ lại các cấu hình đã lưu.

---

# Parking Management Software (Parking Detect)

The software supports automatically detecting and managing empty parking spaces using an AI model (YOLOv8).

## Installation and Usage Guide

### 1. For Users (Directly using the EXE file)
The software has been packaged into an executable `.exe` file. You can run it directly on the Windows operating system without installing Python or complex libraries.

**Steps:**
1. Open the folder containing the application build (usually located in the `dist\ParkingDetect_App` folder).
2. Find and run the **`Parking Detect.exe`** file directly.
3. The application will automatically load the AI model and database to be ready for operation.

*(Tip: You can right-click the `Parking Detect.exe` file -> select **Send to** -> **Desktop (create shortcut)** to create a quick shortcut on the main screen, or use the pre-created shortcut if available).*

---

### 2. For Developers (Installing from source code)
If you want to run the application from the source code to edit, develop further, or rebuild the `.exe` file yourself, follow these steps:

**System Requirements:**
- Operating System: Windows
- Python 3.8 or higher (Python 3.10 or 3.11 is recommended)

**Step 1: Install libraries**
Open the Terminal (Command Prompt or PowerShell) at the source code folder and run the following command to install the required libraries:
```bash
pip install -r requirements.txt
```

*(Note: If your computer has a dedicated graphics card (NVIDIA), you can install the PyTorch version that supports CUDA to significantly increase the AI's detection speed).*

**Step 2: Run the application**
To run the application directly from the source code:
```bash
python main.py
```

**Step 3: Package the application into an .exe file**
The project already has a script to automate the build process. To create the latest `.exe` file, simply run the command:
```bash
python build_exe.py
```
This script will automatically:
- Clean up cache files from the previous build (`build` and `dist` folders).
- Package the source code with data files (`yolov8m.pt`, `presets` folder, `icon.ico`).
- Export the complete `.exe` file at `dist\ParkingDetect_App`.
- Automatically create a Shortcut on the Desktop for you.

---

### Usage Notes
- If you encounter a "File in use" or "Permission denied" error while building the app, make sure you have completely closed the application (no longer running in the background) before running the build command.
- Information about parking area configurations is automatically saved in the `presets` folder. You should not delete this folder if you want to keep the saved configurations.
