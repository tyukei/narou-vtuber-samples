"""Create an explicitly synthetic, original test utterance with local eSpeak NG."""
import ctypes
import ctypes.util
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parents[3]
TEXT = ("This is a synthetic voice conversion demonstration. "
        "The historical speaker did not say these words. "
        "We are testing a model trained from public domain recordings.")

if __name__ == "__main__":
    name = ctypes.util.find_library("espeak-ng")
    if not name:
        raise RuntimeError("Install libespeak-ng1 (Debian/Ubuntu) to generate this optional test input")
    lib = ctypes.CDLL(name)
    lib.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    sr = lib.espeak_Initialize(2, 0, None, 0)
    if sr <= 0:
        raise RuntimeError("eSpeak NG initialization failed")
    chunks = []
    callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)

    @callback_type
    def callback(wav, n, events):
        if n:
            chunks.append(ctypes.string_at(wav, n * 2))
        return 0

    lib.espeak_SetSynthCallback(callback)
    if lib.espeak_SetVoiceByName(b"en-us") != 0:
        raise RuntimeError("eSpeak en-us voice unavailable")
    lib.espeak_SetParameter(1, 145, 0)
    data = TEXT.encode()
    lib.espeak_Synth.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint,
                               ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
                               ctypes.c_void_p, ctypes.c_void_p]
    if lib.espeak_Synth(data, len(data)+1, 0, 1, 0, 1, None, None) != 0:
        raise RuntimeError("eSpeak synthesis failed")
    lib.espeak_Synchronize()
    target = ROOT / "output/voice-model/samples/synthetic_input.wav"
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(b"".join(chunks))
    target.with_suffix(".txt").write_text(TEXT + "\nGenerated locally with eSpeak NG (en-us, 145 words/minute). No human recording used.\n")
    print(target)
