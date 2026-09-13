"""
Súbor: core/logic/services/config_manager.py
Bezpečný manažér .ini súborov s automatickou podporou pre Enumy.
"""

import configparser
from pathlib import Path


class ConfigManager:
    """Spravuje .ini súbory s automatickým ošetrením Enumov a stringov."""
    def __init__(self, filename: str | Path):
        self.path = Path(filename)
        self.config = configparser.ConfigParser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                self.config.read(self.path, encoding='utf-8')
            except Exception as e:
                print(f"[ConfigManager] Varovanie pri čítaní {self.path}: {e}")

    def _normalize(self, val):
        """Vytiahne čistú hodnotu, aj keď je to Enum."""
        if hasattr(val, 'value'):
            return str(val.value)
        return str(val)

    def save(self):
        with self.path.open("w", encoding='utf-8') as f: 
            self.config.write(f)

    def get_value(self, section, key, default=None):
        sec = self._normalize(section)
        k = self._normalize(key)
        return self.config.get(sec, k, fallback=default)

    def set_value(self, section, key, value):
        sec = self._normalize(section)
        k = self._normalize(key)
        val = self._normalize(value)

        if not self.config.has_section(sec): 
            self.config.add_section(sec)
        self.config.set(sec, k, val)
    
    def remove_section(self, section_name: str):
        sec = self._normalize(section_name)
        if self.config.has_section(sec):
            self.config.remove_section(sec)