# photo-to-3d — spec v0.1 (2026-10-18)

## Goal
Phone photos of a real object → 3D model with color → export for Blender / Unity.
Show it as one LinkedIn post (video) + a public GitHub repo.

## Pipeline
1. Photos (4–5 angles, phone) → `cutouts/` — background removed locally (rembg, BiRefNet)
2. Cutouts → TRELLIS (Hugging Face Space `trellis-community/TRELLIS`, multi-image) → `models/<name>/model.glb` (+ `preview.mp4`)
3. `viewer.html` — rotate the model in the browser (model-viewer)

## Web app (v0.2)
- `app.py` (FastAPI, local) + `web/index.html`
- Dark, clean, no decorative icons. Left: drop / pick photos + thumbnails. Right: 3D viewer (rotate) + Download .glb
- Build = cutout (local) → TRELLIS (HF) → status shown by stage → model appears on the right
- Jobs saved under `jobs/<id>/` (input, cutouts, model.glb); `?job=<id>` reopens a finished job

## Video (LinkedIn, 1080×1350, ~25 s, no audio needed) — v0.2
0. Intro: "WEEKEND EXPERIMENT · Photo → 3D" (framed as the author's experiment, not a tool ad; tool credited once at the end)
1. Opening: real front photo with camera focus brackets (AI hand shot dropped — looked cheap)
2. All real photos appear (camera-shutter flash)
3. The web app: photos on the left → 3D model on the right (captured from the real app)
4. Best model (9 photos) 360° spin, then plant
5. Compare: 5 photos vs 9 photos (face close-up) — more photos = more detail
6. End: export .glb → Blender / Unity + repo link
- Background-removal step is not shown as its own step (internal detail; README explains it)
- Turntables rendered from the real `.glb` files (headless Chrome + model-viewer), not faked

## Honesty
- Show weak spots as they are (small text, glasses/ears blurry, back of plate guessed by AI)
- Post says: more detail needs more / closer photos

## Repo (public)
- Scripts + viewer + plant model + README with the video
- ⛔ Figure model file NOT in repo (licensed character) — shown in the video only
- ⛔ `.env` (HF token) never committed
