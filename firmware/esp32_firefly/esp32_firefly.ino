/*
 * PHASE 2 - the real drone.
 *
 * Runs the same firefly rule as fireflysync/oscillator.py, in C++:
 * a phase rises, fires at the threshold, lights the LED and broadcasts;
 * an incoming fire nudges the phase forward.
 *
 * Message format (must match fireflysync/link.py exactly):
 *   FIRE|<node_id>|<sequence_number>|<tx_delay_ms>
 *
 * Wiring: GPIO 2 -> 220 ohm -> LED long leg; LED short leg -> GND.
 * Many boards have a built-in LED on GPIO 2 for a first test.
 *
 * Design notes
 * ------------
 * - Never use delay() for the blink. It blocks the loop, so incoming
 *   messages are missed and the timing drifts. Track elapsed time with
 *   millis() (or micros()) and turn the LED off a few milliseconds later.
 * - Keep the receive handling short. Anything slow in the loop shows up as
 *   timing error in the results.
 * - Use the same period and coupling values that worked in simulation.
 *   Tune in Python first, where a test takes a second.
 *
 * TODO(phase-2): implement.
 */
