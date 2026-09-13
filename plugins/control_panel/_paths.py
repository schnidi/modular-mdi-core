# Súbor: modules/control_panel/_paths.py
# Tento súbor slúži ako jediný zdroj pravdy pre všetky interné cesty v module.

from pathlib import Path

# Naša "kotva", ktorá sa nikdy nemení.
MODULE_ROOT = Path(__file__).parent.resolve()

# Odvodíme cesty k dôležitým podadresárom
UI_DIR = MODULE_ROOT / "ui"
CONFIG_DIR = MODULE_ROOT / "config" # Aj keď adresár neexistuje, cesta je platná

# Môžeme si zadefinovať aj priamu cestu ku konfiguračnému súboru
# pre ešte čistejšie použitie v controlleri.
PANEL_LAYOUT_CONFIG_FILE = CONFIG_DIR / "control_panel_layout.json"