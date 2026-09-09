from __future__ import annotations

import json
from dataclasses import replace

from .crypto import HMACAuthenticator
from .hardware import SimulatedEffectSink
from .models import EpochState, RadioCommand
from .ped import ProtectedEnforcementDomain
from .policy import ConstellationPolicy
from .sink import ApertureFinalitySink
from .store import SQLiteFinalityStore


def command_for(act_type: str = "SAT_RF_ENABLE") -> RadioCommand:
    base = RadioCommand(
        act_type="SAT_RF_ENABLE", vehicle_id="sat-12041", constellation_id="leo-mesh-a",
        orbit_shell="shell-550", beam_id="beam-17", cell_id="cell-in-441",
        pointing_ref="pointing-1902-17", frequency_class="KU_DL", eirp_class="NOMINAL",
        polarization="RHCP", duration_ms=5, next_hop_type="UT", next_hop_id="ut-dish-88",
        administration="IN", license_profile_id="lic-in-ku-7", source_type="onboard_scheduler",
        sink_id="sat-12041-pa-svc", sink_type="SAT_RF_ENABLE", grant_sequence=441,
        flow_digest="flow-users-441", slot_set="slot-20:24",
    )
    variants = {
        "SAT_RF_ENABLE": base,
        "UT_TX_ENABLE": replace(base, act_type="UT_TX_ENABLE", vehicle_id="ut-dish-88",
            orbit_shell="ground", beam_id="beam-17", frequency_class="KU_UL",
            next_hop_type="ISL", next_hop_id="sat-12041", source_type="ut_modem",
            sink_id="ut-dish-88-pa", sink_type="UT_TX_ENABLE"),
        "ISL_FORWARD": replace(base, act_type="ISL_FORWARD", beam_id="", cell_id="",
            pointing_ref="isl-terminal-a", frequency_class="OPTICAL_ISL", eirp_class="NOMINAL",
            next_hop_type="ISL", next_hop_id="sat-12042", source_type="onboard_scheduler",
            sink_id="sat-12041-isl-a", sink_type="ISL_FORWARD"),
        "BEAM_STEER": replace(base, act_type="BEAM_STEER", duration_ms=2,
            next_hop_type="NONE", next_hop_id="", sink_id="sat-12041-beam-driver",
            sink_type="BEAM_STEER"),
        "GW_FEEDER": replace(base, act_type="GW_FEEDER", vehicle_id="gw-in-3",
            orbit_shell="ground", beam_id="gateway-beam-a", cell_id="",
            frequency_class="KA_FEEDER", next_hop_type="ISL", next_hop_id="sat-12041",
            source_type="ground_noc", sink_id="gw-in-3-feeder", sink_type="GW_FEEDER"),
        "HANDOVER_TX": replace(base, act_type="HANDOVER_TX", beam_id="beam-18",
            cell_id="cell-in-442", pointing_ref="pointing-1902-18", next_hop_id="ut-dish-99",
            sink_id="sat-12041-pa-svc", sink_type="SAT_RF_ENABLE", grant_sequence=442),
        "PAYLOAD_CMD": replace(base, act_type="PAYLOAD_CMD", beam_id="payload-beam-1",
            cell_id="", pointing_ref="payload-pointing", frequency_class="S_PAYLOAD",
            eirp_class="LOW", next_hop_type="GATEWAY", next_hop_id="gw-in-3",
            source_type="payload", sink_id="sat-12041-payload-radio", sink_type="PAYLOAD_CMD"),
    }
    return variants[act_type]


def build_demo(command: RadioCommand | None = None):
    command = command or command_for()
    epochs = EpochState(policy_epoch=88, revocation_epoch=11, overflight_epoch=1902)
    all_commands = [command_for(name) for name in (
        "SAT_RF_ENABLE", "UT_TX_ENABLE", "ISL_FORWARD", "BEAM_STEER",
        "GW_FEEDER", "HANDOVER_TX", "PAYLOAD_CMD",
    )]
    policy = ConstellationPolicy(
        epochs=epochs,
        allowed_emitters={(c.vehicle_id, c.act_type, c.frequency_class) for c in all_commands},
        allowed_beams={
            "sat-12041": {"beam-17", "beam-18", "payload-beam-1"},
            "ut-dish-88": {"beam-17"},
            "gw-in-3": {"gateway-beam-a"},
        },
        allowed_eirp={"LOW", "NOMINAL", "HIGH"},
        allowed_administrations={"IN"},
        allowed_license_profiles={"lic-in-ku-7"},
        allowed_provenance={
            "SAT_RF_ENABLE": {"ground_noc", "onboard_scheduler", "autonomy"},
            "UT_TX_ENABLE": {"ut_modem"},
            "ISL_FORWARD": {"onboard_scheduler", "autonomy"},
            "BEAM_STEER": {"ground_noc", "onboard_scheduler", "autonomy"},
            "GW_FEEDER": {"ground_noc"},
            "HANDOVER_TX": {"onboard_scheduler", "ntn_cu"},
            "PAYLOAD_CMD": {"payload"},
        },
        allowed_next_hops={"sat-12041", "sat-12042"},
        max_duration_ms=20,
    )
    store = SQLiteFinalityStore()
    auth = HMACAuthenticator(b"ntn-reference-key-material-32bytes!!")
    hardware = SimulatedEffectSink()
    ped = ProtectedEnforcementDomain(policy, store, auth)
    sink = ApertureFinalitySink(command.sink_id, command.sink_type, store, auth, hardware, lambda: policy.epochs)
    return policy, store, ped, sink, hardware


def main() -> None:
    command = command_for()
    _, store, ped, sink, hardware = build_demo(command)
    act = ped.prepare(command)
    evidence, authority = ped.validate_and_issue(act)
    effect_id = sink.verify_and_effect(act, authority, command)
    print(json.dumps({
        "candidate_status": act.status,
        "grant_digest": act.grant_digest,
        "candidate_act_digest": act.candidate_act_digest,
        "evidence_id": evidence.evidence_id,
        "authority_id": authority.authority_id,
        "authority_state": store.state(authority.authority_id),
        "effect_id": effect_id,
        "simulated_effect_count": len(hardware.effects),
    }, indent=2))


if __name__ == "__main__":
    main()
