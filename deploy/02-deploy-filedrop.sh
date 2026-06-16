#!/usr/bin/env bash
#
# 02-deploy-filedrop.sh
# Step 2: deploy the File Drop stack ON the Hummingbird VM (Architecture sections 2-5).
#
# RUN THIS INSIDE THE HUMMINGBIRD VM, after 01 booted it and you copied the
# project onto the VM. It uses plain podman (no podman-compose needed), so it
# works on a minimal Hummingbird host.
#
# Expects the filedrop/ folder to be the parent folder (..), i.e. run it
# from the deploy/ folder you copied over. Adjust APP_SRC if your layout differs.

set -euo pipefail

APP_SRC="$(cd "$(dirname "$0")/.." && pwd)"

NET="filedrop-net"
DB_IMAGE="registry.access.redhat.com/hi/postgresql:17"
PROXY_IMAGE="registry.access.redhat.com/hi/nginx:latest"
APP_IMAGE="filedrop_app:latest"

echo ">> Using app source: ${APP_SRC}"

echo ">> Creating network and volumes"
podman network exists "${NET}" || podman network create "${NET}"
podman volume exists db-data || podman volume create db-data
podman volume exists file-data || podman volume create file-data

echo ">> Pulling base images"
podman pull "${DB_IMAGE}"
podman pull "${PROXY_IMAGE}"

echo ">> Building the app image (multi-stage build on hi/python)"
podman build -t "${APP_IMAGE}" "${APP_SRC}"

echo ">> Starting PostgreSQL (db)"
podman run -d --name db --network "${NET}" --restart=always \
  -e POSTGRES_USER=filedrop \
  -e POSTGRES_PASSWORD=secret \
  -e POSTGRES_DB=filedrop \
  -v db-data:/var/lib/postgresql/data \
  "${DB_IMAGE}"

echo ">> Starting the app (FastAPI)"
podman run -d --name app --network "${NET}" --restart=always \
  -e DATABASE_URL="postgresql://filedrop:secret@db:5432/filedrop" \
  -v file-data:/data \
  "${APP_IMAGE}"

echo ">> Starting nginx (proxy), exposed on host port 8080"
podman run -d --name proxy --network "${NET}" --restart=always \
  -p 8080:80 \
  -v "${APP_SRC}/nginx.conf":/etc/nginx/nginx.conf:ro \
  "${PROXY_IMAGE}"

echo
echo ">> Deployed. Verify with:"
echo ">>   podman ps"
echo ">>   curl http://localhost:8080/"
echo ">>   sudo bootc status        # confirm you are on the Hummingbird image"
echo ">>   grype ${APP_IMAGE}       # confirm the app image is clean"
