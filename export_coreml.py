"""
Script chuyển đổi model YOLOv8 (.pt) sang định dạng CoreML (.mlpackage)
để chạy tối ưu trên Apple Neural Engine (ANE) của chip Apple Silicon (M1/M2/M3/M4).

Cách sử dụng:
    python export_coreml.py                  # Chuyển đổi yolov8m.pt (mặc định)
    python export_coreml.py yolov8s.pt       # Chuyển đổi model chỉ định
    python export_coreml.py --all            # Chuyển đổi tất cả model .pt có sẵn
"""
import os
import sys
import glob
from typing import Optional


def export_model(pt_path: str) -> Optional[str]:
    """Chuyển đổi một model .pt sang CoreML FP16 với NMS tích hợp."""
    if not os.path.exists(pt_path):
        print(f"[LỖI] Không tìm thấy file model: {pt_path}")
        return None

    try:
        from ultralytics import YOLO

        print(f"\n{'='*60}")
        print(f"  Đang chuyển đổi: {pt_path}")
        print(f"{'='*60}")

        model = YOLO(pt_path)
        output_path = model.export(
            format="coreml",
            half=True,       # FP16 để tối ưu ANE
            nms=True,        # Tích hợp NMS vào model
            imgsz=640,
        )

        print(f"[OK] Chuyển đổi thành công: {output_path}")
        return output_path

    except Exception as e:
        print(f"[LỖI] Chuyển đổi thất bại cho {pt_path}: {e}")
        return None


def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Chuyển đổi tất cả model .pt
        pt_files = sorted(glob.glob(os.path.join(project_dir, "yolov8*.pt")))
        if not pt_files:
            print("[LỖI] Không tìm thấy file yolov8*.pt nào trong thư mục dự án.")
            return 1

        print(f"Tìm thấy {len(pt_files)} model: {[os.path.basename(f) for f in pt_files]}")
        results = []
        for pt_file in pt_files:
            result = export_model(pt_file)
            results.append((os.path.basename(pt_file), result))

        print(f"\n{'='*60}")
        print("  KẾT QUẢ CHUYỂN ĐỔI")
        print(f"{'='*60}")
        for name, result in results:
            status = "✅ OK" if result else "❌ Lỗi"
            print(f"  {status}  {name}")
        return 0

    elif len(sys.argv) > 1:
        # Chuyển đổi model chỉ định
        pt_path = sys.argv[1]
        if not os.path.isabs(pt_path):
            pt_path = os.path.join(project_dir, pt_path)
        result = export_model(pt_path)
        return 0 if result else 1

    else:
        # Mặc định: chuyển đổi yolov8m.pt (model đang dùng trong dự án)
        default_model = os.path.join(project_dir, "yolov8m.pt")
        result = export_model(default_model)
        return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
