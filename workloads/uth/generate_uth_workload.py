#!/usr/bin/env python3
"""
Generate synthetic UTH-style workload/experiment telemetry in the format:

{
  "exec_unit_id": "exec_<unix_seconds>",
  "src_node": "node08",
  "dst_node": "node07",
  "start_time": "2025-12-22T08:45:48.988587Z",
  "end_time": "2025-12-22T08:47:58.554446Z",
  "duration_s": 129.565859,
  "data_amount_mb": 30.0,
  "bandwidth_req_mbps": 2.4,
  "throughput_mbps": 1.12,
  "jitter_ms": 8.734,
  "packet_loss_percent": 45.0,
  "energy_results": {
    "total_tx_Wh": 0.0261,
    "total_rx_Wh": 0.0041,
    "total_energy_Wh": 0.0302,
    "MB": 15.99
  }
}

Defaults:
- Generates one year
- 3 nodes
- All directed src->dst pairs (no self links)
- Fixed interval (default 5 minutes)
- JSONL output (one record per line)
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Tuple


def iso_z(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    # Keep microseconds for realism
    return dt.isoformat(timespec="microseconds").replace("+00:00", "Z")


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def diurnal_congestion_factor(hour_utc: int) -> float:
    """
    Returns ~0..1. Higher means more congestion (worse throughput, higher loss/jitter).
    Roughly peaks mid-day to early evening.
    """
    # Shift phase so congestion peaks around 15:00 UTC-ish
    phase = (hour_utc - 15) / 24.0 * 2.0 * math.pi
    s = (math.sin(phase) + 1.0) / 2.0  # 0..1
    return clamp(0.15 + 0.85 * s, 0.0, 1.0)


@dataclass(frozen=True)
class LinkProfile:
    efficiency_bias: float   # multiplies req->throughput efficiency
    loss_bias: float         # additive percent points
    jitter_bias: float       # additive ms
    tx_power_bias: float     # multiplicative
    rx_power_bias: float     # multiplicative


def build_link_profiles(nodes: List[str], rng: random.Random) -> Dict[Tuple[str, str], LinkProfile]:
    profiles: Dict[Tuple[str, str], LinkProfile] = {}
    for src in nodes:
        for dst in nodes:
            if src == dst:
                continue
            # Create stable heterogeneity per link
            profiles[(src, dst)] = LinkProfile(
                efficiency_bias=clamp(rng.gauss(1.0, 0.08), 0.75, 1.25),
                loss_bias=clamp(rng.gauss(0.4, 0.6), -0.2, 3.0),
                jitter_bias=clamp(rng.gauss(0.8, 1.2), 0.0, 8.0),
                tx_power_bias=clamp(rng.gauss(1.0, 0.07), 0.8, 1.25),
                rx_power_bias=clamp(rng.gauss(1.0, 0.07), 0.8, 1.25),
            )
    return profiles


def sample_data_amount_mb(rng: random.Random) -> float:
    # Typical payload sizes, weighted
    choices = [(10.0, 0.20), (30.0, 0.35), (50.0, 0.25), (100.0, 0.15), (200.0, 0.05)]
    r = rng.random()
    acc = 0.0
    for val, w in choices:
        acc += w
        if r <= acc:
            return val
    return choices[-1][0]


def sample_bandwidth_req_mbps(data_amount_mb: float, rng: random.Random) -> float:
    # A bit correlated with data size, still noisy.
    base = 1.5 + 0.012 * data_amount_mb  # 10MB -> ~1.62, 200MB -> ~3.9
    req = rng.gauss(base, 0.8)
    return round(clamp(req, 0.5, 15.0), 3)


def generate_record(
    start: datetime,
    src: str,
    dst: str,
    link: LinkProfile,
    rng: random.Random,
) -> Dict:
    congestion = diurnal_congestion_factor(start.hour)

    data_amount_mb = sample_data_amount_mb(rng)
    bandwidth_req_mbps = sample_bandwidth_req_mbps(data_amount_mb, rng)

    # Throughput is a fraction of requested bandwidth.
    # Efficiency drops with congestion; link adds stable bias.
    efficiency = rng.lognormvariate(mu=-0.25, sigma=0.35)  # typical ~0.6–0.9 with tail
    efficiency *= (1.0 - 0.45 * congestion)
    efficiency *= link.efficiency_bias
    efficiency = clamp(efficiency, 0.08, 1.05)

    throughput_mbps = bandwidth_req_mbps * efficiency
    throughput_mbps = round(clamp(throughput_mbps, 0.05, bandwidth_req_mbps), 3)

    # Jitter and loss rise with congestion, with occasional nasty spikes.
    base_jitter = rng.lognormvariate(mu=math.log(2.0 + 10.0 * congestion), sigma=0.45)
    jitter_ms = base_jitter + link.jitter_bias + rng.random() * 0.5
    jitter_ms = round(clamp(jitter_ms, 0.1, 250.0), 3)

    loss = max(0.0, rng.gauss(0.3 + 2.0 * congestion, 0.9) + link.loss_bias)
    if rng.random() < 0.015:  # rare bad events
        loss += rng.uniform(8.0, 60.0)
    packet_loss_percent = round(clamp(loss, 0.0, 80.0), 3)

    # Duration roughly based on payload and throughput, plus overhead/noise.
    # Mbps -> MB/s is Mbps/8. Transfer time ~ data / (throughput/8) = 8*data/throughput
    min_thr = max(throughput_mbps, 0.08)
    transfer_time_s = 8.0 * data_amount_mb / min_thr
    overhead_s = rng.uniform(3.0, 18.0)
    duration_s = (transfer_time_s + overhead_s) * rng.uniform(0.75, 1.25)
    duration_s = round(clamp(duration_s, 1.0, 3600.0), 6)

    end = start + timedelta(seconds=duration_s)

    # Effective MB after loss (matches your sample vibe where MB != data_amount_mb).
    effective_mb = data_amount_mb * (1.0 - packet_loss_percent / 100.0) * rng.uniform(0.92, 1.02)
    effective_mb = round(clamp(effective_mb, 0.0, data_amount_mb), 6)

    # Energy model (simple but plausible and close to your sample magnitudes).
    # Power grows mildly with throughput and jitter/loss overhead.
    tx_power_w = (0.70 + 0.10 * throughput_mbps) * link.tx_power_bias * (1.0 + 0.10 * congestion)
    rx_power_w = (0.12 + 0.05 * throughput_mbps) * link.rx_power_bias * (1.0 + 0.08 * congestion)

    # Extra overhead when loss/jitter is bad (retries, buffering, etc).
    overhead_factor = 1.0 + 0.003 * packet_loss_percent + 0.0015 * min(jitter_ms, 100.0)
    tx_wh = tx_power_w * (duration_s / 3600.0) * overhead_factor * rng.uniform(0.93, 1.07)
    rx_wh = rx_power_w * (duration_s / 3600.0) * overhead_factor * rng.uniform(0.93, 1.07)

    total_tx_Wh = round(max(0.0, tx_wh), 15)
    total_rx_Wh = round(max(0.0, rx_wh), 15)
    total_energy_Wh = round(total_tx_Wh + total_rx_Wh, 15)

    exec_unit_id = f"exec_{int(start.timestamp())}"

    return {
        "exec_unit_id": exec_unit_id,
        "src_node": src,
        "dst_node": dst,
        "start_time": iso_z(start),
        "end_time": iso_z(end),
        "duration_s": duration_s,
        "data_amount_mb": float(round(data_amount_mb, 3)),
        "bandwidth_req_mbps": float(bandwidth_req_mbps),
        "throughput_mbps": float(throughput_mbps),
        "jitter_ms": float(jitter_ms),
        "packet_loss_percent": float(packet_loss_percent),
        "energy_results": {
            "total_tx_Wh": float(total_tx_Wh),
            "total_rx_Wh": float(total_rx_Wh),
            "total_energy_Wh": float(total_energy_Wh),
            "MB": float(effective_mb),
        },
    }


def iter_pairs(nodes: List[str]) -> Iterable[Tuple[str, str]]:
    for src in nodes:
        for dst in nodes:
            if src != dst:
                yield src, dst


def parse_dt(s: str) -> datetime:
    # Accept YYYY-MM-DD or full ISO; assume UTC if no tz
    if "T" not in s:
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-01-01", help="Start date/time (YYYY-MM-DD or ISO). Default: 2025-01-01")
    ap.add_argument("--end", default="2026-01-01", help="End date/time (exclusive). Default: 2026-01-01")
    ap.add_argument("--interval-seconds", type=int, default=300, help="Granularity. Default: 300 (5 minutes)")
    ap.add_argument("--nodes", default="node07,node08,node09", help="Comma-separated node names (3 nodes recommended)")
    ap.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    ap.add_argument("--format", choices=["jsonl", "json"], default="jsonl", help="Output format. Default: jsonl")
    ap.add_argument("--out", required=True, help="Output path (e.g., workloads/uth/uth_workload_2025.jsonl)")
    args = ap.parse_args()

    start = parse_dt(args.start)
    end = parse_dt(args.end)
    if end <= start:
        raise SystemExit("end must be after start")

    nodes = [n.strip() for n in args.nodes.split(",") if n.strip()]
    if len(nodes) < 2:
        raise SystemExit("need at least 2 nodes")

    rng = random.Random(args.seed)
    link_profiles = build_link_profiles(nodes, rng)

    interval = timedelta(seconds=args.interval_seconds)
    t = start

    if args.format == "jsonl":
        with open(args.out, "w", encoding="utf-8") as f:
            while t < end:
                for src, dst in iter_pairs(nodes):
                    rec = generate_record(t, src, dst, link_profiles[(src, dst)], rng)
                    f.write(json.dumps(rec, separators=(",", ":")) + "\n")
                t += interval
    else:
        all_recs = []
        while t < end:
            for src, dst in iter_pairs(nodes):
                all_recs.append(generate_record(t, src, dst, link_profiles[(src, dst)], rng))
            t += interval
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(all_recs, f, separators=(",", ":"), ensure_ascii=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
