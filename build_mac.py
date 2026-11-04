#!/usr/bin/env python3
"""
build_mac.py — Script đóng gói Parking Detect thành macOS App Bundle (.app)

Sử dụng:
    source venv/bin/activate
    python build_mac.py

Kết quả:
    dist/Parking Detect.app   — Kéo thả vào /Applications để cài đặt
"""

import subprocess
import sys
import os
import shutil


def check_pyinstaller():
    """Kiểm tra và cài đặt PyInstaller nếu chưa có."""
    try:
        import PyInstaller
        print(f"  ✅ PyInstaller {PyInstaller.__version__} đã được cài đặt")
        return True
    except ImportError:
        print("  ⚠️  PyInstaller chưa được cài đặt. Đang cài...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ❌ Lỗi cài PyInstaller: {result.stderr}")
            return False
        print("  ✅ Đã cài đặt PyInstaller thành công")
        return True


def convert_ico_to_icns(project_dir):
    """Chuyển icon.ico sang icon.icns nếu có sips (macOS built-in)."""
    ico_path = os.path.join(project_dir, "icon.ico")
    icns_path = os.path.join(project_dir, "icon.icns")

    if os.path.exists(icns_path):
        print(f"  ✅ icon.icns đã tồn tại")
        return icns_path

    if not os.path.exists(ico_path):
        print("  ⚠️  Không tìm thấy icon.ico — app sẽ dùng icon mặc định")
        return None

    print("  🔄 Đang chuyển icon.ico → icon.icns...")
    try:
        # Tạo iconset tạm
        iconset_dir = os.path.join(project_dir, "icon.iconset")
        os.makedirs(iconset_dir, exist_ok=True)

        # Dùng sips để resize các kích thước cần thiết
        sizes = [16, 32, 64, 128, 256, 512]
        for size in sizes:
            out_file = os.path.join(iconset_dir, f"icon_{size}x{size}.png")
            subprocess.run(
                ["sips", "-z", str(size), str(size), ico_path,
                 "--out", out_file],
                capture_output=True
            )
            # Retina @2x
            if size <= 256:
                out_file_2x = os.path.join(
                    iconset_dir, f"icon_{size}x{size}@2x.png"
                )
                retina_size = size * 2
                subprocess.run(
                    ["sips", "-z", str(retina_size), str(retina_size),
                     ico_path, "--out", out_file_2x],
                    capture_output=True
                )

        # Dùng iconutil để tạo .icns
        result = subprocess.run(
            ["iconutil", "-c", "icns", iconset_dir, "-o", icns_path],
            capture_output=True, text=True
        )

        # Dọn dẹp iconset tạm
        shutil.rmtree(iconset_dir, ignore_errors=True)

        if result.returncode == 0 and os.path.exists(icns_path):
            print(f"  ✅ Đã tạo icon.icns thành công")
            return icns_path
        else:
            print(f"  ⚠️  Không thể tạo icon.icns: {result.stderr}")
            return None

    except Exception as e:
        print(f"  ⚠️  Lỗi chuyển đổi icon: {e}")
        shutil.rmtree(
            os.path.join(project_dir, "icon.iconset"), ignore_errors=True
        )
        return None


def clean_build(project_dir):
    """Dọn dẹp thư mục build/dist cũ."""
    for folder in ["build", "dist"]:
        path = os.path.join(project_dir, folder)
        if os.path.exists(path):
            print(f"  🗑  Đang xóa {folder}/...")
            shutil.rmtree(path, ignore_errors=True)


def build_app(project_dir):
    """Chạy PyInstaller với spec file macOS."""
    spec_file = os.path.join(project_dir, "parking_detect_mac.spec")

    if not os.path.exists(spec_file):
        print(f"  ❌ Không tìm thấy file: {spec_file}")
        return False

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        spec_file,
    ]

    print(f"\n  🔨 Đang build...\n")
    print(f"  Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=project_dir)

    return result.returncode == 0


def verify_app(project_dir):
    """Kiểm tra kết quả build."""
    app_path = os.path.join(project_dir, "dist", "Parking Detect.app")

    if not os.path.exists(app_path):
        print(f"\n  ❌ Không tìm thấy app tại: {app_path}")
        return False

    # Kiểm tra kích thước
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(app_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)

    size_mb = total_size / (1024 * 1024)
    print(f"\n  ✅ App đã được tạo thành công!")
    print(f"  📦 Vị trí: {app_path}")
    print(f"  📏 Kích thước: {size_mb:.1f} MB")

    # Kiểm tra Info.plist có NSCameraUsageDescription
    info_plist = os.path.join(app_path, "Contents", "Info.plist")
    if os.path.exists(info_plist):
        with open(info_plist, "r") as f:
            content = f.read()
            if "NSCameraUsageDescription" in content:
                print("  🔐 NSCameraUsageDescription: ✅ Có (quyền Camera)")
            else:
                print("  ⚠️  NSCameraUsageDescription: ❌ THIẾU!")
    else:
        print(f"  ⚠️  Không tìm thấy Info.plist")

    return True


def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 60)
    print("  🚗 PARKING DETECT — macOS App Builder")
    print("=" * 60)

    # Bước 1: Kiểm tra PyInstaller
    print("\n📋 Bước 1: Kiểm tra PyInstaller...")
    if not check_pyinstaller():
        return 1

    # Bước 2: Chuyển đổi icon
    print("\n📋 Bước 2: Chuẩn bị icon macOS...")
    convert_ico_to_icns(project_dir)

    # Bước 3: Dọn dẹp build cũ
    print("\n📋 Bước 3: Dọn dẹp build cũ...")
    clean_build(project_dir)

    # Bước 4: Build app
    print("\n📋 Bước 4: Build macOS App Bundle...")
    if not build_app(project_dir):
        print("\n  ❌ Build thất bại!")
        return 1

    # Bước 5: Kiểm tra kết quả
    print("\n📋 Bước 5: Kiểm tra kết quả...")
    if not verify_app(project_dir):
        return 1

    print("\n" + "=" * 60)
    print("  ✅ HOÀN TẤT!")
    print("  Bạn có thể kéo thả 'Parking Detect.app' vào /Applications")
    print("  để cài đặt, hoặc chạy trực tiếp từ thư mục dist/")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())

