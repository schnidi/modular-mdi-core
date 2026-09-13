"""
Súbor: core/windows/test_window.py
Obsahový widget pre testovacie MDI pod-okno.
"""

from PyQt6.QtWidgets import QWidget, QStyleOption, QStyle
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt
from PyQt6 import uic

from core._path import Paths
from core.logic.language_manager import LanguageManager


class TestWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("TestWindow")

        # Načítanie UI obsahu
        uic.loadUi(Paths.get_ui_file("test_window.ui"), self)

        # Prepojenie prekladov
        LanguageManager.connect_language_changed(self.retranslate_ui)

    def paintEvent(self, event):
        """Zabezpečí vykreslenie pozadia podľa QSS."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        super().paintEvent(event)

    def retranslate_ui(self, lang_code=None):
        LanguageManager.translate_ui(self)

    def closeEvent(self, event):
        LanguageManager.disconnect_language_changed(self.retranslate_ui)
        event.accept()