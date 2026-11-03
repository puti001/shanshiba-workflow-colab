"""9:16 智慧導播運鏡版 (Smart Pan & Scan Virtual Camera)
直接從 16:9 (1920x1080) 無字幕母帶取樣，依每鏡劇情、說話者與文物重點，
以 Cosine 平滑緩動 (Smooth Ease-In-Out) 進行水平搖鏡 (Pan) 與呼吸推軌 (Zoom)，
輸出滿版 9:16 (1080x1920) 直式影片並疊加單行分段字幕 (<=20字/行)。
"""
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
POST = OUT / "post"
FPS = 24
SRC_W, SRC_H = 1920, 1080
OUT_W, OUT_H = 1080, 1920

from reburn_single_line_subs import split_sub_clauses, ass_time, dur

# 每鏡專屬的「虛擬導播機」關鍵幀腳本：
# 格式為 [(相對時間比例 0.0~1.0, 水平中心點 cx 0.16~0.84, 垂直中心點 cy 0.45~0.55, 取樣高度比例 zh 0.78~1.0)]
# cx: 0.18=左方角色(黃老師), 0.50=中央展櫃文物, 0.80=右方角色(佛陀/遊客)
# zh: 1.0=標準滿高取樣 (寬 608x高 1080), 0.82=特寫放大 (寬 498x高 885，聚焦表情或碑底細節)
CAMERA_SCRIPT = {
    # S01: 先聚焦左方苦思看稿的黃老師 (0.20) -> 講到「這特展到底該怎麼導覽」時搖向中央〈釋迦出山〉展櫃 (0.46)
    "S01": [(0.0, 0.23, 0.50, 0.94), (0.50, 0.23, 0.50, 0.91), (1.0, 0.24, 0.50, 0.88)],
    # S02: 先聚焦中央展櫃金光躍出的佛陀 (0.48) -> 佛陀開口對黃老師說話時微移至雙人重心 (0.34)
    "S02": [(0.0, 0.48, 0.50, 0.95), (0.35, 0.42, 0.48, 0.92), (1.0, 0.34, 0.48, 0.96)],
    # S03: 佛陀拍肩傳授心法：聚焦佛陀說話神情 (0.52) -> 緩移至左方點頭領悟的黃老師與佛陀同框 (0.38)
    "S03": [(0.0, 0.52, 0.48, 0.92), (0.50, 0.44, 0.48, 0.95), (1.0, 0.36, 0.48, 1.00)],
    # S04: 第一招看〈釋迦出山〉：先拍右方佛陀開示 (0.74) -> 慢推聚焦中央蓄鬍赤足佛像特寫 (0.50, zoom 0.85) -> 帶到左方合十感悟的黃老師 (0.28)
    "S04": [(0.0, 0.74, 0.50, 0.94), (0.45, 0.50, 0.48, 0.85), (0.78, 0.48, 0.48, 0.88), (1.0, 0.28, 0.50, 0.96)],
    # S05: 宋代羅漢：右方佛陀手指向展櫃 (0.68) -> 聚焦中央深邃眼窩與微蹙眉頭的羅漢像 (0.48, zoom 0.84) -> 左方彎腰細看的黃老師 (0.30)
    "S05": [(0.0, 0.68, 0.50, 0.94), (0.45, 0.48, 0.48, 0.84), (0.80, 0.44, 0.48, 0.88), (1.0, 0.30, 0.52, 0.95)],
    # S06: 第二招北齊造像碑：右方蹲下的佛陀說話 (0.72) -> 慢推聚焦中央發光的石碑底座供養人張解 (0.48, zoom 0.82)
    "S06": [(0.0, 0.72, 0.54, 0.92), (0.45, 0.52, 0.55, 0.86), (1.0, 0.46, 0.56, 0.82)],
    # S07: 碑底浮現古人祈福金影：從碑底特寫 (0.50, cy=0.56, zoom=0.84) 隨金影冉冉升起緩緩拉開並上搖 (0.48, cy=0.46, zoom=0.98)
    "S07": [(0.0, 0.52, 0.56, 0.84), (0.60, 0.48, 0.48, 0.92), (1.0, 0.42, 0.46, 0.98)],
    # S08: 唐澄泥與明鐵佛：先拍佛陀雙手捧金光與左方澄泥佛 (0.44) -> 隨佛陀揮手平滑右搖至右側大尊明代鑄鐵坐佛 (0.68)
    "S08": [(0.0, 0.44, 0.50, 0.92), (0.48, 0.52, 0.50, 0.90), (1.0, 0.68, 0.48, 0.94)],
    # S09: 黃老師恍然大悟：特寫左方收起小抄、自信開口的黃老師 (0.28, zoom 0.88) -> 微右移帶入右方合十讚許的佛陀 (0.42, zoom 0.98)
    "S09": [(0.0, 0.28, 0.48, 0.88), (0.60, 0.34, 0.48, 0.92), (1.0, 0.42, 0.48, 0.98)],
    # S10: 佛陀化金光歸位、遊客進場：中央化光佛陀 (0.46) -> 金光飛入右方展櫃 (0.76) -> 快速左搖迎接左方進場的遊客家庭與黃老師 (0.26)
    "S10": [(0.0, 0.46, 0.50, 0.94), (0.42, 0.74, 0.50, 0.94), (1.0, 0.26, 0.50, 0.96)],
    # S11: 黃老師實戰導覽〈釋迦出山〉：左方熱情說話的黃老師 (0.22) -> 搖過中央佛像 (0.50) -> 右方放下手機抬頭驚嘆的遊客一家 (0.74)
    "S11": [(0.0, 0.22, 0.50, 0.92), (0.48, 0.48, 0.48, 0.90), (1.0, 0.72, 0.50, 0.94)],
    # S12: 蹲看北齊石碑：左方蹲下指碑底的黃老師 (0.26) -> 推進中央碑底刻字與右方睜大眼蹲看的母女遊客 (0.58, zoom 0.88)
    "S12": [(0.0, 0.26, 0.54, 0.92), (0.45, 0.48, 0.55, 0.86), (1.0, 0.60, 0.54, 0.90)],
    # S13: 唐代佛頭與觀音畫像：左方合十說話的黃老師 (0.24) -> 緩慢橫搖經過微笑唐代石雕佛頭 (0.50, zoom 0.86) -> 右方合十感動的遊客 (0.66)
    "S13": [(0.0, 0.24, 0.50, 0.90), (0.50, 0.48, 0.48, 0.86), (1.0, 0.64, 0.50, 0.92)],
    # S14: 結尾大合照：先聚焦比 OK 開朗總結的黃老師 (0.34, zoom 0.88) -> 拉開至中央展櫃上方發光佛陀金影與揮手的遊客 (0.50, zoom 1.00)
    "S14": [(0.0, 0.34, 0.50, 0.88), (0.50, 0.46, 0.48, 0.94), (1.0, 0.52, 0.46, 1.00)],
}


def interp_keyframes(kfs, u):
    """使用 Cosine Ease-In-Out 在關鍵幀之間平滑插值"""
    u = max(0.0, min(1.0, float(u)))
    for i in range(len(kfs) - 1):
        t0, cx0, cy0, zh0 = kfs[i]
        t1, cx1, cy1, zh1 = kfs[i + 1]
        if t0 <= u <= t1:
            span = max(1e-6, t1 - t0)
            p = (u - t0) / span
            # Cosine ease-in-out
            w = 0.5 - 0.5 * math.cos(math.pi * p)
            return (
                cx0 + (cx1 - cx0) * w,
                cy0 + (cy1 - cy0) * w,
                zh0 + (zh1 - zh0) * w,
            )
    _, cx, cy, zh = kfs[-1]
    return cx, cy, zh


def render_panscan_shot(src_mp4: Path, dst_mp4: Path, kfs):
    """逐幀執行雙線性高畫質 9:16 智慧取樣與平滑運鏡"""
    d = dur(src_mp4)
    n_frames = max(1, round(d * FPS))

    reader = subprocess.Popen(
        [
            "ffmpeg", "-loglevel", "error", "-i", str(src_mp4),
            "-vf", f"scale={SRC_W}:{SRC_H}:flags=lanczos",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"
        ],
        stdout=subprocess.PIPE
    )
    writer = subprocess.Popen(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS),
            "-i", "-",
            "-c:v", "libx264", "-crf", "15", "-preset", "fast", "-pix_fmt", "yuv420p",
            str(dst_mp4)
        ],
        stdin=subprocess.PIPE
    )

    from PIL import Image
    frame_bytes = SRC_W * SRC_H * 3
    idx = 0
    while True:
        raw = reader.stdout.read(frame_bytes)
        if not raw or len(raw) < frame_bytes:
            break
        u = idx / max(1, n_frames - 1)
        cx, cy, zh = interp_keyframes(kfs, u)

        # 計算 9:16 取樣框尺寸 (寬:高 = 9:16)
        crop_h = SRC_H * zh
        crop_w = crop_h * (9.0 / 16.0)

        x0 = cx * SRC_W - crop_w / 2.0
        y0 = cy * SRC_H - crop_h / 2.0
        x0 = max(0.0, min(SRC_W - crop_w, x0))
        y0 = max(0.0, min(SRC_H - crop_h, y0))

        im = Image.frombytes("RGB", (SRC_W, SRC_H), raw)
        # 使用 PIL transform 支援次像素 (sub-pixel) 浮點座標裁切，徹底消除整數像素移動的抖動感！
        sub_im = im.transform(
            (OUT_W, OUT_H),
            Image.Transform.EXTENT,
            (x0, y0, x0 + crop_w, y0 + crop_h),
            resample=Image.Resampling.BICUBIC
        )
        writer.stdin.write(sub_im.tobytes())
        idx += 1

    reader.stdout.close()
    reader.wait()
    writer.stdin.close()
    writer.wait()


def main():
    cfg = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
    chars = cfg["chars"]
    edl_data = json.loads((POST / "edl.json").read_text(encoding="utf-8"))
    edl_rows = edl_data["shots"]

    vseg_dir = POST / "seg_vert_panscan"
    vseg_dir.mkdir(parents=True, exist_ok=True)
    vparts = []

    print("🎬 開始逐鏡執行 9:16 智慧導播運鏡 (Sub-pixel Smooth Pan & Scan)...")
    for r in edl_rows:
        sid = r["id"]
        src_seg = POST / "seg" / f"{sid}.mp4"
        dst_seg = vseg_dir / f"{sid}.mp4"
        kfs = CAMERA_SCRIPT.get(sid, [(0.0, 0.5, 0.5, 1.0), (1.0, 0.5, 0.5, 1.0)])
        render_panscan_shot(src_seg, dst_seg, kfs)
        vparts.append(dst_seg)
        print(f"  + [{sid}] 完成平滑導播運鏡 ({r['dur']:.2f}s)")

    # 片尾同樣轉為滿版 9:16 中心緩推
    ending_mp4 = OUT / "ending" / "ending.mp4"
    if ending_mp4.exists():
        dst_end = vseg_dir / "ending_vert.mp4"
        render_panscan_shot(ending_mp4, dst_end, [(0.0, 0.50, 0.50, 1.00), (1.0, 0.50, 0.50, 0.94)])
        vparts.append(dst_end)

    list_v = POST / "list_vert_panscan.txt"
    list_v.write_text("".join(f"file '{p.as_posix()}'\n" for p in vparts), encoding="utf-8")
    raw_vert_mp4 = POST / "video_vert_panscan.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_v),
        "-c", "copy", str(raw_vert_mp4)
    ], check=True)

    vtotal = dur(raw_vert_mp4)

    # 產生滿版 9:16 專屬單行分段 ASS 字幕（底部精緻漸層保護區＋頂部微浮水印＋單行 <=20字）
    hdr_v = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: top_badge,Microsoft JhengHei,36,&H0088E8FF,&H000000FF,&H00081020,&H70000000,-1,0,0,0,100,100,2,0,1,4,2,8,40,40,75,1\n"
        "Style: bot_credit,Microsoft JhengHei,28,&H00B8E0FF,&H000000FF,&H00081020,&H80000000,-1,0,0,0,100,100,1,0,1,3,1,2,35,35,65,1\n"
    )
    for k, c in chars.items():
        hdr_v += f"Style: {k},Microsoft JhengHei,48,{c.get('sub_color', '&H00FFFFFF')},&H000000FF,&H00080808,&H90000000,-1,0,0,0,100,100,1,0,1,5,2,2,35,35,195,1\n"
    ev_v = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    ev_v += f"Dialogue: 0,0:00:00.00,{ass_time(vtotal)},top_badge,,0,0,0,,《菩提心起：佛陀教我做導覽》\n"
    ev_v += f"Dialogue: 0,0:00:00.00,{ass_time(vtotal)},bot_credit,,0,0,0,,屏東縣後庄國小黃朝榮老師 (Puti-AI) 作品｜免費分享・歡迎推廣\n"

    caps = sorted([(l, r) for r in edl_rows for l in r["lines"]], key=lambda x: x[0]["film_start"])
    for i, (l, r) in enumerate(caps):
        a = max(r["start"] + 0.10, l["film_start"] - 0.04)
        b = max(a + 0.5, l["film_end"] + 0.16)
        if i + 1 < len(caps):
            b = min(b, caps[i + 1][0]["film_start"] - 0.08)
        b = min(b, r["start"] + r["dur"] - 0.08)
        for seg_a, seg_b, seg_txt in split_sub_clauses(chars[l["who"]]["name"], l["text"], a, b, max_len=20):
            ev_v += f"Dialogue: 1,{ass_time(seg_a)},{ass_time(seg_b)},{l['who']},,0,0,0,,{seg_txt}\n"

    subs_p = POST / "subs_vert_panscan.ass"
    subs_p.write_text(hdr_v + ev_v, encoding="utf-8")

    out_mp4 = OUT / "cut" / "film_vertical_panscan_1080x1920.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", "post/video_vert_panscan.mp4", "-i", "post/mix.wav",
        "-vf", "subtitles=post/subs_vert_panscan.ass",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest",
        str(out_mp4)
    ], cwd=str(OUT), check=True)

    ws_dir = Path(r"c:\antigravity\影片\菩提心起")
    dest_panscan = ws_dir / "菩提心起_佛陀教我做導覽_v3_9x16滿版導播運鏡版.mp4"
    shutil.copy2(out_mp4, dest_panscan)
    # 同時也更新原本的 9x16手機直式版.mp4
    shutil.copy2(out_mp4, ws_dir / "菩提心起_佛陀教我做導覽_v3_9x16手機直式版.mp4")
    print(f"✅ 滿版 9:16 智慧導播運鏡版已輸出至: {dest_panscan}")


if __name__ == "__main__":
    main()
