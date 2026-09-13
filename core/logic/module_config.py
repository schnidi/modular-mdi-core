# Súbor: core/logic/module_config.py

import configparser
from pathlib import Path
from core._path import Paths
from core.enum_core import ConfigKey


class ModuleConfig:
    """Spravuje LEN súbor modules.ini, vrátane cesty k modulu."""
    def __init__(self, file_path=None):
        self.path = Path(file_path if file_path else Paths.get_modules_ini())
        self.config = configparser.ConfigParser()
        self.reload() 

    def reload(self):
        """Zahodí staré dáta a načíta aktuálny stav zo súboru .ini."""
        self.config = configparser.ConfigParser() 
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.config.read(self.path, encoding='utf-8')

    def save(self):
        with self.path.open("w", encoding='utf-8') as f:
            self.config.write(f)
            
    def get_module_path(self, module_name: str) -> str | None:
        """Vráti uloženú plnú cestu k modulu."""
        return self.config.get(module_name, ConfigKey.PATH, fallback=None)

    def set_module_path(self, module_name: str, path: Path | str):
        """Uloží plnú cestu k modulu."""
        if not self.config.has_section(module_name):
            self.config.add_section(module_name)
        self.config.set(module_name, ConfigKey.PATH, str(path))

    def is_module_enabled(self, module_name: str) -> bool:
        return self.config.getboolean(module_name, ConfigKey.ENABLED, fallback=False)

    def set_module_enabled(self, module_name: str, enabled: bool):
        if not self.config.has_section(module_name):
            self.config.add_section(module_name)
        self.config.set(module_name, ConfigKey.ENABLED, str(enabled))

    def remove_module(self, module_name: str):
        if self.config.has_section(module_name):
            self.config.remove_section(module_name)