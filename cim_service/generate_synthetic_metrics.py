#!/usr/bin/env python3
# generate_synthetic_metrics.py
import argparse, json, math, random
from pathlib import Path
from datetime import datetime, timedelta, timezone

def iso_z(dt): return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def clipped_gauss(mu, sigma, lo=0.0, hi=None):
    v = random.gauss(mu, sigma)
    if hi is not None: v = min(v, hi)
    return max(lo, v)

def gen_point(ns, ts, source):
    # mild diurnal variation for cpu, correlate power to cpu
    hour = ts.hour + ts.minute/60
    diurnal = 0.15 * math.sin((hour/24.0) * 2*math.pi)  # -0.15..+0.15
    base_cpu = 45.0 * (1 + diurnal)
    cpu = round(clipped_gauss(base_cpu, 12, 0, 100), 2)

    base_power = 40 + 1.0 * cpu           # simple linear relation
    power_w = round(clipped_gauss(base_power, 8, 0, None), 1)

    # jitter around namespace defaults
    lat0 = float(ns["network"]["latency_ms"])
    bw0  = float(ns["network"]["bandwidth_mbps"])
    ren0 = float(ns["energyContext"]["renewableShare"])

    latency_ms       = round(clipped_gauss(lat0, max(1.0, lat0*0.1), 0), 1)
    bandwidth_mbps   = round(clipped_gauss(bw0,  bw0*0.05, 1), 1)
    renewable_share  = round(max(0.0, min(1.0, clipped_gauss(ren0, 0.02))), 2)

    return {
        "device_id": ns["NodeID"],
        "ts": iso_z(ts),
        "cpu": cpu,
        "power_w": power_w,
        "latency_ms": latency_ms,
        "bandwidth_mbps": bandwidth_mbps,
        "renewable_share": renewable_share,
        "region": ns["Region"],
        "country": ns["Country"],
        "grid_api": ns["energyContext"].get("gridAPI", ""),
        "source": source,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--namespaces", type=Path, default=Path("namespaces.json"))
    ap.add_argument("--out", type=Path, default=Path("synthetic_metrics.ndjson"))
    ap.add_argument("--days", type=int, default=2, help="How many days back from now")
    ap.add_argument("--freq-mins", type=int, default=3, help="Sampling cadence (minutes)")
    ap.add_argument("--source", default="stream", choices=["stream","batch"])
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)

    ns = json.loads(args.namespaces.read_text())
    end   = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(days=args.days)

    step = timedelta(minutes=args.freq_mins)
    ts   = start

    count = 0
    with args.out.open("w", encoding="utf-8") as f:
        while ts < end:
            for row in ns:
                rec = gen_point(row, ts, args.source)
                f.write(json.dumps(rec) + "\n")
                count += 1
            ts += step

    print(f"Wrote {count} rows to {args.out} "
          f"({len(ns)} devices / every {args.freq_mins} min from {start} to {end})")

if __name__ == "__main__":
    main()
