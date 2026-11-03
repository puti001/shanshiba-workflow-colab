import json
import os
import re
import sys
import subprocess
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(r"c:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji")
CFG = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
OUT = HERE / "out"
hd = OUT / "voice" / "h3"
hd.mkdir(parents=True, exist_ok=True)

picks = json.loads((OUT / "voice_picks.json").read_text(encoding="utf-8")) if (OUT / "voice_picks.json").exists() else {}

try:
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8")
except Exception as e:
    print("Could not load WhisperModel:", e)
    model = None

lines_cfg = [(s["id"], s["line"]) for s in CFG["shots"] if s.get("line")]

for i, (sid, ln) in enumerate(lines_cfg):
    clip = OUT / "h3" / sid / "clip.mp4"
    if not clip.exists():
        continue
    wav = hd / f"{sid}_mix.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    
    heard = ""
    st = float(ln.get("at", 0.5))
    en = st + 2.0
    
    if model:
        try:
            segments, info = model.transcribe(str(wav), language="zh")
            segs = list(segments)
            heard = "".join(s.text for s in segs).strip()
            if segs:
                st = max(0.0, segs[0].start - 0.05)
                en = segs[-1].end + 0.15
        except Exception as err:
            print(f"Error transcribing {sid}: {err}")
            
    print(f"{sid}: expected [{ln['text']}], heard [{heard}], window: {st:.2f}-{en:.2f}s")
    
    line_wav = hd / f"line{i}.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ss", f"{st:.3f}", "-to", f"{en:.3f}", "-ar", "48000", str(line_wav)], check=True)
    
    picks[str(i)] = dict(
        shot=sid,
        who=ln["who"],
        text=ln["text"],
        file=str(line_wav),
        heard=heard,
        at=round(st, 3),
        end=round(en, 3),
        source="h3"
    )

(OUT / "voice_picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
print("voice_picks.json successfully updated!")
