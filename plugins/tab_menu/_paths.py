# Súbor: modules/tab_menu/_paths.py

from pathlib import Path

MODULE_ROOT = Path(__file__).parent.resolve()

UI_DIR = MODULE_ROOT / "ui"
# OPRAVA: Premenované z languages na translations podľa špecifikácie
TRANSLATIONS_DIR = MODULE_ROOT / "translations"


def get_ui_file(filename: str) -> str:
    return str(UI_DIR / filename)
