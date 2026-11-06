"""
Súbor: core/enum_core.py
Centrálny register konštánt, enumov a rozhraní pre jadro a moduly.
"""

from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget


# =====================================================================
# 0. ABSTRAKTNÉ PREDPISY A ROZHRANIA (INTERFACES)
# =====================================================================

class ICoreBridge(QObject):
    """
    ABSTRAKTNÝ KOMUNIKAČNÝ KANÁL MEDZI MODULOM A JADROM.
    Modul komunikuje so systémom výhradne cez toto rozhranie.
    """
    _instance = None

    @classmethod
    def get_instance(cls) -> "ICoreBridge":
        """Vráti aktívnu inštanciu mosta jadra."""
        return cls._instance

    # Globálny signál o zmene jazyka
    language_changed = pyqtSignal(str)

    # --- Preklady a jazyk ---
    def set_language(self, lang_code: str) -> bool:
        """Modul požiada o prepnutie jazyka systému."""
        raise NotImplementedError

    def get_current_language(self) -> str:
        """Vráti aktuálny kód jazyka (napr. 'sk_SK')."""
        raise NotImplementedError

    def get_available_languages(self) -> list[str]:
        """Vráti zoznam všetkých dostupných jazykov."""
        raise NotImplementedError

    def get_text(self, key: str, default: str = None) -> str:
        """Vráti preložený text podľa kľúča."""
        raise NotImplementedError

    def translate_widget(self, widget: QWidget) -> None:
        """Automaticky preloží podradené prvky widgetu podľa objectName."""
        raise NotImplementedError

    def connect_language_changed(self, slot) -> None:
        """Prihlási slot na zmenu jazyka."""
        raise NotImplementedError

    def disconnect_language_changed(self, slot) -> None:
        """Odhlási slot zo zmeny jazyka."""
        raise NotImplementedError

    def register_module_translations(self, module_info: dict) -> bool:
        """Zaregistruje preklady modulu podľa jeho metadát."""
        raise NotImplementedError

    # --- Ukladanie nastavení modulu ---
    def save_module_setting(self, module_name: str, section: str, key: str, value: str) -> None:
        """Bezpečne uloží nastavenie modulu do config/plugins/<module_name>/settings.ini."""
        raise NotImplementedError

    def load_module_setting(self, module_name: str, section: str, key: str, default: str = None) -> str:
        """Načíta nastavenie modulu z config/plugins/<module_name>/settings.ini."""
        raise NotImplementedError

    def get_module_config_dir(self, module_name: str) -> str:
        """Vráti cestu k bezpečnému priečinku pre konfigurácie modulu."""
        raise NotImplementedError

    # --- Dialógové okná (v téme aplikácie) ---
    def show_info(self, title: str, text: str, parent: QWidget = None) -> None:
        """Zobrazí informačnú správu."""
        raise NotImplementedError

    def show_warning(self, title: str, text: str, parent: QWidget = None) -> None:
        """Zobrazí varovnú správu."""
        raise NotImplementedError

    def show_error(self, title: str, text: str, details: str = None, parent: QWidget = None) -> None:
        """Zobrazí chybové hlásenie s voliteľnými detailmi."""
        raise NotImplementedError

    def ask_question(self, title: str, text: str, parent: QWidget = None) -> bool:
        """Zobrazí otázku s voľbou Áno / Nie."""
        raise NotImplementedError

    def get_text_input(self, title: str, text: str, is_password: bool = False, parent: QWidget = None) -> tuple[str, bool]:
        """Zobrazí dialóg pre zadanie textového vstupu / hesla."""
        raise NotImplementedError

    def show_dialog(self, content_widget: QWidget, title: str = "", parent: QWidget = None) -> int:
        """Zobrazí vlastný widget v bezrámovom dialógovom okne v téme aplikácie."""
        raise NotImplementedError

    # =========================================================================
    # Služby - Service Manager
    # =========================================================================
    def get_service(self, service_name: str) -> object:
        """Vráti inštanciu služby z centrálneho registra jadra."""
        raise NotImplementedError

    def on_service_ready(self, service_name: str, callback) -> None:
        """Zaregistruje callback, ktorý sa spustí, keď bude služba dostupná."""
        raise NotImplementedError


class ILanguageService(QObject):
    """
    Abstraktný predpis pre interný jazykový manažér.
    """
    language_changed = pyqtSignal(str)

    def load_language(self, lang_code: str = "auto") -> bool:
        raise NotImplementedError

    def get(self, key: str, default: str = None) -> str:
        raise NotImplementedError

    def translate_ui(self, widget: QWidget) -> None:
        raise NotImplementedError

    def get_current_language(self) -> str:
        raise NotImplementedError

    def get_available_languages(self) -> list[str]:
        raise NotImplementedError


# =====================================================================
# 1. KONFIGURAČNÉ A SYSTÉMOVÉ ENUMY
# =====================================================================

class ConfigSection(str, Enum):
    """Názvy sekcií v konfiguračných súboroch .ini."""
    SETTINGS = "Settings"
    MAIN_WINDOW = "MainWindow"
    MODULES = "Modules"
    SYSTEM_GROUPS = "SystemGroups"


class ConfigKey(str, Enum):
    """Kľúče používané v konfiguračných súboroch (.ini)."""
    ACTIVE_THEME = "active_theme"
    ACTIVE_AUTH_MODULE = "active_authentication_module"
    
    PATH = "path"
    ENABLED = "enabled"
    SOURCE_MODULE = "source_module"
    PERMISSIONS = "permissions"
    
    GEOMETRY = "geometry"
    IS_OPEN = "is_open"
    MODE = "mode"
    FLOATING_GEOMETRY = "floating_geometry"
    CURRENT_GEOMETRY = "current_geometry"


class WindowKey(str, Enum):
    """Jednoznačné systémové identifikátory okien."""
    MAIN_WINDOW = "MainWindow"
    MODULE_SETUP = "ModuleSetup"
    TEST_WINDOW = "test_window_1"


class WindowMode(str, Enum):
    """Stavy a režimy pre FramelessMdiSubWindow."""
    NORMAL = "normal"
    MAXIMIZED = "maximized"
    MINIMIZED = "minimized"


class CoreServiceType(str, Enum):
    """Názvy služieb v ServiceManageri."""
    LANGUAGE_MANAGER = "language_manager"
    AUTH_SERVICE = "auth_service"
    GITHUB_UPDATE = "github_update"
    ABOUT_LOGIC = "about_logic"
    TRANSLATION = "translation_service"
    CORE_SERVICE = "core_service"
    GROUP_MANAGER = "group_manager"
    DIALOG_SERVICE = "dialog_service"


class ReservedModuleName(str, Enum):
    """Rezervované systémové názvy modulov."""
    SYSTEM_LANGUAGE = "system_language"


class AuthConstant(str, Enum):
    """Konštanty pre autentifikačný systém."""
    DEFAULT_USER_PREFIX = "DEFAULT"


# =====================================================================
# 2. INTEGRAČNÉ ENUMY
# =====================================================================

class ModuleInfoKey(str, Enum):
    """Štandardizované kľúče v slovníku get_module_info()."""
    NAME = "name"
    MODULE_NAME = "module_name"
    VERSION = "version"
    DESCRIPTION = "description"
    AUTHOR = "author"
    WINDOW_KEY = "window_key"
    INSTALL_PATH_PREFIX = "install_path_prefix"
    PATHS_MODULE_PATH = "paths_module_path"
    PROVIDED_GROUPS = "provided_groups"
    BOOTSTRAP_FUNCTION_PATH = "bootstrap_function_path"
    WIDGET_FACTORY_PATH = "widget_factory_path" 
    AUTH_WIDGET_FACTORY_PATH = "auth_widget_factory_path"
    SETUP_FUNCTION_PATH = "setup_function_path"


class ModuleInstallStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CORRUPTED = "corrupted"
    NOT_INSTALLED = "not_installed"


class DatabaseType(str, Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


class StandardRole(str, Enum):
    ADMIN = "Administrátor"
    MANAGER = "Manažér"
    USER = "Používateľ"
    GUEST = "Hosť"