# -*- coding: utf-8 -*-
"""Exportación anual del expediente en formato legible SIN el sistema (tarea B-08 · ASG-PRO-014).

EL PROBLEMA QUE RESUELVE
------------------------
Los documentos regulados ya viven en el archivo inmutable, organizados por lote. Pero saber QUÉ
documentos componen el expediente de un lote, quién los generó y cuándo, sale de la base de datos.
O sea que el archivo sobrevive a perder el sistema y el ÍNDICE no: quedarían miles de archivos sin
forma de saber cuál corresponde a qué, ni si están todos.

La conservación exigida es de años y supera la vida previsible de cualquier programa. Un expediente
que sólo se puede leer con EOS corriendo no cumple: hay que poder abrirlo dentro de diez años, con
un navegador y nada más.

QUÉ PRODUCE
-----------
Por año, dos archivos que se guardan junto a los documentos:

  · `indice.html` -- se abre con doble clic, sin servidor y sin conexión. Un lote por sección, con
    sus documentos, quién los generó, cuándo, y la ruta exacta dentro del archivo.
  · `indice.csv`  -- la misma información para procesar con cualquier herramienta.

⚠ El índice NO es un resumen: enumera cada documento con su ruta y declara los que nunca llegaron
a archivarse. Un índice que sólo lista lo que salió bien haría creer que el expediente está
completo cuando le falta justo lo que no se pudo guardar (M100).
"""
import csv
import html
import io as _io
import json
import logging
import time
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

PREFIJO = 'exportacion'


def _hoy_col():
    return datetime.utcnow() - timedelta(hours=5)


def _filas(conn, anio):
    """Los documentos del año, por lote. Se ordena por lote y fecha para que el índice se lea
    como el expediente y no como un volcado."""
    c = conn.cursor()
    c.execute(
        "SELECT COALESCE(lote,''), COALESCE(producto_nombre,''), COALESCE(tipo_doc,''), "
        "       COALESCE(formato,''), COALESCE(titulo,''), COALESCE(generado_por,''), "
        "       COALESCE(generado_at,''), COALESCE(r2_key,''), COALESCE(entidad,''), "
        "       COALESCE(codigo,''), id "
        "FROM documentos_regulados "
        "WHERE COALESCE(anulado,0)=0 AND SUBSTR(COALESCE(generado_at,''),1,4)=? "
        "ORDER BY lote, generado_at, id", (str(anio),))
    return c.fetchall()


def _agrupar(filas):
    lotes = {}
    for f in filas:
        lotes.setdefault(f[0] or '(sin lote)', []).append(f)
    return lotes


def construir(conn, anio):
    """Devuelve (html, csv, resumen). No escribe nada: así se puede previsualizar."""
    filas = _filas(conn, anio)
    lotes = _agrupar(filas)
    sin_archivar = [f for f in filas if not f[7] or f[7] == '(sin-archivo)']

    e = lambda x: html.escape(str(x or ''))
    partes = []
    for lote in sorted(lotes):
        docs = lotes[lote]
        prod = next((d[1] for d in docs if d[1]), '')
        partes.append(
            '<section><h2>%s%s</h2><table><thead><tr><th>Documento</th><th>Formato</th>'
            '<th>Tipo</th><th>Generado</th><th>Por</th><th>Ruta en el archivo</th></tr></thead>'
            '<tbody>' % (e(lote), (' &middot; ' + e(prod)) if prod else ''))
        for d in docs:
            ruta = d[7]
            falta = (not ruta or ruta == '(sin-archivo)')
            partes.append(
                '<tr%s><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class="k">%s</td></tr>'
                % (' class="falta"' if falta else '', e(d[4] or d[2]), e(d[3]), e(d[2]),
                   e((d[6] or '')[:19].replace('T', ' ')), e(d[5]),
                   'NO ARCHIVADO' if falta else e(ruta)))
        partes.append('</tbody></table></section>')

    gen = _hoy_col().strftime('%d-%m-%Y %H:%M')
    doc = (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<title>Expediente ' + str(anio) + ' &middot; Espagiria Laboratorio</title><style>'
        'body{font-family:Arial,Helvetica,sans-serif;color:#111;max-width:1100px;margin:0 auto;'
        'padding:28px 20px;font-size:13px;line-height:1.5}'
        'h1{font-size:23px;margin:0 0 4px}'
        '.sub{color:#555;margin-bottom:8px}'
        '.nota{border:1px solid #111;padding:11px 14px;margin:16px 0;background:#f6f6f6}'
        'h2{font-size:15px;margin:26px 0 6px;border-bottom:2px solid #111;padding-bottom:3px}'
        'table{width:100%;border-collapse:collapse;margin-bottom:6px}'
        'th{background:#e6e6e6;text-align:left;padding:6px 8px;font-size:10.5px;'
        'text-transform:uppercase;letter-spacing:.03em;border:1px solid #111}'
        'td{border:1px solid #111;padding:6px 8px;vertical-align:top}'
        'td.k{font-family:ui-monospace,Consolas,monospace;font-size:11px;word-break:break-all}'
        'tr.falta td{background:#ffecec;font-weight:700}'
        '.pie{margin-top:30px;border-top:1px solid #111;padding-top:8px;color:#555;font-size:11.5px}'
        '</style></head><body>'
        '<h1>Expediente de lotes &middot; ' + str(anio) + '</h1>'
        '<div class="sub">ESPAGIRIA LABORATORIO S.A.S. &middot; generado el ' + gen + '</div>'
        '<div class="nota">Este &iacute;ndice se lee sin EOS y sin conexi&oacute;n. Cada fila indica '
        'la ruta exacta del documento dentro del archivo de documentos regulados. '
        '<b>Las filas en rojo son documentos que NUNCA llegaron a archivarse</b>: existen en el '
        'sistema pero no tienen copia en el archivo, y por eso se enumeran en vez de omitirse.'
        '<br>Lotes: <b>' + str(len(lotes)) + '</b> &middot; documentos: <b>' + str(len(filas)) +
        '</b> &middot; sin archivar: <b>' + str(len(sin_archivar)) + '</b></div>'
        + ''.join(partes) +
        '<div class="pie">ASG-PRO-014 numeral 5.11, tarea B-08. La conservaci&oacute;n exigida '
        'supera la vida previsible de cualquier programa: por eso el expediente tiene que poder '
        'abrirse con un navegador y nada m&aacute;s.</div>'
        '</body></html>')

    buf = _io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow(['lote', 'producto', 'tipo_documento', 'formato', 'titulo', 'generado_por',
                'generado_at', 'ruta_archivo', 'entidad', 'codigo', 'id'])
    for f in filas:
        w.writerow([f[0], f[1], f[2], f[3], f[4], f[5], f[6],
                    f[7] if (f[7] and f[7] != '(sin-archivo)') else 'NO ARCHIVADO',
                    f[8], f[9], f[10]])

    resumen = {'anio': int(anio), 'lotes': len(lotes), 'documentos': len(filas),
               'sin_archivar': len(sin_archivar), 'generado': gen}
    return doc, buf.getvalue(), resumen


def exportar(app, anio):
    """Construye el índice del año y lo guarda junto a los documentos."""
    t0 = time.monotonic()
    try:
        from r2_storage import r2_configurado, r2_put
    except Exception as e:
        return {'ok': False, 'motivo': 'almacenamiento no disponible: %s' % str(e)[:120]}
    if not r2_configurado():
        return {'ok': False, 'motivo': 'el almacenamiento de objetos no está configurado'}

    with app.app_context():
        from database import get_db
        doc, csvtxt, resumen = construir(get_db(), anio)

    base = '%s/%s/' % (PREFIJO, anio)
    ok_html = r2_put(base + 'indice.html', doc.encode('utf-8'), 'text/html; charset=utf-8')
    ok_csv = r2_put(base + 'indice.csv', csvtxt.encode('utf-8-sig'), 'text/csv; charset=utf-8')
    r2_put(base + 'resumen.json', json.dumps(resumen, ensure_ascii=False).encode('utf-8'),
           'application/json')

    resumen.update({'ok': bool(ok_html and ok_csv), 'ruta': base,
                    'segundos': round(time.monotonic() - t0, 1)})
    if not resumen['ok']:
        resumen['motivo'] = 'no pude subir el índice al almacenamiento'
    return resumen
