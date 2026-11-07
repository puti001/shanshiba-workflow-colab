"""V3 film.json 產生器（海洋未來式 第1集：發燒的海洋母親 - 17張圖明細版）
明確標註 14 個鏡頭、17 張關鍵幀圖片路徑（14 首幀 + 3 尾幀）。"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent

STYLE = (
    "a vibrant 2D cel-shaded animated feature film, clean bold line art, "
    "deep ocean cyan and warm gallery spotlight illumination, rich harmonious colors, smooth cartoon toon shading"
)
CONSTRAINTS = [
    "Maintain the exact cartoon animation style, clean bold outlines, and character proportions of <Picture 1> in every single frame.",
    "Every character keeps the exact same cartoon design, clothing colors, and robot markings as in <Picture 1> from the first frame to the last frame.",
    "Keep all museum exhibition screens, glass pedestals, and climate graphics solid, stable, and consistent with <Picture 1>.",
    "Keep all character limbs, hands, glasses, antennas, and facial features clean and well-formed.",
]

CHARS = {
    "huang": dict(
        name="黃老師",
        sub_color="&H00FFFFFF",
        look="Teacher Huang, a cartoon Taiwanese male museum volunteer teacher with short grey-black hair, "
             "round black-rimmed glasses, a warm friendly smile, a burgundy volunteer vest over a white short-sleeve shirt, "
             "dark prayer beads on his left wrist, and black trousers",
        h3_voice="a warm, expressive middle-aged Taiwanese male teacher voice, clear and lively, natural Taiwanese Mandarin",
        ref_voice="out/voice/ref_huang.wav"
    ),
    "xiaoji": dict(
        name="小吉",
        sub_color="&H0000E5FF",
        look="Xiaoji (GiGi), a cartoon robot with a smooth round golden-yellow helmet with Puti-AI text on the forehead, "
             "large oval glowing cyan visor eyes on a dark screen face, circular cyan glowing ear discs, "
             "chunky golden-yellow armor, a small chest screen displaying GiGi, dark-grey mechanical joints, and a small backpack with a glowing cyan energy cell",
        h3_voice="a bright, energetic young boy-robot voice, heroic and highly expressive, with a faint metallic ring, natural Taiwanese Mandarin",
        ref_voice="out/voice/ref_xiaoji.wav"
    ),
}

def shot(id, refs, dur, action, camera, use_last, line=None, tail=1.0):
    first_path = f"out/first/{id}.png"
    last_path = f"out/last/{id}.png" if use_last else None
    d = dict(
        id=id,
        refs=refs,
        dur=dur,
        first_frame=first_path,
        use_last=use_last,
        last_frame=last_path,
        camera=camera,
        action=action,
        cut_in=0.0
    )
    if line:
        d["line"] = dict(who=line[0], text=line[1], at=0.6)
        d["tail"] = tail
    else:
        d["line"] = None
        d["cut_out"] = "full"
    return d

SHOTS = [
    shot(
        "S01",
        ["xiaoji"],
        6.5,
        "Starting from <Picture 1>, the lively cartoon robot Xiaoji rushes enthusiastically into the dimly lit exhibition hall, suddenly braking on the glowing deep-blue mirrored floor. Xiaoji tilts his round golden helmet upward in utter astonishment, his large cyan visor eyes widening as the camera pushes forward in a smooth low-angle steadicam movement while towering ocean waves surge across the colossal projection wall ahead.",
        "Low-angle steadicam tracking forward at floor level.",
        False,
        line=("xiaoji", "哇！黃老師你看！這裡黑漆漆的，海水好像真的要漫過來了！"),
        tail=1.0
    ),
    shot(
        "S02",
        ["huang", "xiaoji"],
        6.5,
        "Starting from <Picture 1>, Teacher Huang steps calmly forward from the warm gallery light into the deep oceanic cyan projection glow beside Xiaoji. Teacher Huang adjusts his round glasses, gently points his right hand toward the illuminated sea level numbers on the curved wall, and speaks with an earnest, engaging smile as light reflections ripple smoothly across their faces.",
        "Over-the-shoulder slow dolly-in.",
        False,
        line=("huang", "這座巨幕叫汪洋。我們腳底的不是特效，而是海平面正在上升的真實倒數。"),
        tail=1.0
    ),
    shot(
        "S03",
        ["xiaoji", "huang"],
        6.5,
        "Starting from <Picture 1>, Xiaoji crouches slightly on the reflective blue exhibition floor, tapping the projected water ripples with his metallic index finger. Xiaoji tilts his head sideways with a quizzical blinking expression, turning his glowing cyan visor toward Teacher Huang and asking his question with curious robotic arm gestures while the dark ocean waves swell behind them.",
        "Low-angle subtle tilt with curious gestures.",
        False,
        line=("xiaoji", "倒數？可是老師，海那麼大，怎麼可能裝不下水呢？"),
        tail=1.0
    ),
    shot(
        "S04",
        ["huang", "xiaoji"],
        6.5,
        "Starting from <Picture 1>, Teacher Huang places a gentle hand on Xiaoji rounded shoulder armor, turning slightly toward the glowing world ocean map. Teacher Huang speaks with compassionate emotion, his hands opening outward to describe the vastness of the sea, while ambient volumetric cyan light beams softly illuminate their silhouettes against the rising tide projection.",
        "Lateral tracking shot across the illuminated wall.",
        False,
        line=("huang", "大海就像媽媽一樣包容一切，吸收了大氣超過九成的多餘熱量，但她現在已經開始發燒了。"),
        tail=1.0
    ),
    shot(
        "S05",
        ["xiaoji"],
        6.5,
        "Starting from <Picture 1>, Xiaoji turns and hurries toward the central glowing SST climate pedestal. The central spherical earth display abruptly shifts from cool tranquil ocean blue into an alarming fiery orange-red heatwave pattern, casting intense dramatic crimson reflections across Xiaoji golden helmet and chest screen as he gasps in shock.",
        "Arc rotation around the glowing earth exhibit.",
        False,
        line=("xiaoji", "哇啊！整個地球怎麼突然變得通紅通紅的？！"),
        tail=1.0
    ),
    shot(
        "S06",
        ["huang", "xiaoji"],
        6.5,
        "Starting from <Picture 1>, Teacher Huang walks up to the illuminated stepped heatwave graph, tracing his finger along the glowing red plus one-point-five degrees Celsius warning threshold. Teacher Huang furrows his brows slightly, turning his head toward Xiaoji with a serious yet caring expression as holographic climate data points blink and scroll along the glass display.",
        "Stepped macro push-in on illuminated graph.",
        False,
        line=("huang", "這叫海洋熱浪。每上升一階，對珊瑚和成千上萬的海洋生物來說，就是無處可逃的高燒浩劫。"),
        tail=1.0
    ),
    shot(
        "S07",
        ["xiaoji"],
        6.5,
        "Starting from <Picture 1>, Xiaoji steps backward half a pace, his robotic fingers clutching his chest armor around the GiGi screen in palpable anxiety. Xiaoji gazes up at the pulsing red climate visualization with glowing flickering eyes, shaking his golden helmet slowly as dramatic ambient warning lights create deep shadows across the exhibition floor.",
        "Subtle handheld parallax drift focusing on character tension.",
        False,
        line=("xiaoji", "高燒……就像我上次生病發燒那樣，全身動彈不得嗎？"),
        tail=1.0
    ),
    shot(
        "S08",
        ["huang"],
        6.5,
        "Starting from <Picture 1>, Teacher Huang nods solemnly under the soft gallery spotlight, folding his hands together in a sympathetic posture. Teacher Huang speaks in a warm, resonant voice filled with empathy, the background red indicators softly blurring into smooth circular bokeh as he explains the vulnerability of the marine biosphere.",
        "Gentle close-up push-in with warm rim lighting.",
        False,
        line=("huang", "比那更難受。因為生病發燒的海洋，沒辦法自己吃退燒藥。"),
        tail=1.0
    ),
    shot(
        "S09",
        ["xiaoji"],
        6.5,
        "Starting from <Picture 1>, the camera pushes past the exhibition partition wall to reveal the vibrant Climate Sentiment Emoticon art installation. Xiaoji walks into the new gallery zone, pointing with both robotic hands at the massive wall adorned with brightly colored expressive children masks displaying feverish, terrified, and weeping faces.",
        "Tracking push-in revealing new exhibition area.",
        False,
        line=("xiaoji", "咦？這些臉……怎麼全都看起來好生氣、又像在哭？"),
        tail=1.0
    ),
    shot(
        "S10",
        ["xiaoji"],
        6.5,
        "Starting from <Picture 1>, Xiaoji stands right beside the large glowing red angry emoticon sculpture, mirroring its fierce tilted brow expression. Xiaoji pouts his small digital mouth line, pointing his finger directly at the glowing red mask while glancing back toward Teacher Huang with an indignant, passionate bounce in his stance.",
        "Dutch-angle close shot beside the red emoticon sculpture.",
        False,
        line=("xiaoji", "這張臉……簡直就是我生氣時的樣子嘛！"),
        tail=1.0
    ),
    shot(
        "S11",
        ["xiaoji", "huang"],
        6.5,
        "Starting from <Picture 1>, Xiaoji turns sharply toward the camera with an intense, determined gaze, his cyan visor flashing with righteous energy. Behind them, the golden illuminated quotes of Dr Jane Goodall begin to glow softly on the dark slate wall as Xiaoji raises his arms, delivering his heartfelt question with resonant dramatic momentum.",
        "Tight close-up zoom on righteous emotional delivery.",
        False,
        line=("xiaoji", "黃老師！珍古德博士說的是真的嗎？大人們……是不是真的把地球搞砸了？！"),
        tail=1.0
    ),
    shot(
        "S12",
        ["huang", "xiaoji"],
        6.5,
        "Starting from <Picture 1>, Teacher Huang begins standing beside Xiaoji, then smoothly lowers himself down onto one knee on the polished museum floor to meet Xiaoji at eye level. Teacher Huang looks directly into Xiaoji glowing cyan visor with warmth and honesty, speaking sincerely as the golden light from the quote wall illuminates both characters.",
        "Kneeling eye-level two-shot with warm rim light.",
        True,
        line=("huang", "大人確實犯了貪婪的錯。但搞砸的世界，不能就這樣丟給你們承擔。"),
        tail=1.0
    ),
    shot(
        "S13",
        ["huang", "xiaoji"],
        6.5,
        "Starting from <Picture 1>, Teacher Huang holds his open right hand ready while Xiaoji raises his robotic arm in anticipation. They swiftly swing their palms forward and execute a firm, resonant high-five clap right in the center of the frame, Xiaoji cyan visor eyes curling into joyful crescents as warm golden rim lights sparkle around their connected hands.",
        "Rack-focus high-five connection.",
        True,
        line=("huang", "改變的力量在我們手裡！走，去看看大海居民怎麼對抗這場危機！"),
        tail=1.0
    ),
    shot(
        "S14",
        ["xiaoji", "huang"],
        6.5,
        "Starting from <Picture 1>, Xiaoji turns enthusiastically and breaks into a fast run forward into the dark hall, with Teacher Huang stepping into a swift jog beside him. The camera cranes upward and pulls back smoothly as both characters run toward the glowing turquoise portal of the next marine biodiversity pavilion in the far distance.",
        "Crane pull-out wide shot entering the next portal.",
        True,
        line=("xiaoji", "好！我一定要找出拯救大海的辦法！黃老師等等我！"),
        tail=1.0
    )
]

data = {
    "_comment": "V3 海洋未來式 Ep01: 14個鏡頭(S01~S14)，共需17張圖(14首幀+3尾幀)",
    "title": "海洋未來式 第1集：發燒的海洋母親",
    "total_shots": 14,
    "total_images_required": 17,
    "image_manifest": {
        "first_frames_14": [f"out/first/S{i:02d}.png" for i in range(1, 15)],
        "last_frames_3": ["out/last/S12.png", "out/last/S13.png", "out/last/S14.png"]
    },
    "repo_dir": "../..",
    "voice_mode": "h3_ref",
    "h3": {
        "style": STYLE,
        "setting": "National Museum of Marine Science and Technology exhibition gallery with towering curved ocean projection screens and high-tech climate displays, as an animated cartoon set",
        "draft": False,
        "steps": 14,
        "default_seed": 202611,
        "soundscape": "Immersive deep sea ambient hum with gentle water resonance, museum footsteps, and crisp electronic data pulses.",
        "camera": "Cinematic camera movement with smooth tracking, push-in, and subtle focal depth.",
        "constraints": CONSTRAINTS
    },
    "chars": CHARS,
    "shots": SHOTS
}

if __name__ == "__main__":
    out_file = HERE / "film.json"
    out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated film.json successfully at {out_file}")
