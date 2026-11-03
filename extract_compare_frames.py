import subprocess
from pathlib import Path

out_dir = Path(r"c:\antigravity\影片\shanshiba-workflow-colab\inspect_frames")
out_dir.mkdir(parents=True, exist_ok=True)

v1 = r"c:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji\out\cut\film_1080p.mp4"
v2 = r"c:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji_v2\out\cut\film_1080p.mp4"

# 抽 V1 和 V2 在 S01(2s), S02(6s), S03(12s), S05(25s), S10(53s) 的畫面
timestamps = [
    ("S01_mid", "00:00:02.000"),
    ("S02_start", "00:00:05.000"),
    ("S02_mid", "00:00:07.500"),
    ("S02_end", "00:00:09.500"),
    ("S05_dahei", "00:00:24.000"),
    ("S07_transform", "00:00:36.000"),
]

for name, ts in timestamps:
    subprocess.run(["ffmpeg", "-y", "-ss", ts, "-i", v1, "-vframes", "1", "-q:v", "2", str(out_dir / f"v1_{name}.jpg")], capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-ss", ts, "-i", v2, "-vframes", "1", "-q:v", "2", str(out_dir / f"v2_{name}.jpg")], capture_output=True)

print("Frames extracted to inspect_frames.")
