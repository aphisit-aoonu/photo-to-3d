import sys
from pathlib import Path
from PIL import Image
from rembg import remove, new_session

src, dst, model = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
dst.mkdir(parents=True, exist_ok=True)
session = new_session(model)
for p in sorted(src.glob("*.jpg")):
    if "(2)" in p.name:
        continue
    out = remove(Image.open(p), session=session)
    box = out.getbbox()
    out = out.crop(box)
    w, h = out.size
    side = int(max(w, h) * 1.1)
    sq = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    sq.paste(out, ((side - w) // 2, (side - h) // 2))
    sq.save(dst / (p.stem + ".png"))
    print(p.name, "->", sq.size)
