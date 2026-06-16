#!/usr/bin/env bash
#
# 01-build-and-boot-vm.sh
# Step 1 of deploying File Drop on a Hummingbird VM (Architecture section 3, "VM" mode).
#
# This builds a bootable Hummingbird disk image and boots it as a VM.
# RUN THIS ON A LINUX HOST WITH KVM. It needs: podman, qemu-kvm, libvirt, virt-install.
# It will NOT work on macOS (no KVM).
#
# Run from the deploy/ folder (it uses bib-config.toml next to it).

set -euo pipefail

BASE_IMAGE="quay.io/hummingbird-community/bootc-os:latest"
BUILDER_IMAGE="quay.io/centos-bootc/bootc-image-builder:latest"
CONFIG="$(pwd)/bib-config.toml"
OUTPUT_DIR="/var/lib/libvirt/images"
DISK="${OUTPUT_DIR}/qcow2/disk.qcow2"
VM_NAME="hummingbird-filedrop"

if [[ ! -f "${CONFIG}" ]]; then
  echo "ERROR: bib-config.toml not found in $(pwd). Run this from the deploy/ folder." >&2
  exit 1
fi

echo ">> Pulling the base OS image and the image builder (both needed first)"
sudo podman pull "${BASE_IMAGE}"
sudo podman pull "${BUILDER_IMAGE}"

echo ">> Building the bootable disk image"
sudo podman run --rm -it --privileged --pull=newer \
  --security-opt label=type:unconfined_t \
  -v "${CONFIG}":/config.toml:ro \
  -v "${OUTPUT_DIR}":/output \
  -v /var/lib/containers/storage:/var/lib/containers/storage \
  "${BUILDER_IMAGE}" \
  --type qcow2 --rootfs ext4 \
  "${BASE_IMAGE}"

echo ">> Booting the VM '${VM_NAME}'"
echo ">> Log in as: core / hummingbird   (leave the console with Ctrl+])"
sudo virt-install \
  --name "${VM_NAME}" \
  --memory 4096 --vcpus 2 \
  --import \
  --disk "${DISK}" \
  --os-variant fedora-rawhide \
  --graphics none \
  --console pty,target_type=serial

echo
echo ">> VM is up. Next: copy the project onto it and run 02-deploy-filedrop.sh inside the VM."
echo ">> For example, from this host:"
echo ">>   scp -r ~/filedrop core@<vm-ip>:~/"
