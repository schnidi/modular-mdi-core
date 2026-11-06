# Súbor: core/logic/language_manager.py

import os
import json
import locale
import threading
from pathlib import Path
from PyQt6.QtWidgets import QWidget

from core._path import Paths
from core.logic.resource_manager import ResourceManager
from core.enum_core import ILanguageService
from core.logic.translate.services.module_translation_service import ModuleTranslationService
from core.logic.translate.services.translation_registry import TranslationRegistry


class LanguageManager(ILanguageService):
    """
    Implementácia predpisu ILanguageService s podporou menných priestorov modulov
    a striktnou ochranou systémových prvkov jadra.
    """
    _instance = None
    _lock = threading.Lock()

    _current_data: dict = {}
    _current_lang_code: str = "sk_SK"

    # Systémové tlačidlá titulkových líšt okien, ktoré NIKDY nesmú dostať text z prekladača
    SYSTEM_TITLEBAR_BUTTONS = {
        "btn_close", "btn_minimize", "btn_maximize", 
        "btn_restore", "btn_about", "btn_update_github"
    }

    @classmethod
    def get_instance(cls) -> "LanguageManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = LanguageManager()
            return cls._instance

    def __init__(self):
        super().__init__()
        self.translation_service = ModuleTranslationService.get_instance()
        self.registry = TranslationRegistry.get_instance()

    # =========================================================================
    # REGISTRÁCIA PREKLADOV MODULOV
    # =========================================================================

    @classmethod
    def register_module_translations(cls, module_info: dict) -> bool:
        """
        Zaregistruje preklady modulu podľa jeho metadát (paths_module_path)
        a okamžite ich zlúči do RAM pod menným priestorom '<module_name>.<key>'.
        """
        instance = cls.get_instance()
        success = instance.translation_service.register_module_from_info(module_info)
        if success:
            module_name = module_info.get("name") or module_info.get("module_name")
            trans_dir = instance.translation_service._registered_dirs.get(module_name)
            if trans_dir:
                mod_data = instance.translation_service._load_json_for_language(
                    trans_dir, cls._current_lang_code
                )
                if mod_data:
                    instance.registry.store_module_translations(
                        module_name, cls._current_lang_code, mod_data
                    )
                    with cls._lock:
                        cls._current_data = instance.registry.get_merged_dictionary(cls._current_lang_code)
        return success

    @classmethod
    def unregister_module_translations(cls, module_name: str) -> None:
        """Odregistruje modul a vymaže jeho preklady z pamäte."""
        instance = cls.get_instance()
        instance.translation_service.unregister_module(module_name)
        instance.registry.unregister_module(module_name)
        with cls._lock:
            cls._current_data = instance.registry.get_merged_dictionary(cls._current_lang_code)

    # =========================================================================
    # NAČÍTANIE JAZYKA DO RAM
    # =========================================================================

    @classmethod
    def load_language(cls, lang_code: str = "auto") -> bool:
        if lang_code == "auto":
            try:
                sys_lang = locale.getdefaultlocale()[0]
                lang_code = sys_lang if sys_lang else "sk_SK"
            except Exception:
                lang_code = "sk_SK"

        instance = cls.get_instance()
        trans_dir = Paths.get_translations_dir()

        # 1. Načítanie slovníka jadra
        content = ResourceManager.read_resource_file(trans_dir, lang_code, ".json")
        if not content:
            short_code = lang_code.split('_')[0]
            content = ResourceManager.read_resource_file(trans_dir, short_code, ".json")
        if not content:
            content = ResourceManager.read_resource_file(trans_dir, "sk_SK", ".json")
        if not content:
            content = ResourceManager.read_resource_file(trans_dir, "en_US", ".json")

        core_data = {}
        if content:
            try:
                core_data = json.loads(content)
            except Exception as e:
                print(f"[LanguageManager] CHYBA JSON jadra: {e}")

        instance.registry.store_core_translations(lang_code, core_data)

        # 2. Načítanie všetkých aktívnych modulov do ich vlastných pamäťových segmentov
        with instance.translation_service._lock:
            registered_dirs = list(instance.translation_service._registered_dirs.items())

        for module_name, mod_trans_dir in registered_dirs:
            mod_data = instance.translation_service._load_json_for_language(mod_trans_dir, lang_code)
            if mod_data:
                instance.registry.store_module_translations(module_name, lang_code, mod_data)

        # 3. Zostavenie indexu
        merged_dictionary = instance.registry.get_merged_dictionary(lang_code)

        with cls._lock:
            cls._current_lang_code = lang_code
            cls._current_data = merged_dictionary

        instance.language_changed.emit(lang_code)
        return bool(merged_dictionary)

    # =========================================================================
    # ČÍTANIE PREKLADOV Z RAM
    # =========================================================================

    @classmethod
    def get(cls, key: str, default: str = None, module_id: str = None) -> str:
        """
        Vráti preklad textu podľa kľúča.
        Ak je zadaný module_id, prioritne hľadá '<module_id>.<key>'.
        """
        if not key:
            return default if default is not None else ""

        with cls._lock:
            val = None
            if module_id and not key.startswith(f"{module_id}."):
                val = cls._current_data.get(f"{module_id}.{key}")

            if val is None:
                val = cls._current_data.get(key)

        text = val if val is not None else (default if default is not None else key)
        if isinstance(text, str):
            text = text.replace("\\n", "\n")
        return text

    @classmethod
    def translate_ui(cls, widget: QWidget, module_id: str = None) -> None:
        """
        Automaticky preloží podradené prvky widgetu.
        Garantuje izoláciu menných priestorov a chráni systémové lišty okien.
        """
        if not widget:
            return

        instance = cls.get_instance()
        with cls._lock:
            data_copy = dict(cls._current_data)
            core_keys = set(instance.registry._core_keys)

        # 1. Preklad všetkých prvkov vo vnútri widgetu
        for child in widget.findChildren(QWidget):
            name = getattr(child, "objectName", lambda: "")()
            if not name or name.startswith("qt_"):
                continue

            # OCHRANA 1: Systémové tlačidlá na titulkových lištách okien nesmú dostať žiadny text
            parent_w = child.parentWidget()
            is_titlebar = parent_w and (
                parent_w.objectName() == "CustomTitleBar" 
                or "TitleBar" in parent_w.__class__.__name__
            )
            if is_titlebar and name in cls.SYSTEM_TITLEBAR_BUTTONS:
                continue

            # OCHRANA 2: Dynamické zistenie modulu pre tento konkrétny child prvok
            child_module = module_id
            if not child_module:
                child_module = child.property("module_name") or child.property("module_id")
                if not child_module:
                    curr = parent_w
                    while curr and curr != widget:
                        m = curr.property("module_name") or curr.property("module_id")
                        if m:
                            child_module = m
                            break
                        curr = curr.parentWidget()

            text = None
            if child_module:
                # Prvok patrí modulu: hľadáme primárne v namespace modulu
                text = data_copy.get(f"{child_module}.{name}")
                if text is None:
                    # Fallback na čistý kľúč len ak nepatrí do chránených kľúčov jadra
                    if name not in core_keys:
                        text = data_copy.get(name)
            else:
                # Prvok patrí jadru: smie použiť VÝHRADNE kľúče jadra
                if name in core_keys or f"core.{name}" in data_copy:
                    text = data_copy.get(f"core.{name}") or data_copy.get(name)

            if text:
                text_clean = text.replace("\\n", "\n")
                if hasattr(child, "setPlaceholderText"):
                    child.setPlaceholderText(text_clean)
                elif hasattr(child, "setText"):
                    child.setText(text_clean)
                elif hasattr(child, "setTitle"):
                    child.setTitle(text_clean)
                elif hasattr(child, "setToolTip"):
                    child.setToolTip(text_clean)

        # 2. Preklad samotného okna a jeho MDI lišty
        win_name = widget.objectName()
        target_mod = module_id or widget.property("module_name") or widget.property("module_id")
        
        new_title = None
        if target_mod:
            new_title = data_copy.get(f"{target_mod}.{win_name}")
        if not new_title and (not target_mod or win_name in core_keys):
            new_title = data_copy.get(win_name)

        if new_title:
            new_title_clean = new_title.replace("\\n", "\n")
            widget.setWindowTitle(new_title_clean)

            # Bezpečné nastavenie titulku len pre príslušný TitleBar pod-okna
            if hasattr(widget, "title_bar") and widget.title_bar and hasattr(widget.title_bar, "set_title"):
                widget.title_bar.set_title(new_title_clean)

            # Bublanie len po obalujúce MDI pod-okno (FramelessMdiSubWindow), nikdy nie do MainWindow/QMdiArea
            from PyQt6.QtWidgets import QMdiSubWindow, QMdiArea
            parent = widget.parentWidget()
            while parent:
                if isinstance(parent, QMdiSubWindow) or parent.__class__.__name__ == "FramelessMdiSubWindow":
                    if hasattr(parent, "title_bar") and parent.title_bar and hasattr(parent.title_bar, "set_title"):
                        parent.title_bar.set_title(new_title_clean)
                    parent.setWindowTitle(new_title_clean)
                    break
                # Ak sme narazili na plochu MDI alebo iné hlavné okno, okamžite STOP!
                if isinstance(parent, QMdiArea) or parent.isWindow():
                    break
                parent = parent.parentWidget()

    @classmethod
    def get_current_language(cls) -> str:
        with cls._lock:
            return cls._current_lang_code

    @classmethod
    def get_available_languages(cls) -> list[str]:
        instance = cls.get_instance()
        core_dir = Path(Paths.get_translations_dir())
        return instance.translation_service.get_all_available_languages(core_dir)

    @classmethod
    def connect_language_changed(cls, slot):
        instance = cls.get_instance()
        instance.language_changed.connect(slot)

    @classmethod
    def disconnect_language_changed(cls, slot):
        try:
            instance = cls.get_instance()
            instance.language_changed.disconnect(slot)
        except (TypeError, RuntimeError):
            pass