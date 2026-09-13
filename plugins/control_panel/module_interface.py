# Súbor: modules/control_panel/module_interface.py
# OPRAVENÁ VERZIA, KTORÁ SPRÁVNE ZAOBCHÁDZA S 'provided_groups'

"""
Rozhranie pre modul 'Ovládací panel'.
Využíva dynamické skladanie ciest pre jednoduchú prenositeľnosť.
"""

def _build_dynamic_paths(info: dict) -> dict:
    """
    Pomocná funkcia, ktorá na základe názvu modulu a prefixu automaticky
    vyskladá plné cesty k triedam a funkciám.
    Je to generická funkcia, ktorú je možné použiť vo všetkých moduloch.
    """
    try:
        path_parts = ["modules"]
        prefix = info.get("install_path_prefix", "")
        
        if prefix:
            path_parts.append(prefix.replace('\\', '/').replace('/', '.'))
        
        path_parts.append(info["module_name"])
        base_path = ".".join(path_parts)

        if "widget_factory_path" in info:
            info["widget_factory_path"] = info["widget_factory_path"].format(base_path=base_path)
        
        return info
    except Exception as e:
        print(f"CHYBA: Zlyhalo dynamické skladanie ciest pre modul {info.get('module_name')}: {e}")
        return info

def get_module_info():
    """
    Hlavná funkcia, ktorú volá jadro.
    """
    # ======================================================================
    # ČASŤ 1: KONFIGURÁCIA - Toto je jediné miesto, ktoré treba upraviť
    # ======================================================================
    base_info = {
        "module_type": "core_extension",
        "module_name": "control_panel",
        "install_path_prefix": "",
        "window_key": "ControlPanel",
        "requires_main_controller": True,
        "widget_factory_path": "{base_path}.main_logic.create_control_panel_widget",
        "menu_structure": {
            "Nastavenie": [
                {
                    "text": "Ovládací panel...",
                    "id": "control_panel.open"
                }
            ]
        },
        # Tento kľúč tu zostáva, ale jadro ho číta cez samostatnú funkciu.
        # Máme ho tu pre prehľadnosť a aby sme naň nezabudli.
        "provided_groups": {
            "SystemAdmin": [
                "admin.system_config"
            ]
        }
    }

    # ======================================================================
    # ČASŤ 2: SPRACOVANIE - Túto časť už nikdy nemusíš meniť
    # ======================================================================
    full_info = _build_dynamic_paths(base_info)
    
    # Kľúč 'provided_groups' odstránime z hlavného slovníka,
    # pretože sa očakáva v samostatnej funkcii.
    full_info.pop("provided_groups", None)

    return full_info

def get_provided_groups():
    """
    Táto funkcia vracia oprávnenia, ktoré tento modul pridáva do systému.
    Jadro ju volá samostatne.
    """
    # Tu vraciame natvrdo definované skupiny, pretože neobsahujú dynamické cesty
    # a sú len konfiguračnými dátami.
    return {
        "SystemAdmin": [
            "admin.system_config"
        ]
    }