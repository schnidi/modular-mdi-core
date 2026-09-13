# Súbor: modules/control_panel/logic/flow_layout.py

from PyQt6.QtWidgets import QLayout, QStyle, QWidgetItem
from PyQt6.QtCore import Qt, QPoint, QRect, QSize

class FlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    # --- ZAČIATOK ZMENY: Pridanie chýbajúcej metódy ---
    def insertWidget(self, index, widget):
        """
        Pridá widget do layoutu na špecifický index.
        """
        # Najprv pridáme widget štandardným spôsobom.
        # Tým sa zabezpečí správne rodičovstvo a vytvorenie QWidgetItem.
        # Widget sa dočasne pridá na koniec nášho zoznamu.
        self.addWidget(widget)
        
        # Teraz zoberieme položku z konca zoznamu...
        item = self.itemList.pop()
        
        # ... a vložíme ju na správne miesto určené indexom.
        self.itemList.insert(index, item)
        
        # Informujeme layout, že sa zmenil a je potrebné ho prekresliť.
        self.update()
    # --- KONIEC ZMENY ---

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margin, _, _, _ = self.getContentsMargins()
        size += QSize(2 * margin, 2 * margin)
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0

        spacing = self.spacing()

        for item in self.itemList:
            wid = item.widget()
            space_x = spacing
            space_y = spacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()