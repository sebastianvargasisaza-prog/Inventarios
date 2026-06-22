"""Duración de sesión por ROL (auth.session_expirada + enforcement).

Sebastián 22-jun-2026: admins login ~semanal (7 días), resto cada día (nueva
fecha Colombia → re-login → captura inicio de labores). Antes: 8h fijas para todos.
"""
from datetime import datetime, timezone, timedelta

from .conftest import TEST_PASSWORD, csrf_headers

COL = timezone(timedelta(hours=-5))


def _col(y, m, d, h, mi=0):
    """Epoch de una hora Colombia."""
    return datetime(y, m, d, h, mi, tzinfo=COL).timestamp()


def _se():
    # import dentro del test (tras el fixture app que configura env + sys.path)
    from auth import session_expirada
    return session_expirada


# ── Helper puro ──────────────────────────────────────────────────────────────
def test_admin_sesion_larga_no_expira_a_los_5_dias(app):
    assert _se()("sebastian", _col(2026, 6, 17, 8), _col(2026, 6, 22, 9)) is False


def test_admin_expira_pasados_los_7_dias(app):
    assert _se()("sebastian", _col(2026, 6, 14, 8), _col(2026, 6, 22, 9)) is True


def test_noadmin_mismo_dia_no_expira(app):
    assert _se()("catalina", _col(2026, 6, 22, 8), _col(2026, 6, 22, 16)) is False


def test_noadmin_nuevo_dia_expira(app):
    # logueó ayer 23:00 → hoy 07:00 = nueva fecha Colombia → re-login
    assert _se()("catalina", _col(2026, 6, 22, 23), _col(2026, 6, 23, 7)) is True


def test_noadmin_turno_larguisimo_mismo_dia_expira_por_tope(app):
    # mismo día pero 18h > 16h tope
    assert _se()("catalina", _col(2026, 6, 22, 5), _col(2026, 6, 22, 23)) is True


def test_login_time_invalido_expira(app):
    assert _se()("catalina", 0) is True
    assert _se()("sebastian", None) is True


def test_reloj_desfasado_no_expulsa(app):
    # login "en el futuro" (skew) → no expulsar
    assert _se()("catalina", _col(2026, 6, 22, 10), _col(2026, 6, 22, 8)) is False


def test_admin_dias_configurable(app):
    from auth import SESSION_DIAS_ADMIN
    assert SESSION_DIAS_ADMIN >= 1


# ── Enforcement end-to-end (before_request) ──────────────────────────────────
def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def test_enforcement_noadmin_expira_dia_anterior(app, db_clean):
    import time as _t
    c = _login(app, "catalina")
    # forzar login_time a ayer (>1 día Colombia)
    with c.session_transaction() as s:
        s["login_time"] = _t.time() - 2 * 86400
    r = c.get("/api/recepcion/seguimiento")
    assert r.status_code == 401  # sesión expirada → re-login


def test_enforcement_admin_sobrevive_3_dias(app, db_clean):
    import time as _t
    c = _login(app, "sebastian")
    with c.session_transaction() as s:
        s["login_time"] = _t.time() - 3 * 86400  # 3 días < 7
    r = c.get("/api/recepcion/seguimiento")
    assert r.status_code == 200
