# -*- coding: utf-8 -*-
"""Importación de informes del laboratorio (Microlab) desde el correo .eml.

Parsea el .eml server-side (pdfplumber, import perezoso), extrae resultados micro y
fisicoquímicos de los PDF adjuntos, hace upsert idempotente en calidad_micro_resultados /
calidad_fisicoquimica_resultados (por n_referencia + parámetro + lab) y deja el PDF del COA
enlazado. Re-subir un correo NO duplica: actualiza el COA de los que ya estaban.

La parte de parseo (pdfplumber) y la de upsert (DB pura) están separadas a propósito para
poder testear el upsert sin depender de pdfplumber.
"""
import re
import io
import email
import unicodedata
from email import policy

PATOGENOS = ('E. coli', 'Staphylococcus aureus', 'Pseudomonas aeruginosa',
             'Candida albicans', 'Burkholderia cepacia')


def _na(s):
    """normaliza acentos + minúsculas + quita ** (marcadores fuera-de-alcance)."""
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\*+', '', s).strip()


def _txt(s):
    return re.sub(r'\s+', ' ', (s or '').replace('\n', ' ')).strip()


def norm_micro(a):
    s = _na(a)
    if 'mesofil' in s:
        return 'Mesófilos aerobios totales'
    if 'mohos y levaduras' in s:
        return 'Mohos y levaduras'
    if 'mohos' in s:
        return 'Mohos'
    if 'levaduras' in s:
        return 'Levaduras'
    if 'escherichia' in s or 'e. coli' in s or 'e.coli' in s:
        return 'E. coli'
    if 'pseudomon' in s:
        return 'Pseudomonas aeruginosa'
    if 'staphylo' in s or 'estafiloco' in s or 'aureus' in s:
        return 'Staphylococcus aureus'
    if 'candida' in s:
        return 'Candida albicans'
    if 'coliformes' in s:
        return 'Coliformes totales'
    if 'heterotrof' in s:
        return 'Heterótrofos'
    if 'gram positiv' in s:
        return 'Gram positivas'
    if 'gram negativ' in s:
        return 'Gram negativas'
    return (a or '').strip()[:60]


def cat_muestra(m):
    u = _na(m).upper()
    if u.startswith('MATERIA PRIMA') or any(k in u for k in ['NYLON-', 'BPD-', 'HDI/', 'CERAMIDE', 'CERA MICROCRISTALINA']):
        return 'materia_prima'
    if any(k in u for k in ['SUPERFICIE', 'AMBIENTE', 'UNIFORME', 'MANIPULAD', 'BIDON', 'MESON',
                            'PARED', 'PISO', 'GUANTE', ' MANO']):
        return 'ambiente'
    if u.startswith('AGUA ') and 'MICELAR' not in u:
        return 'ambiente'
    return 'producto'


def clean_prod(m):
    s = (m or '').strip()
    s = re.sub(r'^(MATERIA PRIMA|PRODUCTO TERMINADO|PRODUCTO SEMITERMINADO)\s*:\s*', '', s, flags=re.I)
    s = re.sub(r'\s*-\s*\(?PRODUCTO TERMINADO\)?.*$', '', s, flags=re.I)
    s = re.sub(r'\s*\(PRODUCTO TERMINADO\)\s*$', '', s, flags=re.I)
    s = re.sub(r'\s*-\s*FV[:\s].*$', '', s, flags=re.I)
    s = re.sub(r'\s*-\s*OP[:\s-].*$', '', s, flags=re.I)
    return s.strip()[:120] or 'N/A'


def estado_from_concepto(c):
    c = (c or '').strip().upper().replace('.', '')
    if c == 'NC':
        return 'fuera_industria'
    if c == 'C':
        return 'ok'
    return 'observacion'


def unidad_from(res):
    m = re.search(r'\(([^)]+)\)', res or '')
    return m.group(1) if m else 'UFC/g'


# ── PARSEO (pdfplumber · import perezoso) ────────────────────────────────────
def _parse_pdf(pdf_bytes):
    import pdfplumber  # perezoso: solo al importar un informe
    info = {'tipo': 'micro', 'ref': None, 'lote': None, 'muestra': None,
            'fecha': None, 'analisis': []}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[0]
        full = page.extract_text() or ''
        if 'INFORME' not in full.upper():
            return None
        info['tipo'] = 'fq' if 'FISICOQU' in _na(full).upper() else 'micro'
        rows = [r for t in (page.extract_tables() or []) for r in t]
    hdr = None
    for i, r in enumerate(rows):
        joined = ' '.join((c or '') for c in r).upper()
        c0 = _txt(r[0]) if r and r[0] else ''
        if 'REFERENCIA' in joined and len(r) > 1 and r[1]:
            info['ref'] = _txt(r[1])
        if c0.startswith('TEL') and 'LOTE' in joined:
            vs = [_txt(c) for c in r[2:] if c]
            if vs:
                info['lote'] = vs[-1]
        if c0.startswith('MUESTRA') and len(r) > 1:
            info['muestra'] = _txt(r[1])
        if c0 == 'NA' and len(r) > 1 and re.match(r'\d{4}-\d{2}-\d{2}', _txt(r[1]) or ''):
            vs = [_txt(c) for c in r if c]
            info['fecha'] = vs[-1] if vs else _txt(r[1])
        if 'AN' in joined and 'METODO' in joined and 'RESULTADO' in joined:
            hdr = i
    if info.get('fecha'):
        mm = re.search(r'\d{4}-\d{2}-\d{2}', info['fecha'])
        info['fecha'] = mm.group(0) if mm else None
    if hdr is not None:
        for r in rows[hdr + 1:]:
            cells = [_txt(c) for c in r]
            name = cells[0] if cells else ''
            if not name or 'no estan' in name.lower() or len(name) < 4:
                continue
            nonempty = [c for c in cells if c]
            if info['tipo'] == 'fq':
                info['analisis'].append({'param': name,
                                         'metodo': cells[1] if len(cells) > 1 else '',
                                         'resultado': cells[2] if len(cells) > 2 else ''})
            else:
                concepto = None
                for c in nonempty:
                    if c in ('C', 'N.C', 'NC', 'N.A', 'N.I'):
                        concepto = c
                resultado = None
                idxC = [j for j, c in enumerate(cells) if c in ('C', 'N.C', 'NC')]
                if idxC:
                    prev = [cells[j] for j in range(idxC[0]) if cells[j]]
                    resultado = prev[-1] if prev else None
                if concepto:
                    info['analisis'].append({'analisis': name, 'resultado': resultado, 'concepto': concepto})
    return info


def parse_eml_bytes(data, fallback_date=None):
    """Devuelve {'email_date', 'subject', 'samples':[info+pdf_bytes+pdf_filename]}."""
    msg = email.message_from_bytes(data, policy=policy.default)
    subj = msg['subject'] or ''
    m = re.search(r'(\d{4}-\d{2}-\d{2})', subj)
    edate = m.group(1) if m else fallback_date
    samples = []
    for part in msg.walk():
        if part.get_content_type() == 'application/pdf':
            pdf = part.get_payload(decode=True)
            if not pdf:
                continue
            info = _parse_pdf(pdf)
            if not info or not info.get('ref') or not info.get('analisis'):
                continue
            info['pdf_bytes'] = pdf
            info['pdf_filename'] = part.get_filename() or ((info.get('ref') or 'coa') + '.pdf')
            if not info.get('fecha'):
                info['fecha'] = edate
            samples.append(info)
    return {'email_date': edate, 'subject': subj, 'samples': samples}


# ── UPSERT (DB pura · testeable sin pdfplumber) ──────────────────────────────
def upsert_sample(conn, info, coa_url, usuario='import_eml'):
    """Inserta resultados nuevos + actualiza el COA de los existentes (idempotente por
    n_referencia + parámetro/microorganismo + laboratorio='Microlab Cali')."""
    ref = info.get('ref')
    nuevos = actualizados = oos = 0
    c = conn.cursor()
    if info.get('tipo') == 'fq':
        prod = clean_prod(info.get('muestra'))
        cat = cat_muestra(info.get('muestra'))
        lote = (info.get('lote') or '').strip()
        if lote.upper() in ('NA', 'N/A'):
            lote = ''
        for a in info['analisis']:
            param = (a.get('param') or '').strip()[:120]
            if not param:
                continue
            ya = c.execute("SELECT id FROM calidad_fisicoquimica_resultados "
                           "WHERE n_referencia=? AND parametro=? AND laboratorio='Microlab Cali'",
                           (ref, param)).fetchone()
            if ya:
                c.execute("UPDATE calidad_fisicoquimica_resultados SET archivo_coa_url=? WHERE id=?",
                          (coa_url, ya[0])); actualizados += 1
            else:
                res = (a.get('resultado') or '').strip()
                c.execute("INSERT INTO calidad_fisicoquimica_resultados "
                          "(lote,producto_nombre,categoria,n_referencia,fecha_analisis,parametro,metodo,"
                          " resultado,unidad,estado,laboratorio,archivo_coa_url,creado_por) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (lote, prod, cat, ref, info.get('fecha'), param,
                           (a.get('metodo') or '').strip()[:200],
                           re.sub(r'\s*\([^)]*\)\s*$', '', res)[:60], unidad_from(res),
                           'informado', 'Microlab Cali', coa_url, usuario)); nuevos += 1
        return {'nuevos': nuevos, 'actualizados': actualizados, 'oos': oos}
    # micro
    prod = clean_prod(info.get('muestra'))
    cat = cat_muestra(info.get('muestra'))
    lote = (info.get('lote') or '').strip()
    if lote.upper() in ('NA', 'N/A'):
        lote = ''
    seen = set()
    for a in info['analisis']:
        mic = norm_micro(a.get('analisis'))
        if mic in seen:
            continue
        seen.add(mic)
        est = estado_from_concepto(a.get('concepto'))
        ya = c.execute("SELECT id FROM calidad_micro_resultados "
                       "WHERE n_referencia=? AND microorganismo=? AND laboratorio='Microlab Cali'",
                       (ref, mic)).fetchone()
        if ya:
            c.execute("UPDATE calidad_micro_resultados SET archivo_coa_url=? WHERE id=?",
                      (coa_url, ya[0])); actualizados += 1
        else:
            res = (a.get('resultado') or '').strip()
            c.execute("INSERT INTO calidad_micro_resultados "
                      "(lote,producto_nombre,fecha_analisis,microorganismo,valor_texto,unidad,estado,"
                      " laboratorio,analista,creado_por,categoria,n_referencia,archivo_coa_url) "
                      "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (lote, prod, info.get('fecha'), mic, res[:60], unidad_from(res), est,
                       'Microlab Cali', 'Microlab Cali', usuario, cat, ref, coa_url)); nuevos += 1
            if est == 'fuera_industria':
                oos += 1
    return {'nuevos': nuevos, 'actualizados': actualizados, 'oos': oos}
