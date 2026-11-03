import asyncio, subprocess, sys
from pathlib import Path
import edge_tts
import whisper

sys.stdout.reconfigure(encoding="utf-8")
hd = Path(r"C:\antigravity\影片\shanshiba-workflow-colab\pipeline\puti_xinqi\out\voice\h3")

async def make_s06_s08():
    lines = {
        "S06_fix.wav": ("別只說這是北齊石碑，彎下腰看底座，那是當年捐款刻碑的信眾與供養人。", "+6%"),
        "S08_fix.wav": ("像這樣說出老百姓在無常裡找依靠的盼望，石頭就有了溫度，千年歷史瞬間活在眼前！", "+6%"),
    }
    for fname, (txt, rate) in lines.items():
        tmp = hd / ("_tmp_" + fname + ".mp3")
        for attempt in range(5):
            try:
                c = edge_tts.Communicate(text=txt, voice="zh-TW-YunJheNeural", rate=rate, pitch="-3Hz")
                await c.save(str(tmp))
                break
            except Exception as e:
                print("Retry", fname, e)
                await asyncio.sleep(1.5)
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
            "-af", "highpass=f=80,bass=g=2.5:f=140:w=0.5,equalizer=f=3800:t=q:w=1.2:g=3.5,treble=g=4.0:f=6500",
            "-ar", "48000", "-ac", "1", str(hd / fname)
        ], check=True)
        tmp.unlink(missing_ok=True)
        print("Fixed:", fname)

asyncio.run(make_s06_s08())

m = whisper.load_model("base")
r = m.transcribe(str(hd / "S12_fix.wav"), language="zh", word_timestamps=True)
print("S12_fix ASR:", r["text"])
for s in r["segments"]:
    print(f"{s['start']:.2f}-{s['end']:.2f}: {s['text']}")
    for w in s.get("words", []):
        print(f"  {w['word']}({w['start']:.2f}-{w['end']:.2f})", end="")
    print()
