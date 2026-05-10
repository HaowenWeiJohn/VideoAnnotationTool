from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from video_annotation.tracker import Trajectory


class DualPlot(QWidget):
    """Two stacked plots (x and y of tracked point vs. frame number)."""

    frame_clicked = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._plot_x = pg.PlotWidget()
        self._plot_y = pg.PlotWidget()
        layout.addWidget(self._plot_x)
        layout.addWidget(self._plot_y)

        self._plot_x.setLabel("left", "x (px)")
        self._plot_y.setLabel("left", "y (px)")
        self._plot_y.setLabel("bottom", "frame")
        self._plot_x.getPlotItem().showAxis("bottom", True)
        self._plot_x.setXLink(self._plot_y)

        # Allow zoom/pan: X axis is shared (via setXLink above), Y is per-plot.
        # Click-to-seek still works — pyqtgraph distinguishes click events from drags.
        # StrongFocus + an event filter lets Left/Right arrow keys step frames
        # once the user has clicked on a plot.
        for p in (self._plot_x, self._plot_y):
            p.setMouseEnabled(x=True, y=True)
            p.hideButtons()
            p.setMenuEnabled(False)
            p.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            p.installEventFilter(self)

        curve_style = dict(
            pen=pg.mkPen("#6c8eef", width=1.6),
            symbol="o",
            symbolSize=6,
            symbolBrush=pg.mkBrush("#6c8eef"),
            symbolPen=pg.mkPen(None),
            connect="finite",
        )
        self._curve_x = self._plot_x.plot(**curve_style)
        self._curve_y = self._plot_y.plot(**curve_style)

        self._vline_x = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#ffd370", style=Qt.PenStyle.DashLine))
        self._vline_y = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#ffd370", style=Qt.PenStyle.DashLine))
        self._plot_x.addItem(self._vline_x)
        self._plot_y.addItem(self._vline_y)

        self._total_frames = 0
        self._current_frame = 0

        self._plot_x.scene().sigMouseClicked.connect(self._on_scene_clicked_x)
        self._plot_y.scene().sigMouseClicked.connect(self._on_scene_clicked_y)

    def configure(self, total_frames: int, frame_width: int, frame_height: int) -> None:
        self._total_frames = total_frames
        x_max = max(0, total_frames - 1)
        y_max_x = max(0, frame_width - 1)
        y_max_y = max(0, frame_height - 1)
        self._plot_x.setXRange(0, x_max, padding=0)
        self._plot_x.setYRange(0, y_max_x, padding=0)
        self._plot_y.setXRange(0, x_max, padding=0)
        self._plot_y.setYRange(0, y_max_y, padding=0)
        # Bound user zoom/pan to the data range so they can't get lost in empty space.
        self._plot_x.getViewBox().setLimits(xMin=0, xMax=x_max, yMin=0, yMax=y_max_x)
        self._plot_y.getViewBox().setLimits(xMin=0, xMax=x_max, yMin=0, yMax=y_max_y)

    def set_current_frame(self, frame_idx: int) -> None:
        self._current_frame = frame_idx
        self._vline_x.setPos(frame_idx)
        self._vline_y.setPos(frame_idx)

    def set_trajectory(self, trajectory: Optional[Trajectory]) -> None:
        if trajectory is None or self._total_frames == 0:
            self._curve_x.clear()
            self._curve_y.clear()
            return
        xs = np.arange(self._total_frames, dtype=float)
        ys_x = np.full(self._total_frames, np.nan, dtype=float)
        ys_y = np.full(self._total_frames, np.nan, dtype=float)
        for f, (px, py) in trajectory.points.items():
            ys_x[f] = px
            ys_y[f] = py
        self._curve_x.setData(xs, ys_x, connect="finite")
        self._curve_y.setData(xs, ys_y, connect="finite")

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.KeyPress and self._total_frames > 0:
            key = event.key()
            if key == Qt.Key.Key_Left:
                self.frame_clicked.emit(max(0, self._current_frame - 1))
                return True
            if key == Qt.Key.Key_Right:
                self.frame_clicked.emit(min(self._total_frames - 1, self._current_frame + 1))
                return True
        return super().eventFilter(obj, event)

    def _on_scene_clicked_x(self, ev) -> None:
        self._handle_scene_click(self._plot_x, ev)

    def _on_scene_clicked_y(self, ev) -> None:
        self._handle_scene_click(self._plot_y, ev)

    def _handle_scene_click(self, plot: pg.PlotWidget, ev) -> None:
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        if self._total_frames == 0:
            return
        view_pos = plot.getPlotItem().vb.mapSceneToView(ev.scenePos())
        idx = int(round(view_pos.x()))
        idx = max(0, min(self._total_frames - 1, idx))
        self.frame_clicked.emit(idx)
