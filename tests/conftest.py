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


@pytest.fixture(scope="session")
def test_workspace():
    """Directorio temporal para DB y backups durante toda la sesión de tests."""
    workspace = tempfile.mkdtemp(prefix="inv_test_")
    yield workspace
    shutil.rmtree(workspace, ignore_errors=True)


@pytest.fixture(scope="session")
def app(test_workspace):
    """App Flask con env vars de test — instanciada UNA vez por sesión."""
    # Setup env vars ANTES de importar
    os.environ["DB_PATH"] = os.path.join(test_workspace, "inventario.db")
    os.environ["BACKUPS_DIR"] = os.path.join(test_workspace, "backups")
    os.environ["SECRET_KEY"] = "test-secret-key-only-for-pytest"
    os.environ["BACKUP_RETENTION_DAYS"] = "7"
    os.environ["BACKUP_INTERVAL_HOURS"] = "23"

    # Setear hash de password para todos los users (todos comparten TEST_PASSWORD)
    for u in ALL_USERS:
        os.environ[f"PASS_{u.upper()}"] = TEST_PASSWORD_HASH

    # Asegurar que api/ esté en sys.path (igual que en index.py)
    api_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "api",
    )
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)

    from index import app as flask_app
    flask_app.config["TESTING"] = True
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


@pytest.fixture
def db_clean(app):
    """Limpia tablas que algunos tests modifican (rate_limit, users_passwords).

    Aplica entre tests para no contaminarnos. La DB en sí persiste durante la
    sesión para no recrear el schema 26 veces.
    """
    import sqlite3
    yield
    try:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM rate_limit")
        conn.execute("DELETE FROM users_passwords")
        conn.execute("DELETE FROM backup_log")
        conn.execute("DELETE FROM security_events")
        conn.commit()
        conn.close()
    except Exception:
        pass


def csrf_headers():
    """Headers que pasan el Origin/Referer check para tests POST."""
    return {"Origin": "http://localhost"}
