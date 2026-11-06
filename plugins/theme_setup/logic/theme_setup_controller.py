# Súbor: modules/theme_setup/logic/theme_setup_controller.py

import re
import shutil
import configparser
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QFileDialog

from core.enum_core import ICoreBridge
from .. import _paths


class ThemeSetupController:
    def __init__(self, view, bridge: ICoreBridge = None):
        self.view = view
        self.bridge = bridge or ICoreBridge.get_instance()

        # Cesty k témam aplikácie odvodené z umiestnenia modulu
        self.project_root = _paths.MODULE_ROOT.parent.parent
        self.core_dir = self.project_root / "core"
        self.default_themes_dir = self.core_dir / "themes" / "skin"
        self.user_themes_dir = self.core_dir / "themes" / "user"
        self.config_file = self.core_dir / "config" / "theme_settings.ini"

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

        # 1. Základné systémové témy
        if self.default_themes_dir.exists():
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
        if self.user_themes_dir.exists():
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

    def _process_qss_paths(self, qss_content: str) -> str:
        """Nahradí makrá @THEMES_DIR@, @ICON_DIR@ a @CORE_DIR@ priamymi lomkami pre Qt."""
        themes_dir = str(self.default_themes_dir).replace("\\", "/")
        icons_dir = str(self.core_dir / "themes" / "icon").replace("\\", "/")
        core_dir = str(self.core_dir).replace("\\", "/")

        qss_content = qss_content.replace("@THEMES_DIR@", themes_dir)
        qss_content = qss_content.replace("@ICON_DIR@", icons_dir)
        qss_content = qss_content.replace("@CORE_DIR@", core_dir)
        return qss_content

    def _apply_theme_logic(self, theme_filename: str) -> bool:
        user_path = self.user_themes_dir / theme_filename
        system_path = self.default_themes_dir / theme_filename
        target_path = user_path if user_path.exists() else system_path

        if not target_path.exists():
            msg = self.bridge.get_text("err_theme_not_found", "Súbor témy '{0}' nebol nájdený.").format(theme_filename)
            self.bridge.show_error(self.bridge.get_text("title_error", "Chyba"), msg, parent=self.view)
            return False

        try:
            raw_content = target_path.read_text(encoding='utf-8')
            processed_content = self._process_qss_paths(raw_content)
            QApplication.instance().setStyleSheet(processed_content)
            return True
        except Exception as e:
            msg = self.bridge.get_text("err_apply_theme_failed", "Chyba pri aplikovaní témy: {0}").format(e)
            self.bridge.show_error(self.bridge.get_text("title_error", "Chyba"), msg, parent=self.view)
            return False

    def save_and_apply_theme(self, theme_filename: str):
        if self._apply_theme_logic(theme_filename):
            skin_name = Path(theme_filename).stem
            try:
                config = configparser.ConfigParser()
                self.config_file.parent.mkdir(parents=True, exist_ok=True)
                if self.config_file.exists():
                    config.read(self.config_file, encoding='utf-8')

                if not config.has_section("Settings"):
                    config.add_section("Settings")
                config.set("Settings", "active_theme", skin_name)

                with open(self.config_file, "w", encoding='utf-8') as f:
                    config.write(f)

                msg = self.bridge.get_text("msg_theme_applied", "Téma '{0}' bola úspešne aplikovaná a uložená.").format(skin_name)
                self.bridge.show_info(self.bridge.get_text("title_success", "Úspech"), msg, parent=self.view)
            except Exception as e:
                msg = self.bridge.get_text("err_save_theme_failed", "Nepodarilo sa uložiť nastavenie témy: {0}").format(e)
                self.bridge.show_error(self.bridge.get_text("title_error", "Chyba"), msg, parent=self.view)

    def add_theme(self):
        title = self.bridge.get_text("dialog_select_theme", "Vyberte súbor s témou")
        filter_str = self.bridge.get_text("filter_qss", "QSS (*.qss)")
        filepath, _ = QFileDialog.getOpenFileName(self.view, title, "", filter_str)
        if not filepath:
            return

        source_path = Path(filepath)
        dest_path = self.user_themes_dir / source_path.name

        if dest_path.exists():
            confirm_msg = self.bridge.get_text(
                "msg_theme_overwrite_confirm",
                "Téma '{0}' už existuje. Chcete ju prepísať?"
            ).format(source_path.name)
            if not self.bridge.ask_question(self.bridge.get_text("title_confirm", "Potvrdenie"), confirm_msg, parent=self.view):
                return

        try:
            shutil.copy(source_path, dest_path)
            self.load_available_themes()
            msg = self.bridge.get_text("msg_theme_imported", "Téma '{0}' bola úspešne pridaná.").format(source_path.name)
            self.bridge.show_info(self.bridge.get_text("title_success", "Úspech"), msg, parent=self.view)
        except Exception as e:
            msg = self.bridge.get_text("err_theme_import_failed", "Nepodarilo sa skopírovať súbor: {0}").format(e)
            self.bridge.show_error(self.bridge.get_text("title_error", "Chyba"), msg, parent=self.view)

    def delete_theme(self, theme_filename: str, is_deletable: bool):
        if not is_deletable:
            msg = self.bridge.get_text("err_cannot_delete_default_theme", "Základné témy systému nie je možné zmazať.")
            self.bridge.show_warning(self.bridge.get_text("title_warning", "Upozornenie"), msg, parent=self.view)
            return

        confirm_msg = self.bridge.get_text(
            "msg_theme_delete_confirm",
            "Naozaj chcete permanentne zmazať tému '{0}'?"
        ).format(theme_filename)
        if not self.bridge.ask_question(self.bridge.get_text("title_confirm", "Potvrdenie"), confirm_msg, parent=self.view):
            return

        try:
            (self.user_themes_dir / theme_filename).unlink(missing_ok=True)
            self.load_available_themes()
            msg = self.bridge.get_text("msg_theme_deleted", "Téma '{0}' bola zmazaná.").format(theme_filename)
            self.bridge.show_info(self.bridge.get_text("title_success", "Úspech"), msg, parent=self.view)
        except Exception as e:
            msg = self.bridge.get_text("err_theme_delete_failed", "Nepodarilo sa zmazať súbor: {0}").format(e)
            self.bridge.show_error(self.bridge.get_text("title_error", "Chyba"), msg, parent=self.view)