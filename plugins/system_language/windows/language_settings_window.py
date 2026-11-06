# ================================================================================
# Súbor: modules/system/system_language/windows/language_settings_window.py
# Okno nastavenia jazyka komunikujúce výhradne cez ICoreBridge
# ================================================================================

import os
from PyQt6.QtWidgets import QWidget, QMdiSubWindow
from PyQt6 import uic

from core.enum_core import ICoreBridge
from .._paths import LANGUAGE_SETTINGS_UI_PATH


class LanguageSettingsWindow(QWidget):
    """Okno nastavenia jazyka komunikujúce výhradne cez ICoreBridge."""

    FALLBACK_LANGUAGES = {
        "sk_SK": "Slovenčina (SK)",
        "en_US": "English (US)",
        "de_DE": "Deutsch (DE)",
        "cs_CZ": "Čeština (CZ)"
    }

    def __init__(self, bridge: ICoreBridge = None, parent=None):
        super().__init__(parent)
        self.setObjectName("LanguageSettingsWindow")
        self.bridge = bridge

        # 1. Načítanie UI súboru
        if os.path.exists(LANGUAGE_SETTINGS_UI_PATH):
            uic.loadUi(LANGUAGE_SETTINGS_UI_PATH, self)
        else:
            print(f"[system_language] CHYBA: UI súbor neexistuje: {LANGUAGE_SETTINGS_UI_PATH}")

        # 2. Naplnenie zoznamu jazykov
        self._populate_languages()

        # 3. Prepojenie tlačidiel
        self.sys_lang_btn_apply.clicked.connect(self._apply_changes)
        self.sys_lang_btn_close.clicked.connect(self._close_window)

        # 4. Prihlásenie na signál zmeny jazyka cez most
        if self.bridge:
            self.bridge.connect_language_changed(self.retranslate_ui)

        # 5. Úvodný preklad okna
        self.retranslate_ui()

    def _populate_languages(self):
        """Naplní ComboBox jazykmi s preloženými názvami."""
        self.sys_lang_combo.blockSignals(True)
        current_selected = self.sys_lang_combo.currentData()
        self.sys_lang_combo.clear()

        available_codes = []
        current_lang = "sk_SK"

        if self.bridge:
            available_codes = self.bridge.get_available_languages()
            current_lang = self.bridge.get_current_language()

        if not available_codes:
            available_codes = ["sk_SK", "en_US"]

        for code in available_codes:
            fallback = self.FALLBACK_LANGUAGES.get(code, code)
            display_name = self.bridge.get_text(f"lang_{code}", fallback) if self.bridge else fallback
            self.sys_lang_combo.addItem(display_name, code)

        target_code = current_selected or current_lang
        index = self.sys_lang_combo.findData(target_code)
        if index != -1:
            self.sys_lang_combo.setCurrentIndex(index)

        self.sys_lang_combo.blockSignals(False)

    def _apply_changes(self):
        """Zmení jazyk v systéme a uloží konfiguráciu cez most."""
        selected_code = self.sys_lang_combo.currentData()
        if not selected_code:
            return

        self.sys_lang_btn_apply.setEnabled(False)
        try:
            if self.bridge:
                # 1. Požiadame most o zmenu jazyka v celom systéme
                self.bridge.set_language(selected_code)

                # 2. Požiadame most o uloženie nastavenia do INI
                self.bridge.save_module_setting(
                    module_name="system_language",
                    section="General",
                    key="language",
                    value=selected_code
                )
        finally:
            self.sys_lang_btn_apply.setEnabled(True)

    def retranslate_ui(self, lang_code=None):
        """Preloží všetky texty, tooltipy, prvky a nastaví svoj windowTitle."""
        if not self.bridge:
            return

        # 1. Automatický preklad podradených widgetov
        self.bridge.translate_widget(self)

        # 2. Preklad titulku okna
        new_title = self.bridge.get_text("LanguageSettingsWindow", "Nastavenie Jazyka")
        self.setWindowTitle(new_title)

        # 3. Preklad konkrétnych prvkov
        if hasattr(self, "sys_lang_lbl_select"):
            self.sys_lang_lbl_select.setText(self.bridge.get_text("sys_lang_lbl_select", "Vyberte jazyk aplikácie:"))
        if hasattr(self, "sys_lang_btn_apply"):
            self.sys_lang_btn_apply.setText(self.bridge.get_text("sys_lang_btn_apply", "Aplikovať"))
        if hasattr(self, "sys_lang_btn_close"):
            self.sys_lang_btn_close.setText(self.bridge.get_text("sys_lang_btn_close", "Zatvoriť"))
        if hasattr(self, "sys_lang_combo"):
            self.sys_lang_combo.setToolTip(self.bridge.get_text("sys_lang_combo", "Zoznam dostupných jazykov pre rozhranie aplikácie."))

        # 4. Aktualizácia preložených názvov jazykov v ComboBoxe
        self._populate_languages()

    def _close_window(self):
        """
        Zatvorí okno úplne rovnako ako kliknutie na krížik (X).
        Nájde skutočné QMdiSubWindow v hierarchii rodičov a zavrie celú kartu.
        """
        parent = self.parent()
        while parent:
            if isinstance(parent, QMdiSubWindow):
                parent.close()
                return
            parent = parent.parent()

        # Fallback ak okno náhodou nebeží v MDI ploche
        self.close()

    def closeEvent(self, event):
        if self.bridge:
            self.bridge.disconnect_language_changed(self.retranslate_ui)
        event.accept()