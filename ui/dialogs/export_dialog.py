import os
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QDateEdit, QTimeEdit,
    QFileDialog, QMessageBox, QFrame, QWidget, QAbstractSpinBox
)
from PyQt6.QtCore import Qt, QDate, QTime

from ui.theme import set_titlebar_theme
from logic.excel_exporter import export_parking_report_to_excel


class OptionCard(QFrame):
    """ClickUp-style selectable Option Card container."""

    def __init__(self, title_text, description_text, parent=None):
        super().__init__(parent)
        self.setObjectName("OptionCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 14, 16, 14)
        self.layout.setSpacing(8)

        # Header with Radio button
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(10)

        self.radio = QRadioButton(title_text)
        self.radio.setStyleSheet("""
            QRadioButton {
                font-weight: bold;
                font-size: 14px;
            }
        """)
        self.header_layout.addWidget(self.radio)
        self.header_layout.addStretch()
        self.layout.addLayout(self.header_layout)

        if description_text:
            self.lbl_desc = QLabel(description_text)
            self.lbl_desc.setObjectName("SubHeaderLabel")
            self.lbl_desc.setWordWrap(True)
            self.layout.addWidget(self.lbl_desc)

        # Content container layout for custom controls
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 6, 0, 4)
        self.content_layout.setSpacing(10)
        self.layout.addWidget(self.content_widget)

    def mousePressEvent(self, event):
        self.radio.setChecked(True)
        super().mousePressEvent(event)


class ExportReportDialog(QDialog):
    def __init__(self, parent_ui):
        super().__init__(parent_ui)
        self.parent_ui = parent_ui
        self.db = parent_ui.db

        self.setWindowTitle("📊 Xuất Báo Cáo Excel")
        self.setMinimumWidth(540)
        self._init_ui()
        self.apply_clickup_styles()
        set_titlebar_theme(self, parent_ui.is_dark_mode)

    def apply_clickup_styles(self):
        is_dark = getattr(self.parent_ui, 'is_dark_mode', False)

        if is_dark:
            bg_card = "#1E2030"
            border_normal = "#2C2E43"
            border_hover = "#8B5CF6"
            bg_selected = "#252243"
            border_selected = "#8B5CF6"
            text_primary = "#F8FAFC"
            text_muted = "#94A3B8"
            input_bg = "#161824"
            input_border = "#33374D"
            pill_bg = "#26293B"
            pill_hover = "#33374D"
            pill_active_bg = "#7C3AED"
            pill_active_fg = "#FFFFFF"
        else:
            bg_card = "#FFFFFF"
            border_normal = "#E2E8F0"
            border_hover = "#7B68EE"
            bg_selected = "#F5F3FF"
            border_selected = "#7B68EE"
            text_primary = "#0F172A"
            text_muted = "#64748B"
            input_bg = "#FFFFFF"
            input_border = "#CBD5E1"
            pill_bg = "#F1F5F9"
            pill_hover = "#E2E8F0"
            pill_active_bg = "#7B68EE"
            pill_active_fg = "#FFFFFF"

        self.style_sheet_custom = f"""
            QDialog {{
                background-color: {"#12131C" if is_dark else "#F8FAFC"};
                font-family: 'Segoe UI', system-ui, sans-serif;
            }}
            QFrame#OptionCard {{
                background-color: {bg_card};
                border: 2px solid {border_normal};
                border-radius: 12px;
            }}
            QFrame#OptionCard:hover {{
                border-color: {border_hover};
            }}
            QFrame#OptionCard[selected="true"] {{
                background-color: {bg_selected};
                border-color: {border_selected};
            }}
            QLabel#DialogTitle {{
                font-size: 17px;
                font-weight: bold;
                color: {text_primary};
            }}
            QLabel#SubHeaderLabel {{
                font-size: 12px;
                color: {text_muted};
            }}

            /* Modern Pill Preset Buttons - Fully Rounded Pill Style */
            QPushButton#PresetPill {{
                background-color: {pill_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 16px;
                padding: 7px 16px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton#PresetPill:hover {{
                background-color: {pill_hover};
                border-color: {border_hover};
            }}
            QPushButton#PresetPill[active="true"] {{
                background-color: {pill_active_bg};
                color: {pill_active_fg};
                border-color: {pill_active_bg};
                font-weight: bold;
            }}

            /* Clean Flat Date & Time Edit Controls without ANY internal buttons */
            QDateEdit, QTimeEdit {{
                background-color: {input_bg};
                color: {text_primary};
                border: 1px solid {input_border};
                border-radius: 10px;
                padding: 7px 12px;
                font-weight: 600;
                font-size: 13px;
                min-height: 22px;
            }}
            QDateEdit:focus, QTimeEdit:focus {{
                border: 2px solid {border_hover};
            }}

            /* Hide ALL internal buttons (up/down spin & calendar drop-down) */
            QDateEdit::up-button, QTimeEdit::up-button,
            QDateEdit::down-button, QTimeEdit::down-button,
            QDateEdit::drop-down, QTimeEdit::drop-down {{
                width: 0px;
                height: 0px;
                border: none;
                background: transparent;
            }}
            QDateEdit::up-arrow, QTimeEdit::up-arrow,
            QDateEdit::down-arrow, QTimeEdit::down-arrow,
            QDateEdit::drop-down:hover, QTimeEdit::drop-down:hover {{
                image: none;
                width: 0px;
                height: 0px;
                border: none;
                background: transparent;
            }}

            QPushButton#ClickUpExportBtn {{
                background-color: #7C3AED;
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton#ClickUpExportBtn:hover {{
                background-color: #6D28D9;
            }}
            QPushButton#ClickUpExportBtn:pressed {{
                background-color: #5B21B6;
            }}
            QPushButton#ClickUpCancelBtn {{
                background-color: transparent;
                color: {text_muted};
                border: 1px solid {input_border};
                border-radius: 10px;
                padding: 10px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#ClickUpCancelBtn:hover {{
                background-color: {pill_hover};
                color: {text_primary};
            }}
        """
        self.setStyleSheet(self.style_sheet_custom)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # ----------------------------------------------------
        # 1. Header Component (ClickUp Style)
        # ----------------------------------------------------
        header_card = QFrame()
        header_card.setObjectName("OptionCard")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(16, 14, 16, 14)

        icon_lbl = QLabel("📊")
        icon_lbl.setStyleSheet("font-size: 26px;")
        h_layout.addWidget(icon_lbl)

        v_title = QVBoxLayout()
        v_title.setSpacing(2)
        lbl_title = QLabel("Xuất Báo Cáo Excel Bãi Đỗ Xe")
        lbl_title.setObjectName("DialogTitle")
        lbl_sub = QLabel("Tùy chọn khung giờ trong ngày hoặc toàn bộ lịch sử để trích xuất báo cáo")
        lbl_sub.setObjectName("SubHeaderLabel")
        v_title.addWidget(lbl_title)
        v_title.addWidget(lbl_sub)

        h_layout.addLayout(v_title)
        h_layout.addStretch()

        main_layout.addWidget(header_card)

        # ----------------------------------------------------
        # 2. Quick Presets Bar (Pill Chips Component)
        # ----------------------------------------------------
        preset_bar = QHBoxLayout()
        preset_bar.setSpacing(8)
        
        lbl_p = QLabel("Chọn nhanh:")
        lbl_p.setObjectName("SubHeaderLabel")
        lbl_p.setStyleSheet("font-weight: bold;")
        preset_bar.addWidget(lbl_p)

        self.preset_pills = []
        presets_data = [
            ("Hôm Nay", self._preset_today),
            ("Hôm Qua", self._preset_yesterday),
            ("7 Ngày Qua", self._preset_7days),
            ("Tháng Này", self._preset_month)
        ]

        for text, handler in presets_data:
            btn = QPushButton(text)
            btn.setObjectName("PresetPill")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, h=handler, b=btn: self._on_preset_clicked(h, b))
            preset_bar.addWidget(btn)
            self.preset_pills.append(btn)

        preset_bar.addStretch()
        main_layout.addLayout(preset_bar)

        # ----------------------------------------------------
        # 3. Filter Mode Cards (ClickUp Separated Components)
        # ----------------------------------------------------
        self.btn_group = QButtonGroup(self)

        # CARD 1: Time of Day Range (Lọc theo Khung Giờ Trong Ngày)
        self.card_tod = OptionCard(
            "⏰  Lọc theo Khung Giờ Trong Ngày",
            "Chọn khoảng ngày và khung giờ xuất (Ví dụ: Từ 08:00 đến 17:30)."
        )
        self.btn_group.addButton(self.card_tod.radio, 1)

        tod_dates = QHBoxLayout()
        tod_dates.setSpacing(12)
        tod_dates.addWidget(QLabel("Từ ngày:"))
        self.date_tod_start = QDateEdit(QDate.currentDate().addDays(-7))
        self.date_tod_start.setDisplayFormat("dd/MM/yyyy")
        self.date_tod_start.setCalendarPopup(False)
        self.date_tod_start.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        tod_dates.addWidget(self.date_tod_start)

        tod_dates.addWidget(QLabel("Đến ngày:"))
        self.date_tod_end = QDateEdit(QDate.currentDate())
        self.date_tod_end.setDisplayFormat("dd/MM/yyyy")
        self.date_tod_end.setCalendarPopup(False)
        self.date_tod_end.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        tod_dates.addWidget(self.date_tod_end)
        tod_dates.addStretch()
        self.card_tod.content_layout.addLayout(tod_dates)

        tod_hours = QHBoxLayout()
        tod_hours.setSpacing(12)
        tod_hours.addWidget(QLabel("Từ giờ:"))
        self.time_start = QTimeEdit(QTime(8, 0, 0))
        self.time_start.setDisplayFormat("HH:mm")
        self.time_start.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        tod_hours.addWidget(self.time_start)

        tod_hours.addWidget(QLabel("Đến giờ:"))
        self.time_end = QTimeEdit(QTime(17, 30, 0))
        self.time_end.setDisplayFormat("HH:mm")
        self.time_end.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        tod_hours.addWidget(self.time_end)

        lbl_hint = QLabel("(Khung giờ cố định mỗi ngày)")
        lbl_hint.setObjectName("SubHeaderLabel")
        tod_hours.addWidget(lbl_hint)
        tod_hours.addStretch()

        self.card_tod.content_layout.addLayout(tod_hours)
        main_layout.addWidget(self.card_tod)

        # CARD 2: All Historical Data (Tất Cả Dữ Liệu Lịch Sử)
        self.card_all = OptionCard(
            "🌐  Tất Cả Dữ Liệu Lịch Sử",
            "Xuất toàn bộ bản ghi xe vào/ra và biển số xe từ trước đến nay (không giới hạn thời gian)."
        )
        self.btn_group.addButton(self.card_all.radio, 2)
        main_layout.addWidget(self.card_all)

        # Connect Radio Toggles
        self.btn_group.idToggled.connect(self._on_mode_changed)

        # ----------------------------------------------------
        # 4. Action Footer Bar
        # ----------------------------------------------------
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 8, 0, 0)
        footer_layout.addStretch()

        btn_cancel = QPushButton("Hủy Bỏ")
        btn_cancel.setObjectName("ClickUpCancelBtn")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        footer_layout.addWidget(btn_cancel)

        self.btn_export = QPushButton("📊 Xuất File Excel (.xlsx)")
        self.btn_export.setObjectName("ClickUpExportBtn")
        self.btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export.clicked.connect(self._do_export)
        footer_layout.addWidget(self.btn_export)

        main_layout.addLayout(footer_layout)

        # Default initialization
        self.card_tod.radio.setChecked(True)
        self._preset_today()
        self._set_pill_active(self.preset_pills[0])
        self._on_mode_changed()

    def _on_preset_clicked(self, handler, clicked_btn):
        # Selecting a preset chip automatically selects Card 1 (Time of Day Range)
        self.card_tod.radio.setChecked(True)
        handler()
        self._set_pill_active(clicked_btn)

    def _set_pill_active(self, active_btn):
        for btn in self.preset_pills:
            if btn == active_btn:
                btn.setProperty("active", "true")
            else:
                btn.setProperty("active", "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_mode_changed(self):
        is_tod = self.card_tod.radio.isChecked()
        is_all = self.card_all.radio.isChecked()

        # Update card selected visual states
        for card, checked in [(self.card_tod, is_tod), (self.card_all, is_all)]:
            card.setProperty("selected", "true" if checked else "false")
            card.style().unpolish(card)
            card.style().polish(card)

        # Enable/Disable input widgets
        self.date_tod_start.setEnabled(is_tod)
        self.date_tod_end.setEnabled(is_tod)
        self.time_start.setEnabled(is_tod)
        self.time_end.setEnabled(is_tod)

    def _preset_today(self):
        self.date_tod_start.setDate(QDate.currentDate())
        self.date_tod_end.setDate(QDate.currentDate())

    def _preset_yesterday(self):
        y_date = QDate.currentDate().addDays(-1)
        self.date_tod_start.setDate(y_date)
        self.date_tod_end.setDate(y_date)

    def _preset_7days(self):
        self.date_tod_start.setDate(QDate.currentDate().addDays(-7))
        self.date_tod_end.setDate(QDate.currentDate())

    def _preset_month(self):
        now = datetime.now()
        self.date_tod_start.setDate(QDate(now.year, now.month, 1))
        self.date_tod_end.setDate(QDate.currentDate())

    def _do_export(self):
        filter_opts = {}

        if self.card_tod.radio.isChecked():
            start_date_q = self.date_tod_start.date()
            end_date_q = self.date_tod_end.date()

            if start_date_q > end_date_q:
                QMessageBox.warning(self, "Lỗi Ngày", "Ngày bắt đầu không được lớn hơn ngày kết thúc!")
                return

            t_start_q = self.time_start.time()
            t_end_q = self.time_end.time()

            filter_opts["start_dt"] = start_date_q.toString("yyyy-MM-dd") + " 00:00:00"
            filter_opts["end_dt"] = end_date_q.toString("yyyy-MM-dd") + " 23:59:59"
            filter_opts["start_time"] = t_start_q.toString("HH:mm:ss")
            filter_opts["end_time"] = t_end_q.toString("HH:mm:ss")
            filter_opts["filter_description"] = (
                f"Từ {start_date_q.toString('dd/MM/yyyy')} đến {end_date_q.toString('dd/MM/yyyy')}, "
                f"Khung giờ: {t_start_q.toString('HH:mm')} - {t_end_q.toString('HH:mm')}"
            )

        else:
            filter_opts["filter_description"] = "Tất cả dữ liệu lịch sử"

        # Ask for save file location
        default_filename = f"BaoCao_BaiDo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu File Báo Cáo Excel",
            default_filename,
            "Excel Files (*.xlsx);;All Files (*)"
        )

        if not file_path:
            return

        try:
            export_parking_report_to_excel(file_path, self.db, filter_opts)
            QMessageBox.information(
                self,
                "Xuất Excel Thành Công",
                f"✅ Đã xuất báo cáo Excel thành công!\n\n📁 File đã lưu tại:\n{file_path}"
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Xuất File", f"Không thể xuất file Excel:\n{e}")


def show_export_dialog(parent_ui):
    dialog = ExportReportDialog(parent_ui)
    if hasattr(parent_ui, 'fade_in'):
        parent_ui.fade_in(dialog)
    dialog.exec()
