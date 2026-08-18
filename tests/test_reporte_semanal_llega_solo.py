# -*- coding: utf-8 -*-
"""El reporte semanal llega SOLO · y nace apagado.

El reporte existía desde hace tiempo (`/api/reporte/semanal-ceo`) y su propio docstring decía
*"diseñado para enviar via email cada lunes 8am"*... y **no había ningún cron que lo mandara**:
la capacidad entera, y nadie que la disparara (M121). Es el criterio 4 de la spec de Gerencia:
*"el reporte semanal llega solo, sin que nadie lo ejecute"*.

Lo que estos guards fijan:

  · que el job EXISTA y esté agendado el lunes a las 7:00;
  · que **nazca apagado**: empieza a escribirle a Gerencia todas las semanas y eso no se
    activa de callado (M39 · interruptor reversible, default seguro);
  · que sin destinatarios lo DIGA en vez de darse por enviado -- un 'ok' mudo se ve igual que
    un reporte que llegó (M100);
  · y que esté en la lista de los que NO se reintentan cada 2 h: manda correo, y un reintento
    es un correo duplicado.
"""
import io
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _fuente():
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "auto_plan_jobs.py")
    return io.open(ruta, encoding="utf-8").read()


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def test_esta_agendado_el_lunes_a_las_7(app):
    from blueprints.auto_plan_jobs import JOBS_SCHEDULE
    fila = [j for j in JOBS_SCHEDULE if j[0] == "reporte_semanal_ceo"]
    assert fila, "el reporte semanal no está agendado: sigue sin llegar solo"
    _, hora, minuto, dias, _, callable_name = fila[0]
    assert (hora, minuto) == (7, 0), ("el reporte no sale a las 7:00", hora, minuto)
    assert dias == [0], ("el reporte no sale los LUNES", dias)
    import blueprints.auto_plan_jobs as J
    assert getattr(J, callable_name, None), (
        "el schedule apunta a %s y esa función no existe: el cron lo saltearía en silencio"
        % callable_name)


def test_manda_correo_asi_que_no_se_reintenta_cada_dos_horas(app):
    src = _fuente()
    i = src.find("_RETRY_24H_JOBS")
    assert i > 0
    bloque = src[i:i + 2000]
    assert "'reporte_semanal_ceo'" in bloque, (
        "el reporte no está en los jobs de reintento a 24 h: un fallo lo reintentaría cada 2 h "
        "y Gerencia recibiría el mismo correo varias veces")


def test_nace_apagado_y_no_manda_nada(app, db_clean):
    """Default seguro: construido, agendado, y sin escribirle a nadie hasta que lo prendan."""
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cn.execute("DELETE FROM app_settings WHERE clave='reporte_semanal_auto'")
        cn.commit()
    finally:
        cn.close()
    from blueprints.auto_plan_jobs import job_reporte_semanal_ceo
    ok, res, err = job_reporte_semanal_ceo(app)
    assert ok and not err, (ok, err)
    assert res.get("enviado") is False, ("mandó el reporte estando apagado", res)
    assert "apagado" in (res.get("motivo") or ""), res


def test_encendido_sin_destinatarios_lo_DICE(app, db_clean):
    """Un 'ok' mudo se ve igual que un reporte que llegó (M100)."""
    cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cn.execute("INSERT INTO app_settings (clave, valor) VALUES ('reporte_semanal_auto','1') "
                   "ON CONFLICT(clave) DO UPDATE SET valor='1'")
        cn.execute("DELETE FROM email_destinatarios_config")
        cn.commit()
    finally:
        cn.close()
    try:
        from blueprints.auto_plan_jobs import job_reporte_semanal_ceo
        ok, res, err = job_reporte_semanal_ceo(app)
        assert ok, err
        assert res.get("enviado") is False, res
        assert "destinatarios" in (res.get("motivo") or ""), (
            "no declara que no tenía a quién mandarlo", res)
    finally:
        cn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
        try:
            cn.execute("DELETE FROM app_settings WHERE clave='reporte_semanal_auto'")
            cn.commit()
        finally:
            cn.close()


def test_el_interruptor_existe_y_es_de_admin(app, db_clean):
    cli = _login(app)
    r = cli.get("/api/reporte/semanal-ceo/auto")
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert (r.get_json() or {}).get("activo") is False, "nace encendido"

    r = cli.put("/api/reporte/semanal-ceo/auto", json={"activo": True}, headers=_h())
    assert r.status_code == 200, r.get_data(as_text=True)[:200]
    assert (r.get_json() or {}).get("activo") is True

    # y se puede volver atrás: un interruptor que no apaga no es un interruptor
    r = cli.put("/api/reporte/semanal-ceo/auto", json={"activo": False}, headers=_h())
    assert (r.get_json() or {}).get("activo") is False
