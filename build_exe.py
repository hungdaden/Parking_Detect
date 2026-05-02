import subprocess
import sys
import os
import shutil

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    spec_file = os.path.join(project_dir, "parking_detect.spec")
    icon_file = os.path.join(project_dir, "icon.ico")
    
    print("=" * 60)
    print("  BUILDING PARKING DETECT")
    print("=" * 60)
    
    # Force clean dist/build to avoid Errno 22 / Permission issues
    for folder in ["build", "dist"]:
        path = os.path.join(project_dir, folder)
        if os.path.exists(path):
            try:
                print(f"Cleaning {folder}...")
                # Use powershell for more forceful deletion if needed
                subprocess.run(["powershell", "-Command", f"Remove-Item -Path '{path}' -Recurse -Force -ErrorAction SilentlyContinue"], check=False)
            except Exception as e:
                print(f"Warning: Could not fully clean {folder}: {e}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        spec_file,
    ]
    
    print(f"\nRunning: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=project_dir)
    
    if result.returncode != 0:
        print("\n[ERROR] PyInstaller build failed!")
        return 1
    
    dist_dir = os.path.join(project_dir, "dist", "ParkingDetect_App")
    exe_path = os.path.join(dist_dir, "Parking Detect.exe")
    
    if not os.path.exists(exe_path):
        print(f"\n[ERROR] EXE not found at: {exe_path}")
        return 1
    
    print(f"\n[OK] EXE built successfully: {exe_path}")
    
    # Create Desktop Shortcut
    print("\n" + "=" * 60)
    print("  CREATING DESKTOP SHORTCUT")
    print("=" * 60)
    
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "Parking Detect.lnk")
    working_dir = dist_dir
    icon_abs = os.path.abspath(icon_file)
    
    ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
$Shortcut.TargetPath = "{exe_path}"
$Shortcut.WorkingDirectory = "{working_dir}"
$Shortcut.IconLocation = "{icon_abs},0"
$Shortcut.Description = "Parking Vehicle Detection App"
$Shortcut.Save()
'''
    
    subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
    print(f"[OK] Desktop shortcut created: {shortcut_path}")
    
    print("\nBuild system finished. You can now use the shortcut on your desktop.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
