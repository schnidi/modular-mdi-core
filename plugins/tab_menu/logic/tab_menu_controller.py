# Súbor: modules/tab_menu/logic/tab_menu_controller.py

from typing import Optional, Set
from PyQt6.QtCore import QObject, QTimer, pyqtSlot
from PyQt6.QtWidgets import QVBoxLayout, QWidget, QMdiArea

# JEDINÝ POVOLENÝ IMPORT Z JADRA
from core.enum_core import ICoreBridge

from .window_filter_logic import WindowFilterLogic


class TabMenuController(QObject):
    MODULE_NAME = "tab_menu"
    SETTINGS_SECTION = "TabMenuBar"

    def __init__(self, bar_view: QWidget, bridge: ICoreBridge, main_controller=None):
        super().__init__()
        self.bar_view = bar_view
        self.bridge = bridge
        
        # Získavanie služieb jadra beží STRIKTNE len cez ICoreBridge
        self.main_controller = main_controller or self.bridge.get_service("window_manager")
        self.auth_service = self.bridge.get_service("auth_service")

        # Okenná logika teraz prijíma len bridge, cez ktorý si sama vypýta module_manager
        self.filter_logic = WindowFilterLogic(self.bridge)
        self.active_workspace: str = WindowFilterLogic.ALL_WORKSPACE_ID
        self._is_switching_workspace = False

        self._hooked_window_ids: Set[int] = set()

        self.settings = self._load_settings()
        if hasattr(self.bar_view, "set_settings_state"):
            self.bar_view.set_settings_state(self.settings)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.setInterval(60)
        self.refresh_timer.timeout.connect(self.sync_tabs_with_open_windows)

        # Prepojenie signálov z pohľadu
        if hasattr(self.bar_view, "tab_selected"):
            self.bar_view.tab_selected.connect(self.switch_to_workspace)
        if hasattr(self.bar_view, "tab_close_requested"):
            self.bar_view.tab_close_requested.connect(self.close_workspace_windows)
        if hasattr(self.bar_view, "window_toggle_requested"):
            self.bar_view.window_toggle_requested.connect(self.handle_window_dropdown_click)
        if hasattr(self.bar_view, "setting_changed"):
            self.bar_view.setting_changed.connect(self.on_setting_changed)
        if hasattr(self.bar_view, "desktop_action_requested"):
            self.bar_view.desktop_action_requested.connect(self.on_desktop_action)

        if self.auth_service:
            self.auth_service.user_logged_in.connect(self._on_user_auth_changed)
            self.auth_service.user_logged_out.connect(self._on_user_auth_changed)
        
        if self.bridge:
            self.bridge.connect_language_changed(self._on_language_changed)

        self._inject_into_main_window_layout()
        self._hook_window_lifecycle()

        QTimer.singleShot(0, self._apply_saved_visibility)
        QTimer.singleShot(150, self.sync_tabs_with_open_windows)

    def _get_is_open_key(self) -> str:
        if self.auth_service:
            prefix = self.auth_service.get_current_prefix()
            if prefix != self.auth_service.DEFAULT_USER_PREFIX:
                return f"{prefix}_is_open"
        return "is_open"

    def _apply_saved_visibility(self):
        key = self._get_is_open_key()
        is_open_val = self.bridge.load_module_setting(self.MODULE_NAME, self.SETTINGS_SECTION, key, default="True")
        should_be_visible = (str(is_open_val).lower() == "true")
        self.set_visibility(should_be_visible)

    def set_visibility(self, visible: bool):
        self.bar_view.setVisible(visible)
        key = self._get_is_open_key()
        self.bridge.save_module_setting(self.MODULE_NAME, self.SETTINGS_SECTION, key, str(visible))
        self.bridge.save_module_setting(self.MODULE_NAME, self.SETTINGS_SECTION, "is_open", str(visible))

    def toggle_visibility(self):
        new_state = not self.bar_view.isVisible()
        self.set_visibility(new_state)

    def _on_user_auth_changed(self, *args):
        self._apply_saved_visibility()
        self.schedule_refresh()

    def _load_settings(self) -> dict:
        return {
            "show_close_btn": self.bridge.load_module_setting(self.MODULE_NAME, self.SETTINGS_SECTION, "show_close_btn", "True").lower() == "true",
            "isolate_workspace": self.bridge.load_module_setting(self.MODULE_NAME, self.SETTINGS_SECTION, "isolate_workspace", "True").lower() == "true",
            "bring_to_front": self.bridge.load_module_setting(self.MODULE_NAME, self.SETTINGS_SECTION, "bring_to_front", "True").lower() == "true",
            "dropdown_focus_only": self.bridge.load_module_setting(self.MODULE_NAME, self.SETTINGS_SECTION, "dropdown_focus_only", "False").lower() == "true"
        }

    def _save_settings(self):
        for key, val in self.settings.items():
            self.bridge.save_module_setting(self.MODULE_NAME, self.SETTINGS_SECTION, key, str(val))

    @pyqtSlot(str, bool)
    def on_setting_changed(self, key: str, value: bool):
        self.settings[key] = value
        self._save_settings()
        if hasattr(self.bar_view, "set_settings_state"):
            self.bar_view.set_settings_state(self.settings)
        self.sync_tabs_with_open_windows()

    @pyqtSlot(str, str)
    def handle_window_dropdown_click(self, plugin_id: str, window_key: str):
        if not self.main_controller or not hasattr(self.main_controller, "sub_windows"):
            return
        sub_win = self.main_controller.sub_windows.get(window_key)
        if not sub_win or not sub_win.parent():
            return

        focus_only = self.settings.get("dropdown_focus_only", False)

        if focus_only:
            if getattr(sub_win, "_mode", "") == "minimized":
                sub_win.do_restore()
            else:
                sub_win.show()
            sub_win.raise_()
            if hasattr(self.main_controller.view, "mdiArea"):
                self.main_controller.view.mdiArea.setActiveSubWindow(sub_win)
                sub_win.setFocus()
        else:
            is_minimized = getattr(sub_win, "_mode", "") == "minimized"
            if is_minimized:
                sub_win.do_restore()
                sub_win.raise_()
                if hasattr(self.main_controller.view, "mdiArea"):
                    self.main_controller.view.mdiArea.setActiveSubWindow(sub_win)
                    sub_win.setFocus()
            else:
                sub_win.do_minimize()
        self.schedule_refresh()

    @pyqtSlot(str)
    def on_desktop_action(self, action: str):
        if not self.main_controller or not hasattr(self.main_controller, "sub_windows"):
            return
        mdi_area = getattr(self.main_controller.view, "mdiArea", None)

        if action == "minimize_all":
            for sub_w in self.main_controller.sub_windows.values():
                if sub_w and sub_w.parent() and not sub_w.isHidden():
                    sub_w.do_minimize()
        elif action == "restore_all":
            for sub_w in self.main_controller.sub_windows.values():
                if sub_w and sub_w.parent():
                    sub_w.do_restore()
        elif action == "tile" and mdi_area:
            mdi_area.tileSubWindows()
        elif action == "cascade" and mdi_area:
            mdi_area.cascadeSubWindows()
        self.schedule_refresh()

    def _inject_into_main_window_layout(self):
        if not self.main_controller or not hasattr(self.main_controller, "view"):
            self.main_controller = self.bridge.get_service("window_manager")
            if not self.main_controller or not hasattr(self.main_controller, "view"):
                QTimer.singleShot(100, self._inject_into_main_window_layout)
                return

        main_window = self.main_controller.view
        main_layout = main_window.findChild(QVBoxLayout, "main_layout") or main_window.layout()

        if not main_layout:
            return

        mdi_area = main_window.findChild(QMdiArea, "mdiArea")
        if mdi_area:
            index = main_layout.indexOf(mdi_area)
            if index != -1:
                main_layout.insertWidget(index, self.bar_view)
            else:
                main_layout.addWidget(self.bar_view)
        else:
            main_layout.addWidget(self.bar_view)
        self.bar_view.raise_()

    def _hook_window_lifecycle(self):
        if not self.main_controller or not hasattr(self.main_controller, "view"):
            return
        mdi_area = self.main_controller.view.findChild(QMdiArea, "mdiArea")
        if mdi_area:
            mdi_area.subWindowActivated.connect(self._on_sub_window_activated)

    def _hook_window_title_signals(self, sub_win):
        if not sub_win:
            return

        win_id = id(sub_win)
        if win_id not in self._hooked_window_ids:
            self._hooked_window_ids.add(win_id)
            try:
                sub_win.windowTitleChanged.connect(self._on_window_title_changed)
                sub_win.destroyed.connect(lambda: self._hooked_window_ids.discard(win_id))
            except Exception:
                pass

        client_w = getattr(sub_win, "client_widget", None) or (sub_win.widget() if hasattr(sub_win, "widget") else None)
        if client_w:
            client_id = id(client_w)
            if client_id not in self._hooked_window_ids:
                self._hooked_window_ids.add(client_id)
                try:
                    client_w.windowTitleChanged.connect(self._on_window_title_changed)
                    client_w.destroyed.connect(lambda: self._hooked_window_ids.discard(client_id))
                except Exception:
                    pass

    @pyqtSlot(str)
    def _on_window_title_changed(self, new_title: str):
        self.sync_tabs_with_open_windows()

    def schedule_refresh(self):
        self.refresh_timer.start()

    def _get_window_title(self, sub_win, fallback_key: str) -> str:
        if not sub_win:
            return fallback_key
        client_w = getattr(sub_win, "client_widget", None) or (sub_win.widget() if hasattr(sub_win, "widget") else None)
        if client_w and client_w.windowTitle():
            return client_w.windowTitle()
        if sub_win.windowTitle():
            return sub_win.windowTitle()
        return fallback_key

    @pyqtSlot()
    def sync_tabs_with_open_windows(self):
        if not self.main_controller:
            self.main_controller = self.bridge.get_service("window_manager")

        open_windows = getattr(self.main_controller, "sub_windows", {}) if self.main_controller else {}
        grouped = self.filter_logic.group_windows_by_plugin(open_windows)

        tabs_data = []

        # Čítanie prekladu priamo zo slovníka jadra
        all_text = self.bridge.get_text("tab_all_windows", "Všetky okná")
        total_open = sum(len(w_list) for w_list in grouped.values())
        
        all_windows_list = []
        for w_k, s_w in open_windows.items():
            if s_w and s_w.parent() and not s_w.isHidden():
                self._hook_window_title_signals(s_w)
                all_windows_list.append({
                    "key": w_k,
                    "title": self._get_window_title(s_w, w_k),
                    "is_active": getattr(s_w, "_mode", "") != "minimized"
                })

        tabs_data.append({
            "id": WindowFilterLogic.ALL_WORKSPACE_ID,
            "title": all_text,
            "count": total_open,
            "is_closable": False,
            "icon_path": "",
            "windows_list": all_windows_list
        })

        for plugin_id, win_keys in grouped.items():
            first_w_key = win_keys[0]
            first_win_obj = open_windows.get(first_w_key)
            first_title = self._get_window_title(first_win_obj, first_w_key)

            plugin_windows = []
            for w_k in win_keys:
                sub_w = open_windows.get(w_k)
                if sub_w and sub_w.parent():
                    self._hook_window_title_signals(sub_w)
                    plugin_windows.append({
                        "key": w_k,
                        "title": self._get_window_title(sub_w, w_k),
                        "is_active": getattr(sub_w, "_mode", "") != "minimized"
                    })

            identity = self.filter_logic.get_display_identity(plugin_id, first_title)
            
            if len(win_keys) == 1 and first_title:
                display_title = first_title
            else:
                display_title = identity.get("display_name") or first_title or plugin_id

            tabs_data.append({
                "id": plugin_id,
                "title": display_title,
                "count": len(win_keys),
                "is_closable": True,
                "icon_path": identity.get("icon_path", ""),
                "windows_list": plugin_windows
            })

        available_ids = [t["id"] for t in tabs_data]
        if self.active_workspace not in available_ids:
            self.active_workspace = WindowFilterLogic.ALL_WORKSPACE_ID

        if hasattr(self.bar_view, "populate_tabs"):
            self.bar_view.populate_tabs(tabs_data, active_id=self.active_workspace)

    @pyqtSlot(str)
    def switch_to_workspace(self, workspace_id: str):
        if not self.main_controller or not hasattr(self.main_controller, "sub_windows"):
            return

        self._is_switching_workspace = True
        self.active_workspace = workspace_id
        open_windows = self.main_controller.sub_windows

        to_show, to_minimize = self.filter_logic.partition_windows(workspace_id, open_windows)

        should_isolate = self.settings.get("isolate_workspace", True)
        should_bring_front = self.settings.get("bring_to_front", True)

        try:
            if should_isolate:
                for w_key in to_minimize:
                    sub_win = open_windows.get(w_key)
                    if sub_win and sub_win.parent() and not sub_win.isHidden():
                        if getattr(sub_win, "_mode", "") != "minimized":
                            sub_win.do_minimize()

            last_sub = None
            for w_key in to_show:
                sub_win = open_windows.get(w_key)
                if sub_win and sub_win.parent():
                    if should_bring_front:
                        if getattr(sub_win, "_mode", "") == "minimized":
                            sub_win.do_restore()
                        else:
                            sub_win.show()
                        sub_win.raise_()
                    last_sub = sub_win

            if last_sub and should_bring_front and hasattr(self.main_controller.view, "mdiArea"):
                self.main_controller.view.mdiArea.setActiveSubWindow(last_sub)
                last_sub.setFocus()
        finally:
            self._is_switching_workspace = False

        if hasattr(self.bar_view, "set_active_tab"):
            self.bar_view.set_active_tab(self.active_workspace)

    @pyqtSlot(str)
    def close_workspace_windows(self, workspace_id: str):
        if not self.main_controller or not hasattr(self.main_controller, "sub_windows"):
            return

        open_windows = dict(self.main_controller.sub_windows)
        for w_key, sub_win in open_windows.items():
            plugin_id = self.filter_logic.get_plugin_id_for_window(w_key, sub_win)
            if plugin_id == workspace_id:
                if sub_win and sub_win.parent():
                    sub_win.close()

        self.active_workspace = WindowFilterLogic.ALL_WORKSPACE_ID
        self.schedule_refresh()

    def _on_sub_window_activated(self, sub_win):
        if self._is_switching_workspace:
            return

        if sub_win and hasattr(self.main_controller, "sub_windows"):
            self._hook_window_title_signals(sub_win)
            for w_key, win_obj in self.main_controller.sub_windows.items():
                if win_obj == sub_win:
                    plugin_id = self.filter_logic.get_plugin_id_for_window(w_key, sub_win)
                    if self.active_workspace != WindowFilterLogic.ALL_WORKSPACE_ID:
                        self.active_workspace = plugin_id
                    if hasattr(self.bar_view, "set_active_tab"):
                        self.bar_view.set_active_tab(self.active_workspace)
                    break
            try:
                sub_win.destroyed.connect(self.schedule_refresh)
            except Exception:
                pass
        self.schedule_refresh()

    def _on_language_changed(self, lang_code=None):
        if hasattr(self.filter_logic, "bridge"):
            self.filter_logic.bridge = self.bridge
        self.filter_logic.refresh_module_registry()
        self.sync_tabs_with_open_windows()