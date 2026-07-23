import threading
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox, 
    QListWidget, QFrame, QDialog, QScrollArea, QGridLayout,
    QGraphicsOpacityEffect, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
    QStackedWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QImage

from data.db_manager import ParkingDB
from data.preset_manager import PresetManager
from logic.detection_worker import DetectionWorker
from ui.theme import LIGHT_THEME, DARK_THEME, set_titlebar_theme, resource_path
from ui.components.toggle_switch import ToggleSwitch
from ui.components.hover_sidebar import HoverSidebarFrame
from ui.dialogs import (
    choose_webcam_dialog,
    show_checkin_guidance_dialog,
    execute_draw_window,
    show_export_dialog
)



class ParkingAppUI(QMainWindow):
    """Cửa sổ giao diện chính của ứng dụng Parking Detect."""

    def __init__(self):
        super().__init__()
        # State
        self.db = ParkingDB()
        self.polygons = []
        self.current_polygon = []
        self.current_preset_name = ""
        self.video_path = ""
        self.is_webcam = False
        self.webcam_index = 0

        self.detection_active = False
        self.show_video_embedded = True  # Default: Embedded inside App UI

        self.last_poly_status = []
        self.prev_poly_status = []
        self.last_raw_frame = None
        self.last_frame = None

        self.alpr_enabled = False
        self.is_dark_mode = False
        self.alpr_reader = None
        self.preload_alpr()

        self.init_ui()

    def _repolish(self, widget):
        style = widget.style()
        if style is not None:
            style.unpolish(widget)
            style.polish(widget)

    def preload_alpr(self):
        def _preload():
            try:
                import easyocr
                self.alpr_reader = easyocr.Reader(['en'], gpu=True)
                print("ALPR Model preloaded in background successfully.")
            except Exception as e:
                print("Failed to preload ALPR model:", e)

        threading.Thread(target=_preload, daemon=True).start()

    def init_ui(self):
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.setWindowTitle("Parking Vehicle Detection")
        self.resize(700, 450)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(60, 0, 0, 0)
        main_layout.setSpacing(0)

        # ================= MAIN WORKSPACE AREA =================
        workspace_widget = QWidget()
        workspace_layout = QVBoxLayout(workspace_widget)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        main_layout.addWidget(workspace_widget)

        # ================= HOVER DOCKED SIDEBAR OVERLAY =================
        self.sidebar_frame = HoverSidebarFrame(central, collapsed_width=70, expanded_width=230)
        shadow = QGraphicsDropShadowEffect(self.sidebar_frame)
        shadow.setBlurRadius(20)
        shadow.setXOffset(4)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 70))
        self.sidebar_frame.setGraphicsEffect(shadow)

        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(8, 20, 8, 20)
        sidebar_layout.setSpacing(10)

        # Logo / Brand Header
        brand_layout = QHBoxLayout()
        logo_label = QLabel("")
        logo_label.setFont(QFont('Segoe UI', 18))
        logo_label.setFixedWidth(44)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        brand_layout.addWidget(logo_label)
        brand_layout.addStretch()
        sidebar_layout.addLayout(brand_layout)
        sidebar_layout.addSpacing(15)

        # Navigation Buttons
        self.nav_buttons = []

        nav_items = [
            ("🎯  Cấu Hình", "Cấu hình Camera / Video & Preset Khoanh Vùng"),
            ("📺  Trực Tiếp", "Màn hình Nhận Diện & Sơ Đồ Vị Trí"),
            ("✅  Check In", "Chức năng Check-In & Hướng dẫn đỗ xe"),
            ("📊  Báo Cáo", "Thống kê số lượt xe vào/ra & Lịch sử"),
            ("⚙️  Cài Đặt", "ALPR, Chế độ giao diện & Nút gạt chế độ Camera")
        ]

        for idx, (title, tooltip) in enumerate(nav_items):
            btn = QPushButton(title)
            btn.setObjectName("NavBtn")
            btn.setToolTip(tooltip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self.select_page(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Footer Sidebar (Theme toggle & status)
        self.toggle_theme_btn = QPushButton("🌙  Chế độ Tối")
        self.toggle_theme_btn.setObjectName("NavBtn")
        self.toggle_theme_btn.setToolTip("Chuyển đổi Chế độ Sáng / Tối")
        self.toggle_theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_theme_btn.clicked.connect(self.toggle_theme)
        sidebar_layout.addWidget(self.toggle_theme_btn)

        ver_lbl = QLabel("v2.5")
        ver_lbl.setObjectName("BrandSubtitle")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(ver_lbl)

        # Position initially collapsed
        self.sidebar_frame.setGeometry(0, 0, 60, 730)
        self.sidebar_frame.raise_()

        # Workspace Header Bar
        header_frame = QFrame()
        header_frame.setObjectName("HeaderFrame")
        header_frame.setFixedHeight(60)
        header_bar_layout = QHBoxLayout(header_frame)
        header_bar_layout.setContentsMargins(25, 0, 25, 0)

        self.lbl_page_title = QLabel("🎯 Cấu Hình Nhận Diện & Camera")
        self.lbl_page_title.setObjectName("HeaderLabel")
        header_bar_layout.addWidget(self.lbl_page_title)
        header_bar_layout.addStretch()

        self.btn_header_detect = QPushButton("⚡ BẮT ĐẦU NHẬN DIỆN")
        self.btn_header_detect.setObjectName("SuccessBtn")
        self.btn_header_detect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_header_detect.clicked.connect(self.toggle_detection_state)
        header_bar_layout.addWidget(self.btn_header_detect)

        workspace_layout.addWidget(header_frame)

        # Stacked Pages Widget
        self.stacked_widget = QStackedWidget()

        # ---- Page 0: Cấu hình ----
        page_config = self._create_page_config()
        self.stacked_widget.addWidget(page_config)

        # ---- Page 1: Live Video & Trạng thái ----
        page_status = self._create_page_status()
        self.stacked_widget.addWidget(page_status)

        # ---- Page 2: Check-In ----
        page_checkin = self._create_page_checkin()
        self.stacked_widget.addWidget(page_checkin)

        # ---- Page 3: Báo cáo & Thống kê ----
        page_dashboard = self._create_page_dashboard()
        self.stacked_widget.addWidget(page_dashboard)

        # ---- Page 4: Cài đặt hệ thống ----
        page_settings = self._create_page_settings()
        self.stacked_widget.addWidget(page_settings)

        workspace_layout.addWidget(self.stacked_widget)
        main_layout.addWidget(workspace_widget)

        # Background timers for auto refresh
        self.timer_status = QTimer(self)
        self.timer_status.timeout.connect(self._refresh_status_page)

        self.timer_page_checkin = QTimer(self)
        self.timer_page_checkin.timeout.connect(self._refresh_checkin_page)

        self.timer_dash = QTimer(self)
        self.timer_dash.timeout.connect(self._refresh_dashboard)

        self.select_page(0)
        self.apply_theme()

    def select_page(self, index):
        self.stacked_widget.setCurrentIndex(index)
        titles = [
            "🎯 Cấu Hình Nhận Diện & Camera",
            "📺 Màn Hình Nhận Diện Trực Tiếp & Sơ Đồ Ô Đỗ",
            "✅ Trung Tâm Check-In & Hướng Dẫn Xe Vào",
            "📊 Báo Cáo & Thống Kê Chi Tiết",
            "⚙️ Cài Đặt Hệ Thống & Tùy Chọn Hiển Thị"
        ]
        if index < len(titles):
            self.lbl_page_title.setText(titles[index])

        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setProperty("active", "true")
            else:
                btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Manage background timers based on selected page
        if index == 1:
            self._refresh_status_page()
            self.timer_status.start(1000)
        else:
            self.timer_status.stop()

        if index == 2:
            self._refresh_checkin_page()
            self.timer_page_checkin.start(1000)
        else:
            self.timer_page_checkin.stop()

        if index == 3:
            self._refresh_dashboard()
            self.timer_dash.start(1500)
        else:
            self.timer_dash.stop()

    # ================= PAGE BUILDERS =================

    def _create_page_config(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        card = QFrame()
        card.setObjectName("CardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(20)

        lbl_info = QLabel("CẤU HÌNH LUỒNG VIDEO & VÙNG ĐỖ XE")
        lbl_info.setObjectName("HeaderLabel")
        card_layout.addWidget(lbl_info)

        # Source selector
        v_layout1 = QHBoxLayout()
        v_layout1.addWidget(QLabel("Nguồn Video/Camera:"))
        self.entry_video = QLineEdit()
        self.entry_video.setPlaceholderText("Vui lòng chọn video file hoặc camera...")
        self.entry_video.setReadOnly(True)
        v_layout1.addWidget(self.entry_video)

        self.btn_browse = QPushButton("📁 Duyệt File")
        self.btn_browse.setObjectName("SecondaryBtn")
        self.btn_browse.clicked.connect(self.browse_file)
        v_layout1.addWidget(self.btn_browse)

        self.btn_webcam = QPushButton("📷 Sử Dụng Camera")
        self.btn_webcam.setObjectName("SecondaryBtn")
        self.btn_webcam.clicked.connect(self.choose_webcam)
        v_layout1.addWidget(self.btn_webcam)

        card_layout.addLayout(v_layout1)

        # Time crop range
        v_layout2 = QHBoxLayout()
        v_layout2.addWidget(QLabel("Bắt đầu (giây):"))
        self.entry_start = QLineEdit("0")
        v_layout2.addWidget(self.entry_start)

        v_layout2.addWidget(QLabel("Kết thúc (giây):"))
        self.entry_end = QLineEdit("0")
        v_layout2.addWidget(self.entry_end)

        lbl_hint = QLabel("(0 = chạy hết toàn bộ video)")
        lbl_hint.setObjectName("SubHeaderLabel")
        v_layout2.addWidget(lbl_hint)
        v_layout2.addStretch()

        card_layout.addLayout(v_layout2)

        # Presets & Draw region section
        card_layout.addWidget(QLabel("Preset Khoanh Vùng Ô Đỗ:"))

        preset_layout = QHBoxLayout()
        self.list_presets = QListWidget()
        self.list_presets.setMaximumHeight(120)
        self.refresh_preset_list()
        preset_layout.addWidget(self.list_presets)

        preset_actions = QVBoxLayout()
        btn_load_p = QPushButton("📥 Tải Preset")
        btn_load_p.setObjectName("SecondaryBtn")
        btn_load_p.clicked.connect(self.on_load_selected_preset)

        btn_draw_new = QPushButton("✏️ Vẽ Vùng Mới")
        btn_draw_new.clicked.connect(self.start_draw_regions)

        btn_del_p = QPushButton("🗑️ Xóa Preset")
        btn_del_p.setObjectName("DangerBtn")
        btn_del_p.clicked.connect(self.on_delete_selected_preset)

        preset_actions.addWidget(btn_load_p)
        preset_actions.addWidget(btn_draw_new)
        preset_actions.addWidget(btn_del_p)
        preset_actions.addStretch()

        preset_layout.addLayout(preset_actions)
        card_layout.addLayout(preset_layout)

        # Big Launch Button
        self.btn_detect = QPushButton("🚀 BẮT ĐẦU NHẬN DIỆN NGAY")
        self.btn_detect.setObjectName("SuccessBtn")
        self.btn_detect.setFont(QFont('Segoe UI', 12, QFont.Weight.Bold))
        self.btn_detect.setMinimumHeight(45)
        self.btn_detect.clicked.connect(self.toggle_detection_state)
        card_layout.addWidget(self.btn_detect)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _create_page_status(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # Left Panel: Embedded Video Display Label
        v_card = QFrame()
        v_card.setObjectName("CardFrame")
        v_card_layout = QVBoxLayout(v_card)
        v_card_layout.setContentsMargins(15, 15, 15, 15)

        v_title_bar = QHBoxLayout()
        v_title_bar.addWidget(QLabel("📺 MÀN HÌNH NHẬN DIỆN TRỰC TIẾP"))
        v_title_bar.addStretch()

        self.lbl_video_mode_tag = QLabel("[ Embedded Mode ]" if self.show_video_embedded else "[ Separate Window ]")
        self.lbl_video_mode_tag.setObjectName("SubHeaderLabel")
        v_title_bar.addWidget(self.lbl_video_mode_tag)

        v_card_layout.addLayout(v_title_bar)

        self.lbl_video_display = QLabel("📺 Luồng Video Camera Trực Tiếp\n(Nhấn 'Bắt Đầu Nhận Diện' để xem luồng nhận diện)")
        self.lbl_video_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video_display.setMinimumSize(480, 360)
        self.lbl_video_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.lbl_video_display.setStyleSheet(
            "background-color: #0F172A; color: #94A3B8; border-radius: 10px; font-weight: bold; border: 2px dashed #334155;"
        )
        v_card_layout.addWidget(self.lbl_video_display)

        layout.addWidget(v_card, stretch=3)

        # Right Panel: Stat Cards & Slot List
        r_card = QFrame()
        r_card.setObjectName("CardFrame")
        r_layout = QVBoxLayout(r_card)
        r_layout.setContentsMargins(15, 15, 15, 15)
        r_layout.setSpacing(15)

        stat_bar = QHBoxLayout()

        self.card_stat_free = QFrame()
        self.card_stat_free.setObjectName("CardFrame")
        l1 = QVBoxLayout(self.card_stat_free)
        self.lbl_free_count = QLabel("0")
        self.lbl_free_count.setStyleSheet("font-size: 22px; font-weight: bold; color: #10B981;")
        l1.addWidget(QLabel("TRỐNG"))
        l1.addWidget(self.lbl_free_count)

        self.card_stat_occ = QFrame()
        self.card_stat_occ.setObjectName("CardFrame")
        l2 = QVBoxLayout(self.card_stat_occ)
        self.lbl_occ_count = QLabel("0")
        self.lbl_occ_count.setStyleSheet("font-size: 22px; font-weight: bold; color: #F43F5E;")
        l2.addWidget(QLabel("ĐÃ ĐỖ"))
        l2.addWidget(self.lbl_occ_count)

        stat_bar.addWidget(self.card_stat_free)
        stat_bar.addWidget(self.card_stat_occ)
        r_layout.addLayout(stat_bar)

        r_layout.addWidget(QLabel("Chi Tiết Tình Trạng Ô Đỗ:"))
        self.sa_status_page = QScrollArea()
        self.sa_status_page.setWidgetResizable(True)
        r_layout.addWidget(self.sa_status_page)

        layout.addWidget(r_card, stretch=2)

        return page

    def _create_page_checkin(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        card_header = QFrame()
        card_header.setObjectName("CardFrame")
        cl = QHBoxLayout(card_header)
        cl.setContentsMargins(20, 15, 20, 15)

        info_v = QVBoxLayout()
        t = QLabel("TRUNG TÂM CHECK-IN XE VÀO")
        t.setObjectName("HeaderLabel")
        st = QLabel("Nhấn nút Check-In để hệ thống thông báo hướng dẫn vị trí đỗ trống cho xe.")
        st.setObjectName("SubHeaderLabel")
        info_v.addWidget(t)
        info_v.addWidget(st)

        cl.addLayout(info_v)
        cl.addStretch()

        self.btn_do_checkin = QPushButton("✅ CHECK-IN ")
        self.btn_do_checkin.setObjectName("CheckInBtn")
        self.btn_do_checkin.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
        self.btn_do_checkin.setMinimumHeight(42)
        self.btn_do_checkin.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_do_checkin.clicked.connect(self.perform_checkin_action)
        cl.addWidget(self.btn_do_checkin)

        layout.addWidget(card_header)

        layout.addWidget(QLabel("Danh Sách Tình Trạng Các Ô Đỗ Trong Bãi:"))
        self.sa_checkin_page = QScrollArea()
        self.sa_checkin_page.setWidgetResizable(True)
        layout.addWidget(self.sa_checkin_page)

        return page

    def _create_page_dashboard(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        self.f_stats = QFrame()
        self.f_stats.setObjectName("CardFrame")
        sl = QHBoxLayout(self.f_stats)
        sl.setContentsMargins(20, 15, 20, 15)

        self.lbl_in = QLabel("🚗 Lượt vào: 0")
        self.lbl_out = QLabel("🚙 Lượt ra: 0")
        self.lbl_occ = QLabel("🅿️ Đang đỗ: 0")
        for l in [self.lbl_in, self.lbl_out, self.lbl_occ]:
            l.setStyleSheet("font-size: 14px; font-weight: bold; color: #7B68EE;")
            sl.addWidget(l)

        layout.addWidget(self.f_stats)

        grid = QGridLayout()

        box1 = QVBoxLayout()
        box1.addWidget(QLabel("Thống Kê Theo Ô Đỗ"))
        self.table_slot = QTableWidget()
        if self.table_slot.verticalHeader() is not None:
            self.table_slot.verticalHeader().setVisible(False)  # type: ignore
        box1.addWidget(self.table_slot)
        grid.addLayout(box1, 0, 0)

        box2 = QVBoxLayout()
        box2.addWidget(QLabel("Lịch Sử Sự Kiện Gần Nhất"))
        self.table_hist = QTableWidget()
        if self.table_hist.verticalHeader() is not None:
            self.table_hist.verticalHeader().setVisible(False)  # type: ignore
        box2.addWidget(self.table_hist)
        grid.addLayout(box2, 0, 1)

        layout.addLayout(grid)

        layout.addWidget(QLabel("Lịch Sử Quét Biển Số (ALPR)"))
        self.table_plates = QTableWidget()
        if self.table_plates.verticalHeader() is not None:
            self.table_plates.verticalHeader().setVisible(False)  # type: ignore
        self.table_plates.setMinimumHeight(140)
        layout.addWidget(self.table_plates)

        h_bar = QHBoxLayout()
        btn_export = QPushButton("📊 Xuất Excel Báo Cáo")
        btn_export.setObjectName("SuccessBtn")
        btn_export.setMinimumHeight(36)
        btn_export.clicked.connect(self._open_export_dialog)
        h_bar.addWidget(btn_export)

        btn_clear = QPushButton("🗑️ Xóa Dữ Liệu Báo Cáo")
        btn_clear.setObjectName("DangerBtn")
        btn_clear.setMinimumHeight(36)
        btn_clear.clicked.connect(self._clear_dashboard)
        h_bar.addWidget(btn_clear)

        h_bar.addStretch()
        layout.addLayout(h_bar)

        return page

    def _open_export_dialog(self):
        show_export_dialog(self)

    def _create_page_settings(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        card = QFrame()
        card.setObjectName("CardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(25, 25, 25, 25)
        card_layout.setSpacing(20)

        card_layout.addWidget(QLabel("TÙY CHỌN HỆ THỐNG & HIỂN THỊ"))

        # Sole Horizontal Toggle Switch for Video Display Mode in Settings
        mode_box = QHBoxLayout()
        mode_info = QVBoxLayout()
        mode_title = QLabel("📺 Chế Độ Hiển Thị Luồng Camera Nhận Diện")
        mode_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.lbl_mode_status = QLabel("Trực tiếp trong App (Embedded Mode)" if self.show_video_embedded else "Mở cửa sổ Pop-up riêng (OpenCV Separate Window)")
        self.lbl_mode_status.setObjectName("SubHeaderLabel")

        mode_info.addWidget(mode_title)
        mode_info.addWidget(self.lbl_mode_status)

        mode_box.addLayout(mode_info)
        mode_box.addStretch()

        # Interactive Horizontal Pill Switch Widget in Settings
        self.switch_settings_view = ToggleSwitch()
        self.switch_settings_view.setChecked(self.show_video_embedded)
        self.switch_settings_view.toggled.connect(self.on_toggle_display_mode)

        sw_left = QLabel("Popup Window")
        sw_left.setObjectName("SubHeaderLabel")
        sw_right = QLabel("In App")
        sw_right.setStyleSheet("font-weight: bold; color: #7B68EE;")

        sw_layout = QHBoxLayout()
        sw_layout.addWidget(sw_left)
        sw_layout.addWidget(self.switch_settings_view)
        sw_layout.addWidget(sw_right)

        mode_box.addLayout(sw_layout)
        card_layout.addLayout(mode_box)

        card_layout.addWidget(QFrame())

        # ALPR Switch Box
        alpr_box = QHBoxLayout()
        alpr_info = QVBoxLayout()
        alpr_title = QLabel("📷 Nhận Diện Biển Số Tự Động (ALPR EasyOCR)")
        alpr_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        alpr_desc = QLabel("Tự động quét biển số xe khi xe tiến vào khung hình camera và lưu vào cơ sở dữ liệu.")
        alpr_desc.setObjectName("SubHeaderLabel")
        alpr_info.addWidget(alpr_title)
        alpr_info.addWidget(alpr_desc)

        self.btn_alpr = QPushButton("📷 ALPR: TẮT")
        self.btn_alpr.setCheckable(True)
        self.btn_alpr.setObjectName("SecondaryBtn")
        self.btn_alpr.toggled.connect(self.toggle_alpr)

        alpr_box.addLayout(alpr_info)
        alpr_box.addWidget(self.btn_alpr)
        card_layout.addLayout(alpr_box)

        card_layout.addWidget(QFrame())

        # Theme Switch Box
        theme_box = QHBoxLayout()
        theme_info = QVBoxLayout()
        theme_title = QLabel("🎨 Chế Độ Giao Diện (Theme Style)")
        theme_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        theme_desc = QLabel("Chuyển đổi giữa Chế độ Sáng (Light) và Chế độ Tối (Dark).")
        theme_desc.setObjectName("SubHeaderLabel")
        theme_info.addWidget(theme_title)
        theme_info.addWidget(theme_desc)

        btn_theme_switch = QPushButton("🌓 Đổi Giao Diện")
        btn_theme_switch.setObjectName("SecondaryBtn")
        btn_theme_switch.clicked.connect(self.toggle_theme)

        theme_box.addLayout(theme_info)
        theme_box.addWidget(btn_theme_switch)
        card_layout.addLayout(theme_box)

        card_layout.addWidget(QFrame())

        # Info Box
        info_layout = QVBoxLayout()
        info_title = QLabel("ℹ️ Thông Tin Mô Hình & Cấu Hình")
        info_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        info_lbl = QLabel(
            "• Detector Model: Ultralytics YOLOv8 Medium (yolov8m.pt)\n"
            "• ALPR Engine: EasyOCR (Deep Learning Text Recognition)\n"
            "• Video Switch: Dynamic Multi-toggle OpenCV Window Management\n"
            "• Database: SQLite (parking.db)\n"
            "• Framework: PyQt6 & OpenCV"
        )
        info_lbl.setObjectName("SubHeaderLabel")
        info_layout.addWidget(info_title)
        info_layout.addWidget(info_lbl)
        card_layout.addLayout(info_layout)

        layout.addWidget(card)
        layout.addStretch()
        return page

    # ================= LOGIC & THEME MANAGEMENT =================

    def on_toggle_display_mode(self, checked):
        self.show_video_embedded = checked
        if hasattr(self, 'lbl_mode_status'):
            if checked:
                self.lbl_mode_status.setText("Trực tiếp trong App (Embedded Mode)")
            else:
                self.lbl_mode_status.setText("Mở cửa sổ Pop-up riêng (OpenCV Separate Window)")
        if hasattr(self, 'lbl_video_mode_tag'):
            self.lbl_video_mode_tag.setText("[ Embedded Mode ]" if checked else "[ Separate Window ]")

        if not checked and self.detection_active and hasattr(self, 'lbl_video_display'):
            self.lbl_video_display.setText("🪟 Luồng Video đang hiển thị tại Cửa sổ Pop-up riêng biệt (OpenCV)...")

    def _update_embedded_video(self, qimg):
        if not qimg.isNull() and hasattr(self, 'lbl_video_display'):
            target_size = self.lbl_video_display.size()
            pixmap = QPixmap.fromImage(qimg)
            scaled_pixmap = pixmap.scaled(
                target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_video_display.setPixmap(scaled_pixmap)

    def fade_in(self, widget):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(400)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start()
        widget.anim = anim

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        if self.is_dark_mode:
            self.toggle_theme_btn.setText("🌞  Chế độ Sáng")
        else:
            self.toggle_theme_btn.setText("🌙  Chế độ Tối")

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        central_w = self.centralWidget()
        if hasattr(self, 'sidebar_frame') and central_w is not None:
            h = central_w.height()
            target_w = self.sidebar_frame.expanded_w if self.sidebar_frame.is_expanded else self.sidebar_frame.collapsed_w
            self.sidebar_frame.setGeometry(0, 0, target_w, h)

    def apply_theme(self):
        theme = DARK_THEME if self.is_dark_mode else LIGHT_THEME
        self.setStyleSheet(theme)

        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, (QMainWindow, QDialog)):
                set_titlebar_theme(widget, self.is_dark_mode)

        if hasattr(self, 'switch_settings_view'):
            self.switch_settings_view.update()
        if hasattr(self, 'sidebar_frame'):
            self.sidebar_frame.set_handle_theme(self.is_dark_mode)

    def toggle_alpr(self, checked):
        self.alpr_enabled = checked
        if checked:
            self.btn_alpr.setText("📷 ALPR: BẬT")
            self.btn_alpr.setObjectName("SuccessBtn")
        else:
            self.btn_alpr.setText("📷 ALPR: TẮT")
            self.btn_alpr.setObjectName("SecondaryBtn")
        self._repolish(self.btn_alpr)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn Video", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if file_path:
            self.video_path = file_path
            self.entry_video.setText(file_path)
            self.entry_start.setText("0")
            self.entry_end.setText("0")
            self.is_webcam = False
            self.btn_webcam.setText("📷 Sử Dụng Camera")
            self.polygons = []

    def choose_webcam(self):
        choose_webcam_dialog(self)

    def refresh_preset_list(self):
        self.list_presets.clear()
        presets = PresetManager.get_preset_list()
        self.list_presets.addItems(presets)

    def on_load_selected_preset(self):
        item = self.list_presets.currentItem()
        if not item:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn một preset từ danh sách.")
            return
        name = item.text()
        try:
            self.polygons = PresetManager.load_preset(name)
            self.current_preset_name = name
            QMessageBox.information(self, "Thành công", f"Đã tải preset '{name}' với {len(self.polygons)} ô đỗ.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi tải preset: {e}")

    def on_delete_selected_preset(self):
        item = self.list_presets.currentItem()
        if not item:
            QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn một preset.")
            return
        name = item.text()
        rep = QMessageBox.question(self, "Xác nhận", f"Bạn có chắc muốn xóa preset '{name}'?")
        if rep == QMessageBox.StandardButton.Yes:
            PresetManager.delete_preset(name)
            self.refresh_preset_list()

    def start_draw_regions(self):
        if not self.video_path and not self.is_webcam:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn video trước bằng nút Duyệt File hoặc chọn Camera!")
            return
        execute_draw_window(self)

    def toggle_detection_state(self):
        if self.detection_active:
            self.stop_detection()
        else:
            self.start_detection()

    def start_detection(self):
        if self.detection_active:
            return

        if not self.video_path and not self.is_webcam:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn video trước!")
            return

        if not self.polygons:
            res = QMessageBox.question(self, "Cảnh báo", "Bạn chưa khoanh vùng nhận diện bãi đỗ nào!\nVideo sẽ chạy nhưng không hiện chỗ trống đậu xe. Bạn có muốn tiếp tục chạy luôn không?")
            if res == QMessageBox.StandardButton.No:
                return

        primary = QApplication.primaryScreen()
        if primary is not None:
            screen = primary.geometry()
            w, h = screen.width(), screen.height()
        else:
            w, h = 1920, 1080

        self.worker = DetectionWorker(self, w, h)
        self.worker.on_error.connect(lambda e: QMessageBox.critical(self, "Lỗi", e))
        self.worker.show_checkin_signal.connect(lambda: self.select_page(2))
        self.worker.frame_signal.connect(self._update_embedded_video)
        self.worker.on_finished.connect(self._on_detection_finished)

        self.detection_active = True
        self.btn_detect.setText("🛑 DỪNG NHẬN DIỆN")
        self.btn_detect.setObjectName("DangerBtn")
        self.btn_header_detect.setText("🛑 DỪNG NHẬN DIỆN")
        self.btn_header_detect.setObjectName("DangerBtn")
        self._repolish(self.btn_detect)
        self._repolish(self.btn_header_detect)
        self.btn_alpr.setEnabled(True)

        # Switch to Live Video & Slot Status Page (Page 1)
        self.select_page(1)

        t = threading.Thread(target=self.worker.run, daemon=True)
        t.start()

    def stop_detection(self):
        if hasattr(self, 'worker') and self.worker:
            self.worker.stop()

    def _on_detection_finished(self):
        self.detection_active = False
        self.btn_detect.setText("🚀 BẮT ĐẦU NHẬN DIỆN NGAY")
        self.btn_detect.setObjectName("SuccessBtn")
        self.btn_header_detect.setText("⚡ BẮT ĐẦU NHẬN DIỆN")
        self.btn_header_detect.setObjectName("SuccessBtn")
        self._repolish(self.btn_detect)
        self._repolish(self.btn_header_detect)
        self.btn_alpr.setChecked(False)

        if hasattr(self, 'lbl_video_display'):
            self.lbl_video_display.setText("📺 Luồng Video Camera Trực Tiếp\n(Đã dừng nhận diện)")

    # ================= CHECK-IN ACTION =================

    def perform_checkin_action(self):
        status = self.last_poly_status
        if not status:
            QMessageBox.warning(self, "Check In", "Chưa có dữ liệu nhận diện bãi đỗ. Vui lòng nhấn 'Bắt Đầu Nhận Diện' trước.")
            return

        empty_slots = [i + 1 for i, occ in enumerate(status) if not occ]
        if not empty_slots:
            QMessageBox.warning(self, "Check In Thất Bại", "⛔ Bãi đỗ hiện tại đã đầy! Không còn ô trống nào.")
            return

        slot_id = empty_slots[0]
        show_checkin_guidance_dialog(self, slot_id)
        self._refresh_checkin_page()

    # ================= PAGE REFRESHERS =================

    def _refresh_status_page(self):
        status = self.last_poly_status
        if not status:
            self.lbl_free_count.setText("0")
            self.lbl_occ_count.setText("0")
            return

        empty_slots = [i + 1 for i, occ in enumerate(status) if not occ]
        occ_slots = [i + 1 for i, occ in enumerate(status) if occ]
        tot = len(status)

        self.lbl_free_count.setText(str(len(empty_slots)))
        self.lbl_occ_count.setText(str(len(occ_slots)))

        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setSpacing(10)

        for idx in range(tot):
            slot = idx + 1
            is_occ = status[idx]

            f = QFrame()
            f.setObjectName("CardFrame")
            fl = QHBoxLayout(f)
            fl.setContentsMargins(15, 10, 15, 10)

            if is_occ:
                txt = f"🔴  Ô {slot}:  Đã có xe đỗ"
                col = "#F43F5E"
            else:
                txt = f"🟢  Ô {slot}:  Còn trống"
                col = "#10B981"

            l = QLabel(txt)
            l.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 14px;")
            fl.addWidget(l)
            wl.addWidget(f)

        wl.addStretch()
        self.sa_status_page.setWidget(w)

    def _refresh_checkin_page(self):
        status = self.last_poly_status
        if not status:
            return

        tot = len(status)

        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setSpacing(10)

        for idx in range(tot):
            slot = idx + 1
            is_occ = status[idx]

            f = QFrame()
            f.setObjectName("CardFrame")
            fl = QHBoxLayout(f)
            fl.setContentsMargins(15, 10, 15, 10)

            if is_occ:
                txt = f"🔴  Ô {slot}:  Đã có xe đỗ"
                col = "#F43F5E"
            else:
                txt = f"🟢  Ô {slot}:  Còn trống "
                col = "#10B981"

            l = QLabel(txt)
            l.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 14px;")
            fl.addWidget(l)
            wl.addWidget(f)

        wl.addStretch()
        self.sa_checkin_page.setWidget(w)

    def _clear_dashboard(self):
        rep = QMessageBox.question(self, "Xác nhận", "Xóa toàn bộ dữ liệu báo cáo?")
        if rep == QMessageBox.StandardButton.Yes:
            self.db.clear_all_data()
            self._refresh_dashboard()

    def _refresh_dashboard(self):
        try:
            stats = self.db.get_today_stats()
            self.lbl_in.setText(f"🚗 Lượt vào: {stats['total_in']}")
            self.lbl_out.setText(f"🚙 Lượt ra: {stats['total_out']}")
            self.lbl_occ.setText(f"🅿️ Đang đỗ: {stats['currently_occupied']}")

            def centered_item(text):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return item

            summary = self.db.get_slot_summary()
            self.table_slot.setRowCount(len(summary))
            self.table_slot.setColumnCount(3)
            self.table_slot.setHorizontalHeaderLabels(["Ô đỗ", "Lượt vào", "Lượt ra"])
            if self.table_slot.horizontalHeader() is not None:
                self.table_slot.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # type: ignore

            for r, row in enumerate(summary):
                self.table_slot.setItem(r, 0, centered_item(f"Ô {row['slot_id']}"))
                self.table_slot.setItem(r, 1, centered_item(str(row['total_in'])))
                self.table_slot.setItem(r, 2, centered_item(str(row['total_out'])))

            hist = self.db.get_history(15)
            self.table_hist.setRowCount(len(hist))
            self.table_hist.setColumnCount(5)
            self.table_hist.setHorizontalHeaderLabels(["Ngày", "Giờ", "Ô đỗ", "Xe", "Sự kiện"])
            if self.table_hist.horizontalHeader() is not None:
                self.table_hist.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # type: ignore
                self.table_hist.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # type: ignore

            for r, ev in enumerate(hist):
                try:
                    dt = datetime.strptime(ev["timestamp"], "%Y-%m-%d %H:%M:%S")
                    date_str = dt.strftime("%d/%m")
                    time_str = dt.strftime("%H:%M:%S")
                except Exception:
                    date_str = ""
                    time_str = ev["timestamp"]
                txt = "VÀO" if ev["event_type"] == "IN" else "RA"

                self.table_hist.setItem(r, 0, centered_item(date_str))
                self.table_hist.setItem(r, 1, centered_item(time_str))
                self.table_hist.setItem(r, 2, centered_item(f"Ô {ev['slot_id']}"))
                self.table_hist.setItem(r, 3, centered_item(ev["vehicle_id"] or ""))

                item_event = centered_item(txt)
                item_event.setForeground(QColor("#10B981" if ev["event_type"] == "IN" else "#F59E0B"))
                font = item_event.font()
                font.setBold(True)
                item_event.setFont(font)
                self.table_hist.setItem(r, 4, item_event)

            plates = self.db.get_license_plates(10)
            self.table_plates.setRowCount(len(plates))
            self.table_plates.setColumnCount(3)
            self.table_plates.setHorizontalHeaderLabels(["Thời Gian", "Biển Số", "Hình Ảnh"])
            if self.table_plates.horizontalHeader() is not None:
                self.table_plates.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # type: ignore
            if self.table_plates.verticalHeader() is not None:
                self.table_plates.verticalHeader().setDefaultSectionSize(50)  # type: ignore

            for r, p in enumerate(plates):
                self.table_plates.setItem(r, 0, centered_item(p["timestamp"]))

                txt_item = centered_item(p["plate_text"])
                txt_item.setForeground(QColor("#7B68EE"))
                font = txt_item.font()
                font.setBold(True)
                txt_item.setFont(font)
                self.table_plates.setItem(r, 1, txt_item)

                if p["plate_image"]:
                    img_data = p["plate_image"]
                    qimg = QImage.fromData(img_data)
                    pixmap = QPixmap.fromImage(qimg).scaled(100, 45, Qt.AspectRatioMode.KeepAspectRatio)
                    lbl_img = QLabel()
                    lbl_img.setPixmap(pixmap)
                    lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table_plates.setCellWidget(r, 2, lbl_img)

        except Exception as e:
            print("Refresh err", e)
