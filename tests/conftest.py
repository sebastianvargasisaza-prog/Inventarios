"""
Fixtures compartidos para todos los tests.

Cada test usa una DB temporal (no toca /var/data/inventario.db ni la DB
local del dev). Las env vars críticas (SECRET_KEY, PASS_*) se setean
ANTES de importar la app — config.py se evalúa en import time.

Usage:
    def test_something(client):
        r = client.get('/api/health')
        assert r.status_code == 200
"""
import os
import shutil
import sys
import tempfile

import pytest

# Hash PBKDF2 de la password "TestPass123" — usado para todos los users en tests.
# Generado con: generate_password_hash("TestPass123", method="pbkdf2:sha256:600000")
TEST_PASSWORD = "TestPass123"
TEST_PASSWORD_HASH = (
    "pbkdf2:sha256:600000$5dX2P6VF3huuK1LS$"
    "415562e3f0767e18b4b4268e1e30532e496dc773ef0134d5e664740b1181d9bb"
)

# Lista de todos los users (debe matchear COMPRAS_USERS en config.py)
ALL_USERS = [
    "sebastian", "alejandro", "mayra", "catalina", "daniela", "luz",
    "valentina", "gloria", "hernando", "miguel", "laura", "yuliel",
    "jefferson", "felipe", "luis", "smurillo", "sergio", "mayerlin",
    "camilo",
]

# Tablas TRANSACCIONALES que db_clean resetea entre tests para evitar
# contaminación cruzada en la suite completa (PG comparte la BD toda la sesión).
# SOLO transaccionales — NUNCA tablas seed (formula_headers, maestro_mps, etc.).
_TABLAS_TRANSACCIONALES = (
    'ordenes_compra_items', 'ordenes_compra',
    'solicitudes_compra_items', 'solicitudes_compra',
    'audit_zero_error_runs',
)


@pytest.fixture(scope="session")
def test_workspace():
    """Directorio temporal para DB y backups durante toda la sesión de tests."""
    workspace = tempfile.mkdtemp(prefix="inv_test_")
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


def _postgres_mode():
    return os.environ.get("EOS_DB_BACKEND", "").strip().lower() == "postgres"


def _conninfo():
    return (
        f"host={os.environ.get('PGHOST', '127.0.0.1')} "
        f"port={os.environ.get('PGPORT', '5432')} "
        f"user={os.environ.get('PGUSER', 'postgres')} "
        f"dbname={os.environ.get('PGDATABASE', 'eos_test')}"
    )


def _migrar_a_postgres(sqlite_path):
    """Carga el esquema PostgreSQL en eos_test y copia los datos del SQLite.

    Migración Fase 3-4. Usa las MISMAS funciones que el script de cutover
    (scripts/migrar_datos_a_postgres.py) · así los golden tests validan el
    código real de migración a producción.
    """
    import psycopg

    scripts_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from migrar_datos_a_postgres import cargar_esquema, copiar_datos

    with psycopg.connect(_conninfo(), autocommit=True) as pg:
        cargar_esquema(pg)
        # AUTO-SANADO DE ESQUEMA (17-jun · gate PG confiable y que ESCALA): pg_schema.sql
        # es una foto base que puede quedar atrás de las migraciones (ej. mig 262 agregó
        # sku_producto_map.volumen_ml). El SQLite de test ya corrió TODAS las migraciones,
        # así que es la referencia. Para cada tabla, agregamos a PG cualquier columna que
        # exista en SQLite y falte en PG (solo ADD, nunca DROP). Así una migración futura
        # que agregue una columna NO vuelve a romper el harness PG.
        _sync_columnas_faltantes(sqlite_path, pg)
        copiar_datos(sqlite_path, pg)


def _sync_columnas_faltantes(sqlite_path, pg):
    """ALTER TABLE ADD COLUMN en PG por cada columna presente en el SQLite actual
    y ausente en PG (drift pg_schema.sql vs migraciones). Idempotente · solo ADD."""
    import sqlite3 as _sq
    import psycopg
    def _pg_type(sqlite_type):
        t = (sqlite_type or '').upper()
        if 'INT' in t:
            return 'BIGINT'
        if 'REAL' in t or 'FLOA' in t or 'DOUB' in t:
            return 'DOUBLE PRECISION'
        if 'BLOB' in t:
            return 'BYTEA'
        return 'TEXT'
    sq = _sq.connect(sqlite_path)
    try:
        tablas = [r[0] for r in sq.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()]
        for t in tablas:
            try:
                sq_cols = {r[1]: r[2] for r in sq.execute('PRAGMA table_info("%s")' % t).fetchall()}
            except Exception:
                continue
            if not sq_cols:
                continue
            with pg.cursor() as cur:
                cur.execute("SELECT column_name FROM information_schema.columns "
                            "WHERE table_schema='public' AND table_name=%s", (t.lower(),))
                pg_cols = {r[0].lower() for r in cur.fetchall()}
            if not pg_cols:
                continue  # la tabla no existe en PG (no la creamos aquí)
            for col, sqlite_type in sq_cols.items():
                if col.lower() not in pg_cols:
                    try:
                        with pg.cursor() as cur:
                            cur.execute('ALTER TABLE "%s" ADD COLUMN IF NOT EXISTS "%s" %s'
                                        % (t, col, _pg_type(sqlite_type)))
                    except psycopg.Error:
                        pass
    finally:
        sq.close()


@pytest.fixture(scope="session")
def app(test_workspace):
    """App Flask con env vars de test — instanciada UNA vez por sesión."""
    # Setup env vars ANTES de importar
    os.environ["DB_PATH"] = os.path.join(test_workspace, "inventario.db")
    os.environ["BACKUPS_DIR"] = os.path.join(test_workspace, "backups")
    os.environ["SECRET_KEY"] = "test-secret-key-only-for-pytest"
    os.environ["BACKUP_RETENTION_DAYS"] = "7"
    os.environ["BACKUP_INTERVAL_HOURS"] = "23"
    # Desactivar los daemons de fondo (marketing-metrics, auto-plan-cron,
    # multi-cron, supervisor). El bloque que los arranca en index.py corre al
    # IMPORTAR (antes de que se setee config['TESTING']), así que debe leerse de
    # env. Sin esto, los daemons escriben a la BD durante los tests y causan
    # 'database is locked' intermitente (flaky). Audit ronda2 29-may-2026.
    os.environ["EOS_DISABLE_DAEMONS"] = "1"

    # Hash de password para todos los users · DEBE setearse antes de que
    # se importe config.py (lo evalúa en import time) · en modo Postgres
    # el bloque de abajo importa database -> config, así que va primero.
    for u in ALL_USERS:
        os.environ[f"PASS_{u.upper()}"] = TEST_PASSWORD_HASH

    # Modo PostgreSQL (migración Fase 3-4): construir un SQLite completo y
    # copiar sus datos a eos_test.
    if _postgres_mode():
        os.environ.setdefault("PGHOST", "127.0.0.1")
        os.environ.setdefault("PGPORT", "5432")
        os.environ.setdefault("PGUSER", "postgres")
        os.environ.setdefault("PGDATABASE", "eos_test")
        os.environ.setdefault(
            "PG_DUMP", r"C:\Users\sebas\pgdev\pg2\pgsql\bin\pg_dump.exe")
        api_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        # 1. Construir el SQLite (esquema + migraciones + seeds) corriendo
        #    init_db en modo SQLite (con EOS_DB_BACKEND temporalmente fuera).
        os.environ.pop("EOS_DB_BACKEND", None)
        import database as _dbmod
        _dbmod.init_db()
        _dbmod.run_seed_rrhh()
        os.environ["EOS_DB_BACKEND"] = "postgres"
        # 2. Cargar el esquema PG y copiar los datos del SQLite.
        _migrar_a_postgres(os.environ["DB_PATH"])
        # 3. El harness (_exec/_query y ~40 sitios) abre la BD con
        #    sqlite3.connect(DB_PATH) directo · se redirige al adaptador
        #    Postgres (las conexiones a :memory: y temporales quedan en
        #    SQLite real).
        import sqlite3 as _sq
        _orig_connect = _sq.connect

        def _connect_pg_shim(database, *a, **kw):
            if database == os.environ.get("DB_PATH"):
                from pg_adapter import connect as _pg_connect
                return _pg_connect()
            return _orig_connect(database, *a, **kw)

        _sq.connect = _connect_pg_shim

    # Asegurar que api/ esté en sys.path (igual que en index.py)
    api_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "api",
    )
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)

    from index import app as flask_app
    flask_app.config["TESTING"] = True
    # Batch Record VISIBLE en tests: la funcionalidad EBR/MBR/legajos se prueba con el flag
    # encendido. En prod queda OCULTO por defecto (app_settings.brd_visible ausente) hasta
    # la validación Part 11 (Sebastián 18-jun). Test específico del gate: test_brd_oculto.
    try:
        import sqlite3 as _sqi
        _cc = _sqi.connect(os.environ["DB_PATH"])
        _cc.execute("INSERT INTO app_settings (clave, valor) SELECT 'brd_visible','1' "
                    "WHERE NOT EXISTS (SELECT 1 FROM app_settings WHERE clave='brd_visible')")
        _cc.execute("UPDATE app_settings SET valor='1' WHERE clave='brd_visible'")
        _cc.commit(); _cc.close()
    except Exception:
        pass
    yield flask_app


@pytest.fixture
def client(app):
    """Cliente HTTP sin sesión iniciada."""
    return app.test_client()


@pytest.fixture
def logged_client(app, client):
    """Cliente con sesión activa de un user normal (NO admin)."""
    r = client.post(
        "/login",
        data={"username": "valentina", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    assert r.status_code == 302, f"login fallo en fixture: {r.status_code}"
    return client


@pytest.fixture
def admin_client(app):
    """Cliente con sesión de admin (sebastian)."""
    c = app.test_client()
    r = c.post(
        "/login",
        data={"username": "sebastian", "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    assert r.status_code == 302, f"login admin fallo en fixture: {r.status_code}"
    return c


@pytest.fixture(autouse=True)
def _disable_async_backup_trigger():
    """Anula trigger_backup_async durante tests.

    Hay un hook periodico (cada 50 requests) que lanza backup en thread
    daemon. Si ese thread sigue corriendo cuando termina el test, el
    _local_lock queda atorado y test_backup_now_admin falla.

    En tests dejamos que do_backup directo siga funcionando (algunos
    tests lo prueban) pero el trigger asincrono se desactiva — los
    backups async son ruido en test.
    """
    try:
        import backup as _backup_mod
        original = _backup_mod.trigger_backup_async
        _backup_mod.trigger_backup_async = lambda triggered_by="auto": None
    except Exception:
        original = None
    yield
    try:
        if original is not None:
            _backup_mod.trigger_backup_async = original
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _reset_abast_flag():
    """Sebastián 12-jul · el flag app_settings.abast_contar_pendiente (M39 · déficit cuenta pend/cuar o no) NO lo
    resetea db_clean y PERSISTE entre tests → resetear a DEFAULT (no contar) antes de cada test; los tests que
    validan el modo 'contar' lo setean explícito en su cuerpo (M66)."""
    try:
        import sqlite3 as _sqf
        _cf = _sqf.connect(os.environ["DB_PATH"], timeout=10)
        _cf.execute("DELETE FROM app_settings WHERE clave='abast_contar_pendiente'")
        _cf.commit()
        _cf.close()
    except Exception:
        pass
    yield


@pytest.fixture
def db_clean(app):
    """Limpia tablas que algunos tests modifican (rate_limit, users_passwords).

    Aplica entre tests para no contaminarnos. La DB en sí persiste durante la
    sesión para no recrear el schema 26 veces.

    Tambien libera _local_lock de backup.py: hay un hook periodico que
    lanza backup async en thread daemon; si el thread no termina antes
    del siguiente test, deja el lock adquirido y test_backup_now_admin
    falla con 'another backup running in this worker'.
    """
    import sqlite3
    yield
    try:
        from backup import _local_lock
        # Esperar hasta 1s a que termine el backup async (si lo hay)
        import time
        for _ in range(20):
            if not _local_lock.locked():
                break
            time.sleep(0.05)
        # Si aún sigue locked, forzar release (test isolation)
        try:
            while _local_lock.locked():
                _local_lock.release()
        except RuntimeError:
            pass
    except Exception:
        pass
    _tablas_volatiles = ('rate_limit', 'users_passwords', 'backup_log',
                         'security_events', 'users_mfa')
    try:
        if _postgres_mode():
            import psycopg
            conninfo = (
                f"host={os.environ.get('PGHOST', '127.0.0.1')} "
                f"port={os.environ.get('PGPORT', '5432')} "
                f"user={os.environ.get('PGUSER', 'postgres')} "
                f"dbname={os.environ.get('PGDATABASE', 'eos_test')}"
            )
            conn = psycopg.connect(conninfo, autocommit=True)
            for t in _tablas_volatiles:
                try:
                    with conn.cursor() as cur:
                        cur.execute(f"DELETE FROM {t}")
                except Exception:
                    pass
            # Reset transaccional FK-safe (anti contaminación cruzada en la suite
            # completa · PG comparte la BD toda la sesión). session_replication_role
            # =replica desactiva los triggers de FK para borrar sin importar orden.
            try:
                with conn.cursor() as cur:
                    cur.execute("SET session_replication_role = replica")
                    for t in _TABLAS_TRANSACCIONALES:
                        try:
                            cur.execute(f"DELETE FROM {t}")
                        except Exception:
                            pass
                    cur.execute("SET session_replication_role = DEFAULT")
            except Exception:
                pass
            conn.close()
        else:
            conn = sqlite3.connect(os.environ["DB_PATH"])
            for t in _tablas_volatiles:
                try:
                    conn.execute(f"DELETE FROM {t}")
                except sqlite3.OperationalError:
                    pass
            try:
                conn.execute("PRAGMA foreign_keys=OFF")
                for t in _TABLAS_TRANSACCIONALES:
                    try:
                        conn.execute(f"DELETE FROM {t}")
                    except sqlite3.OperationalError:
                        pass
                conn.execute("PRAGMA foreign_keys=ON")
            except Exception:
                pass
            conn.commit()
            conn.close()
    except Exception:
        pass


def csrf_headers():
    """Headers que pasan el Origin/Referer check para tests POST."""
    return {"Origin": "http://localhost"}
