"""一鍵初始化基於 V3 黃金範本的新專案 (init_v3_project.py)

用法：
    python init_v3_project.py <專案英文ID> [--title <中文片名>]

範例：
    python init_v3_project.py traffic_safety --title "交通安全大作戰"
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent
TEMPL = REPO / "pipeline" / "puti_xinqi"


def main():
    parser = argparse.ArgumentParser(description="一鍵初始化 V3 標準短片專案")
    parser.add_argument("project_id", type=str, help="新專案英文 ID，例如: traffic_safety")
    parser.add_argument("--title", type=str, default="", help="新專案中文片名 (選填)")
    args = parser.parse_args()

    pid = args.project_id.strip()
    title = args.title.strip() or pid

    dst = REPO / "pipeline" / pid
    if dst.exists():
        print(f"❌ 錯誤：專案目錄已存在: {dst}")
        sys.exit(1)

    print(f"🚀 開始初始化專案: {pid} ({title})")
    dst.mkdir(parents=True, exist_ok=True)

    # 1. 建立標準子目錄
    subdirs = [
        "out/first",
        "out/last",
        "out/chars",
        "out/voice",
        "out/sfx",
        "out/cut",
        "out/review",
        "out/ending",
    ]
    for sd in subdirs:
        (dst / sd).mkdir(parents=True, exist_ok=True)

    # 2. 複製核心防呆與自動化腳本
    scripts_to_copy = [
        "lint_v3.py",
        "build_specs_v3.py",
        "build_film_v3.py",
        "gate2_inspect.py",
        "reburn_single_line_subs.py",
        "make_vertical_panscan.py",
        "inspect_vert.py",
        "relax_voices.py",
        "check_spec.py",
        "audit_audio_v3.py",
        "fix_v3_cut.py",
        "make_ending_v3.py",
        "qa_v3.py",
        "review.py",
    ]
    for s in scripts_to_copy:
        src_f = TEMPL / s
        if src_f.exists():
            shutil.copy2(src_f, dst / s)
            print(f"   + 複製腳本: {s}")

    # 3. 建立標準 film.json 樣板 (已鎖定 3D 卡通、14 步、h3_ref 等避坑設定)
    sample_film = {
        "title": title,
        "style": "a vibrant 3D animated family feature film, stylized Pixar-like CG cartoon rendering, soft global illumination, saturated colors, smooth clean toon shading",
        "draft": False,
        "steps": 14,
        "voice_mode": "h3_ref",
        "chars": {
            "hero": {
                "name": "主角",
                "desc": "3D animated cartoon character, cheerful boy wearing a yellow t-shirt and blue shorts",
                "ref_voice": "out/voice/ref_hero.wav",
                "sub_color": "&H00FFFF00",
            }
        },
        "mix": {
            "music_under_lines": 0.22,
            "target_lufs": -15.5,
        },
        "shots": [
            {
                "id": "S01",
                "dur": 4.5,
                "scene": "at a sunny elementary school playground with green trees and running track under bright morning sunlight",
                "first_frame": "out/first/S01.png",
                "last_frame": "out/last/S01.png",
                "use_last": False,
                "action": "Starting from <Picture 1>, the hero stands in front of the camera, waves his right hand cheerfully towards the viewer, speaking with a bright smile, while background trees gently sway in the morning breeze.",
                "line": {
                    "who": "hero",
                    "text": "大家好，今天讓我們一起來守護校園安全！",
                },
            }
        ],
    }

    (dst / "film.json").write_text(json.dumps(sample_film, ensure_ascii=False, indent=2), encoding="utf-8")
    print("   + 建立樣板: film.json (含標準 3D 動畫、14 步、h3_ref 設定)")

    # 4. 建立專案快速指引 README.md
    readme_content = f"""# {title} ({pid})

本專案使用 `shanshiba-workflow` V3 黃金標準管線建立。

## 標準製片 5 步驟：

1. **準備素材**：
   - 首尾幀放置於 `out/first/`、`out/last/`
   - 角色參考音置於 `out/voice/`
   - 編輯 `film.json` 確認分鏡、台詞與動作

2. **生成前防呆檢查 (Pre-flight Lint)**：
   ```powershell
   python lint_v3.py
   python build_specs_v3.py
   ```

3. **Colab G4 渲染 (14 步)**：
   ```powershell
   cd ../..
   python cloud/colab_h3.py check
   python cloud/colab_h3.py start --h3-only
   python cloud/colab_h3.py batch pipeline/{pid}/out/h3/S01/spec.json ...
   python cloud/colab_h3.py stop   # ⚠️ 跑完務必關機！
   cd pipeline/{pid}
   ```

4. **抽幀檢視與精準剪輯 (Tight Edit)**：
   ```powershell
   python make_ending_v3.py
   python fix_v3_cut.py
   ```

5. **成品檢驗**：
   - 成片位於 `out/cut/film_1080p.mp4`
   - 自審圖表位於 `out/review/film_1080p_pass1.jpg` 與 `film_1080p_pass5_cuts.jpg`
"""
    (dst / "README.md").write_text(readme_content, encoding="utf-8")
    print("   + 建立指引: README.md")

    print("\n✅ 專案建立完成！路徑：")
    print(f"👉 {dst}")


if __name__ == "__main__":
    main()

