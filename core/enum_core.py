"""
Súbor: core/enum_core.py
Centrálny register konštánt, enumov a identifikátorov pre celé jadro aj moduly.
"""

from enum import Enum


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
    # Všeobecné nastavenia
    ACTIVE_THEME = "active_theme"
    ACTIVE_AUTH_MODULE = "active_authentication_module"
    
    # Moduly a správa ciest
    PATH = "path"
    ENABLED = "enabled"
    SOURCE_MODULE = "source_module"
    PERMISSIONS = "permissions"
    
    # Geometria a správa okien
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


class ReservedModuleName(str, Enum):
    """Rezervované systémové názvy modulov."""
    SYSTEM_LANGUAGE = "system_language"


class AuthConstant(str, Enum):
    """Konštanty pre autentifikačný systém."""
    DEFAULT_USER_PREFIX = "DEFAULT"


# =====================================================================
# 2. INTEGRAČNÉ ENUMY (Pre moduly a rozhrania)
# =====================================================================

class ModuleInfoKey(str, Enum):
    """Štandardizované kľúče v slovníku get_module_info()."""
    NAME = "name"
    VERSION = "version"
    DESCRIPTION = "description"
    AUTHOR = "author"
    WINDOW_KEY = "window_key"
    INSTALL_PATH_PREFIX = "install_path_prefix"
    PROVIDED_GROUPS = "provided_groups"
    BOOTSTRAP_FUNCTION_PATH = "bootstrap_function_path"
    AUTH_WIDGET_FACTORY_PATH = "auth_widget_factory_path"
    SETUP_FUNCTION_PATH = "setup_function_path"


class ModuleInstallStatus(str, Enum):
    """Stav inštalácie a integrity modulu."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    CORRUPTED = "corrupted"
    NOT_INSTALLED = "not_installed"


class DatabaseType(str, Enum):
    """Podporované databázové ovládače."""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


class StandardRole(str, Enum):
    """Štandardné používateľské roly (skupiny)."""
    ADMIN = "Administrátor"
    MANAGER = "Manažér"
    USER = "Používateľ"
    GUEST = "Hosť"