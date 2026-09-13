from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QMouseEvent, QCursor

class IconButtonWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, icon_path: str, text: str, parent=None):
        super().__init__(parent)
        
        # Povie widgetu, aby rešpektoval štýly pozadia z QSS
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.setFixedSize(120, 100)
        
        # Nastaví kurzor myši na "ručičku", keď je nad widgetom
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.svg_widget = QSvgWidget(icon_path)
        self.svg_widget.setFixedSize(64, 64)
        
        self.label = QLabel(text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        self.label.setWordWrap(True)

        layout.addWidget(self.svg_widget, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.label, 1)

    def mousePressEvent(self, event: QMouseEvent):
        # Táto a nasledujúca metóda by mohli byť nahradené :pressed v QSS,
        # ale pre istotu ich tu nechávame pre robustnosť.
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        # Overíme, či sa kliknutie uvoľnilo nad widgetom, aby sa akcia nespustila omylom
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)