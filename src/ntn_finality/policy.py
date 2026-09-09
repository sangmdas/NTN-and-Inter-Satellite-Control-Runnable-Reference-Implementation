from __future__ import annotations

from dataclasses import dataclass, field

from .errors import Code, FinalityError
from .models import EpochState, SatelliteCandidateAct


@dataclass
class ConstellationPolicy:
    epochs: EpochState
    allowed_emitters: set[tuple[str, str, str]]
    allowed_beams: dict[str, set[str]]
    allowed_eirp: set[str]
    allowed_administrations: set[str]
    allowed_license_profiles: set[str]
    allowed_provenance: dict[str, set[str]]
    allowed_next_hops: set[str] = field(default_factory=set)
    autonomy_eirp_envelope: set[str] = field(default_factory=lambda: {"LOW", "NOMINAL"})
    max_duration_ms: int = 20
    safe_mode: bool = False

    def validate(self, act: SatelliteCandidateAct) -> dict[str, bool]:
        c = act.command
        if self.safe_mode:
            raise FinalityError(Code.SAFE_MODE, "vehicle or terminal is in safe mode")
        if act.epoch_state.policy_epoch != self.epochs.policy_epoch:
            raise FinalityError(Code.POLICY_EPOCH_MISMATCH, "policy epoch is stale")
        if act.epoch_state.revocation_epoch != self.epochs.revocation_epoch:
            raise FinalityError(Code.REVOCATION_EPOCH_MISMATCH, "revocation epoch is stale")
        if act.epoch_state.overflight_epoch != self.epochs.overflight_epoch:
            raise FinalityError(Code.OVERFLIGHT_MISMATCH, "overflight epoch is stale")
        if (c.vehicle_id, c.act_type, c.frequency_class) not in self.allowed_emitters:
            raise FinalityError(Code.EMITTER_NOT_AUTHORIZED, "vehicle/act/frequency tuple is not authorized")
        if c.beam_id and c.beam_id not in self.allowed_beams.get(c.vehicle_id, set()):
            raise FinalityError(Code.BEAM_OR_VEHICLE_MISMATCH, "beam is not allowed for vehicle")
        if c.eirp_class not in self.allowed_eirp:
            raise FinalityError(Code.EIRP_MISMATCH, "EIRP class is not allowed")
        if c.duration_ms > self.max_duration_ms:
            raise FinalityError(Code.DURATION_MISMATCH, "duration exceeds envelope")
        if c.administration.upper() not in self.allowed_administrations:
            raise FinalityError(Code.ADMINISTRATION_MISMATCH, "administration is not authorized")
        if c.license_profile_id not in self.allowed_license_profiles:
            raise FinalityError(Code.ADMINISTRATION_MISMATCH, "license profile is not authorized")
        if c.act_type == "ISL_FORWARD" and c.next_hop_id not in self.allowed_next_hops:
            raise FinalityError(Code.NEXT_HOP_UNRESOLVED, "next hop is not in current topology")
        if c.source_type == "payload" and c.act_type != "PAYLOAD_CMD":
            raise FinalityError(Code.PATH_LAUNDERING, "payload provenance cannot invoke another emitter class")
        if c.source_type not in self.allowed_provenance.get(c.act_type, set()):
            raise FinalityError(Code.PROVENANCE_MISMATCH, "command source is not authorized for act type")
        if c.command_link_state == "FADED" and c.source_type in {"autonomy", "onboard_scheduler"} and c.eirp_class not in self.autonomy_eirp_envelope:
            raise FinalityError(Code.AUTONOMY_ENVELOPE, "faded-link autonomous command exceeds local envelope")
        return {
            "administration_valid": True,
            "beam_valid": True,
            "duration_valid": True,
            "eirp_valid": True,
            "emitter_allowlisted": True,
            "epoch_valid": True,
            "frequency_valid": True,
            "next_hop_valid": True,
            "path_valid": True,
            "provenance_valid": True,
            "sink_binding_valid": True,
        }
