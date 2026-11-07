"""依標點適當斷句，每次只顯示單行字幕（每行 <= 20 字，絕不一次顯示兩行），並快速重壓 16:9 / 9:16 成片。"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
POST = OUT / "post"


def ass_time(t):
    t = max(0.0, float(t))
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def dur(p):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def split_sub_clauses(role_name, text, t_start, t_end, max_len=20):
    """將長句按標點切為多段單行字幕，每段嚴格 <= max_len 字（含首段角色名），絕不出現 \\N 雙行"""
    raw_parts = re.findall(r"[^，。？！、：…]+[，。？！、：…]*", text)
    if not raw_parts:
        raw_parts = [text]

    clauses = []
    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        if not clauses:
            first_cand = f"{role_name}：{part}"
            if len(first_cand) <= max_len:
                clauses.append(first_cand)
            else:
                # 若單一子句加角色名超過 max_len，在 max_len 內切開
                cut_p = max_len - len(role_name) - 1
                clauses.append(f"{role_name}：{part[:cut_p]}")
                clauses.append(part[cut_p:])
        else:
            # 若前一段很短（如「第一招：」或「蹲下來看，」）且合併後 <= max_len，則合併為同一單行
            if len(clauses[-1]) + len(part) <= max_len and (clauses[-1][-1] in "、：" or len(clauses[-1]) <= 10):
                clauses[-1] += part
            elif len(part) <= max_len:
                clauses.append(part)
            else:
                clauses.append(part[:max_len])
                clauses.append(part[max_len:])

    # 按各段字數比例分配時間軸，切換流暢貼合語音
    weights = [max(2, len(re.sub(r"^(黃老師|小吉)：", "", c))) for c in clauses]
    total_w = sum(weights)
    span = max(0.5, t_end - t_start)
    out_segs = []
    cur = t_start
    for idx_c, (c, w) in enumerate(zip(clauses, weights)):
        seg_dur = span * (w / total_w)
        nxt = t_end if idx_c == len(clauses) - 1 else (cur + seg_dur)
        out_segs.append((round(cur, 2), round(nxt, 2), c))
        cur = nxt
    return out_segs


def main():
    cfg = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
    chars = cfg["chars"]
    edl_data = json.loads((POST / "edl.json").read_text(encoding="utf-8"))
    edl_rows = edl_data["shots"]
    vtotal = dur(POST / "video.mp4")

    # 1. 產生 16:9 單行分段 ASS 字幕（PlayResX=1920, WrapStyle=2 禁止自動換成兩行）
    hdr = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 2\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    )
    for k, c in chars.items():
        hdr += f"Style: {k},Microsoft JhengHei,54,{c.get('sub_color', '&H00FFFFFF')},&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,4,1,2,80,80,54,1\n"
    ev = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"

    caps = sorted([(l, r) for r in edl_rows for l in r["lines"]], key=lambda x: x[0]["film_start"])
    print("=== 單行分段字幕預覽（每段 <= 20 字，一次只顯示 1 行）===")
    for i, (l, r) in enumerate(caps):
        a = max(r["start"] + 0.10, l["film_start"] - 0.04)
        b = max(a + 0.5, l["film_end"] + 0.16)
        if i + 1 < len(caps):
            b = min(b, caps[i + 1][0]["film_start"] - 0.08)
        b = min(b, r["start"] + r["dur"] - 0.08)
        segs = split_sub_clauses(chars[l["who"]]["name"], l["text"], a, b, max_len=20)
        for seg_a, seg_b, seg_txt in segs:
            print(f"  [{r['id']}] {seg_a:5.2f}s~{seg_b:5.2f}s ({len(seg_txt):2d}字): {seg_txt}")
            ev += f"Dialogue: 0,{ass_time(seg_a)},{ass_time(seg_b)},{l['who']},,0,0,0,,{seg_txt}\n"

    (POST / "subs.ass").write_text(hdr + ev, encoding="utf-8")

    # 2. 產生 9:16 單行分段 ASS 字幕
    hdr_v = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 2\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: top_tag,Microsoft JhengHei,40,&H0066E0FF,&H000000FF,&H00081020,&H00000000,-1,0,0,0,100,100,2,0,1,4,2,8,40,40,185,1\n"
        "Style: top_title,Microsoft JhengHei,68,&H00FFFFFF,&H000000FF,&H00083878,&H00000000,-1,0,0,0,100,100,3,0,1,6,3,8,40,40,260,1\n"
        "Style: bot_credit,Microsoft JhengHei,30,&H00B0D8FF,&H000000FF,&H00081020,&H00000000,-1,0,0,0,100,100,1,0,1,3,1,2,40,40,120,1\n"
    )
    for k, c in chars.items():
        hdr_v += f"Style: {k},Microsoft JhengHei,46,{c.get('sub_color', '&H00FFFFFF')},&H000000FF,&H00101010,&H90000000,-1,0,0,0,100,100,1,0,1,5,2,2,35,35,340,1\n"
    ev_v = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    ev_v += f"Dialogue: 0,0:00:00.00,{ass_time(vtotal)},top_tag,,0,0,0,,★ 佛光山佛陀紀念館・沉浸式導覽特企 ★\n"
    ev_v += f"Dialogue: 0,0:00:00.00,{ass_time(vtotal)},top_title,,0,0,0,,《菩提心起：佛陀教我做導覽》\n"
    ev_v += f"Dialogue: 0,0:00:00.00,{ass_time(vtotal)},bot_credit,,0,0,0,,屏東縣後庄國小黃朝榮老師 (Puti-AI) 作品｜免費分享・歡迎推廣\n"

    for i, (l, r) in enumerate(caps):
        a = max(r["start"] + 0.10, l["film_start"] - 0.04)
        b = max(a + 0.5, l["film_end"] + 0.16)
        if i + 1 < len(caps):
            b = min(b, caps[i + 1][0]["film_start"] - 0.08)
        b = min(b, r["start"] + r["dur"] - 0.08)
        for seg_a, seg_b, seg_txt in split_sub_clauses(chars[l["who"]]["name"], l["text"], a, b, max_len=20):
            ev_v += f"Dialogue: 1,{ass_time(seg_a)},{ass_time(seg_b)},{l['who']},,0,0,0,,{seg_txt}\n"

    (POST / "subs_vertical.ass").write_text(hdr_v + ev_v, encoding="utf-8")

    # 3. 直接從已組裝好的 post/video.mp4 + post/mix.wav 極速重壓字幕
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", "post/video.mp4", "-i", "post/mix.wav",
        "-vf", "subtitles=post/subs.ass",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest",
        "cut/film_1080p.mp4"
    ], cwd=str(OUT), check=True)

    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(OUT / "cut" / "film_1080p.mp4"),
        "-vf", "scale=1280:720", "-c:v", "libx264", "-crf", "24", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", str(OUT / "cut" / "film_720p_phone.mp4")
    ], check=True)

    vf_vert = (
        "split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:4,eq=brightness=-0.38:saturation=0.75[bg2];"
        "[fg]scale=1080:608:flags=lanczos,"
        "pad=1080:620:0:6:color=0xD4AF37[fg2];"
        "[bg2][fg2]overlay=0:580,subtitles=post/subs_vertical.ass,format=yuv420p"
    )
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", "post/video.mp4", "-i", "post/mix.wav",
        "-filter_complex", vf_vert,
        "-map", "0:a?", "-map", "1:a",
        "-c:v", "libx264", "-crf", "17", "-preset", "fast",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest",
        "cut/film_vertical_1080x1920.mp4"
    ], cwd=str(OUT), check=True)

    ws_dir = Path(r"c:\antigravity\影片\菩提心起")
    shutil.copy2(OUT / "cut" / "film_1080p.mp4", ws_dir / "菩提心起_佛陀教我做導覽_v3_1080p成片.mp4")
    shutil.copy2(OUT / "cut" / "film_720p_phone.mp4", ws_dir / "菩提心起_佛陀教我做導覽_v3_720p手機輕量版.mp4")
    shutil.copy2(OUT / "cut" / "film_vertical_1080x1920.mp4", ws_dir / "菩提心起_佛陀教我做導覽_v3_9x16手機直式版.mp4")
    print("✅ 單行分段字幕 (<=20字/行) 已重壓並同步至 3 支成片！")


if __name__ == "__main__":
    main()
