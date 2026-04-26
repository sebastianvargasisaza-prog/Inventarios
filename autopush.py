"""
autopush.py — Watcher autonomo para Inventarios
Detecta cambios en el repo cada 15 segundos y hace push automatico a GitHub.
El token se lee de .git_token (gitignoreado) — sin secretos en codigo.
"""
import os, time, subprocess, sys

REPO       = r"C:\Users\sebas\OneDrive\Documentos\Claude\Projects\Inventarios"
LOG        = os.path.join(REPO, "autopush.log")
TOKEN_FILE = os.path.join(REPO, ".git_token")
INTERVAL   = 15  # segundos entre chequeos

def get_token():
    try:
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    except Exception as e:
        log(f"ERROR: no se pudo leer .git_token: {e}")
        return None

def get_remote(token):
    return f"https://sebastianvargasisaza-prog:{token}@github.com/sebastianvargasisaza-prog/Inventarios.git"

def run(cmd):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, shell=True)

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line)
    print(line, end="")

def has_changes():
    r = run("git status --porcelain")
    # Ignorar archivos de infra local — nunca deben triggerear un push
    excluir = {"autopush.log", "autopush.py", "push.bat",
               "iniciar_autopush.bat", ".git_token"}
    lines = [l for l in r.stdout.strip().splitlines()
             if not any(ex in l for ex in excluir)]
    return bool(lines)

def do_push():
    token = get_token()
    if not token:
        return "error: token no disponible en .git_token"
    try:
        run(f"git remote set-url origin {get_remote(token)}")
        run("git add -A")
        msg = f"auto-update {time.strftime('%Y-%m-%d %H:%M')}"
        r_commit = run(f'git commit -m "{msg}"')
        if "nothing to commit" in r_commit.stdout or "nothing to commit" in r_commit.stderr:
            return "sin_cambios"
        r_push = run("git push origin main")
        if r_push.returncode == 0:
            return "ok"
        else:
            return f"error: {r_push.stderr[:300]}"
    except Exception as e:
        return f"excepcion: {e}"

log("=" * 50)
log("AutoPush Inventarios iniciado")
log(f"Token: {'OK' if get_token() else 'FALTA .git_token!'}")
log(f"Chequeando cada {INTERVAL}s — Ctrl+C para detener")
log("=" * 50)

while True:
    try:
        if has_changes():
            log("Cambios detectados — haciendo push...")
            resultado = do_push()
            if resultado == "ok":
                log("Push exitoso. Render despliega en ~60s.")
            elif resultado == "sin_cambios":
                log("Sin cambios nuevos.")
            else:
                log(f"Push fallo: {resultado}")
    except KeyboardInterrupt:
        log("AutoPush detenido por usuario.")
        sys.exit(0)
    except Exception as e:
        log(f"Error inesperado: {e}")
    time.sleep(INTERVAL)
