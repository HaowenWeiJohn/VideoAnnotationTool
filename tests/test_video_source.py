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
