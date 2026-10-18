import os, sys, shutil
from pathlib import Path
from gradio_client import Client, handle_file

env = Path(__file__).resolve().parent.parent / ".env"
token = None
if env.exists():
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith("HF_TOKEN="):
            token = line.split("=", 1)[1].strip()

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
imgs = sys.argv[2:]
c = Client("trellis-community/TRELLIS", token=token)
c.predict(api_name="/start_session")
res = c.predict(
    image=handle_file(imgs[0]),
    multiimages=[{"image": handle_file(p), "caption": None} for p in imgs],
    seed=0, ss_guidance_strength=7.5, ss_sampling_steps=12,
    slat_guidance_strength=3.0, slat_sampling_steps=12,
    multiimage_algo=os.environ.get("ALGO", "stochastic"), mesh_simplify=0.95, texture_size=int(os.environ.get("TEX", "1024")),
    api_name="/generate_and_extract_glb",
)
print(res)
for r in res:
    p = r.get("value") if isinstance(r, dict) else r
    if isinstance(p, dict):
        p = p.get("path") or p.get("video")
    if isinstance(p, str) and p.endswith(".mp4"):
        shutil.copy(p, out / "preview.mp4")
    if isinstance(p, str) and p.endswith(".glb"):
        shutil.copy(p, out / "model.glb"); print("saved", out / "model.glb")
        break
