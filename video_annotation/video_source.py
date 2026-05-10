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
