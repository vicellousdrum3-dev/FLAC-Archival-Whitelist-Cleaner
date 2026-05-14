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
    """Extract a ZIP file while preventing path traversal."""
    destination_resolved = destination.resolve()

    with ZipFile(zip_path, "r") as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if os.path.commonpath([str(destination_resolved), str(target)]) != str(destination_resolved):
                raise ValueError(f"Unsafe path inside ZIP: {member.filename}")

        archive.extractall(destination)


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.get("/", response_class=HTMLResponse)
def home(lang: str = "it") -> str:
    if lang not in ("it", "en"):
        lang = "it"

    if lang == "en":
        page_lang = "en"
        language_label = "Language"
        title = "FLAC Archival Whitelist Cleaner"
        intro = """
          Upload a ZIP archive containing one or more folders with <code>.flac</code> files.
          The system recursively analyzes the archive structure, performs controlled metadata cleaning,
          removes non-archival references from streaming services, downloaders or encoders,
          generates a technical report inside each processed folder, and returns a final ZIP ready for download.
        """
        audio_integrity = """
          The original audio file is never converted, re-encoded, resampled or altered in its audio content.
          The procedure works exclusively on textual metadata, preserving embedded cover artwork and official
          archival tags already present whenever available.
        """
        target_users = """
          This service is designed for audiophiles, collectors and users who want to maintain a clean,
          organized and technically documented <strong>hi-res</strong> and <strong>lossless</strong> digital archive.
        """
        button_text = "Upload and process ZIP"
        note = """
          Note: the <code>AUDIO_PCM_FINGERPRINT_MD5</code> calculation may take time on large archives.
          Always work on copies of your original files.
        """
    else:
        page_lang = "it"
        language_label = "Lingua"
        title = "FLAC Archival Whitelist Cleaner"
        intro = """
          Carica uno ZIP contenente una o più cartelle con file <code>.flac</code>.
          Il sistema analizza ricorsivamente la struttura dell’archivio, esegue una pulizia controllata dei metadati,
          rimuove i riferimenti non archivistici provenienti da servizi di streaming, downloader o encoder,
          genera un report tecnico in ogni cartella elaborata e restituisce uno ZIP finale pronto per il download.
        """
        audio_integrity = """
          Il file audio originale non viene convertito, ricodificato, ricampionato o alterato nel contenuto sonoro.
          La procedura interviene esclusivamente sui metadati testuali, preservando le cover integrate e i tag
          ufficiali/archivistici già presenti quando disponibili.
        """
        target_users = """
          Il servizio è pensato per audiofili, collezionisti e utenti che desiderano mantenere un archivio digitale
          <strong>hi-res</strong> e <strong>lossless</strong> pulito, ordinato e tecnicamente documentato.
        """
        button_text = "Carica e processa ZIP"
        note = """
          Nota: il calcolo <code>AUDIO_PCM_FINGERPRINT_MD5</code> può richiedere tempo su archivi grandi.
          Lavora sempre su copie dei file originali.
        """

    it_active = "active" if lang == "it" else ""
    en_active = "active" if lang == "en" else ""

    return f"""
    <!doctype html>
    <html lang="{page_lang}">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{title}</title>
        <style>
          :root {{ color-scheme: light dark; }}
          body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            max-width: 880px;
            margin: 36px auto;
            padding: 18px;
            line-height: 1.58;
          }}
          .box {{
            border: 1px solid #8884;
            border-radius: 16px;
            padding: 26px;
          }}
          .language {{
            display: flex;
            justify-content: flex-end;
            align-items: center;
            gap: 10px;
            margin-bottom: 18px;
            font-size: 14px;
          }}
          .language a {{
            text-decoration: none;
            border: 1px solid #8885;
            border-radius: 999px;
            padding: 6px 12px;
            color: inherit;
          }}
          .language a.active {{
            font-weight: 700;
            background: #8882;
          }}
          .notice {{
            border-left: 4px solid #8886;
            padding-left: 14px;
            margin: 20px 0;
          }}
          input, button, .button {{
            font-size: 16px;
          }}
          button, .button {{
            display: inline-block;
            padding: 12px 18px;
            border-radius: 10px;
            border: 1px solid #8886;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
          }}
          code {{
            background: #8882;
            padding: 2px 6px;
            border-radius: 6px;
          }}
          .small {{
            opacity: .75;
            font-size: 14px;
          }}
        </style>
      </head>
      <body>
        <div class="box">
          <div class="language">
            <span>{language_label}:</span>
            <a href="/?lang=it" class="{it_active}">Italiano</a>
            <a href="/?lang=en" class="{en_active}">English</a>
          </div>

          <h1>{title}</h1>

          <p>{intro}</p>

          <div class="notice">
            <p>{audio_integrity}</p>
            <p>{target_users}</p>
          </div>

          <form action="/process?lang={lang}" enctype="multipart/form-data" method="post">
            <input name="file" type="file" accept=".zip,application/zip" required>
            <br><br>
            <button type="submit">{button_text}</button>
          </form>

          <p class="small">{note}</p>
        </div>
      </body>
    </html>
    """


@app.post("/process", response_class=HTMLResponse)
async def process(file: UploadFile = File(...), lang: str = "it"):
    filename = file.filename or "upload.zip"
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload only a .zip file")

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
        raise HTTPException(status_code=400, detail="Invalid or corrupted ZIP file")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"ZIP extraction error: {exc}")

    try:
        result = subprocess.run(
            ["sh", str(SCRIPT_PATH)],
            cwd=input_dir,
            capture_output=True,
            text=True,
            timeout=int(os.getenv("PROCESS_TIMEOUT_SECONDS", "7200")),
        )
    except subprocess.TimeoutExpired:
        log_file.write_text("Error: processing stopped because of timeout.\n", encoding="utf-8")
        return HTMLResponse(
            f"""
            <h1>Processing timeout</h1>
            <p>The operation took too long.</p>
            <p><a href="/log/{job_id}">Download error log</a></p>
            """,
            status_code=500,
        )

    log_file.write_text(
        "STDOUT:\n" + result.stdout + "\n\nSTDERR:\n" + result.stderr,
        encoding="utf-8",
        errors="ignore",
    )

    if result.returncode != 0:
        return HTMLResponse(
            f"""
            <h1>Processing error</h1>
            <p>The FLAC cleaning script returned an error.</p>
            <p><a href="/log/{job_id}">Download processing log</a></p>
            """,
            status_code=500,
        )

    shutil.make_archive(str(output_zip_base), "zip", input_dir)

    if lang == "en":
        title = "Processing completed"
        message = "Your cleaned FLAC archive is ready."
        download_text = "Download cleaned ZIP"
        home_text = "Back to home"
    else:
        title = "Elaborazione completata"
        message = "Il tuo archivio FLAC pulito è pronto."
        download_text = "Scarica ZIP pulito"
        home_text = "Torna alla home"

    return f"""
    <!doctype html>
    <html lang="{lang}">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>{title}</title>
        <style>
          :root {{ color-scheme: light dark; }}
          body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            max-width: 760px;
            margin: 36px auto;
            padding: 18px;
            line-height: 1.58;
          }}
          .box {{
            border: 1px solid #8884;
            border-radius: 16px;
            padding: 26px;
          }}
          a.button {{
            display: inline-block;
            padding: 12px 18px;
            border-radius: 10px;
            border: 1px solid #8886;
            text-decoration: none;
            color: inherit;
            margin-right: 10px;
          }}
        </style>
      </head>
      <body>
        <div class="box">
          <h1>{title}</h1>
          <p>{message}</p>
          <p>
            <a class="button" href="/download/{job_id}">{download_text}</a>
            <a class="button" href="/?lang={lang}">{home_text}</a>
          </p>
        </div>
      </body>
    </html>
    """


@app.get("/download/{job_id}")
def download(job_id: str):
    output_zip = BASE_DIR / job_id / "flac_archival_cleaned_output.zip"

    if not output_zip.exists():
        raise HTTPException(status_code=404, detail="Cleaned ZIP not found")

    return FileResponse(
        output_zip,
        media_type="application/zip",
        filename="flac_archival_cleaned_output.zip",
    )


@app.get("/log/{job_id}")
def download_log(job_id: str):
    log_file = BASE_DIR / job_id / "log.txt"

    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    return FileResponse(
        log_file,
        media_type="text/plain",
        filename="flac_cleaning_log.txt",
    )
