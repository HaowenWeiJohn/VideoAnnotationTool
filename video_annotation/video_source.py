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
