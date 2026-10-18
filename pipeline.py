import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
_session = None


def hf_token():
    env = ROOT / ".env"
    if not env.exists():
        return None
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("HF_TOKEN="):
            return line.split("=", 1)[1].strip()
    return None


def cutout(src: Path, dst: Path):
    global _session
    from rembg import remove, new_session
    if _session is None:
        _session = new_session("birefnet-general")
    out = remove(Image.open(src).convert("RGB"), session=_session)
    out = out.crop(out.getbbox())
    w, h = out.size
    side = int(max(w, h) * 1.1)
    sq = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    sq.paste(out, ((side - w) // 2, (side - h) // 2))
    sq.save(dst)


def build_glb(images: list[Path], out_dir: Path, texture=2048):
    from gradio_client import Client, handle_file
    c = Client("trellis-community/TRELLIS", token=hf_token())
    c.predict(api_name="/start_session")
    res = c.predict(
        image=handle_file(str(images[0])),
        multiimages=[{"image": handle_file(str(p)), "caption": None} for p in images],
        seed=0, ss_guidance_strength=7.5, ss_sampling_steps=12,
        slat_guidance_strength=3.0, slat_sampling_steps=12,
        multiimage_algo="stochastic", mesh_simplify=0.95, texture_size=texture,
        api_name="/generate_and_extract_glb",
    )
    for r in res:
        p = r.get("video") if isinstance(r, dict) else r
        if isinstance(p, str) and p.endswith(".mp4"):
            shutil.copy(p, out_dir / "preview.mp4")
        if isinstance(p, str) and p.endswith(".glb"):
            shutil.copy(p, out_dir / "model.glb")
            return out_dir / "model.glb"
    raise RuntimeError("no .glb in result")
