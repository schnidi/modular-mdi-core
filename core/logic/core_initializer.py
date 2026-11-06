# Súbor: core/logic/core_initializer.py

import inspect
import importlib
import configparser
from pathlib import Path

from core._path import Paths
from core.logic.core_bridge import CoreBridge
from core.logic.module_manager import ModuleManager
from core.logic.group_manager import GroupManager
from core.logic.services.config_manager import ConfigManager
from core.logic.services.auth_service import AuthService
from core.logic.language_manager import LanguageManager
from core.logic.plugin.service_manager import ServiceManager
from core.logic.services.about_logic import AboutLogic
from core.logic.services.github_update import GitHubUpdate
from core.windows.about_dialog import AboutDialog
from core.windows.custom_message_box import CustomMessageBox
from core.enum_core import ConfigSection, ConfigKey, ReservedModuleName, CoreServiceType
from core.logic.services.window_bounds_manager import WindowBoundsManager

WINDOW_SETUP_INI = Path(Paths.get_window_setup_ini())
AUTH_SETTINGS_INI = Path(Paths.get_auth_settings_ini())


class CoreInitializer:
    def __init__(self):
        self.worker = None
        self.user_info = None

    def run(self, worker) -> dict | None:
        self.worker = worker
        
        try:
            # --- Fáza 0: Inicializácia služieb jadra a mosta ---
            self._initialize_core_services()

            lang_mgr = LanguageManager.get_instance()

            # --- Fáza 1: Autentifikácia (0 % -> 20 %) ---
            msg_check_login = lang_mgr.get("msg_checking_login", "Kontrolujem prihlásenie...")
            self.worker.status_updated.emit(msg_check_login)
            self.worker.progress_updated.emit(15)
            if not self._handle_authentication():
                return None

            # --- Fáza 2: Načítanie modulov a spustenie ich bootstrapov (20 % -> 50 %) ---
            msg_load_mod = lang_mgr.get("msg_loading_modules", "Načítavam aktívne moduly...")
            self.worker.status_updated.emit(msg_load_mod)
            self.worker.progress_updated.emit(45)
            
            module_manager = ModuleManager()
            active_modules_info = module_manager.get_active_modules_info()

            # SPUSTENIE BOOTSTRAP PRE VŠETKY AKTÍVNE MODULY
            self._run_modules_bootstrap(active_modules_info)

            # --- Fáza 3: Príprava rozloženia okien (50 % -> 75 %) ---
            msg_prep_win = lang_mgr.get("msg_preparing_windows", "Pripravujem rozloženie okien...")
            self.worker.status_updated.emit(msg_prep_win)
            self.worker.progress_updated.emit(65)
            windows_to_open = self._get_windows_to_restore()

            # --- Koniec backendovej práce: odovzdanie do UI pri 75 % (NIKDY nie 100 %) ---
            msg_creating_ui = lang_mgr.get("msg_creating_main_window", "Vytváram hlavné okno...")
            self.worker.status_updated.emit(msg_creating_ui)
            self.worker.progress_updated.emit(75)

            startup_data = {
                "user_info": self.user_info if self.user_info is not None else {},
                "active_modules_info": active_modules_info,
                "windows_to_open": windows_to_open
            }
            return startup_data

        except Exception as e:
            print(f"KRITICKÁ CHYBA počas inicializácie jadra: {e}")
            lang_mgr = LanguageManager.get_instance()
            err_tpl = lang_mgr.get("msg_init_error", "Chyba pri inicializácii: {error}")
            self.worker.loading_failed.emit(err_tpl.format(error=e))
            return None

    def _initialize_core_services(self):
        sm = ServiceManager.get_instance()
        lang_mgr = LanguageManager.get_instance()
        bridge = CoreBridge.get_instance()

        sm.register_service(CoreServiceType.LANGUAGE_MANAGER.value, lang_mgr)
        sm.register_service("core_bridge", bridge)
        sm.register_service(CoreServiceType.AUTH_SERVICE.value, AuthService.get_instance())
        sm.register_service(CoreServiceType.GROUP_MANAGER.value, GroupManager.get_instance())
        sm.register_service(CoreServiceType.ABOUT_LOGIC.value, AboutLogic)
        sm.register_service(CoreServiceType.GITHUB_UPDATE.value, GitHubUpdate)
        sm.register_service(CoreServiceType.DIALOG_SERVICE.value, CustomMessageBox)
        sm.register_service("window_bounds_manager", WindowBoundsManager.get_instance())
        sm.register_service("module_manager", ModuleManager())
        
        saved_lang = bridge.load_module_setting(
            module_name="system_language",
            section="General",
            key="language",
            default="sk_SK"
        )
        lang_mgr.load_language(saved_lang)

        AboutLogic.register_about_dialog(AboutDialog)

    def _run_modules_bootstrap(self, active_modules_info: list):
        bridge = CoreBridge.get_instance()
        
        for mod_info in active_modules_info:
            bootstrap_path = mod_info.get("bootstrap_function_path")
            if not bootstrap_path:
                continue

            try:
                mod_path, func_name = bootstrap_path.rsplit('.', 1)
                module = importlib.import_module(mod_path)
                bootstrap_func = getattr(module, func_name)

                sig = inspect.signature(bootstrap_func)
                if len(sig.parameters) > 0:
                    bootstrap_func(bridge)
                else:
                    bootstrap_func()
                    
            except Exception as e:
                mod_name = mod_info.get("name") or mod_info.get("module_name", "Neznámy")
                print(f"[CoreInitializer] CHYBA bootstrap pre modul '{mod_name}' ({bootstrap_path}): {e}")

    def _handle_authentication(self) -> bool:
        auth_info = self.find_active_auth_module()
        if not auth_info:
            return True

        lang_mgr = LanguageManager.get_instance()
        msg = lang_mgr.get("msg_login_required", "Vyžaduje sa prihlásenie...")
        self.worker.status_updated.emit(msg)
        
        if not self.worker.user_info:
            result = self.worker.event_loop.exec()
        else:
            result = 1

        if result == 1 and self.worker.user_info:
            self.user_info = self.worker.user_info
            AuthService.get_instance().login(self.user_info)
            return True
        else:
            cancel_msg = lang_mgr.get("msg_login_cancelled", "Prihlásenie zrušené. Aplikácia sa ukončuje.")
            self.worker.status_updated.emit(cancel_msg)
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1500, QApplication.instance().quit)
            return False

    def _get_windows_to_restore(self) -> list[str]:
        config = ConfigManager(WINDOW_SETUP_INI)
        auth_service = AuthService.get_instance()
        if self.user_info:
             auth_service.login(self.user_info)

        prefix = auth_service.get_current_prefix()
        
        module_manager = ModuleManager()
        all_modules = module_manager._discover_all_modules()
        all_window_keys = set()
        for module_name, interface_file in all_modules:
            info = module_manager._load_module_info(module_name, interface_file)
            if info and (key := info.get("window_key")):
                all_window_keys.add(key)
        all_window_keys.add("ModuleSetup")
        
        windows_to_open = []
        for key in all_window_keys:
            is_open_key = f"{prefix}_{ConfigKey.IS_OPEN}" if prefix != auth_service.DEFAULT_USER_PREFIX else ConfigKey.IS_OPEN
            is_open_val = config.get_value(key, is_open_key)
            if is_open_val is None and prefix != auth_service.DEFAULT_USER_PREFIX:
                is_open_val = config.get_value(key, ConfigKey.IS_OPEN)

            if is_open_val == 'True':
                windows_to_open.append(key)
        
        return windows_to_open

    @staticmethod
    def find_active_auth_module():
        """Statická metóda pre okamžité zistenie aktívneho auth modulu pri štarte."""
        if not AUTH_SETTINGS_INI.exists():
            return None
        
        auth_config = configparser.ConfigParser()
        auth_config.read(AUTH_SETTINGS_INI, encoding='utf-8')
        
        sec = ConfigSection.SETTINGS.value if hasattr(ConfigSection.SETTINGS, 'value') else str(ConfigSection.SETTINGS)
        key = ConfigKey.ACTIVE_AUTH_MODULE.value if hasattr(ConfigKey.ACTIVE_AUTH_MODULE, 'value') else str(ConfigKey.ACTIVE_AUTH_MODULE)
        
        active_auth_module_name = auth_config.get(sec, key, fallback=None)
        if not active_auth_module_name:
            return None
        
        module_manager = ModuleManager()
        all_modules = module_manager._discover_all_modules()
        
        for module_name, interface_file in all_modules:
            if module_name == active_auth_module_name:
                if module_manager.module_config.is_module_enabled(module_name):
                    return module_manager._load_module_info(module_name, interface_file)
        return None

    def _find_active_auth_module(self):
        return self.find_active_auth_module()