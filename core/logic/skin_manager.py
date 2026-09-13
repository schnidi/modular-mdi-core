# Súbor: core/logic/skin_manager.py

import os
from PyQt6.QtWidgets import QApplication
from core._path import Paths
from core.logic.resource_manager import ResourceManager
from core.logic.services.config_manager import ConfigManager
from core.enum_core import ConfigSection, ConfigKey


class SkinManager:
    """Manažér skinov, ktorý využíva výhradne Paths pre dynamické cesty a podporuje perzistenciu tém."""

    @staticmethod
    def get_saved_skin_name() -> str:
        """Načíta názov naposledy zvolenej témy z config/theme_settings.ini."""
        config_path = os.path.join(Paths.get_config_dir(), "theme_settings.ini")
        config = ConfigManager(config_path)
        return config.get_value(ConfigSection.SETTINGS, ConfigKey.ACTIVE_THEME, default="dark")

    @classmethod
    def apply_saved_skin(cls) -> bool:
        """Načíta a okamžite aplikuje uloženú tému (volá sa pri štarte pred SplashScreenom)."""
        skin_name = cls.get_saved_skin_name()
        return cls.apply_skin(skin_name)

    @staticmethod
    def apply_skin(skin_name: str) -> bool:
        """Načíta, spracuje cez Paths a aplikuje QSS štýl."""
        app = QApplication.instance()
        if not app:
            return False

        if not skin_name or skin_name.lower() == "default":
            app.setStyleSheet("")
            return True

        # 1. Hľadáme v systémových témach (core/themes/skin)
        themes_dir = Paths.get_themes_dir()
        content = ResourceManager.read_resource_file(themes_dir, skin_name, ".qss")

        # 2. Ak sa nenašla, hľadáme v používateľských témach (core/themes/user)
        if not content:
            user_themes_dir = Paths.get_user_themes_dir()
            content = ResourceManager.read_resource_file(user_themes_dir, skin_name, ".qss")

        if content:
            # Všetko spracovanie ciest (@ICON_DIR@, @THEMES_DIR@) robí centrálny Paths
            processed_content = Paths.process_qss_paths(content)
            app.setStyleSheet(processed_content)
            return True

        print(f"[SkinManager] CHYBA: Téma '{skin_name}' nebola nájdená v: {themes_dir}")
        
        # Bezpečný fallback na predvolenú tému dark, ak zvolená chýba
        if skin_name != "dark":
            return SkinManager.apply_skin("dark")
            
        return False