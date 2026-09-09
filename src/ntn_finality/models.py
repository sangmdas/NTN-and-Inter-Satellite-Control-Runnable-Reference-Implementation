from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class EpochState:
    policy_epoch: int
    revocation_epoch: int
    overflight_epoch: int

    def to_dict(self) -> dict[str, int]:
        return {
            "policy_epoch": self.policy_epoch,
            "revocation_epoch": self.revocation_epoch,
            "overflight_epoch": self.overflight_epoch,
        }


@dataclass(frozen=True)
class RadioCommand:
    act_type: str
    vehicle_id: str
    constellation_id: str
    orbit_shell: str
    beam_id: str
    cell_id: str
    pointing_ref: str
    frequency_class: str
    eirp_class: str
    polarization: str
    duration_ms: int
    next_hop_type: str
    next_hop_id: str
    administration: str
    license_profile_id: str
    source_type: str
    sink_id: str
    sink_type: str
    grant_sequence: int = 0
    flow_digest: str = ""
    slot_set: str = ""
    command_link_state: str = "AVAILABLE"


@dataclass(frozen=True)
class SatelliteCandidateAct:
    candidate_act_id: str
    command: RadioCommand
    grant_digest: str
    candidate_act_digest: str
    epoch_state: EpochState
    nonce: str
    created_at: datetime
    expires_at: datetime
    status: str = "NON_EFFECTIVE"
    canonicalization: str = "NTN-EF-JCS-SUBSET-1"

    def unsigned_projection(self) -> dict[str, Any]:
        c = self.command
        return {
            "candidate_act_id": self.candidate_act_id,
            "act_type": c.act_type,
            "grant_digest": self.grant_digest,
            "vehicle_id": c.vehicle_id,
            "beam_id": c.beam_id,
            "frequency_class": c.frequency_class,
            "eirp_class": c.eirp_class,
            "duration_ms": c.duration_ms,
            "next_hop_type": c.next_hop_type,
            "next_hop_id": c.next_hop_id,
            "administration": c.administration,
            "license_profile_id": c.license_profile_id,
            "source_type": c.source_type,
            "sink_id": c.sink_id,
            "sink_type": c.sink_type,
            "epochs": self.epoch_state.to_dict(),
            "nonce": self.nonce,
            "created_at": iso_z(self.created_at),
            "expires_at": iso_z(self.expires_at),
        }


@dataclass(frozen=True)
class ProtectedValidationEvidence:
    evidence_id: str
    candidate_act_id: str
    candidate_act_digest: str
    grant_digest: str
    predicates: dict[str, bool]
    issued_at: datetime
    key_id: str
    signature: str = ""

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "version": "1.0",
            "object_type": "protected_validation_evidence",
            "evidence_id": self.evidence_id,
            "candidate_act_id": self.candidate_act_id,
            "candidate_act_digest": self.candidate_act_digest,
            "grant_digest": self.grant_digest,
            "decision": "ALLOW",
            "validated_predicates": dict(sorted(self.predicates.items())),
            "issued_at": iso_z(self.issued_at),
            "protector": {"type": "HMAC-SHA-256-REFERENCE", "key_id": self.key_id},
        }

    def to_dict(self) -> dict[str, Any]:
        result = self.unsigned_dict()
        result["protector"]["signature"] = self.signature
        return result


@dataclass(frozen=True)
class SatelliteFinalityAuthority:
    authority_id: str
    candidate_act_id: str
    evidence_id: str
    scope: dict[str, Any]
    binding: dict[str, Any]
    issued_at: datetime
    expires_at: datetime
    key_id: str
    single_use: bool = True
    signature: str = ""

    def unsigned_dict(self) -> dict[str, Any]:
        return {
            "version": "1.0",
            "object_type": "satellite_finality_authority",
            "authority_id": self.authority_id,
            "candidate_act_id": self.candidate_act_id,
            "evidence_id": self.evidence_id,
            "scope": self.scope,
            "binding": self.binding,
            "lifetime": {
                "issued_at": iso_z(self.issued_at),
                "expires_at": iso_z(self.expires_at),
                "single_use": self.single_use,
            },
            "protector": {"type": "HMAC-SHA-256-REFERENCE", "key_id": self.key_id},
        }

    def to_dict(self) -> dict[str, Any]:
        result = self.unsigned_dict()
        result["protector"]["signature"] = self.signature
        return result

