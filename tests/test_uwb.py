import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("uwb", Path(__file__).parents[1] / "turbopi/uwb.py")
uwb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uwb)


def test_qorvo_cli_json_line():
    line = '{"Block":12, "results":[{"Addr":"0x0001","Status":"Ok","D_cm":123,"LPDoA_deg":0.00,"LAoA_deg":0.00}]}'
    assert abs(uwb.parse_range_m(line) - 1.23) < 1e-9


def test_failed_measurement_is_ignored():
    assert uwb.parse_range_m('{"Block":13, "results":[{"Addr":"0x0001","Status":"Err","D_cm":0}]}') is None
    assert uwb.parse_range_m("Status: Timeout D_cm: 0") is None


def test_text_formats_and_units():
    assert uwb.parse_range_m("DIST: 1.23 m") == 1.23
    assert uwb.parse_range_m("distance=123cm") == 1.23
    assert uwb.parse_range_m("range: 1230 mm") == 1.23
    assert uwb.parse_range_m("D_cm: 87") == 0.87
    assert uwb.parse_range_m("SESSION_INIT ok") is None
    assert uwb.parse_range_m("") is None


def test_slightly_negative_at_contact_and_absurd_values():
    assert uwb.parse_range_m("D_cm: -12") == 0.0
    assert uwb.parse_range_m("D_cm: 900000") is None


def test_ranger_median_offset_and_stale():
    r = uwb.UwbRanger("none", offset_m=0.1)
    for t, cm in ((100.0, 150), (100.1, 152), (100.2, 400), (100.3, 151), (100.4, 149)):
        r.feed(f"D_cm: {cm}", ts=t)
    assert abs(r.range_m(100.45) - 1.41) < 1e-9     # spike rejected, offset applied
    assert r.range_m(100.4 + uwb.STALE_S + 0.01) is None
    assert r.status == "ranging" and r.count == 5


def test_reader_on_a_pseudo_terminal_sends_init_and_reads_ranges():
    import os
    import pty
    import time

    master, slave = pty.openpty()
    r = uwb.UwbRanger(os.ttyname(slave), init_cmd="INITF").start()
    try:
        time.sleep(0.8)
        got = os.read(master, 100)
        assert b"INITF" in got
        for cm in (201, 199, 200):
            os.write(master, f'{{"results":[{{"Status":"Ok","D_cm":{cm}}}]}}\r\n'.encode())
            time.sleep(0.05)
        time.sleep(0.2)
        assert r.active_port == os.ttyname(slave) and abs(r.range_m() - 2.0) < 1e-9
    finally:
        r.stop()
        os.close(master)
