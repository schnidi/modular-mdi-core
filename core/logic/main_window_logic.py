"""
Súbor: core/logic/main_window_logic.py
Hlavný kontrolér pre správu MDI plochy a pod-okien s pamäťou plávajúceho stavu,
presnou pixelovou geometriou (bez posunu o lištu), mantinelmi a aktívnou 6px zónou.
"""

import os
import configparser
from PyQt6.QtCore import QObject, QEvent, QByteArray, QTimer, Qt, QPoint, QRect
from PyQt6.QtWidgets import QMdiSubWindow, QWidget, QVBoxLayout
from PyQt6.QtGui import QCursor

from core._path import Paths
from core.logic.plugin.service_manager import ServiceManager
from core.windows.custom_title_bar_mdi import CustomTitleBarMdi
from core.logic.services.window_bounds_manager import WindowBoundsManager


class FramelessMdiSubWindow(QMdiSubWindow):
    MARGIN = 6
    RESTORE_RATIO = 0.8  # 80 % plochy iba ako počiatočný fallback

    def __init__(self, parent=None, controller=None):
        self.controller = controller
        self._resizing = False
        self._resize_direction = None
        self._drag_start_pos = QPoint()
        self._drag_start_geom = QRect()

        self._mode = "normal"
        self._is_changing_mode = False
        self._is_clamping = False
        self._is_restoring = False
        self._floating_geometry = None

        self.title_bar = None
        self.client_widget = None
        self.container = None

        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)  # Natívny systémový atribút pre Hover
        self.setMouseTracking(True)

    def setup_content(self, client_widget: QWidget, title: str = ""):
        self.client_widget = client_widget
        
        self.container = QWidget(self)
        self.container.setObjectName("MdiContainer")
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        self.title_bar = CustomTitleBarMdi(self)
        if title:
            self.title_bar.set_title(title)
            self.setWindowTitle(title)

        layout.addWidget(self.title_bar, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.client_widget, 1)
        self.setWidget(self.container)

    def _update_floating_geometry(self):
        """Aktualizuje plávajúci stav IBA keď je okno v normal režime, nemení sa stav a neobnovuje sa."""
        if not self._is_changing_mode and not self._is_restoring and self._mode == "normal" and self.height() > 50:
            self._floating_geometry = self.geometry()

    # ========================================================
    # PRECHODY MEDZI STAVMI (PLÁVAJÚCI, MAX, MIN)
    # ========================================================

    def do_maximize_100(self):
        """Maximalizuje okno na celú MDI plochu."""
        if self._mode == "normal":
            self._update_floating_geometry()

        self._is_changing_mode = True
        self._mode = "maximized"
        try:
            self.showNormal()
            mdi = self.mdiArea()
            if mdi:
                self.setGeometry(0, 0, mdi.viewport().width(), mdi.viewport().height())
        finally:
            self._is_changing_mode = False

        if self.title_bar:
            self.title_bar.set_maximize_icon("restore_white.svg")

        if self.controller:
            self.controller.save_states()

    def do_restore(self):
        """Obnoví okno presne do jeho plávajúceho stavu (bez posunu o lištu)."""
        self._is_changing_mode = True
        try:
            self.showNormal()
            if self._floating_geometry and self._floating_geometry.isValid() and self._floating_geometry.height() > 50:
                self.setGeometry(self._floating_geometry)
            else:
                self._apply_fallback_80()
            self._mode = "normal"
        finally:
            self._is_changing_mode = False

        if self.title_bar:
            self.title_bar.set_maximize_icon("maximize_white.svg")

        if self.controller:
            self.controller.save_states()

    def do_minimize(self):
        """Zbalí okno do lišty."""
        if self._mode == "minimized":
            return

        if self._mode == "normal":
            self._update_floating_geometry()

        self._is_changing_mode = True
        self._mode = "minimized"
        try:
            self.showNormal()
            mdi = self.mdiArea()
            if mdi:
                bottom_y = max(0, mdi.viewport().height() - 36)
                self.setGeometry(self.x(), bottom_y, 220, 32)
        finally:
            self._is_changing_mode = False

        if self.title_bar:
            self.title_bar.set_maximize_icon("maximize_white.svg")

        if self.controller:
            self.controller.save_states()

    def handle_maximize_restore_button(self):
        """Obsluha tlačidla Štvorec / Dve okienka."""
        if self._mode == "maximized":
            self.do_restore()
        else:
            self.do_maximize_100()

    def _apply_fallback_80(self):
        """Počiatočný prepočet na 80 % (len pri prvom štarte)."""
        mdi = self.mdiArea()
        if mdi:
            new_w = max(400, int(mdi.viewport().width() * self.RESTORE_RATIO))
            new_h = max(300, int(mdi.viewport().height() * self.RESTORE_RATIO))
            new_x = max(0, (mdi.viewport().width() - new_w) // 2)
            new_y = max(0, (mdi.viewport().height() - new_h) // 2)
            self.setGeometry(new_x, new_y, new_w, new_h)
            self._floating_geometry = self.geometry()

    def on_viewport_resized(self, vw: int, vh: int):
        """Automaticky prispôsobí okno, keď sa zmenší alebo zväčší hlavné okno."""
        if vw <= 50 or vh <= 50 or self._is_restoring:
            return

        if self._mode == "maximized":
            self._is_changing_mode = True
            try:
                self.setGeometry(0, 0, vw, vh)
            finally:
                self._is_changing_mode = False

        elif self._mode == "minimized":
            self._is_changing_mode = True
            try:
                bottom_y = max(0, vh - 36)
                new_x = max(0, min(self.x(), vw - 220))
                self.setGeometry(new_x, bottom_y, min(220, vw), 32)
            finally:
                self._is_changing_mode = False

        elif self._mode == "normal":
            cur_x = self.x()
            cur_y = self.y()
            cur_w = self.width()
            cur_h = self.height()

            # Zmenšenie pri pretečení rozmerov
            new_w = min(cur_w, vw)
            new_h = min(cur_h, vh)
            
            # Vrátenie dnu pri vytlačení z plochy
            new_x = max(0, min(cur_x, vw - new_w))
            new_y = max(0, min(cur_y, vh - new_h))

            if (cur_x, cur_y, cur_w, cur_h) != (new_x, new_y, new_w, new_h):
                self._is_changing_mode = True
                try:
                    self.setGeometry(new_x, new_y, new_w, new_h)
                finally:
                    self._is_changing_mode = False
                self._update_floating_geometry()

    # ========================================================
    # NAŤAHOVANIE MYŠOU (RESIZE) & AKTÍVNA 6PX ZÓNA
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
        left = pos.x() <= m
        right = pos.x() >= rect.width() - m
        top = pos.y() <= m
        bottom = pos.y() >= rect.height() - m

        if top and left: return "top_left"
        if top and right: return "top_right"
        if bottom and left: return "bottom_left"
        if bottom and right: return "bottom_right"
        if left: return "left"
        if right: return "right"
        if top: return "top"
        if bottom: return "bottom"
        return ""

    def event(self, event: QEvent) -> bool:
        """Natívny Qt Hover systém - funguje 100% spoľahlivo ponad všetky deti okna."""
        if event.type() == QEvent.Type.HoverMove and self._mode == "normal" and not self._resizing:
            pos = event.position().toPoint()
            direction = self._get_direction(pos)
            if direction:
                self.setCursor(self._get_cursor_for_direction(direction))
            else:
                if self.cursor().shape() != Qt.CursorShape.ArrowCursor:
                    self.unsetCursor()
        elif event.type() == QEvent.Type.HoverLeave and not self._resizing:
            self.unsetCursor()

        return super().event(event)

    def leaveEvent(self, event):
        if not getattr(self, "_resizing", False):
            self.unsetCursor()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._mode == "normal":
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
            min_w = 200
            min_h = 100

            mdi = self.mdiArea()
            max_w = mdi.viewport().width() if mdi else 9999
            max_h = mdi.viewport().height() if mdi else 9999

            if "left" in self._resize_direction:
                new_left = max(0, min(geom.right() - min_w, self._drag_start_geom.left() + delta.x()))
                geom.setLeft(new_left)
            if "right" in self._resize_direction:
                new_right = min(max_w, max(geom.left() + min_w, self._drag_start_geom.right() + delta.x()))
                geom.setRight(new_right)
            if "top" in self._resize_direction:
                new_top = max(0, min(geom.bottom() - min_h, self._drag_start_geom.top() + delta.y()))
                geom.setTop(new_top)
            if "bottom" in self._resize_direction:
                new_bottom = min(max_h, max(geom.top() + min_h, self._drag_start_geom.bottom() + delta.y()))
                geom.setBottom(new_bottom)

            self.setGeometry(geom)
            self.setCursor(self._get_cursor_for_direction(self._resize_direction))
            event.accept()
            return

        if self._mode == "normal":
            direction = self._get_direction(event.position().toPoint())
            if direction:
                self.setCursor(self._get_cursor_for_direction(direction))
            else:
                self.unsetCursor()
        else:
            self.unsetCursor()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._resize_direction = None
            self._update_floating_geometry()
            if self.controller:
                self.controller.save_states()
            
            # Aktualizácia kurzora po dokončení ťahania
            direction = self._get_direction(event.position().toPoint())
            if direction and self._mode == "normal":
                self.setCursor(self._get_cursor_for_direction(direction))
            else:
                self.unsetCursor()
        super().mouseReleaseEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        if not self._is_changing_mode and not self._is_restoring and self._mode == "normal":
            self._update_floating_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._is_restoring:
            self._update_floating_geometry()


class MainWindowController(QObject):
    """Kontrolér pre správu MDI plochy a ukladanie rozloženia do .ini súboru."""

    def __init__(self, view):
        super().__init__()
        self.view = view
        self.service_manager = ServiceManager.get_instance()
        self.config_path = os.path.join(Paths.get_config_dir(), "window_setup.ini")
        
        # REGISTRÁCIA SLUŽBY DO SERVICEMANAGERA (Z LOGICKEJ VRSTVY)
        self.service_manager.register_service("window_manager", self)

        self.sub_windows = {}
        
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(300)
        self.save_timer.timeout.connect(self.save_all_states)

        # Sledovanie zmeny veľkosti a kliknutia na pod-okná
        if hasattr(self.view, 'mdiArea') and self.view.mdiArea:
            self.view.mdiArea.viewport().installEventFilter(self)
            self.view.mdiArea.subWindowActivated.connect(self._on_sub_window_activated)

    def _on_sub_window_activated(self, active_sub):
        """Dynamicky nastaví 'active' vlastnosť pre QSS na kliknuté okno aj jeho kontajner."""
        if not hasattr(self.view, 'mdiArea') or not self.view.mdiArea:
            return

        for sub in self.view.mdiArea.subWindowList():
            is_active = (sub == active_sub)
            val = "true" if is_active else "false"

            # 1. Nastavenie priamo na MDI pod-okno
            if sub.property("active") != val:
                sub.setProperty("active", val)
                sub.style().unpolish(sub)
                sub.style().polish(sub)

            # 2. Nastavenie na vnútorný kontajner (ktorý nesie rámček)
            w = sub.widget()
            if w and w.property("active") != val:
                w.setProperty("active", val)
                w.style().unpolish(w)
                w.style().polish(w)

            # 3. Nastavenie na titulkovú lištu
            if hasattr(sub, 'title_bar') and sub.title_bar:
                if sub.title_bar.property("active") != val:
                    sub.title_bar.setProperty("active", val)
                    sub.title_bar.style().unpolish(sub.title_bar)
                    sub.title_bar.style().polish(sub.title_bar)

            sub.update()

    @staticmethod
    def rect_to_str(r: QRect) -> str:
        """Prevedie QRect na jednoduchý reťazec x,y,w,h."""
        if not r or not r.isValid():
            return ""
        return f"{r.x()},{r.y()},{r.width()},{r.height()}"

    @staticmethod
    def str_to_rect(s: str) -> QRect | None:
        """Prevedie reťazec x,y,w,h späť na QRect."""
        if not s:
            return None
        try:
            parts = [int(p.strip()) for p in s.split(",")]
            if len(parts) == 4 and parts[2] > 50 and parts[3] > 50:
                return QRect(parts[0], parts[1], parts[2], parts[3])
        except Exception:
            pass
        return None

    def eventFilter(self, obj, event):
        """Zachytáva zmenu veľkosti MDI plochy a prispôsobuje pod-okná."""
        if hasattr(self.view, 'mdiArea') and self.view.mdiArea and obj == self.view.mdiArea.viewport():
            if event.type() == QEvent.Type.Resize:
                vw = event.size().width()
                vh = event.size().height()
                for sub in list(self.sub_windows.values()):
                    if sub and sub.parent() and not sub.isHidden():
                        sub.on_viewport_resized(vw, vh)
        return super().eventFilter(obj, event)

    def restore_visual_state(self):
        """Obnoví geometriu hlavného okna zo súboru .ini."""
        if not os.path.exists(self.config_path):
            return

        config = configparser.ConfigParser()
        config.read(self.config_path, encoding='utf-8')

        if config.has_section("MainWindow"):
            geom_hex = config.get("MainWindow", "geometry", fallback=None)
            if geom_hex:
                self.view.restoreGeometry(QByteArray.fromHex(geom_hex.encode()))

    def open_sub_window(self, window_key: str, widget_factory_func, window_title: str = "") -> FramelessMdiSubWindow:
        """Otvorí pod-okno a nastaví presnú geometriu bez posunu."""
        if window_key in self.sub_windows:
            sub_window = self.sub_windows[window_key]
            if sub_window and sub_window.parent():
                sub_window.show()
                sub_window.raise_()
                sub_window.setFocus()
                self.view.mdiArea.setActiveSubWindow(sub_window)
                return sub_window

        # 1. Vytvorenie widgetu
        client_widget = widget_factory_func()

        # 2. Vytvorenie FramelessMdiSubWindow
        sub_window = FramelessMdiSubWindow(self.view.mdiArea, controller=self)
        sub_window._is_restoring = True  # Zámok proti posunu pri štarte
        sub_window.setup_content(client_widget, window_title)
        self.view.mdiArea.addSubWindow(sub_window)

        # AKTIVÁCIA CENTRÁLNEHO STRÁŽCU MANTINELOV
        WindowBoundsManager.guard_mdi_sub_window(
            sub_window,
            on_geometry_changed=lambda geo: self.save_states()
        )

        # 3. Načítanie stavov z .ini
        config = configparser.ConfigParser()
        saved_mode = "normal"
        floating_rect = None

        if os.path.exists(self.config_path):
            config.read(self.config_path, encoding='utf-8')
            if config.has_section(window_key):
                # 1. Záznam: Plávajúci stav
                geom_str = config.get(window_key, "floating_geometry", fallback=None)
                floating_rect = self.str_to_rect(geom_str)

                # 2. Záznam: Režim pri zatvorení
                saved_mode = config.get(window_key, "mode", fallback="normal")

        # 4. Sledovanie zatvorenia
        sub_window.destroyed.connect(lambda: self._on_sub_window_destroyed(window_key))
        self.sub_windows[window_key] = sub_window

        # 5. Aplikácia plávajúcej veľkosti
        sub_window.show()
        if floating_rect and floating_rect.isValid():
            sub_window._floating_geometry = floating_rect
            sub_window.setGeometry(floating_rect)
        else:
            sub_window._apply_fallback_80()

        # 6. Aplikácia režimu
        if saved_mode == "maximized":
            QTimer.singleShot(0, sub_window.do_maximize_100)
        elif saved_mode == "minimized":
            QTimer.singleShot(0, sub_window.do_minimize)
        else:
            sub_window._mode = "normal"

        # Uvoľnenie zámku po vykreslení
        def _unlock():
            sub_window._is_restoring = False
            sub_window._update_floating_geometry()

        QTimer.singleShot(100, _unlock)

        self.view.mdiArea.setActiveSubWindow(sub_window)
        self._on_sub_window_activated(sub_window)
        self.save_states()
        self.update_main_window_minimum_size()
        return sub_window

    def _on_sub_window_destroyed(self, window_key: str):
        if window_key in self.sub_windows:
            del self.sub_windows[window_key]
        self.save_states()
        self.update_main_window_minimum_size()

    def save_states(self):
        self.save_timer.start()

    def save_all_states(self):
        """Zapíše presné pixelové súradnice do .ini súboru."""
        config = configparser.ConfigParser()
        if os.path.exists(self.config_path):
            config.read(self.config_path, encoding='utf-8')

        if not config.has_section("MainWindow"):
            config.add_section("MainWindow")
        config.set("MainWindow", "geometry", self.view.saveGeometry().toHex().data().decode())

        for key, sub_win in self.sub_windows.items():
            if sub_win and sub_win.parent():
                if not config.has_section(key):
                    config.add_section(key)
                
                config.set(key, "is_open", str(not sub_win.isHidden()))
                config.set(key, "mode", sub_win._mode)
                
                # ZÁZNAM 1: Aktuálna presná geometria
                config.set(key, "current_geometry", self.rect_to_str(sub_win.geometry()))
                
                # ZÁZNAM 2: Plávajúca geometria (pamäť rozmeru)
                fg = sub_win._floating_geometry if sub_win._floating_geometry else sub_win.geometry()
                config.set(key, "floating_geometry", self.rect_to_str(fg))

        with open(self.config_path, "w", encoding='utf-8') as f:
            config.write(f)

    def update_main_window_minimum_size(self):
        max_w, max_h = 700, 450
        for sub in self.sub_windows.values():
            if sub and sub.parent() and not sub.isHidden():
                hint = sub.minimumSizeHint()
                max_w = max(max_w, hint.width() + 50)
                max_h = max(max_h, hint.height() + 80)
        self.view.setMinimumSize(max_w, max_h)