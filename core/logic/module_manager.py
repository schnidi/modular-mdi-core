# Súbor: core/logic/module_manager.py

import os
import importlib.util
from pathlib import Path 

from core._path import Paths
from core.logic.module_config import ModuleConfig


class ModuleManager:
    """Dynamicky objavuje a načítava moduly z disku."""

    def __init__(self, modules_dir=None):
        self.modules_path = Path(modules_dir if modules_dir else Paths.get_modules_dir())
        self.module_config = ModuleConfig()

    def get_active_modules_info(self) -> list:
        """Vráti informácie o všetkých povolených (enabled) moduloch."""
        self.module_config.reload()
        
        active_modules = []
        all_modules = self._discover_all_modules() 
        
        for module_name, interface_file in all_modules:
            if self.module_config.is_module_enabled(module_name):
                info = self._load_module_info(module_name, interface_file)
                if info:
                    active_modules.append(info)
        return active_modules
    
    def get_all_provided_groups(self) -> dict:
        """
        Prejde všetky aktívne moduly a zozbiera ich definície skupín.
        Vracia: {module_name: {group_name: [perm1, perm2]}, ...}
        """
        self.module_config.reload()
        all_provided_groups = {}
        all_modules = self._discover_all_modules() 

        for module_name, interface_file in all_modules:
            info = self._load_module_info(module_name, interface_file)
            if info:
                groups = info.get("provided_groups", {})
                if groups:
                    all_provided_groups[module_name] = groups
                    
        return all_provided_groups

    def get_all_modules_status(self) -> dict:
        """Vráti slovník stavov všetkých modulov {module_name: True/False}."""
        self.module_config.reload()

        all_modules = self._discover_all_modules()
        status_dict = {}
        for module_name, _ in all_modules:
            status_dict[module_name] = self.module_config.is_module_enabled(module_name)
        return status_dict

    def _discover_all_modules(self) -> list:
        """Nájde všetky moduly registrované v modules.ini, ktoré majú fyzicky súbor module_interface.py."""
        self.module_config.reload()
        found_modules = []
        
        for module_name in self.module_config.config.sections():
            module_path_str = self.module_config.get_module_path(module_name)
            
            if module_path_str:
                module_path = Path(module_path_str)
                # Podpora relatívnych aj absolútnych ciest
                if not module_path.is_absolute():
                    module_path = Path(Paths.get_root()) / module_path

                interface_file = module_path / "module_interface.py"
                
                if interface_file.exists():
                    found_modules.append((module_name, interface_file))
        
        return found_modules

    def _load_module_info(self, module_name: str, interface_file: Path) -> dict | None:
        """Načíta informácie z get_module_info() a get_provided_services()."""
        try:
            temp_module_name = f"mod_info_{module_name}"
            spec = importlib.util.spec_from_file_location(temp_module_name, str(interface_file))
            if spec and spec.loader:
                module_interface = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module_interface)
                
                info = {}
                if hasattr(module_interface, "get_module_info"):
                    info = module_interface.get_module_info()

                if hasattr(module_interface, "get_provided_services"):
                    info["provided_services"] = module_interface.get_provided_services()
                    
                if hasattr(module_interface, "get_provided_groups"):
                    info["provided_groups"] = module_interface.get_provided_groups()
                
                return info if info else None

        except Exception as e:
            print(f"[ModuleManager] CHYBA pri načítaní modulu '{module_name}' z {interface_file}: {e}")
        return None