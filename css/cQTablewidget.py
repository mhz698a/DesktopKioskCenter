from PyQt6.QtWidgets import QTableWidget, QWidget, QAbstractItemView
from PyQt6.QtCore import Qt

from css.apply_qss import apply_css_sheet

class cQTableW(QTableWidget):
    def __init__(self, rows: int = 0, columns: int = 0, parent: QWidget = None):
        super().__init__(rows, columns, parent)
        
        # Configuraciones de comportamiento moderno y limpio
        self.setAlternatingRowColors(True) # Filas de colores alternos para mejor lectura
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # Selecciona filas completas
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # Selección única
        self.setShowGrid(False) # Oculta la cuadrícula clásica pesada
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus) # Elimina el molesto rectángulo de líneas punteadas al hacer clic
        
        # Ajustes de dimensiones por defecto para dar aire visual
        self.verticalHeader().setVisible(False) # Oculta los números de fila del lado izquierdo
        self.verticalHeader().setDefaultSectionSize(36) # Altura de fila cómoda y espaciosa
        self.horizontalHeader().setHighlightSections(False) # Evita que el encabezado cambie de color al hacer clic
        
        # Aplicación de los estilos QSS heredables
        self.setStyleSheet(apply_css_sheet("css/qtablewidget.css"))
