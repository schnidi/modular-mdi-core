# Súbor: modules/theme_setup/logic/theme_setup_controller.py (FINÁLNA VERZIA)

from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox
from pathlib import Path
import configparser
import shutil
import re

class ThemeSetupController:
    DEFAULT_THEMES_DIR = Path("app/resources/styles/themes")
    USER_THEMES_DIR = Path("config/user_themes")
    CONFIG_FILE = Path("config/theme_settings.ini")

    def __init__(self, view):
        self.view = view
        self.view.save_and_apply_theme_requested.connect(self.save_and_apply_theme)
        self.view.add_theme_requested.connect(self.add_theme)
        self.view.delete_theme_requested.connect(self.delete_theme)
        
        self.load_available_themes()

    def _parse_theme_metadata(self, file_path: Path) -> dict:
        metadata = {'ThemeName': file_path.name}
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
        self.DEFAULT_THEMES_DIR.mkdir(parents=True, exist_ok=True)
        self.USER_THEMES_DIR.mkdir(parents=True, exist_ok=True)
        
        themes_info = []
        processed_files = set()

        # Načítanie základných tém
        for f in self.DEFAULT_THEMES_DIR.glob("*.qss"):
            if f.name in processed_files: continue
            metadata = self._parse_theme_metadata(f)
            themes_info.append({
                'filename': f.name,
                'display_name': metadata['ThemeName'],
                'is_deletable': False  # Základné nie sú mazateľné
            })
            processed_files.add(f.name)
            
        # Načítanie používateľských tém
        for f in self.USER_THEMES_DIR.glob("*.qss"):
            if f.name in processed_files: continue
            metadata = self._parse_theme_metadata(f)
            themes_info.append({
                'filename': f.name,
                'display_name': metadata['ThemeName'],
                'is_deletable': True  # Používateľské sú mazateľné
            })
            processed_files.add(f.name)
        
        sorted_themes = sorted(themes_info, key=lambda x: x['display_name'])
        self.view.populate_themes_list(sorted_themes)

    def _apply_theme_logic(self, theme_filename: str):
        path_to_apply = self.USER_THEMES_DIR / theme_filename
        if not path_to_apply.exists():
            path_to_apply = self.DEFAULT_THEMES_DIR / theme_filename
        
        if not path_to_apply.exists():
            print(f"CHYBA: Súbor témy '{theme_filename}' nebol nájdený.")
            return False

        try:
            style_sheet = path_to_apply.read_text(encoding='utf-8')
            QApplication.instance().setStyleSheet(style_sheet)
            return True
        except Exception as e:
            print(f"CHYBA pri aplikovaní témy '{theme_filename}': {e}")
            return False

    def save_and_apply_theme(self, theme_filename: str):
        if self._apply_theme_logic(theme_filename):
            config = configparser.ConfigParser()
            config["Settings"] = {"active_theme": theme_filename}
            with self.CONFIG_FILE.open("w", encoding='utf-8') as f:
                config.write(f)
            print(f"INFO: Téma '{theme_filename}' bola uložená ako aktívna.")

    def add_theme(self):
        filepath, _ = QFileDialog.getOpenFileName(self.view, "Vyberte súbor s témou", "", "QSS (*.qss)")
        if not filepath: return
        
        source_path = Path(filepath)
        dest_path = self.USER_THEMES_DIR / source_path.name
        
        if dest_path.exists():
             if QMessageBox.question(self.view, "Súbor existuje", f"Téma '{source_path.name}' už existuje. Prepísať?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
                 return

        try:
            shutil.copy(source_path, dest_path)
            self.load_available_themes()
        except Exception as e:
            QMessageBox.critical(self.view, "Chyba", f"Nepodarilo sa skopírovať súbor:\n{e}")

    def delete_theme(self, theme_filename: str, is_deletable: bool):
        if not is_deletable:
            QMessageBox.warning(self.view, "Operácia zamietnutá", "Základné témy nie je možné zmazať.")
            return
            
        if QMessageBox.question(self.view, "Potvrdenie", f"Naozaj zmazať tému '{theme_filename}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            try:
                (self.USER_THEMES_DIR / theme_filename).unlink()
                self.load_available_themes()
            except Exception as e:
                QMessageBox.critical(self.view, "Chyba", f"Nepodarilo sa zmazať súbor:\n{e}")