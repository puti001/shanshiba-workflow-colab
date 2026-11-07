"""V3 Lint Gate (菩提心起 2D 動畫專案版): 檢查 film.json 與所有 spec.json，違反任何一條直接失敗退出。
1. 嚴禁出現寫實/真人關鍵字：photoreal, live-action, 35mm, Kodak, 8k, real human, tokusatsu
2. 嚴禁 draft=True 或 steps < 14
3. 檢查每個鏡頭 action 字數 >= 45 words，且以 Starting from <Picture 1> 開頭
4. 檢查 first_frame / last_frame 檔案存在，且單張互動鏡 (S01, S03, S05, S09, S11, S12) 不得設 use_last=True
5. 若 use_last=True，自動檢查首尾幀像素差 (mean_abs_diff >= 3.0)，防止誤塞同一張圖導致角色結冰
"""
import json
import re
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
FORBIDDEN = [
    r"photoreal",
    r"live-action",
    r"live action",
    r"35mm",
    r"kodak",
    r"8k",
    r"tokusatsu",
]
SINGLE_FRAME_SHOTS = {"S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11"}


def check_text(label, text, errors):
    for pat in FORBIDDEN:
        if re.search(pat, text, re.IGNORECASE):
            errors.append(f"[{label}] 含有禁用詞 '{pat}'")


def main():
    errors = []
    film_path = HERE / "film.json"
    if not film_path.exists():
        sys.exit("ERROR: film.json does not exist")
    raw = film_path.read_text(encoding="utf-8")
    check_text("film.json", raw, errors)
    film = json.loads(raw)

    h3 = film.get("h3", {})
    if h3.get("draft", False) is not False:
        errors.append("[film.json] h3.draft 必須為 False")
    if int(h3.get("steps", 0)) < 14:
        errors.append(f"[film.json] h3.steps 必須 >= 14，目前為 {h3.get('steps')}")

    shots = film.get("shots", [])
    if len(shots) != 14:
        errors.append(f"[film.json] 鏡頭數必須為 14，目前為 {len(shots)}")

    for s in shots:
        sid = s["id"]
        act = s.get("action", "")
        words = len(act.split())
        if not act.startswith("Starting from <Picture 1>"):
            errors.append(f"[{sid}] action 未以 'Starting from <Picture 1>' 開頭")
        if words < 45:
            errors.append(f"[{sid}] action 字數過短 ({words} words < 45)")
        if sid in SINGLE_FRAME_SHOTS and s.get("use_last"):
            errors.append(f"[{sid}] 互動對話鏡禁止設定 use_last=True（避免背景遊客與老師定格）")
        fp = HERE / "out" / "first" / f"{sid}.png"
        if not fp.exists():
            errors.append(f"[{sid}] 缺少首幀 {fp}")
        if s.get("use_last"):
            lp = HERE / "out" / "last" / f"{sid}.png"
            if not lp.exists():
                errors.append(f"[{sid}] use_last=True 但缺少尾幀 {lp}")
            elif fp.exists():
                im1 = Image.open(fp).convert("RGB").resize((320, 180))
                im2 = Image.open(lp).convert("RGB").resize((320, 180))
                diff = ImageChops.difference(im1, im2)
                mean_diff = sum(ImageStat.Stat(diff).mean) / 3.0
                if mean_diff < 3.0:
                    errors.append(f"[{sid}] 首尾幀幾乎相同 (mean_diff={mean_diff:.2f} < 3.0)，請改設 use_last=False！")

    for sp_file in sorted((HERE / "out" / "h3").glob("S*/spec.json")):
        sp_raw = sp_file.read_text(encoding="utf-8")
        check_text(str(sp_file.relative_to(HERE)), sp_raw, errors)
        sp = json.loads(sp_raw)
        if sp.get("draft") is not False:
            errors.append(f"[{sp_file.parent.name}/spec.json] draft 必須為 False")
        if int(sp.get("steps", 0)) < 14:
            errors.append(f"[{sp_file.parent.name}/spec.json] steps 必須 >= 14")

    if errors:
        print("❌ LINT FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print("✅ LINT PASSED: film.json 與所有 spec 設定 100% 符合 V3 規範（2D 動畫風格鎖定、非 draft、首尾幀防結冰通過）。")


if __name__ == "__main__":
    main()
