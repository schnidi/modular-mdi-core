# Súbor: modules/tab_menu/main_logic.py

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication

# JEDINÝ POVOLENÝ IMPORT Z JADRA - Abstraktné rozhranie
from core.enum_core import ICoreBridge

from .windows.tab_menu_bar_widget import TabMenuBarWidget
from .logic.tab_menu_controller import TabMenuController

_tab_menu_instance = None
_cached_bridge = None  # Držíme si referenciu na bridge, ktorú nám dalo jadro


class TabMenuService:
    @classmethod
    def get_instance(cls):
        global _tab_menu_instance
        return _tab_menu_instance


def _get_bridge(bridge: ICoreBridge = None) -> ICoreBridge:
    """
    Bezpečne získa inštanciu ICoreBridge:
    1. Z odovzdaného parametra
    2. Z lokálnej cache modulu
    3. Priamo zo Singletonu jadra (funguje aj pri aktivácii za behu bez reštartu!)
    """
    global _cached_bridge
    if bridge is not None:
        _cached_bridge = bridge
        return bridge
    if _cached_bridge is not None:
        return _cached_bridge

    _cached_bridge = ICoreBridge.get_instance()
    return _cached_bridge


def bootstrap_tab_menu(bridge: ICoreBridge = None, *args, **kwargs):
    """
    Vstupný bod modulu pri štarte aplikácie.
    """
    b = _get_bridge(bridge)
    create_widget(bridge=b, **kwargs)


def create_widget(bridge: ICoreBridge = None, **kwargs):
    global _tab_menu_instance

    
    bridge = _get_bridge(bridge)

    if not bridge:
        print("[TAB_MENU] CHYBA: Bridge nebol poskytnutý jadrom!")
        return None

    if _tab_menu_instance is not None:
        if getattr(_tab_menu_instance, "bridge", None) != bridge:
            _tab_menu_instance.bridge = bridge
            bridge.connect_language_changed(_tab_menu_instance.retranslate_ui)
        return _tab_menu_instance

    app = QApplication.instance()
    if not app:
        return None

    if QThread.currentThread() != app.thread():
        if hasattr(bridge, "run_on_gui_thread"):
            bridge.run_on_gui_thread.emit(lambda: create_widget(bridge=bridge, **kwargs))
        return None

    
    main_controller = kwargs.get("main_controller") or bridge.get_service("window_manager")

    if not main_controller or not hasattr(main_controller, "view") or main_controller.view is None:
        bridge.on_service_ready(
            "window_manager",
            lambda wm: create_widget(bridge=bridge, main_controller=wm)
        )
        return None

    view = TabMenuBarWidget(bridge=bridge)
    controller = TabMenuController(
        bar_view=view,
        bridge=bridge,
        main_controller=main_controller
    )
    view.controller = controller

    _tab_menu_instance = view
    return view


def toggle_tab_menu(bridge: ICoreBridge = None, *args, **kwargs):
    """
    Obsluha kliknutia na položku v menu 'Okno -> Záložková lišta'.
    Jadro sem posiela inštanciu bridge ako prvý parameter.
    """
    global _tab_menu_instance
    
    
    incoming_bridge = bridge or (args[0] if args and isinstance(args[0], ICoreBridge) else None)
    b = _get_bridge(incoming_bridge)

    if _tab_menu_instance is None:
        create_widget(bridge=b)
    else:
        if hasattr(_tab_menu_instance, "controller") and _tab_menu_instance.controller:
            _tab_menu_instance.controller.toggle_visibility()
        else:
            vis = _tab_menu_instance.isVisible()
            _tab_menu_instance.setVisible(not vis)