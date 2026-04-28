"""Tests Planificación Estratégica:
- ?dias=N (15/30/60/90/180/365) responde con campos extendidos
- mps_status por producción (alcanza/falta) — vista por producción específica
- mps_ok devuelto como lista (staff general)
- POST /api/programacion/planificacion/solicitar-bulk: agrupa por proveedor
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post(
        "/login",
        data={"username": user, "password": TEST_PASSWORD},
        headers=csrf_headers(),
        follow_redirects=False,
    )
    assert r.status_code == 302, f"login fallo: {r.status_code}"
    return c


def test_planificacion_acepta_dias_15(app, db_clean):
    """?dias=15 retorna respuesta con dias=15, horizonte_label esperado."""
    c = _login(app)
    r = c.get("/api/programacion/planificacion?dias=15")
    assert r.status_code == 200
    d = r.get_json()
    assert d["dias"] == 15
    assert "15" in (d.get("horizonte_label") or "")
    assert "producciones" in d
    assert "mps_deficit" in d
    assert "mps_ok" in d  # staff general


def test_planificacion_dias_clampea_max_365(app, db_clean):
    """?dias=9999 se clampa a 365 (no rompe)."""
    c = _login(app)
    r = c.get("/api/programacion/planificacion?dias=9999")
    assert r.status_code == 200
    assert r.get_json()["dias"] == 365


def test_planificacion_dias_invalido_default_60(app, db_clean):
    """?dias=abc cae a default 60."""
    c = _login(app)
    r = c.get("/api/programacion/planificacion?dias=abc")
    assert r.status_code == 200
    assert r.get_json()["dias"] == 60


def test_planificacion_back_compat_meses(app, db_clean):
    """?meses=6 sigue funcionando (back-compat) con dias derivado."""
    c = _login(app)
    r = c.get("/api/programacion/planificacion?meses=6")
    assert r.status_code == 200
    d = r.get_json()
    assert d["meses"] == 6
    # 6 meses ≈ 186 dias (6*31)
    assert d["dias"] == 186


def test_planificacion_producciones_tienen_mps_status(app, db_clean):
    """Cada producción debe traer mps_status (lista) y puede_producir (bool)."""
    c = _login(app)
    r = c.get("/api/programacion/planificacion?dias=60")
    assert r.status_code == 200
    d = r.get_json()
    for p in d.get("producciones", []):
        assert "mps_status" in p, f"falta mps_status en {p.get('producto')}"
        assert isinstance(p["mps_status"], list)
        assert "puede_producir" in p
        assert isinstance(p["puede_producir"], bool)
        assert "n_mps_alcanza" in p
        assert "n_mps_falta" in p
        # Cada item de mps_status debe tener los campos clave
        for m in p["mps_status"]:
            assert "material_id" in m
            assert "nombre" in m
            assert "necesario_g" in m
            assert "alcanza" in m
            assert isinstance(m["alcanza"], bool)


def test_planificacion_mps_ok_es_lista(app, db_clean):
    """mps_ok debe ser una lista, no solo un count (necesario para staff general)."""
    c = _login(app)
    r = c.get("/api/programacion/planificacion?dias=60")
    assert r.status_code == 200
    d = r.get_json()
    assert isinstance(d.get("mps_ok"), list)
    # mps_ok_count debe coincidir con len de mps_ok
    assert d.get("mps_ok_count") == len(d["mps_ok"])


def test_solicitar_bulk_requiere_auth(app, db_clean):
    """POST sin login → 401."""
    c = app.test_client()
    r = c.post(
        "/api/programacion/planificacion/solicitar-bulk",
        json={"dias": 60},
        headers=csrf_headers(),
    )
    assert r.status_code == 401


def test_solicitar_bulk_sin_deficits_ok(app, db_clean):
    """Si no hay déficits, retorna ok con mensaje sin solicitudes."""
    c = _login(app)
    # Con DB limpia no hay producciones → no hay déficits
    r = c.post(
        "/api/programacion/planificacion/solicitar-bulk",
        json={"dias": 15},
        headers=csrf_headers(),
    )
    assert r.status_code == 200
    d = r.get_json()
    assert d.get("ok") is True
    assert d.get("solicitudes_creadas") == []


def test_solicitar_bulk_dias_invalido_default(app, db_clean):
    """dias inválido → cae a 60, no rompe."""
    c = _login(app)
    r = c.post(
        "/api/programacion/planificacion/solicitar-bulk",
        json={"dias": "abc"},
        headers=csrf_headers(),
    )
    assert r.status_code == 200
