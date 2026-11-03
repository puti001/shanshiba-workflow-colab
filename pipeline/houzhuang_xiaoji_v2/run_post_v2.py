import os
import sys
import json
import shutil
import subprocess
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
os.chdir(str(HERE))

# 設定環境變數
os.environ["PY_H3"] = sys.executable
os.environ["PY_VOICE"] = sys.executable
os.environ["UPSCALE"] = "lanczos"
os.environ["ALLOW_REVIEW"] = "1"

OUT = HERE / "out"
POST = OUT / "post"
POST.mkdir(parents=True, exist_ok=True)

# 1. 更新 music_pick.json
music_wav = OUT / "music" / "s77" / "film_77_00001_(Instrumental)_model_bs_roformer_ep_317_sdr_12.wav"
if not music_wav.exists():
    # 嘗試從 v1 複製
    src_wav = REPO / "pipeline" / "houzhuang_xiaoji" / "out" / "music" / "s77" / "film_77_00001_(Instrumental)_model_bs_roformer_ep_317_sdr_12.wav"
    if src_wav.exists():
        music_wav.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_wav, music_wav)

pick_data = {
    "file": str(music_wav.resolve()).replace("\\", "/"),
    "vocal_ratio": 0.7457
}
(POST / "music_pick.json").write_text(json.dumps(pick_data, ensure_ascii=False, indent=1), encoding="utf-8")
print("[v2] music_pick.json updated.")

# 2. 執行 make_film.py 的 edl, ending, cut, review
print("[v2] Running make_film stages: edl ending cut review...")
cmd = [sys.executable, str(HERE / "make_film.py"), "edl", "ending", "cut", "review"]
res = subprocess.run(cmd, cwd=str(HERE))

if res.returncode != 0:
    print(f"[v2] ERROR: make_film failed with code {res.returncode}")
    sys.exit(res.returncode)

# 3. 複製最終 1080p 成品至使用者工作目錄
final_cut = OUT / "cut" / "film_1080p.mp4"
target_dest = Path(r"C:\antigravity\影片\小吉的逆襲\後庄守護者_小吉的逆襲_v2_1080p成片.mp4")

if final_cut.exists():
    shutil.copy2(final_cut, target_dest)
    print(f"[v2] SUCCESS! Copied finished video to: {target_dest}")
else:
    print(f"[v2] Warning: {final_cut} not found!")
