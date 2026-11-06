# Súbor: modules/system/system_language/module_interface.py

def _build_dynamic_paths(info: dict) -> dict:
    try:
        path_parts = ["modules"]
        prefix = info.get("install_path_prefix", "")
        if prefix:
            path_parts.append(prefix.replace('\\', '/').replace('/', '.'))
        path_parts.append(info["module_name"])
        base_path = ".".join(path_parts)

        info["widget_factory_path"] = f"{base_path}.logic.create_widget"
        info["bootstrap_function_path"] = f"{base_path}.logic.bootstrap"
        # ZMENA: doplnená cesta k _paths.py modulu, aby bridge.register_module_translations()
        # (cez LanguageManager -> ModuleTranslationService) vedel nájsť TRANSLATIONS_DIR.
        info["paths_module_path"] = f"{base_path}._paths"
        return info
    except Exception as e:
        print(f"[system_language] Chyba dynamického skladania ciest: {e}")
        return info


def get_module_info():
    """Hlavná registrácia modulu pre jadro."""
    base_info = {
        "module_type": "system",
        "module_name": "system_language",
        "install_path_prefix": "system",
        "window_key": "LanguageSettingsWindow",
        "control_panel_entry": {
            "display_name": "Nastavenie Jazyka",
            "icon_path": "ui/resources/icons/language_icon.svg",
            "action_id": "system_language.open_settings" 
        },
        "menu_structure": {
            "Nastavenie": [
                {
                    "text": "Jazyk...",
                    "id": "system_language.open_settings"
                }
            ]
        }
    }
    return _build_dynamic_paths(base_info)


def get_provided_services():
    return []
