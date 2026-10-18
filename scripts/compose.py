import glob
from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1350, 30
FONTS = ROOT / "assets/fonts"
WHITE, GREY, DIM = (240, 240, 242), (150, 152, 160), (95, 97, 106)
MARGIN = 84
XFADE = 0.5


def font(name, size):
    return ImageFont.truetype(str(FONTS / f"{name}.ttf"), size)


FIG_PHOTOS = sorted(glob.glob("C:/Users/USER/Downloads/harumichi-figure/*.jpg"))
TT_FIG5 = sorted(glob.glob(str(ROOT / "build/tt_figure/*.png")))
TT_FIG9 = sorted(glob.glob(str(ROOT / "build/tt_figure_v2/*.png")))
TT_PLANT = sorted(glob.glob(str(ROOT / "build/tt_plant/*.png")))
APP = sorted(glob.glob(str(ROOT / "build/app_frames/*.png")))

# Crop out stray objects at the photo edge (e.g. the keyboard in one shot): name -> top fraction to drop
PHOTO_CROP_TOP = {"photo_2026-10-18_09-07-28": 0.3}


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def background():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.55) / H) ** 2)
    v = 10 + 16 * np.clip(1 - d * 1.6, 0, 1)
    rgb = np.stack([v, v, v * 1.08], -1)
    return rgb.astype(np.float32)


BASE = background()
_rng = np.random.default_rng(7)


def finish(im):
    # fine grain hides gradient banding and keeps flat areas from looking digital
    a = np.asarray(im, dtype=np.float32) + _rng.normal(0, 2.2, (H, W, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def canvas():
    return Image.fromarray(BASE.astype(np.uint8)).convert("RGBA")


def tracked(d, xy, s, f, fill, spacing):
    x, y = xy
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + spacing
    return x


def tracked_width(d, s, f, spacing):
    return sum(d.textlength(ch, font=f) for ch in s) + spacing * (len(s) - 1)


def fade(c, a):
    return tuple(int(v * a) for v in c) + (int(255 * a),)


def caption(im, t, dur, over, title, note=None, bottom=150):
    a = ease((t - 0.25) / 0.6) * (1 - ease((t - (dur - 0.35)) / 0.35))
    if a <= 0:
        return
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    rise = int(14 * (1 - a))
    y = H - bottom + rise
    tracked(d, (MARGIN, y - 78), over, font("Inter-Medium", 22), fade(GREY, a), 4)
    d.text((MARGIN, y - 44), title, font=font("InterDisplay-SemiBold", 54), fill=fade(WHITE, a))
    if note:
        d.text((MARGIN, y + 28), note, font=font("Inter-Regular", 24), fill=fade(DIM, a))
    im.alpha_composite(layer)


def shadowed(im, radius=22, blur=40, alpha=150):
    w, h = im.size
    pad = blur * 2
    sh = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 18, pad + w, pad + h + 18), radius, fill=(0, 0, 0, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius, fill=255)
    card = im.convert("RGBA")
    card.putalpha(mask)
    sh.alpha_composite(card, (pad, pad))
    return sh, pad


def photo(p):
    im = Image.open(p).convert("RGB")
    top = PHOTO_CROP_TOP.get(Path(p).stem, 0)
    return im.crop((0, int(im.height * top), im.width, im.height)) if top else im


def cover(im, box):
    bw, bh = box
    s = max(bw / im.width, bh / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - bw) // 2, (im.height - bh) // 2
    return im.crop((x, y, x + bw, y + bh))


def turntable(frames, t, size, speed=0.75):
    i = int(t * FPS * speed) % len(frames)
    return Image.open(frames[i]).convert("RGBA").resize((size, size), Image.LANCZOS)


def place_model(im, fr, cx, top):
    im.alpha_composite(fr, (cx - fr.width // 2, top))
    refl = fr.transpose(Image.FLIP_TOP_BOTTOM)
    grad = Image.linear_gradient("L").resize(refl.size).point(lambda v: int(max(0, 255 - v * 3.2) * 0.16))
    a = Image.composite(refl.getchannel("A"), Image.new("L", refl.size, 0), grad)
    refl.putalpha(Image.eval(Image.fromarray(np.minimum(np.asarray(a), np.asarray(grad))), lambda v: v))
    bbox = fr.getchannel("A").getbbox()
    floor = top + (bbox[3] if bbox else fr.height)
    im.alpha_composite(refl.crop((0, fr.height - (bbox[3] if bbox else fr.height), fr.width, fr.height)), (cx - fr.width // 2, floor))


def text_center(im, y, s, f, color, a, spacing=0):
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = tracked_width(d, s, f, spacing) if spacing else d.textlength(s, font=f)
    if spacing:
        tracked(d, ((W - w) / 2, y), s, f, fade(color, a), spacing)
    else:
        d.text(((W - w) / 2, y), s, font=f, fill=fade(color, a))
    im.alpha_composite(layer)


# ---------- scenes ----------

def s_intro(t, dur):
    im = canvas()
    a = ease((t - 0.2) / 0.8)
    rise = int(16 * (1 - a))
    text_center(im, H // 2 - 110 + rise, "WEEKEND EXPERIMENT", font("Inter-Medium", 24), GREY, a, 6)
    text_center(im, H // 2 - 60 + rise, "Photo → 3D", font("InterDisplay-SemiBold", 104), WHITE, a)
    text_center(im, H // 2 + 80 + rise, "Phone photos in. A 3D model out.", font("Inter-Light", 32), GREY, ease((t - 0.7) / 0.8))
    return im


HERO = Image.open("C:/Users/USER/Downloads/harumichi-figure/photo_2026-10-18_09-07-29.jpg").convert("RGB")
HERO_SUBJECT = (360, 300, 615, 960)  # figure box in source pixels


def s_capture(t, dur):
    s = W / HERO.width
    sw, sh = int(HERO.width * s), int(HERO.height * s)
    ox, oy = (sw - W) // 2, int((sh - H) * 0.45)
    im = HERO.resize((sw, sh), Image.LANCZOS).crop((ox, oy, ox + W, oy + H)).convert("RGBA")
    vig = Image.radial_gradient("L").resize((W, H)).point(lambda v: int(min(255, v * 1.1) * 0.75))
    dark = Image.new("RGBA", (W, H), (6, 6, 8, 255))
    dark.putalpha(vig)
    im.alpha_composite(dark)
    x0, y0, x1, y1 = [v * s for v in HERO_SUBJECT]
    x0, x1, y0, y1 = x0 - ox, x1 - ox, y0 - oy, y1 - oy
    lock = ease((t - 0.5) / 0.6)
    grow = 70 * (1 - lock)
    x0, y0, x1, y1 = x0 - grow, y0 - grow, x1 + grow, y1 + grow
    a = ease((t - 0.3) / 0.4) * (1 - ease((t - (dur - 0.5)) / 0.3))
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    c, L, wdt = fade(WHITE, a * 0.9), 46, 3
    for (cx, cy, dx, dy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        d.line((cx, cy, cx + dx * L, cy), fill=c, width=wdt)
        d.line((cx, cy, cx, cy + dy * L), fill=c, width=wdt)
    im.alpha_composite(layer)
    shut = dur - 0.7
    if shut <= t < shut + 0.22:
        k = 1 - abs((t - shut) / 0.11 - 1)
        blk = Image.new("RGBA", im.size, (0, 0, 0, int(150 * k)))
        im.alpha_composite(blk)
    caption(im, t, dur, "01 — CAPTURE", "A few phone photos")
    return im


def s_photos(t, dur):
    im = canvas()
    tw, th, gap = 420, 560, 32
    strip_w = len(FIG_PHOTOS) * (tw + gap) - gap
    x0 = MARGIN - (strip_w - W + 2 * MARGIN) * ease(t / dur)
    y = 330
    for i, p in enumerate(FIG_PHOTOS):
        a = ease((t - i * 0.07) / 0.5)
        if a <= 0:
            continue
        card, pad = shadowed(cover(photo(p), (tw, th)), radius=18, blur=26, alpha=170)
        card.putalpha(Image.eval(card.getchannel("A"), lambda v: int(v * a)))
        im.alpha_composite(card, (int(x0 + i * (tw + gap)) - pad, y - pad + int(20 * (1 - a))))
    caption(im, t, dur, "01 — CAPTURE", "Nine angles, all sides")
    return im


def s_app(t, dur):
    im = canvas()
    fr = Image.open(APP[min(int(t * FPS), len(APP) - 1)]).convert("RGB")
    sw = int(W * 0.92)
    fr = fr.resize((sw, int(sw * fr.height / fr.width)), Image.LANCZOS)
    card, pad = shadowed(fr, radius=20, blur=40, alpha=190)
    im.alpha_composite(card, ((W - fr.width) // 2 - pad, 150 - pad))
    caption(im, t, dur, "02 — BUILD", "Drop them in. Get 3D.", "Build takes about a minute, shortened here", bottom=170)
    return im


def s_result(t, dur):
    im = canvas()
    place_model(im, turntable(TT_FIG9, t, 1000), W // 2, 120)
    caption(im, t, dur, "03 — RESULT", "Shape and color from photos")
    return im


def s_plant(t, dur):
    im = canvas()
    place_model(im, turntable(TT_PLANT, t, 980), W // 2, 110)
    caption(im, t, dur, "03 — RESULT", "Works on other objects too")
    return im


def s_compare(t, dur):
    im = canvas()
    for k, (frames, label) in enumerate([(TT_FIG5, "5 PHOTOS"), (TT_FIG9, "9 PHOTOS")]):
        fr = turntable(frames, t, 600, 0.5)
        cx = W // 4 + k * W // 2
        place_model(im, fr, cx, 230)
        d = ImageDraw.Draw(im)
        f = font("Inter-Medium", 22)
        tracked(d, (cx - tracked_width(d, label, f, 5) / 2, 210), label, f, GREY, 5)
    ImageDraw.Draw(im).line((W // 2, 220, W // 2, 860), fill=(52, 54, 62), width=1)
    caption(im, t, dur, "04 — FINDING", "Better face. Weaker arms.", "Angles matter more than the number of photos", bottom=190)
    return im


def s_outro(t, dur):
    im = canvas()
    a = ease((t - 0.2) / 0.8)
    text_center(im, 430, "WEEKEND EXPERIMENT", font("Inter-Medium", 24), GREY, a, 6)
    text_center(im, 480, "Photo → 3D", font("InterDisplay-SemiBold", 96), WHITE, a)
    text_center(im, 640, "Export .glb  →  Blender · Unity", font("Inter-Regular", 32), GREY, ease((t - 0.6) / 0.7))
    text_center(im, 700, "github.com/aphisit-aoonu/photo-to-3d", font("Inter-Regular", 32), WHITE, ease((t - 0.9) / 0.7))
    note = "3D generation: TRELLIS (open source)"
    text_center(im, H - 120, note, font("Inter-Regular", 21), DIM, ease((t - 1.2) / 0.7))
    return im


SCENES = [(s_intro, 2.2), (s_capture, 2.8), (s_photos, 3.2), (s_app, 5.6), (s_result, 4.2),
          (s_plant, 3.2), (s_compare, 4.6), (s_outro, 3.6)]

if __name__ == "__main__":
    out = ROOT / "build/photo-to-3d.mp4"
    w = imageio.get_writer(out, fps=FPS, codec="libx264", macro_block_size=1,
                           pixelformat="yuv420p", ffmpeg_params=["-crf", "17", "-preset", "slow"])
    prev = None
    for fn, dur in SCENES:
        n = int(dur * FPS)
        for i in range(n):
            t = i / FPS
            fr = fn(t, dur).convert("RGB")
            if prev is not None and t < XFADE:
                fr = Image.blend(prev, fr, ease(t / XFADE))
            w.append_data(np.asarray(finish(fr)))
        prev = fn((n - 1) / FPS, dur).convert("RGB")
    w.close()
    print(out)
