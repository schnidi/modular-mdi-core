"""
Súbor: core/logic/main_window_security.py
Bezpečnostný kontrolér pre správu používateľských relácií,
ochranu dát na ploche, oprávnení a dynamických menu bez duplikácie.
"""

import importlib
from pathlib import Path
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction

from core._path import Paths
from core.logic.services.config_manager import ConfigManager
from core.logic.module_manager import ModuleManager
from core.logic.plugin.module_setup_controller import ModuleSetupController
from core.logic.services.auth_service import AuthService
from core.logic.plugin.service_manager import ServiceManager
from core.logic.language_manager import LanguageManager
from core.enum_core import ConfigKey, WindowKey, CoreServiceType
from core.logic.skin_manager import SkinManager


class MainWindowSecurity(QObject):
    """
    Bezpečnostný manažér hlavného okna.
    Zabezpečuje dynamickú a čistú stavbu menu bez duplicity,
    okamžite zatvára okná pri odhlásení a filtruje položky podľa práv.
    """

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
        
        # Evidencia dynamických prvkov na čisté odstránenie
        self.dynamic_menu_items = []  # Jednotlivé akcie (QAction) a oddeľovače
        self.dynamic_menus = []       # Celé dynamicky vytvorené horné kategórie (QMenu)

        # Prepojenie bezpečnostných signálov
        self.auth_service.user_logged_in.connect(self.handle_user_login)
        self.auth_service.user_logged_out.connect(self.handle_user_logout)
        ModuleSetupController.signals.modules_config_changed.connect(self.rebuild_menu)
        LanguageManager.connect_language_changed(self.handle_language_change)

        # 1. Registrácia služieb modulov
        self._register_module_services()

        # 2. Úvodná stavba menu podľa aktuálnych práv
        self.rebuild_menu()

    # =========================================================================
    # BEZPEČNOSŤ: ŽIVOTNÝ CYKLUS RELÁCIE (LOGIN / LOGOUT)
    # =========================================================================

    def handle_user_login(self, user_info: dict):
        """Vyčistí starú plochu, prepne prefix používateľa a obnoví jeho práva."""
        print(f"[Security] Prihlásený používateľ. Preberám kontrolu nad plochou...")
        
        # 1. BEZPEČNOSŤ: Okamžité zatvorenie všetkých predchádzajúcich okien
        self.close_all_sub_windows_safely()

        # 2. Prepnutie profilu
        new_prefix = self.auth_service.get_current_prefix()
        self.current_config_prefix = new_prefix

        # 3. Načítanie modulov a obnova menu podľa nových práv
        self._register_module_services()
        self.rebuild_menu()
        SkinManager.apply_saved_skin()

        # 4. Obnova okien patriacich výhradne tomuto používateľovi
        QTimer.singleShot(100, self._restore_user_sub_windows)

    def handle_user_logout(self):
        """KRITICKÁ BEZPEČNOSŤ: Okamžite zničí všetky okná s dátami a zamkne menu."""
        print(f"[Security] Odhlásenie: Uzamykám a bezpečne ničím všetky otvorené okná...")
        
        # 1. Zničenie všetkých okien z MDI plochy (žiadny únik citlivých údajov)
        self.close_all_sub_windows_safely()

        # 2. Návrat na predvolený stav
        self.current_config_prefix = self.auth_service.DEFAULT_USER_PREFIX
        
        # 3. Prestavba menu (odstránenie akcií vyžadujúcich prihlásenie)
        self.rebuild_menu()
        SkinManager.apply_saved_skin()

    def close_all_sub_windows_safely(self):
        """Bezpečne a okamžite zničí všetky pod-okná z MDI plochy pri odhlásení."""
        if hasattr(self.view, 'mdiArea') and self.view.mdiArea:
            self.view.mdiArea.closeAllSubWindows()

        if hasattr(self.window_controller, 'sub_windows'):
            self.window_controller.sub_windows.clear()
            
        if hasattr(self.window_controller, 'update_main_window_minimum_size'):
            self.window_controller.update_main_window_minimum_size()

    # =========================================================================
    # DYNAMICKÉ MENU A FILTROVANIE OPRÁVNENÍ (BEZ DUPLICÍT)
    # =========================================================================

    def rebuild_menu(self):
        """Zostaví menu nanovo, načíta čerstvé moduly z disku a vyčistí staré položky."""
        is_logged = self.auth_service.is_logged_in()

        # 1. KROK: Čerstvé načítanie aktuálne aktívnych modulov priamo z disku
        self.active_modules_info = self.module_manager.get_active_modules_info()

        # 2. KROK: Okamžité vymazanie starých dynamických akcií z menu
        for item in self.dynamic_menu_items:
            # Ak je položka priradená v menu, okamžite ju z neho odstránime
            for action in self.view.menu_bar.actions():
                menu = action.menu()
                if menu and item in menu.actions():
                    menu.removeAction(item)
            item.deleteLater()
        self.dynamic_menu_items.clear()

        # 3. KROK: Odstránenie celých dynamických kategórií (QMenu) z lišty
        for menu in self.dynamic_menus:
            self.view.menu_bar.removeAction(menu.menuAction())
            menu.deleteLater()
        self.dynamic_menus.clear()

        # 4. KROK: Zmapovanie základných pevných menu aplikácie (Program, Nastavenie, Okno, Pomocník)
        existing_menus = {}
        for action in self.view.menu_bar.actions():
            menu = action.menu()
            if menu and menu not in self.dynamic_menus:
                clean_title = menu.title().replace("&", "").strip().lower()
                existing_menus[clean_title] = menu

        # 5. KROK: Vloženie položiek aktívnych modulov do príslušných menu
        for mod_info in self.active_modules_info:
            menu_struct = mod_info.get("menu_structure", {})

            for category_name, items in menu_struct.items():
                cat_clean = category_name.replace("&", "").strip().lower()

                # Inteligentné párovanie názvov (Program/Súbor, Nastavenie/Nastavenia)
                target_menu = None
                if cat_clean in ["program", "súbor", "subor", "file"]:
                    target_menu = existing_menus.get("program") or existing_menus.get("súbor") or existing_menus.get("subor")
                elif cat_clean in ["nastavenie", "nastavenia", "settings"]:
                    target_menu = existing_menus.get("nastavenie") or existing_menus.get("nastavenia") or existing_menus.get("settings")
                else:
                    target_menu = existing_menus.get(cat_clean)

                # Vytvorenie nového menu pred 'Okno', ak ešte neexistuje
                if not target_menu:
                    target_menu = QMenu(category_name, self.view)
                    if hasattr(self.view, 'menu_window'):
                        self.view.menu_bar.insertMenu(self.view.menu_window.menuAction(), target_menu)
                    else:
                        self.view.menu_bar.addMenu(target_menu)
                    existing_menus[cat_clean] = target_menu
                    # DÔLEŽITÉ: Evidujeme celú kategóriu na zmazanie pri ďalšej zmene!
                    self.dynamic_menus.append(target_menu)

                # Vkladanie akcií s bezpečnostným filtrom
                for item in items:
                    if item.get("id") == "---SEPARATOR---" or item.get("text") == "---":
                        sep = target_menu.addSeparator()
                        self.dynamic_menu_items.append(sep)
                        continue

                    # Bezpečnostný filter stavu prihlásenia
                    if item.get("requires_login", False) and not is_logged:
                        continue
                    if item.get("requires_logged_out", False) and is_logged:
                        continue

                    # Bezpečnostný filter oprávnení
                    req_perm = item.get("required_permission")
                    if req_perm and not self.auth_service.has_permission(req_perm):
                        continue

                    action_text = item.get("text", "Neznáma akcia")
                    action = QAction(action_text, self.view)

                    handler_path = item.get("handler_path")
                    if handler_path:
                        action.triggered.connect(self._create_handler(handler_path))
                    elif mod_info.get("widget_factory_path") and mod_info.get("window_key"):
                        action.triggered.connect(self._create_window_opener(mod_info, action_text))

                    target_menu.addAction(action)
                    self.dynamic_menu_items.append(action)

    def _create_handler(self, handler_path: str):
        def trigger():
            try:
                mod_path, func_name = handler_path.rsplit('.', 1)
                module = importlib.import_module(mod_path)
                func = getattr(module, func_name)
                func()
            except Exception as e:
                print(f"[Security] Chyba akcie '{handler_path}': {e}")
        return trigger

    def _create_window_opener(self, mod_info: dict, title: str):
        w_key = mod_info.get("window_key")
        factory_path = mod_info.get("widget_factory_path")

        def trigger():
            try:
                mod_path, func_name = factory_path.rsplit('.', 1)
                module = importlib.import_module(mod_path)
                factory_func = getattr(module, func_name)

                self.window_controller.open_sub_window(
                    window_key=w_key,
                    widget_factory_func=factory_func,
                    window_title=title
                )
            except Exception as e:
                import traceback
                print(f"\n[Security] KRITICKÝ DETAIL CHYBY pri otváraní '{w_key}':")
                traceback.print_exc()
                print(f"[Security] Chyba otvorenia okna '{w_key}': {e}\n")
        return trigger

    def _register_module_services(self):
        """Registruje služby poskytované aktívnymi modulmi do ServiceManageru."""
        for module_info in self.active_modules_info:
            if "provided_services" in module_info:
                for service in module_info["provided_services"]:
                    service_type = service.get("service_type")
                    provider_info = service.get("provider_info")
                    if not service_type or not provider_info:
                        continue

                    if service_type == CoreServiceType.CORE_SERVICE:
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
        """Obnoví pod-okná uložené pre aktuálneho prihláseného používateľa."""
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