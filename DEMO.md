# File Drop — Why Hummingbird Is the Best Fit for an Always-On Upload Server

> **Note:** Hummingbird is new. Image names here come from the project's published material, not a live test. Confirm them in the current docs before you rely on them.

## The project

**File Drop** is a small upload service with a real, industry-standard stack:

- A **FastAPI** app (served by Uvicorn) with a clean web page to upload and download files.
- **nginx** in front of it.
- **PostgreSQL** to hold the file details.
- A command-line client for uploads from a terminal.

The server runs on **Linux**, on **Fedora Hummingbird**, and it must stay up **24 hours a day** so people can upload at any time. It listens on the internet and takes files from strangers, so the goal is an always-on server with **zero known security bugs** and the smallest attack surface possible.

The app code lives in this folder. This guide is about *why the server should run on Hummingbird*.

## Running a real framework on a distroless image

The one thing people worry about: distroless images have no `pip`, so how do you run FastAPI? The answer is a **multi-stage build** (see `filedrop/Containerfile`): install the dependencies in a builder stage, then copy them into the final distroless image. The framework runs, and the final image still has no shell and no package manager. This is the part worth showing, because it proves a real stack works here, not just toy code.

## Why Hummingbird is the best fit

**1. Near-zero CVEs = fewer ways in.** The server is exposed all day and handling untrusted files. Fewer known bugs means fewer holes to exploit.

**2. Distroless = nothing useful for an attacker.** No shell, no package manager. If someone slips in a bad file, there are no tools waiting to help them go further.

**3. Immutable root = the system cannot be changed.** The OS is read-only. Uploaded files go to a mounted volume (`/data`), so you accept untrusted files while the system itself stays locked.

**4. Atomic updates with rollback = patch without downtime.** Update the always-on server and roll back instantly if it breaks. You stay patched and you stay up, which is what 24/7 needs.

## The short demo

The whole stack runs from one file (`filedrop/compose.yaml`), and every piece uses `restart: always` so it keeps running 24/7 on the Linux host.

```bash
# from the filedrop/ folder, on your Hummingbird host
podman-compose up -d
```

Open `http://<server>:8080/` and you get a clean page: pick a file, click Upload, and it appears in the list with a download link. Or upload from the terminal:

```bash
python3 client.py ./notes.txt
```

**The proof:** scan the app image.

```bash
grype filedrop_app:latest
```

A normal base image would list CVEs for an always-on, internet-facing upload server. The Hummingbird image aims for close to none.

## The takeaway

File Drop is a real FastAPI + nginx + PostgreSQL stack that stays online all day and takes files from strangers, so security bugs and downtime are the two biggest risks. Running it on Fedora Hummingbird cuts both: near-zero CVEs and a distroless image shrink the attack surface, the immutable root keeps the system locked while uploads go to a separate volume, and atomic rollback keeps it patchable without going down. For an always-on Linux upload server, that is the best fit.
