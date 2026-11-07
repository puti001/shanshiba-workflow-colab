"""V3 Tight Edit 精準剪輯、SFX 峰值正規化、-15.5 LUFS 母帶混音與 16:9 / 9:16 雙版本輸出 (海洋未來式 第1集：發燒的海洋母親)"""
import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
REPO = Path(r"C:\antigravity\影片\shanshiba-workflow-colab")
OUT = HERE / "out"
POST = OUT / "post"
SR, FPS = 48000, 24


def dur(p):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def load_wav(p):
    r = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(p), "-ar", str(SR), "-ac", "1", "-f", "f32le", "-"],
        capture_output=True
    )
    return np.frombuffer(r.stdout, np.float32).copy()


def ass_time(t):
    t = max(0.0, float(t))
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


# 依 8 格抽幀表與 Whisper word_timestamps 標定的自然語速區間
TIGHT_TRIM = {
    "S01": dict(cin=0.0, cout=6.55, spk=(0.74, 6.36), stretch=1.0),
    "S02": dict(cin=0.0, cout=6.55, spk=(0.00, 6.44), stretch=1.0),
    "S03": dict(cin=0.0, cout=6.45, spk=(0.00, 6.16), stretch=1.0),
    "S04": dict(cin=0.0, cout=6.58, spk=(0.00, 6.58), stretch=1.0),
    "S05": dict(cin=0.0, cout=6.50, spk=(2.14, 6.22), stretch=1.0),
    "S06": dict(cin=0.0, cout=6.58, spk=(0.00, 6.56), stretch=1.0),
    "S07": dict(cin=0.0, cout=6.50, spk=(0.74, 6.28), stretch=1.0),
    "S08": dict(cin=0.0, cout=6.35, spk=(0.00, 6.08), stretch=1.0),
    "S09": dict(cin=0.0, cout=6.50, spk=(1.68, 6.18), stretch=1.0),
    "S10": dict(cin=0.0, cout=5.20, spk=(0.00, 4.14), stretch=1.0),  # Tight Cut 剪除講完後的停滯
    "S11": dict(cin=0.0, cout=6.58, spk=(0.00, 6.58), stretch=1.0),
    "S12": dict(cin=0.0, cout=6.55, spk=(0.00, 6.38), stretch=1.0),
    "S13": dict(cin=0.0, cout=6.45, spk=(0.00, 6.10), stretch=1.0),
    "S14": dict(cin=0.0, cout=6.20, spk=(0.72, 5.72), stretch=1.0),
}


def main():
    POST.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
    chars = cfg["chars"]
    shots = cfg["shots"]
    mix_cfg = cfg.get("mix", {})
    amb_files = json.loads((POST / "amb.json").read_text(encoding="utf-8")) if (POST / "amb.json").exists() else {}

    # 1. 準備 14 句完整清晰、絕不超鏡長的台詞音檔
    hd = OUT / "voice" / "h3"
    hd.mkdir(parents=True, exist_ok=True)
    picks = {}
    line_shots = [s["id"] for s in shots if s.get("line")]

    for idx, sid in enumerate(line_shots):
        s = next(x for x in shots if x["id"] == sid)
        ln = s["line"]
        tr = TIGHT_TRIM[sid]
        stretch = float(tr.get("stretch", 1.0))
        raw_shot_len = round(tr["cout"] - tr["cin"], 3)
        shot_len = round(raw_shot_len * stretch, 3)
        max_allowed = shot_len - 0.25
        dst = hd / f"line{idx}_full.wav"

        sp0, sp1 = tr["spk"]
        cpath = OUT / "h3" / sid / "clip.mp4"
        atempo_val = 1.0 / stretch
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(cpath),
            "-vn",
            "-af", f"atrim=start={sp0:.3f}:end={sp1:.3f},asetpts=PTS-STARTPTS,atempo={atempo_val:.4f},highpass=f=85,equalizer=f=3500:t=q:w=1.0:g=4.5,treble=g=6.5:f=6000,acompressor=threshold=-18dB:ratio=2.2:makeup=2dB",
            "-ar", str(SR), "-ac", "1", str(dst)
        ], check=True)
        rel_at = round(max(0.05, (sp0 - tr["cin"]) * stretch), 3)

        d_wav = dur(dst)
        if rel_at + d_wav > shot_len - 0.06:
            rel_at = max(0.02, round(shot_len - d_wav - 0.08, 3))

        picks[str(idx)] = dict(
            shot=sid,
            who=ln["who"],
            text=ln["text"],
            file=str(dst),
            at=rel_at,
            end=round(rel_at + d_wav, 3),
            source="h3"
        )
        print(f"[Line {sid}] ({picks[str(idx)]['source']}) dur={d_wav:.2f}s | 鏡內={rel_at:.2f}s~{rel_at+d_wav:.2f}s / 鏡長={shot_len:.2f}s")

    (OUT / "voice_picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")

    # 2. 建立精準 EDL
    t = 0.0
    edl_rows = []
    for s in shots:
        sid = s["id"]
        tr = TIGHT_TRIM[sid]
        stretch = float(tr.get("stretch", 1.0))
        a = round(tr["cin"] * FPS) / FPS
        b = round(tr["cout"] * FPS) / FPS
        raw_dur = round(b - a, 3)
        shot_dur = round(raw_dur * stretch * FPS) / FPS
        lines = []
        if s.get("line"):
            i = line_shots.index(sid)
            ln = s["line"]
            p = picks[str(i)]
            d_line = dur(p["file"])
            f_start = round(t + p["at"], 3)
            f_end = round(f_start + d_line, 3)
            lines.append(dict(
                id=f"line{i}",
                who=ln["who"],
                text=ln["text"],
                file=p["file"],
                film_start=f_start,
                film_end=f_end
            ))
        edl_rows.append(dict(
            id=sid,
            start=round(t, 3),
            dur=shot_dur,
            raw_dur=raw_dur,
            stretch=stretch,
            src_in=a,
            src_out=b,
            lines=lines,
            amb=amb_files.get(sid)
        ))
        t += shot_dur

    ending_mp4 = OUT / "ending" / "ending.mp4"
    ending_dur = dur(ending_mp4) if ending_mp4.exists() else 0.0
    edl_data = dict(
        shots=edl_rows,
        story_end=round(t, 3),
        ending_dur=round(ending_dur, 3),
        total=round(t + ending_dur, 3),
    )
    (POST / "edl.json").write_text(json.dumps(edl_data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[EDL Natural Pace] 正片 {t:.2f}s + 片尾 {ending_dur:.2f}s = {t + ending_dur:.2f}s")

    # 3. 切出 14 個流暢的 1080p 24fps 鏡頭片段
    seg_dir = POST / "seg"
    seg_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    flash_out_shots = {"S01", "S06", "S09", "S11"}
    flash_in_shots = {"S02", "S07", "S10", "S12"}

    for r in edl_rows:
        sid = r["id"]
        src = OUT / "h3" / sid / "clip.mp4"
        p = seg_dir / f"{sid}.mp4"
        n_frames = round(r["dur"] * FPS)
        st_factor = r["stretch"]
        vf = [
            f"trim=start={r['src_in']:.3f}:duration={r['raw_dur']:.3f}",
            f"setpts={st_factor:.4f}*(PTS-STARTPTS)",
            "minterpolate=fps=24:mi_mode=blend",
            "scale=1920:1080:flags=lanczos",
            "unsharp=3:3:0.35:3:3:0.0",
        ]
        if sid in flash_in_shots:
            vf.append("fade=t=in:st=0:d=0.14:color=white")
        if sid in flash_out_shots:
            st_fade = max(0.0, r["dur"] - 0.14)
            vf.append(f"fade=t=out:st={st_fade:.3f}:d=0.14:color=white")
        vf.append("format=yuv420p")

        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(src),
            "-frames:v", str(n_frames), "-an",
            "-vf", ",".join(vf),
            "-c:v", "libx264", "-crf", "14", "-preset", "medium", str(p)
        ], check=True)
        parts.append(p)

    if ending_mp4.exists():
        parts.append(ending_mp4)

    (POST / "list.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(POST / "list.txt"),
        "-c", "copy", str(POST / "video.mp4")
    ], check=True)

    # 4. 混音：完整人聲 + 峰值正規化 SFX + 背景音樂 Ducking
    music_wav = OUT / "music" / "bgm_puti.wav"
    vtotal = dur(POST / "video.mp4")
    n = int(vtotal * SR) + SR
    voice = np.zeros(n, np.float32)
    amb_ = np.zeros(n, np.float32)
    duck = np.ones(n, np.float32)
    under = float(mix_cfg.get("music_under_lines", 0.22))

    for r in edl_rows:
        for l in r["lines"]:
            a_wav = load_wav(l["file"])
            pk = float(np.max(np.abs(a_wav))) if len(a_wav) else 0.0
            if pk > 1e-4:
                a_wav = a_wav * (0.85 / pk)
            s0 = max(0, int(l["film_start"] * SR))
            seg = a_wav[: max(0, n - s0)]
            voice[s0:s0 + len(seg)] += seg
            d0 = max(0, int((l["film_start"] - 0.15) * SR))
            d1 = min(n, int((l["film_end"] + 0.25) * SR))
            duck[d0:d1] = under

        if r.get("amb") and Path(r["amb"]).exists():
            a_amb = load_wav(r["amb"])
            need_len = int(r["dur"] * SR)
            a_amb = a_amb[:need_len]
            if len(a_amb) > 0:
                pk_amb = float(np.max(np.abs(a_amb)))
                if pk_amb > 1e-4:
                    target_amp = 0.35 if r["lines"] else 0.58
                    a_amb = a_amb * (target_amp / pk_amb)
                fade_len = max(1, int(0.15 * SR))
                idx_arr = np.arange(len(a_amb), dtype=np.float32)
                fade = np.minimum(1.0, np.minimum(idx_arr / fade_len, (len(a_amb) - idx_arr) / fade_len))
                s0 = int(r["start"] * SR)
                seg = (a_amb * fade)[: max(0, n - s0)]
                amb_[s0:s0 + len(seg)] += seg

    k_win = int(0.18 * SR)
    duck = np.convolve(duck, np.ones(k_win, np.float32) / k_win, mode="same")

    m_wav = load_wav(music_wav)
    if len(m_wav) < n:
        m_wav = np.tile(m_wav, (n // len(m_wav)) + 2)
    m_wav = m_wav[:n] * 0.32 * duck
    fade_out_len = int(0.8 * SR)
    end_idx = int(vtotal * SR)
    if end_idx > fade_out_len:
        m_wav[end_idx - fade_out_len:end_idx] *= np.linspace(1.0, 0.0, fade_out_len, dtype=np.float32)
        m_wav[end_idx:] = 0.0

    mix_arr = np.clip(voice + amb_ + m_wav, -0.98, 0.98)
    raw_wav_path = POST / "mix_raw.wav"
    with wave.open(str(raw_wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((mix_arr[:int(vtotal * SR)] * 32767.0).astype(np.int16).tobytes())

    target_lufs = -15.5
    gain = 0.0
    for _ in range(4):
        p = subprocess.run([
            "ffmpeg", "-i", str(raw_wav_path),
            "-af", f"volume={gain:.2f}dB,alimiter=limit=0.82:level=false:attack=2:release=80,ebur128=peak=true",
            "-f", "null", "-"
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        summ = p.stderr[p.stderr.rfind("Summary:"):]
        m = re.search(r"I:\s*(-?[\d.]+) LUFS", summ)
        if not m:
            break
        got = float(m.group(1))
        if abs(got - target_lufs) < 0.15:
            break
        gain += target_lufs - got
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_wav_path),
        "-af", f"volume={gain:.2f}dB,alimiter=limit=0.82:level=false:attack=2:release=80",
        "-ar", str(SR), str(POST / "mix.wav")
    ], check=True)

    def split_sub_clauses(role_name, text, t_start, t_end, max_len=20):
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
                    cut_p = max_len - len(role_name) - 1
                    clauses.append(f"{role_name}：{part[:cut_p]}")
                    clauses.append(part[cut_p:])
            else:
                if len(clauses[-1]) + len(part) <= max_len and (clauses[-1][-1] in "、：" or len(clauses[-1]) <= 10):
                    clauses[-1] += part
                elif len(part) <= max_len:
                    clauses.append(part)
                else:
                    clauses.append(part[:max_len])
                    clauses.append(part[max_len:])

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

    # 1. 產生 16:9 單行分段 ASS 字幕
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
    ev_v += f"Dialogue: 0,0:00:00.00,{ass_time(vtotal)},top_tag,,0,0,0,,★ 國立海科館・海洋未來式特展 ★\n"
    ev_v += f"Dialogue: 0,0:00:00.00,{ass_time(vtotal)},top_title,,0,0,0,,《海洋未來式：發燒的海洋母親》\n"
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

    # 3. 壓制 16:9 1080p
    (OUT / "cut").mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", "post/video.mp4", "-i", "post/mix.wav",
        "-vf", "subtitles=post/subs.ass",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest",
        "cut/film_1080p.mp4"
    ], cwd=str(OUT), check=True)

    # 4. 壓制 720p 手機預覽版
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(OUT / "cut" / "film_1080p.mp4"),
        "-vf", "scale=1280:720", "-c:v", "libx264", "-crf", "24", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k", str(OUT / "cut" / "film_720p_phone.mp4")
    ], check=True)

    # 5. 壓制 9:16 直式短影音版
    vf_vert = (
        "split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:4,eq=brightness=-0.38:saturation=0.75[bg2];"
        "[fg]scale=1080:608:flags=lanczos,"
        "pad=1080:620:0:6:color=0x38BDF8[fg2];"
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

    # 6. 執行自審
    env = {**os.environ, "AI_TOOLS": str(REPO / "tools")}
    r = subprocess.run(
        [sys.executable, str(HERE / "review.py"), str(OUT / "cut" / "film_1080p.mp4")],
        env=env, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    print(r.stdout)

    # 7. 複製至工作區根目錄交付
    ws_dir = Path(r"C:\antigravity\影片\海洋未來式")
    dest_16_9 = ws_dir / "海洋未來式_第1集_發燒的海洋母親_1080p成片.mp4"
    dest_720p = ws_dir / "海洋未來式_第1集_發燒的海洋母親_720p手機輕量版.mp4"
    dest_9_16 = ws_dir / "海洋未來式_第1集_發燒的海洋母親_9x16手機直式版.mp4"
    shutil.copy2(OUT / "cut" / "film_1080p.mp4", dest_16_9)
    shutil.copy2(OUT / "cut" / "film_720p_phone.mp4", dest_720p)
    shutil.copy2(OUT / "cut" / "film_vertical_1080x1920.mp4", dest_9_16)
    print(f"[fix_v3_cut] ✅ 16:9 1080p 成片已輸出至: {dest_16_9}")
    print(f"[fix_v3_cut] ✅ 9:16 手機直式版已輸出至: {dest_9_16}")


if __name__ == "__main__":
    main()
