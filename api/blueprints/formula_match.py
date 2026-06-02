"""Motor único de matching nombre-de-ingrediente ↔ código de maestro_mps.

1-jun-2026 · Sebastián: capturas "N-acetil glucosamina (MP00175)" y
"Acetyl tetrapeptide-5 (MP00175)" — dos MPs químicamente distintas apuntando
al MISMO código en formula_items. El formulario (código y nombre son inputs
independientes) y el backend (solo validaba que el código existiera, no que
concordara con el nombre) dejaban pasar el mapeo cruzado → stock cruzado →
"Hay 0g / Hay 17.5g" al producir aunque la bodega tenga material.

Este módulo centraliza la lógica de scoring que ANTES vivía inline en
admin.admin_diagnosticar_formulas, para que el DETECTOR (reporte) y el GUARDADO
(bloqueo preventivo en POST /api/formulas) usen EXACTAMENTE el mismo criterio
(principio M1 · un solo resolver por entidad). No diverger nunca.

API pública:
  build_maestro_index(rows)            rows = [(codigo, nombre_comercial, nombre_inci), ...]
  evaluar_item(nombre_formula, mid, idx) -> dict con problema/candidatos/mejor/...
  es_match_plausible(nombre_formula, mid, idx) -> bool (atajo para el guard)
"""
import re as _re
import unicodedata as _ud

# Palabras que se ignoran al comparar (genéricas / sufijos de proveedor)
STOPWORDS = {
    'LYPHAR', 'YTBIO', 'LIQUIDO', 'POLVO', 'SOLUCION', 'AL', 'EN',
    'KD', 'KDA', 'DE', 'LA', 'EL', 'LOS', 'LAS', 'POR', 'PARA',
    'GRADO', 'COSMETICO', 'COSMETICA', 'NF', 'USP',
    'INCHEMICAL', 'AGENQUIMICOS', 'BASF', 'IMCD',
}

# Sinónimos cosméticos español/inglés + INCI
SINONIMOS_PARES = [
    # Polioles
    ('GLICERINA', 'GLYCERIN', 'GLYCEROL'),
    ('PROPILENGLICOL', 'PROPYLENE', 'GLYCOL', 'PG'),
    ('POLIETILENGLICOL', 'POLYETHYLENE', 'GLYCOL', 'PEG'),
    ('BUTILENGLICOL', 'BUTYLENE', 'GLYCOL', 'BG'),
    ('PENTILENGLICOL', 'PENTYLENE', 'GLYCOL'),
    ('HEXANODIOL', 'HEXANEDIOL'),
    # Ácidos
    ('ACIDO', 'ACID'),
    ('SALICILICO', 'SALICYLIC'),
    ('HIALURONICO', 'HYALURONIC'),
    ('LACTICO', 'LACTIC'),
    ('GLICOLICO', 'GLYCOLIC'),
    ('CITRICO', 'CITRIC'),
    ('TRANEXAMICO', 'TRANEXAMIC'),
    ('AZELAICO', 'AZELAIC'),
    ('ASCORBICO', 'ASCORBIC'),
    ('KOJICO', 'KOJIC'),
    ('FERULICO', 'FERULIC'),
    ('MANDELICO', 'MANDELIC'),
    ('SUCCINICO', 'SUCCINIC'),
    ('PALMITICO', 'PALMITIC'),
    # Surfactantes / emulsificantes
    ('TWEEN', 'POLYSORBATE'),
    ('SORBITAN', 'SORBITAN'),
    # Alcoholes
    ('ALCOHOL', 'ETHANOL', 'ETANOL'),
    ('CETILICO', 'CETYL'),
    ('ESTEARILICO', 'STEARYL'),
    ('CETOESTEARILICO', 'CETEARYL'),
    # Conservantes
    ('FENOXIETANOL', 'PHENOXYETHANOL'),
    ('BENZOATO', 'BENZOATE'),
    ('SORBATO', 'SORBATE'),
    ('PARABENO', 'PARABEN'),
    # Vitaminas / activos
    ('NIACINAMIDA', 'NIACINAMIDE', 'NICOTINAMIDE'),
    ('UREA', 'CARBAMIDE'),
    ('ALANTOINA', 'ALLANTOIN'),
    ('PANTENOL', 'PANTHENOL'),
    ('RETINALDEHIDO', 'RETINALDEHYDE', 'RETINAL'),
    ('RETINOL', 'RETINOL'),
    ('TOCOFEROL', 'TOCOPHEROL'),
    ('ASCORBIL', 'ASCORBYL'),
    ('ARBUTINA', 'ARBUTIN'),
    ('ECTOINA', 'ECTOIN', 'ECTOINE'),
    ('BAKUCHIOL', 'BAKUCHIOL', 'BACKUCHIOL'),
    ('CAFEINA', 'CAFFEINE'),
    ('GLUTATION', 'GLUTATHIONE'),
    ('ADENOSINA', 'ADENOSINE'),
    ('BIOTINA', 'BIOTIN'),
    ('MELATONINA', 'MELATONIN'),
    # Aminoácidos / proteínas
    ('GLICINA', 'GLYCINE'),
    ('CARNITINA', 'CARNITINE'),
    ('BETAINA', 'BETAINE'),
    ('GLICINAMIDA', 'GLYCINAMIDE'),
    # Cationes
    ('SODIO', 'SODIUM'),
    ('POTASIO', 'POTASSIUM'),
    ('CALCIO', 'CALCIUM'),
    ('MAGNESIO', 'MAGNESIUM'),
    ('ZINC', 'ZINC'),
    ('HIERRO', 'IRON'),
    # Óxidos / minerales
    ('OXIDO', 'OXIDE'),
    ('TITANIO', 'TITANIUM'),
    ('DIOXIDO', 'DIOXIDE'),
    # Aguas / vehículos
    ('AGUA', 'WATER', 'AQUA'),
    ('DESIONIZADA', 'DEIONIZED'),
    ('DESTILADA', 'DISTILLED'),
    # Aceites / ésteres
    ('ACEITE', 'OIL'),
    ('TRIGLICERIDO', 'TRIGLYCERIDE'),
    ('CAPRILICO', 'CAPRYLIC'),
    ('CAPRICO', 'CAPRIC'),
    ('JOJOBA', 'JOJOBA'),
    ('ARGAN', 'ARGAN'),
    ('ESCUALANO', 'SQUALANE'),
    ('ESCUALENO', 'SQUALENE'),
    # Emulsionantes / espesantes
    ('CARBOPOL', 'CARBOMER'),
    ('GOMA', 'GUM'),
    ('XANTAN', 'XANTHAN'),
    ('CELULOSA', 'CELLULOSE'),
    # Otros
    ('EDTA', 'EDTA'),
    ('TRIETANOLAMINA', 'TRIETHANOLAMINE', 'TEA'),
    ('CENTELLA', 'CENTELLA', 'GOTU', 'KOLA'),
    ('REGALIZ', 'LICORICE'),
    ('SALVIA', 'SAGE'),
    ('YOGURT', 'YOGURT'),
    ('SILIMARINA', 'SILYMARIN'),
    ('RESVERATROL', 'RESVERATROL'),
    ('BETAGLUCAN', 'BETAGLUCAN', 'BETA-GLUCAN'),
    ('NAG', 'GLUCOSAMINE', 'GLUCOSAMINA'),
    ('PEPTIDO', 'PEPTIDE'),
    ('PALMITOIL', 'PALMITOYL'),
    ('ACETIL', 'ACETYL'),
    ('TETRAPEPTIDO', 'TETRAPEPTIDE'),
    ('TRIPEPTIDO', 'TRIPEPTIDE'),
    ('HEXAPEPTIDO', 'HEXAPEPTIDE'),
    ('PENTAPEPTIDO', 'PENTAPEPTIDE'),
    ('NONAPEPTIDO', 'NONAPEPTIDE'),
    ('MIRISTOIL', 'MYRISTOYL'),
    ('FOSFATO', 'PHOSPHATE'),
    ('TOCOFERIL', 'TOCOPHERYL'),
    ('GLUCOSIDE', 'GLUCOSIDO'),
    ('GLUCONOLACTONA', 'GLUCONOLACTONE'),
    ('HIDROXIDO', 'HYDROXIDE'),
    ('BICARBONATO', 'BICARBONATE'),
    ('EXTRACTO', 'EXTRACT'),
    ('POLVO', 'POWDER'),
]

SINONIMOS = {}
for _grupo in SINONIMOS_PARES:
    for _w in _grupo:
        SINONIMOS.setdefault(_w, set()).update(set(_grupo) - {_w})

# Tokens "de identidad" — palabras largas que distinguen una MP de otra
# (GLUCOSAMINA vs TETRAPEPTIDE). Si la línea tiene un token de identidad sin
# equivalente (ni sinónimo) en el catálogo del código asignado, es mismatch
# por más que compartan un token genérico (ACETYL, ACID, GLYCOL...).
# No es stopword pero tampoco distingue por sí solo.
TOKENS_NO_IDENTIDAD = {
    'ACETIL', 'ACETYL', 'ACID', 'ACIDO', 'GLYCOL', 'OIL', 'ACEITE',
    'EXTRACT', 'EXTRACTO', 'POWDER', 'PEPTIDE', 'PEPTIDO', 'SODIUM',
    'SODIO', 'OXIDE', 'OXIDO', 'WATER', 'AGUA', 'AQUA', 'PALMITOYL',
    'PALMITOIL', 'PHOSPHATE', 'FOSFATO',
}


def norm(s):
    """ascii, uppercase, sin paréntesis, separadores → espacio, colapsa espacios."""
    if not s:
        return ''
    s = _ud.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper().strip()
    s = _re.sub(r'\([^)]*\)', '', s)
    s = _re.sub(r'[\-_,.;:/]', ' ', s)
    s = _re.sub(r'\s+', ' ', s).strip()
    return s


def palabras_clave(s):
    """Set de palabras significativas (sin stopwords)."""
    return set(p for p in norm(s).split() if p and p not in STOPWORDS)


def expandir_sinonimos(palabras):
    ampliado = set(palabras)
    for p in palabras:
        if p in SINONIMOS:
            ampliado.update(SINONIMOS[p])
    return ampliado


def build_maestro_index(rows):
    """rows: iterable de (codigo, nombre_comercial, nombre_inci)."""
    maestro = []
    for r in rows:
        cod = r[0]
        nc = r[1] or ''
        inci = r[2] or '' if len(r) > 2 else ''
        nombres_norm = set(filter(None, [norm(nc), norm(inci)]))
        palabras = set()
        for nm in [nc, inci]:
            palabras.update(palabras_clave(nm))
        maestro.append({
            'codigo': cod, 'nombres_norm': nombres_norm,
            'palabras_clave': palabras,
            'nombre_comercial': nc, 'nombre_inci': inci,
        })
    return maestro


def _score_entry(palabras_form, palabras_form_exp, nombre_norm, m):
    """Score 0-100 de cuán bien el nombre de fórmula coincide con la entrada m."""
    score = 0
    len_form = len(palabras_form)
    len_cat = len(m['palabras_clave'])
    cat_palabras_exp = expandir_sinonimos(m['palabras_clave'])

    if nombre_norm and nombre_norm in m['nombres_norm']:
        score = 100
    elif palabras_form and m['palabras_clave'] and palabras_form == m['palabras_clave']:
        score = 95
    elif palabras_form and m['palabras_clave']:
        comunes = palabras_form & m['palabras_clave']
        comunes_exp = palabras_form_exp & cat_palabras_exp
        len_comunes = len(comunes)
        len_comunes_exp = len(comunes_exp)
        if comunes == palabras_form and len_form >= 1:
            if len_cat <= len_form + 1:
                score = 92
            elif len_cat <= len_form * 2:
                score = 88
            else:
                score = 80
        elif comunes == m['palabras_clave'] and len_cat >= 1:
            if len_form <= len_cat + 1:
                score = 85
            else:
                score = 75
        elif len_comunes_exp >= len_form and len_form >= 1:
            score = 80
        elif len_comunes >= max(2, int(len_form * 0.7)):
            score = 70
        elif len_comunes_exp >= max(2, int(len_form * 0.7)):
            score = 65
        elif len_comunes >= max(1, int(len_form * 0.5)) and len_comunes >= 1:
            score = 55

    # Bonus substring (ej. 'GLIC' ⊂ 'GLICERINA')
    if score < 70 and palabras_form and m['palabras_clave']:
        substring_matches = 0
        for pf in palabras_form:
            if len(pf) >= 4:
                for pc in m['palabras_clave']:
                    if pc.startswith(pf) or pf.startswith(pc):
                        substring_matches += 1
                        break
        if substring_matches == len(palabras_form) and len_form >= 1:
            score = max(score, 75)
        elif substring_matches >= max(1, int(len_form * 0.7)):
            score = max(score, 65)
    return score


def _hay_identidad_disjunta(palabras_form, cat_palabras):
    """True si la LÍNEA tiene un token de IDENTIDAD (largo, distintivo) cuyo
    grupo de sinónimos no aparece en el catálogo del código asignado.

    Distingue 'N-acetil GLUCOSAMINA' de 'acetyl TETRAPEPTIDE-5': comparten
    ACETYL (genérico, no-identidad) pero GLUCOSAMINA no está en el código del
    tetrapéptido → la línea dice ser otra MP → mismatch.

    Solo dirección línea→código (no la inversa): el maestro suele tener nombre
    comercial + INCI con palabras extra legítimas (p.ej. 'Pemulen EZ-4U' con
    INCI 'Acrylates...') que la fórmula no repite — eso NO es un mapeo cruzado."""
    cat_exp = expandir_sinonimos(cat_palabras)
    for w in palabras_form:
        if len(w) >= 5 and w not in TOKENS_NO_IDENTIDAD:
            grupo = {w} | SINONIMOS.get(w, set())
            if not (grupo & cat_exp):
                return True  # token de identidad de la línea ausente en el código
    return False


def mejor_match(nombre, maestro_index):
    """Devuelve (entry, score) del mejor match de `nombre` en el índice, o None.
    Útil para casar una línea de fórmula contra un catálogo (p.ej. el Excel maestro)."""
    pf = palabras_clave(nombre)
    pfe = expandir_sinonimos(pf)
    nn = norm(nombre)
    best = None
    for m in maestro_index:
        s = _score_entry(pf, pfe, nn, m)
        if s > 0 and (best is None or s > best[1]):
            best = (m, s)
    return best


def evaluar_item(nombre_formula, mid, maestro_index):
    """Evalúa una línea de fórmula contra el catálogo.

    Devuelve dict:
      es_huerfano, problema ('huerfano'|'mismatch_nombre'|None),
      candidatos (top5), mejor_candidato, auto_corregible,
      maestro_nombre (del código asignado, si existe).
    """
    nombre_norm = norm(nombre_formula)
    palabras_form = palabras_clave(nombre_formula)
    palabras_form_exp = expandir_sinonimos(palabras_form)
    catalogo_codigos = {m['codigo'] for m in maestro_index}
    es_huerfano = mid not in catalogo_codigos

    candidatos = []
    for m in maestro_index:
        score = _score_entry(palabras_form, palabras_form_exp, nombre_norm, m)
        if score > 0:
            candidatos.append({
                'codigo': m['codigo'],
                'nombre_comercial': m['nombre_comercial'],
                'nombre_inci': m['nombre_inci'],
                'score': score,
            })
    candidatos.sort(key=lambda x: -x['score'])
    if candidatos and candidatos[0]['score'] >= 85:
        min_threshold = max(70, candidatos[0]['score'] - 20)
        candidatos = [c for c in candidatos if c['score'] >= min_threshold]
    candidatos = candidatos[:5]

    auto_corregible = False
    if candidatos:
        top_score = candidatos[0]['score']
        second_score = candidatos[1]['score'] if len(candidatos) > 1 else 0
        delta = top_score - second_score
        if top_score == 100 and len([c for c in candidatos if c['score'] == 100]) == 1:
            auto_corregible = True
        elif top_score >= 95 and delta >= 5:
            auto_corregible = True
        elif top_score >= 88 and delta >= 8:
            auto_corregible = True
        elif top_score >= 80 and delta >= 10:
            auto_corregible = True
        elif top_score >= 75 and delta >= 15:
            auto_corregible = True

    problema = None
    maestro_nombre = None
    if es_huerfano:
        problema = 'huerfano'
    else:
        cat_match = next((m for m in maestro_index if m['codigo'] == mid), None)
        if cat_match:
            maestro_nombre = cat_match['nombre_comercial'] or cat_match['nombre_inci']
            if palabras_form and cat_match['palabras_clave']:
                # Overlap CON sinónimos (no crudo) → no marca falso positivo en
                # cross-idioma (Glicerina↔Glycerin). El criterio histórico usaba
                # overlap crudo y marcaba esos casos legítimos.
                comunes_exp = palabras_form_exp & expandir_sinonimos(cat_match['palabras_clave'])
                # Mismatch si <50% coinciden (con sinónimos) O si hay tokens de
                # IDENTIDAD disjuntos (acetil-glucosamina vs acetil-tetrapéptido
                # comparten ACETYL genérico pero difieren en GLUCOSAMINA/TETRAPEPTIDE).
                if (len(comunes_exp) < max(1, int(len(palabras_form) * 0.5))
                        or _hay_identidad_disjunta(palabras_form, cat_match['palabras_clave'])):
                    problema = 'mismatch_nombre'

    mejor = candidatos[0] if candidatos else None
    if mejor and auto_corregible:
        mejor = dict(mejor)
        mejor['auto'] = True

    return {
        'es_huerfano': es_huerfano,
        'problema': problema,
        'candidatos': candidatos,
        'mejor_candidato': mejor,
        'auto_corregible': auto_corregible,
        'maestro_nombre': maestro_nombre,
    }
