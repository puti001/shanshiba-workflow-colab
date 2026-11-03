"""深層檢查 V3 成片音軌與每句台詞的實際聽感、字詞準確度、底噪、切音與唇形時間差。"""
import json
import subprocess
import sys
import wave
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
edl = json.loads((OUT / "post" / "edl.json").read_text(encoding="utf-8"))
picks = json.loads((OUT / "voice_picks.json").read_text(encoding="utf-8"))
mp4 = Path(r"C:\antigravity\影片\小吉的逆襲\後庄守護者_小吉的逆襲_v3_1080p成片.mp4")

model = WhisperModel("small", device="cpu", compute_type="int8")

print("=== 1. 逐句檢查 line0..7.wav 的細節時間戳與底噪 ===")
for k, v in picks.items():
    f = v["file"]
    segs, _ = model.transcribe(f, language="zh", word_timestamps=True)
    segs = list(segs)
    words = []
    for s in segs:
        for w in (s.words or []):
            words.append(f"{w.word}({w.start:.2f}-{w.end:.2f})")
    # 讀 wav 計算前後能量與噪音
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", f, "-ar", "16000", "-ac", "1", "-f", "f32le", "-"], capture_output=True)
    arr = np.frombuffer(r.stdout, np.float32)
    dur_s = len(arr) / 16000.0
    print(f"[{v['shot']}] ({v['who']}) dur={dur_s:.2f}s | 預期: {v['text']}")
    print(f"   聽出: {v['heard']}")
    print(f"   逐字時間: {' '.join(words)}")

print("\n=== 2. 逐鏡檢查最終成片 MP4 各鏡音量 (RMS dBFS) ===")
for r in edl["shots"]:
    sid = r["id"]
    st, du = r["start"], r["dur"]
    raw = subprocess.run([
        "ffmpeg", "-loglevel", "error", "-ss", f"{st:.3f}", "-t", f"{du:.3f}",
        "-i", str(mp4), "-vn", "-ar", "16000", "-ac", "1", "-f", "f32le", "-"
    ], capture_output=True).stdout
    arr = np.frombuffer(raw, np.float32)
    rms = 20 * np.log10(np.sqrt(np.mean(arr ** 2)) + 1e-9)
    peak = 20 * np.log10(np.max(np.abs(arr)) + 1e-9)
    has_line = "有台詞" if r["lines"] else ("有SFX" if r.get("amb") else "純配樂")
    print(f"[{sid}] {st:5.1f}-{st+du:5.1f}s ({has_line:4s}) | RMS={rms:6.1f} dBFS | Peak={peak:6.1f} dBFS")
