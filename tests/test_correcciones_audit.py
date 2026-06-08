"""Panel 'Correcciones / Auditoría' del legajo EBR · Audit Trail Part 11.

Regresión que clava el bug del 8-jun: el parseo de antes/despues usaba
`json.loads` cuando el módulo está importado como `_json` en brd.py · el
NameError lo tragaba un `except Exception` y el diff campo/anterior/nuevo
salía SIEMPRE vacío (anti-patrón M4 · tragar except). Si alguien revierte
`_json.loads` a `json.loads`, `campos` queda vacío y este test falla.
"""


def _crear_ebr(app, lote="LOTE-CORR-1"):
    """MBR + EBR mínimos en estado 'iniciado'. Devuelve ebr_id."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.execute(
            """INSERT INTO mbr_templates (producto_nombre, version, estado,
                 lote_size_g, creado_por) VALUES (?, 1, 'aprobado',
                 1000, 'sebastian')""", (f"PROD-CORR-{lote}",))
        mbr_id = cur.lastrowid
        cur = conn.execute(
            """INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote,
                 estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, fase)
               VALUES (?,1,?,'iniciado','sebastian','2026-06-06 10:00:00',1000,'fabricacion')""",
            (mbr_id, lote))
        ebr_id = cur.lastrowid
        conn.commit()
        return ebr_id


def _escribir_correccion(app, ebr_id, antes, despues, tabla="ebr_pesajes"):
    """Escribe una corrección por el camino real (audit_helpers.audit_log)."""
    from database import get_db
    try:
        from audit_helpers import audit_log
    except ImportError:
        from api.audit_helpers import audit_log
    with app.app_context():
        conn = get_db()
        audit_log(conn, usuario="sebastian", accion="CORREGIR_PESAJE",
                  tabla=tabla, registro_id=12345, antes=antes, despues=despues)
        conn.commit()


def test_correcciones_muestra_diff_de_campos(admin_client, app):
    ebr = _crear_ebr(app, "DIFF")
    _escribir_correccion(
        app, ebr,
        antes={"ebr_id": ebr, "cantidad_g": 8},
        despues={"ebr_id": ebr, "cantidad_g": 10})

    d = admin_client.get(f"/api/brd/ebr/{ebr}/vista-completa").get_json()
    corrs = d.get("correcciones")
    assert corrs, "vista-completa debe incluir 'correcciones'"

    pesaje = [c for c in corrs if c.get("tabla") == "ebr_pesajes"]
    assert pesaje, f"debe listar la corrección por LIKE despues ebr_id={ebr}: {corrs}"

    campos = pesaje[0]["campos"]
    # El diff debe poblarse (si no, regresión _json.loads → campos vacío).
    assert any(cp["campo"] == "cantidad_g"
               and cp["anterior"] == "8" and cp["nuevo"] == "10"
               for cp in campos), f"diff vacío/incorrecto: {campos}"
    # ebr_id es la llave de correlación, NO un cambio mostrable.
    assert all(cp["campo"] != "ebr_id" for cp in campos)


def test_correcciones_no_filtra_por_ebr_ajeno(admin_client, app):
    """La corrección de un EBR no debe aparecer en el legajo de otro
    (el LIKE '"ebr_id": N,'/'"ebr_id": N}' delimita por ebr_id exacto)."""
    ebr_a = _crear_ebr(app, "A")
    ebr_b = _crear_ebr(app, "B")
    _escribir_correccion(
        app, ebr_a,
        antes={"ebr_id": ebr_a, "ph": "5.0"},
        despues={"ebr_id": ebr_a, "ph": "5.5"})

    d_b = admin_client.get(f"/api/brd/ebr/{ebr_b}/vista-completa").get_json()
    ajenas = [c for c in (d_b.get("correcciones") or [])
              if c.get("tabla") == "ebr_pesajes"]
    assert not ajenas, f"el legajo de B no debe ver correcciones de A: {ajenas}"
