"""
Súbor: core/windows/splash_screen.py
Načítavacie / uvítacie okno aplikácie s podporou dynamického prihlasovacieho formulára.
"""

from PyQt6.QtWidgets import QWidget, QMessageBox, QStyleOption, QStyle
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6 import uic

from core._path import Paths


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()

        # 1. Nastavenia bezrámového Splash okna, ktoré je vždy navrchu
        self.setWindowFlags(
            Qt.WindowType.SplashScreen 
            | Qt.WindowType.WindowStaysOnTopHint 
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setObjectName("SplashScreen")

        # 2. Načítanie UI súboru striktne cez centrálny Paths manažér
        uic.loadUi(Paths.get_ui_file("splash_screen.ui"), self)

    def paintEvent(self, event):
        """Nevyhnutné pre PyQt: zabezpečí správne vykreslenie tmavého QSS pozadia a okrajov."""
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
        """
        Dynamicky vytvorí a vloží prihlasovací widget do tela splash screenu.
        Prepojí signály z formulára so slotmi workera pre odblokovanie načítavania.
        """
        try:
            # Továrenská funkcia vráti inštanciu prihlasovacieho widgetu
            login_widget = factory_func()

            # Prepojenie signálov z widgetu na worker
            if hasattr(login_widget, 'login_successful'):
                login_widget.login_successful.connect(worker.on_login_success)
            if hasattr(login_widget, 'login_cancelled'):
                login_widget.login_cancelled.connect(worker.on_login_cancelled)

            # Vloženie do pripraveného kontajnera v splash_screen.ui
            if hasattr(self, 'loginContainerLayout'):
                self.loginContainerLayout.addWidget(login_widget)

            # Automatické zväčšenie okna podľa vloženého formulára
            self.adjustSize()

        except Exception as e:
            self.show_error(f"Chyba pri vytváraní prihlasovacieho formulára: {e}")
            if hasattr(worker, 'on_login_cancelled'):
                worker.on_login_cancelled()

    @pyqtSlot(object)
    def on_startup_finished(self, main_window):
        """Po úspešnom načítaní zobrazí hlavné okno a zatvorí splash screen."""
        self.main_window = main_window
        self.main_window.show()
        self.close()

    @pyqtSlot(str)
    def show_error(self, message: str):
        """Zobrazí chybové hlásenie a ukončí splash screen."""
        QMessageBox.critical(self, "Chyba pri štarte", message)
        self.close()