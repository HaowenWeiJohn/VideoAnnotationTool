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
