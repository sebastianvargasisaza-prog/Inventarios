"""Tests de los helpers globales · audit_helpers + http_helpers."""
import math
import os
import sqlite3
import sys
import threading
from datetime import datetime

import pytest

# api/ debe estar en sys.path (igual que conftest)
_api_dir = os.path.join(os.path.dirname(__file__), '..', 'api')
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)


# ─── validate_money (http_helpers) ─────────────────────────────────────

def test_validate_money_acepta_positivo():
    from http_helpers import validate_money
    v, err = validate_money(100)
    assert err is None
    assert v == 100.0


def test_validate_money_rechaza_negativo():
    from http_helpers import validate_money
    v, err = validate_money(-50)
    assert v is None
    assert err['codigo'] == 'MONTO_INVALIDO'


def test_validate_money_rechaza_cero_default():
    from http_helpers import validate_money
    v, err = validate_money(0)
    assert v is None  # default allow_zero=False
    assert err['codigo'] == 'MONTO_INVALIDO'


def test_validate_money_acepta_cero_si_allow():
    from http_helpers import validate_money
    v, err = validate_money(0, allow_zero=True)
    assert err is None
    assert v == 0.0


def test_validate_money_rechaza_negativo_aun_con_allow_zero():
    from http_helpers import validate_money
    v, err = validate_money(-1, allow_zero=True)
    assert v is None
    assert err['codigo'] == 'MONTO_INVALIDO'


def test_validate_money_rechaza_nan():
    from http_helpers import validate_money
    v, err = validate_money(float('nan'))
    assert v is None
    assert 'NaN' in err['error']


def test_validate_money_rechaza_infinity():
    from http_helpers import validate_money
    v, err = validate_money(float('inf'))
    assert v is None
    assert 'Infinity' in err['error']


def test_validate_money_rechaza_no_numerico():
    from http_helpers import validate_money
    v, err = validate_money('abc')
    assert v is None
    assert err['codigo'] == 'MONTO_INVALIDO'


def test_validate_money_acepta_string_numerica():
    from http_helpers import validate_money
    v, err = validate_money('1500.50')
    assert err is None
    assert v == 1500.5


def test_validate_money_rechaza_excede_cap():
    from http_helpers import validate_money
    v, err = validate_money(2_000_000_000_000)  # 2B excede el cap 1B
    assert v is None
    assert err['codigo'] == 'MONTO_FUERA_DE_RANGO'


def test_validate_money_cap_personalizado():
    from http_helpers import validate_money
    v, err = validate_money(5000, max_value=1000)
    assert v is None
    assert err['codigo'] == 'MONTO_FUERA_DE_RANGO'


def test_validate_money_field_name_aparece_en_error():
    from http_helpers import validate_money
    v, err = validate_money(-1, field_name='precio_unitario')
    assert 'precio_unitario' in err['error']


# ─── audit_helpers · siguiente_codigo_secuencial ───────────────────────

def test_siguiente_codigo_primer_codigo(app, db_clean):
    """Sin desviaciones existentes con prefijo HELPRTEST → -0001."""
    from audit_helpers import siguiente_codigo_secuencial
    # Usar el conn del app context para garantizar que DB está inicializada
    with app.test_request_context('/'):
        from database import get_db
        c = get_db().cursor()
        c.execute("DELETE FROM desviaciones WHERE codigo LIKE 'HELPRTEST-%'")
        anio_actual = datetime.now().year
        cod = siguiente_codigo_secuencial(c, 'HELPRTEST', 'desviaciones', anio=anio_actual)
        assert cod.startswith('HELPRTEST-')
        assert cod.endswith('-0001')


def test_siguiente_codigo_incrementa(app, db_clean):
    """Con un código existente -0005 → siguiente es -0006."""
    from audit_helpers import siguiente_codigo_secuencial
    with app.test_request_context('/'):
        from database import get_db
        c = get_db().cursor()
        anio = 2099
        c.execute("""
            INSERT INTO desviaciones (codigo, fecha_deteccion, detectado_por, tipo,
                                         descripcion, estado)
            VALUES ('SEQTEST-2099-0005', '2099-01-01', 'sebastian', 'otra',
                    'Test secuencial', 'detectada')
        """)
        cod = siguiente_codigo_secuencial(c, 'SEQTEST', 'desviaciones', anio=anio)
        assert cod == 'SEQTEST-2099-0006'
        c.execute("DELETE FROM desviaciones WHERE codigo LIKE 'SEQTEST-2099-%'")


# ─── audit_helpers · intentar_insert_con_retry ─────────────────────────

def test_retry_exitoso_primer_intento():
    """Si insert_fn no falla, retorna en primer intento."""
    from audit_helpers import intentar_insert_con_retry
    calls = []
    def fn():
        calls.append(1)
        return ('CODE-001', 42)
    result = intentar_insert_con_retry(fn, max_intentos=3)
    assert result == ('CODE-001', 42)
    assert len(calls) == 1


def test_retry_reintentos_en_integrity_error():
    """Si IntegrityError sobre 'codigo' los primeros 2, reintenta y eventualmente OK."""
    from audit_helpers import intentar_insert_con_retry
    calls = []
    def fn():
        calls.append(1)
        if len(calls) < 3:
            raise sqlite3.IntegrityError('UNIQUE constraint failed: desviaciones.codigo')
        return ('CODE-003', 3)
    result = intentar_insert_con_retry(fn, max_intentos=5)
    assert result == ('CODE-003', 3)
    assert len(calls) == 3


def test_retry_max_intentos_propaga_error():
    """Si todos los intentos fallan, propaga la última excepción."""
    from audit_helpers import intentar_insert_con_retry
    def fn():
        raise sqlite3.IntegrityError('UNIQUE constraint failed: desviaciones.codigo')
    with pytest.raises(sqlite3.IntegrityError):
        intentar_insert_con_retry(fn, max_intentos=2)


def test_retry_no_reintenta_otros_errores():
    """IntegrityError sobre OTRA columna NO se reintenta."""
    from audit_helpers import intentar_insert_con_retry
    calls = []
    def fn():
        calls.append(1)
        raise sqlite3.IntegrityError('UNIQUE constraint failed: pagos_oc.numero_factura')
    with pytest.raises(sqlite3.IntegrityError):
        intentar_insert_con_retry(fn, max_intentos=5)
    assert len(calls) == 1  # NO retry


# ─── audit_helpers · audit_log ─────────────────────────────────────────

def test_audit_log_inserta_correctamente(app, db_clean):
    """audit_log inserta con todos los campos del schema."""
    from audit_helpers import audit_log
    from database import get_db
    with app.test_request_context('/api/test'):
        c = get_db().cursor()
        audit_log(c, usuario='sebastian', accion='TEST_HELPER',
                  tabla='test_table', registro_id='HELPER-TEST-001',
                  antes={'estado': 'a'}, despues={'estado': 'b'},
                  detalle='Test del helper')
        row = c.execute("""
            SELECT usuario, accion, tabla, registro_id, antes, despues
            FROM audit_log WHERE registro_id='HELPER-TEST-001'
        """).fetchone()
        c.execute("DELETE FROM audit_log WHERE registro_id='HELPER-TEST-001'")
        assert row is not None
        assert row[0] == 'sebastian'
        assert row[1] == 'TEST_HELPER'
        assert row[2] == 'test_table'
        assert '"estado": "a"' in (row[4] or '')
        assert '"estado": "b"' in (row[5] or '')
