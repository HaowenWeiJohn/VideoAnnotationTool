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
