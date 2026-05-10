# Video Annotation Tool — Design (v1)

**Date:** 2026-05-10
**Status:** Approved for implementation planning
**Stack:** Python, PyQt6, pyqtgraph, OpenCV (`cv2`), NumPy

## Goal

A single-window desktop tool that loads a video, lets the user right-click any
pixel on any frame to seed a tracked point, propagates that point ±10 frames
with Lucas–Kanade optical flow, and visualizes the resulting (x, y) trajectory
on two stacked plots synchronized with a frame slider.

## Layout

One main window with three vertically stacked regions:

1. **Image view** (top, takes most vertical space) — shows the current frame.
2. **Frame slider** (middle, thin) — `QSlider`, range `[0, total_frames-1]`.
3. **Dual plot** (bottom) — two stacked `pyqtgraph.PlotWidget`s sharing an
   x-axis (frame number).

A `File` menu with `Open Video…` (Ctrl+O) and `Quit` (Ctrl+Q). A status bar
showing `Frame {i}/{total-1}  •  {width}×{height}`.

## Architecture

Six modules, dependencies flowing one way:

```
main.py
   │
   └──> main_window.py   (assembles widgets, owns AppState, wires signals)
            │
            ├──> image_view.py    (zoom/pan, right-click → point_clicked signal)
            ├──> plots.py         (dual PlotWidget, vertical line, click-to-seek)
            ├──> tracker.py       (pure: track(video, frame, x, y) -> Trajectory)
            └──> video_source.py  (VideoCapture + LRU frame cache)
```

**Boundaries:**

- `video_source` is the *only* module that touches `cv2.VideoCapture`. Everyone
  else gets numpy arrays.
- `tracker` is a pure function; no Qt imports. Testable in isolation against
  `test_video.mp4`.
- `image_view` and `plots` are dumb widgets that emit user-intent signals and
  accept render commands. They never talk to each other.
- `main_window` is the *only* place that holds state and wires signals.

## Core types

```python
# tracker.py
@dataclass(frozen=True)
class Trajectory:
    seed_frame: int                            # frame N where user clicked
    points: dict[int, tuple[float, float]]     # frame_index -> (x, y) in original coords
    # Frames outside ±10 of seed_frame, or where LK failed, are absent from points.
```

`frame_index in trajectory.points` answers both "should I draw a marker on this
frame?" and "should the plot have a gap here?".

## State

`MainWindow` holds:

- `video: VideoSource | None`
- `current_frame: int` (0 if no video)
- `trajectory: Trajectory | None`

No state lives anywhere else. Widgets are stateless w.r.t. domain data — they
hold only their own visual state (zoom level, scatter item handles, etc.).

## Signals and data flow

**Widget-emitted signals (user intent):**

| Source                   | Signal                              | Payload                  |
| ------------------------ | ----------------------------------- | ------------------------ |
| `image_view`             | `point_clicked(x: float, y: float)` | original-frame coords    |
| `plots`                  | `frame_clicked(i: int)`             | frame index              |
| `slider`                 | `valueChanged(i: int)`              | Qt built-in              |
| `open_video_action`      | `triggered()`                       | menu                     |

**Flow 1 — frame change** (slider moved, plot clicked, or programmatic):

```
any source -> main_window.set_current_frame(i):
    with QSignalBlocker(slider): slider.setValue(i)
    plots.set_current_frame(i)                    # moves vertical line
    frame = video.get_frame(i)
    marker = trajectory.points.get(i) if trajectory else None
    image_view.show_frame(frame, marker=marker)
```

`QSignalBlocker` around the slider prevents re-entrancy when the slider is
driven from a plot click.

**Flow 2 — new annotation** (right-click in image view):

```
image_view.point_clicked(x, y) -> main_window.start_tracking(current_frame, x, y):
    trajectory = tracker.track(video, current_frame, x, y)
    plots.set_trajectory(trajectory)              # redraws curves with NaN gaps
    image_view.show_frame(current_frame_bgr, marker=trajectory.points[current_frame])
```

Subsequent right-click overwrites `trajectory` unconditionally — only one
annotation exists at a time.

## Component internals

### `video_source.VideoSource`

- Wraps `cv2.VideoCapture`. Exposes `total_frames`, `width`, `height`,
  `get_frame(i: int) -> np.ndarray` (BGR).
- LRU cache of ~64 most recently read frames (`functools.lru_cache` with a
  bound method, or an explicit `collections.OrderedDict`).
- `get_frame` calls `cap.set(CAP_PROP_POS_FRAMES, i)` then `cap.read()` on a
  cache miss.
- Open path:
  - `cap = cv2.VideoCapture(path)`
  - Validate `cap.isOpened() and total_frames > 0 and width > 0 and height > 0`
  - On failure, raise `VideoOpenError` (custom exception defined in this module).

### `image_view.ImageView` (subclass of `pyqtgraph.GraphicsView` + `ViewBox`)

- `pyqtgraph.ImageItem` for the frame; `ScatterPlotItem` for the marker (one
  point).
- **Zoom**: override `wheelEvent` → `view_box.scaleBy(factor, center=mouse_scene_pos)`.
  pyqtgraph computes the cursor-centered transform.
- **Pan**: pyqtgraph's built-in left-drag pan (`MouseMode.PanMode`).
- **Right-click**: override `mousePressEvent`; on `Qt.RightButton`, map scene
  → view via `ViewBox.mapSceneToView` to get original-frame pixel coords. Emit
  `point_clicked(x, y)`.
- **`show_frame(frame_bgr, marker)`**: `image_item.setImage(frame_bgr[..., ::-1])`
  (BGR→RGB via slicing — no copy), then `scatter.setData([m.x], [m.y])` if
  marker else `scatter.clear()`.
- **Crucial**: `show_frame` does *not* reset the view range — the user's
  zoom/pan persists across frame changes.

### `plots.DualPlot` (a `QWidget` containing two stacked `pyqtgraph.PlotWidget`s)

- `plot1.setXLink(plot2)`. X range fixed to `[0, total_frames-1]`.
- Plot 1 Y range fixed to `[0, frame_width-1]`; Plot 2 Y range fixed to
  `[0, frame_height-1]`. Disable user range manipulation on both axes — these
  are display-only.
- **Trajectory line**: build x/y arrays of length `total_frames` filled with
  `np.nan`, then write the known values. `pg.PlotDataItem(x, y, connect='finite')`
  renders NaNs as gaps. No manual segmentation.
- **Vertical line**: one `pg.InfiniteLine(angle=90, movable=False)` per plot.
  `set_current_frame(i)` calls `line.setPos(i)`.
- **Click-to-seek**: connect each plot's `scene().sigMouseClicked` — on
  left-click, map scene → view, take the x value, round, clamp, emit
  `frame_clicked(i)`.

### `tracker.track(video, seed_frame, x, y) -> Trajectory`

Pure function. Walks forward and backward from `seed_frame` independently.

Module-level constants:

```python
WINDOW = 10
LK_PARAMS = dict(
    winSize=(21, 21),
    maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
)
```

**Forward walk:**
- `prev_pt = (x, y)`; `prev_gray = gray(video.get_frame(seed_frame))`
- For `k in 1..WINDOW`:
  - `target = seed_frame + k`. If `target > total_frames - 1`, stop.
  - `next_gray = gray(video.get_frame(target))`
  - `pts, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, next_gray,
    np.array([prev_pt], np.float32), None, **LK_PARAMS)`
  - If `status[0] == 0`, **stop forward propagation** — no further forward
    points are recorded. (LK failure → trajectory ends here on this side.)
  - Else `points[target] = tuple(pts[0])`; `prev_pt = pts[0]`; `prev_gray = next_gray`.

**Backward walk:** symmetric. For `k in 1..WINDOW`: `target = seed_frame - k`,
stop if `target < 0` or if LK reports failure on that step.

**Always:** `points[seed_frame] = (x, y)`, regardless of either walk's outcome.

LK requires grayscale; tracker converts on demand. Frames stay BGR in the
cache (so `image_view` can reuse them without re-reading).

## Error handling

Boundaries only — no try/except inside core logic.

1. **`VideoSource.open(path)`** — raises `VideoOpenError` if `cap.isOpened()`
   is false or dimensions/frame-count are zero. `main_window` catches and
   shows a `QMessageBox.warning`; existing state is preserved.
2. **`VideoSource.get_frame(i)`** — if `cap.read()` returns `(False, _)`
   (corrupt mid-file frame), return the last successfully decoded frame and
   skip caching the bad index.
3. **Pre-load guards** — `MainWindow.start_tracking` and
   `set_current_frame` no-op when `video is None`. Slider and menu items
   are disabled before a video is loaded; image view ignores right-clicks.

LK "failure" (`status[0] == 0`) is normal control flow, not an exception.

## UX details

- **Window title**: `"Video Annotation — <basename>"` after open, else
  `"Video Annotation"`.
- **Status bar**: `"Frame {i}/{total-1}  •  {width}×{height}"`.
- **Menu**: `File` only — `Open Video…` (Ctrl+O), `Quit` (Ctrl+Q).
- **Initial state**: blank gray image, empty plots, disabled slider.
- No "tracking…" indicator — sync tracking is fast enough that flicker would
  be the dominant effect.

## Testing

- **`tracker.py`** — unit-test against `test_video.mp4`. Pick a textured pixel,
  assert the returned `Trajectory` has `seed_frame` populated, length ≤ 21,
  and consecutive points are within a few pixels of each other (sanity, not
  an accuracy regression test).
- **`video_source.py`** — open `test_video.mp4`, assert `total_frames`,
  `width`, `height` match `ffprobe`. Exercise the cache with a synthetic
  access pattern; assert hit/miss counts.
- **No GUI tests.** Headless PyQt6 + pyqtgraph testing is high-friction for
  a single-developer tool; the value isn't there for v1. Manual smoke-test
  against `test_video.mp4` is the sign-off gate.

## Deliberately out of scope for v1

- Persisting trajectories to disk
- Multiple simultaneous annotations
- A "tracking failed" indicator in the UI (failures render as gaps only —
  user-confirmed, leave implicit)
- Forward-backward consistency check, `cornerSubPix` refinement, template
  fallback (referenced in `docs/point-tracking-options.md` as future options)
- Async / cancellable tracking
- Video playback (no play/pause; navigation is via slider, plot click)
- Keyboard shortcuts beyond Ctrl+O / Ctrl+Q
- Resizing/refitting behavior beyond Qt defaults

## Decisions made during brainstorming

| Question                                         | Choice                              |
| ------------------------------------------------ | ----------------------------------- |
| Tracking algorithm                               | Basic LK only (per literal spec)    |
| Frame access                                     | On-demand seek + LRU cache (~64)    |
| Tracking execution                               | Synchronous on UI thread            |
| Project layout                                   | Modular package (six modules)       |
| Marker on seed frame N                           | Yes — N is included in trajectory   |
| Tracking-failure indicator in UI                 | Implicit (gaps only) for v1         |
