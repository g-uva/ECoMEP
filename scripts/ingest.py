#!/usr/bin/env python3
import sys, shutil, pathlib

src, dst = map(lambda p: pathlib.Path(p).resolve(), sys.argv[1:3])

for f in src.rglob("*.csv"):                 # walk sub-folders
    out = dst / f.relative_to(src)           # preserve layout
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, out)

print(f"Copied {sum(1 for _ in dst.rglob('*.csv'))} CSV files to {dst}")
