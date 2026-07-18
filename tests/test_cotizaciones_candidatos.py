"""Auto-cotizar (18-jul): candidatos a cotizar = MPs activos SIN precio de referencia
(nunca comprados). Excluye los que ya tienen una ronda de cotización abierta."""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="catalina"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10)
    try:
        cur = conn.execute(sql, params); conn.commit(); return cur.lastrowid
    finally:
        conn.close()


def test_candidatos_sin_precio(app, db_clean):
    # nombres con prefijo "AAA" para que ordenen primero (el endpoint cap 60 · el seed trae muchos MP sin precio)
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,precio_referencia,activo,controla_stock) "
          "VALUES ('MP-COTZ1','AAA Material Sin Precio ZZ',0,1,1)")
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,precio_referencia,activo,controla_stock) "
          "VALUES ('MP-COTZ2','AAA Material Con Precio ZZ',5000,1,1)")
    c = _login(app)
    d = c.get("/api/compras/cotizaciones/candidatos").get_json()
    noms = [i["nombre"] for i in d.get("items", [])]
    assert "AAA Material Sin Precio ZZ" in noms, f"MP sin precio debe ser candidato · {noms[:8]}"
    assert "AAA Material Con Precio ZZ" not in noms, "MP con precio NO debe ser candidato"


def test_candidato_en_ronda_abierta_se_excluye(app, db_clean):
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,precio_referencia,activo,controla_stock) "
          "VALUES ('MP-COTZ3','AAA Material En Ronda ZZ',0,1,1)")
    # ya tiene una ronda de cotización abierta con esa descripción
    _exec("INSERT INTO cotizaciones (ronda_id,proveedor,descripcion,estado) "
          "VALUES ('COT-TEST','Prov X','AAA Material En Ronda ZZ','Pendiente')")
    c = _login(app)
    d = c.get("/api/compras/cotizaciones/candidatos").get_json()
    noms = [i["nombre"] for i in d.get("items", [])]
    assert "AAA Material En Ronda ZZ" not in noms, "un MP ya en ronda abierta no debe re-sugerirse"


def test_candidato_en_ronda_con_prefijo_cotizar_se_excluye(app, db_clean):
    # la ronda creada desde un candidato guarda la descripción con prefijo 'Cotizar: <nombre>'
    # (compras_html · nuevaRondaCotizModal) → el dedup debe pelar el prefijo, si no reaparece
    _exec("INSERT OR REPLACE INTO maestro_mps (codigo_mp,nombre_comercial,precio_referencia,activo,controla_stock) "
          "VALUES ('MP-COTZ4','AAA Material Prefijo ZZ',0,1,1)")
    _exec("INSERT INTO cotizaciones (ronda_id,proveedor,descripcion,estado) "
          "VALUES ('COT-TESTP','Prov X','Cotizar: AAA Material Prefijo ZZ','Pendiente')")
    c = _login(app)
    d = c.get("/api/compras/cotizaciones/candidatos").get_json()
    noms = [i["nombre"] for i in d.get("items", [])]
    assert "AAA Material Prefijo ZZ" not in noms, "ronda con prefijo 'Cotizar:' debe excluir el candidato"
