from __future__ import annotations

import secrets
from dataclasses import replace
from datetime import timedelta
from typing import Callable

from .canonical import b64_digest, digest_grant, validate_command
from .crypto import Authenticator
from .errors import Code, FinalityError
from .models import (
    ProtectedValidationEvidence, RadioCommand, SatelliteCandidateAct,
    SatelliteFinalityAuthority, utc_now,
)
from .policy import ConstellationPolicy
from .store import SQLiteFinalityStore


class ProtectedEnforcementDomain:
    def __init__(self, policy: ConstellationPolicy, store: SQLiteFinalityStore,
                 authenticator: Authenticator, ttl_seconds: float = 8.0,
                 clock: Callable = utc_now) -> None:
        self.policy = policy
        self.store = store
        self.authenticator = authenticator
        self.ttl_seconds = ttl_seconds
        self.clock = clock

    def prepare(self, command: RadioCommand) -> SatelliteCandidateAct:
        validate_command(command)
        now = self.clock()
        act = SatelliteCandidateAct(
            candidate_act_id="act-sat-" + secrets.token_urlsafe(16),
            command=command,
            grant_digest=digest_grant(command),
            candidate_act_digest="",
            epoch_state=self.policy.epochs,
            nonce=secrets.token_urlsafe(24),
            created_at=now,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        return replace(act, candidate_act_digest=b64_digest(act.unsigned_projection()))

    def validate_and_issue(self, act: SatelliteCandidateAct) -> tuple[ProtectedValidationEvidence, SatelliteFinalityAuthority]:
        now = self.clock()
        if act.status != "NON_EFFECTIVE" or now >= act.expires_at:
            raise FinalityError(Code.EXPIRED_AUTHORITY, "candidate is stale or not non-effective")
        if b64_digest(act.unsigned_projection()) != act.candidate_act_digest:
            raise FinalityError(Code.ACT_MISMATCH, "Candidate Act fields changed after preparation")
        predicates = self.policy.validate(act)
        evidence = ProtectedValidationEvidence(
            evidence_id="pve-sat-" + secrets.token_urlsafe(16),
            candidate_act_id=act.candidate_act_id,
            candidate_act_digest=act.candidate_act_digest,
            grant_digest=act.grant_digest,
            predicates=predicates,
            issued_at=now,
            key_id=self.authenticator.key_id,
        )
        evidence = replace(evidence, signature=self.authenticator.sign(evidence.unsigned_dict()))
        self.store.commit_evidence(evidence)

        c = act.command
        authority = SatelliteFinalityAuthority(
            authority_id="sfa-" + secrets.token_urlsafe(16),
            candidate_act_id=act.candidate_act_id,
            evidence_id=evidence.evidence_id,
            scope={
                "act_type": c.act_type, "vehicle_id": c.vehicle_id,
                "beam_id": c.beam_id, "frequency_class": c.frequency_class,
                "eirp_class": c.eirp_class, "duration_ms": c.duration_ms,
                "next_hop_type": c.next_hop_type, "next_hop_id": c.next_hop_id,
                "administration": c.administration.upper(),
                "license_profile_id": c.license_profile_id,
                "source_type": c.source_type, "sink_type": c.sink_type,
            },
            binding={
                "candidate_act_digest": act.candidate_act_digest,
                "grant_digest": {"algorithm": "SHA-256", "value": act.grant_digest},
                "nonce": act.nonce,
                "overflight_epoch": act.epoch_state.overflight_epoch,
                "policy_epoch": act.epoch_state.policy_epoch,
                "revocation_epoch": act.epoch_state.revocation_epoch,
                "finality_sink_id": c.sink_id,
            },
            issued_at=now,
            expires_at=act.expires_at,
            key_id=self.authenticator.key_id,
        )
        authority = replace(authority, signature=self.authenticator.sign(authority.unsigned_dict()))
        self.store.register(authority)
        return evidence, authority

