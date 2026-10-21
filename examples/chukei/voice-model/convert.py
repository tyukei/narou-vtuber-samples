"""Offline conversion using the exported RVC model; no microphone or server required."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
RVC = ROOT / ".locals/voice-model/RVC"
OUT = ROOT / "output/voice-model"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--index-rate", type=float, default=0.25)
    parser.add_argument("--pitch", type=int, default=0)
    parser.add_argument("--model", type=Path, default=OUT / "theodore_roosevelt_1912.pth")
    args = parser.parse_args()
    if not 0 <= args.index_rate <= 1:
        parser.error("--index-rate must be between 0 and 1")
    model = args.model.resolve()
    env = dict(os.environ, PYTHONPATH=str(RVC), OMP_NUM_THREADS="4", OPENBLAS_NUM_THREADS="4",
               RVC_CUDA_GRAPH="0", weight_root=str(model.parent),
               rmvpe_root=str(RVC / "assets/rmvpe"))
    started = time.perf_counter()
    subprocess.run([sys.executable, "-m", "infer.cli", "--model", str(model),
        "--input", str(args.input.resolve()), "--output", str(args.output.resolve()),
        "--speaker-id", "0", "--pitch", str(args.pitch), "--f0-method", "rmvpe",
        "--index", str(OUT / "theodore_roosevelt_1912.index"),
        "--index-rate", str(args.index_rate), "--protect", "0.33", "--rms-mix-rate", "1"],
        cwd=RVC, env=env, check=True)
    print(f"Elapsed including model load: {time.perf_counter()-started:.3f} seconds")
