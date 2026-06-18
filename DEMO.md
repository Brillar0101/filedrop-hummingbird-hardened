# File Drop Demo: Fedora Hummingbird Linux

File Drop is a small upload service with a real stack: FastAPI, nginx, PostgreSQL, and a command-line client. It runs on Fedora Hummingbird Linux and stays up 24/7, taking files from the internet with the smallest attack surface possible.

## Hummingbird vs traditional Fedora

On a traditional Fedora server, you install packages, pull whatever images you want, and the system accumulates software and drift over time. On Hummingbird, the host OS is read-only and image-based. You don't install packages on it. You run your workload as containers.

The `bootc status` command confirms the VM is running the Hummingbird OS image:

![bootc status showing the Hummingbird OS image](screenshots/hb-bootc-status.png)

And when you try to install a package with `dnf`, the system refuses. The root filesystem is read-only:

![dnf install blocked — the bootc system is configured to be read-only](screenshots/hb-dnf-blocked.png)

## The running stack

After deploying on a Hummingbird VM (see `deploy/README.md`), three containers are running, all on Hummingbird `hi/*` images:

![podman ps showing db, app, and proxy containers running on hi/* images](screenshots/hb-podman-ps.png)

The distroless Hummingbird images are small because they carry only what the app needs:

![podman images showing hi/* images between 51 MB and 196 MB](screenshots/hb-podman-images.png)

## The UI

Open the browser and the File Drop UI is live. Upload a file and get a download link:

![File Drop web UI running on Hummingbird with uploaded files](screenshots/hb-ui.png)

## CVE scan results

Scan the app image to verify the near-zero CVE claim:

```bash
grype filedrop_app:latest
```

![grype scan of the hummingbird app image showing minimal CVEs](screenshots/hb-grype-scan.png)

The vulnerabilities that do appear come from the Python dependencies, not from unused OS packages. There are no unused OS packages because there are no unused OS packages.

A companion project ([filedrop-hummingbird-unhardened](https://github.com/Brillar0101/filedrop-hummingbird-unhardened)) runs the same app on the same Hummingbird host, but using standard Docker Hub images. Scan that image too and compare the CVE counts. The difference comes from the base images, not the application code.
