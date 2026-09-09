from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from .errors import Code, FinalityError
from .models import RadioCommand


ACT_TYPES = {
    "SAT_RF_ENABLE", "UT_TX_ENABLE", "ISL_FORWARD", "BEAM_STEER",
    "GW_FEEDER", "HANDOVER_TX", "PAYLOAD_CMD", "OTHER",
}
SINK_TYPES = {
    "SAT_RF_ENABLE", "UT_TX_ENABLE", "ISL_FORWARD", "BEAM_STEER",
    "GW_FEEDER", "PAYLOAD_CMD", "OTHER",
}
NEXT_HOP_TYPES = {"ISL", "GATEWAY", "UT", "NONE"}
SOURCE_TYPES = {"ground_noc", "onboard_scheduler", "ntn_cu", "ut_modem", "payload", "autonomy", "other"}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def b64_digest(value: Any) -> str:
    digest = hashlib.sha256(canonical_json(value)).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def validate_command(command: RadioCommand) -> None:
    if command.act_type not in ACT_TYPES or command.sink_type not in SINK_TYPES:
        raise FinalityError(Code.MALFORMED_ACT, "unsupported act or sink type")
    if command.next_hop_type not in NEXT_HOP_TYPES or command.source_type not in SOURCE_TYPES:
        raise FinalityError(Code.MALFORMED_ACT, "unsupported next-hop or source type")
    required = (command.vehicle_id, command.constellation_id, command.frequency_class,
                command.eirp_class, command.administration, command.license_profile_id,
                command.sink_id)
    if any(not isinstance(value, str) or not value for value in required):
        raise FinalityError(Code.MALFORMED_ACT, "required identifier is empty")
    if not isinstance(command.duration_ms, int) or isinstance(command.duration_ms, bool) or command.duration_ms <= 0:
        raise FinalityError(Code.MALFORMED_ACT, "duration_ms must be a positive integer")
    if command.grant_sequence < 0:
        raise FinalityError(Code.MALFORMED_ACT, "grant_sequence must be non-negative")
    if command.act_type == "ISL_FORWARD" and (command.next_hop_type != "ISL" or not command.next_hop_id):
        raise FinalityError(Code.NEXT_HOP_UNRESOLVED, "ISL forward requires a resolved ISL next hop")
    if command.act_type in {"SAT_RF_ENABLE", "UT_TX_ENABLE", "BEAM_STEER", "HANDOVER_TX"} and not command.beam_id:
        raise FinalityError(Code.MALFORMED_ACT, "beam-bound act requires beam_id")


def grant_projection(command: RadioCommand) -> dict[str, Any]:
    """Explicit load-bearing RF/ISL command projection."""
    return {
        "act_type": command.act_type,
        "vehicle": {
            "vehicle_id": command.vehicle_id,
            "constellation_id": command.constellation_id,
            "orbit_shell": command.orbit_shell,
        },
        "beam": {
            "beam_id": command.beam_id,
            "cell_id": command.cell_id,
            "pointing_ref": command.pointing_ref,
        },
        "radio": {
            "frequency_class": command.frequency_class,
            "eirp_class": command.eirp_class,
            "polarization": command.polarization,
            "duration_ms": command.duration_ms,
            "slot_set": command.slot_set,
        },
        "next_hop": {
            "hop_type": command.next_hop_type,
            "next_hop_id": command.next_hop_id,
            "flow_digest": command.flow_digest,
        },
        "regulatory": {
            "administration": command.administration.upper(),
            "license_profile_id": command.license_profile_id,
        },
        "provenance": {
            "source_type": command.source_type,
            "grant_sequence": command.grant_sequence,
            "command_link_state": command.command_link_state,
        },
        "sink": {"sink_id": command.sink_id, "sink_type": command.sink_type},
    }


def digest_grant(command: RadioCommand) -> str:
    validate_command(command)
    return b64_digest(grant_projection(command))

