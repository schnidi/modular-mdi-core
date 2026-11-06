# Súbor: core/windows/custom_title_bar_mdi.py

import os
from PyQt6.QtWidgets import QWidget, QStyleOption, QStyle
from PyQt6.QtGui import QPainter, QIcon
from PyQt6 import uic
from PyQt6.QtCore import Qt

from core._path import Paths
from core.logic.language_manager import LanguageManager


class CustomTitleBarMdi(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("CustomTitleBar")

        uic.loadUi(Paths.get_ui_file("custom_title_bar_mdi.ui"), self)
        self.lbl_icon.setScaledContents(False)

        # Absolútne súradnice pre 100% plynulý drag bez straty subpixelov
        self._drag_start_global = None
        self._drag_start_window_pos = None

        self.lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.lbl_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.btn_minimize.setText("")
        self.btn_maximize.setText("")
        self.btn_close.setText("")

        self.btn_maximize.setProperty("maximized", "false")

        self.connect_signals()
        self.setup_from_parent()

        LanguageManager.connect_language_changed(self.retranslate_ui)
        self.retranslate_ui()

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)

    def connect_signals(self):
        self.btn_minimize.clicked.connect(self.parent_window.do_minimize)
        self.btn_maximize.clicked.connect(self.parent_window.handle_maximize_restore_button)
        self.btn_close.clicked.connect(self.parent_window.close)

    def set_title(self, text: str):
        self.lbl_title.setText(text)

    def set_minimized_state(self, is_minimized: bool):
        if hasattr(self, 'btn_minimize'):
            self.btn_minimize.setVisible(not is_minimized)

    def set_maximized_state(self, is_maximized: bool):
        self.btn_maximize.setIcon(QIcon())
        val = "true" if is_maximized else "false"
        if self.btn_maximize.property("maximized") != val:
            self.btn_maximize.setProperty("maximized", val)
            self.btn_maximize.style().unpolish(self.btn_maximize)
            self.btn_maximize.style().polish(self.btn_maximize)
            self.btn_maximize.update()

    def set_maximize_icon(self, icon_filename: str):
        is_max = "restore" in icon_filename.lower()
        self.set_maximized_state(is_max)

    def setup_from_parent(self):
        if self.parent_window and self.parent_window.windowTitle():
            self.lbl_title.setText(self.parent_window.windowTitle())

        self.lbl_icon.setFixedSize(20, 20)

        # 1. Ak ikonu nastavilo QSS (cez qproperty-pixmap), nerobíme nič a necháme QSS
        current_pixmap = self.lbl_icon.pixmap()
        if current_pixmap and not current_pixmap.isNull():
            self.lbl_icon.show()
            return

        # 2. Bezpečný fallback natvrdo, ak v QSS pravidlo chýba
        icon_path = Paths.get_icon_path("app.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            smooth_pixmap = icon.pixmap(20, 20)
            self.lbl_icon.setPixmap(smooth_pixmap)
            self.lbl_icon.show()
        else:
            self.lbl_icon.hide()

    def retranslate_ui(self, lang_code: str = None):
        if hasattr(self.parent_window, "client_widget") and self.parent_window.client_widget:
            key = self.parent_window.client_widget.objectName()
            new_title = LanguageManager.get(key)
            if new_title and new_title != key:
                self.set_title(new_title)
                self.parent_window.setWindowTitle(new_title)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_global = event.globalPosition().toPoint()
            self._drag_start_window_pos = self.parent_window.pos()
            is_maximized = (
                getattr(self.parent_window, '_is_maximized_mode', False)
                or (getattr(self.parent_window, '_mode', '') == 'maximized')
            )
            if not is_maximized and hasattr(self.parent_window, 'start_title_drag'):
                self.parent_window.start_title_drag(self._drag_start_global)
            event.accept()

    def mouseMoveEvent(self, event):
        is_maximized = (
            getattr(self.parent_window, '_is_maximized_mode', False)
            or (getattr(self.parent_window, '_mode', '') == 'maximized')
        )
        if self._drag_start_global is not None and not is_maximized and (event.buttons() & Qt.MouseButton.LeftButton):
            if hasattr(self.parent_window, 'update_title_drag'):
                self.parent_window.update_title_drag(event.globalPosition().toPoint())
                event.accept()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if hasattr(self.parent_window, 'end_title_drag'):
            self.parent_window.end_title_drag()
        self._drag_start_global = None
        self._drag_start_window_pos = None
        if hasattr(self.parent_window, 'controller') and self.parent_window.controller:
            self.parent_window.controller.save_states()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_window.handle_maximize_restore_button()


# =========================================================================
# POISTKA: Ak by niekto hľadal CustomTitleBar v tomto súbore, nespadne to!
# =========================================================================
CustomTitleBar = CustomTitleBarMdi