"""修復版 (Match Cut 跳接法)：
將 S14 切除中間 180 度鬼畜轉身，重組為：
S14A (0.00s~1.75s, 正面衝刺) + S14B (3.35s~6.50s, 遠景背影奔向光門)
輸出獨立成片，絕不覆蓋原檔！
"""
import json
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(r"C:\antigravity\影片\shanshiba-workflow-colab\pipeline\ocean_future_ep01")
OUT = HERE / "out"
POST = OUT / "post_fix"
POST.mkdir(parents=True, exist_ok=True)
SR, FPS = 48000, 24

from reburn_single_line_subs import split_sub_clauses, ass_time, dur

def load_wav(p):
    r = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(p), "-ar", str(SR), "-ac", "1", "-f", "f32le", "-"],
        capture_output=True
    )
    return np.frombuffer(r.stdout, np.float32).copy()

def main():
    cfg = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
    chars = cfg["chars"]
    orig_edl = json.loads((OUT / "post" / "edl.json").read_text(encoding="utf-8"))
    orig_rows = orig_edl["shots"]
    mix_cfg = cfg.get("mix", {})
    amb_files = json.loads((OUT / "post" / "amb.json").read_text(encoding="utf-8")) if (OUT / "post" / "amb.json").exists() else {}

    # 1. 重構 EDL：將 S14 拆為 S14A (1.75s) 與 S14B (3.15s)
    edl_rows = []
    t = 0.0
    for r in orig_rows:
        if r["id"] != "S14":
            r_new = dict(r)
            r_new["start"] = round(t, 3)
            # update lines start
            if r_new.get("lines"):
                for l in r_new["lines"]:
                    l_dur = l["film_end"] - l["film_start"]
                    l["film_start"] = round(t + (l["film_start"] - r["start"]), 3)
                    l["film_end"] = round(l["film_start"] + l_dur, 3)
            edl_rows.append(r_new)
            t += r["dur"]
        else:
            # 取得 S14 台詞
            l_orig = r["lines"][0]
            # S14A (正面衝刺)
            dur_14a = 1.75
            edl_rows.append(dict(
                id="S14A",
                orig_id="S14",
                start=round(t, 3),
                dur=dur_14a,
                raw_dur=dur_14a,
                stretch=1.0,
                src_in=0.0,
                src_out=1.75,
                lines=[dict(
                    id="line13_a",
                    who="xiaoji",
                    text="好！我一定要找出拯救大海的辦法！",
                    file=l_orig["file"],
                    film_start=round(t + 0.55, 3),
                    film_end=round(t + dur_14a, 3)
                )],
                amb=None
            ))
            t += dur_14a

            # S14B (遠景背影)
            dur_14b = 3.25
            edl_rows.append(dict(
                id="S14B",
                orig_id="S14",
                start=round(t, 3),
                dur=dur_14b,
                raw_dur=dur_14b,
                stretch=1.0,
                src_in=3.35,
                src_out=6.60,
                lines=[dict(
                    id="line13_b",
                    who="xiaoji",
                    text="黃老師等等我！",
                    file=l_orig["file"],
                    film_start=round(t + 0.15, 3),
                    film_end=round(t + 1.85, 3)
                )],
                amb=None
            ))
            t += dur_14b

    ending_mp4 = OUT / "ending" / "ending.mp4"
    ending_dur = dur(ending_mp4) if ending_mp4.exists() else 0.0
    vtotal = round(t + ending_dur, 3)
    print(f"🎬 [Match Cut EDL] 正片 {t:.2f}s + 片尾 {ending_dur:.2f}s = 總片長 {vtotal:.2f}s")

    # 2. 剪出 S14A 與 S14B 鏡頭片段
    seg_dir = POST / "seg"
    seg_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    flash_out_shots = {"S01", "S06", "S09", "S11"}
    flash_in_shots = {"S02", "S07", "S10", "S12"}

    for r in edl_rows:
        sid = r["id"]
        orig_sid = r.get("orig_id", sid)
        src = OUT / "h3" / orig_sid / "clip.mp4"
        p = seg_dir / f"{sid}.mp4"
        n_frames = round(r["dur"] * FPS)
        vf = [
            f"trim=start={r['src_in']:.3f}:duration={r['raw_dur']:.3f}",
            "setpts=PTS-STARTPTS",
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

    list_txt = POST / "list.txt"
    list_txt.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    raw_video = POST / "video.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_txt),
        "-c", "copy", str(raw_video)
    ], check=True)

    # 3. 混音音訊
    voice_picks = json.loads((OUT / "voice_picks.json").read_text(encoding="utf-8"))
    music_wav = OUT / "music" / "bgm_puti.wav"
    n_samples = int(vtotal * SR) + SR
    voice = np.zeros(n_samples, np.float32)
    amb_ = np.zeros(n_samples, np.float32)
    duck = np.ones(n_samples, np.float32)
    under = float(mix_cfg.get("music_under_lines", 0.22))

    for r in edl_rows:
        for l in r["lines"]:
            if r["id"] not in ("S14A", "S14B"):
                a_wav = load_wav(l["file"])
                pk = float(np.max(np.abs(a_wav))) if len(a_wav) else 0.0
                if pk > 1e-4:
                    a_wav = a_wav * (0.85 / pk)
                s0 = max(0, int(l["film_start"] * SR))
                seg = a_wav[: max(0, n_samples - s0)]
                voice[s0:s0 + len(seg)] += seg
                d0 = max(0, int((l["film_start"] - 0.15) * SR))
                d1 = min(n_samples, int((l["film_end"] + 0.25) * SR))
                duck[d0:d1] = under
            elif r["id"] == "S14A":
                # S14 前半句語音 (0.0s ~ 3.5s)
                cpath = OUT / "h3" / "S14" / "clip.mp4"
                tmp_a = POST / "s14a_voice.wav"
                subprocess.run([
                    "ffmpeg", "-y", "-loglevel", "error", "-i", str(cpath), "-vn",
                    "-af", "atrim=start=0.72:end=3.50,asetpts=PTS-STARTPTS,highpass=f=85,equalizer=f=3500:t=q:w=1.0:g=4.5,treble=g=6.5:f=6000",
                    "-ar", str(SR), "-ac", "1", str(tmp_a)
                ], check=True)
                a_wav = load_wav(tmp_a)
                pk = float(np.max(np.abs(a_wav))) if len(a_wav) else 0.0
                if pk > 1e-4: a_wav = a_wav * (0.85 / pk)
                s0 = max(0, int(l["film_start"] * SR))
                voice[s0:s0 + len(a_wav)] += a_wav
                duck[s0:s0 + len(a_wav)] = under
            elif r["id"] == "S14B":
                # S14 後半句語音 (3.8s ~ 5.72s)
                cpath = OUT / "h3" / "S14" / "clip.mp4"
                tmp_b = POST / "s14b_voice.wav"
                subprocess.run([
                    "ffmpeg", "-y", "-loglevel", "error", "-i", str(cpath), "-vn",
                    "-af", "atrim=start=3.85:end=5.72,asetpts=PTS-STARTPTS,highpass=f=85,equalizer=f=3500:t=q:w=1.0:g=4.5,treble=g=6.5:f=6000",
                    "-ar", str(SR), "-ac", "1", str(tmp_b)
                ], check=True)
                a_wav = load_wav(tmp_b)
                pk = float(np.max(np.abs(a_wav))) if len(a_wav) else 0.0
                if pk > 1e-4: a_wav = a_wav * (0.85 / pk)
                s0 = max(0, int(l["film_start"] * SR))
                voice[s0:s0 + len(a_wav)] += a_wav
                duck[s0:s0 + len(a_wav)] = under

        orig_sid = r.get("orig_id", r["id"])
        if amb_files.get(orig_sid) and Path(amb_files[orig_sid]).exists():
            a_amb = load_wav(amb_files[orig_sid])
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
                seg = (a_amb * fade)[: max(0, n_samples - s0)]
                amb_[s0:s0 + len(seg)] += seg

    k_win = int(0.18 * SR)
    duck = np.convolve(duck, np.ones(k_win, np.float32) / k_win, mode="same")
    m_wav = load_wav(music_wav)
    if len(m_wav) < n_samples:
        m_wav = np.tile(m_wav, (n_samples // len(m_wav)) + 2)
    m_wav = m_wav[:n_samples] * 0.32 * duck
    fade_out_len = int(0.8 * SR)
    end_idx = int(vtotal * SR)
    if end_idx > fade_out_len:
        m_wav[end_idx - fade_out_len:end_idx] *= np.linspace(1.0, 0.0, fade_out_len, dtype=np.float32)
        m_wav[end_idx:] = 0.0

    mix_arr = np.clip(voice + amb_ + m_wav, -0.98, 0.98)
    raw_wav_path = POST / "mix_raw.wav"
    with wave.open(str(raw_wav_path), "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
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
        if not m: break
        got = float(m.group(1))
        if abs(got - target_lufs) < 0.15: break
        gain += target_lufs - got

    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(raw_wav_path),
        "-af", f"volume={gain:.2f}dB,alimiter=limit=0.82:level=false:attack=2:release=80",
        "-ar", str(SR), str(POST / "mix.wav")
    ], check=True)

    # 4. 生成 16:9 ASS 字幕
    hdr = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 2\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    )
    for k, c in chars.items():
        hdr += f"Style: {k},Microsoft JhengHei,54,{c.get('sub_color', '&H00FFFFFF')},&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,4,1,2,80,80,54,1\n"
    ev = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"

    for r in edl_rows:
        for l in r["lines"]:
            a = max(r["start"] + 0.05, l["film_start"])
            b = min(r["start"] + r["dur"] - 0.05, l["film_end"])
            for seg_a, seg_b, seg_txt in split_sub_clauses(chars[l["who"]]["name"], l["text"], a, b, max_len=20):
                ev += f"Dialogue: 0,{ass_time(seg_a)},{ass_time(seg_b)},{l['who']},,0,0,0,,{seg_txt}\n"

    (POST / "subs.ass").write_text(hdr + ev, encoding="utf-8")

    # 5. 壓制 16:9 1080p 成片（修復版）
    out_1080p = POST / "film_1080p_fixed.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(raw_video), "-i", str(POST / "mix.wav"),
        "-vf", "subtitles=post_fix/subs.ass",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest",
        str(out_1080p)
    ], cwd=str(OUT), check=True)

    # 6. 輸出滿版 9:16 智慧導播版（修復版）
    # 對 S14A 與 S14B 分別執行虛擬導播運鏡
    vseg_dir = POST / "seg_vert"
    vseg_dir.mkdir(parents=True, exist_ok=True)
    from make_vertical_panscan import render_panscan_shot, CAMERA_SCRIPT
    vparts = []
    for r in edl_rows:
        sid = r["id"]
        src_seg = seg_dir / f"{sid}.mp4"
        dst_seg = vseg_dir / f"{sid}.mp4"
        if sid == "S14A":
            kfs = [(0.0, 0.45, 0.50, 0.90), (1.0, 0.46, 0.48, 0.85)]  # 正面衝刺特寫放大
        elif sid == "S14B":
            kfs = [(0.0, 0.50, 0.52, 0.92), (1.0, 0.50, 0.46, 0.98)]  # 遠景光門背影拉開
        else:
            kfs = CAMERA_SCRIPT.get(sid, [(0.0, 0.5, 0.5, 1.0), (1.0, 0.5, 0.5, 1.0)])
        render_panscan_shot(src_seg, dst_seg, kfs)
        vparts.append(dst_seg)

    if ending_mp4.exists():
        dst_end = vseg_dir / "ending_vert.mp4"
        render_panscan_shot(ending_mp4, dst_end, [(0.0, 0.50, 0.50, 1.00), (1.0, 0.50, 0.50, 0.94)])
        vparts.append(dst_end)

    list_v = POST / "list_vert.txt"
    list_v.write_text("".join(f"file '{p.as_posix()}'\n" for p in vparts), encoding="utf-8")
    raw_vert_mp4 = POST / "video_vert.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_v),
        "-c", "copy", str(raw_vert_mp4)
    ], check=True)

    # 9:16 ASS 字幕
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
    ev_v += f"Dialogue: 0,0:00:00.00,{ass_time(vtotal)},top_badge,,0,0,0,,★ 國立海科館・海洋未來式特展 ★\n"
    ev_v += f"Dialogue: 0,0:00:00.00,{ass_time(vtotal)},bot_credit,,0,0,0,,屏東縣後庄國小黃朝榮老師 (Puti-AI) 作品｜免費分享・歡迎推廣\n"

    for r in edl_rows:
        for l in r["lines"]:
            a = max(r["start"] + 0.05, l["film_start"])
            b = min(r["start"] + r["dur"] - 0.05, l["film_end"])
            for seg_a, seg_b, seg_txt in split_sub_clauses(chars[l["who"]]["name"], l["text"], a, b, max_len=20):
                ev_v += f"Dialogue: 1,{ass_time(seg_a)},{ass_time(seg_b)},{l['who']},,0,0,0,,{seg_txt}\n"

    (POST / "subs_vert.ass").write_text(hdr_v + ev_v, encoding="utf-8")

    out_vert = POST / "film_vert_fixed.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(raw_vert_mp4), "-i", str(POST / "mix.wav"),
        "-vf", "subtitles=post_fix/subs_vert.ass",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest",
        str(out_vert)
    ], cwd=str(OUT), check=True)

    # 7. 交付至工作區，名稱後綴【_修復版】，絕不覆蓋原檔！
    ws_dir = Path(r"C:\antigravity\影片\海洋未來式")
    dest_16_9 = ws_dir / "海洋未來式_第1集_發燒的海洋母親_1080p成片_修復版.mp4"
    dest_vert = ws_dir / "海洋未來式_第1集_發燒的海洋母親_9x16滿版導播版_修復版.mp4"

    shutil.copy2(out_1080p, dest_16_9)
    shutil.copy2(out_vert, dest_vert)
    print(f"🎉 [修復版交付] 16:9 已輸出至: {dest_16_9}")
    print(f"🎉 [修復版交付] 9:16 滿版已輸出至: {dest_vert}")

if __name__ == "__main__":
    main()
