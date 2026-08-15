"""La etiqueta y la caja del cliente dejan de ser una marca sin efecto (15-ago-2026).

Catalina define al aceptar el pedido SI lleva etiqueta y SI lleva caja (mig 432). Esa
decisión sola no alcanza para actuar: **sin el CÓDIGO del material no se puede comprar,
ni alistar, ni descontar**, así que la marca quedaba de adorno y el material se olvidaba
hasta que faltaba en el piso.

Lo que fija este guard:
  · que el lote diga qué material de marca del cliente exige, resuelto por UN solo helper
    (M3) y DERIVADO de los pedidos, no copiado a otra tabla (M99);
  · que cuando la marca está y el código no, se DECLARE `falta_definir` en vez de
    adivinar un código parecido — así es como se termina comprando el material de otro
    cliente (M19/M100);
  · que un código que no existe en el maestro se RECHACE al guardarlo: apuntar al vacío
    no da error, da un material que nadie ve hasta el día que falta (M179/M195);
  · que la pantalla lo PINTE, porque un dato que el backend manda y la vista no dibuja no
    existe (M115).
"""
import os
import sqlite3

from .conftest import TEST_PASSWORD, csrf_headers


def _login(app, user="sebastian"):
    c = app.test_client()
    r = c.post("/login", data={"username": user, "password": TEST_PASSWORD},
               headers=csrf_headers(), follow_redirects=False)
    assert r.status_code == 302, r.data[:200]
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
    for sql in ("DELETE FROM pedidos_b2b_lote WHERE pedido_b2b_id IN "
                "(SELECT id FROM pedidos_b2b WHERE cliente_nombre LIKE 'ZMAT%')",
                "DELETE FROM pedidos_b2b WHERE cliente_nombre LIKE 'ZMAT%'",
                "DELETE FROM produccion_programada WHERE producto LIKE 'ZMAT%'",
                "DELETE FROM maestro_mee WHERE codigo LIKE 'ZMAT-%'"):
        try:
            _exec(sql)
        except Exception:
            pass


def _sembrar(lleva_etiqueta=1, etiqueta_codigo='', lleva_caja=0, caja_codigo=''):
    """Un lote con un aporte de cliente que lleva etiqueta (y quizá caja)."""
    pp = _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
               "estado, origen) VALUES ('ZMAT PRODUCTO','2026-09-01',50,'pendiente','eos_plan')")
    ped = _exec("INSERT INTO pedidos_b2b (cliente_id, cliente_nombre, producto_nombre, "
                "cantidad_uds, ml_unidad, estado, creado_por, "
                "lleva_etiqueta, etiqueta_codigo, lleva_caja, caja_codigo) "
                "VALUES ('ZMAT-CLI','ZMAT Kelly','ZMAT PRODUCTO',1200,30,'confirmado',"
                "'sebastian',?,?,?,?)",
                (lleva_etiqueta, etiqueta_codigo, lleva_caja, caja_codigo))
    _exec("INSERT INTO pedidos_b2b_lote (pedido_b2b_id, lote_produccion_id, kg_aporte, "
          "unidades_aporte, cliente_nombre) VALUES (?,?,36,1200,'ZMAT Kelly')", (ped, pp))
    return pp, ped


def _material(app, pp):
    from api.blueprints.programacion import _material_cliente_lote
    from api.database import get_db
    with app.app_context():
        return _material_cliente_lote(get_db(), pp)


def test_el_lote_dice_que_material_de_cliente_exige(app, db_clean):
    _limpiar()
    _exec("INSERT INTO maestro_mee (codigo, descripcion, categoria, stock_actual) "
          "VALUES ('ZMAT-ETQ-01','Etiqueta Kelly 30 ml','Etiqueta',0)")
    pp, _ped = _sembrar(lleva_etiqueta=1, etiqueta_codigo='ZMAT-ETQ-01')
    mats = _material(app, pp)
    assert len(mats) == 1, mats
    m = mats[0]
    assert m["tipo"] == "etiqueta"
    assert m["codigo"] == "ZMAT-ETQ-01"
    assert m["unidades"] == 1200, m
    assert m["falta_definir"] is False
    assert "Kelly" in m["cliente"]


def test_marca_sin_codigo_se_declara_en_vez_de_adivinarse(app, db_clean):
    """Adivinar un código parecido es como se compra el material de otro cliente."""
    _limpiar()
    pp, _ = _sembrar(lleva_etiqueta=1, etiqueta_codigo='', lleva_caja=1, caja_codigo='')
    mats = _material(app, pp)
    assert len(mats) == 2, mats
    assert all(m["falta_definir"] for m in mats), mats
    assert all(m["codigo"] == "" for m in mats), mats
    assert {m["tipo"] for m in mats} == {"etiqueta", "caja"}


def test_un_lote_sin_cliente_no_exige_material_de_marca(app, db_clean):
    """El borde que hace que el guard signifique algo: sin aporte de cliente, nada."""
    _limpiar()
    pp = _exec("INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, "
               "estado, origen) VALUES ('ZMAT SOLO','2026-09-02',20,'pendiente','eos_plan')")
    assert _material(app, pp) == []


def test_lo_que_no_lleva_no_aparece(app, db_clean):
    """`lleva_caja=0` no puede producir una fila: pediría un material que nadie usa."""
    _limpiar()
    pp, _ = _sembrar(lleva_etiqueta=1, etiqueta_codigo='', lleva_caja=0)
    mats = _material(app, pp)
    assert [m["tipo"] for m in mats] == ["etiqueta"], mats


def test_el_maestro_de_lotes_lo_muestra(app, db_clean):
    """Un dato que el backend manda y la pantalla no dibuja no existe (M115)."""
    c = _login(app)
    html = c.get("/calidad/maestro-lotes").data.decode("utf-8")
    for que, pieza in (("el bloque de material del cliente", "Material de marca del cliente"),
                       ("el aviso de lo que falta definir", "falta definir cu&aacute;l")):
        assert pieza in html, "la pantalla no muestra %s" % que
    # y el bloque de ÁNIMUS no puede quedar colgando de una condición muerta
    assert "if(false){" not in html, (
        "quedó un if(false) en la pantalla: el else cuelga de él y el texto sale siempre")


def test_un_codigo_que_no_existe_se_rechaza(app, db_clean):
    """Apuntar al vacío no da error: da un material que nadie ve hasta que falta."""
    _limpiar()
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "plan.py")
    fuente = open(ruta, encoding="utf-8").read()
    i = fuente.find('("etiqueta_codigo", "etiqueta_codigo")')
    assert i > 0, "no está el guardado del código de etiqueta"
    bloque = fuente[i:i + 1800]
    assert "FROM maestro_mee" in bloque, "no valida contra el maestro de envases"
    assert "MATERIAL_INEXISTENTE" in bloque, "no rechaza el código que no existe"


def test_hay_un_solo_lugar_que_resuelve_el_material_de_cliente(app, db_clean):
    """Dos copias de la misma regla divergen el día que alguien corrige una (M3/M45)."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    definiciones = 0
    for carpeta, _sub, archivos in os.walk(os.path.join(base, "api")):
        for a in archivos:
            if not a.endswith(".py"):
                continue
            with open(os.path.join(carpeta, a), encoding="utf-8", errors="ignore") as f:
                definiciones += f.read().count("def _material_cliente_lote(")
    assert definiciones == 1, "el resolvedor está definido %d veces" % definiciones


def test_el_maestro_no_pide_el_material_lote_por_lote(app, db_clean):
    """Una consulta por fila es lo que tumba la pantalla (M43/M63) — y lo escribí así en
    la primera versión, dentro del recorrido por lote. El guard mira que la resolución
    quede FUERA del loop y que se use la variante que resuelve la lista completa."""
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "api", "blueprints", "calidad.py")
    fuente = open(ruta, encoding="utf-8").read()
    i = fuente.find("material de MARCA DEL CLIENTE")
    assert i > 0, "no está el bloque"
    bloque = fuente[i:i + 1800]
    assert "_material_cliente_lotes(" in bloque, (
        "no usa el resolvedor de la lista completa")
    k = bloque.find("_material_cliente_lotes(conn")
    m = bloque.find("for lf, L in vista.items():")
    assert k > 0 and m > 0, bloque[:200]
    assert k < m, "la consulta quedó DENTRO del recorrido por lote"


def test_resolver_muchos_da_lo_mismo_que_resolver_uno(app, db_clean):
    """Si las dos formas contestan distinto, hay dos reglas y una va a quedar vieja."""
    _limpiar()
    pp1, _ = _sembrar(lleva_etiqueta=1, etiqueta_codigo='', lleva_caja=1)
    from api.blueprints.programacion import _material_cliente_lote, _material_cliente_lotes
    from api.database import get_db
    with app.app_context():
        db = get_db()
        uno = _material_cliente_lote(db, pp1)
        muchos = _material_cliente_lotes(db, [pp1, 0, None]).get(pp1, [])
    assert uno == muchos, (uno, muchos)
    assert len(uno) == 2, uno
