"""File Drop — a small FastAPI upload service with a web UI.

Uploaded files go to STORE (a mounted volume). Metadata goes to PostgreSQL.
Real stack: FastAPI + Uvicorn, behind nginx, with PostgreSQL.
"""

from __future__ import annotations

import html
import os
import secrets
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Iterator

import psycopg2
from psycopg2 import pool as pg_pool
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

STORE = os.environ.get("STORE_DIR", "/data")
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))  # 50 MB
CHUNK = 1024 * 1024  # 1 MB streaming chunk

_pool: pg_pool.SimpleConnectionPool | None = None


def _dsn() -> str:
    """Read the database connection string from the environment (no hardcoded secret)."""
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set; provide it via the environment.")
    return dsn


@contextmanager
def get_conn() -> Iterator["psycopg2.extensions.connection"]:
    """Borrow a pooled connection, commit on success, roll back on error, return to pool."""
    if _pool is None:
        raise RuntimeError("connection pool is not initialized")
    conn = _pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


def _init_pool(retries: int = 30, delay: float = 1.0) -> None:
    """Create the connection pool, retrying while the database comes up."""
    global _pool
    last_err: Exception | None = None
    for _ in range(retries):
        try:
            _pool = pg_pool.SimpleConnectionPool(1, 10, _dsn())
            return
        except psycopg2.OperationalError as err:  # database not ready yet
            last_err = err
            time.sleep(delay)
    raise RuntimeError(f"could not connect to the database: {last_err}")


def _init_schema() -> None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                size BIGINT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )"""
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> Iterator[None]:
    os.makedirs(STORE, exist_ok=True)
    _init_pool()
    _init_schema()
    yield
    if _pool is not None:
        _pool.closeall()


app = FastAPI(lifespan=lifespan)


def list_files() -> list[tuple[str, str, int]]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, name, size FROM files ORDER BY created_at DESC")
        return cur.fetchall()


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>File Drop</title>
<style>
  :root { --line:#e4e4e7; --muted:#6b7280; --fg:#111; }
  body { font-family: system-ui, -apple-system, sans-serif; color:var(--fg);
         max-width:640px; margin:64px auto; padding:0 20px; line-height:1.5; }
  h1 { font-size:20px; font-weight:600; margin:0 0 24px; }
  form { display:flex; gap:8px; margin-bottom:32px; }
  input[type=file] { flex:1; }
  button { padding:8px 16px; border:1px solid var(--fg); background:var(--fg);
           color:#fff; border-radius:6px; cursor:pointer; font-size:14px; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th { text-align:left; color:var(--muted); font-weight:500;
       border-bottom:1px solid var(--line); padding:8px 0; }
  td { border-bottom:1px solid var(--line); padding:10px 0; }
  td.size, th.size { text-align:right; color:var(--muted); padding-right:32px; }
  td.dl, th.dl { text-align:right; white-space:nowrap; }
  a { color:#2563eb; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .empty { color:var(--muted); padding:24px 0; text-align:center; }
</style>
</head>
<body>
  <h1>File Drop</h1>
  <form action="/upload" method="post" enctype="multipart/form-data">
    <input type="file" name="file" required>
    <button type="submit">Upload</button>
  </form>
  <table>
    <tr><th>File</th><th class="size">Size</th><th class="dl"></th></tr>
    {rows}
  </table>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    files = list_files()
    if files:
        rows = "".join(
            f"<tr><td>{html.escape(name)}</td>"
            f'<td class="size">{size:,} B</td>'
            f'<td class="dl"><a href="/file/{html.escape(fid)}">Download</a></td></tr>'
            for fid, name, size in files
        )
    else:
        rows = '<tr><td colspan="3" class="empty">No files yet</td></tr>'
    return PAGE.replace("{rows}", rows)


@app.post("/upload")
async def upload(file: UploadFile) -> RedirectResponse:
    file_id = secrets.token_urlsafe(8)
    name = os.path.basename(file.filename or "file")  # strip any path, never empty
    dest = os.path.join(STORE, file_id)

    size = 0
    with open(dest, "wb") as out:
        while chunk := await file.read(CHUNK):  # stream, do not load whole file in memory
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                out.close()
                os.remove(dest)
                raise HTTPException(status_code=413, detail="file too large")
            out.write(chunk)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO files (id, name, size) VALUES (%s, %s, %s)",
            (file_id, name, size),
        )
    return RedirectResponse("/", status_code=303)


@app.get("/file/{file_id}")
def download(file_id: str) -> FileResponse:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT name FROM files WHERE id = %s", (file_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    path = os.path.join(STORE, os.path.basename(file_id))
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path, filename=row[0])
