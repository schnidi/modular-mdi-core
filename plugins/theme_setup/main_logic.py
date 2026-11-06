# Súbor: modules/theme_setup/main_logic.py

from core.enum_core import ICoreBridge
from . import _paths
from .module_interface import get_module_info
from .windows.theme_setup_window import ThemeSetupWindow
from .logic.theme_setup_controller import ThemeSetupController


def _get_bridge(bridge: ICoreBridge = None) -> ICoreBridge:
    return bridge if bridge is not None else ICoreBridge.get_instance()


def bootstrap(bridge: ICoreBridge = None):
    """Zavolá sa jadrom pri štarte aplikácie na registráciu prekladov."""
    b = _get_bridge(bridge)
    if b:
        b.register_module_translations(get_module_info())


def create_theme_setup_widget(bridge: ICoreBridge = None, **kwargs):
    """
    Továrenská funkcia, ktorú volá jadro na vytvorenie hlavného widgetu modulu.
    """
    b = _get_bridge(bridge)
    if b:
        b.register_module_translations(get_module_info())

    view = ThemeSetupWindow(bridge=b)
    view.setProperty("module_name", _paths.MODULE_NAME)

    controller = ThemeSetupController(view, bridge=b)
    view.controller = controller

    if b:
        b.translate_widget(view)

    return view