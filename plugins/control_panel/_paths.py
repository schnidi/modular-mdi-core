# Súbor: modules/control_panel/_paths.py
from pathlib import Path

# Dynamické zistenie koreňa tohto konkrétneho modulu
MODULE_ROOT = Path(__file__).parent.resolve()
MODULE_NAME = MODULE_ROOT.name

UI_DIR = MODULE_ROOT / "ui"
UI_FILE_PATH = UI_DIR / "control_panel_window.ui"

# PREMENOVANÉ: Jadro (ModuleTranslationService) hľadá presne túto konštantu
TRANSLATIONS_DIR = MODULE_ROOT / "translations"