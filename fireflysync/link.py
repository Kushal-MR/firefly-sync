"""UDP link between the laptop swarm and the real ESP32 drone.

Message formats (plain text, so the ESP32 needs no library to read them):

    FIRE|<node_id>|<sequence_number>|<tx_delay_ms>     a node flashed
    HELLO|laptop                                        "here I am"

The ESP32 learns where the laptop is from whatever packet it last received,
so nobody has to type the laptop's IP into the firmware. HELLO is sent every
couple of seconds so it learns this even before any flash reaches it.

tx_delay_ms is always 0 for now. It is there because the Reachback algorithm
(Phase 3) needs it, and adding a field later means changing both sides.

UDP, not TCP, on purpose: TCP re-sends lost packets, which adds unpredictable
delay. A lost flash is fine; a late flash is the real problem.
"""
import socket
from dataclasses import dataclass

DEFAULT_ESP32_PORT = 4210
DEFAULT_LAPTOP_PORT = 4211


@dataclass(frozen=True)
class FireMessage:
    node_id: str
    seq: int
    tx_delay_ms: int
    received_at: float


def format_fire(node_id, seq, tx_delay_ms=0):
    if "|" in node_id:
        raise ValueError("node_id cannot contain '|'")
    return f"FIRE|{node_id}|{seq}|{tx_delay_ms}".encode()


def parse_fire(data, received_at):
    """Return a FireMessage, or None for anything that isn't a valid FIRE."""
    try:
        parts = data.decode("ascii").strip().split("|")
        if len(parts) != 4 or parts[0] != "FIRE" or not parts[1]:
            return None
        return FireMessage(parts[1], int(parts[2]), int(parts[3]), received_at)
    except (UnicodeDecodeError, ValueError):
        return None


class UdpLink:
    def __init__(self, peer_ip, peer_port=DEFAULT_ESP32_PORT, listen_port=DEFAULT_LAPTOP_PORT):
        self.peer = (peer_ip, peer_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", listen_port))
        self.sock.setblocking(False)
        self._seq = 0
        self.last_heard = None          # time of the last valid message from the peer
        self.sent = 0
        self.received = 0

    def send_fire(self, node_id, tx_delay_ms=0):
        self._send(format_fire(node_id, self._seq, tx_delay_ms))
        self._seq += 1

    def send_hello(self):
        self._send(b"HELLO|laptop")

    def _send(self, payload):
        try:
            self.sock.sendto(payload, self.peer)
            self.sent += 1
        except OSError:
            pass                            # network blip: a lost flash is acceptable

    def poll(self, now):
        """Every message waiting right now. Never blocks."""
        out = []
        while True:
            try:
                data, _ = self.sock.recvfrom(256)
            except BlockingIOError:
                break
            except ConnectionResetError:
                # Windows quirk: if an earlier packet hit a closed port (ESP32
                # still booting), the NEXT receive raises this. Not fatal.
                continue
            except OSError:
                break
            msg = parse_fire(data, now)
            if msg is not None:
                out.append(msg)
                self.received += 1
                self.last_heard = now
        return out

    def close(self):
        self.sock.close()
