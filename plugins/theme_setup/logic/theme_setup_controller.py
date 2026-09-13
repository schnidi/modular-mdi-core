# Súbor: modules/theme_setup/logic/theme_setup_controller.py

from pathlib import Path
import shutil
import re

from PyQt6.QtWidgets import QApplication

# Používame len služby a veci, ktoré reálne v jadre máš
from core.logic.plugin.service_manager import ServiceManager
from core.logic.language_manager import LanguageManager
from core.logic.skin_manager import SkinManager
from core.logic.services.config_manager import ConfigManager
from core._path import Paths
from core.enum_core import ConfigSection, ConfigKey

_ = LanguageManager.get


class ThemeSetupController:
    def __init__(self, view, service_manager=None):
        self.view = view
        self.service_manager = service_manager or ServiceManager.get_instance()
        
        # Dialógy berieme z jadra, aby prevzali štýl aplikácie
        self.dialog_service = self.service_manager.get_service("dialog_service")
        
        # Cesty k témam
        self.default_themes_dir = Path(Paths.get_themes_dir())
        self.user_themes_dir = Path(Paths.get_user_themes_dir())
        self.config_manager = ConfigManager(Path(Paths.get_config_dir()) / "theme_settings.ini")

        # Signály z UI
        self.view.save_and_apply_theme_requested.connect(self.save_and_apply_theme)
        self.view.add_theme_requested.connect(self.add_theme)
        self.view.delete_theme_requested.connect(self.delete_theme)
        
        self.load_available_themes()

    def _parse_theme_metadata(self, file_path: Path) -> dict:
        metadata = {'ThemeName': file_path.stem}
        try:
            with file_path.open('r', encoding='utf-8') as f:
                header = "".join([next(f) for _ in range(10)])
            name_match = re.search(r"@ThemeName:\s*(.*)", header)
            if name_match:
                metadata['ThemeName'] = name_match.group(1).strip()
        except Exception:
            pass
        return metadata

    def load_available_themes(self):
        self.default_themes_dir.mkdir(parents=True, exist_ok=True)
        self.user_themes_dir.mkdir(parents=True, exist_ok=True)
        
        themes_info = []
        processed_files = set()

        # 1. Základné témy
        for f in self.default_themes_dir.glob("*.qss"):
            if f.name in processed_files: 
                continue
            metadata = self._parse_theme_metadata(f)
            themes_info.append({
                'filename': f.name,
                'display_name': metadata['ThemeName'],
                'is_deletable': False
            })
            processed_files.add(f.name)
            
        # 2. Užívateľské témy
        for f in self.user_themes_dir.glob("*.qss"):
            if f.name in processed_files: 
                continue
            metadata = self._parse_theme_metadata(f)
            themes_info.append({
                'filename': f.name,
                'display_name': metadata['ThemeName'],
                'is_deletable': True
            })
            processed_files.add(f.name)
        
        sorted_themes = sorted(themes_info, key=lambda x: x['display_name'].lower())
        self.view.populate_themes_list(sorted_themes)

    def _apply_theme_logic(self, theme_filename: str) -> bool:
        skin_name = Path(theme_filename).stem
        user_theme_path = self.user_themes_dir / theme_filename

        # Užívateľská téma: modul sám spracuje cesty a nastaví štýl
        if user_theme_path.exists():
            try:
                raw_content = user_theme_path.read_text(encoding='utf-8')
                processed_content = Paths.process_qss_paths(raw_content)
                QApplication.instance().setStyleSheet(processed_content)
                return True
            except Exception as e:
                if self.dialog_service:
                    self.dialog_service.critical(self.view, _("Chyba"), f"Chyba pri aplikovaní témy: {e}")
                return False

        # Základná systémová téma: voláme SkinManager
        return SkinManager.apply_skin(skin_name)

    def save_and_apply_theme(self, theme_filename: str):
        if self._apply_theme_logic(theme_filename):
            self.config_manager.set_value(
                ConfigSection.SETTINGS, 
                ConfigKey.ACTIVE_THEME, 
                Path(theme_filename).stem
            )
            self.config_manager.save()

    def add_theme(self):
        # Ak vie dialog_service otvoriť výber súboru, použije sa, inak fallback
        if self.dialog_service and hasattr(self.dialog_service, "get_open_file_name"):
            filepath = self.dialog_service.get_open_file_name(self.view, _("Vyberte súbor s témou"), "", "QSS (*.qss)")
        else:
            from PyQt6.QtWidgets import QFileDialog
            filepath, _ = QFileDialog.getOpenFileName(self.view, _("Vyberte súbor s témou"), "", "QSS (*.qss)")

        if not filepath: 
            return
        
        source_path = Path(filepath)
        dest_path = self.user_themes_dir / source_path.name
        
        if dest_path.exists():
            question_text = _("Téma '{name}' už existuje. Prepísať?").format(name=source_path.name)
            if self.dialog_service:
                if not self.dialog_service.question(self.view, _("Súbor existuje"), question_text):
                    return

        try:
            shutil.copy(source_path, dest_path)
            self.load_available_themes()
            if self.dialog_service:
                self.dialog_service.information(self.view, _("Úspech"), _("Téma bola úspešne pridaná."))
        except Exception as e:
            if self.dialog_service:
                self.dialog_service.critical(self.view, _("Chyba"), f"Nepodarilo sa skopírovať súbor:\n{e}")

    def delete_theme(self, theme_filename: str, is_deletable: bool):
        if not is_deletable:
            if self.dialog_service:
                self.dialog_service.warning(self.view, _("Operácia zamietnutá"), _("Základné témy nie je možné zmazať."))
            return
            
        question_text = _("Naozaj zmazať tému '{name}'?").format(name=theme_filename)
        if self.dialog_service:
            if not self.dialog_service.question(self.view, _("Potvrdenie"), question_text):
                return

        try:
            (self.user_themes_dir / theme_filename).unlink()
            self.load_available_themes()
            if self.dialog_service:
                self.dialog_service.information(self.view, _("Úspech"), _("Téma bola úspešne zmazaná."))
        except Exception as e:
            if self.dialog_service:
                self.dialog_service.critical(self.view, _("Chyba"), f"Nepodarilo sa zmazať súbor:\n{e}")