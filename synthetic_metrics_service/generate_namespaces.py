import os
import argparse, json, random, re
from pathlib import Path

SEEDS = [
    # (Country, Region, gridAPI, lat, lon, latency_ms, bandwidth_mbps, renewableShare)
    ("Netherlands", "North Netherlands", "TenneT", 53.2194, 6.5665, 10, 1000, 0.45),
    ("Netherlands", "Randstad",         "TenneT", 52.3702, 4.8952,  8, 1200, 0.52),
    ("Italy",       "Lombardy",          "Terna", 45.4668, 9.1905, 15,  900, 0.38),
    ("Italy",       "Tuscany",           "Terna", 43.7696,11.2558, 18,  850, 0.41),
    ("Hungary",     "Budapest",          "MAVIR", 47.4979,19.0402, 12,  950, 0.29),
    ("Hungary",     "Transdanubia",      "MAVIR", 46.2530,18.2331, 14,  800, 0.31),
    ("Spain",       "Madrid",              "REE", 40.4168,-3.7038, 11, 1100, 0.54),
    ("Spain",       "Catalonia",           "REE", 41.3851, 2.1734, 13, 1050, 0.57),
    ("France",      "Île-de-France",        "RTE", 48.8566, 2.3522,  9, 1300, 0.36),
    ("Germany",     "Berlin-Brandenburg","50Hertz",52.5200,13.4050, 7, 1400, 0.60),
]

TYPE_ABBR = {"IoT":"EDGE", "Network":"NET", "Cloud":"CLD", "Grid":"GRID"}

def slug(s): return re.sub(r'[^a-z0-9]+','-', s.lower()).strip('-')

def make_node_id(cc, region_code, stype, index):
    return f"{cc}-{region_code}-{TYPE_ABBR.get(stype,'EDGE')}{index:02d}"

def country_code(country):
    return {
        "Netherlands":"NL", "Italy":"IT", "Hungary":"HU",
        "Spain":"ES", "France":"FR", "Germany":"DE"
    }.get(country, country[:2].upper())

def region_code(region):
    up = re.sub(r'[^A-Z0-9]+','', region.upper())
    return (up[:4] or "REGN")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12, help="How many nodes")
    ap.add_argument("--outfile", type=Path, default=Path("gen/namespaces.json"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--types", default="IoT,Network,Cloud,Grid",
                    help="Comma-separated SourceTypes to sample from")
    args = ap.parse_args()
    random.seed(args.seed)

    types = [t.strip() for t in args.types.split(",") if t.strip()]
    data = []
    counters = {t:1 for t in types}

    for i in range(args.n):
        country, region, gridAPI, lat, lon, lat_ms, bw_mbps, ren = random.choice(SEEDS)
        stype = random.choice(types)
        cc = country_code(country)
        rc = region_code(region)
        node_id = make_node_id(cc, rc, stype, counters[stype]); counters[stype]+=1

        site_code = f"{cc}-{rc}".upper()
        entry = {
            "SourceType": stype,                 # Cloud | Network | Grid | IoT
            "Site": f"{region}, {country}",
            "SiteCode": site_code,               # used in MQTT topic
            "Country": country,
            "Region": region,
            "NodeID": node_id,
            "geoLocation": {"lat": lat, "lon": lon},
            "subsystems": ["cpu","wifi"],        # minimal set aligned with HERMIS
            "network": {"latency_ms": lat_ms, "bandwidth_mbps": bw_mbps},
            "energyContext": {"gridAPI": gridAPI, "renewableShare": ren}
        }
        data.append(entry)

    # Writing directory in case it doesn't exist.
    base_path = os.path.dirname(args.outfile)
    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)
            
    args.outfile.write_text(json.dumps(data, indent=2))
    print(f"Wrote {len(data)} nodes to {args.outfile}")

if __name__ == "__main__":
    main()
