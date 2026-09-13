# Súbor: core/windows/frameless_dialog.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QWidget, QStyleOption, QStyle
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt
from core.windows.custom_title_bar import CustomTitleBar
from core.logic.services.window_bounds_manager import WindowBoundsManager


class FramelessDialog(QDialog):
    """
    Bezrámový obal pre widgety modulov s plnou podporou QSS tém.
    Používa rovnaké ID ako AboutDialog, aby QSS okamžite naformátovalo
    všetky texty, vstupné polia a tlačidlá do tmavej témy.
    """
    def __init__(self, content_widget: QWidget, title: str = "", parent=None):
        super().__init__(parent)
        
        # 1. Bezrámové okno a ID, ktoré poznajú všetky vaše QSS témy
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("AboutDialog")  # TOTO ID ZAISTÍ BIELY TEXT A TMAVÉ POLIA Z TÉMY!
        self.setMinimumWidth(380)

        # AKTIVÁCIA STRÁŽCU MANTINELOV
        WindowBoundsManager.guard_dialog(self)

        # 2. Hlavný layout s 1px okrajom pre orámovanie okna
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        self.main_layout.setSpacing(0)

        # 3. Naša lišta
        self.title_bar = CustomTitleBar(self)
        if title:
            self.title_bar.set_title(title)
        self.title_bar.btn_minimize.hide()
        self.title_bar.btn_maximize.hide()
        self.title_bar.btn_about.hide()
        if hasattr(self.title_bar, 'btn_update_github'):
            self.title_bar.btn_update_github.hide()
        self.main_layout.addWidget(self.title_bar)
        
        # 4. Vnútorný kontajner s normálnym paddingom (aby obsah nebol nalepený na kraji!)
        self.container = QWidget()
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(25, 20, 25, 20)
        container_layout.addWidget(content_widget)
        
        self.main_layout.addWidget(self.container)

        # Prepojenie tlačidiel ak widget emitne zatvorenie
        if hasattr(content_widget, 'login_successful'):
            content_widget.login_successful.connect(self.accept)
        if hasattr(content_widget, 'login_cancelled'):
            content_widget.login_cancelled.connect(self.reject)

    def paintEvent(self, event):
        """NEVYHNUTNÉ: Zabezpečí prekreslenie témy z QSS súboru."""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        super().paintEvent(event)