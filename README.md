# File Drop on Fedora Hummingbird

A small file-upload service built to run on **Fedora Hummingbird Linux**, 24/7, with near-zero CVEs. Upload a file through a clean web page (or the command line) and get a download link back. This repo is a complete, self-contained example: the app, the architecture, and the deployment.

## The stack

| Piece | Job | Image |
|------|-----|-------|
| FastAPI + Uvicorn | The app and web UI | built on `hi/python:3.11` |
| nginx | Front door / reverse proxy | `hi/nginx:latest` |
| PostgreSQL | Stores file details | `hi/postgresql:17` |
| Volume `/data` | Stores the actual files | mounted volume |

The app image is built with a **multi-stage build** (`Containerfile`): dependencies install in a builder stage, then copy into the final distroless image, which has no `pip`. That is how a real framework runs on a distroless Hummingbird image.

## What's in this folder

```
filedrop/
  README.md            you are here
  ARCHITECTURE.md      the full architecture (components, topology, security, scaling)
  DEMO.md              short "why Hummingbird" write-up
  app/main.py          the FastAPI app + web UI
  client.py            command-line uploader
  local_demo.py        stdlib-only local runner (preview the UI, no Hummingbird needed)
  Containerfile        multi-stage build on hi/python
  compose.yaml         runs app + nginx + postgres, 24/7
  nginx.conf           reverse proxy config
  requirements.txt     Python dependencies
  deploy/              deploy to a Hummingbird VM (the real thing)
  tests/               unit tests (incl. XSS-escaping regression)
```

## Three ways to run it

### 1. See the UI right now (any machine, no Hummingbird)

```bash
python3 local_demo.py
# open http://127.0.0.1:8087/
```

A stdlib-only stand-in that shows the exact UI and real upload/download. For previewing only.

### 2. Run on the real Hummingbird images (Linux with Podman)

```bash
podman-compose up -d
# open http://localhost:8080/
```

Builds the app on `hi/python` and runs the full stack on the genuine hardened images.

### 3. Deploy on a Hummingbird VM (the real deal)

See [`deploy/README.md`](./deploy/README.md). It builds and boots a Hummingbird VM, then deploys the three-container stack on it. **This step needs a Linux host with KVM (a Fedora machine works perfectly).**

## Docs

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) — components, deployment topology (with diagram), build pipeline, security model, scaling, and the key decisions
- [`DEMO.md`](./DEMO.md) — the short "why Hummingbird is the best fit" write-up
- [`deploy/README.md`](./deploy/README.md) — deploy on a Hummingbird VM

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Covers the HTML rendering, including the filename-escaping (XSS) safeguard.

## Notes

- Image tags checked against the live registry: `hi/python:3.11`, `hi/python:3.11-builder`, `hi/nginx:latest`, `hi/postgresql:17`. Note `hi/postgresql:16` does **not** exist, and `hi/mysql` is **not** in the set (this project uses PostgreSQL on purpose).
- Uploaded files go to the `/data` volume, never the read-only root, so the system stays locked even while it accepts untrusted files.
- `DATABASE_URL` is required from the environment (no hardcoded secret in the app). Set `POSTGRES_PASSWORD` before any real use.
- Uploads are streamed to disk and capped at `MAX_UPLOAD_BYTES` (default 50 MB). The app has **no authentication** by design — add a gateway/auth layer before exposing it to untrusted users.
