# -*- coding: utf-8 -*-
"""Copia de la base FUERA del proveedor · tarea B-01 del ASG-PRO-014.

Lo que estos tests protegen no es "el respaldo corre", es que **se pueda VOLVER a leer**. Un
respaldo que no se puede abrir se ve exactamente igual que uno bueno hasta el día que hace falta,
y ese día ya no hay nada que hacer. Por eso cada guard se prueba reintroduciendo su defecto:
si el detector no muerde con la copia rota, no está detectando nada (M104/M152).
"""
import gzip
import json
import os
import sys
import tempfile

import pytest

# ⚠ NO se toca `sys.path` a nivel de módulo. Hacerlo deja `config` importado ANTES de que corra la
# fixture `app`, o sea sin las claves de prueba, y a partir de ahí el login de los tests siguientes
# falla con un error que no habla de este archivo (M165). La fixture `app` ya pone `api/` en la
# ruta, así que cada test que importe del backend la pide, aunque no use la base.


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Cifrado
# ─────────────────────────────────────────────────────────────────────────────────────────────

def _tmp(nombre):
    return os.path.join(tempfile.gettempdir(), nombre)


def test_cifrado_ida_y_vuelta_devuelve_lo_mismo(app, monkeypatch):
    """Lo que entra tiene que ser byte a byte lo que sale · incluido el caso multi-bloque."""
    import respaldo_db as R
    monkeypatch.setenv('BACKUP_CIPHER_KEY', 'clave-de-prueba-eos')
    origen, cif, vuelta = _tmp('r_o.bin'), _tmp('r_c.bin'), _tmp('r_v.bin')
    # Más de un bloque a propósito: el nonce se deriva del contador y un error ahí sólo se ve
    # cuando hay más de uno.
    datos = os.urandom(int(R.BLOQUE * 2.5))
    with open(origen, 'wb') as f:
        f.write(datos)
    clave = R._clave()
    n = R._cifrar_a(origen, cif, clave)
    assert n == 3, 'se esperaban 3 bloques, hubo %d' % n
    R._descifrar_a(cif, vuelta, clave)
    with open(vuelta, 'rb') as f:
        assert f.read() == datos
    for p in (origen, cif, vuelta):
        os.remove(p)


def test_cifrado_detecta_que_alteraron_el_archivo(app, monkeypatch):
    """DIENTES · si alguien cambia un byte, el descifrado FALLA en vez de devolver basura.

    Es la diferencia entre un archivo cifrado y un archivo cifrado que además prueba su
    integridad. Sin la etiqueta de autenticidad, una copia corrupta se restauraría en silencio.
    """
    import respaldo_db as R
    monkeypatch.setenv('BACKUP_CIPHER_KEY', 'clave-de-prueba-eos')
    origen, cif, vuelta = _tmp('r_o2.bin'), _tmp('r_c2.bin'), _tmp('r_v2.bin')
    with open(origen, 'wb') as f:
        f.write(b'contenido regulado que no puede corromperse en silencio' * 100)
    clave = R._clave()
    R._cifrar_a(origen, cif, clave)

    with open(cif, 'r+b') as f:            # se altera UN byte del texto cifrado
        f.seek(len(R.MAGIC) + 4 + 12 + 5)
        b = f.read(1)
        f.seek(-1, 1)
        f.write(bytes([b[0] ^ 0xFF]))

    with pytest.raises(Exception):
        R._descifrar_a(cif, vuelta, clave)
    for p in (origen, cif, vuelta):
        if os.path.exists(p):
            os.remove(p)


def test_sin_clave_no_cifra_pero_lo_dice(app, monkeypatch):
    """Sin clave el respaldo IGUAL se hace (tener los datos importa más), pero se declara."""
    import respaldo_db as R
    monkeypatch.delenv('BACKUP_CIPHER_KEY', raising=False)
    assert R._clave() is None
    assert R.clave_configurada() is False


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Volcado
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_volcado_incluye_las_filas_sembradas(app):
    """El volcado tiene que traer los datos REALES, y el manifiesto tiene que cuadrar con ellos."""
    import respaldo_db as R
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        # Limpieza ANTES de sembrar (M103): la base de tests es compartida y persiste entre
        # corridas en PostgreSQL.
        c.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'RESPTEST%'")
        for i in range(3):
            c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
                      "VALUES (?,?,?,1)",
                      ('RESPTEST%02d' % i, 'INCI PRUEBA %d' % i, 'Comercial %d' % i))
        conn.commit()

        ruta = _tmp('respaldo_prueba.jsonl.gz')
        man = R.volcar(conn, ruta, presupuesto_seg=300)

    assert man['completo'], 'el volcado se truncó: %s' % man['truncado']
    assert man['tablas'].get('maestro_mps', {}).get('filas', 0) >= 3

    hallados = []
    with gzip.open(ruta, 'rt', encoding='utf-8') as f:
        cab = json.loads(f.readline())
        assert cab.get('__eos_respaldo__') == 1
        for linea in f:
            r = json.loads(linea)
            if r['t'] == 'maestro_mps' and str(r['f'].get('codigo_mp', '')).startswith('RESPTEST'):
                hallados.append(r['f']['codigo_mp'])
    assert len(hallados) == 3, 'esperaba 3 filas sembradas, hallé %d' % len(hallados)
    os.remove(ruta)


def test_volcado_truncado_se_declara(app, monkeypatch):
    """DIENTES · con presupuesto cero el volcado NO puede decir que está completo.

    Una copia recortada que se reporta completa es la peor de todas: nadie la revisa hasta que
    hace falta restaurar.
    """
    import respaldo_db as R
    with app.app_context():
        from database import get_db
        ruta = _tmp('respaldo_truncado.jsonl.gz')
        man = R.volcar(get_db(), ruta, presupuesto_seg=-1)
    assert man['completo'] is False
    assert man['truncado'], 'debía enumerar las tablas que quedaron sin volcar'
    os.remove(ruta)


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Estado · lo que lee la verificación mensual (ASG-PRO-014-F01)
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_estado_dice_cuando_nunca_hubo_copia(app):
    """Sin ninguna copia el estado NO puede salir en verde."""
    import respaldo_db as R
    with app.app_context():
        from database import get_db
        conn = get_db()
        conn.cursor().execute("DELETE FROM respaldo_log")
        conn.commit()
        est = R.estado(conn)
    assert est['ok'] is False
    texto = ' '.join(est['hallazgos']).lower()
    assert 'nunca' in texto


def test_estado_marca_la_copia_vieja(app):
    """DIENTES · una copia semanal de hace 30 días tiene que salir como hallazgo."""
    import respaldo_db as R
    from datetime import timedelta
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM respaldo_log")
        vieja = (R._hoy_col() - timedelta(days=30)).isoformat()
        reciente = R._hoy_col().isoformat()
        c.execute("INSERT INTO respaldo_log (tipo, fecha, r2_key, bytes, filas, completo, cifrado) "
                  "VALUES ('semanal',?,'k',10,10,1,1)", (vieja,))
        c.execute("INSERT INTO respaldo_log (tipo, fecha, r2_key, bytes, filas, completo, cifrado) "
                  "VALUES ('mensual',?,'k',10,10,1,1)", (reciente,))
        conn.commit()
        est = R.estado(conn)
    assert est['ok'] is False
    assert any('30 d' in h or 'días' in h for h in est['hallazgos']), est['hallazgos']


def test_estado_sin_hallazgos_con_copias_al_dia(app, monkeypatch):
    """Y el caso sano: con las dos copias frescas y cifradas, no hay hallazgos.

    Sin este test el anterior pasaría aunque `estado()` gritara SIEMPRE, que es la forma más
    común de que una alerta deje de mirarse (M129).
    """
    import respaldo_db as R
    monkeypatch.setenv('BACKUP_CIPHER_KEY', 'clave-de-prueba-eos')
    monkeypatch.setattr(R, 'clave_configurada', lambda: True)
    import r2_storage
    monkeypatch.setattr(r2_storage, 'r2_configurado', lambda: True)
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM respaldo_log")
        ahora = R._hoy_col().isoformat()
        for tipo in ('semanal', 'mensual'):
            c.execute("INSERT INTO respaldo_log (tipo, fecha, r2_key, bytes, filas, completo, "
                      "cifrado) VALUES (?,?,'k',999,999,1,1)", (tipo, ahora))
        conn.commit()
        est = R.estado(conn)
    assert est['ok'] is True, est['hallazgos']


# ─────────────────────────────────────────────────────────────────────────────────────────────
# La pantalla y los permisos
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_pagina_respaldos_abre(admin_client):
    """El golden no abre páginas de admin: sin este test, un NameError acá se descubre en
    producción cuando alguien usa el botón (M78)."""
    r = admin_client.get('/admin/respaldos')
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'respaldo-estado' in html
    assert 'Verificar' in html


def test_estado_requiere_admin(logged_client):
    """Un usuario común no puede ver ni disparar los respaldos."""
    assert logged_client.get('/api/admin/respaldo-estado').status_code in (401, 403)
    assert logged_client.post('/api/admin/respaldo-ahora', json={}).status_code in (401, 403)


def test_respaldo_ahora_sin_almacenamiento_no_miente(admin_client, monkeypatch):
    """Si no hay dónde guardar, el botón lo dice · no responde ok y no hace nada."""
    import r2_storage
    monkeypatch.setattr(r2_storage, 'r2_configurado', lambda: False)
    r = admin_client.post('/api/admin/respaldo-ahora', json={'tipo': 'semanal'})
    assert r.status_code == 503
    assert 'no está configurado' in r.get_json().get('error', '')


def test_tipo_invalido_se_rechaza(admin_client):
    r = admin_client.post('/api/admin/respaldo-ahora', json={'tipo': 'diario'})
    assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────────────────────
# El cron quedó ENCHUFADO (una capacidad que nadie dispara no existe · M121)
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_los_respaldos_estan_en_el_cron(app):
    from blueprints.auto_plan_jobs import JOBS_SCHEDULE
    nombres = {j[0] for j in JOBS_SCHEDULE}
    assert 'respaldo_base_semanal' in nombres
    assert 'respaldo_base_mensual' in nombres
    llamables = {j[5] for j in JOBS_SCHEDULE if j[0].startswith('respaldo_base')}
    import blueprints.auto_plan_jobs as J
    for nombre in llamables:
        assert hasattr(J, nombre), 'el cron apunta a %s y esa función no existe' % nombre


def test_la_pagina_esta_enlazada():
    """M121 · una pantalla sin un solo enlace obliga a teclear la URL, o sea no existe."""
    import io
    import re
    encontrado = False
    for ruta in ('api/templates_py/dashboard_html.py', 'api/blueprints/admin.py'):
        try:
            s = io.open(ruta, encoding='utf-8').read()
        except OSError:
            continue
        # Se busca el enlace REAL, no la definición de la ruta ni un comentario que la mencione
        # (M154: un test que encuentra su propia explicación pasa por la razón equivocada).
        sin_comentarios = re.sub(r'^\s*#.*$', '', s, flags=re.M)
        if re.search(r'''href=["']/admin/respaldos["']''', sin_comentarios):
            encontrado = True
            break
    assert encontrado, 'la pantalla /admin/respaldos no está enlazada desde ninguna parte'


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Verificación · el guard que decide si una copia SIRVE
# ─────────────────────────────────────────────────────────────────────────────────────────────

def _copia_falsa(R, filas_reales, filas_manifiesto, cifrar=False, clave=None):
    """Arma una copia en memoria y su manifiesto. `filas_manifiesto` puede MENTIR a propósito."""
    import io as _io
    buf = _io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as gz:
        gz.write((json.dumps({'__eos_respaldo__': 1, 'formato': 'jsonl-datos'}) + '\n')
                 .encode('utf-8'))
        for i in range(filas_reales):
            gz.write((json.dumps({'t': 'maestro_mps', 'f': {'codigo_mp': 'X%d' % i}}) + '\n')
                     .encode('utf-8'))
    datos = buf.getvalue()
    if cifrar:
        o, c = _tmp('vf_o.gz'), _tmp('vf_c.bin')
        with open(o, 'wb') as f:
            f.write(datos)
        R._cifrar_a(o, c, clave)
        with open(c, 'rb') as f:
            datos = f.read()
        for p in (o, c):
            os.remove(p)
    manifiesto = json.dumps({'tablas': {'maestro_mps': {'filas': filas_manifiesto}}}).encode('utf-8')
    return datos, manifiesto


def test_verificar_acepta_una_copia_buena(app, monkeypatch):
    """Caso sano · si la copia cuadra con su manifiesto, la verificación pasa.

    Sin este test, el de abajo pasaría igual con un verificador que dijera 'mal' SIEMPRE.
    """
    import respaldo_db as R
    import r2_storage
    datos, man = _copia_falsa(R, 25, 25)
    monkeypatch.setattr(r2_storage, 'r2_get',
                        lambda k: man if k.endswith('.manifiesto.json') else datos)
    res = R.verificar('respaldo/semanal/x.jsonl.gz')
    assert res['ok'] is True, res
    assert res['filas'] == 25


def test_verificar_detecta_una_copia_incompleta(app, monkeypatch):
    """DIENTES · el manifiesto dice 100 filas y el archivo trae 25 → NO puede dar por buena.

    Es exactamente el defecto que produce un volcado cortado a mitad: el archivo se abre bien,
    pesa lo suyo y le faltan datos. Contar contra el manifiesto es lo único que lo distingue.
    """
    import respaldo_db as R
    import r2_storage
    datos, man = _copia_falsa(R, 25, 100)
    monkeypatch.setattr(r2_storage, 'r2_get',
                        lambda k: man if k.endswith('.manifiesto.json') else datos)
    res = R.verificar('respaldo/semanal/x.jsonl.gz')
    assert res['ok'] is False
    assert res['n_diferencias'] == 1
    assert res['diferencias'][0]['tabla'] == 'maestro_mps'
    assert res['diferencias'][0]['manifiesto'] == 100
    assert res['diferencias'][0]['leidas'] == 25


def test_verificar_abre_una_copia_cifrada(app, monkeypatch):
    """El camino real: la copia va cifrada, así que la verificación tiene que descifrarla."""
    import respaldo_db as R
    import r2_storage
    monkeypatch.setenv('BACKUP_CIPHER_KEY', 'clave-de-prueba-eos')
    datos, man = _copia_falsa(R, 12, 12, cifrar=True, clave=R._clave())
    monkeypatch.setattr(r2_storage, 'r2_get',
                        lambda k: man if k.endswith('.manifiesto.json') else datos)
    res = R.verificar('respaldo/semanal/x.jsonl.gz.enc')
    assert res['ok'] is True, res
    assert res['cifrado'] is True


def test_verificar_sin_clave_no_finge_que_esta_bien(app, monkeypatch):
    """Una copia cifrada sin clave a mano NO se puede verificar, y eso se dice."""
    import respaldo_db as R
    import r2_storage
    monkeypatch.setenv('BACKUP_CIPHER_KEY', 'clave-de-prueba-eos')
    datos, man = _copia_falsa(R, 5, 5, cifrar=True, clave=R._clave())
    monkeypatch.delenv('BACKUP_CIPHER_KEY', raising=False)
    monkeypatch.setattr(r2_storage, 'r2_get',
                        lambda k: man if k.endswith('.manifiesto.json') else datos)
    res = R.verificar('respaldo/semanal/x.jsonl.gz.enc')
    assert res['ok'] is False
    assert 'clave' in res['motivo'].lower()


# ─────────────────────────────────────────────────────────────────────────────────────────────
# IDA Y VUELTA COMPLETA · volcar → cifrar → descifrar → CARGAR en una base nueva
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_ida_y_vuelta_completa_a_una_base_nueva(app, monkeypatch):
    """La prueba que hace que esto sea un respaldo y no un archivo.

    Recorre el camino REAL de una restauración: se vuelca la base de pruebas, se cifra, se
    descifra y se carga en una base VACÍA con el mismo esquema; después se cuentan las filas de
    los dos lados. Todo lo demás (que el archivo pese, que se suba, que exista) puede estar bien
    y aun así no haber nada que restaurar.

    Sólo corre sobre SQLite: en modo PostgreSQL la base de pruebas es compartida y crear otra
    dentro del test la ensuciaría (M103).
    """
    import sqlite3
    import respaldo_db as R

    with app.app_context():
        from database import get_db
        conn = get_db()
        if 'sqlite' not in type(conn).__module__.lower() and not hasattr(conn, 'execute'):
            pytest.skip('la ida y vuelta se prueba en SQLite')
        c = conn.cursor()
        try:
            c.execute("SELECT sql, name FROM sqlite_master WHERE type='table' AND sql IS NOT NULL")
            esquema = c.fetchall()
        except Exception:
            pytest.skip('la ida y vuelta se prueba en SQLite')

        c.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'IDAVUELTA%'")
        for i in range(5):
            c.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, nombre_comercial, activo) "
                      "VALUES (?,?,?,1)",
                      ('IDAVUELTA%02d' % i, 'INCI %d' % i, 'Comercial · tildes ñ %d' % i))
        conn.commit()

        crudo = _tmp('iv_datos.jsonl.gz')
        man = R.volcar(conn, crudo, presupuesto_seg=300)
        esperado = {t: v['filas'] for t, v in man['tablas'].items()
                    if isinstance(v, dict) and v.get('filas', 0) > 0}

    # cifrar y descifrar, como en producción
    monkeypatch.setenv('BACKUP_CIPHER_KEY', 'clave-de-prueba-eos')
    cif, vuelto = _tmp('iv_datos.enc'), _tmp('iv_datos_vuelto.gz')
    R._cifrar_a(crudo, cif, R._clave())
    R._descifrar_a(cif, vuelto, R._clave())

    # base NUEVA con el mismo esquema
    destino = _tmp('iv_destino.db')
    if os.path.exists(destino):
        os.remove(destino)
    nueva = sqlite3.connect(destino)
    for sql, _n in esquema:
        try:
            nueva.execute(sql)
        except Exception:
            pass
    nueva.commit()

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
    import restaurar_respaldo as RR
    contados, fallidas = RR.cargar(nueva, vuelto, verbose=False)

    # Lo sembrado tiene que estar del otro lado, con las tildes intactas
    fila = nueva.execute("SELECT nombre_comercial FROM maestro_mps WHERE codigo_mp='IDAVUELTA00'"
                         ).fetchone()
    assert fila is not None, 'la fila sembrada no llegó a la base restaurada'
    assert 'ñ' in fila[0], 'se perdió la codificación en el camino'

    # y el conteo por tabla tiene que coincidir con el volcado
    faltantes = {t: (n, contados.get(t, 0)) for t, n in esperado.items()
                 if t not in RR.OMITIR and contados.get(t, 0) != n}
    assert not faltantes, 'no se cargaron completas: %s' % list(faltantes.items())[:5]

    nueva.close()
    for p in (crudo, cif, vuelto, destino):
        try:
            os.remove(p)
        except OSError:
            pass


# ─────────────────────────────────────────────────────────────────────────────────────────────
# Proteccion del contenedor (tarea B-03) · "no pude comprobarlo" NO es "esta apagado"
# ─────────────────────────────────────────────────────────────────────────────────────────────

def test_proteccion_apagada_es_hallazgo(app, monkeypatch):
    """DIENTES · con el versionado y el bloqueo apagados, el estado NO puede salir en verde."""
    import respaldo_db as R
    import r2_storage
    monkeypatch.setattr(R, 'clave_configurada', lambda: True)
    monkeypatch.setattr(r2_storage, 'r2_configurado', lambda: True)
    monkeypatch.setattr(r2_storage, 'r2_proteccion',
                        lambda: {'versionado': False, 'bloqueo_objetos': False, 'detalle': ''})
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM respaldo_log")
        ahora = R._hoy_col().isoformat()
        for tipo in ('semanal', 'mensual'):
            c.execute("INSERT INTO respaldo_log (tipo, fecha, r2_key, bytes, filas, completo, "
                      "cifrado) VALUES (?,?,'k',9,9,1,1)", (tipo, ahora))
        conn.commit()
        est = R.estado(conn)
    assert est['ok'] is False
    texto = ' '.join(est['hallazgos']).lower()
    assert 'versionado' in texto and 'inmutable' in texto


def test_no_poder_comprobarlo_NO_se_reporta_como_apagado(app, monkeypatch):
    """El caso que hace legítimo el guard: si el proveedor no expone la consulta, la pantalla
    NO puede acusar una falla que no verificó · una alerta que suena sin motivo deja de mirarse."""
    import respaldo_db as R
    import r2_storage
    monkeypatch.setattr(R, 'clave_configurada', lambda: True)
    monkeypatch.setattr(r2_storage, 'r2_configurado', lambda: True)
    monkeypatch.setattr(r2_storage, 'r2_proteccion',
                        lambda: {'versionado': None, 'bloqueo_objetos': None,
                                 'detalle': 'no pude consultarlo'})
    with app.app_context():
        from database import get_db
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM respaldo_log")
        ahora = R._hoy_col().isoformat()
        for tipo in ('semanal', 'mensual'):
            c.execute("INSERT INTO respaldo_log (tipo, fecha, r2_key, bytes, filas, completo, "
                      "cifrado) VALUES (?,?,'k',9,9,1,1)", (tipo, ahora))
        conn.commit()
        est = R.estado(conn)
    assert est['ok'] is True, 'no debe haber hallazgos por algo que no se pudo comprobar: %s' % est['hallazgos']
    assert est['proteccion']['versionado'] is None
