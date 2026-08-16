# -*- coding: utf-8 -*-
"""La solicitud de pago de caja dice A QUIÉN y CÓMO se le paga (5-ago).

Sebastián: *"proveedor o persona debería poderse elegir de los proveedores ya existentes, o
crear uno nuevo, o solo poner un concepto. Observaciones están bien pero falta la parte de los
datos: Nequi, cuenta bancaria, pagar en efectivo, número de cuenta, número de Nequi. Esto debe
ser así tanto en Compras como en Espagiria y reflejarse a Daniela en Ánimus cuando le llega la
solicitud."*

Hasta hoy la solicitud decía **cuánto** y **a quién** (texto libre), nunca **cómo**. Daniela
recibía una orden de pago que no se puede ejecutar: si era transferencia faltaba la cuenta, si
era Nequi el celular. Eso se resolvía por WhatsApp — fuera del sistema y sin rastro, que es
exactamente lo que este módulo existe para evitar.

Lo que estos tests protegen, en orden de lo que más duele si se rompe:

1. **Una solicitud que dice "transferencia" sin cuenta no se puede crear.** La validación vive
   en el backend, no en la pantalla: dos pantallas mandan al mismo endpoint y si cada una
   validara por su cuenta, una de las dos quedaría floja (M45).
2. **El maestro de proveedores no se vuelca con las cuentas en el load.** La cuenta se pide de
   a una y queda auditada (Ley 1581 · el hallazgo M12(e) fue exactamente ese volcado).
3. **Las tres pantallas muestran lo mismo** porque comparten el pintor, no porque cada una tenga
   su copia.
"""
import io
import json
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _src(rel):
    return io.open(os.path.join(RAIZ, rel), encoding='utf-8').read()


def _post(admin_client, **extra):
    from .conftest import csrf_headers
    cuerpo = {'concepto': 'ZZ prueba caja', 'monto': 5000, 'empresa': 'ANIMUS'}
    cuerpo.update(extra)
    return admin_client.post('/api/caja/solicitudes', data=json.dumps(cuerpo),
                             headers=csrf_headers(), content_type='application/json')


def _limpiar(app):
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM caja_solicitudes_pago WHERE concepto LIKE 'ZZ prueba%'")
        conn.commit()


# ── 1 · una orden de pago que nadie puede ejecutar no se crea ────────────────

def test_TRANSFERENCIA_sin_cuenta_NO_se_puede_pedir(app, admin_client, db_clean):
    """El momento de descubrir que falta la cuenta no puede ser cuando Daniela va a pagar."""
    _limpiar(app)
    r = _post(admin_client, pago_medio='transferencia', pago_banco='Bancolombia')
    assert r.status_code == 400, 'dejó pedir una transferencia sin número de cuenta'
    assert 'cuenta' in (r.get_json() or {}).get('error', '').lower()

    r = _post(admin_client, pago_medio='transferencia', pago_num_cuenta='1234567890')
    assert r.status_code == 400, 'dejó pedir una transferencia sin banco'
    assert 'banco' in (r.get_json() or {}).get('error', '').lower()
    _limpiar(app)


def test_NEQUI_sin_celular_NO_se_puede_pedir(app, admin_client, db_clean):
    _limpiar(app)
    r = _post(admin_client, pago_medio='nequi')
    assert r.status_code == 400, 'dejó pedir un Nequi sin número'
    assert 'nequi' in (r.get_json() or {}).get('error', '').lower()
    _limpiar(app)


def test_EFECTIVO_no_pide_nada_mas(app, admin_client, db_clean):
    """Se le entrega la plata en la mano · guardar una cuenta que no se va a usar sería guardar
    un dato personal sin motivo."""
    _limpiar(app)
    r = _post(admin_client, pago_medio='efectivo')
    assert r.status_code == 201, r.data[:300]
    from database import get_db
    with app.app_context():
        f = get_db().execute(
            "SELECT pago_medio, pago_num_cuenta, pago_nequi FROM caja_solicitudes_pago "
            " WHERE concepto='ZZ prueba caja' ORDER BY id DESC LIMIT 1").fetchone()
    assert f[0] == 'efectivo'
    assert not (f[1] or '') and not (f[2] or ''), 'guardó datos bancarios de un pago en efectivo'
    _limpiar(app)


def test_la_transferencia_COMPLETA_se_guarda_entera(app, admin_client, db_clean):
    _limpiar(app)
    r = _post(admin_client, pago_medio='transferencia', pago_banco='Davivienda',
              pago_tipo_cuenta='ahorros', pago_num_cuenta='4567891230',
              pago_titular='Julián Quiceno', pago_documento='1017234567')
    assert r.status_code == 201, r.data[:300]
    from database import get_db
    with app.app_context():
        f = get_db().execute(
            "SELECT pago_medio, pago_banco, pago_tipo_cuenta, pago_num_cuenta, pago_titular "
            "  FROM caja_solicitudes_pago WHERE concepto='ZZ prueba caja' "
            " ORDER BY id DESC LIMIT 1").fetchone()
    assert list(f) == ['transferencia', 'Davivienda', 'ahorros', '4567891230', 'Julián Quiceno']
    _limpiar(app)


def test_el_celular_de_NEQUI_se_guarda_SIN_espacios_ni_guiones(app, admin_client, db_clean):
    """Un celular con separadores se copia mal a la app del banco y el que paga lo teclea de
    nuevo a mano · que es donde se equivoca."""
    _limpiar(app)
    r = _post(admin_client, pago_medio='nequi', pago_nequi='300 123-4567')
    assert r.status_code == 201, r.data[:300]
    from database import get_db
    with app.app_context():
        f = get_db().execute(
            "SELECT pago_nequi FROM caja_solicitudes_pago WHERE concepto='ZZ prueba caja' "
            " ORDER BY id DESC LIMIT 1").fetchone()
    assert f[0] == '3001234567'
    _limpiar(app)


# ── 2 · a quién ──────────────────────────────────────────────────────────────

def test_decir_PROVEEDOR_sin_elegir_cual_NO_pasa(app, admin_client, db_clean):
    _limpiar(app)
    r = _post(admin_client, beneficiario_tipo='proveedor')
    assert r.status_code == 400, 'aceptó tipo proveedor sin proveedor'
    _limpiar(app)


def test_un_proveedor_que_NO_existe_no_se_guarda(app, admin_client, db_clean):
    """Un beneficiario colgado de un proveedor borrado deja la solicitud sin a-quién-pagarle, y
    nadie se entera hasta que hay que pagar."""
    _limpiar(app)
    r = _post(admin_client, beneficiario_tipo='proveedor', proveedor_id=99999999)
    assert r.status_code == 400
    _limpiar(app)


def test_el_picker_NO_vuelca_las_cuentas(app, admin_client, db_clean):
    """Habeas Data (Ley 1581): abrir la pantalla no puede dejar el maestro entero de cuentas en
    la respuesta · es el hallazgo M12(e)."""
    r = admin_client.get('/api/caja/beneficiarios')
    assert r.status_code == 200
    crudo = r.data.decode('utf-8', 'replace')
    for prohibido in ('num_cuenta', 'tipo_cuenta', 'banco'):
        assert prohibido not in crudo, 'el picker devuelve %s · eso es volcar el maestro' % prohibido


def test_pedir_los_datos_de_un_proveedor_queda_AUDITADO(app, admin_client, db_clean):
    """Una consulta de dato personal es justo lo que una auditoría de Habeas Data pregunta:
    quién vio qué, y cuándo."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM proveedores WHERE nombre='ZZ PROV CAJA'")
        c.execute("INSERT INTO proveedores (nombre, activo, banco, tipo_cuenta, num_cuenta, nit) "
                  "VALUES ('ZZ PROV CAJA',1,'Bancolombia','ahorros','9876543210','900123')")
        conn.commit()
        pid = conn.execute("SELECT id FROM proveedores WHERE nombre='ZZ PROV CAJA'").fetchone()[0]

    r = admin_client.get('/api/caja/beneficiario-datos?proveedor_id=%d' % pid)
    assert r.status_code == 200, r.data[:200]
    d = r.get_json()
    assert d['num_cuenta'] == '9876543210' and d['tiene_datos'] is True

    with app.app_context():
        conn = get_db()
        n = conn.execute("SELECT COUNT(*) FROM audit_log WHERE accion='CAJA_VER_DATOS_BANCARIOS' "
                         " AND registro_id=?", (str(pid),)).fetchone()[0]
        conn.execute("DELETE FROM proveedores WHERE nombre='ZZ PROV CAJA'")
        conn.commit()
    assert n >= 1, 'ver una cuenta bancaria no dejó rastro en audit_log'


def test_un_proveedor_SIN_cuenta_lo_DICE(app, admin_client, db_clean):
    """Campos vacíos se leen como "no tiene" · son dos cosas distintas y la segunda manda a
    buscar el dato por fuera del sistema."""
    from database import get_db
    with app.app_context():
        conn = get_db(); c = conn.cursor()
        c.execute("DELETE FROM proveedores WHERE nombre='ZZ PROV SIN CTA'")
        c.execute("INSERT INTO proveedores (nombre, activo) VALUES ('ZZ PROV SIN CTA',1)")
        conn.commit()
        pid = conn.execute("SELECT id FROM proveedores WHERE nombre='ZZ PROV SIN CTA'").fetchone()[0]
    d = admin_client.get('/api/caja/beneficiario-datos?proveedor_id=%d' % pid).get_json()
    assert d['tiene_datos'] is False and d['aviso'], 'no avisa que el proveedor no tiene cuenta'
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM proveedores WHERE nombre='ZZ PROV SIN CTA'")
        conn.commit()


# ── 3 · el audit no se lleva el dato personal ────────────────────────────────

def test_el_AUDIT_guarda_el_medio_pero_NO_la_cuenta(app, admin_client, db_clean):
    """`audit_log` es inmutable por trigger: un dato personal que entra ahí no sale nunca más.
    El rastro que importa es "se pidió pagar por transferencia"."""
    _limpiar(app)
    _post(admin_client, pago_medio='transferencia', pago_banco='BBVA',
          pago_num_cuenta='5551234444')
    from database import get_db
    with app.app_context():
        filas = get_db().execute(
            "SELECT COALESCE(despues,'') FROM audit_log WHERE accion='CAJA_SOLICITUD_CREAR' "
            " ORDER BY id DESC LIMIT 3").fetchall()
    junto = ' '.join(str(f[0]) for f in filas)
    assert 'transferencia' in junto, 'el audit no registra el medio de pago'
    assert '5551234444' not in junto, 'el audit se llevó el número de cuenta'
    _limpiar(app)


# ── 4 · UNA definición para las tres pantallas ───────────────────────────────

def test_las_TRES_pantallas_usan_el_MISMO_pintor(app, db_clean):
    """Compras, Espagiria y la bandeja de Daniela. Si cada una armara el suyo, el día que se
    agregue un medio de pago dos quedarían mostrando el anterior (M45)."""
    import sys
    sys.path.insert(0, os.path.join(RAIZ, 'api'))
    from .conftest import contenido_pantalla
    from templates_py.espagiria_html import HTML as ESP_HTML
    from templates_py.animus_html import ANIMUS_HTML
    # El JS de Compras se sirve como archivo aparte desde el 15-ago: la pantalla es el HTML
    # MAS su bundle (M166 · lo que se fija es que la funcion exista, no donde este escrita).
    COMPRAS_HTML = contenido_pantalla('compras_html', 'COMPRAS_HTML')
    for nombre, h in (('compras', COMPRAS_HTML), ('espagiria', ESP_HTML), ('animus', ANIMUS_HTML)):
        assert h.count('function cajaComoPagar(') == 1, \
            '%s no tiene el pintor compartido (o lo tiene duplicado)' % nombre
        assert 'cajaComoPagar(s,' in h, '%s no lo usa en su tabla' % nombre
        assert '.cajam-chip' in h, '%s no trae el estilo de los chips' % nombre


def test_el_MODAL_esta_en_las_dos_pantallas_que_lo_piden(app, db_clean):
    import sys
    sys.path.insert(0, os.path.join(RAIZ, 'api'))
    from templates_py.compras_html import COMPRAS_HTML
    from templates_py.espagiria_html import HTML as ESP_HTML
    for nombre, h, pref in (('compras', COMPRAS_HTML, 'cp'), ('espagiria', ESP_HTML, 'ep')):
        n = h.count('class="cajam-box"')
        assert n == 1, '%s tiene %d modales (esperaba 1)' % (nombre, n)
        # los tres caminos de "a quién" y los tres medios de pago
        for t in ('proveedor', 'persona', 'concepto'):
            assert 'data-bt="%s"' % t in h, '%s no ofrece el camino "%s"' % (nombre, t)
        for m in ('efectivo', 'nequi', 'transferencia'):
            assert 'data-medio="%s"' % m in h, '%s no ofrece pagar por %s' % (nombre, m)
        assert '%s-numcta' % pref in h and '%s-nequi' % pref in h
        # y no quedó ningún marcador sin rellenar (si el replace no matchea, el botón abriría
        # un modal que no existe · M112/M116)
        assert 'CAJA_MODAL' not in h and '__CAJA_JS' not in h, \
            '%s tiene un marcador de inyección sin rellenar' % nombre


def test_no_quedaron_DOS_definiciones_de_la_misma_funcion(app, db_clean):
    """Dos `function X` con el mismo nombre no dan error: gana la última, en silencio (M120).
    Es lo que pasó al reemplazar el `epAbrir` viejo por el compartido."""
    import sys
    sys.path.insert(0, os.path.join(RAIZ, 'api'))
    from .conftest import contenido_pantalla
    from templates_py.espagiria_html import HTML as ESP_HTML
    COMPRAS_HTML = contenido_pantalla('compras_html', 'COMPRAS_HTML')
    for nombre, h, pref in (('compras', COMPRAS_HTML, 'cp'), ('espagiria', ESP_HTML, 'ep')):
        for fn in ('Abrir', 'Cerrar', 'Cuerpo', 'Medio', 'BenTipo', 'CargarBenef'):
            n = len(re.findall(r'function %s%s\s*\(' % (pref, fn), h))
            assert n == 1, '%s define %s%s %d veces' % (nombre, pref, fn, n)


def test_el_JS_de_las_tres_pantallas_es_VALIDO(app, db_clean):
    """node --check del valor EVALUADO · el AST de Python pasa igual con el `<script>` roto."""
    import subprocess
    import sys
    import tempfile
    import pytest
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
    except Exception:
        pytest.skip('sin node en este entorno')
    sys.path.insert(0, os.path.join(RAIZ, 'api'))
    from templates_py.compras_html import COMPRAS_HTML
    from templates_py.espagiria_html import HTML as ESP_HTML
    from templates_py.animus_html import ANIMUS_HTML
    tmp = tempfile.mkdtemp()
    # El bloque grande de Compras ya no esta inline: si no se agrega aca, este guard deja de
    # revisar justo el archivo mas grande y pasa verde sin haberlo mirado (M143/M173).
    from templates_py.compras_html import COMPRAS_APP_JS as _CP_BUNDLE
    bloques_extra = [('compras-bundle', _CP_BUNDLE)] if _CP_BUNDLE else []
    for nombre, h in (('compras', COMPRAS_HTML), ('espagiria', ESP_HTML), ('animus', ANIMUS_HTML)):
        for idx, blk in enumerate(re.findall(r'<script[^>]*>(.*?)</script>', h, re.S)):
            if not blk.strip() or 'src=' in blk[:80]:
                continue
            f = os.path.join(tmp, '%s%d.js' % (nombre, idx))
            io.open(f, 'w', encoding='utf-8').write(blk)
            r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
            assert r.returncode == 0, 'JS roto en %s bloque %d: %s' % (nombre, idx, r.stderr[:500])
    for nombre, blk in bloques_extra:
        f = os.path.join(tmp, '%s.js' % nombre)
        io.open(f, 'w', encoding='utf-8').write(blk)
        r = subprocess.run(['node', '--check', f], capture_output=True, text=True)
        assert r.returncode == 0, 'JS roto en %s: %s' % (nombre, r.stderr[:500])


def test_la_migracion_es_ADITIVA(app, db_clean):
    """Las solicitudes que ya existen se siguen leyendo igual · ponerle un medio de pago a una
    solicitud vieja sería inventar un hecho que nadie registró (M117)."""
    db = _src('api/database.py')
    i = db.find("(417, \"caja menor: COMO se le paga")
    assert i > 0, 'no encontré la migración 417'
    bloque = db[i:db.find('\n    ]),', i)]
    for prohibido in ('UPDATE ', 'DELETE ', 'DROP '):
        assert prohibido not in bloque.upper(), \
            'la migración 417 hace %s · tiene que ser sólo ADD COLUMN' % prohibido.strip()
    assert bloque.count('ADD COLUMN') == 9
