import pathlib
import re

p = pathlib.Path(r"c:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji_v2\make_film.py")
s = p.read_text(encoding="utf-8")

stages = ["amb", "edl", "music", "ending", "cut", "review"]
for st in stages:
    m = re.search(r'@stage\("' + st + r'"\)\s*\ndef ' + st + r'\(\):.*?(?=@stage|\Z)', s, re.DOTALL)
    if m:
        lines = m.group(0).splitlines()[:15]
        print(f"=== {st} ===")
        print("\n".join(lines))
