# Súbor: core/logic/startup_worker.py

import sys
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QEventLoop
from PyQt6.QtWidgets import QApplication

from core.logic.core_initializer import CoreInitializer


class StartupWorker(QObject):
    """
    Vykonáva dlhotrvajúce úlohy pri štarte aplikácie na pozadí.
    Deleguje komplexnú logiku na CoreInitializer.
    """
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    auth_widget_required = pyqtSignal(object, object)
    
    loading_finished = pyqtSignal(dict) 
    loading_failed = pyqtSignal(str)
    finished = pyqtSignal()
    startup_aborted = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.user_info = None
        self.event_loop = None

    def run(self):
        """Hlavná metóda, ktorá sa spustí vo vlákne na pozadí."""
        self.event_loop = QEventLoop()
        
        try:
            initializer = CoreInitializer()
            startup_data = initializer.run(self)
            
            if startup_data:
                self.loading_finished.emit(startup_data)

        except Exception as e:
            print(f"KRITICKÁ CHYBA v StartupWorker: {e}")
            self.loading_failed.emit(str(e))
        
        finally:
            self.finished.emit()

    @pyqtSlot(dict)
    def on_login_success(self, user_info: dict):
        self.user_info = user_info
        if self.event_loop and self.event_loop.isRunning():
            self.event_loop.exit(1)

    @pyqtSlot()
    def on_login_cancelled(self):
        self.user_info = None
        self.startup_aborted.emit()
        if self.event_loop and self.event_loop.isRunning():
            self.event_loop.exit(0)