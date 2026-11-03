import os
import shutil

src_dir = r"C:\antigravity\影片\小吉與大黑\生成圖片\分鏡關鍵幀"
dst_dir = r"C:\antigravity\影片\shanshiba-workflow-colab\pipeline\houzhuang_xiaoji\out\first"

files = sorted(os.listdir(src_dir))
for f in files:
    if f.endswith(('.png', '.jpg')):
        prefix = f.split('_')[0] # S01, S02...
        if prefix.startswith('S') and len(prefix) == 3:
            dst_name = f"{prefix}.png"
            src_p = os.path.join(src_dir, f)
            dst_p = os.path.join(dst_dir, dst_name)
            shutil.copy2(src_p, dst_p)
            print(f"Copied {f} -> {dst_name}")

print("All 14 keyframes ready in out/first/!")
