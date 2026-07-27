"""El despeje de línea va en el ORDEN del procedimiento, y reordenarlo no toca lo firmado (26-jul).

Sebastián, comparando la pantalla contra MyBatch: *"tiene que quedar como dice MyBatch"*. La lista
de EOS estaba **exactamente al revés**: arrancaba por "¿Cuenta con los EPP?" y terminaba por "El
área está libre del producto anterior", que es lo PRIMERO que se verifica. Los 12 textos ya
coincidían palabra por palabra; lo único mal era la secuencia. El operario la leía de abajo hacia
arriba.

El orden de un despeje NO es cosmético: es el procedimiento. Y reordenarlo tiene una trampa que
este archivo existe para vigilar: `ebr_despeje_items` referencia por `item_idx`, así que mover un
ítem le cambia el TEXTO a los registros históricos. Un lote donde el operario firmó "Temperatura
menor a 30 grados · Sí" pasaría a decir "El área está libre... · Sí" — eso es falsificar un
registro regulado (Part 11), y no lo detecta ningún test de los que ya existían.
"""
import os
import sys

# conftest agrega `api/` al path recién dentro del fixture `app`, así que los tests que sólo miran
# la CONSTANTE (sin BD · más rápidos y deterministas · M103) no lo tendrían. Se agrega acá.
_API = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api')
if _API not in sys.path:
    sys.path.insert(0, _API)

from blueprints.brd import DESPEJE_LINEA_ITEMS, despeje_checklist   # noqa: E402

# El orden EXACTO de MyBatch (capturas del 26-jul-2026, OF-2026-77).
ORDEN_MYBATCH = [
    "El área está libre",
    "limpias y desinfectadas",
    "formatos de Limpieza",
    "Equipo limpio",
    "Área limpia",
    "completamente limpios",
    "identificada con el producto",
    "corresponden al producto a trabajar",
    "condiciones ambientales son las idóneas",
    "formato de registro de condiciones ambientales",
    "equipos requeridos se encuentran aptos",
    "EPP requeridos",
]


def test_el_orden_es_el_de_mybatch():
    """Si alguien reordena la lista, esto lo caza. El orden es el procedimiento."""
    assert len(DESPEJE_LINEA_ITEMS) == 12, (
        'MyBatch tiene 12 verificaciones, EOS tiene %d' % len(DESPEJE_LINEA_ITEMS))
    for i, marca in enumerate(ORDEN_MYBATCH):
        assert marca.lower() in DESPEJE_LINEA_ITEMS[i].lower(), (
            'la verificación %d debería ser "%s..." y es "%s"'
            % (i + 1, marca, DESPEJE_LINEA_ITEMS[i][:60]))


def test_lo_primero_es_que_no_quede_nada_del_producto_anterior():
    """El corazón del despeje. Estaba de último."""
    assert 'libre de materias primas' in DESPEJE_LINEA_ITEMS[0]
    assert 'producto anterior' in DESPEJE_LINEA_ITEMS[0]


def test_el_epp_va_al_final():
    """Lo último antes de arrancar es el EPP de quien trabaja. Estaba de segundo."""
    assert 'EPP' in DESPEJE_LINEA_ITEMS[-1]


def test_el_item_de_temperatura_ya_no_esta():
    """MyBatch no lo tiene · las condiciones ambientales las cubren los ítems 9 y 10."""
    assert not any('emperatura' in t for t in DESPEJE_LINEA_ITEMS), DESPEJE_LINEA_ITEMS


def _ebr_de_prueba(producto):
    """Un EBR real (hay FK desde ebr_despeje_items). Limpia ANTES de sembrar y usa nombre fijo:
    la BD de tests es compartida y en PostgreSQL persiste entre corridas (M103)."""
    from database import get_db
    conn = get_db(); cur = conn.cursor()
    for r in cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote=?",
                         ('L-' + producto,)).fetchall():
        cur.execute("DELETE FROM ebr_despeje_items WHERE ebr_id=?", (r[0],))
        cur.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (r[0],))
    for r in cur.execute("SELECT id FROM mbr_templates WHERE producto_nombre=?",
                         (producto,)).fetchall():
        cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (r[0],))
        cur.execute("DELETE FROM mbr_templates WHERE id=?", (r[0],))
    cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, "
                "creado_por) VALUES (?,1,'draft',1000,'test')", (producto,))
    mbr = cur.lastrowid
    cur.execute("INSERT INTO ebr_ejecuciones (mbr_template_id, mbr_version, lote, estado, "
                "iniciado_por, iniciado_at_utc, cantidad_objetivo_g) "
                "VALUES (?,1,?,'iniciado','test','2026-07-01T09:00:00',1000)",
                (mbr, 'L-' + producto))
    eid = cur.lastrowid
    conn.commit()
    return eid, conn


def test_un_item_ya_firmado_conserva_SU_texto_aunque_la_lista_cambie(app):
    """La regla dura de Part 11: lo que se muestra de un ítem registrado es el texto que el
    operario tenía delante cuando firmó, no el que hoy ocupe esa posición en la constante."""
    with app.app_context():
        eid, conn = _ebr_de_prueba('DESPEJE TEXTO VIEJO')
        conn.execute(
            "INSERT INTO ebr_despeje_items (ebr_id, item_idx, item_texto, cumple, "
            "observaciones, registrado_por, registrado_at_utc, etapa) "
            "VALUES (?, 0, ?, 1, '', 'operario', '2026-07-01T10:00:00', 'dispensacion')",
            (eid, 'TEXTO VIEJO QUE SE FIRMÓ ASÍ'))
        conn.commit()
        filas = despeje_checklist(conn, eid, 'dispensacion')
    assert filas[0]['texto'] == 'TEXTO VIEJO QUE SE FIRMÓ ASÍ', (
        'el ítem firmado tomó el texto de la constante en vez del suyo: %s' % filas[0]['texto'])
    assert filas[0]['cumple'] == 1
    # los que nadie tocó sí muestran el texto vigente
    assert filas[1]['texto'] == DESPEJE_LINEA_ITEMS[1]


def test_un_item_retirado_del_procedimiento_no_desaparece_del_lote(app):
    """Un registro regulado no se borra porque el procedimiento haya cambiado después. La mig 381
    manda el ítem retirado al índice 100; tiene que seguir viéndose, al final y marcado."""
    with app.app_context():
        eid, conn = _ebr_de_prueba('DESPEJE ITEM RETIRADO')
        conn.execute(
            "INSERT INTO ebr_despeje_items (ebr_id, item_idx, item_texto, cumple, "
            "observaciones, registrado_por, registrado_at_utc, etapa) "
            "VALUES (?, 100, 'Temperatura menor a 30 grados', 1, '', 'operario', "
            "'2026-07-01T10:00:00', 'dispensacion')", (eid,))
        conn.commit()
        filas = despeje_checklist(conn, eid, 'dispensacion')
    assert len(filas) == 13, 'las 12 vigentes + la retirada, no %d' % len(filas)
    assert filas[-1]['texto'] == 'Temperatura menor a 30 grados'
    assert filas[-1]['historico'] is True
    assert filas[-1]['cumple'] == 1
    assert all(not f['historico'] for f in filas[:12])


def test_el_remapeo_de_la_migracion_es_la_inversion_exacta():
    """El mapa viejo->nuevo de la mig 381 (nuevo = 12 - viejo) tiene que dejar cada texto en su
    posición de MyBatch. Se verifica contra la lista VIEJA, escrita acá tal como estaba."""
    vieja = [
        "Temperatura menor a 30 grados",
        "¿Cuenta con los EPP requeridos para el proceso?",
        "¿Los equipos requeridos se encuentran aptos para su uso? (mantenimiento y calibración al día)",
        "¿El formato de registro de condiciones ambientales se encuentra diligenciado y al día?",
        "¿Las condiciones ambientales son las idóneas para el proceso?",
        "Las materias primas, material de envase y empaque, graneles, etiquetas y documentación corresponden al producto a trabajar.",
        "El área se encuentra identificada con el producto en proceso",
        "El área y sus equipos y/o utensilios se encuentran completamente limpios y con los respectivos rótulos de Limpieza Área / Equipo.",
        "¿Se comprueba que todas las áreas están rotuladas como \"Área limpia\" y están listas para ser usadas?",
        "¿Se comprueba que todos los equipos están rotulados como \"Equipo limpio\" y están listos para ser usados?",
        "¿Los formatos de Limpieza de áreas se encuentran diligenciados y al día?",
        "¿Se asegura que las áreas de producción estén limpias y desinfectadas antes de cada lote?",
        "El área está libre de materias primas, material de envase y empaque, gráneles, etiquetas, producto terminado y documentación del producto anterior.",
    ]
    for viejo_idx in range(1, 13):
        nuevo_idx = 12 - viejo_idx
        assert vieja[viejo_idx] == DESPEJE_LINEA_ITEMS[nuevo_idx], (
            'la mig 381 dejaría el viejo %d en la posición %d, y ahí el texto no coincide:\n'
            '  viejo: %s\n  nuevo: %s'
            % (viejo_idx, nuevo_idx, vieja[viejo_idx][:70], DESPEJE_LINEA_ITEMS[nuevo_idx][:70]))
    # el viejo 0 es el retirado: no tiene lugar en la lista vigente
    assert vieja[0] not in DESPEJE_LINEA_ITEMS
