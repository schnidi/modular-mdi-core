"""
Súbor: core/windows/error_dialog.py
Vlastný dialóg pre zobrazenie detailných a čitateľných chybových hlásení v téme.
"""
from core.windows.custom_message_box import CustomMessageBox

def show_error_dialog(title: str, main_text: str, detailed_text: str, parent=None):
    """Zobrazí chybu v našom bezrámovom okne s rozklikávacím detailom."""
    CustomMessageBox.critical(parent, title=title, text=main_text, detailed_text=detailed_text)