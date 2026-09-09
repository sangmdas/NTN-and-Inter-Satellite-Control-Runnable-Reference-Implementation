# NTN/RF Execution Finality — Satellite Reference Implementation

Runnable, non-radiating reference implementation of aperture-time execution finality for LEO/NTN service links, user-terminal uplinks, inter-satellite links, beam steering, gateway feeder links, handover-coupled transmission and hosted-payload emitters.

This repository is derived from **`draft-das-ntn-rf-execution-finality-00`**, *RF Enable Is Not Transmit Authority: Finality for LEO/NTN and Inter-Satellite Control*, by Sangam Das.

> A scheduler may compute a burst. A flight computer may authenticate a command. A user terminal may be registered. None of those facts alone is authority for energy or a forwarded hop to leave the controlled boundary.

## Implemented chain

```text
scheduler / flight software / NTN CU / autonomy
                         |
                         v
              Satellite Candidate Act
                    NON_EFFECTIVE
                         |
                         v
             Protected Enforcement Domain
        vehicle + beam + band + EIRP + duration
       next hop + administration + provenance
          current epochs + intended finality sink
                         |
             commit protected evidence first
             issue scoped single-use authority
                         |
                         v
          RF / ISL / UT / GW / payload sink
                         |
             verify live command and consume
                         |
                  +------+------+
                  |             |
                PASS           FAIL
                  |             |
          simulated effect   aperture stays dark
```

The implementation keeps the hardware effect function unreachable until the sink independently validates the exact live command.

## Covered satellite paths

| Candidate Act | Demonstrated sink | Bound consequence |
|---|---|---|
| `SAT_RF_ENABLE` | spacecraft PA/service-link controller | service-link radiation |
| `UT_TX_ENABLE` | user-terminal PA enable | phased-array terminal uplink |
| `ISL_FORWARD` | optical/RF crosslink switch | next-hop forwarding |
| `BEAM_STEER` | beamformer/array driver | pointing or steer change |
| `GW_FEEDER` | gateway feeder controller | high-power feeder radiation |
| `HANDOVER_TX` | target PA/beam sink | transmit across handover |
| `PAYLOAD_CMD` | hosted-payload radio gate | secondary emitter or payload downlink |

All seven paths have executable allow tests. The test suite also covers beam, vehicle, band, EIRP, duration, next-hop, administration, licence profile, provenance, command-link state and slot substitution.

## What comes from the Internet-Draft

The implementation directly exercises these draft concepts:

- a scheduler or autonomy output remains a Candidate Act;
- the Candidate Act is held in a non-effective state;
- vehicle, beam/cell, frequency class, EIRP class, duration/slot set, next hop, overflight epoch, command provenance and sink are load-bearing;
- PED validation precedes authority issuance;
- protected validation evidence is committed before authority is usable;
- authority is digest-, nonce-, epoch- and sink-bound rather than accepted by possession;
- the aperture-side or forwarding sink reconstructs the live grant digest;
- authority is single-use and consumed at the effecting boundary;
- changed overflight, policy or revocation epochs invalidate unused authority;
- faded command links do not inherit a previous unbounded permission;
- a payload/debug/override path cannot bypass the effecting sink;
- timeout or missing state does not become permission to enable.

Vendor names in the draft describe a public topology class and do not assert implementation details of any operator.

## Reference-only engineering choices

The following are implementation choices, not requirements stated by the draft:

- Python 3.10+ for readable executable behavior;
- HMAC-SHA-256 as a replaceable software test authenticator;
- SQLite as a single-node durable evidence and consume store;
- `NTN-EF-JCS-SUBSET-1` as a controlled deterministic JSON subset;
- an in-process, non-radiating effect adapter;
- p99 engineering goals of 1 ms for the local sink and 5 ms for the complete local path;
- explicit licence-profile, flow-digest, slot-set and command-link-state fields in the digest projection.

See [Parameters and provenance](docs/PARAMETERS.md) for the source of every sample value.

## Quick start

```bash
python -m pip install -e .
ntn-finality-demo
python -m unittest discover -s tests -v
ntn-finality-benchmark --iterations 1000 --warmup 100 --act-type SAT_RF_ENABLE
```

No live RF, optical link, modem, gateway or spacecraft interface is used.

## Binding model

The grant digest covers:

| Domain | Fields |
|---|---|
| Act | act type |
| Vehicle | vehicle ID, constellation ID, orbit shell |
| Beam | beam ID, cell ID, pointing reference |
| Radio | frequency class, EIRP class, polarization, duration, slot set |
| Route | next-hop type, next-hop ID, flow digest |
| Sovereignty | administration and licence-profile ID |
| Provenance | source type, grant sequence, command-link state |
| Sink | sink ID and sink type |

The separate Candidate Act digest additionally binds:

- Candidate Act ID;
- grant digest;
- policy, revocation and overflight epochs;
- nonce;
- creation and expiration time;
- intended finality sink.

Copying authority to a second spacecraft, beam, terminal, gateway, ISL neighbour, payload radio or epoch fails.

## Evidence and authority ordering

`ProtectedEnforcementDomain.validate_and_issue()` performs:

1. Candidate Act integrity and freshness check.
2. Current epoch comparison.
3. emitter tuple allowlist check.
4. beam, EIRP, duration, administration and licence checks.
5. ISL topology and provenance checks.
6. faded-link autonomy-envelope check.
7. protected evidence construction and signature.
8. durable evidence commitment.
9. scoped authority construction and signature.
10. authority registration in `UNUSED` state.

An `ALLOW` boolean without committed evidence is not sufficient in this reference.

## Consume state machine

```text
UNUSED ──verify/reserve──> CONSUMED_PENDING ──confirmed effect──> EFFECTED
                                      |
                                      └──confirmed no effect──> FAILED_DEFINITE
```

If the driver or remote controller returns an uncertain outcome, the state remains `CONSUMED_PENDING`. The implementation requires safe-output action and hardware-state reconciliation. It does not issue a blind second enable.

SQLite uses a conditional state transition and a unique partial index over active/effected grant digests. Concurrent presentation has exactly one winner in the tested single-node trust domain.

## Test suite

The repository contains **77 passing tests** covering:

- all seven satellite/NTN act paths;
- Candidate Act, grant, sink, nonce and epoch binding;
- service-link beam and vehicle substitution;
- UT grant, cell, pointing and PA-sink substitution;
- ISL next-hop and flow substitution;
- gateway site/sink and feeder-command substitution;
- handover beam/slot inheritance;
- payload-bus path laundering;
- frequency, EIRP, polarization and duration changes;
- administration and licence-profile changes;
- stale overflight, policy and revocation epochs;
- safe mode;
- faded-link autonomy inside and outside its envelope;
- malformed duration, sequence, act and sink types;
- missing or modified evidence;
- modified authority;
- same-authority and same-grant replay;
- concurrent consume with exactly one simulated effect;
- definite and uncertain hardware outcomes;
- durable SQLite reopen;
- three deterministic cross-language vectors.

See [Satellite test matrix](docs/TEST_MATRIX.md).

## Latency

The source draft requires a mandatory sink check on the hot path but does **not** state a numeric latency target. The repository therefore labels its numeric goals as implementation-only:

| Reference goal | Value |
|---|---:|
| Local sink verify + consume + simulated effect, p99 | ≤ 1,000 µs |
| Complete local prepare + issue + sink path, p99 | ≤ 5,000 µs |

On the reference environment, 1,000 `SAT_RF_ENABLE` iterations after 100 warmups measured:

| Stage | p50 | p95 | p99 |
|---|---:|---:|---:|
| Prepare | 63.76 µs | 113.04 µs | 221.08 µs |
| PED evidence/authority issue | 185.37 µs | 425.92 µs | 761.85 µs |
| Sink verify/consume/simulated effect | 145.07 µs | 254.18 µs | 613.32 µs |
| Complete local path | 413.27 µs | 738.07 µs | 1,574.27 µs |

These are software reference measurements, not RF-slot, modem, FPGA, flight-safety or operator SLAs. See [Latency and real-time integration](docs/LATENCY.md).

## System variations

The same invariants can be implemented as:

- ground PED with an onboard aperture sink;
- colocated onboard PED and PA gate;
- protected UT modem/TEE plus PA-enable sink;
- spacecraft service-link PA/beamformer gate;
- optical or RF ISL switch gate;
- gateway feeder controller;
- beam-driver/array-steer interlock;
- hosted-payload radio gate;
- FPGA or rad-hard MCU enforcement block;
- flight-software partition with a hardware interlock;
- hardware-in-the-loop verification deployment.

Each changes latency, fault containment, key distribution and offline autonomy behavior. See [System variations](docs/SYSTEM_VARIATIONS.md).

## Language variations

The Python implementation is portable by invariant, not by source syntax. The repository provides guidance for:

- C11/C17;
- C++17/20;
- Rust and `no_std` environments;
- Ada/SPARK;
- Go;
- Java/Kotlin;
- TypeScript;
- FPGA/RTL or MCU offload.

Every port must reproduce the supplied canonical bytes and digests, use bounded parsing, constant-time authentication checks, monotonic/secure time and an exactly-one consume transition. See [Language variations](docs/LANGUAGE_VARIATIONS.md).

## Important limitations

This is not flight software and is not connected to an emitter. It does not provide:

- CCSDS telecommand integration;
- 3GPP NTN grant parsing;
- waveform or PHY control;
- orbit propagation or geofencing;
- ITU filing or landing-right verification;
- GNSS-independent secure position/time;
- flight-qualified cryptography;
- radiation-tolerant memory behavior;
- FPGA register interlocks;
- distributed constellation consensus;
- real optical/RF ISL switching;
- formal verification or safety certification;
- protection against an unmodeled analog bypass.

See [Limitations](docs/LIMITATIONS.md) and [Security](SECURITY.md) before adapting the design.

## Repository map

```text
src/ntn_finality/
  canonical.py   load-bearing command projection and digests
  models.py      command, Candidate Act, evidence and authority
  policy.py      constellation and autonomy-envelope policy
  ped.py         validate, commit evidence, issue authority
  store.py       durable consume/effect state machine
  sink.py        aperture-side independent verification
  hardware.py    non-radiating effect adapter interface
  demo.py        complete SAT_RF_ENABLE example
  benchmark.py   stage-level microsecond measurement
tests/           77 executable tests
test-vectors/    SAT RF, UT uplink and ISL canonical vectors
schemas/         Satellite Candidate Act schema
docs/            detailed implementation references
```

## Relationship to existing controls

This profile is additive. TT&C authentication, CCSDS protections, 3GPP NTN registration and NAS security, flight allowlists, safe mode, link encryption, gateway ACLs, ITU coordination and national permissions remain necessary controls. They are treated as inputs or surrounding controls, not substitutes for act-specific sink verification.

Authentication determines who or what supplied a command. Execution finality determines whether this exact command may create this RF, beam or forwarding effect at this sink now.

## Rights and IPR notice

The source draft states that certain concepts are associated with pending applications in the DAS Protocols family, including PCT/IB2026/055615 and follow-on NTN-related filings, and that IETF disclosure should follow BCP 79.

No software licence is selected in this package. Before public reuse is invited, the repository owner should choose an appropriate software licence and separately state any applicable patent-licensing position.

**RF enable is not transmit authority.**

