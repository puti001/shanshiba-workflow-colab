import asyncio, shutil, subprocess, sys
from pathlib import Path
import edge_tts

sys.stdout.reconfigure(encoding="utf-8")
hd = Path(r"C:\antigravity\影片\shanshiba-workflow-colab\pipeline\puti_xinqi\out\voice\h3")

# 1. 將先前被加速壓進 6.0s 的 S01_fix.wav 與 S11_fix.wav 還原回 1.0x 自然語速 (~7.0s)
for fname in ["S01_fix.wav", "S11_fix.wav"]:
    src = hd / fname
    bak = hd / f"_fast_{fname}"
    if not bak.exists():
        shutil.copy2(src, bak)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(bak),
        "-af", "atempo=0.86", "-ar", "48000", "-ac", "1", str(src)
    ], check=True)
    print("Restored natural pace:", fname)

# 2. 將佛陀 S04, S05, S06 以從容自然語速 (rate='-4%') 重新合成 (~7.0s)
async def make_calm_buddha():
    lines = {
        "S04_fix.wav": "第一招：看神情問自己。為什麼這位佛陀留著鬍子、赤著雙腳？因為他剛走過人間最痛的迷惘。",
        "S05_fix.wav": "再看這尊宋代羅漢，眼窩深邃、眉頭微蹙，他不是遙不可及的神，而是正為人生難題苦思的你我！",
        "S06_fix.wav": "第二招：找尋藏在細節裡的小人物！別只看大佛，帶遊客蹲下來，看碑底這位北齊的張解。",
    }
    for fname, txt in lines.items():
        tmp = hd / f"_tmp_calm_{fname}.mp3"
        for _ in range(4):
            try:
                c = edge_tts.Communicate(text=txt, voice="zh-TW-YunJheNeural", rate="-4%", pitch="-3Hz")
                await c.save(str(tmp))
                break
            except Exception:
                await asyncio.sleep(1.0)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
            "-af", "highpass=f=80,bass=g=2.5:f=140:w=0.5,equalizer=f=3800:t=q:w=1.2:g=3.5,treble=g=4.0:f=6500",
            "-ar", "48000", "-ac", "1", str(hd / fname)
        ], check=True)
        tmp.unlink(missing_ok=True)
        print("Calm Buddha synthesized:", fname)

asyncio.run(make_calm_buddha())
