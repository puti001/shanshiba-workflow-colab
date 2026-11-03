"""V3 film.json 產生器（菩提心起：佛陀教我做導覽）
角色描述、action 100% 依實際分鏡圖（out/first、out/last）撰寫對齊。"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent

STYLE = (
    "a vibrant 2D cel-shaded animated feature film, clean bold line art, "
    "warm museum spotlight illumination, rich harmonious colors, smooth 2D cartoon shading"
)
CONSTRAINTS = [
    "Maintain the exact 2D cel-shaded cartoon animation style, clean bold outlines, and character proportions of <Picture 1> in every single frame.",
    "Every character keeps the exact same 2D cartoon design, clothing colors, and proportions as in <Picture 1> from the first frame to the last frame.",
    "Keep all museum glass display cases, pedestals, and Buddhist sculptures inside them solid, stable, and consistent with <Picture 1>.",
    "Keep all character limbs, hands, glasses, and facial features clean and well-formed.",
]

CHARS = {
    "huang": dict(
        name="黃老師",
        sub_color="&H00FFFFFF",
        look="Teacher Huang, a 2D cel-shaded cartoon Taiwanese male museum volunteer teacher with short grey-black hair, "
             "round black-rimmed glasses, a warm friendly smile, a burgundy volunteer vest over a white short-sleeve shirt, "
             "dark prayer beads on his left wrist, and black trousers",
        h3_voice="a warm, expressive middle-aged Taiwanese male teacher's voice, clear and lively, natural Taiwanese Mandarin",
    ),
    "buddha": dict(
        name="佛陀",
        sub_color="&H0000E5FF",
        look="the 2D cel-shaded cartoon Buddha, with dark curly hair connected to a full beard, long earlobes, "
             "a gentle wise smile, a brown monastic robe draped with the right shoulder bare, and bare feet",
        h3_voice="a warm, resonant, compassionate and humorous wise male voice, calm yet expressive, natural Taiwanese Mandarin",
    ),
    "visitors": dict(
        name="遊客",
        sub_color="&H00FFFFFF",
        look="2D cel-shaded cartoon museum visitors including a young man in a beige jacket, a mother in a cream blouse and pink skirt, "
             "and children in colorful casual clothes",
        h3_voice="cheerful museum visitors' voices",
    ),
}


def shot(id, refs, dur, action, camera, use_last, line=None, tail=1.0):
    d = dict(id=id, refs=refs, dur=dur, action=action, camera=camera, use_last=use_last, cut_in=0.0)
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
        ["huang"],
        6.5,
        "Starting from <Picture 1>, Teacher Huang stands to the left of the glass display case holding a white clipboard of notes "
        "in his left hand, scratches his head with his right hand, furrows his brows and speaks with a troubled sigh, glancing down "
        "at his clipboard and shaking his head slightly while the bronze Buddha statue stands quietly inside the lit glass case.",
        "The camera slowly pushes in from a medium shot.",
        False,
        ("huang", "北魏、北齊、高一百一十公分……背了一堆數字，遊客聽兩句就滑手機，這特展到底該怎麼導覽啊？"),
        1.2,
    ),
    shot(
        "S02",
        ["buddha", "huang"],
        6.5,
        "Starting from <Picture 1>, swirling golden light sparkles around the glass display case as the living 2D cartoon Buddha "
        "leaps gracefully forward out of the case and lands barefoot on the museum floor right beside Teacher Huang. The Buddha "
        "brings his palms together in gassho and speaks with a warm, humorous smile as golden sparkles float around him, while "
        "Teacher Huang stares at him in astonished wonder holding his clipboard.",
        "The camera holds a static medium-wide shot on a tripod.",
        True,
        ("buddha", "朝榮老師，別再背我的身高體重啦！我當年出山苦思的是眾生，不是一百一十公分呀！"),
        1.0,
    ),
    shot(
        "S03",
        ["buddha", "huang"],
        6.5,
        "Starting from <Picture 1>, the 2D cartoon Buddha keeps his right hand gently on Teacher Huang's shoulder, pats it twice "
        "and speaks with a warm, lively smile while pointing his left finger toward his own bearded face. Teacher Huang adjusts his "
        "round glasses with his right hand, nods his head repeatedly in sudden realization, and smiles warmly back at the Buddha.",
        "The camera holds a static medium two-shot on a tripod.",
        False,
        ("buddha", "想讓遊客感動，別把佛像當冰冷古董，要帶他們做人物剖析，走進造像時的心境！"),
        1.0,
    ),
    shot(
        "S04",
        ["buddha", "huang"],
        6.5,
        "Starting from <Picture 1>, the 2D cartoon Buddha stands to the right of the glass display case with his palms together "
        "in gassho, speaking calmly and softly. Warm golden ribbons of light begin to spiral gently around the Buddha, the bronze "
        "statue inside the glass case, and Teacher Huang on the left. Moved by the peaceful atmosphere, Teacher Huang brings his "
        "hands together in gassho and closes his eyes in quiet contemplation.",
        "The camera slowly pushes in on the three figures.",
        True,
        ("buddha", "第一招：看神情問自己。為什麼這位佛陀留著鬍子、赤著雙腳？因為他剛走過人間最痛的迷惘。"),
        1.0,
    ),
    shot(
        "S05",
        ["buddha", "huang"],
        6.5,
        "Starting from <Picture 1>, the 2D cartoon Buddha on the right points his right index finger toward the Song dynasty clay "
        "Arhat statue inside the glass display case and speaks with an expressive, animated smile, moving his left hand in a "
        "storytelling gesture. On the left, Teacher Huang leans forward with his hands on his knees, examines the Arhat's deep-set "
        "eyes closely through his glasses, and nods with an appreciative smile.",
        "The camera holds a static medium shot on a tripod.",
        False,
        ("buddha", "再看這尊宋代羅漢，眼窩深邃、眉頭微蹙，他不是遙不可及的神，而是正為人生難題苦思的你我！"),
        1.0,
    ),
    shot(
        "S06",
        ["buddha", "huang"],
        6.5,
        "Starting from <Picture 1>, crouched beside the glass display case housing the Northern Qi stone stele, the 2D cartoon "
        "Buddha on the right speaks warmly and points his right index finger closely at the bottom register of the stele. The tiny "
        "carved donor figures along the base of the stone stele light up with a warm golden amber glow, and Teacher Huang on the "
        "left leans his head closer to peer at the glowing carvings in fascination.",
        "The camera holds a low-angle medium shot on a tripod.",
        True,
        ("buddha", "第二招：找尋藏在細節裡的小人物！別只看大佛，帶遊客蹲下來，看碑底這位北齊的張解。"),
        1.0,
    ),
    shot(
        "S07",
        ["buddha", "huang"],
        5.5,
        "Starting from <Picture 1>, as the 2D cartoon Buddha on the right holds his glowing right palm toward the base of the "
        "Northern Qi stone stele, warm golden light radiates brighter from the bottom carvings. Translucent golden spirit silhouettes "
        "of ancient donors clasping their hands in prayer and holding lotus blossoms rise gently upward around the stone stele with "
        "floating golden sparkles, while Teacher Huang on the left watches in deep, quiet awe.",
        "The camera slowly tilts up slightly as the golden silhouettes rise.",
        True,
    ),
    shot(
        "S08",
        ["buddha", "huang"],
        6.5,
        "Starting from <Picture 1>, standing between the small Tang clay plaque display case on the left and the large Ming cast-iron "
        "seated Buddha case on the right, the 2D cartoon Buddha first cups a warm golden glow in his palms while speaking, then raises "
        "his left arm to gesture gracefully toward the cast-iron seated Buddha as both display cases shimmer with warm golden light. "
        "Teacher Huang places his right hand over his heart and nods with deep understanding.",
        "The camera holds a static medium-wide shot on a tripod.",
        True,
        ("buddha", "泥土能壓出真如妙身，鐵佛的鏽痕刻著五百年歲月。帶遊客想像親手捧著泥佛的溫度！"),
        1.0,
    ),
    shot(
        "S09",
        ["huang", "buddha"],
        6.5,
        "Starting from <Picture 1>, Teacher Huang on the left tucks the white note card into his burgundy vest pocket with his right "
        "hand, raises his left hand with prayer beads in an enthusiastic gesture, and speaks with a bright, confident smile. On the "
        "right, the 2D cartoon Buddha keeps his palms together in gassho, smiles warmly, and nods his head twice in proud approval.",
        "The camera holds a static medium two-shot on a tripod.",
        False,
        ("huang", "我懂了！石頭與泥土只是身體，裡面裝的是千年前人們的眼淚、盼望與慈悲！"),
        1.0,
    ),
    shot(
        "S10",
        ["buddha", "huang", "visitors"],
        5.5,
        "Starting from <Picture 1>, the 2D cartoon Buddha in the center smiles warmly and dissolves into a swirling stream of golden "
        "light particles that flow into the glass display case on the right and reform into the bronze Sakyamuni statue on its "
        "pedestal. Teacher Huang steps forward cheerfully with his left arm extended to guide the arriving family of visitors toward "
        "the exhibit.",
        "The camera holds a static wide shot on a tripod.",
        True,
    ),
    shot(
        "S11",
        ["huang", "visitors"],
        6.5,
        "Starting from <Picture 1>, Teacher Huang stands on the left with open, welcoming hands and speaks with lively warmth and "
        "enthusiasm, gesturing toward the bronze Buddha statue inside the center glass case. On the right, the young man lowers his "
        "smartphone, and he, the woman, and the boy in the yellow jacket all lean in slightly, looking up at the bearded bronze "
        "statue with fascinated smiles and nodding.",
        "The camera holds a static medium-wide shot on a tripod.",
        False,
        ("huang", "各位朋友，請先別看說明牌！你們看眼前這位蓄著鬍鬚、赤著雙腳的佛陀，像不像剛走過低谷的我們？"),
        1.2,
    ),
    shot(
        "S12",
        ["huang", "visitors"],
        6.5,
        "Starting from <Picture 1>, Teacher Huang crouches on the left beside the glass display case and points his left finger "
        "warmly at the small carved donor figures along the base of the Northern Qi stone stele while speaking passionately. On the "
        "right, the crouching mother, the little girl in pink, and the young man lean forward with wide, amazed eyes, looking closely "
        "at the ancient stone carvings and smiling in wonder.",
        "The camera holds a static low-angle medium shot on a tripod.",
        False,
        ("huang", "蹲下來看，一千五百年前一位叫張解的人，把對家人的愛全刻進石頭裡，今天正與你的目光相遇！"),
        1.2,
    ),
    shot(
        "S13",
        ["buddha", "huang", "visitors"],
        6.5,
        "Starting from <Picture 1>, in front of the framed Guanyin painting and the smiling Tang dynasty stone Buddha head inside "
        "the glass case, warm golden light and glowing golden lotus blossoms drift gently through the gallery air. Teacher Huang on "
        "the left raises both hands and brings his palms together in gassho with a serene, deeply moved smile, while the visitors on "
        "the right gaze up in peaceful reverence with their hands in gassho.",
        "The camera slowly pushes in on the serene gallery scene.",
        True,
        ("huang", "當你從佛像看見千年前的真心，那一刻，菩提心就已經在你心裡生起了。"),
        1.2,
    ),
    shot(
        "S14",
        ["huang", "visitors"],
        6.5,
        "Starting from <Picture 1>, facing the camera in front of the center display case, Teacher Huang holds his left hand up in "
        "a cheerful OK sign and speaks the closing line with a big, joyful smile, while the young man, the little girl in pink, and "
        "the mother beside him smile and wave warmly. Above the glass display case, a radiant golden silhouette of the 2D cartoon "
        "Buddha in gassho shines brightly amidst floating golden sparkles.",
        "The camera holds a static medium-wide shot on a tripod.",
        True,
        ("huang", "觀像觀心，菩提心起！歡迎來佛陀紀念館，找回屬於你的千年感動！"),
        1.5,
    ),
]

FILM = {
    "_comment": "V3 菩提心起：2D 賽璐璐動畫風格、非 draft (14 steps)、首尾幀依實際生成圖 100% 對齊、h3_ref 演繹",
    "title": "菩提心起：佛陀教我做導覽",
    "repo_dir": "../..",
    "voice_mode": "h3_ref",
    "h3": {
        "style": STYLE,
        "setting": "Fo Guang Shan Buddha Museum Gallery 2 exhibition hall with warm museum spotlights and glass display cases, as a 2D animated set",
        "draft": False,
        "steps": 14,
        "default_seed": 31415,
        "soundscape": "Quiet, serene museum gallery ambience with gentle footsteps and warm golden chime resonance.",
        "camera": "The camera holds a static shot on a tripod.",
        "constraints": CONSTRAINTS,
    },
    "chars": CHARS,
    "shots": SHOTS,
    "seeds": {f"h3_{s['id']}": 31415 + 101 * i for i, s in enumerate(SHOTS)},
    "music": {
        "caption": "Genre: Warm inspirational animated film score blended with gentle guqin harmonics, soft piano, warm strings, and serene temple bell accents, uplifting finale. BPM 92.\n"
                   "Vocal: NONE. No singing, no choir.\n"
                   "Arrangement: acoustic piano, warm cello and strings, delicate guqin plucks, soft glockenspiel and singing bowl shimmer.",
        "seeds": [11, 42, 88],
    },
    "mix": {"say_lead": 0.0, "default_tail": 1.0, "music_under_lines": 0.22, "target_lufs": -15.5},
    "ending": {"custom": True},
}

(HERE / "film.json").write_text(json.dumps(FILM, ensure_ascii=False, indent=1), encoding="utf-8")
print("film.json written:", len(SHOTS), "shots")
