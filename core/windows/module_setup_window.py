"""
Súbor: core/windows/module_setup_window.py
Grafické okno správy a inštalácie modulov pre MDI plochu.
"""

from PyQt6.QtWidgets import QWidget, QStyleOption, QStyle, QSpacerItem, QSizePolicy
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import uic

from core._path import Paths
from core.logic.language_manager import LanguageManager
from core.windows.module_list_item import ModuleListItem


class ModuleSetupWindow(QWidget):
    """View pre správu, zapínanie a inštaláciu modulov."""

    # Signály, ktoré očakáva ModuleSetupController
    apply_changes_requested = pyqtSignal(dict)   # {module_name: is_enabled, ...}
    install_requested = pyqtSignal()
    uninstall_requested = pyqtSignal(str)        # module_name

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("ModuleSetupWindow")

        # Načítanie UI
        uic.loadUi(Paths.get_ui_file("module_setup_window.ui"), self)

        # Zoznam vytvorených položiek
        self.module_items = []

        # Prepojenie tlačidiel okna
        self.btn_install.clicked.connect(self.install_requested.emit)
        self.btn_apply.clicked.connect(self._on_apply_clicked)

        # Jazykový manažér
        LanguageManager.connect_language_changed(self.retranslate_ui)

    def paintEvent(self, event):
        """Vykreslenie QSS pozadia."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        super().paintEvent(event)

    def populate_modules_list(self, all_modules_status: dict):
        """
        Naplní zoznam modulov (volá ModuleSetupController).
        all_modules_status = {module_name: is_enabled, ...}
        """
        # Vyčistenie starých položiek z layoutu
        self._clear_modules_layout()
        self.module_items.clear()

        if not all_modules_status:
            return

        for module_name, is_enabled in all_modules_status.items():
            item = ModuleListItem(module_name, is_enabled, self)
            item.uninstall_clicked.connect(self.uninstall_requested.emit)
            self.modules_layout.addWidget(item)
            self.module_items.append(item)

        # Pružný spacer na spodok, aby položky neboli roztiahnuté po celej výške
        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.modules_layout.addItem(spacer)

    def _clear_modules_layout(self):
        """Bezpečne odstráni všetky widgety zo zoznamu."""
        while self.modules_layout.count():
            child = self.modules_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _on_apply_clicked(self):
        """Zozbiera stav všetkých checkboxov a vyšle signál."""
        new_status = {}
        for item in self.module_items:
            new_status[item.module_name] = item.is_checked()
        self.apply_changes_requested.emit(new_status)

    def retranslate_ui(self, lang_code=None):
        LanguageManager.translate_ui(self)

    def closeEvent(self, event):
        LanguageManager.disconnect_language_changed(self.retranslate_ui)
        event.accept()