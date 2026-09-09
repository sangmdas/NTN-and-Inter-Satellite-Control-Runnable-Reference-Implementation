# Satellite test matrix

The suite contains 77 tests.

| Group | Coverage |
|---|---|
| Path allows | SAT RF, UT TX, ISL, beam steer, gateway feeder, handover, payload |
| Digest substitution | 20 load-bearing command fields plus sink ID/type |
| Epochs | policy, revocation, overflight |
| Autonomy | faded-link nominal allow, high-EIRP denial |
| Sovereignty | administration and licence-profile denial |
| Route | unknown ISL next hop, flow and hop substitution |
| Alternate paths | payload laundering and unauthorized debug/other provenance |
| Safety | safe mode, duration/EIRP envelope |
| Integrity | authority signature/scope, missing/tampered evidence, act mutation |
| Replay | same authority, second authority/same grant, concurrent consume |
| Hardware result | definite failure and uncertain result |
| Input validation | act/sink enums, duration, sequence, required IDs, ISL hop |
| Portability | SAT RF, UT TX and ISL canonical vectors |
| Durability | SQLite close/reopen |

Every denial test asserts that the simulated effect count remains zero. Replay/concurrency tests assert that exactly one effect occurs.

