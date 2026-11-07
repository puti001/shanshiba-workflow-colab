"""根據 V3 film.json 建立 14 個鏡頭的 spec.json，並用 h3_shot.py --dry-run 產生與驗證 prompt.txt，
同時自動合成古琴／磬鐘／金光粒子音效並準備 out/post/amb.json 音效映射表。"""
import json
import math
import os
import struct
import subprocess
import sys
import wave
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
SR, FPS = 48000, 24


def frames_for(d):
    n = 0
    while 17 * n + 5 < d * FPS:
        n += 1
    return 17 * n + 5


def synth_sfx_wav(path: Path, freqs, dur=10.0, shimmer=True):
    """合成溫暖鐘磬／金光流轉／古琴泛音環境音效 (48kHz mono)"""
    n_samples = int(dur * SR)
    buf = bytearray()
    for i in range(n_samples):
        t = i / SR
        val = 0.0
        for idx, f in enumerate(freqs):
            onset = idx * 0.35
            if t >= onset:
                dt = t - onset
                env = math.exp(-dt * (0.65 + 0.12 * idx)) * (1.0 - math.exp(-dt * 25.0))
                val += 0.22 * env * math.sin(2 * math.pi * f * dt)
                val += 0.08 * env * math.sin(2 * math.pi * (f * 2.0) * dt)
        if shimmer:
            # 高頻金光粒子泛音
            sh_env = math.exp(-t * 0.35) * (0.5 + 0.5 * math.sin(2 * math.pi * 3.2 * t))
            val += 0.05 * sh_env * math.sin(2 * math.pi * 1760.0 * t + 1.5 * math.sin(2 * math.pi * 7.0 * t))
        s = max(-0.92, min(0.92, val))
        buf.extend(struct.pack("<h", int(s * 32767)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(buf))


def main():
    # 1. 先執行 build_film_v3.py 確保 film.json 最新
    subprocess.run([sys.executable, str(HERE / "build_film_v3.py")], check=True)
    cfg = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
    h = cfg["h3"]
    chars = cfg["chars"]
    shots = cfg["shots"]

    for s in shots:
        sid = s["id"]
        od = OUT / "h3" / sid
        od.mkdir(parents=True, exist_ok=True)
        secs = frames_for(s["dur"]) / FPS
        dlg = []
        if s.get("line"):
            ln = s["line"]
            dlg = [dict(
                subject=ln["who"],
                line=ln["text"],
                lang="Chinese",
                after="Right after the line the speaker's lips close and stay closed."
            )]

        sp = dict(
            duration=round(secs - 0.02, 3),
            size=[1344, 768],
            seed=int(cfg.get("seeds", {}).get(f"h3_{sid}", h.get("default_seed", 31415))),
            steps=int(h.get("steps", 14)),
            draft=bool(h.get("draft", False)),
            style=h["style"],
            setting=h["setting"],
            first_frame=os.path.relpath(OUT / "first" / f"{sid}.png", od).replace("\\", "/"),
            subjects=[dict(key=k, desc=chars[k]["look"], voice=chars[k]["h3_voice"]) for k in s["refs"]],
            shots=[dict(camera=s.get("camera", h["camera"]), action=s["action"], dialogue=dlg)],
            constraints=h["constraints"] + s.get("extra_constraints", []),
            soundscape=h["soundscape"],
            music="N/A",
        )
        if s.get("use_last"):
            lp = OUT / "last" / f"{sid}.png"
            assert lp.exists(), f"Missing last frame: {lp}"
            sp["last_frame"] = os.path.relpath(lp, od).replace("\\", "/")

        if s.get("line"):
            ln = s["line"]
            ref_wav = OUT / "voice" / f"ref_{ln['who']}.wav"
            assert ref_wav.exists(), f"Missing voice ref: {ref_wav}"
            sp["audio"] = {
                "voice_ref": {
                    "subject": ln["who"],
                    "file": os.path.relpath(ref_wav, od).replace("\\", "/")
                }
            }
        else:
            # 無台詞鏡頭給靜音 guide.wav 防止角色亂動嘴
            g_wav = od / "guide.wav"
            buf = bytes(int(secs * SR) * 2)
            with wave.open(str(g_wav), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SR)
                w.writeframes(buf)
            sp["audio"] = {"fixed": {"file": "guide.wav"}}

        spec_path = od / "spec.json"
        spec_path.write_text(json.dumps(sp, ensure_ascii=False, indent=1), encoding="utf-8")

        # 用 h3_shot.py --dry-run 產生並檢查官方格式 prompt.txt
        r = subprocess.run(
            [sys.executable, str(REPO / "tools" / "h3_shot.py"), str(spec_path), "--out", str(od), "--dry-run"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        print(f"[{sid}] dry-run:", r.stdout.strip())
        if r.returncode != 0:
            print(r.stderr)
            sys.exit(f"h3_shot.py --dry-run failed on {sid}")

    # 2. 建立加長到 10 秒的古琴／鐘磬／金光音效檔並寫入 out/post/amb.json
    sfx_dir = OUT / "sfx"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    sfx_presets = {
        "S02": ([523.25, 659.25, 783.99, 1046.50], True),   # 佛陀躍出展台金光琶音
        "S04": ([261.63, 392.00, 523.25], False),           # 釋迦出山沉思古鐘共鳴
        "S06": ([329.63, 440.00, 659.25], True),            # 造像碑底座微光點亮
        "S07": ([293.66, 440.00, 587.33, 880.00], True),    # 千年供養人祈福金影浮現
        "S08": ([349.23, 523.25, 698.46], False),           # 泥塑與鐵佛溫暖共鳴
        "S10": ([1046.50, 783.99, 659.25, 523.25], True),   # 佛陀化作金光歸位展座
        "S13": ([261.63, 329.63, 392.00, 523.25], True),    # 金蓮飄落一念菩提心起
        "S14": ([523.25, 659.25, 783.99, 1046.50, 1318.5], True),  # 壓軸歡喜大合照
    }
    amb_map = {}
    for sid, (freqs, shim) in sfx_presets.items():
        pad_sfx = sfx_dir / f"{sid}_10s.wav"
        synth_sfx_wav(pad_sfx, freqs, dur=10.0, shimmer=shim)
        amb_map[sid] = str(pad_sfx.resolve()).replace("\\", "/")

    (OUT / "post").mkdir(parents=True, exist_ok=True)
    (OUT / "post" / "amb.json").write_text(json.dumps(amb_map, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[amb.json] 已寫入音效軌:", list(amb_map.keys()))


if __name__ == "__main__":
    main()
