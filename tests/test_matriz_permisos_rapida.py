# -*- coding: utf-8 -*-
"""La matriz de permisos tiene que ABRIR, y no puede quedar vieja.

Sebastián (8-ago): *"la matriz de permisos se queda cargando y no abre"*. Medido: el endpoint
tardaba **26 segundos**, y en producción eso se come uno de los tres workers y pasa del timeout,
así que la pantalla no abría nunca (M43).

De esos 26 segundos, **23 se iban en `ast.get_source_segment`**, que vuelve a partir en líneas el
archivo ENTERO en cada llamada; acá se llama una vez por ruta, o sea ~700 pasadas sobre el 1,5 MB
de `admin.py`. Se parten las líneas una vez por archivo y se corta por número de línea.

El resto se cachea, pero **sólo la mitad que sale del CÓDIGO**: el código no puede cambiar dentro
de un proceso vivo (un despliegue reinicia los workers) y la firma de los archivos lo verifica. La
otra mitad -- quién tiene la cuenta bloqueada -- sale de la base y se relee en cada carga: si se
cacheara, la pantalla mostraría con permisos a alguien que ya se fue, que es exactamente la
objeción que uno no quiere en una auditoría (M9).
"""
import json
import os
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def _limpiar_cache():
    import permisos_matriz
    permisos_matriz._CACHE_ESCANEO['firma'] = None
    permisos_matriz._CACHE_ESCANEO['rutas'] = None


def test_la_matriz_es_LA_MISMA_con_el_cache_y_sin_el(app):
    """Un atajo que puede contestar distinto no es un atajo (M128)."""
    import permisos_matriz
    with app.app_context():
        _limpiar_cache()
        fria = json.dumps(permisos_matriz.construir(), sort_keys=True, default=str)
        caliente = json.dumps(permisos_matriz.construir(), sort_keys=True, default=str)
        _limpiar_cache()
        otra_fria = json.dumps(permisos_matriz.construir(), sort_keys=True, default=str)
    assert fria == caliente, 'el cache cambia la matriz'
    assert fria == otra_fria, 'la matriz no es estable entre reconstrucciones'


def test_un_usuario_DESACTIVADO_se_ve_aunque_el_cache_este_caliente(app):
    """La parte que sale de la BASE no se cachea. Si se cacheara, la matriz mostraría con permisos
    a alguien que ya se fue."""
    from database import get_db
    import permisos_matriz
    with app.app_context():
        permisos_matriz.construir()             # deja el cache caliente
        c = get_db()
        fila = c.execute("SELECT username FROM users_passwords WHERE COALESCE(activo,1)=1 "
                         " LIMIT 1").fetchone()
        if not fila:
            return                              # sin usuarios en la BD de pruebas, nada que medir
        quien = (fila[0] or '').strip()
        antes = permisos_matriz.construir()
        activo_antes = (antes['por_usuario'].get(quien.lower(), {}) or {}).get('cuenta_activa')
        c.execute("UPDATE users_passwords SET activo=0 WHERE username=?", (quien,))
        c.commit()
        try:
            despues = permisos_matriz.construir()
            assert quien.lower() in despues['usuarios_desactivados'], \
                'con el cache caliente, la matriz NO vio la baja de %s' % quien
            if activo_antes is not None:
                assert (despues['por_usuario'].get(quien.lower(), {}) or {}) \
                    .get('cuenta_activa') is False
        finally:
            c.execute("UPDATE users_passwords SET activo=1 WHERE username=?", (quien,))
            c.commit()


def test_si_CAMBIA_un_archivo_de_codigo_el_cache_se_descarta(app):
    """La firma lleva tamaño y fecha de cada fuente: tocar una obliga a re-escanear. Sin esto, un
    cache de módulo podría quedar viejo sin que nadie lo note."""
    import permisos_matriz
    with app.app_context():
        permisos_matriz.construir()
        firma1 = permisos_matriz._CACHE_ESCANEO['firma']
        assert firma1, 'no se guardó la firma'
        ruta = os.path.join(RAIZ, 'api', 'blueprints', 'core.py')
        st = os.stat(ruta)
        os.utime(ruta, (st.st_atime, st.st_mtime + 60))
        try:
            assert permisos_matriz._firma_fuentes() != firma1, \
                'tocar un archivo NO cambió la firma: el cache podría quedar viejo'
            permisos_matriz.construir()
            assert permisos_matriz._CACHE_ESCANEO['firma'] != firma1, 're-escaneó pero no re-selló'
        finally:
            os.utime(ruta, (st.st_atime, st.st_mtime))


def test_la_pantalla_ABRE_en_un_tiempo_razonable(app, admin_client):
    """El trinquete de los 26 segundos. La primera carga paga el escaneo; las siguientes no."""
    import permisos_matriz
    with app.app_context():
        permisos_matriz.construir()             # simula el proceso ya tibio
    t0 = time.time()
    r = admin_client.get('/api/admin/matriz-permisos')
    ms = (time.time() - t0) * 1000
    assert r.status_code == 200, r.data[:200]
    assert ms < 3000, 'la matriz tardó %.0f ms con el proceso tibio (antes eran 26.000)' % ms
    # ⚠ El camino FRÍO no se mide con el reloj. Si alguien vuelve a `ast.get_source_segment`, el
    # cache tapa el problema en la 2ª carga y sólo se dispara la 1ª -- la de después de cada
    # despliegue -- así que hay que vigilarlo; pero un techo en milisegundos depende de cuánto más
    # esté corriendo la máquina: este mismo guard midió 6.800 ms en reposo y 19.800 ms con el gate
    # cargado, y tumbó el push por un rojo que no hablaba del código (M133).
    #
    # Lo que sí es independiente de la máquina: que la 2ª carga aproveche el escaneo de la 1ª.
    with app.app_context():
        _limpiar_cache()
        t1 = time.time()
        permisos_matriz.construir()
        frio = (time.time() - t1) * 1000
    assert ms * 10 < frio, \
        'la 2ª carga no aprovecha el escaneo (fría %.0f ms · tibia %.0f ms)' % (frio, ms)


def test_la_matriz_no_vuelve_a_PARTIR_el_archivo_en_cada_ruta(app):
    """La invariante de los 23 segundos, medida sin reloj.

    `ast.get_source_segment` vuelve a partir en líneas el archivo ENTERO en cada llamada; acá se
    llama una vez por ruta y `admin.py` tiene ~700, o sea 700 pasadas sobre 1,5 MB. Se corta por
    número de línea, sobre las líneas partidas una sola vez por archivo.

    Es la misma vigilancia que el techo de milisegundos, pero sobre un hecho del código: no puede
    dar rojo porque la máquina esté ocupada.
    """
    import io as _io
    ruta = os.path.join(RAIZ, 'api', 'permisos_matriz.py')
    src = _io.open(ruta, encoding='utf-8').read()
    # Sin comentarios: si no, al test lo satisface la explicación de por qué ya NO se usa, que es
    # justo la trampa en la que caí dos veces (M154).
    codigo = '\n'.join(l.split('#')[0] for l in src.splitlines())
    assert 'get_source_segment' not in codigo, \
        'volvió a ast.get_source_segment: es cuadrático y la pantalla deja de abrir'
    assert 'splitlines()' in codigo, 'ya no parte las líneas una sola vez por archivo'
