# Súbor: modules/control_panel/main_logic.py

from .windows.control_panel_window import ControlPanelWindow
from .logic.control_panel_controller import ControlPanelController

def create_control_panel_widget(**kwargs):
    """
    Továrenská funkcia, ktorú volá nové jadro.
    """
    service_manager = kwargs.get("service_manager")
    main_controller = kwargs.get("main_controller")

    view = ControlPanelWindow()
    controller = ControlPanelController(view, service_manager, main_controller)
    view.controller = controller
    return view