#!/bin/bash
# =============================================================
#  Parking Detect - Cài đặt tự động trên macOS (Apple Silicon)
# =============================================================
set -e

echo "============================================================="
echo "  PARKING DETECT - CÀI ĐẶT MÔI TRƯỜNG macOS"
echo "============================================================="

# Kiểm tra hệ điều hành
if [[ "$(uname)" != "Darwin" ]]; then
    echo "[LỖI] Script này chỉ dành cho macOS."
    exit 1
fi

ARCH=$(uname -m)
echo "[INFO] Kiến trúc CPU: $ARCH"

# Kiểm tra Python
PYTHON_CMD=""
for cmd in python3.11 python3.10 python3; do
    if command -v "$cmd" &> /dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    echo "[LỖI] Không tìm thấy Python 3. Vui lòng cài đặt Python 3.10+ từ https://www.python.org/"
    exit 1
fi

PY_VERSION=$($PYTHON_CMD --version 2>&1)
echo "[INFO] Sử dụng: $PY_VERSION ($PYTHON_CMD)"

# Tạo môi trường ảo
VENV_DIR="venv"
if [[ ! -d "$VENV_DIR" ]]; then
    echo ""
    echo "[BƯỚC 1/4] Đang tạo môi trường ảo Python..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo "[OK] Đã tạo môi trường ảo: $VENV_DIR/"
else
    echo ""
    echo "[BƯỚC 1/4] Môi trường ảo đã tồn tại: $VENV_DIR/"
fi

# Kích hoạt venv
source "$VENV_DIR/bin/activate"

# Nâng cấp pip
echo ""
echo "[BƯỚC 2/4] Đang nâng cấp pip..."
pip install --upgrade pip

# Cài đặt PyTorch cho Apple Silicon
echo ""
echo "[BƯỚC 3/4] Đang cài đặt PyTorch và các thư viện cần thiết..."
pip install torch torchvision

# Cài đặt các thư viện dự án (bỏ qua pygrabber trên macOS nhờ platform marker)
pip install -r requirements.txt

echo "[OK] Đã cài đặt tất cả thư viện thành công."

# Chuyển đổi model sang CoreML (tùy chọn)
echo ""
echo "[BƯỚC 4/4] Chuyển đổi model YOLO sang CoreML cho Apple Neural Engine..."
if [[ -f "yolov8m.pt" ]]; then
    echo "Đang chuyển đổi yolov8m.pt -> CoreML (quá trình này mất 1-3 phút)..."
    python export_coreml.py yolov8m.pt || echo "[CẢNH BÁO] Chuyển đổi CoreML thất bại. Ứng dụng vẫn chạy được với file .pt gốc."
else
    echo "[BỎ QUA] Không tìm thấy yolov8m.pt"
fi

echo ""
echo "============================================================="
echo "  CÀI ĐẶT HOÀN TẤT!"
echo "============================================================="
echo ""
echo "Để chạy ứng dụng:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "Lưu ý: Lần đầu chạy, macOS sẽ hỏi quyền truy cập Camera."
echo "Hãy chọn 'Allow' để ứng dụng có thể kết nối webcam."
echo ""
