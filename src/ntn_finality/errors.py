from dataclasses import dataclass
from enum import Enum


class Code(str, Enum):
    NO_FINALITY_AUTHORITY = "EF-002"
    AUTHORITY_ALREADY_USED = "EF-005"
    REPLAY_DETECTED = "EF-006"
    MALFORMED_ACT = "EF-010"
    INVALID_AUTHORITY = "EF-011"
    EXPIRED_AUTHORITY = "EF-012"
    EVIDENCE_MISSING = "EF-013"
    NEXT_HOP_UNRESOLVED = "EF-020"
    GRANT_SUBSTITUTION = "EF-021"
    ACT_MISMATCH = "EF-022"
    OVERFLIGHT_MISMATCH = "EF-023"
    EMITTER_NOT_AUTHORIZED = "EF-024"
    FREQUENCY_MISMATCH = "EF-025"
    EIRP_MISMATCH = "EF-026"
    DURATION_MISMATCH = "EF-027"
    PROVENANCE_MISMATCH = "EF-028"
    PATH_LAUNDERING = "EF-029"
    ADMINISTRATION_MISMATCH = "EF-030"
    POLICY_EPOCH_MISMATCH = "EF-031"
    REVOCATION_EPOCH_MISMATCH = "EF-032"
    SINK_MISMATCH = "EF-040"
    BEAM_OR_VEHICLE_MISMATCH = "EF-041"
    NEXT_HOP_MISMATCH = "EF-042"
    ACT_TYPE_MISMATCH = "EF-043"
    AUTONOMY_ENVELOPE = "EF-070"
    SAFE_MODE = "EF-071"
    FAIL_CLOSED = "EF-080"
    EFFECT_RESULT_UNKNOWN = "EF-090"


@dataclass
class FinalityError(Exception):
    code: Code
    message: str
    retryable: bool = False

    def __str__(self) -> str:
        return f"{self.code.value} {self.message}"

