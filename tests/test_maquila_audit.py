"""Tests CERO SESGO · maquila · audit + validate_money en mutations."""
import os
import sqlite3

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _last_audit(accion=None):
    conn = sqlite3.connect(os.environ["DB_PATH"])
    sql = "SELECT usuario, accion, tabla, registro_id, detalle FROM audit_log"
    params = []
    if accion:
        sql += " WHERE accion=?"; params.append(accion)
    sql += " ORDER BY id DESC LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


def test_crear_prospecto_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/maquila/prospectos",
               json={"empresa": "Lab Test S.A.", "contacto": "Juan",
                     "valor_estimado": 5000000, "kam_asignado": "Luz"},
               headers=csrf_headers())
    assert r.status_code == 201
    pid = r.get_json()["id"]
    audit = _last_audit(accion="CREAR_PROSPECTO_MAQUILA")
    assert audit is not None
    assert "Lab Test" in (audit[4] or "")
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM maquila_prospectos WHERE id=?", (pid,))
    conn.commit(); conn.close()


def test_crear_prospecto_valor_invalido_400(app, db_clean):
    c = _login(app, "sebastian")
    # NaN no permitido
    r = c.post("/api/maquila/prospectos",
               json={"empresa": "X", "valor_estimado": float('inf')},
               headers=csrf_headers())
    assert r.status_code == 400


def test_crear_prospecto_sin_empresa_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/maquila/prospectos",
               json={"contacto": "Sin empresa"}, headers=csrf_headers())
    assert r.status_code == 400


def test_crear_orden_maquila_audita(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/maquila/ordenes",
               json={"empresa": "Cliente Test", "producto": "Crema X",
                     "batch_size_kg": 10, "valor_total": 2500000},
               headers=csrf_headers())
    assert r.status_code == 201
    oid = r.get_json()["id"]
    audit = _last_audit(accion="CREAR_ORDEN_MAQUILA")
    assert audit is not None
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM maquila_ordenes WHERE id=?", (oid,))
    conn.commit(); conn.close()


def test_crear_orden_batch_excesivo_400(app, db_clean):
    """batch_size_kg > 10000 no es físicamente posible · debe rechazar."""
    c = _login(app, "sebastian")
    r = c.post("/api/maquila/ordenes",
               json={"empresa": "X", "producto": "Y",
                     "batch_size_kg": 50000, "valor_total": 1000},
               headers=csrf_headers())
    assert r.status_code == 400


def test_crear_orden_valor_negativo_no_admitido(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/maquila/ordenes",
               json={"empresa": "X", "producto": "Y",
                     "batch_size_kg": 10, "valor_total": -5000},
               headers=csrf_headers())
    assert r.status_code == 400


def test_crear_orden_sin_empresa_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.post("/api/maquila/ordenes",
               json={"producto": "Sin empresa"}, headers=csrf_headers())
    assert r.status_code == 400
