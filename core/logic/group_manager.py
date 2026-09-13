# Súbor: core/logic/group_manager.py

import configparser
from pathlib import Path
from typing import Dict, List, Set
from core._path import Paths


class GroupManager:
    """
    Spravuje perzistentný zoznam všetkých skupín (roles) a ich oprávnení
    poskytovaných rôznymi modulmi v systéme.
    Dáta sú uložené v config/system_groups.ini.
    """
    _instance = None

    @staticmethod
    def get_instance():
        if GroupManager._instance is None:
            GroupManager._instance = GroupManager(Paths.get_system_groups_ini())
        return GroupManager._instance

    def __init__(self, file_path=None):
        if GroupManager._instance is not None:
            raise Exception("Táto trieda je singleton!")
            
        self.path = Path(file_path if file_path else Paths.get_system_groups_ini())
        self.config = configparser.ConfigParser()
        self.reload() 
        GroupManager._instance = self

    def reload(self):
        """Načíta aktuálny stav zo súboru .ini."""
        self.config = configparser.ConfigParser() 
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.config.read(self.path, encoding='utf-8')

    def save(self):
        """Uloží aktuálny stav do súboru .ini."""
        with self.path.open("w", encoding='utf-8') as f:
            self.config.write(f)
            
    def get_all_groups(self) -> Dict[str, List[str]]:
        """
        Vráti všetky skupiny v systéme vo formáte {group_name: [perm1, perm2]}.
        """
        all_groups = {}
        self.reload()
        for group_name in self.config.sections():
            perms_str = self.config.get(group_name, 'permissions', fallback='').strip()
            all_groups[group_name] = [p.strip() for p in perms_str.split(',') if p.strip()]
        return all_groups
    
    def get_permissions_for_groups(self, group_names: List[str]) -> Set[str]:
        """
        Vezme zoznam názvov skupín a vráti sadu všetkých unikátnych oprávnení, 
        ktoré tieto skupiny poskytujú.
        """
        all_perms = set()
        all_system_groups = self.get_all_groups()
        for group_name in group_names:
            if group_name in all_system_groups:
                all_perms.update(all_system_groups[group_name])
        return all_perms

    def update_module_groups(self, module_name: str, groups_data: Dict[str, List[str]]):
        """
        Aktualizuje alebo pridá skupiny definované daným modulom.
        groups_data = {group_name: [perm1, perm2], ...}
        """
        sections_to_remove = [s for s in self.config.sections() if self.config.get(s, 'source_module', fallback='') == module_name]
        for section in sections_to_remove:
            self.config.remove_section(section)
            
        for group_name, permissions in groups_data.items():
            section_name = group_name
            if not self.config.has_section(section_name):
                self.config.add_section(section_name)
            
            self.config.set(section_name, 'source_module', module_name)
            self.config.set(section_name, 'permissions', ', '.join(permissions))
        
        self.save()