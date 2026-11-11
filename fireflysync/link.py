"""UDP link between the laptop swarm and the real ESP32.

Messages (plain text, so the ESP32 needs no library to read them):

    FIRE|<node_id>|<seq>|<tx_delay_ms>   a node flashed. Each ESP32 LED has its
                                         own id: esp32-L1, esp32-L2, ...
    HELLO|esp32|<n_leds>                 ESP32 -> broadcast, every 2 s: "I exist".
                                         The laptop learns the ESP32's IP from it.
    HELLO|laptop                         laptop -> ESP32: teaches it our address.
    PING|<seq>                           laptop -> ESP32, echoed straight back.
                                         Half the round trip = one-way delay.

So nobody types the ESP32's IP or the delay: both are found automatically.
Passing an IP (--peer) still works, for hotspots that block broadcast.

UDP, not TCP, on purpose: TCP re-sends lost packets, which adds unpredictable
delay. A lost flash is fine; a late flash is the real problem.

This is an I/O layer, so unlike the core it may read the real clock - it
needs it to time PING round trips.
"""
import socket
import statistics
import time
from collections import deque
from dataclasses import dataclass

DEFAULT_ESP32_PORT = 4210
DEFAULT_LAPTOP_PORT = 4211
PING_HISTORY = 30


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


def parse_hello(data):
    """Number of LEDs an ESP32 announces, or None if this isn't its HELLO."""
    try:
        parts = data.decode("ascii").strip().split("|")
        if len(parts) == 3 and parts[0] == "HELLO" and parts[1] == "esp32":
            return int(parts[2])
    except (UnicodeDecodeError, ValueError):
        pass
    return None


class UdpLink:
    def __init__(self, peer_ip=None, peer_port=DEFAULT_ESP32_PORT, listen_port=DEFAULT_LAPTOP_PORT):
        self.peer_port = peer_port
        self.peer = (peer_ip, peer_port) if peer_ip else None
        self.discovered = False             # True if the peer was found by broadcast
        self.announced_leds = None          # what the ESP32's HELLO said
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", listen_port))
        self.sock.setblocking(False)
        self._seq = 0
        self._ping_seq = 0
        self._ping_sent = {}                # seq -> perf_counter at send
        self._rtts = deque(maxlen=PING_HISTORY)
        self.last_heard = None              # session time of the last FIRE from the peer
        self.sent = 0
        self.received = 0

    # ----- sending -----------------------------------------------------------
    def send_fire(self, node_id, tx_delay_ms=0):
        if self.peer and self._send(format_fire(node_id, self._seq, tx_delay_ms)):
            self._seq += 1

    def send_hello(self):
        if self.peer:
            self._send(b"HELLO|laptop")

    def send_ping(self):
        if not self.peer:
            return
        seq = self._ping_seq
        self._ping_seq += 1
        self._ping_sent[seq] = time.perf_counter()
        for old in [s for s in self._ping_sent if s < seq - PING_HISTORY]:
            del self._ping_sent[old]
        self._send(f"PING|{seq}".encode())

    def _send(self, payload):
        try:
            self.sock.sendto(payload, self.peer)
            self.sent += 1
            return True
        except OSError:
            return False                    # network blip: a lost flash is acceptable

    # ----- receiving ---------------------------------------------------------
    def poll(self, now):
        """Every FIRE waiting right now. Never blocks. Handles HELLO and PING
        replies on the way."""
        out = []
        while True:
            try:
                data, addr = self.sock.recvfrom(256)
            except BlockingIOError:
                break
            except ConnectionResetError:
                # Windows quirk: if an earlier packet hit a closed port (ESP32
                # still booting), the NEXT receive raises this. Not fatal.
                continue
            except OSError:
                break
            if data.startswith(b"PING|"):
                self._on_pong(data)
                continue
            leds = parse_hello(data)
            if leds is not None:
                self.announced_leds = leds
                if self.peer is None:
                    self.peer = (addr[0], self.peer_port)
                    self.discovered = True
                continue
            msg = parse_fire(data, now)
            if msg is not None:
                if self.peer is None:                  # found it from a flash instead
                    self.peer = (addr[0], self.peer_port)
                    self.discovered = True
                out.append(msg)
                self.received += 1
                self.last_heard = now
        return out

    def _on_pong(self, data):
        try:
            seq = int(data.decode("ascii").split("|")[1])
        except (UnicodeDecodeError, ValueError, IndexError):
            return
        sent = self._ping_sent.pop(seq, None)
        if sent is not None:
            self._rtts.append((time.perf_counter() - sent) * 1000.0)

    # ----- delay -------------------------------------------------------------
    @property
    def rtt_ms(self):
        return statistics.median(self._rtts) if self._rtts else None

    @property
    def oneway_ms(self):
        """Measured one-way delay: half the median round trip. None until measured."""
        r = self.rtt_ms
        return None if r is None else r / 2

    def close(self):
        self.sock.close()
