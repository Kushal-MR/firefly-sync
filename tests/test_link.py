import socket
import time

from fireflysync.link import FireMessage, UdpLink, format_fire, parse_fire


def test_format_and_parse_round_trip():
    msg = parse_fire(format_fire("esp32-1", 42, 7), received_at=1.5)
    assert msg == FireMessage("esp32-1", 42, 7, 1.5)


def test_rubbish_is_ignored_not_crashed_on():
    for junk in [b"", b"HELLO|laptop", b"FIRE|x|notanumber|0", b"FIRE||1|0",
                 b"FIRE|x|1", b"\xff\xfe", b"FIRE|a|1|0|extra"]:
        assert parse_fire(junk, 0.0) is None


def test_ids_with_separator_are_refused():
    try:
        format_fire("bad|id", 0)
    except ValueError:
        return
    assert False, "expected ValueError"


def test_udp_round_trip_over_loopback():
    peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    peer.bind(("127.0.0.1", 0))
    peer.settimeout(2)
    link = UdpLink("127.0.0.1", peer.getsockname()[1], listen_port=0)
    try:
        assert link.poll(0.0) == []                       # nothing waiting: must not block
        link.send_fire("v3")
        data, addr = peer.recvfrom(256)
        assert parse_fire(data, 0).node_id == "v3"
        peer.sendto(format_fire("esp32-1", 0), addr)
        deadline = time.time() + 2
        got = []
        while not got and time.time() < deadline:
            got = link.poll(1.0)
        assert got[0].node_id == "esp32-1"
        assert link.last_heard == 1.0
    finally:
        link.close()
        peer.close()
