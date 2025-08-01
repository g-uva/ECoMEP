#!/usr/bin/env python3
"""
Writes a 1-byte ONNX file – just enough for DVC to hash.
Later replace with your real PyTorch/TensorFlow training script.
"""

import sys, pathlib

src = pathlib.Path(sys.argv[1])      # data/features
model_path = pathlib.Path(sys.argv[2])  # models/lstm.onnx
model_path.parent.mkdir(parents=True, exist_ok=True)

# fake model artefact
model_path.write_bytes(b"\0")
print(f"Wrote placeholder model to {model_path}")
