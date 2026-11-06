# Súbor: modules/theme_setup/module_interface.py

from core.enum_core import ModuleInfoKey


def _build_dynamic_paths(info: dict) -> dict:
    """Zostaví dynamickú základnú cestu podľa inštalačného prefixu a názvu modulu."""
    try:
        path_parts = ["modules"]
        prefix = info.get(ModuleInfoKey.INSTALL_PATH_PREFIX.value, "")
        if prefix:
            path_parts.append(prefix.replace('\\', '/').replace('/', '.'))
        path_parts.append(info.get(ModuleInfoKey.MODULE_NAME.value, "theme_setup"))
        base_path = ".".join(path_parts)

        path_keys_to_process = [
            ModuleInfoKey.PATHS_MODULE_PATH.value,
            ModuleInfoKey.WIDGET_FACTORY_PATH.value,
            ModuleInfoKey.BOOTSTRAP_FUNCTION_PATH.value
        ]

        for key in path_keys_to_process:
            if key in info and isinstance(info[key], str):
                info[key] = info[key].format(base_path=base_path)

        if "menu_structure" in info:
            for category, items in info["menu_structure"].items():
                for item in items:
                    if "handler_path" in item and "{base_path}" in item["handler_path"]:
                        item["handler_path"] = item["handler_path"].format(base_path=base_path)
                    if "widget_factory_path" in item and "{base_path}" in item["widget_factory_path"]:
                        item["widget_factory_path"] = item["widget_factory_path"].format(base_path=base_path)

        return info
    except Exception as e:
        print(f"[theme_setup] CHYBA dynamického skladania ciest: {e}")
        return info


def get_module_info():
    """Hlavná registrácia modulu pre jadro."""
    base_info = {
        ModuleInfoKey.NAME.value: "theme_setup",
        ModuleInfoKey.MODULE_NAME.value: "theme_setup",
        "version": "1.0.0",
        "description": "Správa vzhľadu a tém aplikácie",
        "author": "VenvHub Team",
        "module_type": "utility",
        ModuleInfoKey.INSTALL_PATH_PREFIX.value: "",
        ModuleInfoKey.WINDOW_KEY.value: "ThemeSetup",

        # Cesta k súboru s definíciami ciest
        ModuleInfoKey.PATHS_MODULE_PATH.value: "{base_path}._paths",

        # Vstupné body modulu
        ModuleInfoKey.BOOTSTRAP_FUNCTION_PATH.value: "{base_path}.main_logic.bootstrap",
        ModuleInfoKey.WIDGET_FACTORY_PATH.value: "{base_path}.main_logic.create_theme_setup_widget",

        # Závislosti (nemá žiadne)
        "dependencies": [],

        # Informácie pre ovládací panel
        "control_panel_entry": {
            "display_name": "Vzhľad a Témy",
            "icon_path": "resources/theme_icon.svg"
        },

        # Registrácia položky v menu jadra
        "menu_structure": {
            "Nastavenie": [
                {
                    "text": "Vzhľad a Témy...",
                    "id": "theme_setup.menu_title",
                    "window_key": "ThemeSetup",
                    "widget_factory_path": "{base_path}.main_logic.create_theme_setup_widget",
                    "requires_login": False
                }
            ]
        }
    }

    return _build_dynamic_paths(base_info)


def get_provided_groups():
    return {}


def get_provided_services():
    return []