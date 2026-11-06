"""
Súbor: core/logic/translate/services/translation_registry.py
Centrálny register a strážca menných priestorov (Namespace Guard) pre preklady.
Zabezpečuje izoláciu slovníkov podľa ID modulu v tvare <module_id>.<key>.
"""

import threading
from typing import Dict, Optional, Set


class TranslationRegistry:
    """
    Spravuje viacúrovňové úložisko prekladov v RAM:
    _storage = {
        "CORE": {"sk_SK": {...}, "en_US": {...}},
        "standard_auth": {"sk_SK": {...}, "en_US": {...}},
        "db_connector": {"sk_SK": {...}, "en_US": {...}}
    }
    """
    _instance = None
    _lock = threading.Lock()

    CORE_MODULE_ID = "CORE"

    @classmethod
    def get_instance(cls) -> "TranslationRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = TranslationRegistry()
            return cls._instance

    def __init__(self):
        # Štruktúra: {module_id: {lang_code: {key: value}}}
        self._storage: Dict[str, Dict[str, Dict[str, str]]] = {
            self.CORE_MODULE_ID: {}
        }
        self._core_keys: Set[str] = set()
        self._flattened_cache: Dict[str, Dict[str, str]] = {}

    # =========================================================================
    # 1. ZÁPIS PREKLADOV DO RAM
    # =========================================================================

    def store_core_translations(self, lang_code: str, data: Dict[str, str]) -> None:
        """Uloží preklady jadra a označí ich kľúče ako systémové."""
        with self._lock:
            if self.CORE_MODULE_ID not in self._storage:
                self._storage[self.CORE_MODULE_ID] = {}

            self._storage[self.CORE_MODULE_ID][lang_code] = dict(data)
            self._core_keys.update(data.keys())
            self._invalidate_cache(lang_code)

    def store_module_translations(self, module_id: str, lang_code: str, data: Dict[str, str]) -> None:
        """
        Uloží preklady modulu. Každý kľúč modulu je v pamäti striktne
        uložený pod jeho menným priestorom '<module_id>.<key>'.
        """
        if not module_id or module_id == self.CORE_MODULE_ID:
            return

        with self._lock:
            if module_id not in self._storage:
                self._storage[module_id] = {}

            safe_data: Dict[str, str] = {}
            prefix = f"{module_id}."

            for raw_key, raw_val in data.items():
                clean_key = str(raw_key).strip()
                clean_val = str(raw_val)

                # Zabránenie prepísaniu chránených systémových kľúčov jadra
                if clean_key in self._core_keys and not clean_key.startswith(prefix):
                    clean_key = f"{prefix}{clean_key}"

                safe_data[clean_key] = clean_val
                # Garantujeme existenciu kľúča s menným priestorom modulu
                if not clean_key.startswith(prefix):
                    safe_data[f"{prefix}{clean_key}"] = clean_val

            self._storage[module_id][lang_code] = safe_data
            self._invalidate_cache(lang_code)

    def unregister_module(self, module_id: str) -> None:
        """Vymaže pamäťový segment konkrétneho modulu pri jeho deaktivácii."""
        with self._lock:
            if module_id in self._storage and module_id != self.CORE_MODULE_ID:
                del self._storage[module_id]
                self._flattened_cache.clear()

    def clear_all_modules(self) -> None:
        """Vymaže všetky moduly z pamäte, jadro ponechá."""
        with self._lock:
            core_backup = self._storage.get(self.CORE_MODULE_ID, {})
            self._storage = {self.CORE_MODULE_ID: core_backup}
            self._flattened_cache.clear()

    # =========================================================================
    # 2. ZLUČOVANIE DO CACHE PRE RÝCHLE ČÍTANIE O(1)
    # =========================================================================

    def _invalidate_cache(self, lang_code: str = None) -> None:
        if lang_code:
            self._flattened_cache.pop(lang_code, None)
        else:
            self._flattened_cache.clear()

    def get_merged_dictionary(self, lang_code: str) -> Dict[str, str]:
        """
        Vytvorí kompletný index pre daný jazyk:
        1. Kľúče jadra: 'key' aj 'core.key'
        2. Kľúče modulov: '<module_id>.<key>' (izolované, bez možnosti kolízie)
        3. Voľné nekonfliktné kľúče bez prefixu ako pohodlný fallback.
        """
        with self._lock:
            if lang_code in self._flattened_cache:
                return dict(self._flattened_cache[lang_code])

            merged: Dict[str, str] = {}
            claimed_unprefixed: Dict[str, str] = {}

            # Krok 1: Jadro má absolútnu prednosť pre kľúče bez prefixu
            core_dict = self._storage.get(self.CORE_MODULE_ID, {}).get(lang_code, {})
            for k, v in core_dict.items():
                merged[k] = v
                merged[f"core.{k}"] = v
                claimed_unprefixed[k] = self.CORE_MODULE_ID

            # Krok 2: Vloženie kľúčov jednotlivých modulov
            for mod_id, lang_map in self._storage.items():
                if mod_id == self.CORE_MODULE_ID:
                    continue

                mod_dict = lang_map.get(lang_code, {})
                mod_prefix = f"{mod_id}."

                for k, v in mod_dict.items():
                    # Primárne uloženie: VŽDY s menným priestorom modulu
                    namespaced_key = k if k.startswith(mod_prefix) else f"{mod_prefix}{k}"
                    merged[namespaced_key] = v

                    # Sekundárne uloženie: čistý kľúč bez prefixu (ak ho neobsadilo jadro ani iný modul)
                    raw_key = k[len(mod_prefix):] if k.startswith(mod_prefix) else k
                    if raw_key not in claimed_unprefixed:
                        merged[raw_key] = v
                        claimed_unprefixed[raw_key] = mod_id

            self._flattened_cache[lang_code] = dict(merged)
            return merged

    def get_text(self, lang_code: str, key: str, default: Optional[str] = None, module_id: Optional[str] = None) -> str:
        """Vyhľadanie prekladu podľa jazyka, kľúča a voliteľného ID modulu."""
        merged = self.get_merged_dictionary(lang_code)

        if module_id and not key.startswith(f"{module_id}."):
            val = merged.get(f"{module_id}.{key}")
            if val is not None:
                return val

        val = merged.get(key)
        if val is not None:
            return val

        return default if default is not None else key