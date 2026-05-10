from pathlib import Path
import pytest

@pytest.fixture(scope="session")
def test_video_path() -> Path:
    """Path to the bundled test video at the project root."""
    path = Path(__file__).parent.parent / "test_video.mp4"
    assert path.exists(), f"test_video.mp4 missing at {path}"
    return path
