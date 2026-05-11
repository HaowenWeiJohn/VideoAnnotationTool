from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal


class ImageView(pg.GraphicsLayoutWidget):
    """Displays a video frame with zoom/pan and emits right-click coords in original-frame space."""

    point_clicked = pyqtSignal(float, float)  # (x, y) in original frame coords

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._view = self.addViewBox()
        self._view.setAspectLocked(True)
        self._view.invertY(True)  # image coords: y grows downward
        self._view.setMouseMode(pg.ViewBox.PanMode)
        self._view.setMenuEnabled(False)  # don't pop the default right-click menu

        self._image_item = pg.ImageItem(axisOrder="row-major")
        self._view.addItem(self._image_item)

        self._marker = pg.ScatterPlotItem(
            size=14,
            pen=pg.mkPen("r", width=2),
            brush=pg.mkBrush(255, 90, 90, 60),
        )
        self._view.addItem(self._marker)

        # Right-click handling via the scene's mouse-click signal.
        self.scene().sigMouseClicked.connect(self._on_scene_clicked)

    def show_frame(
        self, frame_bgr: np.ndarray, marker: Optional[tuple[float, float]] = None
    ) -> None:
        # BGR -> RGB via slicing (no copy).
        self._image_item.setImage(frame_bgr[..., ::-1], autoLevels=False)
        if marker is None:
            self._marker.clear()
        else:
            self._marker.setData([marker[0]], [marker[1]])

    def clear(self) -> None:
        self._image_item.clear()
        self._marker.clear()

    def _on_scene_clicked(self, ev) -> None:
        if ev.button() != Qt.MouseButton.RightButton:
            return
        view_pos = self._view.mapSceneToView(ev.scenePos())
        self.point_clicked.emit(float(view_pos.x()), float(view_pos.y()))
        ev.accept()
