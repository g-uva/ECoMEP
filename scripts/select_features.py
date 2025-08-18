#!/usr/bin/env python3
import sys, json, pathlib, yaml, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    feats_path = ROOT / "data" / "features" / "train.parquet"
    aliases_path = ROOT / "schema" / "aliases.yaml"
    params_path = ROOT / "params.yaml"
    report_path = ROOT / "reports" / "schema_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(feats_path)
    with open(aliases_path) as f: aliases = yaml.safe_load(f) or {}
    with open(params_path) as f: params = yaml.safe_load(f) or {}

    required = params.get("schema", {}).get("required", [])
    ranges = params.get("schema", {}).get("ranges", {})

    # Build canonical map
    canonical_map = {}
    for canon, candidates in (aliases.get("aliases", {}) or {}).items():
        for cand in candidates:
            if cand in df.columns:
                canonical_map[cand] = canon
                break

    # Apply alias renames (non-destructive for columns already canonical)
    for cand, canon in list(canonical_map.items()):
        if canon not in df.columns:
            df = df.rename(columns={cand: canon})

    present = list(df.columns)
    missing = [c for c in required if c not in present]
    dtype_issues = [c for c in required if c in df.columns and not pd.api.types.is_numeric_dtype(df[c])]
    range_issues = []
    for c, rr in ranges.items():
        if c in df.columns:
            lo, hi = rr.get("min", None), rr.get("max", None)
            if lo is not None and df[c].min() < lo: range_issues.append({"column": c, "issue": "below_min"})
            if hi is not None and df[c].max() > hi: range_issues.append({"column": c, "issue": "above_max"})

    ok = (not missing) and (not dtype_issues) and (not range_issues)
    report = {
        "ok": ok,
        "missing": missing,
        "dtype_issues": dtype_issues,
        "range_issues": range_issues,
        "applied_aliases": canonical_map,
        "schema_version": params.get("schema", {}).get("version", "unknown")
    }
    with open(report_path, "w") as f: json.dump(report, f, indent=2)

    if not ok:
        print(json.dumps(report, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
