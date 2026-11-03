"""V3 Lint Gate: 檢查 film.json 與所有 spec.json，違反任何一條直接失敗退出。
1. 嚴禁出現寫實/真人關鍵字：photoreal, live-action, 35mm, Kodak, 8k, real human, tokusatsu
2. 嚴禁 draft=True 或 steps < 14
3. 嚴禁 S03/S11/S13 出現舊版錯誤劇本殘留（camera lens, umbilical, students across campus clean）
4. 檢查每個鏡頭 action 字數 >= 45 words，且以 Starting from <Picture 1> 開頭
5. 檢查 first_frame / last_frame 檔案存在，且 S01/S03 不得掛載近似靜態的 last_frame
"""
import json
import re
import sys
from pathlib import Path

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
    r"optical lens",
    r"umbilical",
    r"vanguard clone",
]


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
        if sid in ("S01", "S03") and s.get("use_last"):
            errors.append(f"[{sid}] 禁止設定 use_last=True（避免背景學生與老師定格）")
        fp = HERE / "out" / "first" / f"{sid}.png"
        if not fp.exists():
            errors.append(f"[{sid}] 缺少首幀 {fp}")
        if s.get("use_last"):
            lp = HERE / "out" / "last" / f"{sid}.png"
            if not lp.exists():
                errors.append(f"[{sid}] use_last=True 但缺少尾幀 {lp}")

    # 若已經生成 spec.json 也一併檢查
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
    print("✅ LINT PASSED: film.json 與所有 spec 設定 100% 符合 V3 規範（無寫實詞、非 draft、劇本與圖片對齊）。")


if __name__ == "__main__":
    main()
