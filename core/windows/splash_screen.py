"""
Súbor: core/windows/splash_screen.py
Načítavacie / uvítacie okno aplikácie s podporou dynamického prihlasovacieho formulára.
"""

import importlib
import inspect
from PyQt6.QtWidgets import QWidget, QMessageBox, QStyleOption, QStyle, QApplication
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6 import uic

from core._path import Paths
from core.logic.language_manager import LanguageManager
from core.logic.core_bridge import CoreBridge


class SplashScreen(QWidget):
    def __init__(self, worker=None):
        super().__init__()
        self.worker = worker

        # 1. Nastavenia bezrámového Splash okna, ktoré je vždy navrchu
        self.setWindowFlags(
            Qt.WindowType.SplashScreen 
            | Qt.WindowType.WindowStaysOnTopHint 
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setObjectName("SplashScreen")

        # 2. Načítanie UI súboru
        uic.loadUi(Paths.get_ui_file("splash_screen.ui"), self)
        self.setFixedWidth(460)

        # 3. Predpripravenie obsahu (ak systém vyžaduje prihlásenie, vloží sa pred zobrazením)
        self._prepare_auth_content()

        # 4. Preklad celého okna a vycentrovanie v pamäti pred zobrazením
        LanguageManager.translate_ui(self)
        self.adjustSize()
        self.center_on_screen()

    def _prepare_auth_content(self):
        """Zistí v konfigurácii, či je aktívny auth modul a pripraví formulár pred zobrazením."""
        from core.logic.core_initializer import CoreInitializer
        auth_info = CoreInitializer.find_active_auth_module()
        if not auth_info:
            return

        bridge = CoreBridge.get_instance()
        bridge.register_module_translations(auth_info)

        # Spustenie bootstrap funkcie auth modulu, ak existuje
        bootstrap_path = auth_info.get("bootstrap_function_path")
        if bootstrap_path:
            try:
                mod_path, func_name = bootstrap_path.rsplit('.', 1)
                bootstrap_func = getattr(importlib.import_module(mod_path), func_name)
                if len(inspect.signature(bootstrap_func).parameters) > 0:
                    bootstrap_func(bridge)
                else:
                    bootstrap_func()
            except Exception as e:
                print(f"[SplashScreen] Chyba bootstrap auth modulu: {e}")

        # Vytvorenie formulára z továrne auth modulu
        factory_path = auth_info.get("auth_widget_factory_path")
        if factory_path:
            try:
                mod_path, func_name = factory_path.rsplit('.', 1)
                factory_func = getattr(importlib.import_module(mod_path), func_name)
                sig = inspect.signature(factory_func)
                login_widget = factory_func(bridge=bridge) if "bridge" in sig.parameters else factory_func()

                # Prepojenie signálov na worker
                if self.worker:
                    if hasattr(login_widget, 'login_successful'):
                        login_widget.login_successful.connect(self.worker.on_login_success)
                    if hasattr(login_widget, 'login_cancelled'):
                        login_widget.login_cancelled.connect(self.worker.on_login_cancelled)

                # Vloženie do pripraveného layoutu
                if hasattr(self, 'loginContainerLayout'):
                    self.loginContainerLayout.addWidget(login_widget)

            except Exception as e:
                print(f"[SplashScreen] Chyba vytvorenia prihlasovacieho widgetu: {e}")

    def center_on_screen(self):
        """Centrálne vycentrovanie Splash Screenu podľa dostupnej pracovnej plochy monitora."""
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.left() + (geo.width() - self.width()) // 2
            y = geo.top() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def paintEvent(self, event):
        """Zabezpečí správne vykreslenie tmavého QSS pozadia a okrajov."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        super().paintEvent(event)

    @pyqtSlot(str)
    def update_status(self, text: str):
        """Aktualizuje textový popis stavu načítavania v UI."""
        if hasattr(self, 'lblStatus'):
            self.lblStatus.setText(text)

    @pyqtSlot(int)
    def update_progress(self, value: int):
        """Aktualizuje percentuálnu hodnotu na progress bare."""
        if hasattr(self, 'progressBar'):
            self.progressBar.setValue(value)

    @pyqtSlot(object, object)
    def handle_auth_request(self, factory_func, worker):
        """Fallback slot v prípade, že by formulár nebol inicializovaný vopred."""
        if hasattr(self, 'loginContainerLayout') and self.loginContainerLayout.count() > 0:
            return  # Formulár už bol vložený pri štarte

        try:
            bridge = CoreBridge.get_instance()
            sig = inspect.signature(factory_func)
            login_widget = factory_func(bridge=bridge) if "bridge" in sig.parameters else factory_func()

            if hasattr(login_widget, 'login_successful'):
                login_widget.login_successful.connect(worker.on_login_success)
            if hasattr(login_widget, 'login_cancelled'):
                login_widget.login_cancelled.connect(worker.on_login_cancelled)

            if hasattr(self, 'loginContainerLayout'):
                self.loginContainerLayout.addWidget(login_widget)

            self.adjustSize()
            self.center_on_screen()
        except Exception as e:
            self.show_error(f"Chyba prihlasovacieho formulára: {e}")

    @pyqtSlot(object)
    def on_startup_finished(self, main_window):
        """Po úspešnom načítaní zobrazí hlavné okno a zatvorí splash screen."""
        self.main_window = main_window
        self.main_window.show()
        self.close()

    @pyqtSlot(str)
    def show_error(self, message: str):
        """Zobrazí chybové hlásenie a ukončí splash screen."""
        title = LanguageManager.get("splash_err_title", "Chyba pri štarte")
        QMessageBox.critical(self, title, message)
        self.close()