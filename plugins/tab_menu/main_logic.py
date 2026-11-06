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


def bootstrap_tab_menu(bridge: ICoreBridge, *args, **kwargs):
    """
    Vstupný bod modulu. Jadro sem injektuje ICoreBridge.
    Modul si ho uloží a použije na všetko.
    """
    global _cached_bridge
    _cached_bridge = bridge
    create_widget(bridge=bridge, **kwargs)


def create_widget(bridge: ICoreBridge = None, **kwargs):
    global _tab_menu_instance, _cached_bridge

    # Ak nám funkciu volá iná časť modulu bez bridge-a, použijeme cachovaný
    bridge = bridge or _cached_bridge
    
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
        # OPRAVA: Vrátený bezpečný mechanizmus z tvojho jadra na prenos z Worker vlákna na GUI vlákno!
        # QTimer.singleShot tu zlyhával, lebo app event loop ešte plne nebežal.
        if hasattr(bridge, "run_on_gui_thread"):
            bridge.run_on_gui_thread.emit(lambda: create_widget(bridge=bridge, **kwargs))
        return None

    # Služby pýtame VÝHRADNE cez ICoreBridge
    main_controller = kwargs.get("main_controller") or bridge.get_service("window_manager")

    if not main_controller or not hasattr(main_controller, "view") or main_controller.view is None:
        # Ak okno ešte nie je hotové, prenecháme čakanie na ICoreBridge a ServiceManager
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


def toggle_tab_menu(*args, **kwargs):
    global _tab_menu_instance
    if _tab_menu_instance is None:
        create_widget()
    else:
        if hasattr(_tab_menu_instance, "controller") and _tab_menu_instance.controller:
            _tab_menu_instance.controller.toggle_visibility()
        else:
            vis = _tab_menu_instance.isVisible()
            _tab_menu_instance.setVisible(not vis)