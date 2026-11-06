"""
Súbor: core/logic/translate/services/module_translation_service.py
Centrálna služba pre deterministickú registráciu a zlučovanie prekladov modulov.
Spravuje zoznam aktívnych modulov a ich TRANSLATIONS_DIR získaný striktne z _paths.py.
"""

import json
import importlib
import threading
from pathlib import Path
from typing import Dict, Set, Optional


class ModuleTranslationService:
    """
    Spravuje registráciu ciest k prekladom modulov a ich bezpečné zlučovanie (Merge)
    s centrálnym slovníkom jadra.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "ModuleTranslationService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = ModuleTranslationService()
            return cls._instance

    def __init__(self):
        # Mapa: {module_name: Path k TRANSLATIONS_DIR}
        self._registered_dirs: Dict[str, Path] = {}

    # =========================================================================
    # 1. REGISTRÁCIA A ODREGISTROVANIE MODULOV
    # =========================================================================

    def register_module_from_info(self, module_info: dict) -> bool:
        """
        Vytiahne 'paths_module_path' z metadát modulu, deterministicky importuje
        jeho _paths.py a zaregistruje konštantu TRANSLATIONS_DIR.
        """
        if not isinstance(module_info, dict):
            return False

        module_name = module_info.get("name") or module_info.get("module_name")
        paths_import_path = module_info.get("paths_module_path")

        if not module_name:
            print("[ModuleTranslationService] VAROVANIE: Chýba názov modulu pri registrácii prekladov.")
            return False

        if not paths_import_path:
            # Ak modul nedeklaruje paths_module_path, nemá preklady alebo nesplnil kontrakt
            return False

        try:
            # 1. Dynamický import _paths.py modulu
            paths_module = importlib.import_module(paths_import_path)

            # 2. Striktná kontrola povinnej konštanty TRANSLATIONS_DIR
            if not hasattr(paths_module, "TRANSLATIONS_DIR"):
                print(f"[ModuleTranslationService] CHYBA: Modul '{module_name}' v '{paths_import_path}' "
                      f"nemá povinnú konštantu 'TRANSLATIONS_DIR'!")
                return False

            raw_trans_dir = getattr(paths_module, "TRANSLATIONS_DIR")
            trans_dir = Path(raw_trans_dir).resolve()

            if not trans_dir.exists() or not trans_dir.is_dir():
                print(f"[ModuleTranslationService] VAROVANIE: Priečinok prekladov modulu '{module_name}' "
                      f"neexistuje na ceste: {trans_dir}")
                return False

            with self._lock:
                self._registered_dirs[module_name] = trans_dir

            print(f"[ModuleTranslationService] Zaregistrované preklady pre modul '{module_name}' -> {trans_dir}")
            return True

        except Exception as e:
            print(f"[ModuleTranslationService] CHYBA pri načítaní _paths pre modul '{module_name}' ({paths_import_path}): {e}")
            return False

    def unregister_module(self, module_name: str) -> None:
        """Odstráni preklady modulu z registra pri jeho deaktivácii."""
        with self._lock:
            if module_name in self._registered_dirs:
                del self._registered_dirs[module_name]
                print(f"[ModuleTranslationService] Odregistrované preklady pre modul '{module_name}'.")

    def clear(self) -> None:
        """Vyčistí všetky registrované cesty modulov."""
        with self._lock:
            self._registered_dirs.clear()

    # =========================================================================
    # 2. ZLUČOVANIE PREKLADOV (MERGE ENGINE)
    # =========================================================================

    def merge_module_translations(self, lang_code: str, base_dictionary: dict) -> dict:
        """
        Prejde všetky registrované priečinky modulov, nájde príslušný JSON súbor
        pre daný jazyk a spojí kľúče do jedného spoločného slovníka.
        """
        merged_data = dict(base_dictionary)

        with self._lock:
            registered_items = list(self._registered_dirs.items())

        for module_name, trans_dir in registered_items:
            mod_data = self._load_json_for_language(trans_dir, lang_code)
            if mod_data:
                # Zlúčenie kľúčov do slovníka
                merged_data.update(mod_data)

        return merged_data

    def _load_json_for_language(self, trans_dir: Path, lang_code: str) -> Optional[dict]:
        """
        Nájde a načíta JSON súbor pre daný jazyk s fallbackom (napr. sk_SK -> sk -> en_US).
        """
        # Kandidáti na vyhľadanie súboru
        short_code = lang_code.split('_')[0] if '_' in lang_code else lang_code
        candidates = [
            trans_dir / f"{lang_code}.json",
            trans_dir / f"{short_code}.json",
            trans_dir / "sk_SK.json",
            trans_dir / "en_US.json"
        ]

        target_file = next((f for f in candidates if f.exists() and f.is_file()), None)
        if not target_file:
            return None

        try:
            with open(target_file, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ModuleTranslationService] CHYBA pri čítaní súboru {target_file}: {e}")
            return None

    # =========================================================================
    # 3. ZISTENIE DOSTUPNÝCH JAZYKOV V SYSTÉME
    # =========================================================================

    def get_all_available_languages(self, core_translations_dir: Path) -> list[str]:
        """
        Zozbiera všetky unikátne jazykové kódy zo slovníkov jadra a všetkých modulov.
        """
        available_codes: Set[str] = set()

        # 1. Jazyky z jadra
        if core_translations_dir.exists() and core_translations_dir.is_dir():
            for file in core_translations_dir.glob("*.json"):
                available_codes.add(file.stem)

        # 2. Jazyky z registrovaných modulov
        with self._lock:
            all_dirs = list(self._registered_dirs.values())

        for trans_dir in all_dirs:
            if trans_dir.exists() and trans_dir.is_dir():
                for file in trans_dir.glob("*.json"):
                    available_codes.add(file.stem)

        return sorted(list(available_codes)) if available_codes else ["sk_SK", "en_US"]