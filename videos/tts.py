"""Voice-over with Kokoro-82M (Apache-2.0) through kokoro-onnx, run locally on the CPU.

Install: .venv/bin/pip install kokoro-onnx soundfile
Model files go in videos/_final_build/kokoro/ (gitignored), from
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0:
kokoro-v1.0.onnx and voices-v1.0.bin.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import soundfile as sf

MODEL_DIR = Path(__file__).resolve().parent / "_final_build" / "kokoro"


@lru_cache(maxsize=1)
def _engine():
    from kokoro_onnx import Kokoro
    return Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))


def synth(text: str, path: str, voice: str = "am_michael", speed: float = 1.0) -> None:
    samples, sr = _engine().create(text, voice=voice, speed=speed, lang="en-us")
    sf.write(path, samples, sr)
