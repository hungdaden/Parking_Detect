import os
import json
import shutil
import threading
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QFileDialog, QMessageBox, 
    QListWidget, QFrame, QDialog, QScrollArea, QGridLayout,
    QGraphicsOpacityEffect, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
    QStackedWidget, QGraphicsDropShadowEffect, QComboBox
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap, QImage, QGuiApplication

from data.db_manager import ParkingDB
from data.preset_manager import PresetManager
from logic.detection_worker import DetectionWorker
from ui.theme import LIGHT_THEME, DARK_THEME, set_titlebar_theme, resource_path
from ui.components import ToggleSwitch, HoverSidebarFrame, ClickUpRangeSlider
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
        self.show_slot_numbers = True    # Default: Show slot numbers
        self.show_vehicle_bbox = True    # Default: Show vehicle bounding boxes
        self.show_vehicle_center = True  # Default: Show vehicle center dot
        self.misparked_enabled = True    # Default: Enable misplaced parking warning
        self.misparked_delay_sec = 10    # Default: 10 seconds stationary delay
        self.show_stationary_timer = True # Default: Show yellow live timer badge
        self.debounce_delay_sec = 0.5    # Default: 0.5 seconds anti-flicker debounce

        self.last_poly_status = []
        self.prev_poly_status = []
        self.last_raw_frame = None
        self.last_frame = None

        self.alpr_enabled = False
        self.is_dark_mode = False
        self.alpr_reader = None

        self.selected_guidance_screens = [0]
        self._active_guidance_dialogs = []
        self.load_app_config()
        self.preload_alpr()

        app_instance = QApplication.instance()
        if isinstance(app_instance, QGuiApplication):
            app_instance.screenAdded.connect(self._on_screens_changed)
            app_instance.screenRemoved.connect(self._on_screens_changed)
            app_instance.primaryScreenChanged.connect(self._on_screens_changed)

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
        self.sidebar_frame = HoverSidebarFrame(central, collapsed_width=69, expanded_width=230)
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

        if index == 4:
            self.refresh_guidance_screen_combo()

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

        # ClickUp-Style Video Time Crop Section
        time_card = QFrame()
        time_card.setObjectName("CardFrame")
        time_card.setStyleSheet("""
            QFrame#CardFrame {
                background-color: rgba(123, 104, 238, 0.05);
                border: 1px dashed rgba(123, 104, 238, 0.35);
                border-radius: 12px;
            }
        """)
        tc_layout = QVBoxLayout(time_card)
        tc_layout.setContentsMargins(14, 12, 14, 12)
        tc_layout.setSpacing(8)

        # Header bar with info badges
        header_time = QHBoxLayout()
        lbl_time_title = QLabel("🎬 Cắt Đoạn Video")
        lbl_time_title.setFont(QFont('Segoe UI', 10, QFont.Weight.Bold))

        self.lbl_time_duration = QLabel("⏳ Tổng thời lượng: --:--")
        self.lbl_time_duration.setObjectName("SubHeaderLabel")
        self.lbl_time_duration.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))

        header_time.addWidget(lbl_time_title)
        header_time.addStretch()
        header_time.addWidget(self.lbl_time_duration)
        tc_layout.addLayout(header_time)

        # Dual Range Slider (ClickUp Range Slider)
        self.range_slider = ClickUpRangeSlider(minimum=0, maximum=300, low_val=0, high_val=300)
        self.range_slider.valuesChanged.connect(self._on_range_slider_changed)
        tc_layout.addWidget(self.range_slider)

        # Bottom Controls & Input Badges (Bi-directional sync with entry_start & entry_end)
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        ctrl_layout.addWidget(QLabel("⏱️ Bắt đầu:"))
        self.entry_start = QLineEdit("0")
        self.entry_start.setFixedWidth(55)
        self.entry_start.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry_start.setToolTip("Nhập thời điểm bắt đầu (giây)")
        self.entry_start.textChanged.connect(self._on_entry_start_changed)
        ctrl_layout.addWidget(self.entry_start)

        self.lbl_start_fmt = QLabel("(00:00)")
        self.lbl_start_fmt.setStyleSheet("color: #7B68EE; font-weight: bold;")
        ctrl_layout.addWidget(self.lbl_start_fmt)

        ctrl_layout.addSpacing(15)

        ctrl_layout.addWidget(QLabel("⏱️ Kết thúc:"))
        self.entry_end = QLineEdit("0")
        self.entry_end.setFixedWidth(55)
        self.entry_end.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry_end.setToolTip("Nhập thời điểm kết thúc (giây), 0 = đến hết video")
        self.entry_end.textChanged.connect(self._on_entry_end_changed)
        ctrl_layout.addWidget(self.entry_end)

        self.lbl_end_fmt = QLabel("(Hết video)")
        self.lbl_end_fmt.setStyleSheet("color: #7B68EE; font-weight: bold;")
        ctrl_layout.addWidget(self.lbl_end_fmt)

        ctrl_layout.addStretch()

        self.lbl_range_span = QLabel("🎯 Chạy toàn bộ video")
        self.lbl_range_span.setFont(QFont('Segoe UI', 9, QFont.Weight.Bold))
        self.lbl_range_span.setStyleSheet("color: #10B981;")
        ctrl_layout.addWidget(self.lbl_range_span)

        tc_layout.addLayout(ctrl_layout)
        card_layout.addWidget(time_card)

        # Presets & Draw region section
        card_layout.addWidget(QLabel("Preset Khoanh Vùng Ô Đỗ:"))

        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(15)

        preset_actions = QVBoxLayout()
        preset_actions.setSpacing(8)

        btn_load_p = QPushButton("📥 Tải Preset")
        btn_load_p.setObjectName("SecondaryBtn")
        btn_load_p.clicked.connect(self.on_load_selected_preset)

        btn_browse_p = QPushButton("📁 Chọn Từ Máy")
        btn_browse_p.setObjectName("SecondaryBtn")
        btn_browse_p.clicked.connect(self.browse_preset_file)

        btn_draw_new = QPushButton("✏️ Vẽ Vùng Mới")
        btn_draw_new.clicked.connect(self.start_draw_regions)

        btn_del_p = QPushButton("🗑️ Xóa Preset")
        btn_del_p.setObjectName("DangerBtn")
        btn_del_p.clicked.connect(self.on_delete_selected_preset)

        preset_actions.addWidget(btn_load_p)
        preset_actions.addWidget(btn_browse_p)
        preset_actions.addWidget(btn_draw_new)
        preset_actions.addWidget(btn_del_p)

        self.list_presets = QListWidget()
        self.list_presets.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_presets.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_presets.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.refresh_preset_list()

        preset_layout.addWidget(self.list_presets)
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
        self.sa_status_page.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sa_status_page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        self.sa_checkin_page.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sa_checkin_page.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        self.lbl_misparked = QLabel("⚠️ Đỗ sai: 0")
        self.lbl_misparked.setStyleSheet("font-size: 14px; font-weight: bold; color: #E11D48;")
        for l in [self.lbl_in, self.lbl_out, self.lbl_occ]:
            l.setStyleSheet("font-size: 14px; font-weight: bold; color: #7B68EE;")
            sl.addWidget(l)
        sl.addWidget(self.lbl_misparked)

        layout.addWidget(self.f_stats)

        grid = QGridLayout()

        box1 = QVBoxLayout()
        box1.addWidget(QLabel("Thống Kê Theo Ô Đỗ"))
        self.table_slot = QTableWidget()
        self.table_slot.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_slot.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        if self.table_slot.verticalHeader() is not None:
            self.table_slot.verticalHeader().setVisible(False)  # type: ignore
        box1.addWidget(self.table_slot)
        grid.addLayout(box1, 0, 0)

        box2 = QVBoxLayout()
        box2.addWidget(QLabel("Lịch Sử Sự Kiện Gần Nhất"))
        self.table_hist = QTableWidget()
        self.table_hist.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_hist.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        if self.table_hist.verticalHeader() is not None:
            self.table_hist.verticalHeader().setVisible(False)  # type: ignore
        box2.addWidget(self.table_hist)
        grid.addLayout(box2, 0, 1)

        box3 = QVBoxLayout()
        box3.addWidget(QLabel("⚠️ Vi Phạm Đỗ Sai Vị Trí"))
        self.table_misparked = QTableWidget()
        self.table_misparked.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_misparked.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        if self.table_misparked.verticalHeader() is not None:
            self.table_misparked.verticalHeader().setVisible(False)  # type: ignore
        box3.addWidget(self.table_misparked)
        grid.addLayout(box3, 0, 2)

        layout.addLayout(grid)

        layout.addWidget(QLabel("Lịch Sử Quét Biển Số (ALPR)"))
        self.table_plates = QTableWidget()
        self.table_plates.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_plates.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(scroll_content)
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
        sw_left.setFixedWidth(110)
        sw_left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sw_right = QLabel("In App")
        sw_right.setStyleSheet("font-weight: bold; color: #7B68EE;")
        sw_right.setFixedWidth(55)
        sw_right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        sw_layout = QHBoxLayout()
        sw_layout.addWidget(sw_left)
        sw_layout.addWidget(self.switch_settings_view)
        sw_layout.addWidget(sw_right)

        mode_box.addLayout(sw_layout)
        card_layout.addLayout(mode_box)

        card_layout.addWidget(QFrame())

        # 1. Slot Numbering Display Switch
        slot_num_box = QHBoxLayout()
        slot_num_info = QVBoxLayout()
        slot_num_title = QLabel("🔢 Hiển Thị Số Thứ Tự Ô Đỗ")
        slot_num_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.lbl_slot_num_status = QLabel("Hiển thị số thứ tự ô đỗ (1, 2, 3...) khi nhận diện" if self.show_slot_numbers else "Ẩn số thứ tự ô đỗ trên khung nhận diện")
        self.lbl_slot_num_status.setObjectName("SubHeaderLabel")

        slot_num_info.addWidget(slot_num_title)
        slot_num_info.addWidget(self.lbl_slot_num_status)

        slot_num_box.addLayout(slot_num_info)
        slot_num_box.addStretch()

        self.switch_slot_num = ToggleSwitch()
        self.switch_slot_num.setChecked(self.show_slot_numbers)
        self.switch_slot_num.toggled.connect(self.on_toggle_slot_numbers)

        sw_sn_left = QLabel("Tắt")
        sw_sn_left.setObjectName("SubHeaderLabel")
        sw_sn_left.setFixedWidth(110)
        sw_sn_left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sw_sn_right = QLabel("Bật")
        sw_sn_right.setStyleSheet("font-weight: bold; color: #7B68EE;")
        sw_sn_right.setFixedWidth(55)
        sw_sn_right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        sw_sn_layout = QHBoxLayout()
        sw_sn_layout.addWidget(sw_sn_left)
        sw_sn_layout.addWidget(self.switch_slot_num)
        sw_sn_layout.addWidget(sw_sn_right)

        slot_num_box.addLayout(sw_sn_layout)
        card_layout.addLayout(slot_num_box)

        card_layout.addWidget(QFrame())

        # 2. Vehicle Bounding Box Switch
        bbox_box = QHBoxLayout()
        bbox_info = QVBoxLayout()
        bbox_title = QLabel("🚘 Khung Bao Xung Quanh Phương Tiện")
        bbox_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.lbl_bbox_status = QLabel("Hiển thị khung bao xung quanh phương tiện" if self.show_vehicle_bbox else "Ẩn khung bao xung quanh phương tiện")
        self.lbl_bbox_status.setObjectName("SubHeaderLabel")

        bbox_info.addWidget(bbox_title)
        bbox_info.addWidget(self.lbl_bbox_status)

        bbox_box.addLayout(bbox_info)
        bbox_box.addStretch()

        self.switch_vehicle_bbox = ToggleSwitch()
        self.switch_vehicle_bbox.setChecked(self.show_vehicle_bbox)
        self.switch_vehicle_bbox.toggled.connect(self.on_toggle_vehicle_bbox)

        sw_bbox_left = QLabel("Tắt")
        sw_bbox_left.setObjectName("SubHeaderLabel")
        sw_bbox_left.setFixedWidth(110)
        sw_bbox_left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sw_bbox_right = QLabel("Bật")
        sw_bbox_right.setStyleSheet("font-weight: bold; color: #7B68EE;")
        sw_bbox_right.setFixedWidth(55)
        sw_bbox_right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        sw_bbox_layout = QHBoxLayout()
        sw_bbox_layout.addWidget(sw_bbox_left)
        sw_bbox_layout.addWidget(self.switch_vehicle_bbox)
        sw_bbox_layout.addWidget(sw_bbox_right)

        bbox_box.addLayout(sw_bbox_layout)
        card_layout.addLayout(bbox_box)

        card_layout.addWidget(QFrame())

        # 3. Vehicle Center Dot Switch
        center_box = QHBoxLayout()
        center_info = QVBoxLayout()
        center_title = QLabel("🎯 Dấu Chấm Trung Tâm Phương Tiện")
        center_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.lbl_center_status = QLabel("Hiển thị dấu chấm tâm của phương tiện" if self.show_vehicle_center else "Ẩn dấu chấm tâm của phương tiện")
        self.lbl_center_status.setObjectName("SubHeaderLabel")

        center_info.addWidget(center_title)
        center_info.addWidget(self.lbl_center_status)

        center_box.addLayout(center_info)
        center_box.addStretch()

        self.switch_vehicle_center = ToggleSwitch()
        self.switch_vehicle_center.setChecked(self.show_vehicle_center)
        self.switch_vehicle_center.toggled.connect(self.on_toggle_vehicle_center)

        sw_cnt_left = QLabel("Tắt")
        sw_cnt_left.setObjectName("SubHeaderLabel")
        sw_cnt_left.setFixedWidth(110)
        sw_cnt_left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sw_cnt_right = QLabel("Bật")
        sw_cnt_right.setStyleSheet("font-weight: bold; color: #7B68EE;")
        sw_cnt_right.setFixedWidth(55)
        sw_cnt_right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        sw_cnt_layout = QHBoxLayout()
        sw_cnt_layout.addWidget(sw_cnt_left)
        sw_cnt_layout.addWidget(self.switch_vehicle_center)
        sw_cnt_layout.addWidget(sw_cnt_right)

        center_box.addLayout(sw_cnt_layout)
        card_layout.addLayout(center_box)

        card_layout.addWidget(QFrame())

        # 4. Misplaced Parking Warning Switch
        misparked_box = QHBoxLayout()
        misparked_info = QVBoxLayout()
        misparked_title = QLabel("⚠️ Cảnh Báo Xe Đỗ Sai Vị Trí")
        misparked_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #E11D48;")

        self.lbl_misparked_status = QLabel(
            f"Phát cảnh báo và lưu báo cáo khi xe đứng im khoảng {self.misparked_delay_sec}s lấn vào ô đỗ" if self.misparked_enabled else "Đã tắt cảnh báo đỗ sai vị trí"
        )
        self.lbl_misparked_status.setObjectName("SubHeaderLabel")

        misparked_info.addWidget(misparked_title)
        misparked_info.addWidget(self.lbl_misparked_status)

        misparked_box.addLayout(misparked_info)
        misparked_box.addStretch()

        self.switch_misparked = ToggleSwitch()
        self.switch_misparked.setChecked(self.misparked_enabled)
        self.switch_misparked.toggled.connect(self.on_toggle_misparked)

        sw_mp_left = QLabel("Tắt")
        sw_mp_left.setObjectName("SubHeaderLabel")
        sw_mp_left.setFixedWidth(110)
        sw_mp_left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sw_mp_right = QLabel("Bật")
        sw_mp_right.setStyleSheet("font-weight: bold; color: #E11D48;")
        sw_mp_right.setFixedWidth(55)
        sw_mp_right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        sw_mp_layout = QHBoxLayout()
        sw_mp_layout.addWidget(sw_mp_left)
        sw_mp_layout.addWidget(self.switch_misparked)
        sw_mp_layout.addWidget(sw_mp_right)

        misparked_box.addLayout(sw_mp_layout)
        card_layout.addLayout(misparked_box)

        card_layout.addWidget(QFrame())

        # 5. Stationary Duration Selector Dropdown (QComboBox)
        delay_box = QHBoxLayout()
        delay_info = QVBoxLayout()
        delay_title = QLabel("⏱️ Thời Gian Chờ Cảnh Báo")
        delay_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        delay_desc = QLabel("Thời gian phương tiện phải dừng hoàn toàn trước khi hệ thống báo vi phạm.")
        delay_desc.setObjectName("SubHeaderLabel")

        delay_info.addWidget(delay_title)
        delay_info.addWidget(delay_desc)

        delay_box.addLayout(delay_info)
        delay_box.addStretch()

        self.combo_misparked_delay = QComboBox()
        self.combo_misparked_delay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_misparked_delay.setMinimumWidth(140)
        self.combo_misparked_delay.setFixedHeight(36)

        for sec in range(5, 31):
            self.combo_misparked_delay.addItem(f"{sec} giây", userData=sec)

        curr_delay = int(getattr(self, 'misparked_delay_sec', 10))
        matching_idx = 5  # default 10s (5s is idx 0)
        for idx in range(self.combo_misparked_delay.count()):
            if self.combo_misparked_delay.itemData(idx) == curr_delay:
                matching_idx = idx
                break
        self.combo_misparked_delay.setCurrentIndex(matching_idx)
        self.combo_misparked_delay.currentIndexChanged.connect(self.on_misparked_delay_combo_changed)

        delay_box.addWidget(self.combo_misparked_delay)
        card_layout.addLayout(delay_box)

        card_layout.addWidget(QFrame())

        # 6. Show/Hide Stationary Timer Badge Switch
        timer_badge_box = QHBoxLayout()
        timer_badge_info = QVBoxLayout()
        timer_badge_title = QLabel("⏳ Thẻ Đếm Giây Xe Đang Dừng")
        timer_badge_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.lbl_timer_badge_status = QLabel(
            "Hiển thị thẻ màu vàng đếm ngược giây đang dừng (Xs/10s) trên luồng camera" if self.show_stationary_timer else "Ẩn thẻ đếm giây vàng (chỉ hiển thị nhãn đỏ khi vi phạm)"
        )
        self.lbl_timer_badge_status.setObjectName("SubHeaderLabel")

        timer_badge_info.addWidget(timer_badge_title)
        timer_badge_info.addWidget(self.lbl_timer_badge_status)

        timer_badge_box.addLayout(timer_badge_info)
        timer_badge_box.addStretch()

        self.switch_stationary_timer = ToggleSwitch()
        self.switch_stationary_timer.setChecked(self.show_stationary_timer)
        self.switch_stationary_timer.toggled.connect(self.on_toggle_stationary_timer)

        sw_timer_left = QLabel("Tắt")
        sw_timer_left.setObjectName("SubHeaderLabel")
        sw_timer_left.setFixedWidth(110)
        sw_timer_left.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sw_timer_right = QLabel("Bật")
        sw_timer_right.setStyleSheet("font-weight: bold; color: #7B68EE;")
        sw_timer_right.setFixedWidth(55)
        sw_timer_right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        sw_timer_layout = QHBoxLayout()
        sw_timer_layout.addWidget(sw_timer_left)
        sw_timer_layout.addWidget(self.switch_stationary_timer)
        sw_timer_layout.addWidget(sw_timer_right)

        timer_badge_box.addLayout(sw_timer_layout)
        card_layout.addLayout(timer_badge_box)

        card_layout.addWidget(QFrame())

        # 7. Debounce Delay Control Dropdown
        debounce_box = QHBoxLayout()
        debounce_info = QVBoxLayout()
        debounce_title = QLabel("🛡️ Debounce Delay chống nhiễu")
        debounce_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        debounce_desc = QLabel("Độ trễ thời gian duy trì trạng thái ổn định trước khi xác nhận có xe vào/ra ô đỗ.")
        debounce_desc.setObjectName("SubHeaderLabel")

        debounce_info.addWidget(debounce_title)
        debounce_info.addWidget(debounce_desc)

        debounce_box.addLayout(debounce_info)
        debounce_box.addStretch()

        self.combo_debounce_delay = QComboBox()
        self.combo_debounce_delay.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_debounce_delay.setMinimumWidth(180)
        self.combo_debounce_delay.setFixedHeight(36)

        debounce_options = [
            (0.2, "0.2 giây (Siêu nhạy)"),
            (0.3, "0.3 giây (Nhanh)"),
            (0.5, "0.5 giây (Mặc định)"),
            (1.0, "1.0 giây (Ổn định)"),
            (1.5, "1.5 giây (Chậm)"),
            (2.0, "2.0 giây (Rất chậm)"),
            (3.0, "3.0 giây (Chống nhiễu cao)"),
            (5.0, "5.0 giây (Cực kỳ ổn định)"),
            (10.0, "10.0 giây (Độ trễ cao)")
        ]

        for sec_val, label_str in debounce_options:
            self.combo_debounce_delay.addItem(label_str, userData=sec_val)

        curr_db_sec = float(getattr(self, 'debounce_delay_sec', 0.5))
        db_matching_idx = 2  # default 0.5s
        for idx in range(self.combo_debounce_delay.count()):
            if abs(self.combo_debounce_delay.itemData(idx) - curr_db_sec) < 0.05:
                db_matching_idx = idx
                break
        self.combo_debounce_delay.setCurrentIndex(db_matching_idx)
        self.combo_debounce_delay.currentIndexChanged.connect(self.on_debounce_delay_combo_changed)

        debounce_box.addWidget(self.combo_debounce_delay)
        card_layout.addLayout(debounce_box)

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
        self.btn_alpr.toggled.connect(self.toggle_alpr)
        self.toggle_alpr(False)

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

        # Guidance Box Target Screen Setting Row (Styled identically to setting rows above)
        screen_box = QHBoxLayout()
        screen_info = QVBoxLayout()
        screen_title = QLabel("🖥️ Màn Hình Hiển Thị Box Hướng Dẫn Xe Vào Ô Đỗ")
        screen_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.lbl_screen_status = QLabel("Chọn màn hình kết nối sẽ xuất hiện cửa sổ Hướng Dẫn Xe Vào Ô Đỗ khi bấm Check-In.")
        self.lbl_screen_status.setObjectName("SubHeaderLabel")

        screen_info.addWidget(screen_title)
        screen_info.addWidget(self.lbl_screen_status)

        screen_box.addLayout(screen_info)
        screen_box.addStretch()

        self.combo_guidance_screen = QComboBox()
        self.combo_guidance_screen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo_guidance_screen.setMinimumWidth(260)
        self.combo_guidance_screen.currentIndexChanged.connect(self.on_screen_selection_changed)

        screen_box.addWidget(self.combo_guidance_screen)
        card_layout.addLayout(screen_box)

        # Populate screen dropdown options
        self.refresh_guidance_screen_combo()

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

        scroll_area.setWidget(scroll_content)
        page_layout.addWidget(scroll_area)
        return page

    # ================= LOGIC & THEME MANAGEMENT =================

    # ================= CONFIG & SCREEN MANAGEMENT =================

    def load_app_config(self):
        new_config_path = os.path.join("config", "app_config.json")
        old_config_path = os.path.join("presets", "app_config.json")

        if not os.path.exists(new_config_path) and os.path.exists(old_config_path):
            try:
                os.makedirs("config", exist_ok=True)
                shutil.move(old_config_path, new_config_path)
            except Exception as e:
                print("Error migrating app config:", e)

        config_path = new_config_path if os.path.exists(new_config_path) else old_config_path
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.selected_guidance_screens = data.get("selected_guidance_screens", [0])
                    self.show_video_embedded = data.get("show_video_embedded", True)
                    self.show_slot_numbers = data.get("show_slot_numbers", True)
                    self.show_vehicle_bbox = data.get("show_vehicle_bbox", True)
                    self.show_vehicle_center = data.get("show_vehicle_center", True)
                    self.misparked_enabled = data.get("misparked_enabled", True)
                    self.misparked_delay_sec = data.get("misparked_delay_sec", 10)
                    self.show_stationary_timer = data.get("show_stationary_timer", True)
                    self.debounce_delay_sec = float(data.get("debounce_delay_sec", 0.5))
        except Exception as e:
            print("Error loading app config:", e)

    def save_app_config(self):
        if not os.path.exists("config"):
            os.makedirs("config", exist_ok=True)
        config_path = os.path.join("config", "app_config.json")
        try:
            data = {
                "selected_guidance_screens": self.selected_guidance_screens,
                "show_video_embedded": self.show_video_embedded,
                "show_slot_numbers": self.show_slot_numbers,
                "show_vehicle_bbox": self.show_vehicle_bbox,
                "show_vehicle_center": self.show_vehicle_center,
                "misparked_enabled": self.misparked_enabled,
                "misparked_delay_sec": self.misparked_delay_sec,
                "show_stationary_timer": self.show_stationary_timer,
                "debounce_delay_sec": self.debounce_delay_sec
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Error saving app config:", e)

    def _on_screens_changed(self, screen=None):
        self.refresh_guidance_screen_combo()

    def refresh_guidance_screen_combo(self):
        if not hasattr(self, 'combo_guidance_screen'):
            return

        self.combo_guidance_screen.blockSignals(True)
        self.combo_guidance_screen.clear()

        screens = QApplication.screens()
        primary_screen = QApplication.primaryScreen()

        for idx, scr in enumerate(screens):
            geo = scr.geometry()
            is_primary = (scr == primary_screen)
            text = f"Màn hình {idx + 1}: {geo.width()}x{geo.height()} px"
            if is_primary:
                text += " (Chính)"
            self.combo_guidance_screen.addItem(text, userData=[idx])

        if len(screens) > 1:
            self.combo_guidance_screen.addItem("🖥️ Tất cả các màn hình", userData=list(range(len(screens))))

        # Select target index based on saved config
        selected_index = 0
        if hasattr(self, 'selected_guidance_screens'):
            if len(screens) > 1 and len(self.selected_guidance_screens) == len(screens):
                selected_index = self.combo_guidance_screen.count() - 1
            elif self.selected_guidance_screens:
                first_idx = self.selected_guidance_screens[0]
                if 0 <= first_idx < len(screens):
                    selected_index = first_idx

        self.combo_guidance_screen.setCurrentIndex(selected_index)
        self.combo_guidance_screen.blockSignals(False)

    def on_screen_selection_changed(self, index):
        if index < 0 or not hasattr(self, 'combo_guidance_screen'):
            return
        user_data = self.combo_guidance_screen.itemData(index)
        if isinstance(user_data, list):
            self.selected_guidance_screens = user_data
        else:
            self.selected_guidance_screens = [index]
        self.save_app_config()

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
        self.save_app_config()

    def on_toggle_slot_numbers(self, checked):
        self.show_slot_numbers = checked
        if hasattr(self, 'lbl_slot_num_status'):
            if checked:
                self.lbl_slot_num_status.setText("Hiển thị số thứ tự ô đỗ (1, 2, 3...) khi nhận diện")
            else:
                self.lbl_slot_num_status.setText("Ẩn số thứ tự ô đỗ trên khung nhận diện")
        self.save_app_config()

    def on_toggle_vehicle_bbox(self, checked):
        self.show_vehicle_bbox = checked
        if hasattr(self, 'lbl_bbox_status'):
            if checked:
                self.lbl_bbox_status.setText("Hiển thị khung bao xung quanh phương tiện")
            else:
                self.lbl_bbox_status.setText("Ẩn khung bao xung quanh phương tiện")
        self.save_app_config()

    def on_toggle_vehicle_center(self, checked):
        self.show_vehicle_center = checked
        if hasattr(self, 'lbl_center_status'):
            if checked:
                self.lbl_center_status.setText("Hiển thị dấu chấm tâm của phương tiện")
            else:
                self.lbl_center_status.setText("Ẩn dấu chấm tâm của phương tiện")
        self.save_app_config()

    def on_toggle_misparked(self, checked):
        self.misparked_enabled = checked
        if hasattr(self, 'lbl_misparked_status'):
            if checked:
                self.lbl_misparked_status.setText(f"Phát cảnh báo và lưu báo cáo khi xe đứng im khoảng {self.misparked_delay_sec}s lấn vào ô đỗ")
            else:
                self.lbl_misparked_status.setText("Đã tắt cảnh báo đỗ sai vị trí")
        self.save_app_config()

    def on_misparked_delay_combo_changed(self, index):
        if not hasattr(self, 'combo_misparked_delay'):
            return
        sec = self.combo_misparked_delay.itemData(index)
        if sec is not None:
            self.misparked_delay_sec = int(sec)
            if hasattr(self, 'lbl_misparked_status') and self.misparked_enabled:
                self.lbl_misparked_status.setText(f"Phát cảnh báo và lưu báo cáo khi xe đứng im khoảng {self.misparked_delay_sec}s lấn vào ô đỗ")
            self.save_app_config()

    def on_toggle_stationary_timer(self, checked):
        self.show_stationary_timer = checked
        if hasattr(self, 'lbl_timer_badge_status'):
            if checked:
                self.lbl_timer_badge_status.setText("Hiển thị thẻ màu vàng đếm ngược giây đang dừng (Xs/10s) trên luồng camera")
            else:
                self.lbl_timer_badge_status.setText("Ẩn thẻ đếm giây vàng (chỉ hiển thị nhãn đỏ khi vi phạm)")
        self.save_app_config()

    def on_debounce_delay_combo_changed(self, index):
        if not hasattr(self, 'combo_debounce_delay'):
            return
        sec = self.combo_debounce_delay.itemData(index)
        if sec is not None:
            self.debounce_delay_sec = float(sec)
            self.save_app_config()

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
        if hasattr(self, 'btn_alpr'):
            self.toggle_alpr(self.btn_alpr.isChecked())

    def toggle_alpr(self, checked):
        self.alpr_enabled = checked
        if checked:
            self.btn_alpr.setText("📷 ALPR: BẬT")
            self.btn_alpr.setStyleSheet("""
                QPushButton {
                    background-color: #10B981;
                    color: #FFFFFF;
                    border: 1px solid #059669;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #059669;
                    color: #FFFFFF;
                }
            """)
        else:
            self.btn_alpr.setText("📷 ALPR: TẮT")
            if getattr(self, 'is_dark_mode', False):
                self.btn_alpr.setStyleSheet("""
                    QPushButton {
                        background-color: #282B3D;
                        color: #CBD5E1;
                        border: 1px solid #33374D;
                        border-radius: 8px;
                        padding: 8px 16px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #33374D;
                        color: #F1F5F9;
                    }
                """)
            else:
                self.btn_alpr.setStyleSheet("""
                    QPushButton {
                        background-color: #F1F5F9;
                        color: #334155;
                        border: 1px solid #CBD5E1;
                        border-radius: 8px;
                        padding: 8px 16px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #E2E8F0;
                        color: #0F172A;
                    }
                """)

    # ================= VIDEO TIMELINE RANGE SLIDER LOGIC =================

    def _format_sec_to_mmss(self, seconds):
        s = max(0, int(seconds))
        m = s // 60
        sec = s % 60
        return f"{m:02d}:{sec:02d}"

    def _probe_video_duration(self, file_path):
        try:
            import cv2
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                cap.release()
                if fps > 0 and total_frames > 0:
                    return int(total_frames / fps)
        except Exception:
            pass
        return 0

    def _on_range_slider_changed(self, low, high):
        self.entry_start.blockSignals(True)
        self.entry_end.blockSignals(True)

        self.entry_start.setText(str(low))
        max_val = self.range_slider.maximum() if hasattr(self, 'range_slider') else 0
        if high == max_val and max_val > 0:
            self.entry_end.setText("0")
        else:
            self.entry_end.setText(str(high))

        self.entry_start.blockSignals(False)
        self.entry_end.blockSignals(False)
        self._update_time_badge_labels(low, high)

    def _on_entry_start_changed(self, text):
        if not hasattr(self, 'range_slider'):
            return
        try:
            val = int(float(text)) if text.strip() else 0
            self.range_slider.setLowValue(val)
        except ValueError:
            pass

    def _on_entry_end_changed(self, text):
        if not hasattr(self, 'range_slider'):
            return
        try:
            val = int(float(text)) if text.strip() else 0
            if val == 0:
                val = self.range_slider.maximum()
            self.range_slider.setHighValue(val)
        except ValueError:
            pass

    def _update_time_badge_labels(self, low, high):
        if not hasattr(self, 'lbl_start_fmt'):
            return
        self.lbl_start_fmt.setText(f"({self._format_sec_to_mmss(low)})")
        
        max_val = self.range_slider.maximum() if hasattr(self, 'range_slider') else 0
        if high == max_val or high == 0:
            self.lbl_end_fmt.setText(f"({self._format_sec_to_mmss(max_val)} - Hết)")
        else:
            self.lbl_end_fmt.setText(f"({self._format_sec_to_mmss(high)})")

        span = max(0, (max_val if high == 0 else high) - low)
        if low == 0 and (high == max_val or high == 0):
            self.lbl_range_span.setText("🎯 Chạy toàn bộ video")
        else:
            self.lbl_range_span.setText(f"🎯 Khoảng: {self._format_sec_to_mmss(span)} ({span}s)")

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Chọn Video", "", "Video Files (*.mp4 *.avi *.mkv *.mov)")
        if file_path:
            self.video_path = file_path
            self.entry_video.setText(file_path)
            self.is_webcam = False
            self.btn_webcam.setText("📷 Sử Dụng Camera")
            self.polygons = []

            # Probe video duration using OpenCV
            duration_sec = self._probe_video_duration(file_path)
            if hasattr(self, 'range_slider'):
                self.range_slider.setEnabled(True)
                if duration_sec > 0:
                    self.range_slider.setRange(0, duration_sec)
                    self.range_slider.setValues(0, duration_sec)
                    self.entry_start.setText("0")
                    self.entry_end.setText("0")
                    self.lbl_time_duration.setText(f"⏳ Tổng: {self._format_sec_to_mmss(duration_sec)} ({duration_sec}s)")
                else:
                    self.range_slider.setRange(0, 300)
                    self.range_slider.setValues(0, 300)
                    self.entry_start.setText("0")
                    self.entry_end.setText("0")
                    self.lbl_time_duration.setText("⏳ Tổng: Không xác định")
            else:
                self.entry_start.setText("0")
                self.entry_end.setText("0")

    def browse_preset_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn File Preset (JSON)", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                polygons = [list(map(tuple, poly)) for poly in data.get("polygons", [])]
                if not polygons:
                    QMessageBox.warning(self, "Cảnh báo", "File preset không chứa dữ liệu ô đỗ hợp lệ.")
                    return

                preset_name = data.get("name") or os.path.splitext(os.path.basename(file_path))[0]

                # Save / copy preset to presets directory if not already there
                dest_path = os.path.join("presets", f"{preset_name}.json")
                if os.path.abspath(file_path) != os.path.abspath(dest_path):
                    if not os.path.exists("presets"):
                        os.makedirs("presets")
                    shutil.copy2(file_path, dest_path)

                self.polygons = polygons
                self.current_preset_name = preset_name
                self.refresh_preset_list()

                items = self.list_presets.findItems(preset_name, Qt.MatchFlag.MatchExactly)
                if items:
                    self.list_presets.setCurrentItem(items[0])

                QMessageBox.information(
                    self,
                    "Thành công",
                    f"Đã tải preset '{preset_name}' từ máy với {len(self.polygons)} ô đỗ."
                )
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể đọc file preset: {e}")

    def choose_webcam(self):
        choose_webcam_dialog(self)
        if hasattr(self, 'range_slider'):
            self.range_slider.setEnabled(False)
        if hasattr(self, 'lbl_time_duration'):
            self.lbl_time_duration.setText("⏳ Trực tiếp (Camera Live)")

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
        show_checkin_guidance_dialog(self, slot_id, self.selected_guidance_screens)
        self._refresh_checkin_page()

    # ================= PAGE REFRESHERS =================

    def _build_compact_slot_grid(self, status):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        gl = QGridLayout(w)
        gl.setContentsMargins(4, 4, 4, 4)
        gl.setSpacing(8)

        cols = 2
        tot = len(status)

        for idx in range(tot):
            slot = idx + 1
            is_occ = status[idx]

            badge = QFrame()
            badge.setFrameShape(QFrame.Shape.NoFrame)
            bl = QHBoxLayout(badge)
            bl.setContentsMargins(10, 6, 10, 6)
            bl.setSpacing(6)
            bl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            dot = QWidget()
            dot.setFixedSize(8, 8)

            if is_occ:
                status_text = f"Ô {slot:02d}: Đã đỗ" if slot < 100 else f"Ô {slot}: Đã đỗ"
                if self.is_dark_mode:
                    badge_style = "QFrame { background-color: #2D1520; border: 1px solid #5F1D29; border-radius: 8px; }"
                    label_style = "color: #FF859B; font-weight: bold; font-size: 12px; background-color: transparent; border: none;"
                    dot_style = "background-color: #F43F5E; border-radius: 4px; border: none;"
                else:
                    badge_style = "QFrame { background-color: #FFF1F2; border: 1px solid #FECDD3; border-radius: 8px; }"
                    label_style = "color: #E11D48; font-weight: bold; font-size: 12px; background-color: transparent; border: none;"
                    dot_style = "background-color: #E11D48; border-radius: 4px; border: none;"
            else:
                status_text = f"Ô {slot:02d}: Trống" if slot < 100 else f"Ô {slot}: Trống"
                if self.is_dark_mode:
                    badge_style = "QFrame { background-color: #0D2818; border: 1px solid #14532D; border-radius: 8px; }"
                    label_style = "color: #4ADE80; font-weight: bold; font-size: 12px; background-color: transparent; border: none;"
                    dot_style = "background-color: #10B981; border-radius: 4px; border: none;"
                else:
                    badge_style = "QFrame { background-color: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; }"
                    label_style = "color: #16A34A; font-weight: bold; font-size: 12px; background-color: transparent; border: none;"
                    dot_style = "background-color: #16A34A; border-radius: 4px; border: none;"

            badge.setStyleSheet(badge_style)
            dot.setStyleSheet(dot_style)

            l = QLabel(status_text)
            l.setStyleSheet(label_style)

            bl.addWidget(dot)
            bl.addWidget(l)

            row = idx // cols
            col = idx % cols
            gl.addWidget(badge, row, col)

        grid_rows = (tot + cols - 1) // cols
        gl.setRowStretch(grid_rows, 1)
        return w

    def _refresh_status_page(self):
        status = self.last_poly_status
        if not status:
            self.lbl_free_count.setText("0")
            self.lbl_occ_count.setText("0")
            return

        empty_slots = [i + 1 for i, occ in enumerate(status) if not occ]
        occ_slots = [i + 1 for i, occ in enumerate(status) if occ]

        self.lbl_free_count.setText(str(len(empty_slots)))
        self.lbl_occ_count.setText(str(len(occ_slots)))

        self.sa_status_page.setWidget(self._build_compact_slot_grid(status))

    def _refresh_checkin_page(self):
        status = self.last_poly_status
        if not status:
            return

        self.sa_checkin_page.setWidget(self._build_compact_slot_grid(status))

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
            active_misparked = getattr(self, 'current_misparked_count', 0)
            self.lbl_misparked.setText(f"⚠️ Đỗ sai: {active_misparked}")

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

            misparked_list = self.db.get_misparked_history(15)
            self.table_misparked.setRowCount(len(misparked_list))
            self.table_misparked.setColumnCount(4)
            self.table_misparked.setHorizontalHeaderLabels(["Thời gian", "Ô đỗ", "Mã xe", "Trạng thái"])
            if self.table_misparked.horizontalHeader() is not None:
                self.table_misparked.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # type: ignore

            for r, ev in enumerate(misparked_list):
                try:
                    dt = datetime.strptime(ev["timestamp"], "%Y-%m-%d %H:%M:%S")
                    time_str = dt.strftime("%H:%M:%S")
                except Exception:
                    time_str = ev["timestamp"]

                self.table_misparked.setItem(r, 0, centered_item(time_str))
                self.table_misparked.setItem(r, 1, centered_item(f"Ô {ev['slot_id']}"))
                self.table_misparked.setItem(r, 2, centered_item(ev["vehicle_id"] or ""))

                item_mp = centered_item("ĐỖ SAI VỊ TRÍ")
                item_mp.setForeground(QColor("#E11D48"))
                font_mp = item_mp.font()
                font_mp.setBold(True)
                item_mp.setFont(font_mp)
                self.table_misparked.setItem(r, 3, item_mp)

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
