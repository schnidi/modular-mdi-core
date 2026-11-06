# Súbor: system_language/_paths.py

from pathlib import Path

MODULE_ROOT = Path(__file__).parent.resolve()
MODULE_NAME = "system_language"

# UI súbory, ikony a preklady vnútri modulu
UI_FILES_DIR = MODULE_ROOT / "ui" / "ui_files"
RESOURCES_DIR = MODULE_ROOT / "ui" / "resources"

# ZMENA: premenované z MODULE_TRANSLATIONS_DIR na TRANSLATIONS_DIR - toto je presný
# názov konštanty, ktorý vyžaduje ModuleTranslationService.register_module_from_info()
# pri oficiálnej registrácii cez bridge.register_module_translations().
TRANSLATIONS_DIR = MODULE_ROOT / "core" / "translations"

LANGUAGE_SETTINGS_UI_PATH = str(UI_FILES_DIR / "language_settings_window.ui")
LANGUAGE_ICON_PATH = str(RESOURCES_DIR / "icons" / "language_icon.svg")
