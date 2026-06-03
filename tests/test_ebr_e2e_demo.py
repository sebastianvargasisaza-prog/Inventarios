"""DEMO/PROOF E2E del Batch Record (EBR · reemplazo MyBatch).

Recorre la cadena REALISTA completa tal como la usará planta y muestra (con
prints, correr con `-s`) qué devuelve cada pantalla del runner:

  fórmula existente -> generar MBR -> aprobar (e-firma) -> EBR_MODE=warn ->
  aceptar producción (EBR auto) -> listado runner -> abrir EBR -> pesaje +
  2ª firma de verificación -> ejecutar pasos (doble firma) -> conciliación de
  material -> observaciones -> completar (yield) -> liberar (e-firma) -> PDF legajo.

No es un golden path (no entra al gate de guardian); es la prueba viva de que
el módulo está funcional end-to-end. Si algo del flujo se rompe, este test lo
caza con un assert claro.
"""
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers

PRODUCTO = "ZZ-EBR-DEMO"


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {"Content-Type": "application/json"}; h.update(csrf_headers()); return h


def _firmar(c, *, record_table, record_id, meaning):
    rc = c.post("/api/sign/challenge", json={"password": TEST_PASSWORD},
                headers=csrf_headers())
    assert rc.status_code == 200, rc.data
    token = rc.get_json()["token"]
    rs = c.post("/api/sign", json={
        "record_table": record_table, "record_id": str(record_id),
        "meaning": meaning, "challenge_token": token,
    }, headers=csrf_headers())
    assert rs.status_code == 201, rs.data
    return rs.get_json()["signature_id"]


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def test_ebr_e2e_demo(app, db_clean, monkeypatch):
    import blueprints.programacion as _prog
    c = _login(app, "sebastian")
    # e-firma necesita cédula en la identidad
    c.patch("/api/identidad/sebastian",
            json={"cedula": "77777777", "nombre_completo": "Sebastián Vargas"},
            headers=_h())

    print("\n" + "=" * 70)
    print("DEMO BATCH RECORD (EBR) · cadena completa")
    print("=" * 70)

    # ── 1. La fórmula ya existe en EOS (no se re-ingresa la receta) ──────────
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES ('MP-A','Agua',1)")
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES ('MP-B','Glicerina',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 1, 1)", (PRODUCTO,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) VALUES (?,'MP-A','Agua',60,600)", (PRODUCTO,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote) VALUES (?,'MP-B','Glicerina',40,400)", (PRODUCTO,))
    print(f"[1] Fórmula '{PRODUCTO}' (1000 g/lote): Agua 60% · Glicerina 40%")

    # ── 2. Generar MBR desde la fórmula ─────────────────────────────────────
    r = c.post("/api/brd/mbr/generar-desde-formula",
               json={"producto_nombre": PRODUCTO}, headers=_h())
    assert r.status_code == 201, r.data
    mbr_id = r.get_json()["id"]
    print(f"[2] MBR #{mbr_id} generado desde fórmula · {r.get_json()['pasos']} pasos (draft)")

    # ── 3. Aprobar el MBR (e-firma de Calidad) ──────────────────────────────
    assert c.post(f"/api/brd/mbr/{mbr_id}/submit", json={}, headers=_h()).status_code == 200
    sig = _firmar(c, record_table="mbr_templates", record_id=mbr_id, meaning="aprueba")
    ra = c.post(f"/api/brd/mbr/{mbr_id}/aprobar",
                json={"signature_id": sig}, headers=_h())
    assert ra.status_code == 200, ra.data
    print(f"[3] MBR #{mbr_id} APROBADO con e-firma (meaning=aprueba)")

    # ── 4. Aceptar producción con EBR_MODE=warn -> EBR automático ────────────
    monkeypatch.setattr(_prog, "EBR_MODE", "warn")
    pp = _exec("INSERT INTO produccion_programada (producto, fecha_programada, lotes, estado) "
               "VALUES (?, date('now'), 1, 'pendiente')", (PRODUCTO,))
    ra = c.post(f"/api/planta/aceptar-produccion/{pp}", json={}, headers=_h())
    assert ra.status_code == 200, ra.data
    ebr_info = ra.get_json().get("ebr") or {}
    assert ebr_info.get("ok") is True, ra.data
    print(f"[4] Producción #{pp} aceptada -> EBR creado automático (EBR_MODE=warn): {ebr_info}")

    # ── 5. Listado del runner (lo que ves en Fabricación -> Legajos EBR) ─────
    rl = c.get("/api/brd/ebr")
    items = rl.get_json()["items"]
    mine = [it for it in items if it["produccion_id"] == pp]
    assert mine, "el EBR no aparece en el listado del runner"
    ebr_id = mine[0]["id"]
    print(f"[5] Runner GET /api/brd/ebr -> {len(items)} legajo(s). El nuestro: "
          f"EBR #{ebr_id} lote={mine[0]['lote']} fase={mine[0]['fase']} estado={mine[0]['estado']}")

    # ── 6. Abrir EBR (detalle + pasos) ──────────────────────────────────────
    det = c.get(f"/api/brd/ebr/{ebr_id}").get_json()
    pasos = det["pasos"]
    print(f"[6] Abrir EBR #{ebr_id}: {len(pasos)} pasos · estado={det['estado']}")

    # ── 7. Estación PESAJE + 2ª firma de verificación ───────────────────────
    rp = c.post(f"/api/brd/ebr/{ebr_id}/pesajes",
                json={"material_id": "MP-A", "cantidad_real_g": 598.0, "lote_mp": "L-AGUA-01"},
                headers=_h())
    assert rp.status_code in (200, 201), rp.data
    pj = rp.get_json()
    print(f"[7a] Pesaje MP-A: teórico={pj.get('cantidad_teorica_g')} real=598 "
          f"delta={pj.get('delta_g')} ({pj.get('delta_pct')}%) · pesó sebastian")
    # un pesaje pesado por OTRA persona (mayerlin) para verificar con segregación
    pid2 = _exec("INSERT INTO ebr_pesajes (ebr_id, material_id, material_nombre, "
                 "cantidad_teorica_g, cantidad_real_g, delta_g, delta_pct, lote_mp, "
                 "pesado_por, pesado_at_utc) VALUES (?,'MP-B','Glicerina',400,401,1,0.25,"
                 "'L-GLI-01','mayerlin',datetime('now','utc'))", (ebr_id,))
    sigv = _firmar(c, record_table="ebr_pesajes", record_id=pid2, meaning="supervisa")
    rv = c.post(f"/api/brd/ebr/{ebr_id}/pesajes/{pid2}/verificar",
                json={"signature_id": sigv}, headers=_h())
    assert rv.status_code == 200, rv.data
    print(f"[7b] 2ª firma: pesaje MP-B (pesó mayerlin) VERIFICADO por "
          f"{rv.get_json()['verificado_por']} (segregación OK)")

    # ── 8. Ejecutar los pasos (con doble firma donde aplique) ───────────────
    for p in pasos:
        orden = p["orden"]
        c.post(f"/api/brd/ebr/{ebr_id}/pasos/{orden}/iniciar", json={}, headers=_h())
        rc1 = c.post(f"/api/brd/ebr/{ebr_id}/pasos/{orden}/completar",
                     json={"observaciones": f"Paso {orden} conforme"}, headers=_h())
        if rc1.status_code == 400:  # requiere e-firma del ejecutor
            sgp = _firmar(c, record_table="ebr_pasos_ejecutados",
                          record_id=p["id"], meaning="ejecuta")
            rc1 = c.post(f"/api/brd/ebr/{ebr_id}/pasos/{orden}/completar",
                         json={"observaciones": f"Paso {orden} conforme",
                               "signature_id": sgp}, headers=_h())
        assert rc1.status_code == 200, (orden, rc1.data)
    print(f"[8] {len(pasos)} pasos ejecutados y completados")

    # ── 9. Conciliación de material (envases) ───────────────────────────────
    rcm = c.post(f"/api/brd/ebr/{ebr_id}/conciliacion-material",
                 json={"tipo": "envase", "material_nombre": "Frasco 30 ml",
                       "cant_requerida": 100, "cant_recibida": 100, "cant_devuelta": 3},
                 headers=_h())
    assert rcm.status_code in (200, 201), rcm.data
    cm = c.get(f"/api/brd/ebr/{ebr_id}/conciliacion-material").get_json()["items"][0]
    print(f"[9] Conciliación: recibida={cm['cant_recibida']} devuelta={cm['cant_devuelta']} "
          f"-> utilizada={cm['cant_utilizada']} (calculada)")

    # ── 10. Observaciones (bitácora) ────────────────────────────────────────
    ro = c.post(f"/api/brd/ebr/{ebr_id}/observaciones",
                json={"descripcion": "Proceso sin novedades. Temperatura estable."},
                headers=_h())
    assert ro.status_code in (200, 201), ro.data
    print("[10] Observación de bitácora registrada")

    # ── 11. Completar EBR (calcula yield) ───────────────────────────────────
    rcomp = c.post(f"/api/brd/ebr/{ebr_id}/completar",
                   json={"cantidad_real_g": 970.0}, headers=_h())
    assert rcomp.status_code == 200, rcomp.data
    dcomp = rcomp.get_json()
    print(f"[11] EBR completado · cantidad_real=970 g · yield={dcomp.get('yield_pct')}%")

    # ── 12. Liberar (e-firma de Calidad, meaning=libera) ────────────────────
    sigl = _firmar(c, record_table="ebr_ejecuciones", record_id=ebr_id, meaning="libera")
    rlib = c.post(f"/api/brd/ebr/{ebr_id}/liberar",
                  json={"signature_id": sigl}, headers=_h())
    assert rlib.status_code == 200, rlib.data
    assert rlib.get_json()["estado"] == "liberado"
    print("[12] EBR LIBERADO con e-firma (lote conforme · ahora inmutable)")

    # ── 13. PDF del legajo ──────────────────────────────────────────────────
    rpdf = c.get(f"/api/brd/ebr/{ebr_id}/pdf")
    assert rpdf.status_code == 200, rpdf.data
    assert rpdf.data[:4] == b"%PDF", "el legajo no es un PDF válido"
    print(f"[13] PDF legajo generado · {len(rpdf.data):,} bytes")
    print("=" * 70)
    print("RESULTADO: cadena EBR funcional end-to-end OK")
    print("=" * 70 + "\n")
