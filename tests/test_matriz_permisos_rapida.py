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
    # Y el escaneo FRÍO también tiene techo: si alguien vuelve a `ast.get_source_segment` el cache
    # tapa el problema en la 2ª carga, pero la 1ª (la de después de cada despliegue) se dispara a
    # 26 segundos y la pantalla no abre. Un guard que sólo mide el camino caliente no vería eso.
    with app.app_context():
        _limpiar_cache()
        t1 = time.time()
        permisos_matriz.construir()
        frio = (time.time() - t1) * 1000
    assert frio < 15000, 'el escaneo frío tardó %.0f ms (antes eran 32.000)' % frio
