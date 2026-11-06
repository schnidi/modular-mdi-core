"""
Súbor: main.py
Hlavný vstupný bod aplikácie so SplashScreenom a viacvláknovým štartom.
"""

import sys
import os
import gc

# =============================================================================
# NASTAVENIE ČISTENIA PAMÄTE (True / 1 = čistí, False / 0 = nečistí)
# =============================================================================
CLEANUP_MEMORY = True

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
from core.logic.language_manager import LanguageManager
from core.logic.core_bridge import CoreBridge
from core.logic.startup_worker import StartupWorker
from core.windows.splash_screen import SplashScreen


def main():
    """Hlavná funkcia aplikácie – riadi výhradne postupnosť štartu."""
    app = QApplication(sys.argv)

    # KROK 1: Počiatočná téma a jazyk
    SkinManager.apply_saved_skin()
    bridge = CoreBridge.get_instance()
    saved_lang = bridge.load_module_setting(
        module_name="system_language",
        section="General",
        key="language",
        default="sk_SK"
    )
    LanguageManager.load_language(saved_lang)

    # KROK 2: Vytvorenie vlákna a workera pre načítavanie na pozadí
    thread = QThread()
    worker = StartupWorker()
    worker.moveToThread(thread)

    # KROK 3: Vytvorenie a zobrazenie Splash Screenu (všetko pripravené vopred)
    splash = SplashScreen(worker=worker)
    splash.show()

    window_holder = {}

    @pyqtSlot(dict)
    def on_loading_finished(startup_data):
        """
        Spustí sa po dokončení backendu (pri 75 %).
        Zostaví MainWindow a až keď je okno skutočne vytvorené v pamäti,
        nastaví 100 % a v tom istom okamihu otvorí MainWindow a zavrie Splash.
        """
        # 1. Plynulý posun baru počas preberania dát do UI
        splash.update_status(LanguageManager.get("msg_creating_main_window", "Vytváram hlavné okno..."))
        splash.update_progress(80)
        app.processEvents()

        # 2. Zostavenie MainWindow v pamäti
        from core.windows.main_window import MainWindow
        main_window = MainWindow(startup_data)
        window_holder["main_window"] = main_window

        # 3. 100 % naskočí AŽ v momente reálneho dokončenia celého okna
        splash.update_status(LanguageManager.get("msg_init_done", "Hotovo."))
        splash.update_progress(100)
        app.processEvents()

        # 4. Okamžité prepnutie okien bez čakania
        main_window.show()
        splash.close()

        if CLEANUP_MEMORY:
            gc.collect()

    # Prepojenie signálov z workera na Splash Screen
    worker.status_updated.connect(splash.update_status)
    worker.progress_updated.connect(splash.update_progress)
    worker.loading_failed.connect(splash.show_error)
    worker.loading_finished.connect(on_loading_finished)
    worker.auth_widget_required.connect(splash.handle_auth_request)

    # KROK 4: Spustenie štartovacieho procesu
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)

    if CLEANUP_MEMORY:
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
    else:
        window_holder["worker"] = worker
        window_holder["thread"] = thread

    app.aboutToQuit.connect(thread.quit)

    thread.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()