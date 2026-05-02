"""Tests del endpoint /api/planta/cronograma-areas + página /programacion-areas.

Cronograma estilo Alejandro · matriz 5 días Lun-Vie × 10 áreas.
"""
import os
import sqlite3

import pytest

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


# ─── Endpoint ────────────────────────────────────────────────────────

def test_cronograma_requires_auth(client, db_clean):
    r = client.get("/api/planta/cronograma-areas")
    assert r.status_code == 401


def test_cronograma_estructura(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/planta/cronograma-areas")
    assert r.status_code == 200
    d = r.get_json()
    assert "rango" in d
    assert "days" in d
    assert "areas" in d
    # 5 días Lun-Vie
    assert len(d["days"]) == 5
    # 10 áreas esperadas
    for area in ('fab1', 'fye2', 'fye3', 'env1', 'env2',
                 'micro', 'lib', 'acond', 'entr', 'limp'):
        assert area in d["areas"], f"falta área {area}"
        # cada área tiene 5 listas (una por día)
        assert len(d["areas"][area]) == 5


def test_cronograma_desde_invalido_400(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/api/planta/cronograma-areas?desde=foo")
    assert r.status_code == 400


def test_cronograma_proyecta_fab(app, db_clean):
    """Si hay producción programada en la semana, aparece en el área fab/fye."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    # Limpiar
    conn.execute("DELETE FROM produccion_programada WHERE producto LIKE 'PROD-CRON-%'")
    # Calcular lunes de esta semana
    from datetime import date, timedelta
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    martes = lunes + timedelta(days=1)
    # Buscar id de PROD1
    pr1 = conn.execute("SELECT id FROM areas_planta WHERE codigo='PROD1'").fetchone()
    pr1_id = pr1[0] if pr1 else None
    cur = conn.execute("""INSERT INTO produccion_programada
        (producto, fecha_programada, lotes, estado, area_id)
        VALUES ('PROD-CRON-T1', ?, 1, 'pendiente', ?)""", (martes.isoformat(), pr1_id))
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.get(f"/api/planta/cronograma-areas?desde={lunes.isoformat()}")
        d = r.get_json()
        # fab1 (PROD1) martes (idx 1) debe tener algo
        fab1_martes = d["areas"]["fab1"][1]
        labels = [chip["l"] for chip in fab1_martes]
        assert any("PROD-CRON-T1" in lbl for lbl in labels), \
               f"PROD-CRON-T1 no apareció en fab1 martes · {labels}"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()


def test_cronograma_proyecta_limpieza(app, db_clean):
    """Limpieza profunda agendada aparece en fila limp."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    from datetime import date, timedelta
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    miercoles = lunes + timedelta(days=2)
    # Limpiar antes
    conn.execute("DELETE FROM limpieza_profunda_calendario WHERE area_codigo='TEST-AREA'")
    conn.execute("""INSERT INTO limpieza_profunda_calendario
        (fecha, area_codigo, estado)
        VALUES (?, 'TEST-AREA', 'programada')""", (miercoles.isoformat(),))
    conn.commit(); conn.close()
    try:
        r = c.get(f"/api/planta/cronograma-areas?desde={lunes.isoformat()}")
        d = r.get_json()
        limp_mier = d["areas"]["limp"][2]
        labels = [chip["l"] for chip in limp_mier]
        assert any("TEST-AREA" in lbl for lbl in labels), \
               f"Limpieza no apareció · {labels}"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM limpieza_profunda_calendario WHERE area_codigo='TEST-AREA'")
        conn.commit(); conn.close()


def test_cronograma_proyecta_micro(app, db_clean):
    """Muestra micro en rango aparece en fila micro."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    from datetime import date, timedelta
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    jueves = lunes + timedelta(days=3)
    conn.execute("DELETE FROM calidad_micro_resultados WHERE producto_nombre='PROD-MICRO-T'")
    conn.execute("""INSERT INTO calidad_micro_resultados
        (lote, producto_nombre, fecha_muestreo, microorganismo, estado)
        VALUES ('LOTE-MIC-T', 'PROD-MICRO-T', ?, 'pendiente', 'ok')""",
        (jueves.isoformat(),))
    conn.commit(); conn.close()
    try:
        r = c.get(f"/api/planta/cronograma-areas?desde={lunes.isoformat()}")
        d = r.get_json()
        micro_jue = d["areas"]["micro"][3]
        labels = [chip["l"] for chip in micro_jue]
        assert any("PROD-MICRO-T" in lbl for lbl in labels)
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM calidad_micro_resultados WHERE producto_nombre='PROD-MICRO-T'")
        conn.commit(); conn.close()


def test_cronograma_proyecta_liberacion(app, db_clean):
    """Liberación con fecha_min_liberacion en rango aparece en fila lib."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    from datetime import date, timedelta
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    viernes = lunes + timedelta(days=4)
    conn.execute("DELETE FROM cola_liberacion WHERE producto_nombre='PROD-LIB-T'")
    conn.execute("""INSERT INTO cola_liberacion
        (envasado_id, producto_nombre, lote, unidades, fecha_envasado,
         fecha_min_liberacion, estado)
        VALUES (1, 'PROD-LIB-T', 'LOTE-LIB-T', 100, date('now','-7 days'),
                ?, 'esperando_micro')""", (viernes.isoformat(),))
    conn.commit(); conn.close()
    try:
        r = c.get(f"/api/planta/cronograma-areas?desde={lunes.isoformat()}")
        d = r.get_json()
        lib_vie = d["areas"]["lib"][4]
        labels = [chip["l"] for chip in lib_vie]
        assert any("PROD-LIB-T" in lbl for lbl in labels)
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM cola_liberacion WHERE producto_nombre='PROD-LIB-T'")
        conn.commit(); conn.close()


def test_cronograma_marca_urgente(app, db_clean):
    """Producción con observación 'urgente' debe marcarse u=true."""
    c = _login(app, "sebastian")
    conn = sqlite3.connect(os.environ["DB_PATH"])
    conn.execute("DELETE FROM produccion_programada WHERE producto='PROD-URG-T'")
    from datetime import date, timedelta
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    pr1 = conn.execute("SELECT id FROM areas_planta WHERE codigo='PROD1'").fetchone()
    pr1_id = pr1[0] if pr1 else None
    cur = conn.execute("""INSERT INTO produccion_programada
        (producto, fecha_programada, lotes, estado, area_id, observaciones)
        VALUES ('PROD-URG-T', ?, 1, 'pendiente', ?, '⚡ URGENTE · revisar')""",
        (lunes.isoformat(), pr1_id))
    pid = cur.lastrowid
    conn.commit(); conn.close()
    try:
        r = c.get(f"/api/planta/cronograma-areas?desde={lunes.isoformat()}")
        d = r.get_json()
        fab1_lun = d["areas"]["fab1"][0]
        urgentes = [chip for chip in fab1_lun
                     if "PROD-URG-T" in chip.get("l", "") and chip.get("u")]
        assert len(urgentes) >= 1, "Debería estar marcado urgente"
    finally:
        conn = sqlite3.connect(os.environ["DB_PATH"])
        conn.execute("DELETE FROM produccion_programada WHERE id=?", (pid,))
        conn.commit(); conn.close()


# ─── Página UI ───────────────────────────────────────────────────────

def test_pagina_programacion_areas_renderiza(app, db_clean):
    c = _login(app, "sebastian")
    r = c.get("/programacion-areas")
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    # Elementos clave
    assert "Programación por Área" in body
    assert "/api/planta/cronograma-areas" in body
    # Las 10 áreas en AREA_LABELS
    for label in ("FABRICACIÓN", "ENVASADO", "MICROBIOLOGÍA",
                  "LIBERACIÓN", "ACONDICIONAMIENTO", "ENTREGA",
                  "LIMPIEZA PROFUNDA"):
        assert label in body
    # Botones de navegación de semana
    assert "Semana ant" in body and "Semana sig" in body
    # Función JS
    assert "function cargarSemana" in body


def test_pagina_programacion_areas_requires_auth(client, db_clean):
    r = client.get("/programacion-areas", follow_redirects=False)
    assert r.status_code == 302
