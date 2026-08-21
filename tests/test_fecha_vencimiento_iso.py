# -*- coding: utf-8 -*-
"""La fecha de vencimiento del kardex vive en ISO, o el stock desaparece en silencio · 21-ago-2026.

Sebastián, con el AZ HYBRID CLEAR abierto: *"le digo que me mire stock y dice esto, pero cuando
reviso el inventario sí tengo esas materias primas"*. El PROPYLENE GLYCOL decía **"disponible 0g ·
FALTA 4000g"** y en la MISMA fila, tres milímetros más abajo, *"LOTES A USAR (FEFO): 20251226 ·
29.137,5g · Est. Estiba"* -- con el lote VIGENTE en bodega.

No era el motor: era el FORMATO. El lote traía `26-Dic-2026` en vez de `2026-12-26`, y de ahí
salen dos comportamientos opuestos sobre el mismo hecho:

  · el DISPONIBLE compara con `date(fecha_vencimiento)`, que ante un texto devuelve NULL -> la
    comparación es falsa -> el lote se cae del stock distribuible, y el FEFO tampoco lo consume;
  · la LISTA de lotes comparaba como TEXTO, donde `26-Dic-2026` es "mayor" que `2026-08-21` sólo
    porque empieza con `2` -> lo daba por vigente.

Y `job_marcar_vencidos` usa el mismo `date(...)`: un lote realmente vencido con la fecha así
**nunca se marca**, o sea que el control de vencimiento deja de sonar sin avisar.
"""
import os
import re
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

_COD = 'MP-FVISO-TEST'
_LOTE = 'LOTE-FVISO-1'
_NOM_MP = 'MP DE PRUEBA FVISO'


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
    return c


def _sql(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.fetchall()
    finally:
        conn.close()


def _limpiar():
    """Limpieza ANTES de sembrar, con nombres FIJOS: idempotente por construcción (M103)."""
    _sql("DELETE FROM movimientos WHERE material_id=?", (_COD,))
    _sql("DELETE FROM maestro_mps WHERE codigo_mp=?", (_COD,))


def _sembrar_mp():
    _sql("INSERT INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES (?,?,1)",
         (_COD, 'MP DE PRUEBA FVISO'))


# ── el helper, que es donde vive la regla ────────────────────────────────────

def test_el_helper_lee_lo_que_la_gente_escribe_y_devuelve_ISO():
    from api.audit_helpers import fecha_iso
    assert fecha_iso('26-Dic-2026') == '2026-12-26', "el formato que apareció en producción"
    assert fecha_iso('5-Dic-2025') == '2025-12-05', "día de un solo dígito"
    assert fecha_iso('15-ENE-2027') == '2027-01-15'
    assert fecha_iso('26/12/2026') == '2026-12-26'
    assert fecha_iso('26-12-2026') == '2026-12-26'
    assert fecha_iso('2026-12-26') == '2026-12-26', "lo que ya está bien no se toca"
    assert fecha_iso('2026-12-26 00:00:00') == '2026-12-26', "la hora sobra"


def test_lo_que_no_se_puede_leer_NO_se_adivina():
    """Inventar una fecha de vencimiento es dejar entrar material vencido a producción (M19)."""
    from api.audit_helpers import fecha_iso
    for basura in ('', None, 'proximamente', '26-Xyz-2026', '2026-13-45', 'sin fecha'):
        assert fecha_iso(basura) == '', "adivinó una fecha para %r" % (basura,)


# ── la escritura: entre lo que entre, al kardex va ISO ───────────────────────

def test_el_ingreso_guarda_ISO_aunque_le_manden_la_fecha_en_texto(app, db_clean):
    _limpiar()
    _sembrar_mp()
    c = _login(app)
    r = c.post('/api/recepcion', json={
        'codigo_mp': _COD, 'nombre': 'MP DE PRUEBA FVISO', 'cantidad': 1000,
        'lote': _LOTE, 'fecha_vencimiento': '26-Dic-2027', 'proveedor': 'PRUEBA',
        'cuarentena': False,
    }, headers=csrf_headers())
    assert r.status_code in (200, 201), r.data[:300]
    fv = _sql("SELECT fecha_vencimiento FROM movimientos WHERE material_id=? AND lote=?",
              (_COD, _LOTE))
    assert fv, "no quedó el movimiento"
    assert fv[0][0] == '2027-12-26', (
        "el kardex guardó %r en vez de ISO: con eso date() devuelve NULL "
        "y el lote se cae del stock sin un solo mensaje" % (fv[0][0],))
    _limpiar()


# ── el motor y la pantalla no se pueden contradecir ──────────────────────────

def test_un_lote_con_fecha_ilegible_NO_se_muestra_como_usable(app, db_clean):
    """Si el FEFO no lo va a consumir, la pantalla no puede decir "lote a usar": ésa es
    exactamente la contradicción que Sebastián vio (M5/M161)."""
    _limpiar()
    _sembrar_mp()
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "fecha_vencimiento, estado_lote) VALUES (?,?,?,'Entrada',?,?,?,'VIGENTE')",
         (_COD, 'MP DE PRUEBA FVISO', 5000, '2026-01-10', _LOTE, 'proximamente'))
    with app.app_context():
        from api.database import get_db
        from api.blueprints.programacion import _lotes_de_material
        res = _lotes_de_material(get_db().cursor(), _COD)
    usables = [x['lote'] for x in res['usables']]
    retenidos = dict((x['lote'], x.get('motivo', '')) for x in res['retenidos'])
    assert _LOTE not in usables, \
        "prometió como usable un lote que el FEFO no puede consumir (fecha ilegible)"
    assert _LOTE in retenidos, "el lote desapareció en vez de declararse"
    assert 'ilegible' in retenidos[_LOTE].lower(), \
        "no dice POR QUÉ no se puede usar: %r" % (retenidos[_LOTE],)
    _limpiar()


def test_con_la_fecha_en_ISO_el_lote_vuelve_a_contarse(app, db_clean):
    """El caso de Sebastián al derecho: 29 kg vigentes tienen que alcanzar para 4 kg."""
    _limpiar()
    _sembrar_mp()
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "fecha_vencimiento, estado_lote) VALUES (?,?,?,'Entrada',?,?,?,'VIGENTE')",
         (_COD, 'MP DE PRUEBA FVISO', 29137.5, '2026-01-10', _LOTE, '2027-12-26'))
    with app.app_context():
        from api.database import get_db
        from api.blueprints.programacion import (_lotes_de_material,
                                                 _validar_stock_para_produccion)
        cur = get_db().cursor()
        res = _lotes_de_material(cur, _COD)
        faltan = _validar_stock_para_produccion(
            cur, [{'codigo_mp': _COD, 'nombre': 'MP DE PRUEBA FVISO',
                   'cantidad_g': 4000}])
    assert _LOTE in [x['lote'] for x in res['usables']], "la pantalla no lo ve"
    assert not faltan, "el motor dice que falta con 29 kg vigentes en bodega: %r" % (faltan,)
    _limpiar()


def test_el_cron_de_vencidos_marca_lo_ISO_y_NO_puede_con_lo_ilegible(app, db_clean):
    """El otro lado del mismo bug, y el límite se DECLARA en vez de esconderse.

    `job_marcar_vencidos` compara `fecha_vencimiento < date('now','-5 hours')`, o sea texto
    contra texto. Con ISO marca bien. Con `26-Dic-2026` la comparación no puede funcionar, así
    que un lote vencido escrito así **se queda VIGENTE para siempre** y el control de
    vencimiento deja de sonar sin avisar (M127). Por eso el vigía diario de materias primas
    lleva la firma `fecha_vencimiento_que_el_motor_no_lee`: es lo único que lo hace visible.
    """
    _limpiar()
    _sembrar_mp()
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "fecha_vencimiento, estado_lote) VALUES (?,?,?,'Entrada',?,?,?,'VIGENTE')",
         (_COD, _NOM_MP, 100.0, '2026-01-10', 'FVISO-VENC-ISO', '2020-05-01'))
    _sql("INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, lote, "
         "fecha_vencimiento, estado_lote) VALUES (?,?,?,'Entrada',?,?,?,'VIGENTE')",
         (_COD, _NOM_MP, 100.0, '2026-01-10', 'FVISO-VENC-TXT', '01-May-2020'))
    try:
        from api.blueprints.auto_plan_jobs import job_marcar_vencidos
        job_marcar_vencidos(app)
        estados = dict(_sql("SELECT lote, UPPER(COALESCE(estado_lote,'')) FROM movimientos "
                            "WHERE material_id=?", (_COD,)))
        assert estados.get('FVISO-VENC-ISO') == 'VENCIDO',             "el cron no marcó un lote vencido con fecha ISO: %r" % (estados,)
        # El límite, dicho con todas las letras: el cron NO puede con la fecha en texto.
        assert estados.get('FVISO-VENC-TXT') == 'VIGENTE', (
            "si esto cambia, el cron aprendió a leer texto y hay que actualizar la nota "
            "-- pero mientras compare como texto, ese lote es invisible para el control")
        # Y lo que lo hace visible: el vigía diario lo reporta como GRAVE.
        with app.app_context():
            from api.database import get_db
            from api.blueprints.programacion import _salud_mp_core
            salud = _salud_mp_core(get_db().cursor())
        assert 'fecha_vencimiento_que_el_motor_no_lee' in salud['graves'],             "el vigía no vigila las fechas que el motor no lee"
        raros = [h for h in (salud['hallazgos'].get('fecha_vencimiento_que_el_motor_no_lee') or [])
                 if h.get('codigo') == _COD]
        assert raros, "el lote con la fecha en texto no aparece en el vigía"
    finally:
        _limpiar()


# ── la migración, probada con datos sembrados (M105) ─────────────────────────

def test_la_migracion_443_convierte_lo_inequivoco_y_deja_lo_ambiguo():
    import sys
    if 'api' not in sys.path:
        sys.path.insert(0, 'api')
    import database as D
    mig = [m for m in D.MIGRATIONS if m[0] == 443]
    assert mig, "la migración 443 no existe"
    conn = sqlite3.connect(':memory:')
    try:
        for t in ('movimientos', 'movimientos_mee'):
            conn.execute("CREATE TABLE %s (id INTEGER PRIMARY KEY, fecha_vencimiento TEXT)" % t)
        casos = [
            ('26-Dic-2026', '2026-12-26'),
            ('5-Dic-2025', '2025-12-05'),
            ('15-ENE-2027', '2027-01-15'),
            ('26/12/2026', '2026-12-26'),
            ('26-12-2026', '2026-12-26'),
            ('2026-12-26', '2026-12-26'),
            ('2026-12-26 00:00:00', '2026-12-26'),
            ('', ''),
            # Ambiguo: se deja como está y se reporta. Una fecha de vencimiento no se adivina.
            ('proximamente', 'proximamente'),
            ('26-Xyz-2026', '26-Xyz-2026'),
        ]
        for i, (v, _esp) in enumerate(casos):
            conn.execute("INSERT INTO movimientos VALUES (?,?)", (i, v))
            conn.execute("INSERT INTO movimientos_mee VALUES (?,?)", (i, v))
        for sql in mig[0][2]:
            conn.execute(sql)
        for i, (v, esperado) in enumerate(casos):
            for t in ('movimientos', 'movimientos_mee'):
                got = conn.execute(
                    "SELECT fecha_vencimiento FROM %s WHERE id=?" % t, (i,)).fetchone()[0]
                assert got == esperado, "%s: %r quedó %r (esperaba %r)" % (t, v, got, esperado)
    finally:
        conn.close()


# ── que ningún escritor nuevo nazca sin normalizar ───────────────────────────

def test_los_puntos_de_entrada_del_kardex_normalizan_la_fecha():
    """Barrido del FUENTE: una regla sin algo que la mida es una intención (M104/M106).

    Mide qué hace un endpoint con la fecha que le MANDAN: si la toma del request y la escribe
    tal cual, vuelve el bug. Se mide sobre el código sin comentarios ni docstrings, para que
    esta explicación no satisfaga el guard (M154).
    """
    import io as _io
    revisados = 0
    culpables = []
    patron = re.compile(
        r"^[^\n=]*\w\s*=[^\n]*\.get\(\s*'fecha_vencimiento[^']*'", re.M)
    for f in ('api/blueprints/inventario.py', 'api/blueprints/compras.py',
              'api/blueprints/calidad.py', 'api/blueprints/admin.py'):
        src = _io.open(f, encoding='utf-8').read()
        src = re.sub(r'"""(?:.|\n)*?"""', '', src)
        src = re.sub(r'^\s*#.*$', '', src, flags=re.M)
        # Quitar comentarios deja LÍNEAS VACÍAS, y una ventana de N líneas sobre huecos mide
        # el aire: se colapsan para que la vecindad sea de código real.
        src = re.sub(r'\n\s*\n+', '\n', src)
        for m in patron.finditer(src):
            fin = src.find('\n', m.start())
            linea = src[m.start():fin if fin > 0 else len(src)]
            # El vencimiento de una FACTURA de proveedor es otro dominio (cuentas por pagar):
            # no viaja al kardex, así que no entra a la medición. Se decide por la FUNCIÓN
            # contenedora, no por la línea: la línea de la factura no dice "factura".
            _defs = [d for d in re.finditer(r'^\s*def\s+(\w+)', src[:m.start()], re.M)]
            _fn = _defs[-1].group(1).lower() if _defs else ''
            # `fp_*` es el prefijo de facturas de proveedor (cuentas por pagar) en compras.py.
            if _fn.startswith('fp_') or 'factura' in _fn or 'factura' in linea.lower():
                continue
            revisados += 1
            # Se mira la línea Y las dos siguientes: un endpoint puede guardar el valor CRUDO
            # a propósito (para poder decir en el error qué fue lo que no se pudo leer) y
            # normalizar en el renglón de abajo. Lo que el guard exige es que la normalización
            # esté en la vecindad inmediata, no en la misma línea.
            _fin3 = src.find('\n', src.find('\n', fin + 1) + 1)
            ventana = src[m.start():_fin3 if _fin3 > 0 else len(src)]
            if 'fecha_iso' not in ventana:
                culpables.append('%s :: %s' % (f, linea.strip()[:90]))
    assert revisados >= 5, \
        "el barrido midió sólo %d puntos de entrada: dejó de medir sin avisar" % revisados
    assert not culpables, (
        "estos leen la fecha del request y la escriben sin normalizar:\n  "
        + "\n  ".join(culpables))
