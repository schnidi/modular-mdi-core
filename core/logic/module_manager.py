# Súbor: core/logic/module_manager.py

import os
import importlib.util
from pathlib import Path 

from core._path import Paths
from core.logic.module_config import ModuleConfig


class ModuleManager:
    """Dynamicky objavuje, načítava a overuje moduly a ich závislosti."""

    def __init__(self, modules_dir=None):
        self.modules_path = Path(modules_dir if modules_dir else Paths.get_modules_dir())
        self.module_config = ModuleConfig()

    def get_active_modules_info(self) -> list:
        """Vráti informácie o všetkých povolených moduloch s overenými závislosťami."""
        self.module_config.reload()
        
        active_modules = []
        all_modules = self._discover_all_modules() 
        all_modules_map = {name: path for name, path in all_modules}
        
        for module_name, interface_file in all_modules:
            if self.module_config.is_module_enabled(module_name):
                info = self._load_module_info(module_name, interface_file)
                if not info:
                    continue

                # KONTROLA ZÁVISLOSTÍ: Sú všetky vyžadované moduly aktívne?
                deps = info.get("dependencies", [])
                missing_or_disabled = [
                    d for d in deps 
                    if not self.module_config.is_module_enabled(d)
                ]

                if missing_or_disabled:
                    print(f"[ModuleManager] VAROVANIE: Modul '{module_name}' sa nespustí! "
                          f"Chýbajúce/neaktívne závislosti: {missing_or_disabled}")
                    continue

                active_modules.append(info)

        return active_modules

    def get_module_dependencies(self, module_name: str) -> list[str]:
        """Vráti zoznam modulov, ktoré daný modul vyžaduje."""
        all_modules = dict(self._discover_all_modules())
        interface_file = all_modules.get(module_name)
        if interface_file:
            info = self._load_module_info(module_name, interface_file)
            if info:
                return info.get("dependencies", [])
        return []

    def get_dependents_of(self, target_module_name: str) -> list[str]:
        """Zistí, ktoré moduly závisia od daného modulu."""
        dependents = []
        all_modules = self._discover_all_modules()
        for mod_name, interface_file in all_modules:
            if mod_name == target_module_name:
                continue
            info = self._load_module_info(mod_name, interface_file)
            if info and target_module_name in info.get("dependencies", []):
                dependents.append(mod_name)
        return dependents

    def get_all_provided_groups(self) -> dict:
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
        self.module_config.reload()
        all_modules = self._discover_all_modules()
        status_dict = {}
        for module_name, _ in all_modules:
            status_dict[module_name] = self.module_config.is_module_enabled(module_name)
        return status_dict

    def _discover_all_modules(self) -> list:
        self.module_config.reload()
        found_modules = []
        
        for module_name in self.module_config.config.sections():
            module_path_str = self.module_config.get_module_path(module_name)
            
            if module_path_str:
                module_path = Path(module_path_str)
                if not module_path.is_absolute():
                    module_path = Path(Paths.get_root()) / module_path

                interface_file = module_path / "module_interface.py"
                
                if interface_file.exists():
                    found_modules.append((module_name, interface_file))
        
        return found_modules

    def _load_module_info(self, module_name: str, interface_file: Path) -> dict | None:
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