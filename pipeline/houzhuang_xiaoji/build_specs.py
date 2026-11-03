import json
import os
import re
import wave
from pathlib import Path

HERE = Path(r"c:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji")
CFG = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
OUT = HERE / "out"
FPS, SR = 24, 48000

def frames_for(d):
    n = 0
    while 17 * n + 5 < d * FPS:
        n += 1
    return 17 * n + 5

def est_line_secs(ln):
    return max(1.2, len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", ln["text"])) / 4.0)

CHARS = CFG["chars"]
H = CFG["h3"]

for s in CFG["shots"]:
    od = OUT / "h3" / s["id"]
    od.mkdir(parents=True, exist_ok=True)
    
    # Remove old clip
    old_clip = od / "clip.mp4"
    if old_clip.exists():
        old_clip.unlink()
    
    d = s["dur"]
    ln = s.get("line")
    dlg = []
    if ln:
        d = max(d, ln.get("at", 0.5) + est_line_secs(ln) + 1.2)
        dlg = [dict(subject=ln["who"], line=ln["text"], lang="Chinese", after="Right after the line the speaker's lips close and stay closed.")]
    secs = frames_for(d) / FPS
    
    seed = int(CFG.get("seeds", {}).get("h3_" + s["id"], H.get("default_seed", 20261007)))
    first_p = OUT / "first" / f"{s['id']}.png"
    last_p = OUT / "last" / f"{s['id']}.png"
    
    spec = dict(
        duration=round(secs - 0.02, 3),
        size=[1344, 768],
        seed=seed,
        steps=14,
        draft=True,
        style=H["style"],
        setting=H["setting"],
        first_frame=str(first_p),
        subjects=[dict(key=k, desc=CHARS[k]["look"], voice=CHARS[k]["h3_voice"]) for k in s["refs"]],
        shots=[dict(camera=s.get("camera", H.get("camera", "The camera holds a static shot on a tripod.")), action=s["action"], dialogue=dlg)],
        constraints=H.get("constraints", []) + s.get("extra_constraints", []),
        soundscape=H["soundscape"],
        music="N/A"
    )
    if last_p.exists():
        spec["last_frame"] = str(last_p)
    
    if ln:
        spec["audio"] = {"voice_ref": {"subject": ln["who"], "file": str(OUT / "voice" / f"ref_{ln['who']}.wav")}}
    else:
        buf = bytearray(int(secs * SR) * 2)
        guide_p = od / "guide.wav"
        with wave.open(str(guide_p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(bytes(buf))
        spec["audio"] = {"fixed": {"file": str(guide_p)}}
    
    (od / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{s['id']}: spec.json generated (duration={spec['duration']}s, has_last={bool(spec.get('last_frame'))}, audio={list(spec['audio'].keys())[0]})")

print("All 14 spec.json files built successfully!")
