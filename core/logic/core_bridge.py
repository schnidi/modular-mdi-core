# Súbor: core/logic/core_bridge.py

import os
import inspect
import threading
from pathlib import Path
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QLineEdit

from core._path import Paths
from core.enum_core import ICoreBridge
from core.logic.language_manager import LanguageManager
from core.logic.services.config_manager import ConfigManager
from core.logic.plugin.service_manager import ServiceManager
from core.windows.custom_message_box import CustomMessageBox


class CoreBridge(ICoreBridge):
    """
    Konkrétna implementácia komunikačného mosta ICoreBridge v jadre.
    Automaticky dopĺňa menný priestor volajúceho modulu pre bezkolízny prístup k prekladom.
    """
    _instance = None
    _lock = threading.Lock()

    run_on_gui_thread = pyqtSignal(object)

    @classmethod
    def get_instance(cls) -> "CoreBridge":
        with cls._lock:
            if cls._instance is None:
                cls._instance = CoreBridge()
            return cls._instance

    def __init__(self):
        super().__init__()
        # Registrácia inštancie pre abstraktné rozhranie v enum_core
        ICoreBridge._instance = self

        LanguageManager.connect_language_changed(self._on_internal_language_changed)
        self.run_on_gui_thread.connect(self._execute_on_gui_thread)

    def _on_internal_language_changed(self, lang_code: str):
        self.language_changed.emit(lang_code)

    def _execute_on_gui_thread(self, callback):
        callback()

    # =========================================================================
    # DETEKCIA VOLAJÚCEHO MODULU CEZ STACK TRACE
    # =========================================================================

    def _detect_calling_module(self) -> str | None:
        """
        Deterministicky zistí názov modulu, ktorý volá most,
        porovnaním cesty súboru voči registrovaným priečinkom modulov.
        """
        try:
            from core.logic.translate.services.module_translation_service import ModuleTranslationService
            mts = ModuleTranslationService.get_instance()

            stack = inspect.stack()
            for frame_info in stack[2:]:
                filepath = frame_info.filename.replace("\\", "/")
                with mts._lock:
                    for mod_name, trans_path in mts._registered_dirs.items():
                        mod_root = str(trans_path.parent).replace("\\", "/")
                        if mod_root in filepath:
                            return mod_name
        except Exception:
            pass
        return None

    # =========================================================================
    # JAZYK A PREKLADY S MENNÝMI PRIESTORMI
    # =========================================================================

    def set_language(self, lang_code: str) -> bool:
        return LanguageManager.load_language(lang_code)

    def get_current_language(self) -> str:
        return LanguageManager.get_current_language()

    def get_available_languages(self) -> list[str]:
        return LanguageManager.get_available_languages()

    def get_text(self, key: str, default: str = None, module_name: str = None) -> str:
        """
        Vráti preklad textu podľa kľúča.
        Automaticky vyhľadá '<volajúci_modul>.<key>'.
        """
        mod_id = module_name or self._detect_calling_module()
        return LanguageManager.get(key, default=default, module_id=mod_id)

    def translate_widget(self, widget: QWidget, module_name: str = None) -> None:
        """
        Automaticky preloží podradené prvky widgetu s menným priestorom modulu.
        """
        mod_id = module_name or widget.property("module_name") or self._detect_calling_module()
        if mod_id and not widget.property("module_name"):
            widget.setProperty("module_name", mod_id)
        LanguageManager.translate_ui(widget, module_id=mod_id)

    def connect_language_changed(self, slot) -> None:
        self.language_changed.connect(slot)

    def disconnect_language_changed(self, slot) -> None:
        try:
            self.language_changed.disconnect(slot)
        except (TypeError, RuntimeError):
            pass

    def register_module_translations(self, module_info: dict) -> bool:
        return LanguageManager.register_module_translations(module_info)

    # =========================================================================
    # KONFIGURÁCIE MODULOV
    # =========================================================================

    def get_module_config_dir(self, module_name: str) -> str:
        config_dir = os.path.join(Paths.get_config_dir(), "plugins", module_name)
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    def _get_module_config_file(self, module_name: str) -> str:
        return os.path.join(self.get_module_config_dir(module_name), "settings.ini")

    def save_module_setting(self, module_name: str, section: str, key: str, value: str) -> None:
        cfg_file = self._get_module_config_file(module_name)
        cfg = ConfigManager(cfg_file)
        cfg.set_value(section, key, value)
        cfg.save()

    def load_module_setting(self, module_name: str, section: str, key: str, default: str = None) -> str:
        cfg_file = self._get_module_config_file(module_name)
        if not os.path.exists(cfg_file):
            return default
        cfg = ConfigManager(cfg_file)
        return cfg.get_value(section, key, default=default)

    # =========================================================================
    # DIALÓGY V TÉME APLIKÁCIE
    # =========================================================================

    def show_info(self, title: str, text: str, parent: QWidget = None) -> None:
        CustomMessageBox.information(parent, title, text)

    def show_warning(self, title: str, text: str, parent: QWidget = None) -> None:
        CustomMessageBox.warning(parent, title, text)

    def show_error(self, title: str, text: str, details: str = None, parent: QWidget = None) -> None:
        CustomMessageBox.critical(parent, title, text, detailed_text=details)

    def ask_question(self, title: str, text: str, parent: QWidget = None) -> bool:
        return CustomMessageBox.question(parent, title, text)

    def get_text_input(self, title: str, text: str, is_password: bool = False, parent: QWidget = None) -> tuple[str, bool]:
        echo = QLineEdit.EchoMode.Password if is_password else QLineEdit.EchoMode.Normal
        return CustomMessageBox.get_text(parent, title, text, echo=echo)

    def show_dialog(self, content_widget: QWidget, title: str = "", parent: QWidget = None) -> int:
        return CustomMessageBox.show_dialog(content_widget, title=title, parent=parent)

    # =========================================================================
    # SLUŽBY (IoC PRE MODULY)
    # =========================================================================

    def get_service(self, service_name: str) -> object:
        return ServiceManager.get_instance().get_service(service_name)

    def on_service_ready(self, service_name: str, callback) -> None:
        ServiceManager.get_instance().on_service_ready(service_name, callback)