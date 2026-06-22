"""Fase 0 · Normalizar inventario de ENVASES (MEE) tan inteligente como MP · 19-jun.

Cubre:
- mig 279: maestro_mee gana nombre_inci + material_referencia.
- _norm_envase_name reusa el normalizador canónico de MP (M1/M2).
- _resolver_envase_bodega: con puente → canónico; sin puente → el mismo.
- _get_mee_stock pass-3: el stock del duplicado se ATRIBUYE al canónico (lookup por
  cualquiera de los dos códigos devuelve el TOTAL) · el kardex NO se toca.
- /api/admin/maestro-envases-diff detecta el grupo duplicado.
- /api/admin/maestro-envases-aplicar: fusionar crea puente + estado=Inactivo;
  deshacer lo revierte; backfill-inci rellena nombre_inci vacío.
"""
import os
import sqlite3
import importlib
import sys

from .conftest import TEST_PASSWORD, csrf_headers


def _api():
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _conn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)


def _seed_dup(conn, canon, dup, cat="ZZTEST", desc="ZZ WIDGET UNICO 30mL",
              canon_mov=100, dup_mov=40):
    conn.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,estado,stock_actual,stock_minimo) "
                 "VALUES (?,?,?,'Activo',0,0)", (canon, desc, cat))
    conn.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,estado,stock_actual,stock_minimo) "
                 "VALUES (?,?,?,'Activo',0,0)", (dup, desc.replace('mL', 'ml'), cat))
    if canon_mov:
        conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,anulado) VALUES (?,'Entrada',?,0)", (canon, canon_mov))
    if dup_mov:
        conn.execute("INSERT INTO movimientos_mee (mee_codigo,tipo,cantidad,anulado) VALUES (?,'Entrada',?,0)", (dup, dup_mov))
    conn.commit()


def test_mig279_columnas(app, db_clean):
    conn = _conn()
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(maestro_mee)").fetchall()}
        assert 'nombre_inci' in cols, "mig 279 debe agregar nombre_inci"
        assert 'material_referencia' in cols, "mig 279 debe agregar material_referencia"
    finally:
        conn.close()


def test_norm_envase_reusa_norm_mp(app, db_clean):
    _api()
    prog = importlib.import_module("blueprints.programacion")
    # mismo normalizador → mismas reglas (acentos, puntuación, mayúsc)
    assert prog._norm_envase_name("Envase Ámbar 30mL") == prog._norm_mp_name("Envase Ámbar 30mL")
    assert prog._norm_envase_name("ENV-AMB-10") == prog._norm_envase_name("env amb 10")


def test_resolver_envase_con_y_sin_puente(app, db_clean):
    _api()
    prog = importlib.import_module("blueprints.programacion")
    conn = _conn()
    try:
        canon, dup = "ZZENV-CANON-30", "ZZENV-DUP-30"
        _seed_dup(conn, canon, dup, canon_mov=0, dup_mov=0)
        c = conn.cursor()
        # sin puente → devuelve el mismo
        assert prog._resolver_envase_bodega(c, dup).upper() == dup.upper()
        # con puente → canónico
        conn.execute("INSERT INTO mee_aliases (alias,codigo_mee,tipo,fuente,activo) VALUES (?,?,'sinonimo','manual',1)", (dup, canon))
        conn.commit()
        assert prog._resolver_envase_bodega(c, dup).upper() == canon.upper()
        # puente inactivo → vuelve a sí mismo
        conn.execute("UPDATE mee_aliases SET activo=0 WHERE alias=?", (dup,))
        conn.commit()
        assert prog._resolver_envase_bodega(c, dup).upper() == dup.upper()
    finally:
        conn.close()


def test_get_mee_stock_pliega_puente(app, db_clean):
    _api()
    prog = importlib.import_module("blueprints.programacion")
    conn = _conn()
    try:
        canon, dup = "ZZST-CANON-30", "ZZST-DUP-30"
        _seed_dup(conn, canon, dup, canon_mov=100, dup_mov=40)
        # sin puente: separados
        st = prog._get_mee_stock(conn)
        assert abs(st.get(canon.upper(), 0) - 100) < 0.5
        assert abs(st.get(dup.upper(), 0) - 40) < 0.5
        # con puente: lookup por cualquiera devuelve el TOTAL (140)
        conn.execute("INSERT INTO mee_aliases (alias,codigo_mee,tipo,fuente,activo) VALUES (?,?,'sinonimo','manual',1)", (dup, canon))
        conn.commit()
        st2 = prog._get_mee_stock(conn)
        assert abs(st2.get(canon.upper(), 0) - 140) < 0.5, f"canónico debe sumar el duplicado · got {st2.get(canon.upper())}"
        assert abs(st2.get(dup.upper(), 0) - 140) < 0.5, f"el duplicado debe reportar el total canónico · got {st2.get(dup.upper())}"
        # el kardex no se tocó (movimientos_mee del duplicado siguen bajo su código)
        n = conn.execute("SELECT COUNT(*) FROM movimientos_mee WHERE mee_codigo=?", (dup,)).fetchone()[0]
        assert n == 1, "el kardex del duplicado NO se mueve"
    finally:
        conn.close()


def test_diff_detecta_duplicado(app, db_clean):
    conn = _conn()
    try:
        _seed_dup(conn, "ZZDF-CANON-30", "ZZDF-DUP-30", cat="ZZDFCAT", desc="ZZDF UNICO 30mL", canon_mov=100, dup_mov=40)
    finally:
        conn.close()
    c = _login(app)
    j = c.get("/api/admin/maestro-envases-diff").get_json()
    assert j["ok"], j
    grupo = next((g for g in j["duplicados"]
                  if "ZZDF-CANON-30" in [x["codigo"] for x in g["codigos"]]), None)
    assert grupo is not None, "debe detectar el grupo duplicado"
    assert grupo["canonico_sugerido"] == "ZZDF-CANON-30", "el de más stock es el canónico sugerido"


def test_aplicar_fusionar_deshacer(app, db_clean):
    canon, dup = "ZZAP-CANON-30", "ZZAP-DUP-30"
    conn = _conn()
    try:
        _seed_dup(conn, canon, dup, canon_mov=100, dup_mov=40)
    finally:
        conn.close()
    c = _login(app)
    hdr = {"X-CSRF-Token": c.get("/api/csrf-token").get_json()["csrf_token"]}
    # fusionar
    r = c.post("/api/admin/maestro-envases-aplicar", json={
        "accion": "fusionar", "merges": [{"duplicado": dup, "canonico": canon}], "dry_run": 0}, headers=hdr)
    d = r.get_json()
    assert r.status_code == 200 and d["aplicados"] == 1, d
    conn = _conn()
    try:
        # puente creado + duplicado Inactivo · canónico intacto
        br = conn.execute("SELECT codigo_mee, activo FROM mee_aliases WHERE alias=?", (dup,)).fetchone()
        assert br and br[0] == canon and br[1] == 1, f"puente activo dup→canon · got {br}"
        est = conn.execute("SELECT estado FROM maestro_mee WHERE codigo=?", (dup,)).fetchone()[0]
        assert (est or '').lower() == 'inactivo', f"duplicado debe quedar Inactivo · got {est}"
        est_c = conn.execute("SELECT estado FROM maestro_mee WHERE codigo=?", (canon,)).fetchone()[0]
        assert (est_c or '').lower() == 'activo', "canónico intacto"
    finally:
        conn.close()
    # deshacer
    r2 = c.post("/api/admin/maestro-envases-aplicar", json={
        "accion": "deshacer", "merges": [{"duplicado": dup}], "dry_run": 0}, headers=hdr)
    d2 = r2.get_json()
    assert r2.status_code == 200 and d2["aplicados"] == 1, d2
    conn = _conn()
    try:
        br = conn.execute("SELECT activo FROM mee_aliases WHERE alias=?", (dup,)).fetchone()
        assert br and br[0] == 0, "deshacer desactiva el puente"
        est = conn.execute("SELECT estado FROM maestro_mee WHERE codigo=?", (dup,)).fetchone()[0]
        assert (est or '').lower() == 'activo', "deshacer reactiva el código"
    finally:
        conn.close()


def test_backfill_inci(app, db_clean):
    cod = "ZZBF-30"
    conn = _conn()
    try:
        conn.execute("INSERT OR IGNORE INTO maestro_mee (codigo,descripcion,categoria,estado,stock_actual,stock_minimo) "
                     "VALUES (?,?,?,'Activo',0,0)", (cod, "ENVASE BACKFILL 30ml", "Envase"))
        conn.commit()
    finally:
        conn.close()
    c = _login(app)
    hdr = {"X-CSRF-Token": c.get("/api/csrf-token").get_json()["csrf_token"]}
    r = c.post("/api/admin/maestro-envases-aplicar", json={"accion": "backfill-inci", "dry_run": 0}, headers=hdr)
    assert r.status_code == 200, r.data
    conn = _conn()
    try:
        ni = conn.execute("SELECT nombre_inci FROM maestro_mee WHERE codigo=?", (cod,)).fetchone()[0]
        assert (ni or '') == "ENVASE BACKFILL 30ml", f"nombre_inci debe rellenarse con la descripción · got {ni}"
    finally:
        conn.close()
