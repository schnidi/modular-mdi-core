# 🖥️ PyQt6 Modular MDI Desktop Framework

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://pypi.org/project/PyQt6/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPLv3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

A modern, frameless desktop core built with **PyQt6**, designed as a universal foundation for modular desktop applications. It enables developers to easily build, install, and manage standalone sub-windows (plugins) within a single unified workspace.

---

## 🌟 Key Core Features

### 🪟 Advanced Frameless MDI Interface (Multi-Document Interface)
* **100% Frameless Architecture:** Both the main window and all nested MDI sub-windows feature custom native-like title bars (`CustomTitleBar`, `CustomTitleBarMdi`) with complete support for minimize, maximize, and restore operations.
* **Precision 6px Resize Engine:** Uses Qt's native `WA_Hover` event system for seamless, responsive window border resizing without cursor lag or flickering.
* **Window Bounds Guard (`WindowBoundsManager`):** Guarantees that dialogs and sub-windows never overflow beyond screen boundaries or clip beneath the top bar.
* **Layout & Geometry Persistence:** Automatically records and restores exact pixel geometry, coordinates, and display modes (normal, minimized, maximized) across sessions via `.ini` configuration files.

### 🧩 Modular Hot-Plug Plugin Engine
* **Runtime ZIP Installation:** Install, activate, or remove plugins directly from `.zip` archives using the built-in Module Manager without restarting the application.
* **Standardized Interface (`module_interface.py`):** Clean, declarative schema for plugins to register their windows, menus, and actions.
* **ServiceManager (IoC Registry):** A centralized service container allowing independent modules to register and consume shared services without tight coupling or hard imports.

### 🎨 Theming & Localization
* **Dynamic QSS Theming Engine:** Runtime switching between dark and light themes with automatic dynamic path resolution (`@ICON_DIR@`, `@THEMES_DIR@`).
* **Multi-language Support (`LanguageManager`):** Centralized translation engine powered by JSON resource files *(module in development)*.
* **Asynchronous Multi-threaded Startup:** Smooth, non-blocking background initialization paired with a responsive Splash Screen.

---

## 🏗️ Project Architecture

```text
core/
├── config/          # .ini configurations (windows, modules, themes)
├── logic/           # Core controllers, Module Manager, ServiceManager IoC
├── themes/          # QSS stylesheets and vector SVG icons
├── ui/              # Qt Designer templates (.ui files)
└── windows/         # View components (MainWindow, MDI sub-windows, dialogs)
modules/             # Workspace for external plugins / custom modules
```

---

## 🚀 Quick Start

### 1. Prerequisites
* Python 3.10 or higher
* PyQt6

### 2. Installation & Launch

```bash
# Clone the repository
git clone https://github.com/schnidi/modular-mdi-core.git
cd modular-mdi-core

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Linux / macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install PyQt6 requests

# Navigate to the core directory and run the application
cd core
python main.py
```

---

## 📦 Installing Plugins from ZIP

Plugins for this framework are distributed as standalone `.zip` archives. To install and use a plugin:

1. **Download the Plugin:** Download the target plugin as a `.zip` archive.
2. **Open Module Manager:** In the application menu, navigate to **Settings** (`Nastavenie`) $\rightarrow$ **Module Manager...** (`Správca Modulov...`).
3. **Install from Archive:** Click the **Install from ZIP...** (`Inštalovať zo ZIP...`) button and select the downloaded `.zip` file.
4. **Activate the Plugin:** Once extracted and validated by the core, check the checkbox next to the module name and click **Apply Changes** (`Použiť zmeny`).

The plugin’s windows, menu entries, and background services will be immediately loaded into the workspace without requiring an application restart.

---

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0 (GNU AGPLv3)**.  
See the [LICENSE](LICENSE) file for more details.
