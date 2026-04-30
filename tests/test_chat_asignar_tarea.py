"""Tests del endpoint /api/chat/threads/<id>/asignar-tarea — Sebastian (30-abr-2026).

Cubre el flujo completo:
1. Crear thread directo entre 2 usuarios
2. Asignar tarea desde el chat
3. Verificar que tareas_operativas tiene fila nueva
4. Verificar que chat_messages tiene mensaje tipo='tarea' linkeado
5. Verificar errores: sin auth, sin titulo, sin asignado, no-miembro
"""
import sqlite3
import os
import pytest

from .conftest import TEST_PASSWORD


def _login(client, username="sebastian"):
    r = client.post(
        "/login",
        data={"username": username, "password": TEST_PASSWORD},
        headers={"Origin": "http://localhost"},
        follow_redirects=False,
    )
    assert r.status_code == 302, r.get_data(as_text=True)


def _crear_thread_directo(client, otro_username="alejandro"):
    """Crea un thread 1-a-1 entre el user actual y otro. Devuelve thread_id."""
    r = client.post(
        "/api/chat/threads",
        json={"tipo": "directo", "miembros": [otro_username]},
        headers={"Origin": "http://localhost"},
    )
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    return r.get_json().get("id") or r.get_json().get("thread_id")


def test_asignar_tarea_sin_auth_devuelve_401(app, db_clean):
    client = app.test_client()
    r = client.post("/api/chat/threads/1/asignar-tarea",
                    json={"titulo": "x", "asignado_a": "alejandro"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 401


def test_asignar_tarea_sin_titulo_devuelve_400(app, db_clean):
    client = app.test_client()
    _login(client)
    thread_id = _crear_thread_directo(client)
    r = client.post(f"/api/chat/threads/{thread_id}/asignar-tarea",
                    json={"titulo": "", "asignado_a": "alejandro"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 400
    assert "titulo" in r.get_json().get("error", "").lower()


def test_asignar_tarea_sin_asignado_devuelve_400(app, db_clean):
    client = app.test_client()
    _login(client)
    thread_id = _crear_thread_directo(client)
    r = client.post(f"/api/chat/threads/{thread_id}/asignar-tarea",
                    json={"titulo": "Calibrar marmita", "asignado_a": ""},
                    headers={"Origin": "http://localhost"})
    assert r.status_code == 400
    assert "asignado" in r.get_json().get("error", "").lower()


def test_asignar_tarea_no_miembro_del_thread_devuelve_403(app, db_clean):
    """Un usuario que NO está en el thread no puede asignar tareas en él."""
    client_owner = app.test_client()
    _login(client_owner, "sebastian")
    thread_id = _crear_thread_directo(client_owner, otro_username="alejandro")

    # Otro user (mayra) que NO está en el thread intenta asignar
    client_otro = app.test_client()
    _login(client_otro, "mayra")
    r = client_otro.post(f"/api/chat/threads/{thread_id}/asignar-tarea",
                         json={"titulo": "Inyectar tarea", "asignado_a": "sebastian"},
                         headers={"Origin": "http://localhost"})
    assert r.status_code == 403


def test_asignar_tarea_flujo_completo_crea_tarea_y_mensaje(app, db_clean):
    """Asignar tarea inserta fila en tareas_operativas + mensaje tipo='tarea'."""
    client = app.test_client()
    _login(client, "sebastian")
    thread_id = _crear_thread_directo(client, "alejandro")

    titulo = "Calibrar balanza analítica BAL-003"
    descripcion = "Calibración trimestral con pesa patrón clase E2."
    fecha_obj = "2026-05-15"

    r = client.post(f"/api/chat/threads/{thread_id}/asignar-tarea",
                    json={"titulo": titulo, "descripcion": descripcion,
                          "asignado_a": "alejandro", "fecha_objetivo": fecha_obj},
                    headers={"Origin": "http://localhost"})
    assert r.status_code in (200, 201), r.get_data(as_text=True)

    # Verificar tarea_operativa creada
    db_path = os.environ["DB_PATH"]
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    tarea = con.execute(
        "SELECT * FROM tareas_operativas WHERE titulo=? ORDER BY id DESC LIMIT 1",
        (titulo,)
    ).fetchone()
    assert tarea is not None
    assert tarea["asignado_a"] == "alejandro"
    assert tarea["fecha_objetivo"] == fecha_obj
    assert tarea["origen_tipo"] == "chat"
    assert tarea["origen_id"] == thread_id
    assert tarea["creado_por"] == "sebastian"
    assert tarea["estado"] == "pendiente"

    # Verificar mensaje en chat_messages tipo='tarea' linkeado
    msg = con.execute(
        "SELECT * FROM chat_messages WHERE thread_id=? AND tipo_mensaje='tarea' "
        "ORDER BY id DESC LIMIT 1", (thread_id,)
    ).fetchone()
    assert msg is not None
    assert msg["tarea_operativa_id"] == tarea["id"]
    assert "📋" in msg["contenido"]
    assert titulo in msg["contenido"]
    con.close()


def test_asignar_tarea_actualiza_thread_preview(app, db_clean):
    """Al asignar tarea, el thread se actualiza con preview '[tarea] <titulo>'."""
    client = app.test_client()
    _login(client, "sebastian")
    thread_id = _crear_thread_directo(client, "alejandro")

    r = client.post(f"/api/chat/threads/{thread_id}/asignar-tarea",
                    json={"titulo": "Revisar lote COS-2026-04-12",
                          "asignado_a": "alejandro"},
                    headers={"Origin": "http://localhost"})
    assert r.status_code in (200, 201)

    db_path = os.environ["DB_PATH"]
    con = sqlite3.connect(db_path)
    row = con.execute(
        "SELECT ultimo_mensaje_preview FROM chat_threads WHERE id=?",
        (thread_id,)
    ).fetchone()
    con.close()
    assert row is not None
    assert row[0].startswith("[tarea]")
    assert "Revisar lote" in row[0]


def test_widget_js_se_sirve_a_usuario_logueado(app, db_clean):
    """El widget JS debe servirse correctamente — sin esto, FAB no aparece."""
    client = app.test_client()
    _login(client)
    r = client.get("/api/chat/widget.js")
    assert r.status_code == 200
    assert "javascript" in r.headers.get("Content-Type", "").lower()
    body = r.get_data(as_text=True)
    # Debe contener el FAB y el badge
    assert "cw-fab" in body
    assert "cw-badge" in body
    # Sebastian (30-abr-2026): widget ahora abre /chat en pestaña nueva
    # (sin iframe). Verificamos que la nueva implementación está activa.
    assert "_blank" in body
    # Anchor (no iframe) — el widget nuevo NO crea elementos iframe.
    assert "createElement('iframe'" not in body
    assert "createElement(\"iframe\"" not in body


def test_widget_js_no_auth_devuelve_401(app, db_clean):
    """Sin auth, el widget devuelve 401 (middleware require_auth_for_api).

    En producción esto NO es problema porque el widget solo se inyecta
    en páginas que requieren login (anonymous nunca verán el <script> tag).
    """
    client = app.test_client()
    r = client.get("/api/chat/widget.js")
    assert r.status_code == 401
