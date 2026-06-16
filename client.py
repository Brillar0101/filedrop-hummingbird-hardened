"""File Drop client — uploads a file from the command line.
Standard library only, so the client needs no extra packages.

Usage:
    python3 client.py <path-to-file>
"""

import os
import sys
import urllib.request
import uuid

SERVER = "http://localhost:8080"


def upload(path):
    boundary = uuid.uuid4().hex
    name = os.path.basename(path)
    with open(path, "rb") as f:
        content = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()

    req = urllib.request.Request(
        SERVER + "/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    urllib.request.urlopen(req, timeout=15)
    print(f"uploaded {name} — open {SERVER}/ to see it")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 client.py <file>")
        sys.exit(1)
    upload(sys.argv[1])
