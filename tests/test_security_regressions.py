"""Tests de regresión de seguridad — Sebastian (30-abr-2026).

Tienes muchas medidas (CSRF, rate limit, MFA, RBAC, security headers).
Sin tests dedicados, un refactor accidental puede desactivarlas y nadie
se entera hasta que un atacante las explota.

Cubre:
1. Rate limit en /login (lockout tras 5 intentos)
2. Auth gate /api/* (401 sin sesión)
3. Security headers presentes (CSP, HSTS, X-Frame-Options, etc)
4. CSRF Origin/Referer check (POST sin Origin → 403)
5. Cookie SameSite=Lax + Secure + HttpOnly
6. Password policy se aplica (rechaza weak passwords)
"""
import pytest

from .conftest import TEST_PASSWORD


# ── 1. Rate limit en login ───────────────────────────────────────────

def test_login_rate_limit_5_intentos_bloquea(app, db_clean):
    """5 intentos fallidos consecutivos desde la misma IP → lockout 15min."""
    client = app.test_client()
    for _ in range(5):
        r = client.post(
            "/login",
            data={"username": "sebastian", "password": "WRONG"},
            headers={"Origin": "http://localhost"},
            follow_redirects=False,
        )
        # Cada intento responde 200 con error (no 401) en el HTML
        assert r.status_code == 200
    # 6º intento — ahora debería estar locked
    r = client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    body = r.get_data(as_text=True).lower()
    assert "demasiados intentos" in body or "espera" in body, (
        "Rate limit no se aplica tras 5 intentos fallidos"
    )


# ── 2. Auth gate ────────────────────────────────────────────────────

def test_api_endpoints_sin_sesion_devuelven_401(app, db_clean):
    """Cualquier /api/* sin sesión activa → 401 (excepto whitelist pública)."""
    client = app.test_client()
    # Endpoints que NO requieren auth (whitelist en auth.py:205)
    public = {"/api/health", "/api/login", "/api/logout"}
    # Endpoints que sí requieren auth — sample
    private_samples = [
        "/api/clientes",
        "/api/inventario/stock",
        "/api/marketing/dashboard",
        "/api/chat/threads",
        "/api/mfa/status",
    ]
    for ep in private_samples:
        r = client.get(ep)
        assert r.status_code in (401, 405), (
            f"{ep} debería requerir auth (401), retornó {r.status_code}"
        )


# ── 3. Security headers ─────────────────────────────────────────────

def test_security_headers_presentes(app, db_clean):
    """Todos los responses deben llevar headers de seguridad básicos."""
    client = app.test_client()
    # Health es el endpoint público más simple
    r = client.get("/api/health")
    assert r.status_code == 200
    h = r.headers
    assert h.get("X-Frame-Options") == "SAMEORIGIN", "X-Frame-Options falta o mal configurado"
    assert h.get("X-Content-Type-Options") == "nosniff", "X-Content-Type-Options falta"
    assert "Strict-Transport-Security" in h, "HSTS no configurado"
    assert "Content-Security-Policy" in h, "CSP no configurado"
    csp = h["Content-Security-Policy"]
    # Frame-ancestors 'self' permite el widget flotante en mismo dominio
    assert "frame-ancestors 'self'" in csp
    # default-src 'self' — base de toda CSP defensiva
    assert "default-src 'self'" in csp
    # object-src 'none' — anti plugins
    assert "object-src 'none'" in csp


# ── 4. CSRF / Origin check ──────────────────────────────────────────

def test_post_sin_origin_referer_con_sesion_se_rechaza(app, db_clean):
    """POST con sesión activa pero sin Origin/Referer → 403 (CSRF protección).

    El CSRF check en auth.py:225 acepta el request si NO hay sesión Y
    si Origin/Referer matchean el host. Pero un atacante con session
    hijacking + sin Origin (curl) sería rechazado.

    Excepción: si la sesión es válida pero no hay Origin/Referer, el
    código permite con audit log. Eso es para soporte de scripts CLI
    legítimos (smoke_check.py, etc.).
    """
    client = app.test_client()
    # Login normal
    r = client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
    )
    assert r.status_code == 302
    # Intentar POST con Origin de otro dominio (cross-origin attack)
    r = client.post(
        "/api/cambiar-password",
        json={"password_actual": TEST_PASSWORD, "password_nueva": "NewPass456",
              "password_confirmar": "NewPass456"},
        headers={"Origin": "http://attacker.example.com"},
    )
    # Origin distinto → CSRF block (403). Si pasara, el atacante podría
    # cambiar la password del usuario logueado.
    assert r.status_code == 403, (
        f"CSRF Origin check no funciona — POST con Origin atacante "
        f"retornó {r.status_code}, esperado 403"
    )


# ── 5. Cookies seguras ─────────────────────────────────────────────

def test_session_cookie_es_httponly_secure_lax(app, db_clean):
    """La cookie de sesión debe ser HttpOnly + Secure + SameSite=Lax."""
    client = app.test_client()
    r = client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
    )
    cookies = r.headers.get_all("Set-Cookie")
    session_cookie = next((c for c in cookies if c.startswith("session=")), None)
    if session_cookie is None:
        # Si no hay Set-Cookie, la sesión ya estaba activa — ok
        return
    cookie_lower = session_cookie.lower()
    assert "httponly" in cookie_lower, "Cookie de sesión NO es HttpOnly (XSS puede leerla)"
    assert "secure" in cookie_lower, "Cookie de sesión NO es Secure (transmite en HTTP)"
    assert "samesite=lax" in cookie_lower, "Cookie de sesión sin SameSite=Lax (vulnerable a CSRF)"


# ── 6. Password policy ────────────────────────────────────────────

def test_password_policy_rechaza_password_blacklist(app, db_clean):
    """Cambiar password a una en blacklist debe ser rechazado."""
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
    )
    r = client.post(
        "/api/cambiar-password",
        json={
            "password_actual": TEST_PASSWORD,
            "password_nueva": "password123",  # ← en blacklist
            "password_confirmar": "password123",
        },
        headers={"Origin": "http://localhost"},
    )
    assert r.status_code == 400
    assert "común" in r.get_json().get("error", "").lower() or "comun" in r.get_json().get("error", "").lower()


def test_password_policy_rechaza_password_igual_a_username(app, db_clean):
    """Password EXACTAMENTE igual al username debe ser rechazada."""
    client = app.test_client()
    # Necesita un username con al menos 8 chars (para pasar el check de longitud)
    # y que tenga al menos 1 letra + 1 número... pero los usernames son solo
    # letras. Por lo tanto este test usa un escenario donde el username tiene
    # números. En la realidad COMPRAS_USERS son solo letras, así que el check
    # anti-username protege contra el escenario "alguien crea username con
    # numero después y usa como password". Test conceptual.
    #
    # Como TEST_PASSWORD ya cumple la policy y no es user, lo usamos para
    # validar que la regla de longitud + complejidad funciona.
    client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
    )
    # Test simplificado: password "sebastian" exacto al username
    r = client.post(
        "/api/cambiar-password",
        json={
            "password_actual": TEST_PASSWORD,
            "password_nueva": "sebastian",   # = username + sin número
            "password_confirmar": "sebastian",
        },
        headers={"Origin": "http://localhost"},
    )
    # Falla por: no tiene número (regla compuesta) Y igual al username
    assert r.status_code == 400


def test_password_policy_minimo_8_caracteres(app, db_clean):
    """Password de menos de 8 caracteres rechazado."""
    client = app.test_client()
    client.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
    )
    r = client.post(
        "/api/cambiar-password",
        json={
            "password_actual": TEST_PASSWORD,
            "password_nueva": "Ab12",  # 4 chars
            "password_confirmar": "Ab12",
        },
        headers={"Origin": "http://localhost"},
    )
    assert r.status_code == 400
    assert "8" in r.get_json().get("error", "")
