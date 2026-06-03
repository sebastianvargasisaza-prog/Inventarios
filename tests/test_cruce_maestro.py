"""Cruce Maestro · Excel (CÓD. BATCH canónico) ↔ maestro/fórmulas/inventario.

Cubre: reporte read-only detecta INCI vacío / código fuera de fórmula, y
?aplicar=inci rellena el INCI vacío del maestro desde el Excel (sin sobrescribir).
"""
import io
import os
import sqlite3
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data
    return c


def _excel_maestro(rows, producto="PROD CRUCE T1"):
    """Construye un Excel maestro de 1 hoja: header en fila 4, MPs debajo.
    rows = [(inci, comercial, cod, pct), ...]"""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = producto
    ws.cell(row=1, column=1, value=producto)
    ws.cell(row=4, column=1, value="#")
    ws.cell(row=4, column=2, value="NOMBRE INCI")
    ws.cell(row=4, column=3, value="NOMBRE COMERCIAL")
    ws.cell(row=4, column=4, value="CÓD. BATCH")
    ws.cell(row=4, column=5, value="% FÓRMULA")
    for i, (inci, com, cod, pct) in enumerate(rows, start=1):
        r = 4 + i
        ws.cell(row=r, column=1, value=i)
        ws.cell(row=r, column=2, value=inci)
        ws.cell(row=r, column=3, value=com)
        ws.cell(row=r, column=4, value=cod)
        ws.cell(row=r, column=5, value=pct)
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


def test_cruce_maestro_reporte_y_backfill_inci(app, db_clean):
    c = _login(app)
    # maestro: una MP con INCI vacío (se debe rellenar), otra con INCI ok
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, tipo_material, activo) "
                 "VALUES ('MP-CR-A', '', 'MP', 1)")  # INCI vacío
    conn.execute("INSERT OR REPLACE INTO maestro_mps (codigo_mp, nombre_inci, tipo_material, activo) "
                 "VALUES ('MP-CR-B', 'Glycerin', 'MP', 1)")
    conn.commit(); conn.close()

    xls = _excel_maestro([
        ("BORON NITRIDE", "Boron nitride", "MP-CR-A", 0.02),
        ("GLYCERIN", "Glicerina", "MP-CR-B", 5.0),
    ], producto="PROD CRUCE T1")

    # 1) read-only: detecta INCI_VACIO en MP-CR-A
    r = c.post("/api/admin/cruce-maestro",
               data={"file": (io.BytesIO(xls), "m.xlsx")},
               headers=csrf_headers(),
               content_type="multipart/form-data")
    assert r.status_code == 200, r.data
    d = r.get_json()
    assert d["resumen"]["inci_vacio"] >= 1, d["resumen"]
    assert d["aplicado"] is False
    # INCI no se tocó aún
    conn = sqlite3.connect(os.environ["DB_PATH"])
    inci_a = conn.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp='MP-CR-A'").fetchone()[0]
    conn.close()
    assert (inci_a or "") == "", "read-only no debe modificar"

    # 2) aplicar=inci: rellena el vacío desde el Excel, NO toca el que ya tenía
    r2 = c.post("/api/admin/cruce-maestro?aplicar=inci",
                data={"file": (io.BytesIO(xls), "m.xlsx")},
                headers=csrf_headers(),
                content_type="multipart/form-data")
    assert r2.status_code == 200, r2.data
    assert r2.get_json()["aplicado"] is True
    assert r2.get_json()["resumen"]["inci_rellenados"] >= 1, r2.get_json()["resumen"]
    conn = sqlite3.connect(os.environ["DB_PATH"])
    a2 = conn.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp='MP-CR-A'").fetchone()[0]
    b2 = conn.execute("SELECT nombre_inci FROM maestro_mps WHERE codigo_mp='MP-CR-B'").fetchone()[0]
    conn.close()
    assert a2 == "BORON NITRIDE", f"INCI debe rellenarse · {a2}"
    assert b2 == "Glycerin", "INCI existente no debe sobrescribirse"


def test_cruce_maestro_requiere_admin(app, db_clean):
    c = _login(app, "jefferson")  # marketing, no admin
    xls = _excel_maestro([("X", "x", "MP-CR-Z", 1.0)])
    r = c.post("/api/admin/cruce-maestro",
               data={"file": (io.BytesIO(xls), "m.xlsx")},
               headers=csrf_headers(),
               content_type="multipart/form-data")
    assert r.status_code in (401, 403), r.data
