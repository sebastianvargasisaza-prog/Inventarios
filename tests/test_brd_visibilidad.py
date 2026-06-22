"""Visibilidad del Batch Digital por USUARIO (brd._brd_visible + /api/admin/brd-visibilidad).

Sebastián 22-jun: poder dejar el batch digital visible SOLO para él mientras lo trabaja.
app_settings.brd_visible: '1'=todos · '0'/''=nadie · '<usuario>'=solo ese · 'admin'=admins.
El gate _gate_brd_pages muestra la página "en validación" a quien no puede verlo.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, f"login {user} -> {r.status_code}"
    return c


def _csrf(c):
    return {"X-CSRF-Token": c.get("/api/csrf-token").get_json()["csrf_token"]}


def _set_modo(c, modo):
    r = c.post("/api/admin/brd-visibilidad", json={"modo": modo}, headers=_csrf(c))
    assert r.status_code == 200, r.data
    return r.get_json()


def _oculto(resp):
    return "validaci" in resp.get_data(as_text=True).lower()


def test_solo_yo_solo_lo_ve_sebastian(app, db_clean):
    seb = _login(app, "sebastian")
    j = _set_modo(seb, "solo_yo")
    assert j["valor"] == "sebastian" and j["modo"] == "solo_usuario"
    # sebastián SÍ ve /brd (no es la página de "en validación")
    assert _oculto(seb.get("/brd")) is False
    # catalina NO lo ve (página oculta)
    cat = _login(app, "catalina")
    assert _oculto(cat.get("/brd")) is True


def test_oculto_para_todos(app, db_clean):
    seb = _login(app, "sebastian")
    _set_modo(seb, "oculto")
    assert _oculto(seb.get("/brd")) is True
    cat = _login(app, "catalina")
    assert _oculto(cat.get("/brd")) is True


def test_todos_lo_ven(app, db_clean):
    seb = _login(app, "sebastian")
    _set_modo(seb, "todos")
    cat = _login(app, "catalina")
    assert _oculto(cat.get("/brd")) is False


def test_set_requiere_admin(app, db_clean):
    cat = _login(app, "catalina")
    r = cat.post("/api/admin/brd-visibilidad", json={"modo": "solo_yo"}, headers=_csrf(cat))
    assert r.status_code in (401, 403)
