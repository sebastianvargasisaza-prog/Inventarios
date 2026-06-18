"""Migración 275 · cobertura de planeación a 2 años.

Toda fórmula ACTIVA (lote>0) debe estar en sku_planeacion_config (para que la
proyección la cubra), y las entradas huérfanas (sin fórmula activa) deben quedar
desactivadas. Verificado contra la BD migrada fresca (init_db una sola vez).
"""
import os
import re
import sqlite3
import sys
import tempfile
import unicodedata

import pytest


def _nz(s):
    n = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]+', ' ', n).strip()


@pytest.fixture(scope="module")
def fresh_conn():
    os.environ['DB_PATH'] = os.path.join(tempfile.mkdtemp(prefix='m275t_'), 'fresh.db')
    os.environ.pop('EOS_DB_BACKEND', None)
    os.environ.pop('DATABASE_URL', None)
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)
    import database as dbmod
    dbmod.init_db()
    conn = sqlite3.connect(os.environ['DB_PATH'])
    yield conn
    conn.close()


def test_mig275_toda_formula_activa_esta_en_planeacion(fresh_conn):
    fa = set(_nz(r[0]) for r in fresh_conn.execute(
        "SELECT producto_nombre FROM formula_headers "
        "WHERE COALESCE(activo,1)=1 AND COALESCE(lote_size_kg,0)>0").fetchall())
    cfg = set(_nz(r[0]) for r in fresh_conn.execute(
        "SELECT producto_nombre FROM sku_planeacion_config "
        "WHERE COALESCE(activo,1)=1 AND COALESCE(estado,'activo') NOT IN ('descontinuado','pausado')").fetchall())
    sin_config = sorted(fa - cfg)
    assert sin_config == [], f"fórmulas activas sin programar: {sin_config}"


def test_mig275_los_6_quedaron_activos(fresh_conn):
    for p in ('BLUSH BALM', 'BOOSTER TENSOR', 'HYDRAPEPTIDE', 'HYDRA BALANCE',
              'LIP SERUM VOLUMINIZADOR PEPTIDOS', 'CREMA FACIAL UREA 10'):
        r = fresh_conn.execute("SELECT activo, estado FROM sku_planeacion_config "
                               "WHERE UPPER(TRIM(producto_nombre))=?", (p,)).fetchone()
        assert r is not None and r[0] == 1 and r[1] == 'activo', f"{p} no quedó activo: {r}"


def test_mig275_huerfanas_sin_formula_activa_desactivadas(fresh_conn):
    fa = set(_nz(r[0]) for r in fresh_conn.execute(
        "SELECT producto_nombre FROM formula_headers WHERE COALESCE(activo,1)=1").fetchall())
    activos_cfg = [r[0] for r in fresh_conn.execute(
        "SELECT producto_nombre FROM sku_planeacion_config "
        "WHERE COALESCE(activo,1)=1 AND COALESCE(estado,'activo') NOT IN ('descontinuado','pausado')").fetchall()]
    huerfanos = [p for p in activos_cfg if _nz(p) not in fa]
    assert huerfanos == [], f"config activas sin fórmula activa: {huerfanos}"
