"""Hoja de decisión de INCI ambiguos (para Alejandro) · read-only.

Auditoría 25-jul: el resolver elegía entre MPs del MISMO INCI por STOCK, así que una fórmula
que pedía hialurónico 50 kD podía descontar el de 1500 kD. Eso ya se cerró (fail-safe: si los
grados difieren, no adivina). Este diagnóstico arma la hoja para decidir el mapeo real.

Lo que NO puede hacer: marcar como ambiguo un código simplemente duplicado (mismo material,
mismo grado). Eso el resolver sí lo unifica solo y no necesita decisión humana.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers

INCI = 'ZZINCI AMBIGUO TEST'


def _sql(*stmts):
    db = sqlite3.connect(os.environ['DB_PATH'], timeout=15)
    try:
        for s in stmts:
            db.execute(s)
        db.commit()
    finally:
        db.close()


def _limpiar():
    _sql("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'ZZAMB%'")


def test_exige_admin(logged_client):
    assert logged_client.get('/api/admin/inci-ambiguos').status_code == 403


def test_distingue_grado_distinto_de_codigo_duplicado(admin_client):
    _limpiar()
    _sql("INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) "
         "VALUES ('ZZAMB1','%s','Acido test (50 kD)','MP',1)" % INCI,
         "INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) "
         "VALUES ('ZZAMB2','%s','Acido test (1500 kD)','MP',1)" % INCI,
         # par duplicado SIN grado distinto → NO necesita decisión humana
         "INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) "
         "VALUES ('ZZAMB3','ZZINCI DUP TEST','Pantenol test','MP',1)",
         "INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,tipo_material,activo) "
         "VALUES ('ZZAMB4','ZZINCI DUP TEST','Pantenol test','MP',1)")
    try:
        r = admin_client.get('/api/admin/inci-ambiguos')
        assert r.status_code == 200, r.data[:300]
        d = r.get_json()
        g_amb = next((g for g in d['grupos'] if 'ZZINCI AMBIGUO' in g['inci_normalizado']), None)
        g_dup = next((g for g in d['grupos'] if 'ZZINCI DUP' in g['inci_normalizado']), None)
        assert g_amb is not None and g_amb['ambiguo_por_grado'] is True, g_amb
        assert {c['grado'] for c in g_amb['codigos']} == {'50 kD', '1500 kD'}, g_amb
        assert g_dup is not None and g_dup['ambiguo_por_grado'] is False, \
            'un código duplicado del MISMO material no exige decisión humana'
    finally:
        _limpiar()
