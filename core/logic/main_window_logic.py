"""
Súbor: core/logic/main_window_logic.py
Hlavný kontrolér pre správu MDI plochy a pod-okien.
"""

import os
import configparser
from PyQt6.QtCore import QObject, QEvent, QByteArray, QTimer, Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QMouseEvent
from PyQt6.QtWidgets import QMdiSubWindow, QWidget, QVBoxLayout, QApplication

from core._path import Paths
from core.logic.plugin.service_manager import ServiceManager
from core.windows.custom_title_bar_mdi import CustomTitleBarMdi
from core.logic.services.window_bounds_manager import WindowBoundsManager


class _MdiMoveGhost(QWidget):
    """Natívne top-level okno so snímkou MDI pod-okna — DWM ho posúva bez prekresľovania QMdiArea."""

    def __init__(self, pixmap, owner: "FramelessMdiSubWindow"):
        super().__init__(None)
        self._owner = owner
        self._pixmap = pixmap
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setFixedSize(pixmap.size())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawPixmap(0, 0, self._pixmap)

    def mouseMoveEvent(self, event):
        self._owner.update_title_drag(event.globalPosition().toPoint())
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._owner.end_title_drag()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class FramelessMdiSubWindow(QMdiSubWindow):
    MARGIN = 6
    RESTORE_RATIO = 0.8

    MINIMIZED_WIDTH = 290
    MINIMIZED_HEIGHT = 34

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
        self._is_dragging = False
        self._floating_geometry = None
        self._move_ghost = None
        self._drag_ghost_active = False
        self._drag_filter_installed = False
        self._was_hidden_for_drag = False

        self.title_bar = None
        self.client_widget = None
        self.container = None

        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)

    def setup_content(self, client_widget: QWidget, title: str = ""):
        self.client_widget = client_widget

        self.container = QWidget(self)
        self.container.setObjectName("MdiContainer")

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)

        self.title_bar = CustomTitleBarMdi(self)

        initial_title = self.client_widget.windowTitle() if self.client_widget.windowTitle() else title
        if initial_title:
            self.title_bar.set_title(initial_title)
            self.setWindowTitle(initial_title)

        self.client_widget.windowTitleChanged.connect(self.title_bar.set_title)
        self.client_widget.windowTitleChanged.connect(self.setWindowTitle)

        layout.addWidget(self.title_bar, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.client_widget, 1)
        self.setWidget(self.container)

    def _update_floating_geometry(self):
        """Aktualizuje plávajúci stav IBA keď je okno v normal režime."""
        if not self._is_changing_mode and not self._is_restoring and self._mode == "normal" and self.height() > 50:
            self._floating_geometry = self.geometry()

    def _clamp_normal_geometry(self, geo: QRect) -> QRect:
        mdi = self.mdiArea()
        if not mdi:
            return QRect(geo)
        vw = mdi.viewport().width()
        vh = mdi.viewport().height()
        w = min(max(geo.width(), 200), vw)
        h = min(max(geo.height(), 100 if self._mode != "minimized" else self.MINIMIZED_HEIGHT), vh)
        if self._mode == "minimized":
            w = min(self.MINIMIZED_WIDTH, vw)
            h = min(self.MINIMIZED_HEIGHT, vh)
        x = max(0, min(geo.x(), max(0, vw - w)))
        y = max(0, min(geo.y(), max(0, vh - h)))
        return QRect(x, y, w, h)

    def _mdi_local_to_global(self, geo: QRect) -> QPoint:
        mdi = self.mdiArea()
        if not mdi:
            return geo.topLeft()
        return mdi.viewport().mapToGlobal(geo.topLeft())

    def _install_drag_filter(self):
        app = QApplication.instance()
        if app and not self._drag_filter_installed:
            app.installEventFilter(self)
            self._drag_filter_installed = True

    def _remove_drag_filter(self):
        app = QApplication.instance()
        if app and self._drag_filter_installed:
            app.removeEventFilter(self)
            self._drag_filter_installed = False

    def _destroy_move_ghost(self):
        ghost = self._move_ghost
        self._move_ghost = None
        self._drag_ghost_active = False
        if ghost is not None:
            ghost.releaseMouse()
            ghost.hide()
            ghost.deleteLater()

    def _activate_move_ghost(self):
        if self._drag_ghost_active:
            return
        self._drag_ghost_active = True
        pixmap = self.grab()
        self._move_ghost = _MdiMoveGhost(pixmap, self)
        self._move_ghost.move(self.mapToGlobal(QPoint(0, 0)))
        self._move_ghost.show()
        self._move_ghost.raise_()
        self._move_ghost.grabMouse()
        self._was_hidden_for_drag = True
        self.hide()

    def start_title_drag(self, global_pos: QPoint):
        self._is_dragging = True
        self._drag_ghost_active = False
        self._was_hidden_for_drag = False
        self._drag_start_pos = QPoint(global_pos)
        self._drag_start_geom = QRect(self.geometry())
        self._install_drag_filter()

    def update_title_drag(self, global_pos: QPoint):
        if not self._is_dragging:
            return
        delta = global_pos - self._drag_start_pos
        if not self._drag_ghost_active:
            if delta.manhattanLength() < 4:
                return
            self._activate_move_ghost()

        clamped = self._clamp_normal_geometry(self._drag_start_geom.translated(delta))
        if self._move_ghost is not None:
            self._move_ghost.move(self._mdi_local_to_global(clamped))

    def end_title_drag(self):
        if not self._is_dragging:
            return
        self._is_dragging = False
        self._remove_drag_filter()

        final_geo = QRect(self._drag_start_geom)
        if self._move_ghost is not None and self.mdiArea():
            local_tl = self.mdiArea().viewport().mapFromGlobal(self._move_ghost.pos())
            final_geo.moveTopLeft(local_tl)

        self._destroy_move_ghost()
        self.setGeometry(self._clamp_normal_geometry(final_geo))
        if self._was_hidden_for_drag:
            self.show()
            mdi = self.mdiArea()
            if mdi:
                mdi.setActiveSubWindow(self)
        self._was_hidden_for_drag = False
        self._update_floating_geometry()

    def eventFilter(self, obj, event):
        if self._is_dragging and isinstance(event, QMouseEvent):
            if event.type() == QEvent.Type.MouseMove:
                self.update_title_drag(event.globalPosition().toPoint())
            elif (
                event.type() == QEvent.Type.MouseButtonRelease
                and event.button() == Qt.MouseButton.LeftButton
            ):
                self.end_title_drag()
        return super().eventFilter(obj, event)

    # ========================================================
    # PRECHODY MEDZI STAVMI (PLÁVAJÚCI, MAX, MIN)
    # ========================================================

    def _cancel_interactive_geometry(self):
        if self._is_dragging:
            self.end_title_drag()
        if self._resizing:
            self.releaseMouse()
            if self.client_widget:
                self.client_widget.setUpdatesEnabled(True)
        self._is_dragging = False
        self._resizing = False
        self._resize_direction = None

    def do_maximize_100(self):
        """Maximalizuje okno na celú MDI plochu."""
        self._cancel_interactive_geometry()
        if self._mode == "normal":
            self._update_floating_geometry()

        self._is_changing_mode = True
        self._mode = "maximized"
        try:
            # Uvoľniť fixnú veľkosť
            self.setMinimumSize(200, 100)
            self.setMaximumSize(16777215, 16777215)

            if self.client_widget:
                self.client_widget.show()

            self.showNormal()
            mdi = self.mdiArea()
            if mdi:
                self.setGeometry(0, 0, mdi.viewport().width(), mdi.viewport().height())
        finally:
            self._is_changing_mode = False

        if self.title_bar:
            self.title_bar.set_maximize_icon("restore_white.svg")
            if hasattr(self.title_bar, 'set_minimized_state'):
                self.title_bar.set_minimized_state(False)

        if self.controller:
            self.controller.save_states()

    def do_restore(self):
        """Obnoví okno presne do jeho plávajúceho stavu."""
        self._cancel_interactive_geometry()
        self._is_changing_mode = True
        try:
            # Uvoľniť fixnú veľkosť
            self.setMinimumSize(200, 100)
            self.setMaximumSize(16777215, 16777215)

            if self.client_widget:
                self.client_widget.show()

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
            if hasattr(self.title_bar, 'set_minimized_state'):
                self.title_bar.set_minimized_state(False)

        if self.controller:
            self.controller.save_states()

    def do_minimize(self):
        """Zbalí okno do lišty a zamkne ho na fixnú veľkosť."""
        if self._mode == "minimized":
            return
        self._cancel_interactive_geometry()

        if self._mode == "normal":
            self._update_floating_geometry()

        self._is_changing_mode = True
        self._mode = "minimized"
        try:
            if self.client_widget:
                self.client_widget.hide()

            # ZAMKNÚŤ PEVNÚ VEĽKOSŤ: Úplne eliminuje akékoľvek chvenie rozmerov pri pohybe
            self.setFixedSize(self.MINIMIZED_WIDTH, self.MINIMIZED_HEIGHT)

            self.showNormal()
            mdi = self.mdiArea()
            if mdi:
                bottom_y = max(0, mdi.viewport().height() - (self.MINIMIZED_HEIGHT + 4))
                new_x = max(0, min(self.x(), mdi.viewport().width() - self.MINIMIZED_WIDTH))
                self.move(new_x, bottom_y)
        finally:
            self._is_changing_mode = False

        if self.title_bar:
            self.title_bar.set_maximize_icon("maximize_white.svg")
            if hasattr(self.title_bar, 'set_minimized_state'):
                self.title_bar.set_minimized_state(True)

        if self.controller:
            self.controller.save_states()

    def handle_maximize_restore_button(self):
        if self._mode == "maximized":
            self.do_restore()
        else:
            self.do_maximize_100()

    def _apply_fallback_80(self):
        mdi = self.mdiArea()
        if mdi:
            new_w = max(400, int(mdi.viewport().width() * self.RESTORE_RATIO))
            new_h = max(300, int(mdi.viewport().height() * self.RESTORE_RATIO))
            new_x = max(0, (mdi.viewport().width() - new_w) // 2)
            new_y = max(0, (mdi.viewport().height() - new_h) // 2)
            self.setGeometry(new_x, new_y, new_w, new_h)
            self._floating_geometry = self.geometry()

    def on_viewport_resized(self, vw: int, vh: int):
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
                bottom_y = max(0, vh - (self.MINIMIZED_HEIGHT + 4))
                new_x = max(0, min(self.x(), vw - self.MINIMIZED_WIDTH))
                self.move(new_x, bottom_y)
            finally:
                self._is_changing_mode = False

        elif self._mode == "normal":
            cur_x = self.x()
            cur_y = self.y()
            cur_w = self.width()
            cur_h = self.height()

            new_w = min(cur_w, vw)
            new_h = min(cur_h, vh)
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
    # RESIZE MYŠOU & 6PX ZÓNA (IBA V NORMAL REŽIME)
    # ========================================================

    def _get_cursor_for_direction(self, direction: str) -> Qt.CursorShape:
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
        if event.type() == QEvent.Type.HoverMove and self._mode == "normal" and not self._resizing and not self._is_dragging:
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
                if self.client_widget:
                    self.client_widget.setUpdatesEnabled(False)
                self.grabMouse()
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

            self.setGeometry(self._clamp_normal_geometry(geom))
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
            self.releaseMouse()
            if self.client_widget:
                self.client_widget.setUpdatesEnabled(True)
            self._resizing = False
            self._resize_direction = None
            self._update_floating_geometry()
            if self.controller:
                self.controller.save_states()

            direction = self._get_direction(event.position().toPoint())
            if direction and self._mode == "normal":
                self.setCursor(self._get_cursor_for_direction(direction))
            else:
                self.unsetCursor()
        super().mouseReleaseEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)
        if not self._is_changing_mode and not self._is_restoring and not self._is_dragging and self._mode == "normal":
            self._update_floating_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._is_restoring and self._mode == "normal":
            self._update_floating_geometry()


class MainWindowController(QObject):
    """Kontrolér pre správu MDI plochy a ukladanie rozloženia do .ini súboru."""

    def __init__(self, view):
        super().__init__()
        self.view = view
        self.service_manager = ServiceManager.get_instance()
        self.config_path = os.path.join(Paths.get_config_dir(), "window_setup.ini")

        self.service_manager.register_service("window_manager", self)

        self.sub_windows = {}
        self._last_active_sub = None

        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(300)
        self.save_timer.timeout.connect(self.save_all_states)

        if hasattr(self.view, 'mdiArea') and self.view.mdiArea:
            self.view.mdiArea.viewport().installEventFilter(self)
            self.view.mdiArea.subWindowActivated.connect(self._on_sub_window_activated)

    def _apply_active_style(self, sub, is_active: bool):
        if not sub:
            return
        val = "true" if is_active else "false"

        if sub.property("active") != val:
            sub.setProperty("active", val)
            sub.style().unpolish(sub)
            sub.style().polish(sub)

        w = sub.widget()
        if w and w.property("active") != val:
            w.setProperty("active", val)
            w.style().unpolish(w)
            w.style().polish(w)

        title_bar = getattr(sub, 'title_bar', None)
        if title_bar and title_bar.property("active") != val:
            title_bar.setProperty("active", val)
            title_bar.style().unpolish(title_bar)
            title_bar.style().polish(title_bar)

        sub.update()

    def _on_sub_window_activated(self, active_sub):
        if not hasattr(self.view, 'mdiArea') or not self.view.mdiArea:
            return

        if active_sub and (
            getattr(active_sub, '_is_dragging', False)
            or getattr(active_sub, '_resizing', False)
        ):
            return

        previous = self._last_active_sub
        if previous is active_sub:
            return

        if previous and previous.parent():
            self._apply_active_style(previous, False)
        self._apply_active_style(active_sub, True)
        self._last_active_sub = active_sub

    @staticmethod
    def rect_to_str(r: QRect) -> str:
        if not r or not r.isValid():
            return ""
        return f"{r.x()},{r.y()},{r.width()},{r.height()}"

    @staticmethod
    def str_to_rect(s: str) -> QRect | None:
        if not s:
            return None
        try:
            parts = [int(p.strip()) for p in s.split(",")]
            if len(parts) == 4 and parts[2] > 50 and parts[3] > 20:
                return QRect(parts[0], parts[1], parts[2], parts[3])
        except Exception:
            pass
        return None

    def eventFilter(self, obj, event):
        if hasattr(self.view, 'mdiArea') and self.view.mdiArea and obj == self.view.mdiArea.viewport():
            if event.type() == QEvent.Type.Resize:
                vw = event.size().width()
                vh = event.size().height()
                for sub in list(self.sub_windows.values()):
                    if sub and sub.parent() and not sub.isHidden():
                        sub.on_viewport_resized(vw, vh)
        return super().eventFilter(obj, event)

    def restore_visual_state(self):
        if not os.path.exists(self.config_path):
            return

        config = configparser.ConfigParser()
        config.read(self.config_path, encoding='utf-8')

        if config.has_section("MainWindow"):
            geom_hex = config.get("MainWindow", "geometry", fallback=None)
            if geom_hex:
                self.view.restoreGeometry(QByteArray.fromHex(geom_hex.encode()))

    def open_sub_window(self, window_key: str, widget_factory_func, window_title: str = "", module_name: str = None) -> FramelessMdiSubWindow:
        if window_key in self.sub_windows:
            sub_window = self.sub_windows[window_key]
            if sub_window and sub_window.parent():
                sub_window.show()
                sub_window.raise_()
                sub_window.setFocus()
                self.view.mdiArea.setActiveSubWindow(sub_window)
                return sub_window

        client_widget = widget_factory_func()

        if module_name:
            client_widget.setProperty("module_name", module_name)

        sub_window = FramelessMdiSubWindow(self.view.mdiArea, controller=self)
        if module_name:
            sub_window.setProperty("module_name", module_name)

        sub_window._is_restoring = True
        sub_window.setup_content(client_widget, window_title)
        self.view.mdiArea.addSubWindow(sub_window)

        WindowBoundsManager.guard_mdi_sub_window(
            sub_window,
            on_geometry_changed=lambda geo: self.save_states()
        )

        config = configparser.ConfigParser()
        saved_mode = "normal"
        floating_rect = None

        if os.path.exists(self.config_path):
            config.read(self.config_path, encoding='utf-8')
            if config.has_section(window_key):
                geom_str = config.get(window_key, "floating_geometry", fallback=None)
                floating_rect = self.str_to_rect(geom_str)
                saved_mode = config.get(window_key, "mode", fallback="normal")

        sub_window.destroyed.connect(lambda: self._on_sub_window_destroyed(window_key))
        self.sub_windows[window_key] = sub_window

        sub_window.show()
        if floating_rect and floating_rect.isValid():
            sub_window._floating_geometry = floating_rect
            sub_window.setGeometry(floating_rect)
        else:
            sub_window._apply_fallback_80()

        if saved_mode == "maximized":
            QTimer.singleShot(0, sub_window.do_maximize_100)
        elif saved_mode == "minimized":
            QTimer.singleShot(0, sub_window.do_minimize)
        else:
            sub_window._mode = "normal"

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
        gone = self.sub_windows.get(window_key)
        if gone is self._last_active_sub:
            self._last_active_sub = None
        if window_key in self.sub_windows:
            del self.sub_windows[window_key]
        self.save_states()
        self.update_main_window_minimum_size()

    def save_states(self):
        self.save_timer.start()

    def save_all_states(self):
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
                config.set(key, "current_geometry", self.rect_to_str(sub_win.geometry()))

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