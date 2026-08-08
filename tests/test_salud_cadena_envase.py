# -*- coding: utf-8 -*-
"""El vigía de la cadena del envase · cada firma se prueba SEMBRANDO su bug real.

La cadena está cubierta pieza por pieza (35 archivos de test), pero cada verificación corre sólo
cuando alguien abre un endpoint. Un kardex de envases con un descuento de más se ve igual que uno
sano, y el doble descuento estuvo semanas a la vista sin que nadie lo notara. Lo que faltaba no
era el arreglo: era el DETECTOR (M127/M134).

⚠ Cada firma corresponde a un bug que YA PASÓ, no a una hipótesis, y cada test lo reproduce:
sembrar la condición, ver que se detecta, quitarla, ver que desaparece. Un detector que nunca se
probó contra el defecto real es una intención (M142).

⚠ Y NO se afirma que la BD de tests esté limpia: varios fixtures siembran el cache en cero a
propósito (M164), así que exigir cero hallazgos daría rojo por la razón equivocada. Lo que se
prueba es que el detector DISTINGUE.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

PREF = 'SALUDMEE'


def _core(app):
    from database import get_db
    try:
        from blueprints.programacion import _salud_mee_core
    except ImportError:
        from programacion import _salud_mee_core
    with app.app_context():
        return _salud_mee_core(get_db().cursor())


def _limpiar(app):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos_mee WHERE mee_codigo LIKE ?", (PREF + '%',))
        c.execute("DELETE FROM maestro_mee WHERE codigo LIKE ?", (PREF + '%',))
        c.execute("DELETE FROM producto_presentaciones WHERE producto_nombre LIKE ?", (PREF + '%',))
        c.commit()


def _mee(app, codigo, stock_cache=0.0, base=None):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO maestro_mee (codigo, descripcion, stock_actual, material_referencia) "
                  "VALUES (?,?,?,?)", (codigo, 'test ' + codigo, stock_cache, base or ''))
        c.commit()


def _mov(app, codigo, tipo, cantidad):
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, fecha, anulado) "
                  "VALUES (?,?,?, date('now','-5 hours'), 0)", (codigo, tipo, cantidad))
        c.commit()


def _hall(app, firma):
    return [x for x in (_core(app)['hallazgos'].get(firma) or [])
            if PREF in str(x)]


def test_caza_el_serigrafiado_que_ENTRA_y_nunca_SALE(app):
    """M147 causa (a): el frasco vuelve marcado, su stock sólo crece, y producción sigue
    descontando el BASE. El impreso que nunca sale es la huella."""
    _limpiar(app)
    _mee(app, PREF + '-BASE')
    _mee(app, PREF + '-IMP', base=PREF + '-BASE')
    _mov(app, PREF + '-IMP', 'Entrada', 500)          # volvió marcado y nunca se usó
    assert _hall(app, 'serigrafiado_entra_y_nunca_sale'), 'no ve el impreso que sólo crece'
    _mov(app, PREF + '-IMP', 'Salida', 100)           # ahora sí se consume
    assert not _hall(app, 'serigrafiado_entra_y_nunca_sale'), 'sigue avisando con el caso sano'
    _limpiar(app)


def test_caza_el_DOBLE_descuento_base_mas_impreso(app):
    """El otro lado del mismo bug: salen los dos, así que el envase se descontó dos veces."""
    _limpiar(app)
    _mee(app, PREF + '-B2')
    _mee(app, PREF + '-I2', base=PREF + '-B2')
    _mov(app, PREF + '-B2', 'Entrada', 500)
    _mov(app, PREF + '-I2', 'Entrada', 500)
    _mov(app, PREF + '-I2', 'Salida', 100)
    assert not _hall(app, 'base_y_serigrafiado_salen_los_dos'), 'avisa con el caso sano'
    _mov(app, PREF + '-B2', 'Salida', 100)            # y ahora también sale el base
    assert _hall(app, 'base_y_serigrafiado_salen_los_dos'), 'no ve el doble descuento'
    _limpiar(app)


def test_caza_lo_que_SALE_sin_haber_ENTRADO(app):
    """Código fantasma, o una clave con un espacio pegado que partió el stock en dos (M100)."""
    _limpiar(app)
    _mee(app, PREF + '-X')
    _mov(app, PREF + '-X', 'Salida', 30)
    assert _hall(app, 'sale_sin_haber_entrado'), 'no ve el envase que se consumió sin comprarse'
    _mov(app, PREF + '-X', 'Entrada', 100)
    assert not _hall(app, 'sale_sin_haber_entrado'), 'sigue avisando cuando sí entró'
    _limpiar(app)


def test_caza_el_CACHE_que_no_coincide_con_el_kardex(app):
    """M153, que es peor que el doble descuento: con el cache por debajo, la próxima Salida se
    registra CLAMPEADA y el envase se usa mientras el kardex dice que sigue en bodega."""
    _limpiar(app)
    # ⚠ El detalle viene recortado a 50 y ordenado por la diferencia mas grande, asi que el caso
    # sembrado tiene que ser el MAYOR o queda fuera de la lista y el guard mide otra cosa · me
    # paso: con 400 no aparecia y el test daba rojo con el detector sano (M152).
    _mee(app, PREF + '-C', stock_cache=0)
    _mov(app, PREF + '-C', 'Entrada', 999999999)      # kardex enorme, cache 0
    assert _hall(app, 'cache_distinto_del_kardex'), 'no ve el drift del cache'
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("UPDATE maestro_mee SET stock_actual=999999999 WHERE codigo=?", (PREF + '-C',))
        c.commit()
    assert not _hall(app, 'cache_distinto_del_kardex'), 'sigue avisando ya sincronizado'
    _limpiar(app)


def test_el_CLAMP_legitimo_no_se_reporta_como_drift(app):
    """El cache se clampea a 0 por diseño, así que cache=0 con kardex negativo NO es drift: es el
    clamp haciendo lo suyo. Una alerta que suena también en el caso sano deja de mirarse (M129)."""
    _limpiar(app)
    _mee(app, PREF + '-K', stock_cache=0)
    _mov(app, PREF + '-K', 'Salida', 50)              # kardex -50, cache 0
    assert not _hall(app, 'cache_distinto_del_kardex'), \
        'reporta el clamp legítimo como si fuera drift'
    _limpiar(app)


def test_caza_el_stock_NEGATIVO(app):
    _limpiar(app)
    _mee(app, PREF + '-N')
    _mov(app, PREF + '-N', 'Entrada', 10)
    _mov(app, PREF + '-N', 'Salida', 40)
    assert _hall(app, 'stock_negativo'), 'no ve el stock negativo'
    _limpiar(app)


def test_caza_la_PRESENTACION_que_apunta_a_un_envase_que_no_existe(app):
    """Su compra no se resuelve, así que ese envase no se compra nunca y nadie se entera (M5)."""
    _limpiar(app)
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, "
                  "etiqueta, volumen_ml, envase_codigo, activo) "
                  "VALUES (?,'V30','30 ml',30,?,1)", (PREF + ' PRODUCTO', PREF + '-NOEXISTE'))
        c.commit()
    assert _hall(app, 'presentacion_apunta_a_envase_inexistente'), \
        'no ve la presentación que apunta a la nada'
    _mee(app, PREF + '-NOEXISTE')
    assert not _hall(app, 'presentacion_apunta_a_envase_inexistente'), \
        'sigue avisando cuando el envase ya existe'
    _limpiar(app)


def test_caza_la_CLAVE_SUCIA(app):
    """Un tabulador pegado a un código es una clave DISTINTA: parte el stock en dos sin un solo
    error a la vista (M100, que dejó 1.000 envases invisibles)."""
    _limpiar(app)
    _mee(app, PREF + '-S')
    _mov(app, '\t' + PREF + '-S', 'Entrada', 100)
    assert _hall(app, 'codigo_con_espacios_o_control'), 'no ve la clave con un tabulador pegado'
    _limpiar(app)
    from database import get_db
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM movimientos_mee WHERE mee_codigo LIKE ?", ('%' + PREF + '%',))
        c.commit()


def test_un_chequeo_que_NO_pudo_correr_se_DECLARA(app):
    """Si un chequeo devolviera lista vacía en silencio, su resultado se leería como "todo limpio"
    y estaría mintiendo (M100)."""
    r = _core(app)
    assert 'checks_fallidos' in r and 'graves' in r and 'universo' in r
    assert r['ok'] == (r['n_graves'] == 0 and not r['checks_fallidos'])


def test_se_puede_ABRIR_y_lo_mira_un_cron(app, admin_client):
    """Un diagnóstico que nadie abre no existe · y uno que hay que acordarse de abrir es lo mismo
    que no tenerlo, que es la razón por la que este vigía existe (M121/M127)."""
    r = admin_client.get('/api/mee/salud-cadena')
    assert r.status_code == 200
    assert 'hallazgos' in (r.get_json() or {})

    import io as _io
    jobs = _io.open(os.path.join(RAIZ, 'api', 'blueprints', 'auto_plan_jobs.py'),
                    encoding='utf-8').read()
    assert "'job_salud_envases'" in jobs, 'el vigía no está registrado en el multi-cron'
    assert 'def job_salud_envases' in jobs, 'el cron apunta a una función que no existe'
    # avisa cuando CAMBIA, no todos los días
    assert 'salud_mee_firma' in jobs, 'notificaría lo mismo todos los días y dejaría de mirarse'
