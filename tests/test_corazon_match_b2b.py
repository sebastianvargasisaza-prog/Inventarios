"""PROPIEDAD 5 (verificación independiente · clave 'match_b2b').

Confirma empíricamente que GET /api/abastecimiento/consumo-horizontes:
  (A) hace MATCH producción↔fórmula tolerando acentos / '+' / puntuación
      (programar "QAmatch_b2b ÁCIDO + NÁD (Z)" contra fórmula
       "QAmatch_b2b ACIDO NAD Z" SÍ debe cruzar y aportar consumo), y
  (B) NO doble-cuenta: una sola producción con un solo item de fórmula
      aporta exactamente UNA vez su consumo (no 2x), aunque el nombre
      programado difiera en acentos/signos del registrado en la fórmula.

Datos 100% controlados, prefijo 'QAMATCHB2B', aislado con db_clean.
NO toca código de la app.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def _consumo_mp(app, codigo):
    c = _login(app)
    r = c.get("/api/abastecimiento/consumo-horizontes?tipo=mp&horizontes=15,30,60,90")
    assert r.status_code == 200, r.data
    js = r.get_json()
    for m in js.get("mps", []):
        if (m.get("codigo") or "").upper() == codigo.upper():
            return m, js
    return None, js


def test_match_tolera_acento_signo_puntuacion(app, db_clean):
    """(A) Nombre con acento + '+' + paréntesis cruza con fórmula sin acento."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('QAMATCHB2B-MP1','QAmatch acento','QAMATCH INCI 1',1)")
    # Fórmula registrada SIN acento, SIN signos: 50% de la MP.
    # _norm_prod colapsa [^A-Z0-9]+ a UN espacio → 'QA MATCHB2B ACIDO NAD Z'
    # debe normalizar IGUAL en ambos lados; por eso aquí usamos espacios
    # explícitos donde la versión programada tendrá acento/'+'/paréntesis.
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
          "VALUES ('QA MATCHB2B ACIDO NAD Z', 1, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('QA MATCHB2B ACIDO NAD Z', 'QAMATCHB2B-MP1', 'QAmatch acento', 50, 0)")
    # Programado CON acento, '+', paréntesis y doble espacio → texto MUY distinto
    # pero es EL MISMO producto tras _norm_prod (NFKD + [^A-Z0-9]+→espacio):
    #   'QA MATCHB2B  ÁCIDO + NÁD (Z)' → 'QA MATCHB2B ACIDO NAD Z'
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QA MATCHB2B  ÁCIDO + NÁD (Z)', date('now','-5 hours','+5 days'), 1, 'pendiente', 10, 'eos_plan')")

    mp, js = _consumo_mp(app, "QAMATCHB2B-MP1")
    assert mp is not None, f"el match acento/'+'/punct DEBE cruzar → MP no apareció. resp.mps={js.get('mps')}"
    cons = mp["consumo"]
    # 50% de 10 kg = 5000 g · día 5 entra en TODOS los horizontes (acumulativo).
    assert abs(cons["15"] - 5000) < 1, f"15d esperado 5000g · {cons}"
    assert abs(cons["90"] - 5000) < 1, f"90d esperado 5000g (acumula igual) · {cons}"


def test_no_doble_cuenta_un_solo_aporte(app, db_clean):
    """(B) Una producción + un item de fórmula = consumo UNA sola vez (no 2x)."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_comercial, nombre_inci, activo) "
          "VALUES ('QAMATCHB2B-MP2','QAmatch single','QAMATCH INCI 2',1)")
    # Ambos lados normalizan a 'QA MATCHB2B SINGLE PROD'.
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) "
          "VALUES ('QA MATCHB2B SINGLE PROD', 1, 1)")
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) "
          "VALUES ('QA MATCHB2B SINGLE PROD', 'QAMATCHB2B-MP2', 'QAmatch single', 25, 0)")
    # Una sola producción, nombre con acento/signo (vuelve a usar el camino normalizado):
    #   'QA MATCHB2B SÍNGLE  PRÓD' → 'QA MATCHB2B SINGLE PROD'
    _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado, cantidad_kg, origen) "
          "VALUES ('QA MATCHB2B SÍNGLE  PRÓD', date('now','-5 hours','+3 days'), 1, 'pendiente', 8, 'eos_plan')")

    mp, js = _consumo_mp(app, "QAMATCHB2B-MP2")
    assert mp is not None, f"MP única no apareció. resp.mps={js.get('mps')}"
    cons = mp["consumo"]
    # 25% de 8 kg = 2000 g · UNA vez. Si doble-contara saldría 4000.
    assert abs(cons["15"] - 2000) < 1, f"15d esperado 2000g (NO 4000=doble) · {cons}"
    assert abs(cons["90"] - 2000) < 1, f"90d esperado 2000g (NO 4000=doble) · {cons}"
