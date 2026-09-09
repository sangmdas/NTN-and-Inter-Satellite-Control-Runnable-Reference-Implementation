# Satellite and NTN system variations

## Ground PED, onboard sink

Ground policy issues short-lived authority; the spacecraft verifies at the PA, beam or ISL controller. This centralizes policy but requires command-link delivery, onboard key verification, secure time and an offline envelope.

## Onboard PED and sink

Both roles run in protected flight partitions. This reduces latency and supports link fade, but policy/ephemeris/licence epochs must be securely provisioned and rollback-resistant.

## User-terminal enforcement

The PED may run in a modem TEE, secure processor or vendor radio service. The true sink must control PA enable or its cryptographic prerequisite. Application-level grant checking alone is bypassable if a diagnostic or baseband path can key the PA.

## Spacecraft service-link gate

Place verification after scheduler selection and immediately before beamformer/PA enable. Bind panel, beam/cell, band, EIRP, slots, user/flow digest and overflight epoch.

## Optical/RF ISL gate

The sink controls the crosslink switch or terminal transmission queue. Bind current vehicle, terminal, next hop, flow/grant digest and topology epoch. Route recomputation creates a new Candidate Act or explicit epoch transition.

## Gateway feeder gate

The sink resides immediately before the feeder transmitter. Site diversity is a new act because gateway ID, pass, band, polarization, target vehicle and administration can change.

## Beam steer and handover

Beam steering is itself an effect. Handover must not silently inherit an old beam authority. Use either separate steer/transmit acts or a compound object whose required transitions cannot be partially completed.

## Hosted payload

Give the payload emitter a separate sink and consequence class. Spacecraft-bus access must not imply service-link or secondary-emitter authority.

## FPGA/rad-hard MCU sink

A small hardware block can verify a prevalidated capability, check local epoch/nonce registers and gate the enable line. Key storage, counter rollover, SEU response, watchdog behavior and atomic consume must be designed for the target radiation environment.

## Distributed constellation

Authority may be issued centrally, regionally or onboard. A global shared consume table is rarely feasible at aperture time. Sink binding and per-vehicle nonce domains can reduce coordination, but handover or multi-sink effects require an explicit distributed design.

## Safe degraded operation

When command links fade, an onboard hot envelope may allow bounded vehicle/beam/band/EIRP/epoch combinations. Unknown administration, new beam, high EIRP, new next hop or expired epoch must hold dark or enter a predefined safe pattern.

