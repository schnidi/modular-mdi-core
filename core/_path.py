import os

class Paths:
    """Centrálny manažér ciest pre celú aplikáciu."""

    ASSETS_DIR_NAME = "assets"

    @staticmethod
    def get_root():
        """Vráti koreň projektu (zložka nad 'core')."""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @staticmethod
    def get_core_dir():
        return os.path.join(Paths.get_root(), "core")

    @staticmethod
    def get_config_dir():
        """Vráti cestu k priečinku s konfiguráciami."""
        config_dir = os.path.join(Paths.get_core_dir(), "config")
        os.makedirs(config_dir, exist_ok=True)
        return config_dir

    @staticmethod
    def get_modules_dir():
        """Vráti cestu k priečinku s pluginmi/modulmi (v koreni projektu)."""
        modules_dir = os.path.join(Paths.get_root(), "modules")
        os.makedirs(modules_dir, exist_ok=True)
        return modules_dir

    @staticmethod
    def get_ui_file(filename):
        """Vráti cestu k .ui súboru."""
        return os.path.join(Paths.get_core_dir(), "ui", filename)

    @staticmethod
    def get_themes_dir():
        """Vráti cestu k .qss témam."""
        return os.path.join(Paths.get_core_dir(), "themes", "skin")

    @staticmethod
    def get_user_themes_dir():
        """Vráti cestu k užívateľským témam."""
        return os.path.join(Paths.get_core_dir(), "themes", "user")

    @staticmethod
    def get_translations_dir():
        """Vráti cestu k .json prekladom."""
        return os.path.join(Paths.get_core_dir(), "translations")

    @staticmethod
    def get_assets_dir():
        """Vráti cestu k assetom (napr. about.json)."""
        return os.path.join(Paths.get_core_dir(), Paths.ASSETS_DIR_NAME)

    @staticmethod
    def get_icon_dir():
        """Vráti cestu k priečinku s ikonami."""
        return os.path.join(Paths.get_core_dir(), "themes", "icon")

    @staticmethod
    def get_icon_path(filename):
        """Vráti cestu ku konkrétnej ikone."""
        return os.path.join(Paths.get_icon_dir(), filename)

    @staticmethod
    def process_qss_paths(qss_content: str) -> str:
        """
        Centrálne nahradí zástupné symboly a normalizuje cesty pre QSS engine.
        Qt vyžaduje v URL priame lomky (/).
        """
        if not qss_content:
            return ""
        
        themes_dir = Paths.get_themes_dir().replace("\\", "/")
        icons_dir = Paths.get_icon_dir().replace("\\", "/")
        core_dir = Paths.get_core_dir().replace("\\", "/")

        qss_content = qss_content.replace("@THEMES_DIR@", themes_dir)
        qss_content = qss_content.replace("@ICON_DIR@", icons_dir)
        qss_content = qss_content.replace("@CORE_DIR@", core_dir)

        return qss_content

    # Aliasy pre spätnú kompatibilitu
    @staticmethod
    def get_app_root_path(): return Paths.get_root()
    @staticmethod
    def get_base_path(): return Paths.get_root()


    @staticmethod
    def get_modules_ini():
        """Vráti cestu k súboru modules.ini."""
        return os.path.join(Paths.get_config_dir(), "modules.ini")

    @staticmethod
    def get_system_groups_ini():
        """Vráti cestu k súboru system_groups.ini."""
        return os.path.join(Paths.get_config_dir(), "system_groups.ini")

    @staticmethod
    def get_auth_settings_ini():
        """Vráti cestu k súboru auth_settings.ini."""
        return os.path.join(Paths.get_config_dir(), "auth_settings.ini")

    @staticmethod
    def get_window_setup_ini():
        """Vráti cestu k súboru window_setup.ini."""
        return os.path.join(Paths.get_config_dir(), "window_setup.ini")