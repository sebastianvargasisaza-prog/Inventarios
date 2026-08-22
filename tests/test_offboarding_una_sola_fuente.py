# -*- coding: utf-8 -*-
"""Dar de baja a alguien lo saca de TODAS partes · 21-ago-2026.

El offboarding era sólo una migración que pone `users_passwords.activo=0`. Eso bloquea el login
-- que es lo que de verdad cierra la puerta -- pero la MATRIZ de permisos, que es la única
fuente de quién ve qué, seguía listando a la persona en los módulos que se derivan de *"todos
los que tienen login"*.

Dos fuentes diciendo cosas distintas de la misma persona: hoy gana la buena, y el día que
alguien reactive esa fila para "ver una cosa" recupera los módulos sin que nadie lo decida
(M211).
"""
import os
import sqlite3
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))

from .conftest import TEST_PASSWORD, csrf_headers


def test_quien_esta_desvinculado_no_figura_en_NINGUN_modulo(app, db_clean):
    """La matriz es la única fuente de quién ve qué: si sigue nombrando a alguien que se fue,
    describe un acceso que no debería existir."""
    import config as C
    assert C.USUARIOS_DESVINCULADOS, 'la lista existe pero está vacía: nadie la mantiene'
    for quien in C.USUARIOS_DESVINCULADOS:
        mods = sorted(m for m, u in C.MODULOS_ACCESO.items() if quien in u)
        assert not mods, '%s está desvinculado y la matriz le da: %r' % (quien, mods)

    # Hay DOS mecanismos y el de arriba sólo ejerce el primero: restar de `_TODOS` cubre los
    # módulos DERIVADOS, y el barrido final cubre los que alguien escribe A MANO. Sin el
    # barrido, agregar el nombre a un set explícito le devolvería el acceso en silencio -- así
    # que su existencia es parte de la invariante y se mide sobre el fuente (M227).
    import io as _io
    import os as _os
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    src = _io.open(_os.path.join(raiz, 'api', 'config.py'), encoding='utf-8').read()
    assert 'set(COMPRAS_USERS) - USUARIOS_DESVINCULADOS' in src,         'los módulos "para todos" volvieron a derivarse del diccionario entero'
    cuerpo = src[src.rindex('for _mod in MODULOS_ACCESO'):][:220]
    assert 'MODULOS_ACCESO[_mod] -= USUARIOS_DESVINCULADOS' in cuerpo,         ('falta el barrido final: un desvinculado escrito a mano en un set explícito '
         'conservaría el acceso')


def test_pero_sigue_RECONOCIBLE_en_sus_registros_historicos(app, db_clean):
    """No se borra del diccionario de usuarios: lleva registros regulados firmados y borrarlo
    los dejaría sin dueño (GMP conserva el rastro, no lo limpia)."""
    import config as C
    for quien in C.USUARIOS_DESVINCULADOS:
        assert quien in C.COMPRAS_USERS, \
            '%s se borró del diccionario: sus firmas quedan sin a quién atribuirlas' % quien


def test_por_cada_desvinculado_hay_una_MIGRACION_que_lo_bloquea(app, db_clean):
    """La invariante es sobre el CODIGO, no sobre los datos.

    `db_clean` vacia `users_passwords` a proposito, asi que mirar las filas mide la fixture y no
    produccion (M218). Un barrido del fuente no se contamina y caza mas: encuentra al que
    alguien agregue manana a la lista sin escribir su migracion (M227).

    Y el INSERT tiene que estar, no solo el UPDATE: quien existe unicamente en las variables de
    entorno no tiene fila que actualizar, asi que un `UPDATE ... SET activo=0` no hace nada y la
    persona sigue entrando por el respaldo del config.
    """
    import config as C
    import database as D
    sql_todo = '\n'.join(
        str(x) for m in D.MIGRATIONS for x in (m[2] if len(m) > 2 and m[2] else []))
    for quien in C.USUARIOS_DESVINCULADOS:
        marca = "'" + quien + "'"
        assert 'users_passwords' in sql_todo and marca in sql_todo, \
            ('%s esta en la lista de desvinculados y ninguna migracion lo bloquea: sacarlo de '
             'la matriz sin cerrar el login es cambiar un candado por un rotulo' % quien)
        bloque = [x for m in D.MIGRATIONS for x in (m[2] if len(m) > 2 and m[2] else [])
                  if marca in str(x) and 'users_passwords' in str(x)]
        texto = '\n'.join(str(x) for x in bloque)
        assert 'INSERT' in texto.upper(), \
            ('%s se bloquea solo con UPDATE: quien existe unicamente en el config no tiene fila '
             'que actualizar y seguiria entrando' % quien)
        assert 'activo=0' in texto.replace(' ', ''), \
            '%s: la migracion no deja su fila en activo=0' % quien


def test_el_mecanismo_del_bloqueo_FUNCIONA(app, db_clean):
    """Que la migracion exista no prueba que el bloqueo cierre. Se siembra la fila y se intenta
    entrar: es la medicion que vale (M211/M252)."""
    import config as C
    quien = sorted(C.USUARIOS_DESVINCULADOS)[0]
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cn.execute("INSERT OR IGNORE INTO users_passwords (username, password_hash, changed_by) "
                   "VALUES (?, '!DESACTIVADO', 'test')", (quien,))
        cn.execute("UPDATE users_passwords SET activo=0 WHERE username=?", (quien,))
        cn.commit()
    finally:
        cn.close()
    try:
        c = app.test_client()
        r = c.post("/login", data={"username": quien, "password": TEST_PASSWORD},
                   headers=csrf_headers(), follow_redirects=False)
        assert r.status_code != 302, \
            ('%s tiene su fila en activo=0 y el login lo dejo pasar: el bloqueo no cierra'
             % quien)
        # y el borde: alguien que SI trabaja aca entra igual
        r2 = app.test_client().post("/login",
                                    data={"username": "jose", "password": TEST_PASSWORD},
                                    headers=csrf_headers(), follow_redirects=False)
        assert r2.status_code == 302, 'el bloqueo se llevo puesto a quien si trabaja aca'
    finally:
        cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
        try:
            cn.execute("DELETE FROM users_passwords WHERE username=?", (quien,))
            cn.commit()
        finally:
            cn.close()


def test_y_NO_se_llevo_puesto_a_nadie_mas(app, db_clean):
    """Un barrido que resta de TODOS los módulos es fácil que saque de más: el borde son las
    personas que sí trabajan acá y usan esos mismos módulos."""
    import config as C
    for quien, mod in (('jose', 'planta'), ('milton', 'chat'), ('camilo', 'recepcion'),
                       ('catalina', 'compras'), ('miguel', 'aseguramiento'),
                       ('hernando', 'tecnica'), ('luz', 'espagiria')):
        assert quien in C.MODULOS_ACCESO[mod], \
            'el barrido le quitó %s a %s, que trabaja acá' % (mod, quien)
