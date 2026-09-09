# Language and platform variations

## Invariants for every port

1. Identical canonical UTF-8 bytes and SHA-256 digest.
2. Bounded parsing with unknown load-bearing properties rejected.
3. No locale-dependent case, number or time conversion.
4. Constant-time authentication-tag comparison.
5. Secure/monotonic expiry and rollback-resistant epochs.
6. Exactly one `UNUSED → CONSUMED_PENDING` transition.
7. Effect function unreachable on every verification error.
8. Unknown hardware outcome stays terminal/pending until reconciled.

## C11/C17

Use fixed-size structures and bounded buffers; avoid dynamic allocation on the enable path. Define network byte order and canonical field encoding explicitly. Use a reviewed crypto library and constant-time compare. Protect consume state with an RTOS critical section, atomic primitive or durable monotonic counter appropriate to reset behavior.

## C++17/20

Use value types and explicit enums for acts/states. Avoid exception-based default recovery around the hardware call. Restrict allocations in real-time sections and ensure RAII cleanup cannot accidentally toggle an enable line.

## Rust / `no_std`

Model states and act types as enums, use bounded collections, and keep the effect adapter behind a capability that only the verified transition can obtain. `no_std` targets need explicit time, storage and crypto providers. Use constant-time comparison and audited serialization.

## Ada/SPARK

Represent state transitions and field ranges with strong types and contracts. Prove that the effect procedure's precondition requires verified, current and consumed authority. This is especially suitable for assurance-oriented flight partitions, but proof scope must include hardware-interface wrappers.

## Go

Use fixed structs rather than maps for canonical fields, a canonical encoder, `hmac.Equal`, UTC time and a conditional durable update. Garbage-collection pauses must be measured against the target control-loop budget.

## Java/Kotlin

Use `Instant`, fixed schemas, deterministic canonical serialization and `MessageDigest.isEqual`. Bound allocation and pause behavior for modem or gateway real-time contexts.

## TypeScript

Suitable for ground/gateway control planes, not assumed flight-qualified. Use a reviewed canonical JSON library, `timingSafeEqual`, strict schemas and transactional conditional consume. Do not rely on normal object insertion order.

## FPGA/RTL

Use a fixed binary authority profile, precomputed signatures/MACs where appropriate, explicit nonce/epoch registers and a one-way verified-enable state transition. Analyse reset, rollover, metastability, fault injection, SEU and debug-port behavior. JSON is usually terminated before this boundary.

## Cross-language vectors

Three vectors cover spacecraft RF, UT transmit and ISL forwarding. Each includes the complete logical command, exact canonical text and base64url SHA-256 digest. A port must reproduce all three before interoperability claims.

