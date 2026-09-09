# Detailed implementation reference

## Trust boundaries

The scheduler, flight process, NTN controller, autonomy process and payload computer are candidate generators. They may prepare commands but are not trusted to finalize radiation or forwarding.

The PED is trusted to evaluate current policy and protect evidence. The aperture sink is trusted to refuse the physical or forwarding effect. These roles may be collocated only when evidence ordering and immediate live-command verification remain enforceable.

## Candidate construction

`ProtectedEnforcementDomain.prepare()` validates structural fields, computes the grant digest, snapshots all three epochs, creates a fresh nonce and short expiry, and computes a second digest over the Candidate Act envelope. No effect adapter is reachable during preparation.

## PED validation

`ConstellationPolicy.validate()` checks the tuple `(vehicle_id, act_type, frequency_class)` instead of independent broad allowlists. This prevents a band permitted on one emitter class from automatically authorizing another.

It also checks vehicle-to-beam membership, EIRP class, maximum duration, administration, licence profile, current ISL next hop, act-specific provenance and faded-link autonomy envelope.

Payload provenance used for a non-payload act is explicitly treated as path laundering.

## Evidence

Protected Validation Evidence records the Candidate Act digest, grant digest, predicate outcomes, issue time and protector identity. It is signed and durably committed before authority registration.

The sink resolves and verifies this evidence. Missing evidence or a false/empty predicate set is a denial.

## Authority

The Satellite Finality Authority has two layers:

- `scope`: act, vehicle, beam, band, EIRP, duration, next hop, administration, licence, provenance and sink type;
- `binding`: Candidate Act digest, grant digest, nonce, three epochs and exact sink ID.

It is short-lived and single-use.

## Sink verification

`ApertureFinalitySink.verify_and_effect()` verifies authority integrity, evidence integrity and ordering, act binding, expiry, sink ID/type, all current epochs and a freshly recomputed live grant digest. It repeats explicit field comparisons as defence in depth.

Only after all checks does it reserve consume state and call the effect adapter.

## Effect adapter contract

The adapter returns an effect identifier or one of two failure classes:

- definite failure: hardware or controller proves no external effect occurred;
- unknown result: software cannot determine whether radiation/forwarding occurred.

Unknown outcomes remain consumed-pending and require a safe-output command plus state reconciliation. A production adapter must never label a timeout as definite without hardware evidence.

## Alternate-path closure

Every path capable of creating the same effect must cross the sink or be physically unable to effect:

- mission scheduler;
- autonomy process;
- payload bus;
- test/debug interface;
- ground override;
- recovery console;
- modem diagnostic mode;
- FPGA register path;
- discrete PA-enable line.

A policy server that is only consulted by one software path is not the finality sink.

