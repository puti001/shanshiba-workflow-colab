import json
import sys
from pathlib import Path

for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

p1 = Path(r"c:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji")
p2 = Path(r"c:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji_v2")

edl1 = json.load(open(p1 / "out" / "post" / "edl.json", encoding="utf-8"))
edl2 = json.load(open(p2 / "out" / "post" / "edl.json", encoding="utf-8"))

rev1 = json.load(open(p1 / "out" / "review" / "film_1080p_review.json", encoding="utf-8"))
rev2 = json.load(open(p2 / "out" / "review" / "film_1080p_review.json", encoding="utf-8"))

print("=== TOTAL DURATION ===")
print(f"V1: {edl1.get('total')}s, V2: {edl2.get('total')}s")

print("\n=== SHOT BY SHOT COMPARISON ===")
for r1, r2 in zip(edl1["shots"], edl2["shots"]):
    sid = r1["id"]
    l1 = r1["lines"][0] if r1["lines"] else None
    l2 = r2["lines"][0] if r2["lines"] else None
    t1_str = f"dur={r1['dur']}s, line={l1['text'] if l1 else 'None'} ({l1['film_start'] if l1 else 0}-{l1['film_end'] if l1 else 0}s)" if l1 else f"dur={r1['dur']}s, no line"
    t2_str = f"dur={r2['dur']}s, line={l2['text'] if l2 else 'None'} ({l2['film_start'] if l2 else 0}-{l2['film_end'] if l2 else 0}s)" if l2 else f"dur={r2['dur']}s, no line"
    print(f"[{sid}]")
    print(f"  V1: {t1_str}")
    print(f"  V2: {t2_str}")
    if l2:
        shot_end = r2["start"] + r2["dur"]
        diff = l2["film_end"] - shot_end
        print(f"      V2 line cutoff overflow: {diff:+.3f}s")
