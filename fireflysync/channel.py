"""Artificial delay and packet loss, so experiments are repeatable.

PHASE 3.

Real Wi-Fi is different every run, which makes it useless for a controlled
comparison. This module adds a known, seeded amount of delay and loss on top,
so "simple vs Reachback at 50 ms delay" means the same thing every time.

Planned interface
-----------------
class Channel:
    def __init__(self, delay_ms, jitter_ms, loss_prob, seed=None): ...
    def submit(self, message, now) -> None      # queue for later delivery
    def deliver(self, now) -> list              # whatever is due by now

Design notes
------------
- Delay is a queue, not a sleep. Messages are held until their due time and
  released by the simulation loop.
- Jitter matters as much as average delay. Constant delay is easy to absorb;
  delay that varies from message to message is what actually breaks sync.
- Same seed must give the same run, or the sweeps cannot be compared.

TODO(phase-3): implement.
"""
