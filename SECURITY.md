# Security and safety integration notes

- Keep signing keys outside untrusted scheduler, model, payload and application processes.
- Make the finality sink own the only effective route to the PA, beamformer, crosslink switch or payload emitter.
- Protect epochs against rollback and define secure-time failure behavior.
- Use bounded parsers and fixed schemas at spacecraft and modem boundaries.
- Treat verification/storage timeout as dark/hold or a predefined safe pattern.
- Do not retry an uncertain effect until hardware state is reconciled.
- Inventory ground override, payload bus, debug, test, recovery and discrete hardware paths.
- Hash or pseudonymize user-terminal association maps outside trusted operational domains.
- Treat overflight/administration as a load-bearing sovereignty input, not telemetry.
- Validate real implementations with hardware-in-the-loop fault injection, reset, concurrency and missed-deadline tests.

This repository does not describe disabling, jamming or commandeering third-party satellites. It models an operator-controlled authorization gate on its own effecting path.

