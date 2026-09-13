# Súbor: core/windows/module_list_item.py

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QPushButton
from PyQt6.QtCore import pyqtSignal
from core.logic.language_manager import LanguageManager


class ModuleListItem(QWidget):
    """Jeden riadok v zozname modulov (názov + checkbox + tlačidlo odinštalovať)."""
    
    uninstall_clicked = pyqtSignal(str)  # Vysiela názov modulu na odinštalovanie

    def __init__(self, module_name: str, is_enabled: bool, parent=None):
        super().__init__(parent)
        self.module_name = module_name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)

        self.checkbox = QCheckBox(module_name)
        self.checkbox.setChecked(is_enabled)
        layout.addWidget(self.checkbox, 1)

        btn_text = LanguageManager.get("btn_uninstall", "Odinštalovať")
        self.btn_uninstall = QPushButton(btn_text)
        self.btn_uninstall.setFixedWidth(110)
        self.btn_uninstall.clicked.connect(self._on_uninstall_clicked)
        layout.addWidget(self.btn_uninstall)
    
    def _on_uninstall_clicked(self):
        """Vyšle signál s menom tohto modulu."""
        self.uninstall_clicked.emit(self.module_name)
    
    def is_checked(self) -> bool:
        """Vráti True, ak je modul zaškrtnutý ako aktívny."""
        return self.checkbox.isChecked()