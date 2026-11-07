import json, subprocess, sys, numpy as np
from pathlib import Path
import whisper

sys.stdout.reconfigure(encoding="utf-8")
hd = Path(r"C:\antigravity\影片\shanshiba-workflow-colab\pipeline\puti_xinqi\out\voice\h3")
picks = json.loads((hd.parent.parent / "voice_picks.json").read_text(encoding="utf-8"))
m = whisper.load_model("base")

for k, v in picks.items():
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", v["file"], "-ar", "48000", "-ac", "1", "-f", "f32le", "-"], capture_output=True)
    x = np.frombuffer(r.stdout, np.float32)
    spec = np.abs(np.fft.rfft(x))
    freqs = np.fft.rfftfreq(len(x), 1/48000)
    hi = spec[freqs > 3500].sum() / (spec.sum() + 1e-9) * 100
    vhi = spec[freqs > 7000].sum() / (spec.sum() + 1e-9) * 100
    asr = m.transcribe(v["file"], language="zh")["text"].strip()
    print(f"{v['shot']} ({v['who']:6s}, src={v['source']:3s}): >3.5k={hi:4.1f}% >7k={vhi:4.1f}% | 字幕={v['text']} | 實聽={asr}")
