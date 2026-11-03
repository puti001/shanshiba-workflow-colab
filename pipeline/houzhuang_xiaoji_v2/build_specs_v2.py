import json
import os
import subprocess
import wave
import numpy as np
from pathlib import Path

HERE = Path(r"C:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji_v2")
CFG = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
OUT = HERE / "out"
FPS, SR = 24, 48000

def frames_for(d):
    n = 0
    while 17 * n + 5 < d * FPS:
        n += 1
    return 17 * n + 5

CHARS = CFG["chars"]
H = CFG["h3"]
voice_fixed_dir = OUT / "voice" / "fixed"
sfx_src = Path(r"c:\antigravity\影片\小吉與大黑\sfx_library")

sfx_map = {
    "S04": sfx_src / "s04_lightning_strike.wav",
    "S08": sfx_src / "s08_metal_hit.wav",
    "S09": sfx_src / "s09_heavy_punch_knockback.wav",
    "S14_sfx": sfx_src / "s14_grand_finale.wav"
}

picks = {}

for i, s in enumerate(CFG["shots"]):
    od = OUT / "h3" / s["id"]
    od.mkdir(parents=True, exist_ok=True)
    
    sid = s["id"]
    first_p = OUT / "first" / f"{sid}.png"
    last_p = OUT / "last" / f"{sid}.png"
    fixed_audio_p = od / "audio_guide.wav"
    
    ln = s.get("line")
    dlg = []
    
    if ln:
        src_wav = voice_fixed_dir / f"{sid}.wav"
        # load wav and pad
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src_wav)], capture_output=True, text=True)
        v_dur = float(r.stdout.strip())
        
        at = float(ln.get("at", 0.4))
        tot_dur = max(float(s["dur"]), at + v_dur + 0.8)
        secs = frames_for(tot_dur) / FPS
        
        # Build padded 48kHz mono wav
        buf = bytearray(int(secs * SR) * 2)
        pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src_wav), "-ar", str(SR), "-ac", "1", "-f", "s16le", "-"], capture_output=True).stdout
        st = int(at * SR) * 2
        seg = pcm[: len(buf) - st]
        buf[st: st + len(seg)] = seg
        
        with wave.open(str(fixed_audio_p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(bytes(buf))
            
        dlg = [dict(subject=ln["who"], line=ln["text"], lang="Chinese", after="Right after the line the speaker's lips close and stay closed.")]
        spec_audio = {"fixed": {"file": str(fixed_audio_p)}}
        
        picks[str(len(picks))] = dict(
            shot=sid, who=ln["who"], text=ln["text"], file=str(fixed_audio_p),
            at=at, dur=v_dur, source="fixed"
        )
    else:
        tot_dur = float(s["dur"])
        secs = frames_for(tot_dur) / FPS
        buf = bytearray(int(secs * SR) * 2)
        
        if sid in sfx_map and sfx_map[sid].exists():
            pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(sfx_map[sid]), "-ar", str(SR), "-ac", "1", "-f", "s16le", "-"], capture_output=True).stdout
            st = int(0.3 * SR) * 2
            seg = pcm[: len(buf) - st]
            buf[st: st + len(seg)] = seg
            
        with wave.open(str(fixed_audio_p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(bytes(buf))
        spec_audio = {"fixed": {"file": str(fixed_audio_p)}}

    seed = int(CFG.get("seeds", {}).get("h3_" + sid, H.get("default_seed", 20261007)))
    
    spec = dict(
        duration=round(secs - 0.02, 3),
        size=[1344, 768],
        seed=seed,
        steps=14,
        draft=True,
        style=H["style"],
        setting=H["setting"],
        first_frame=str(first_p),
        last_frame=str(last_p),
        subjects=[dict(key=k, desc=CHARS[k]["look"], voice=CHARS[k]["h3_voice"]) for k in s["refs"]],
        shots=[dict(camera=s.get("camera", H.get("camera", "The camera holds a static shot on a tripod.")), action=s["action"], dialogue=dlg)],
        constraints=H.get("constraints", []) + s.get("extra_constraints", []),
        soundscape=H["soundscape"],
        music="N/A",
        audio=spec_audio
    )
    
    (od / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{sid}] spec.json built (dur={spec['duration']}s, has_dialogue={bool(ln)})")

(OUT / "voice_picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
print("All 14 v2 specs and voice_picks built successfully!")
