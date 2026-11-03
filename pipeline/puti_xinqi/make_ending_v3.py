"""自製 V3 專屬《菩提心起：佛陀教我做導覽》片尾（8.5 秒，1920x1080 24fps）：
- Ken Burns 動態推進 S14 大合照 + 金色菩提光點
- 雙階段彈性字卡（片名主視覺 → 佛陀紀念館第二展廳展覽資訊與 Puti-AI 署名）
- 所有文字嚴格置中於安全框（左右各留 >= 160px 邊距），絕不切字。"""
import math
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
ED = OUT / "ending"
ED.mkdir(parents=True, exist_ok=True)

W, H, FPS = 1920, 1080, 24
DUR = 8.5
N_FRAMES = int(DUR * FPS)


def get_font(size):
    for p in (
        r"C:\Windows\Fonts\msjhbd.ttc",
        r"C:\Windows\Fonts\msjh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
    ):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


FONT_HERO = get_font(92)
FONT_SUB = get_font(44)
FONT_BANNER = get_font(48)
FONT_CREDIT = get_font(34)
FONT_SMALL = get_font(28)


def ease_out_back(x):
    x = max(0.0, min(1.0, x))
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * pow(x - 1.0, 3) + c1 * pow(x - 1.0, 2)


def ease_in_out(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


def draw_centered_text(draw, y, text, font, fill, stroke_fill=(15, 23, 42, 255), stroke_width=6):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    draw.text((x, y), text, font=font, fill=fill, stroke_fill=stroke_fill, stroke_width=stroke_width)


def main():
    bg_src = Image.open(OUT / "last" / "S14.png").convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    c1 = Image.open(OUT / "last" / "S02.png").convert("RGB").resize((360, 202), Image.Resampling.LANCZOS)
    c2 = Image.open(OUT / "last" / "S07.png").convert("RGB").resize((360, 202), Image.Resampling.LANCZOS)
    c3 = Image.open(OUT / "last" / "S13.png").convert("RGB").resize((360, 202), Image.Resampling.LANCZOS)

    rng = np.random.default_rng(20261103)
    sparkles = [
        (rng.uniform(0, W), rng.uniform(0, H), rng.uniform(3, 9), rng.uniform(30, 80), rng.uniform(0, 6.28))
        for _ in range(55)
    ]

    out_mp4 = ED / "ending.mp4"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p",
        str(out_mp4)
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for fn in range(N_FRAMES):
        t = fn / FPS
        # 1. Ken Burns 背景微推進
        scale = 1.0 + 0.07 * (t / DUR)
        sw, sh = int(W * scale), int(H * scale)
        bg = bg_src.resize((sw, sh), Image.Resampling.BICUBIC)
        left = (sw - W) // 2
        top = int((sh - H) * 0.35)
        frame = bg.crop((left, top, left + W, top + H))

        # 2. 第二階段背景柔焦與深棕暖金漸層壓暗，讓文字清晰
        if t < 3.6:
            darken = 0.22 * ease_in_out(t / 0.8)
        else:
            p2 = ease_in_out((t - 3.6) / 0.7)
            blurred = frame.filter(ImageFilter.GaussianBlur(radius=8 * p2))
            frame = Image.blend(frame, blurred, p2 * 0.75)
            darken = 0.22 + 0.45 * p2

        overlay = Image.new("RGBA", (W, H), (24, 16, 12, int(255 * darken)))
        canvas = Image.alpha_composite(frame.convert("RGBA"), overlay)
        draw = ImageDraw.Draw(canvas, "RGBA")

        # 3. 漂浮金色菩提光點
        for sx, sy, sr, vy, phase in sparkles:
            cy = (sy - vy * t) % H
            cx = (sx + 18.0 * math.sin(t * 1.8 + phase)) % W
            alpha = int(110 + 95 * math.sin(t * 3.5 + phase))
            draw.ellipse((cx - sr, cy - sr, cx + sr, cy + sr), fill=(255, 225, 110, alpha))

        # 4. 階段一（0.2s ~ 3.9s）：片名大字卡
        if 0.15 <= t <= 3.95:
            a_in = ease_out_back((t - 0.15) / 0.55)
            a_out = 1.0 - ease_in_out((t - 3.45) / 0.5) if t > 3.45 else 1.0
            op = max(0.0, min(1.0, a_in * a_out))
            y_shift = int((1.0 - a_in) * 50)

            box_w, box_h = 1420, 310
            bx = (W - box_w) // 2
            by = 650 + y_shift
            draw.rounded_rectangle(
                (bx, by, bx + box_w, by + box_h),
                radius=36,
                fill=(38, 22, 16, int(220 * op)),
                outline=(255, 204, 51, int(245 * op)),
                width=5,
            )
            draw_centered_text(
                draw, by + 34,
                "★ 佛光山佛陀紀念館・沉浸式導覽特企動畫 ★",
                FONT_SUB,
                fill=(255, 224, 102, int(255 * op)),
                stroke_fill=(20, 12, 8, int(240 * op)),
                stroke_width=4,
            )
            draw_centered_text(
                draw, by + 115,
                "菩提心起：佛陀教我做導覽",
                FONT_HERO,
                fill=(255, 255, 255, int(255 * op)),
                stroke_fill=(180, 83, 9, int(255 * op)),
                stroke_width=8,
            )

        # 5. 階段二（3.8s ~ 8.5s）：特展資訊＋精選劇照＋Puti-AI 版權宣告
        if t >= 3.8:
            op = ease_in_out((t - 3.8) / 0.55)
            draw_centered_text(
                draw, 58,
                "《菩提心起：佛陀教我做導覽》",
                FONT_SUB,
                fill=(255, 230, 128, int(255 * op)),
                stroke_fill=(20, 12, 8, int(240 * op)),
                stroke_width=5,
            )
            cards = [(c1, "佛陀現身・破冰點撥"), (c2, "人物剖析・千年祈願"), (c3, "觀像觀心・菩提心起")]
            gap = 56
            total_w = 3 * 360 + 2 * gap
            start_x = (W - total_w) // 2
            cy = 155
            for idx, (cim, cap) in enumerate(cards):
                cx = start_x + idx * (360 + gap)
                draw.rounded_rectangle(
                    (cx - 6, cy - 6, cx + 366, cy + 258),
                    radius=18,
                    fill=(45, 26, 18, int(235 * op)),
                    outline=(255, 204, 51, int(240 * op)),
                    width=4,
                )
                c_rgba = cim.copy().convert("RGBA")
                c_rgba.putalpha(int(255 * op))
                canvas.paste(c_rgba, (cx, cy), c_rgba)
                tb = draw.textbbox((0, 0), cap, font=FONT_SMALL)
                tx = cx + (360 - (tb[2] - tb[0])) // 2
                draw.text((tx, cy + 214), cap, font=FONT_SMALL, fill=(255, 240, 180, int(255 * op)))

            ban_w, ban_h = 1520, 150
            bx = (W - ban_w) // 2
            by = 465
            draw.rounded_rectangle(
                (bx, by, bx + ban_w, by + ban_h),
                radius=28,
                fill=(145, 32, 32, int(238 * op)),
                outline=(255, 224, 102, int(255 * op)),
                width=5,
            )
            draw_centered_text(
                draw, by + 42,
                "佛光山佛陀紀念館本館第二展廳｜菩提心起—史博館典藏佛像特展",
                FONT_BANNER,
                fill=(255, 250, 220, int(255 * op)),
                stroke_fill=(70, 10, 10, int(255 * op)),
                stroke_width=6,
            )

            foot_w, foot_h = 1560, 275
            fx = (W - foot_w) // 2
            fy = 665
            draw.rounded_rectangle(
                (fx, fy, fx + foot_w, fy + foot_h),
                radius=26,
                fill=(24, 18, 15, int(230 * op)),
                outline=(245, 190, 90, int(210 * op)),
                width=3,
            )
            draw_centered_text(
                draw, fy + 32,
                "企劃／導演／製作：屏東縣後庄國小 黃朝榮老師（Puti-AI）",
                FONT_CREDIT,
                fill=(253, 224, 71, int(255 * op)),
                stroke_fill=(15, 10, 8, int(240 * op)),
                stroke_width=4,
            )
            draw_centered_text(
                draw, fy + 105,
                "屏東縣後庄國小黃朝榮老師作品，免費分享，歡迎擴散推廣",
                FONT_CREDIT,
                fill=(255, 255, 255, int(255 * op)),
                stroke_fill=(15, 10, 8, int(240 * op)),
                stroke_width=4,
            )
            draw_centered_text(
                draw, fy + 165,
                "嚴禁商用與任何侵權、不尊重著作權的行為｜更多 Puti-AI 教學工具歡迎至專區體驗",
                FONT_SMALL,
                fill=(226, 232, 240, int(255 * op)),
                stroke_fill=(15, 10, 8, int(220 * op)),
                stroke_width=3,
            )

        # 6. 最後 0.6 秒淡出至黑畫面
        if t > DUR - 0.6:
            fade_a = int(255 * ease_in_out((t - (DUR - 0.6)) / 0.6))
            draw.rectangle((0, 0, W, H), fill=(0, 0, 0, fade_a))

        rgb = canvas.convert("RGB")
        proc.stdin.write(rgb.tobytes())
        if fn == int(1.8 * FPS):
            rgb.save(ED / "preview_phase1.jpg", quality=90)
        elif fn == int(5.5 * FPS):
            rgb.save(ED / "preview_phase2.jpg", quality=90)

    proc.stdin.close()
    rc = proc.wait()
    assert rc == 0, f"ffmpeg ending failed: {rc}"
    print(f"[ending_v3] 已生成 {out_mp4} ({DUR}s)")


if __name__ == "__main__":
    main()
