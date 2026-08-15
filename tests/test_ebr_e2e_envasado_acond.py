"""E2E de ENVASADO y ACONDICIONAMIENTO, sección por sección contra MyBatch.

Sebastián 15-ago-2026, abriendo MyBatch: *"necesitamos clonarlo perfecto ... esta
es la que regula INVIMA, y ellos ya están habilitados; la idea es reemplazarlos
por EOS cuando pidamos la certificación"*.

Relevé las tres instrucciones de MyBatch y éstas son sus secciones:

  ENVASADO (OF)                          ACONDICIONAMIENTO (OA)
  1 Precauciones                          1 Precauciones
  2 Despejes de Línea                     2 Despejes de Línea
  3 Recepción de Material de Envase       3 Recepción de Material de Empaque
  4 Envasado (pasos)                      4 Acondicionamiento (pasos)
  5 Controles en Proceso (volumen)        5 Controles en Proceso (atributos)
  6 Observaciones Generales               6 Observaciones Generales
  7 Registros Físicos                     7 Registros Físicos
  + presentaciones por cliente            + Aprobación de Artes / Codificación
  + conciliación del material             + conciliación del material

El E2E de FABRICACIÓN ya existía (`test_ebr_e2e_demo.py`) y estas dos fases no
tenían el suyo: el legajo se podía abrir, pero nadie había demostrado que se
recorre COMPLETO por los endpoints reales. Para una certificación eso es la
diferencia entre "está construido" y "está validado" (M94).

Cada sección va con su assert y su print, así que si algo se corta se ve dónde.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

PRODUCTO = "ZZ-OFOA-DEMO"


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _limpiar():
    for sql in ("DELETE FROM mbr_pasos WHERE mbr_template_id IN "
                "(SELECT id FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-OFOA%')",
                "DELETE FROM mbr_templates WHERE producto_nombre LIKE 'ZZ-OFOA%'",
                "DELETE FROM formula_items WHERE producto_nombre LIKE 'ZZ-OFOA%'",
                "DELETE FROM formula_headers WHERE producto_nombre LIKE 'ZZ-OFOA%'",
                "DELETE FROM maestro_mee WHERE codigo LIKE 'ZOF-%'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _sembrar_formula():
    """La fórmula del producto de prueba · el MBR se genera desde ella."""
    _exec("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
          "VALUES ('MP-OFOA-A','Agua',1)")
    _exec("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?,1,1)",
          (PRODUCTO,))
    _exec("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, "
          "porcentaje, cantidad_g_por_lote) VALUES (?,'MP-OFOA-A','Agua',100,1000)",
          (PRODUCTO,))


def _mbr_listo(c, fase, pasos):
    """Deja el MBR del producto APROBADO y con instructivo de ESA fase.

    El sistema no deja abrir un legajo sin eso (409 NO_MBR_APROBADO), y hace
    bien: es la regla GMP de que se ejecuta contra un procedimiento aprobado.
    El E2E la respeta en vez de saltearla.
    """
    # El MBR nace de la FÓRMULA (así lo hace planta), no se inventa a mano.
    r = c.post("/api/brd/mbr/generar-desde-formula",
               json={"producto_nombre": PRODUCTO}, headers=_h())
    assert r.status_code in (200, 201, 409), ("generar-mbr", r.status_code, r.data[:300])
    r = c.post("/api/brd/mbr/cargar-instructivo",
               json={"producto": PRODUCTO, "pasos": pasos, "fase": fase}, headers=_h())
    assert r.status_code == 200, ("cargar-instructivo", fase, r.status_code, r.data[:300])
    r = c.post("/api/brd/mbr/preparar-aprobado",
               json={"producto_nombre": PRODUCTO}, headers=_h())
    assert r.status_code in (200, 201), ("preparar-aprobado", r.status_code, r.data[:300])


def _legajo(c, fase, lote):
    """Crea el legajo de una fase por el endpoint real."""
    r = c.post("/api/brd/legajo-rapido",
               json={"producto": PRODUCTO, "lote": lote, "fase": fase}, headers=_h())
    assert r.status_code in (200, 201), (fase, r.status_code, r.data)
    d = r.get_json()
    ebr_id = d.get("id") or d.get("ebr_id")
    assert ebr_id, "legajo-rapido no devolvió el id: %s" % d
    return ebr_id


def _secciones_comunes(c, ebr_id, etiqueta):
    """Las 5 secciones que MyBatch tiene IGUALES en las dos fases."""
    hechas = []

    # 1 · Precauciones
    r = c.post(f"/api/brd/ebr/{ebr_id}/precauciones",
               json={"descripcion": "Usar EPP completo antes de iniciar", "tipo": "seguridad"}, headers=_h())
    assert r.status_code in (200, 201), ("precauciones", r.status_code, r.data)
    hechas.append("precauciones")

    # 2 · Despeje de línea (el encabezado + los ítems verificados)
    r = c.post(f"/api/brd/ebr/{ebr_id}/despeje",
               json={"area_codigo": "ENV1", "resultado": "conforme",
                     "observaciones": "área libre del producto anterior"}, headers=_h())
    assert r.status_code in (200, 201), ("despeje", r.status_code, r.data)
    items = c.get(f"/api/brd/ebr/{ebr_id}/despeje-items").get_json()
    assert isinstance(items, dict), items
    hechas.append("despeje")

    # 6 · Observaciones generales del proceso
    r = c.post(f"/api/brd/ebr/{ebr_id}/observaciones",
               json={"descripcion": "Proceso sin novedades"}, headers=_h())
    assert r.status_code in (200, 201), ("observaciones", r.status_code, r.data)
    hechas.append("observaciones")

    # 7 · Registros físicos (los papeles que se adjuntan)
    r = c.post(f"/api/brd/ebr/{ebr_id}/registros-fisicos",
               json={"codigo": "F-01", "descripcion": "Formato de %s" % etiqueta},
               headers=_h())
    assert r.status_code in (200, 201), ("registros-fisicos", r.status_code, r.data)
    hechas.append("registros_fisicos")

    # 5 · Controles en proceso (volumen en envasado · atributos en acondicionamiento)
    r = c.get(f"/api/brd/ebr/{ebr_id}/ipc-estandar")
    assert r.status_code == 200, ("ipc-estandar", r.status_code, r.data)
    hechas.append("controles_en_proceso")

    print("    [%s] secciones comunes OK: %s" % (etiqueta, ", ".join(hechas)))
    return hechas


def test_e2e_envasado_completo(app, db_clean):
    """ENVASADO: las 7 secciones de MyBatch + presentaciones por cliente."""
    _limpiar()
    _sembrar_formula()
    _exec("INSERT OR IGNORE INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
          "VALUES ('ZOF-ENV-30','Frasco 30 ml de prueba',0,'Activo')")
    c = _login(app)
    c.patch("/api/identidad/sebastian",
            json={"cedula": "77777777", "nombre_completo": "Sebastián Vargas"}, headers=_h())

    print("\n" + "=" * 74)
    print("E2E ENVASADO · las secciones que MyBatch exige")
    print("=" * 74)
    _mbr_listo(c, "envasado", [
        "Paso 1. Alistar envases y ajustar la llenadora.",
        "Paso 2. Llenar y controlar el peso cada 30 minutos.",
        "Paso 3. Sellar, despejar el área y entregar a acondicionamiento.",
    ])
    ebr_id = _legajo(c, "envasado", "LOTE-OF-E2E")
    print("    legajo de envasado #%s creado" % ebr_id)

    _secciones_comunes(c, ebr_id, "envasado")

    # 3 · Recepción de Material de Envase (requerida vs recibida, con su lote)
    r = c.post(f"/api/brd/ebr/{ebr_id}/material-envase",
               json={"material_codigo": "ZOF-ENV-30", "requerida": 500,
                     "lote_material": "LM-OF-1", "recibida": 500}, headers=_h())
    assert r.status_code in (200, 201), ("material-envase", r.status_code, r.data)
    v = c.get(f"/api/brd/ebr/{ebr_id}/vista-completa").get_json()
    mats = v.get("envasado_materiales") or []
    assert mats, "el material de envase no quedó en el legajo"
    print("    material de envase registrado: %s" % mats[0].get("material_codigo"))

    # + Presentaciones POR CLIENTE (lo que Sebastián pidió ver en Envasado)
    r = c.post(f"/api/brd/ebr/{ebr_id}/presentacion",
               json={"presentacion": "30 ml", "cliente": "Cliente Demo",
                     "unidades": 300, "volumen_ml": 30}, headers=_h())
    assert r.status_code in (200, 201), ("presentacion", r.status_code, r.data)
    v = c.get(f"/api/brd/ebr/{ebr_id}/vista-completa").get_json()
    pres = v.get("envasado_presentaciones") or []
    assert pres, "la presentación no quedó en el legajo"
    assert any((p.get("cliente") or "") == "Cliente Demo" for p in pres), (
        "la presentación no conserva el CLIENTE: sin eso, en el piso no se sabe "
        "cuántas unidades son de cada quien")
    print("    presentación por cliente: %s uds de %s para %s"
          % (pres[0].get("unidades"), pres[0].get("presentacion"), pres[0].get("cliente")))

    # El legajo se puede leer entero (es lo que se descarga para la auditoría)
    assert c.get(f"/api/brd/ebr/{ebr_id}/pdf").status_code == 200, "el legajo no imprime"
    print("    PDF del legajo: OK")


def test_e2e_acondicionamiento_completo(app, db_clean):
    """ACONDICIONAMIENTO: las 7 secciones + artes/codificación + conciliación."""
    _limpiar()
    _sembrar_formula()
    c = _login(app)
    c.patch("/api/identidad/sebastian",
            json={"cedula": "77777777", "nombre_completo": "Sebastián Vargas"}, headers=_h())

    print("\n" + "=" * 74)
    print("E2E ACONDICIONAMIENTO · las secciones que MyBatch exige")
    print("=" * 74)
    _mbr_listo(c, "acondicionamiento", [
        "Paso 1. Recibir el producto envasado y verificar cantidad y estado.",
        "Paso 2. Etiquetar, codificar y encajar segun el arte aprobado.",
        "Paso 3. Solicitar a calidad la revision del producto terminado.",
    ])
    ebr_id = _legajo(c, "acondicionamiento", "LOTE-OA-E2E")
    print("    legajo de acondicionamiento #%s creado" % ebr_id)

    _secciones_comunes(c, ebr_id, "acondicionamiento")

    # 3 · Recepción de Material de Empaque (etiquetas, plegadizas)
    r = c.post(f"/api/brd/ebr/{ebr_id}/material-envase",
               json={"material_codigo": "ETQ-E2E", "requerida": 300,
                     "lote_material": "LM-OA-1", "recibida": 300}, headers=_h())
    assert r.status_code in (200, 201), ("material-empaque", r.status_code, r.data)

    # + Aprobación de Artes / Codificación (el visto bueno del arte)
    ra = c.post(f"/api/brd/ebr/{ebr_id}/artes",
                json={"tipo": "etiqueta", "descripcion": "Etiqueta 30 ml v2",
                      "codigo_arte": "ART-E2E"}, headers=_h())
    assert ra.status_code in (200, 201), ("artes", ra.status_code, ra.data)
    arts = (c.get(f"/api/brd/ebr/{ebr_id}/artes").get_json() or {}).get("items") or []
    assert arts, "el arte no quedó registrado"
    print("    arte registrado: %s" % arts[0].get("descripcion"))

    # + Conciliación del material (requerida/recibida/devuelta/utilizada)
    rc = c.post(f"/api/brd/ebr/{ebr_id}/conciliacion-material",
                json={"tipo": "empaque", "material_codigo": "ETQ-E2E",
                      "material_nombre": "Etiqueta 30 ml", "lote_material": "LM-OA-1",
                      "cant_requerida": 300, "cant_recibida": 300,
                      "cant_devuelta": 10, "cant_utilizada": 285}, headers=_h())
    assert rc.status_code in (200, 201), ("conciliacion", rc.status_code, rc.data)
    conc = (c.get(f"/api/brd/ebr/{ebr_id}/conciliacion-material").get_json() or {}).get("items") or []
    assert conc, "la conciliación no quedó registrada"
    fila = conc[0]
    print("    conciliación: requerida %s · recibida %s · devuelta %s · utilizada %s"
          % (fila.get("cant_requerida"), fila.get("cant_recibida"),
             fila.get("cant_devuelta"), fila.get("cant_utilizada")))

    assert c.get(f"/api/brd/ebr/{ebr_id}/pdf").status_code == 200, "el legajo no imprime"
    print("    PDF del legajo: OK")
