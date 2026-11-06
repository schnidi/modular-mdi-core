"""
Súbor: run.py
Hlavný spúšťač aplikácie z koreňového adresára projektu
s voliteľným čistením vyrovnávacej pamäte (__pycache__).
"""

import os
import sys
import shutil

# =============================================================================
# NASTAVENIE ČISTENIA CACHE (True / 1 = čistí, False / 0 = NEČISTÍ)
# =============================================================================
CLEANUP_CACHE = False


def cleanup_project_cache(root_dir: str):
    """
    Vymaže všetky __pycache__ priečinky a .pyc súbory v projekte
    a vypíše zoznam zmazaných položiek do konzoly.
    """
    ignore_dirs = {'.venv', 'venv', '.git', '.idea', '.vscode', 'node_modules', 'dist', 'build'}
    deleted_dirs_count = 0
    deleted_files_count = 0

    print("[Cache Cleaner] Kontrolujem a čistím vyrovnávaciu pamäť v projekte...")
    
    for current_root, dirs, files in os.walk(root_dir):
        # Preskočíme priečinky knižníc a git
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        # 1. Mazanie priečinkov __pycache__
        for d in list(dirs):
            if d == '__pycache__':
                cache_path = os.path.join(current_root, d)
                rel_path = os.path.relpath(cache_path, root_dir)
                try:
                    shutil.rmtree(cache_path, ignore_errors=True)
                    print(f"  [Zmazaný priečinok] {rel_path}")
                    deleted_dirs_count += 1
                except Exception as e:
                    print(f"  [Chyba mazania] {rel_path}: {e}")
                dirs.remove(d)

        # 2. Mazanie osirelých .pyc a .pyo súborov
        for f in files:
            if f.endswith(('.pyc', '.pyo')):
                file_path = os.path.join(current_root, f)
                rel_path = os.path.relpath(file_path, root_dir)
                try:
                    os.remove(file_path)
                    print(f"  [Zmazaný súbor] {rel_path}")
                    deleted_files_count += 1
                except Exception as e:
                    print(f"  [Chyba súboru] {rel_path}: {e}")

    if deleted_dirs_count == 0 and deleted_files_count == 0:
        print("[Cache Cleaner] Projekt je čistý (žiadna stará cache nenájdená).\n")
    else:
        print(f"[Cache Cleaner] Hotovo. Odstránených: {deleted_dirs_count} priečinkov cache, {deleted_files_count} súborov.\n")


# 1. Nastavenie koreňového priečinka projektu a pridanie do sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 2. Nastavenie pracovného priečinka na koreň
os.chdir(ROOT_DIR)

# 3. Vyčistenie vyrovnávacej pamäte iba vtedy, ak je to povolené
if CLEANUP_CACHE:
    cleanup_project_cache(ROOT_DIR)

# 4. Import a spustenie funkcie main z core/main.py
from core.main import main

if __name__ == "__main__":
    main()