# Súbor: core/logic/main_window_security.py

import inspect
import importlib
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction

from core._path import Paths
from core.logic.core_bridge import CoreBridge
from core.logic.services.config_manager import ConfigManager
from core.logic.module_manager import ModuleManager
from core.logic.plugin.module_setup_controller import ModuleSetupController
from core.logic.services.auth_service import AuthService
from core.logic.plugin.service_manager import ServiceManager
from core.logic.language_manager import LanguageManager
from core.enum_core import ConfigKey, CoreServiceType, ModuleInfoKey
from core.logic.skin_manager import SkinManager


class MainWindowSecurity(QObject):
    def __init__(self, view, window_controller, startup_data=None):
        super().__init__()
        self.view = view
        self.window_controller = window_controller
        self.startup_data = startup_data or {}

        self.auth_service = AuthService.get_instance()
        self.service_manager = ServiceManager.get_instance()
        self.module_manager = ModuleManager()
        self.config = ConfigManager(Paths.get_window_setup_ini())

        self.current_config_prefix = self.auth_service.get_current_prefix()
        self.active_modules_info = []

        self.dynamic_menu_items = []
        self.dynamic_menus = []
        self._translated_modules = set()

        self.auth_service.user_logged_in.connect(self.handle_user_login)
        self.auth_service.user_logged_out.connect(self.handle_user_logout)
        ModuleSetupController.signals.modules_config_changed.connect(self.rebuild_menu)
        LanguageManager.connect_language_changed(self.handle_language_change)

        # OPRAVA 1: Najprv načítame zoznam modulov (rebuild_menu), až potom registrujeme služby!
        self.rebuild_menu()
        self._register_module_services()

    def handle_user_login(self, user_info: dict):
        self.close_all_sub_windows_safely()
        new_prefix = self.auth_service.get_current_prefix()
        self.current_config_prefix = new_prefix
        
        # OPRAVA 1b: Aj pri prihlásení najprv načítame zoznam!
        self.rebuild_menu()
        self._register_module_services()
        
        SkinManager.apply_saved_skin()
        QTimer.singleShot(100, self._restore_user_sub_windows)

    def handle_user_logout(self):
        self.close_all_sub_windows_safely()
        self.current_config_prefix = self.auth_service.DEFAULT_USER_PREFIX
        self.rebuild_menu()
        SkinManager.apply_saved_skin()

    def close_all_sub_windows_safely(self):
        if hasattr(self.view, 'mdiArea') and self.view.mdiArea:
            self.view.mdiArea.closeAllSubWindows()

        if hasattr(self.window_controller, 'sub_windows'):
            self.window_controller.sub_windows.clear()

        if hasattr(self.window_controller, 'update_main_window_minimum_size'):
            self.window_controller.update_main_window_minimum_size()

    def rebuild_menu(self):
        """Zostaví menu nanovo s plnou podporou a bez akejkoľvek duplicity."""
        is_logged = self.auth_service.is_logged_in()
        
        # TU SA NAPĹŇA self.active_modules_info!
        self.active_modules_info = self.module_manager.get_active_modules_info()

        # 0. Preklady aktívnych modulov musia byť v slovníku PRED stavbou menu
        self._ensure_module_translations()

        # 1. Vyčistenie starých dynamických položiek
        for item in self.dynamic_menu_items:
            for action in self.view.menu_bar.actions():
                menu = action.menu()
                if menu and item in menu.actions():
                    menu.removeAction(item)
            item.deleteLater()
        self.dynamic_menu_items.clear()

        # 2. Vyčistenie starých dynamických kategórií
        for menu in self.dynamic_menus:
            self.view.menu_bar.removeAction(menu.menuAction())
            menu.deleteLater()
        self.dynamic_menus.clear()

        # 3. Zmapovanie pevných menu priamo podľa ich objektov a názvov
        existing_menus = {}

        if hasattr(self.view, 'menu_file') and self.view.menu_file:
            existing_menus["program"] = self.view.menu_file
            existing_menus["súbor"] = self.view.menu_file
            existing_menus["subor"] = self.view.menu_file
            existing_menus["file"] = self.view.menu_file

        if hasattr(self.view, 'menu_settings') and self.view.menu_settings:
            existing_menus["nastavenie"] = self.view.menu_settings
            existing_menus["nastavenia"] = self.view.menu_settings
            existing_menus["settings"] = self.view.menu_settings

        if hasattr(self.view, 'menu_window') and self.view.menu_window:
            existing_menus["okno"] = self.view.menu_window
            existing_menus["window"] = self.view.menu_window

        if hasattr(self.view, 'menu_help') and self.view.menu_help:
            existing_menus["pomocník"] = self.view.menu_help
            existing_menus["pomocnik"] = self.view.menu_help
            existing_menus["help"] = self.view.menu_help

        for action in self.view.menu_bar.actions():
            menu = action.menu()
            if menu and menu not in self.dynamic_menus:
                raw_title = menu.title() if menu.title() else action.text()
                clean_title = raw_title.replace("&", "").strip().lower()
                if clean_title and clean_title not in existing_menus:
                    existing_menus[clean_title] = menu

        # 4. Vloženie položiek modulov do správnych menu
        for mod_info in self.active_modules_info:
            menu_struct = mod_info.get("menu_structure", {})

            for category_name, items in menu_struct.items():
                cat_clean = category_name.replace("&", "").strip().lower()
                target_menu = existing_menus.get(cat_clean)

                if not target_menu:
                    display_name = LanguageManager.get(category_name, category_name)
                    target_menu = QMenu(display_name, self.view)
                    if hasattr(self.view, 'menu_window') and self.view.menu_window:
                        self.view.menu_bar.insertMenu(self.view.menu_window.menuAction(), target_menu)
                    else:
                        self.view.menu_bar.addMenu(target_menu)
                    existing_menus[cat_clean] = target_menu
                    self.dynamic_menus.append(target_menu)

                self._populate_menu_items(target_menu, items, mod_info, is_logged)

    def _ensure_module_translations(self):
        for mod_info in self.active_modules_info:
            name = mod_info.get("name") or mod_info.get("module_name")
            if not name or name in self._translated_modules:
                continue
            if not mod_info.get("paths_module_path"):
                continue
            if LanguageManager.register_module_translations(mod_info):
                self._translated_modules.add(name)

    def _populate_menu_items(self, target_menu: QMenu, items: list, mod_info: dict, is_logged: bool):
        for item in items:
            if item.get("id") == "---SEPARATOR---" or item.get("text") == "---":
                sep = target_menu.addSeparator()
                self.dynamic_menu_items.append(sep)
                continue

            if item.get("requires_login", False) and not is_logged:
                continue
            if item.get("requires_logged_out", False) and is_logged:
                continue

            req_perm = item.get("required_permission")
            if req_perm and not self.auth_service.has_permission(req_perm):
                continue

            raw_text = item.get("text", "Neznáma akcia")
            item_id = item.get("id")
            action_text = LanguageManager.get(item_id, LanguageManager.get(raw_text, raw_text))

            if "submenu" in item and isinstance(item["submenu"], list):
                sub_menu = target_menu.addMenu(action_text)
                self.dynamic_menus.append(sub_menu)
                self._populate_menu_items(sub_menu, item["submenu"], mod_info, is_logged)
                continue

            action = QAction(action_text, self.view)
            handler_path = item.get("handler_path")
            w_key = item.get("window_key") or mod_info.get("window_key")
            factory_path = item.get(ModuleInfoKey.WIDGET_FACTORY_PATH) or mod_info.get(ModuleInfoKey.WIDGET_FACTORY_PATH)

            if handler_path:
                action.triggered.connect(self._create_handler(handler_path))
            elif factory_path and w_key:
                custom_mod_info = dict(mod_info)
                custom_mod_info["window_key"] = w_key
                custom_mod_info["widget_factory_path"] = factory_path
                action.triggered.connect(self._create_window_opener(custom_mod_info, action_text))

            target_menu.addAction(action)
            self.dynamic_menu_items.append(action)

    def _create_handler(self, handler_path: str):
        def trigger():
            try:
                mod_path, func_name = handler_path.rsplit('.', 1)
                module = importlib.import_module(mod_path)
                func = getattr(module, func_name)

                sig = inspect.signature(func)
                bridge = CoreBridge.get_instance()
                if len(sig.parameters) > 0:
                    func(bridge)
                else:
                    func()
            except Exception as e:
                print(f"[Security] Chyba akcie '{handler_path}': {e}")
        return trigger

    def _create_window_opener(self, mod_info: dict, title: str):
        w_key = mod_info.get("window_key")
        factory_path = mod_info.get("widget_factory_path")
        mod_name = mod_info.get("name") or mod_info.get("module_name")

        def trigger():
            try:
                mod_path, func_name = factory_path.rsplit('.', 1)
                module = importlib.import_module(mod_path)
                factory_func = getattr(module, func_name)

                bridge = CoreBridge.get_instance()
                sig = inspect.signature(factory_func)
                if len(sig.parameters) > 0:
                    widget_factory = lambda: factory_func(bridge=bridge)
                else:
                    widget_factory = factory_func

                self.window_controller.open_sub_window(
                    window_key=w_key,
                    widget_factory_func=widget_factory,
                    window_title=title,
                    module_name=mod_name
                )
            except Exception as e:
                print(f"[Security] Chyba otvorenia okna '{w_key}': {e}")
        return trigger

    def _register_module_services(self):
        for module_info in self.active_modules_info:
            if "provided_services" in module_info:
                for service in module_info["provided_services"]:
                    service_type = service.get("service_type")
                    provider_info = service.get("provider_info")
                    if not service_type or not provider_info:
                        continue

                    # OPRAVA 2: Zvládne to čistý text "core_service" aj enum hodnotu!
                    if service_type == CoreServiceType.CORE_SERVICE or service_type == "core_service":
                        service_name = provider_info.get("service_name")
                        instance_path = provider_info.get("service_instance_path")
                        if service_name and instance_path and not self.service_manager.has_service(service_name):
                            try:
                                mod_path, cls_name, fn_name = instance_path.rsplit('.', 2)
                                mod = importlib.import_module(mod_path)
                                s_cls = getattr(mod, cls_name)
                                getter = getattr(s_cls, fn_name)
                                self.service_manager.register_service(service_name, getter())
                            except Exception as e:
                                print(f"[Security] Chyba registrácie služby '{service_name}': {e}")

    def _restore_user_sub_windows(self):
        prefix = self.current_config_prefix
        for mod_info in self.active_modules_info:
            w_key = mod_info.get("window_key")
            if not w_key:
                continue

            req_perm = mod_info.get("control_panel_entry", {}).get("required_permission")
            if req_perm and not self.auth_service.has_permission(req_perm):
                continue

            is_open_key = f"{prefix}_{ConfigKey.IS_OPEN}" if prefix != self.auth_service.DEFAULT_USER_PREFIX else ConfigKey.IS_OPEN
            is_open = self.config.get_value(w_key, is_open_key)
            if is_open == "True":
                opener = self._create_window_opener(mod_info, mod_info.get("module_name", w_key))
                opener()

    def handle_language_change(self, lang_code=None):
        self.rebuild_menu()