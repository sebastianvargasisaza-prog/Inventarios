# -*- coding: utf-8 -*-
"""Los registros del Director Tecnico decian 0 sin haber medido nada · 19-ago-2026.

Direccion Tecnica mostraba `FORMULAS VIGENTES 0`, `FICHAS TECNICAS 0`, `REG. INVIMA
VIGENTES 0`. Verificado: esos son los registros PROPIOS del DT, su pantalla tiene el
CRUD completo y las personas correctas pueden usarlo (Hernando, Miguel, Alejandro y
Sebastian: alta 200, y el KPI sube). O sea que no habia nada roto -- pero tampoco habia
nada cargado.

El problema es que las dos situaciones se veian IGUAL. "0 vigentes" se lee como *esta
todo al dia*; lo que pasa de verdad es que nadie ha cargado un solo registro, que es lo
contrario (M154/M100: un cero que nadie calculo se lee como "no hay nada que hacer").

Ahora el tablero distingue: con el registro vacio dice `Sin cargar`, y cuando hay al
menos una fila vuelve a ser un numero. Lo que no se pudo medir se declara con `None`,
nunca como cero.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _cn():
    return sqlite3.connect(os.environ["DB_PATH"], timeout=20.0)


def _cli(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, user
    return c


def _limpiar():
    cn = _cn()
    try:
        cn.execute("DELETE FROM registros_invima WHERE producto LIKE 'ZINV%'")
        cn.commit()
    finally:
        cn.close()


def test_el_tablero_dice_cuantos_hay_CARGADOS_no_solo_cuantos_vigentes(app, db_clean):
    cli = _cli(app)
    d = cli.get('/api/tecnica/dashboard').get_json() or {}
    cg = d.get('cargados')
    assert isinstance(cg, dict), (
        "el tablero no publica cuantos registros hay cargados · sin eso, 'vacio' y "
        "'cero vigentes' se ven igual", sorted(d.keys()))
    for k in ('formulas', 'fichas', 'invima', 'docs'):
        assert k in cg, ("falta el conteo de '%s'" % k, cg)


def test_al_cargar_un_registro_el_tablero_deja_de_decir_VACIO(app, db_clean):
    """La cadena completa: si esto pasa, cuando Hernando cargue los suyos se ve."""
    _limpiar()
    cli = _cli(app)
    antes = ((cli.get('/api/tecnica/dashboard').get_json() or {}).get('cargados') or {}).get('invima')
    r = cli.post('/api/tecnica/invima', json={
        'producto': 'ZINV PRODUCTO', 'num_registro': 'NSOC-ZINV',
        'tipo_tramite': 'Notificacion Sanitaria', 'fecha_expedicion': '2026-01-01',
        'fecha_vencimiento': '2027-01-01', 'estado': 'Vigente'}, headers=csrf_headers())
    try:
        assert r.status_code in (200, 201), ("no se pudo dar de alta un registro INVIMA",
                                             r.status_code, r.get_json())
        d = cli.get('/api/tecnica/dashboard').get_json() or {}
        assert int((d.get('cargados') or {}).get('invima') or 0) == int(antes or 0) + 1, (
            "el registro cargado no se refleja en el tablero", antes, d.get('cargados'))
        assert int(d.get('registros_vigentes') or 0) >= 1, (
            "el registro vigente recien cargado no cuenta como vigente", d)
    finally:
        _limpiar()


def test_el_DIRECTOR_TECNICO_puede_cargarlos(app, db_clean):
    """Una pantalla cuyo dueño no puede escribir es una capacidad que no existe (M121)."""
    problemas = {}
    for quien in ('hernando', 'miguel'):
        try:
            cli = _cli(app, quien)
        except AssertionError:
            problemas[quien] = 'no pudo entrar'
            continue
        r = cli.post('/api/tecnica/invima', json={
            'producto': 'ZINV %s' % quien, 'num_registro': 'NSOC-%s' % quien,
            'fecha_vencimiento': '2027-01-01', 'estado': 'Vigente'},
            headers=csrf_headers())
        if r.status_code not in (200, 201):
            problemas[quien] = r.status_code
    _limpiar()
    assert not problemas, (
        "las personas que tienen que cargar los registros INVIMA no pueden: %s" % problemas)


def test_la_pantalla_dice_SIN_CARGAR_en_vez_de_un_cero(app, db_clean):
    """Se mide sobre el JS SERVIDO · el backend puede tener el dato y la pantalla tirarlo."""
    import re
    cli = _cli(app)
    html = cli.get('/tecnica', follow_redirects=True).get_data(as_text=True)
    total = html
    for src in set(re.findall(r'<script[^>]+src="([^"]+\.js[^"]*)"', html)):
        if not src.startswith('http'):
            rb = cli.get(src)
            if rb.status_code == 200:
                total += rb.get_data(as_text=True)
    sin_com = "\n".join(l for l in total.splitlines() if not l.strip().startswith('//'))
    assert 'Sin cargar' in sin_com, (
        "la pantalla ya no distingue un registro vacio de uno en cero")
    assert 'cargados' in sin_com, (
        "la pantalla no lee el conteo de cargados que el backend publica")
