"""修復 V3 自審抓出的 4 大實質問題：
1. 【台詞腰斬修復】：S03、S10、S12 原本因 Whisper 無 word_timestamps 將結尾量化在 4.15s/5.15s，
   導致「核心永遠滿格」(4.20-5.70s)、「力量還在暴漲」(5.16-6.62s)、「把力量借給我」(5.16-6.20s) 後半句被切掉（有嘴型無聲音）。
   現改用完整未截斷的鏡頭人聲軌（精準對齊 word_timestamps 起訖），100% 保留整句台詞與嘴型同步。
2. 【尾幀停滯與懸空修剪 (Tight Edit)】：
   - S01 裁在 4.6s（比讚敬禮完成即切，砍掉後面 2s 乾等）
   - S02 裁在 5.2s（變形推土機完成即切，砍掉後面 1.4s 原地停滯）
   - S03 取 1.2s~6.2s（涵蓋投瓶、揮手與完整 2.50~5.70s 台詞）
   - S04 取 1.6s~5.4s（跳過 0.7s 預閃，直接呈現主雷擊與爆炸）
   - S06 取 2.2s~5.8s（跳過前 2 秒比例過大的前景便當盒，保留黑泥吸入核心）
   - S07 取 0.0s~4.8s（講完台詞並架好推土鏟盾牌即切，砍掉尾段停滯）
   - S08 取 0.0s~4.3s（撞擊火花最高潮切走，避免尾段慢動作停滯）
   - S09 取 0.0s~4.1s（推土機被拋飛升空瞬間切走，消除 4.2s~5.8s 推土機違反重力懸停在左上角的穿幫）
   - S10 取 2.0s~7.1s（小吉撐起身體＋完整講完 3.44s~6.62s 台詞）
   - S11 取 0.0s~5.4s（師生分類回收＋金光升空）
   - S12 取 1.2s~6.8s（金光匯聚＋完整講完 2.18s~6.20s 台詞＋舉拳衝天）
   - S13 取 0.4s~5.6s（大黑裂解化為白光散入晴空）
   - S14 取 0.0s~4.5s（講完校慶見＋全體舉手歡呼最高點直接切入片尾，消除最後 2 秒舉手定格）
3. 【SFX 音效峰值正規化】：解決 S06、S11、S13 音效僅 -25 dBFS 過小的問題。
"""
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


# 依逐幀與逐字時間戳精確標定的剪輯點 (src_in, src_out) 與台詞在原片中的真實起訖 (spk_start, spk_end)
TIGHT_TRIM = {
    "S01": dict(cin=0.0, cout=4.6, spk=(0.00, 3.00)),
    "S02": dict(cin=0.0, cout=5.3, spk=(0.00, 5.00)),
    "S03": dict(cin=1.2, cout=6.2, spk=(2.45, 5.85)),
    "S04": dict(cin=1.6, cout=5.4, spk=None),
    "S05": dict(cin=0.0, cout=5.6, spk=(0.00, 4.85), use_v1_vocal=True),
    "S06": dict(cin=2.5, cout=5.8, spk=None),
    "S07": dict(cin=0.0, cout=4.8, spk=(0.00, 4.30)),
    "S08": dict(cin=0.0, cout=4.3, spk=None),
    "S09": dict(cin=0.0, cout=4.1, spk=None),
    "S10": dict(cin=2.0, cout=7.1, spk=(3.35, 6.75)),
    "S11": dict(cin=0.0, cout=5.4, spk=None),
    "S12": dict(cin=1.2, cout=6.8, spk=(2.10, 6.35)),
    "S13": dict(cin=0.4, cout=5.6, spk=None),
    "S14": dict(cin=0.0, cout=4.5, spk=(0.00, 3.55)),
}


def main():
    cfg = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
    chars = cfg["chars"]
    shots = cfg["shots"]
    mix_cfg = cfg.get("mix", {})
    amb_files = json.loads((POST / "amb.json").read_text(encoding="utf-8")) if (POST / "amb.json").exists() else {}

    # 1. 重新從原片完整切出未腰斬的 8 句台詞音檔
    hd = OUT / "voice" / "h3"
    hd.mkdir(parents=True, exist_ok=True)
    v1_hd = REPO / "pipeline" / "houzhuang_xiaoji" / "out" / "voice" / "h3"
    picks = {}
    line_shots = [s["id"] for s in shots if s.get("line")]

    for idx, sid in enumerate(line_shots):
        s = next(x for x in shots if x["id"] == sid)
        ln = s["line"]
        tr = TIGHT_TRIM[sid]
        sp0, sp1 = tr["spk"]
        dst = hd / f"line{idx}_full.wav"

        if tr.get("use_v1_vocal"):
            v1_voc = next(v1_hd.glob(f"{sid}_mix_(Vocals)*.wav"))
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(v1_voc),
                "-ss", f"{sp0:.3f}", "-to", f"{sp1:.3f}",
                "-ar", str(SR), "-ac", "1", str(dst)
            ], check=True)
        else:
            cpath = OUT / "h3" / sid / "clip.mp4"
            subprocess.run([
                "ffmpeg", "-y", "-loglevel", "error", "-i", str(cpath),
                "-vn", "-ss", f"{sp0:.3f}", "-to", f"{sp1:.3f}",
                "-af", "highpass=f=85,lowpass=f=12000,afftdn=nf=-20",
                "-ar", str(SR), "-ac", "1", str(dst)
            ], check=True)

        # 相對於修剪後鏡頭起點 cin 的開口時間
        rel_at = round(max(0.05, sp0 - tr["cin"]), 3)
        d_wav = dur(dst)
        picks[str(idx)] = dict(
            shot=sid,
            who=ln["who"],
            text=ln["text"],
            file=str(dst),
            at=rel_at,
            end=round(rel_at + d_wav, 3),
            source="h3"
        )
        print(f"[Line {sid}] 完整音軌 dur={d_wav:.2f}s | 鏡內位置={rel_at:.2f}s~{rel_at+d_wav:.2f}s / 鏡長={tr['cout']-tr['cin']:.2f}s")

    (OUT / "voice_picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")

    # 2. 建立精準 EDL
    t = 0.0
    edl_rows = []
    for s in shots:
        sid = s["id"]
        tr = TIGHT_TRIM[sid]
        a = round(tr["cin"] * FPS) / FPS
        b = round(tr["cout"] * FPS) / FPS
        shot_dur = round(b - a, 3)
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
    print(f"[EDL Tight] 正片 {t:.2f}s + 片尾 {ending_dur:.2f}s = {t + ending_dur:.2f}s")

    # 3. 重新切出 14 個緊湊無停滯的 1080p 24fps 鏡頭片段
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
        vf = [
            f"trim=start={r['src_in']:.3f}:duration={r['dur']:.3f}",
            "setpts=PTS-STARTPTS",
            "scale=1920:1080:flags=lanczos",
            "unsharp=3:3:0.35:3:3:0.0",
            "fps=24",
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

    # 4. 混音：完整人聲 + 峰值正規化 SFX + 配樂 Ducking
    music_wav = OUT / "music" / "s77" / "film_77_00001_(Instrumental)_model_bs_roformer_ep_317_sdr_12.wav"
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
                a_wav = a_wav * (0.78 / pk)
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
                # 峰值正規化 SFX，解決 S06/S11/S13 音效過小的問題
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
    m_wav = m_wav[:n] * 0.36 * duck
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

    # 5. 產生與實際開口時間 100% 同步的 ASS 字幕
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
        a = max(r["start"] + 0.12, l["film_start"] - 0.05)
        b = max(a + 0.5, l["film_end"] + 0.25)
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

    env = {**os.environ, "AI_TOOLS": str(REPO / "tools")}
    r = subprocess.run([sys.executable, str(HERE / "review.py"), str(OUT / "cut" / "film_1080p.mp4")], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout)

    dest = Path(r"C:\antigravity\影片\小吉的逆襲\後庄守護者_小吉的逆襲_v3_1080p成片.mp4")
    shutil.copy2(OUT / "cut" / "film_1080p.mp4", dest)
    print(f"[fix_v3_cut] ✅ 完整修復版已輸出至: {dest}")


if __name__ == "__main__":
    main()
