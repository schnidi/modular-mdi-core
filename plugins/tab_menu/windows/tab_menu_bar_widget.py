# Súbor: modules/tab_menu/windows/tab_menu_bar_widget.py

from PyQt6.QtWidgets import (
    QWidget, QToolButton, QMenu, QSpacerItem, 
    QSizePolicy, QStyleOption, QStyle
)
from PyQt6.QtGui import QPainter, QAction
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6 import uic

# JEDINÝ POVOLENÝ IMPORT Z JADRA
from core.enum_core import ICoreBridge

from .. import _paths
from .tab_item_widget import TabItemWidget


class TabMenuBarWidget(QWidget):
    tab_selected = pyqtSignal(str)
    tab_close_requested = pyqtSignal(str)
    window_toggle_requested = pyqtSignal(str, str)
    setting_changed = pyqtSignal(str, bool)
    desktop_action_requested = pyqtSignal(str)

    def __init__(self, bridge: ICoreBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.controller = None

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("TabMenuBar")
        self.setFixedHeight(30)

        ui_file_path = _paths.get_ui_file("tab_menu_bar.ui")
        uic.loadUi(ui_file_path, self)

        if hasattr(self, "tabsContainerWidget"):
            self.tabsContainerWidget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.tab_widgets = {}
        self._settings_state = {
            "show_close_btn": True,
            "isolate_workspace": True,
            "bring_to_front": True,
            "dropdown_focus_only": False 
        }

        self._setup_settings_button()

        if self.bridge:
            self.bridge.connect_language_changed(self.retranslate_ui)

        self.retranslate_ui()

        self.style().unpolish(self)
        self.style().polish(self)

    def retranslate_ui(self, lang_code: str = None):
        if not self.bridge:
            return

        # POZOR: Žiadne volanie self.bridge.translate_widget(self) !!!
        # Dynamické záložky nesmú byť plošne prekladané jadrom, inak sa zničí krížik btn_close.

        # Tooltip pre ozubené koliesko
        if hasattr(self, "btn_settings"):
            tip = self.bridge.get_text("tabSettingsBtn", "Nastavenia záložkovej lišty")
            self.btn_settings.setToolTip(tip)

        # Prekreslenie záložiek
        if self.controller and hasattr(self.controller, "sync_tabs_with_open_windows"):
            self.controller.sync_tabs_with_open_windows()

    def closeEvent(self, event):
        if self.bridge:
            self.bridge.disconnect_language_changed(self.retranslate_ui)
        super().closeEvent(event)

    def _setup_settings_button(self):
        self.btn_settings = QToolButton(self)
        self.btn_settings.setObjectName("tabSettingsBtn")
        self.btn_settings.setArrowType(Qt.ArrowType.DownArrow)
        self.btn_settings.setAutoRaise(True)
        self.btn_settings.setFixedSize(22, 22)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.clicked.connect(self._show_settings_menu)
        self.main_layout.addWidget(self.btn_settings, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_settings_state(self, settings: dict):
        self._settings_state.update(settings)

    def _show_settings_menu(self):
        if not self.bridge:
            return
            
        menu = QMenu(self)
        menu.setObjectName("TabSettingsMenu")

        lbl_close = self.bridge.get_text("tab_setting_close", "Zobraziť tlačidlo zatvorenia (krížik)")
        act_close = QAction(lbl_close, menu)
        act_close.setCheckable(True)
        act_close.setChecked(self._settings_state.get("show_close_btn", True))
        act_close.triggered.connect(lambda chk: self.setting_changed.emit("show_close_btn", chk))
        menu.addAction(act_close)

        lbl_isolate = self.bridge.get_text("tab_setting_isolate", "Zobraziť len okná aktívnej záložky (minimalizovať ostatné)")
        act_isolate = QAction(lbl_isolate, menu)
        act_isolate.setCheckable(True)
        act_isolate.setChecked(self._settings_state.get("isolate_workspace", True))
        act_isolate.triggered.connect(lambda chk: self.setting_changed.emit("isolate_workspace", chk))
        menu.addAction(act_isolate)

        lbl_front = self.bridge.get_text("tab_setting_front", "Preniesť okná záložky do popredia")
        act_front = QAction(lbl_front, menu)
        act_front.setCheckable(True)
        act_front.setChecked(self._settings_state.get("bring_to_front", True))
        act_front.triggered.connect(lambda chk: self.setting_changed.emit("bring_to_front", chk))
        menu.addAction(act_front)

        menu.addSeparator()

        lbl_focus = self.bridge.get_text("tab_setting_focus", "Vyrolované okno: Kliknutím ihneď aktivovať do popredia (namiesto zbalenia)")
        act_focus_mode = QAction(lbl_focus, menu)
        act_focus_mode.setCheckable(True)
        act_focus_mode.setChecked(self._settings_state.get("dropdown_focus_only", False))
        act_focus_mode.triggered.connect(lambda chk: self.setting_changed.emit("dropdown_focus_only", chk))
        menu.addAction(act_focus_mode)

        menu.addSeparator()

        act_min_all = menu.addAction(self.bridge.get_text("tab_action_min_all", "Minimalizovať všetky okná"))
        act_min_all.triggered.connect(lambda: self.desktop_action_requested.emit("minimize_all"))

        act_rest_all = menu.addAction(self.bridge.get_text("tab_action_rest_all", "Obnoviť všetky okná"))
        act_rest_all.triggered.connect(lambda: self.desktop_action_requested.emit("restore_all"))

        act_tile = menu.addAction(self.bridge.get_text("tab_action_tile", "Usporiadať vedľa seba (Dlaždice)"))
        act_tile.triggered.connect(lambda: self.desktop_action_requested.emit("tile"))

        act_cascade = menu.addAction(self.bridge.get_text("tab_action_cascade", "Usporiadať kaskádovito"))
        act_cascade.triggered.connect(lambda: self.desktop_action_requested.emit("cascade"))

        btn_pos = self.btn_settings.mapToGlobal(QPoint(0, self.btn_settings.height()))
        menu.exec(btn_pos)

    def populate_tabs(self, tabs_data: list, active_id: str):
        self._clear_tabs_layout()
        self.tab_widgets.clear()

        show_close = self._settings_state.get("show_close_btn", True)

        for tab_info in tabs_data:
            w_id = tab_info["id"]
            tab_item = TabItemWidget(
                workspace_id=w_id,
                title=tab_info["title"],
                count=tab_info.get("count", 1),
                is_closable=tab_info.get("is_closable", True) and show_close,
                icon_path=tab_info.get("icon_path", ""),
                windows_list=tab_info.get("windows_list", []),
                bridge=self.bridge,
                parent=self.tabsContainerWidget
            )

            tab_item.clicked.connect(self.tab_selected.emit)
            tab_item.close_clicked.connect(self.tab_close_requested.emit)
            tab_item.window_toggle_requested.connect(self.window_toggle_requested.emit)

            if w_id == active_id:
                tab_item.set_active(True)

            self.tabs_layout.addWidget(tab_item)
            self.tab_widgets[w_id] = tab_item

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.tabs_layout.addItem(spacer)

    def set_active_tab(self, active_id: str):
        for w_id, widget in self.tab_widgets.items():
            widget.set_active(w_id == active_id)

    def _clear_tabs_layout(self):
        while self.tabs_layout.count():
            item = self.tabs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        super().paintEvent(event)