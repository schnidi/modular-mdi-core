"""
Súbor: core/windows/custom_title_bar.py
"""

import os
from PyQt6.QtWidgets import QWidget, QStyleOption, QStyle
from PyQt6.QtGui import QPainter, QIcon, QDesktopServices
from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize, QUrl

from core._path import Paths
from core.logic.services.about_logic import AboutLogic
from core.logic.services.github_update import GitHubUpdate
from core.logic.language_manager import LanguageManager


class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("CustomTitleBar")

        uic.loadUi(Paths.get_ui_file("custom_title_bar.ui"), self)
        self.lbl_icon.setScaledContents(False)
        self.old_pos = None

        self.btn_minimize.setText("")
        self.btn_maximize.setText("")
        self.btn_close.setText("")
        if hasattr(self, 'btn_about'):
            self.btn_about.setText("")
        if hasattr(self, 'btn_update_github'):
            self.btn_update_github.setText("")
            self.btn_update_github.hide()

        self.connect_signals()
        self.setup_from_parent()

        if self.parent_window and hasattr(self.parent_window, 'windowTitleChanged'):
            self.parent_window.windowTitleChanged.connect(self.lbl_title.setText)

        self.refresh_update_button()
        LanguageManager.connect_language_changed(self.retranslate_ui)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        super().paintEvent(event)

    def connect_signals(self):
        self.btn_minimize.clicked.connect(self._on_minimize)
        self.btn_maximize.clicked.connect(self.toggle_maximize_restore)
        self.btn_close.clicked.connect(self.parent_window.close)
        self.btn_about.clicked.connect(self.show_about_dialog)

        if hasattr(self, 'btn_update_github'):
            self.btn_update_github.clicked.connect(self.open_update_url)

    def _on_minimize(self):
        if hasattr(self.parent_window, 'do_minimize'):
            self.parent_window.do_minimize()
        else:
            self.parent_window.showMinimized()

    def toggle_maximize_restore(self):
        if hasattr(self.parent_window, 'handle_maximize_restore_button'):
            self.parent_window.handle_maximize_restore_button()
            return

        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self._set_maximize_button_icon("maximize_white.svg")
        else:
            self.parent_window.showMaximized()
            self._set_maximize_button_icon("restore_white.svg")

    def set_title(self, text: str):
        self.lbl_title.setText(text)

    def setup_from_parent(self):
        if self.parent_window and self.parent_window.windowTitle():
            self.lbl_title.setText(self.parent_window.windowTitle())

        icon_path = Paths.get_icon_path("app.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            size = 20
            self.lbl_icon.setFixedSize(size, size)
            smooth_pixmap = icon.pixmap(size, size)
            self.lbl_icon.setPixmap(smooth_pixmap)
            self.lbl_icon.show()
        else:
            self.lbl_icon.hide()

    def retranslate_ui(self, lang_code: str = None):
        LanguageManager.translate_ui(self)
        if self.parent_window and self.parent_window.windowTitle():
            self.lbl_title.setText(self.parent_window.windowTitle())
        self.refresh_update_button()

    def refresh_update_button(self):
        if not hasattr(self, 'btn_update_github'):
            return
        has_update = GitHubUpdate.get_status()
        if has_update:
            self.btn_update_github.show()
        else:
            self.btn_update_github.hide()

    def open_update_url(self):
        url_str = GitHubUpdate.get_download_url()
        QDesktopServices.openUrl(QUrl(url_str))

    def show_about_dialog(self):
        AboutLogic.show_about_dialog(self.parent_window)

    def toggle_maximize_restore(self):
        if hasattr(self.parent_window, 'toggle_maximize'):
            self.parent_window.toggle_maximize()
            return

        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
            self._set_maximize_button_icon("maximize_white.svg")
        else:
            self.parent_window.showMaximized()
            self._set_maximize_button_icon("restore_white.svg")

    def _set_maximize_button_icon(self, icon_filename: str):
        icon_path = Paths.get_icon_path(icon_filename)
        if os.path.exists(icon_path):
            self.btn_maximize.setIcon(QIcon(icon_path))
            self.btn_maximize.setIconSize(QSize(12, 12))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        is_maximized = getattr(self.parent_window, '_is_custom_maximized', False) or self.parent_window.isMaximized()
        if self.old_pos and not is_maximized and (event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.globalPosition().toPoint() - self.old_pos
            raw_target_pos = self.parent_window.pos() + delta

            # Vopred orežeme na mantinely — žiadny záblesk ani pretečenie nevznikne
            from core.logic.services.window_bounds_manager import WindowBoundsManager
            clamped_pos = WindowBoundsManager.get_clamped_position(self.parent_window, raw_target_pos)

            self.parent_window.move(clamped_pos)
            self.old_pos = event.globalPosition().toPoint()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        event.accept()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize_restore()