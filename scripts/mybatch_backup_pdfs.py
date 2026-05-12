#!/usr/bin/env python3
"""
mybatch_backup_pdfs.py — Descarga TODOS los PDFs de Órdenes de Producción de
MYBATCH (Espagiria · CielTechno SAS) para preservar compliance INVIMA antes de
migrar a EOS / cancelar el proveedor.

Lee la lista de OPs desde archive/mybatch-snapshot/ops_index.json (52 registros)
y descarga el PDF de cada una vía /productionorder/pdf/<uuid>/ usando la cookie
de sesión del usuario.

Uso:
    # Windows PowerShell:
    $env:MYBATCH_COOKIE = "sessionid=XXXXX"
    python scripts/mybatch_backup_pdfs.py

    # Bash (Git Bash, macOS, Linux):
    export MYBATCH_COOKIE="sessionid=XXXXX"
    python scripts/mybatch_backup_pdfs.py

    # Opcional: descargar también los Rótulos de Pesaje
    python scripts/mybatch_backup_pdfs.py --include-labels

Salida:
    archive/mybatch-pdfs/OP-YYYY-NN-lote-NNNNNN.pdf        (PDF lote completo)
    archive/mybatch-pdfs/OP-YYYY-NN-lote-NNNNNN-labels.pdf (rótulos pesaje, opc.)
    archive/mybatch-snapshot/backup_log.json               (log con éxitos/errores)

Idempotente: si un PDF ya existe en disco, se salta.
Respeta el servidor: 0.5s de delay entre descargas.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime

BASE_URL = "https://esparigia-mybatch-907403675147.us-east4.run.app"
PDF_URL = BASE_URL + "/productionorder/pdf/{uuid}/"
LABELS_URL = BASE_URL + "/productionorder/weight_pdf/{uuid}/"

REPO_ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO_ROOT / "archive" / "mybatch-snapshot" / "ops_index.json"
PDF_DIR = REPO_ROOT / "archive" / "mybatch-pdfs"
LOG_PATH = REPO_ROOT / "archive" / "mybatch-snapshot" / "backup_log.json"

USER_AGENT = "Mozilla/5.0 (EOS-Backup/1.0)"
DELAY_S = 0.5
TIMEOUT_S = 60


def get_cookie() -> str:
    cookie = os.environ.get("MYBATCH_COOKIE", "").strip()
    if not cookie:
        print("ERROR: define la variable de entorno MYBATCH_COOKIE")
        print()
        print("Cómo sacarla:")
        print("  1. En Chrome, abre cualquier página de MYBATCH (ya logueada)")
        print("  2. F12 → Application → Cookies → "
              "https://esparigia-mybatch-907403675147.us-east4.run.app")
        print("  3. Copia el valor completo de la cookie 'sessionid'")
        print("  4. Pega así (PowerShell):")
        print('         $env:MYBATCH_COOKIE = "sessionid=el-valor-largo"')
        print("     o así (Bash):")
        print('         export MYBATCH_COOKIE="sessionid=el-valor-largo"')
        sys.exit(1)
    return cookie


def load_index() -> dict:
    if not INDEX_PATH.exists():
        print(f"ERROR: no existe {INDEX_PATH}")
        print("  Ejecuta primero la extracción de UUIDs desde MYBATCH.")
        sys.exit(1)
    with INDEX_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def fetch_pdf(url: str, cookie: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "Cookie": cookie,
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,*/*",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
        ctype = resp.headers.get("Content-Type", "")
        data = resp.read()
        if not data.startswith(b"%PDF"):
            raise ValueError(
                f"respuesta no es PDF (content-type={ctype}, "
                f"primer-bytes={data[:30]!r})"
            )
        return data


def safe_filename(num: str, lote: str, suffix: str = "") -> str:
    clean_lote = lote.replace("*", "").replace("/", "-").strip()
    base = f"{num}-lote-{clean_lote}"
    return f"{base}{suffix}.pdf"


def backup_one(op: dict, cookie: str, include_labels: bool) -> dict:
    result = {
        "num": op["num"],
        "uuid": op["uuid"],
        "estado": op["estado"],
        "pdf": {"status": "pending"},
    }
    if include_labels:
        result["labels"] = {"status": "pending"}

    # PDF principal
    pdf_path = PDF_DIR / safe_filename(op["num"], op["lote"])
    if pdf_path.exists():
        result["pdf"] = {"status": "skipped",
                         "reason": "ya existe",
                         "path": str(pdf_path.relative_to(REPO_ROOT))}
    else:
        try:
            data = fetch_pdf(PDF_URL.format(uuid=op["uuid"]), cookie)
            pdf_path.write_bytes(data)
            result["pdf"] = {"status": "ok",
                             "bytes": len(data),
                             "path": str(pdf_path.relative_to(REPO_ROOT))}
        except urllib.error.HTTPError as e:
            result["pdf"] = {"status": "http_error", "code": e.code,
                             "msg": str(e)}
        except Exception as e:
            result["pdf"] = {"status": "error", "msg": str(e)}

    # Rótulos de pesaje (opcional)
    if include_labels:
        labels_path = PDF_DIR / safe_filename(
            op["num"], op["lote"], suffix="-labels")
        if labels_path.exists():
            result["labels"] = {"status": "skipped", "reason": "ya existe"}
        else:
            try:
                data = fetch_pdf(LABELS_URL.format(uuid=op["uuid"]), cookie)
                labels_path.write_bytes(data)
                result["labels"] = {"status": "ok", "bytes": len(data)}
            except Exception as e:
                result["labels"] = {"status": "error", "msg": str(e)}

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--include-labels", action="store_true",
                        help="También descargar Rótulos de Pesaje")
    parser.add_argument("--filter-estado", default=None,
                        choices=["Aprobado", "En Proceso", "Cancelado"],
                        help="Solo OPs con este estado (default: todos)")
    args = parser.parse_args()

    cookie = get_cookie()
    index = load_index()
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    ops = index["ops"]
    if args.filter_estado:
        ops = [o for o in ops if o["estado"] == args.filter_estado]

    print(f"MYBATCH PDF Backup · {datetime.now().isoformat(timespec='seconds')}")
    print(f"Total OPs a procesar: {len(ops)}  "
          f"(filtro: {args.filter_estado or 'ninguno'})")
    print(f"Destino: {PDF_DIR.relative_to(REPO_ROOT)}\\")
    print(f"Rótulos de pesaje: {'sí' if args.include_labels else 'no'}")
    print(f"Delay entre descargas: {DELAY_S}s")
    print("-" * 70)

    results = []
    ok = skipped = errors = 0
    for i, op in enumerate(ops, 1):
        res = backup_one(op, cookie, args.include_labels)
        results.append(res)

        pdf_status = res["pdf"]["status"]
        if pdf_status == "ok":
            kb = res["pdf"]["bytes"] / 1024
            print(f"[{i:3}/{len(ops)}] OK    {op['num']:<13} ({kb:6.1f} KB)")
            ok += 1
        elif pdf_status == "skipped":
            print(f"[{i:3}/{len(ops)}] SKIP  {op['num']:<13} (ya existe)")
            skipped += 1
        else:
            msg = res["pdf"].get("msg", "?")
            print(f"[{i:3}/{len(ops)}] ERROR {op['num']:<13} → {msg[:60]}")
            errors += 1

        if pdf_status == "ok":
            time.sleep(DELAY_S)

    print("-" * 70)
    print(f"Resumen: {ok} OK · {skipped} SKIP · {errors} ERROR · "
          f"{len(ops)} total")

    log_data = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(ops),
        "ok": ok,
        "skipped": skipped,
        "errors": errors,
        "include_labels": args.include_labels,
        "filter_estado": args.filter_estado,
        "results": results,
    }
    with LOG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(log_data, fh, indent=2, ensure_ascii=False)
    print(f"Log: {LOG_PATH.relative_to(REPO_ROOT)}")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
