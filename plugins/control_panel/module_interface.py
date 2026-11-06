# Súbor: modules/control_panel/module_interface.py

from pathlib import Path
from core.enum_core import ModuleInfoKey


def _get_dynamic_base_import_path() -> str:
    """Zistí koreňový importovací reťazec modulu (napr. 'modules.control_panel')."""
    try:
        module_dir = Path(__file__).parent.resolve()
        parts = module_dir.parts
        if "modules" in parts:
            modules_index = parts.index("modules")
            sub_parts = parts[modules_index:]
            return ".".join(sub_parts)
        else:
            return f"modules.{module_dir.name}"
    except Exception:
        return "modules.control_panel"


def _build_dynamic_paths(info: dict) -> dict:
    """Nahradí {base_path} v kľúčoch a položkách menu za skutočnú importovaciu cestu."""
    try:
        base_path = _get_dynamic_base_import_path()

        path_keys = [
            ModuleInfoKey.PATHS_MODULE_PATH.value,
            ModuleInfoKey.WIDGET_FACTORY_PATH.value,
            ModuleInfoKey.BOOTSTRAP_FUNCTION_PATH.value,
            ModuleInfoKey.SETUP_FUNCTION_PATH.value,
            ModuleInfoKey.AUTH_WIDGET_FACTORY_PATH.value,
        ]

        for key in path_keys:
            if key in info and isinstance(info[key], str):
                info[key] = info[key].format(base_path=base_path)

        if "menu_structure" in info and isinstance(info["menu_structure"], dict):
            for menu_items in info["menu_structure"].values():
                for item in menu_items:
                    if isinstance(item, dict):
                        if "widget_factory_path" in item and isinstance(item["widget_factory_path"], str):
                            item["widget_factory_path"] = item["widget_factory_path"].format(base_path=base_path)
                        if "handler_path" in item and isinstance(item["handler_path"], str):
                            item["handler_path"] = item["handler_path"].format(base_path=base_path)

        return info
    except Exception as e:
        print(f"[control_panel] CHYBA: Zlyhalo dynamické skladanie ciest: {e}")
        return info


def get_module_info() -> dict:
    """Hlavná registrácia a zmluva modulu voči jadru."""
    base_info = {
        ModuleInfoKey.NAME.value: "control_panel",
        ModuleInfoKey.MODULE_NAME.value: "control_panel",
        ModuleInfoKey.VERSION.value: "1.0.0",
        ModuleInfoKey.DESCRIPTION.value: "Centrálny ovládací panel",
        ModuleInfoKey.AUTHOR.value: "VenvHub Developer",
        "dependencies": [],
        ModuleInfoKey.INSTALL_PATH_PREFIX.value: "",
        ModuleInfoKey.WINDOW_KEY.value: "ControlPanel",

        # Cesta k _paths.py pre lokalizáciu
        ModuleInfoKey.PATHS_MODULE_PATH.value: "{base_path}._paths",

        # Vstupné body modulu
        ModuleInfoKey.BOOTSTRAP_FUNCTION_PATH.value: "{base_path}.main_logic.bootstrap",
        ModuleInfoKey.WIDGET_FACTORY_PATH.value: "{base_path}.main_logic.create_control_panel_widget",

        # Štruktúra položiek menu
        "menu_structure": {
            "Nastavenie": [
                {
                    "id": "control_panel.open",
                    "text": "Ovládací panel...",
                    "window_key": "ControlPanel",
                    "widget_factory_path": "{base_path}.main_logic.create_control_panel_widget",
                    "required_permission": None,
                    "requires_login": False,
                    "requires_logged_out": False,
                }
            ]
        },
    }
    return _build_dynamic_paths(base_info)


def get_provided_groups() -> dict:
    """Skupiny a oprávnenia, ktoré modul poskytuje do systému."""
    return {
        "Administrátor": [
            "admin.system_config",
            "perm_control_panel_edit_layout",
        ]
    }


def get_provided_services() -> list:
    return []