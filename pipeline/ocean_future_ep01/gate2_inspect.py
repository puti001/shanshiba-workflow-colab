"""Gate 2: 14 鏡 8 格高密度抽幀檢視表 + Whisper word_timestamps 逐字聽寫驗證"""
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw
from faster_whisper import WhisperModel

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
REV = OUT / "review"
REV.mkdir(parents=True, exist_ok=True)
cfg = json.loads((HERE / "film.json").read_text(encoding="utf-8"))


def get_dur(p):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def main():
    pcts = [0.02, 0.15, 0.29, 0.43, 0.57, 0.71, 0.85, 0.97]
    tw, th = 320, 180
    for part, sids in [(1, [f"S{i:02d}" for i in range(1, 8)]), (2, [f"S{i:02d}" for i in range(8, 15)])]:
        sheet = Image.new("RGB", (tw * 8, th * len(sids)), (15, 15, 15))
        draw = ImageDraw.Draw(sheet)
        for row, sid in enumerate(sids):
            cpath = OUT / "h3" / sid / "clip.mp4"
            d = get_dur(cpath)
            for col, pct in enumerate(pcts):
                ts = max(0.0, min(d - 0.05, d * pct))
                tmp_png = REV / f"_tmp_{sid}_{col}.png"
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ts:.3f}", "-i", str(cpath), "-frames:v", "1", str(tmp_png)],
                    check=True
                )
                im = Image.open(tmp_png).convert("RGB").resize((tw, th))
                tmp_png.unlink(missing_ok=True)
                sheet.paste(im, (col * tw, row * th))
                draw.rectangle([col * tw, row * th, col * tw + 105, row * th + 24], fill=(0, 0, 0))
                draw.text((col * tw + 5, row * th + 5), f"{sid} {ts:.2f}s", fill=(255, 255, 0))
        sheet.save(REV / f"dense_part{part}.jpg", quality=88)
    print("✅ Saved dense_part1.jpg & dense_part2.jpg")

    model = WhisperModel("small", device="cpu", compute_type="int8")
    asr_report = {}
    for s in cfg["shots"]:
        sid = s["id"]
        cpath = OUT / "h3" / sid / "clip.mp4"
        d = get_dur(cpath)
        ln = s.get("line")
        if not ln:
            print(f"[{sid}] (無台詞) clip_dur={d:.2f}s")
            asr_report[sid] = {"clip_dur": round(d, 3), "line": None}
            continue
        wav_tmp = REV / f"_tmp_{sid}.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(cpath), "-vn",
             "-af", "highpass=f=85,lowpass=f=12000,afftdn=nf=-20", "-ar", "16000", "-ac", "1", str(wav_tmp)],
            check=True
        )
        segs, _ = model.transcribe(str(wav_tmp), language="zh", word_timestamps=True)
        wav_tmp.unlink(missing_ok=True)
        words = []
        for seg in segs:
            for w in (seg.words or []):
                words.append({"w": w.word, "s": round(w.start, 2), "e": round(w.end, 2)})
        heard = "".join(x["w"] for x in words).strip()
        sp0 = max(0.0, words[0]["s"] - 0.12) if words else 0.0
        sp1 = min(d, words[-1]["e"] + 0.18) if words else d
        who = ln["who"]
        exp = ln["text"]
        print(f"[{sid}] ({who}) clip={d:.2f}s | spk=({sp0:.2f}, {sp1:.2f})")
        print(f"   預期: {exp}")
        print(f"   聽出: {heard}")
        asr_report[sid] = {
            "clip_dur": round(d, 3),
            "who": who,
            "expected": exp,
            "heard": heard,
            "sp0": round(sp0, 3),
            "sp1": round(sp1, 3),
            "words": words,
        }

    (REV / "gate2_asr.json").write_text(json.dumps(asr_report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
