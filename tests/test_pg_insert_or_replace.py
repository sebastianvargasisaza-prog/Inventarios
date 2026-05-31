"""Fix 30-may-2026 · INSERT OR REPLACE en Postgres debe usar la constraint
UNIQUE correcta como objetivo del ON CONFLICT, no siempre la PK.

Caso real: animus_shopify_orders (PK=id autoincrement + UNIQUE shopify_id).
El sync de Shopify chocaba con 'duplicate key' porque el rewrite apuntaba a
la PK (id, que no va en el INSERT) en vez de a shopify_id.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

import pg_adapter


def _cursor():
    return pg_adapter._Cursor.__new__(pg_adapter._Cursor)


def test_usa_unique_no_pk_cuando_pk_no_va_en_insert(monkeypatch):
    # PK = id (no va en el INSERT) · UNIQUE = shopify_id (sí va)
    monkeypatch.setattr(pg_adapter, "_unique_keysets",
                        lambda cur, t: [(True, ["id"]), (False, ["shopify_id"])])
    monkeypatch.setattr(pg_adapter, "_pk_columns", lambda cur, t: ["id"])
    cur = _cursor()
    cur._cur = None
    sql = ("INSERT OR REPLACE INTO animus_shopify_orders "
           "(shopify_id, nombre, total) VALUES (?,?,?)")
    out = cur._reescribir_insert_or_replace(sql)
    assert "ON CONFLICT (shopify_id)" in out, out
    assert "ON CONFLICT (id)" not in out, out
    assert "nombre=EXCLUDED.nombre" in out and "total=EXCLUDED.total" in out, out
    # shopify_id es la clave · no debe actualizarse
    assert "shopify_id=EXCLUDED.shopify_id" not in out, out


def test_prefiere_pk_si_esta_en_el_insert(monkeypatch):
    # animus_config: clave es PK y va en el INSERT → debe usarla (sin cambios)
    monkeypatch.setattr(pg_adapter, "_unique_keysets",
                        lambda cur, t: [(True, ["clave"]), (False, ["otra"])])
    monkeypatch.setattr(pg_adapter, "_pk_columns", lambda cur, t: ["clave"])
    cur = _cursor()
    cur._cur = None
    sql = "INSERT OR REPLACE INTO animus_config (clave, valor) VALUES (?,?)"
    out = cur._reescribir_insert_or_replace(sql)
    assert "ON CONFLICT (clave)" in out, out
    assert "valor=EXCLUDED.valor" in out, out


def test_fallback_a_pk_si_ninguna_unique_calza(monkeypatch):
    # Si ninguna constraint única tiene todas sus columnas en el INSERT,
    # cae a la PK (comportamiento previo, no rompe nada).
    monkeypatch.setattr(pg_adapter, "_unique_keysets", lambda cur, t: [])
    monkeypatch.setattr(pg_adapter, "_pk_columns", lambda cur, t: ["id"])
    cur = _cursor()
    cur._cur = None
    sql = "INSERT OR REPLACE INTO t (a, b) VALUES (?,?)"
    out = cur._reescribir_insert_or_replace(sql)
    assert "ON CONFLICT (id)" in out, out
