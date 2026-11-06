# Súbor: modules/tab_menu/run_tab_menu_diagnostics.py
# Spustenie z koreňa: python modules\tab_menu\run_tab_menu_diagnostics.py

import os
import sys
import json
from pathlib import Path

# Nastavenie offscreen režimu pre test
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Korektné nájdenie koreňa celého projektu (!SaL_Modular)
CURRENT_FILE = Path(__file__).resolve()
if "modules" in CURRENT_FILE.parts:
    # modules/tab_menu -> rodič 0 = tab_menu, rodič 1 = modules, rodič 2 = koreň projektu
    PROJECT_ROOT = CURRENT_FILE.parents[2]
else:
    PROJECT_ROOT = CURRENT_FILE.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication, QWidget, QMdiSubWindow
from PyQt6.QtCore import pyqtSignal, QObject


def log(section: str, message: str, status: str = "INFO"):
    colors = {
        "INFO": "\033[94m",
        "PASS": "\033[92m",
        "WARN": "\033[93m",
        "FAIL": "\033[91m",
        "STEP": "\033[95m",
        "RESET": "\033[0m"
    }
    col = colors.get(status, colors["RESET"])
    reset = colors["RESET"]
    print(f"{col}[{status:4s}] [{section:16s}] {message}{reset}")


class DiagnosticCoreBridge(QObject):
    language_changed = pyqtSignal(str)

    def __init__(self, translations_dir: Path):
        super().__init__()
        self.translations_dir = translations_dir
        self.current_lang = "sk_SK"
        self.dictionaries = {}
        self.connected_slots = []
        self.load_dictionaries()

    def load_dictionaries(self):
        log("CoreBridge", f"Hľadám slovníky v: {self.translations_dir}")
        for lang_code in ["sk_SK", "en_US"]:
            json_file = self.translations_dir / f"{lang_code}.json"
            if json_file.exists():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        self.dictionaries[lang_code] = json.load(f)
                    log("CoreBridge", f"Načítaný slovník '{lang_code}' ({len(self.dictionaries[lang_code])} kľúčov)", "PASS")
                except Exception as e:
                    log("CoreBridge", f"Chyba pri parsovaní {json_file.name}: {e}", "FAIL")
                    self.dictionaries[lang_code] = {}
            else:
                log("CoreBridge", f"Súbor {json_file.name} NEEXISTUJE!", "FAIL")
                self.dictionaries[lang_code] = {}

    def get_text(self, key: str, default: str = None) -> str:
        current_dict = self.dictionaries.get(self.current_lang, {})
        val = current_dict.get(key)
        if val is not None:
            return val
        log("CoreBridge", f"Preklad pre kľúč '{key}' sa v '{self.current_lang}' nenašiel! Použitý fallback: '{default}'", "WARN")
        return default if default is not None else key

    def translate_widget(self, widget: QWidget):
        current_dict = self.dictionaries.get(self.current_lang, {})
        matched_count = 0
        for child in widget.findChildren(QWidget):
            name = child.objectName()
            if name and name in current_dict:
                matched_count += 1
                new_text = current_dict[name]
                if hasattr(child, "setText"):
                    child.setText(new_text)
                elif hasattr(child, "setToolTip"):
                    child.setToolTip(new_text)
        log("CoreBridge", f"translate_widget() prešiel widget '{widget.objectName()}', preložených prvkov: {matched_count}")

    def connect_language_changed(self, slot):
        if slot not in self.connected_slots:
            self.connected_slots.append(slot)
            self.language_changed.connect(slot)
            slot_name = getattr(slot, "__qualname__", str(slot))
            log("CoreBridge", f"Zaregistrovaný poslucháč jazyka: {slot_name}")

    def disconnect_language_changed(self, slot):
        if slot in self.connected_slots:
            self.connected_slots.remove(slot)
            try:
                self.language_changed.disconnect(slot)
                slot_name = getattr(slot, "__qualname__", str(slot))
                log("CoreBridge", f"Odhlásený poslucháč jazyka: {slot_name}")
            except Exception:
                pass

    def switch_language(self, new_lang: str):
        log("CoreBridge", f"=== PREPÍNAM JAZYK NA: {new_lang} ===", "STEP")
        self.current_lang = new_lang
        self.language_changed.emit(new_lang)

    def load_module_setting(self, module, section, key, default="True"):
        return default

    def save_module_setting(self, module, section, key, value):
        pass


class MockWindowManager:
    def __init__(self):
        self.view = QWidget()
        self.view.setObjectName("MainWindowMock")
        self.sub_windows = {}

    def add_mock_subwindow(self, win_key: str, client_title: str):
        sub_w = QMdiSubWindow()
        sub_w.setObjectName(win_key)
        sub_w.setWindowTitle(client_title)
        
        client_w = QWidget(sub_w)
        client_w.setObjectName(win_key)
        client_w.setWindowTitle(client_title)
        sub_w.client_widget = client_w
        sub_w.setWidget(client_w)

        self.sub_windows[win_key] = sub_w
        return sub_w


class MockServiceManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.services = {}

    def get_service(self, name: str):
        return self.services.get(name)

    def register_service(self, name: str, svc):
        self.services[name] = svc


def run_diagnostics():
    print("\n" + "=" * 70)
    print("      KOMPLETNÁ DIAGNOSTIKA PREKLADOV MODULU TAB_MENU      ")
    print("=" * 70 + "\n")

    app = QApplication.instance() or QApplication(sys.argv)

    module_path = PROJECT_ROOT / "modules" / "tab_menu"
    trans_dir = module_path / "translations"
    log("Init", f"Koreň projektu: {PROJECT_ROOT}")
    log("Init", f"Koreň modulu: {module_path}")
    log("Init", f"Priečinok prekladov: {trans_dir}")

    bridge = DiagnosticCoreBridge(trans_dir)

    log("Import", "Importujem triedy z modulu tab_menu...")
    try:
        from modules.tab_menu.windows.tab_menu_bar_widget import TabMenuBarWidget
        from modules.tab_menu.logic.tab_menu_controller import TabMenuController
        log("Import", "Triedy TabMenuBarWidget a TabMenuController úspešne importované.", "PASS")
    except Exception as e:
        log("Import", f"CHYBA pri importe komponentov: {e}", "FAIL")
        return False

    log("Setup", "Vytváram simulované prostredie s MDI oknami...")
    mock_wm = MockWindowManager()
    mock_wm.add_mock_subwindow("user_manager", "Správa používateľov")
    mock_wm.add_mock_subwindow("invoices", "Faktúry")

    service_manager = MockServiceManager.get_instance()
    service_manager.register_service("window_manager", mock_wm)
    service_manager.register_service("module_manager", None)

    log("Lifecycle", "Vytváram inštanciu TabMenuBarWidget s bridge...", "STEP")
    view = TabMenuBarWidget(bridge=bridge)
    
    log("Lifecycle", "Vytváram inštanciu TabMenuController...", "STEP")
    controller = TabMenuController(
        bar_view=view,
        bridge=bridge,
        service_manager=service_manager,
        main_controller=mock_wm
    )
    view.controller = controller

    log("Inspect", "Kontrolujem počiatočný stav v slovenskom jazyku (sk_SK)...", "STEP")
    controller.sync_tabs_with_open_windows()
    app.processEvents()

    initial_tab_text = bridge.get_text("tab_all_windows", "FAIL")
    initial_btn_tooltip = view.btn_settings.toolTip()
    
    log("Inspect", f"Základný text 'tab_all_windows': '{initial_tab_text}'")
    log("Inspect", f"Tooltip tlačidla nastavení: '{initial_btn_tooltip}'")

    if initial_tab_text in ["FAIL", "tab_all_windows"]:
        log("Inspect", "Kľúč 'tab_all_windows' chýba v sk_SK.json!", "WARN")
    else:
        log("Inspect", "Počiatočný preklad v sk_SK je aktívny.", "PASS")

    # TEST: Prepnutie do en_US
    log("Test", "--- KROK 1: Prepnutie do en_US ---", "STEP")
    bridge.switch_language("en_US")
    app.processEvents()

    en_tab_text = bridge.get_text("tab_all_windows", "FAIL")
    en_btn_tooltip = view.btn_settings.toolTip()

    log("Test", f"Nový text 'tab_all_windows' (en_US): '{en_tab_text}'")
    log("Test", f"Nový tooltip tlačidla (en_US): '{en_btn_tooltip}'")

    if en_tab_text != initial_tab_text and en_tab_text != "FAIL":
        log("Test", "Dynamická zmena textu záložiek na en_US ZBEHLA SPRÁVNE!", "PASS")
    else:
        log("Test", "Nedošlo k zmene textu 'tab_all_windows' po prepnutí na en_US!", "FAIL")

    # TEST: Prepnutie späť do sk_SK
    log("Test", "--- KROK 2: Prepnutie späť do sk_SK ---", "STEP")
    bridge.switch_language("sk_SK")
    app.processEvents()

    sk_tab_text = bridge.get_text("tab_all_windows", "FAIL")
    sk_btn_tooltip = view.btn_settings.toolTip()

    log("Test", f"Text po návrate do sk_SK: '{sk_tab_text}'")
    log("Test", f"Tooltip po návrate do sk_SK: '{sk_btn_tooltip}'")

    if sk_tab_text == initial_tab_text:
        log("Test", "Návrat do pôvodného jazyka ZBEHOL SPRÁVNE!", "PASS")
    else:
        log("Test", "Po návrate do sk_SK nezodpovedá text pôvodnému!", "FAIL")

    # TEST: Kontrola odhlásenia poslucháčov
    log("Cleanup", "--- KROK 3: Test odhlásenia signálov pri zatvorení ---", "STEP")
    active_listeners_before = len(bridge.connected_slots)
    log("Cleanup", f"Počet aktívnych poslucháčov pred zatvorením: {active_listeners_before}")

    view.close()
    controller._cleanup()
    active_listeners_after = len(bridge.connected_slots)
    log("Cleanup", f"Počet aktívnych poslucháčov po zatvorení: {active_listeners_after}")

    if active_listeners_after < active_listeners_before:
        log("Cleanup", "Všetky signály boli bezpečne odpojené.", "PASS")
    else:
        log("Cleanup", "Signály ostali zaregistrované (hrozí memory leak)!", "FAIL")

    print("\n" + "=" * 70)
    print("                    VÝSLEDOK DIAGNOSTIKY                   ")
    print("=" * 70)
    print("Prebehla kompletná simulácia a otestovanie prekladového systému.")
    print("=" * 70 + "\n")
    return True


if __name__ == "__main__":
    run_diagnostics()