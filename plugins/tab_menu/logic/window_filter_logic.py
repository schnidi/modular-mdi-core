# Súbor: modules/tab_menu/logic/window_filter_logic.py

from typing import Dict, List, Set, Tuple

# JEDINÝ POVOLENÝ IMPORT Z JADRA
from core.enum_core import ICoreBridge


class WindowFilterLogic:
    """
    Spája všetky okná jedného modulu/pluginu do jedného Workspace.
    Názov záložky prekladá podľa 'id' výlučne cez injektovaný ICoreBridge.
    """
    ALL_WORKSPACE_ID = "__ALL__"

    def __init__(self, bridge: ICoreBridge):
        self.bridge = bridge
        self.module_manager = self.bridge.get_service("module_manager")
        self._modules_info_cache: Dict[str, dict] = {}
        self.refresh_module_registry()

    def _extract_title_recursive(self, items: list) -> str:
        if not isinstance(items, list):
            return ""

        for item in items:
            if not isinstance(item, dict):
                continue

            if "submenu" in item and isinstance(item["submenu"], list):
                res = self._extract_title_recursive(item["submenu"])
                if res:
                    return res

            action_id = item.get("id")
            fallback_text = item.get("text", "").strip().rstrip(".").rstrip()

            # Preklad realizovaný výlučne cez jadro
            if action_id and self.bridge:
                translated = self.bridge.get_text(action_id, default=None)
                if translated and translated != action_id:
                    return translated.rstrip(".").rstrip()

            if fallback_text:
                return fallback_text

        return ""

    def refresh_module_registry(self):
        self._modules_info_cache.clear()
        
        if not self.module_manager:
            self.module_manager = self.bridge.get_service("module_manager")
            if not self.module_manager:
                return

        active_modules = self.module_manager.get_active_modules_info()

        for mod_info in active_modules:
            mod_name = mod_info.get("name") or mod_info.get("module_name", "")
            if not mod_name:
                continue

            display_name = ""
            menu_struct = mod_info.get("menu_structure", {})

            if isinstance(menu_struct, dict):
                for category, items in menu_struct.items():
                    display_name = self._extract_title_recursive(items)
                    if display_name:
                        break

            if not display_name:
                display_name = mod_info.get("name") or mod_name.replace("_", " ").title()

            cp_entry = mod_info.get("control_panel_entry", {})
            icon_rel_path = cp_entry.get("icon_path", "")

            self._modules_info_cache[mod_name] = {
                "module_name": mod_name,
                "display_name": display_name,
                "icon_path": icon_rel_path,
                "module_info": mod_info
            }

        setup_title = self.bridge.get_text("ModuleSetup", "Správa Modulov") if self.bridge else "Správa Modulov"
        test_title = self.bridge.get_text("test_window", "Testovací Modul") if self.bridge else "Testovací Modul"

        self._modules_info_cache["ModuleSetup"] = {
            "module_name": "ModuleSetup",
            "display_name": setup_title,
            "icon_path": ""
        }
        self._modules_info_cache["test_window"] = {
            "module_name": "test_window",
            "display_name": test_title,
            "icon_path": ""
        }

    def get_plugin_id_for_window(self, window_key: str, sub_win) -> str:
        if not sub_win:
            return window_key

        client_w = getattr(sub_win, "client_widget", None)
        if client_w is None and hasattr(sub_win, "widget"):
            client_w = sub_win.widget()

        if client_w is not None:
            mod_path = client_w.__class__.__module__ 
            parts = mod_path.split(".")

            cls_name = client_w.__class__.__name__
            if "ModuleSetup" in cls_name or window_key == "ModuleSetup":
                return "ModuleSetup"
            if "TestWindow" in cls_name or "test_window" in window_key:
                return "test_window"

            for mod_name in self._modules_info_cache:
                if mod_name in parts:
                    return mod_name

            if parts[0] == "modules" and len(parts) > 1:
                internal_subfolders = {"windows", "logic", "ui", "views", "controllers", "widgets"}
                for idx, part in enumerate(parts):
                    if part in internal_subfolders and idx > 1:
                        return parts[idx - 1]

                if len(parts) >= 3:
                    return parts[-2]
                return parts[1]

        for mod_name, info in self._modules_info_cache.items():
            mod_info = info.get("module_info", {})
            if mod_info.get("window_key") == window_key:
                return mod_name

        return window_key

    def get_display_identity(self, plugin_id: str, sample_window_title: str = "") -> dict:
        if plugin_id not in self._modules_info_cache:
            self.refresh_module_registry()

        if plugin_id in self._modules_info_cache:
            return self._modules_info_cache[plugin_id]

        return {
            "module_name": plugin_id,
            "display_name": plugin_id.replace("_", " ").title(),
            "icon_path": ""
        }

    def group_windows_by_plugin(self, open_sub_windows: dict) -> Dict[str, List[str]]:
        grouped: Dict[str, List[str]] = {}
        for w_key, sub_win in open_sub_windows.items():
            if not sub_win or not sub_win.parent():
                continue
            if sub_win.isHidden():
                continue
            plugin_id = self.get_plugin_id_for_window(w_key, sub_win)
            if plugin_id not in grouped:
                grouped[plugin_id] = []
            grouped[plugin_id].append(w_key)
        return grouped

    def partition_windows(self, target_workspace_id: str, open_sub_windows: dict) -> Tuple[Set[str], Set[str]]:
        to_show = set()
        to_minimize = set()

        if target_workspace_id == self.ALL_WORKSPACE_ID:
            for w_key, sub_win in open_sub_windows.items():
                if sub_win and sub_win.parent() and not sub_win.isHidden():
                    to_show.add(w_key)
            return to_show, to_minimize

        for w_key, sub_win in open_sub_windows.items():
            if not sub_win or not sub_win.parent():
                continue
            plugin_id = self.get_plugin_id_for_window(w_key, sub_win)
            if plugin_id == target_workspace_id:
                to_show.add(w_key)
            else:
                to_minimize.add(w_key)

        return to_show, to_minimize