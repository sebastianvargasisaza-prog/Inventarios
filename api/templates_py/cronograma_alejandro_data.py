"""Datos del cronograma estático de Alejandro (mayo 2026).

Extraídos de animuslab.neocities.org/programacion_mayo_areas (snapshot
del HTML que mandó como referencia · 2-may-2026).

Solo incluyo eventos de FABRICACIÓN — los demás (env/micro/lib/acond/
entrega) se DERIVAN de la fabricación con offsets estándar y son los
que el sistema auto-genera. La comparación útil es:
  Alejandro dice fabricar X el día Y → ¿está programado en Calendar?

Si está → match.
Si no → diferencia (Alejandro tiene algo que el sistema no sabe).
Si Calendar tiene algo que Alejandro no → otra diferencia.
"""

# Cada entrada: (fecha_ISO, producto_canonical, area_codigo, urgente)
# producto_canonical es el nombre que matchea con produccion_programada.producto
ALEJANDRO_FAB_MAYO_2026 = [
    # ── SEMANA 1 · 04–08 may ──
    ('2026-05-05', 'Gel Hidratante 50ml', 'PROD1', False),
    ('2026-05-06', 'Limpiador Iluminador Kojico 150ml', 'PROD1', False),
    ('2026-05-08', 'Emulsion Hidratante Iluminadora', 'PROD1', False),
    ('2026-05-04', 'Blush Balm', 'PROD2', False),
    ('2026-05-07', 'Lip Serum Voluminizador', 'PROD2', False),
    ('2026-05-05', 'Booster Tensor', 'PROD3', True),

    # ── SEMANA 2 · 11–15 may ──
    ('2026-05-11', 'Hydra Balance', 'PROD1', True),  # CRÍTICO Nuevo Lanz.
    ('2026-05-12', 'Hydra Peptide', 'PROD1', True),  # CRÍTICO Nuevo Lanz.
    ('2026-05-12', 'Blush Balm Tonos 1-10', 'PROD2', False),
    ('2026-05-13', 'Blush Balm Tonos 11-20', 'PROD2', False),

    # ── SEMANA 3 · 18–22 may ──
    ('2026-05-18', 'Suero Multipeptidos 30ml', 'PROD1', False),
    ('2026-05-19', 'Suero Iluminador TRX 30ml', 'PROD1', False),
    ('2026-05-20', 'Limpiador Facial Hidratante 150ml', 'PROD1', False),
    ('2026-05-21', 'Suero Antioxidante Renova C10', 'PROD1', False),
    ('2026-05-22', 'Suero Exfoliante BHA 2% 30ml', 'PROD1', False),

    # ── SEMANA 4 · 25–29 may ──
    ('2026-05-25', 'Suero Niacinamida 30ml', 'PROD1', False),
    ('2026-05-26', 'Esencia Centella Asiatica 30ml', 'PROD1', False),
    ('2026-05-27', 'Suero Vitamina C+ 30ml', 'PROD1', False),
    ('2026-05-29', 'Crema Corporal ReNova Body', 'PROD1', False),
]


def normalizar_producto(nombre: str) -> str:
    """Normaliza nombre para matching fuzzy: lowercase, sin acentos, sin espacios extra."""
    if not nombre:
        return ''
    import unicodedata
    s = nombre.strip().lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')  # sin acentos
    s = ' '.join(s.split())  # collapse spaces
    return s


def matchea(producto_a, producto_b):
    """¿Dos nombres de producto representan el mismo? Match parcial robusto."""
    na, nb = normalizar_producto(producto_a), normalizar_producto(producto_b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    # Match si uno contiene al otro (ej "Gel Hidratante" matchea "Gel Hidratante 50ml")
    if na in nb or nb in na:
        return True
    # Match por keywords clave: si comparten 2+ palabras significativas (>3 chars)
    pa = set(w for w in na.split() if len(w) > 3)
    pb = set(w for w in nb.split() if len(w) > 3)
    if len(pa & pb) >= 2:
        return True
    return False
