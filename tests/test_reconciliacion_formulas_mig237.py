"""Migración 237 · reconciliación fórmulas vs maestro de Alejandro (Sebastián 12-jun).

Prueba con datos concretos que la migración:
  #1  re-apunta SOLO Propylheptyl/Sensoft de MP00137(Argán) → MP00030,
      y NO toca un uso legítimo de MP00137 como Argán (scope por material_nombre).
  #2  unifica Kakai MP00444 → MPCAKY01: re-apunta fórmulas, mueve el stock
      (movimientos re-keados + marcados) y archiva MP00444 (activo=0, no se borra).
  #3  agrega Myristoyl Nonapeptide-3 (MP00250) a Suero Exfoliante BHA y Booster Tensor.
  + idempotencia (correr dos veces no duplica ni rompe) y cero pérdida de stock.

Es un test de la SQL de la migración sobre un SQLite fresco con el trigger FK de
mig 98 replicado (para confirmar que respeta el enforcement).
"""
import os
import sys
import sqlite3


def _load_migrations():
    # Importa MIGRATIONS sin contaminar sys.path de forma permanente (si este
    # test corre primero bajo pytest-randomly, dejar api/ insertado podía
    # ensombrecer imports de otros tests · se restaura en finally).
    api_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "api")
    added = api_dir not in sys.path
    if added:
        sys.path.insert(0, api_dir)
    try:
        from database import MIGRATIONS
        return MIGRATIONS
    finally:
        if added:
            try:
                sys.path.remove(api_dir)
            except ValueError:
                pass


def _mig237_stmts():
    for ver, _desc, stmts in _load_migrations():
        if ver == 237:
            return stmts
    raise AssertionError("migración 237 no encontrada en MIGRATIONS")


def _fresh_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE maestro_mps (codigo_mp TEXT PRIMARY KEY, nombre_inci TEXT,
            nombre_comercial TEXT, tipo TEXT, proveedor TEXT,
            stock_minimo REAL DEFAULT 0, activo INTEGER DEFAULT 1);
        CREATE TABLE formula_items (id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_nombre TEXT, material_id TEXT, material_nombre TEXT, porcentaje REAL);
        CREATE TABLE movimientos (id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id TEXT, material_nombre TEXT, cantidad REAL, tipo TEXT,
            fecha TEXT, observaciones TEXT, lote TEXT, fecha_vencimiento TEXT);
    """)
    # Trigger FK de mig 98 (replicado): material_id debe existir activo en maestro.
    conn.executescript("""
        CREATE TRIGGER trg_fi_fk BEFORE INSERT ON formula_items FOR EACH ROW
        WHEN NEW.material_id IS NOT NULL AND TRIM(NEW.material_id) != ''
          AND NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp=NEW.material_id AND activo=1)
        BEGIN SELECT RAISE(ABORT,'FK insert'); END;
        CREATE TRIGGER trg_fi_fk_upd BEFORE UPDATE OF material_id ON formula_items FOR EACH ROW
        WHEN NEW.material_id IS NOT NULL AND TRIM(NEW.material_id) != ''
          AND NEW.material_id != OLD.material_id
          AND NOT EXISTS (SELECT 1 FROM maestro_mps WHERE codigo_mp=NEW.material_id AND activo=1)
        BEGIN SELECT RAISE(ABORT,'FK update'); END;
    """)
    return conn


def _seed(conn):
    # MP00137 = Argán (real, existe) · MP00444 = Kakai "sucio" (INCI vacío)
    conn.executescript("""
        INSERT INTO maestro_mps (codigo_mp,nombre_inci,nombre_comercial,activo) VALUES
          ('MP00137','ARGANIA SPINOSA KERNEL OIL','Beauty Oil Argan',1),
          ('MP00444',NULL,'Beauty oil Kakai',1);
    """)
    items = [
        # Emulsión Iluminadora: Sensoft + Propylheptyl mal en MP00137, + Argán LEGÍTIMO en MP00137
        ('EMULSION HIDRATANTE ILUMINADORA', 'MP00137', 'Beauty Sensoft', 3.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MP00137', 'PROPYLHEPTYL CAPRYLATE', 3.0),
        ('EMULSION HIDRATANTE ILUMINADORA', 'MP00137', 'Beauty Oil Argan', 5.0),  # NO tocar
        # Emulsión Limpiadora: Sensoft mal en MP00137
        ('EMULSION LIMPIADORA', 'MP00137', 'Beauty Sensoft', 4.5),
        # Kakai en MP00444 (dos productos)
        ('HYDRAPEPTIDE', 'MP00444', 'Aceite de cacay', 0.75),
        ('BLUSH BALM', 'MP00444', 'Beauty oil Kakai', 0.5),
        # Fórmulas sin Myristoyl (debe agregarse)
        ('Suero Exfoliante BHA 2%', 'MP00137', 'Beauty Oil Argan', 2.0),
        ('Booster Tensor', 'MP00137', 'Beauty Oil Argan', 1.0),
    ]
    conn.executemany(
        "INSERT INTO formula_items (producto_nombre,material_id,material_nombre,porcentaje) VALUES (?,?,?,?)",
        items)
    # Stock de Kakai en MP00444: 600 entrada - 70 salida = 530 neto
    conn.executemany(
        "INSERT INTO movimientos (material_id,material_nombre,cantidad,tipo,lote,observaciones) VALUES (?,?,?,?,?,?)",
        [('MP00444', 'Beauty oil Kakai', 600, 'Entrada', 'L-KAK-01', ''),
         ('MP00444', 'Beauty oil Kakai', -70, 'Salida',  'L-KAK-01', '')])
    conn.commit()


def _apply(conn):
    for stmt in _mig237_stmts():
        conn.execute(stmt)
    conn.commit()


def _mid(conn, producto, nombre_like):
    row = conn.execute(
        "SELECT material_id FROM formula_items WHERE producto_nombre=? "
        "AND UPPER(material_nombre) LIKE ?", (producto, nombre_like)).fetchone()
    return row[0] if row else None


def _stock(conn, codigo):
    return conn.execute(
        "SELECT COALESCE(SUM(cantidad),0) FROM movimientos WHERE material_id=?",
        (codigo,)).fetchone()[0]


def test_mig237_fix1_sensoft_propylheptyl_a_mp00030_y_no_toca_argan():
    conn = _fresh_db(); _seed(conn); _apply(conn)
    # Sensoft y Propylheptyl re-apuntados a MP00030 en ambas emulsiones
    assert _mid(conn, 'EMULSION HIDRATANTE ILUMINADORA', '%SENSOFT%') == 'MP00030'
    assert _mid(conn, 'EMULSION HIDRATANTE ILUMINADORA', '%PROPYLHEPTYL%') == 'MP00030'
    assert _mid(conn, 'EMULSION LIMPIADORA', '%SENSOFT%') == 'MP00030'
    # El Argán legítimo en MP00137 NO se tocó
    assert _mid(conn, 'EMULSION HIDRATANTE ILUMINADORA', '%ARGAN%') == 'MP00137'
    assert _mid(conn, 'Suero Exfoliante BHA 2%', '%ARGAN%') == 'MP00137'
    # MP00030 quedó activo con INCI correcto
    row = conn.execute("SELECT activo,nombre_inci FROM maestro_mps WHERE codigo_mp='MP00030'").fetchone()
    assert row and row[0] == 1 and row[1] == 'PROPYLHEPTYL CAPRYLATE'


def test_mig237_fix2_kakai_unifica_a_mpcaky01_mueve_stock_y_archiva():
    conn = _fresh_db(); _seed(conn); _apply(conn)
    # Fórmulas re-apuntadas
    assert _mid(conn, 'HYDRAPEPTIDE', '%CACAY%') == 'MPCAKY01'
    assert _mid(conn, 'BLUSH BALM', '%KAKAI%') == 'MPCAKY01'
    # Stock movido íntegro (530g) y nada quedó en MP00444
    assert _stock(conn, 'MP00444') == 0
    assert _stock(conn, 'MPCAKY01') == 530
    # Movimientos marcados con el origen (trazable/reversible)
    marcados = conn.execute(
        "SELECT COUNT(*) FROM movimientos WHERE material_id='MPCAKY01' "
        "AND observaciones LIKE '%mig237%'").fetchone()[0]
    assert marcados == 2
    # MP00444 archivado (no borrado) · MPCAKY01 activo con INCI CACAY OIL
    assert conn.execute("SELECT activo FROM maestro_mps WHERE codigo_mp='MP00444'").fetchone()[0] == 0
    row = conn.execute("SELECT activo,nombre_inci FROM maestro_mps WHERE codigo_mp='MPCAKY01'").fetchone()
    assert row and row[0] == 1 and row[1] == 'CACAY OIL'


def test_mig237_fix3_agrega_myristoyl_a_dos_formulas_con_pct_correcto():
    conn = _fresh_db(); _seed(conn); _apply(conn)
    bha = conn.execute("SELECT porcentaje FROM formula_items WHERE producto_nombre='Suero Exfoliante BHA 2%' "
                       "AND material_id='MP00250'").fetchone()
    bt = conn.execute("SELECT porcentaje FROM formula_items WHERE producto_nombre='Booster Tensor' "
                      "AND material_id='MP00250'").fetchone()
    assert bha and abs(bha[0] - 0.0015) < 1e-9
    assert bt and abs(bt[0] - 0.003) < 1e-9
    assert conn.execute("SELECT activo FROM maestro_mps WHERE codigo_mp='MP00250'").fetchone()[0] == 1


def test_mig237_idempotente_y_cero_perdida_de_stock():
    conn = _fresh_db(); _seed(conn)
    total_antes = conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos").fetchone()[0]
    _apply(conn)
    _apply(conn)  # segunda corrida: no debe duplicar ni romper
    # Myristoyl no se duplica
    for prod in ('Suero Exfoliante BHA 2%', 'Booster Tensor'):
        n = conn.execute("SELECT COUNT(*) FROM formula_items WHERE producto_nombre=? "
                         "AND material_id='MP00250'", (prod,)).fetchone()[0]
        assert n == 1, f"{prod} duplicó Myristoyl"
    # Stock global intacto (solo se re-keó, nada se perdió ni duplicó)
    total_despues = conn.execute("SELECT COALESCE(SUM(cantidad),0) FROM movimientos").fetchone()[0]
    assert abs(total_despues - total_antes) < 1e-9
