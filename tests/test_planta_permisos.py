"""Tests de permisos granulares en módulo Planta (Sprint 1)."""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo {user}: {r.status_code}"
    return c


# ── POST /api/movimientos requires PLANTA/CALIDAD/ADMIN ──────────────────────

def test_movimientos_post_blocked_for_marketing(app, db_clean):
    """Felipe (Marketing) NO debe poder registrar movimientos de inventario."""
    c = _login(app, "felipe")
    r = c.post("/api/movimientos",
               json={"material_id": "X", "material_nombre": "Test", "cantidad": 100,
                     "tipo": "Entrada"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_movimientos_post_allowed_for_planta(app, db_clean):
    """Luis (Planta) SÍ puede."""
    c = _login(app, "luis")
    r = c.post("/api/movimientos",
               json={"material_id": "TEST_X", "material_nombre": "Test",
                     "cantidad": 100, "tipo": "Entrada"},
               headers=csrf_headers())
    assert r.status_code == 201


def test_movimientos_post_allowed_for_calidad(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/movimientos",
               json={"material_id": "TEST_Y", "material_nombre": "Test",
                     "cantidad": 50, "tipo": "Entrada"},
               headers=csrf_headers())
    assert r.status_code == 201


def test_movimientos_get_open_to_authenticated(app, db_clean):
    """GET es lectura — cualquier autenticado puede consultar."""
    c = _login(app, "valentina")
    r = c.get("/api/movimientos")
    assert r.status_code == 200


# ── POST /api/produccion ─────────────────────────────────────────────────────

def test_produccion_blocked_for_marketing(app, db_clean):
    c = _login(app, "jefferson")
    r = c.post("/api/produccion",
               json={"producto": "TEST", "cantidad_kg": 1},
               headers=csrf_headers())
    assert r.status_code == 403


# ── POST /api/recepcion ──────────────────────────────────────────────────────

def test_recepcion_blocked_for_marketing(app, db_clean):
    c = _login(app, "felipe")
    r = c.post("/api/recepcion",
               json={"codigo_mp": "MP_TEST", "cantidad": 10},
               headers=csrf_headers())
    assert r.status_code == 403


def test_recepcion_allowed_for_planta(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/recepcion",
               json={"codigo_mp": "MP_TEST_R", "cantidad": 10,
                     "nombre_inci": "Test", "nombre_comercial": "Test MP",
                     "lote": "TESTLOTE001"},
               headers=csrf_headers())
    # Esperado 200 o 201 si todo OK; lo importante es que NO sea 403
    assert r.status_code != 403


# ── POST /api/lotes/liberar (QC) ─────────────────────────────────────────────

def test_liberar_lote_blocked_for_planta_user(app, db_clean):
    """Operario de planta NO puede liberar QC."""
    c = _login(app, "luis")
    r = c.post("/api/lotes/liberar",
               json={"id": 999, "accion": "APROBAR"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_liberar_lote_allowed_for_calidad(app, db_clean):
    """Yuliel (analista QC) SÍ puede."""
    c = _login(app, "yuliel")
    r = c.post("/api/lotes/liberar",
               json={"id": 999, "accion": "APROBAR"},
               headers=csrf_headers())
    # 999 no existe → puede ser 404, lo importante: NO 403
    assert r.status_code != 403


# ── POST /api/lotes/cc-review (QC) ───────────────────────────────────────────

def test_cc_review_blocked_for_marketing(app, db_clean):
    c = _login(app, "jefferson")
    r = c.post("/api/lotes/cc-review",
               json={"mov_id": 1},
               headers=csrf_headers())
    assert r.status_code == 403


def test_cc_review_allowed_for_calidad(app, db_clean):
    c = _login(app, "miguel")
    r = c.post("/api/lotes/cc-review",
               json={"mov_id": 1},
               headers=csrf_headers())
    # Mov 1 puede no existir, pero permiso debe pasar
    assert r.status_code != 403


# ── POST /api/lotes/cuarentena/<id>/liberar ──────────────────────────────────

def test_liberar_cuarentena_blocked_for_planta(app, db_clean):
    """Operarios de planta no pueden liberar cuarentena (decisión QC)."""
    c = _login(app, "smurillo")
    r = c.post("/api/lotes/cuarentena/1/liberar",
               json={"decision": "Aprobado"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_liberar_cuarentena_allowed_for_calidad(app, db_clean):
    c = _login(app, "laura")
    r = c.post("/api/lotes/cuarentena/1/liberar",
               json={"decision": "Aprobado"},
               headers=csrf_headers())
    # 1 puede no existir; importante: NO 403
    assert r.status_code != 403


# ── reset_movimientos triple confirmación ────────────────────────────────────

def test_reset_movimientos_blocked_for_non_admin(app, db_clean):
    c = _login(app, "luis")
    r = c.post("/api/reset-movimientos",
               json={"confirmacion": "BORRAR_TODO_INVENTARIO_AHORA"},
               headers=csrf_headers())
    assert r.status_code == 403


def test_reset_movimientos_requires_exact_confirmacion(admin_client, db_clean):
    """Admin pero confirmación incorrecta → 400."""
    r = admin_client.post("/api/reset-movimientos",
                          json={"confirmacion": "BORRAR"},  # demasiado simple
                          headers=csrf_headers())
    assert r.status_code == 400


def test_reset_movimientos_requires_today_date(admin_client, db_clean):
    """Confirmación correcta pero fecha vieja → 400 (anti copy-paste)."""
    r = admin_client.post("/api/reset-movimientos",
                          json={"confirmacion": "BORRAR_TODO_INVENTARIO_AHORA",
                                "fecha_actual": "2020-01-01"},
                          headers=csrf_headers())
    assert r.status_code == 400


# ── Endpoint duplicado eliminado ─────────────────────────────────────────────

def test_old_trazabilidad_endpoint_removed(admin_client, db_clean):
    """El endpoint duplicado /api/trazabilidad/<lote> ya no existe.
    El que queda es /api/trazabilidad/lote/<path:lote>."""
    r = admin_client.get("/api/trazabilidad/SOMELOTE")
    # Debe ser 404 (ruta no existe) — el de path está en otra URL
    assert r.status_code == 404
    # El bueno sigue funcionando
    r = admin_client.get("/api/trazabilidad/lote/SOMELOTE")
    assert r.status_code == 200
