# File Drop using Harden Images

A file-upload service built to run on Fedora Hummingbird Linux using Hummingbird's `hi/*` container images. Upload a file through a clean web page (or the command line) and get a download link back.

This project demonstrates how the near-zero CVE goal works in practice: distroless images, multi-stage builds, non-root containers, and an immutable root filesystem. A companion project ([filedrop-hummingbird-unhardened](https://github.com/Brillar0101/filedrop-hummingbird-unhardened)) runs the same app on standard Docker Hub images to show what happens when you step outside the Hummingbird catalog.

## The stack

| Piece | Job | Image |
|-------|-----|-------|
| FastAPI + Uvicorn | The app and web UI | built on `hi/python:3.11` |
| nginx | Reverse proxy | `hi/nginx:latest` |
| PostgreSQL | Stores file details | `hi/postgresql:17` |
| Volume `/data` | Stores the actual files | mounted volume |

The app image uses a multi-stage build (`Containerfile`): dependencies install in a builder stage, then copy into the final distroless image, which has no `pip`. That's how a real framework runs on a distroless Hummingbird image.

## Three ways to run it

### See the UI right now (any machine, no Hummingbird)

```bash
python3 local_demo.py
# open http://127.0.0.1:8087/
```

A stdlib-only stand-in that shows the exact UI and real upload/download. For previewing only.

### Run on the real Hummingbird images (Linux with Podman)

```bash
podman-compose up -d
# open http://localhost:8090/
```

Builds the app on `hi/python` and runs the full stack on the Hummingbird images.

### Deploy on a Hummingbird VM

See [`deploy/README.md`](./deploy/README.md). It builds and boots a Hummingbird VM, then deploys the three-container stack on it. This step needs a Linux host with KVM (a Fedora machine works perfectly).

## Verify the CVE posture

Scan the app image to see the actual CVE count:

```bash
grype filedrop_app:latest
```

Compare with the [unhardened version](https://github.com/Brillar0101/filedrop-hummingbird-unhardened) to see the difference that distroless Hummingbird images make.

## Docs

- [`ARCHITECTURE.md`](./ARCHITECTURE.md) - components, deployment topology, build pipeline, security model, and key decisions
- [`DEMO.md`](./DEMO.md) - walkthrough with screenshots showing Hummingbird in action
- [`deploy/README.md`](./deploy/README.md) - deploy on a Hummingbird VM

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Covers the HTML rendering, including the filename-escaping (XSS) safeguard.

## Notes

- Image tags checked against the live registry: `hi/python:3.11`, `hi/python:3.11-builder`, `hi/nginx:latest`, `hi/postgresql:17`. Note `hi/postgresql:16` does not exist, and `hi/mysql` is not in the catalog (this project uses PostgreSQL on purpose).
- Uploaded files go to the `/data` volume, never the read-only root, so the system stays locked even while it accepts untrusted files.
- `DATABASE_URL` is required from the environment (no hardcoded secret in the app). Set `POSTGRES_PASSWORD` before any real use.
- Uploads are streamed to disk and capped at `MAX_UPLOAD_BYTES` (default 50 MB). The app has no authentication by design . Add a gateway/auth layer before exposing it to untrusted users.
