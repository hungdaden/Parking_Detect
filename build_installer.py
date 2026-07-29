import subprocess
import sys
import os
import shutil

def find_inno_setup_compiler():
    # 1. Check system PATH
    iscc = shutil.which("iscc")
    if iscc:
        return iscc
    
    # 2. Check standard Windows installation paths
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    return None

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    spec_file = os.path.join(project_dir, "parking_detect.spec")
    iss_file = os.path.join(project_dir, "installer.iss")
    
    print("=" * 65)
    print("      BUILDING PARKING DETECT INSTALLER (setup.exe)")
    print("=" * 65)
    
    # 1. Clean dist & build folders
    for folder in ["build", "dist"]:
        path = os.path.join(project_dir, folder)
        if os.path.exists(path):
            try:
                print(f"Cleaning {folder}...")
                subprocess.run(
                    ["powershell", "-Command", f"Remove-Item -Path '{path}' -Recurse -Force -ErrorAction SilentlyContinue"],
                    check=False
                )
            except Exception as e:
                print(f"Warning: Could not fully clean {folder}: {e}")

    # 2. Locate Virtual Environment Python
    python_exe = sys.executable
    for venv_dir in [".venv", "venv", "env"]:
        venv_python = os.path.join(project_dir, venv_dir, "Scripts", "python.exe")
        if os.path.exists(venv_python):
            python_exe = venv_python
            break

    # 3. Step 1: Run PyInstaller
    print("\n[STEP 1/2] Compiling Python Application with PyInstaller...")
    cmd_pyinstaller = [
        python_exe, "-m", "PyInstaller",
        "--noconfirm",
        spec_file,
    ]
    
    print(f"Running: {' '.join(cmd_pyinstaller)}\n")
    res_pyi = subprocess.run(cmd_pyinstaller, cwd=project_dir)
    
    if res_pyi.returncode != 0:
        print("\n[ERROR] PyInstaller compilation failed!")
        return 1

    dist_app_dir = os.path.join(project_dir, "dist", "ParkingDetect_App")
    exe_path = os.path.join(dist_app_dir, "Parking Detect.exe")
    
    if not os.path.exists(exe_path):
        print(f"\n[ERROR] Compiled app executable not found at: {exe_path}")
        return 1

    print(f"[OK] Application bundle created successfully at: {dist_app_dir}")

    # 4. Step 2: Compile Installer using Inno Setup Compiler
    print("\n[STEP 2/2] Packaging into Setup Installer Executable (setup.exe)...")
    iscc_path = find_inno_setup_compiler()
    
    if not iscc_path:
        print("\n" + "!" * 65)
        print(" [WARNING] Inno Setup Compiler (ISCC.exe) was not found on this system.")
        print(" - Application files are ready in: dist\\ParkingDetect_App")
        print(" - To create 'ParkingDetect_Setup.exe':")
        print("   1. Download & Install Inno Setup 6 (Free) from: https://jrsoftware.org/isdl.php")
        print("   2. Re-run this script: python build_installer.py")
        print("   OR open 'installer.iss' in Inno Setup GUI and click Compile.")
        print("!" * 65 + "\n")
        return 0

    print(f"Found Inno Setup Compiler: {iscc_path}")
    cmd_inno = [iscc_path, iss_file]
    
    print(f"Running: {' '.join(cmd_inno)}\n")
    res_inno = subprocess.run(cmd_inno, cwd=project_dir)
    
    if res_inno.returncode != 0:
        print("\n[ERROR] Inno Setup compilation failed!")
        return 1

    setup_exe_path = os.path.join(project_dir, "dist", "ParkingDetect_Setup.exe")
    if os.path.exists(setup_exe_path):
        print("\n" + "=" * 65)
        print("      BUILD SUCCESSFUL!")
        print("=" * 65)
        print(f"File setup đã hoàn thành: {setup_exe_path}")
        print("Bạn có thể gửi file này cho người dùng khác để họ cài đặt tự động!")
        print("=" * 65)
    else:
        print(f"\n[OK] Inno Setup finished. Check output folder: {os.path.join(project_dir, 'dist')}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
