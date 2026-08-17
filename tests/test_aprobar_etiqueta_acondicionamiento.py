# -*- coding: utf-8 -*-
"""La aprobación de la etiqueta se puede dar DESDE el legajo de acondicionamiento.

En MyBatch la acción "Aprobar Etiqueta" vive en la orden de acondicionamiento, que es donde se
etiqueta. En EOS el endpoint existe para las tres fases desde junio, pero el único lugar desde
donde se podía llegar era el modal del dashboard: en la pantalla del producto terminado la
aprobación era inalcanzable (M121 · el mismo hueco que tenía el visto bueno del DT).

⚠ Lo que este test protege de verdad no es el botón: es que el botón use el contrato CORRECTO.
`firmar-rapido` firma SIEMPRE sobre `ebr_ejecuciones`, y el aprobador valida la firma contra
`ebr_artes_codificacion` -- con la firma rápida el botón se ve bien y la aprobación lo rechaza,
que es la peor forma de negar un permiso (M219/M166).
"""
import pytest

H = {"Content-Type": "application/json", "Origin": "http://localhost"}


def _login(client, usuario):
    r = client.post("/login", data={"username": usuario, "password": "TestPass123"},
                    headers={"Origin": "http://localhost"}, follow_redirects=False)
    assert r.status_code == 302, "no entro %s" % usuario
    return client


def _ebr_acond(app):
    """El legajo de ACONDICIONAMIENTO del demo, en un estado editable.

    ⚠ No se siembra la fila a mano: `ebr_ejecuciones` exige MBR, versión y fecha de inicio, y
    una fila inventada no representa lo que la pantalla recibe de verdad (M153).
    """
    import database
    from flask import session
    with app.test_request_context("/", method="POST", json={}):
        session["compras_user"] = "sebastian"
        from blueprints.brd import crear_planta_demo
        j = crear_planta_demo().get_json()
    eid = j.get("acondicionamiento_ebr")
    assert eid, "el demo no armó el legajo de acondicionamiento: %s" % j
    with app.app_context():
        c = database.get_db()
        c.execute("DELETE FROM ebr_artes_codificacion WHERE ebr_id=?", (eid,))
        c.execute("UPDATE ebr_ejecuciones SET estado='en_proceso' WHERE id=?", (eid,))
        c.execute("INSERT INTO app_settings (clave, valor) VALUES ('brd_visible','1') "
                  "ON CONFLICT (clave) DO UPDATE SET valor=excluded.valor")
        c.commit()
    return eid


def test_la_pantalla_ofrece_aprobar_la_etiqueta(client, app):
    """El bloque tiene que estar EN la pantalla del producto terminado, no sólo en la API."""
    eid = _ebr_acond(app)
    html = _login(client, "sebastian").get(
        "/planta/legajo-acondicionamiento/%d" % eid).get_data(as_text=True)

    assert "en validación" not in html, "el candado de Part 11 tapó la pantalla"
    assert "Artes y Codificacion" in html, "la tarjeta de artes no está en la pantalla"
    for fn in ("function registrarArte", "function guardarArte", "async function aprobarArte"):
        assert fn in html, "falta %s · el botón llamaría a algo que no existe (M166)" % fn
    assert 'id="arte-ov"' in html and 'id="arte-desc"' in html, "falta el formulario"

    # el contrato: la firma apunta al registro del ARTE, no al legajo
    assert "ebr_artes_codificacion" in html and "/api/sign/challenge" in html
    i = html.find("async function aprobarArte")
    # ⚠ sin quitar los comentarios el guard se encuentra a SÍ MISMO: el comentario de arriba
    #   explica justamente por qué no se usa `firmar-rapido` (M154 · pasó al escribir este test)
    import re as _re
    cuerpo = _re.sub(r"//[^\n]*", "", html[i:i + 2600])
    assert "firmar-rapido" not in cuerpo, (
        "aprobarArte usa la firma RAPIDA · esa firma va sobre ebr_ejecuciones y el aprobador "
        "la rechaza: el boton quedaria mudo (M219)")


def test_registrar_y_aprobar_la_etiqueta_de_punta_a_punta(client, app):
    """Se recorre por los endpoints REALES: registrar, firmar y aprobar."""
    eid = _ebr_acond(app)
    cli = _login(client, "sebastian")

    r = cli.post("/api/brd/ebr/%d/artes" % eid,
                 json={"descripcion": "Etiqueta frasco 30 mL", "codigo_lote": "ZZ-ARTE",
                       "codigo_vencimiento": "2028-01"}, headers=H)
    assert r.status_code in (200, 201), r.get_json()
    arte_id = (r.get_json() or {}).get("id")
    assert arte_id

    lista = cli.get("/api/brd/ebr/%d/artes" % eid).get_json() or {}
    mia = [x for x in (lista.get("items") or []) if x["id"] == arte_id]
    assert mia and not (mia[0].get("aprobado_por") or "").strip(), "nace SIN aprobar"

    # ── la firma rápida NO sirve para esto, y el test lo fija ──────────────────
    rf = cli.post("/api/brd/ebr/%d/firmar-rapido" % eid, json={"meaning": "aprueba"}, headers=H)
    if rf.status_code == 200 and (rf.get_json() or {}).get("signature_id"):
        mala = cli.post("/api/brd/ebr/%d/artes/%d/aprobar" % (eid, arte_id),
                        json={"signature_id": rf.get_json()["signature_id"]}, headers=H)
        assert mala.status_code != 200, (
            "la firma rapida (sobre ebr_ejecuciones) NO puede aprobar un arte · si pasa, la "
            "firma dejo de estar atada a su registro")

    # ── el contrato correcto: challenge + sign sobre el registro del arte ──────
    rc = cli.post("/api/sign/challenge", json={"password": "TestPass123", "totp_token": ""},
                  headers=H)
    assert rc.status_code == 200, rc.get_json()
    tok = (rc.get_json() or {}).get("token")

    rs = cli.post("/api/sign", json={"record_table": "ebr_artes_codificacion",
                                     "record_id": str(arte_id), "meaning": "aprueba",
                                     "challenge_token": tok}, headers=H)
    assert rs.status_code in (200, 201), rs.get_json()
    sig = (rs.get_json() or {}).get("signature_id")

    ok = cli.post("/api/brd/ebr/%d/artes/%d/aprobar" % (eid, arte_id),
                  json={"signature_id": sig}, headers=H)
    assert ok.status_code == 200, ok.get_json()

    lista2 = cli.get("/api/brd/ebr/%d/artes" % eid).get_json() or {}
    fila = [x for x in (lista2.get("items") or []) if x["id"] == arte_id][0]
    assert (fila.get("aprobado_por") or "").strip() == "sebastian"
    assert fila.get("aprobado_at_utc"), "quedó aprobada sin fecha · no sirve como registro GMP"

    # no se re-aprueba
    otra = cli.post("/api/brd/ebr/%d/artes/%d/aprobar" % (eid, arte_id),
                    json={"signature_id": sig}, headers=H)
    assert otra.status_code == 409, "una etiqueta aprobada se volvió a aprobar"
