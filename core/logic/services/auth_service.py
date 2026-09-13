# Súbor: core/logic/services/auth_service.py

from PyQt6.QtCore import QObject, pyqtSignal
from core.enum_core import AuthConstant


class AuthService(QObject):
    """
    Singleton služba, ktorá drží informácie o aktuálne prihlásenom používateľovi.
    """
    # Signály, ktoré informujú zvyšok aplikácie o zmene stavu
    user_logged_in = pyqtSignal(dict)  # Posiela user_info
    user_logged_out = pyqtSignal()

    _instance = None
    
    # --- KONŠTANTA PRE NEPRIHLÁSENÝ STAV ---
    DEFAULT_USER_PREFIX = AuthConstant.DEFAULT_USER_PREFIX

    @staticmethod
    def get_instance():
        if AuthService._instance is None:
            AuthService._instance = AuthService()
        return AuthService._instance

    def __init__(self):
        super().__init__()
        if AuthService._instance is not None:
            raise Exception("Táto trieda je singleton!")
        self._current_user = None
        self._permissions = set()
        AuthService._instance = self

    def login(self, user_info: dict):
        """Uloží informácie o používateľovi a vyšle signál."""
        if user_info and "username" in user_info and "permissions" in user_info:
            self._current_user = user_info["username"]
            self._permissions = set(user_info["permissions"])
            print(f"Používateľ '{self._current_user}' sa prihlásil s oprávneniami: {self._permissions}")
            self.user_logged_in.emit(user_info)

    def logout(self):
        """Vymaže informácie o používateľovi a vyšle signál."""
        print(f"Používateľ '{self._current_user}' sa odhlasuje.")
        self._current_user = None
        self._permissions = set()
        self.user_logged_out.emit()

    def is_logged_in(self) -> bool:
        return self._current_user is not None

    def get_username(self) -> str | None:
        return self._current_user

    # --- NOVÁ METÓDA PRE DYNAMICKÝ PREFIX ---
    def get_current_prefix(self) -> str:
        """Vráti meno používateľa alebo 'DEFAULT' prefix pre konfiguráciu."""
        if self._current_user:
            return self._current_user
        return self.DEFAULT_USER_PREFIX
    
    def has_permission(self, permission: str) -> bool:
        """Overí, či má prihlásený používateľ požadované oprávnenie."""
        return permission in self._permissions