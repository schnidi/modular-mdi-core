# Súbor: modules/control_panel/windows/control_panel_window.py

import os
from PyQt6.QtWidgets import QWidget
from PyQt6 import uic

from core.enum_core import ICoreBridge
from .. import _paths
from ..logic.control_panel_controller import ControlPanelController


class ControlPanelWindow(QWidget):
    def __init__(self, bridge: ICoreBridge = None, parent=None):
        super().__init__(parent)
        self.setObjectName("ControlPanelWindow")

        # KĽÚČOVÉ: Nastavenie mena modulu pre bezkolízne preklady
        self.setProperty("module_name", _paths.MODULE_NAME)

        self.bridge = bridge or ICoreBridge.get_instance()

        # 1. Načítanie UI súboru
        ui_path = _paths.UI_FILE_PATH
        if os.path.exists(str(ui_path)):
            uic.loadUi(str(ui_path), self)
        else:
            print(f"[control_panel] CHYBA: UI súbor neexistuje: {ui_path}")

        # 2. Vytvorenie kontroléra
        self.controller = ControlPanelController(self, bridge=self.bridge)

        # 3. Prihlásenie na zmenu jazyka
        if self.bridge:
            self.bridge.connect_language_changed(self.retranslate_ui)

        # 4. Úvodný preklad okna pri štarte
        self.retranslate_ui()

    def retranslate_ui(self, lang_code=None):
        """Preloží MDI lištu, nadpisy a ikony."""
        if self.bridge:
            self.bridge.translate_widget(self)

            new_title = self.bridge.get_text("ControlPanel", "Ovládací panel")
            self.setWindowTitle(new_title)

            if hasattr(self, "lbl_control_panel_title"):
                self.lbl_control_panel_title.setText(self.bridge.get_text("lbl_control_panel_title", new_title))
            if hasattr(self, "lbl_control_panel_subtitle"):
                self.lbl_control_panel_subtitle.setText(self.bridge.get_text("lbl_control_panel_subtitle", "Vyberte kategóriu nastavení:"))

        if self.controller and hasattr(self.controller, "retranslate_icons"):
            self.controller.retranslate_icons()

    def closeEvent(self, event):
        if self.bridge:
            self.bridge.disconnect_language_changed(self.retranslate_ui)

        if self.controller and hasattr(self.controller, "cleanup"):
            self.controller.cleanup()
        event.accept()