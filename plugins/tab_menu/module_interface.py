# Súbor: modules/tab_menu/module_interface.py


def _build_dynamic_paths(info: dict) -> dict:
    try:
        path_parts = ["modules"]
        prefix = info.get("install_path_prefix", "")

        if prefix:
            path_parts.append(prefix.replace('\\', '/').replace('/', '.'))

        name = info.get("name") or info.get("module_name", "tab_menu")
        path_parts.append(name)
        base_path = ".".join(path_parts)

        if info.get("widget_factory_path"):
            info["widget_factory_path"] = info["widget_factory_path"].format(base_path=base_path)

        if info.get("bootstrap_function_path"):
            info["bootstrap_function_path"] = info["bootstrap_function_path"].format(base_path=base_path)

        # >>> ZMENA: Formátovanie cesty pre paths_module_path
        if info.get("paths_module_path"):
            info["paths_module_path"] = info["paths_module_path"].format(base_path=base_path)
        # <<< KONIEC ZMENY

        menu_struct = info.get("menu_structure", {})
        for category, items in menu_struct.items():
            for item in items:
                if item.get("handler_path"):
                    item["handler_path"] = item["handler_path"].format(base_path=base_path)

        return info
    except Exception as e:
        print(f"[TabMenu] CHYBA v _build_dynamic_paths: {e}")
        return info


def get_module_info():
    base_info = {
        "name": "tab_menu",
        "module_name": "tab_menu",
        "version": "1.0.0",
        "description": "Záložková lišta pre MDI okná",
        "author": "VenvHub Developer",
        "dependencies": [],
        "install_path_prefix": "",
        "window_key": "TabMenuWindow",
        "module_type": "core_extension",
        "requires_main_controller": True,
        "bootstrap_function_path": "{base_path}.main_logic.bootstrap_tab_menu",
        
        # >>> ZMENA: Pridanie paths_module_path, aby jadro automaticky prevzalo správu prekladov
        "paths_module_path": "{base_path}._paths",
        # <<< KONIEC ZMENY
        
        "menu_structure": {
            "Okno": [
                {
                    "text": "Záložková lišta okien (Zobraziť/Skryť)",
                    "id": "tab_menu.toggle",
                    "handler_path": "{base_path}.main_logic.toggle_tab_menu"
                }
            ]
        }
    }
    return _build_dynamic_paths(base_info)


def get_provided_services():
    return [
        {
            "service_type": "core_service",
            "provider_info": {
                "service_name": "tab_menu_service",
                "service_instance_path": "modules.tab_menu.main_logic.TabMenuService.get_instance"
            }
        }
    ]