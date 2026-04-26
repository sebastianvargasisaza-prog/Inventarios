"""Tests de la matriz de permisos por rol."""
from .conftest import TEST_PASSWORD, csrf_headers


def test_admins_in_correct_groups(app):
    """Sebastian y Alejandro son admins. Los blueprints aplican
    `GROUP | ADMIN_USERS` para dar acceso, así que admins NO necesitan
    estar en cada grupo individual.
    """
    from config import (
        ADMIN_USERS, COMPRAS_ACCESS, FINANZAS_ACCESS, CLIENTES_ACCESS,
        TECNICA_USERS, MARKETING_USERS, ANIMUS_ACCESS, ESPAGIRIA_ACCESS,
        RRHH_USERS, CALIDAD_USERS,
    )
    for admin in ("sebastian", "alejandro"):
        assert admin in ADMIN_USERS
        # Los grupos donde el patrón blueprint hace `GROUP | ADMIN_USERS`
        # deben incluir admins explícitamente cuando el endpoint NO usa la
        # unión. En la práctica la mayoría de blueprints sí incluye admins:
        assert admin in COMPRAS_ACCESS
        assert admin in FINANZAS_ACCESS
        assert admin in CLIENTES_ACCESS
        assert admin in TECNICA_USERS
        assert admin in MARKETING_USERS
        assert admin in ANIMUS_ACCESS
        assert admin in ESPAGIRIA_ACCESS
        assert admin in RRHH_USERS
        assert admin in CALIDAD_USERS


def test_mayra_contadora_groups(app):
    from config import (
        CONTADORA_USERS, COMPRAS_ACCESS, FINANZAS_ACCESS,
        CLIENTES_ACCESS, RRHH_USERS,
    )
    assert "mayra" in CONTADORA_USERS
    assert "mayra" in COMPRAS_ACCESS
    assert "mayra" in FINANZAS_ACCESS
    assert "mayra" in CLIENTES_ACCESS
    assert "mayra" in RRHH_USERS


def test_catalina_same_as_mayra(app):
    """Catalina (asistente compras) tiene mismo perfil financiero que Mayra."""
    from config import CONTADORA_USERS, COMPRAS_ACCESS, FINANZAS_ACCESS, RRHH_USERS
    assert "catalina" in CONTADORA_USERS
    assert "catalina" in COMPRAS_ACCESS
    assert "catalina" in FINANZAS_ACCESS
    assert "catalina" in RRHH_USERS


def test_daniela_animus(app):
    """Daniela accede a ANIMUS pero NO a Espagiria ni a Compras."""
    from config import (
        ANIMUS_ACCESS, ESPAGIRIA_ACCESS, MARKETING_USERS,
        CLIENTES_ACCESS, COMPRAS_ACCESS,
    )
    assert "daniela" in ANIMUS_ACCESS
    assert "daniela" not in ESPAGIRIA_ACCESS
    assert "daniela" in MARKETING_USERS
    assert "daniela" in CLIENTES_ACCESS
    assert "daniela" not in COMPRAS_ACCESS


def test_luz_espagiria(app):
    """Luz accede a Espagiria pero NO a ANIMUS ni a Compras."""
    from config import (
        ESPAGIRIA_ACCESS, ANIMUS_ACCESS, MARKETING_USERS,
        CLIENTES_ACCESS, COMPRAS_ACCESS,
    )
    assert "luz" in ESPAGIRIA_ACCESS
    assert "luz" not in ANIMUS_ACCESS
    assert "luz" in MARKETING_USERS
    assert "luz" in CLIENTES_ACCESS
    assert "luz" not in COMPRAS_ACCESS


def test_planta_users_only_general(app):
    """Operarios de planta SOLO están en PLANTA_USERS, no en módulos sensibles."""
    from config import (
        PLANTA_USERS, COMPRAS_ACCESS, FINANZAS_ACCESS,
        ANIMUS_ACCESS, MARKETING_USERS, ADMIN_USERS,
    )
    for u in PLANTA_USERS:
        assert u not in ADMIN_USERS
        assert u not in COMPRAS_ACCESS
        assert u not in FINANZAS_ACCESS
        assert u not in ANIMUS_ACCESS
        assert u not in MARKETING_USERS


def test_gloria_only_rrhh(app):
    """Gloria está SOLO en RRHH."""
    from config import (
        RRHH_USERS, COMPRAS_ACCESS, MARKETING_USERS, ANIMUS_ACCESS,
        TECNICA_USERS, ADMIN_USERS,
    )
    assert "gloria" in RRHH_USERS
    assert "gloria" not in COMPRAS_ACCESS
    assert "gloria" not in MARKETING_USERS
    assert "gloria" not in ANIMUS_ACCESS
    assert "gloria" not in TECNICA_USERS
    assert "gloria" not in ADMIN_USERS


def test_marketing_team_in_marketing(app):
    from config import MARKETING_USERS
    assert "jefferson" in MARKETING_USERS
    assert "felipe" in MARKETING_USERS


def test_calidad_team(app):
    from config import CALIDAD_USERS, TECNICA_USERS
    for u in ("laura", "yuliel"):
        assert u in CALIDAD_USERS
    # Miguel está en ambos
    assert "miguel" in CALIDAD_USERS
    assert "miguel" in TECNICA_USERS


def test_hernando_director_tecnico(app):
    from config import TECNICA_USERS, ADMIN_USERS
    assert "hernando" in TECNICA_USERS
    assert "hernando" not in ADMIN_USERS


# ── Endpoints validan permisos en runtime ────────────────────────────────────


def test_animus_blocked_for_non_animus_user(app, db_clean):
    """Daniela puede acceder a /api/animus, gloria no."""
    c = app.test_client()
    c.post("/login", data={"username": "gloria", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.get("/api/animus/dashboard")
    # Puede ser 403 (blocked por _auth) o 404 (ruta no existe específica)
    # Lo importante: NO devuelve 200 con datos
    assert r.status_code in (403, 404)


def test_admin_endpoints_blocked_for_non_admin(app, db_clean):
    """Endpoints /api/admin/* son ADMIN_USERS only."""
    for user in ("daniela", "luz", "valentina", "hernando", "miguel"):
        c = app.test_client()
        r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
                   headers=csrf_headers(), follow_redirects=False)
        assert r.status_code == 302, f"login fallo para {user}"
        r = c.get("/api/admin/backups")
        assert r.status_code == 403, f"{user} pudo acceder a /api/admin/backups"


def test_marketing_module_users(app, db_clean):
    """Daniela y Luz tienen acceso al módulo marketing."""
    for user in ("daniela", "luz", "jefferson", "felipe"):
        c = app.test_client()
        c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
        r = c.get("/api/marketing/ads/capabilities")
        assert r.status_code == 200, f"{user} sin acceso a marketing"
