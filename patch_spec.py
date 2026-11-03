import re
from pathlib import Path

p = Path(r"c:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji\make_film.py")
code = p.read_text(encoding="utf-8")

old_pattern = r'def h3_spec\(s, secs, dialogue\):[\s\S]*?soundscape=h\["soundscape"\], music="N/A"\)'

new_block = '''def h3_spec(s, secs, dialogue):
    h = CFG["h3"]
    sp = dict(duration=round(secs - 0.02, 3), size=[1344, 768], seed=seed("h3_" + s["id"], h.get("default_seed", 20261007)), steps=14, draft=True,
              style=h["style"], setting=h["setting"], first_frame=str(OUT / "first" / f"{s['id']}.png"),
              subjects=[dict(key=k, desc=CHARS[k]["look"], voice=CHARS[k]["h3_voice"]) for k in s["refs"]],
              shots=[dict(camera=s.get("camera", h.get("camera", "The camera holds a static shot on a tripod.")), action=s["action"], dialogue=dialogue)],
              constraints=h.get("constraints", []) + s.get("extra_constraints", []), soundscape=h["soundscape"], music="N/A")
    last_p = OUT / "last" / f"{s['id']}.png"
    if last_p.exists():
        sp["last_frame"] = str(last_p)
    return sp'''

new_code, count = re.subn(old_pattern, new_block, code)
assert count == 1, f"Expected 1 replacement, got {count}"
p.write_text(new_code, encoding="utf-8")
print("Successfully patched make_film.py!")
