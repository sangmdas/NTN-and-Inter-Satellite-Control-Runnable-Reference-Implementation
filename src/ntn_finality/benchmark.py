from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import statistics
import time
from dataclasses import replace

from .demo import build_demo, command_for


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * p))]


def summarize(values_ns: list[int]) -> dict[str, float]:
    values = [v / 1_000 for v in values_ns]
    return {
        "min_us": round(min(values), 2), "mean_us": round(statistics.fmean(values), 2),
        "p50_us": round(percentile(values, .50), 2), "p95_us": round(percentile(values, .95), 2),
        "p99_us": round(percentile(values, .99), 2), "max_us": round(max(values), 2),
    }


def run(iterations: int, warmup: int, act_type: str) -> dict:
    base = command_for(act_type)
    policy, _, ped, sink, _ = build_demo(base)
    samples = {"prepare": [], "ped_issue": [], "sink_verify_consume_effect": [], "total": []}
    for i in range(iterations + warmup):
        command = replace(base, grant_sequence=10_000 + i, slot_set=f"bench-slot-{i}")
        t0 = time.perf_counter_ns()
        act = ped.prepare(command)
        t1 = time.perf_counter_ns()
        _, authority = ped.validate_and_issue(act)
        t2 = time.perf_counter_ns()
        sink.verify_and_effect(act, authority, command)
        t3 = time.perf_counter_ns()
        if i >= warmup:
            samples["prepare"].append(t1 - t0)
            samples["ped_issue"].append(t2 - t1)
            samples["sink_verify_consume_effect"].append(t3 - t2)
            samples["total"].append(t3 - t0)
    return {
        "warning": "Local software benchmark with in-memory SQLite and simulated hardware; not an RF timing, flight-qualification, or safety SLA.",
        "draft_numeric_target": None,
        "reference_engineering_targets": {
            "sink_p99_us": 1000,
            "full_local_path_p99_us": 5000,
            "status": "repository goals, not requirements from draft-das-ntn-rf-execution-finality-00",
        },
        "environment": {
            "python": platform.python_version(), "implementation": platform.python_implementation(),
            "platform": platform.platform(), "sqlite": sqlite3.sqlite_version,
            "store": "SQLite :memory:", "authenticator": "HMAC-SHA-256 software",
            "effect_adapter": "in-process non-radiating simulator", "act_type": act_type,
        },
        "iterations": iterations, "warmup": warmup,
        "results": {name: summarize(values) for name, values in samples.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--warmup", type=int, default=100)
    parser.add_argument("--act-type", choices=("SAT_RF_ENABLE", "UT_TX_ENABLE", "ISL_FORWARD", "BEAM_STEER", "GW_FEEDER", "HANDOVER_TX", "PAYLOAD_CMD"), default="SAT_RF_ENABLE")
    args = parser.parse_args()
    if args.iterations < 1 or args.warmup < 0:
        parser.error("iterations must be positive and warmup non-negative")
    print(json.dumps(run(args.iterations, args.warmup, args.act_type), indent=2))


if __name__ == "__main__":
    main()

