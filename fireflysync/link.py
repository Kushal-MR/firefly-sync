"""UDP link between the laptop swarm and the real ESP32 drone.

PHASE 2.

Message format (plain text, no library needed on either side):

    FIRE|<node_id>|<sequence_number>|<tx_delay_ms>

    example:  FIRE|esp32-1|42|7

tx_delay_ms is sent as 0 in Phase 2. The field exists from the start because
Phase 3's Reachback algorithm needs it, and adding a field later means
changing the laptop and the firmware at the same moment.

Planned interface
-----------------
class UdpLink:
    def __init__(self, listen_port, peer_addr): ...
    def send_fire(self, node_id, seq, tx_delay_ms=0) -> None
    def poll(self) -> list[FireMessage]   # non-blocking, returns what arrived

Design notes
------------
- poll() must never block. If the main loop waits on the network, the LED
  timing and the window both stutter.
- UDP, not TCP, on purpose: TCP retransmits lost messages, which adds
  unpredictable delay. A lost flash is fine; a late flash is the problem.
- Stamp each message on arrival and subtract the one-way delay measured in
  Phase 0, or the real drone will always look late. See docs/PLAN.md.
- Ignore malformed packets rather than crashing. Something else on the
  network will eventually send you rubbish.

TODO(phase-2): implement.
"""
