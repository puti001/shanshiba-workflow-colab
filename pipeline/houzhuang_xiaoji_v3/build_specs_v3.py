"""根據 V3 film.json 建立 14 個鏡頭的 spec.json，並用 h3_shot.py --dry-run 產生與驗證 prompt.txt，
同時準備 out/post/amb.json 音效映射表。"""
import json
import os
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
            seed=int(cfg["seeds"].get(f"h3_{sid}", h.get("default_seed", 31415))),
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

    # 2. 建立加長到 10 秒（避免被較長鏡頭裁切）的音效檔並寫入 out/post/amb.json
    sfx_dir = OUT / "sfx"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    amb_map = {}
    for sid in ("S04", "S06", "S08", "S09", "S11", "S13"):
        src_sfx = sfx_dir / f"{sid}.wav"
        pad_sfx = sfx_dir / f"{sid}_10s.wav"
        if src_sfx.exists():
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(src_sfx),
                "-af", "apad=whole_dur=10.0", "-ar", str(SR), "-ac", "1", str(pad_sfx)
            ], check=True)
            amb_map[sid] = str(pad_sfx.resolve()).replace("\\", "/")

    # 也把變形與結尾音效從 sfx_library 補進 S07, S14
    lib_dir = Path(r"c:\antigravity\影片\小吉與大黑\sfx_library")
    extra_sfx = {
        "S07": lib_dir / "s07_mech_transform.wav",
        "S14": lib_dir / "s14_grand_finale.wav",
    }
    for sid, spath in extra_sfx.items():
        if spath.exists():
            pad_sfx = sfx_dir / f"{sid}_10s.wav"
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(spath),
                "-af", "apad=whole_dur=10.0", "-ar", str(SR), "-ac", "1", str(pad_sfx)
            ], check=True)
            amb_map[sid] = str(pad_sfx.resolve()).replace("\\", "/")

    (OUT / "post").mkdir(parents=True, exist_ok=True)
    (OUT / "post" / "amb.json").write_text(json.dumps(amb_map, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[amb.json] 已寫入音效軌:", list(amb_map.keys()))


if __name__ == "__main__":
    main()
