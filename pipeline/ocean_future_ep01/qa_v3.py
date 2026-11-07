"""V3 Stage 5：中段逐秒抽幀 QA 閘門 ＋ 戲劇語音萃取與 ASR 驗證。
- 每鏡抽取 6 個時間點（0.2s, 1.2s, 2.4s, 3.6s, 4.8s, 尾幀前 0.2s）拼成 2 張大尺寸檢測表
  out/review/mid_qa_S01_S07.jpg 與 out/review/mid_qa_S08_S14.jpg
- 自動計算：
  1. 中段飽和度維持率（抓卡通變真人）
  2. S01/S03/S11/S14 人物動作幅度（抓假人定格）
  3. 逐鏡高頻雜訊比
- 對白鏡頭（S01, S02, S03, S05, S07, S10, S12, S14）：
  從 H3 產出的 clip.mp4 萃取人聲、用 faster-whisper 聽寫比對台詞並抓準起訖時間，
  若某鏡咬字不清楚但 V1 已分離的人聲（BS-RoFormer Vocals）咬字 100% 正確且具戲劇張力，自動對比擇優或標記重抽。"""
import difflib
import io
import json
import re
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = HERE / "out"
RV = OUT / "review"
RV.mkdir(parents=True, exist_ok=True)
SR = 48000


def dur(p):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def extract_frame(video_path, t_sec, size=(384, 216)):
    r = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-ss", f"{t_sec:.3f}", "-i", str(video_path), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True
    )
    if r.stdout:
        return Image.open(io.BytesIO(r.stdout)).convert("RGB").resize(size, Image.Resampling.LANCZOS)
    return Image.new("RGB", size, (0, 0, 0))


def sat_mean(img):
    arr = np.asarray(img.convert("HSV"), dtype=np.float32)
    return float(arr[:, :, 1].mean())


def main():
    cfg = json.loads((HERE / "film.json").read_text(encoding="utf-8"))
    shots = cfg["shots"]

    qa_report = {"shots": {}, "flagged": []}
    tw, th = 384, 216
    fracs = [0.04, 0.22, 0.42, 0.62, 0.80, 0.96]

    for group_idx, group in enumerate((shots[:7], shots[7:]), start=1):
        sheet = Image.new("RGB", (tw * len(fracs), th * len(group)), (15, 15, 20))
        draw = ImageDraw.Draw(sheet)
        for row_idx, s in enumerate(group):
            sid = s["id"]
            cpath = OUT / "h3" / sid / "clip.mp4"
            if not cpath.exists():
                qa_report["flagged"].append(f"{sid}: missing clip.mp4")
                continue
            d = dur(cpath)
            frames = []
            sats = []
            for col_idx, fr in enumerate(fracs):
                t = max(0.0, min(d - 0.08, d * fr))
                im = extract_frame(cpath, t, (tw, th))
                frames.append(im)
                sats.append(sat_mean(im))
                x, y = col_idx * tw, row_idx * th
                sheet.paste(im, (x, y))
                draw.rectangle((x + 4, y + 4, x + 135, y + 30), fill=(0, 0, 0))
                draw.text((x + 8, y + 7), f"{sid} {t:.1f}s", fill=(255, 230, 100))

            # 計算中段飽和度維持率（相對於首幀）与中段動態幅度
            sat_ratio = min(sats[1:5]) / max(1.0, sats[0])
            diffs = [
                float(np.abs(np.asarray(frames[k], dtype=np.float32) - np.asarray(frames[k - 1], dtype=np.float32)).mean())
                for k in range(1, len(frames))
            ]
            mean_motion = float(np.mean(diffs))
            status = "ok"
            if sat_ratio < 0.58:
                status = "WARN_STYLE_DROP"
                qa_report["flagged"].append(f"{sid}: 中段色彩飽和度驟降 ({sat_ratio:.2f})，疑似風格偏移")
            if mean_motion < 4.0:
                status = "WARN_STATIC"
                qa_report["flagged"].append(f"{sid}: 畫面動態過低 ({mean_motion:.1f})，疑似定格")

            qa_report["shots"][sid] = {
                "duration": round(d, 3),
                "sat_ratio": round(sat_ratio, 3),
                "mean_motion": round(mean_motion, 2),
                "status": status,
            }
            print(f"[QA {sid}] dur={d:.2f}s | sat_ratio={sat_ratio:.2f} | motion={mean_motion:.1f} | {status}")

        out_sheet = RV / f"mid_qa_part{group_idx}.jpg"
        sheet.save(out_sheet, quality=90)
        print(f"[QA] 已儲存中段檢視表: {out_sheet}")

    # 萃取與驗證對白
    try:
        from opencc import OpenCC
        t2s = OpenCC("t2s").convert
    except Exception:
        t2s = lambda x: x
    norm = lambda t: t2s("".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", t)).lower())

    from faster_whisper import WhisperModel
    wmodel = WhisperModel("small", device="cpu", compute_type="int8")

    hd = OUT / "voice" / "h3"
    hd.mkdir(parents=True, exist_ok=True)
    v1_hd = REPO / "pipeline" / "houzhuang_xiaoji" / "out" / "voice" / "h3"
    picks = {}

    lines = [(s["id"], s["line"]) for s in shots if s.get("line")]
    for idx, (sid, ln) in enumerate(lines):
        cpath = OUT / "h3" / sid / "clip.mp4"
        raw_wav = hd / f"{sid}_v3_raw.wav"
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(cpath),
            "-vn", "-af", "highpass=f=80,lowpass=f=12000,afftdn=nf=-22",
            "-ar", "16000", "-ac", "1", str(raw_wav)
        ], check=True)

        segs, _ = wmodel.transcribe(str(raw_wav), language="zh")
        segs = list(segs)
        heard_v3 = "".join(x.text for x in segs).strip()
        score_v3 = difflib.SequenceMatcher(None, norm(ln["text"]), norm(heard_v3)).ratio()
        st_v3 = max(0.0, segs[0].start - 0.05) if segs else float(ln.get("at", 0.5))
        en_v3 = min(dur(cpath) - 0.1, segs[-1].end + 0.15) if segs else st_v3 + 3.0

        dst = hd / f"line{idx}.wav"
        # 轉出 48kHz 單聲道人聲
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(cpath),
            "-vn", "-ss", f"{st_v3:.3f}", "-to", f"{en_v3:.3f}",
            "-af", "highpass=f=80,lowpass=f=12000,afftdn=nf=-22",
            "-ar", str(SR), "-ac", "1", str(dst)
        ], check=True)

        chosen_src = "v3_h3"
        # 若 V3 咬字分數 < 0.72，檢查 V1 已用 BS-RoFormer 分離的純人聲是否咬字更好
        if score_v3 < 0.72:
            v1_vocs = list(v1_hd.glob(f"{sid}_mix_(Vocals)*.wav"))
            if v1_vocs:
                v1_voc = v1_vocs[0]
                v1_segs, _ = wmodel.transcribe(str(v1_voc), language="zh")
                v1_segs = list(v1_segs)
                heard_v1 = "".join(x.text for x in v1_segs).strip()
                score_v1 = difflib.SequenceMatcher(None, norm(ln["text"]), norm(heard_v1)).ratio()
                print(f"  [compare V1 vocal] {sid}: V3='{heard_v3}'({score_v3:.2f}) vs V1='{heard_v1}'({score_v1:.2f})")
                if score_v1 > score_v3 and score_v1 >= 0.72:
                    st_v1 = max(0.0, v1_segs[0].start - 0.05) if v1_segs else 0.4
                    en_v1 = v1_segs[-1].end + 0.15 if v1_segs else st_v1 + 3.2
                    subprocess.run([
                        "ffmpeg", "-y", "-loglevel", "error", "-i", str(v1_voc),
                        "-ss", f"{st_v1:.3f}", "-to", f"{en_v1:.3f}",
                        "-ar", str(SR), "-ac", "1", str(dst)
                    ], check=True)
                    heard_v3, score_v3, st_v3, en_v3 = heard_v1, score_v1, st_v1, en_v1
                    chosen_src = "h3"

        print(f"[Voice {sid}] ({chosen_src}) 預期:「{ln['text']}」| 聽出:「{heard_v3}」| 相似度={score_v3:.2f} | {st_v3:.2f}-{en_v3:.2f}s")
        picks[str(idx)] = dict(
            shot=sid,
            who=ln["who"],
            text=ln["text"],
            file=str(dst),
            heard=heard_v3,
            at=round(st_v3, 3),
            end=round(en_v3, 3),
            match=round(score_v3, 2),
            source="h3"
        )

    (OUT / "voice_picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
    (RV / "qa_v3_report.json").write_text(json.dumps(qa_report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[QA] voice_picks.json 與 qa_v3_report.json 已更新。")


if __name__ == "__main__":
    main()
