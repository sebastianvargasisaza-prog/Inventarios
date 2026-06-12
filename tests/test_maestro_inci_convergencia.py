"""Convergencia Maestro INCI ↔ Excel de Alejandro (11-jun · 'lo más grande').
Etapa 2: sembrar faltantes + backfill INCI vacío + corregir INCI (whitelist), SIN tocar
stock. Garantía dura: SUM(movimientos) global NUNCA cambia (cero pérdida de inventario).
"""
import io
import os
import sqlite3
import openpyxl
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


def _sum_mov():
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        return conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos").fetchone()[0]
    finally:
        conn.close()


def _excel(rows):
    """rows = [(codigo, inci, comercial), ...]. Header en fila 1, hoja INVENTARIO."""
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "INVENTARIO"
    ws.append(["CÓDIGO MP", "NOMBRE INCI", "NOMBRE COMERCIAL"])
    for r in rows:
        ws.append(list(r))
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf


def _post(c, ruta, rows, **fields):
    data = {k: v for k, v in fields.items()}
    data["file"] = (_excel(rows), "inv.xlsx")
    return c.post(ruta, data=data, content_type="multipart/form-data", headers=csrf_headers())


def test_diff_detecta_brecha(app, db_clean):
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MPQA001','NIACINAMIDE','Niacinamida B3',1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MPQA002','','Algo sin inci',1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MPQA003','UREA','Urea',1)")
    # MPQA777 está en maestro (pasa el FK) pero NO estará en el Excel → formula_sin_maestro
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MPQA777','VIEJO','Viejo cod',1)")
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('QA PROD','MPQA777','Viejo',5)")
    rows = [
        ("MPQA001", "NIACINAMIDE", "Niacinamida"),          # match
        ("MPQA002", "GLYCERIN", "Glicerina"),               # backfill (app vacío)
        ("MPQA003", "UREA STIBARIUM", "Urea"),              # mismatch (UREA != UREA STIBARIUM)
        ("MPQA050", "PANTHENOL", "Pantenol"),               # falta en maestro
        ("MPQA060", "PARFUM", "Citronela"),                 # repetido
        ("MPQA061", "PARFUM", "Eucalipto"),                 # repetido
    ]
    c = _login(app)
    d = _post(c, "/api/admin/maestro-inci-diff", rows).get_json()
    assert d["ok"], d
    cods_falta = {x["codigo"] for x in d["falta_en_maestro"]}
    assert "MPQA050" in cods_falta
    cods_mis = {x["codigo"] for x in d["inci_mismatch"]}
    assert "MPQA003" in cods_mis and "MPQA002" not in cods_mis  # vacío no es mismatch
    cods_fs = {x["codigo"] for x in d["formula_sin_maestro"]}
    assert "MPQA777" in cods_fs
    incis_rep = {x["inci"] for x in d["repetidos_inci"]}
    assert "PARFUM" in incis_rep


def test_sembrar_inserta_sin_tocar_stock(app, db_clean):
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo) VALUES ('MPQAEX','EXISTENTE',1)")
    _exec("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MPQAEX','Exist','Entrada',5000,'L1',date('now'))")
    s0 = _sum_mov()
    rows = [("MPQAEX", "EXISTENTE", "x"), ("MPQANEW", "ACIDO HIALURONICO", "AH bajo peso")]
    c = _login(app)
    # dry_run no escribe
    dprev = _post(c, "/api/admin/maestro-inci-aplicar", rows, modo="sembrar", dry_run="1").get_json()
    assert dprev["dry_run"] and dprev["total"] == 1 and dprev["cambios"][0]["codigo"] == "MPQANEW"
    n0 = sqlite3.connect(os.environ["DB_PATH"]).execute("SELECT COUNT(*) FROM maestro_mps WHERE codigo_mp='MPQANEW'").fetchone()[0]
    assert n0 == 0, "dry_run NO debe insertar"
    # aplicar real
    dapp = _post(c, "/api/admin/maestro-inci-aplicar", rows, modo="sembrar", dry_run="0").get_json()
    assert dapp["aplicado"] and dapp["aplicados"] == 1, dapp
    got = sqlite3.connect(os.environ["DB_PATH"]).execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp='MPQANEW'").fetchone()
    assert got and got[0] == "ACIDO HIALURONICO"
    assert _sum_mov() == s0, "sembrar NO debe tocar movimientos/stock"


def test_backfill_no_sobrescribe(app, db_clean):
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo) VALUES ('MPQAV','',1)")       # vacío
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo) VALUES ('MPQAP','VIEJO INCI',1)")  # poblado
    rows = [("MPQAV", "GLYCERIN", "g"), ("MPQAP", "OTRO INCI", "o")]
    c = _login(app)
    _post(c, "/api/admin/maestro-inci-aplicar", rows, modo="backfill-inci", dry_run="0")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    assert conn.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp='MPQAV'").fetchone()[0] == "GLYCERIN"
    assert conn.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp='MPQAP'").fetchone()[0] == "VIEJO INCI", "backfill NUNCA sobrescribe un INCI ya poblado"


def test_corregir_solo_whitelist(app, db_clean):
    import json
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo) VALUES ('MPQAA','MAL A',1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo) VALUES ('MPQAB','MAL B',1)")
    rows = [("MPQAA", "BIEN A", "a"), ("MPQAB", "BIEN B", "b")]
    c = _login(app)
    # dry_run muestra los 2
    dprev = _post(c, "/api/admin/maestro-inci-aplicar", rows, modo="corregir-inci", dry_run="1").get_json()
    assert dprev["total"] == 2
    # aplicar SOLO MPQAA (whitelist)
    dapp = _post(c, "/api/admin/maestro-inci-aplicar", rows, modo="corregir-inci", dry_run="0",
                 codigos=json.dumps(["MPQAA"])).get_json()
    assert dapp["aplicados"] == 1, dapp
    conn = sqlite3.connect(os.environ["DB_PATH"])
    assert conn.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp='MPQAA'").fetchone()[0] == "BIEN A"
    assert conn.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp='MPQAB'").fetchone()[0] == "MAL B", "sin whitelist NO se toca"


def test_cruce_detecta_stock_en_otro_codigo(app, db_clean):
    """El 'roto' Quincream: la fórmula usa un código sin stock, pero hay stock bajo OTRO
    código del MISMO INCI → cruce lo marca STOCK_EN_OTRO_CODIGO + sugiere unificar."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MPQF1','ACRYLATES COPOLYMER','Quincream',1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MPQF2','ACRYLATES COPOLYMER','Quimcream',1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MPQF3','GLYCERIN','Glicerina',1)")
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('QA CRUCE',10,1)")
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('QA CRUCE','MPQF1','Quincream',5)")
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('QA CRUCE','MPQF3','Glicerina',10)")
    # stock: 0 bajo MPQF1 (el de la fórmula) · 276 bajo MPQF2 (otro código mismo INCI) · MPQF3 con stock propio
    _exec("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MPQF2','Quimcream','Entrada',276,'LQ',date('now'))")
    _exec("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MPQF3','Glicerina','Entrada',1000,'LG',date('now'))")

    c = _login(app)
    d = c.get("/api/admin/formula-bodega-cruce").get_json()
    assert d["ok"], d
    byc = {i["codigo"]: i for i in d["items"]}
    assert byc["MPQF1"]["estado"] == "STOCK_EN_OTRO_CODIGO", byc["MPQF1"]
    assert any(z["codigo"] == "MPQF2" and abs(z["stock"] - 276) < 1 for z in byc["MPQF1"]["duplicados"]), byc["MPQF1"]
    assert byc["MPQF3"]["estado"] == "OK", byc["MPQF3"]
    assert d["resumen"]["stock_en_otro"] >= 1


def test_cruce_excluye_agua_y_no_unifica_parfum(app, db_clean):
    """Fixes 11-jun: (a) agua (controla_stock=0) NO aparece en el cruce; (b) PARFUM
    (INCI ambiguo · varias fragancias) NO se sugiere unificar (mezclaría fragancias)."""
    # agua infinita usada en una fórmula
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo,controla_stock) VALUES ('MPQAGUA','AQUA',1,0)")
    # 2 fragancias distintas, ambas INCI PARFUM (genérico ambiguo) · una sin stock usada en fórmula, otra con stock
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MPQPAR1','PARFUM','Citronela',1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MPQPAR2','PARFUM','Eucalipto',1)")
    _exec("INSERT INTO formula_headers (producto_nombre,lote_size_kg,activo) VALUES ('QA PARF',10,1)")
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('QA PARF','MPQAGUA','Agua',80)")
    _exec("INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES ('QA PARF','MPQPAR1','Citronela',1)")
    _exec("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MPQPAR2','Eucalipto','Entrada',500,'LE',date('now'))")

    c = _login(app)
    d = c.get("/api/admin/formula-bodega-cruce").get_json()
    cods = {i["codigo"]: i for i in d["items"]}
    assert "MPQAGUA" not in cods, "el agua (controla_stock=0) NO debe aparecer en el cruce"
    par1 = cods.get("MPQPAR1")
    assert par1 is not None
    assert par1["estado"] != "STOCK_EN_OTRO_CODIGO", "PARFUM no debe proponer unificar (fragancias distintas)"
    assert "INCI_AMBIGUO" in par1["flags"], par1
    assert not par1["duplicados"], "no sugiere unificar con la otra fragancia"


def test_inspector_mp_muestra_movimientos_y_neto(app, db_clean):
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES ('MPINSP','TEST INCI','Test comercial',1)")
    _exec("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MPINSP','Test','Entrada',300,'L1',date('now'))")
    _exec("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MPINSP','Test','Salida',120,'L1',date('now'))")
    c = _login(app)
    d = c.get("/api/admin/mp-inspeccionar?q=MPINSP").get_json()
    assert d["ok"]
    res = [x for x in d["resultados"] if x["codigo"] == "MPINSP"]
    assert res, d
    assert abs(res[0]["neto"] - 180) < 1, res[0]  # 300 - 120
    assert res[0]["n_movs"] == 2


def test_cero_perdida_stock_global(app, db_clean):
    """Estrella: tras sembrar+backfill+corregir, SUM(movimientos) global IDÉNTICO."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo) VALUES ('MPQAS1','',1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp,nombre_inci,activo) VALUES ('MPQAS2','MAL',1)")
    _exec("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MPQAS1','x','Entrada',8000,'LA',date('now'))")
    _exec("INSERT INTO movimientos (material_id,material_nombre,tipo,cantidad,lote,fecha) VALUES ('MPQAS2','y','Salida',1200,'LB',date('now'))")
    s0 = _sum_mov()
    import json
    rows = [("MPQAS1", "INCI UNO", "u"), ("MPQAS2", "INCI DOS", "d"), ("MPQANEWZ", "INCI TRES", "t")]
    c = _login(app)
    _post(c, "/api/admin/maestro-inci-aplicar", rows, modo="sembrar", dry_run="0")
    _post(c, "/api/admin/maestro-inci-aplicar", rows, modo="backfill-inci", dry_run="0")
    _post(c, "/api/admin/maestro-inci-aplicar", rows, modo="corregir-inci", dry_run="0", codigos=json.dumps(["MPQAS2"]))
    assert _sum_mov() == s0, "NINGUNA fase de convergencia INCI debe tocar el stock"
