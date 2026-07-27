"""El envase del cliente se sabe: hay que usarlo · y las piezas se declaran por UN solo camino.

Sebastián 26-jul: *"tenemos varios clientes... desde necesidades o calendario el envase para ese
cliente, revisemos. Revisa también si en inventario de MEE está bien montada la lógica para
agregar los envases con sus partes."*

Al recorrerlo aparecieron dos cosas:

1. **`clientes_b2b_envases` valida pero no sugiere.** La tabla guarda desde mayo qué envases usa
   cada cliente, y se usaba sólo para RECHAZAR uno que no fuera suyo. Si no escribías ninguno, el
   pedido entraba sin envase y ese cliente terminaba llevándose el frasco de ÁNIMUS sin que nadie
   lo notara.

2. **Había CUATRO caminos para declarar una pieza y sólo uno estaba bien hecho.** Dos insertaban
   sin verificar que la pieza existiera en el maestro (un código mal tecleado = pieza fantasma que
   el abastecimiento intenta comprar y el envasado descontar, sin poder reponerla · M1) y uno
   tragaba el error en silencio (M4).
"""
from .conftest import TEST_PASSWORD, csrf_headers

CLIENTE = 'ZZ CLIENTE TEST'
ENV_A = 'ZZ-CLI-FR-A'
ENV_B = 'ZZ-CLI-FR-B'
ENV_BASE = 'ZZ-HELPER-FR'
PIEZA = 'ZZ-HELPER-GOT'


def _admin(app):
    c = app.test_client()
    r = c.post("/login", data={"username": "sebastian", "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _seed_mee(conn, *codigos):
    cur = conn.cursor()
    for cod in codigos:
        cur.execute("DELETE FROM maestro_mee WHERE codigo=?", (cod,))
        cur.execute("INSERT INTO maestro_mee (codigo, descripcion, categoria, estado) "
                    "VALUES (?,?,'Frasco','Activo')", (cod, 'Test ' + cod))


def _limpiar_cliente(conn):
    conn.execute("DELETE FROM clientes_b2b_envases WHERE UPPER(TRIM(cliente_id))=UPPER(TRIM(?))",
                 (CLIENTE,))


# ── 1 · el envase del cliente se precarga ────────────────────────────────────────────────────

def test_con_un_solo_envase_el_del_cliente_se_precarga(app):
    """Lo que pidió: que lo jale solo. El dato ya estaba guardado."""
    from blueprints.plan import _envase_por_defecto_del_cliente
    from database import get_db
    with app.app_context():
        conn = get_db()
        _limpiar_cliente(conn)
        _seed_mee(conn, ENV_A)
        conn.execute("INSERT INTO clientes_b2b_envases (cliente_id, envase_codigo, activo) "
                     "VALUES (?,?,1)", (CLIENTE, ENV_A))
        conn.commit()
        assert _envase_por_defecto_del_cliente(conn, CLIENTE) == ENV_A


def test_con_varios_envases_NO_adivina(app):
    """Con dientes, y es la parte que más importa: elegir por él pondría un frasco equivocado en
    el pedido de un cliente, que es peor que pedirle que elija."""
    from blueprints.plan import _envase_por_defecto_del_cliente
    from database import get_db
    with app.app_context():
        conn = get_db()
        _limpiar_cliente(conn)
        _seed_mee(conn, ENV_A, ENV_B)
        for e in (ENV_A, ENV_B):
            conn.execute("INSERT INTO clientes_b2b_envases (cliente_id, envase_codigo, activo) "
                         "VALUES (?,?,1)", (CLIENTE, e))
        conn.commit()
        assert _envase_por_defecto_del_cliente(conn, CLIENTE) == ''


def test_un_envase_inactivo_no_cuenta(app):
    """Si el cliente dejó de usar un frasco, no puede volver por la puerta de atrás."""
    from blueprints.plan import _envase_por_defecto_del_cliente
    from database import get_db
    with app.app_context():
        conn = get_db()
        _limpiar_cliente(conn)
        _seed_mee(conn, ENV_A, ENV_B)
        conn.execute("INSERT INTO clientes_b2b_envases (cliente_id, envase_codigo, activo) "
                     "VALUES (?,?,1)", (CLIENTE, ENV_A))
        conn.execute("INSERT INTO clientes_b2b_envases (cliente_id, envase_codigo, activo) "
                     "VALUES (?,?,0)", (CLIENTE, ENV_B))
        conn.commit()
        assert _envase_por_defecto_del_cliente(conn, CLIENTE) == ENV_A


def test_un_cliente_sin_lista_no_inventa(app):
    from blueprints.plan import _envase_por_defecto_del_cliente
    from database import get_db
    with app.app_context():
        conn = get_db()
        _limpiar_cliente(conn)
        conn.commit()
        assert _envase_por_defecto_del_cliente(conn, CLIENTE) == ''
        assert _envase_por_defecto_del_cliente(conn, '') == ''


# ── 2 · un solo camino para declarar piezas ──────────────────────────────────────────────────

def test_el_helper_rechaza_una_pieza_que_no_existe(app):
    """El caso que dejaba pasar el alta de envases: un código mal tecleado creaba una pieza
    fantasma que el abastecimiento intentaría comprar y el envasado descontar."""
    from audit_helpers import agregar_parte_envase
    from database import get_db
    with app.app_context():
        conn = get_db()
        _seed_mee(conn, ENV_BASE)
        conn.commit()
        ok, motivo = agregar_parte_envase(conn.cursor(), envase=ENV_BASE,
                                          parte='ZZ-NO-EXISTE-777', usuario='test')
    assert ok is False
    assert 'no existe' in (motivo or ''), motivo


def test_el_helper_no_deja_declarar_la_misma_pieza_dos_veces(app):
    """Duplicarla descontaría el doble en cada lote."""
    from audit_helpers import agregar_parte_envase
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        _seed_mee(conn, ENV_BASE, PIEZA)
        cur.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (ENV_BASE,))
        conn.commit()
        ok1, _ = agregar_parte_envase(cur, envase=ENV_BASE, parte=PIEZA, usuario='test')
        ok2, motivo = agregar_parte_envase(cur, envase=ENV_BASE, parte=PIEZA, usuario='test')
        conn.commit()
    assert ok1 is True
    assert ok2 is False and 'ya está declarada' in (motivo or ''), motivo


def test_el_helper_no_deja_que_un_envase_sea_pieza_de_si_mismo(app):
    from audit_helpers import agregar_parte_envase
    from database import get_db
    with app.app_context():
        conn = get_db()
        _seed_mee(conn, ENV_BASE)
        conn.commit()
        ok, motivo = agregar_parte_envase(conn.cursor(), envase=ENV_BASE, parte=ENV_BASE,
                                          usuario='test')
    assert ok is False and 'sí mismo' in (motivo or ''), motivo


def test_el_helper_audita_quien_declaro_la_pieza(app):
    """Cambia lo que se compra y lo que se descuenta en todos los lotes futuros: tiene que quedar
    quién lo decidió."""
    from audit_helpers import agregar_parte_envase
    from database import get_db
    with app.app_context():
        conn = get_db(); cur = conn.cursor()
        _seed_mee(conn, ENV_BASE, PIEZA)
        cur.execute("DELETE FROM mee_partes WHERE mee_codigo=?", (ENV_BASE,))
        conn.commit()
        ok, _ = agregar_parte_envase(cur, envase=ENV_BASE, parte=PIEZA, descripcion='gotero',
                                     cantidad=2, usuario='mayerlin')
        conn.commit()
        n = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE accion='AGREGAR_PARTE_ENVASE' "
            "AND registro_id=?", (ENV_BASE,)).fetchone()[0]
        cant = conn.execute(
            "SELECT cantidad FROM mee_partes WHERE UPPER(TRIM(mee_codigo))=? "
            "AND UPPER(TRIM(parte_codigo))=?", (ENV_BASE, PIEZA)).fetchone()[0]
    assert ok is True
    assert n >= 1, 'no quedó auditado'
    assert float(cant) == 2.0, 'no respetó la cantidad'


def test_el_helper_nunca_lanza(app):
    """Lo llaman cargas masivas: un dato malo devuelve motivo, no tumba el alta entera."""
    from audit_helpers import agregar_parte_envase
    from database import get_db
    with app.app_context():
        cur = get_db().cursor()
        for envase, parte, cant in ((None, None, 1), ('', 'X', 1), (ENV_BASE, '', 1),
                                    (ENV_BASE, PIEZA, 0), (ENV_BASE, PIEZA, 'abc')):
            ok, motivo = agregar_parte_envase(cur, envase=envase, parte=parte, cantidad=cant,
                                              usuario='test')
            assert ok is False and motivo, (envase, parte, cant)
