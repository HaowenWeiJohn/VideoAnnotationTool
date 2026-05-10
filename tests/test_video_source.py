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
