"""Plan de suplencias · quién puede cubrir el puesto de quién, y hasta cuándo.

Sebastián 20-ago-2026, sobre los roles del batch record: *"son backup, como reemplazos: en
caso de que no estén, ellos pueden hacerlo"* · *"lo puede hacer sólo por plan de suplencias"*.

Por qué existe esto y no una lista de permisos más ancha:

  · Cubrir una ausencia sin plan obliga a que alguien firme con el usuario de otro. Eso es lo
    único que un registro Part 11 no puede permitir: la firma deja de decir quién hizo el acto.
  · Una ampliación PERMANENTE contradice el procedimiento aprobado (`COC-PRO-010` §3.4 y
    `PRD-INS-001-004` reservan las verificaciones de proceso a Control de Calidad). Una
    suplencia con titular, motivo y fecha de fin es otra cosa: es la figura que el propio
    sistema de calidad contempla, y es defendible en auditoría.

Por eso la VIGENCIA es obligatoria: una fila sin `hasta` no habilita nada. El plan puede estar
declarado (quién es backup de qué puesto) sin estar activo — declarar no es otorgar.

Lo que esto NO relaja: la regla de las dos personas. Quien ejecuta un paso, un pesaje o un
ítem de despeje no puede firmar su propia verificación; ese control es por REGISTRO y vive en
`brd.py`. Un puesto de más nunca habilita firmar dos veces el mismo renglón.
"""
# Los puestos que se pueden suplir. Es la misma nomenclatura que los roles del batch record
# (`brd._BATCH_CAPS_POR_ROL`), a propósito: dos vocabularios para lo mismo terminan en dos
# verdades distintas.
ROLES_SUPLIBLES = ('calidad', 'aseguramiento', 'director_tecnico', 'jefe_produccion')

ROL_LABEL = {
    'calidad': 'Control de Calidad',
    'aseguramiento': 'Aseguramiento',
    'director_tecnico': 'Dirección Técnica',
    'jefe_produccion': 'Jefatura de Producción',
}

# La pantalla que necesita cada puesto: un permiso de firma sin el módulo donde se firma no
# sirve de nada (M121).
MODULO_POR_ROL = {
    'calidad': 'calidad',
    'aseguramiento': 'aseguramiento',
    'director_tecnico': 'tecnica',
    'jefe_produccion': 'planta',
}


def hoy_co():
    """Fecha de hoy en Colombia como YYYY-MM-DD.

    Sale del resolver unico del negocio (M24): en Render el server corre en UTC y de noche
    en Colombia ya es "manana", asi que una suplencia se apagaria cinco horas antes."""
    from tz_colombia import hoy_colombia
    return hoy_colombia().isoformat()


def _flag(v):
    """0/False/'f' es CERO. `int(v or 1)` convertiría una fila apagada en encendida."""
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    return str(v).strip().lower() in ('1', 't', 'true', 'si', 'sí', 'yes', 'y')


def _filas(usuario):
    """Filas del plan de esa persona. Sin tabla (base vieja) devuelve vacío y nada cambia."""
    try:
        from database import get_db
        return get_db().execute(
            "SELECT rol, COALESCE(desde,''), COALESCE(hasta,''), COALESCE(activo,0), "
            "       COALESCE(titular,''), COALESCE(motivo,'') "
            "  FROM plan_suplencias WHERE LOWER(suplente)=?", (usuario,)).fetchall()
    except Exception:
        return []


def roles_vigentes(usuario, hoy=None):
    """Puestos que `usuario` puede ejercer HOY porque tiene una suplencia activa y en fecha.

    Se cachea por request: este resolver lo consulta cada gate y cada pantalla, y sin caché
    serían decenas de consultas idénticas en un solo pedido.
    """
    u = (usuario or '').strip().lower()
    if not u:
        return set()
    dia = hoy or hoy_co()
    clave = '_suplencias_%s_%s' % (u, dia)
    try:
        from flask import g, has_app_context
        if has_app_context() and hasattr(g, clave):
            return getattr(g, clave)
    except Exception:
        g = has_app_context = None

    roles = set()
    for r in _filas(u):
        rol = str(r[0] or '').strip().lower()
        desde, hasta = str(r[1] or '').strip(), str(r[2] or '').strip()
        if rol not in ROLES_SUPLIBLES or not _flag(r[3]):
            continue
        # Sin fecha de fin NO habilita: eso sería una ampliación permanente disfrazada.
        if not hasta or dia > hasta:
            continue
        if desde and dia < desde:
            continue
        roles.add(rol)
    try:
        if has_app_context and has_app_context():
            setattr(g, clave, roles)
    except Exception:
        pass
    return roles


def plan_completo(solo_vigentes=False, hoy=None):
    """Todo el plan, para la pantalla y para la matriz de permisos."""
    dia = hoy or hoy_co()
    try:
        from database import get_db
        rows = get_db().execute(
            "SELECT id, suplente, rol, COALESCE(titular,''), COALESCE(motivo,''), "
            "       COALESCE(desde,''), COALESCE(hasta,''), COALESCE(activo,0), "
            "       COALESCE(creado_por,''), COALESCE(creado_en,'') "
            "  FROM plan_suplencias ORDER BY suplente, rol").fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        desde, hasta = str(r[5] or ''), str(r[6] or '')
        vig = bool(_flag(r[7]) and hasta and dia <= hasta and (not desde or dia >= desde))
        if solo_vigentes and not vig:
            continue
        out.append({
            'id': r[0], 'suplente': r[1], 'rol': r[2],
            'rol_label': ROL_LABEL.get(str(r[2] or ''), str(r[2] or '')),
            'titular': r[3], 'motivo': r[4], 'desde': desde, 'hasta': hasta,
            'activo': 1 if _flag(r[7]) else 0, 'vigente': vig,
            'creado_por': r[8], 'creado_en': r[9],
        })
    return out
