"""Sebastián 7-jul: las páginas admin nuevas (logo Espagiria, purgar GCal, producciones sin fórmula)
renderizan 200 (regresión del NameError get_db que no estaba en scope de módulo en admin.py)."""


def test_pagina_logo_espagiria_200(admin_client):
    r = admin_client.get("/admin/logo-espagiria")
    assert r.status_code == 200, r.status_code
    assert b"Logo de Espagiria" in r.data


def test_pagina_purgar_gcal_200(admin_client):
    r = admin_client.get("/admin/purgar-gcal")
    assert r.status_code == 200, r.status_code
    assert b"Google Calendar" in r.data


def test_pagina_producciones_sin_formula_200(admin_client):
    r = admin_client.get("/admin/producciones-sin-formula")
    assert r.status_code == 200, r.status_code
    assert b"sin f" in r.data  # "sin fórmula"


def test_purgar_gcal_post_ok(admin_client):
    r = admin_client.post("/api/admin/purgar-gcal", json={})
    assert r.status_code == 200, r.status_code
    assert r.get_json().get("ok") is True
