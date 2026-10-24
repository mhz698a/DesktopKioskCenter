from PyQt6.QtWidgets import (QToolBar, QWidget)
from PyQt6.QtCore import Qt

from css.apply_qss import apply_css_sheet

class cQToolbar(QToolBar):
    def __init__(self, title: str = "", parent: QWidget = None):
        super().__init__(title, parent)
        
        self.setMovable(False)
        self.setFloatable(False)
        self.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea | Qt.ToolBarArea.BottomToolBarArea)
        
        self.setStyleSheet(apply_css_sheet("css/qtoolbar.css"))