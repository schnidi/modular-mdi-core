# Súbor: modules/theme_setup/_paths.py

from pathlib import Path

MODULE_ROOT = Path(__file__).parent.resolve()
MODULE_NAME = "theme_setup"

UI_DIR = MODULE_ROOT / "ui"
RESOURCES_DIR = MODULE_ROOT / "resources"
TRANSLATIONS_DIR = MODULE_ROOT / "translations"