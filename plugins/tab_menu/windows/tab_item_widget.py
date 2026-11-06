# Súbor: modules/tab_menu/windows/tab_item_widget.py

import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, 
    QToolButton, QStyleOption, QStyle, QMenu
)
from PyQt6.QtGui import QPainter, QCursor, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtSvgWidgets import QSvgWidget

from core.enum_core import ICoreBridge


# Špeciálna trieda pre krížik, ktorá v Pythone ZAKAZUJE akýkoľvek text.
# QSS štýly na ňom fungujú na 100% cez #btn_close, ale žiaden text sa pod krížik nedostane!
class TabCloseButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        super().setText("")
        self.setObjectName("btn_close")
        self.setFlat(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def setText(self, text: str):
        # AKÉKOĽVEK NASTAVENIE TEXTU V PYTHONE IGNORUJEME!
        # Krížik musí mať text VŽDY prázdny, aby QSS nerozbíjalo rozhranie textom "ok".
        super().setText("")


class TabItemWidget(QWidget):
    clicked = pyqtSignal(str)
    close_clicked = pyqtSignal(str)
    window_toggle_requested = pyqtSignal(str, str)

    def __init__(
        self, 
        workspace_id: str, 
        title: str, 
        count: int = 1, 
        is_closable: bool = True, 
        icon_path: str = "", 
        windows_list: list = None,
        bridge: ICoreBridge = None,
        parent=None
    ):
        super().__init__(parent)
        self.bridge = bridge
        self.workspace_id = workspace_id
        self.is_closable = is_closable
        self.windows_list = windows_list or []
        self._is_active = False

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("TabItemWidget")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(26)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_dropdown_menu)

        self._setup_ui(title, count, icon_path)
        self.set_active(False)

    def _setup_ui(self, title: str, count: int, icon_path: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 6, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 1. Ikona modulu
        if icon_path and os.path.exists(icon_path):
            if icon_path.lower().endswith(".svg"):
                self.icon_widget = QSvgWidget(icon_path)
                self.icon_widget.setFixedSize(14, 14)
                self.icon_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                layout.addWidget(self.icon_widget, 0, Qt.AlignmentFlag.AlignVCenter)
            else:
                lbl_icon = QLabel()
                lbl_icon.setFixedSize(14, 14)
                lbl_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                layout.addWidget(lbl_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        # 2. Dynamický názov okna
        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("tabTitle")
        self.lbl_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.lbl_title, 0, Qt.AlignmentFlag.AlignVCenter)

        # 3. Odznak počtu okien
        self.lbl_badge = QLabel(f"({count})" if count > 1 else "")
        self.lbl_badge.setObjectName("tabBadge")
        self.lbl_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        if count <= 1:
            self.lbl_badge.hide()
        layout.addWidget(self.lbl_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        # 4. Šípka roletky pri viacerých oknách
        if len(self.windows_list) > 1:
            self.btn_dropdown = QToolButton()
            self.btn_dropdown.setObjectName("tabDropdownBtn")
            self.btn_dropdown.setArrowType(Qt.ArrowType.DownArrow)
            self.btn_dropdown.setAutoRaise(True)
            self.btn_dropdown.setFixedSize(14, 14)
            self.btn_dropdown.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.btn_dropdown.clicked.connect(lambda: self._show_dropdown_menu(QPoint(0, self.height())))
            layout.addWidget(self.btn_dropdown, 0, Qt.AlignmentFlag.AlignVCenter)

        # 5. Tlačidlo zatvorenia [✕] – chránené proti akémukoľvek textu
        if self.is_closable:
            self.btn_close = TabCloseButton(self)
            self.btn_close.clicked.connect(self._on_close_clicked)
            layout.addWidget(self.btn_close, 0, Qt.AlignmentFlag.AlignVCenter)
        else:
            self.btn_close = None

    def update_title(self, new_title: str):
        if hasattr(self, "lbl_title") and self.lbl_title:
            self.lbl_title.setText(new_title)

    def _show_dropdown_menu(self, pos: QPoint):
        if not self.windows_list:
            return

        menu = QMenu(self)
        menu.setObjectName("TabWindowsMenu")

        for win_info in self.windows_list:
            w_key = win_info["key"]
            w_title = win_info["title"]
            is_active = win_info.get("is_active", True)

            action = QAction(w_title, menu)
            action.setCheckable(True)
            action.setChecked(is_active)
            action.triggered.connect(lambda checked, key=w_key: self.window_toggle_requested.emit(self.workspace_id, key))
            menu.addAction(action)

        global_pos = self.mapToGlobal(QPoint(pos.x(), self.height()))
        menu.exec(global_pos)

    def set_active(self, is_active: bool):
        self._is_active = is_active
        val = "true" if is_active else "false"
        self.setProperty("active", val)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.workspace_id)
        super().mousePressEvent(event)

    def _on_close_clicked(self):
        self.close_clicked.emit(self.workspace_id)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        super().paintEvent(event)