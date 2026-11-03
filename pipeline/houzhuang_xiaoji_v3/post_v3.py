"""V3 Stage 6–8：後製剪輯、白閃轉場、混音（戲劇人聲＋SFX＋配樂 Ducking）、字幕燒錄與五遍成片審查。
解決 V1/V2 殘留的所有後製瑕疵：
1. 若某鏡台詞尾音接近鏡頭結尾，自動用 tpad=stop_mode=clone 補齊尾韻安全緩衝（0.35s），保證 0 句台詞被截斷。
2. 在 S03→S04（風暴雷擊降臨）與 S12→S13（黃金終極大招爆發）加入 0.15s 能量閃白過渡，消除突兀硬切與高反差視覺疲勞。
3. 混入 out/post/amb.json 的 8 軌動作與環境音效 + BS-RoFormer 伴奏配樂自動閃避（Ducking）。
4. 燒錄無負時間碼的 ASS 繁中角色專屬色彩字幕，並接上自製的 8.5s 後庄校慶 Puti-AI 片尾。"""
import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
POST = OUT / "post"
POST.mkdir(parents=True, exist_ok=True)
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


def main():
    cfg = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
    chars = cfg["chars"]
    shots = cfg["shots"]
    mix_cfg = cfg.get("mix", {})
    picks = json.loads((OUT / "voice_picks.json").read_text(encoding="utf-8"))
    amb_files = json.loads((POST / "amb.json").read_text(encoding="utf-8")) if (POST / "amb.json").exists() else {}

    # 1. 準備配樂
    music_wav = OUT / "music" / "s77" / "film_77_00001_(Instrumental)_model_bs_roformer_ep_317_sdr_12.wav"
    if not music_wav.exists():
        src_wav = REPO / "pipeline" / "houzhuang_xiaoji" / "out" / "music" / "s77" / "film_77_00001_(Instrumental)_model_bs_roformer_ep_317_sdr_12.wav"
        music_wav.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_wav, music_wav)
    (POST / "music_pick.json").write_text(
        json.dumps({"file": str(music_wav.resolve()).replace("\\", "/"), "vocal_ratio": 0.7457}, ensure_ascii=False, indent=1),
        encoding="utf-8"
    )

    # 2. 計算 EDL（確保每鏡時長 >= 台詞結束 + 0.35s 餘裕，絕不切台詞）
    line_shots = [s["id"] for s in shots if s.get("line")]
    t = 0.0
    edl_rows = []
    for s in shots:
        sid = s["id"]
        cpath = OUT / "h3" / sid / "clip.mp4"
        cd = dur(cpath)
        a = round(float(s.get("cut_in", 0.0)) * FPS) / FPS
        b = s.get("cut_out")
        lines = []
        min_needed = cd
        if s.get("line"):
            i = line_shots.index(sid)
            ln = s["line"]
            p = picks[str(i)]
            d_line = dur(p["file"])
            at = max(0.0, float(p.get("at", 0.0)))
            f_start = round(t + at - a, 3)
            f_end = round(f_start + d_line, 3)
            lines.append(dict(
                id=f"line{i}",
                who=ln["who"],
                text=ln["text"],
                file=p["file"],
                film_start=f_start,
                film_end=f_end
            ))
            tail = float(s.get("tail", mix_cfg.get("default_tail", 0.8)))
            min_needed = at + d_line + max(0.35, tail)

        b = max(cd, min_needed) if b in (None, "full") else max(float(b), min_needed)
        b = round(b * FPS) / FPS
        pad_sec = max(0.0, b - cd + 0.1)
        shot_dur = round(b - a, 3)
        edl_rows.append(dict(
            id=sid,
            start=round(t, 3),
            dur=shot_dur,
            src_in=a,
            src_out=round(b, 3),
            pad_sec=round(pad_sec, 3),
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
    print(f"[EDL] 正片 {t:.2f}s + 片尾 {ending_dur:.2f}s = {t + ending_dur:.2f}s")

    # 3. 逐鏡轉出 1080p 24fps 片段（含色彩微調、尾韻延長防切字、以及 S03->S04 / S12->S13 閃白轉場）
    seg_dir = POST / "seg"
    seg_dir.mkdir(parents=True, exist_ok=True)
    parts = []
    flash_out_shots = {"S03", "S12"}
    flash_in_shots = {"S04", "S13"}

    for r in edl_rows:
        sid = r["id"]
        src = OUT / "h3" / sid / "clip.mp4"
        p = seg_dir / f"{sid}.mp4"
        n_frames = round(r["dur"] * FPS)
        vf = ["scale=1920:1080:flags=lanczos", "unsharp=3:3:0.35:3:3:0.0", "fps=24"]
        if r["pad_sec"] > 0:
            vf.append(f"tpad=stop_mode=clone:stop_duration={r['pad_sec'] + 0.2:.2f}")
        if sid in flash_in_shots:
            vf.append("fade=t=in:st=0:d=0.14:color=white")
        if sid in flash_out_shots:
            st_fade = max(0.0, r["dur"] - 0.14)
            vf.append(f"fade=t=out:st={st_fade:.3f}:d=0.14:color=white")
        vf.append("format=yuv420p")

        if not p.exists() or p.stat().st_mtime < src.stat().st_mtime:
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-ss", f"{r['src_in']:.3f}", "-i", str(src),
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

    # 4. 混音：戲劇人聲 + 動作音效 + 配樂 Ducking
    vtotal = dur(POST / "video.mp4")
    n = int(vtotal * SR) + SR
    voice = np.zeros(n, np.float32)
    amb_ = np.zeros(n, np.float32)
    duck = np.ones(n, np.float32)
    under = float(mix_cfg.get("music_under_lines", 0.24))

    for r in edl_rows:
        for l in r["lines"]:
            a_wav = load_wav(l["file"])
            # 峰值正規化每句人聲，確保角色聲音清晰飽滿
            pk = float(np.max(np.abs(a_wav))) if len(a_wav) else 0.0
            if pk > 1e-4:
                a_wav = a_wav * (0.72 / pk)
            s0 = max(0, int(l["film_start"] * SR))
            seg = a_wav[: max(0, n - s0)]
            voice[s0:s0 + len(seg)] += seg
            d0 = max(0, int((l["film_start"] - 0.2) * SR))
            d1 = min(n, int((l["film_end"] + 0.3) * SR))
            duck[d0:d1] = under

        if r.get("amb") and Path(r["amb"]).exists():
            a_amb = load_wav(r["amb"])
            need_len = int(r["dur"] * SR)
            a_amb = a_amb[:need_len]
            if len(a_amb) > 0:
                fade_len = max(1, int(0.15 * SR))
                idx_arr = np.arange(len(a_amb), dtype=np.float32)
                fade = np.minimum(1.0, np.minimum(idx_arr / fade_len, (len(a_amb) - idx_arr) / fade_len))
                s0 = int(r["start"] * SR)
                seg = (a_amb * fade * 0.65)[: max(0, n - s0)]
                amb_[s0:s0 + len(seg)] += seg

    # 柔和曲線化 ducking
    k_win = int(0.18 * SR)
    duck = np.convolve(duck, np.ones(k_win, np.float32) / k_win, mode="same")

    m_wav = load_wav(music_wav)
    if len(m_wav) < n:
        reps = (n // len(m_wav)) + 2
        m_wav = np.tile(m_wav, reps)
    m_wav = m_wav[:n] * 0.38 * duck
    # 結尾最後 0.8s 配樂淡出
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

    # 精準迭代校準響度至 -15.5 LUFS（符合 review.py -16.5 ~ -14.5 LUFS 規範）
    target_lufs = -15.5
    gain = 0.0
    for _ in range(4):
        p = subprocess.run([
            "ffmpeg", "-i", str(raw_wav_path),
            "-af", f"volume={gain:.2f}dB,alimiter=limit=0.82:level=false:attack=2:release=80,ebur128=peak=true",
            "-f", "null", "-"
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        summ = p.stderr[p.stderr.rfind("Summary:"):]
        m = __import__("re").search(r"I:\s*(-?[\d.]+) LUFS", summ)
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

    # 5. 產生 ASS 字幕並燒錄成片（嚴格限制字幕於該鏡頭 [start+0.10, end-0.10] 內，絕不跨鏡殘留）
    hdr = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    )
    for k, c in chars.items():
        hdr += f"Style: {k},Microsoft JhengHei,58,{c.get('sub_color', '&H00FFFFFF')},&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,4,1,2,60,60,70,1\n"
    ev = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    caps = sorted([(l, r) for r in edl_rows for l in r["lines"]], key=lambda x: x[0]["film_start"])
    for i, (l, r) in enumerate(caps):
        a = max(r["start"] + 0.12, l["film_start"])
        b = max(a + 0.5, l["film_end"] + 0.35)
        if i + 1 < len(caps):
            b = min(b, caps[i + 1][0]["film_start"] - 0.12)
        b = min(b, r["start"] + r["dur"] - 0.10)
        ev += f"Dialogue: 0,{ass_time(a)},{ass_time(b)},{l['who']},,0,0,0,,{chars[l['who']]['name']}：{l['text']}\n"

    (POST / "subs.ass").write_text(hdr + ev, encoding="utf-8")
    (OUT / "cut").mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", "post/video.mp4", "-i", "post/mix.wav",
        "-vf", "subtitles=post/subs.ass",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest",
        "cut/film_1080p.mp4"
    ], cwd=str(OUT), check=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(OUT / "cut" / "film_1080p.mp4"),
        "-vf", "scale=1280:720", "-c:v", "libx264", "-crf", "24",
        "-c:a", "aac", "-b:a", "128k", str(OUT / "cut" / "film_720p_phone.mp4")
    ], check=True)

    # 6. 執行 review.py
    env = {**os.environ, "AI_TOOLS": str(REPO / "tools")}
    r = subprocess.run([sys.executable, str(HERE / "review.py"), str(OUT / "cut" / "film_1080p.mp4")], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout)

    # 7. 複製到使用者專案根目錄
    dest = Path(r"C:\antigravity\影片\小吉的逆襲\後庄守護者_小吉的逆襲_v3_1080p成片.mp4")
    shutil.copy2(OUT / "cut" / "film_1080p.mp4", dest)
    print(f"[post_v3] ✅ 完成！已輸出至: {dest}")


if __name__ == "__main__":
    main()
