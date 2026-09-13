# Súbor: modules/control_panel/logic/control_panel_controller.py

import json
import importlib
from pathlib import Path
from functools import partial

from PyQt6.QtCore import Qt, QObject, QMimeData, QTimer, QPoint
from PyQt6.QtGui import QDrag

# --- OPRAVENÉ IMPORTY PRE NOVÉ JADRO ---
from core.logic.services.auth_service import AuthService
from core.logic.services.config_manager import ConfigManager
from core.logic.module_manager import ModuleManager
from core.logic.plugin.service_manager import ServiceManager
from core._path import Paths

from .. import _paths
from .flow_layout import FlowLayout
from ..windows.icon_button_widget import IconButtonWidget


class ControlPanelController(QObject):
    DRAG_DELAY_MS = 500
    DRAG_DISTANCE_PX = 5

    def __init__(self, view, service_manager=None, main_controller=None):
        super().__init__()
        self.view = view
        self.service_manager = service_manager or ServiceManager.get_instance()
        self.main_controller = main_controller
        
        self.config_manager = ConfigManager(_paths.PANEL_LAYOUT_CONFIG_FILE)
        self.icon_buttons = {}
        
        self.drag_timer = QTimer(self)
        self.drag_timer.setSingleShot(True)
        self.drag_timer.setInterval(self.DRAG_DELAY_MS)
        self.drag_timer.timeout.connect(self._start_drag)
        
        self.widget_to_drag = None
        self.drag_start_position = None

        # Dynamický ModuleManager bez hardcodovanej cesty
        self.module_manager = ModuleManager()
        
        self._setup_ui()
        self.populate_icons()
        self._apply_permissions()

    def _setup_ui(self):
        flow_layout = FlowLayout()
        self.view.iconContainerWidget.setLayout(flow_layout)
        self.view.iconContainerWidget.setAcceptDrops(True)

    def populate_icons(self):
        layout = self.view.iconContainerWidget.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.icon_buttons.clear()

        active_modules_info = self.module_manager.get_active_modules_info()
        saved_order_str = self.config_manager.get_value("Layout", "order", default="[]")
        try:
            saved_order = json.loads(saved_order_str)
        except Exception:
            saved_order = []

        panel_entries = {}
        for module_info in active_modules_info:
            if "control_panel_entry" in module_info and "window_key" in module_info:
                panel_entries[module_info["window_key"]] = module_info

        sorted_keys = [k for k in saved_order if k in panel_entries]
        sorted_keys.extend([k for k in panel_entries if k not in sorted_keys])

        for window_key in sorted_keys:
            module_info = panel_entries[window_key]
            entry_data = module_info["control_panel_entry"]
            module_name = module_info.get("module_name", window_key)
            display_name = entry_data.get("display_name", module_name)
            icon_rel_path = entry_data.get("icon_path")
            
            if not icon_rel_path:
                continue

            module_config = self.module_manager.module_config
            module_path_str = module_config.get_module_path(module_name)
            if not module_path_str:
                continue

            module_path = Path(module_path_str)
            if not module_path.is_absolute():
                module_path = Path(Paths.get_root()) / module_path

            full_icon_path = module_path / icon_rel_path
            if not full_icon_path.exists():
                continue

            icon_button = IconButtonWidget(str(full_icon_path), display_name)
            icon_button.clicked.connect(partial(self._open_module_window, window_key, module_info))
            icon_button.setProperty("window_key", window_key)
            
            self.icon_buttons[window_key] = icon_button
            self.view.iconContainerWidget.layout().addWidget(icon_button)
            icon_button.hide()

    def _apply_permissions(self):
        auth_service = AuthService.get_instance()
        active_modules_info = self.module_manager.get_active_modules_info()
        modules_by_key = {info["window_key"]: info for info in active_modules_info if "window_key" in info}

        for window_key, icon_button in self.icon_buttons.items():
            module_info = modules_by_key.get(window_key)
            if module_info:
                entry_data = module_info.get("control_panel_entry", {})
                required_perm = entry_data.get("required_permission")
                if not required_perm or auth_service.has_permission(required_perm):
                    icon_button.show()

        if auth_service.has_permission("admin.system_config"):
            self.view.iconContainerWidget.installEventFilter(self)

    def _start_drag(self):
        if not self.widget_to_drag:
            return
        self.drag_timer.stop()
        drag = QDrag(self.view)
        mime_data = QMimeData()
        window_key = self.widget_to_drag.property("window_key")
        mime_data.setText(window_key)
        drag.setMimeData(mime_data)
        pixmap = self.widget_to_drag.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self.widget_to_drag.mapFromGlobal(self.view.cursor().pos()))
        drag.exec()
        self.widget_to_drag = None
        self.drag_start_position = None

    def eventFilter(self, source, event):
        if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            child = source.childAt(event.pos())
            while child is not None and not isinstance(child, IconButtonWidget):
                child = child.parent()
            if isinstance(child, IconButtonWidget):
                self.widget_to_drag = child
                self.drag_start_position = event.pos()
                self.drag_timer.start()
            return False

        if event.type() == event.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            self.drag_timer.stop()
            self.widget_to_drag = None
            self.drag_start_position = None
            return False

        if event.type() == event.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
            if self.drag_start_position:
                distance = (event.pos() - self.drag_start_position).manhattanLength()
                if distance >= self.DRAG_DISTANCE_PX:
                    self._start_drag()
                    return True

        if event.type() == event.Type.DragEnter:
            if event.mimeData().hasText():
                event.acceptProposedAction()
            return True

        if event.type() == event.Type.Drop:
            dragged_key = event.mimeData().text()
            dragged_widget = self.icon_buttons.get(dragged_key)

            if dragged_widget:
                layout = self.view.iconContainerWidget.layout()
                pos = event.position().toPoint()
                
                dropped_on = source.childAt(pos)
                while dropped_on is not None and not isinstance(dropped_on, IconButtonWidget):
                    dropped_on = dropped_on.parent()

                if isinstance(dropped_on, IconButtonWidget) and dropped_on is not dragged_widget:
                    index = layout.indexOf(dropped_on)
                    local_pos = dropped_on.mapFrom(source, pos)
                    if local_pos.x() > (dropped_on.width() / 2):
                        index += 1
                    layout.insertWidget(index, dragged_widget)
                else:
                    layout.addWidget(dragged_widget)

                self._save_layout_order()
                event.acceptProposedAction()
            return True

        return super().eventFilter(source, event)

    def _save_layout_order(self):
        layout = self.view.iconContainerWidget.layout()
        order = [item.widget().property("window_key") for i in range(layout.count()) if (item := layout.itemAt(i)) and isinstance(item.widget(), IconButtonWidget)]
        self.config_manager.set_value("Layout", "order", json.dumps(order))
        self.config_manager.save()

    def _open_module_window(self, window_key: str, module_info: dict):
        """
        Univerzálne otvorenie okna kompatibilné s novým kontrolérom aj priamym načítaním.
        """
        if not window_key:
            return

        factory_path = module_info.get("widget_factory_path")
        display_name = module_info.get("control_panel_entry", {}).get("display_name", window_key)

        if not factory_path:
            print(f"[ControlPanel] Modul '{window_key}' nemá definovaný 'widget_factory_path'.")
            return

        try:
            mod_path, func_name = factory_path.rsplit('.', 1)
            mod = importlib.import_module(mod_path)
            factory_func = getattr(mod, func_name)

            # 1. Pokus: ak máme main_controller
            if self.main_controller and hasattr(self.main_controller, 'open_sub_window'):
                self.main_controller.open_sub_window(
                    window_key=window_key,
                    widget_factory_func=factory_func,
                    window_title=display_name
                )
                return

            # 2. Pokus: nájdenie MainWindow cez parent widgety
            parent = self.view.parent()
            while parent:
                if hasattr(parent, 'controller') and hasattr(parent.controller, 'open_sub_window'):
                    parent.controller.open_sub_window(
                        window_key=window_key,
                        widget_factory_func=factory_func,
                        window_title=display_name
                    )
                    return
                parent = parent.parent()

            print(f"[ControlPanel] Nepodarilo sa nájsť kontrolér pre otvorenie '{window_key}'.")

        except Exception as e:
            print(f"[ControlPanel] Chyba pri otváraní okna '{window_key}': {e}")