"""
Súbor: core/logic/services/window_bounds_manager.py
Centrálna služba a EventFilter pre stráženie mantinelov všetkých typov okien.
Presne rozlišuje lokálne MDI súradnice od globálnych súradníc dialógov.
"""

from typing import Callable, Optional
from PyQt6.QtCore import QObject, QEvent, QTimer, QRect
from PyQt6.QtWidgets import QWidget, QMdiSubWindow, QMdiArea, QDialog, QApplication
from PyQt6.QtGui import QGuiApplication


class WindowBoundsClampFilter(QObject):
    """
    Univerzálny EventFilter na odchytávanie udalostí presunu (Move) a zmeny veľkosti (Resize).
    """

    def __init__(
        self,
        target_widget: QWidget,
        parent: Optional[QObject] = None,
        boundary_mode: str = "auto",
        on_geometry_changed: Optional[Callable[[QRect], None]] = None,
        debounce_ms: int = 300
    ):
        super().__init__(parent or target_widget)
        self.target_widget = target_widget
        self.boundary_mode = boundary_mode
        self.on_geometry_changed = on_geometry_changed

        self._is_adjusting = False
        self._pending_geometry: Optional[QRect] = None

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(debounce_ms)
        self._save_timer.timeout.connect(self._emit_geometry_changed)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj == self.target_widget and not self._is_adjusting:
            if event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
                self._clamp_bounds(self.target_widget)

        return super().eventFilter(obj, event)

    def _clamp_bounds(self, widget: QWidget):
        """Vyberie správny matematický model podľa typu okna."""
        # A) Ak ide o MDI pod-okno
        if isinstance(widget, QMdiSubWindow) or self.boundary_mode == "mdi" or (hasattr(widget, "mdiArea") and widget.mdiArea()):
            self._clamp_mdi_subwindow(widget)
        # B) Ak ide o dialóg alebo samostatné okno
        else:
            self._clamp_dialog_or_window(widget)

    def _clamp_mdi_subwindow(self, sub_win: QWidget):
        """Prepočet pre MDI pod-okná (lokálne súradnice 0,0 až viewport max)."""
        area = None
        if hasattr(sub_win, "mdiArea") and callable(sub_win.mdiArea):
            area = sub_win.mdiArea()
        elif isinstance(sub_win.parentWidget(), QMdiArea):
            area = sub_win.parentWidget()

        if not area:
            return

        viewport = area.viewport()
        vw = viewport.width()
        vh = viewport.height()

        if vw <= 50 or vh <= 50:
            return

        geo = sub_win.geometry()
        cur_x, cur_y, cur_w, cur_h = geo.x(), geo.y(), geo.width(), geo.height()

        # Obmedzenie rozmerov na max plochu
        new_w = min(cur_w, vw)
        new_h = min(cur_h, vh)

        # Prísne mantinely: X a Y nesmú byť menšie ako 0 a nesmú vytŕčať z plochy
        new_x = max(0, min(cur_x, max(0, vw - new_w)))
        new_y = max(0, min(cur_y, max(0, vh - new_h)))

        if (new_x, new_y, new_w, new_h) != (cur_x, cur_y, cur_w, cur_h):
            self._is_adjusting = True
            try:
                sub_win.setGeometry(new_x, new_y, new_w, new_h)
            finally:
                self._is_adjusting = False

        if self.on_geometry_changed:
            self._pending_geometry = sub_win.geometry()
            self._save_timer.start()

    def _clamp_dialog_or_window(self, dialog: QWidget):
        """Prepočet pre Dialógy (globálne súradnice monitora a rodičovského okna)."""
        geo = dialog.geometry()
        cur_x, cur_y, cur_w, cur_h = geo.x(), geo.y(), geo.width(), geo.height()

        # Zistenie rodičovského okna (hlavné okno)
        parent = dialog.parentWidget()
        while parent and parent.parentWidget() and not parent.isWindow():
            parent = parent.parentWidget()

        # 1. Ak má rodičovské okno, držíme dialóg v ňom
        if parent and parent.isVisible() and parent.width() > 100:
            p_geo = parent.geometry()
            min_x = p_geo.left()
            max_x = max(min_x, p_geo.right() - cur_w + 1)
            min_y = p_geo.top()
            max_y = max(min_y, p_geo.bottom() - cur_h + 1)
        # 2. Inak ho držíme v rámci obrazovky monitora
        else:
            screen = dialog.screen() or QGuiApplication.primaryScreen()
            if not screen:
                return
            s_geo = screen.availableGeometry()
            min_x = s_geo.left()
            max_x = max(min_x, s_geo.right() - cur_w + 1)
            min_y = s_geo.top()
            max_y = max(min_y, s_geo.bottom() - cur_h + 1)

        new_x = max(min_x, min(cur_x, max_x))
        new_y = max(min_y, min(cur_y, max_y))

        if (new_x, new_y) != (cur_x, cur_y):
            self._is_adjusting = True
            try:
                dialog.move(new_x, new_y)
            finally:
                self._is_adjusting = False

    def _emit_geometry_changed(self):
        if self._pending_geometry and self.on_geometry_changed:
            self.on_geometry_changed(self._pending_geometry)

    def flush(self):
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._emit_geometry_changed()


class WindowBoundsManager:
    """Centrálna služba správy mantinelov."""
    _instance = None

    @classmethod
    def get_instance(cls) -> "WindowBoundsManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def attach_guard(
        widget: QWidget,
        boundary_mode: str = "auto",
        on_geometry_changed: Optional[Callable[[QRect], None]] = None
    ) -> WindowBoundsClampFilter:
        clamp_filter = WindowBoundsClampFilter(
            target_widget=widget,
            boundary_mode=boundary_mode,
            on_geometry_changed=on_geometry_changed
        )
        widget.installEventFilter(clamp_filter)

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(clamp_filter.flush)

        return clamp_filter

    @staticmethod
    def guard_mdi_sub_window(
        sub_window: QMdiSubWindow,
        on_geometry_changed: Optional[Callable[[QRect], None]] = None
    ) -> WindowBoundsClampFilter:
        return WindowBoundsManager.attach_guard(
            widget=sub_window,
            boundary_mode="mdi",
            on_geometry_changed=on_geometry_changed
        )

    @staticmethod
    def guard_dialog(dialog: QDialog) -> WindowBoundsClampFilter:
        return WindowBoundsManager.attach_guard(
            widget=dialog,
            boundary_mode="parent"
        )