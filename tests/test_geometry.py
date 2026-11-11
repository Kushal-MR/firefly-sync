from fireflysync.geometry import blocked, segments_cross, two_rooms


def test_crossing_and_non_crossing_segments():
    assert segments_cross((0, 0), (2, 2), (0, 2), (2, 0))
    assert not segments_cross((0, 0), (1, 0), (0, 1), (1, 1))


def test_touching_counts_as_crossing():
    assert segments_cross((0, 0), (2, 0), (1, 0), (1, 5))


def test_closed_wall_blocks_both_rooms():
    walls = two_rooms((20, 12), door_open=False)
    assert blocked((5, 6), (15, 6), walls)
    assert not blocked((2, 2), (8, 9), walls)          # same room


def test_open_door_lets_radio_through_the_gap_only():
    walls = two_rooms((20, 12), door_open=True)
    assert not blocked((5, 6), (15, 6), walls)          # straight through the door
    assert blocked((5, 1), (15, 1), walls)              # through solid wall
