# File Drop on Fedora Hummingbird Linux (hardened)

The goal of this project was to boot the new Fedora Hummingbird Linux bootc
image OS and prove that a real, internet-facing workload runs on it the way
the platform intends: distroless `hi/*` container images, multi-stage builds,
non-root containers, and an immutable host. The workload is File Drop, a
file-upload service: upload a file through a web page or the command line,
get a download link back.

A companion project, [filedrop-hummingbird-unhardened](https://github.com/Brillar0101/filedrop-hummingbird-unhardened),
runs the same app on the same Hummingbird OS using standard Docker Hub
images, so the two repos together show exactly what the hardened images buy
you and what stepping outside the catalog costs.

## The stack

| Piece | Job | Image |
|-------|-----|-------|
| FastAPI + Uvicorn | The app and web UI | built on `hi/python:3.11` |
| nginx | Reverse proxy, the only exposed port | `hi/nginx:latest` |
| PostgreSQL | Stores file metadata | `hi/postgresql:17` |
| Volume `/data` | Stores the actual file bytes | mounted volume |

The app image is a multi-stage build (`Containerfile`): dependencies install
in `hi/python:3.11-builder`, then copy into the distroless final image, which
has no `pip`, no shell, and no package manager. That is how a real framework
runs on a distroless image.

## Findings

These came out of actually booting the OS and running the stack, not from
reading about it:

- **The bootc model is real and strict.** `bootc status` shows the host
  running the Hummingbird OS image, and `dnf install` fails because the root
  filesystem is read-only. You do not install software on this host; you run
  containers, and the OS itself updates atomically (`bootc upgrade`) with
  instant rollback (`bootc rollback`). Screenshots in `DEMO.md`.
- **The CVE difference is dramatic and measurable.** The `hi/*` images scan
  near zero with grype. The companion project's app image, same app on
  `node:22`, scanned at 1,479 vulnerabilities including critical and high.
  The difference is entirely the base images, not the application code.
- **The images are small.** The `hi/*` images run 51 to 196 MB. The Docker
  Hub equivalents in the companion project run 831 MB to 1.3 GB.
- **No shell and no man pages, anywhere: is that a problem?** Distroless
  containers have no `bash`, no `man`, no `curl`, and the lean host does not
  offer much more. The honest verdict from working this way: it is not a
  problem for running the service, and it is precisely why the attack surface
  is so small, but it does change how you debug. `podman exec` into a
  distroless container gets you nothing because there is no shell to exec.
  You work from outside instead: `podman logs`, `podman cp`, inspecting
  volumes from the host, or attaching a separate debug container when you
  really need tools. Treat it as a discipline change, not a blocker.
- **The catalog decides your stack.** There is no `hi/mysql` and no
  `hi/node`, and `hi/postgresql:16` does not exist (17 does). This project
  uses PostgreSQL and FastAPI because those are the supported images; a team
  that mandates MySQL would have to leave the catalog and give up the
  near-zero CVE posture. Check tags against the live registry before
  building.

## Three ways to run it

Preview the UI on any machine with nothing but Python:

```bash
python3 local_demo.py
# open http://127.0.0.1:8087/
```

Run the real stack on the Hummingbird images (Linux with Podman):

```bash
podman-compose up -d
# open http://localhost:8090/
```

Deploy on an actual Hummingbird VM (Linux host with KVM): see
[`deploy/README.md`](./deploy/README.md). It builds the bootc disk image,
boots the VM, and deploys the three-container stack onto it.

Verify the CVE posture yourself:

```bash
grype filedrop_app:latest
```

## What every file does

| File | What it is |
|------|------------|
| `app/main.py` | The FastAPI service: upload, download, listing, HTML UI |
| `client.py` | Command-line client: upload a file, print the download link |
| `local_demo.py` | Stdlib-only stand-in that serves the same UI for previewing |
| `Containerfile` | Multi-stage build: deps in the builder, distroless final image |
| `compose.yaml` | The three-container stack for `podman-compose` |
| `nginx.conf` | Reverse proxy config: upload cap, security headers |
| `requirements.txt` | App dependencies |
| `requirements-dev.txt` | Test dependencies (pytest) |
| `tests/test_app.py` | Tests, including the filename-escaping (XSS) safeguard |
| `deploy/01-build-and-boot-vm.sh` | Builds the Hummingbird bootc disk image and boots the VM |
| `deploy/02-deploy-filedrop.sh` | Deploys the container stack onto the running VM |
| `deploy/bib-config.toml` | bootc-image-builder config for the VM disk image |
| `deploy/README.md` | The VM deployment walkthrough |
| `ARCHITECTURE.md` | Components, topology and build-pipeline diagrams, security model, key decisions |
| `DEMO.md` | Screenshot walkthrough of the running system |
| `screenshots/` | Evidence: `bootc status`, blocked `dnf`, `podman ps`, image sizes, the UI, the grype scan |

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Notes

- Uploaded files go to the `/data` volume, never the read-only root, so the
  system stays locked down even while accepting untrusted files.
- `DATABASE_URL` comes from the environment; there is no hardcoded secret.
  Set `POSTGRES_PASSWORD` before any real use.
- Uploads stream to disk and are capped at `MAX_UPLOAD_BYTES` (default
  50 MB). The app has no authentication by design; put a gateway in front
  before exposing it to untrusted users.
