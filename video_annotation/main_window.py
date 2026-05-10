from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from video_annotation.image_view import ImageView
from video_annotation.plots import DualPlot
from video_annotation.tracker import Trajectory
from video_annotation.video_source import VideoSource


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Video Annotation")
        self.resize(1100, 900)

        # State
        self._video: Optional[VideoSource] = None
        self._current_frame: int = 0
        self._trajectory: Optional[Trajectory] = None

        # Widgets
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self._image_view = ImageView()
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._plots = DualPlot()

        layout.addWidget(self._image_view, stretch=4)
        layout.addWidget(self._slider, stretch=0)
        layout.addWidget(self._plots, stretch=2)

        # Initial disabled state — re-enabled on Open Video.
        self._slider.setEnabled(False)
        self._slider.setRange(0, 0)

        # Menu
        file_menu = self.menuBar().addMenu("&File")
        self._open_action = QAction("&Open Video…", self)
        self._open_action.setShortcut(QKeySequence("Ctrl+O"))
        file_menu.addAction(self._open_action)
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Status bar
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("No video loaded")
