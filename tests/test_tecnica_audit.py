"""Tests de audit_log en módulo Técnica.

Verifica que TODAS las mutaciones regulatorias (fórmulas, fichas, registros
INVIMA, SGDs) generan entradas en audit_log con la acción correcta.
INVIMA Resolución 2214/2021 exige trazabilidad de cambios en documentación
regulatoria.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="hernando"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login fallo para {user}: {r.status_code}"
    return c


def _last_audit(accion=None, registro_id=None):
    """Devuelve la última entrada de audit_log con filtros opcionales."""
    conn = sqlite3.connect(os.environ["DB_PATH"])
    where = ['1=1']
    params = []
    if accion:
        where.append('accion = ?'); params.append(accion)
    if registro_id is not None:
        where.append('registro_id = ?'); params.append(str(registro_id))
    sql = f"""SELECT usuario, accion, tabla, registro_id, detalle
              FROM audit_log WHERE {' AND '.join(where)}
              ORDER BY id DESC LIMIT 1"""
    row = conn.execute(sql, params).fetchone()
    conn.close()
    return row


# ─── Fórmulas ────────────────────────────────────────────────────────

def test_formula_crear_audita(app, db_clean):
    c = _login(app, "hernando")
    r = c.post("/api/tecnica/formulas",
               json={"codigo": "FRM-AUDIT-T1", "nombre": "Fórmula audit test",
                     "tipo": "COSMETICO"},
               headers=csrf_headers())
    assert r.status_code == 200
    fid = r.get_json()["id"]
    audit = _last_audit(accion="CREAR_FORMULA", registro_id=fid)
    assert audit is not None, "audit_log CREAR_FORMULA no registrado"
    assert audit[0] == "hernando"
    assert audit[2] == "formulas_maestras"
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM formulas_maestras WHERE id=?", (fid,))
    conn.commit(); conn.close()


def test_formula_modificar_audita(app, db_clean):
    c = _login(app, "hernando")
    r = c.post("/api/tecnica/formulas",
               json={"codigo": "FRM-MOD-T1", "nombre": "Original"},
               headers=csrf_headers())
    fid = r.get_json()["id"]
    r = c.patch(f"/api/tecnica/formulas/{fid}",
                json={"nombre": "Modificado", "motivo_cambio": "Test audit"},
                headers=csrf_headers())
    assert r.status_code == 200
    audit = _last_audit(accion="MODIFICAR_FORMULA", registro_id=fid)
    assert audit is not None
    assert "MODIFICAR_FORMULA" == audit[1]
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM formulas_maestras WHERE id=?", (fid,))
    conn.commit(); conn.close()


def test_formula_eliminar_audita(app, db_clean):
    c = _login(app, "sebastian")  # admin
    r = c.post("/api/tecnica/formulas",
               json={"codigo": "FRM-DEL-T1", "nombre": "Para eliminar"},
               headers=csrf_headers())
    fid = r.get_json()["id"]
    r = c.delete(f"/api/tecnica/formulas/{fid}", headers=csrf_headers())
    assert r.status_code == 200
    audit = _last_audit(accion="ELIMINAR_FORMULA", registro_id=fid)
    assert audit is not None
    assert audit[0] == "sebastian"


# ─── Registros INVIMA ────────────────────────────────────────────────

def test_invima_crear_audita(app, db_clean):
    c = _login(app, "hernando")
    r = c.post("/api/tecnica/invima",
               json={"producto": "Test producto", "num_registro": "NSO-123-T",
                     "tipo_tramite": "Notificacion Sanitaria"},
               headers=csrf_headers())
    assert r.status_code == 200
    rid = r.get_json()["id"]
    audit = _last_audit(accion="CREAR_REGISTRO_INVIMA", registro_id=rid)
    assert audit is not None, "audit_log CREAR_REGISTRO_INVIMA no registrado"
    assert "Test producto" in (audit[4] or "")
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM registros_invima WHERE id=?", (rid,))
    conn.commit(); conn.close()


def test_invima_modificar_audita(app, db_clean):
    c = _login(app, "hernando")
    r = c.post("/api/tecnica/invima",
               json={"producto": "P-mod", "num_registro": "NSO-MOD-T",
                     "estado": "Vigente"},
               headers=csrf_headers())
    rid = r.get_json()["id"]
    r = c.patch(f"/api/tecnica/invima/{rid}",
                json={"estado": "En_Tramite"},
                headers=csrf_headers())
    assert r.status_code == 200
    audit = _last_audit(accion="MODIFICAR_REGISTRO_INVIMA", registro_id=rid)
    assert audit is not None
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM registros_invima WHERE id=?", (rid,))
    conn.commit(); conn.close()


# ─── Fichas técnicas ─────────────────────────────────────────────────

def test_ficha_crear_audita(app, db_clean):
    c = _login(app, "hernando")
    r = c.post("/api/tecnica/fichas",
               json={"codigo": "FT-AUDIT-T1", "nombre": "Ficha test"},
               headers=csrf_headers())
    assert r.status_code == 200
    fid = r.get_json()["id"]
    audit = _last_audit(accion="CREAR_FICHA", registro_id=fid)
    assert audit is not None, "audit_log CREAR_FICHA no registrado"
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM fichas_tecnicas WHERE id=?", (fid,))
    conn.commit(); conn.close()


# ─── SGD documentos ──────────────────────────────────────────────────

def test_sgd_crear_audita(app, db_clean):
    c = _login(app, "hernando")
    r = c.post("/api/tecnica/documentos",
               json={"tipo": "SOP", "codigo": "SOP-AUDIT-T1",
                     "nombre": "SOP test audit"},
               headers=csrf_headers())
    assert r.status_code == 200
    did = r.get_json()["id"]
    audit = _last_audit(accion="CREAR_SGD", registro_id=did)
    assert audit is not None, "audit_log CREAR_SGD no registrado"
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM documentos_sgd WHERE id=?", (did,))
    conn.commit(); conn.close()


def test_sgd_marcar_revisado_audita(app, db_clean):
    c = _login(app, "hernando")
    r = c.post("/api/tecnica/documentos",
               json={"tipo": "SOP", "codigo": "SOP-REV-T1", "nombre": "Revisar"},
               headers=csrf_headers())
    did = r.get_json()["id"]
    r = c.post(f"/api/tecnica/documentos/{did}/marcar-revisado",
               headers=csrf_headers())
    assert r.status_code == 200
    audit = _last_audit(accion="REVISAR_SGD", registro_id=did)
    assert audit is not None
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM documentos_sgd WHERE id=?", (did,))
    conn.commit(); conn.close()


# ─── RBAC ────────────────────────────────────────────────────────────

def test_tecnica_endpoint_rechaza_no_tecnica(app, db_clean):
    """Usuario sin TECNICA_USERS ni ADMIN_USERS recibe 401."""
    c = _login(app, "luis")  # luis no es Técnica ni Admin
    r = c.post("/api/tecnica/formulas",
               json={"codigo": "FRM-X", "nombre": "X"},
               headers=csrf_headers())
    assert r.status_code == 401


def test_eliminar_formula_solo_admin(app, db_clean):
    """Hernando es Técnica pero NO admin · DELETE devuelve 403."""
    c = _login(app, "hernando")
    r = c.post("/api/tecnica/formulas",
               json={"codigo": "FRM-NOADM-T", "nombre": "Test"},
               headers=csrf_headers())
    fid = r.get_json()["id"]
    r = c.delete(f"/api/tecnica/formulas/{fid}", headers=csrf_headers())
    assert r.status_code == 403
    # cleanup
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM formulas_maestras WHERE id=?", (fid,))
    conn.commit(); conn.close()
