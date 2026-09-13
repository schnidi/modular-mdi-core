"""
Súbor: core/logic/services/window_bounds_manager.py
Centrálna služba a EventFilter pre stráženie mantinelov všetkých typov okien.
Využíva 100% dynamický prepočet súradníc cez Qt maticu (mapToGlobal),
bez akýchkoľvek natvrdo zapísaných hodnôt.
"""

from typing import Callable, Optional
from PyQt6.QtCore import QObject, QEvent, QTimer, QRect, QPoint
from PyQt6.QtWidgets import QWidget, QMdiSubWindow, QMdiArea, QDialog, QApplication, QMenuBar
from PyQt6.QtGui import QGuiApplication


class WindowBoundsClampFilter(QObject):
    """
    Univerzálny EventFilter na odchytávanie udalostí presunu (Move) a zmeny veľkosti (Resize).
    V reálnom čase drží okná v ich povolených pracovných zónach.
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

        # Odložený časovač na zápis geometrie (nezapisuje pri každom jednotlivom pixeli)
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
        # A) Ak ide o MDI pod-okno (lokálny priestor MDI plochy)
        if isinstance(widget, QMdiSubWindow) or self.boundary_mode == "mdi" or (hasattr(widget, "mdiArea") and widget.mdiArea()):
            self._clamp_mdi_subwindow(widget)
        # B) Ak ide o dialóg alebo samostatné okno (globálny priestor monitora)
        else:
            self._clamp_dialog_or_window(widget)

    def _clamp_mdi_subwindow(self, sub_win: QWidget):
        """
        Dynamický prepočet pre MDI pod-okná.
        Súradnice 0,0 sú viazané striktne na aktívny viewport MDI plochy.
        """
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

        # Obmedzenie rozmerov okna na maximálnu veľkosť plochy
        new_w = min(cur_w, vw)
        new_h = min(cur_h, vh)

        # Presné mantinely: okno nesmie mať X, Y záporné ani pretekať vpravo/dole
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
        """
        100% dynamický prepočet pre Dialógy a chybové hlásenia.
        Cez mapToGlobal vypočíta presné globálne hranice tak, aby okno
        nikdy neprekrylo hornú lištu a menu bar hlavného okna.
        """
        geo = dialog.geometry()
        cur_x, cur_y, cur_w, cur_h = geo.x(), geo.y(), geo.width(), geo.height()

        # Nájdenie hlavného rodičovského okna
        parent = dialog.parentWidget()
        while parent and parent.parentWidget() and not parent.isWindow():
            parent = parent.parentWidget()

        # 1. AK DIALÓG NEMÁ HLAVNÉ OKNO: Mantinel je obrazovka monitora
        if not parent or not parent.isVisible():
            screen = dialog.screen() or QGuiApplication.primaryScreen()
            if not screen:
                return
            s_geo = screen.availableGeometry()
            min_x, min_y = s_geo.left(), s_geo.top()
            max_x = max(min_x, s_geo.right() - cur_w + 1)
            max_y = max(min_y, s_geo.bottom() - cur_h + 1)

        else:
            # 2. PRIORITA: Ak má hlavné okno MDI plochu, mantinel je presne MDI plocha
            mdi_area = getattr(parent, "mdiArea", None) or parent.findChild(QMdiArea)
            
            if mdi_area and mdi_area.isVisible() and mdi_area.width() > 50:
                # Dynamický prepočet pixelu (0,0) MDI plochy na globálne súradnice monitora
                top_left = mdi_area.mapToGlobal(QPoint(0, 0))
                min_x = top_left.x()
                min_y = top_left.y()  # Toto je presná spodná čiara menu baru
                max_x = max(min_x, min_x + mdi_area.width() - cur_w)
                max_y = max(min_y, min_y + mdi_area.height() - cur_h)

            # 3. PRIORITA: Ak MDI plocha nie je, dynamicky zmeriame výšku lišty a menu baru
            else:
                top_offset = 0
                for child in parent.findChildren(QWidget):
                    if child.objectName() in ("CustomTitleBar", "menu_bar") or isinstance(child, QMenuBar):
                        if child.isVisible():
                            top_offset += child.height()

                top_left = parent.mapToGlobal(QPoint(0, top_offset))
                min_x = top_left.x()
                min_y = top_left.y()
                max_x = max(min_x, parent.mapToGlobal(QPoint(parent.width(), 0)).x() - cur_w)
                max_y = max(min_y, parent.mapToGlobal(QPoint(0, parent.height())).y() - cur_h)

        # Výpočet a aplikácia bezpečných súradníc
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
        """Vynúti okamžitý zápis pri zatváraní okna."""
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._emit_geometry_changed()


class WindowBoundsManager:
    """
    Centrálna služba správy mantinelov.
    Dostupná pre celé jadro aj pre externé moduly cez ServiceManager.
    """
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
        """
        Nainštaluje strážny filter priamo na okno alebo dialóg.
        """
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
        """Špecializovaná metóda pre MDI pod-okná."""
        return WindowBoundsManager.attach_guard(
            widget=sub_window,
            boundary_mode="mdi",
            on_geometry_changed=on_geometry_changed
        )

    @staticmethod
    def guard_dialog(dialog: QDialog) -> WindowBoundsClampFilter:
        """Špecializovaná metóda pre dialógy a chybové hlásenia."""
        return WindowBoundsManager.attach_guard(
            widget=dialog,
            boundary_mode="parent"
        )