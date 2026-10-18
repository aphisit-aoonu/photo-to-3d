# uvicorn app:app --port 8770
import json
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import pipeline

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
JOBS.mkdir(exist_ok=True)
app = FastAPI()
_lock = threading.Lock()  # HF free quota: one build at a time


def _status(job: Path, **kw):
    f = job / "status.json"
    s = json.loads(f.read_text()) if f.exists() else {}
    s.update(kw)
    f.write_text(json.dumps(s))


def _run(job: Path):
    try:
        with _lock:
            ins = sorted((job / "in").iterdir())
            (job / "cut").mkdir(exist_ok=True)
            cuts = []
            for i, p in enumerate(ins, 1):
                _status(job, stage="prepare", detail=f"Preparing photo {i} of {len(ins)}")
                dst = job / "cut" / (p.stem + ".png")
                pipeline.cutout(p, dst)
                cuts.append(dst)
            _status(job, stage="build", detail="Building the 3D model")
            pipeline.build_glb(cuts, job)
            _status(job, stage="done", detail="Done")
    except Exception as e:
        _status(job, stage="error", detail=str(e)[:300])


@app.post("/api/jobs")
async def create_job(files: list[UploadFile] = File(...)):
    if not 1 <= len(files) <= 12:
        raise HTTPException(400, "Use 1 to 12 photos")
    jid = uuid.uuid4().hex[:10]
    job = JOBS / jid
    (job / "in").mkdir(parents=True)
    for i, f in enumerate(files):
        ext = Path(f.filename or "").suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            raise HTTPException(400, f"Not an image: {f.filename}")
        (job / "in" / f"{i:02d}{ext}").write_bytes(await f.read())
    _status(job, stage="queued", detail="Waiting", photos=len(files))
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return {"id": jid}


def _job(jid: str) -> Path:
    job = JOBS / jid
    if not jid.isalnum() or not job.is_dir():
        raise HTTPException(404)
    return job


@app.get("/api/jobs/{jid}")
def job_status(jid: str):
    job = _job(jid)
    s = json.loads((job / "status.json").read_text())
    s["photos"] = [f"/api/jobs/{jid}/in/{p.name}" for p in sorted((job / "in").iterdir())]
    return s


@app.get("/api/jobs/{jid}/in/{name}")
def job_photo(jid: str, name: str):
    p = _job(jid) / "in" / Path(name).name
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p)


@app.get("/api/jobs/{jid}/model.glb")
def job_model(jid: str):
    p = _job(jid) / "model.glb"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="model/gltf-binary", filename="model.glb")


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
