# -*- coding: utf-8 -*-
"""La alerta de MP de China (60 días de lead time) tiene que poder sonar.

`_get_china_mps` devolvía SIEMPRE un set vacío: pedía `SELECT id` y `maestro_mps` no tiene esa
columna (su llave es `codigo_mp`). La consulta reventaba en cada llamada, un `except: pass` lo
tragaba, y con el set vacío las DOS alertas que dependen de él nunca se dispararon -- entre
ellas la que escala a CRÍTICO *"comprar HOY o se detiene la línea"*, que existe justamente
porque con 60 días de lead time ya estás tarde.

Una alerta que no suena se ve igual que una que no tiene motivo para sonar: por eso no lo
reportó nadie (M96/M12a).
"""
import pytest


def _limpiar(cur):
    cur.execute("DELETE FROM maestro_mps WHERE codigo_mp LIKE 'ZZCN-%'")
    cur.execute("DELETE FROM mp_formula_bridge WHERE formula_material_id LIKE 'ZZCN-%'")


def test_reconoce_la_mp_del_proveedor_chino(app):
    import database
    from blueprints.programacion import _get_china_mps, PROVEEDORES_CHINA

    assert PROVEEDORES_CHINA, "sin proveedores chinos declarados la alerta no existe"

    with app.app_context():
        c = database.get_db()
        cur = c.cursor()
        _limpiar(cur)
        cur.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, proveedor, activo) "
                    "VALUES ('ZZCN-1','ZZ PEPTIDO','Lyphar Biotech',1)")
        cur.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, proveedor, activo) "
                    "VALUES ('ZZCN-2','ZZ LOCAL','Proveedor Local SAS',1)")
        c.commit()

        china = _get_china_mps(c)

    assert "ZZCN-1" in china, (
        "la MP de Lyphar no entró al set · la alerta de China no puede sonar: %s"
        % sorted(x for x in china if str(x).startswith("ZZCN")))
    assert "ZZCN-2" not in china, "una MP local no puede contar como China"


def test_tambien_reconoce_el_codigo_de_formula_por_el_puente(app):
    """El set se compara contra `formula_items.material_id`, que puede ser un código fantasma."""
    import database
    from blueprints.programacion import _get_china_mps

    with app.app_context():
        c = database.get_db()
        cur = c.cursor()
        _limpiar(cur)
        cur.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, proveedor, activo) "
                    "VALUES ('ZZCN-1','ZZ PEPTIDO','Yitibio Co',1)")
        cur.execute("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, "
                    "activo) VALUES ('ZZCN-FANTASMA','ZZCN-1',1)")
        c.commit()

        china = _get_china_mps(c)

    assert "ZZCN-1" in china
    assert "ZZCN-FANTASMA" in china, (
        "el código de fórmula que llega a la MP china por el puente tiene que reconocerse, "
        "o la alerta se apaga justo para las fórmulas con código fantasma (M1)")
    assert "" not in china, "un código vacío en el set haría match con cualquier cosa"


def test_un_puente_inactivo_no_cuenta(app):
    """Un puente dado de baja es una decisión: no puede seguir marcando la MP como china."""
    import database
    from blueprints.programacion import _get_china_mps

    with app.app_context():
        c = database.get_db()
        cur = c.cursor()
        _limpiar(cur)
        cur.execute("INSERT INTO maestro_mps (codigo_mp, nombre_inci, proveedor, activo) "
                    "VALUES ('ZZCN-1','ZZ PEPTIDO','Lyphar',1)")
        cur.execute("INSERT INTO mp_formula_bridge (formula_material_id, bodega_material_id, "
                    "activo) VALUES ('ZZCN-VIEJO','ZZCN-1',0)")
        c.commit()

        china = _get_china_mps(c)

    assert "ZZCN-VIEJO" not in china
