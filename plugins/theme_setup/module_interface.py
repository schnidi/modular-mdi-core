# Súbor: modules/theme_setup/module_interface.py

def _build_dynamic_paths(info: dict) -> dict:
    """
    Pomocná funkcia, ktorá doplní dynamicky generovanú cestu k továrni na widgety.
    """
    try:
        path_parts = []
        path_parts.append(info["module_name"])
        path_parts.append(info["factory_module_name"])
        path_parts.append(info["factory_function_name"])
        
        info["widget_factory_path"] = f"modules.{'.'.join(path_parts)}"
        return info
    except Exception as e:
        print(f"CHYBA pri skladaní dynamických ciest pre {info.get('module_name', 'N/A')}: {e}")
        return info

def get_module_info():
    """
    Hlavná funkcia poskytujúca kompletné informácie o module pre jadro.
    """
    base_info = {
        # Typ a identifikácia modulu
        "module_type": "utility",
        "module_name": "theme_setup",
        "install_path_prefix": "",
        "window_key": "ThemeSetup",
        
        # Továreň na widget
        "factory_module_name": "main_logic",
        "factory_function_name": "create_theme_setup_widget",
        
        
        "menu_structure": {
            "Nastavenie": [
                {
                    "text": "Vzhľad a Témy...",
                    "requires_login": False
                }
            ]
        },
        
        # Informácie pre ovládací panel
        "control_panel_entry": {
            "display_name": "Vzhľad a Témy",
            "icon_path": "resources/theme_icon.svg"
        }
    }

    return _build_dynamic_paths(base_info)