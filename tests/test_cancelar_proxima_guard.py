"""audit Planta 1-jun · cancelar_proxima NO debe cancelar una producción ya
iniciada/descontada sin revertir (drift de MP permanente)."""
import os, sqlite3


def _login_as(app, user):
    from .conftest import TEST_PASSWORD, csrf_headers
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _seed(db, **cols):
    db.execute("DELETE FROM produccion_programada WHERE producto='ZZCANCEL TEST'")
    key_list = ["producto", "fecha_programada", "estado"] + list(cols.keys())
    vals = ["ZZCANCEL TEST", "2026-06-10", "programado"] + list(cols.values())
    ph = ",".join(["?"] * len(key_list))
    cur = db.execute(
        f"INSERT INTO produccion_programada ({', '.join(key_list)}) VALUES ({ph})", vals)
    db.commit()
    return cur.lastrowid


def test_cancelar_proxima_bloquea_si_descontado(app, db_clean):
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    pid = _seed(db, inventario_descontado_at="2026-06-09 10:00:00")
    db.close()
    r = c.delete(f"/api/plan/proximas/{pid}")
    assert r.status_code == 409, r.data
    assert r.get_json().get("codigo") == "YA_EN_EJECUCION", r.get_json()
    # sigue NO cancelada
    db = sqlite3.connect(os.environ["DB_PATH"])
    est = db.execute("SELECT estado FROM produccion_programada WHERE id=?", (pid,)).fetchone()[0]
    db.close()
    assert est != "cancelado", est


def test_cancelar_proxima_ok_si_no_iniciada(app, db_clean):
    c = _login_as(app, "sebastian")
    db = sqlite3.connect(os.environ["DB_PATH"])
    pid = _seed(db)
    db.close()
    r = c.delete(f"/api/plan/proximas/{pid}")
    assert r.status_code == 200, r.data
    assert r.get_json().get("estado") == "cancelado"
