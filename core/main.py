"""
Súbor: main.py
Hlavný vstupný bod aplikácie so SplashScreenom a viacvláknovým štartom.
"""

import sys
import os

# 1. Pridanie koreňa projektu do sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core
sys.modules['app'] = sys.modules[__name__]
sys.modules['app.core'] = core
if 'core.enum_core' in sys.modules or os.path.exists(os.path.join(os.path.dirname(__file__), "enum_core.py")):
    import core.enum_core
    sys.modules['app.enum_core'] = core.enum_core

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSlot

from core.logic.skin_manager import SkinManager
from core.logic.startup_worker import StartupWorker
from core.windows.splash_screen import SplashScreen
from core.windows.main_window import MainWindow


def main():
    """Hlavná funkcia aplikácie."""
    app = QApplication(sys.argv)

    # =========================================================================
    # KROK 1: OKAMŽITÉ NAČÍTANIE ULOŽENEJ TÉMY (PRED SPLASH SCREENOM!)
    # Globálny štýl sa aplikuje skôr, než sa vytvorí jediný pixel na obrazovke!
    # =========================================================================
    SkinManager.apply_saved_skin()

    # KROK 2: Vytvorenie a zobrazenie Splash Screenu (už nabehne v správnej téme)
    splash = SplashScreen()
    screen_geometry = app.primaryScreen().geometry()
    splash.move(
        (screen_geometry.width() - splash.width()) // 2,
        (screen_geometry.height() - splash.height()) // 2
    )
    splash.show()

    # KROK 3: Príprava vlákna a workera pre načítavanie na pozadí
    thread = QThread()
    worker = StartupWorker()
    worker.moveToThread(thread)

    window_holder = {}

    @pyqtSlot(dict)
    def on_loading_finished(startup_data):
        """Spustí sa po úspešnom dokončení všetkých štartovacích úloh."""
        main_window = MainWindow(startup_data)
        window_holder["main_window"] = main_window
        main_window.show()
        splash.close()

    # Prepojenie signálov z workera na Splash Screen
    worker.status_updated.connect(splash.update_status)
    worker.progress_updated.connect(splash.update_progress)
    worker.loading_failed.connect(splash.show_error)
    worker.loading_finished.connect(on_loading_finished)
    worker.auth_widget_required.connect(splash.handle_auth_request)

    # Správa životného cyklu vlákna
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    app.aboutToQuit.connect(thread.quit)

    thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()