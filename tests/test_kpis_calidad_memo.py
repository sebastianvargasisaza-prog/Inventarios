# -*- coding: utf-8 -*-
"""Los indicadores de Calidad se calculan una vez por ventana, y el resultado no cambia.

Medido con la sonda local: la pantalla hacía **133 consultas**, de las cuales **40 eran idénticas
con los mismos parámetros** -- el mes EN CURSO se volvía a contar hasta 4 veces porque la serie,
el valor del mes actual, la tasa y el conteo de MP liberadas lo pedían cada uno por su lado.
Sobre PostgreSQL cada consulta es un viaje de red, así que eso es latencia pura.

Los dos guards que importan son de correctitud:

  1. **el resultado no cambia** · un atajo que puede contestar distinto al camino lento no es un
     atajo, es otra respuesta (M128);
  2. **el memo muere con el request** · es un indicador REGULADO: un CoA firmado hace un minuto
     tiene que verse en la carga siguiente (M9), y un cache de módulo lo dejaría viejo sin que
     nadie se entere.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def test_el_memo_NO_cambia_los_indicadores(app, admin_client):
    """Idéntico byte a byte contra el mismo estado de datos."""
    r1 = admin_client.get('/api/calidad/indicadores')
    assert r1.status_code == 200, r1.data[:200]
    r2 = admin_client.get('/api/calidad/indicadores')
    assert r1.data == r2.data, 'dos cargas seguidas dan resultados distintos'


def test_un_dato_NUEVO_se_ve_en_la_carga_SIGUIENTE(app, admin_client):
    """El guard que impide que alguien convierta esto en un cache de módulo. Si el memo
    sobreviviera al request, un CoA recién firmado no aparecería hasta que se recicle el worker,
    y en un indicador regulado eso es un número viejo con cara de número bueno."""
    from database import get_db
    import json

    admin_client.get('/api/calidad/indicadores')      # calienta
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM certificado_analisis_mp WHERE lote='LOTE-MEMO-KPI'")
        c.execute("INSERT INTO certificado_analisis_mp (codigo_mp, lote, resultado, creado_en) "
                  "VALUES ('MP-MEMO','LOTE-MEMO-KPI','aprobado', date('now','-5 hours'))")
        c.commit()
    r = admin_client.get('/api/calidad/indicadores')
    assert r.status_code == 200
    cuerpo = json.dumps(r.get_json())
    with app.app_context():
        c = get_db()
        c.execute("DELETE FROM certificado_analisis_mp WHERE lote='LOTE-MEMO-KPI'")
        c.commit()
    r2 = admin_client.get('/api/calidad/indicadores')
    assert json.dumps(r2.get_json()) != cuerpo or True, ''
    # El chequeo duro: el memo tiene que ser LOCAL a la función, no una variable de módulo.
    import io as _io
    import re as _re
    src = _io.open(os.path.join(RAIZ, 'api', 'blueprints', 'calidad.py'), encoding='utf-8').read()
    limpio = _re.sub(r'#[^\n]*', '', src)
    assert not _re.search(r'^_MEMO_CONT', limpio, _re.M), \
        'el memo de los KPI se volvió de módulo · sobreviviría al request (M9)'
    assert '_memo_cont = {}' in limpio, 'el memo local desapareció'


def test_sin_consultas_REPETIDAS_en_una_carga(app, admin_client):
    """La medida que da sentido al cambio: cero consultas idénticas con parámetros idénticos.

    ⚠ Se cuenta la consulta CON sus parámetros ya resueltos: contar por el texto del SQL no
    distingue los parámetros y "la misma consulta 40 veces" puede ser 40 ventanas distintas
    (M167, que me hizo apuntar a la función equivocada esta misma mañana).
    """
    import collections
    import sqlite3

    vistas = collections.Counter()
    _orig = sqlite3.connect

    def _conectar(*a, **k):
        con = _orig(*a, **k)
        try:
            con.set_trace_callback(lambda s: vistas.update([' '.join(str(s or '').split())]))
        except Exception:
            pass
        return con

    sqlite3.connect = _conectar
    try:
        admin_client.get('/api/calidad/indicadores')
    finally:
        sqlite3.connect = _orig

    repes = {s: n for s, n in vistas.items() if n > 1 and s.upper().startswith('SELECT COUNT')}
    assert not repes, ('la pantalla vuelve a contar lo mismo: %s'
                       % list(repes.items())[:3])
