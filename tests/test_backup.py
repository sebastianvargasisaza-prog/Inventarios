"""Tests del feature de backups."""
import gzip
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .conftest import TEST_PASSWORD, csrf_headers


def test_backup_manual_creates_file(app, db_clean):
    """do_backup() genera archivo gz válido con DB íntegra."""
    from backup import do_backup

    r = do_backup(triggered_by="test_manual")
    assert r.get("ok") is True
    assert os.path.exists(r["file_path"])
    assert r["size_bytes"] > 0

    # Descomprimir y verificar integridad
    extracted = r["file_path"] + ".extracted.db"
    with gzip.open(r["file_path"], "rb") as fin, open(extracted, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    conn = sqlite3.connect(extracted)
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    os.remove(extracted)
    assert integrity == "ok"


def test_path_traversal_blocked(app):
    """get_backup_path() rechaza filenames con .. / o caracteres raros."""
    from backup import get_backup_path

    assert get_backup_path("../etc/passwd") is None
    assert get_backup_path("/etc/passwd") is None
    assert get_backup_path("..\\windows") is None
    assert get_backup_path("foo.txt") is None
    assert get_backup_path("inventario_BAD.zip") is None


def test_path_traversal_accepts_valid(app, db_clean):
    """get_backup_path acepta filenames válidos generados por la app."""
    from backup import do_backup, get_backup_path

    r = do_backup(triggered_by="test_valid_path")
    filename = r["filename"]
    assert get_backup_path(filename) is not None


def test_rotation_removes_old_backups(app, db_clean):
    """_rotate_old_backups borra archivos > RETENTION_DAYS."""
    from backup import _rotate_old_backups, BACKUPS_DIR, list_backups, do_backup

    # Crear un backup real para tener al menos uno
    do_backup(triggered_by="test_rotation_baseline")

    # Crear archivo "viejo" simulado
    old_file = Path(BACKUPS_DIR) / "inventario_20200101_000000.db.gz"
    old_file.write_bytes(b"fake-old-backup-content")
    old_time = (datetime.utcnow() - timedelta(days=10)).timestamp()
    os.utime(old_file, (old_time, old_time))

    deleted = _rotate_old_backups()
    assert deleted >= 1
    assert not old_file.exists()


def test_lock_prevents_concurrent_backup(app, db_clean):
    """Si otro worker está 'running', do_backup retorna skipped=True."""
    from backup import do_backup

    # Simular otro worker activo: insertar slot 'running' reciente
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute(
        "INSERT INTO backup_log (status, started_at) VALUES ('running', datetime('now', 'utc'))"
    )
    conn.commit()
    conn.close()

    r = do_backup(triggered_by="test_should_skip")
    assert r.get("skipped") is True


def test_should_run_backup_initial(app, db_clean):
    """should_run_backup retorna True si nunca se hizo uno."""
    from backup import should_run_backup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        assert should_run_backup(conn) is True
    finally:
        conn.close()


def test_should_run_backup_recent_says_no(app, db_clean):
    """Si un backup OK fue hace <23h, should_run_backup retorna False."""
    from backup import should_run_backup, do_backup
    do_backup(triggered_by="test_recent")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    try:
        assert should_run_backup(conn) is False
    finally:
        conn.close()


# ── Endpoints HTTP ────────────────────────────────────────────────────────────


def test_backup_list_requires_auth(client, db_clean):
    r = client.get("/api/admin/backups")
    assert r.status_code == 401


def test_backup_list_requires_admin(app, db_clean):
    """User no-admin recibe 403."""
    c = app.test_client()
    c.post("/login", data={"username": "valentina", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.get("/api/admin/backups")
    assert r.status_code == 403


def test_backup_list_admin_ok(admin_client, db_clean):
    r = admin_client.get("/api/admin/backups")
    assert r.status_code == 200
    data = r.get_json()
    assert "backups" in data
    assert "recent_runs" in data
    assert isinstance(data["backups"], list)


def test_backup_now_admin(admin_client, db_clean):
    r = admin_client.post("/api/admin/backup-now", headers=csrf_headers())
    assert r.status_code == 200
    assert r.get_json().get("ok") is True


def test_backup_now_non_admin_blocked(app, db_clean):
    c = app.test_client()
    c.post("/login", data={"username": "gloria", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.post("/api/admin/backup-now", headers=csrf_headers())
    assert r.status_code == 403


def test_admin_panel_html(admin_client, db_clean):
    r = admin_client.get("/admin")
    assert r.status_code == 200
    assert b"Backups de Base de Datos" in r.data


def test_admin_panel_blocked_for_non_admin(app, db_clean):
    c = app.test_client()
    c.post("/login", data={"username": "luis", "password": TEST_PASSWORD},
           headers=csrf_headers(), follow_redirects=False)
    r = c.get("/admin")
    assert r.status_code == 403


def test_backup_download_invalid_filename(admin_client, db_clean):
    r = admin_client.get("/api/admin/backup/../etc/passwd")
    # Werkzeug normaliza .. en URL — pero get_backup_path también valida
    assert r.status_code in (404, 400)
