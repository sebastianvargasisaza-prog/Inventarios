# -*- coding: utf-8 -*-
"""Ver el comprobante SIN tener que pagarle a alguien.

Sebastián: *"muéstrame en una pantalla el comprobante como se ve"*. Hasta hoy el documento sólo
se podía mirar abriendo el PDF de un pago YA hecho desde una fila de Contabilidad: para revisar el
diseño había que pagarle a alguien primero.

⚠ La vista previa usa el generador PURO (`generar_comprobante_egreso_pdf`), NO el que reserva
número y persiste: un preview que consumiera un correlativo dejaría huecos en una numeración que
existe justamente para que los huecos se vean (M106).
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))


def test_la_muestra_ABRE_y_es_un_PDF(app, admin_client, db_clean):
    r = admin_client.get('/comprobante-muestra')
    assert r.status_code == 200, r.data[:200]
    assert r.mimetype == 'application/pdf', r.mimetype
    assert r.data[:4] == b'%PDF', 'no devolvió un PDF'
    assert len(r.data) > 2000, 'el PDF salió vacío'


def test_se_ve_en_la_PANTALLA_no_se_descarga(app, admin_client, db_clean):
    """`inline` para poder mirarlo · `attachment` obligaría a bajarlo para verlo."""
    r = admin_client.get('/comprobante-muestra')
    assert 'inline' in r.headers.get('Content-Disposition', ''), r.headers.get('Content-Disposition')


def test_las_DOS_empresas(app, admin_client, db_clean):
    """Ánimus y Espagiria tienen identidad distinta · hay que poder ver las dos."""
    a = admin_client.get('/comprobante-muestra?empresa=animus')
    e = admin_client.get('/comprobante-muestra?empresa=espagiria')
    assert a.status_code == 200 and e.status_code == 200
    assert a.data != e.data, 'las dos empresas salen idénticas'


def test_un_valor_raro_NO_rompe_la_pantalla(app, admin_client, db_clean):
    """Un parámetro inventado cae al default en vez de reventar."""
    r = admin_client.get('/comprobante-muestra?empresa=<script>')
    assert r.status_code == 200
    assert r.data[:4] == b'%PDF'


def test_NO_consume_un_numero_de_comprobante(app, admin_client, db_clean):
    """La numeración prueba que no faltan documentos · un preview que gaste correlativos deja
    huecos que después nadie puede explicar (M106)."""
    from database import get_db
    with app.app_context():
        antes = get_db().execute("SELECT COUNT(*) FROM comprobantes_pago").fetchone()[0]
    admin_client.get('/comprobante-muestra')
    admin_client.get('/comprobante-muestra')
    with app.app_context():
        despues = get_db().execute("SELECT COUNT(*) FROM comprobantes_pago").fetchone()[0]
    assert despues == antes, 'la vista previa persistió un comprobante'


def test_se_ve_que_es_una_MUESTRA(app, db_clean):
    """Un PDF de aspecto formal suelto en una carpeta se confunde con uno real."""
    import io as _io
    src = _io.open(os.path.join(RAIZ, 'api/blueprints/compras.py'), encoding='utf-8').read()
    i = src.find('def comprobante_muestra')
    bloque = src[i:i + 2600]
    assert 'MUESTRA' in bloque, 'el documento no se identifica como muestra'
    assert 'no corresponde a un pago real' in bloque


def test_NO_es_publica(app, client, db_clean):
    """Lleva la identidad de la empresa y el formato del soporte de egreso."""
    r = client.get('/comprobante-muestra')
    assert r.status_code in (302, 401, 403, 404), r.status_code
