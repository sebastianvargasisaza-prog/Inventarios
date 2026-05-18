"""Tests del traductor de placeholders SQLite -> PostgreSQL (Fase 1 migración).

Puro · sin base de datos. Verifica que translate_placeholders maneje bien
los casos peligrosos: `?` dentro de strings, `%` literales (LIKE), comillas
escapadas, y consultas sin parámetros.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from pg_compat import translate_placeholders as tr


def test_placeholder_simple():
    assert tr("SELECT * FROM t WHERE id=?") == "SELECT * FROM t WHERE id=%s"


def test_placeholder_multiple():
    assert tr("SELECT * FROM t WHERE a=? AND b=?") == \
        "SELECT * FROM t WHERE a=%s AND b=%s"


def test_sin_placeholders_no_cambia():
    assert tr("SELECT 1 FROM t") == "SELECT 1 FROM t"


def test_like_con_porcentaje_se_escapa():
    # Los % literales de un LIKE deben pasar a %% para psycopg.
    assert tr("WHERE nombre LIKE '%foo%'") == "WHERE nombre LIKE '%%foo%%'"


def test_like_con_porcentaje_y_parametro():
    assert tr("WHERE a LIKE ? AND b LIKE '%x%'") == \
        "WHERE a LIKE %s AND b LIKE '%%x%%'"


def test_interrogacion_dentro_de_string_no_se_toca():
    # Un ? dentro de un literal es texto, no un placeholder.
    assert tr("WHERE q = 'really?'") == "WHERE q = 'really?'"


def test_interrogacion_dentro_de_string_con_parametro_real():
    assert tr("WHERE q = 'hola?' AND id = ?") == \
        "WHERE q = 'hola?' AND id = %s"


def test_comilla_escapada_sql():
    # 'it''s' es un solo string con comilla escapada · el id=? sí es placeholder.
    assert tr("WHERE nota = 'it''s ok' AND id=?") == \
        "WHERE nota = 'it''s ok' AND id=%s"


def test_porcentaje_dentro_de_string_se_escapa():
    assert tr("WHERE x = '50%' AND id=?") == "WHERE x = '50%%' AND id=%s"


def test_combinado_realista():
    sql = ("INSERT INTO movimientos (material_id, observaciones) "
           "VALUES (?, 'Recepcion 100%') WHERE nombre LIKE ?")
    esperado = ("INSERT INTO movimientos (material_id, observaciones) "
                "VALUES (%s, 'Recepcion 100%%') WHERE nombre LIKE %s")
    assert tr(sql) == esperado


def test_idempotencia_no_aplica_doble():
    # Traducir dos veces NO debe ser igual a una (documenta que NO es
    # idempotente · se traduce exactamente una vez, en el cursor).
    una = tr("WHERE id=?")
    dos = tr(una)
    assert una == "WHERE id=%s"
    assert dos == "WHERE id=%%s"
