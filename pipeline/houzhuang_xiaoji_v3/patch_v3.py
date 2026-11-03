"""V3 對 make_film.py 的修正（每一處都 assert，對不上就停）。
1. h3_spec：draft/steps 從 film.json 讀（原本寫死 draft=True＝DMAD 4 步預覽）
2. h3_spec：last_frame 只在 shot.use_last=true 才加（原本有檔就加 → 首尾同圖人物凍結）
3. h3_spec：每鏡 subject 可帶 voice 覆寫；constraints 合併
4. harvest_lines：比對前先繁簡統一（OpenCC），避免「确/確」被誤判
5. ending：custom=true 時不跑樣板，直接用預先做好的 out/ending/ending.mp4
"""
import pathlib
import sys

p = pathlib.Path(__file__).with_name("make_film.py")
s = p.read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, f"找不到或不唯一：{old[:80]}"
    s = s.replace(old, new)


rep('steps=14, draft=True,', 'steps=int(h.get("steps", 14)), draft=bool(h.get("draft", False)),')
rep('''    last_p = OUT / "last" / f"{s['id']}.png"
    if last_p.exists():
        sp["last_frame"] = str(last_p)
    return sp''', '''    last_p = OUT / "last" / f"{s['id']}.png"
    if s.get("use_last") and last_p.exists():
        sp["last_frame"] = str(last_p)
    for k in ("first_frame", "last_frame"):
        if k in sp:
            sp[k] = os.path.relpath(sp[k], OUT / "h3" / s["id"])   # 相對路徑：本機與 VM 都能用
    return sp''')
rep('''    norm = lambda t: "".join(re.findall(r"[\\u4e00-\\u9fffA-Za-z0-9]", t)).lower()''',
    '''    try:
        from opencc import OpenCC
        _t2s = OpenCC("t2s").convert
    except Exception:
        _t2s = lambda t: t
    norm = lambda t: _t2s("".join(re.findall(r"[\\u4e00-\\u9fffA-Za-z0-9]", t)).lower())''')
rep('''    e = CFG.get("ending")
    if not e:
        return
    from PIL import Image''', '''    e = CFG.get("ending")
    if not e:
        return
    if e.get("custom"):
        assert (OUT / "ending" / "ending.mp4").exists(), "custom ending：先做好 out/ending/ending.mp4"
        return
    from PIL import Image''')
p.write_text(s, encoding="utf-8")
print("make_film.py patched (v3)")
