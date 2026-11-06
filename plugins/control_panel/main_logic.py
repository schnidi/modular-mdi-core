# Súbor: modules/control_panel/main_logic.py

from core.enum_core import ICoreBridge
from . import _paths
from .module_interface import get_module_info
from .windows.control_panel_window import ControlPanelWindow


def _get_bridge(bridge: ICoreBridge = None) -> ICoreBridge:
    return bridge if bridge is not None else ICoreBridge.get_instance()


def bootstrap(bridge: ICoreBridge = None):
    """Zavolá sa pri štarte jadra pred stavbou UI."""
    b = _get_bridge(bridge)
    if b:
        b.register_module_translations(get_module_info())


def create_control_panel_widget(bridge: ICoreBridge = None, **kwargs):
    """Továrenská funkcia, ktorú volá jadro na vytvorenie ovládacieho panela."""
    b = _get_bridge(bridge)
    if b:
        b.register_module_translations(get_module_info())

    view = ControlPanelWindow(bridge=b)
    view.setProperty("module_name", _paths.MODULE_NAME)
    return view