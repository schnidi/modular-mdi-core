"""
Súbor: core/windows/custom_message_box.py
Centrálny bezrámový dialóg pre správy, otázky, chyby a vstupy.
Plne rešpektuje QSS témy rovnako ako AboutDialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QWidget, QStyleOption, QStyle
)
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt
from core.windows.custom_title_bar import CustomTitleBar
from core.logic.language_manager import LanguageManager
from core.logic.services.window_bounds_manager import WindowBoundsManager


class CustomMessageBox(QDialog):
    def __init__(self, parent=None, title="", text="", icon_type="info", 
                 buttons=None, show_input=False, input_echo=QLineEdit.EchoMode.Normal,
                 detailed_text=None):
        super().__init__(parent)
        
        # 1. Zrušenie Windows rámu a nastavenie ID, ktoré pozná QSS téma
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("AboutDialog")  # TOTO ID MAJÚ VŠETKY VAŠE QSS TÉMY!
        self.setMinimumWidth(420)

        # AKTIVÁCIA STRÁŽCU MANTINELOV
        WindowBoundsManager.guard_dialog(self)

        # 2. Hlavný layout s 1px okrajom presne ako v AboutDialog
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(1, 1, 1, 1)
        self.main_layout.setSpacing(0)

        # 3. Naša bezrámová lišta CustomTitleBar
        self.title_bar = CustomTitleBar(self)
        self.title_bar.set_title(title or "Správa")
        self.title_bar.btn_minimize.hide()
        self.title_bar.btn_maximize.hide()
        self.title_bar.btn_about.hide()
        if hasattr(self.title_bar, 'btn_update_github'):
            self.title_bar.btn_update_github.hide()
        self.main_layout.addWidget(self.title_bar)

        # 4. Vnútorný kontajner na obsah
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Riadok: Ikona + Text správy
        msg_row = QHBoxLayout()
        msg_row.setSpacing(15)

        icon_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "❌",
            "question": "❓"
        }
        lbl_icon = QLabel(icon_map.get(icon_type, "ℹ️"))
        lbl_icon.setStyleSheet("font-size: 26px;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignTop)
        msg_row.addWidget(lbl_icon, 0)

        lbl_text = QLabel(text)
        lbl_text.setWordWrap(True)
        lbl_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl_text.setStyleSheet("font-size: 13px;")
        msg_row.addWidget(lbl_text, 1)
        content_layout.addLayout(msg_row)

        # Vstupné pole (pre náhradu QInputDialog)
        self.line_input = None
        if show_input:
            self.line_input = QLineEdit()
            self.line_input.setEchoMode(input_echo)
            content_layout.addWidget(self.line_input)

        # Detailný text chyby (voliteľný)
        self.details_edit = None
        if detailed_text:
            self.btn_toggle_details = QPushButton(LanguageManager.get("btn_show_details", "▶ Detaily chyby"))
            self.btn_toggle_details.setCheckable(True)
            self.btn_toggle_details.setStyleSheet("text-align: left; background: transparent; border: none; color: #007acc; font-weight: bold;")
            
            self.details_edit = QTextEdit()
            self.details_edit.setReadOnly(True)
            self.details_edit.setPlainText(detailed_text)
            self.details_edit.hide()
            self.details_edit.setMinimumHeight(100)
            self.details_edit.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")

            def toggle_details(checked):
                if checked:
                    self.details_edit.show()
                    self.btn_toggle_details.setText(LanguageManager.get("btn_hide_details", "▼ Skryť detaily"))
                else:
                    self.details_edit.hide()
                    self.btn_toggle_details.setText(LanguageManager.get("btn_show_details", "▶ Detaily chyby"))
                self.adjustSize()

            self.btn_toggle_details.clicked.connect(toggle_details)
            content_layout.addWidget(self.btn_toggle_details)
            content_layout.addWidget(self.details_edit)

        # Tlačidlá
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if buttons is None:
            buttons = [("OK", QDialog.DialogCode.Accepted, True)]

        for btn_text, return_code, is_default in buttons:
            btn = QPushButton(btn_text)
            btn.setMinimumWidth(85)
            btn.setMinimumHeight(28)
            if is_default:
                btn.setDefault(True)
            
            def make_handler(code=return_code):
                def handler():
                    self.done(code)
                return handler

            btn.clicked.connect(make_handler())
            btn_row.addWidget(btn)

        content_layout.addLayout(btn_row)
        self.main_layout.addWidget(self.content_widget)

    def paintEvent(self, event):
        """NEVYHNUTNÉ: Bez tohto PyQt neodkreslí QSS pozadie okna a rámy!"""
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        super().paintEvent(event)

    # =========================================================================
    # STATICKÉ POMOCNÉ METÓDY (Náhrada za QMessageBox a QInputDialog)
    # =========================================================================

    @classmethod
    def information(cls, parent, title: str, text: str):
        ok_text = LanguageManager.get("btn_ok", "OK")
        dlg = cls(parent, title=title, text=text, icon_type="info",
                  buttons=[(ok_text, QDialog.DialogCode.Accepted, True)])
        dlg.exec()

    @classmethod
    def warning(cls, parent, title: str, text: str):
        ok_text = LanguageManager.get("btn_ok", "OK")
        dlg = cls(parent, title=title, text=text, icon_type="warning",
                  buttons=[(ok_text, QDialog.DialogCode.Accepted, True)])
        dlg.exec()

    @classmethod
    def critical(cls, parent, title: str, text: str, detailed_text: str = None):
        ok_text = LanguageManager.get("btn_ok", "OK")
        dlg = cls(parent, title=title, text=text, icon_type="critical",
                  detailed_text=detailed_text,
                  buttons=[(ok_text, QDialog.DialogCode.Accepted, True)])
        dlg.exec()

    @classmethod
    def question(cls, parent, title: str, text: str) -> bool:
        yes_text = LanguageManager.get("btn_yes", "Áno")
        no_text = LanguageManager.get("btn_no", "Nie")
        dlg = cls(parent, title=title, text=text, icon_type="question",
                  buttons=[
                      (yes_text, QDialog.DialogCode.Accepted, True),
                      (no_text, QDialog.DialogCode.Rejected, False)
                  ])
        return dlg.exec() == QDialog.DialogCode.Accepted

    @classmethod
    def get_text(cls, parent, title: str, text: str, echo=QLineEdit.EchoMode.Normal) -> tuple[str, bool]:
        ok_text = LanguageManager.get("btn_ok", "OK")
        cancel_text = LanguageManager.get("btn_cancel", "Zrušiť")
        dlg = cls(parent, title=title, text=text, icon_type="info",
                  show_input=True, input_echo=echo,
                  buttons=[
                      (ok_text, QDialog.DialogCode.Accepted, True),
                      (cancel_text, QDialog.DialogCode.Rejected, False)
                  ])
        res = dlg.exec()
        val = dlg.line_input.text() if dlg.line_input else ""
        return val, (res == QDialog.DialogCode.Accepted)

    @classmethod
    def show_dialog(cls, content_widget, title: str = "", parent=None):
        """Umožní modulu zobraziť svoj widget cez dialog_service v téme."""
        from core.windows.frameless_dialog import FramelessDialog
        dlg = FramelessDialog(content_widget, title=title, parent=parent)
        return dlg.exec()