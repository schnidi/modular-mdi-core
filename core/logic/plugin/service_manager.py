"""
Súbor: core/logic/plugin/service_manager.py
Centrálny register (IoC trhovisko) pre služby a pluginy.
"""


class ServiceManager:
    """
    Singleton, ktorý funguje ako centrálny register služieb.
    Umožňuje modulom vzájomne komunikovať a pristupovať k službám
    bez priamych tvrdých importov.
    """
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if ServiceManager._instance is not None:
            raise RuntimeError("ServiceManager je singleton! Použite ServiceManager.get_instance().")
        self._services = {}
        self._waiters: dict[str, list] = {}

    def has_service(self, service_name: str) -> bool:
        """Overí, či je služba s daným kľúčom už zaregistrovaná."""
        return service_name in self._services

    def register_service(self, service_name: str, service_instance: object):
        """Zaregistruje inštanciu alebo triedu služby."""
        if not service_name:
            print("[ServiceManager] VAROVANIE: Pokus o registráciu služby bez mena.")
            return

        if self.has_service(service_name):
            return

        self._services[service_name] = service_instance
        print(f"[ServiceManager] Zaregistrovaná služba: '{service_name}'")

        for callback in self._waiters.pop(service_name, []):
            callback(service_instance)

    def get_service(self, service_name: str) -> object | None:
        """Vráti inštanciu služby podľa jej mena."""
        return self._services.get(service_name)

    def on_service_ready(self, service_name: str, callback):
        """
        Zavolá callback okamžite, ak je služba už zaregistrovaná.
        Inak si callback odloží a zavolá ho automaticky vo chvíli,
        keď sa služba pod daným menom zaregistruje cez register_service().
        Nahrádza polling (napr. QTimer.singleShot) na strane modulov.
        """
        existing = self._services.get(service_name)
        if existing is not None:
            callback(existing)
        else:
            self._waiters.setdefault(service_name, []).append(callback)

    def clear_all_services(self):
        """Vymaže všetky registrované služby."""
        self._services.clear()
        print("[ServiceManager] Všetky služby boli odregistrované.")
