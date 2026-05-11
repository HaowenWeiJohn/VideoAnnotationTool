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
