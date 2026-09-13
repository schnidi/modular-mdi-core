# Súbor: modules/theme_setup/main_logic.py

# Importujeme View a Controller, ktoré sme práve vytvorili
from .windows.theme_setup_window import ThemeSetupWindow
from .logic.theme_setup_controller import ThemeSetupController

def create_theme_setup_widget(**kwargs):
    """
    Továrenská funkcia, ktorú volá jadro na vytvorenie hlavného widgetu modulu.
    Spojí dokopy View (okno) a Controller (logiku).
    """
    # 1. Vytvoríme inštanciu nášho okna (View)
    view = ThemeSetupWindow()
    
    # 2. Vytvoríme inštanciu našej logiky (Controller) a prepojíme ju s oknom
    controller = ThemeSetupController(view)
    
    # 3. Uložíme si referenciu na controller do view (dobrý zvyk pre ladenie)
    view.controller = controller
    
    # 4. Vrátime hotový a funkčný widget jadru aplikácie
    return view