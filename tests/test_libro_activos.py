"""Libro de activos · qué tiene la empresa y cuánto vale (30-jul).

Sebastián, sobre el Excel maestro de activos: *"esto es trazabilidad y plata, pero a la vez nos
permite hacer seguimientos · como CEO debo verlo, Tesorería también, y todo lo que llegue se debe
recepcionar"*. Y sobre el alcance: *"materias primas y envases no, porque ese es vivo, varía con
el uso; es todo lo otro, equipos y demás"*.

Lo que este archivo fija:
  · **el valor en libros se DERIVA del estado**, no se teclea: un activo de baja, hurtado o fuera
    de uso deja de sumar, y `Dañado` SIGUE sumando (es un bien deteriorado, no una pérdida);
  · **la baja conserva la fila y exige motivo** — un activo robado no desaparece del libro, se
    registra como pérdida (y se puede revertir si aparece);
  · **el import del Excel no borra nada**: da de alta y actualiza, y lo que sobra se lista;
  · **el equipo que se recibe entra al libro** en el mismo acto (si dependiera de que alguien lo
    copie después, el valor de la empresa quedaría siempre viejo);
  · sólo lo ven CEO y Tesorería.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

COD = 'ZZ-ACT-001'


def _login(app, user='sebastian'):
    c = app.test_client()
    r = c.post('/login', data={'username': user, 'password': TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % user
    return c


def _h():
    h = {'Content-Type': 'application/json'}
    h.update(csrf_headers())
    return h


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ['DB_PATH'], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        filas = cur.fetchall()
        conn.commit()
        return filas
    finally:
        conn.close()


def _limpiar():
    _sql("DELETE FROM activos_eventos WHERE activo_codigo LIKE 'ZZ-ACT%'")
    _sql("DELETE FROM activos WHERE codigo LIKE 'ZZ-ACT%'")


def _sembrar(estado='En uso', costo=1000000, deprec=0):
    _limpiar()
    _sql("INSERT INTO activos (codigo, empresa, nombre, tipo_bien, categoria_contable, "
         "ubicacion, responsable, estado, costo_cop, depreciacion_acumulada_cop, origen) "
         "VALUES (?,?,?,?,?,?,?,?,?,?, 'excel')",
         (COD, 'ANIMUS', 'ZZTEST Computador', 'Equipo/Herramienta', 'Equipo de computo',
          'Administrativa', 'Daniela', estado, costo, deprec))


def _libro(app, user='sebastian'):
    r = _login(app, user).get('/api/activos')
    assert r.status_code == 200, r.data[:300]
    return r.get_json()


def _mio(j):
    return next((x for x in j['items'] if x['codigo'] == COD), None)


# ══ el valor se DERIVA ══════════════════════════════════════════════════════════

def test_el_valor_en_libros_es_costo_menos_depreciacion(app, db_clean):
    _sembrar(costo=1000000, deprec=300000)
    x = _mio(_libro(app))
    assert x and x['en_libros'] is True
    assert x['valor_en_libros'] == 700000, x


def test_un_activo_DANADO_sigue_sumando(app, db_clean):
    """Dañado no es una pérdida: es un bien deteriorado. Sacarlo del valor sería decidir una
    baja que nadie decidió (el propio Excel lo marca como 'para revisión / posible baja')."""
    _sembrar(estado='Dañado', costo=500000)
    x = _mio(_libro(app))
    assert x['en_libros'] is True and x['valor_en_libros'] == 500000, x


def test_hurto_y_baja_NO_suman_pero_la_fila_QUEDA(app, db_clean):
    """Un activo robado no desaparece del libro: se registra como pérdida."""
    for estado in ('Hurto', 'De baja', 'Fuera de uso'):
        _sembrar(estado=estado, costo=800000)
        x = _mio(_libro(app))
        assert x is not None, 'la fila desapareció del libro con estado %s' % estado
        assert x['en_libros'] is False and x['valor_en_libros'] == 0, (estado, x)


# ══ la baja ═════════════════════════════════════════════════════════════════════

def test_dar_de_baja_exige_motivo(app, db_clean):
    _sembrar()
    r = _login(app).post('/api/activos/%s/baja' % COD, headers=_h(),
                         json={'estado': 'De baja'})
    assert r.status_code == 400, 'aceptó sacar plata del libro sin explicar por qué'


def test_dar_de_baja_saca_del_valor_y_deja_el_motivo(app, db_clean):
    _sembrar(costo=1200000, deprec=200000)
    r = _login(app).post('/api/activos/%s/baja' % COD, headers=_h(),
                         json={'estado': 'Hurto', 'motivo': 'ZZTEST se lo llevaron del taller'})
    assert r.status_code == 200, r.data[:300]
    assert r.get_json()['valor_que_sale'] == 1000000
    x = _mio(_libro(app))
    assert x['en_libros'] is False and x['valor_en_libros'] == 0
    assert 'ZZTEST' in x['baja_motivo'], x
    ev = _sql("SELECT tipo, valor_antes, estado_despues FROM activos_eventos "
              "WHERE activo_codigo=? ORDER BY id DESC", (COD,))
    assert ev and ev[0][0] == 'BAJA' and float(ev[0][1]) == 1000000, ev


def test_no_se_da_de_baja_dos_veces(app, db_clean):
    _sembrar()
    cli = _login(app)
    cli.post('/api/activos/%s/baja' % COD, headers=_h(),
             json={'estado': 'De baja', 'motivo': 'ZZTEST primera'})
    r = cli.post('/api/activos/%s/baja' % COD, headers=_h(),
                 json={'estado': 'Hurto', 'motivo': 'ZZTEST segunda'})
    assert r.status_code == 409, 'registró dos pérdidas del mismo activo'


def test_la_baja_se_puede_revertir(app, db_clean):
    """Si el activo aparece, vuelve a sumar. Un libro que no se puede corregir se corrige por
    fuera, y ahí deja de ser el libro."""
    _sembrar(costo=400000)
    cli = _login(app)
    cli.post('/api/activos/%s/baja' % COD, headers=_h(),
             json={'estado': 'Hurto', 'motivo': 'ZZTEST desapareció'})
    r = cli.post('/api/activos/%s/baja' % COD, headers=_h(),
                 json={'revertir': True, 'motivo': 'ZZTEST apareció en otra bodega'})
    assert r.status_code == 200, r.data[:300]
    x = _mio(_libro(app))
    assert x['en_libros'] is True and x['valor_en_libros'] == 400000, x


# ══ quién lo ve ═════════════════════════════════════════════════════════════════

def test_solo_CEO_y_tesoreria(app, db_clean):
    _sembrar()
    r = _login(app, 'mayra').get('/api/activos')           # contadora = Tesorería
    assert r.status_code == 200, 'Tesorería debería ver el libro'
    r = _login(app, 'mayerlin').get('/api/activos')        # operaria de planta
    assert r.status_code == 401, 'el libro de activos no es para toda la planta'


def test_la_pagina_carga(app, db_clean):
    r = _login(app).get('/activos')
    assert r.status_code == 200, r.status_code
    body = r.data.decode('utf-8', 'replace')
    assert 'Libro de activos' in body and 'function actCargar' in body


# ══ el equipo que llega entra al libro ══════════════════════════════════════════

def test_el_equipo_recibido_entra_al_libro(app, db_clean):
    """*"todo lo que llegue se debe recepcionar"*: si el libro dependiera de que alguien copie
    el equipo después, el valor de la empresa estaría siempre viejo."""
    for (cod,) in _sql("SELECT codigo FROM equipos_planta WHERE nombre LIKE 'ZZTEST%'"):
        _sql("DELETE FROM activos_eventos WHERE activo_codigo=?", (cod,))
        _sql("DELETE FROM activos WHERE codigo=?", (cod,))
    _sql("DELETE FROM equipos_planta WHERE nombre LIKE 'ZZTEST%'")
    _sql("DELETE FROM activos WHERE nombre LIKE 'ZZTEST%'")
    r = _login(app).post('/api/recepcion/equipos', headers=_h(), json={
        'nombre': 'ZZTEST equipo libro', 'tipo_prefijo': 'BL', 'area_codigo': 'FAB1',
        'empresa': 'ESPAGIRIA', 'proveedor': 'ZZ Proveedor', 'factura': 'FV-777',
        'valor_cop': 3200000, 'fecha_ingreso': '2026-07-30', 'serial': 'SN-LIBRO-1'})
    assert r.status_code == 201, r.data[:400]
    cod = r.get_json()['codigos'][0]
    j = _libro(app)
    x = next((i for i in j['items'] if i['codigo'] == cod), None)
    assert x is not None, 'el equipo recibido no entró al libro de activos'
    assert x['valor_en_libros'] == 3200000, x
    assert x['origen'] == 'recepcion' and x['equipo_codigo'] == cod, x
    assert x['factura'] == 'FV-777' and x['serial'] == 'SN-LIBRO-1', (
        'el libro perdió la factura o el serial, que es lo que sostiene el valor')


# ══ el import no pierde filas ═══════════════════════════════════════════════════

def _wb_bytes(filas):
    """Arma un Excel con la forma del maestro real (encabezados en la fila 3)."""
    import io as _io
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'INVENTARIO HHA'
    ws.append(['INVENTARIO GENERAL DE ACTIVOS'])
    ws.append(['Consolidado'])
    ws.append(['Código', 'Empresa', 'Tipo de bien', 'Descripción / detalle', 'Área / Ubicación',
               'Responsable', 'Cant.', 'Estado', 'Rotulado', 'Valor estimado (COP)'])
    for f in filas:
        ws.append(f)
    buf = _io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_una_fila_SIN_DESCRIPCION_no_se_pierde_y_se_declara(app, db_clean):
    """Pasó con el archivo real: 3 activos (una balanza y dos tapadoras) traen código y tipo de
    bien pero la descripción vacía, y el import los descartaba SIN AVISO -- 158 de 161. Perder
    un activo en silencio es lo contrario de un libro. Ahora se cargan con el tipo como nombre
    y el plan los DECLARA para que se corrija el Excel."""
    import io as _io
    _limpiar()
    data = _wb_bytes([
        ['ZZ-ACT-001', 'ANIMUS', 'Balanza', 'Balanza analitica', 'Lab', 'Laura', 1, 'En uso', 'SI', 900000],
        ['ZZ-ACT-002', 'ANIMUS', 'Tapadora', '', 'Envasado', 'Sergio', 1, 'En uso', 'NO', 1500000],
    ])
    cli = _login(app)
    r = cli.post('/api/activos/importar?dry_run=0', headers=csrf_headers(),
                 data={'archivo': (_io.BytesIO(data), 'act.xlsx')},
                 content_type='multipart/form-data')
    assert r.status_code == 200, r.data[:400]
    p = r.get_json()
    assert p['en_archivo'] == 2, 'se perdió una fila: %r' % p
    assert p['n_incompletos'] == 1 and p['aviso_incompletos'], (
        'cargó la fila incompleta sin declararla · el silencio es el problema')
    j = _libro(app)
    x = next((i for i in j['items'] if i['codigo'] == 'ZZ-ACT-002'), None)
    assert x is not None, 'la fila sin descripción no entró al libro'
    assert x['nombre'] == 'Tapadora', 'no cayó al tipo de bien como nombre: %r' % x


def test_el_import_no_borra_lo_que_no_viene_en_el_archivo(app, db_clean):
    """*"El Excel manda, sólo usá los que te subo"* NO significa borrar lo que no venga: un
    activo que falta en el archivo puede ser un olvido, y borrarlo perdería su historia. Se
    lista para que Sebastián decida."""
    import io as _io
    _sembrar(costo=700000)                     # ZZ-ACT-001 ya está en el libro
    data = _wb_bytes([
        ['ZZ-ACT-009', 'ANIMUS', 'Silla', 'Silla ejecutiva', 'Gerencia', 'Daniela', 1, 'En uso', 'NO', 250000],
    ])
    r = _login(app).post('/api/activos/importar?dry_run=1', headers=csrf_headers(),
                         data={'archivo': (_io.BytesIO(data), 'act.xlsx')},
                         content_type='multipart/form-data')
    assert r.status_code == 200, r.data[:300]
    p = r.get_json()
    assert p['dry_run'] is True, 'el preview escribió'
    assert COD in (p.get('detalle_sobran') or []), (
        'no avisó que un activo del libro no viene en el archivo: %r' % p)
    assert _mio(_libro(app)) is not None, 'el preview borró algo'
