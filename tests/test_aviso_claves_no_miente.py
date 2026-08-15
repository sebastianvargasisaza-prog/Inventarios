"""El aviso de contraseñas mira la base antes de afirmar (15-ago-2026).

Sebastián, sobre José y Milton: *"ellos sí tienen usuario y clave"*. Tenía razón, y el
defecto era del AVISO: miraba únicamente las env vars `PASS_<USER>` y desde ahí afirmaba
que esos usuarios **NO pueden entrar** — cuando el login resuelve PRIMERO por
`users_passwords` (quien cambió su clave o le hicieron reset desde la app tiene su hash
ahí y entra perfecto).

Un aviso de severidad HIGH que dice algo falso en CADA arranque es lo que enseña a
ignorar todos los avisos de arranque, que es el daño de fondo. Un chequeo que no puede
ver la mitad de la evidencia declara lo que midió, no dicta un veredicto (M100/M170).
"""
import os
import sqlite3

import pytest


def _sin_hash(username):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute("DELETE FROM users_passwords WHERE username=?", (username,))
        conn.commit()
    finally:
        conn.close()


def _con_hash(username, activo=1):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        conn.execute("DELETE FROM users_passwords WHERE username=?", (username,))
        conn.execute(
            "INSERT INTO users_passwords (username, password_hash, activo, changed_by) "
            "VALUES (?,?,?,'test')",
            (username, "pbkdf2:sha256:600000$x$" + "a" * 64, activo))
        conn.commit()
    finally:
        conn.close()


def _issues(monkeypatch, faltantes):
    """Corre la validación con `faltantes` sin clave en las env vars."""
    import config
    falsos = {u: "" for u in faltantes}
    reales = {k: v for k, v in config.COMPRAS_USERS.items() if k not in falsos}
    # a los demás se les pone un hash válido para que no ensucien el resultado
    for k in list(reales):
        reales[k] = "pbkdf2:sha256:600000$y$" + "b" * 64
    monkeypatch.setattr(config, "COMPRAS_USERS", dict(reales, **falsos), raising=True)
    return {i["code"]: i for i in config.validate_config()}


def test_quien_tiene_clave_en_la_base_no_se_reporta_como_bloqueado(app, db_clean,
                                                                   monkeypatch):
    """El caso de José y Milton: sin env var pero con clave en la base."""
    _con_hash("jose")
    codes = _issues(monkeypatch, ["jose"])
    assert "MISSING_USER_PASSWORD" not in codes, (
        "sigue diciendo que no puede entrar alguien que entra: %s"
        % codes.get("MISSING_USER_PASSWORD", {}).get("msg", ""))
    aviso = codes.get("USER_PASSWORD_SOLO_EN_BD")
    assert aviso, codes.keys()
    assert aviso["severity"] == "INFO", aviso["severity"]
    assert "jose" in aviso["msg"]


def test_quien_no_tiene_clave_en_ningun_lado_si_se_reporta(app, db_clean, monkeypatch):
    """El guard tiene que seguir mordiendo donde el problema es real."""
    _sin_hash("milton")
    codes = _issues(monkeypatch, ["milton"])
    aviso = codes.get("MISSING_USER_PASSWORD")
    assert aviso, "dejó de avisar del caso que sí existe: %s" % list(codes)
    assert aviso["severity"] == "HIGH", aviso["severity"]
    assert "milton" in aviso["msg"]
    assert "ningún lado" in aviso["msg"] or "ningun lado" in aviso["msg"], aviso["msg"]


def test_un_usuario_desactivado_no_cuenta_como_que_tiene_clave(app, db_clean, monkeypatch):
    """`activo=0` bloquea el login: contarlo como "tiene clave" taparía un offboarding."""
    _con_hash("milton", activo=0)
    codes = _issues(monkeypatch, ["milton"])
    assert "MISSING_USER_PASSWORD" in codes, (
        "un usuario desactivado se reportó como que puede entrar")


def test_si_no_se_puede_mirar_la_base_no_se_afirma_nada(app, db_clean, monkeypatch):
    """Distinguir "no tiene clave" de "no pude mirar" es todo el punto de este arreglo."""
    import config
    monkeypatch.setattr(config, "_usuarios_con_clave_en_bd", lambda: None, raising=True)
    codes = _issues(monkeypatch, ["jose", "milton"])
    assert "MISSING_USER_PASSWORD" not in codes, (
        "afirmó que no pueden entrar sin haber podido verificarlo")
    aviso = codes.get("USER_PASSWORD_NO_VERIFICABLE")
    assert aviso, codes.keys()
    assert aviso["severity"] == "INFO", aviso["severity"]
    assert "NO significa" in aviso["msg"], aviso["msg"]


def test_el_lector_de_la_base_no_importa_database(app, db_clean):
    """`database` importa `config`: importarlo desde acá cerraría el ciclo en el arranque."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "config.py")
    fuente = open(ruta, encoding="utf-8").read()
    i = fuente.find("def _usuarios_con_clave_en_bd(")
    assert i > 0, "no está el lector"
    bloque = fuente[i:i + 2200]
    assert "from database" not in bloque and "import database" not in bloque, (
        "config importa database: eso cierra el ciclo de imports en pleno arranque")
