"""
Súbor: core/logic/services/window_bounds_manager.py
Centrálna služba a EventFilter pre stráženie mantinelov všetkých typov okien.
Zabezpečuje, že MDI pod-okná, chybové dialógy ani modálne okná nepretečú cez okraje.
"""

from typing import Callable, Optional
from PyQt6.QtCore import QObject, QEvent, QTimer, QRect, Qt
from PyQt6.QtWidgets import QWidget, QMdiSubWindow, QMdiArea, QDialog, QApplication
from PyQt6.QtGui import QGuiApplication


class WindowBoundsClampFilter(QObject):
    """
    Univerzálny EventFilter na odchytávanie udalostí presunu (Move) a zmeny veľkosti (Resize).
    V reálnom čase vracia okná späť do povolených mantinelov.
    """

    def __init__(
        self,
        target_widget: QWidget,
        parent: Optional[QObject] = None,
        boundary_mode: str = "auto",
        on_geometry_changed: Optional[Callable[[QRect], None]] = None,
        debounce_ms: int = 300
    ):
        """
        :param target_widget: Okno, ktoré má byť strážené.
        :param boundary_mode: "auto" | "mdi" | "parent" | "screen"
        :param on_geometry_changed: Voliteľný callback volaný po ustálení pohybu okna.
        :param debounce_ms: Oneskorenie pred vyvolaním uloženia polohy (debounce).
        """
        super().__init__(parent or target_widget)
        self.target_widget = target_widget
        self.boundary_mode = boundary_mode
        self.on_geometry_changed = on_geometry_changed

        self._is_adjusting = False  # Zámok proti rekurzívnemu zacykleniu udalostí
        self._pending_geometry: Optional[QRect] = None

        # Časovač pre bezpečný a odložený zápis geometrie (nezapisuje pri každom pixeli)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(debounce_ms)
        self._save_timer.timeout.connect(self._emit_geometry_changed)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if obj == self.target_widget and not self._is_adjusting:
            if event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
                self._clamp_bounds(self.target_widget)

        return super().eventFilter(obj, event)

    def _get_boundary_rect(self, widget: QWidget) -> Optional[QRect]:
        """Vypočíta maximálny povolený obdĺžnik podľa zvoleného režimu a typu okna."""
        mode = self.boundary_mode

        # 1. MDI REŽIM (Pre MDI pod-okná)
        if mode in ("auto", "mdi"):
            area = None
            if hasattr(widget, "mdiArea") and callable(widget.mdiArea):
                area = widget.mdiArea()
            elif isinstance(widget.parentWidget(), QMdiArea):
                area = widget.parentWidget()

            if area is not None:
                viewport = area.viewport()
                vw = viewport.width()
                vh = viewport.height()
                if vw > 10 and vh > 10:
                    return QRect(0, 0, vw, vh)
            elif mode == "mdi":
                return None

        # 2. RODIČOVSKÉ OKNO (Pre modálne okná, dialógy a chybové hlášky)
        if mode in ("auto", "parent"):
            parent_widget = widget.parentWidget()
            if parent_widget is not None and not isinstance(parent_widget, QMdiArea):
                pw = parent_widget.width()
                ph = parent_widget.height()
                if pw > 50 and ph > 50:
                    return QRect(0, 0, pw, ph)
            elif mode == "parent":
                return None

        # 3. OBRAZOVKA / MONITOR (Záložný mantinel, aby okno neušlo mimo monitor)
        screen = None
        if widget.windowHandle() and widget.windowHandle().screen():
            screen = widget.windowHandle().screen()
        else:
            screen = QGuiApplication.primaryScreen()

        if screen:
            return screen.availableGeometry()

        return None

    def _clamp_bounds(self, widget: QWidget):
        """Vykoná matematický prepočet mantinelov a vráti okno dnu."""
        bound = self._get_boundary_rect(widget)
        if not bound or bound.width() <= 0 or bound.height() <= 0:
            return

        geo = widget.geometry()
        cur_x = geo.x()
        cur_y = geo.y()
        cur_w = geo.width()
        cur_h = geo.height()

        # Obmedzenie veľkosti (okno nesmie byť väčšie ako samotná plocha)
        new_w = min(cur_w, bound.width())
        new_h = min(cur_h, bound.height())

        # Obmedzenie pozície X a Y v mantineloch (0 až max_šírka - šírka_okna)
        min_x = bound.left()
        max_x = max(min_x, bound.right() - new_w + 1)
        new_x = max(min_x, min(cur_x, max_x))

        min_y = bound.top()
        max_y = max(min_y, bound.bottom() - new_h + 1)
        new_y = max(min_y, min(cur_y, max_y))

        # Ak došlo k prekročeniu mantinelu, bezpečne korigujeme geometriu
        if (new_x, new_y, new_w, new_h) != (cur_x, cur_y, cur_w, cur_h):
            self._is_adjusting = True
            try:
                widget.setGeometry(new_x, new_y, new_w, new_h)
            finally:
                self._is_adjusting = False

        # Ak máme nastavený callback na ukladanie, spustíme debounce časovač
        if self.on_geometry_changed:
            self._pending_geometry = widget.geometry()
            self._save_timer.start()

    def _emit_geometry_changed(self):
        """Vyvolá notifikáciu o ustálenej zmene polohy."""
        if self._pending_geometry and self.on_geometry_changed:
            self.on_geometry_changed(self._pending_geometry)

    def flush(self):
        """Okamžite uloží stav pred ukončením okna alebo aplikácie."""
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
        
        :param widget: Cieľový QWidget / QMdiSubWindow / QDialog.
        :param boundary_mode: "auto" (zistí samo) | "mdi" | "parent" | "screen"
        :param on_geometry_changed: Voliteľný callback pri zmene rozmerov.
        :return: Vytvorený filter.
        """
        clamp_filter = WindowBoundsClampFilter(
            target_widget=widget,
            boundary_mode=boundary_mode,
            on_geometry_changed=on_geometry_changed
        )
        widget.installEventFilter(clamp_filter)

        # Prepojenie bezpečného vyprázdnenia pred zatvorením aplikácie
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(clamp_filter.flush)

        return clamp_filter

    @staticmethod
    def guard_mdi_sub_window(
        sub_window: QMdiSubWindow,
        on_geometry_changed: Optional[Callable[[QRect], None]] = None
    ) -> WindowBoundsClampFilter:
        """Špecializovaná metóda pre bezpečné stráženie MDI pod-okna."""
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