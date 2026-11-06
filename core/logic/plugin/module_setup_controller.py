# Súbor: core/logic/plugin/module_setup_controller.py

import sys
import zipfile
import shutil
from pathlib import Path
import importlib.util
from uuid import uuid4 

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QFileDialog

from core._path import Paths
from core.logic.services.config_manager import ConfigManager
from core.logic.module_manager import ModuleManager
from core.logic.module_config import ModuleConfig
from core.logic.group_manager import GroupManager
from core.logic.language_manager import LanguageManager
from core.enum_core import ConfigSection, ConfigKey
from core.windows.custom_message_box import CustomMessageBox


class ModuleSetupController:
    class _Signals(QObject):
        modules_config_changed = pyqtSignal()

    signals = _Signals()

    def __init__(self, view, main_controller=None):
        self.view = view
        self.main_controller = main_controller
        self.modules_dir = Path(Paths.get_modules_dir())
        self.module_manager = ModuleManager()
        self.module_config = ModuleConfig(file_path=Paths.get_modules_ini())
        self.window_config = ConfigManager(filename=Paths.get_window_setup_ini())
        self.auth_settings_config = ConfigManager(filename=Paths.get_auth_settings_ini())
        self.group_manager = GroupManager.get_instance()

        self._synchronize_config_with_disk()

        self.view.apply_changes_requested.connect(self.save_and_apply_changes)
        self.view.install_requested.connect(self.handle_install)
        self.view.uninstall_requested.connect(self.handle_uninstall)
        self.load_initial_state()

    def _synchronize_config_with_disk(self):
        self.module_config.reload()
        all_module_names = self.module_config.config.sections()
        
        removed_count = 0
        for module_name in all_module_names:
            module_path_str = self.module_config.get_module_path(module_name)
            
            if module_path_str:
                module_path = Path(module_path_str)
                if not module_path.is_absolute():
                    module_path = Path(Paths.get_root()) / module_path

                if not module_path.exists():
                    self.module_config.remove_module(module_name)
                    self.group_manager.update_module_groups(module_name, {})
                    removed_count += 1

        if removed_count > 0:
            self.module_config.save()

    def _get_info_from_interface(self, interface_file: Path) -> dict | None:
        if not interface_file.exists():
            return None
            
        module_dir = str(interface_file.parent.resolve())
        if module_dir not in sys.path:
            sys.path.insert(0, module_dir)

        if 'app.core' not in sys.modules:
            import core
            sys.modules['app'] = sys.modules.get('__main__', sys.modules[__name__]) 
            sys.modules['app.core'] = core
            if 'core.enum_core' in sys.modules:
                sys.modules['app.enum_core'] = sys.modules['core.enum_core']

        try:
            temp_module_name = f"temp_interface_{uuid4().hex}"
            spec = importlib.util.spec_from_file_location(temp_module_name, str(interface_file))
            if spec and spec.loader:
                module_interface = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module_interface)
                if hasattr(module_interface, "get_module_info"):
                    return module_interface.get_module_info()
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            raise RuntimeError(f"Chyba pri čítaní {interface_file.name}:\n\n{error_details}")
        finally:
            if module_dir in sys.path:
                sys.path.remove(module_dir)
                
        return None

    def load_initial_state(self):
        all_modules_status = self.module_manager.get_all_modules_status()
        self.view.populate_modules_list(all_modules_status)

    def save_and_apply_changes(self, new_status: dict):
        self.module_config.reload()

        # 1. AUTO-AKTIVÁCIA ZÁVISLOSTÍ
        auto_enabled_info = []
        for mod_name, is_enabled in list(new_status.items()):
            if is_enabled:
                deps = self.module_manager.get_module_dependencies(mod_name)
                for dep in deps:
                    if dep in new_status and not new_status[dep]:
                        new_status[dep] = True
                        auto_enabled_info.append(f"Modul '{dep}' (vyžadovaný modulom '{mod_name}')")

        # 2. OCHRANA DEAKTIVÁCIE
        for mod_name, is_enabled in new_status.items():
            if not is_enabled:
                dependents = self.module_manager.get_dependents_of(mod_name)
                active_dependents = [d for d in dependents if new_status.get(d, False)]
                if active_dependents:
                    title = LanguageManager.get("msg_dep_title", "Závislosť modulov")
                    msg = LanguageManager.get(
                        "msg_dep_cannot_disable",
                        "Nemôžete deaktivovať modul '{0}', pretože ho vyžadujú nasledujúce aktívne moduly:\n\n• {1}\n\nNajprv deaktivujte tieto moduly."
                    ).format(mod_name, ', '.join(active_dependents))
                    CustomMessageBox.critical(self.view, title, msg)
                    self.load_initial_state()
                    return

        # 3. Kontrola AUTH modulov (max 1)
        active_auth_modules_names = []
        for name, enabled in new_status.items():
            if enabled:
                module_path_str = self.module_config.get_module_path(name)
                if module_path_str and "auth" in Path(module_path_str).parts:
                    active_auth_modules_names.append(name)
        
        if len(active_auth_modules_names) > 1:
            title = LanguageManager.get("msg_config_error_title", "Chyba konfigurácie")
            msg = LanguageManager.get("msg_err_max_one_auth", "Môže byť aktívny maximálne JEDEN autentifikačný modul!")
            CustomMessageBox.critical(self.view, title, msg)
            return

        active_auth_module = active_auth_modules_names[0] if active_auth_modules_names else None

        all_groups_data = self.module_manager.get_all_provided_groups()
        for module_name, groups in all_groups_data.items():
            self.group_manager.update_module_groups(module_name, groups)
        
        if active_auth_module:
            setup_successful = self._run_first_time_setup(active_auth_module)
            if not setup_successful:
                title = LanguageManager.get("msg_aborted_title", "Prerušené")
                msg = LanguageManager.get("msg_setup_incomplete", "Nastavenie modulu nebolo dokončené.")
                CustomMessageBox.warning(self.view, title, msg)
                self.load_initial_state() 
                return

        for module_name, is_enabled in new_status.items():
            self.module_config.set_module_enabled(module_name, is_enabled)
        self.module_config.save()

        self.auth_settings_config.set_value(ConfigSection.SETTINGS, ConfigKey.ACTIVE_AUTH_MODULE, active_auth_module or "")
        self.auth_settings_config.save()

        self.load_initial_state()
        self.signals.modules_config_changed.emit()

        msg = LanguageManager.get("msg_modules_saved_ok", "Zmeny v moduloch boli úspešne aplikované.")
        if auto_enabled_info:
            msg += "\n\n" + LanguageManager.get("msg_auto_enabled_deps", "Automaticky boli aktivované tieto závislosti:\n• ") + "\n• ".join(auto_enabled_info)

        title = LanguageManager.get("msg_done_title", "Hotovo")
        CustomMessageBox.information(self.view, title, msg)

    def handle_install(self, file_path=None):
        if not file_path:
            dialog_title = LanguageManager.get("dialog_select_zip", "Vyberte .zip archív s modulom")
            file_filter = LanguageManager.get("filter_zip_archives", "ZIP archívy (*.zip)")
            file_path, _ = QFileDialog.getOpenFileName(self.view, dialog_title, "", file_filter)
        if not file_path:
            return

        temp_dir = self.modules_dir.parent / f"temp_install_{uuid4().hex}"
        module_name = None

        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                interface_path_in_zip = next(
                    (name for name in zip_ref.namelist() 
                     if name.endswith('module_interface.py') and '__MACOSX' not in name), 
                    None
                )
                if not interface_path_in_zip:
                    raise ValueError(LanguageManager.get("err_zip_no_interface", "Archív neobsahuje povinný súbor 'module_interface.py'."))

                module_name = Path(interface_path_in_zip).parent.name
                temp_dir.mkdir(parents=True, exist_ok=True)
                zip_ref.extractall(temp_dir)

            temp_module_root = temp_dir / Path(interface_path_in_zip).parent
            interface_file = temp_module_root / "module_interface.py"
            
            info = self._get_info_from_interface(interface_file)
            if not info:
                raise ValueError(LanguageManager.get("err_read_interface_fail", "Nepodarilo sa načítať informácie z module_interface.py pre '{0}'.").format(module_name))

            dependencies = info.get("dependencies", [])
            if dependencies:
                self.module_config.reload()
                installed_modules = self.module_config.config.sections()
                missing_deps = [dep for dep in dependencies if dep not in installed_modules]
                
                if missing_deps:
                    title = LanguageManager.get("msg_install_denied_title", "Inštalácia zamietnutá")
                    msg = LanguageManager.get(
                        "msg_install_missing_deps",
                        "Modul '{0}' nie je možné nainštalovať!\n\nVyžaduje nasledujúce chýbajúce moduly, ktoré nie sú v systéme:\n• {1}\n\nNainštalujte prosím najprv požadované moduly."
                    ).format(module_name, ', '.join(missing_deps))
                    CustomMessageBox.critical(self.view, title, msg)
                    return

            install_prefix = info.get("install_path_prefix", "")
            target_dir = self.modules_dir / install_prefix if install_prefix else self.modules_dir
            final_path = target_dir / module_name

            if final_path.exists():
                raise ValueError(LanguageManager.get("err_module_exists", "Modul '{0}' je už na ceste '{1}' nainštalovaný.").format(module_name, final_path))

            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(temp_module_root), str(final_path))

            rel_path = final_path.relative_to(Path(Paths.get_root()))
            self.module_config.set_module_path(module_name, str(rel_path).replace("\\", "/"))
            
            if window_key := info.get("window_key"):
                self.window_config.set_value(window_key, ConfigKey.IS_OPEN, 'False')
                self.window_config.save()
            
            self.module_config.set_module_enabled(module_name, False)
            self.module_config.save()

            provided_groups = info.get("provided_groups", {})
            if provided_groups:
                self.group_manager.update_module_groups(module_name, provided_groups)
            
            title = LanguageManager.get("msg_success_title", "Úspech")
            msg = LanguageManager.get("msg_module_installed_ok", "Modul '{0}' bol úspešne nainštalovaný.").format(module_name)
            CustomMessageBox.information(self.view, title, msg)
            self.load_initial_state()
            self.signals.modules_config_changed.emit()

        except Exception as e:
            title = LanguageManager.get("msg_err_install_title", "Chyba pri inštalácii")
            main_text = LanguageManager.get("msg_unexpected_error", "Nastala neočakávaná chyba:")
            CustomMessageBox.critical(self.view, title, main_text, detailed_text=str(e))
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def handle_uninstall(self, module_name: str):
        dependents = self.module_manager.get_dependents_of(module_name)
        if dependents:
            title = LanguageManager.get("msg_uninstall_denied_title", "Odinštalácia zamietnutá")
            msg = LanguageManager.get(
                "msg_uninstall_has_dependents",
                "Nemôžete odinštalovať modul '{0}', pretože na ňom závisia nasledujúce nainštalované moduly:\n\n• {1}\n\nNajprv odinštalujte tieto závislé moduly."
            ).format(module_name, ', '.join(dependents))
            CustomMessageBox.critical(self.view, title, msg)
            return

        confirm_title = LanguageManager.get("msg_confirm_delete_title", "Potvrdenie zmazania")
        confirm_msg = LanguageManager.get("msg_confirm_delete", "Naozaj chcete permanentne zmazať modul '{0}'?").format(module_name)
        if not CustomMessageBox.question(self.view, confirm_title, confirm_msg):
            return
        
        try:
            self.module_config.reload()
            module_path_str = self.module_config.get_module_path(module_name)
            
            if module_path_str:
                module_path = Path(module_path_str)
                if not module_path.is_absolute():
                    module_path = Path(Paths.get_root()) / module_path
            else:
                raise FileNotFoundError(f"Cesta pre modul '{module_name}' nebola nájdená v konfigurácii.")

            if module_path.is_dir():
                shutil.rmtree(module_path, ignore_errors=True)
            
            self.group_manager.update_module_groups(module_name, {}) 

            if self.window_config.config.has_section(module_name):
                self.window_config.remove_section(module_name)
                self.window_config.save()
                
            self.module_config.remove_module(module_name)
            self.module_config.save()
            
            if self.auth_settings_config.get_value(ConfigSection.SETTINGS, ConfigKey.ACTIVE_AUTH_MODULE) == module_name:
                self.auth_settings_config.set_value(ConfigSection.SETTINGS, ConfigKey.ACTIVE_AUTH_MODULE, "")
                self.auth_settings_config.save()
            
            title = LanguageManager.get("msg_success_title", "Úspech")
            msg = LanguageManager.get("msg_module_uninstalled_ok", "Modul '{0}' bol úspešne odinštalovaný.").format(module_name)
            CustomMessageBox.information(self.view, title, msg)
            
            self._synchronize_config_with_disk()
            self.load_initial_state()
            self.signals.modules_config_changed.emit()
            
        except Exception as e: 
            title = LanguageManager.get("msg_err_uninstall_title", "Chyba pri odinštalácii")
            main_text = LanguageManager.get("msg_unexpected_error", "Nastala neočakávaná chyba:")
            CustomMessageBox.critical(self.view, title, main_text, detailed_text=str(e))

    def _run_first_time_setup(self, module_name: str) -> bool:
        try:
            self.module_config.reload()
            module_path_str = self.module_config.get_module_path(module_name)
            
            if not module_path_str:
                raise FileNotFoundError("Chýba cesta k modulu v konfigurácii.")
                
            module_path = Path(module_path_str)
            if not module_path.is_absolute():
                module_path = Path(Paths.get_root()) / module_path

            interface_file = module_path / "module_interface.py"
            info = self._get_info_from_interface(interface_file)
            if not info:
                return True

            setup_path = info.get("setup_function_path")
            if setup_path:
                mod_path, func_name = setup_path.rsplit('.', 1)
                module = importlib.import_module(mod_path)
                setup_func = getattr(module, func_name)
                return setup_func()
            
            return True

        except Exception as e:
            title = LanguageManager.get("msg_warning_title", "Upozornenie")
            msg = LanguageManager.get("msg_setup_failed", "Nepodarilo sa spustiť počiatočné nastavenie pre modul '{0}'.").format(module_name)
            CustomMessageBox.critical(self.view, title, msg, detailed_text=str(e))
            return False