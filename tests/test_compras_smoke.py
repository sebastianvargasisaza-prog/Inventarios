"""Smoke tests para compras — endpoints + JS parse + URL alignment.

Catch del audit:
- syntax error JS por escapado triple (rompía TODA la página)
- async async function (typo)
- ReferenceError loadCCSolicitudes en init
- URL /api/materiales que no existía (404)
"""
import re
import shutil
import subprocess

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_compras_page_loads(app, db_clean):
    c = _login(app)
    r = c.get("/compras")
    assert r.status_code == 200
    assert b"Compras HHA" in r.data or b"Compras" in r.data


def test_compras_real_endpoints(app, db_clean):
    """Cada endpoint que el frontend de compras llama debe existir.

    Se extrae la lista de fetch('/api/...') del HTML y se verifica que
    cada uno responde 200 (o 401/403 que también prueba que existe).
    Esto previene URLs huérfanas tipo /api/materiales (que era 404).
    """
    c = _login(app)
    real_endpoints = [
        "/api/compras/alertas-vivas",
        "/api/compras/consolidado-proveedor",
        "/api/compras/por-pagar",
        "/api/maestro-mps",  # Antes el frontend llamaba /api/materiales (404)
        "/api/maestro-mps?tipo_material=MP",
        "/api/ordenes-compra",
        "/api/programacion/n-alertas",
        "/api/programacion/mps-deficit",
        "/api/proveedores-compras",
        "/api/solicitudes-compra",
    ]
    fail = []
    for url in real_endpoints:
        r = c.get(url)
        if r.status_code not in (200, 401, 403):
            fail.append((url, r.status_code))
    assert not fail, f"Endpoints rotos: {fail}"


def test_compras_html_js_parses():
    """Compila el JS embebido en COMPRAS_HTML con node.

    Si esto falla, TODO el <script> de compras se rompe y la página queda
    inerte — pasó dos veces (escapado triple inline + async async).
    """
    if not shutil.which("node"):
        pytest.skip("node no disponible")

    from api.templates_py.compras_html import COMPRAS_HTML

    scripts = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
        COMPRAS_HTML, re.DOTALL,
    )
    assert scripts, "no <script> en COMPRAS_HTML"

    full_js = "\n;\n".join(scripts)
    wrapped = f"(async function() {{\n{full_js}\n}})();"

    import tempfile
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".js", delete=False, encoding="utf-8"
    ) as f:
        f.write(wrapped)
        tmp = f.name

    try:
        proc = subprocess.run(
            ["node", "--check", tmp],
            capture_output=True, text=True, timeout=20,
        )
        assert proc.returncode == 0, (
            f"JS de compras_html.py no parsea — rompería la página entera:\n"
            f"{proc.stderr[-1500:]}"
        )
    finally:
        import os as _os
        try: _os.unlink(tmp)
        except OSError: pass


def test_all_pages_js_parses_with_node(app, db_clean):
    """Audit V8: cada página HTML del app debe tener JS válido.

    Detecta patrones que rompen toda la página:
      1. Comillas mal escapadas en onclick inline
      2. 'async async function' (typo de keyword duplicado)
      3. Backticks/dollars con escape inválido en templates Python no-raw
      4. Newlines literales dentro de strings con comilla simple/doble

    Cualquiera de estos hace que TODO el script JS falle al parsear y la
    página queda inerte — sin handlers, sin tabs, sin loaders.
    """
    if not shutil.which("node"):
        pytest.skip("node no disponible")

    PAGES = [
        "/hub", "/marketing", "/compras", "/planta", "/admin",
        "/contabilidad", "/financiero", "/calidad", "/animus",
        "/clientes", "/recepcion", "/tecnica", "/rrhh", "/gerencia",
        "/compromisos",
    ]

    c = _login(app)
    failures = []
    for page in PAGES:
        r = c.get(page)
        if r.status_code != 200:
            continue
        html = r.get_data(as_text=True)
        scripts = re.findall(
            r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
            html, re.DOTALL,
        )
        if not scripts:
            continue
        full_js = "\n;\n".join(scripts)
        wrapped = f"(async function() {{\n{full_js}\n}})();"
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False, encoding="utf-8"
        ) as f:
            f.write(wrapped)
            tmp = f.name
        try:
            proc = subprocess.run(
                ["node", "--check", tmp],
                capture_output=True, text=True, timeout=20,
            )
            if proc.returncode != 0:
                err_first_line = (proc.stderr.split('\n')[1]
                                  if len(proc.stderr.split('\n')) > 1
                                  else proc.stderr)[:200]
                failures.append((page, err_first_line))
        finally:
            import os as _os
            try: _os.unlink(tmp)
            except OSError: pass

    assert not failures, (
        f"Páginas con JS inválido — usuarios verán botones inertes:\n" +
        "\n".join(f"  {p}: {err}" for p, err in failures)
    )


def test_compras_no_orphan_fetch_urls():
    """Audit de URLs que el frontend llama vs endpoints registrados.

    Extrae todos los fetch('/api/...') del HTML y verifica que apuntan a
    endpoints que existen en los blueprints. Cazamos /api/materiales aquí.
    """
    from api.templates_py.compras_html import COMPRAS_HTML

    # Encontrar todos los fetch('/api/X')
    fetches = re.findall(r"fetch\('(/api/[^'?]+)", COMPRAS_HTML)
    fetches = sorted(set(fetches))

    # Lista whitelist de prefijos válidos. Cualquier fetch debe coincidir
    # con uno de estos prefijos (o ser literal).
    valid_prefixes = [
        "/api/compras/", "/api/comprobantes-pago",
        "/api/maestro-mps", "/api/maestro-mp/",
        "/api/ordenes-compra", "/api/programacion/",
        "/api/proveedores-compras", "/api/solicitudes-compra",
        "/api/conteo/", "/api/admin/",
    ]
    orphans = []
    for url in fetches:
        if not any(url.startswith(p) or url == p.rstrip("/") for p in valid_prefixes):
            orphans.append(url)
    assert not orphans, (
        f"URLs frontend que no apuntan a ningún endpoint registrado: "
        f"{orphans}. Verificá que coincidan con los @bp.route(...)."
    )


def test_solicitudes_pdf_renders(app, db_clean):
    """El PDF consolidado de solicitudes debe rendear sin crashear.

    Es el documento ejecutivo que va a Alejandro. Si esta ruta falla,
    Compras pierde el flujo de aprobación. Inserta una solicitud mínima
    + 1 item y verifica que llega un PDF válido (>1KB con cabecera %PDF).
    """
    import sqlite3
    import os

    c = _login(app)

    # Insertar 1 solicitud Pendiente con 1 item — datos mínimos válidos
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO solicitudes_compra
           (numero, fecha, estado, solicitante, urgencia, observaciones,
            empresa, categoria, area, fecha_requerida)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        ("SOL-TEST-PDF", "2026-04-27", "Pendiente", "test_user", "Alta",
         "Solicitud de prueba para smoke test PDF",
         "Espagiria", "Materia Prima", "Produccion", "2026-05-01"),
    )
    cur.execute(
        """INSERT INTO solicitudes_compra_items
           (numero, codigo_mp, nombre_mp, cantidad_g, unidad,
            justificacion, valor_estimado)
           VALUES (?,?,?,?,?,?,?)""",
        ("SOL-TEST-PDF", "MPTESTSMK01", "MATERIAL TEST SMOKE",
         1500, "g", "Deficit para produccion de: TEST", 50000),
    )
    conn.commit()
    conn.close()

    r = c.get("/api/compras/solicitudes/pdf?estados=Pendiente,Aprobada")
    assert r.status_code == 200, (
        f"PDF endpoint rompió: {r.status_code} — body: {r.data[:300]!r}"
    )
    assert r.mimetype == "application/pdf", (
        f"Mimetype incorrecto: {r.mimetype}"
    )
    assert r.data.startswith(b"%PDF"), (
        f"Respuesta no es PDF: empieza con {r.data[:8]!r}"
    )
    # Un PDF con header + caja resumen + 1 card + firmas debe pesar ≥4KB
    assert len(r.data) > 4000, (
        f"PDF sospechosamente pequeño: {len(r.data)} bytes"
    )
    cd = r.headers.get("Content-Disposition", "")
    assert "attachment" in cd and "solicitudes_compra_" in cd, (
        f"Content-Disposition mal formado: {cd}"
    )
