"""
Súbor: core/windows/custom_title_bar_mdi.py
Vlastná lišta pre MDI pod-okná (FramelessMdiSubWindow).
"""

import os
from PyQt6.QtWidgets import QWidget, QStyleOption, QStyle
from PyQt6.QtGui import QPainter, QIcon
from PyQt6 import uic
from PyQt6.QtCore import Qt, QSize

from core._path import Paths
from core.logic.language_manager import LanguageManager


class CustomTitleBarMdi(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent

        # DÔLEŽITÉ PRE QSS: Presný názov zhodný so štýlmi
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("CustomTitleBar")

        uic.loadUi(Paths.get_ui_file("custom_title_bar_mdi.ui"), self)
        self.lbl_icon.setScaledContents(False)
        self.old_pos = None

        # Vyčistenie textov z tlačidiel (ikony dodá výhradne QSS)
        self.btn_minimize.setText("")
        self.btn_maximize.setText("")
        self.btn_close.setText("")

        # Počiatočný stav pre QSS
        self.btn_maximize.setProperty("maximized", "false")

        self.connect_signals()
        self.setup_from_parent()

        if self.parent_window and hasattr(self.parent_window, 'windowTitleChanged'):
            self.parent_window.windowTitleChanged.connect(self.lbl_title.setText)

        LanguageManager.connect_language_changed(self.retranslate_ui)

    def paintEvent(self, event):
        """Vykreslenie QSS štýlov pozadia."""
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)
        super().paintEvent(event)

    def connect_signals(self):
        """Čisté volanie logiky pod-okna."""
        self.btn_minimize.clicked.connect(self.parent_window.do_minimize)
        self.btn_maximize.clicked.connect(self.parent_window.handle_maximize_restore_button)
        self.btn_close.clicked.connect(self.parent_window.close)

    def set_title(self, text: str):
        self.lbl_title.setText(text)

    # =========================================================================
    # INTELIGENTNÉ PREPÍNANIE IKONY MAXIMALIZE / RESTORE CEZ QSS
    # =========================================================================

    def set_maximized_state(self, is_maximized: bool):
        """
        Nastaví vlastnosť 'maximized' pre QSS.
        QSS samo rozhodne, či zobrazí čiernu alebo bielu ikonu podľa témy!
        """
        # Vyčistíme natvrdo nastavenú ikonu v Pythone, aby mal prednosť QSS štýl
        self.btn_maximize.setIcon(QIcon())
        
        val = "true" if is_maximized else "false"
        if self.btn_maximize.property("maximized") != val:
            self.btn_maximize.setProperty("maximized", val)
            self.btn_maximize.style().unpolish(self.btn_maximize)
            self.btn_maximize.style().polish(self.btn_maximize)
            self.btn_maximize.update()

    def set_maximize_icon(self, icon_filename: str):
        """
        Automatická oprava starých volaní z main_window_logic.py:
        Zistí stav zo slova 'restore' a odovzdá riadenie QSS.
        """
        is_max = "restore" in icon_filename.lower()
        self.set_maximized_state(is_max)

    def _set_maximize_button_icon(self, icon_filename: str):
        self.set_maximize_icon(icon_filename)

    # =========================================================================

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

    # ========================================================
    # PRESÚVANIE MDI OKNA MYŠOU ZA LIŠTU
    # ========================================================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        is_maximized = getattr(self.parent_window, '_is_maximized_mode', False) or (getattr(self.parent_window, '_mode', '') == 'maximized')
        if self.old_pos and not is_maximized:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.parent_window.move(
                self.parent_window.x() + delta.x(),
                self.parent_window.y() + delta.y()
            )
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        if hasattr(self.parent_window, 'controller') and self.parent_window.controller:
            self.parent_window.controller.save_states()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_window.handle_maximize_restore_button()