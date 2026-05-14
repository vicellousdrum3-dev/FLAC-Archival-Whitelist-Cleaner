import os
import shutil
import subprocess
import uuid
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

app = FastAPI(title="FLAC Archival Whitelist Cleaner")

SCRIPT_PATH = Path("/app/flac_archival_whitelist_recursive.sh")


def get_base_dir() -> Path:
    preferred = Path(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", os.getenv("DATA_DIR", "/data"))) / "jobs"
    try:
        preferred.mkdir(parents=True, exist_ok=True)
        return preferred
    except Exception:
        fallback = Path("/tmp/flac-cleaner-jobs")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


BASE_DIR = get_base_dir()


def safe_extract_zip(zip_path: Path, destination: Path) -> None:
    """Extract a zip file while preventing path traversal."""
    destination_resolved = destination.resolve()
    with ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not str(target).startswith(str(destination_resolved)):
                raise ValueError(f"Percorso non sicuro nello ZIP: {member.filename}")
        archive.extractall(destination)


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
    <!doctype html>
    <html lang="it">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>FLAC Archival Whitelist Cleaner</title>
        <style>
          :root { color-scheme: light dark; }
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            max-width: 820px;
            margin: 36px auto;
            padding: 18px;
            line-height: 1.55;
          }
          .box {
            border: 1px solid #8884;
            border-radius: 16px;
            padding: 24px;
          }
          input, button {
            font-size: 16px;
          }
          button {
            padding: 12px 18px;
            border-radius: 10px;
            border: 1px solid #8886;
            cursor: pointer;
          }
          code {
            background: #8882;
            padding: 2px 6px;
            border-radius: 6px;
          }
          .small { opacity: .75; font-size: 14px; }
        </style>
      </head>
      <body>
        <div class="box">
          <h1>FLAC Archival Whitelist Cleaner</h1>
          <p>
            Carica uno ZIP contenente cartelle con file <code>.flac</code>.
            Il sistema pulisce i metadati, genera un report in ogni cartella e restituisce uno ZIP finale.
          </p>
          <form action="/process" enctype="multipart/form-data" method="post">
            <input name="file" type="file" accept=".zip,application/zip" required>
            <br><br>
            <button type="submit">Carica e processa ZIP</button>
          </form>
          <p class="small">
            Nota: il calcolo <code>AUDIO_PCM_FINGERPRINT_MD5</code> può richiedere tempo su archivi grandi.
            Lavora sempre su copie dei file originali.
          </p>
        </div>
      </body>
    </html>
    """


@app.post("/process")
async def process(file: UploadFile = File(...)):
    filename = file.filename or "upload.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Carica solo un file .zip")

    job_id = str(uuid.uuid4())
    job_dir = BASE_DIR / job_id
    input_dir = job_dir / "input"
    uploaded_zip = job_dir / "upload.zip"
    output_zip_base = job_dir / "flac_archival_cleaned_output"
    output_zip = output_zip_base.with_suffix(".zip")
    log_file = job_dir / "log.txt"

    input_dir.mkdir(parents=True, exist_ok=True)

    with uploaded_zip.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        safe_extract_zip(uploaded_zip, input_dir)
    except BadZipFile:
        raise HTTPException(status_code=400, detail="ZIP non valido o corrotto")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Errore estrazione ZIP: {exc}")

    try:
        result = subprocess.run(
            ["sh", str(SCRIPT_PATH)],
            cwd=input_dir,
            capture_output=True,
            text=True,
            timeout=int(os.getenv("PROCESS_TIMEOUT_SECONDS", "7200")),
        )
    except subprocess.TimeoutExpired:
        log_file.write_text("Errore: elaborazione interrotta per timeout.\n", encoding="utf-8")
        return FileResponse(log_file, media_type="text/plain", filename="errore_timeout_flac.txt")

    log_file.write_text(
        "STDOUT:\n" + result.stdout + "\n\nSTDERR:\n" + result.stderr,
        encoding="utf-8",
        errors="ignore",
    )

    if result.returncode != 0:
        return FileResponse(log_file, media_type="text/plain", filename="errore_elaborazione_flac.txt")

    shutil.make_archive(str(output_zip_base), "zip", input_dir)

    return FileResponse(
        output_zip,
        media_type="application/zip",
        filename="flac_archival_cleaned_output.zip",
    )
