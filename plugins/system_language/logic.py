# Súbor: system_language/logic.py

from core.enum_core import ICoreBridge
from .module_interface import get_module_info


def bootstrap(bridge: ICoreBridge = None):
    """
    Štartovacia funkcia modulu volaná jadrom pri inicializácii.
    Všetko vykonáva priamo cez most 'bridge'.
    """
    if bridge:
        # 1. ZMENA: preklady sa registrujú výhradne cez oficiálny bridge mechanizmus
        # (LanguageManager -> TranslationRegistry), nie ručným zásahom do privátnych
        # atribútov LanguageManagera. Toto zaregistruje modul do _registered_dirs,
        # takže sa jeho preklady automaticky správne zlúčia pri KAŽDOM budúcom
        # bridge.set_language(...), nielen jednorazovo pri štarte.
        bridge.register_module_translations(get_module_info())

        # 2. Načítame uložený jazyk cez most
        selected_lang = bridge.load_module_setting(
            module_name="system_language",
            section="General",
            key="language",
            default="sk_SK"
        )
        # 3. Nastavíme jazyk v celom systéme
        bridge.set_language(selected_lang)


def create_widget(bridge: ICoreBridge = None, **kwargs):
    """Továreň pre vytvorenie okna – odovzdá most do UI okna."""
    from .windows.language_settings_window import LanguageSettingsWindow
    return LanguageSettingsWindow(bridge=bridge)
