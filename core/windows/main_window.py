"""
Súbor: core/windows/main_window.py
Čisté hlavné okno (View) bez biznis logiky.
"""

from PyQt6.QtWidgets import QWidget, QStyleOption, QStyle, QMenu
from PyQt6.QtGui import QPainter
from PyQt6.QtCore import Qt, QPoint, QRect, QEvent
from PyQt6 import uic

from core._path import Paths
from core.windows.custom_title_bar import CustomTitleBar
from core.windows.test_window import TestWindow
from core.windows.module_setup_window import ModuleSetupWindow
from core.logic.plugin.module_setup_controller import ModuleSetupController
from core.logic.services.about_logic import AboutLogic
from core.logic.language_manager import LanguageManager
from core.logic.skin_manager import SkinManager
from core.logic.main_window_logic import MainWindowController
from core.logic.main_window_security import MainWindowSecurity


class MainWindow(QWidget):
    MARGIN = 6

    def __init__(self, startup_data=None):
        super().__init__()
        
        self.startup_data = startup_data or {}

        # 1. Vzhľad a bezrámové okno
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)
        self.setObjectName("MainWindow")

        self._resizing = False
        self._resize_direction = None
        self._drag_start_pos = QPoint()
        self._drag_start_geom = QRect()
        
        # 2. Načítanie UI
        uic.loadUi(Paths.get_ui_file("main_window.ui"), self)
        self.mdiArea.setBackground(Qt.GlobalColor.transparent)
        
        # Zapnutie sledovania myši a filtra na MDI ploche
        self.mdiArea.viewport().setMouseTracking(True)
        self.mdiArea.viewport().installEventFilter(self)
        self.menu_bar.setCursor(Qt.CursorShape.ArrowCursor)
        
        # 3. Vlastná lišta
        self.title_bar = CustomTitleBar(self)
        self.title_bar_layout.addWidget(self.title_bar)
        
        # 4. KONTROLÉRY (Presné rozdelenie zodpovednosti!)
        # Vizuálny kontrolér okien
        self.controller = MainWindowController(self)
        
        # Základné menu Nastavenie
        self._setup_base_menus()
        self.connect_actions()

        # Bezpečnostný kontrolér (rieši relácie, práva, odhlásenie a dynamické menu)
        self.security = MainWindowSecurity(self, self.controller, self.startup_data)
        
        # 5. Jazyk, Skin a obnova geometrie
        LanguageManager.connect_language_changed(self.retranslate_ui)
        # SkinManager.apply_skin("dark")
        self.controller.restore_visual_state()

    def _setup_base_menus(self):
        if hasattr(self, 'menu_file'):
            self.menu_file.setTitle("Program")

        self.menu_settings = QMenu("Nastavenie", self)
        self.action_plugins = self.menu_settings.addAction("Správca Modulov...")
        self.action_plugins.triggered.connect(self.open_module_setup)
        self.menu_bar.insertMenu(self.menu_window.menuAction(), self.menu_settings)

    def connect_actions(self):
        self.action_exit.triggered.connect(self.close)
        self.action_minimize.triggered.connect(self.showMinimized)
        self.action_maximize.triggered.connect(self.title_bar.toggle_maximize_restore)
        self.action_about.triggered.connect(lambda: AboutLogic.show_about_dialog(self))

        self.action_tile.triggered.connect(self.mdiArea.tileSubWindows)
        self.action_cascade.triggered.connect(self.mdiArea.cascadeSubWindows)
        self.action_open_test.triggered.connect(self.open_test_window)

    def open_module_setup(self):
        def factory():
            view = ModuleSetupWindow()
            view.controller = ModuleSetupController(view, main_controller=self.controller)
            return view

        self.controller.open_sub_window(
            window_key="ModuleSetup",
            widget_factory_func=factory,
            window_title="Správca Modulov"
        )

    def open_test_window(self):
        self.controller.open_sub_window(
            window_key="test_window_1",
            widget_factory_func=TestWindow,
            window_title="Testovací Modul"
        )

    # ========================================================
    # EVENTY OKNA A RESIZE (AKTÍVNA 6PX ZÓNA)
    # ========================================================

    def _get_cursor_for_direction(self, direction: str) -> Qt.CursorShape:
        """Priradí správny tvar šípky podľa smeru okraja."""
        cursor_map = {
            "top_left": Qt.CursorShape.SizeFDiagCursor, "bottom_right": Qt.CursorShape.SizeFDiagCursor,
            "top_right": Qt.CursorShape.SizeBDiagCursor, "bottom_left": Qt.CursorShape.SizeBDiagCursor,
            "left": Qt.CursorShape.SizeHorCursor, "right": Qt.CursorShape.SizeHorCursor,
            "top": Qt.CursorShape.SizeVerCursor, "bottom": Qt.CursorShape.SizeVerCursor,
        }
        return cursor_map.get(direction, Qt.CursorShape.ArrowCursor)

    def _get_direction(self, pos: QPoint) -> str:
        rect = self.rect()
        m = self.MARGIN
        left, right = pos.x() <= m, pos.x() >= rect.width() - m
        top, bottom = pos.y() <= m, pos.y() >= rect.height() - m

        if top and left: return "top_left"
        if top and right: return "top_right"
        if bottom and left: return "bottom_left"
        if bottom and right: return "bottom_right"
        if left: return "left"
        if right: return "right"
        if top: return "top"
        if bottom: return "bottom"
        return ""

    def eventFilter(self, obj, event):
        """Inteligentné stráženie kurzora na MDI ploche pri okrajoch okna."""
        if obj == self.mdiArea.viewport() and not self._resizing:
            if event.type() in (QEvent.Type.MouseMove, QEvent.Type.Enter):
                pos_in_window = self.mapFromGlobal(event.globalPosition().toPoint())
                direction = self._get_direction(pos_in_window)
                if direction and not self.isMaximized():
                    target_cursor = self._get_cursor_for_direction(direction)
                    if self.cursor().shape() != target_cursor:
                        self.setCursor(target_cursor)
                else:
                    if self.cursor().shape() != Qt.CursorShape.ArrowCursor:
                        self.unsetCursor()
        return super().eventFilter(obj, event)

    def leaveEvent(self, event):
        if not self._resizing:
            self.unsetCursor()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            direction = self._get_direction(event.position().toPoint())
            if direction:
                self._resizing = True
                self._resize_direction = direction
                self._drag_start_pos = event.globalPosition().toPoint()
                self._drag_start_geom = self.geometry()
                self.setCursor(self._get_cursor_for_direction(direction))
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            geom = QRect(self._drag_start_geom)
            min_w = self.minimumWidth() if self.minimumWidth() > 0 else 700
            min_h = self.minimumHeight() if self.minimumHeight() > 0 else 450

            if "left" in self._resize_direction:
                new_w = max(min_w, geom.width() - delta.x())
                geom.setLeft(geom.right() - new_w)
            if "right" in self._resize_direction:
                geom.setWidth(max(min_w, geom.width() + delta.x()))
            if "top" in self._resize_direction:
                new_h = max(min_h, geom.height() - delta.y())
                geom.setTop(geom.bottom() - new_h)
            if "bottom" in self._resize_direction:
                geom.setHeight(max(min_h, geom.height() + delta.y()))

            self.setGeometry(geom)
            self.setCursor(self._get_cursor_for_direction(self._resize_direction))
            event.accept()
            return

        if not self.isMaximized() and event.buttons() == Qt.MouseButton.NoButton:
            direction = self._get_direction(event.position().toPoint())
            if direction:
                self.setCursor(self._get_cursor_for_direction(direction))
            else:
                self.unsetCursor()
        elif event.buttons() == Qt.MouseButton.NoButton:
            self.unsetCursor()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._resize_direction = None
            self.controller.save_states()
            
            # Po pustení tlačidla aktualizujeme kurzor podľa aktuálnej polohy
            direction = self._get_direction(event.position().toPoint())
            if direction and not self.isMaximized():
                self.setCursor(self._get_cursor_for_direction(direction))
            else:
                self.unsetCursor()
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'controller'):
            self.controller.save_states()

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, 'controller'):
            self.controller.save_states()

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        super().paintEvent(event)

    def retranslate_ui(self, lang_code=None):
        LanguageManager.translate_ui(self)

    def closeEvent(self, event):
        self.controller.save_all_states()
        LanguageManager.disconnect_language_changed(self.retranslate_ui)
        event.accept()