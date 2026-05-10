# Video Annotation Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-window PyQt6 desktop tool that loads a video, lets the user right-click a pixel to seed Lucas–Kanade point tracking ±10 frames, and visualizes the (x, y) trajectory on two stacked plots synced with a frame slider.

**Architecture:** Six-module Python package (`video_annotation/`). One direction of dependency: `main → main_window → {image_view, plots, tracker, video_source}`. Widgets are dumb (emit user-intent signals, accept render commands); state lives only in `MainWindow`. Tracker is a pure function; `VideoSource` is the only module that touches `cv2.VideoCapture`. Tests target the two non-Qt modules; widgets are validated by manual smoke tests.

**Tech Stack:** Python 3.11+, PyQt6, pyqtgraph, opencv-python, NumPy, pytest

**Spec:** `docs/superpowers/specs/2026-05-10-video-annotation-tool-design.md`

**Platform note:** All commands assume Windows + PowerShell. Replace `.venv\Scripts\python.exe` with `.venv/bin/python` on macOS/Linux.

---

## File Structure

```
VideoAnnotationTool/
├── pyproject.toml                 # project metadata + dependency list
├── test_video.mp4                 # bundled test fixture (already present)
├── video_annotation/
│   ├── __init__.py                # package marker (empty)
│   ├── __main__.py                # `python -m video_annotation` entry point — instantiates QApp + MainWindow
│   ├── video_source.py            # VideoSource class wrapping cv2.VideoCapture with LRU frame cache; VideoOpenError
│   ├── tracker.py                 # Trajectory dataclass; track() pure function running pyramidal LK ±10 frames
│   ├── image_view.py              # ImageView widget — zoom/pan/right-click, renders frame + marker
│   ├── plots.py                   # DualPlot widget — two stacked PlotWidgets, vertical line, click-to-seek
│   └── main_window.py             # MainWindow — assembles widgets, owns state, wires all signals
└── tests/
    ├── __init__.py                # package marker (empty)
    ├── conftest.py                # shared pytest fixture: path to test_video.mp4
    ├── test_video_source.py       # unit tests for VideoSource
    └── test_tracker.py            # unit tests for track() against test_video.mp4
```

Each Python module is expected to stay under ~150 lines. If `main_window.py` grows past ~250 lines during implementation, that's the signal to split out the signal-wiring helpers.

---

## Task 0: Project setup

**Files:**
- Create: `pyproject.toml`
- Create: `video_annotation/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create the package skeleton**

Create `video_annotation/__init__.py` with content:
```python
```
(empty file — package marker)

Create `tests/__init__.py` with content:
```python
```
(empty file)

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "video-annotation"
version = "0.1.0"
description = "Desktop video annotation tool with Lucas-Kanade point tracking"
requires-python = ">=3.11"
dependencies = [
    "PyQt6>=6.6",
    "pyqtgraph>=0.13",
    "opencv-python>=4.8",
    "numpy>=1.26",
]

[project.optional-dependencies]
dev = ["pytest>=7"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["video_annotation*"]
exclude = ["tests*"]
```

- [ ] **Step 3: Create `tests/conftest.py`**

```python
from pathlib import Path
import pytest

@pytest.fixture(scope="session")
def test_video_path() -> Path:
    """Path to the bundled test video at the project root."""
    path = Path(__file__).parent.parent / "test_video.mp4"
    assert path.exists(), f"test_video.mp4 missing at {path}"
    return path
```

- [ ] **Step 4: Install dependencies**

Run: `.venv\Scripts\python.exe -m pip install -e ".[dev]"`
Expected: install completes without errors; `pip list` shows PyQt6, pyqtgraph, opencv-python, numpy, pytest.

- [ ] **Step 5: Verify pytest discovers no tests yet**

Run: `.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: `no tests ran in <time>` (exit code 5 is fine — no tests collected).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml video_annotation/__init__.py tests/__init__.py tests/conftest.py
git commit -m "chore: scaffold video_annotation package and pytest setup"
```

---

## Task 1: `VideoSource` — open + dimensions

**Files:**
- Create: `video_annotation/video_source.py`
- Create: `tests/test_video_source.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_video_source.py`:
```python
import cv2
import pytest
from video_annotation.video_source import VideoSource, VideoOpenError


def test_open_test_video_reports_dimensions(test_video_path):
    src = VideoSource(str(test_video_path))
    try:
        # Cross-check VideoSource's reported dimensions against a direct cv2 read.
        cap = cv2.VideoCapture(str(test_video_path))
        try:
            assert src.total_frames == int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            assert src.width == int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            assert src.height == int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        finally:
            cap.release()
        assert src.total_frames > 0
        assert src.width > 0 and src.height > 0
    finally:
        src.close()


def test_open_missing_file_raises(tmp_path):
    bogus = tmp_path / "nope.mp4"
    with pytest.raises(VideoOpenError):
        VideoSource(str(bogus))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_video_source.py -v`
Expected: ImportError or ModuleNotFoundError because `video_annotation.video_source` doesn't exist yet.

- [ ] **Step 3: Implement minimal `VideoSource`**

Create `video_annotation/video_source.py`:
```python
from __future__ import annotations

import cv2


class VideoOpenError(RuntimeError):
    """Raised when a video file cannot be opened or has invalid metadata."""


class VideoSource:
    def __init__(self, path: str) -> None:
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            self._cap.release()
            raise VideoOpenError(f"could not open video: {path}")
        self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if self.total_frames <= 0 or self.width <= 0 or self.height <= 0:
            self._cap.release()
            raise VideoOpenError(
                f"invalid video metadata: frames={self.total_frames}, "
                f"size={self.width}x{self.height}"
            )

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_video_source.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add video_annotation/video_source.py tests/test_video_source.py
git commit -m "feat(video_source): open VideoCapture and expose dimensions"
```

---

## Task 2: `VideoSource.get_frame` with LRU cache

**Files:**
- Modify: `video_annotation/video_source.py`
- Modify: `tests/test_video_source.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_video_source.py`:
```python
import numpy as np


def test_get_frame_returns_bgr_array(test_video_path):
    src = VideoSource(str(test_video_path))
    try:
        frame = src.get_frame(0)
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (src.height, src.width, 3)
        assert frame.dtype == np.uint8
    finally:
        src.close()


def test_cache_avoids_redundant_reads(test_video_path):
    src = VideoSource(str(test_video_path))
    try:
        src.get_frame(5)
        reads_after_first = src._read_count
        # Same frame again — should hit cache, no new read.
        src.get_frame(5)
        assert src._read_count == reads_after_first
        # Different frame — should read.
        src.get_frame(6)
        assert src._read_count == reads_after_first + 1
    finally:
        src.close()


def test_get_frame_out_of_range_raises(test_video_path):
    src = VideoSource(str(test_video_path))
    try:
        with pytest.raises(IndexError):
            src.get_frame(-1)
        with pytest.raises(IndexError):
            src.get_frame(src.total_frames)
    finally:
        src.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_video_source.py -v`
Expected: three new tests FAIL with AttributeError (no `get_frame` method).

- [ ] **Step 3: Implement `get_frame` with cache**

Replace contents of `video_annotation/video_source.py`:
```python
from __future__ import annotations

from collections import OrderedDict
from typing import Optional

import cv2
import numpy as np


CACHE_SIZE = 64


class VideoOpenError(RuntimeError):
    """Raised when a video file cannot be opened or has invalid metadata."""


class VideoSource:
    def __init__(self, path: str) -> None:
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            self._cap.release()
            raise VideoOpenError(f"could not open video: {path}")
        self.total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if self.total_frames <= 0 or self.width <= 0 or self.height <= 0:
            self._cap.release()
            raise VideoOpenError(
                f"invalid video metadata: frames={self.total_frames}, "
                f"size={self.width}x{self.height}"
            )
        self._cache: "OrderedDict[int, np.ndarray]" = OrderedDict()
        self._read_count = 0  # exposed for tests

    def get_frame(self, index: int) -> np.ndarray:
        if index < 0 or index >= self.total_frames:
            raise IndexError(f"frame index {index} out of range [0, {self.total_frames})")

        cached = self._cache.get(index)
        if cached is not None:
            self._cache.move_to_end(index)
            return cached

        self._cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = self._cap.read()
        self._read_count += 1
        if not ok or frame is None:
            # Corrupt frame mid-stream — return a recent good frame if we have one,
            # and don't poison the cache with the bad index.
            if self._cache:
                last_index = next(reversed(self._cache))
                return self._cache[last_index]
            raise VideoOpenError(f"failed to read frame {index} and no fallback in cache")

        self._cache[index] = frame
        self._cache.move_to_end(index)
        if len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)
        return frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._cache.clear()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_video_source.py -v`
Expected: all five tests PASS.

- [ ] **Step 5: Commit**

```bash
git add video_annotation/video_source.py tests/test_video_source.py
git commit -m "feat(video_source): add get_frame with bounded LRU cache"
```

---

## Task 3: `tracker.Trajectory` dataclass + module constants

**Files:**
- Create: `video_annotation/tracker.py`
- Create: `tests/test_tracker.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tracker.py`:
```python
import pytest
from video_annotation.tracker import Trajectory, WINDOW


def test_window_is_ten():
    assert WINDOW == 10


def test_trajectory_dataclass_is_frozen():
    traj = Trajectory(seed_frame=42, points={42: (100.0, 200.0)})
    assert traj.seed_frame == 42
    assert traj.points[42] == (100.0, 200.0)
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        traj.seed_frame = 0  # type: ignore[misc]


def test_trajectory_membership_check():
    traj = Trajectory(seed_frame=10, points={10: (5.0, 5.0), 11: (6.0, 5.0)})
    assert 10 in traj.points
    assert 12 not in traj.points
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_tracker.py -v`
Expected: ModuleNotFoundError for `video_annotation.tracker`.

- [ ] **Step 3: Implement minimal `tracker.py`**

Create `video_annotation/tracker.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

import cv2


WINDOW = 10
LK_PARAMS = dict(
    winSize=(21, 21),
    maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
)


@dataclass(frozen=True)
class Trajectory:
    seed_frame: int
    points: dict[int, tuple[float, float]]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_tracker.py -v`
Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add video_annotation/tracker.py tests/test_tracker.py
git commit -m "feat(tracker): add Trajectory dataclass and LK constants"
```

---

## Task 4: `tracker.track` — forward propagation

**Files:**
- Modify: `video_annotation/tracker.py`
- Modify: `tests/test_tracker.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tracker.py`:
```python
from video_annotation.tracker import track
from video_annotation.video_source import VideoSource


def test_track_seed_frame_always_present(test_video_path):
    src = VideoSource(str(test_video_path))
    try:
        seed = min(20, src.total_frames - 1)
        x, y = src.width / 2, src.height / 2
        traj = track(src, seed, x, y)
        assert traj.seed_frame == seed
        assert seed in traj.points
        assert traj.points[seed] == (x, y)
    finally:
        src.close()


def test_track_forward_within_bounds(test_video_path):
    src = VideoSource(str(test_video_path))
    try:
        # Seed in the middle so forward+backward have room.
        seed = src.total_frames // 2
        x, y = src.width / 2, src.height / 2
        traj = track(src, seed, x, y)
        forward_frames = [f for f in traj.points if f > seed]
        # At most WINDOW forward points; each within frame bounds.
        assert len(forward_frames) <= 10
        for f in forward_frames:
            px, py = traj.points[f]
            assert 0 <= px < src.width
            assert 0 <= py < src.height
    finally:
        src.close()


def test_track_clamps_at_video_end(test_video_path):
    src = VideoSource(str(test_video_path))
    try:
        # Seed near the end — forward walk can't go past total_frames - 1.
        seed = src.total_frames - 1
        x, y = src.width / 2, src.height / 2
        traj = track(src, seed, x, y)
        assert max(traj.points) <= src.total_frames - 1
        # No forward propagation possible.
        assert all(f <= seed for f in traj.points)
    finally:
        src.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_tracker.py -v`
Expected: three new tests FAIL with ImportError or "track is not defined".

- [ ] **Step 3: Implement `track` with forward walk only**

Replace contents of `video_annotation/tracker.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from video_annotation.video_source import VideoSource


WINDOW = 10
LK_PARAMS = dict(
    winSize=(21, 21),
    maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
)


@dataclass(frozen=True)
class Trajectory:
    seed_frame: int
    points: dict[int, tuple[float, float]]


def _to_gray(frame_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)


def track(video: VideoSource, seed_frame: int, x: float, y: float) -> Trajectory:
    points: dict[int, tuple[float, float]] = {seed_frame: (x, y)}
    seed_gray = _to_gray(video.get_frame(seed_frame))

    # Forward walk
    prev_gray = seed_gray
    prev_pt = np.array([[x, y]], dtype=np.float32)
    for k in range(1, WINDOW + 1):
        target = seed_frame + k
        if target > video.total_frames - 1:
            break
        next_gray = _to_gray(video.get_frame(target))
        new_pts, status, _ = cv2.calcOpticalFlowPyrLK(
            prev_gray, next_gray, prev_pt, None, **LK_PARAMS
        )
        if status[0, 0] == 0:
            break
        nx, ny = float(new_pts[0, 0]), float(new_pts[0, 1])
        points[target] = (nx, ny)
        prev_gray = next_gray
        prev_pt = new_pts

    return Trajectory(seed_frame=seed_frame, points=points)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_tracker.py -v`
Expected: all six tests PASS.

- [ ] **Step 5: Commit**

```bash
git add video_annotation/tracker.py tests/test_tracker.py
git commit -m "feat(tracker): forward Lucas-Kanade propagation up to N+10"
```

---

## Task 5: `tracker.track` — backward propagation

**Files:**
- Modify: `video_annotation/tracker.py`
- Modify: `tests/test_tracker.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_tracker.py`:
```python
def test_track_backward_within_bounds(test_video_path):
    src = VideoSource(str(test_video_path))
    try:
        seed = src.total_frames // 2
        x, y = src.width / 2, src.height / 2
        traj = track(src, seed, x, y)
        backward_frames = [f for f in traj.points if f < seed]
        assert len(backward_frames) <= 10
        for f in backward_frames:
            assert f >= 0
            px, py = traj.points[f]
            assert 0 <= px < src.width
            assert 0 <= py < src.height
    finally:
        src.close()


def test_track_clamps_at_video_start(test_video_path):
    src = VideoSource(str(test_video_path))
    try:
        seed = 0
        x, y = src.width / 2, src.height / 2
        traj = track(src, seed, x, y)
        assert min(traj.points) >= 0
        # No backward propagation possible.
        assert all(f >= seed for f in traj.points)
    finally:
        src.close()


def test_track_consecutive_points_are_close(test_video_path):
    """Sanity: LK on a normal video shouldn't jump huge distances frame-to-frame."""
    src = VideoSource(str(test_video_path))
    try:
        seed = src.total_frames // 2
        # Pick a point likely to be on something textured (avoid pure center).
        x, y = src.width * 0.4, src.height * 0.4
        traj = track(src, seed, x, y)
        sorted_frames = sorted(traj.points)
        for a, b in zip(sorted_frames, sorted_frames[1:]):
            if b - a == 1:  # adjacent frames only
                ax, ay = traj.points[a]
                bx, by = traj.points[b]
                # 100 px is generous — well-behaved video should be much less.
                assert abs(bx - ax) < 100, f"jump {a}->{b}: dx={bx-ax}"
                assert abs(by - ay) < 100, f"jump {a}->{b}: dy={by-ay}"
    finally:
        src.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv\Scripts\python.exe -m pytest tests/test_tracker.py -v`
Expected: `test_track_backward_within_bounds` and possibly `test_track_clamps_at_video_start` FAIL because there's no backward walk yet (no points with `f < seed`).

- [ ] **Step 3: Add backward walk to `track`**

Replace the `track` function in `video_annotation/tracker.py`:
```python
def track(video: VideoSource, seed_frame: int, x: float, y: float) -> Trajectory:
    points: dict[int, tuple[float, float]] = {seed_frame: (x, y)}
    seed_gray = _to_gray(video.get_frame(seed_frame))

    # Forward walk
    prev_gray = seed_gray
    prev_pt = np.array([[x, y]], dtype=np.float32)
    for k in range(1, WINDOW + 1):
        target = seed_frame + k
        if target > video.total_frames - 1:
            break
        next_gray = _to_gray(video.get_frame(target))
        new_pts, status, _ = cv2.calcOpticalFlowPyrLK(
            prev_gray, next_gray, prev_pt, None, **LK_PARAMS
        )
        if status[0, 0] == 0:
            break
        nx, ny = float(new_pts[0, 0]), float(new_pts[0, 1])
        points[target] = (nx, ny)
        prev_gray = next_gray
        prev_pt = new_pts

    # Backward walk
    prev_gray = seed_gray
    prev_pt = np.array([[x, y]], dtype=np.float32)
    for k in range(1, WINDOW + 1):
        target = seed_frame - k
        if target < 0:
            break
        next_gray = _to_gray(video.get_frame(target))
        new_pts, status, _ = cv2.calcOpticalFlowPyrLK(
            prev_gray, next_gray, prev_pt, None, **LK_PARAMS
        )
        if status[0, 0] == 0:
            break
        nx, ny = float(new_pts[0, 0]), float(new_pts[0, 1])
        points[target] = (nx, ny)
        prev_gray = next_gray
        prev_pt = new_pts

    return Trajectory(seed_frame=seed_frame, points=points)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv\Scripts\python.exe -m pytest tests/test_tracker.py -v`
Expected: all nine tracker tests PASS.

- [ ] **Step 5: Commit**

```bash
git add video_annotation/tracker.py tests/test_tracker.py
git commit -m "feat(tracker): backward Lucas-Kanade propagation down to N-10"
```

---

## Task 6: `ImageView` — frame display + zoom + pan

**Files:**
- Create: `video_annotation/image_view.py`

This widget has no automated tests (per spec). Validation is a smoke test at the end.

- [ ] **Step 1: Implement `ImageView`**

Create `video_annotation/image_view.py`:
```python
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
```

- [ ] **Step 2: Smoke-test the widget standalone**

Create a temporary script `_smoke_image_view.py` at the project root:
```python
import sys
import cv2
from PyQt6.QtWidgets import QApplication
from video_annotation.image_view import ImageView

app = QApplication(sys.argv)
view = ImageView()
view.resize(800, 600)
view.show()

cap = cv2.VideoCapture("test_video.mp4")
ok, frame = cap.read()
cap.release()
assert ok, "could not read test_video.mp4"
view.show_frame(frame, marker=(frame.shape[1] / 2, frame.shape[0] / 2))

view.point_clicked.connect(lambda x, y: print(f"clicked ({x:.1f}, {y:.1f})"))
sys.exit(app.exec())
```

Run: `.venv\Scripts\python.exe _smoke_image_view.py`
Expected:
- Window opens showing the first frame of `test_video.mp4`
- A red marker is centered on the frame
- Mouse wheel zooms (centered on cursor)
- Left-drag pans the view
- Right-click prints `clicked (x, y)` with original-frame pixel coords (verify by clicking near the marker — coords should be near frame center)

Close the window when satisfied.

- [ ] **Step 3: Delete the smoke-test script**

```bash
rm _smoke_image_view.py
```

- [ ] **Step 4: Commit**

```bash
git add video_annotation/image_view.py
git commit -m "feat(image_view): widget with zoom/pan and right-click annotation signal"
```

---

## Task 7: `DualPlot` — structure + ranges + vertical line

**Files:**
- Create: `video_annotation/plots.py`

- [ ] **Step 1: Implement `DualPlot` skeleton**

Create `video_annotation/plots.py`:
```python
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
```

- [ ] **Step 2: Smoke-test the widget standalone**

Create `_smoke_plots.py`:
```python
import sys
from PyQt6.QtWidgets import QApplication
from video_annotation.plots import DualPlot
from video_annotation.tracker import Trajectory

app = QApplication(sys.argv)
plot = DualPlot()
plot.resize(900, 300)
plot.configure(total_frames=300, frame_width=1920, frame_height=1080)

# Synthetic trajectory: frames 90..110 with a smooth curve.
points = {f: (50.0 + (f - 100) * 5, 200.0 + (f - 100) ** 2) for f in range(90, 111)}
plot.set_trajectory(Trajectory(seed_frame=100, points=points))
plot.set_current_frame(100)

plot.frame_clicked.connect(lambda i: print(f"seek to frame {i}"))
plot.show()
sys.exit(app.exec())
```

Run: `.venv\Scripts\python.exe _smoke_plots.py`
Expected:
- Two stacked plots appear
- A blue curve in each, only between frames 90 and 110, gaps elsewhere
- Vertical yellow dashed line at frame 100
- X-axis range is 0..299 on both plots, both linked
- Clicking anywhere on either plot prints "seek to frame <N>"

Close window.

- [ ] **Step 3: Delete the smoke-test script**

```bash
rm _smoke_plots.py
```

- [ ] **Step 4: Commit**

```bash
git add video_annotation/plots.py
git commit -m "feat(plots): dual-plot widget with linked x-axis, NaN-gap curves, click-to-seek"
```

---

## Task 8: `MainWindow` — layout shell + initial state

**Files:**
- Create: `video_annotation/main_window.py`

- [ ] **Step 1: Implement `MainWindow` skeleton (no Open Video flow yet)**

Create `video_annotation/main_window.py`:
```python
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
```

- [ ] **Step 2: Smoke-test the shell**

Create `_smoke_main_window.py`:
```python
import sys
from PyQt6.QtWidgets import QApplication
from video_annotation.main_window import MainWindow

app = QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec())
```

Run: `.venv\Scripts\python.exe _smoke_main_window.py`
Expected:
- Window titled "Video Annotation" opens (~1100×900)
- Three vertical regions: large image area (blank), thin disabled slider, two empty plots
- File menu has "Open Video…" (Ctrl+O) and "Quit" (Ctrl+Q)
- Ctrl+Q closes the window
- Status bar reads "No video loaded"

Close window.

- [ ] **Step 3: Delete the smoke-test script**

```bash
rm _smoke_main_window.py
```

- [ ] **Step 4: Commit**

```bash
git add video_annotation/main_window.py
git commit -m "feat(main_window): assemble layout shell with menu and disabled initial state"
```

---

## Task 9: `MainWindow` — Open Video flow

**Files:**
- Modify: `video_annotation/main_window.py`

- [ ] **Step 1: Wire up Open Video**

Add this method on `MainWindow` and connect the action. Replace the body of `__init__` after the menu setup with the version below, and add the `_open_video` method.

Update imports near the top:
```python
from pathlib import Path
from PyQt6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSlider,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
```

Connect the action at the end of `__init__`, just after `file_menu.addAction(self._open_action)`:
```python
        self._open_action.triggered.connect(self._open_video)
```

Add this method:
```python
    def _open_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Video",
            "",
            "Video files (*.mp4 *.avi *.mov *.mkv *.webm);;All files (*)",
        )
        if not path:
            return
        try:
            new_video = VideoSource(path)
        except Exception as e:
            QMessageBox.warning(self, "Open Video", f"Could not open video:\n{e}")
            return

        # Replace any existing video.
        if self._video is not None:
            self._video.close()
        self._video = new_video
        self._trajectory = None
        self._current_frame = 0

        self._slider.setEnabled(True)
        self._slider.setRange(0, max(0, new_video.total_frames - 1))
        self._slider.setValue(0)
        self._plots.configure(new_video.total_frames, new_video.width, new_video.height)
        self._plots.set_trajectory(None)
        self._plots.set_current_frame(0)
        self._image_view.show_frame(new_video.get_frame(0), marker=None)

        self.setWindowTitle(f"Video Annotation — {Path(path).name}")
        self._update_status()

    def _update_status(self) -> None:
        if self._video is None:
            self.statusBar().showMessage("No video loaded")
            return
        self.statusBar().showMessage(
            f"Frame {self._current_frame}/{self._video.total_frames - 1}"
            f"  •  {self._video.width}×{self._video.height}"
        )
```

- [ ] **Step 2: Smoke-test Open Video**

Create `_smoke_main_window.py`:
```python
import sys
from PyQt6.QtWidgets import QApplication
from video_annotation.main_window import MainWindow

app = QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec())
```

Run: `.venv\Scripts\python.exe _smoke_main_window.py`
Expected:
- Open via File → Open Video… → select `test_video.mp4`
- Window title becomes `Video Annotation — test_video.mp4`
- Status bar shows `Frame 0/<N-1>  •  <W>×<H>`
- Image view displays the first frame
- Slider becomes enabled with range 0..N-1
- Plots configured with appropriate ranges (visible blank axes)
- Try to open a non-video file (e.g. README.md) — `QMessageBox` warning appears, prior state preserved

Close window.

- [ ] **Step 3: Delete the smoke-test script**

```bash
rm _smoke_main_window.py
```

- [ ] **Step 4: Commit**

```bash
git add video_annotation/main_window.py
git commit -m "feat(main_window): Open Video flow with error handling and state reset"
```

---

## Task 10: `MainWindow` — frame-change synchronization

**Files:**
- Modify: `video_annotation/main_window.py`

- [ ] **Step 1: Add `set_current_frame` and wire slider + plot signals**

Update the imports at the top of `main_window.py`:
```python
from PyQt6.QtCore import Qt, QSignalBlocker
```

Add this method to `MainWindow`:
```python
    def set_current_frame(self, frame_idx: int) -> None:
        if self._video is None:
            return
        frame_idx = max(0, min(self._video.total_frames - 1, frame_idx))
        self._current_frame = frame_idx
        with QSignalBlocker(self._slider):
            self._slider.setValue(frame_idx)
        self._plots.set_current_frame(frame_idx)
        marker = self._trajectory.points.get(frame_idx) if self._trajectory else None
        self._image_view.show_frame(self._video.get_frame(frame_idx), marker=marker)
        self._update_status()
```

In `__init__`, just below `self._open_action.triggered.connect(self._open_video)`, add:
```python
        self._slider.valueChanged.connect(self.set_current_frame)
        self._plots.frame_clicked.connect(self.set_current_frame)
```

Also, in `_open_video`, **replace** these two lines:
```python
        self._plots.set_current_frame(0)
        self._image_view.show_frame(new_video.get_frame(0), marker=None)
```
with a single call:
```python
        self.set_current_frame(0)
```
Keep the `setRange` and `setValue(0)` lines on the slider (they still need to run before `set_current_frame` so the slider's range is valid).

- [ ] **Step 2: Smoke-test sync**

Create `_smoke_main_window.py`:
```python
import sys
from PyQt6.QtWidgets import QApplication
from video_annotation.main_window import MainWindow

app = QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec())
```

Run: `.venv\Scripts\python.exe _smoke_main_window.py` and open `test_video.mp4`.
Expected:
- Drag slider → image view shows the right frame; plots' yellow line follows; status bar updates
- Click on either plot → slider snaps to that frame; image updates; both plots' lines move
- No re-entrancy / oscillation (lock up, flicker, infinite events)

Close window.

- [ ] **Step 3: Delete the smoke-test script**

```bash
rm _smoke_main_window.py
```

- [ ] **Step 4: Commit**

```bash
git add video_annotation/main_window.py
git commit -m "feat(main_window): synchronize slider, image view, and plots on frame change"
```

---

## Task 11: `MainWindow` — annotation flow

**Files:**
- Modify: `video_annotation/main_window.py`

- [ ] **Step 1: Add `start_tracking` and wire image-view right-click**

Update imports at the top of `main_window.py`:
```python
from video_annotation.tracker import Trajectory, track
```
(replace the existing `from video_annotation.tracker import Trajectory`)

Add this method to `MainWindow`:
```python
    def start_tracking(self, x: float, y: float) -> None:
        if self._video is None:
            return
        # Bound the click to the frame; LK is forgiving but we shouldn't seed off-screen.
        if not (0 <= x < self._video.width and 0 <= y < self._video.height):
            return
        self._trajectory = track(self._video, self._current_frame, x, y)
        self._plots.set_trajectory(self._trajectory)
        # Re-render current frame so the new marker appears immediately.
        marker = self._trajectory.points.get(self._current_frame)
        self._image_view.show_frame(self._video.get_frame(self._current_frame), marker=marker)
```

In `__init__`, just below `self._plots.frame_clicked.connect(self.set_current_frame)`, add:
```python
        self._image_view.point_clicked.connect(self.start_tracking)
```

- [ ] **Step 2: Smoke-test annotation end-to-end**

Create `_smoke_main_window.py`:
```python
import sys
from PyQt6.QtWidgets import QApplication
from video_annotation.main_window import MainWindow

app = QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec())
```

Run: `.venv\Scripts\python.exe _smoke_main_window.py` and open `test_video.mp4`. Then:
- Move slider to a middle frame
- Right-click on a textured pixel in the image
- Expected: red marker appears on that pixel; both plot curves render with a 21-frame segment around the current frame and gaps elsewhere; yellow line is at the current frame; clicking near either end of the curve in a plot seeks there and the marker on the image follows the trajectory
- Right-click somewhere else on a different frame
- Expected: previous trajectory is replaced; only the new ±10 window is plotted

Close window.

- [ ] **Step 3: Delete the smoke-test script**

```bash
rm _smoke_main_window.py
```

- [ ] **Step 4: Commit**

```bash
git add video_annotation/main_window.py
git commit -m "feat(main_window): right-click triggers tracking and updates plots + marker"
```

---

## Task 12: `__main__.py` entry point

**Files:**
- Create: `video_annotation/__main__.py`

- [ ] **Step 1: Implement the entry point**

Create `video_annotation/__main__.py`:
```python
from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from video_annotation.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the app**

Run: `.venv\Scripts\python.exe -m video_annotation`
Expected: window opens. Open `test_video.mp4`, scrub, right-click to track, click plots to seek, Ctrl+Q to quit. No tracebacks in the terminal.

- [ ] **Step 3: Commit**

```bash
git add video_annotation/__main__.py
git commit -m "feat: package entry point (python -m video_annotation)"
```

---

## Task 13: Final end-to-end manual smoke test

**Files:** none

- [ ] **Step 1: Run the full test suite**

Run: `.venv\Scripts\python.exe -m pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 2: Run the app and exercise every feature**

Run: `.venv\Scripts\python.exe -m video_annotation`

Walk this checklist with `test_video.mp4`:
- [ ] **Open Video flow** — title updates, status bar populates, slider enables, first frame shows
- [ ] **Slider scrub** — image view follows; yellow line in both plots follows
- [ ] **Plot click seek** — clicking either plot snaps slider/image
- [ ] **Image zoom** — mouse wheel zooms in/out, centered on cursor
- [ ] **Image pan** — left-drag pans without resetting zoom
- [ ] **Persisting view** — zoom in, then scrub; the zoom level should persist across frames
- [ ] **Right-click annotation** — marker appears at the clicked pixel in original-frame coords (verify by zooming in first, then right-clicking; the marker should land where you clicked, not where the cursor was in screen space)
- [ ] **Trajectory plots** — both plots show a connected line for ~21 frames around the seed, gaps elsewhere
- [ ] **Marker persistence** — scrub through the ±10 window; marker tracks the propagated point each frame; outside the window, no marker
- [ ] **Replace annotation** — right-click somewhere else; old trajectory is gone, new one in its place
- [ ] **Edge clamping** — click near frame 0 (then right-click); only forward propagation visible. Click near the last frame (then right-click); only backward propagation visible
- [ ] **Bad file** — File → Open Video → pick `README.md`; warning dialog appears, app does not crash
- [ ] **Ctrl+O / Ctrl+Q** — both shortcuts work

- [ ] **Step 3: If any issue surfaces, file it as a follow-up task and fix before committing**

If everything passes: no commit needed (no changes).
