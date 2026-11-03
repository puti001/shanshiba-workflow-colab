import pathlib

p = pathlib.Path(r"c:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji_v2\make_film.py")
s = p.read_text(encoding="utf-8")

old_ass = '''def ass_time(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"'''

new_ass = '''def ass_time(t):
    t = max(0.0, float(t))
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"'''

old_clip = '''        a = l["film_start"] - 0.05; b = l["film_end"] + 0.45'''
new_clip = '''        a = max(0.0, l["film_start"] - 0.05); b = max(a + 0.1, l["film_end"] + 0.45)'''

assert old_ass in s, "old_ass not found"
assert old_clip in s, "old_clip not found"

s = s.replace(old_ass, new_ass).replace(old_clip, new_clip)
p.write_text(s, encoding="utf-8")
print("make_film.py successfully patched!")
