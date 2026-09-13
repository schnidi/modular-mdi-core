# Súbor: core/logic/core_initializer.py

import importlib
import configparser
from pathlib import Path

from core._path import Paths
from core.logic.module_manager import ModuleManager
from core.logic.services.config_manager import ConfigManager
from core.logic.services.auth_service import AuthService
from core.logic.language_manager import LanguageManager
from core.logic.plugin.service_manager import ServiceManager
from core.logic.services.about_logic import AboutLogic
from core.logic.services.github_update import GitHubUpdate
from core.windows.about_dialog import AboutDialog
from core.windows.custom_message_box import CustomMessageBox
from core.enum_core import ConfigSection, ConfigKey, ReservedModuleName
from core.logic.services.window_bounds_manager import WindowBoundsManager

WINDOW_SETUP_INI = Path(Paths.get_window_setup_ini())
AUTH_SETTINGS_INI = Path(Paths.get_auth_settings_ini())


class CoreInitializer:
    """
    Táto trieda centralizuje a riadi komplexnú logiku štartu aplikácie.
    Beží v kontexte StartupWorker-a (vo vedľajšom vlákne), aby neblokovala UI,
    a pripravuje všetky dáta potrebné pre MainWindow pred jeho zobrazením.
    """
    def __init__(self):
        self.worker = None # Referencia na workera pre posielanie signálov
        self.user_info = None

    def run(self, worker) -> dict | None:
        """
        Hlavná metóda, ktorá vykoná celý štartovací proces.
        Vracia "štartovací balíček" (slovník) s pripravenými dátami,
        alebo None v prípade zrušenia alebo chyby.
        """
        self.worker = worker
        
        try:
            # --- Fáza 0: Inicializácia kritickej infraštruktúry ---
            self._initialize_core_services()
            self._initialize_translation_service()

            # --- Fáza 1: Autentifikácia ---
            self.worker.status_updated.emit("Kontrolujem prihlásenie...")
            self.worker.progress_updated.emit(10)
            if not self._handle_authentication():
                return None

            # --- Fáza 2: Načítanie modulov a služieb ---
            self.worker.status_updated.emit("Načítavam aktívne moduly...")
            self.worker.progress_updated.emit(50)
            module_manager = ModuleManager()
            active_modules_info = module_manager.get_active_modules_info()

            # --- Fáza 3: Príprava stavu okien ---
            self.worker.status_updated.emit("Pripravujem rozloženie okien...")
            self.worker.progress_updated.emit(80)
            windows_to_open = self._get_windows_to_restore()

            self.worker.status_updated.emit("Príprava dokončená...")
            self.worker.progress_updated.emit(100)

            # --- Vytvorenie finálneho "štartovacieho balíčka" ---
            startup_data = {
                "user_info": self.user_info if self.user_info is not None else {},
                "active_modules_info": active_modules_info,
                "windows_to_open": windows_to_open
            }
            return startup_data

        except Exception as e:
            print(f"KRITICKÁ CHYBA počas inicializácie jadra: {e}")
            self.worker.loading_failed.emit(f"Chyba pri inicializácii: {e}")
            return None

    def _initialize_core_services(self):
        """Základné interné služby jadra."""
        sm = ServiceManager.get_instance()
        sm.register_service("language_manager", LanguageManager)
        sm.register_service("auth_service", AuthService.get_instance())
        sm.register_service("about_logic", AboutLogic)
        sm.register_service("github_update", GitHubUpdate)
        sm.register_service("dialog_service", CustomMessageBox)
        sm.register_service("window_bounds_manager", WindowBoundsManager.get_instance())
        LanguageManager.load_language("sk_SK")
        AboutLogic.register_about_dialog(AboutDialog)

    def _initialize_translation_service(self):
        self.worker.status_updated.emit("Inicializujem prekladový systém...")
        
        module_name_to_find = ReservedModuleName.SYSTEM_LANGUAGE
        module_info = None
        
        try:
            module_manager = ModuleManager()
            all_modules = module_manager._discover_all_modules()

            for name, interface_file in all_modules:
                if name == module_name_to_find:
                    if module_manager.module_config.is_module_enabled(name):
                        module_info = module_manager._load_module_info(name, interface_file)
                    else:
                        print(f"INFO: Prekladový modul '{name}' je deaktivovaný.")
                    break 
            
            if not module_info:
                print(f"INFO: Prekladový modul '{module_name_to_find}' nebol nájdený alebo nie je aktívny. Aplikácia nebude preložená.")
                return

            bootstrap_path = module_info.get("bootstrap_function_path")
            if not bootstrap_path:
                print(f"CHYBA: Prekladový modul '{module_name_to_find}' nemá definovanú 'bootstrap_function_path'.")
                return

            try:
                module_path, func_name = bootstrap_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                bootstrap_func = getattr(module, func_name)
                bootstrap_func()
                print(f"INFO: Prekladový modul '{module_name_to_find}' bol úspešne inicializovaný.")
            except Exception as e:
                print(f"KRITICKÁ CHYBA: Zlyhala inicializácia bootstrap funkcie pre '{module_name_to_find}': {e}")
        
        except Exception as e:
            print(f"CHYBA: Vyskytla sa neočakávaná chyba pri pokuse o inicializáciu prekladov: {e}")

    def _handle_authentication(self) -> bool:
        auth_info = self._find_active_auth_module()
        if not auth_info:
            return True

        msg = LanguageManager.get("msg_login_required", "Vyžaduje sa prihlásenie...")

        self.worker.status_updated.emit(msg)
        factory_path = auth_info.get("auth_widget_factory_path")
        if not factory_path:
            raise ValueError("Aktívny autentifikačný modul neposkytuje 'auth_widget_factory_path'.")

        module_path, func_name = factory_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        factory_func = getattr(module, func_name)

        self.worker.auth_widget_required.emit(factory_func, self.worker)
        result = self.worker.event_loop.exec()

        if result == 1 and self.worker.user_info:
            self.user_info = self.worker.user_info
            AuthService.get_instance().login(self.user_info)
            return True
        else:
            cancel_msg = LanguageManager.get("msg_login_cancelled", "Prihlásenie zrušené. Aplikácia sa ukončuje.")
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
        
        # auth_service.logout()
        return windows_to_open

    def _find_active_auth_module(self):
        if not AUTH_SETTINGS_INI.exists(): return None
        
        auth_config = configparser.ConfigParser()
        auth_config.read(AUTH_SETTINGS_INI, encoding='utf-8')
        
        # Získanie sekcie a kľúča
        sec = ConfigSection.SETTINGS.value if hasattr(ConfigSection.SETTINGS, 'value') else str(ConfigSection.SETTINGS)
        key = ConfigKey.ACTIVE_AUTH_MODULE.value if hasattr(ConfigKey.ACTIVE_AUTH_MODULE, 'value') else str(ConfigKey.ACTIVE_AUTH_MODULE)
        
        active_auth_module_name = auth_config.get(sec, key, fallback=None)
        
        if not active_auth_module_name: return None
        
        module_manager = ModuleManager()
        all_modules = module_manager._discover_all_modules()
        
        for module_name, interface_file in all_modules:
            if module_name == active_auth_module_name:
                if module_manager.module_config.is_module_enabled(module_name):
                    return module_manager._load_module_info(module_name, interface_file)
        return None