# Súbor: modules/theme_setup/windows/theme_setup_window.py (FINÁLNA VERZIA)

from PyQt6.QtWidgets import QWidget, QListWidgetItem
# --- TOTO JE KĽÚČOVÁ OPRAVA: PRIDANIE CHÝBAJÚCEHO IMPORTU ---
from PyQt6.QtCore import pyqtSignal, Qt 
# --- KONIEC OPRAVY ---
from PyQt6 import uic
from pathlib import Path
from typing import List, Dict

class ThemeSetupWindow(QWidget):
    save_and_apply_theme_requested = pyqtSignal(str)
    add_theme_requested = pyqtSignal()
    delete_theme_requested = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        ui_path = Path(__file__).parent.parent / "ui" / "theme_setup_window.ui"
        uic.loadUi(ui_path, self)

        self.controller = None
        self.btnApplyTheme.clicked.connect(self._on_save_and_apply_clicked)
        self.btnAddTheme.clicked.connect(self.add_theme_requested.emit)
        self.btnDeleteTheme.clicked.connect(self._on_delete_clicked)
        self.listThemes.currentItemChanged.connect(self.update_ui_state)

    def populate_themes_list(self, themes: List[Dict]):
        self.listThemes.clear()
        for theme_info in themes:
            display_name = theme_info['display_name']
            filename = theme_info['filename']
            is_deletable = theme_info['is_deletable']
            
            item_text = display_name
            if not is_deletable:
                item_text += " (základná)"
            
            item = QListWidgetItem(item_text)
            
            # Tento riadok teraz bude fungovať, lebo sme importovali Qt
            item.setData(Qt.ItemDataRole.UserRole, {'filename': filename, 'is_deletable': is_deletable})
            
            self.listThemes.addItem(item)
            
        if self.listThemes.count() > 0:
            self.listThemes.setCurrentRow(0)
        self.update_ui_state()

    def update_ui_state(self, current_item=None):
        if not current_item:
            current_item = self.listThemes.currentItem()
        
        is_deletable = False
        if current_item:
            data = current_item.data(Qt.ItemDataRole.UserRole)
            is_deletable = data.get('is_deletable', False)
            
        self.btnDeleteTheme.setEnabled(is_deletable)

    def _on_save_and_apply_clicked(self):
        selected_item = self.listThemes.currentItem()
        if selected_item:
            data = selected_item.data(Qt.ItemDataRole.UserRole)
            self.save_and_apply_theme_requested.emit(data['filename'])

    def _on_delete_clicked(self):
        selected_item = self.listThemes.currentItem()
        if selected_item:
            data = selected_item.data(Qt.ItemDataRole.UserRole)
            self.delete_theme_requested.emit(data['filename'], data['is_deletable'])