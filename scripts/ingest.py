#!/usr/bin/env python3
"""
Tiny placeholder that just copies the raw CSV/Parquet files
into the clean/ directory so the next stage has something to read.
"""

import shutil, sys, pathlib

src = pathlib.Path(sys.argv[1])      # e.g. data/raw
dst = pathlib.Path(sys.argv[2])      # e.g. data/clean
dst.mkdir(parents=True, exist_ok=True)

for f in src.glob("*.*"):            # copy everything for now
    shutil.copy2(f, dst / f.name)
print(f"Copied {len(list(dst.iterdir()))} files to {dst}")
