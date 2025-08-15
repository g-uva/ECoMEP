# generate_synthetic_metrics.py (aligned to HERMIS + MQTT schema)
import os
import argparse, json, math, random, re
from pathlib import Path
from datetime import datetime, timedelta, timezone

def iso_z(dt): return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

def clipped(v, lo=None, hi=None):
    if lo is not None: v = max(lo, v)
    if hi is not None: v = min(hi, v)
    return v

def clipped_gauss(mu, sigma, lo=None, hi=None):
    return clipped(random.gauss(mu, sigma), lo, hi)

def autogen_nodes(n=12):
    regions = [
        ("North Netherlands","Netherlands"), ("Randstad","Netherlands"),
        ("Lombardy","Italy"), ("Tuscany","Italy"),
        ("Budapest","Hungary"), ("Transdanubia","Hungary"),
        ("Madrid","Spain"), ("Catalonia","Spain"),
        ("Île-de-France","France"), ("Berlin-Brandenburg","Germany")
    ]
    out = []
    for i in range(n):
        region, country = regions[i % len(regions)]
        node_id = f"{country[:2].upper()}-{slug(region)[:4].upper()}-EDGE{(i%3)+1:02d}"
        out.append({
            "Region": region, "Country": country, "NodeID": node_id,
            "SourceType": "IoT",
            "geoLocation": {},  # optional
            "network": { "latency_ms": random.randint(7,18), "bandwidth_mbps": random.randint(800,1400) },
            "energyContext": { "gridAPI": "unknown", "renewableShare": round(random.uniform(0.28,0.62),2) }
        })
    return out

def make_records(ns_row, ts, interval_s, seq):
    # Namespace basics
    region = ns_row.get("Region","unknown")
    country = ns_row.get("Country","unknown")
    node_id = ns_row["NodeID"]
    site    = slug(region)
    stype   = ns_row.get("SourceType","IoT")

    # Diurnal pattern + CPU
    hour = ts.hour + ts.minute/60
    diurnal = 0.15 * math.sin((hour/24.0) * 2*math.pi)
    base_cpu = 45.0 * (1 + diurnal)
    u = round(clipped_gauss(base_cpu, 12, 0, 100), 2)

    # HERMIS-style CPU model: P_cpu = a*u + b  (simple linear fit)
    a, b = 0.021, 0.45
    p_cpu = round(a*u + b + random.uniform(-0.3, 0.3), 3)  # W

    # Network/Wi-Fi side
    C = float(ns_row["network"]["bandwidth_mbps"])  # channel capacity proxy (Mbps)
    link_load = round(clipped_gauss(0.55, 0.18, 0.0, 1.0), 3)
    C_eff = round(C * clipped_gauss(0.92, 0.04, 0.75, 1.0), 3)  # effective capacity
    thr_pred = round(C_eff * link_load, 3)
    thr_obs  = round(max(1.0, clipped_gauss(thr_pred, max(1.0, thr_pred*0.08), 0.5, C_eff)), 3)

    # Energy per bit (rough synthetic), adjusted for TX state
    ebit = clipped_gauss(2.2e-7, 3.0e-8, 1.2e-7, 3.2e-7)  # J/bit
    ebit_adj = ebit * clipped_gauss(0.95, 0.03, 0.85, 1.05)
    bits = thr_obs * 1e6 / 8 * interval_s  # Mbps -> bytes/s -> seconds
    e_net = round(ebit_adj * bits, 6)  # J over the window

    base_labels = {
        "node_id": node_id, "region": region, "country": country,
        "grid_api": ns_row.get("energyContext",{}).get("gridAPI",""),
        "seq": seq
    }

    def rec(subsystem, metric, value, unit, extra=None, quality="estimated"):
        labels = dict(base_labels)
        if extra: labels.update(extra)
        return {
            "source_type": stype,
            "site": site,
            "node_id": node_id,
            "subsystem": subsystem,
            "metric": metric,
            "ts": iso_z(ts),
            "value": value,
            "unit": unit,
            "labels": labels,
            "interval_ms": int(interval_s*1000),
            "quality": quality
        }

    records = [
        rec("cpu", "utilisation", u, "%"),
        rec("cpu", "power", p_cpu, "W", {"a": a, "b": b, "u_percent": u}),
        rec("wifi", "channel_capacity", C_eff, "Mbps"),
        rec("wifi", "link_load", link_load, "ratio"),
        rec("wifi", "throughput_observed", thr_obs, "Mbps"),
        rec("wifi", "throughput_predicted", thr_pred, "Mbps"),
        rec("wifi", "energy_per_bit_tx_adjusted", round(ebit_adj, 10), "J/bit",
            {"energy_per_bit_raw": round(ebit,10)}),
        rec("wifi", "network_energy", e_net, "J"),
        rec("grid", "renewable_share", ns_row.get("energyContext",{}).get("renewableShare", 0.0), "ratio"),
    ]
    return records

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--namespaces", type=Path, default=Path("gen/namespaces.json"))
    ap.add_argument("--autogen-nodes", type=int, default=0, help="If >0, ignore file and autogenerate N nodes (IoT)")
    ap.add_argument("--out", type=Path, default=Path("gen/synthetic_metrics.ndjson"))
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--freq-mins", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)

    if args.autogen_nodes > 0:
        ns = autogen_nodes(args.autogen_nodes)
    else:
        ns = json.loads(args.namespaces.read_text())

    end   = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(days=args.days)
    step = timedelta(minutes=args.freq_mins)

    seq = 0
    count = 0
    
    # Writing directory in case it doesn't exist.
    base_path = os.path.dirname(args.out)
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)

    with args.out.open("w", encoding="utf-8") as f:
        ts = start
        while ts < end:
            for row in ns:
                for rec in make_records(row, ts, step.total_seconds(), seq):
                    f.write(json.dumps(rec) + "\n")
                    count += 1
                seq += 1
            ts += step
    print(f"Wrote {count} metrics to {args.out} "
          f"({len(ns)} nodes x multiple metrics / every {args.freq_mins} min, from {start} to {end})")

if __name__ == "__main__":
    main()
