# Súbor: modules/theme_setup/module_interface.py

def _build_dynamic_paths(info: dict) -> dict:
    """
    Pomocná funkcia, ktorá doplní dynamicky generovanú cestu k továrni na widgety.
    Je volaná z hlavnej funkcie get_module_info, aby sa zabezpečilo,
    že výsledok je vždy kompletný.
    """
    try:
        path_parts = []
        
        # Tento modul nemá prefix, inštaluje sa priamo do /modules,
        # preto je táto časť zakomentovaná, ale ponechaná pre budúce použitie.
        # prefix = info.get("install_path_prefix", "")
        # if prefix:
        #     path_parts.append(prefix.replace('\\', '/').replace('/', '.'))
        
        path_parts.append(info["module_name"])
        path_parts.append(info["factory_module_name"])
        path_parts.append(info["factory_function_name"])
        
        # Zostavíme finálnu cestu, ktorú jadro použije na dynamický import
        info["widget_factory_path"] = f"modules.{'.'.join(path_parts)}"
        
        return info
    except Exception as e:
        # Vypíše chybu, ak by chýbal niektorý z kľúčov potrebných na zostavenie cesty
        print(f"CHYBA pri skladaní dynamických ciest pre {info.get('module_name', 'N/A')}: {e}")
        return info

def get_module_info():
    """
    Hlavná a jediná funkcia, ktorá poskytuje kompletné informácie o module 'theme_setup'.
    Je navrhnutá tak, aby bola robustná a vždy vrátila kompletné a konzistentné dáta.
    """
    # Krok 1: Definujeme základný, statický slovník informácií.
    # Tento slovník obsahuje všetky kľúčové informácie o module.
    base_info = {
        # Typ modulu - 'utility' je vhodný pre nástroje na správu aplikácie
        "module_type": "utility",
        
        # Interný názov modulu (musí zodpovedať názvu priečinku)
        "module_name": "theme_setup",
        
        # Inštalačný prefix - prázdny, lebo je to hlavný modul
        "install_path_prefix": "",
        
        # Unikátny kľúč pre jeho hlavné okno (pre správu v MDI oblasti)
        "window_key": "ThemeSetup",
        
        # Názvy súborov a funkcií, ktoré má jadro hľadať na vytvorenie widgetu
        "factory_module_name": "main_logic",
        "factory_function_name": "create_theme_setup_widget",
        
        # --- Informácie pre Ovládací panel ---
        "control_panel_entry": {
            "display_name": "Vzhľad a Témy",
            "icon_path": "resources/theme_icon.svg",
            
            # Kľúč "required_permission" je úmyselne vynechaný.
            # Jeho absencia znamená, že ikona bude viditeľná pre každého,
            # bez ohľadu na prihlásenie alebo oprávnenia.
        }
    }

    # Krok 2: Na tomto základnom slovníku zavoláme pomocnú funkciu,
    # ktorá ho doplní o dynamicky generované cesty.
    full_info = _build_dynamic_paths(base_info)

    # Krok 3: Vrátime finálny, vždy kompletný slovník.
    return full_info