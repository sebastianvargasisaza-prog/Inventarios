"""Plan de suplencias · quién puede cubrir el puesto de quién, y hasta cuándo.

Sebastián 20-ago-2026, sobre los roles del batch record: *"son backup, como reemplazos: en caso
de que no estén, ellos pueden hacerlo"* · *"lo puede hacer sólo por plan de suplencias"*.

Lo que estos guards fijan:
  · el CARGO no cambia por una suplencia (el Director Técnico sigue siendo el DT);
  · una suplencia DECLARADA no habilita nada -- declarar no es otorgar;
  · sin fecha de fin no habilita, y al vencer se apaga sola;
  · quien cubre un puesto ve la pantalla donde ese puesto firma;
  · y la regla de las dos personas NO se relaja: el guard es por REGISTRO.
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, "no se pudo entrar como %s: %s" % (user, r.data[:200])
    return c


def _exec(sql, params=()):
    conn = sqlite3.connect(os.environ["DB_PATH"], timeout=10.0)
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _limpiar():
    """Limpiar ANTES de sembrar (M103): un finally no corre si el proceso muere."""
    _exec("UPDATE plan_suplencias SET activo=0, desde='', hasta='', titular='', motivo=''")


def _suplencia(suplente, rol, desde, hasta, activo=1, titular='yuliel'):
    _limpiar()
    _exec("UPDATE plan_suplencias SET titular=?, motivo=?, desde=?, hasta=?, activo=? "
          "WHERE LOWER(suplente)=? AND LOWER(rol)=?",
          (titular, 'licencia', desde, hasta, activo, suplente, rol))


def _hoy():
    from datetime import timedelta
    from api.tz_colombia import hoy_colombia
    h = hoy_colombia()
    return h, (h - timedelta(days=30)).isoformat(), (h + timedelta(days=30)).isoformat()


def test_el_cargo_no_cambia_por_una_suplencia(app, db_clean):
    """Quien cubre a Control de Calidad durante una ausencia sigue siendo el Director
    Técnico, y el registro tiene que decir eso."""
    from datetime import timedelta
    with app.app_context():
        from blueprints.brd import _batch_role_info
        _, ayer, en30 = _hoy()
        _suplencia('hernando', 'calidad', ayer, en30)
        info = _batch_role_info('hernando')
        assert info['tipo'] == 'director_tecnico', info
        assert info['rol'] == 'Director Técnico', info
        assert 'calidad' in info['suple'], "no tomó la suplencia vigente"
        # Y suma lo del puesto que cubre.
        assert info['verifica'] is True, "no puede verificar cubriendo a Calidad"
        assert info['puede_ejecutar'] is True
        # Lo suyo no se pierde.
        assert info['aprueba_dt'] is True, "perdió su propio acto (la liberación)"
        _limpiar()


def test_declarada_no_habilita(app, db_clean):
    """El plan nace declarado: dice quién PUEDE cubrir, y no otorga nada hasta que alguien
    registre la ausencia concreta con su vigencia."""
    with app.app_context():
        from blueprints.brd import _batch_role_info
        _limpiar()                      # activo=0, sin fechas = como nace el plan
        info = _batch_role_info('hernando')
        assert info['suple'] == [], "una suplencia declarada habilitó sin activarse"
        assert info['verifica'] is False, "el DT verifica sin suplencia activa"


def test_sin_fecha_de_fin_y_vencida_no_habilitan(app, db_clean):
    """Sin `hasta` no es una suplencia, es un permiso permanente. Y al vencer se apaga sola."""
    from datetime import timedelta
    with app.app_context():
        from blueprints.brd import _batch_role_info
        hoy, ayer, _en30 = _hoy()
        # activa pero SIN fecha de fin
        _suplencia('miguel', 'calidad', ayer, '')
        assert _batch_role_info('miguel')['suple'] == [], "habilitó sin fecha de fin"
        # activa y VENCIDA
        _suplencia('miguel', 'calidad', (hoy - timedelta(days=60)).isoformat(),
                   (hoy - timedelta(days=1)).isoformat())
        assert _batch_role_info('miguel')['suple'] == [], "una suplencia vencida siguió habilitando"
        # y todavía no empezada
        _suplencia('miguel', 'calidad', (hoy + timedelta(days=5)).isoformat(),
                   (hoy + timedelta(days=40)).isoformat())
        assert _batch_role_info('miguel')['suple'] == [], "habilitó antes de la fecha de inicio"
        _limpiar()


def test_el_jefe_de_produccion_no_lleva_suplencia(app, db_clean):
    """Decisión de Sebastián el 20-ago. Y sigue sin poder dar la 2ª firma de lo que ejecuta
    su propia área (PRD-PRO-001)."""
    with app.app_context():
        from blueprints.brd import _batch_role_info
        _limpiar()
        jefe = _batch_role_info('jose')
        assert jefe['tipo'] == 'jefe_produccion', jefe
        assert jefe['suple'] == [], "el jefe de producción quedó con suplencias"
        assert jefe['realiza'] is True, "tiene que poder EJECUTAR"
        assert jefe['verifica'] is False, "no puede verificar lo que ejecuta su área"


def test_quien_cubre_un_puesto_ve_su_pantalla(app, db_clean):
    """Un permiso de firma sin la pantalla donde se firma no sirve de nada (M121).

    Cada `app_context` es un request distinto A PROPÓSITO: el resolver cachea por request
    (lo consultan todos los gates y todas las pantallas de un mismo pedido), así que medir
    el antes y el después dentro del mismo contexto leería el valor cacheado."""
    _, ayer, en30 = _hoy()
    _limpiar()
    with app.app_context():
        from config import puede_ver_modulo
        assert puede_ver_modulo('laura', 'tecnica') is False, "ve Técnica sin suplencia"
    _suplencia('laura', 'director_tecnico', ayer, en30, titular='hernando')
    with app.app_context():
        from config import puede_ver_modulo
        assert puede_ver_modulo('laura', 'tecnica') is True, "cubre el puesto y no ve la pantalla"
        # No le abre otras puertas.
        assert puede_ver_modulo('laura', 'tesoreria') is False, "la suplencia abrió un módulo ajeno"
    _limpiar()


def test_la_bandeja_del_director_tecnico_le_abre_al_director_tecnico(app, db_clean):
    """Su propio mensaje decía "solo Dirección Técnica / Calidad / Admin" y el gate sólo
    miraba Calidad y Admin -- Hernando no está en ninguno de los dos."""
    _limpiar()
    c = _login(app, "hernando")
    r = c.get("/api/brd/bandeja-dt")
    assert r.status_code == 200, "el DT no entra a su propia bandeja: %s" % r.data[:200]


def test_compras_sigue_afuera(app, db_clean):
    """Dientes: los sombreros no le abren la puerta a otras áreas."""
    with app.app_context():
        from blueprints.brd import _brd_puede
        _limpiar()
        assert _brd_puede('catalina', 'verifica') is False
        assert _brd_puede('catalina', 'puede_aprobar') is False


def test_activar_exige_motivo_y_fecha_de_fin(app, db_clean):
    """Una suplencia activa sin motivo no se puede justificar en una auditoría, y sin fecha
    de fin es un permiso permanente con otro nombre."""
    _limpiar()
    _hoy_, _ayer, en30 = _hoy()
    c = _login(app, "miguel")          # Aseguramiento administra el plan
    base = {"suplente": "hernando", "rol": "calidad", "titular": "yuliel", "activo": True}
    r = c.post("/api/aseguramiento/suplencias/guardar",
               json=dict(base, motivo="", hasta=en30), headers=csrf_headers())
    assert r.status_code == 400 and "motivo" in r.get_json().get("error", ""), r.data[:200]
    r = c.post("/api/aseguramiento/suplencias/guardar",
               json=dict(base, motivo="licencia", hasta=""), headers=csrf_headers())
    assert r.status_code == 400 and "fecha de fin" in r.get_json().get("error", ""), r.data[:200]
    # Y una vigencia eterna tampoco.
    from datetime import timedelta
    hoy, _a, _b = _hoy()
    r = c.post("/api/aseguramiento/suplencias/guardar",
               json=dict(base, motivo="licencia",
                         hasta=(hoy + timedelta(days=800)).isoformat()),
               headers=csrf_headers())
    assert r.status_code == 400 and "vigencia" in r.get_json().get("error", ""), r.data[:200]
    # Con todo en regla, entra.
    r = c.post("/api/aseguramiento/suplencias/guardar",
               json=dict(base, motivo="licencia de la analista", hasta=en30),
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:300]
    with app.app_context():
        from blueprints.brd import _batch_role_info
        assert 'calidad' in _batch_role_info('hernando')['suple']
    _limpiar()


def test_solo_aseguramiento_o_direccion_administran_el_plan(app, db_clean):
    """Quién puede firmar en lugar de quién es gobierno del sistema de calidad."""
    _limpiar()
    c = _login(app, "mayerlin")         # operaria
    r = c.post("/api/aseguramiento/suplencias/guardar",
               json={"suplente": "hernando", "rol": "calidad", "activo": True,
                     "motivo": "x", "hasta": "2027-01-01"},
               headers=csrf_headers())
    assert r.status_code == 403, r.data[:200]


def test_revocar_corta_la_habilitacion_y_conserva_el_registro(app, db_clean):
    """El titular volvió antes de la fecha. La fila NO se borra: la constancia de que alguien
    estuvo habilitado durante un período es justo lo que hay que poder mostrar después."""
    _, ayer, en30 = _hoy()
    _suplencia('miguel', 'calidad', ayer, en30)
    with app.app_context():
        from blueprints.brd import _batch_role_info
        assert 'calidad' in _batch_role_info('miguel')['suple']
    c = _login(app, "sebastian")
    fila = c.get("/api/aseguramiento/suplencias").get_json()
    sid = [f for f in fila["suplencias"]
           if f["suplente"] == "miguel" and f["rol"] == "calidad"][0]["id"]
    r = c.post("/api/aseguramiento/suplencias/revocar", json={"id": sid},
               headers=csrf_headers())
    assert r.status_code == 200, r.data[:200]
    with app.app_context():
        from blueprints.brd import _batch_role_info
        assert _batch_role_info('miguel')['suple'] == [], "siguió habilitado tras revocar"
    despues = c.get("/api/aseguramiento/suplencias").get_json()["suplencias"]
    assert any(f["id"] == sid for f in despues), "la fila se borró en vez de conservarse"
    _limpiar()


def test_la_pantalla_existe_y_tiene_puerta(app, db_clean):
    """Una pantalla sin enlace no existe (M121). Y cada `goTab('X')` necesita su panel y su
    entrada en el mapa de pestañas, o el resaltado apunta a otra (M112/M146)."""
    c = _login(app, "miguel")
    r = c.get("/aseguramiento/suplencias")
    assert r.status_code == 200, r.data[:200]
    html = r.get_data(as_text=True)
    assert "Plan de suplencias" in html
    # El JS de Aseguramiento vive en su bundle, así que se mide sobre lo que la pantalla
    # EJECUTA (HTML + <script src> propios), no sobre la constante del template (M216).
    from .conftest import pantalla_servida
    aseg = pantalla_servida(c, "/aseguramiento")
    assert "goTab('tab-suplencias')" in aseg, "no hay puerta desde Aseguramiento"
    assert 'id="tab-suplencias"' in aseg, "el botón lleva a un panel que no existe"
    assert "'tab-suplencias'" in aseg.split("_tabIds")[1][:400], "falta en el mapa de pestañas"


def test_la_lectura_del_plan_es_abierta(app, db_clean):
    """Saber quién cubre a quién es parte de operar; lo que se gatea es CAMBIARLO."""
    _limpiar()
    c = _login(app, "mayerlin")
    r = c.get("/api/aseguramiento/suplencias")
    assert r.status_code == 200, r.data[:200]
    assert r.get_json()["puede_editar"] is False, "una operaria puede editar el plan"
