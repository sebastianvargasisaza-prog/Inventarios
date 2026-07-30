"""El que REGISTRA no puede APROBAR el control en proceso (29-jul · mig 400).

Sebastián, cuando le dije que el mismo operario que mide podía declarar "Cumple":
*"sí, pues eso debemos hacerlo, el que registra no puede aprobar"*.

En MyBatch la sección 5 (Controles en Proceso) la firma **Calidad**. Acá cualquier ejecutor
del batch podía anotar el valor Y adjudicarlo. Se separa en dos actos, espejando la 2ª firma
del material de envase (INV-14):

  · **anotar el valor** → lo hace quien mide;
  · **adjudicar** (Cumple / No cumple / No aplica) → sólo quien VERIFICA por rol, y **nunca
    sobre su propia medición**.

⚠ Hacía falta la migración: el upsert pisaba `medido_por` con quien adjudicaba, así que sin
`adjudicado_por` no quedaba constancia de quién midió y la regla no se podía ni auditar.
Los lotes DEMO- se caminan con una sola persona, igual que el despeje.
"""
from .conftest import TEST_PASSWORD, csrf_headers

LOTE_REAL = 'ZZ-SOD-IPC'


def _login(app, user):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, 'no pudo entrar %s' % user
    return c


def _h():
    h = {"Content-Type": "application/json"}
    h.update(csrf_headers())
    return h


def _sembrar(app, lote=LOTE_REAL):
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        f = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()
        if f:
            cu.execute("DELETE FROM ipc_estandar_resultados WHERE ebr_id=?", (f[0],))
            cu.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (f[0],))
        cu.execute(
            "INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, lote_codigo, "
            "estado, fase, iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
            "VALUES (?,?,?,?,'en_proceso','fabricacion','sebastian','2026-07-30T10:00:00',1000)",
            (1, 1, lote, lote))
        eid = cu.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?", (lote,)).fetchone()[0]
        conn.commit()
    return eid


def _post(cli, eid, **body):
    return cli.post('/api/brd/ebr/%d/ipc-estandar' % eid, headers=_h(), json=body)


# ══ el operario mide, no adjudica ═══════════════════════════════════════════════

def test_el_operario_puede_ANOTAR_el_valor(app, db_clean):
    """Medir es su trabajo: anotar el pH no le está prohibido."""
    eid = _sembrar(app)
    r = _post(_login(app, 'mayerlin'), eid, control_codigo='ph', valor_texto='5.4')
    assert r.status_code in (200, 201), r.data[:300]
    assert r.get_json()['conforme'] is None, 'quedó adjudicado por el operario'


def test_el_operario_NO_puede_declarar_que_cumple(app, db_clean):
    """El corazón del pedido: declarar la conformidad es de Calidad."""
    eid = _sembrar(app)
    r = _post(_login(app, 'mayerlin'), eid, control_codigo='ph', valor_texto='5.4',
              conforme=True)
    assert r.status_code == 403, r.data[:300]
    assert r.get_json().get('codigo') == 'SOLO_CALIDAD_ADJUDICA'


def test_el_operario_tampoco_puede_marcar_No_aplica(app, db_clean):
    """'No aplica' también es una decisión de Calidad sobre el producto."""
    eid = _sembrar(app)
    r = _post(_login(app, 'mayerlin'), eid, control_codigo='olor', no_aplica=True)
    assert r.status_code == 403, r.data[:300]


# ══ Calidad adjudica, pero no lo suyo ═══════════════════════════════════════════

def test_calidad_NO_adjudica_su_propia_medicion(app, db_clean):
    """Regla de las 2 personas: quien mide y quien declara que cumple son distintos."""
    eid = _sembrar(app)
    cli = _login(app, 'laura')
    r = _post(cli, eid, control_codigo='ph', valor_texto='5.4')
    assert r.status_code in (200, 201), r.data[:300]
    r = _post(cli, eid, control_codigo='ph', valor_texto='5.4', conforme=True)
    assert r.status_code == 409, r.data[:300]
    assert r.get_json().get('codigo') == 'AUTOADJUDICACION_BLOQUEADA'


def test_calidad_adjudica_la_medicion_de_OTRO(app, db_clean):
    """Dientes del otro lado, y lo que importa para auditar: quedan las DOS personas."""
    eid = _sembrar(app)
    r = _post(_login(app, 'mayerlin'), eid, control_codigo='ph', valor_texto='5.4')
    assert r.status_code in (200, 201), r.data[:300]
    r = _post(_login(app, 'laura'), eid, control_codigo='ph', valor_texto='5.4', conforme=True)
    assert r.status_code in (200, 201), r.data[:300]
    from database import get_db
    with app.app_context():
        row = get_db().cursor().execute(
            "SELECT medido_por, adjudicado_por, conforme FROM ipc_estandar_resultados "
            "WHERE ebr_id=? AND control_codigo='ph'", (eid,)).fetchone()
    assert row[0] == 'mayerlin', 'se perdió quién midió: %r' % (row[0],)
    assert row[1] == 'laura', 'no quedó quién adjudicó: %r' % (row[1],)
    assert int(row[2]) == 1


def test_aseguramiento_tambien_adjudica(app, db_clean):
    """El set que verifica es Calidad ∪ Aseguramiento ∪ Jefe de Producción ∪ Dirección
    Técnica: si fuera sólo Laura, un día que ella no está el lote se traba.

    ⚠ Este test destapó un hueco de 3 capas: `_batch_role_info` le da a Miguel
    (Aseguramiento) y a Hernando (DT) `verifica`/`corrige`/`aprueba_dt` desde el 7-jul, pero
    `_require_brd_ejecutor` los rechazaba ANTES de leer esos flags — en los 36 endpoints de
    ejecución. La 2ª firma del despeje, la del material de envase y el visto bueno del DT
    estaban construidos y eran inalcanzables para quienes los tienen que dar (M116)."""
    eid = _sembrar(app)
    _post(_login(app, 'mayerlin'), eid, control_codigo='color', valor_texto='ambar')
    r = _post(_login(app, 'miguel'), eid, control_codigo='color', valor_texto='ambar',
              conforme=True)
    assert r.status_code in (200, 201), r.data[:300]


def test_el_director_tecnico_entra_al_batch_record(app, db_clean):
    """Hernando estaba fuera del gate de ejecución, así que su visto bueno (mig 286) no se
    podía dar ni con el meaning arreglado."""
    eid = _sembrar(app)
    _post(_login(app, 'mayerlin'), eid, control_codigo='apariencia', valor_texto='homogenea')
    r = _post(_login(app, 'hernando'), eid, control_codigo='apariencia',
              valor_texto='homogenea', conforme=True)
    assert r.status_code in (200, 201), r.data[:300]


def test_compras_sigue_afuera(app, db_clean):
    """Dientes del gate: ampliarlo a Aseguramiento y DT no puede abrirle la puerta a otras
    áreas. Un registro de lote regulado no lo toca compras."""
    eid = _sembrar(app)
    r = _post(_login(app, 'catalina'), eid, control_codigo='ph', valor_texto='5.4')
    assert r.status_code == 403, r.data[:300]


# ══ el sandbox sigue caminable por una persona ══════════════════════════════════

def test_en_un_lote_DEMO_una_sola_persona_camina_el_flujo(app, db_clean):
    """Un lote de demostración es un sandbox para recorrer el flujo, igual que el despeje."""
    eid = _sembrar(app, lote='DEMO-SOD-1')
    cli = _login(app, 'sebastian')
    r = _post(cli, eid, control_codigo='ph', valor_texto='5.4')
    assert r.status_code in (200, 201), r.data[:300]
    r = _post(cli, eid, control_codigo='ph', valor_texto='5.4', conforme=True)
    assert r.status_code in (200, 201), r.data[:300]
