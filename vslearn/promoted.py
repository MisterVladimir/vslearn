# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QGraphicsView
from typing import Tuple


class WGraphicsView(QGraphicsView):
    """
    Zoomable GraphicsView.
    """
    # minimum image view size
    minimum_size: Tuple[int, int] = (256, 256)
    # sensitivity to zoom
    zoom_rate: float = 1.1

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.scene().selectedItems():
            super().wheelEvent(event)
        else:
            factor = self.zoom_rate**(event.angleDelta().y() / 120.)
            self.scale(factor, factor)

    @pyqtSlot()
    def zoom_in(self) -> None:
        self.scale(self.zoom_rate, self.zoom_rate)

    @pyqtSlot()
    def zoom_out(self) -> None:
        self.scale(1. / self.zoom_rate, 1. / self.zoom_rate)

    @pyqtSlot()
    def fit_to_window(self) -> None:
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
