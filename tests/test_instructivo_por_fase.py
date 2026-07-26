"""Cargar el instructivo de una fase NO puede tocar las otras (26-jul).

Sebastián: *"tenemos envasado de emulsiones, limpiadores, sueros…"* → hay que poder cargar un
instructivo de ENVASADO por producto, no sólo el de fabricación.

Dos cosas estaban mal y las dos eran silenciosas:
  1. el cargador escribía SIEMPRE `fase='fabricacion'` hardcodeado → un instructivo de envasado
     habría entrado como pasos de MEZCLA y habría corrompido la receta del producto;
  2. al reemplazar en un borrador borraba TODOS los pasos del MBR → cargar envasado habría
     BORRADO el instructivo de fabricación del mismo borrador.

Ninguna de las dos habría dado error: el operario habría abierto el legajo y habría leído los
pasos equivocados. Eso es exactamente lo que un registro regulado no puede hacer.
"""
from .conftest import TEST_PASSWORD, csrf_headers

FAB = ['Paso 1. Calentar la fase acuosa a 55°C.', 'Paso 2. Emulsificar y enfriar a 40°C.']
ENV = ['Paso 1. Alistar frascos y ajustar la llenadora al volumen.',
       'Paso 2. Control de peso cada 15 minutos.',
       'Paso 3. Sellar y entregar a acondicionamiento.']
ACO = ['Paso 1. Verificar arte y codificación de lote y vencimiento.',
       'Paso 2. Etiquetar y encajar.']


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _h(c):
    h = dict(csrf_headers())
    h["X-CSRF-Token"] = c.get("/api/csrf-token").get_json()["csrf_token"]
    h["Content-Type"] = "application/json"
    return h


def _pasos_por_fase(app, mbr_id):
    from blueprints.brd import _fase_canonica
    from database import get_db
    with app.app_context():
        filas = get_db().execute(
            "SELECT COALESCE(fase,''), descripcion FROM mbr_pasos WHERE mbr_template_id=? ORDER BY orden",
            (mbr_id,)).fetchall()
    out = {}
    for fase, desc in filas:
        out.setdefault(_fase_canonica(fase), []).append(desc)
    return out


def _sembrar_mbr(app, producto):
    """MBR en BORRADOR, limpio (los tests tienen que ser re-ejecutables · M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db()
        cur = conn.cursor()
        for r in cur.execute("SELECT id FROM mbr_templates WHERE UPPER(TRIM(producto_nombre))="
                             "UPPER(TRIM(?))", (producto,)).fetchall():
            cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (r[0],))
            cur.execute("DELETE FROM mbr_templates WHERE id=?", (r[0],))
        cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                    "creado_por) VALUES (?,1,'draft',10000,'test')", (producto,))
        mid = cur.lastrowid
        conn.commit()
        return mid


def test_cargar_envasado_no_borra_el_instructivo_de_fabricacion(app):
    """El bug que más importa: eran dos fases en el mismo MBR y una pisaba a la otra."""
    prod = 'FASE TEST PRODUCTO A'
    mid = _sembrar_mbr(app, prod)
    c = _admin(app)
    r1 = c.post("/api/brd/mbr/cargar-instructivo", headers=_h(c),
                json={'producto': prod, 'pasos': FAB})
    assert r1.status_code == 200, r1.data[:200]
    r2 = c.post("/api/brd/mbr/cargar-instructivo", headers=_h(c),
                json={'producto': prod, 'pasos': ENV, 'fase': 'envasado'})
    assert r2.status_code == 200, r2.data[:200]
    d = _pasos_por_fase(app, mid)
    assert len(d.get('fabricacion', [])) == 2, ('el instructivo de fabricación se perdió: %s' % d)
    assert len(d.get('envasado', [])) == 3, d
    assert '55°C' in ' '.join(d['fabricacion'])
    assert 'llenadora' in ' '.join(d['envasado'])


def test_las_tres_fases_conviven(app):
    prod = 'FASE TEST PRODUCTO B'
    mid = _sembrar_mbr(app, prod)
    c = _admin(app)
    for pasos, fase in ((FAB, 'fabricacion'), (ENV, 'envasado'), (ACO, 'acondicionamiento')):
        r = c.post("/api/brd/mbr/cargar-instructivo", headers=_h(c),
                   json={'producto': prod, 'pasos': pasos, 'fase': fase})
        assert r.status_code == 200, (fase, r.data[:160])
    d = _pasos_por_fase(app, mid)
    assert len(d.get('fabricacion', [])) == 2, d
    assert len(d.get('envasado', [])) == 3, d
    assert len(d.get('acondicionamiento', [])) == 2, d


def test_recargar_una_fase_la_reemplaza_y_deja_las_otras(app):
    prod = 'FASE TEST PRODUCTO C'
    mid = _sembrar_mbr(app, prod)
    c = _admin(app)
    for pasos, fase in ((FAB, 'fabricacion'), (ENV, 'envasado')):
        c.post("/api/brd/mbr/cargar-instructivo", headers=_h(c),
               json={'producto': prod, 'pasos': pasos, 'fase': fase})
    # recargar envasado con OTRO contenido
    c.post("/api/brd/mbr/cargar-instructivo", headers=_h(c),
           json={'producto': prod, 'pasos': ['Paso 1. Envasado corregido.'], 'fase': 'envasado'})
    d = _pasos_por_fase(app, mid)
    assert d.get('envasado') == ['Paso 1. Envasado corregido.'], d
    assert len(d.get('fabricacion', [])) == 2, 'fabricación no se toca al recargar envasado'


def test_una_fase_inventada_se_rechaza(app):
    """Una fase mal escrita no puede terminar como pasos huérfanos que nadie ve."""
    prod = 'FASE TEST PRODUCTO D'
    _sembrar_mbr(app, prod)
    c = _admin(app)
    r = c.post("/api/brd/mbr/cargar-instructivo", headers=_h(c),
               json={'producto': prod, 'pasos': ENV, 'fase': 'enbasado'})
    assert r.status_code == 400, r.status_code
    assert 'fase' in (r.get_json() or {}).get('error', '').lower()


def test_sin_fase_sigue_siendo_fabricacion(app):
    """Compatibilidad: los 28 instructivos ya cargados no pasaban `fase`."""
    prod = 'FASE TEST PRODUCTO E'
    mid = _sembrar_mbr(app, prod)
    c = _admin(app)
    r = c.post("/api/brd/mbr/cargar-instructivo", headers=_h(c),
               json={'producto': prod, 'pasos': FAB})
    assert r.get_json()['fase'] == 'fabricacion'
    assert len(_pasos_por_fase(app, mid).get('fabricacion', [])) == 2


def test_al_versionar_un_MBR_aprobado_las_otras_fases_se_conservan(app):
    """Si el MBR está aprobado se crea v+1. Esa versión nueva tiene que traer las fases que NO se
    cargaron, o aprobarla dejaría al producto sin instructivo de mezcla."""
    prod = 'FASE TEST PRODUCTO F'
    mid = _sembrar_mbr(app, prod)
    c = _admin(app)
    c.post("/api/brd/mbr/cargar-instructivo", headers=_h(c),
           json={'producto': prod, 'pasos': FAB})
    from database import get_db
    with app.app_context():
        conn = get_db()
        conn.execute("UPDATE mbr_templates SET estado='aprobado' WHERE id=?", (mid,))
        conn.commit()
    r = c.post("/api/brd/mbr/cargar-instructivo", headers=_h(c),
               json={'producto': prod, 'pasos': ENV, 'fase': 'envasado'})
    d = r.get_json()
    assert d['nueva_version'] is True, d
    nuevo = d['mbr_id']
    assert nuevo != mid
    pf = _pasos_por_fase(app, nuevo)
    assert len(pf.get('envasado', [])) == 3, pf
    assert len(pf.get('fabricacion', [])) == 2, (
        'la versión nueva perdió el instructivo de fabricación: %s' % pf)
