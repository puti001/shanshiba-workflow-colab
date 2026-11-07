import json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
POST = OUT / "post"
edl = json.loads((POST / "edl.json").read_text(encoding="utf-8"))
vmp4 = OUT / "cut" / "film_vertical_panscan_1080x1920.mp4"

# 抽 14 鏡的 9:16 實際畫面 (每鏡抽 3 格: 15%, 50%, 85%) 拼成檢視表，親眼檢查有沒有切到人！
tw, th = 216, 384
cols = 6  # 每排 2 鏡 (各 3 格)
rows = 7
sheet = Image.new("RGB", (tw * cols, th * rows))
draw = ImageDraw.Draw(sheet)

for idx, r in enumerate(edl["shots"]):
    sid = r["id"]
    st, du = r["start"], r["dur"]
    for k, frac in enumerate([0.15, 0.50, 0.85]):
        t = st + du * frac
        raw = subprocess.run([
            "ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(vmp4),
            "-frames:v", "1", "-vf", f"scale={tw}:{th}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
        ], capture_output=True).stdout
        if len(raw) == tw * th * 3:
            im = Image.frombytes("RGB", (tw, th), raw)
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, 130, 26], fill=(0, 0, 0))
            d.text((4, 4), f"{sid} {int(frac*100)}% ({t:.1f}s)", fill=(255, 255, 0))
            c = (idx % 2) * 3 + k
            rw = idx // 2
            sheet.paste(im, (c * tw, rw * th))

out_jpg = OUT / "review" / "vert_panscan_check.jpg"
sheet.save(out_jpg, quality=85)
print("Saved:", out_jpg)
