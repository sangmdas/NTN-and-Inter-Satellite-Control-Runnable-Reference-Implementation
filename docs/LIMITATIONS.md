# Limitations

- Python is not represented as flight-qualified or hard real-time software.
- HMAC key material is in process memory; there is no secure element, HSM, TEE, key rotation or certificate chain.
- SQLite demonstrates single-node atomic consume, not global constellation consensus.
- The canonical JSON subset is not full RFC 8785 for arbitrary JSON.
- The effect adapter is non-radiating and does not drive a PA, modem, beamformer, optical terminal, FPGA or gateway.
- No CCSDS, 3GPP NTN, proprietary scheduler, ioctl, spacecraft-bus or RF-driver adapter is supplied.
- There is no orbit propagator, beam-footprint calculation, geofence or independent administration/licence resolver.
- Secure position, secure time and epoch distribution are assumed.
- Radiation effects, SEU/SEL, watchdog reset, counter rollover, power-cycle persistence and fault injection are not modeled.
- Multi-satellite handover and atomic multi-sink effects are not implemented.
- No formal proof establishes that every physical/debug/analog enable path is closed.
- An unmodeled strap, coupler, amplifier, debug register or recovery path remains residual risk.
- The autonomy envelope is illustrative and not operator flight policy.
- Unknown hardware outcomes require reconciliation tooling not supplied here.
- The repository does not create ITU rights, landing rights, spectrum authorization or regulatory compliance.
- It is not safety-certified, security-audited, formally verified or tested in hardware-in-the-loop facilities.
- Passing 77 tests demonstrates the implemented paths, not absence of every spacecraft or RF failure mode.

