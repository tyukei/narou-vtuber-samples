"""Reproduce the historical-voice experiment. Run with the dedicated venv Python."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / ".locals/voice-model"
RVC = WORK / "RVC"
OUT = ROOT / "output/voice-model"
NAME = "theodore_roosevelt_1912"
EXP = RVC / "logs" / NAME
REV = "81eed5e8f68b6bed1789f682fe78cdd324495afc"
ASSET_REV = "e6d0c1a17da07c33557852f9dfa2bd44cc75737d"
ENV = dict(os.environ, PYTHONPATH=str(RVC), OMP_NUM_THREADS="4",
           OPENBLAS_NUM_THREADS="4", RVC_CUDA_GRAPH="0", HF_HUB_DISABLE_XET="1")


def run(args, cwd=RVC):
    print("Running:", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, env=ENV, check=True)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sources():
    return json.loads(Path(__file__).with_name("sources.json").read_text())


def download():
    from huggingface_hub import hf_hub_download
    WORK.mkdir(parents=True, exist_ok=True)
    if not RVC.exists():
        run(["git", "clone", "https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI.git", RVC], ROOT)
        run(["git", "checkout", "--detach", REV])
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=RVC, text=True).strip()
    if actual != REV:
        raise RuntimeError(f"Expected upstream {REV}, found {actual}; use a separate checkout")
    for item in sources():
        path = WORK / "sources" / item["filename"]
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            run(["curl", "-fL", "--retry", "2", item["download_url"], "-o", path], ROOT)
        if digest(path) != item["sha256"]:
            raise RuntimeError(f"Source checksum mismatch: {path}")
    files = ["hubert_base/config.json", "hubert_base/preprocessor_config.json",
             "hubert_base/pytorch_model.bin", "pretrained_v2/f0G40k.pth",
             "pretrained_v2/f0D40k.pth", "rmvpe.pt"]
    for name in files:
        p = hf_hub_download("lj1995/VoiceConversionWebUI", name,
                            revision=ASSET_REV, local_dir=RVC / "assets")
        if name == "rmvpe.pt":
            target = RVC / "assets/rmvpe/rmvpe.pt"
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(p, target)


def prepare():
    import soundfile as sf
    OUT.mkdir(parents=True, exist_ok=True)
    EXP.mkdir(parents=True, exist_ok=True)
    train = WORK / "dataset/train"
    train.mkdir(parents=True, exist_ok=True)
    evaluation = OUT / "samples"
    evaluation.mkdir(exist_ok=True)
    rows = []
    for item in sources():
        source = WORK / "sources" / item["filename"]
        if digest(source) != item["sha256"]:
            raise RuntimeError(f"Checksum mismatch: {source}")
        for split, interval in item["intervals_seconds"].items():
            start, end = interval
            target = (train if split == "train" else evaluation) / f"{item['id']}_{split}.wav"
            # No neural enhancement: retain source timbre and use conservative DSP.
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                 "-ss", start, "-i", source, "-t", end-start, "-ac", "1", "-ar", "40000",
                 "-af", "highpass=f=80,lowpass=f=5500,afftdn=nf=-25,alimiter=limit=0.95:level=false",
                 "-c:a", "pcm_s16le", target])
            rows.append({"source":item["id"], "split":split, "start":start,
                         "end":end, "seconds":sf.info(target).duration,
                         "path":str(target.relative_to(ROOT)), "sha256":digest(target)})
    (OUT / "dataset.json").write_text(json.dumps(rows, indent=2)+"\n")
    run([sys.executable, "-m", "train.preprocess", train, "40000", "2", EXP, "True", "3.7"])
    config = json.loads((RVC / "configs/v1/40k.json").read_text())
    config["train"]["log_interval"] = 50
    (EXP / "config.json").write_text(json.dumps(config, indent=2)+"\n")
    (RVC / "assets/weights").mkdir(exist_ok=True)


def features():
    import numpy as np
    run([sys.executable, "-m", "train.dataset.extract_f0", "cuda", "1", "0", "0", EXP, "True"])
    run([sys.executable, "-m", "train.dataset.extract_hubert_feature", "cuda", "1", "0", "0", EXP, "v2", "True"])
    lines = []
    wavs = sorted((EXP / "0_gt_wavs").glob("*.wav"))
    if not wavs:
        raise RuntimeError("No training segments")
    for wav in wavs:
        paths = [wav, EXP / "3_feature768" / (wav.stem+".npy"),
                 EXP / "2a_f0" / (wav.name+".npy"), EXP / "2b-f0nsf" / (wav.name+".npy")]
        for p in paths[1:]:
            x = np.load(p, allow_pickle=False)
            if not x.size or not np.isfinite(x).all():
                raise RuntimeError(f"Invalid features: {p}")
        lines.append("|".join(map(str, paths))+"|0")
    (EXP / "filelist.txt").write_text("\n".join(lines)+"\n")
    run([sys.executable, "-m", "train.train_index", NAME, "v2", RVC / "assets/indices", "4", "single"])
    print(f"Verified {len(lines)} training segments", flush=True)


def train(epochs, batch):
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    run([sys.executable, "-m", "train.train", "-e", NAME, "-sr", "40k", "-f0", "1",
         "-bs", batch, "-g", "0", "-te", epochs, "-se", "10", "-pg", "assets/pretrained_v2/f0G40k.pth",
         "-pd", "assets/pretrained_v2/f0D40k.pth", "-l", "1", "-c", "0", "-sw", "1", "-v", "v2"])
    (OUT / "training_run.json").write_text(json.dumps({"started_unix":started,
        "ended_unix":time.time(), "elapsed_seconds":time.time()-started,
        "total_epochs":epochs, "batch_size":batch, "rvc_revision":REV,
        "assets_revision":ASSET_REV}, indent=2)+"\n")


def export():
    import numpy as np
    import torch
    OUT.mkdir(parents=True, exist_ok=True)
    model = RVC / "assets/weights" / (NAME+".pth")
    checkpoint = torch.load(model, map_location="cpu", weights_only=True)
    assert checkpoint["version"] == "v2" and checkpoint["f0"] == 1
    assert checkpoint["config"][-1] == 40000
    assert all(torch.isfinite(w).all() for w in checkpoint["weight"].values())
    shutil.copy2(model, OUT / model.name)
    indices = list(EXP.glob("added_*.index"))
    if len(indices) != 1:
        raise RuntimeError(f"Expected one index, got {indices}")
    shutil.copy2(indices[0], OUT / (NAME+".index"))
    shutil.copy2(EXP / "config.json", OUT / "training_config.json")
    shutil.copy2(EXP / "train.log", OUT / "training.log")
    (OUT / "SHA256SUMS").write_text("".join(f"{digest(p)}  {p.name}\n" for p in sorted(OUT.iterdir()) if p.suffix in {".pth", ".index"}))
    print("Exported", checkpoint["info"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["download", "prepare", "features", "train", "export"])
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=6)
    args = parser.parse_args()
    if args.stage == "train":
        train(args.epochs, args.batch)
    else:
        globals()[args.stage]()
