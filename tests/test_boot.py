"""Test de boot — Sebastian (30-abr-2026): "smoke test de boot".

Si una migration falla silenciosamente o un blueprint no se registra,
te enteras hasta que un usuario hace login. Este test arranca la app
y verifica los puntos críticos:

1. App importa sin errores
2. Todos los blueprints están registrados
3. Migraciones aplicadas correctamente (schema_migrations completa)
4. /healthz responde 200 con DB+WAL OK
5. /api/health responde con structure válida
6. Las tablas críticas existen
"""
import os
import sqlite3
import pytest


def test_app_se_importa_sin_errores(app):
    """La fixture 'app' del conftest ya importó la app — si llega aquí, OK."""
    assert app is not None
    assert app.name == "index"


def test_blueprints_registrados(app):
    """Verifica que TODOS los blueprints declarados están registrados.

    Regresion guard: si alguien agrega blueprint nuevo y olvida registrar,
    este test lo pilla.
    """
    expected_blueprints = {
        "core", "hub", "inventario", "compras", "clientes", "gerencia",
        "financiero", "maquila", "despachos", "rrhh", "calidad", "tecnica",
        "marketing", "animus", "espagiria", "comunicacion", "contabilidad",
        "programacion", "admin", "chat", "bienestar", "mfa",
    }
    registered = set(app.blueprints.keys())
    missing = expected_blueprints - registered
    extra = registered - expected_blueprints
    assert not missing, f"Blueprints declarados pero no registrados: {missing}"
    # No fail por extra — alguien puede agregar uno nuevo legítimamente,
    # pero sí avisa para revisar el set expected.
    if extra:
        print(f"WARN: blueprints registrados no en expected: {extra}")


def test_migrations_aplicadas_completas(app):
    """schema_migrations debe tener registradas TODAS las migraciones del MIGRATIONS list.

    Si falla, significa que una migration no corrió (RuntimeError silenciado
    o init_db no ejecutó run_migrations).
    """
    db_path = os.environ["DB_PATH"]
    conn = sqlite3.connect(db_path)
    try:
        # Versions registradas en la DB
        applied = {row[0] for row in conn.execute(
            "SELECT version FROM schema_migrations"
        )}
    finally:
        conn.close()

    # Versions declaradas en código
    import sys
    api_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "api",
    )
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)
    from database import MIGRATIONS
    declared = {version for version, _, _ in MIGRATIONS}

    missing_in_db = declared - applied
    assert not missing_in_db, (
        f"Migrations declaradas pero no aplicadas: {sorted(missing_in_db)}. "
        f"Probable causa: una migration falló y RuntimeError no se propagó."
    )


def test_healthz_endpoint_publico(app):
    """/healthz debe responder 200 sin auth (uptime monitor)."""
    client = app.test_client()
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.get_json()
    assert body["status"] == "ok"
    assert body["db"]["wal_mode"] is True, "WAL mode no activado — concurrencia deficiente"
    assert body["db"]["tables"] >= 50, f"Solo {body['db']['tables']} tablas — algo no migró"


def test_api_health_alias(app):
    """/api/health y /healthz comparten handler — ambos responden 200 status ok."""
    client = app.test_client()
    r1 = client.get("/api/health")
    assert r1.status_code == 200
    j1 = r1.get_json()
    assert j1["status"] == "ok"
    # Si esta primer respuesta tiene 'db', /healthz también lo tendrá
    # (mismo handler). No hacemos doble call para evitar race en SQLite WAL
    # con conexiones efímeras del test client.
    if "db" in j1:
        assert j1["db"]["wal_mode"] is True


def test_tablas_criticas_existen(app):
    """Tablas que TODA versión de la app necesita para funcionar."""
    db_path = os.environ["DB_PATH"]
    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
    finally:
        conn.close()

    critical = {
        "schema_migrations",       # tracking de migrations
        "users_passwords",         # auth self-service
        "users_mfa",               # MFA
        "movimientos",             # inventario MP
        "movimientos_mee",         # inventario MEE
        "maestro_mps",             # catálogo MPs
        "maestro_mee",             # catálogo MEEs
        "formula_headers",         # fórmulas
        "formula_items",           # ingredientes por fórmula
        "produccion_programada",   # programación planta
        "ordenes_compra",          # OCs
        "marketing_campanas",      # marketing
        "chat_threads",            # chat
        "chat_messages",
        "tareas_operativas",       # tareas RACI
        "rate_limit",              # auth rate limit
        "security_events",         # audit log
        "backup_log",              # backups
    }
    missing = critical - tables
    assert not missing, f"Tablas críticas faltantes: {sorted(missing)}"
