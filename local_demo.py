"""Local demo runner for File Drop. Stdlib only (http.server + sqlite3) so it
runs anywhere with no extra packages. Same clean UI as the real FastAPI app.
This is ONLY for seeing the app work locally. Production runs FastAPI + nginx +
PostgreSQL on Fedora Hummingbird."""

import http.server
import html
import os
import secrets
import socketserver
import sqlite3

BASE = os.path.join(os.path.dirname(__file__), ".demo-data")
UP = os.path.join(BASE, "uploads")
DB = os.path.join(BASE, "files.db")
PORT = 8087
os.makedirs(UP, exist_ok=True)


def conn():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS files (id TEXT PRIMARY KEY, name TEXT, size INTEGER)")
    return c


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>File Drop</title>
<style>
  :root { --line:#e4e4e7; --muted:#6b7280; --fg:#111; }
  body { font-family: system-ui, -apple-system, sans-serif; color:var(--fg);
         max-width:640px; margin:64px auto; padding:0 20px; line-height:1.5; }
  h1 { font-size:20px; font-weight:600; margin:0 0 24px; }
  form { display:flex; gap:8px; margin-bottom:32px; }
  input[type=file] { flex:1; }
  button { padding:8px 16px; border:1px solid var(--fg); background:var(--fg);
           color:#fff; border-radius:6px; cursor:pointer; font-size:14px; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th { text-align:left; color:var(--muted); font-weight:500;
       border-bottom:1px solid var(--line); padding:8px 0; }
  td { border-bottom:1px solid var(--line); padding:10px 0; }
  td.size, th.size { text-align:right; color:var(--muted); padding-right:32px; }
  td.dl, th.dl { text-align:right; white-space:nowrap; }
  a { color:#2563eb; text-decoration:none; }
  a:hover { text-decoration:underline; }
  .empty { color:var(--muted); padding:24px 0; text-align:center; }
</style>
</head>
<body>
  <h1>File Drop</h1>
  <form action="/upload" method="post" enctype="multipart/form-data">
    <input type="file" name="file" required>
    <button type="submit">Upload</button>
  </form>
  <table>
    <tr><th>File</th><th class="size">Size</th><th class="dl"></th></tr>
    {rows}
  </table>
</body>
</html>"""


def render():
    c = conn()
    rows = c.execute("SELECT id, name, size FROM files ORDER BY rowid DESC").fetchall()
    c.close()
    if rows:
        body = "".join(
            f'<tr><td>{html.escape(n)}</td>'
            f'<td class="size">{s:,} B</td>'
            f'<td class="dl"><a href="/file/{i}">Download</a></td></tr>'
            for i, n, s in rows
        )
    else:
        body = '<tr><td colspan="3" class="empty">No files yet</td></tr>'
    return PAGE.replace("{rows}", body)


def parse_multipart(body, boundary):
    for part in body.split(b"--" + boundary):
        if b"filename=" in part:
            header, _, content = part.partition(b"\r\n\r\n")
            name = "file"
            for line in header.decode("utf-8", "ignore").split("\r\n"):
                if "filename=" in line:
                    after = line.split("filename=", 1)[1]
                    if after.startswith('"'):
                        name = after[1:].split('"', 1)[0]
                    else:
                        name = after.split(";")[0].strip()
                    break
            return name, content.rstrip(b"\r\n")
    return None, None


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body = render().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/file/"):
            fid = os.path.basename(self.path[6:])
            c = conn()
            row = c.execute("SELECT name FROM files WHERE id=?", (fid,)).fetchone()
            c.close()
            path = os.path.join(UP, fid)
            if row and os.path.isfile(path):
                with open(path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Disposition", f'attachment; filename="{row[0]}"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_error(404)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/upload":
            ctype = self.headers.get("Content-Type", "")
            length = int(self.headers.get("Content-Length", 0))
            data = self.rfile.read(length)
            if "boundary=" in ctype:
                boundary = ctype.split("boundary=", 1)[1].encode()
                name, content = parse_multipart(data, boundary)
                if name and content is not None:
                    fid = secrets.token_urlsafe(8)
                    with open(os.path.join(UP, fid), "wb") as f:
                        f.write(content)
                    c = conn()
                    c.execute("INSERT INTO files VALUES (?,?,?)", (fid, name, len(content)))
                    c.commit()
                    c.close()
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"File Drop demo running at http://127.0.0.1:{PORT}")
        httpd.serve_forever()
