"""Audit exported artifacts and data separation; optional intelligibility proxy via ASR."""
import argparse
import json
from pathlib import Path
import re

import faiss
import numpy as np
import soundfile as sf
import torch

from run import ROOT, RVC, OUT, EXP, NAME, digest, sources
from make_demo_input import TEXT


def wer(reference, hypothesis):
    words = lambda t: re.findall(r"[a-z]+(?:'[a-z]+)?", t.lower())
    ref, hyp = words(reference), words(hypothesis)
    row = list(range(len(hyp)+1))
    for i, a in enumerate(ref, 1):
        nxt = [i]
        for j, b in enumerate(hyp, 1):
            nxt.append(min(nxt[-1]+1, row[j]+1, row[j-1]+(a != b)))
        row = nxt
    return row[-1]/len(ref)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--asr", action="store_true")
    args = p.parse_args()
    model = OUT / (NAME+".pth")
    trained = torch.load(model, map_location="cpu", weights_only=True)
    base = torch.load(RVC / "assets/pretrained_v2/f0G40k.pth", map_location="cpu", weights_only=True)["model"]
    # Compare in exported fp16 precision so rounding alone cannot count as training.
    names = [k for k in trained["weight"] if k in base]
    changed = [k for k in names if not torch.equal(trained["weight"][k], base[k].half())]
    assert changed and all(torch.isfinite(w).all() for w in trained["weight"].values())
    assert trained["version"] == "v2" and trained["f0"] == 1 and trained["config"][-1] == 40000
    for item in sources():
        a, b = item["intervals_seconds"]["train"], item["intervals_seconds"]["reference"]
        assert a[1] <= b[0] or b[1] <= a[0], "Training/reference overlap"
        assert digest(ROOT / ".locals/voice-model/sources" / item["filename"]) == item["sha256"]
    features = list((EXP / "3_feature768").glob("*.npy"))
    ntotal = sum(np.load(p, allow_pickle=False).shape[0] for p in features)
    idx = faiss.read_index(str(OUT / (NAME+".index")))
    assert idx.ntotal == ntotal and idx.d == 768
    filelist = (EXP / "filelist.txt").read_text().splitlines()
    assert len(filelist) == len(features)
    assert all("reference" not in row for row in filelist)
    audio = {}
    for path in sorted((OUT / "samples").glob("*.wav")):
        data, sr = sf.read(path)
        assert data.size and np.isfinite(data).all()
        rms = float(np.sqrt(np.mean(data**2)))
        assert rms > 1e-5, f"Silent output: {path}"
        audio[path.name] = {"sample_rate":sr, "seconds":len(data)/sr,
            "peak":float(np.max(np.abs(data))), "rms":rms,
            "near_full_scale_ratio":float(np.mean(np.abs(data)>=0.999)), "sha256":digest(path)}
    assert "synthetic_converted.wav" in audio and "social_converted.wav" in audio
    for a, b in [("synthetic_input.wav", "synthetic_converted.wav"), ("social_reference.wav", "social_converted.wav")]:
        assert abs(audio[a]["seconds"] - audio[b]["seconds"]) < 0.15
        assert audio[a]["sha256"] != audio[b]["sha256"]
    result = {"model_info":trained["info"], "model_bytes":model.stat().st_size,
        "compared_tensor_count":len(names), "changed_tensor_count":len(changed),
        "training_segments":len(features), "index_vectors":idx.ntotal,
        "prepared_training_seconds":sum(sf.info(p).duration for p in (EXP/"0_gt_wavs").glob("*.wav")),
        "training_reference_intervals_disjoint":True,
        "evaluation_limit":"Same original recordings, disjoint intervals with 10-second gaps; not independent recording conditions",
        "audio":audio, "subjective_listening_test":"not performed", "vc_client_gui_test":"not performed"}
    if args.asr:
        from faster_whisper import WhisperModel
        asr = WhisperModel("small.en", device="cpu", compute_type="int8", cpu_threads=4)
        result["asr"] = {"engine":"faster-whisper/small.en CPU int8 beam_size=3", "samples":{}}
        for name in ["synthetic_input.wav", "synthetic_converted.wav"]:
            segments, _ = asr.transcribe(str(OUT/"samples"/name), language="en", beam_size=3)
            text = " ".join(s.text.strip() for s in segments)
            result["asr"]["samples"][name] = {"text":text, "wer":wer(TEXT,text)}
        result["asr"]["limitation"] = "ASR checks words only; it does not measure speaker similarity or naturalness"
    (OUT/"validation.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
