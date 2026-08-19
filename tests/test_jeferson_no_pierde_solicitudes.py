# -*- coding: utf-8 -*-
"""A Jeferson se le desaparecian solicitudes de pago · 19-ago-2026.

Jeferson (Marketing): *"se me desaparecen solicitudes, no me quedan guardadas"*. Es la
SEGUNDA vez que lo reporta: el 27-may ya se habia atacado con un modal de confirmacion
prominente ("para que sepa que QUEDO GUARDADO"), o sea el sintoma. La causa estaba en
el token de idempotencia que se agrego despues, el 7-jul.

El token vive en `window._pagoInfTok`, se genera una vez y **solo se limpia cuando el
pago sale bien**. El modal de pago resetea todos sus campos al abrirse -valor, concepto,
entregable, link- y nunca el token. Entonces:

  1. Jeferson pide el pago de la creadora A · el servidor lo crea y hace commit
  2. la respuesta se pierde (red, pestaña dormida, lo que sea) · el cliente no ve `ok`
     -> el token NO se limpia
  3. Jeferson abre la creadora B y pide su pago · viaja EL MISMO token
  4. el backend lo reclama con un UNIQUE global -> 409 "ya fue registrada (doble envio)"
     -> la solicitud de B **no se crea nunca**

Y el mensaje habla de un doble envio que, para una creadora que nunca se toco, no
significa nada. Desde su silla: la solicitud desaparecio.

Dos creadoras distintas son dos pagos distintos, sin importar que token mande el
cliente. La deduplicacion se ancla al ACTO (token + creador), no al token suelto
-- es la misma leccion del stock vendible: la idempotencia se ancla al hecho que
identifica, o termina saltandose algo legitimo EN SILENCIO, que es peor que
duplicarlo porque no se ve (M240/M134).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

TOK = 'ZJEF-TOKEN-COMPARTIDO'


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)


def _cli(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _limpiar():
    cn = _cn()
    try:
        cn.execute("DELETE FROM oc_recepcion_dedup WHERE recepcion_id LIKE 'ZJEF-%'")
        cn.execute("DELETE FROM pagos_influencers WHERE influencer_nombre LIKE 'ZJEF %'")
        cn.execute("DELETE FROM marketing_influencers WHERE nombre LIKE 'ZJEF %'")
        cn.commit()
    finally:
        cn.close()


def _creadora(nombre):
    cn = _cn()
    try:
        cn.execute("INSERT INTO marketing_influencers (nombre, banco, cuenta_bancaria, "
                   "tipo_cuenta, cedula_nit, estado, tarifa) VALUES (?,?,?,?,?,?,?)",
                   (nombre, 'Nequi', '3001234567', 'Nequi', '123456', 'Activo', 400000))
        cn.commit()
        return cn.execute("SELECT id FROM marketing_influencers WHERE nombre=?",
                          (nombre,)).fetchone()[0]
    finally:
        cn.close()


def _pedir(cli, iid, tok, concepto='Reel de agosto'):
    return cli.post('/api/marketing/influencers/%d/solicitar-pago' % iid,
                    json={'valor': 400000, 'concepto': concepto,
                          'fecha_publicacion': '2026-08-10',
                          'fecha_contenido': '2026-08-10',
                          'entregable': 'Reel de producto',
                          'solicitud_id': tok},
                    headers=csrf_headers())


def test_dos_creadoras_distintas_no_se_bloquean_entre_si(app, db_clean):
    """El caso de Jeferson: un token que quedo colgado no puede matar el pago de OTRA."""
    _limpiar()
    a = _creadora('ZJEF CREADORA A')
    b = _creadora('ZJEF CREADORA B')
    try:
        cli = _cli(app)
        r1 = _pedir(cli, a, TOK)
        assert r1.status_code == 200, ("la primera solicitud fallo", r1.status_code,
                                       r1.get_json())
        r2 = _pedir(cli, b, TOK)          # mismo token · otra creadora
        assert r2.status_code == 200, (
            "la solicitud de OTRA creadora se rechazo por un token que quedo colgado "
            "de un pago anterior · desde Marketing la solicitud simplemente desaparece",
            r2.status_code, r2.get_json())

        cn = _cn()
        try:
            n = cn.execute("SELECT COUNT(*) FROM pagos_influencers "
                           "WHERE influencer_nombre LIKE 'ZJEF %'").fetchone()[0]
        finally:
            cn.close()
        assert n == 2, ("deberian existir las dos solicitudes, una por creadora", n)
    finally:
        _limpiar()


def test_el_doble_click_en_la_MISMA_creadora_sigue_bloqueado(app, db_clean):
    """El borde que impide que el arreglo abra la puerta al doble pago (M96)."""
    _limpiar()
    a = _creadora('ZJEF CREADORA A')
    try:
        cli = _cli(app)
        assert _pedir(cli, a, TOK).status_code == 200
        r2 = _pedir(cli, a, TOK)
        assert r2.status_code == 409, (
            "un doble envio a la MISMA creadora con el mismo token tiene que seguir "
            "rechazandose · si no, es doble egreso", r2.status_code, r2.get_json())

        cn = _cn()
        try:
            n = cn.execute("SELECT COUNT(*) FROM pagos_influencers "
                           "WHERE influencer_nombre='ZJEF CREADORA A'").fetchone()[0]
        finally:
            cn.close()
        assert n == 1, ("el doble click creo dos pagos", n)
    finally:
        _limpiar()


def test_el_modal_arranca_con_token_LIMPIO(app, db_clean):
    """La otra mitad: el token identifica UN pago, asi que nace al abrir el modal.

    Sin esto, un token que quedo colgado bloquea el siguiente pago de la MISMA
    creadora -- que es legitimo cuando publico dos veces en el mes.
    """
    import io
    import re
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "templates_py", "marketing_html.py")
    src = io.open(ruta, encoding="utf-8").read()
    m = re.search(r"function solicitarPagoInf\s*\([^)]*\)\s*\{(.*?)\n\}", src, re.S)
    assert m, "no encontre la funcion que abre el modal de pago"
    cuerpo = "\n".join(l for l in m.group(1).splitlines()
                       if not l.strip().startswith("//"))
    assert re.search(r"_pagoInfTok\s*=\s*(null|'')", cuerpo), (
        "el modal de pago no limpia `_pagoInfTok` al abrirse · un token colgado de un "
        "envio anterior viaja con el pago siguiente y el backend lo rechaza como "
        "duplicado")


# ── La segunda mitad: borrar un creador duplicado se llevaba sus solicitudes ──

def test_borrar_un_creador_NO_puede_destruir_su_solicitud_pendiente(app, db_clean):
    """El boton de borrar duplicados -que pidio Jeferson- destruia su propio trabajo.

    El guard contaba unicamente pagos en estado `Pagada`. Un creador con solicitudes
    PENDIENTES contaba como "sin pagos", asi que se dejaba borrar, y el DELETE se
    llevaba `pagos_influencers ... estado != 'Pagada'` y desvinculaba la SOL. La orden
    de compra quedaba huerfana y el audit_log registraba los conteos de lo PAGADO
    (que eran 0), o sea ni rastro de lo destruido.

    Una solicitud pendiente es plata comprometida y trabajo en curso: no puede
    desaparecer como efecto colateral de limpiar un duplicado.
    """
    _limpiar()
    a = _creadora('ZJEF CREADORA A')
    try:
        cli = _cli(app)
        assert _pedir(cli, a, TOK).status_code == 200

        r = cli.delete('/api/marketing/influencers/%d' % a, headers=csrf_headers())
        assert r.status_code == 409, (
            "se dejo borrar un creador que tiene una solicitud de pago pendiente · "
            "esa solicitud se destruye en silencio", r.status_code, r.get_json())

        cn = _cn()
        try:
            n = cn.execute("SELECT COUNT(*) FROM pagos_influencers "
                           "WHERE influencer_nombre='ZJEF CREADORA A'").fetchone()[0]
        finally:
            cn.close()
        assert n == 1, ("la solicitud pendiente desaparecio al intentar borrar el creador", n)

        j = r.get_json() or {}
        assert 'pendiente' in (j.get('error') or '').lower(), (
            "el mensaje no dice que lo que frena el borrado es una solicitud pendiente", j)
    finally:
        _limpiar()


def test_un_creador_SIN_nada_pendiente_se_sigue_borrando(app, db_clean):
    """El borde: el arreglo no puede trabar la limpieza de duplicados (M96).

    Jeferson pidio ese boton justamente porque hay creadores repetidos.
    """
    _limpiar()
    a = _creadora('ZJEF CREADORA A')
    try:
        cli = _cli(app)
        r = cli.delete('/api/marketing/influencers/%d' % a, headers=csrf_headers())
        assert r.status_code == 200, (
            "un creador duplicado sin nada pendiente dejo de poder borrarse · el "
            "arreglo trabo la limpieza que Jeferson pidio", r.status_code, r.get_json())
    finally:
        _limpiar()


def test_el_reset_masivo_NO_borra_sin_confirmacion(app, db_clean):
    """La herramienta admin que limpia lo pendiente borraba de un POST.

    Es admin-only y deliberada (*"ya he pagado los que se han pagado"*), pero lo que
    barre es exactamente lo que Marketing acaba de crear. Sin un paso de confirmacion,
    una corrida pensada para limpiar lo viejo se lleva tambien lo de hoy -- y desde el
    lado de Jeferson eso se ve como que sus solicitudes desaparecieron solas.
    """
    _limpiar()
    a = _creadora('ZJEF CREADORA A')
    try:
        cli = _cli(app)
        assert _pedir(cli, a, TOK).status_code == 200

        r = cli.post('/admin/influencers-reset-pendientes', json={}, headers=csrf_headers())
        assert r.status_code == 200, (r.status_code, r.get_data(as_text=True)[:200])
        j = r.get_json() or {}
        assert j.get('dry_run') is True, (
            "el reset masivo borro sin pedir confirmacion", j)

        cn = _cn()
        try:
            n = cn.execute("SELECT COUNT(*) FROM pagos_influencers "
                           "WHERE influencer_nombre='ZJEF CREADORA A'").fetchone()[0]
        finally:
            cn.close()
        assert n == 1, ("la solicitud pendiente se borro en la vista previa", n)
        assert (j.get('a_eliminar') or {}).get('pagos_influencers', 0) >= 1, (
            "la vista previa no dice cuantas solicitudes se llevaria", j)
    finally:
        _limpiar()
