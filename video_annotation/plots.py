from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
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

        # Disable user range manipulation — axes are display-only.
        for p in (self._plot_x, self._plot_y):
            p.setMouseEnabled(x=False, y=False)
            p.hideButtons()
            p.setMenuEnabled(False)

        self._curve_x = self._plot_x.plot(pen=pg.mkPen("#6c8eef", width=1.6), connect="finite")
        self._curve_y = self._plot_y.plot(pen=pg.mkPen("#6c8eef", width=1.6), connect="finite")

        self._vline_x = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#ffd370", style=Qt.PenStyle.DashLine))
        self._vline_y = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen("#ffd370", style=Qt.PenStyle.DashLine))
        self._plot_x.addItem(self._vline_x)
        self._plot_y.addItem(self._vline_y)

        self._total_frames = 0

        self._plot_x.scene().sigMouseClicked.connect(self._on_scene_clicked_x)
        self._plot_y.scene().sigMouseClicked.connect(self._on_scene_clicked_y)

    def configure(self, total_frames: int, frame_width: int, frame_height: int) -> None:
        self._total_frames = total_frames
        self._plot_x.setXRange(0, max(0, total_frames - 1), padding=0)
        self._plot_x.setYRange(0, max(0, frame_width - 1), padding=0)
        self._plot_y.setXRange(0, max(0, total_frames - 1), padding=0)
        self._plot_y.setYRange(0, max(0, frame_height - 1), padding=0)

    def set_current_frame(self, frame_idx: int) -> None:
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
