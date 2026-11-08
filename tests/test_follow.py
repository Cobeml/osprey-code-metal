from osprey.follow import FollowController


def test_follow_error_and_stop_priority():
    f = FollowController()
    m = f.on_frame(True, True, (0.6, 0.4, 0.8, 0.8), 1.0, 1.0)
    assert m["type"] == "follow" and m["err"] == [0.2, 0.1]
    assert f.on_frame(True, True, None, 1.1, 1.1)["type"] == "hold"
    assert f.on_frame(True, True, None, 1.2, 1.2) is None  # rate limited
    assert f.on_frame(False, False, (0.4, 0.4, 0.6, 0.6), 1.3, 1.3)["type"] == "stop"
    # launched rover searching on its own lock: the ground must not stop it
    assert f.on_frame(False, True, None, 2.0, 2.0) is None
    assert f.on_frame(False, True, None, 9.0, 9.0) is None
