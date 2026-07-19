import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def set_titlebar_theme(window, is_dark):
    if sys.platform != "win32":
        return
    try:
        from ctypes.wintypes import HWND, DWORD
        import ctypes
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        hwnd = HWND(int(window.winId()))
        value = DWORD(1 if is_dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
        
        DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


LIGHT_THEME = """
QWidget {
    background-color: #F8FAFC;
    color: #1E293B;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QMainWindow {
    background-color: #F8FAFC;
}
QFrame#SidebarFrame {
    background-color: #FFFFFF;
    border-right: 1px solid #E2E8F0;
}
QFrame#HeaderFrame {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}
QFrame#CardFrame {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}
QLabel#BrandTitle {
    font-size: 16px;
    font-weight: bold;
    color: #0F172A;
}
QLabel#BrandSubtitle {
    font-size: 11px;
    color: #64748B;
}
QLabel#HeaderLabel {
    font-size: 16px;
    font-weight: bold;
    color: #0F172A;
}
QLabel#SubHeaderLabel {
    font-size: 12px;
    color: #64748B;
}
QPushButton#NavBtn {
    background-color: transparent;
    color: #64748B;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#NavBtn:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}
QPushButton#NavBtn[active="true"] {
    background-color: #EFEEFD;
    color: #5B46E8;
    font-weight: bold;
    border-left: 3px solid #7B68EE;
}
QPushButton {
    background-color: #7B68EE;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #6B56E8;
}
QPushButton:disabled {
    background-color: #CBD5E1;
    color: #94A3B8;
}
QPushButton#CheckInBtn {
    background-color: #10B981;
    color: white;
}
QPushButton#CheckInBtn:hover {
    background-color: #059669;
}
QPushButton#CheckInBtn:disabled {
    background-color: #CBD5E1;
    color: #94A3B8;
}
QPushButton#SuccessBtn {
    background-color: #10B981;
    color: white;
}
QPushButton#SuccessBtn:hover {
    background-color: #059669;
}
QPushButton#DangerBtn {
    background-color: #F43F5E;
    color: white;
}
QPushButton#DangerBtn:hover {
    background-color: #E11D48;
}
QPushButton#SecondaryBtn {
    background-color: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
}
QPushButton#SecondaryBtn:hover {
    background-color: #E2E8F0;
}
QLineEdit {
    padding: 7px 12px;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    background-color: #FFFFFF;
    color: #0F172A;
}
QLineEdit:focus {
    border: 2px solid #7B68EE;
}
QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 4px;
}
QListWidget::item {
    padding: 8px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background-color: #EFEEFD;
    color: #5B46E8;
    font-weight: bold;
}
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    gridline-color: #F1F5F9;
}
QHeaderView::section {
    font-size: 12px;
    font-weight: bold;
    background-color: #F8FAFC;
    color: #475569;
    border: none;
    border-bottom: 2px solid #E2E8F0;
    padding: 6px;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
"""

DARK_THEME = """
QWidget {
    background-color: #12131C;
    color: #F1F5F9;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QMainWindow {
    background-color: #12131C;
}
QFrame#SidebarFrame {
    background-color: #1A1C29;
    border-right: 1px solid #282B3D;
}
QFrame#HeaderFrame {
    background-color: #1A1C29;
    border-bottom: 1px solid #282B3D;
}
QFrame#CardFrame {
    background-color: #1E2030;
    border: 1px solid #2C2E43;
    border-radius: 12px;
}
QLabel#BrandTitle {
    font-size: 16px;
    font-weight: bold;
    color: #F8FAFC;
}
QLabel#BrandSubtitle {
    font-size: 11px;
    color: #94A3B8;
}
QLabel#HeaderLabel {
    font-size: 16px;
    font-weight: bold;
    color: #F8FAFC;
}
QLabel#SubHeaderLabel {
    font-size: 12px;
    color: #94A3B8;
}
QPushButton#NavBtn {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 13px;
}
QPushButton#NavBtn:hover {
    background-color: #25283B;
    color: #F1F5F9;
}
QPushButton#NavBtn[active="true"] {
    background-color: #2A274E;
    color: #A78BFA;
    font-weight: bold;
    border-left: 3px solid #8B5CF6;
}
QPushButton {
    background-color: #8B5CF6;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #7C3AED;
}
QPushButton:disabled {
    background-color: #33374D;
    color: #64748B;
}
QPushButton#CheckInBtn {
    background-color: #10B981;
    color: white;
}
QPushButton#CheckInBtn:hover {
    background-color: #059669;
}
QPushButton#CheckInBtn:disabled {
    background-color: #33374D;
    color: #64748B;
}
QPushButton#SuccessBtn {
    background-color: #10B981;
    color: white;
}
QPushButton#SuccessBtn:hover {
    background-color: #059669;
}
QPushButton#DangerBtn {
    background-color: #F43F5E;
    color: white;
}
QPushButton#DangerBtn:hover {
    background-color: #E11D48;
}
QPushButton#SecondaryBtn {
    background-color: #282B3D;
    color: #CBD5E1;
    border: 1px solid #33374D;
}
QPushButton#SecondaryBtn:hover {
    background-color: #33374D;
}
QLineEdit {
    padding: 7px 12px;
    border: 1px solid #33374D;
    border-radius: 8px;
    background-color: #161824;
    color: #F1F5F9;
}
QLineEdit:focus {
    border: 2px solid #8B5CF6;
}
QListWidget {
    background-color: #161824;
    border: 1px solid #2C2E43;
    border-radius: 8px;
    padding: 4px;
    color: #F1F5F9;
}
QListWidget::item {
    padding: 8px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background-color: #2A274E;
    color: #A78BFA;
    font-weight: bold;
}
QTableWidget {
    background-color: #1E2030;
    border: 1px solid #2C2E43;
    border-radius: 8px;
    gridline-color: #282B3D;
    color: #F1F5F9;
}
QHeaderView::section {
    font-size: 12px;
    font-weight: bold;
    background-color: #161824;
    color: #94A3B8;
    border: none;
    border-bottom: 2px solid #2C2E43;
    padding: 6px;
}
QScrollArea {
    border: none;
    background-color: transparent;
}
"""
