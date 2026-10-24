import glob
import subprocess
from pathlib import Path

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS = 1080, 1350, 30
FONTS = ROOT / "assets/fonts"
WHITE, GREY, DIM = (244, 242, 238), (160, 156, 150), (100, 97, 94)
ACCENT = (255, 178, 122)
MARGIN = 84
XFADE = 0.3
BPM = 84  # scenes are cut on the beat of build/music/lofi.wav
BEAT = 60 / BPM
MUSIC = ROOT / "build/music/lofi.wav"


def font(name, size):
    return ImageFont.truetype(str(FONTS / f"{name}.ttf"), size)


CUT_FIG = sorted(glob.glob(str(ROOT / "cutouts/figure_v2/*.png")))
CUT_PLANT = sorted(glob.glob(str(ROOT / "cutouts/plant/*.png")))
TT_FIG5 = sorted(glob.glob(str(ROOT / "build/tt_figure/*.png")))
TT_FIG9 = sorted(glob.glob(str(ROOT / "build/tt_figure_v2/*.png")))
TT_PLANT = sorted(glob.glob(str(ROOT / "build/tt_plant/*.png")))
APP = sorted(glob.glob(str(ROOT / "build/app_frames/*.png")))


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def pop(t):
    # quick rise with a small overshoot, settles at 1
    t = max(0.0, min(1.0, t))
    return 1 + 2.2 * (t - 1) ** 3 + 1.2 * (t - 1) ** 2


def background():
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / W) ** 2 + ((y - H * 0.52) / H) ** 2 * 1.6)
    glow = np.clip(1 - d * 1.9, 0, 1) ** 2
    base = np.full((H, W, 3), 9.0)
    return (base + glow[..., None] * np.array([46, 30, 22])).astype(np.float32)


BASE = background()
_rng = np.random.default_rng(7)


def finish(im):
    # fine grain hides gradient banding in the glow
    a = np.asarray(im, dtype=np.float32) + _rng.normal(0, 1.6, (H, W, 1))
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


def text_center(im, y, s, f, color, a, spacing=0):
    if a <= 0:
        return
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w = tracked_width(d, s, f, spacing) if spacing else d.textlength(s, font=f)
    if spacing:
        tracked(d, ((W - w) / 2, y), s, f, fade(color, a), spacing)
    else:
        d.text(((W - w) / 2, y), s, font=f, fill=fade(color, a))
    im.alpha_composite(layer)


def heading(im, t, dur, label, title, note=None, y=110):
    a = ease_out((t - 0.1) / 0.45) * (1 - ease((t - (dur - 0.3)) / 0.3))
    rise = int(18 * (1 - a))
    text_center(im, y + rise, label, font("Inter-SemiBold", 22), ACCENT, a, 6)
    text_center(im, y + 40 + rise, title, font("InterDisplay-SemiBold", 60), WHITE, a)
    if note:
        text_center(im, y + 124 + rise, note, font("Inter-Regular", 26), GREY, a * ease((t - 0.35) / 0.4))


def card(path, size):
    im = Image.open(path).convert("RGBA")
    bbox = im.getchannel("A").getbbox()
    im = im.crop(bbox)
    pad = int(size * 0.1)
    im.thumbnail((size - 2 * pad, size - 2 * pad), Image.LANCZOS)
    c = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, size - 1, size - 1), int(size * 0.09), fill=(24, 22, 21, 255), outline=(48, 44, 41, 255), width=2)
    c.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    return c


def paste_scaled(im, src, cx, cy, s, a):
    if a <= 0 or s <= 0.01:
        return
    w, h = max(1, int(src.width * s)), max(1, int(src.height * s))
    fr = src.resize((w, h), Image.LANCZOS)
    if a < 1:
        fr.putalpha(fr.getchannel("A").point(lambda v: int(v * a)))
    im.alpha_composite(fr, (int(cx - w / 2), int(cy - h / 2)))


def turntable(frames, t, size, speed=0.4, start=-16):
    # frame 0 faces the camera; the AI-guessed back stays mostly out of view
    i = int(t * FPS * speed + start) % len(frames)
    return Image.open(frames[i]).convert("RGBA").resize((size, size), Image.LANCZOS)


def place_model(im, fr, cx, top, a=1.0):
    if a < 1:
        fr = fr.copy()
        fr.putalpha(fr.getchannel("A").point(lambda v: int(v * a)))
    im.alpha_composite(fr, (cx - fr.width // 2, top))
    refl = fr.transpose(Image.FLIP_TOP_BOTTOM)
    grad = Image.linear_gradient("L").resize(refl.size).point(lambda v: int(max(0, 255 - v * 3.2) * 0.14))
    refl.putalpha(Image.fromarray(np.minimum(np.asarray(refl.getchannel("A")), np.asarray(grad))))
    bbox = fr.getchannel("A").getbbox()
    bottom = bbox[3] if bbox else fr.height
    im.alpha_composite(refl.crop((0, fr.height - bottom, fr.width, fr.height)), (cx - fr.width // 2, top + bottom))


def grid_slots(n, cols, size, gap, cy):
    rows = (n + cols - 1) // cols
    out = []
    for i in range(n):
        r, c = divmod(i, cols)
        in_row = min(cols, n - r * cols)
        x0 = (W - (in_row * size + (in_row - 1) * gap)) / 2
        out.append((x0 + c * (size + gap) + size / 2, cy - (rows * size + (rows - 1) * gap) / 2 + r * (size + gap) + size / 2))
    return out


# ---------- scenes ----------

FIG_CARDS = [card(p, 250) for p in CUT_FIG]
FIG_SLOTS = grid_slots(len(FIG_CARDS), 3, 250, 26, 760)
PLANT_CARDS = [card(p, 300) for p in CUT_PLANT]
PLANT_SLOTS = grid_slots(len(PLANT_CARDS), 2, 300, 28, 760)


def s_hook(t, dur):
    im = canvas()
    place_model(im, turntable(TT_FIG9, t, 820), W // 2, 400, ease((t - 0.05) / 0.5))
    a = ease_out((t - 0.2) / 0.6)
    text_center(im, 120 + int(16 * (1 - a)), "Photo → 3D", font("InterDisplay-SemiBold", 108), WHITE, a)
    b = ease_out((t - 0.75) / 0.6)
    text_center(im, 268 + int(12 * (1 - b)), "Phone photos in. A 3D model out.", font("Inter-Light", 34), GREY, b)
    return im


def grid_in(t, cards, slots):
    im = canvas()
    for i, (c, (x, y)) in enumerate(zip(cards, slots)):
        k = (t - 0.15 - i * BEAT / 4) / 0.38
        paste_scaled(im, c, x, y + 24 * (1 - ease_out(k)), 0.86 + 0.14 * pop(k), ease(k * 1.6))
    return im


def merge(t, dur, cards, slots, frames, size, top):
    im = canvas()
    cx, cy = W / 2, top + size * 0.5
    u = ease((t - 0.05) / (dur * 0.55))
    for i, (c, (x, y)) in enumerate(zip(cards, slots)):
        lag = ease((t - 0.05 - i * 0.025) / (dur * 0.55))
        paste_scaled(im, c, x + (cx - x) * lag, y + (cy - y) * lag, 1 - 0.75 * lag, 1 - ease((lag - 0.55) / 0.45))
    m = ease_out((t - dur * 0.35) / (dur * 0.4))
    if m > 0:
        fr = turntable(frames, t - dur * 0.35, int(size * (0.86 + 0.14 * m)))
        place_model(im, fr, W // 2, int(top + size * 0.07 * (1 - m)), m)
    return im, u


def s_grid(t, dur):
    im = grid_in(t, FIG_CARDS, FIG_SLOTS)
    heading(im, t, dur, "INPUT", "9 phone photos", "Background removed, all sides")
    return im


def s_merge(t, dur):
    im, _ = merge(t, dur, FIG_CARDS, FIG_SLOTS, TT_FIG9, 860, 330)
    heading(im, t, dur, "BUILD", "Combined into one model")
    return im


def s_app(t, dur):
    im = canvas()
    fr = Image.open(APP[min(int(t / dur * len(APP)), len(APP) - 1)]).convert("RGBA")
    sw = int(W * 0.9)
    fr = fr.resize((sw, int(sw * fr.height / fr.width)), Image.LANCZOS)
    mask = Image.new("L", fr.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fr.width - 1, fr.height - 1), 22, fill=255)
    fr.putalpha(mask)
    a = ease_out((t - 0.05) / 0.4)
    paste_scaled(im, fr, W / 2, 420 + fr.height / 2 + 20 * (1 - a), 1, a)
    heading(im, t, dur, "THE APP", "Drop photos. Get 3D.", "Real app, sped up · about a minute")
    return im


def s_result(t, dur):
    im = canvas()
    place_model(im, turntable(TT_FIG9, t, 940, 0.4, -24), W // 2, 340)
    heading(im, t, dur, "RESULT", "Shape and color")
    return im


def s_plant_grid(t, dur):
    im = grid_in(t, PLANT_CARDS, PLANT_SLOTS)
    heading(im, t, dur, "ANOTHER OBJECT", "A potted plant")
    return im


def s_plant_merge(t, dur):
    im, _ = merge(t, dur, PLANT_CARDS, PLANT_SLOTS, TT_PLANT, 900, 320)
    heading(im, t, dur, "RESULT", "Leaves came out well")
    return im


def s_compare(t, dur):
    im = canvas()
    for k, (frames, label) in enumerate([(TT_FIG5, "5 PHOTOS"), (TT_FIG9, "9 PHOTOS")]):
        a = ease_out((t - 0.1 - k * BEAT / 2) / 0.45)
        cx = W // 4 + k * W // 2
        place_model(im, turntable(frames, t, 560), cx, 470, a)
        text_center_at(im, cx, 440, label, font("Inter-SemiBold", 22), GREY, a, 5)
    heading(im, t, dur, "FINDING", "Better face. Weaker arms.", "Angles matter more than photo count")
    return im


def text_center_at(im, cx, y, s, f, color, a, spacing):
    if a <= 0:
        return
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    tracked(d, (cx - tracked_width(d, s, f, spacing) / 2, y), s, f, fade(color, a), spacing)
    im.alpha_composite(layer)


def s_outro(t, dur):
    im = canvas()
    a = ease_out((t - 0.1) / 0.6)
    text_center(im, 440 + int(14 * (1 - a)), "WEEKEND EXPERIMENT", font("Inter-SemiBold", 22), ACCENT, a, 6)
    text_center(im, 486 + int(14 * (1 - a)), "Photo → 3D", font("InterDisplay-SemiBold", 100), WHITE, a)
    text_center(im, 650, "Export .glb  →  Blender · Unity", font("Inter-Regular", 32), GREY, ease((t - 0.5) / 0.6))
    text_center(im, 706, "github.com/aphisit-aoonu/photo-to-3d", font("Inter-Medium", 32), WHITE, ease((t - 0.8) / 0.6))
    text_center(im, H - 120, "3D generation: TRELLIS (open source) · Music: made in code", font("Inter-Regular", 21), DIM,
                ease((t - 1.1) / 0.6))
    return im


SCENES = [(s_hook, 4), (s_grid, 4), (s_merge, 3), (s_app, 6), (s_result, 5),
          (s_plant_grid, 3), (s_plant_merge, 5), (s_compare, 6), (s_outro, 6)]  # lengths in beats

if __name__ == "__main__":
    silent = ROOT / "build/_silent.mp4"
    out = ROOT / "build/photo-to-3d.mp4"
    w = imageio.get_writer(silent, fps=FPS, codec="libx264", macro_block_size=1,
                           pixelformat="yuv420p", ffmpeg_params=["-crf", "17", "-preset", "slow"])
    prev, frame = None, 0
    clock = 0.0
    for fn, beats in SCENES:
        clock += beats * BEAT
        start, n = frame, round(clock * FPS) - frame
        for i in range(n):
            t = i / FPS
            fr = fn(t, n / FPS).convert("RGB")
            if prev is not None and t < XFADE:
                fr = Image.blend(prev, fr, ease(t / XFADE))
            w.append_data(np.asarray(finish(fr)))
        frame += n
        prev = fn((n - 1) / FPS, n / FPS).convert("RGB")
    w.close()
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(silent), "-i", str(MUSIC),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", "volume=0.8", "-shortest", str(out)], check=True)
    silent.unlink()
    print(out)
