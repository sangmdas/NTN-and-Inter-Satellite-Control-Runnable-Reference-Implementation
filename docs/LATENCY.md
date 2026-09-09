# Latency and real-time integration

## Source-draft position

`draft-das-ntn-rf-execution-finality-00` requires verification immediately before enable and permits cached, short-lived authority inside a bounded hot envelope. It does not define a numeric latency constant.

## Repository engineering goals

The repository uses implementation-only regression goals:

- local sink p99 at or below 1,000 microseconds;
- full local reference path p99 at or below 5,000 microseconds.

These are not IETF requirements and are not suitable as RF scheduling or flight-safety SLAs.

## Measured reference result

The checked-in result uses CPython, software HMAC, in-memory SQLite and a simulated non-radiating effect. The SAT RF sink measured 613.32 µs p99; the complete path measured 1,574.27 µs p99 over 1,000 iterations after 100 warmups.

## Real deployments

Measure separately:

- parser and canonicalization;
- signature/MAC verification;
- epoch lookup;
- consume-state access;
- hardware register or controller transaction;
- interrupt and scheduler jitter;
- secure-element/HSM access;
- storage durability;
- worst-case contention and failover;
- cold policy evaluation;
- command-link delay, which is not sink overhead.

For a hard real-time slot boundary, move fixed-format verification and consume to an MCU, FPGA, modem security block or flight-qualified service. Python results only show logical feasibility of the reference path.

Timeout is not enable. A missed deadline should select a defined safe state, not bypass verification.

