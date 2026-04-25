#!/usr/bin/env python3
"""Push fix for JS SyntaxError: Unexpected string in dashboard_html.py
Root cause: \\' inside Python triple-quoted string renders as ' (stripping backslash),
causing adjacent string literals in JS. Fix: use \\\\' so Python renders \\' in HTML.
"""
import urllib.request, urllib.error, json, base64, os

TOKEN  = "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"
OWNER  = "espagiria"
REPO   = "hha-portal"
BRANCH = "main"
PATH   = "api/templates_py/dashboard_html.py"

# Read local fixed file
local_path = os.path.join(os.path.dirname(__file__), "api", "templates_py", "dashboard_html.py")
with open(local_path, "rb") as f:
    content_bytes = f.read()

# Get current SHA
api_base = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{PATH}"
req = urllib.request.Request(
    api_base + f"?ref={BRANCH}",
    headers={"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}
)
with urllib.request.urlopen(req) as r:
    sha = json.load(r)["sha"]
print(f"Current SHA: {sha}")

# Push
payload = json.dumps({
    "message": "fix: JS SyntaxError in conteo cíclico — escape backslash-quote correctly in Python triple-string",
    "content": base64.b64encode(content_bytes).decode(),
    "sha": sha,
    "branch": BRANCH
}).encode()

req2 = urllib.request.Request(
    api_base,
    data=payload,
    method="PUT",
    headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
)
with urllib.request.urlopen(req2) as r:
    resp = json.load(r)
    print(f"✅ Pushed! Commit: {resp['commit']['sha'][:12]} — {resp['commit']['message']}")
