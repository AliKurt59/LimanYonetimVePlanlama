from PyQt6.QtWidgets import QGraphicsObject
from PyQt6.QtGui import QBrush, QColor, QPen
from PyQt6.QtCore import pyqtSignal, QRectF

class InteractiveRectItem(QGraphicsObject):
    """
    Üzerine gelindiğinde ve tıklandığında sinyal yayan,
    interaktif bir QGraphicsObject dikdörtgeni.
    """
    clicked = pyqtSignal(dict)

    def __init__(self, x, y, width, height, parent=None):
        super().__init__(parent)
        self._rect = QRectF(0, 0, width, height)
        self.setPos(x, y)
        self.setAcceptHoverEvents(True)
        self.original_brush = QBrush()
        self.hover_brush = QBrush(QColor(46, 204, 113, 150)) # Yeşilimsi hover rengi
        self._current_brush = self.original_brush
        self._pen = QPen()

    def setBrush(self, brush):
        self.original_brush = brush
        self._current_brush = brush
        self.update()

    def setPen(self, pen):
        self._pen = pen
        self._pen.setCosmetic(True)
        self.update()

    def boundingRect(self):
        return self._rect

    def paint(self, painter, option, widget=None):
        painter.setBrush(self._current_brush)
        painter.setPen(self._pen)
        painter.drawRect(self.boundingRect())

    def mousePressEvent(self, event):
        self.clicked.emit(self.data(0))
        event.accept()

    def hoverEnterEvent(self, event):
        data = self.data(0)
        # Sadece tıklanabilir/yerleştirilebilir item'lar için hover efekti uygula
        if data and (
            data.get('type') in ['block', 'bay', 'bay_overview'] or 
            data.get('placeable', False) or 
            data.get('placeable_for_relocation', False)
        ):
            self._current_brush = self.hover_brush
            self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._current_brush = self.original_brush
        self.update()
        super().hoverLeaveEvent(event)