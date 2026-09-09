from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .canonical import digest_grant
from .crypto import Authenticator
from .errors import Code, FinalityError
from .hardware import DefiniteEffectFailure, EffectAdapter, UnknownEffectResult
from .models import EpochState, RadioCommand, SatelliteCandidateAct, SatelliteFinalityAuthority
from .store import SQLiteFinalityStore


class ApertureFinalitySink:
    def __init__(self, sink_id: str, sink_type: str, store: SQLiteFinalityStore,
                 authenticator: Authenticator, effect_adapter: EffectAdapter,
                 current_epochs: Callable[[], EpochState]) -> None:
        self.sink_id = sink_id
        self.sink_type = sink_type
        self.store = store
        self.authenticator = authenticator
        self.effect_adapter = effect_adapter
        self.current_epochs = current_epochs

    def verify_and_effect(self, act: SatelliteCandidateAct, authority: SatelliteFinalityAuthority,
                          live_command: RadioCommand, now: datetime | None = None) -> str:
        now = now or datetime.now(timezone.utc)
        if not self.authenticator.verify(authority.unsigned_dict(), authority.signature):
            raise FinalityError(Code.INVALID_AUTHORITY, "authority integrity check failed")
        evidence = self.store.evidence(authority.evidence_id)
        if evidence is None:
            raise FinalityError(Code.EVIDENCE_MISSING, "protected validation evidence cannot be resolved")
        evidence_signature = evidence["protector"].pop("signature")
        if not self.authenticator.verify(evidence, evidence_signature):
            raise FinalityError(Code.INVALID_AUTHORITY, "evidence integrity check failed")
        if (evidence.get("decision") != "ALLOW" or
                evidence.get("candidate_act_id") != act.candidate_act_id or
                evidence.get("candidate_act_digest") != act.candidate_act_digest or
                evidence.get("grant_digest") != act.grant_digest or
                not evidence.get("validated_predicates") or
                not all(evidence["validated_predicates"].values())):
            raise FinalityError(Code.INVALID_AUTHORITY, "evidence does not validate this act")
        if authority.candidate_act_id != act.candidate_act_id or authority.binding["candidate_act_digest"] != act.candidate_act_digest:
            raise FinalityError(Code.ACT_MISMATCH, "authority does not bind this Candidate Act")
        if now >= authority.expires_at:
            raise FinalityError(Code.EXPIRED_AUTHORITY, "authority expired")
        if (authority.binding["finality_sink_id"] != self.sink_id or
                live_command.sink_id != self.sink_id or
                authority.scope["sink_type"] != self.sink_type or
                live_command.sink_type != self.sink_type):
            raise FinalityError(Code.SINK_MISMATCH, "sink ID or type mismatch")

        epochs = self.current_epochs()
        if authority.binding["policy_epoch"] != epochs.policy_epoch:
            raise FinalityError(Code.POLICY_EPOCH_MISMATCH, "policy epoch is stale")
        if authority.binding["revocation_epoch"] != epochs.revocation_epoch:
            raise FinalityError(Code.REVOCATION_EPOCH_MISMATCH, "revocation epoch is stale")
        if authority.binding["overflight_epoch"] != epochs.overflight_epoch:
            raise FinalityError(Code.OVERFLIGHT_MISMATCH, "overflight epoch is stale")

        live_digest = digest_grant(live_command)
        if live_digest != act.grant_digest or live_digest != authority.binding["grant_digest"]["value"]:
            raise FinalityError(Code.GRANT_SUBSTITUTION, "live RF/ISL command digest changed")

        s = authority.scope
        checks = (
            (live_command.act_type == s["act_type"], Code.ACT_TYPE_MISMATCH, "act type mismatch"),
            (live_command.vehicle_id == s["vehicle_id"] and live_command.beam_id == s["beam_id"], Code.BEAM_OR_VEHICLE_MISMATCH, "beam or vehicle mismatch"),
            (live_command.frequency_class == s["frequency_class"], Code.FREQUENCY_MISMATCH, "frequency mismatch"),
            (live_command.eirp_class == s["eirp_class"], Code.EIRP_MISMATCH, "EIRP mismatch"),
            (live_command.duration_ms == s["duration_ms"], Code.DURATION_MISMATCH, "duration mismatch"),
            (live_command.next_hop_type == s["next_hop_type"] and live_command.next_hop_id == s["next_hop_id"], Code.NEXT_HOP_MISMATCH, "next hop mismatch"),
            (live_command.administration.upper() == s["administration"] and live_command.license_profile_id == s["license_profile_id"], Code.ADMINISTRATION_MISMATCH, "administration or license mismatch"),
            (live_command.source_type == s["source_type"], Code.PROVENANCE_MISMATCH, "provenance mismatch"),
        )
        for passed, code, message in checks:
            if not passed:
                raise FinalityError(code, message)

        self.store.reserve(authority.authority_id, live_digest, self.sink_id)
        try:
            effect_id = self.effect_adapter.effect(live_command, authority.authority_id)
        except DefiniteEffectFailure:
            self.store.fail_definite(authority.authority_id)
            raise
        except UnknownEffectResult as exc:
            raise FinalityError(Code.EFFECT_RESULT_UNKNOWN, "force safe output and reconcile hardware state", False) from exc
        except Exception as exc:
            raise FinalityError(Code.EFFECT_RESULT_UNKNOWN, "unclassified hardware outcome; fail closed", False) from exc
        self.store.complete(authority.authority_id, effect_id)
        return effect_id

