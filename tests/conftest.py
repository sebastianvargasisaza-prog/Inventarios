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
        # ── QUE UN TEST QUE SE OLVIDA DE CERRAR NO CUELGUE LA SUITE (26-jul) ───────────────────
        # Un test que escribe y deja la transacción abierta retiene candados; el siguiente que
        # toque esa fila espera PARA SIEMPRE. Pasó con `formula_headers`: una conexión quedó
        # `idle in transaction` 587 segundos y el gate se veía "corriendo" sin avanzar. Desde
        # afuera es indistinguible de estar trabajando: sin salida, sin CPU, sin error.
        # Con estos dos timeouts el mismo caso se vuelve un FALLO CON NOMBRE en menos de un
        # minuto, que es información. Un test que se cuelga esconde el bug; uno que falla lo
        # señala. No cambia el resultado de ningún test sano.
        try:
            with pg.cursor() as _cur:
                _cur.execute("SET idle_in_transaction_session_timeout = '45s'")
                _cur.execute("SET lock_timeout = '60s'")
                _cur.execute("ALTER DATABASE %s SET idle_in_transaction_session_timeout = '45s'"
                             % os.environ.get('PGDATABASE', 'eos_test'))
                _cur.execute("ALTER DATABASE %s SET lock_timeout = '60s'"
                             % os.environ.get('PGDATABASE', 'eos_test'))
        except Exception as _e_to:
            print('[pg] no se pudieron fijar los timeouts anti-cuelgue: %s' % str(_e_to)[:120])
        cargar_esquema(pg)
        # AUTO-SANADO DE ESQUEMA (17-jun · gate PG confiable y que ESCALA): pg_schema.sql
        # es una foto base que puede quedar atrás de las migraciones (ej. mig 262 agregó
        # sku_producto_map.volumen_ml). El SQLite de test ya corrió TODAS las migraciones,
        # así que es la referencia. Para cada tabla, agregamos a PG cualquier columna que
        # exista en SQLite y falte en PG (solo ADD, nunca DROP). Así una migración futura
        # que agregue una columna NO vuelve a romper el harness PG.
        _sync_columnas_faltantes(sqlite_path, pg)
        copiar_datos(sqlite_path, pg)


def _copiar_unicos(sq, pg, tabla):
    """Recrea en PG los índices ÚNICOS que la tabla tiene en SQLite.

    27-jul · El auto-sanado creaba las tablas ausentes con columnas y clave primaria, pero SIN los
    índices únicos. Consecuencia: cualquier `INSERT ... ON CONFLICT (a,b)` fallaba en el gate con
    "there is no unique or exclusion constraint matching the ON CONFLICT specification" — un rojo
    que NO existe en producción (allá la tabla se crea con su UNIQUE) y que además dejaba al gate
    **ciego** para los conflictos de unicidad reales, que son el mecanismo con el que este sistema
    garantiza idempotencia y evita dobles descuentos.

    Un gate que da un rojo falso y a la vez no puede ver el problema verdadero es lo peor de los
    dos mundos: enseña a ignorarlo y no protege.
    """
    import psycopg
    try:
        indices = sq.execute('PRAGMA index_list("%s")' % tabla).fetchall()
    except Exception:
        return
    for idx in indices:
        # PRAGMA index_list: (seq, name, unique, origin, partial)
        nombre, es_unico, parcial = idx[1], idx[2], (idx[4] if len(idx) > 4 else 0)
        if not es_unico or parcial:
            continue
        try:
            cols = [r[2] for r in sq.execute('PRAGMA index_info("%s")' % nombre).fetchall() if r[2]]
        except Exception:
            continue
        if not cols:
            continue
        try:
            with pg.cursor() as cur:
                cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS "%s" ON "%s" (%s)'
                            % (('ux_%s_%s' % (tabla, '_'.join(cols)))[:60], tabla,
                               ','.join('"%s"' % c for c in cols)))
        except psycopg.Error as e:
            print('[pg-autoheal] UNIQUE %s(%s) falló: %s' % (tabla, ','.join(cols), str(e)[:120]))


def _sync_columnas_faltantes(sqlite_path, pg):
    """Auto-sana el esquema PG contra el SQLite actual (drift pg_schema.sql vs migraciones):
    CREA las TABLAS ausentes en PG y agrega las COLUMNAS ausentes a las existentes, tomando el
    SQLite (que ya corrió TODAS las migraciones) como referencia. Idempotente · nunca DROP. Así
    una migración futura que agregue una tabla o columna NO vuelve a romper el gate PG."""
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
                # PRAGMA: (cid, name, type, notnull, dflt_value, pk)
                pragma = sq.execute('PRAGMA table_info("%s")' % t).fetchall()
            except Exception:
                continue
            if not pragma:
                continue
            sq_cols = {r[1]: r[2] for r in pragma}
            with pg.cursor() as cur:
                cur.execute("SELECT column_name FROM information_schema.columns "
                            "WHERE table_schema='public' AND table_name=%s", (t.lower(),))
                pg_cols = {r[0].lower() for r in cur.fetchall()}
            if not pg_cols:
                # Tabla AUSENTE en PG (migración nueva no reflejada en pg_schema.sql · ej.
                # producto_formula_alias, stock_por_entrar, ventas_diarias). La CREAMOS a partir
                # del PRAGMA de SQLite (traduciendo tipos + PK) para que el gate PG escale con las
                # migraciones sin regenerar pg_schema.sql. Corre ANTES de copiar_datos → se llenan.
                pk_cols = [r[1] for r in pragma if r[5]]  # r[5]=pk (>0 si es parte de la PK)
                col_defs = []
                for r in pragma:
                    cname, ctype, ispk = r[1], r[2], r[5]
                    # PK simple INTEGER = AUTOINCREMENT en SQLite → IDENTITY en PG (para inserts que
                    # esperan el id autogenerado). BY DEFAULT permite además insertar ids explícitos.
                    if ispk and len(pk_cols) == 1 and 'INT' in (ctype or '').upper():
                        col_defs.append('"%s" BIGINT GENERATED BY DEFAULT AS IDENTITY' % cname)
                    else:
                        col_defs.append('"%s" %s' % (cname, _pg_type(ctype)))
                if pk_cols:
                    col_defs.append('PRIMARY KEY (%s)' % ','.join('"%s"' % c for c in pk_cols))
                try:
                    with pg.cursor() as cur:
                        cur.execute('CREATE TABLE IF NOT EXISTS "%s" (%s)' % (t, ','.join(col_defs)))
                except psycopg.Error as _e_ct:
                    print('[pg-autoheal] CREATE TABLE %s falló: %s' % (t, str(_e_ct)[:160]))
                _copiar_unicos(sq, pg, t)
                continue
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
    # La BD de la suite es un archivo temporal que se tira al terminar, así que forzar un
    # fsync en cada commit (synchronous=FULL, que en producción es obligatorio porque el
    # disco de Render es un volumen de red) sólo compra lentitud. Eran miles de fsync: la
    # mitad del tiempo del gate. Producción no se entera -- lo lee sólo este flag.
    os.environ["EOS_TEST_SQLITE_RAPIDO"] = "1"
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
        # 1 y 2 · CONSTRUIR la base de tests: armar el SQLite completo (esquema + las 381
        #    migraciones + seeds) y después copiar TODO a PostgreSQL fila por fila.
        #
        #    Eso es lo que se lleva ~8 minutos de cada corrida del gate — los tests en sí son
        #    ~50 segundos. Sebastián 26-jul: *"eso harta que comas muchos créditos, además de que
        #    hará más lento el trabajo"*. Tenía razón: reconstruir todo en cada corrida fue un
        #    martillazo para tapar que la base acumulaba basura entre corridas.
        #
        #    `guardian.sh --pg` ahora guarda la base ya construida como PLANTILLA de PostgreSQL y
        #    la restaura con `CREATE DATABASE ... TEMPLATE ...`, que es una copia de archivos:
        #    segundos en vez de minutos. Cuando lo hace, pasa EOS_PG_LISTA=1 y este bloque se
        #    saltea entero. La plantilla se reconstruye sola cuando cambia el esquema (hash de
        #    database.py + pg_schema.sql + este archivo), así que no puede quedar vieja.
        if os.environ.get("EOS_PG_LISTA") == "1":
            print("    [conftest] base restaurada desde la plantilla · no se reconstruye")
        else:
            os.environ.pop("EOS_DB_BACKEND", None)
            import database as _dbmod
            _dbmod.init_db()
            _dbmod.run_seed_rrhh()
            os.environ["EOS_DB_BACKEND"] = "postgres"
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

    # ── PLANTILLA de la base de tests (SQLite) ────────────────────────────────────────────
    #
    # Importar `index` corre `init_db()`, o sea el esquema + las 400 migraciones + los seeds:
    # medido, **10,6 segundos por sesion de pytest**. Eso se paga en CADA corrida, incluidas las
    # de un solo archivo que uno hace decenas de veces al dia, y se MULTIPLICA por worker cuando
    # la suite corre en paralelo (con 8 workers son 85 de los 160 segundos).
    #
    # La base ya construida se guarda como PLANTILLA y despues se COPIA: copiar un archivo son
    # milisegundos. `init_db()` encuentra las migraciones aplicadas y sale enseguida.
    #
    # ⚠ La plantilla se llavea por el HASH de lo que la construye (`database.py` y este archivo):
    # si cambia una migracion, el hash cambia y se reconstruye sola. No hay forma de que quede
    # vieja sin que se note, que es la unica condicion para que un atajo asi sea legitimo (M105).
    _tpl = None
    if not _postgres_mode():
        try:
            import hashlib as _hl
            import shutil as _sh
            _h = _hl.sha256()
            for _f in (os.path.join(api_dir, 'database.py'), os.path.abspath(__file__)):
                with open(_f, 'rb') as _fh:
                    _h.update(_fh.read())
            _tpl = os.path.join(tempfile.gettempdir(),
                                'eos_test_tpl_' + _h.hexdigest()[:16] + '.db')
            if os.path.exists(_tpl) and os.path.getsize(_tpl) > 100000:
                _sh.copyfile(_tpl, os.environ["DB_PATH"])
        except Exception:
            _tpl = None       # sin plantilla se construye como siempre · nunca se rompe por esto

    from index import app as flask_app
    flask_app.config["TESTING"] = True

    if _tpl and not os.path.exists(_tpl):
        # Primera corrida con este esquema: se guarda la base recien construida como plantilla.
        # Se escribe a un temporal y se renombra, para que dos sesiones a la vez no dejen media
        # plantilla escrita (que seria peor que no tenerla).
        try:
            import shutil as _sh2
            _tmp = _tpl + '.' + str(os.getpid()) + '.tmp'
            _sh2.copyfile(os.environ["DB_PATH"], _tmp)
            os.replace(_tmp, _tpl)
        except Exception:
            try:
                os.remove(_tmp)
            except Exception:
                pass
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
