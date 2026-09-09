from __future__ import annotations

import json
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from ntn_finality.canonical import b64_digest, canonical_json, digest_grant, grant_projection
from ntn_finality.demo import build_demo, command_for
from ntn_finality.errors import Code, FinalityError
from ntn_finality.hardware import DefiniteEffectFailure, UnknownEffectResult
from ntn_finality.models import EpochState, RadioCommand
from ntn_finality.store import SQLiteFinalityStore


ACT_TYPES = (
    "SAT_RF_ENABLE", "UT_TX_ENABLE", "ISL_FORWARD", "BEAM_STEER",
    "GW_FEEDER", "HANDOVER_TX", "PAYLOAD_CMD",
)


class DefiniteFailHardware:
    def effect(self, command, authority_id):
        raise DefiniteEffectFailure("interlock confirmed dark")


class UnknownFailHardware:
    def effect(self, command, authority_id):
        raise UnknownEffectResult("driver response lost")


class ReferenceCase(unittest.TestCase):
    def setUp(self):
        self.command = command_for()
        self.policy, self.store, self.ped, self.sink, self.hardware = build_demo(self.command)

    def issue(self, command=None):
        command = command or self.command
        act = self.ped.prepare(command)
        evidence, authority = self.ped.validate_and_issue(act)
        return act, evidence, authority

    def deny_sink(self, code, live=None, act=None, authority=None):
        if act is None or authority is None:
            act, _, authority = self.issue()
        with self.assertRaises(FinalityError) as caught:
            self.sink.verify_and_effect(act, authority, live or self.command)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(len(self.hardware.effects), 0)


class CoreFlowTests(ReferenceCase):
    def test_candidate_is_non_effective(self):
        act = self.ped.prepare(self.command)
        self.assertEqual(act.status, "NON_EFFECTIVE")
        self.assertEqual(len(self.hardware.effects), 0)

    def test_allow_effects_once(self):
        act, _, authority = self.issue()
        effect_id = self.sink.verify_and_effect(act, authority, self.command)
        self.assertTrue(effect_id.startswith("effect-sat_rf_enable"))
        self.assertEqual(self.store.state(authority.authority_id), "EFFECTED")
        self.assertEqual(len(self.hardware.effects), 1)

    def test_evidence_precedes_authority(self):
        _, evidence, authority = self.issue()
        self.assertIsNotNone(self.store.evidence(evidence.evidence_id))
        self.assertEqual(authority.evidence_id, evidence.evidence_id)

    def test_authority_binds_act_digest(self):
        act, _, authority = self.issue()
        self.assertEqual(authority.binding["candidate_act_digest"], act.candidate_act_digest)

    def test_authority_binds_grant_digest(self):
        act, _, authority = self.issue()
        self.assertEqual(authority.binding["grant_digest"]["value"], act.grant_digest)

    def test_authority_binds_sink(self):
        _, _, authority = self.issue()
        self.assertEqual(authority.binding["finality_sink_id"], self.command.sink_id)

    def test_authority_binds_epochs(self):
        _, _, authority = self.issue()
        self.assertEqual(authority.binding["overflight_epoch"], 1902)
        self.assertEqual(authority.binding["policy_epoch"], 88)
        self.assertEqual(authority.binding["revocation_epoch"], 11)

    def test_authority_is_single_use(self):
        _, _, authority = self.issue()
        self.assertTrue(authority.single_use)

    def test_same_authority_replay(self):
        act, _, authority = self.issue()
        self.sink.verify_and_effect(act, authority, self.command)
        with self.assertRaises(FinalityError) as caught:
            self.sink.verify_and_effect(act, authority, self.command)
        self.assertEqual(caught.exception.code, Code.AUTHORITY_ALREADY_USED)
        self.assertEqual(len(self.hardware.effects), 1)

    def test_second_authority_same_grant_replay(self):
        act1, _, authority1 = self.issue()
        act2, _, authority2 = self.issue()
        self.sink.verify_and_effect(act1, authority1, self.command)
        with self.assertRaises(FinalityError) as caught:
            self.sink.verify_and_effect(act2, authority2, self.command)
        self.assertEqual(caught.exception.code, Code.REPLAY_DETECTED)
        self.assertEqual(len(self.hardware.effects), 1)

    def test_concurrent_consume_exactly_one_effect(self):
        act, _, authority = self.issue()
        barrier = threading.Barrier(2)
        outcomes = []
        def worker():
            barrier.wait()
            try:
                outcomes.append(self.sink.verify_and_effect(act, authority, self.command))
            except Exception as exc:
                outcomes.append(exc)
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(sum(isinstance(value, str) for value in outcomes), 1)
        self.assertEqual(len(self.hardware.effects), 1)

    def test_expiry_boundary_denies(self):
        act, _, authority = self.issue()
        with self.assertRaises(FinalityError) as caught:
            self.sink.verify_and_effect(act, authority, self.command, now=authority.expires_at)
        self.assertEqual(caught.exception.code, Code.EXPIRED_AUTHORITY)

    def test_policy_epoch_change_denies(self):
        act, _, authority = self.issue()
        self.policy.epochs = EpochState(89, 11, 1902)
        self.deny_sink(Code.POLICY_EPOCH_MISMATCH, act=act, authority=authority)

    def test_revocation_epoch_change_denies(self):
        act, _, authority = self.issue()
        self.policy.epochs = EpochState(88, 12, 1902)
        self.deny_sink(Code.REVOCATION_EPOCH_MISMATCH, act=act, authority=authority)

    def test_overflight_boundary_change_denies(self):
        act, _, authority = self.issue()
        self.policy.epochs = EpochState(88, 11, 1903)
        self.deny_sink(Code.OVERFLIGHT_MISMATCH, act=act, authority=authority)

    def test_tampered_authority_signature(self):
        act, _, authority = self.issue()
        self.deny_sink(Code.INVALID_AUTHORITY, act=act, authority=replace(authority, signature="bad"))

    def test_tampered_authority_scope(self):
        act, _, authority = self.issue()
        scope = dict(authority.scope); scope["beam_id"] = "beam-attacker"
        self.deny_sink(Code.INVALID_AUTHORITY, act=act, authority=replace(authority, scope=scope))

    def test_missing_evidence(self):
        act, _, authority = self.issue()
        self.store._conn.execute("PRAGMA foreign_keys=OFF")
        self.store._conn.execute("DELETE FROM evidence WHERE evidence_id=?", (authority.evidence_id,))
        self.deny_sink(Code.EVIDENCE_MISSING, act=act, authority=authority)

    def test_tampered_evidence(self):
        act, evidence, authority = self.issue()
        payload = self.store.evidence(evidence.evidence_id)
        payload["decision"] = "DENY"
        self.store._conn.execute("UPDATE evidence SET payload=? WHERE evidence_id=?", (json.dumps(payload), evidence.evidence_id))
        self.deny_sink(Code.INVALID_AUTHORITY, act=act, authority=authority)

    def test_candidate_mutation_before_issue(self):
        act = self.ped.prepare(self.command)
        altered = replace(act, nonce="different-but-still-long-nonce")
        with self.assertRaises(FinalityError) as caught:
            self.ped.validate_and_issue(altered)
        self.assertEqual(caught.exception.code, Code.ACT_MISMATCH)

    def test_definite_effect_failure_terminal(self):
        act, _, authority = self.issue()
        self.sink.effect_adapter = DefiniteFailHardware()
        with self.assertRaises(DefiniteEffectFailure):
            self.sink.verify_and_effect(act, authority, self.command)
        self.assertEqual(self.store.state(authority.authority_id), "FAILED_DEFINITE")

    def test_unknown_effect_keeps_pending(self):
        act, _, authority = self.issue()
        self.sink.effect_adapter = UnknownFailHardware()
        with self.assertRaises(FinalityError) as caught:
            self.sink.verify_and_effect(act, authority, self.command)
        self.assertEqual(caught.exception.code, Code.EFFECT_RESULT_UNKNOWN)
        self.assertEqual(self.store.state(authority.authority_id), "CONSUMED_PENDING")

    def test_store_reopens(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = SQLiteFinalityStore(f"{tmp}/ntn.db")
            first.close()
            second = SQLiteFinalityStore(f"{tmp}/ntn.db")
            self.assertIsNone(second.state("unknown"))
            second.close()


class PolicyDenialTests(ReferenceCase):
    def assert_ped_denial(self, command, code):
        act = self.ped.prepare(command)
        with self.assertRaises(FinalityError) as caught:
            self.ped.validate_and_issue(act)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(len(self.hardware.effects), 0)

    def test_safe_mode(self):
        self.policy.safe_mode = True
        self.assert_ped_denial(self.command, Code.SAFE_MODE)

    def test_vehicle_emitter_not_allowlisted(self):
        self.assert_ped_denial(replace(self.command, vehicle_id="sat-evil"), Code.EMITTER_NOT_AUTHORIZED)

    def test_frequency_not_allowlisted(self):
        self.assert_ped_denial(replace(self.command, frequency_class="UNLICENSED"), Code.EMITTER_NOT_AUTHORIZED)

    def test_beam_not_allowed_for_vehicle(self):
        self.assert_ped_denial(replace(self.command, beam_id="beam-999"), Code.BEAM_OR_VEHICLE_MISMATCH)

    def test_eirp_class_rejected(self):
        self.assert_ped_denial(replace(self.command, eirp_class="EXTREME"), Code.EIRP_MISMATCH)

    def test_duration_exceeds_envelope(self):
        self.assert_ped_denial(replace(self.command, duration_ms=21), Code.DURATION_MISMATCH)

    def test_administration_rejected(self):
        self.assert_ped_denial(replace(self.command, administration="ZZ"), Code.ADMINISTRATION_MISMATCH)

    def test_license_profile_rejected(self):
        self.assert_ped_denial(replace(self.command, license_profile_id="expired-license"), Code.ADMINISTRATION_MISMATCH)

    def test_payload_path_laundering(self):
        self.assert_ped_denial(replace(self.command, source_type="payload"), Code.PATH_LAUNDERING)

    def test_debug_or_other_provenance_rejected(self):
        self.assert_ped_denial(replace(self.command, source_type="other"), Code.PROVENANCE_MISMATCH)

    def test_faded_link_autonomy_high_eirp(self):
        changed = replace(self.command, source_type="autonomy", command_link_state="FADED", eirp_class="HIGH")
        self.assert_ped_denial(changed, Code.AUTONOMY_ENVELOPE)

    def test_faded_link_autonomy_nominal_allowed(self):
        changed = replace(self.command, source_type="autonomy", command_link_state="FADED", eirp_class="NOMINAL")
        act, _, authority = self.issue(changed)
        self.sink.verify_and_effect(act, authority, changed)
        self.assertEqual(len(self.hardware.effects), 1)

    def test_isl_unknown_next_hop(self):
        command = command_for("ISL_FORWARD")
        policy, _, ped, _, hardware = build_demo(command)
        changed = replace(command, next_hop_id="sat-unknown")
        act = ped.prepare(changed)
        with self.assertRaises(FinalityError) as caught:
            ped.validate_and_issue(act)
        self.assertEqual(caught.exception.code, Code.NEXT_HOP_UNRESOLVED)
        self.assertEqual(len(hardware.effects), 0)


class MalformedCommandTests(ReferenceCase):
    def assert_prepare_denial(self, command, code=Code.MALFORMED_ACT):
        with self.assertRaises(FinalityError) as caught:
            self.ped.prepare(command)
        self.assertEqual(caught.exception.code, code)

    def test_zero_duration(self): self.assert_prepare_denial(replace(self.command, duration_ms=0))
    def test_negative_duration(self): self.assert_prepare_denial(replace(self.command, duration_ms=-1))
    def test_boolean_duration(self): self.assert_prepare_denial(replace(self.command, duration_ms=True))
    def test_negative_sequence(self): self.assert_prepare_denial(replace(self.command, grant_sequence=-1))
    def test_unknown_act_type(self): self.assert_prepare_denial(replace(self.command, act_type="UNKNOWN"))
    def test_unknown_sink_type(self): self.assert_prepare_denial(replace(self.command, sink_type="UNKNOWN"))
    def test_empty_vehicle(self): self.assert_prepare_denial(replace(self.command, vehicle_id=""))
    def test_empty_sink(self): self.assert_prepare_denial(replace(self.command, sink_id=""))
    def test_isl_missing_next_hop(self):
        self.assert_prepare_denial(replace(command_for("ISL_FORWARD"), next_hop_id=""), Code.NEXT_HOP_UNRESOLVED)


class VectorTests(unittest.TestCase):
    def test_sat_rf_vector(self): self._check("sat-rf-enable")
    def test_ut_tx_vector(self): self._check("ut-tx-enable")
    def test_isl_vector(self): self._check("isl-forward")

    def _check(self, name):
        path = Path(__file__).parents[1] / "test-vectors" / f"{name}.json"
        vector = json.loads(path.read_text(encoding="utf-8"))
        command = RadioCommand(**vector["command"])
        self.assertEqual(canonical_json(grant_projection(command)).decode(), vector["expected_canonical_utf8"])
        self.assertEqual(digest_grant(command), vector["expected_digest"])


def _make_allow_test(act_type):
    def test(self):
        command = command_for(act_type)
        _, store, ped, sink, hardware = build_demo(command)
        act = ped.prepare(command)
        _, authority = ped.validate_and_issue(act)
        sink.verify_and_effect(act, authority, command)
        self.assertEqual(store.state(authority.authority_id), "EFFECTED")
        self.assertEqual(len(hardware.effects), 1)
    return test


class SatellitePathAllowTests(unittest.TestCase):
    pass


for _act_type in ACT_TYPES:
    setattr(SatellitePathAllowTests, f"test_allow_{_act_type.lower()}", _make_allow_test(_act_type))


MUTATIONS = {
    "act_type": "UT_TX_ENABLE",
    "vehicle_id": "sat-12042",
    "constellation_id": "other-constellation",
    "orbit_shell": "shell-1200",
    "beam_id": "beam-18",
    "cell_id": "cell-other",
    "pointing_ref": "pointing-other",
    "frequency_class": "KA_DL",
    "eirp_class": "HIGH",
    "polarization": "LHCP",
    "duration_ms": 6,
    "next_hop_type": "GATEWAY",
    "next_hop_id": "gw-in-3",
    "administration": "US",
    "license_profile_id": "lic-other",
    "source_type": "ground_noc",
    "grant_sequence": 442,
    "flow_digest": "flow-other",
    "slot_set": "slot-25:29",
    "command_link_state": "FADED",
}


def _make_substitution_test(field, value):
    def test(self):
        live = replace(self.command, **{field: value})
        self.deny_sink(Code.GRANT_SUBSTITUTION, live=live)
    return test


class GrantSubstitutionTests(ReferenceCase):
    def test_sink_id_substitution(self):
        self.deny_sink(Code.SINK_MISMATCH, live=replace(self.command, sink_id="other-sink"))
    def test_sink_type_substitution(self):
        self.deny_sink(Code.SINK_MISMATCH, live=replace(self.command, sink_type="UT_TX_ENABLE"))


for _field, _value in MUTATIONS.items():
    setattr(GrantSubstitutionTests, f"test_{_field}_substitution", _make_substitution_test(_field, _value))


if __name__ == "__main__":
    unittest.main()

