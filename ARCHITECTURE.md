# Architecture: File Drop on Fedora Hummingbird Linux

## Context

We run a small, internet-facing service that must stay up 24/7, stay patched, and carry as few known security bugs as possible. Together with a companion project ([filedrop-hummingbird-unhardened](https://github.com/Brillar0101/filedrop-hummingbird-unhardened)), this project answers three questions about Fedora Hummingbird Linux:

1. How is the near-zero CVE goal implemented? Through Hummingbird's distroless `hi/*` container images, multi-stage builds, and the disciplines they enforce.
2. What is the impact of using external container repositories? The companion project deploys the same app on the same Hummingbird host using standard Docker Hub images. Compare the CVE scans to see the difference.
3. How does Fedora Hummingbird Linux protect you regardless? The host OS provides an immutable root filesystem, atomic updates via `bootc`, instant rollback, and no host-level package manager. These protections apply whether containers are hardened or not.

The reference workload is File Drop: a file-upload service. A user uploads a file through a web page or the command line and gets back a download link. It is a web app, a reverse proxy, a database, and a place to store files. The architecture generalizes to most services.

## Components

| Component | Responsibility | Hummingbird image |
|-----------|----------------|-------------------|
| App | Business logic + web UI (FastAPI on Uvicorn) | built on `hi/python:3.11` (+ `hi/python:3.11-builder` for deps) |
| Web / Proxy | Front door: TLS termination, reverse proxy, upload size limits | `hi/nginx:latest` |
| Database | Stores file metadata (who, what, when, link) | `hi/postgresql:17` |
| File storage | Holds the actual uploaded bytes | mounted volume at `/data` |
| DB storage | Holds Postgres data files | mounted volume at `/var/lib/postgresql/data` |

The app image carries no package manager. Dependencies are baked in at build time via a multi-stage build. At runtime there is no `pip`, no shell, no way to add software. State lives only in volumes; everything else is immutable.

## Deployment Topology

Three containers on one Hummingbird host, orchestrated by Podman (via `podman-compose`). The same images can also run inside a Hummingbird VM or on bare metal. The container layout is identical because they share the same OCI images.

![Deployment topology — proxy (hi/nginx), app (hi/python:3.11), db (hi/postgresql:17) on a Hummingbird host with file-data and db-data volumes](screenshots/deployment_topology_hummingbird.png)

Traffic flow: client -> host port 8080 -> nginx (proxy) -> app:8080 (Uvicorn) -> Postgres (db:5432) for metadata and the `/data` volume for file bytes.

nginx is the only component that publishes a host port. App and database are reached only over Podman's internal network and are not exposed externally.

## Build Pipeline

The central technique is the multi-stage build (`Containerfile`). It lets a real framework like FastAPI run on a distroless image that has no package manager, and it's the primary mechanism behind the near-zero CVE count.

![Multi-stage build — builder stage installs deps with pip, final distroless stage carries only app code and deps](screenshots/multistage_build_pipeline_hummingbird.png)

The builder stage has everything needed to compile and install Python packages. The final stage has nothing except the runtime and the installed dependencies. Build tools, `pip`, and the shell all stay behind in the builder stage. This is the core reason the final image has so few CVEs: there is almost nothing in it to be vulnerable.

The full pipeline from build to deploy:

1. Build: `podman build -t filedrop_app:latest .` Dependencies resolve in the builder stage and copy into the distroless final image.
2. Scan: `grype filedrop_app:latest`. Verify the CVE count before promoting. This is the gate that backs the near-zero CVE claim.
3. Sign (recommended): `cosign sign` the image and optionally attach the SBOM and scan results as signed attestations.
4. Publish: push the signed image to your registry.
5. Deploy: on the Hummingbird host, `podman-compose up -d` pulls the images and starts all services with `restart: always`.

## Security Model

Defense in depth, with layers at both the container level and the host OS level.

### Container protections (from Hummingbird images)

- Distroless: the runtime image contains only the app and its dependencies. No shell, no package manager, no general-purpose tools. Fewer packages means fewer CVEs.
- Non-root (UID 65532): every component runs as an unprivileged user. A compromised process has no root on the host.
- Immutable, read-only root: the running container filesystem cannot be modified. No quiet file edits, no drive-by package installs.
- Near-zero CVEs, verified: images are scanned (`grype`) before promotion. This is a measured property, not a one-time claim.

### OS protections (from Fedora Hummingbird Linux)

- Immutable host root filesystem: even if an attacker escapes a container, they cannot modify the host OS, install rootkits, or create persistence.
- Atomic OS updates (bootc): the host updates as a whole image. No partial patches, no inconsistent state.
- Instant rollback: `bootc rollback` reverts to the previous known-good OS image.
- No host-level package manager: you cannot `dnf install` on a running Hummingbird host. What ships in the image is what runs.

## Key Decisions

### PostgreSQL, not MySQL

There is no `hi/mysql` image in the Hummingbird catalog. PostgreSQL is the supported relational database with a verified image (`hi/postgresql:17`). If a team mandates MySQL, they'd need to run it from an external repository and lose the near-zero CVE benefit.

### Multi-stage build instead of a runtime package manager

Install dependencies in `hi/python:3.11-builder`, copy into distroless `hi/python:3.11`. This keeps the final image distroless and low-CVE, but every dependency change requires a rebuild, rescan, and redeploy. No hotfixing a live container. That's the intended discipline.

### nginx as the only exposed component

Only the proxy port is published. App and database stay internal. This gives a single ingress point and a central place for TLS, rate limits, and request size caps (`client_max_body_size 50m`).
