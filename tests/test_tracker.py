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
