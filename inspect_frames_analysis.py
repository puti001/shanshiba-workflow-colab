from PIL import Image
import numpy as np
from pathlib import Path

dir_p = Path(r"c:\antigravity\影片\shanshiba-workflow-colab\inspect_frames")
for f in sorted(dir_p.glob("*.jpg")):
    im = Image.open(f)
    arr = np.array(im)
    mean_color = arr.mean(axis=(0,1))
    std_color = arr.std(axis=(0,1))
    print(f"{f.name:15s} | size: {im.size} | mean RGB: ({mean_color[0]:.1f}, {mean_color[1]:.1f}, {mean_color[2]:.1f}) | std: {std_color.mean():.1f}")
