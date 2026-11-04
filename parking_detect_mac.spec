# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file cho macOS App Bundle (.app)
# Sử dụng: python -m PyInstaller --noconfirm parking_detect_mac.spec

import os
import sys
from pathlib import Path

project_dir = os.path.dirname(os.path.abspath(SPEC))

# Tìm model CoreML (ưu tiên .mlpackage, fallback .pt)
model_datas = []
for model_name in ['yolov8m.mlpackage', 'yolov8s.mlpackage']:
    model_path = os.path.join(project_dir, model_name)
    if os.path.exists(model_path):
        model_datas.append((model_path, model_name))
        break

# Fallback: nếu không có .mlpackage, đóng gói .pt
if not model_datas:
    for model_name in ['yolov8m.pt', 'yolov8s.pt']:
        model_path = os.path.join(project_dir, model_name)
        if os.path.exists(model_path):
            model_datas.append((model_path, '.'))
            break

a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=[],
    datas=[
        ('presets', 'presets'),
        ('assets', 'assets'),
        ('config', 'config'),
        ('icon.ico', '.'),
    ] + model_datas,
    hiddenimports=[
        'ultralytics',
        'easyocr',
        'cv2',
        'torch',
        'PIL',
        'openpyxl',
        'coremltools',
        'PyQt6',
        'PyQt6.sip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pygrabber',        # Windows-only
        'tkinter',          # Không cần
        'matplotlib',       # Nặng, không cần
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Parking Detect',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX gây vấn đề trên ARM64 macOS
    console=False,       # Ẩn terminal khi chạy .app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=os.path.join(project_dir, 'entitlements.plist'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ParkingDetect',
)

app = BUNDLE(
    coll,
    name='Parking Detect.app',
    icon=os.path.join(project_dir, 'icon.ico'),
    bundle_identifier='com.vtio.parkingdetect',
    info_plist={
        'CFBundleName': 'Parking Detect',
        'CFBundleDisplayName': 'Parking Detect',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'NSCameraUsageDescription': 'Ứng dụng cần quyền truy cập Camera để nhận diện xe trong bãi đỗ.',
        'NSSupportsAutomaticGraphicsSwitching': True,
        'LSMinimumSystemVersion': '12.0',
    },
)

