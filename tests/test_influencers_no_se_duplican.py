"""El panel no puede volver a fabricar creadores duplicados (28-jul).

Sebastián, mirando el directorio: *"aparecen mil veces Camila Correal y todos salen repetidos
muchas veces"*. 751 creadores, casi todos copias del mismo puñado de nombres, en $0.

Dos defectos que se multiplicaban:
  1. El panel auto-crea un influencer por cada nombre de pago que no reconoce, pero armaba el
     set de "conocidos" con la lista FILTRADA por el buscador. Con `?q=` puesto, todos los que
     el filtro escondía parecían nuevos y se re-insertaban: **cada tecla en el buscador dejaba
     una copia de cada creador con pagos**.
  2. El `INSERT OR IGNORE` no deduplicaba nada, porque el índice UNIQUE que el comentario del
     código daba por hecho NUNCA se creó (sólo lo creaba el botón de fusionar duplicados).

El primero es el que multiplicaba; el segundo es el que lo dejaba pasar.
"""
from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302
    return c


def _cuantos(app, nombre):
    from database import get_db
    with app.app_context():
        conn = get_db()
        return conn.cursor().execute(
            "SELECT COUNT(*) FROM marketing_influencers WHERE LOWER(TRIM(nombre))=?",
            (nombre.strip().lower(),)).fetchone()[0]


def _sembrar(app, nombre, otro):
    """Limpia ANTES de sembrar (M103)."""
    from database import get_db
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        for n in (nombre, otro):
            cu.execute("DELETE FROM pagos_influencers WHERE influencer_nombre=?", (n,))
            cu.execute("DELETE FROM marketing_influencers WHERE LOWER(TRIM(nombre))=?",
                       (n.strip().lower(),))
        # El creador existe en el catálogo Y tiene un pago a su nombre.
        cu.execute("INSERT INTO marketing_influencers (nombre, estado) VALUES (?,?)",
                   (nombre, 'Activo'))
        iid = cu.execute("SELECT id FROM marketing_influencers WHERE nombre=?",
                         (nombre,)).fetchone()[0]
        cu.execute("INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, "
                   "fecha, estado) VALUES (?,?,?,?,?)",
                   (iid, nombre, 500000, '2026-07-10', 'Pagada'))
        conn.commit()
    return iid


def test_buscar_a_OTRO_creador_no_duplica_al_que_el_filtro_esconde(app, db_clean):
    """Se busca otro nombre, el filtro esconde a nuestro creador, y el auto-crear lo trataba
    como nuevo porque su set de conocidos salía de la lista filtrada.

    ⚠ Medido: reintroduciendo SOLO ese defecto, este test sigue verde -- porque el UNIQUE de
    la mig 388 ya no deja entrar la copia. O sea que verifica el RESULTADO (no aparecen
    duplicados), y el backstop que lo sostiene es el índice. El defecto del set filtrado lo
    caza `test_el_set_de_conocidos_NO_sale_de_la_consulta_filtrada`, que sí muerde.
    Hacían falta los DOS defectos juntos para producir las ~700 copias.
    """
    NOM, OTRO = 'ZZ DUP CREADOR', 'ZZ DUP OTRO'
    _sembrar(app, NOM, OTRO)
    assert _cuantos(app, NOM) == 1

    c = _login(app)
    # Una búsqueda que NO matchea a nuestro creador: es el caso que lo duplicaba.
    for _ in range(3):
        assert c.get('/api/marketing/influencers-panel?q=' + OTRO).status_code == 200

    assert _cuantos(app, NOM) == 1, (
        'buscar otro nombre duplicó al creador escondido por el filtro · quedaron %d copias'
        % _cuantos(app, NOM))


def test_abrir_el_panel_muchas_veces_no_acumula_copias(app, db_clean):
    NOM, OTRO = 'ZZ DUP REPETIR', 'ZZ DUP REPETIR B'
    _sembrar(app, NOM, OTRO)
    c = _login(app)
    for _ in range(4):
        assert c.get('/api/marketing/influencers-panel').status_code == 200
    assert _cuantos(app, NOM) == 1, '%d copias tras abrir el panel 4 veces' % _cuantos(app, NOM)


def test_el_set_de_conocidos_NO_sale_de_la_consulta_filtrada(app, db_clean):
    """El guard de la causa raíz, en el código: si alguien vuelve a armar los "conocidos"
    desde `influencers` (la lista ya filtrada), el bug renace y sólo se nota semanas después,
    cuando ya hay cientos de copias.

    Regla general: un set de "lo que ya existe" jamás se arma desde una consulta filtrada --
    lo que el filtro esconde parece que no existe.
    """
    import inspect
    from blueprints import marketing as mkt
    src = inspect.getsource(mkt.mkt_influencers_panel)
    i = src.index('known_lower')
    linea = src[i:i + 260]
    assert 'SELECT nombre FROM marketing_influencers' in linea, (
        'known_lower volvió a armarse desde la lista filtrada: %s' % linea[:160])


def test_un_pago_a_un_nombre_nuevo_SI_crea_su_creador(app, db_clean):
    """El auto-crear existe por algo: un pago importado a un nombre que no está en el catálogo
    tiene que hacer aparecer a ese creador. Arreglar el duplicado no puede matar la feature."""
    from database import get_db
    NUEVO = 'ZZ DUP NACE'
    with app.app_context():
        conn = get_db(); cu = conn.cursor()
        cu.execute("DELETE FROM pagos_influencers WHERE influencer_nombre=?", (NUEVO,))
        cu.execute("DELETE FROM marketing_influencers WHERE LOWER(TRIM(nombre))=?",
                   (NUEVO.lower(),))
        cu.execute("INSERT INTO pagos_influencers (influencer_id, influencer_nombre, valor, "
                   "fecha, estado) VALUES (?,?,?,?,?)",
                   (None, NUEVO, 120000, '2026-07-15', 'Pagada'))
        conn.commit()
    c = _login(app)
    assert c.get('/api/marketing/influencers-panel').status_code == 200
    assert _cuantos(app, NUEVO) == 1, 'el creador nuevo no se creó (o se creó de más)'


def test_existe_la_migracion_que_limpia_y_la_que_pone_el_UNIQUE(app, db_clean):
    """El UNIQUE va en su PROPIA migración a propósito: si queda algún duplicado CON datos que
    la limpieza no toca, ese statement falla, y así no arrastra la limpieza -- que sí es
    segura -- al estado de pendiente."""
    from database import MIGRATIONS
    versiones = {v: (d, s) for v, d, s in MIGRATIONS}
    assert 387 in versiones and 388 in versiones
    limpieza = ' '.join(versiones[387][1])
    assert 'DELETE FROM marketing_influencers' in limpieza
    # La limpieza sólo puede tocar cáscaras: nunca una fila con datos o referencias.
    for guarda in ('NOT EXISTS', 'pagos_influencers', 'solicitudes_compra',
                   "COALESCE(cuenta_bancaria,'')=''", "COALESCE(email,'')=''"):
        assert guarda in limpieza, 'la limpieza perdió el guard: %s' % guarda
    unico = ' '.join(versiones[388][1])
    assert 'CREATE UNIQUE INDEX' in unico and 'LOWER(TRIM(nombre))' in unico
    assert 'DELETE' not in unico, 'la migración del UNIQUE no puede borrar nada'
