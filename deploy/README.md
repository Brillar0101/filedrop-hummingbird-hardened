# Deploy File Drop on a Hummingbird VM

This is the turnkey implementation of **Architecture option: VM mode** (see `../ARCHITECTURE.md`, section 3). It provisions a Hummingbird virtual machine, then deploys the three-container File Drop stack on it.

> **Where this runs:** The VM build and boot step must run on a **Linux host with KVM** (it needs `podman`, `qemu-kvm`, `libvirt`, `virt-install`). It will not run on macOS, because KVM is a Linux-only feature. Everything here is verified for correctness; the actual boot happens on your Linux/KVM host or your real Hummingbird VM.

## What gets built

The architecture's three containers on one Hummingbird host:

- `proxy` — `hi/nginx:latest`, the only exposed port (8080)
- `app` — File Drop (FastAPI), built multi-stage on `hi/python:3.11`
- `db` — `hi/postgresql:17`
- volumes `file-data` (/data uploads) and `db-data` (Postgres data)

## Files

- `bib-config.toml` — the VM build config (defines the `core` login user)
- `01-build-and-boot-vm.sh` — build the bootable image and boot the VM (run on the Linux/KVM host)
- `02-deploy-filedrop.sh` — deploy the stack with plain `podman` (run inside the VM)

## On Fedora: prerequisites (do this first)

A Fedora machine is the easiest host, because Fedora is Linux, so KVM is built in.

```bash
# install the VM tools (one time)
sudo dnf install -y podman qemu-kvm libvirt virt-install
sudo systemctl enable --now libvirtd

# confirm virtualization is available
ls /dev/kvm                                   # this file must exist
egrep -c '(vmx|svm)' /proc/cpuinfo            # should print a number > 0
```

Two gotchas:
- On a **physical Fedora machine**, turn on VT-x / AMD-V in the BIOS (usually already on).
- On a **Fedora cloud VM**, you need **nested virtualization** enabled, since you are running a VM inside a VM. Bare metal or a nested-virt-capable instance is safest.
- Give the host headroom: the VM is set to 4 GB RAM / 2 vCPUs (8 GB+ host recommended). Adjust in `01-build-and-boot-vm.sh`.

## Steps

### 1. Build and boot the VM (on your Linux/KVM host)

```bash
cd filedrop/deploy
./01-build-and-boot-vm.sh
```

Log in as `core` / `hummingbird`. Confirm you are on Hummingbird:

```bash
sudo bootc status
```

### 2. Copy the project onto the VM

From your host (replace `<vm-ip>`):

```bash
scp -r ~/filedrop core@<vm-ip>:~/
```

### 3. Deploy the app (inside the VM)

```bash
cd ~/filedrop/deploy
./02-deploy-filedrop.sh
```

This creates the network and volumes, pulls `hi/postgresql:17` and `hi/nginx`, builds the app image, and starts all three containers with `--restart=always` (24/7).

### 4. Verify

```bash
podman ps                      # three containers running
curl http://localhost:8080/    # the File Drop page
grype filedrop_app:latest      # confirm the app image is clean
```

Open `http://<vm-ip>:8080/` in a browser to use it.

## Notes

- Uses plain `podman` (not `podman-compose`), so it works on a minimal Hummingbird host.
- The DB password here is a demo value. Use an injected secret before any real use (Architecture section 5).
- Image tags (`hi/postgresql:17`, `hi/nginx:latest`, `hi/python:3.11`) were checked against the live registry. Confirm again on your host.
