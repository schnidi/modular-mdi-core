# Súbor: modules/control_panel/windows/control_panel_window.py
# OPRAVENÁ VERZIA S CHÝBAJÚCIM IMPORTOM

from PyQt6.QtWidgets import QWidget
from PyQt6 import uic

# --- TOTO JE OPRAVA: Pridanie chýbajúceho importu ---
from .. import _paths

class ControlPanelWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Tento kód je už správny, ale bez importu vyššie nemohol fungovať
        ui_path = _paths.UI_DIR / "control_panel_window.ui"
        uic.loadUi(ui_path, self)
        
        # Controller, ktorý bude riadiť toto okno
        self.controller = None