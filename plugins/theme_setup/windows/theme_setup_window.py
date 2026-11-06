# Súbor: modules/theme_setup/windows/theme_setup_window.py

from pathlib import Path
from typing import List, Dict
from PyQt6.QtWidgets import QWidget, QListWidgetItem
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6 import uic

from core.enum_core import ICoreBridge
from .. import _paths


class ThemeSetupWindow(QWidget):
    save_and_apply_theme_requested = pyqtSignal(str)
    add_theme_requested = pyqtSignal()
    delete_theme_requested = pyqtSignal(str, bool)

    def __init__(self, bridge: ICoreBridge = None, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemeSetupWindow")
        self.setProperty("module_name", _paths.MODULE_NAME)

        self.bridge = bridge or ICoreBridge.get_instance()
        self.controller = None

        ui_path = _paths.UI_DIR / "theme_setup_window.ui"
        if ui_path.exists():
            uic.loadUi(str(ui_path), self)
        else:
            print(f"[theme_setup] CHYBA: UI súbor neexistuje: {ui_path}")

        self.btnApplyTheme.clicked.connect(self._on_save_and_apply_clicked)
        self.btnAddTheme.clicked.connect(self.add_theme_requested.emit)
        self.btnDeleteTheme.clicked.connect(self._on_delete_clicked)
        self.listThemes.currentItemChanged.connect(self.update_ui_state)

        if self.bridge:
            self.bridge.connect_language_changed(self.retranslate_ui)
        self.retranslate_ui()

    def populate_themes_list(self, themes: List[Dict]):
        self.listThemes.clear()
        
        default_label = (
            self.bridge.get_text("lbl_default_theme_tag", "(základná)")
            if self.bridge else "(základná)"
        )

        for theme_info in themes:
            display_name = theme_info['display_name']
            filename = theme_info['filename']
            is_deletable = theme_info['is_deletable']

            item_text = display_name
            if not is_deletable:
                item_text += f" {default_label}"

            item = QListWidgetItem(item_text)
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

    def retranslate_ui(self, lang_code=None):
        if self.bridge:
            self.bridge.translate_widget(self)
            new_title = self.bridge.get_text("ThemeSetupWindow", "Správa Vzhľadu a Tém")
            self.setWindowTitle(new_title)

    def closeEvent(self, event):
        if self.bridge:
            self.bridge.disconnect_language_changed(self.retranslate_ui)
        event.accept()