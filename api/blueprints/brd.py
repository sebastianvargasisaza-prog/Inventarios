"""Blueprint brd · Batch Record Digital (MBR + EBR + IPCs + cleaning + pesajes).

Sebastián 12-may-2026 · Fase 1 del salto a Batch Record digital.

MBR = procedimiento aprobado por QA para fabricar UN producto en UN tamaño
de lote estándar. Workflow:
    draft        → editable libremente por el creador.
    en_revision  → submit a QA · ya no editable, esperando aprobación.
    aprobado     → vigente · puede instanciarse en EBR. Inmutable (mig 109
                   triggers bloquean UPDATE de campos críticos).
    obsoleto     → reemplazado por nueva versión.

Endpoints:
    GET    /api/brd/mbr                       lista (filtros: producto, estado)
    GET    /api/brd/mbr/<id>                  detalle (template + pasos)
    POST   /api/brd/mbr                       crea draft nuevo
    PATCH  /api/brd/mbr/<id>                  edita header del draft
    POST   /api/brd/mbr/<id>/pasos            agrega paso al final
    PATCH  /api/brd/mbr/<id>/pasos/<paso_id>  edita paso (solo en draft)
    DELETE /api/brd/mbr/<id>/pasos/<paso_id>  borra paso (solo en draft)
    POST   /api/brd/mbr/<id>/submit           draft → en_revision
    POST   /api/brd/mbr/<id>/aprobar          en_revision → aprobado (requiere
                                              signature_id de e_signatures con
                                              meaning='aprueba')
    POST   /api/brd/mbr/<id>/obsoletar        aprobado → obsoleto (requiere motivo)

Permisos:
    - Crear/editar drafts: cualquier user logueado (después restringir a
      Técnica/Calidad si se necesita).
    - Submit a revisión: el creador o admin.
    - Aprobar/obsoletar: ADMIN_USERS o CALIDAD_USERS.
"""
import json as _json
import logging
from flask import Blueprint, Response, jsonify, redirect, request, session

from database import get_db
from config import ADMIN_USERS, CALIDAD_USERS, PLANTA_USERS
try:
    from templates_py.ui_help import TOOLTIP_CSS
except Exception:  # deploy-safe
    try:
        from api.templates_py.ui_help import TOOLTIP_CSS
    except Exception:
        TOOLTIP_CSS = ""
try:
    from config import EBR_MODE
except ImportError:  # deploy-safe
    EBR_MODE = "off"


def _ebr_mode_now(c=None):
    """Modo EBR EFECTIVO por request: app_settings 'ebr_mode' (toggle UI) → env EBR_MODE → 'off'.
    Usar esto en los gates (no la constante de import) para que el interruptor de la UI tenga efecto
    inmediato sin redeploy. Sebastián 24-jun: activar warn → pulir con uso → strict."""
    try:
        from database import ebr_mode
    except ImportError:
        from api.database import ebr_mode
    return ebr_mode(c)


from audit_helpers import audit_log, registrar_documento

bp = Blueprint("brd", __name__)
log = logging.getLogger("brd")


def _brd_visible(conn=None):
    """¿El Batch Record (EBR/MBR/legajos) está VISIBLE para el usuario ACTUAL?

    Gobernado por app_settings.brd_visible:
      - '1'/'true'/'on'   → visible para TODOS
      - '0'/''/ausente    → OCULTO para todos (default · seguro)
      - 'admin'           → visible solo para ADMIN_USERS
      - '<usuario>' (o lista coma-separada) → visible solo para ese/esos usuario(s)
    Sebastián 18-jun: oculto hasta validación Part 11. 22-jun: modo por-usuario para que
    Sebastián trabaje el batch digital sin que el resto lo vea. Reversible · sin redeploy."""
    try:
        c = conn or get_db()
        r = c.execute("SELECT valor FROM app_settings WHERE clave='brd_visible' LIMIT 1").fetchone()
        val = (str(r[0]).strip().lower() if (r and r[0] is not None) else '')
    except Exception:
        return False  # ante la duda, OCULTO (seguro · no exponer regulado sin validar)
    if val in ('1', 'true', 'yes', 'si', 'sí', 'on'):
        return True
    if val in ('', '0', 'false', 'no', 'off'):
        return False
    # modo restringido por usuario(s): 'admin' o username(s) coma-separados
    try:
        u = (session.get('compras_user') or '').strip().lower()
    except Exception:
        return False
    if not u:
        return False
    if val == 'admin':
        return u in {x.lower() for x in ADMIN_USERS}
    return u in {x.strip() for x in val.split(',') if x.strip()}


_BRD_OCULTO_HTML = (
    "<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Módulo en validación</title>"
    # ⚠ Los tokens estaban puestos por VALOR y no por SIGNIFICADO (M104): el fondo usaba
    # `--cx-text` -- el color del TEXTO -- porque su valor en tema claro coincide con el gris
    # oscuro que este candado quería. Hoy no se ve mal porque la página NO enlaza cortex.css y
    # todo cae al respaldo; el día que alguien la enlace, el fondo y el texto se mueven en
    # direcciones opuestas y queda ilegible. Cada uno apunta al token de su rol.
    "<style>body{font-family:system-ui,sans-serif;background:var(--cx-bg, #0f172a);color:var(--cx-text, #e2e8f0);display:flex;"
    "align-items:center;justify-content:center;min-height:100vh;margin:0;padding:24px}"
    ".c{background:var(--cx-card, #1e293b);border:1px solid var(--cx-border, #334155);border-radius:16px;padding:40px;max-width:520px;text-align:center}"
    "h2{color:var(--cx-primary-text, #a78bfa);margin:0 0 12px}p{color:var(--cx-text-soft, #94a3b8);line-height:1.5;margin:0 0 18px}"
    "a{display:inline-block;background:var(--cx-primary, #7c3aed);color:#fff;text-decoration:none;padding:10px 24px;border-radius:8px;font-weight:700}</style>"
    "</head><body><div class='c'><div style='font-size:46px;margin-bottom:8px'>&#128272;</div>"
    "<h2>Batch Record · en validación</h2>"
    "<p>El registro digital de lote (EBR/MBR · GMP) está <b>oculto temporalmente</b> hasta completar "
    "la validación por un tercero (21 CFR Part 11). El resto de Planta funciona normal.</p>"
    "<a href='/planta'>&larr; Volver a Planta</a></div></body></html>"
)


@bp.before_request
def _gate_brd_pages():
    """Oculta las PÁGINAS del batch record (no las APIs · /api/brd/* siguen vivas para que
    el historial de producción del dashboard no se rompa) hasta que Part 11 esté lista."""
    try:
        p = request.path or ''
    except Exception:
        return None
    if p.startswith('/api/'):
        return None
    if _brd_visible():
        return None
    return Response(_BRD_OCULTO_HTML, mimetype='text/html; charset=utf-8')

# Despeje de Línea · checklist GMP canónico. El CUMPLE por ítem se guarda en
# `ebr_despeje_items` con e-firma del responsable.
#
# ⚠ EL ORDEN ES PARTE DEL PROCEDIMIENTO, no es cosmético (Sebastián 26-jul-2026, comparando
# contra MyBatch: *"tiene que quedar como dice MyBatch"*). La lista estaba EXACTAMENTE AL REVÉS:
# arrancaba por los EPP y terminaba por "el área está libre del producto anterior", que es lo
# PRIMERO que hay que verificar. El operario la leía de abajo hacia arriba. Los 12 textos ya
# coincidían palabra por palabra con MyBatch; lo único mal era la secuencia (y un ítem de más,
# "Temperatura menor a 30 grados", que MyBatch no tiene y se retiró · las condiciones ambientales
# quedan cubiertas por los ítems 9 y 10).
#
# La secuencia sigue el orden real del despeje: primero que no quede NADA del producto anterior,
# después que esté limpio, después que los formatos y rótulos lo respalden, y al final las
# condiciones, los equipos y el EPP de quien va a trabajar.
#
# ⚠ SI ALGUNA VEZ REORDENÁS O EDITÁS ESTA LISTA: `ebr_despeje_items` referencia por `item_idx`, así
# que mover un ítem le cambia el TEXTO a los registros históricos (un lote donde el operario firmó
# "Temperatura menor a 30 grados · Sí" pasaría a decir otra cosa: eso es falsificar un registro
# regulado). Por eso la lectura ahora prefiere el `item_texto` GUARDADO en cada fila, y hay una
# migración que remapea los `item_idx` existentes emparejando POR TEXTO. Ver mig 380 y
# `tests/test_despeje_orden_mybatch.py`.
DESPEJE_LINEA_ITEMS = [
    "El área está libre de materias primas, material de envase y empaque, gráneles, etiquetas, producto terminado y documentación del producto anterior.",
    "¿Se asegura que las áreas de producción estén limpias y desinfectadas antes de cada lote?",
    "¿Los formatos de Limpieza de áreas se encuentran diligenciados y al día?",
    "¿Se comprueba que todos los equipos están rotulados como \"Equipo limpio\" y están listos para ser usados?",
    "¿Se comprueba que todas las áreas están rotuladas como \"Área limpia\" y están listas para ser usadas?",
    "El área y sus equipos y/o utensilios se encuentran completamente limpios y con los respectivos rótulos de Limpieza Área / Equipo.",
    "El área se encuentra identificada con el producto en proceso",
    "Las materias primas, material de envase y empaque, graneles, etiquetas y documentación corresponden al producto a trabajar.",
    "¿Las condiciones ambientales son las idóneas para el proceso?",
    "¿El formato de registro de condiciones ambientales se encuentra diligenciado y al día?",
    "¿Los equipos requeridos se encuentran aptos para su uso? (mantenimiento y calibración al día)",
    "¿Cuenta con los EPP requeridos para el proceso?",
]


def _checklist_configurado(conn, tipo, ambito):
    """Lo que el director técnico configuró para este ámbito, o None si no tocó nada.

    En MyBatch los ítems del despeje y los controles de atributos son pantallas de
    configuración del DT; en EOS eran constantes del código y cambiar un ítem exigía un
    despliegue. Ahora se configuran (Sebastián 15-ago-2026) sin perder lo que el código
    daba gratis: cada cambio deja su rastro en `audit_log` y el texto de lo YA FIRMADO
    no se toca nunca (M105 · lo firmado se muestra con el texto que se guardó con él).

    Devuelve None -no una lista vacía- cuando el DT no configuró este ámbito: ahí manda
    la lista de fábrica. Distinguir "no configurado" de "configurado sin ítems" importa,
    porque lo segundo dejaría un legajo SIN verificaciones y se vería igual (M124).

    Sólo devuelve los ítems ACTIVOS: uno retirado del procedimiento no se borra (los
    lotes donde se registró lo siguen mostrando), simplemente deja de pedirse.
    """
    try:
        rows = conn.execute(
            "SELECT clave, texto, COALESCE(unidad,''), COALESCE(activo,1) "
            "  FROM checklist_items WHERE tipo=? AND ambito=? "
            " ORDER BY orden, id", (str(tipo), str(ambito))).fetchall()
    except Exception as _e:
        # Sin la tabla (instancia sin migrar) se sigue con las de fábrica · pero se dice,
        # que un except mudo convierte "no pude leer" en "no hay nada" (M4/M94).
        log.warning("checklist_items(%s, %s) no legible: %s", tipo, ambito, _e)
        return None
    if not rows:
        return None
    return [(str(r[0]), str(r[1]), str(r[2] or '')) for r in rows if int(r[3] or 0) == 1]


def _fecha_colombia(ts):
    """La fecha (YYYY-MM-DD) de una marca de tiempo UTC, en hora de Colombia (UTC-5).

    Cortar un `..._at_utc` con `[:10]` da la fecha UTC, que entre las 19:00 y la medianoche local
    ya es el día siguiente. Mostrarla así adelanta un día la orden, y compararla contra un "hoy"
    anclado en Colombia da edades negativas (M24). Si el valor ya es una fecha suelta (los
    registros simples guardan `YYYY-MM-DD`), se devuelve tal cual.
    """
    s = (ts or '').strip()
    if len(s) <= 10:
        return s[:10]
    from datetime import datetime as _d, timedelta as _td
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S'):
        try:
            return (_d.strptime(s[:19], fmt) - _td(hours=5)).date().isoformat()
        except ValueError:
            continue
    return s[:10]


def despeje_checklist(conn, ebr_id, etapa='dispensacion'):
    """Las verificaciones de despeje de un EBR, en el orden del procedimiento.

    UN solo resolvedor para los 4 sitios que las muestran (pantalla, PDF del batch record,
    endpoint de checklist e imprimible de despeje). Antes cada uno armaba el texto por su cuenta
    desde la constante y por POSICIÓN, así que reordenar la lista le cambiaba el texto a lo ya
    firmado.

    Regla dura (Part 11): **el texto que se muestra de un ítem YA REGISTRADO es el que se guardó
    con él** (`item_texto`), porque es lo que el operario tenía delante cuando firmó. La constante
    sólo se usa para los ítems que todavía nadie tocó.

    Un ítem retirado del procedimiento (p.ej. "Temperatura menor a 30 grados") NO desaparece de los
    lotes donde se registró: se devuelve al final marcado como `historico`. Un registro regulado no
    se borra porque el procedimiento haya cambiado después.
    """
    reg = {}
    try:
        for r in conn.execute(
            "SELECT item_idx, cumple, COALESCE(observaciones,''), COALESCE(registrado_por,''), "
            "COALESCE(registrado_at_utc,''), COALESCE(verificado_por,''), "
            "COALESCE(verificado_at_utc,''), COALESCE(item_texto,'') "
            "FROM ebr_despeje_items WHERE ebr_id=? AND COALESCE(etapa,'dispensacion')=?",
            (ebr_id, etapa)).fetchall():
            reg[int(r[0])] = r
    except Exception as _e:            # nunca romper la vista del legajo por esto...
        log.warning("despeje_checklist(%s, %s) fallo: %s", ebr_id, etapa, _e)
        reg = {}                       # ...pero dejar rastro (un except mudo esconde el bug · M94)

    def _fila(idx, texto_canonico, historico=False):
        r = reg.get(idx)
        guardado = (r[7] if (r and len(r) > 7) else '') or ''
        return {
            'idx': idx,
            # el guardado manda: lo firmado no cambia de texto aunque la lista se reordene
            'texto': (guardado.strip() or texto_canonico),
            'cumple': (int(r[1]) if r and r[1] is not None else None),
            'observaciones': (r[2] if r else ''),
            'registrado_por': (r[3] if r else ''),
            'fecha': (r[4] if r else ''),
            'registrado_at': (r[4] if r else ''),
            'verificado_por': (r[5] if r else ''),
            'verificado_at': (r[6] if r else ''),
            'historico': historico,
        }

    # Lo que el DT configuró manda; sin configuración, la lista de fábrica (M3: un solo
    # lugar decide). La CLAVE de cada ítem es su `item_idx`, no su posición: así el DT
    # puede reordenar la pantalla sin cambiarle el texto a lo que ya se firmó.
    cfg = _checklist_configurado(conn, 'despeje', etapa or 'dispensacion')
    if cfg:
        filas, vistos = [], set()
        for clave, texto, _u in cfg:
            try:
                idx = int(clave)
            except (TypeError, ValueError):
                continue
            vistos.add(idx)
            filas.append(_fila(idx, texto))
        # Un ítem RETIRADO del procedimiento no desaparece del lote donde se registró:
        # se conserva al final, marcado. Un registro regulado no se borra porque el
        # procedimiento haya cambiado después.
        for idx in sorted(k for k in reg if k not in vistos):
            filas.append(_fila(idx, '', historico=True))
        return filas

    filas = [_fila(i, t) for i, t in enumerate(DESPEJE_LINEA_ITEMS)]
    # ítems registrados que ya no están en el procedimiento vigente (se conservan, al final)
    for idx in sorted(k for k in reg if k >= len(DESPEJE_LINEA_ITEMS)):
        filas.append(_fila(idx, '', historico=True))
    return filas

# Controles en Proceso ESTÁNDAR · Sebastián 6-jun-2026. Se muestran SIEMPRE en
# la sección 6 (aunque el MBR del producto no defina IPCs), y cada uno se puede
# registrar con valor o marcar "No aplica". (codigo, nombre, unidad).
# Un paso del INSTRUCTIVO no lleva 2ª firma · Sebastián 16-ago-2026: **"entonces por etapa"**.
#
# Los instructivos se cargaban marcando `requiere_qc=1` en TODOS sus pasos, y ese flag no es
# decorativo: el registro del paso devuelve 400 hasta que otra persona firme `supervisa`. Con
# ~20 pasos por lote eso son 20 firmas de Calidad por lote, y el sistema documental de la
# empresa no pide eso -- pide las verificaciones POR ETAPA:
#
#   · `PRD-INS-001-004` marca las verificaciones de CC como tablas propias de cada etapa
#     ("diligenciamiento EXCLUSIVO de Control de Calidad"), no como una firma por renglón.
#   · `PRD-PRO-001` pone la verificación de CC sobre el DESPEJE, una por área.
#   · `COC-PRO-010` §3.4 le da al analista "ejecutar verificaciones", que en el batch digital
#     son los controles en proceso y las aprobaciones de etapa.
#
# Lo que se firma sigue firmándose, y son cinco actos, no veinte: el **despeje** (con su
# verificación independiente de CC), los **controles en proceso** (que sólo Calidad adjudica),
# los **pesajes**, el **material de envase** (INV-14) y la **liberación**. Un control que se
# pide igual en cada renglón se contesta por inercia y tapa al que sí importa (M205).
#
# Sigue siendo configurable paso por paso desde el MBR (`PATCH .../pasos/<id>`), así que marcar
# un paso crítico es un clic -- lo que cambia es el DEFAULT, no la capacidad.
_REQUIERE_QC_INSTRUCTIVO = 0

IPC_ESTANDAR = [
    ("densidad",   "Densidad a 25°C", "g/mL"),
    ("ph",         "pH a 25°C",       ""),
    ("olor",       "Olor",            ""),
    ("color",      "Color",           ""),
    ("apariencia", "Apariencia",      ""),
]

# Los controles dependen de la FASE (Sebastián 15-ago-2026, clonando MyBatch para la
# certificación). Pedir "Densidad a 25°C" y "pH" en un legajo de ACONDICIONAMIENTO es
# pedirle la densidad a una caja: el control no aplica, se marca "No aplica" por
# inercia, y el que sí importa -que la etiqueta esté adherida y derecha- no está.
# MyBatch usa control de llenado en envasado y 14 controles de ATRIBUTOS en
# acondicionamiento; son los que firma Calidad antes de liberar.
IPC_ESTANDAR_ENVASADO = [
    ("llenado",        "Control de llenado (volumen)",              "mL"),
    ("peso_llenado",   "Control de peso del llenado",               "g"),
    ("sellado",        "Sellado (continuo, sin interrupciones)",    ""),
    ("aspecto_envase", "Aspecto del envase (limpio, sin daños)",    ""),
]

IPC_ESTANDAR_ACONDICIONAMIENTO = [
    ("etq_adherencia",  "Adherencia de la etiqueta (sin bordes levantados ni burbujas)", ""),
    ("etq_alineacion",  "Alineación de la etiqueta (centrada según el envase)", ""),
    ("etq_integridad",  "Integridad de la etiqueta (sin arrugas, rasgaduras ni decoloración)", ""),
    ("etiquetado",      "Etiquetado conforme a la lista de chequeo de etiquetas", ""),
    ("legibilidad",     "Legibilidad (información clara, sin manchas ni errores)", ""),
    ("caja_integridad", "Integridad de la caja plegadiza (bien armada, sin deformaciones)", ""),
    ("caja_impresion",  "Impresión de la caja plegadiza (nítida, sin manchas)", ""),
    ("caja_aspecto",    "Aspecto de la caja plegadiza (limpia, sin arrugas)", ""),
    ("caja_limpieza",   "Limpieza de la caja plegadiza (sin polvo, pegamento o partículas)", ""),
    ("sellado",         "Sellado (continuo, conforme y sin interrupciones visibles)", ""),
    ("derrames",        "Derrames (sin residuos dentro ni fuera del envase)", ""),
    ("particulas",      "Partículas (producto libre de partículas extrañas)", ""),
    ("aspecto_final",   "Aspecto final (envase/empaque sin abolladuras, raspones ni manchas)", ""),
    ("aspecto_general", "Aspecto general del producto", ""),
]


def _ipc_estandar_fabrica(fase):
    """La lista de FÁBRICA de esta fase (lo que EOS trae escrito en el código)."""
    f = _fase_canonica(fase or "fabricacion")
    if f == "envasado":
        return IPC_ESTANDAR_ENVASADO
    if f == "acondicionamiento":
        return IPC_ESTANDAR_ACONDICIONAMIENTO
    return IPC_ESTANDAR


def _ipc_estandar_de_fase(fase, conn=None):
    """Qué controles en proceso se piden en esta fase. UN solo lugar decide (M3).

    `conn` es opcional a propósito: con conexión se mira lo que el director técnico
    configuró, y sin ella se responde la lista de fábrica igual que siempre, así que
    ningún llamador viejo cambia de comportamiento (aditivo · M117).
    """
    f = _fase_canonica(fase or "fabricacion")
    if conn is not None:
        cfg = _checklist_configurado(conn, 'ipc', f)
        if cfg:
            return [(c, t, u) for c, t, u in cfg]
    return _ipc_estandar_fabrica(f)


def _ipc_estandar_ebr(conn, ebr_id):
    """La lista de controles del legajo · si no se puede leer la fase, cae a la de
    fabricación (la de siempre) en vez de quedarse sin controles."""
    try:
        row = conn.execute("SELECT COALESCE(fase,'fabricacion') FROM ebr_ejecuciones "
                           "WHERE id=?", (ebr_id,)).fetchone()
        return _ipc_estandar_de_fase((row[0] if row else "fabricacion"), conn)
    except Exception as _e:
        log.warning("fase del EBR %s no legible para IPC estándar: %s", ebr_id, _e)
        return IPC_ESTANDAR


def _batch_role_info(usuario):
    """Rol del usuario en el batch record (segregación de funciones GMP · 25-jun).
    UI-hint: el backend YA bloquea con 403; esto adapta la vista · quién REALIZA
    (operario/jefe prod) vs quién VERIFICA (calidad/jefe prod/dir. téc.). Reusa los
    sets de config.py. Roles finos: operario · jefe_produccion · calidad ·
    aseguramiento · director_tecnico · admin · consulta."""
    u = (usuario or "").strip().lower()
    try:
        from config import ASEGURAMIENTO_USERS, TECNICA_USERS
    except Exception:
        ASEGURAMIENTO_USERS, TECNICA_USERS = set(), set()
    A, C, P = set(ADMIN_USERS), set(CALIDAD_USERS), set(PLANTA_USERS)
    AS_, T = set(ASEGURAMIENTO_USERS), set(TECNICA_USERS)
    if u in A:
        tipo, rol = "admin", "Dirección / Admin"
    elif u in (C - A):
        tipo, rol = "calidad", "Control de Calidad"
    elif u in (AS_ - A):
        tipo, rol = "aseguramiento", "Aseguramiento"
    elif u in (T - A - AS_):
        tipo, rol = "director_tecnico", "Director Técnico"
    elif u in {"jose"}:
        tipo, rol = "jefe_produccion", "Jefe de Producción"
    elif u in (P | {"milton"}):
        tipo, rol = "operario", "Operario"
    elif u in {"luz", "catalina"}:
        tipo, rol = "administrativo", "Administrativo"
    else:
        tipo, rol = "consulta", "Consulta"
    realiza = tipo in ("operario", "jefe_produccion", "admin")
    # Quién VERIFICA · corregido 16-ago-2026 contra el sistema documental de la empresa (Drive), a pedido de
    # Sebastián: *"todas las verificaciones las pueden hacer analista y jefe de control de calidad"*.
    #   · COC-PRO-010 §3.4 (procedimiento del batch digital): "Analista de Calidad: EJECUTAR verificaciones,
    #     revisiones y aprobaciones conforme a su perfil autorizado".
    #   · PRD-INS-001-004 (instructivos operativos): las tablas de verificación son "de diligenciamiento
    #     EXCLUSIVO de Control de Calidad", firmadas por el Analista CC.
    #   · PRD-PRO-001 (despejes): el Jefe de Producción REALIZA el despeje y Control de Calidad lo verifica
    #     "de forma INDEPENDIENTE al Jefe de Producción" -- por eso el jefe queda en `realiza` y NO en
    #     `verifica`: quien ejecuta no puede dar su propia 2ª firma (segregación de funciones).
    #   · El Director Técnico sale de acá porque su acto es la LIBERACIÓN del producto terminado (acta de
    #     revisión con Hernando, 27-jul-2026), no verificar pasos de proceso · sigue con `aprueba_dt`.
    # Aseguramiento (Jefe de Garantía de Calidad) se conserva: COC-PRO-010 §3.2 le da verificar el
    # cumplimiento y revisar la trazabilidad de los registros electrónicos.
    verifica = tipo in ("calidad", "aseguramiento", "admin")
    return {
        "usuario": u, "tipo": tipo, "rol": rol,
        "realiza": realiza,
        "verifica": verifica,
        "corrige": tipo in ("calidad", "aseguramiento", "director_tecnico", "admin"),
        "aprueba_dt": tipo in ("director_tecnico", "admin"),
        "puede_ejecutar": tipo in ("operario", "jefe_produccion", "calidad", "admin"),
        "puede_verificar": verifica,
        "puede_liberar": tipo in ("calidad", "aseguramiento", "director_tecnico", "admin"),
        "puede_aprobar": tipo in ("calidad", "director_tecnico", "admin"),
    }


def _qc_verificadores():
    """Usuarios que VERIFICAN el despeje/pesaje (Control de Calidad + Aseguramiento), sin los admins-dueños
    (sebastián/alejandro) para no llenarles la campana. Sebastián 7-jul: se les alerta cuando empieza
    fabricación y en cada ítem marcado, para que estén AL LADO supervisando (no se bloquea al operario).

    16-ago: se saca al Director Técnico, en el mismo movimiento que `_batch_role_info` -- él ya no firma
    verificaciones de proceso, así que avisarle de cada ítem sería una campana que lleva a algo que no
    puede hacer (M202) · su acto, la liberación del producto terminado, tiene su propio aviso."""
    try:
        from config import ASEGURAMIENTO_USERS
    except Exception:
        ASEGURAMIENTO_USERS = set()
    dest = (set(CALIDAD_USERS) | set(ASEGURAMIENTO_USERS)) - set(ADMIN_USERS)
    return sorted(d for d in dest if d)


# ── UI dashboard (read-only listings) ──────────────────────────────────────

@bp.route("/brd", methods=["GET"])
@bp.route("/brd/", methods=["GET"])
def brd_dashboard():
    """UI dashboard read-only del BRD. Listados de MBR/EBR/Cleaning con
    drill-down a detalle. Acciones (crear, firmar, ejecutar) vía API."""
    if not session.get("compras_user"):
        return Response("No autorizado · login requerido", status=401)
    from templates_py.brd_html import render_brd_dashboard
    return Response(render_brd_dashboard(), mimetype="text/html")

VALID_TIPO_PASO = {
    "pesaje", "dispensacion", "mezclado", "caliente",
    "enfriamiento", "control_ipc", "envasado", "inspeccion",
    "limpieza", "otro",
}


# ── helpers permisos ────────────────────────────────────────────────────────

def _require_login():
    if not session.get("compras_user"):
        return jsonify({"error": "No autorizado"}), 401
    return None


def _require_qa_or_admin():
    u = session.get("compras_user", "")
    if u not in ADMIN_USERS and u not in CALIDAD_USERS:
        return jsonify({"error": "Solo admin o calidad pueden aprobar/obsoletar MBR"}), 403
    return None


# Endpoints EXENTOS del gate "la orden se aprueba antes de arrancar".
#
# El diseño es DEFAULT-DENY (M45: un guard aplicado a mano deja hermanos sin blindar):
# el gate corre dentro de `_require_brd_ejecutor`, así que TODO endpoint de ejecución
# -incluidos los que se escriban mañana- lo hereda sin que nadie se acuerde. Lo que se
# enumera acá es lo contrario: lo que NUNCA se puede frenar por falta de aprobación,
# porque o es la aprobación misma, o es DOCUMENTAR/CORREGIR algo que ya pasó (un
# registro regulado no se puede dejar sin anotar por un permiso administrativo).
_APROBACION_ORDEN_EXENTOS = frozenset({
    "brd.aprobar_orden_ebr",             # la aprobación en sí (si no, se muerde la cola)
    "brd.aprobar_dt_ebr",                # visto bueno del DT al CERRAR (mig 286)
    "brd.remanente_granel_ebr",          # conciliación del granel (mig 392)
    "brd.registrar_observacion_ebr",     # bitácora del proceso
    "brd.agregar_correccion_ebr",        # corrección de un dato ya asentado
    "brd.registrar_registro_fisico_ebr",  # adjuntar el PDF firmado
    "brd.registrar_precaucion_ebr",      # equipos/precauciones
})
# Los nombres de arriba son ENDPOINTS de Flask, no rutas: uno mal escrito no falla, queda
# de peso muerto y el endpoint que creías eximido se frena. `test_aprobacion_orden.py`
# los contrasta contra el `url_map` real (fue así como se cazó uno inventado).


def _exige_aprobacion_orden(conn) -> bool:
    """Toggle de `app_settings` · default OFF (M68: un modo beta es NO-OP TOTAL).

    Se prende desde /admin/seguridad-planta cuando planta ya trabaje con la orden
    aprobada de rutina; hasta entonces la firma se REGISTRA y se MUESTRA, pero no
    frena a nadie. Encenderlo a ciegas trabaría el piso el mismo día."""
    try:
        r = conn.execute("SELECT valor FROM app_settings WHERE clave='exigir_aprobacion_orden'").fetchone()
        return bool(r) and str(r[0]).strip() in ("1", "true", "True")
    except Exception as _e:                       # tabla ausente = beta (nunca frenar por esto)
        log.warning("exigir_aprobacion_orden no legible: %s", _e)
        return False


def _exige_ipc_estandar(conn) -> bool:
    """Toggle de `app_settings` · default OFF (M68: un modo beta es NO-OP TOTAL).

    Exigir los 5 controles estándar (densidad/pH/olor/color/apariencia) ANTES de
    completar es la posición GMP, pero encenderlo a ciegas traba el piso el mismo
    día: hoy casi ningún lote los registra. Se prende desde /admin/seguridad-planta
    cuando Calidad ya los tome de rutina.

    ⚠ Esto NO gobierna el bloqueo por NO CONFORMIDAD: un estándar marcado 'No
    cumple' frena la liberación SIEMPRE (nadie lo marca por accidente · liberar
    producto con una no conformidad declarada es lo que no puede pasar)."""
    try:
        r = conn.execute("SELECT valor FROM app_settings WHERE clave='exigir_ipc_estandar'").fetchone()
        return bool(r) and str(r[0]).strip() in ("1", "true", "True")
    except Exception as _e:                       # tabla ausente = beta (nunca frenar por esto)
        log.warning("exigir_ipc_estandar no legible: %s", _e)
        return False


def _exige_justificacion_yield(conn) -> bool:
    """Toggle de `app_settings` · default OFF.

    El control ("un rendimiento fuera del 80-115% no se libera sin explicación")
    existía desde antes, pero vivía DENTRO del bloque `EBR_MODE == 'strict'`, y el
    modo real es warn: o sea que hoy un lote al 127% se libera en silencio y el
    control estaba muerto (M119 · un control que vive en un camino por el que no
    pasa el tráfico no es un control).

    Se saca de ahí y se le da interruptor propio, como el de los IPC estándar:
    encenderlo a ciegas trabaría la liberación el mismo día (M126), así que nace
    apagado y, mientras tanto, liberar sin justificar DEJA RASTRO en el audit en
    vez de pasar sin que nadie se entere (M100).
    """
    try:
        r = conn.execute(
            "SELECT valor FROM app_settings WHERE clave='exigir_justificacion_yield'"
        ).fetchone()
        return bool(r) and str(r[0]).strip() in ("1", "true", "True")
    except Exception as _e:
        log.warning("exigir_justificacion_yield no legible: %s", _e)
        return False


def _gate_aprobacion_orden():
    """Si el toggle está ON, un legajo SIN aprobar no deja ejecutar el proceso.

    Devuelve None (sigue) o la respuesta 409. Lee el `ebr_id` de la ruta, así que
    los endpoints que no lo llevan quedan fuera por construcción."""
    # Sólo lo que ESCRIBE: un control de ARRANQUE frena la ejecución, nunca la consulta.
    # Hoy ningún endpoint gateado lee (`ipc-estandar` sirve GET y POST con la misma
    # función, pero su rama GET retorna antes de llamar al guard · verificado, no
    # supuesto). Va igual porque el guard es DEFAULT-DENY y lo hereda todo lo que se
    # escriba después: el día que alguien ponga el guard arriba de un GET+POST
    # compartido, planta perdería una lectura por un permiso administrativo.
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return None
    ebr_id = (request.view_args or {}).get("ebr_id")
    if not ebr_id or request.endpoint in _APROBACION_ORDEN_EXENTOS:
        return None
    conn = get_db()
    if not _exige_aprobacion_orden(conn):
        return None
    # Vale la firma propia del legajo O la de su ORDEN madre (mig 395): el sentido de
    # aprobar el encabezado UNA vez es que valga para TODOS sus lotes. Si se mirara sólo
    # el legajo, la orden aprobada no serviría de nada y habría que firmar lote por lote.
    row = conn.execute(
        "SELECT COALESCE(e.aprobada_orden_por,''), COALESCE(e.lote_codigo, e.lote, ''), "
        "COALESCE(o.aprobada_por,''), COALESCE(o.fase,''), COALESCE(o.aprobada_calidad_por,'') "
        "FROM ebr_ejecuciones e LEFT JOIN ordenes_produccion o ON o.id=e.orden_id "
        "WHERE e.id=?", (ebr_id,)).fetchone()
    if not row:
        return None
    if (row[0] or "").strip():
        return None
    # En acondicionamiento la orden necesita SUS DOS firmas para autorizar el arranque
    # (producción y calidad); con una sola todavía no está aprobada.
    if (row[2] or "").strip() and (row[3] != "acondicionamiento" or (row[4] or "").strip()):
        return None
    if es_lote_demo(row[1]):   # el legajo demo no firma nada
        return None
    return jsonify({
        "error": "La orden todavía no está aprobada · Producción debe autorizarla antes de arrancar",
        "codigo": "ORDEN_SIN_APROBAR"}), 409


def es_lote_demo(valor):
    """¿Este lote es de DEMOSTRACIÓN? · Sebastián 16-ago: *"lo importante es que el demo no pida
    permisos, que me deje probar cada botón, continuar, guardar y seguir los flujos hasta el
    final, así compruebo"*.

    Un demo lo camina UNA persona sola, así que todo control que exija la firma o la
    autorización de OTRO lo vuelve inútil: no se puede comprobar un flujo que se traba en el
    segundo paso esperando a Laura.

    El cálculo estaba copiado a mano en SIETE sitios (`str(x or '').upper().startswith('DEMO-')`)
    y cada copia miraba un campo distinto -- `lote`, `_lote`, `row[2]`... --, así que un gate
    nuevo nacía sin la excepción y el demo se trababa justo ahí (M3/M45). Ahora hay una sola.

    ⚠ Lo que NO afloja: los controles de ESTADO y de DATO (`YA_CERRADO`, `LOTE_DUPLICADO`,
    `CANTIDAD_INVALIDA`, `LEGAJO_INMUTABLE`). Esos no piden permiso a nadie -- dicen "ya lo
    hiciste" o "el dato está mal" -- y en un demo tienen que frenar igual, porque son parte de
    lo que se está comprobando.
    """
    return str(valor or "").strip().upper().startswith("DEMO-")


def _es_demo_ebr(conn, ebr_id):
    """Lo mismo, resolviendo el lote del legajo · para los gates que sólo tienen el id."""
    try:
        r = conn.execute(
            "SELECT COALESCE(lote_codigo, lote, '') FROM ebr_ejecuciones WHERE id=?",
            (ebr_id,)).fetchone()
        return es_lote_demo(r[0] if r else "")
    except Exception:
        # ante la duda NO se afloja: un demo trabado es un fastidio, un lote real sin firma es
        # un registro regulado falso
        return False


def _require_brd_ejecutor():
    """Solo personal que ejecuta lotes: Planta, Calidad o Admin. Evita que
    un usuario de otra área (compras, marketing, RRHH...) ejecute pasos de
    un registro de lote regulado (INVIMA · escalada de privilegios).

    Además aplica el gate de aprobación de la orden (default OFF · ver arriba)."""
    u = session.get("compras_user", "")
    if not u:
        return jsonify({"error": "No autorizado"}), 401
    # FIX 30-jul · ASEGURAMIENTO y DIRECCIÓN TÉCNICA entran. `_batch_role_info` les da
    # `verifica`, `corrige`, `puede_liberar` y al DT `aprueba_dt` desde el 7-jul... pero este
    # gate los rechazaba ANTES de que ninguno de esos flags se leyera, en los 36 endpoints de
    # ejecución. O sea: la 2ª firma del despeje (mig 285), la del material de envase (mig 394)
    # y el visto bueno del Director Técnico (mig 286) estaban construidos y eran INALCANZABLES
    # para las personas que los tienen que dar. Es la 3ª capa del mismo hueco de M116: el
    # permiso del final decía sí y el del principio decía no.
    # No abre la puerta a otras áreas: compras/marketing/RRHH siguen fuera, y `realiza=False`
    # los mantiene fuera de ejecutar pasos de producción (sólo verifican y corrigen).
    try:
        from config import ASEGURAMIENTO_USERS as _AS_BRD, TECNICA_USERS as _T_BRD
    except Exception:
        _AS_BRD, _T_BRD = set(), set()
    if u not in (PLANTA_USERS | CALIDAD_USERS | ADMIN_USERS | set(_AS_BRD) | set(_T_BRD)):
        return jsonify({"error": "Solo Planta/Calidad/Aseguramiento/Dirección Técnica/Admin "
                                 "pueden ejecutar pasos del registro de lote"}), 403
    return _gate_aprobacion_orden()


# Tolerancia por defecto de la conciliación del granel. Configurable en app_settings
# porque el % razonable depende del producto (un suero deja más en la tolva que una
# crema); 2% es el arranque conservador acordado, NO una constante de dominio.
_TOLERANCIA_GRANEL_PCT = 2.0


def _conciliacion_granel(conn, ebr_id, header=None):
    """Cierra la cuenta del granel de un legajo de ENVASADO: ¿en qué terminó?

        entró (mL) = envasado (Σ unidades × mL) + remanente + diferencia sin explicar

    Es la pregunta que hace una auditoría INVIMA y que el legajo hoy no contesta: en la
    OF-2026-77 entraron 12.658,95 mL y salieron 1.000 en unidades; los otros 11.658,95
    no los explicaba ningún registro (puede ser perfectamente legítimo -quedó granel
    para otra orden- pero nadie lo había escrito).

    Todo se DERIVA de datos que ya existen (M71: lo derivado no se guarda). Lo único
    que hay que ir a medir es el REMANENTE, y se captura en GRAMOS porque así se mide
    en piso -con balanza-; los mL salen de la densidad, igual que el granel de entrada.
    """
    h = header or {}
    row = None
    if not h:
        row = conn.execute(
            "SELECT COALESCE(fase,'fabricacion'), ml_envasable, densidad_g_ml, remanente_g, "
            "COALESCE(remanente_destino,''), COALESCE(remanente_observaciones,''), "
            "COALESCE(remanente_por,''), COALESCE(remanente_at_utc,'') "
            "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        if not row:
            return None
        h = {"fase": row[0], "ml_envasable": row[1], "densidad_g_ml": row[2],
             "remanente_g": row[3], "remanente_destino": row[4],
             "remanente_observaciones": row[5], "remanente_por": row[6],
             "remanente_at_utc": row[7]}
    if str(h.get("fase") or "").strip().lower() != "envasado":
        return None                      # la conciliación de granel es del envasado

    def _f(v):
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    disponible = _f(h.get("ml_envasable"))
    densidad = _f(h.get("densidad_g_ml"))
    remanente_g = _f(h.get("remanente_g"))

    # ── El granel REAL de fabricación viaja solo al envasado (Sebastián 29-jul) ──
    # *"al final de la producción que aparezca peso total del granel, así en envasado ya
    # va con un teórico para cálculo de rendimiento"*. Sin esto la cadena está cortada:
    # el peso real existe en la OP y el envasado esperaba que alguien lo tecleara -- y lo
    # tecleado es lo primero que queda viejo (M9). Se toma del legajo de FABRICACIÓN del
    # MISMO lote físico (`lote_codigo` · M10: la llave del OF va sufijada, el lote no).
    origen_granel = "legajo" if disponible else None
    if not disponible:
        _lote_fis = (h.get("lote_codigo") or "").strip()
        if _lote_fis:
            try:
                _op = conn.execute(
                    "SELECT cantidad_real_g, densidad_g_ml, ml_envasable FROM ebr_ejecuciones "
                    "WHERE COALESCE(lote_codigo, lote)=? AND COALESCE(fase,'fabricacion')='fabricacion' "
                    "ORDER BY id DESC LIMIT 1", (_lote_fis,)).fetchone()
                if _op:
                    densidad = densidad or _f(_op[1])
                    _ml_op = _f(_op[2])
                    if not _ml_op and _f(_op[0]) and densidad:
                        _ml_op = round(_f(_op[0]) / densidad, 2)
                    if _ml_op:
                        disponible, origen_granel = _ml_op, "fabricacion"
            except Exception as _e:
                log.warning("puente granel OP->OF (lote %s) no disponible: %s", _lote_fis, _e)

    presentaciones, envasado_ml, sin_volumen = [], 0.0, 0
    for r in conn.execute(
        "SELECT COALESCE(presentacion_codigo,''), COALESCE(etiqueta,''), COALESCE(volumen_ml,0), "
        "COALESCE(unidades,0), COALESCE(no_envasada,0) "
        "FROM ebr_envasado_unidades WHERE ebr_id=? ORDER BY presentacion_codigo", (ebr_id,)).fetchall():
        uds, vol = float(r[3] or 0), float(r[2] or 0)
        if r[4] or uds <= 0:
            continue
        if vol <= 0:
            sin_volumen += 1             # sin volumen no se puede pesar la cuenta (se declara)
            continue
        sub = round(uds * vol, 2)
        envasado_ml += sub
        presentaciones.append({"codigo": r[0], "etiqueta": r[1], "volumen_ml": vol,
                               "unidades": uds, "subtotal_ml": sub})
    envasado_ml = round(envasado_ml, 2)

    # Unidades TEÓRICAS y rendimiento · derivados del granel que entró (M71: lo derivado
    # no se guarda). Es para lo que sirve el teórico: cuántas unidades DEBERÍAN haber
    # salido de ese granel, y cuántas salieron. Con una sola presentación el teórico es
    # exacto; con varias no se puede repartir el granel sin inventar un criterio, así que
    # se declara el teórico TOTAL en mL y no se parte por presentación (M8: si no se puede
    # scopear bien, no se reparte).
    unidades_teoricas = rendimiento_uds_pct = None
    if disponible and len(presentaciones) == 1 and presentaciones[0]["volumen_ml"] > 0:
        unidades_teoricas = int(disponible // presentaciones[0]["volumen_ml"])
        presentaciones[0]["unidades_teoricas"] = unidades_teoricas
        if unidades_teoricas:
            rendimiento_uds_pct = round(
                presentaciones[0]["unidades"] / unidades_teoricas * 100, 2)
            presentaciones[0]["rendimiento_pct"] = rendimiento_uds_pct
    # El rendimiento en VOLUMEN sí vale con cualquier cantidad de presentaciones: es el
    # granel que terminó en unidades sobre el que entró.
    rendimiento_ml_pct = (round(envasado_ml / disponible * 100, 2)
                          if disponible else None)

    # El remanente se PESA; los mL se derivan. Sin densidad no hay conversión posible:
    # se declara el gramaje y la cuenta queda abierta (M109: sin dato no se inventa).
    remanente_ml = round(remanente_g / densidad, 2) if (remanente_g is not None and densidad) else None

    try:
        _t = conn.execute(
            "SELECT valor FROM app_settings WHERE clave='conciliacion_granel_tolerancia_pct'").fetchone()
        tolerancia = float(_t[0]) if _t and str(_t[0]).strip() else _TOLERANCIA_GRANEL_PCT
    except Exception:
        tolerancia = _TOLERANCIA_GRANEL_PCT

    diferencia = pct = None
    if disponible is not None:
        diferencia = round(disponible - envasado_ml - (remanente_ml or 0.0), 2)
        pct = round(diferencia / disponible * 100, 2) if disponible else None

    # `cuadra` sólo puede ser True cuando la cuenta está COMPLETA: sin remanente
    # declarado, un 0 de diferencia sería casualidad, no conciliación.
    completa = disponible is not None and remanente_ml is not None and not sin_volumen
    cuadra = bool(completa and pct is not None and abs(pct) <= tolerancia)
    return {
        "aplica": True,
        "disponible_ml": disponible,
        "envasado_ml": envasado_ml,
        "remanente_g": remanente_g,
        "remanente_ml": remanente_ml,
        "remanente_destino": h.get("remanente_destino") or "",
        "remanente_observaciones": h.get("remanente_observaciones") or "",
        "remanente_por": h.get("remanente_por") or "",
        "remanente_at_utc": h.get("remanente_at_utc") or "",
        "diferencia_ml": diferencia,
        "diferencia_pct": pct,
        "tolerancia_pct": tolerancia,
        "densidad_g_ml": densidad,
        "origen_granel": origen_granel,          # 'fabricacion' = vino solo del lote de OP
        "unidades_teoricas": unidades_teoricas,
        "rendimiento_uds_pct": rendimiento_uds_pct,
        "rendimiento_ml_pct": rendimiento_ml_pct,
        "presentaciones": presentaciones,
        "presentaciones_sin_volumen": sin_volumen,
        "falta_densidad": bool(remanente_g is not None and not densidad),
        "falta_remanente": remanente_g is None,
        "completa": completa,
        "cuadra": cuadra,
    }


# Destinos válidos del remanente. Whitelist explícita (regla: un campo de estado se
# valida contra una lista, no acepta cualquier string) · el texto libre va en las
# observaciones, que es donde puede ir cualquier cosa sin romper una agrupación (M115).
_REMANENTE_DESTINOS = {
    "otra_orden": "Queda en bodega para otra orden",
    "devuelto_granel": "Devuelto al granel del lote",
    "muestra_retenida": "Muestra de retención / contramuestra",
    "descartado": "Descartado (merma)",
    "sin_remanente": "No quedó remanente",
}


# ── helpers data ────────────────────────────────────────────────────────────

def _mbr_to_dict(row, pasos=None):
    d = {
        "id": row["id"],
        "producto_nombre": row["producto_nombre"],
        "formula_version_id": row["formula_version_id"],
        "version": row["version"],
        "estado": row["estado"],
        "titulo": row["titulo"] or "",
        "descripcion": row["descripcion"] or "",
        "lote_size_g": row["lote_size_g"],
        "tiempo_total_estimado_min": row["tiempo_total_estimado_min"] or 0,
        "creado_por": row["creado_por"],
        "creado_at_utc": row["creado_at_utc"],
        "updated_at_utc": row["updated_at_utc"],
        "aprobado_por": row["aprobado_por"] or "",
        "aprobado_at_utc": row["aprobado_at_utc"],
        "aprobado_signature_id": row["aprobado_signature_id"],
        "obsoleto_at_utc": row["obsoleto_at_utc"],
        "obsoleto_motivo": row["obsoleto_motivo"] or "",
    }
    if pasos is not None:
        d["pasos"] = [_paso_to_dict(p) for p in pasos]
    return d


def _paso_to_dict(row):
    return {
        "id": row["id"],
        "mbr_template_id": row["mbr_template_id"],
        "orden": row["orden"],
        "fase": row["fase"] or "",
        "descripcion": row["descripcion"],
        "tipo_paso": row["tipo_paso"] or "otro",
        "equipo_requerido": row["equipo_requerido"] or "",
        "tiempo_estimado_min": row["tiempo_estimado_min"] or 0,
        "requiere_e_sign": int(row["requiere_e_sign"] or 0),
        "requiere_qc": int(row["requiere_qc"] or 0),
        "notas": row["notas"] or "",
    }


def _next_version(conn, producto):
    row = conn.execute(
        "SELECT MAX(version) FROM mbr_templates WHERE producto_nombre = ?",
        (producto,),
    ).fetchone()
    return int(row[0] or 0) + 1


def assign_numero_op(c, year=None):
    """Genera atómicamente el siguiente numero_op MyBatch-compat.

    Format: 'OP-YYYY-NNNN' (4 dígitos zero-padded).

    Usa tabla op_counters (mig 117) como counter atómico por año. SQLite WAL
    serializa los writes · safe ante races concurrentes (worker A y B
    bloquean uno al otro mientras hacen UPDATE op_counters).

    Reset implícito de año: la primera vez que se llama con un año nuevo
    se inserta fila counter=0 y arranca en 1. No hay reset manual.

    El cursor debe ser de una transacción viva (caller debe hacer commit
    después de la INSERT INTO ebr_ejecuciones que use el numero_op
    retornado · si rollback, op_counters queda con el counter incrementado
    pero ese numero queda sin uso · es comportamiento aceptable porque
    Part 11 no exige numeros contiguos, solo únicos).
    """
    if year is None:
        from datetime import datetime as _dt, timezone as _tz
        year = _dt.now(_tz.utc).year
    c.execute(
        "INSERT OR IGNORE INTO op_counters (year, counter) VALUES (?, 0)",
        (year,),
    )
    c.execute(
        """UPDATE op_counters
           SET counter = counter + 1,
               updated_at_utc = datetime('now', 'utc')
           WHERE year = ?""",
        (year,),
    )
    counter = c.execute(
        "SELECT counter FROM op_counters WHERE year = ?", (year,),
    ).fetchone()[0]
    return f"OP-{year}-{counter:04d}"


# ── endpoints ───────────────────────────────────────────────────────────────

@bp.route("/api/brd/cuarentena-explicita", methods=["GET"])
def brd_cuarentena_explicita():
    """MyBatch parity Sprint E · 21-may-2026 · Estado cuarentena explícito.

    Lista TODOS los EBRs en cuarentena (completados pero no liberados):
    - lote · producto · fecha completado · días en cuarentena
    - flag bandera_roja si >7 días sin liberar
    - acción: link al detalle + botón liberar/rechazar visible
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    try:
        # FIX · 21-may-2026 · usar COALESCE(lote_codigo, lote) + COALESCE(operario, iniciado_por)
        # · compat con BD sin mig 153 aplicada (aliases nuevos)
        rows = conn.execute(
            """SELECT e.id,
                      COALESCE(e.lote_codigo, e.lote) AS lote_codigo,
                      e.completado_at_utc,
                      COALESCE(e.operario, e.iniciado_por) AS operario,
                      mb.producto_nombre,
                      julianday('now','-5 hours') - julianday(e.completado_at_utc) as dias
               FROM ebr_ejecuciones e
               LEFT JOIN mbr_templates mb ON mb.id = e.mbr_template_id
               WHERE e.estado = 'completado'
                 AND e.completado_at_utc IS NOT NULL
                 AND (e.liberado_at_utc IS NULL OR e.liberado_at_utc = '')
                 AND (COALESCE(e.rechazado_at_utc,'') = '')
               ORDER BY e.completado_at_utc ASC""",
        ).fetchall()
    except Exception as e:
        return jsonify({'error': f'query fallo: {e}'}), 500
    items = []
    bandera_roja_count = 0
    for r in rows:
        dias = round(float(r[5] or 0), 1) if r[5] else 0
        bandera = dias > 7
        if bandera:
            bandera_roja_count += 1
        items.append({
            'ebr_id': r[0], 'lote': r[1] or '',
            'completado_at_utc': r[2] or '',
            'operario': r[3] or '',
            'producto': r[4] or '',
            'dias_en_cuarentena': dias,
            'bandera_roja': bandera,
        })
    # Estadísticas adicionales: rechazados últimos 30d
    rechazados_30d = 0
    try:
        # FIX · 21-may-2026 · cutoff Python (date multi-arg falla en PG)
        from datetime import datetime as _dtbrd2, timedelta as _tdbrd2
        cutoff_30d = (_dtbrd2.now() - _tdbrd2(days=30)).date().isoformat()
        rechazados_30d = int((conn.execute(
            """SELECT COUNT(*) FROM ebr_ejecuciones
               WHERE COALESCE(rechazado_at_utc,'') != ''
                 AND date(rechazado_at_utc) >= ?""",
            (cutoff_30d,),
        ).fetchone() or [0])[0])
    except Exception:
        pass
    return jsonify({
        'items': items,
        'total_cuarentena': len(items),
        'bandera_roja_count': bandera_roja_count,
        'rechazados_30d': rechazados_30d,
    })


@bp.route("/api/brd/dashboard-estados", methods=["GET"])
def brd_dashboard_estados():
    """MyBatch parity Sprint A · 21-may-2026 · Sebastián.

    Reemplaza la pantalla INICIO de MyBatch · muestra:
    - Counts de MBRs por estado (draft / en_revision / aprobado / obsoleto)
    - Counts de EBRs (ejecuciones) por estado (iniciado / en_curso / completado)
    - Productos sin MBR aprobado (gap crítico)
    - Próximos vencimientos de MBR (>6 meses sin revisión)
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    out = {'mbr': {}, 'ebr': {}, 'gaps': [], 'vencimientos': []}
    # MBR por estado
    try:
        rows = conn.execute(
            "SELECT estado, COUNT(*) FROM mbr_templates GROUP BY estado",
        ).fetchall()
        for r in rows:
            out['mbr'][r[0] or 'sin_estado'] = int(r[1] or 0)
    except Exception:
        pass
    # Total productos vs productos con MBR aprobado
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM formula_headers WHERE COALESCE(activo,1)=1",
        ).fetchone()
        con_mbr = conn.execute(
            """SELECT COUNT(DISTINCT fh.producto_nombre)
               FROM formula_headers fh
               JOIN mbr_templates mb ON mb.producto_nombre = fh.producto_nombre
                                    AND mb.estado = 'aprobado'
               WHERE COALESCE(fh.activo,1)=1""",
        ).fetchone()
        out['productos_total'] = int(total[0] or 0) if total else 0
        out['productos_con_mbr_aprobado'] = int(con_mbr[0] or 0) if con_mbr else 0
        out['cobertura_pct'] = round(
            (out['productos_con_mbr_aprobado'] / out['productos_total'] * 100)
            if out['productos_total'] else 0, 1
        )
    except Exception:
        out['productos_total'] = 0
        out['productos_con_mbr_aprobado'] = 0
        out['cobertura_pct'] = 0
    # Productos SIN MBR aprobado (gap)
    try:
        rows = conn.execute(
            """SELECT fh.producto_nombre
               FROM formula_headers fh
               WHERE COALESCE(fh.activo,1)=1
                 AND fh.producto_nombre NOT IN (
                   SELECT producto_nombre FROM mbr_templates WHERE estado='aprobado'
                 )
               ORDER BY fh.producto_nombre LIMIT 20""",
        ).fetchall()
        out['gaps'] = [r[0] for r in rows]
    except Exception:
        pass
    # EBR ejecuciones por estado
    try:
        rows = conn.execute(
            "SELECT estado, COUNT(*) FROM ebr_ejecuciones GROUP BY estado",
        ).fetchall()
        for r in rows:
            out['ebr'][r[0] or 'sin_estado'] = int(r[1] or 0)
    except Exception:
        pass
    # MBR aprobados hace >180d sin revisión
    try:
        rows = conn.execute(
            """SELECT producto_nombre, version, aprobado_at_utc
               FROM mbr_templates
               WHERE estado='aprobado'
                 AND COALESCE(aprobado_at_utc,'') != ''
                 AND date(aprobado_at_utc) < date('now','-180 days')
               ORDER BY aprobado_at_utc ASC LIMIT 20""",
        ).fetchall()
        out['vencimientos'] = [
            {'producto': r[0], 'version': r[1], 'aprobado': r[2]}
            for r in rows
        ]
    except Exception:
        pass
    return jsonify(out)


@bp.route("/api/brd/mbr", methods=["GET"])
def listar_mbr():
    err = _require_login()
    if err:
        return err
    producto = (request.args.get("producto") or "").strip()
    estado = (request.args.get("estado") or "").strip()
    where = []
    params = []
    if producto:
        where.append("producto_nombre = ?")
        params.append(producto)
    if estado:
        where.append("estado = ?")
        params.append(estado)
    sql = """SELECT id, producto_nombre, formula_version_id, version, estado,
                    titulo, descripcion, lote_size_g, tiempo_total_estimado_min,
                    creado_por, creado_at_utc, updated_at_utc,
                    aprobado_por, aprobado_at_utc, aprobado_signature_id,
                    obsoleto_at_utc, obsoleto_motivo
             FROM mbr_templates"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY producto_nombre, version DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"items": [_mbr_to_dict(r) for r in rows]})


@bp.route("/api/brd/mbr/<int:mbr_id>", methods=["GET"])
def detalle_mbr(mbr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    row = conn.execute(
        """SELECT id, producto_nombre, formula_version_id, version, estado,
                  titulo, descripcion, lote_size_g, tiempo_total_estimado_min,
                  creado_por, creado_at_utc, updated_at_utc,
                  aprobado_por, aprobado_at_utc, aprobado_signature_id,
                  obsoleto_at_utc, obsoleto_motivo
           FROM mbr_templates WHERE id = ?""",
        (mbr_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "MBR no encontrado"}), 404
    pasos = conn.execute(
        """SELECT id, mbr_template_id, orden, fase, descripcion, tipo_paso,
                  equipo_requerido, tiempo_estimado_min, requiere_e_sign,
                  requiere_qc, notas
           FROM mbr_pasos WHERE mbr_template_id = ? ORDER BY orden""",
        (mbr_id,),
    ).fetchall()
    return jsonify(_mbr_to_dict(row, pasos))


def _mbr_doc_helpers():
    """Helpers de render de documento regulado (los mismos que F01/F02 · un solo look).

    Import perezoso para no acoplar el módulo en el arranque. Si por alguna razón no
    resuelven, devuelve un juego mínimo: un documento regulado nunca debe caerse.
    """
    try:
        from blueprints.calidad import _rc_doc_css, _rc_head, _rc_fld, _rc_firma, _rc_fecha_firma, _e
    except Exception:
        try:
            from api.blueprints.calidad import _rc_doc_css, _rc_head, _rc_fld, _rc_firma, _rc_fecha_firma, _e
        except Exception:
            import html as _h
            _e = lambda v: _h.escape(str(v if v is not None else ''))
            _rc_doc_css = lambda: "<style>body{font-family:Arial,sans-serif;font-size:12px}</style>"
            _rc_head = lambda t, c, x='': f"<h2>{_e(t)}</h2><div>{_e(c)} {_e(x)}</div>"
            _rc_fld = lambda k, v: f"<div><b>{_e(k)}:</b> {_e(v)}</div>"
            _rc_firma = lambda c, v: ''
            _rc_fecha_firma = lambda v: ''
    return _rc_doc_css, _rc_head, _rc_fld, _rc_firma, _rc_fecha_firma, _e


@bp.route("/api/brd/mbr/<int:mbr_id>/imprimible", methods=["GET"])
def mbr_imprimible(mbr_id):
    """MBR imprimible · el procedimiento maestro APROBADO como documento auditable (INVIMA/GMP).

    Es el documento que una auditoría pide junto al batch record: qué procedimiento estaba
    aprobado, en qué versión, y QUIÉN lo aprobó. La firma electrónica (e_signatures) es el
    control legal §11.200; acá se estampa además la RÚBRICA MANUSCRITA del aprobador
    (manifestación visible §11.50), igual que en el F01/F02 y el batch record.
    """
    err = _require_login()
    if err:
        return err
    _css, _head, _fld, _firma, _fecha_firma, _e = _mbr_doc_helpers()
    conn = get_db()
    m = conn.execute(
        """SELECT id, producto_nombre, formula_version_id, version, estado, titulo, descripcion,
                  lote_size_g, tiempo_total_estimado_min, creado_por, creado_at_utc,
                  COALESCE(aprobado_por,'') AS aprobado_por, aprobado_at_utc, aprobado_signature_id,
                  obsoleto_at_utc, COALESCE(obsoleto_motivo,'') AS obsoleto_motivo
             FROM mbr_templates WHERE id = ?""",
        (mbr_id,),
    ).fetchone()
    if not m:
        return Response("<p style='font-family:sans-serif;padding:40px'>No existe el MBR solicitado.</p>",
                        mimetype="text/html", status=404)
    pasos = conn.execute(
        """SELECT orden, COALESCE(fase,'') AS fase, descripcion, COALESCE(tipo_paso,'') AS tipo_paso,
                  COALESCE(equipo_requerido,'') AS equipo_requerido,
                  COALESCE(tiempo_estimado_min,0) AS tiempo_estimado_min,
                  COALESCE(requiere_e_sign,0) AS requiere_e_sign, COALESCE(requiere_qc,0) AS requiere_qc
             FROM mbr_pasos WHERE mbr_template_id = ? ORDER BY orden""",
        (mbr_id,),
    ).fetchall()
    specs = conn.execute(
        """SELECT parametro, COALESCE(unidad,'') AS unidad, valor_min, valor_max,
                  COALESCE(metodo,'') AS metodo, COALESCE(obligatorio,0) AS obligatorio
             FROM ipc_specs WHERE mbr_template_id = ? ORDER BY id""",
        (mbr_id,),
    ).fetchall()
    # Identidad del aprobador tomada de la e_signature (snapshot legal del momento de firmar).
    sig = None
    if m["aprobado_signature_id"]:
        sig = conn.execute(
            "SELECT signer_username, COALESCE(signer_full_name,'') AS signer_full_name, "
            "COALESCE(signer_cedula,'') AS signer_cedula, COALESCE(signer_cargo,'') AS signer_cargo, "
            "signed_at_utc, COALESCE(signature_hash,'') AS signature_hash "
            "FROM e_signatures WHERE id = ?", (m["aprobado_signature_id"],)).fetchone()

    estado = (m["estado"] or "").lower()
    est_cls = "ok" if estado == "aprobado" else ("no" if estado == "obsoleto" else "")
    est_txt = {"aprobado": "APROBADO Y VIGENTE", "draft": "BORRADOR (sin valor regulatorio)",
               "en_revision": "EN REVISIÓN (aún sin aprobar)",
               "obsoleto": "OBSOLETO (no usar para fabricar)"}.get(estado, (m["estado"] or "-").upper())
    _tipo = {"pesaje": "Pesaje", "dispensacion": "Dispensación", "mezclado": "Mezclado",
             "caliente": "Fase caliente", "enfriamiento": "Enfriamiento", "control_ipc": "Control IPC",
             "envasado": "Envasado", "inspeccion": "Inspección", "limpieza": "Limpieza", "otro": ""}
    filas_p = "".join(
        "<tr><td style='text-align:center;font-weight:700'>%s</td><td>%s</td><td>%s%s</td>"
        "<td>%s</td><td style='text-align:center'>%s</td><td style='text-align:center'>%s</td></tr>"
        % (p["orden"], _e(p["fase"] or "-"), _e(p["descripcion"]),
           ("<br><span style='color:#8b8b9e;font-size:9.5px'>Equipo: %s</span>" % _e(p["equipo_requerido"]))
           if p["equipo_requerido"] else "",
           _e(_tipo.get(p["tipo_paso"], p["tipo_paso"])),
           (str(p["tiempo_estimado_min"]) if p["tiempo_estimado_min"] else "-"),
           ("Operario + QC" if p["requiere_qc"] else ("Operario" if p["requiere_e_sign"] else "-")))
        for p in pasos)
    _rango = lambda a, b: ("%s a %s" % (a, b)) if (a is not None and b is not None) else (
        ("mín %s" % a) if a is not None else (("máx %s" % b) if b is not None else "-"))
    filas_s = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td style='text-align:center'>%s</td></tr>"
        % (_e(s["parametro"]), _e(_rango(s["valor_min"], s["valor_max"])), _e(s["unidad"] or "-"),
           _e(s["metodo"] or "-"), ("Sí" if s["obligatorio"] else "No"))
        for s in specs)

    _ap_nom = (sig["signer_full_name"] if (sig and sig["signer_full_name"]) else (m["aprobado_por"] or ""))
    _ap_user = (sig["signer_username"] if sig else (m["aprobado_por"] or ""))
    _ap_meta = ""
    if sig:
        _ap_meta = ("<span style='display:block;color:#a1a1b0;font-size:9px;margin-top:2px'>"
                    "C.C. %s · %s · firma electrónica #%s</span>"
                    % (_e(sig["signer_cedula"] or "-"), _e(sig["signer_cargo"] or "-"),
                       _e(m["aprobado_signature_id"])))
    body = (_css() + _head("Registro maestro de lote (MBR)", "MBR v%s" % _e(m["version"]),
                           m["producto_nombre"])
            + ("<div class='res %s'>Estado del maestro: %s</div>" % (est_cls, _e(est_txt)))
            + "<div class='grid'>"
            + _fld("Producto", m["producto_nombre"]) + _fld("Versión del maestro", "v%s" % m["version"])
            + _fld("Tamaño de lote (referencia)", "%s g" % format(int(m["lote_size_g"] or 0), ",d").replace(",", "."))
            + _fld("Tiempo estimado", "%s min" % (m["tiempo_total_estimado_min"] or 0))
            + _fld("Fórmula vinculada", m["formula_version_id"] or "-")
            + _fld("Pasos del procedimiento", len(pasos))
            + "</div>"
            + ((f"<div class='fld'><span class='k'>Título</span><span class='v'>{_e(m['titulo'])}</span></div>") if m["titulo"] else "")
            + ((f"<div class='fld'><span class='k'>Descripción</span><span class='v'>{_e(m['descripcion'])}</span></div>") if m["descripcion"] else "")
            + (("<table><thead><tr><th style='width:38px'>#</th><th style='width:110px'>Fase</th>"
                "<th>Instrucción</th><th style='width:100px'>Tipo</th><th style='width:52px'>Min</th>"
                "<th style='width:96px'>Firma</th></tr></thead><tbody>" + filas_p + "</tbody></table>")
               if pasos else "<p style='color:var(--cx-warn-text, #b45309)'>Este maestro no tiene pasos cargados.</p>")
            + (("<table><thead><tr><th>Control en proceso (IPC)</th><th style='width:130px'>Especificación</th>"
                "<th style='width:80px'>Unidad</th><th style='width:150px'>Método</th>"
                "<th style='width:80px'>Obligatorio</th></tr></thead><tbody>" + filas_s + "</tbody></table>")
               if specs else "")
            + ((("<div class='res no'>Maestro OBSOLETADO el %s · motivo: %s</div>")
                % (_e((m["obsoleto_at_utc"] or "")[:19]), _e(m["obsoleto_motivo"] or "-"))) if m["obsoleto_at_utc"] else "")
            + "<div class='firmas'>"
            + ("<div class='firma'>%s<b>%s</b>Elabora el maestro%s</div>"
               % (_firma(conn, m["creado_por"]), _e(m["creado_por"] or "-"),
                  _fecha_firma((m["creado_at_utc"] or "")[:19])))
            + ("<div class='firma'>%s<b>%s</b>Aprueba · Aseguramiento / Control de Calidad%s%s</div>"
               % (_firma(conn, _ap_user), _e(_ap_nom or "-"),
                  _fecha_firma(((sig["signed_at_utc"] if sig else m["aprobado_at_utc"]) or "")[:19]), _ap_meta))
            + "</div>"
            + "<p style='margin-top:18px;font-size:9px;color:var(--cx-text-faint, #94a3b8)'>Documento generado desde EOS · "
            + "la firma electrónica (21 CFR Part 11 §11.200) es el control legal · la rúbrica es su "
            + "manifestación visible (§11.50).</p>"
            + "<div class='noimp'><button onclick='window.print()'>🖨️ Imprimir / Guardar PDF</button></div>")
    return Response(body, mimetype="text/html")


@bp.route("/api/brd/mbr", methods=["POST"])
def crear_mbr():
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    producto = (body.get("producto_nombre") or "").strip()
    if not producto:
        return jsonify({"error": "producto_nombre requerido"}), 400
    try:
        lote_size_g = float(body.get("lote_size_g") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "lote_size_g inválido"}), 400
    if lote_size_g <= 0:
        return jsonify({"error": "lote_size_g debe ser > 0"}), 400

    conn = get_db()
    cur = conn.cursor()
    version = _next_version(conn, producto)
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO mbr_templates
             (producto_nombre, formula_version_id, version, estado,
              titulo, descripcion, lote_size_g, tiempo_total_estimado_min,
              creado_por)
           VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, ?)""",
        (producto,
         body.get("formula_version_id"),
         version,
         (body.get("titulo") or f"{producto} v{version}").strip(),
         (body.get("descripcion") or "").strip(),
         lote_size_g,
         int(body.get("tiempo_total_estimado_min") or 0),
         user),
    )
    mbr_id = cur.lastrowid
    conn.commit()
    audit_log(None, usuario=user, accion="CREATE_MBR_DRAFT",
              tabla="mbr_templates", registro_id=mbr_id,
              despues={"producto": producto, "version": version})
    return jsonify({"ok": True, "id": mbr_id, "version": version}), 201


_INSTRUCTIVO_SUERO_MULTIP = """En un recipiente con capacidad adecuada, adicionar con agitación constante y a temperatura ambiente: Agua (60% de la fórmula), Niacinamida, Gluconolactona y Glucosamina.
Adicionar uno por uno hasta total disolución (no adicionar la siguiente MP si la anterior no se disolvió). En esta primera parte ajustar el pH = 6.0 con Trietanolamina. pH final: ___ · Cantidad de TEA: ___ ml.
Una vez ajustado el pH, adicionar lentamente y con agitación constante: Glicina, Copper tripeptide-1, Glutatión, Adenosina, PDRN, Dipeptide Diaminobutiroil benzalamida diacetato.
Adicionar uno por uno hasta total disolución. En esta segunda parte ajustar el pH = 6.0 con Trietanolamina. pH final: ___ · Cantidad de TEA: ___ ml.
Seguir agitando manteniendo el pH.
Finalmente, adicionar con agitación constante y temperatura ambiente: Acetyl tetrapeptide-5, Acetyl hexapeptido-8, Palmitoyl Tripeptide-5, Colágeno hidrolizado, EDTA disódico. Verificar pH=6.0 y ajustar con TEA si es necesario.
En otro recipiente, calentar el Propilenglicol a ~60°C. Al llegar a esa temperatura adicionar: Palmitoyl tripeptide-1, Palmitoyl tetrapeptide-7, Palmitoyl Pentapeptide-4.
Enfriar de forma rápida; luego agregar esta solución a los Ácidos hialurónicos 50KDa, 300KDa y 1500KDa hasta total dispersión.
Agregar esta dispersión con agitación constante al resto del agua de la fórmula (40%) y seguir agitando 20 minutos más, hasta total hidratación.
Usar la batidora de mano para total homogenización y disolución de los péptidos.
Una vez hidratados los AH y a temperatura menor de 40°C, adicionar la mezcla anterior suavemente y con agitación constante a la fase acuosa inicial.
Adicionar a la mezcla anterior, con agitación constante: Gransil VX 419 y Biosure FE.
Verificar pH=6.0 y ajustar con TEA si es necesario. pH final: ___ · TEA: ___ ml. Seguir agitando 20 minutos más. Tiempo real: ___ min."""


@bp.route("/admin/cargar-instructivo", methods=["GET"])
def cargar_instructivo_page():
    """Página simple para cargar el instructivo de fabricación (pasos de proceso) en el MBR de un producto."""
    err = _require_qa_or_admin()
    if err:
        return err
    try:
        prods = [r[0] for r in get_db().execute(
            "SELECT DISTINCT producto_nombre FROM mbr_templates ORDER BY producto_nombre").fetchall()]
    except Exception:
        prods = []
    import html as _html
    opts = "".join(
        f'<option value="{_html.escape(p)}"{" selected" if "MULTIP" in (p or "").upper() else ""}>{_html.escape(p)}</option>'
        for p in prods)
    pre = _html.escape(_INSTRUCTIVO_SUERO_MULTIP)
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cargar instructivo de fabricación</title>
<style>body{{font-family:system-ui,Segoe UI,Arial;background:#0f0f14;color:#e7e7ea;margin:0;padding:24px 14px}}
.wrap{{max-width:780px;margin:0 auto}}h1{{font-size:19px;color:var(--cx-primary-light, #a78bfa)}}label{{display:block;font-size:13px;color:#a1a1aa;margin:14px 0 5px;font-weight:700}}
select,textarea{{width:100%;box-sizing:border-box;background:#1a1a22;color:#e7e7ea;border:1px solid #34343f;border-radius:9px;padding:11px;font-size:14px}}
textarea{{min-height:300px;line-height:1.5;font-family:inherit}}button{{margin-top:16px;background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;border:none;border-radius:9px;padding:13px 22px;font-size:15px;font-weight:800;cursor:pointer}}
.hint{{font-size:12px;color:#71717a;margin-top:6px}}#res{{margin-top:16px;font-size:14px;font-weight:700;min-height:22px}}</style></head>
<body><div class="wrap">
<h1>📋 Cargar instructivo de fabricación al MBR</h1>
<p class="hint">Cada línea = un paso del proceso de mezcla. El dispensado de MP sale solo de la fórmula (sección 3). Si el MBR está aprobado, se crea una versión NUEVA en borrador (la apruebás después con e-firma).</p>
<div style="background:#17171f;border:1px solid #3a2f5a;border-radius:11px;padding:14px;margin:0 0 18px">
<b style="color:var(--cx-primary-light, #a78bfa)">&#9889; Cargar TODOS los instructivos de una vez</b>
<p class="hint" style="margin-top:6px">Carga los instructivos capturados a sus MBR. Los que est&aacute;n aprobados generan una versi&oacute;n NUEVA en borrador (Calidad la aprueba con e-firma · la activa sigue vigente hasta entonces).</p>
<button onclick="verTodos()" style="margin-top:8px">Ver resumen</button>
<button onclick="cargarTodos()" id="btnTodos" disabled style="margin-top:8px;background:#3a2f1a;color:var(--cx-accent, #fbbf24)">1) Cargar TODOS</button>
<button onclick="aprobarTodos()" id="btnAprobar" style="margin-top:8px;background:linear-gradient(135deg,#059669,#047857);color:#fff">2) Aprobar TODOS (e-firma)</button>
<div id="resTodos" class="hint" style="margin-top:10px"></div>
<p class="hint" style="margin-top:6px">Los instructivos vienen del batch record ya aprobado por Direcci&oacute;n T&eacute;cnica. "Aprobar TODOS" los pone activos con tu e-firma (la versi&oacute;n anterior se obsoleta) &middot; ah&iacute; ya salen en las fabricaciones.</p>
</div>
<label>Producto (MBR destino) · o cargá uno solo</label><select id="prod">{opts}</select>
<label>Pasos del proceso (uno por línea)</label><textarea id="pasos">{pre}</textarea>
<div class="hint">Pre-cargado: instructivo del Suero Multipéptidos (de tu PDF). Editá o cambiá de producto.</div>
<button onclick="cargar()">✓ Cargar instructivo</button>
<div id="res"></div>
</div>
<script>
var _todosOK=false;
async function verTodos(){{
  var res=document.getElementById('resTodos'); res.style.color='#a1a1aa'; res.textContent='Cargando resumen...';
  try{{
    var r=await fetch('/api/brd/mbr/cargar-todos-instructivos',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:'{{}}'}});
    var d=await r.json();
    if(!r.ok){{ res.style.color='#f87171'; res.textContent='Error: '+(d.error||r.status); return; }}
    var sm=(d.sin_mbr||[]);
    res.style.color='#a1a1aa';
    res.innerHTML='Con MBR: <b style="color:#e7e7ea">'+d.con_mbr+'</b> de '+d.total+(sm.length?(' &middot; sin MBR (se saltan): '+sm.join(', ')):' &middot; todos tienen MBR');
    _todosOK=(d.con_mbr>0);
    document.getElementById('btnTodos').disabled=!_todosOK;
  }}catch(e){{ res.style.color='#f87171'; res.textContent='Error de red'; }}
}}
async function cargarTodos(){{
  if(!_todosOK) return;
  if(!confirm('Cargar los instructivos a todos los MBR? Los aprobados generan una version nueva en borrador que Calidad aprueba con e-firma.')) return;
  var b=document.getElementById('btnTodos'); b.disabled=true;
  var res=document.getElementById('resTodos'); res.style.color='#a1a1aa'; res.textContent='Cargando...';
  try{{
    var r=await fetch('/api/brd/mbr/cargar-todos-instructivos',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{aplicar:true,confirmar:'SI'}})}});
    var d=await r.json();
    if(r.ok&&d.aplicado){{ res.style.color='#34d399'; res.textContent='OK: '+d.cargados+' instructivos cargados ('+d.nuevas_versiones+' versiones nuevas en borrador, '+d.reemplazados+' borradores). Aprobalos con e-firma en el modulo MBR.'; }}
    else {{ res.style.color='#f87171'; res.textContent='Error: '+(d.error||d.detalle||r.status); b.disabled=false; }}
  }}catch(e){{ res.style.color='#f87171'; res.textContent='Error de red'; b.disabled=false; }}
}}
async function aprobarTodos(){{
  if(!confirm('Aprobar con tu e-firma las versiones nuevas con instructivo? Vienen del batch record ya aprobado por Direccion Tecnica. Quedan como version activa (la anterior se obsoleta).')) return;
  var b=document.getElementById('btnAprobar'); b.disabled=true;
  var res=document.getElementById('resTodos'); res.style.color='#a1a1aa'; res.textContent='Aprobando...';
  try{{
    var r=await fetch('/api/brd/mbr/aprobar-todos-instructivos',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{aplicar:true,confirmar:'SI'}})}});
    var d=await r.json();
    if(r.ok&&d.aplicado){{ res.style.color='#34d399'; res.textContent='OK: '+d.aprobados+' instructivos APROBADOS y activos. Ya salen en las fabricaciones.'; }}
    else {{ res.style.color='#f87171'; res.textContent='Error: '+(d.error||d.detalle||r.status); b.disabled=false; }}
  }}catch(e){{ res.style.color='#f87171'; res.textContent='Error de red'; b.disabled=false; }}
}}
async function cargar(){{
  var prod=document.getElementById('prod').value;
  var pasos=document.getElementById('pasos').value;
  var res=document.getElementById('res');
  res.style.color='#a1a1aa'; res.textContent='Cargando…';
  try{{
    var r=await fetch('/api/brd/mbr/cargar-instructivo',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{producto:prod,pasos:pasos}})}});
    var d=await r.json();
    if(!r.ok){{ res.style.color='#f87171'; res.textContent='Error: '+(d.error||r.status); return; }}
    res.style.color='#34d399'; res.textContent='✓ '+d.pasos+' pasos cargados en '+d.producto+' · '+(d.aviso||'');
  }}catch(e){{ res.style.color='#f87171'; res.textContent='Error de red'; }}
}}
</script></body></html>"""


@bp.route("/api/brd/mbr/cargar-instructivo", methods=["POST"])
def cargar_instructivo_mbr():
    """Carga el INSTRUCTIVO de fabricación REAL (los pasos de proceso de mezcla) en el MBR de un
    producto · Sebastián 25-jun. body: {producto, pasos: [texto...] o texto multilínea}.
    Respeta inmutabilidad GMP: si el MBR activo está APROBADO, crea una versión NUEVA en borrador con
    estos pasos (Calidad la aprueba con e-firma para que entre en vigor); si está en BORRADOR, reemplaza
    sus pasos. El dispensado de MP sigue saliendo de la fórmula (sección 3), no de estos pasos."""
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    producto_in = (body.get("producto") or "").strip()
    pasos = body.get("pasos") or []
    if isinstance(pasos, str):
        pasos = pasos.split("\n")
    pasos = [str(p).strip() for p in pasos if str(p or "").strip()][:80]
    if not producto_in or not pasos:
        return jsonify({"error": "producto y pasos requeridos"}), 400
    # FASE del instructivo (26-jul · Sebastián: "tenemos envasado de emulsiones, limpiadores,
    # sueros..."). Antes esto escribía SIEMPRE `fase='fabricacion'` hardcodeado: cargar un
    # instructivo de ENVASADO habría entrado como pasos de FABRICACIÓN y habría corrompido la
    # receta de mezcla del producto. El legajo clona por fase (`_fase_canonica`), así que la fase
    # tiene que ser explícita y validada, no supuesta.
    fase_in = (body.get("fase") or "fabricacion").strip().lower()
    if fase_in not in _FASES_VALIDAS:
        return jsonify({"error": "fase inválida: '%s' · válidas: %s"
                        % (fase_in, ", ".join(sorted(_FASES_VALIDAS)))}), 400
    # El tipo de paso y la etiqueta de fase que el legajo espera por cada fase.
    _TIPO_POR_FASE = {"fabricacion": "mezclado", "envasado": "envasado",
                      "acondicionamiento": "acondicionamiento"}
    _ETIQUETA_FASE = {"fabricacion": "Fabricación", "envasado": "Envasado",
                      "acondicionamiento": "Acondicionamiento"}
    conn = get_db()
    cur = conn.cursor()
    user = session.get("compras_user", "")
    mbr = cur.execute(
        "SELECT id, estado, COALESCE(lote_size_g,0), producto_nombre FROM mbr_templates "
        "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) ORDER BY version DESC LIMIT 1",
        (producto_in,)).fetchone()
    if not mbr:
        return jsonify({"error": f"No hay MBR para '{producto_in}'. Generá el MBR del producto primero."}), 404
    producto = mbr[3]  # nombre canónico
    if (mbr[1] or "") == "draft":
        target_id = mbr[0]
        nueva_version = False
        # ⚠ SÓLO los pasos de ESTA fase. Antes borraba TODOS los del MBR, así que cargar el
        # instructivo de envasado habría BORRADO el de fabricación del mismo borrador. Se compara
        # con `_fase_canonica` porque la fase se guarda con etiquetas distintas según quién la
        # escribió ('Fabricación', 'fabricacion', 'Envasado'…).
        for _r in cur.execute("SELECT id, COALESCE(fase,'') FROM mbr_pasos WHERE mbr_template_id=?",
                              (target_id,)).fetchall():
            if _fase_canonica(_r[1]) == fase_in:
                cur.execute("DELETE FROM mbr_pasos WHERE id=?", (_r[0],))
    else:
        version = _next_version(conn, producto)
        cur.execute(
            "INSERT INTO mbr_templates (producto_nombre, version, estado, titulo, lote_size_g, creado_por) "
            "VALUES (?, ?, 'draft', ?, ?, ?)",
            (producto, version, f"{producto} v{version} · instructivo de {_ETIQUETA_FASE[fase_in].lower()}",
             mbr[2], user))
        target_id = cur.lastrowid
        nueva_version = True
        # La versión nueva arranca de la anterior y se le REEMPLAZA sólo la fase que se carga: si
        # no, aprobar el instructivo de envasado dejaría al producto sin instructivo de mezcla.
        for _r in cur.execute(
            "SELECT orden, COALESCE(fase,''), descripcion, COALESCE(tipo_paso,''), "
            "       COALESCE(equipo_requerido,''), COALESCE(requiere_e_sign,0), COALESCE(requiere_qc,0) "
            "FROM mbr_pasos WHERE mbr_template_id=? ORDER BY orden", (mbr[0],)).fetchall():
            if _fase_canonica(_r[1]) == fase_in:
                continue
            cur.execute(
                "INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, tipo_paso, "
                "                       equipo_requerido, requiere_e_sign, requiere_qc) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (target_id, _r[0], _r[1], _r[2], _r[3], _r[4], _r[5], _r[6]))
    # El orden arranca después de lo que ya hay, para no chocar con los pasos de las otras fases.
    _base = cur.execute("SELECT COALESCE(MAX(orden),0) FROM mbr_pasos WHERE mbr_template_id=?",
                        (target_id,)).fetchone()[0] or 0
    for i, txt in enumerate(pasos, start=1):
        cur.execute(
            "INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, tipo_paso, requiere_qc) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (target_id, _base + i, _ETIQUETA_FASE[fase_in], txt[:1500], _TIPO_POR_FASE[fase_in],
             _REQUIERE_QC_INSTRUCTIVO))
    audit_log(cur, usuario=user, accion="CARGAR_INSTRUCTIVO_MBR", tabla="mbr_templates",
              registro_id=target_id,
              despues={"producto": producto, "fase": fase_in, "pasos": len(pasos),
                       "nueva_version": nueva_version})
    conn.commit()
    return jsonify({"ok": True, "mbr_id": target_id, "producto": producto, "pasos": len(pasos),
                    "nueva_version": nueva_version,
                    "fase": fase_in,
                    "aviso": ("Versión NUEVA en borrador creada con el instructivo de %s · aprobala "
                              "con e-firma en el módulo MBR para que entre en vigor (la anterior "
                              "sigue activa hasta entonces · los pasos de las OTRAS fases se "
                              "copiaron tal cual)" % _ETIQUETA_FASE[fase_in].lower()
                              if nueva_version else
                              "Pasos de %s reemplazados en el borrador (las otras fases quedaron "
                              "intactas)" % _ETIQUETA_FASE[fase_in].lower())}), 200


@bp.route("/api/brd/mbr/cargar-todos-instructivos", methods=["GET", "POST"])
def cargar_todos_instructivos():
    """Carga los instructivos de fabricación de TODOS los productos de BATCH_INSTRUCTIVOS a sus MBR
    de una sola vez (Sebastián 24-jul). Respeta inmutabilidad GMP: MBR aprobado -> versión NUEVA en
    borrador que Calidad aprueba con e-firma (la activa sigue vigente hasta entonces); MBR en borrador
    -> reemplaza sus pasos. Salta los productos sin MBR (hay que generar el MBR primero). DRY-RUN por
    default (GET o POST sin aplicar); aplica con POST {aplicar:true, confirmar:'SI'}."""
    err = _require_qa_or_admin()
    if err:
        return err
    try:
        from batch_formulas_data import BATCH_INSTRUCTIVOS
    except Exception as e:
        return jsonify({"error": "no se pudo cargar batch_formulas_data: %s" % e}), 500
    body = request.get_json(silent=True) or {}
    aplicar = (request.method == "POST" and body.get("aplicar") is True
               and str(body.get("confirmar", "")).strip().upper() == "SI")
    conn = get_db()
    cur = conn.cursor()
    user = session.get("compras_user", "")
    plan = []
    for producto_in, pasos in BATCH_INSTRUCTIVOS.items():
        pasos_l = [str(p).strip() for p in (pasos or []) if str(p or "").strip()][:80]
        mbr = cur.execute(
            "SELECT id, estado, COALESCE(lote_size_g,0), producto_nombre FROM mbr_templates "
            "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) ORDER BY version DESC LIMIT 1",
            (producto_in,)).fetchone()
        if not mbr:
            plan.append({"producto": producto_in, "estado": "sin MBR (generar primero)", "pasos": len(pasos_l), "_ok": False})
            continue
        accion = "reemplaza borrador" if (mbr[1] or "") == "draft" else "nueva versión (borrador)"
        plan.append({"producto": mbr[3], "estado": accion, "pasos": len(pasos_l), "_ok": True, "_mbr": mbr, "_pasos": pasos_l})
    out = {"ok": True, "dry_run": (not aplicar), "total": len(BATCH_INSTRUCTIVOS),
           "con_mbr": len([p for p in plan if p["_ok"]]),
           "sin_mbr": [p["producto"] for p in plan if not p["_ok"]],
           "plan": [{"producto": p["producto"], "estado": p["estado"], "pasos": p["pasos"]} for p in plan],
           "aplicado": False}
    if not aplicar:
        return jsonify(out)
    cargados = nuevas = reemplazados = 0
    prod_actual = None
    try:
        for p in plan:
            if not p["_ok"]:
                continue
            mbr = p["_mbr"]; pasos_l = p["_pasos"]; producto = mbr[3]; prod_actual = producto
            if (mbr[1] or "") == "draft":
                target_id = mbr[0]; nueva = False
                cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (target_id,))
            else:
                version = _next_version(conn, producto)
                cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, titulo, lote_size_g, creado_por) "
                            "VALUES (?, ?, 'draft', ?, ?, ?)",
                            (producto, version, f"{producto} v{version} · instructivo de fabricación", mbr[2], user))
                target_id = cur.lastrowid; nueva = True
            for i, txt in enumerate(pasos_l, start=1):
                cur.execute("INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, tipo_paso, requiere_qc) "
                            "VALUES (?, ?, 'fabricacion', ?, 'mezclado', ?)",
                            (target_id, i, txt[:1500], _REQUIERE_QC_INSTRUCTIVO))
            cargados += 1
            if nueva:
                nuevas += 1
            else:
                reemplazados += 1
        audit_log(cur, usuario=user, accion="CARGAR_TODOS_INSTRUCTIVOS", tabla="mbr_templates", registro_id="(bulk)",
                  despues={"cargados": cargados, "nuevas_versiones": nuevas, "reemplazados": reemplazados})
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "falló la carga · rollback total (nada cambió)", "producto": prod_actual, "detalle": str(e)[:250]}), 500
    out.update({"aplicado": True, "cargados": cargados, "nuevas_versiones": nuevas, "reemplazados": reemplazados,
                "aviso": "Las versiones nuevas quedan en BORRADOR · aprobalas con e-firma en el módulo MBR para que entren en vigor (la activa sigue vigente hasta entonces)."})
    return jsonify(out)


@bp.route("/api/brd/mbr/aprobar-todos-instructivos", methods=["GET", "POST"])
def aprobar_todos_instructivos():
    """Aprueba con e-firma las versiones de MBR con instructivo que quedaron en borrador tras
    'Cargar TODOS' (Sebastián 24-jul). Los instructivos son transcripción del BATCH RECORD REAL,
    que YA está aprobado y revisado por Dirección Técnica → adoptarlos en EOS = aprobar lo ya
    validado. Firma con la e-firma del usuario actual (queda registrado quién/cuándo · Part 11) y
    obsoleta la versión aprobada anterior de cada producto (queda UNA activa). DRY-RUN por default
    (GET); aplica con POST {aplicar:true, confirmar:'SI'}."""
    err = _require_qa_or_admin()
    if err:
        return err
    try:
        from batch_formulas_data import BATCH_INSTRUCTIVOS
    except Exception as e:
        return jsonify({"error": "no se pudo cargar batch_formulas_data: %s" % e}), 500
    body = request.get_json(silent=True) or {}
    aplicar = (request.method == "POST" and body.get("aplicar") is True
               and str(body.get("confirmar", "")).strip().upper() == "SI")
    conn = get_db()
    cur = conn.cursor()
    user = session.get("compras_user", "")
    plan = []
    for producto_in in BATCH_INSTRUCTIVOS:
        mbr = cur.execute("SELECT id, estado, producto_nombre, version FROM mbr_templates "
                          "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) ORDER BY version DESC LIMIT 1",
                          (producto_in,)).fetchone()
        if not mbr:
            plan.append({"producto": producto_in, "estado": "sin MBR"})
            continue
        estado = mbr[1]
        if estado == "aprobado":
            plan.append({"producto": mbr[2], "estado": "ya aprobado"})
        elif estado in ("draft", "en_revision"):
            plan.append({"producto": mbr[2], "estado": f"a aprobar (v{mbr[3]})", "_id": mbr[0], "_estado": estado, "_prod": mbr[2]})
        else:
            plan.append({"producto": mbr[2], "estado": f"estado {estado} (saltado)"})
    a_aprobar = [p for p in plan if "_id" in p]
    out = {"ok": True, "dry_run": (not aplicar), "a_aprobar": len(a_aprobar),
           "ya_aprobados": len([p for p in plan if p["estado"] == "ya aprobado"]),
           "sin_mbr": [p["producto"] for p in plan if p["estado"] == "sin MBR"],
           "plan": [{"producto": p["producto"], "estado": p["estado"]} for p in plan], "aplicado": False}
    if not aplicar:
        return jsonify(out)
    try:
        from blueprints.firmas import crear_firma_directa
    except Exception:
        from api.blueprints.firmas import crear_firma_directa
    aprobados, errores = [], []
    prod_actual = None
    try:
        for p in a_aprobar:
            mbr_id = p["_id"]; producto = p["_prod"]; prod_actual = producto
            if p["_estado"] == "draft":
                cur.execute("UPDATE mbr_templates SET estado='en_revision' WHERE id=? AND estado='draft'", (mbr_id,))
            sig_id = crear_firma_directa(conn, username=user, record_table="mbr_templates", record_id=str(mbr_id),
                                         meaning="aprueba",
                                         comment="Instructivo del batch record (revisado/aprobado por Dirección Técnica) adoptado en EOS")
            cur.execute("UPDATE mbr_templates SET estado='aprobado', aprobado_por=?, aprobado_at_utc=datetime('now','utc'), "
                        "aprobado_signature_id=? WHERE id=? AND estado='en_revision'", (user, sig_id, mbr_id))
            if cur.rowcount == 0:
                errores.append({"producto": producto, "error": "estado cambió"})
                continue
            cur.execute("UPDATE mbr_templates SET estado='obsoleto', obsoleto_at_utc=datetime('now','utc'), "
                        "obsoleto_motivo='Reemplazada por versión con instructivo del batch record' "
                        "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND estado='aprobado' AND id != ?", (producto, mbr_id))
            audit_log(cur, usuario=user, accion="APROBAR_INSTRUCTIVO_BULK", tabla="mbr_templates", registro_id=mbr_id,
                      despues={"producto": producto, "estado": "aprobado", "signature_id": sig_id})
            aprobados.append(producto)
        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "falló la aprobación · rollback total (nada cambió)", "producto": prod_actual, "detalle": str(e)[:250]}), 500
    out.update({"aplicado": True, "aprobados": len(aprobados), "productos_aprobados": aprobados, "errores": errores})
    return jsonify(out)


@bp.route("/api/brd/mbr/<int:mbr_id>", methods=["PATCH"])
def editar_mbr(mbr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT estado, creado_por FROM mbr_templates WHERE id = ?", (mbr_id,)
    ).fetchone()
    if not row:
        return jsonify({"error": "MBR no encontrado"}), 404
    if row["estado"] != "draft":
        return jsonify({"error": f"solo editable en estado 'draft' (actual: {row['estado']})"}), 409
    body = request.get_json(silent=True) or {}
    EDITABLE = {"titulo", "descripcion", "lote_size_g",
                "tiempo_total_estimado_min", "formula_version_id"}
    cambios = {k: v for k, v in body.items() if k in EDITABLE}
    if not cambios:
        return jsonify({"error": "No hay campos editables", "editables": sorted(EDITABLE)}), 400
    set_clause = ", ".join(f"{k} = ?" for k in cambios)
    cur.execute(f"UPDATE mbr_templates SET {set_clause} WHERE id = ?",
                list(cambios.values()) + [mbr_id])
    conn.commit()
    audit_log(None, usuario=session.get("compras_user", ""),
              accion="UPDATE_MBR_DRAFT", tabla="mbr_templates",
              registro_id=mbr_id, despues=cambios)
    return jsonify({"ok": True})


@bp.route("/api/brd/mbr/<int:mbr_id>/pasos", methods=["POST"])
def agregar_paso(mbr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)).fetchone()
    if not row:
        return jsonify({"error": "MBR no encontrado"}), 404
    if row["estado"] != "draft":
        return jsonify({"error": "solo se agregan pasos en draft"}), 409
    body = request.get_json(silent=True) or {}
    descripcion = (body.get("descripcion") or "").strip()
    if not descripcion:
        return jsonify({"error": "descripcion requerida"}), 400
    tipo = (body.get("tipo_paso") or "otro").strip().lower()
    if tipo not in VALID_TIPO_PASO:
        return jsonify({"error": f"tipo_paso inválido · use {sorted(VALID_TIPO_PASO)}"}), 400
    siguiente_orden = (cur.execute(
        "SELECT COALESCE(MAX(orden), 0) FROM mbr_pasos WHERE mbr_template_id = ?",
        (mbr_id,),
    ).fetchone()[0] or 0) + 1
    cur.execute(
        """INSERT INTO mbr_pasos
             (mbr_template_id, orden, fase, descripcion, tipo_paso,
              equipo_requerido, tiempo_estimado_min, requiere_e_sign,
              requiere_qc, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (mbr_id, siguiente_orden,
         (body.get("fase") or "").strip(), descripcion, tipo,
         (body.get("equipo_requerido") or "").strip(),
         int(body.get("tiempo_estimado_min") or 0),
         1 if body.get("requiere_e_sign") else 0,
         1 if body.get("requiere_qc") else 0,
         (body.get("notas") or "").strip()),
    )
    paso_id = cur.lastrowid
    audit_log(cur, usuario=session.get("compras_user", ""), accion="AGREGAR_PASO_MBR",
              tabla="mbr_pasos", registro_id=paso_id,
              despues={"mbr_id": mbr_id, "orden": siguiente_orden,
                       "descripcion": descripcion[:120]})
    conn.commit()
    return jsonify({"ok": True, "id": paso_id, "orden": siguiente_orden}), 201


@bp.route("/api/brd/mbr/<int:mbr_id>/pasos/<int:paso_id>", methods=["PATCH"])
def editar_paso(mbr_id, paso_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute("SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "draft":
        return jsonify({"error": "solo se editan pasos en draft"}), 409
    body = request.get_json(silent=True) or {}
    EDITABLE = {"fase", "descripcion", "tipo_paso", "equipo_requerido",
                "tiempo_estimado_min", "requiere_e_sign", "requiere_qc",
                "notas", "orden"}
    cambios = {k: v for k, v in body.items() if k in EDITABLE}
    if "tipo_paso" in cambios:
        if cambios["tipo_paso"] not in VALID_TIPO_PASO:
            return jsonify({"error": "tipo_paso inválido"}), 400
    if not cambios:
        return jsonify({"error": "No hay campos editables", "editables": sorted(EDITABLE)}), 400
    # bool/int normalización
    if "requiere_e_sign" in cambios:
        cambios["requiere_e_sign"] = 1 if cambios["requiere_e_sign"] else 0
    if "requiere_qc" in cambios:
        cambios["requiere_qc"] = 1 if cambios["requiere_qc"] else 0
    set_clause = ", ".join(f"{k} = ?" for k in cambios)
    cur.execute(
        f"UPDATE mbr_pasos SET {set_clause} WHERE id = ? AND mbr_template_id = ?",
        list(cambios.values()) + [paso_id, mbr_id],
    )
    if cur.rowcount == 0:
        return jsonify({"error": "paso no encontrado o no pertenece al MBR"}), 404
    audit_log(cur, usuario=session.get("compras_user", ""), accion="EDITAR_PASO_MBR",
              tabla="mbr_pasos", registro_id=paso_id, despues=cambios)
    conn.commit()
    return jsonify({"ok": True})


@bp.route("/api/brd/mbr/<int:mbr_id>/pasos/<int:paso_id>", methods=["DELETE"])
def borrar_paso(mbr_id, paso_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute("SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "draft":
        return jsonify({"error": "solo se borran pasos en draft"}), 409
    cur.execute(
        "DELETE FROM mbr_pasos WHERE id = ? AND mbr_template_id = ?",
        (paso_id, mbr_id),
    )
    if cur.rowcount == 0:
        return jsonify({"error": "paso no encontrado"}), 404
    audit_log(cur, usuario=session.get("compras_user", ""), accion="BORRAR_PASO_MBR",
              tabla="mbr_pasos", registro_id=paso_id, detalle=f"MBR {mbr_id}")
    conn.commit()
    return jsonify({"ok": True})


@bp.route("/api/brd/mbr/<int:mbr_id>/submit", methods=["POST"])
def submit_a_revision(mbr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute(
        "SELECT estado, creado_por FROM mbr_templates WHERE id = ?", (mbr_id,)
    ).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "draft":
        return jsonify({"error": f"solo draft puede submit (actual: {tpl['estado']})"}), 409
    user = session.get("compras_user", "")
    if user != tpl["creado_por"] and user not in ADMIN_USERS:
        return jsonify({"error": "Solo el creador o admin puede submit"}), 403
    n_pasos = cur.execute(
        "SELECT COUNT(*) FROM mbr_pasos WHERE mbr_template_id = ?", (mbr_id,)
    ).fetchone()[0]
    if n_pasos < 1:
        return jsonify({"error": "MBR debe tener al menos 1 paso antes de submit"}), 400
    cur.execute(
        "UPDATE mbr_templates SET estado = 'en_revision' WHERE id = ? AND estado = 'draft'",
        (mbr_id,),
    )
    # FIX 7-jul (audit ultracode · M27 CAS): estado en el WHERE + rowcount (transición única draft→en_revision).
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "El MBR ya cambió de estado · refrescá", "codigo": "ESTADO_CAMBIO"}), 409
    conn.commit()
    audit_log(None, usuario=user, accion="SUBMIT_MBR",
              tabla="mbr_templates", registro_id=mbr_id,
              antes={"estado": "draft"}, despues={"estado": "en_revision"})
    return jsonify({"ok": True, "estado": "en_revision"})


@bp.route("/api/brd/mbr/<int:mbr_id>/aprobar", methods=["POST"])
def aprobar_mbr(mbr_id):
    """Aprueba un MBR en revisión. Requiere signature_id de e_signatures
    con meaning='aprueba' del usuario actual sobre este MBR."""
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")
    if not signature_id:
        return jsonify({
            "error": "signature_id requerido · primero firmá vía POST /api/sign con "
                      "{record_table:'mbr_templates', record_id:'<id>', meaning:'aprueba'}"
        }), 400

    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute(
        "SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)
    ).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "en_revision":
        return jsonify({"error": f"solo en_revision puede aprobarse (actual: {tpl['estado']})"}), 409

    # Validar la firma: debe ser del usuario actual, sobre este MBR, meaning='aprueba'
    user = session.get("compras_user", "")
    sig = cur.execute(
        """SELECT id FROM e_signatures
           WHERE id = ? AND record_table = 'mbr_templates'
             AND record_id = ? AND meaning = 'aprueba' AND signer_username = ?""",
        (int(signature_id), str(mbr_id), user),
    ).fetchone()
    if not sig:
        return jsonify({
            "error": "signature_id no corresponde a una firma 'aprueba' de este MBR por vos",
        }), 400

    cur.execute(
        """UPDATE mbr_templates
             SET estado = 'aprobado',
                 aprobado_por = ?,
                 aprobado_at_utc = datetime('now', 'utc'),
                 aprobado_signature_id = ?
           WHERE id = ? AND estado = 'en_revision'""",
        (user, int(signature_id), mbr_id),
    )
    # FIX 7-jul (audit ultracode · M27 CAS): condición de estado en el WHERE + rowcount (como los EBR del mismo
    # archivo · 3255/3710/3818). Sin esto, 2 aprobaciones concurrentes (o aprobar+obsoletar) pasaban el check
    # de Python y ambas hacían UPDATE.
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "El MBR ya cambió de estado · refrescá", "codigo": "ESTADO_CAMBIO"}), 409
    conn.commit()
    audit_log(None, usuario=user, accion="APROBAR_MBR",
              tabla="mbr_templates", registro_id=mbr_id,
              antes={"estado": "en_revision"},
              despues={"estado": "aprobado", "signature_id": signature_id})
    return jsonify({"ok": True, "estado": "aprobado"})


@bp.route("/api/brd/mbr/<int:mbr_id>/obsoletar", methods=["POST"])
def obsoletar_mbr(mbr_id):
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    motivo = (body.get("motivo") or "").strip()
    if not motivo:
        return jsonify({"error": "motivo requerido para obsoletar"}), 400
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute(
        "SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)
    ).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "aprobado":
        return jsonify({"error": f"solo aprobado puede obsoletarse (actual: {tpl['estado']})"}), 409
    user = session.get("compras_user", "")
    cur.execute(
        """UPDATE mbr_templates
             SET estado = 'obsoleto',
                 obsoleto_at_utc = datetime('now', 'utc'),
                 obsoleto_motivo = ?
           WHERE id = ? AND estado = 'aprobado'""",
        (motivo, mbr_id),
    )
    # FIX 7-jul (audit ultracode · M27 CAS): estado en el WHERE + rowcount (evita doble-obsoletar concurrente).
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "El MBR ya cambió de estado · refrescá", "codigo": "ESTADO_CAMBIO"}), 409
    conn.commit()
    audit_log(None, usuario=user, accion="OBSOLETAR_MBR",
              tabla="mbr_templates", registro_id=mbr_id,
              antes={"estado": "aprobado"},
              despues={"estado": "obsoleto", "motivo": motivo})
    return jsonify({"ok": True, "estado": "obsoleto"})


# ════════════════════════════════════════════════════════════════════════════
# EBR (Executed Batch Record) · ejecución de un lote real desde un MBR
# ════════════════════════════════════════════════════════════════════════════
# Flujo típico:
#   1. POST /api/brd/ebr {mbr_template_id, lote, produccion_id?}
#      → clona pasos del MBR a ebr_pasos_ejecutados (pendientes).
#   2. Operario va al wizard del EBR. Por cada paso: iniciar → completar
#      con observaciones + e-sign si requerido.
#   3. POST /api/brd/ebr/<id>/completar con cantidad_real_g → yield_pct.
#   4. QC firma: POST /api/brd/ebr/<id>/liberar con signature_id.

VALID_ESTADOS_EBR = {"iniciado", "en_proceso", "completado",
                     "en_revision_qc", "liberado", "rechazado"}


def _ebr_to_dict(row, pasos=None):
    d = {
        "id": row["id"],
        "mbr_template_id": row["mbr_template_id"],
        "mbr_version": row["mbr_version"],
        "produccion_id": row["produccion_id"],
        "lote": row["lote"],
        "numero_op": row["numero_op"] if "numero_op" in row.keys() else None,
        "estado": row["estado"],
        "iniciado_por": row["iniciado_por"],
        "iniciado_at_utc": row["iniciado_at_utc"],
        "completado_at_utc": row["completado_at_utc"],
        "liberado_por": row["liberado_por"] or "",
        "liberado_at_utc": row["liberado_at_utc"],
        "liberado_signature_id": row["liberado_signature_id"],
        "rechazado_motivo": row["rechazado_motivo"] or "",
        "cantidad_objetivo_g": row["cantidad_objetivo_g"],
        "cantidad_real_g": row["cantidad_real_g"],
        "yield_pct": row["yield_pct"],
        # Por qué se liberó un lote con un rendimiento anómalo · el gate la exige, así
        # que tiene que poder LEERSE después (mig 434). Defensivo: un SELECT viejo o una
        # instancia sin la migración no rompe la pantalla.
        "yield_justificacion": ((row["yield_justificacion"] or "")
                                if "yield_justificacion" in row.keys() else ""),
        "notas": row["notas"] or "",
        # fase del legajo · defensivo: SELECTs viejos pueden no traer la columna
        "fase": (row["fase"] if "fase" in row.keys() and row["fase"] else "fabricacion"),
        # puente OP→OF · defensivo
        "densidad_g_ml": (row["densidad_g_ml"] if "densidad_g_ml" in row.keys() else None),
        "ml_envasable": (row["ml_envasable"] if "ml_envasable" in row.keys() else None),
    }
    if pasos is not None:
        d["pasos"] = [_paso_ej_to_dict(p) for p in pasos]
    return d


def _paso_ej_to_dict(row):
    return {
        "id": row["id"],
        "ebr_id": row["ebr_id"],
        "mbr_paso_id": row["mbr_paso_id"],
        "orden": row["orden"],
        "descripcion": row["descripcion"],
        "tipo_paso": row["tipo_paso"] or "otro",
        "equipo_requerido": row["equipo_requerido"] or "",
        "requiere_e_sign": int(row["requiere_e_sign"] or 0),
        "requiere_qc": int(row["requiere_qc"] or 0),
        "estado": row["estado"],
        "operario_username": row["operario_username"] or "",
        "iniciado_at_utc": row["iniciado_at_utc"],
        "completado_at_utc": row["completado_at_utc"],
        "observaciones": row["observaciones"] or "",
        "e_sign_id": row["e_sign_id"],
        "qc_username": row["qc_username"] or "",
        "qc_e_sign_id": row["qc_e_sign_id"],
        "desviacion_id": row["desviacion_id"],
        # fase del paso · defensivo (SELECTs viejos pueden no traer la columna)
        "fase": (row["fase"] if "fase" in row.keys() and row["fase"] else ""),
    }


# Fases del motor EBR único (reemplazo MyBatch · OP/OF/OA comparten esqueleto).
_FASES_VALIDAS = {"fabricacion", "envasado", "acondicionamiento"}

# ── LA ORDEN como objeto propio (mig 395) ───────────────────────────────────────
#
# Sebastián: *"todas inician con una ORDEN; esa orden se le entrega al operario, y después
# empieza el proceso"*. Una orden agrupa N lotes: se aprueba UNA vez para todos, y su
# número es lo que se imprime. Los legajos viejos siguen sin orden madre (`orden_id` NULL)
# y funcionan igual -- el cambio es ADITIVO por construcción, no por cortesía.

_ORDEN_PREFIJO = {"fabricacion": "OP", "envasado": "OF", "acondicionamiento": "OA"}
_ORDEN_ESTADOS = ("borrador", "aprobada", "cerrada", "anulada")


def _orden_numero_siguiente(cur, fase, anio=None):
    """'OF-2026-0007'. NO race-safe por sí solo: el UNIQUE de `numero` es el respaldo y
    el caller reintenta (patrón de `siguiente_correlativo` · M45/M96: jamás
    `CAST(SUBSTR(...))`, que revienta en PG con cualquier sufijo)."""
    from datetime import datetime as _dt, timezone as _tz
    from audit_helpers import siguiente_correlativo
    anio = anio or _dt.now(_tz.utc).year
    pref = "%s-%s-" % (_ORDEN_PREFIJO.get(fase, "OP"), anio)
    return "%s%04d" % (pref, siguiente_correlativo(cur, "ordenes_produccion", "numero", pref))


def _orden_dict(row, lotes=None):
    d = {
        "id": row["id"], "numero": row["numero"] or "",
        "fase": row["fase"] or "fabricacion",
        "producto_nombre": row["producto_nombre"] or "",
        "lote_bulk": row["lote_bulk"] or "",
        "cantidad_g": row["cantidad_g"],
        "densidad_g_ml": row["densidad_g_ml"],
        "estado": row["estado"] or "borrador",
        "observaciones": row["observaciones"] or "",
        "creado_por": row["creado_por"] or "", "creado_at_utc": row["creado_at_utc"] or "",
        "elaborado_por": row["elaborado_por"] or "",
        "aprobada_por": row["aprobada_por"] or "",
        "aprobada_at_utc": row["aprobada_at_utc"] or "",
        "aprobada_calidad_por": row["aprobada_calidad_por"] or "",
        "aprobada_calidad_at_utc": row["aprobada_calidad_at_utc"] or "",
        "anulada_motivo": row["anulada_motivo"] or "",
    }
    # Cantidad por envasar en mL: DERIVADA de la densidad, no se guarda (M71). Sin
    # densidad queda en None y la pantalla muestra un punto, no un cero que miente.
    try:
        d["cantidad_ml"] = (round(float(d["cantidad_g"]) / float(d["densidad_g_ml"]), 2)
                            if d["cantidad_g"] and d["densidad_g_ml"] else None)
    except (TypeError, ValueError, ZeroDivisionError):
        d["cantidad_ml"] = None
    # Acondicionamiento lleva DOS aprobaciones (producción y calidad · como la OA-2026-102
    # real: "Supervisado por: Jefe de producción" Y "Aprobado por: Laura González, Jefe de
    # calidad"). Las otras dos fases, una sola.
    d["exige_calidad"] = (d["fase"] == "acondicionamiento")
    d["aprobada"] = bool(d["aprobada_por"] and (not d["exige_calidad"] or d["aprobada_calidad_por"]))
    if lotes is not None:
        d["lotes"] = lotes
    return d


def _orden_de_ebr(conn, ebr_id):
    """La orden madre de un legajo, o None si no tiene (los de antes de la mig 395)."""
    try:
        r = conn.execute(
            "SELECT o.* FROM ordenes_produccion o "
            "JOIN ebr_ejecuciones e ON e.orden_id=o.id WHERE e.id=?", (ebr_id,)).fetchone()
        return _orden_dict(r) if r else None
    except Exception as _e:
        log.warning("orden madre de ebr=%s no legible: %s", ebr_id, _e)
        return None


def _fase_canonica(label):
    """Normaliza la etiqueta libre de fase de un paso de MBR (p.ej.
    'Dispensación', 'Fabricación', 'Envasado', 'Acondicionamiento/Etiquetado')
    a la fase canónica del EBR (fabricacion/envasado/acondicionamiento).

    Batch B (audit 3-jun) · el motor EBR es por fase: un EBR de envasado debe
    clonar SOLO los pasos de envasado, no los de fabricación. Todo lo que no sea
    claramente envasado/acondicionamiento cuenta como 'fabricacion' (default
    seguro · preserva el comportamiento actual de los MBR de una sola fase)."""
    s = (label or "").strip().lower()
    # quitar acentos básicos
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        s = s.replace(a, b)
    if any(k in s for k in ("acondi", "etiqu", "codif", "empaqu", "estuch", "arte")):
        return "acondicionamiento"
    if any(k in s for k in ("envas", "llen", "sell", "tapad")):
        return "envasado"
    return "fabricacion"


def _validar_signature(cur, signature_id, *, record_table, record_id,
                       meaning, signer_username):
    sig = cur.execute(
        """SELECT id FROM e_signatures
           WHERE id = ? AND record_table = ? AND record_id = ?
             AND meaning = ? AND signer_username = ?""",
        (int(signature_id), record_table, str(record_id), meaning, signer_username),
    ).fetchone()
    return sig is not None


def crear_ebr_desde_mbr(cur, *, producto_nombre, lote, produccion_id=None,
                        cantidad_objetivo_g=None, usuario='', notas='',
                        fase='fabricacion', area_codigo=''):
    """Crea (o reusa) un EBR para un lote desde el MBR APROBADO del producto.

    Reutilizable fuera de brd.py (p.ej. hook de aceptar producción en planta ·
    reemplazo de MyBatch fase 1). NO hace commit ni audit_log: el caller maneja
    la transacción y la auditoría. Usa índices posicionales (no row['k']) para
    funcionar con cualquier row_factory del cursor del caller.

    Returns dict:
      {ok:True, id, numero_op, pasos}            · EBR creado
      {ok:True, id, numero_op, reusado:True}     · ya existía para esa producción
      {ok:False, error:'NO_MBR_APROBADO'|'LOTE_DUPLICADO', detail}
    """
    # `ebr_ejecuciones.lote` es UNIQUE a nivel BD. Para que el MISMO lote físico tenga
    # legajo de fabricación/envasado/acondicionamiento (órdenes OP/OF/OA distintas, como
    # MyBatch · 10-jun), la LLAVE `lote` lleva sufijo de fase (·OF/·OA) y el lote físico
    # real se guarda en `lote_codigo`. La idempotencia/dedup van por (lote_codigo, FASE).
    _fase_norm = fase if fase in _FASES_VALIDAS else 'fabricacion'
    lote_codigo = (lote or '').strip()
    _suf = {'fabricacion': '', 'envasado': '-OF', 'acondicionamiento': '-OA'}.get(_fase_norm, '')
    lote_key = lote_codigo + _suf
    # Idempotencia por (produccion_id, lote_codigo, FASE): re-aceptar la misma fase reusa
    # el legajo de ESE lote físico. Batch C · multi-lote: lotes físicos distintos = N legajos.
    if produccion_id is not None:
        ex = cur.execute(
            "SELECT id, numero_op FROM ebr_ejecuciones "
            "WHERE produccion_id=? AND COALESCE(lote_codigo,lote)=? AND COALESCE(fase,'fabricacion')=?",
            (produccion_id, lote_codigo, _fase_norm),
        ).fetchone()
        if ex:
            return {'ok': True, 'id': ex[0], 'numero_op': ex[1],
                    'pasos': 0, 'reusado': True}
    # MBR aprobado más reciente del producto (BPM: no se fabrica sin MBR aprobado).
    # FIX 26-jul · el match era por nombre EXACTO (case-sensitive) y por eso dos productos
    # con instructivo cargado nacían SIN legajo: la fórmula dice 'BLUSH BALM' y el MBR está
    # guardado 'Blush Balm'; igual 'SUERO EXFOLIANTE NOVA PHA' vs 'Suero Exfoliante Nova PHA'.
    # Para el sistema eran productos distintos → NO_MBR_APROBADO → la orden caía a "registro
    # simple" y el procedimiento aprobado nunca llegaba al piso. Es la regla M2: todo match de
    # producto por nombre entre tablas distintas va con UPPER(TRIM(...)) a AMBOS lados.
    # `id DESC` desempata: sin él, dos MBR de la misma versión salen en orden no determinista
    # en PostgreSQL.
    mbr = cur.execute(
        """SELECT id, version, lote_size_g
             FROM mbr_templates
            WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND estado='aprobado'
            ORDER BY version DESC, id DESC LIMIT 1""",
        (producto_nombre,),
    ).fetchone()
    if not mbr:
        # ⚠ Un MBR APROBADO es INMUTABLE (mig 109), así que al renombrar un producto su nombre
        # queda viejo y este lookup deja de encontrarlo: el producto pasa a NO poder generar su
        # legajo. Pasó el 2-ago con HYDRA BALANCE→HYDRABALANCE y con "Suero de Vitamina C+
        # fórmula nueva"→"Suero Vitamina C+", y `renombrar-producto` lo reportó como
        # "aprobados_inmutables: 2" -- que se lee como un pendiente y era una ROTURA.
        #
        # El documento sigue siendo VÁLIDO; lo viejo es la etiqueta. Así que se busca por los
        # mismos puentes que el resto del sistema, en orden de fuerza y SIEMPRE declarando por
        # cuál cruzó (`mbr_match_por`): un emparejamiento que no se puede auditar no sirve para
        # un dato regulado (M19/M132). Re-versionar sigue siendo cosa de Calidad, pero mientras
        # tanto la planta no se queda sin batch record.
        _mbr_via = ''
        try:
            from .programacion import _norm_prod_fuerte as _npf
        except Exception:
            from blueprints.programacion import _norm_prod_fuerte as _npf

        def _sin_espacios(s):
            return _npf(s or '').replace(' ', '')

        # (a) alias explícito producto→fórmula · lo pone una persona (o el rename, ver abajo)
        try:
            _al = cur.execute(
                "SELECT producto_formula FROM producto_formula_alias "
                "WHERE UPPER(TRIM(producto_plan))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1 "
                "LIMIT 1", (producto_nombre,)).fetchone()
            if _al and _al[0]:
                mbr = cur.execute(
                    """SELECT id, version, lote_size_g FROM mbr_templates
                        WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND estado='aprobado'
                        ORDER BY version DESC, id DESC LIMIT 1""", (_al[0],)).fetchone()
                if mbr:
                    _mbr_via = 'alias'
        except Exception as _ea:
            log.warning('crear_ebr · alias MBR: %s', _ea)

        # (b) el mismo nombre sin espacios ni puntuación · caza HYDRABALANCE ↔ "HYDRA BALANCE".
        #     Sólo si es INEQUÍVOCO: con dos candidatos no se elige, se avisa (M132).
        if not mbr:
            try:
                _obj = _sin_espacios(producto_nombre)
                _cands = [r for r in cur.execute(
                    "SELECT id, version, lote_size_g, producto_nombre FROM mbr_templates "
                    "WHERE estado='aprobado' ORDER BY version DESC, id DESC").fetchall()
                    if _sin_espacios(r[3]) == _obj]
                _nombres = {r[3] for r in _cands}
                if len(_nombres) == 1 and _cands:
                    mbr, _mbr_via = _cands[0], 'nombre_sin_espacios'
            except Exception as _eb:
                log.warning('crear_ebr · match MBR sin espacios: %s', _eb)

        if not mbr:
            return {'ok': False, 'error': 'NO_MBR_APROBADO',
                    'detail': f"No hay MBR aprobado para '{producto_nombre}'"}
        log.warning('crear_ebr · MBR de %r resuelto por %s (el MBR aprobado conserva el nombre '
                    'viejo · Calidad debe re-versionarlo)', producto_nombre, _mbr_via)
    # Un solo EBR por (lote físico, FASE): Fabricación/Envasado/Acondicionamiento del
    # mismo lote conviven. Dentro de UNA fase, el lote sigue siendo único.
    if cur.execute(
        "SELECT id FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote)=? AND COALESCE(fase,'fabricacion')=?",
        (lote_codigo, _fase_norm)).fetchone():
        return {'ok': False, 'error': 'LOTE_DUPLICADO',
                'detail': f"el lote '{lote_codigo}' ya tiene un EBR de fase {_fase_norm}"}
    # Resolver colisión del UNIQUE `lote` (por si la llave sufijada ya existe por otra vía).
    _base_key = lote_key; _n = 1
    while cur.execute("SELECT 1 FROM ebr_ejecuciones WHERE lote=?", (lote_key,)).fetchone():
        _n += 1
        lote_key = f"{_base_key}-{_n}"
    # Magnitud del lote (M67): manda lo que el caller pasa; si no lo pasó pero hay
    # produccion_id, deriva de la FUENTE DE VERDAD produccion_programada.cantidad_kg × 1000;
    # solo como ÚLTIMO recurso el lote_size_g del MBR (default genérico de dominio que NO
    # refleja este lote → daba TEÓRICA/rendimiento/pesajes falsos). Blinda a los callers
    # (envasado/acondicionamiento) que crean el EBR sin pasar la cantidad.
    cant = cantidad_objetivo_g
    if cant is None and produccion_id is not None:
        try:
            _ck = cur.execute(
                "SELECT COALESCE(cantidad_kg,0) FROM produccion_programada WHERE id=?",
                (produccion_id,)).fetchone()
            if _ck and _ck[0]:
                cant = round(float(_ck[0]) * 1000, 1)
        except Exception:
            pass
    if cant is None:
        cant = mbr[2]
    # ÁREA/LÍNEA · la hereda del lote programado (26-jul). La columna `area_codigo` existe desde la
    # mig 219 y la cabecera del legajo la muestra, pero NINGÚN caller la pasaba: los 8 sitios que
    # crean un EBR la dejaban vacía, así que el legajo mostraba "Área/Línea: -" siempre. En vez de
    # parchar los 8, se deriva acá, que es donde ya está el `produccion_id` y donde no puede
    # volver a divergir (M1). El caller que la pase explícitamente sigue mandando.
    if not (area_codigo or '').strip() and produccion_id:
        try:
            _ar = cur.execute(
                "SELECT COALESCE(a.codigo,'') FROM produccion_programada pp "
                "JOIN areas_planta a ON a.id = pp.area_id WHERE pp.id=?",
                (produccion_id,)).fetchone()
            if _ar and (_ar[0] or '').strip():
                area_codigo = _ar[0].strip()
        except Exception as _e_ar:
            # nunca impedir la creación del legajo por esto, pero dejar rastro (M94)
            log.warning('crear_ebr_desde_mbr: no se pudo heredar el área de la producción %s: %s',
                        produccion_id, _e_ar)
    numero_op = assign_numero_op(cur)
    try:
        cur.execute(
            """INSERT INTO ebr_ejecuciones
                 (mbr_template_id, mbr_version, produccion_id, lote, numero_op,
                  estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, notas,
                  fase, area_codigo)
               VALUES (?, ?, ?, ?, ?, 'iniciado', ?, datetime('now', 'utc'), ?, ?, ?, ?)""",
            (mbr[0], mbr[1], produccion_id, lote_key, numero_op, usuario,
             float(cant or 0), notas, _fase_norm, (area_codigo or '')),
        )
    except Exception as _e_ac:
        # Fallback SOLO si la columna area_codigo aún no existe (mig 219 sin aplicar). Un fallo
        # REAL del INSERT (UNIQUE lote, tipo, tx PG abortada) NO se disfraza de drift: propaga
        # para no crear el EBR silenciosamente mal (M4/M69).
        _es = str(_e_ac).lower()
        if not ('area_codigo' in _es and ('no such column' in _es or 'does not exist' in _es
                                          or 'undefined column' in _es)):
            raise
        cur.execute(
            """INSERT INTO ebr_ejecuciones
                 (mbr_template_id, mbr_version, produccion_id, lote, numero_op,
                  estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, notas,
                  fase)
               VALUES (?, ?, ?, ?, ?, 'iniciado', ?, datetime('now', 'utc'), ?, ?, ?)""",
            (mbr[0], mbr[1], produccion_id, lote_key, numero_op, usuario,
             float(cant or 0), notas, _fase_norm),
        )
    ebr_id = cur.lastrowid
    # lote_codigo = lote físico real (la llave `lote` puede llevar sufijo de fase).
    try:
        cur.execute("UPDATE ebr_ejecuciones SET lote_codigo=? WHERE id=?",
                    (lote_codigo, ebr_id))
    except Exception:
        pass
    _fase_ebr = _fase_norm
    pasos = cur.execute(
        """SELECT id, orden, descripcion, tipo_paso, equipo_requerido,
                  requiere_e_sign, requiere_qc, COALESCE(fase,'') AS fase
             FROM mbr_pasos WHERE mbr_template_id=? ORDER BY orden""",
        (mbr[0],),
    ).fetchall()
    # Batch B · clonar SOLO los pasos de la fase del EBR (un EBR de envasado no
    # debe traer los pasos de fabricación, y viceversa).
    n_clonados = 0
    for p in pasos:
        if _fase_canonica(p[7]) != _fase_ebr:
            continue
        cur.execute(
            """INSERT INTO ebr_pasos_ejecutados
                 (ebr_id, mbr_paso_id, orden, descripcion, tipo_paso,
                  equipo_requerido, requiere_e_sign, requiere_qc, estado, fase)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)""",
            (ebr_id, p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]),
        )
        n_clonados += 1
    return {'ok': True, 'id': ebr_id, 'numero_op': numero_op, 'pasos': n_clonados}


def _generar_mbr_desde_formula(cur, producto_nombre, usuario=''):
    """Crea un MBR borrador a partir de la fórmula EXISTENTE del producto.

    Reemplazo MyBatch · las fórmulas ya viven en EOS (formula_headers/items), así
    que no se re-ingresa la receta: el MBR se vincula a la fórmula
    (formula_version_id = formula_headers.id) y genera un paso de dispensación
    por componente + un paso de mezcla. El usuario revisa, agrega IPCs y aprueba.
    NO commitea. Idempotente: si el producto ya tiene un MBR no-obsoleto, lo reusa.

    Returns dict: {ok, id, version, pasos, lote_size_g} | {ok, id, estado, ya_existe}
                  | {ok:False, error:'SIN_FORMULA'}
    """
    # No duplicar: si ya hay un MBR vigente (draft/en_revision/aprobado), reusar.
    ex = cur.execute(
        """SELECT id, estado, version FROM mbr_templates
            WHERE producto_nombre=? AND COALESCE(estado,'') != 'obsoleto'
            ORDER BY version DESC LIMIT 1""",
        (producto_nombre,),
    ).fetchone()
    if ex:
        return {'ok': True, 'id': ex[0], 'estado': ex[1], 'version': ex[2],
                'ya_existe': True}
    # Fórmula activa del producto (la receta ya existe en EOS).
    fh = cur.execute(
        """SELECT id, COALESCE(lote_size_kg,0), COALESCE(unidad_base_g,0)
             FROM formula_headers
            WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1
            ORDER BY id DESC LIMIT 1""",
        (producto_nombre,),
    ).fetchone()
    if not fh:
        return {'ok': False, 'error': 'SIN_FORMULA',
                'detail': f"'{producto_nombre}' no tiene fórmula activa"}
    formula_id = fh[0]
    items = cur.execute(
        """SELECT material_nombre, material_id, COALESCE(porcentaje,0),
                  COALESCE(cantidad_g_por_lote,0)
             FROM formula_items WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?))
               -- FIX 7-jul (audit fórmulas · M73): NO mezclar los items de un header CASE-DUPLICADO INACTIVO
               -- ('Blush Balm' activo=0) con el activo ('BLUSH BALM') → un MBR nuevo salía con 38 pasos al
               -- 167%. Crear MBR es PLANEACIÓN (filtro activo=0 OK · distinto del pesaje que es ejecución · M52).
               AND TRIM(producto_nombre) NOT IN (
                   SELECT TRIM(producto_nombre) FROM formula_headers WHERE COALESCE(activo,1)=0)
            ORDER BY cantidad_g_por_lote DESC""",
        (producto_nombre,),
    ).fetchall()
    # Tamaño de lote en g: lote_size_kg*1000, o unidad_base_g, o suma de componentes.
    lote_size_g = fh[1] * 1000.0 or fh[2] or sum(float(i[3] or 0) for i in items)
    if lote_size_g <= 0:
        lote_size_g = 1000.0  # fallback razonable; el usuario lo ajusta en draft
    version = _next_version(cur, producto_nombre)
    cur.execute(
        """INSERT INTO mbr_templates
             (producto_nombre, formula_version_id, version, estado, lote_size_g, creado_por)
           VALUES (?, ?, ?, 'draft', ?, ?)""",
        (producto_nombre, formula_id, version, float(lote_size_g), usuario),
    )
    mbr_id = cur.lastrowid
    orden = 0
    for it in items:
        orden += 1
        mat_nom, mat_id, pct, cant_g = it[0], it[1], it[2], it[3]
        # FIX 26-jul · el paso NO puede llevar un peso ABSOLUTO congelado. El texto de un paso
        # se escribe una vez y sirve para lotes de cualquier tamaño, así que un gramaje fijo
        # queda mintiendo en cuanto cambia el lote. Caso real: un lote de 10 kg mostraba
        # "Dispensar AGUA · 77.79 g" mientras la hoja de pesaje decía 7.779 g — 100 veces menos,
        # los dos números dentro del MISMO legajo (M5: el número que se muestra tiene que ser el
        # que decide). Encima venía de `cantidad_g_por_lote`, una columna DERIVADA que puede
        # quedar stale (M71) y que además es relativa a la base de la FÓRMULA, no a este lote.
        # Lo invariante es el PORCENTAJE; el peso de cada lote lo calcula la hoja de pesaje
        # desde la cantidad real (M67). %-first, con la derivada solo como respaldo.
        try:
            _pct = float(pct or 0)
        except (TypeError, ValueError):
            _pct = 0.0
        if _pct <= 0 and lote_size_g > 0:
            try:
                _pct = float(cant_g or 0) / float(lote_size_g) * 100.0
            except (TypeError, ValueError, ZeroDivisionError):
                _pct = 0.0
        desc = (f"Dispensar {mat_nom or mat_id} ({mat_id}) · {round(_pct, 3)}% de la fórmula "
                f"· el peso exacto de ESTE lote está en la hoja de pesaje")
        cur.execute(
            """INSERT INTO mbr_pasos
                 (mbr_template_id, orden, fase, descripcion, tipo_paso,
                  requiere_e_sign, requiere_qc)
               VALUES (?, ?, 'Dispensación', ?, 'dispensacion', 1, 0)""",
            (mbr_id, orden, desc),
        )
    # Paso de mezcla/homogenización tras la dispensación.
    orden += 1
    cur.execute(
        """INSERT INTO mbr_pasos
             (mbr_template_id, orden, fase, descripcion, tipo_paso,
              requiere_e_sign, requiere_qc)
           VALUES (?, ?, 'Fabricación', 'Mezcla y homogenización del granel', 'mezclado', 1, 0)""",
        (mbr_id, orden),
    )
    # Batch B · pasos genéricos de Envasado (OF) y Acondicionamiento (OA), para
    # que el EBR de cada fase tenga un esqueleto editable (el usuario los ajusta
    # por producto en el draft). Sin esto, un EBR de OF/OA nacería vacío.
    _pasos_fase = [
        ('Envasado', 'Luego que control de calidad apruebe el granel, se debe realizar el despeje de línea indicado.', 'envasado'),
        ('Envasado', 'Realizar el alistamiento de los envases y de la máquina de envasado que se requiere para este llenado.', 'envasado'),
        ('Envasado', 'Ajustar la máquina a la cantidad requerida.', 'envasado'),
        ('Envasado', 'Realizar controles periódicos al proceso de llenado con el fin de verificar que se mantiene en el rango de llenado.', 'envasado'),
        ('Envasado', 'Al finalizar despejar el área, dejar todo limpio y realizar la entrega al área de acondicionamiento.', 'envasado'),
        ('Acondicionamiento', 'Aprobación de arte/etiqueta y codificación (lote/vencimiento)', 'acondicionamiento'),
        ('Acondicionamiento', 'Etiquetado', 'acondicionamiento'),
        ('Acondicionamiento', 'Encajado / empaque secundario', 'acondicionamiento'),
    ]
    for _et, _desc, _tipo in _pasos_fase:
        orden += 1
        cur.execute(
            """INSERT INTO mbr_pasos
                 (mbr_template_id, orden, fase, descripcion, tipo_paso,
                  requiere_e_sign, requiere_qc)
               VALUES (?, ?, ?, ?, ?, 1, 0)""",
            (mbr_id, orden, _et, _desc, _tipo),
        )
    return {'ok': True, 'id': mbr_id, 'version': version, 'pasos': orden,
            'lote_size_g': float(lote_size_g)}


@bp.route("/api/brd/mbr/generar-desde-formula", methods=["POST"])
def mbr_generar_desde_formula():
    """Genera un MBR borrador desde la fórmula de UN producto. Body: {producto_nombre}."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in ADMIN_USERS and user not in CALIDAD_USERS:
        return jsonify({"error": "solo Admin/Calidad puede generar MBR"}), 403
    body = request.get_json(silent=True) or {}
    producto = (body.get("producto_nombre") or "").strip()
    if not producto:
        return jsonify({"error": "producto_nombre requerido"}), 400
    conn = get_db(); cur = conn.cursor()
    res = _generar_mbr_desde_formula(cur, producto, usuario=user)
    if not res.get("ok"):
        return jsonify(res), 404
    if not res.get("ya_existe"):
        audit_log(cur, usuario=user, accion="GENERAR_MBR_DESDE_FORMULA",
                  tabla="mbr_templates", registro_id=res["id"],
                  despues={"producto": producto, "version": res.get("version"),
                            "pasos": res.get("pasos")})
    conn.commit()
    return jsonify(res), (200 if res.get("ya_existe") else 201)


@bp.route("/api/brd/mbr/preparar-aprobado", methods=["POST"])
def mbr_preparar_aprobado():
    """Genera (si falta) Y APRUEBA el MBR de un producto en UN paso · para probar el
    legajo de envasado sin el flujo manual submit→firmar→aprobar. Firma con la identidad
    del usuario actual (e_signature REAL · 21 CFR Part 11 · auditable). Solo Admin/Calidad.
    Body: {producto_nombre}. Sebastián 9-jun-2026."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in ADMIN_USERS and user not in CALIDAD_USERS:
        return jsonify({"ok": False, "error": "solo Admin/Calidad puede aprobar MBR"}), 403
    body = request.get_json(silent=True) or {}
    producto = (body.get("producto_nombre") or "").strip()
    if not producto:
        return jsonify({"ok": False, "error": "producto_nombre requerido"}), 400
    _regenerar = body.get("regenerar") in (True, 1, "1", "true", "True", "si")
    conn = get_db(); cur = conn.cursor()
    if _regenerar:
        # Obsoletar el MBR vigente para generar uno fresco (nueva versión) con los pasos
        # actualizados · forma GMP correcta (obsoletar + version+1 · el trigger lo permite).
        # audit_log por cada MBR obsoletado (mutación regulada · ANTES del commit final).
        try:
            _viejos = cur.execute(
                "SELECT id FROM mbr_templates WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) "
                "AND COALESCE(estado,'') != 'obsoleto'", (producto,)).fetchall()
            cur.execute(
                "UPDATE mbr_templates SET estado='obsoleto', "
                "obsoleto_at_utc=datetime('now','utc'), "
                "obsoleto_motivo='Regeneración: pasos de envasado actualizados' "
                "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) "
                "AND COALESCE(estado,'') != 'obsoleto'",
                (producto,))
            for _row in _viejos:
                _vid = (_row[0] if not hasattr(_row, 'keys') else _row['id'])
                audit_log(cur, usuario=user, accion="OBSOLETAR_MBR_REGENERAR",
                          tabla="mbr_templates", registro_id=_vid,
                          antes={"estado": "vigente"},
                          despues={"estado": "obsoleto",
                                   "motivo": "Regeneración: pasos de envasado actualizados"})
        except Exception as _eo:
            __import__('logging').getLogger('brd').warning('regenerar: obsoletar fallo: %s', _eo)
    res = _generar_mbr_desde_formula(cur, producto, usuario=user)
    if not res.get("ok"):
        return jsonify({"ok": False, "error": res.get("error") or "no se pudo generar el MBR"}), 404
    mbr_id = res["id"]
    row = cur.execute("SELECT estado FROM mbr_templates WHERE id=?", (mbr_id,)).fetchone()
    estado = (row[0] if row else None)
    if estado == "aprobado":
        conn.commit()
        return jsonify({"ok": True, "id": mbr_id, "ya_aprobado": True})
    if estado == "draft":
        cur.execute("UPDATE mbr_templates SET estado='en_revision' WHERE id=? AND estado='draft'", (mbr_id,))
    try:
        from blueprints.firmas import crear_firma_directa
    except Exception:
        from api.blueprints.firmas import crear_firma_directa
    sig_id = crear_firma_directa(conn, username=user, record_table="mbr_templates",
                                 record_id=str(mbr_id), meaning="aprueba",
                                 comment="Aprobación rápida para prueba de legajo de envasado")
    cur.execute("""UPDATE mbr_templates SET estado='aprobado', aprobado_por=?,
                     aprobado_at_utc=datetime('now','utc'), aprobado_signature_id=?
                   WHERE id=? AND estado='en_revision'""", (user, sig_id, mbr_id))
    # FIX 7-jul (audit ultracode · M27 CAS): el UPDATE final aprueba solo desde en_revision (cierra la ventana
    # aprobar-vs-obsoletar concurrente). Acá el row ES en_revision (lo era, o L1409 lo promovió en esta tx).
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"ok": False, "error": "El MBR cambió de estado · refrescá", "codigo": "ESTADO_CAMBIO"}), 409
    audit_log(cur, usuario=user, accion="APROBAR_MBR_RAPIDO",
              tabla="mbr_templates", registro_id=mbr_id,
              despues={"producto": producto, "estado": "aprobado", "signature_id": sig_id})
    conn.commit()
    return jsonify({"ok": True, "id": mbr_id, "version": res.get("version"),
                    "pasos": res.get("pasos"), "signature_id": sig_id})


@bp.route("/api/brd/mbr/generar-todas-desde-formulas", methods=["POST"])
def mbr_generar_todas_desde_formulas():
    """Genera MBR borrador para TODAS las fórmulas activas sin MBR vigente (bulk).

    Idempotente: salta productos que ya tienen MBR no-obsoleto. Devuelve resumen.
    """
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in ADMIN_USERS and user not in CALIDAD_USERS:
        return jsonify({"error": "solo Admin/Calidad puede generar MBR"}), 403
    conn = get_db(); cur = conn.cursor()
    productos = [r[0] for r in cur.execute(
        """SELECT DISTINCT producto_nombre FROM formula_headers
            WHERE COALESCE(activo,1)=1 AND producto_nombre IS NOT NULL
              AND TRIM(producto_nombre) != ''
            ORDER BY producto_nombre""",
    ).fetchall()]
    creados, reusados, sin_formula = [], [], []
    for p in productos:
        res = _generar_mbr_desde_formula(cur, p, usuario=user)
        if not res.get("ok"):
            sin_formula.append(p)
        elif res.get("ya_existe"):
            reusados.append(p)
        else:
            creados.append({"producto": p, "mbr_id": res["id"], "pasos": res.get("pasos")})
            audit_log(cur, usuario=user, accion="GENERAR_MBR_DESDE_FORMULA",
                      tabla="mbr_templates", registro_id=res["id"],
                      despues={"producto": p, "version": res.get("version"),
                                "pasos": res.get("pasos"), "bulk": True})
    conn.commit()
    return jsonify({
        "ok": True,
        "total_formulas": len(productos),
        "mbr_creados": len(creados),
        "ya_tenian_mbr": len(reusados),
        "sin_formula": sin_formula,
        "creados": creados,
        "nota": "MBR creados en DRAFT · revisá pasos, agregá IPCs y aprobá cada uno "
                "(la aprobación exige e-firma). Recién ahí EBR_MODE=strict los usará.",
    }), 201


@bp.route("/api/brd/mbr/aprobar-todas", methods=["POST"])
def mbr_aprobar_todas():
    """ACTIVACIÓN MASIVA de legajos automáticos · Sebastián 5-jun-2026.

    Genera (desde fórmula) y APRUEBA en lote todos los MBR faltantes, con UNA
    re-autenticación (password + TOTP si MFA). 21 CFR Part 11 §11.200(a)(1)(ii):
    serie de firmas durante un acceso continuo controlado. Solo Admin/Calidad.
    Después, con EBR_MODE=warn, cada producción crea su legajo automático."""
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    password = body.get("password", "")
    totp = body.get("totp_token", "")
    try:
        from blueprints.firmas import (_verify_password, _verify_totp_if_enrolled,
                                       crear_firma_directa)
    except Exception:
        from api.blueprints.firmas import (_verify_password, _verify_totp_if_enrolled,
                                           crear_firma_directa)
    user = session.get("compras_user", "")
    if not _verify_password(user, password):
        return jsonify({"error": "Credenciales inválidas", "codigo": "PWD"}), 401
    ok_totp, factor = _verify_totp_if_enrolled(user, totp)
    if not ok_totp:
        return jsonify({"error": "Token MFA inválido", "codigo": "MFA"}), 401
    conn = get_db(); cur = conn.cursor()
    productos = [r[0] for r in cur.execute(
        "SELECT DISTINCT producto_nombre FROM formula_headers WHERE COALESCE(activo,1)=1 "
        "AND producto_nombre IS NOT NULL AND TRIM(producto_nombre)!='' "
        "ORDER BY producto_nombre").fetchall()]
    generados = 0; aprobados = 0; ya = 0; fallidos = []
    for p in productos:
        try:
            res = _generar_mbr_desde_formula(cur, p, usuario=user)
            if not res.get("ok"):
                fallidos.append({"producto": p, "error": res.get("error", "sin_formula")})
                continue
            mbr_id = res["id"]
            if not res.get("ya_existe"):
                generados += 1
            est_row = cur.execute("SELECT estado FROM mbr_templates WHERE id=?", (mbr_id,)).fetchone()
            est = (est_row[0] if est_row else "") or ""
            if est == "aprobado":
                ya += 1
                continue
            if est == "draft":
                cur.execute("UPDATE mbr_templates SET estado='en_revision' WHERE id=? AND estado='draft'", (mbr_id,))
            sig_id = crear_firma_directa(conn, username=user, record_table="mbr_templates",
                                         record_id=mbr_id, meaning="aprueba", auth_factor=factor)
            cur.execute(
                "UPDATE mbr_templates SET estado='aprobado', aprobado_por=?, "
                "aprobado_at_utc=datetime('now','utc'), aprobado_signature_id=? WHERE id=? AND estado='en_revision'",
                (user, sig_id, mbr_id))
            if cur.rowcount == 0:
                # FIX 7-jul (audit ultracode · M27 CAS per-item): otro worker ya lo aprobó/cambió → contar como
                # ya-aprobado y seguir · NUNCA abortar el bulk entero (rompería el RUNBOOK de encender EBR).
                ya += 1
                continue
            try:
                audit_log(cur, usuario=user, accion="APROBAR_MBR_BULK", tabla="mbr_templates",
                          registro_id=mbr_id, despues={"producto": p, "signature_id": sig_id})
            except Exception:
                pass
            aprobados += 1
        except Exception as e:
            fallidos.append({"producto": p, "error": str(e)[:140]})
    conn.commit()
    return jsonify({
        "ok": True,
        "total_productos": len(productos),
        "mbr_generados": generados,
        "mbr_aprobados": aprobados,
        "ya_estaban_aprobados": ya,
        "fallidos": fallidos,
        "nota": "MBR aprobados. Con EBR_MODE=warn cada producción crea su legajo automático.",
    })


def _get_or_create_draft_mbr(cur, producto, usuario=''):
    """Devuelve (mbr_id, creado) de un MBR DRAFT editable para el producto.
    Si el último MBR vigente es draft → lo reusa. Si está aprobado/en_revisión →
    crea una NUEVA versión draft (para no pisar el aprobado · BPM versionado).
    Si no existe ninguno → crea uno draft vinculado a la fórmula activa.
    Integración MyBatch · 2-jun-2026 · editar procedimiento/IPC desde Fórmulas."""
    row = cur.execute(
        "SELECT id, estado, version FROM mbr_templates "
        "WHERE producto_nombre=? AND COALESCE(estado,'')!='obsoleto' "
        "ORDER BY version DESC LIMIT 1", (producto,)).fetchone()
    if row and row["estado"] == "draft":
        return row["id"], False
    fh = cur.execute(
        "SELECT id AS fid, COALESCE(lote_size_kg,0) AS lk, COALESCE(unidad_base_g,0) AS ub "
        "FROM formula_headers WHERE producto_nombre=? AND COALESCE(activo,1)=1 "
        "ORDER BY id DESC LIMIT 1", (producto,)).fetchone()
    formula_id = fh["fid"] if fh else None
    lote_size_g = ((fh["lk"] if fh else 0) or 0) * 1000.0 or (fh["ub"] if fh else 0) or 1000.0
    version = _next_version(cur, producto)
    cur.execute(
        "INSERT INTO mbr_templates (producto_nombre, formula_version_id, version, estado, lote_size_g, creado_por) "
        "VALUES (?,?,?,'draft',?,?)", (producto, formula_id, version, float(lote_size_g), usuario))
    return cur.lastrowid, True


@bp.route("/api/brd/mbr/por-producto", methods=["GET"])
def mbr_por_producto():
    """Devuelve el MBR vigente (procedimiento + IPC) de un producto · para precargar
    el editor de Fórmulas. ?producto=NOMBRE."""
    err = _require_login()
    if err:
        return err
    producto = (request.args.get("producto") or "").strip()
    if not producto:
        return jsonify({"error": "producto requerido"}), 400
    conn = get_db(); cur = conn.cursor()
    row = cur.execute(
        "SELECT id, estado, version FROM mbr_templates "
        "WHERE producto_nombre=? AND COALESCE(estado,'')!='obsoleto' "
        "ORDER BY version DESC LIMIT 1", (producto,)).fetchone()
    if not row:
        return jsonify({"ok": True, "existe": False, "pasos": [], "ipc": []})
    mbr_id = row["id"]
    pasos = [{"orden": p["orden"], "descripcion": p["descripcion"],
              "fase": p["fase"], "resultado_label": p["notas"]}
             for p in cur.execute(
                 "SELECT orden, descripcion, COALESCE(fase,'') fase, COALESCE(notas,'') notas "
                 "FROM mbr_pasos WHERE mbr_template_id=? ORDER BY orden", (mbr_id,)).fetchall()]
    ipc = [{"parametro": s["parametro"], "unidad": s["unidad"],
            "valor_min": s["valor_min"], "valor_max": s["valor_max"],
            "especificacion": s["notas"]}
           for s in cur.execute(
               "SELECT parametro, COALESCE(unidad,'') unidad, valor_min, valor_max, COALESCE(notas,'') notas "
               "FROM ipc_specs WHERE mbr_template_id=?", (mbr_id,)).fetchall()]
    return jsonify({"ok": True, "existe": True, "mbr_id": mbr_id,
                    "estado": row["estado"], "version": row["version"],
                    "pasos": pasos, "ipc": ipc})


@bp.route("/api/brd/mbr/sync-procedimiento", methods=["POST"])
def mbr_sync_procedimiento():
    """Guarda el PROCEDIMIENTO (pasos de fabricación) + IPC de un producto como su
    MBR draft · lo usa el editor de Fórmulas (integración MyBatch · el procedimiento
    vive junto a la receta). Reemplaza pasos/IPC del draft. NO aprueba (eso exige
    e-firma vía /aprobar). Body: {producto_nombre, pasos:[{descripcion,fase?,
    resultado_label?,tipo_paso?}], ipc:[{parametro,unidad?,valor_min?,valor_max?,
    especificacion?,metodo?}]}."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in ADMIN_USERS and user not in CALIDAD_USERS:
        return jsonify({"error": "solo Admin/Calidad puede editar el MBR"}), 403
    b = request.get_json(silent=True) or {}
    producto = (b.get("producto_nombre") or "").strip()
    if not producto:
        return jsonify({"error": "producto_nombre requerido"}), 400
    pasos = b.get("pasos") or []
    ipc = b.get("ipc") or []
    conn = get_db(); cur = conn.cursor()
    mbr_id, creado = _get_or_create_draft_mbr(cur, producto, user)
    # reemplazar procedimiento (pasos)
    cur.execute("DELETE FROM mbr_pasos WHERE mbr_template_id=?", (mbr_id,))
    orden = 0
    for p in pasos:
        desc = (p.get("descripcion") or "").strip()
        if not desc:
            continue
        orden += 1
        tipo = (p.get("tipo_paso") or "mezclado").strip().lower()
        if tipo not in VALID_TIPO_PASO:
            tipo = "otro"
        cur.execute(
            "INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, tipo_paso, "
            "requiere_e_sign, requiere_qc, notas) VALUES (?,?,?,?,?,1,0,?)",
            (mbr_id, orden, (p.get("fase") or "Fabricación").strip(), desc, tipo,
             (p.get("resultado_label") or "").strip()))
    # reemplazar IPC
    cur.execute("DELETE FROM ipc_specs WHERE mbr_template_id=?", (mbr_id,))

    def _f(v):
        try:
            return float(v) if v not in (None, "") else None
        except (ValueError, TypeError):
            return None
    n_ipc = 0
    for s in ipc:
        par = (s.get("parametro") or "").strip()
        if not par:
            continue
        n_ipc += 1
        cur.execute(
            "INSERT INTO ipc_specs (mbr_template_id, parametro, unidad, valor_min, valor_max, "
            "metodo, obligatorio, notas) VALUES (?,?,?,?,?,?,?,?)",
            (mbr_id, par, (s.get("unidad") or "").strip(), _f(s.get("valor_min")), _f(s.get("valor_max")),
             (s.get("metodo") or "").strip(), 1 if s.get("obligatorio", 1) else 0,
             (s.get("especificacion") or s.get("notas") or "").strip()))
    audit_log(cur, usuario=user, accion="SYNC_MBR_PROCEDIMIENTO", tabla="mbr_templates",
              registro_id=mbr_id, despues={"producto": producto, "n_pasos": orden,
                                           "n_ipc": n_ipc, "mbr_creado": creado})
    conn.commit()
    return jsonify({"ok": True, "mbr_id": mbr_id, "n_pasos": orden, "n_ipc": n_ipc,
                    "mbr_creado": creado})


@bp.route("/api/brd/ebr", methods=["POST"])
def iniciar_ebr():
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    mbr_id = body.get("mbr_template_id")
    lote = (body.get("lote") or "").strip()
    if not mbr_id or not lote:
        return jsonify({"error": "mbr_template_id y lote requeridos"}), 400

    conn = get_db()
    cur = conn.cursor()
    mbr = cur.execute(
        """SELECT id, producto_nombre, version, estado, lote_size_g
           FROM mbr_templates WHERE id = ?""", (int(mbr_id),),
    ).fetchone()
    if not mbr:
        return jsonify({"error": "MBR no encontrado"}), 404
    if mbr["estado"] != "aprobado":
        return jsonify({
            "error": f"solo MBR aprobado puede instanciar EBR (actual: {mbr['estado']})",
        }), 409

    fase = (body.get("fase") or "fabricacion").strip().lower()
    if fase not in _FASES_VALIDAS:
        return jsonify({"error": f"fase inválida · use {sorted(_FASES_VALIDAS)}"}), 400

    # `lote` es UNIQUE a nivel BD (1 legajo por código de lote). Para que el
    # MISMO lote físico tenga legajo de fabricación/envasado/acondicionamiento,
    # el código de lote del EBR lleva sufijo de fase (·OF/·OA) y el lote físico
    # real se guarda en lote_codigo (vía asignar-lote-fisico). Batch B.
    if cur.execute("SELECT id FROM ebr_ejecuciones WHERE lote = ?", (lote,)).fetchone():
        return jsonify({"error": f"lote '{lote}' ya tiene un EBR"}), 409

    # Magnitud del lote (M67): si el body no trae cantidad_objetivo_g pero sí produccion_id,
    # deriva de la FUENTE DE VERDAD produccion_programada.cantidad_kg × 1000 antes de caer al
    # lote_size_g genérico del MBR (mismo orden que _intentar_crear_ebr_auto y crear_ebr_desde_mbr).
    try:
        _obj_body = body.get("cantidad_objetivo_g")
        if _obj_body in (None, ''):
            _obj_por_kg = 0.0
            _pid_body = body.get("produccion_id")
            if _pid_body:
                _ckb = cur.execute(
                    "SELECT COALESCE(cantidad_kg,0) FROM produccion_programada WHERE id=?",
                    (_pid_body,)).fetchone()
                if _ckb and _ckb[0]:
                    _obj_por_kg = round(float(_ckb[0]) * 1000, 1)
            cantidad_obj = _obj_por_kg or float(mbr["lote_size_g"])
        else:
            cantidad_obj = float(_obj_body)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_objetivo_g inválida"}), 400

    user = session.get("compras_user", "")
    numero_op = assign_numero_op(cur)
    cur.execute(
        """INSERT INTO ebr_ejecuciones
             (mbr_template_id, mbr_version, produccion_id, lote, numero_op,
              estado, iniciado_por, iniciado_at_utc, cantidad_objetivo_g, notas,
              fase)
           VALUES (?, ?, ?, ?, ?, 'iniciado', ?, datetime('now', 'utc'), ?, ?, ?)""",
        (mbr["id"], mbr["version"], body.get("produccion_id"), lote, numero_op,
         user, cantidad_obj, (body.get("notas") or "").strip(), fase),
    )
    ebr_id = cur.lastrowid

    pasos_mbr = cur.execute(
        """SELECT id, orden, descripcion, tipo_paso, equipo_requerido,
                  requiere_e_sign, requiere_qc, COALESCE(fase,'') AS fase
           FROM mbr_pasos WHERE mbr_template_id = ? ORDER BY orden""",
        (mbr["id"],),
    ).fetchall()
    # Batch B · clonar SOLO los pasos de la fase del EBR.
    n_clonados = 0
    for p in pasos_mbr:
        if _fase_canonica(p["fase"]) != fase:
            continue
        cur.execute(
            """INSERT INTO ebr_pasos_ejecutados
                 (ebr_id, mbr_paso_id, orden, descripcion, tipo_paso,
                  equipo_requerido, requiere_e_sign, requiere_qc, estado, fase)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)""",
            (ebr_id, p["id"], p["orden"], p["descripcion"], p["tipo_paso"],
             p["equipo_requerido"], p["requiere_e_sign"], p["requiere_qc"],
             p["fase"]),
        )
        n_clonados += 1
    conn.commit()
    audit_log(None, usuario=user, accion="INICIAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"mbr_template_id": mbr["id"], "lote": lote,
                        "numero_op": numero_op, "fase": fase,
                        "pasos_clonados": n_clonados})
    # Sebastián 7-jul (v2): ALERTA IMPORTANTE a Calidad · empezó la fabricación → que vaya al lado a supervisar
    # el despeje (firma dual en tiempo real, sin trabar al operario). Best-effort (no rompe el inicio del EBR).
    try:
        try:
            from blueprints.notif import push_notif_multi as _pnm
        except Exception:
            from api.blueprints.notif import push_notif_multi as _pnm
        _fase_lbl = (fase or 'fabricacion').capitalize()
        _pnm([q for q in _qc_verificadores() if q != user],
             'fabricacion_iniciada',
             f'Empezó {_fase_lbl} · andá a verificar el despeje',
             body=f'Lote {lote} · OP {numero_op}. El operario va a registrar el despeje de línea · '
                  f'estás para verificar cada paso al lado.',
             link='/planta', remitente=user, importante=True)
    except Exception:
        pass
    return jsonify({"ok": True, "id": ebr_id, "numero_op": numero_op,
                     "pasos": n_clonados}), 201


@bp.route("/api/brd/legajo-rapido", methods=["POST"])
def legajo_rapido():
    """Crea un legajo EBR rápido (producto + lote + fase) con el resolver canónico
    crear_ebr_desde_mbr (resuelve MBR aprobado, sufijo de fase, idempotencia). Para el
    botón '+ Nueva orden de envasado' de la página de Órdenes (9-jun-2026)."""
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    producto = (body.get("producto") or "").strip()
    lote = (body.get("lote") or "").strip()
    fase = (body.get("fase") or "envasado").strip().lower()
    if not producto or not lote:
        return jsonify({"ok": False, "error": "producto y lote requeridos"}), 400
    if fase not in _FASES_VALIDAS:
        return jsonify({"ok": False, "error": "fase inválida"}), 400
    conn = get_db(); cur = conn.cursor()
    user = session.get("compras_user", "")
    r = crear_ebr_desde_mbr(cur, producto_nombre=producto, lote=lote, usuario=user, fase=fase)
    if not r.get("ok") and r.get("error") == "LOTE_DUPLICADO":
        # ── "YA EXISTE" NO ES UN ERROR: ES LA RESPUESTA (17-ago) ──────────────────────────────
        # Este endpoint es el que usa la pantalla para **abrir o crear** el legajo de un lote, y
        # contestaba 409 justo en el caso más común -- que el legajo ya esté --, obligando a cada
        # llamador a inventar su propio rescate. El mismo defecto tenía el enganche
        # envasado→acondicionamiento y ahí ya se pagó: el operario cerraba el envasado y no
        # recibía el enlace al paso siguiente (M129: un registro que sale de una pantalla tiene
        # que decir a dónde se fue). Devolver el que existe hace que el endpoint sea idempotente
        # y que "abrir o crear" sea UNA llamada, no un árbol de casos en cada botón.
        _ya = conn.execute(
            "SELECT id, COALESCE(numero_op,'') FROM ebr_ejecuciones "
            " WHERE COALESCE(NULLIF(lote_codigo,''), lote)=? AND COALESCE(fase,'')=? "
            " ORDER BY id DESC LIMIT 1", (lote, fase)).fetchone()
        if _ya:
            r = {"ok": True, "id": _ya[0], "numero_op": _ya[1], "reusado": True}
    if not r.get("ok"):
        msg = ("El producto no tiene MBR APROBADO con pasos de esa fase · aprueba su MBR primero."
               if r.get("error") == "NO_MBR_APROBADO" else (r.get("detail") or r.get("error") or "error"))
        return jsonify({"ok": False, "error": msg, "detail": r.get("error")}), 409
    try:
        audit_log(cur, usuario=user or "sistema", accion="CREAR_LEGAJO_RAPIDO",
                  tabla="ebr_ejecuciones", registro_id=r.get("id"),
                  despues={"producto": producto, "lote": lote, "fase": fase})
    except Exception:
        pass
    conn.commit()
    # El enlace lleva a la pantalla de SU fase. `/planta/orden/<id>` redirige para las otras dos,
    # pero mandar al operario por un redirect es una vuelta que no hace falta dar.
    _link = {"envasado": "/planta/legajo-envasado/%s" % r.get("id"),
             "acondicionamiento": "/planta/legajo-acondicionamiento/%s" % r.get("id")}.get(
        fase, "/planta/orden/%s" % r.get("id"))
    return jsonify({"ok": True, "id": r.get("id"), "numero_op": r.get("numero_op"),
                    "link": _link, "fase": fase, "reusado": r.get("reusado", False)})


@bp.route("/api/brd/limpiar-demos", methods=["POST"])
def limpiar_demos():
    """Borra TODOS los demos del batch record (produccion_programada marcada DEMO_LEGAJO + descarta sus legajos +
    legajos DEMO-* sin liberar). NO toca producciones reales. Sebastian 30-jun."""
    err = _require_login()
    if err:
        return err
    from database import get_db
    conn = get_db()
    c = conn.cursor()
    n_prod = 0
    n_leg = 0
    n_mp = 0
    try:
        _ids = [r[0] for r in c.execute(
            "SELECT id FROM produccion_programada WHERE UPPER(COALESCE(observaciones,'')) LIKE '%DEMO_LEGAJO%'"
        ).fetchall()]
        if _ids:
            _ph = ','.join('?' for _ in _ids)
            try:
                c.execute('SAVEPOINT _lim_demo')
                c.execute("UPDATE ebr_ejecuciones SET estado='descartado' WHERE produccion_id IN (" + _ph + ") "
                          "AND COALESCE(liberado_at_utc,'')=''", tuple(_ids))
                n_leg += (c.rowcount or 0)
                c.execute('RELEASE SAVEPOINT _lim_demo')
            except Exception:
                try:
                    c.execute('ROLLBACK TO SAVEPOINT _lim_demo')
                except Exception:
                    pass
            n_prod = c.execute("DELETE FROM produccion_programada "
                               "WHERE UPPER(COALESCE(observaciones,'')) LIKE '%DEMO_LEGAJO%'").rowcount or 0
        try:
            c.execute('SAVEPOINT _lim_demo2')
            c.execute("UPDATE ebr_ejecuciones SET estado='descartado' WHERE UPPER(COALESCE(lote,'')) LIKE 'DEMO-%' "
                      "AND COALESCE(liberado_at_utc,'')='' AND COALESCE(estado,'') <> 'descartado'")
            n_leg += (c.rowcount or 0)
            c.execute('RELEASE SAVEPOINT _lim_demo2')
        except Exception:
            try:
                c.execute('ROLLBACK TO SAVEPOINT _lim_demo2')
            except Exception:
                pass
        # La materia prima que el demo sembró en bodega se retira con él · si no, queda stock
        # fantasma en el kardex de un material que sólo existe para la demostración, y el
        # inventario dice que hay 50 kg de algo que nadie compró (M172).
        #
        # ⚠ Se retira SOLO el lote del demo (`DEMO-MP-1`), nunca por material: si alguien llegara
        # a cargar un lote real bajo esos códigos, borrarlo sería tocar inventario de verdad.
        try:
            c.execute('SAVEPOINT _lim_demo3')
            # Por LOTE, sin filtrar material: ese lote lo crea únicamente el demo, y desde que
            # el stock se siembra según la fórmula los materiales ya no son una lista fija.
            n_mp = c.execute("DELETE FROM movimientos WHERE lote=?",
                             (_DEMO_MP_LOTE,)).rowcount or 0
            c.execute('RELEASE SAVEPOINT _lim_demo3')
        except Exception as _e:
            # se DICE que quedó, en vez de callar: un demo a medio borrar se ve igual que uno
            # limpio, y el stock fantasma aparece semanas después sin explicación (M4/M100)
            log.warning("limpiar_demos · no se pudo retirar la MP del demo: %s", _e)
            try:
                c.execute('ROLLBACK TO SAVEPOINT _lim_demo3')
            except Exception:
                pass
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)[:180]}), 500
    conn.commit()
    return jsonify({"ok": True, "producciones_borradas": n_prod, "legajos_descartados": n_leg,
                    "movimientos_mp_demo_retirados": n_mp})


@bp.route("/api/brd/demo-legajo", methods=["POST"])
def demo_legajo():
    """DEMO (Sebastián 25-jun) · crea una orden EN CURSO + su legajo EBR para VER el batch record inline
    en Fabricación, SIN descontar MP (inserción directa · no pasa por el motor de descuento). Marcada
    'DEMO_LEGAJO' en observaciones → se borra con 🧹 Limpiar. Solo para ver la UI."""
    err = _require_login()
    if err:
        return err
    from database import get_db
    conn = get_db(); cur = conn.cursor()
    row = cur.execute("SELECT producto_nombre FROM mbr_templates WHERE estado='aprobado' "
                      "ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return jsonify({"error": "No hay ningún MBR aprobado · activá los legajos primero en "
                                 "/planta/activar-legajos"}), 400
    producto = row[0]
    from datetime import datetime, timedelta
    _co = datetime.now() - timedelta(hours=5)
    lote = 'DEMO-' + _co.strftime('%y%m%d%H%M%S')
    user = session.get("compras_user", "")
    cur.execute(
        "INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, lotes, "
        "inicio_real_at, estado, origen, observaciones) VALUES (?,?,?,?,?,?,?,?)",
        (producto, _co.strftime('%Y-%m-%d'), 10, 1, _co.isoformat(timespec='seconds'),
         'programado', 'eos_plan', 'DEMO_LEGAJO · sin descuento de MP · borrar con 🧹 Limpiar'))
    pid = cur.lastrowid
    try:
        r = crear_ebr_desde_mbr(cur, producto_nombre=producto, lote=lote, produccion_id=pid,
                                cantidad_objetivo_g=10000, usuario=user, notas='DEMO')
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "No se pudo crear el legajo demo: " + str(e)[:160]}), 500
    conn.commit()
    return jsonify({"ok": True, "producto": producto, "lote": lote, "produccion_id": pid,
                    "ebr_id": (r.get("id") if isinstance(r, dict) else None)})


@bp.route("/api/brd/ebr", methods=["GET"])
def listar_ebr():
    err = _require_login()
    if err:
        return err
    estado = (request.args.get("estado") or "").strip()
    lote = (request.args.get("lote") or "").strip()
    numero_op = (request.args.get("numero_op") or "").strip()
    fase = (request.args.get("fase") or "").strip().lower()
    where, params = [], []
    if estado:
        where.append("estado = ?")
        params.append(estado)
    else:
        # por defecto NO mostrar legajos descartados (p.ej. los de prueba que limpió el jefe)
        where.append("LOWER(COALESCE(estado,'')) <> 'descartado'")
    if fase:
        # COALESCE → legajos viejos (fase NULL) cuentan como 'fabricacion'
        where.append("COALESCE(fase,'fabricacion') = ?")
        params.append(fase)
    if lote:
        where.append("lote = ?")
        params.append(lote)
    if numero_op:
        # Match exacto · MyBatch-compat
        where.append("numero_op = ?")
        params.append(numero_op)
    sql = """SELECT id, mbr_template_id, mbr_version, produccion_id, lote,
                    numero_op, estado, iniciado_por, iniciado_at_utc,
                    completado_at_utc, liberado_por, liberado_at_utc,
                    liberado_signature_id, rechazado_motivo,
                    cantidad_objetivo_g, cantidad_real_g, yield_pct, notas,
                    COALESCE(fase,'fabricacion') AS fase
             FROM ebr_ejecuciones"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY iniciado_at_utc DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"items": [_ebr_to_dict(r) for r in rows]})


@bp.route("/brd/timeline/<int:ebr_id>", methods=["GET"])
def brd_timeline_page(ebr_id):
    """MyBatch parity Sprint D · 21-may-2026 · Timeline visual del BR.

    Página HTML standalone con timeline cronológico de eventos del lote:
    pesajes · pasos · IPC · liberación · todo en orden temporal con
    badges de estado. Renderiza vista-completa pero como línea de tiempo.
    """
    err = _require_login()
    if err:
        return err
    # Timeline estilo MyBatch (Sebastián 6-jun-2026) · "Batch Record Bulk Lote N°"
    # línea de tiempo vertical de NODOS de etapa (no eventos sueltos): Orden de
    # Producción → Instrucciones de Fabricación (con estado por etapa) → Liberación.
    # OJO ESCAPES: este HTML va en un string Python '''...''' → NUNCA usar \n/\t
    # crudos en cadenas JS (Python los volvería saltos de línea reales y romperían
    # el <script>). Ver memoria feedback_js_escapes_template_python.
    html = '''<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Timeline BR · ''' + str(ebr_id) + '''</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;font-family:'Inter',system-ui,Arial,sans-serif}
body{margin:0;background:var(--cx-primary-pale, #f5f3ff);padding:22px;color:var(--cx-text, #0f172a)}
.wrap{max-width:880px;margin:0 auto}
a.back{display:inline-flex;align-items:center;gap:8px;background:var(--cx-card, #fff);color:var(--cx-primary-text, #7c3aed);font-size:13px;font-weight:700;text-decoration:none;padding:9px 16px;border-radius:10px;border:1px solid #e9d5ff;box-shadow:0 2px 8px rgba(124,58,237,.10)}
h1{text-align:center;color:var(--cx-text, #1e293b);margin:18px 0 2px;font-size:24px}
.sub{text-align:center;color:var(--cx-primary-text, #6d28d9);font-weight:600;margin:0 0 24px;font-size:16px}
.tl{position:relative;padding-left:56px}
.tl::before{content:'';position:absolute;left:21px;top:8px;bottom:8px;width:3px;background:#fbcfe8}
.node{position:relative;margin-bottom:26px}
.node .ico{position:absolute;left:-49px;top:6px;width:42px;height:42px;border-radius:50%;background:#fb923c;color:#fff;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 3px 10px rgba(251,146,60,.4)}
.card{background:var(--cx-card, #fff);border-radius:14px;padding:18px 20px;box-shadow:0 3px 14px rgba(76,29,149,.08)}
.tag{display:inline-block;background:#fb923c;color:#fff;font-size:11px;font-weight:800;letter-spacing:.4px;padding:4px 12px;border-radius:6px;text-transform:uppercase;margin-bottom:12px}
.tag.fab{background:#7c2d12}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;font-size:13px}
.grid .lbl{color:var(--cx-text-faint, #94a3b8);font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.3px}
.grid .val{color:var(--cx-text, #1e293b);margin-top:2px;font-weight:600}
.mono{font-family:ui-monospace,monospace;color:var(--cx-info-text, #1e40af)}
.stages{list-style:none;margin:6px 0 0;padding:0}
.stages li{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 4px;border-bottom:1px solid var(--cx-border-soft, #f1f5f9);font-size:13.5px}
.stages li:last-child{border-bottom:none}
.st-badge{font-size:10px;font-weight:800;padding:3px 10px;border-radius:20px;text-transform:uppercase;letter-spacing:.3px;white-space:nowrap}
.fin{background:var(--cx-success-pale, #dcfce7);color:var(--cx-success-text, #166534)}
.proc{background:#fef9c3;color:#854d0e}
.pend{background:var(--cx-border-soft, #f1f5f9);color:var(--cx-text-faint, #94a3b8)}
.btns{margin-top:14px;display:flex;gap:10px;flex-wrap:wrap}
.btns a{border:none;border-radius:9px;padding:9px 16px;font-size:12.5px;font-weight:700;cursor:pointer;text-decoration:none;color:#fff}
.b-ver{background:#fb923c}.b-desc{background:var(--cx-danger, #ef4444)}
</style></head><body>
<div class="wrap">
<a class="back" href="/planta/orden/''' + str(ebr_id) + '''">&larr; Volver a la Orden</a>
<h1 id="t1">Batch Record</h1>
<div class="sub" id="t2">Cargando…</div>
<div class="tl" id="timeline"></div>
</div>
<script>
var EBR_ID = ''' + str(ebr_id) + ''';
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function dt(s){return s?esc(String(s).substring(0,16).replace('T',' ')):'·';}
function stBadge(done,partial){
  if(done) return '<span class="st-badge fin">Finalizado</span>';
  if(partial) return '<span class="st-badge proc">En proceso</span>';
  return '<span class="st-badge pend">Pendiente</span>';
}
async function load(){
  try{
    var ctrl=new AbortController();var to=setTimeout(function(){ctrl.abort();},15000);
    var r;
    try{ r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store',signal:ctrl.signal}); }
    catch(fe){ clearTimeout(to); document.getElementById('t2').textContent='No se pudo cargar (timeout/red).'; return; }
    clearTimeout(to);
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){ document.getElementById('t2').textContent='Error: '+esc(d.error||r.status); return; }
    var h=d.header||{};
    // El titulo dice DE QUE es el legajo. "Bulk" es el granel: en un lote de envasado o
    // de acondicionamiento decia lo que no era, y esta es la pantalla a la que llega
    // Calidad desde su cola de controles.
    var _tf=(h.fase||'fabricacion');
    var _tit=(_tf==='envasado')?'Batch Record de Envasado · Lote N°: '
            :(_tf==='acondicionamiento')?'Batch Record de Acondicionamiento · Lote N°: '
            :'Batch Record Bulk Lote N°: ';
    document.getElementById('t1').textContent=_tit+(h.lote_codigo||'·');
    document.getElementById('t2').textContent=h.producto||h.titulo||'·';
    // Estado de cada etapa (honesto · desde la data real)
    var prec=d.precauciones||[], chk=d.despeje_checklist||[], sheet=d.pesaje_sheet||[], pasos=d.pasos||[];
    var estado=(h.estado||'').toLowerCase();
    var liberado=(estado.indexOf('liber')>=0)||!!h.liberado_at_utc;
    var completado=liberado||(estado.indexOf('complet')>=0)||!!h.completado_at_utc;
    var precDone=prec.length>0;
    var chkDone=chk.length>0 && chk.every(function(x){return x.cumple===1;});
    var chkPart=chk.some(function(x){return x.cumple!=null;});
    var sheetDone=sheet.length>0 && sheet.every(function(x){return x.pesado;});
    var sheetPart=sheet.some(function(x){return x.pesado;});
    var pasosDone=completado||(pasos.length>0 && pasos.every(function(p){return p.completado_flag;}));
    var pasosPart=pasos.some(function(p){return p.completado_flag;});
    // Etapas segun la FASE del legajo. Antes estaban cableadas a fabricacion, asi que
    // un lote de envasado mostraba "Pesaje de Materias Primas" y "Mezclado" -- controles
    // que en esa fase no existen (M205: una lista que no es de la fase se contesta por
    // inercia). Y esta pantalla es a donde llega Calidad desde su cola de controles.
    var _fase=(h.fase||'fabricacion');
    var etapas;
    if(_fase==='envasado'){
      etapas=[
        {n:'1. Precauciones', done:precDone, part:false},
        {n:'2. Despeje de Línea - Envasado', done:chkDone, part:chkPart},
        {n:'3. Alistamiento de envase y tapa', done:sheetDone, part:sheetPart},
        {n:'4. Llenado, control de peso y sellado', done:pasosDone, part:pasosPart}
      ];
    } else if(_fase==='acondicionamiento'){
      etapas=[
        {n:'1. Precauciones', done:precDone, part:false},
        {n:'2. Despeje de Línea - Acondicionamiento', done:chkDone, part:chkPart},
        {n:'3. Alistamiento de etiquetas y empaque', done:sheetDone, part:sheetPart},
        {n:'4. Etiquetado, empaque y cierre', done:pasosDone, part:pasosPart}
      ];
    } else {
      etapas=[
        {n:'1. Precauciones', done:precDone, part:false},
        {n:'2. Despeje de Línea - Dispensación', done:chkDone, part:chkPart},
        {n:'3. Pesaje de Materias Primas', done:sheetDone, part:sheetPart},
        {n:'4. Fabricación / Mezclado', done:pasosDone, part:pasosPart}
      ];
    }
    var etapasHtml=etapas.map(function(e){
      return '<li><span>'+esc(e.n)+'</span>'+stBadge(e.done,e.part)+'</li>';
    }).join('');
    // Nodo 1: Orden de Producción
    var ordenCard=
      '<div class="node"><div class="ico">📋</div><div class="card">'+
        '<span class="tag">Orden de Producción</span>'+
        '<div class="grid">'+
          '<div><div class="lbl">'+(_fase==='fabricacion'?'N° de Lote Bulk':'N° de Lote')+'</div><div class="val mono">'+esc(h.lote_codigo||'·')+'</div></div>'+
          '<div><div class="lbl">Tamaño de Lote</div><div class="val">'+(h.lote_size_g!=null?Number(h.lote_size_g).toLocaleString('es-CO')+' g':'·')+'</div></div>'+
          '<div><div class="lbl">Fecha / Hora</div><div class="val">'+dt(h.iniciado_at_utc)+'</div></div>'+
          '<div><div class="lbl">Estado Actual</div><div class="val">'+esc(h.estado||'·')+'</div></div>'+
          '<div><div class="lbl">Elaborado por</div><div class="val">'+esc(h.operario||'·')+'</div></div>'+
          '<div><div class="lbl">Supervisado por</div><div class="val">'+esc(h.supervisado_por||'·')+'</div></div>'+
        '</div>'+
        '<div class="btns">'+
          '<a class="b-ver" href="/planta/orden/'+EBR_ID+'">Ver</a>'+
          '<a class="b-desc" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">📄 Descargar</a>'+
        '</div>'+
      '</div></div>';
    // Nodo 2: las instrucciones de LA FASE de este lote.
    // El rótulo decía "Fabricación" siempre: en un lote de envasado quedaba anunciando una
    // fase que no es la suya, justo encima de los pasos correctos (M205/M214 · se arregló
    // el título y los pasos, y este rótulo quedó atrás porque no se MIRÓ la pantalla).
    var _titFase = (_fase==='envasado') ? 'Instrucciones de Envasado'
                 : (_fase==='acondicionamiento') ? 'Instrucciones de Acondicionamiento'
                 : 'Instrucciones de Fabricación';
    var instrCard=
      '<div class="node"><div class="ico">📖</div><div class="card">'+
        '<span class="tag fab">'+_titFase+'</span>'+
        '<ul class="stages">'+etapasHtml+'</ul>'+
        '<div class="btns"><a class="b-ver" href="/planta/orden/'+EBR_ID+'">Ver</a></div>'+
      '</div></div>';
    // Nodo 3 (si liberado/completado): Liberación QC
    var libCard='';
    if(completado){
      libCard='<div class="node"><div class="ico" style="background:'+(liberado?'#16a34a':'#0891b2')+'">'+(liberado?'🔓':'🏁')+'</div><div class="card">'+
        '<span class="tag" style="background:'+(liberado?'#16a34a':'#0891b2')+'">'+(liberado?'Liberación de Calidad':'Fabricación Completada')+'</span>'+
        '<div class="grid">'+
          '<div><div class="lbl">'+(liberado?'Liberado por':'Completado')+'</div><div class="val">'+esc(liberado?(h.liberado_por_full||h.liberado_por||'·'):dt(h.completado_at_utc))+'</div></div>'+
          (h.rechazado_at_utc?'<div><div class="lbl">⛔ Rechazado</div><div class="val">'+esc(h.rechazado_motivo||'')+'</div></div>':'')+
        '</div>'+
      '</div></div>';
    }
    document.getElementById('timeline').innerHTML = ordenCard + instrCard + libCard;
  }catch(e){
    document.getElementById('t2').textContent='Error: '+esc(e&&e.message||e);
  }
}
load();
</script></body></html>'''
    return Response(html, mimetype='text/html')


def _pp_id_para_producto(cur, producto, ebr_produccion_id=None):
    """Resuelve el produccion_programada.id relevante para un producto (no hay FK · se
    enlaza por producto). Prefiere el produccion_id del EBR si coincide; si no, el más
    reciente no-cancelado del producto. Devuelve id o None."""
    if not producto:
        return None
    try:
        if ebr_produccion_id:
            r = cur.execute(
                "SELECT id FROM produccion_programada WHERE id=? "
                "AND LOWER(TRIM(producto))=LOWER(TRIM(?))",
                (ebr_produccion_id, producto)).fetchone()
            if r:
                return r[0]
        r = cur.execute(
            "SELECT id FROM produccion_programada "
            "WHERE LOWER(TRIM(producto))=LOWER(TRIM(?)) "
            "AND COALESCE(estado,'') NOT IN ('cancelado') "
            "ORDER BY id DESC LIMIT 1", (producto,)).fetchone()
        return r[0] if r else None
    except Exception:
        return None


def _codigos_de_envasado(cur, producto):
    """Los códigos que consume el ENVASADO de ese producto: envase, tapa y caja.

    Sirven para que el legajo de ACONDICIONAMIENTO no los liste como material suyo. La regla es
    de Sebastián y está escrita en `cerrar-envasado` desde el 20-jul: *"Tapa/caja siempre el
    default. Etiqueta NO va acá (se pone en Acondicionamiento)"*.
    """
    codigos = set()
    try:
        for r in cur.execute(
            "SELECT COALESCE(envase_codigo,''), COALESCE(tapa_codigo,''), COALESCE(caja_codigo,'') "
            "  FROM producto_presentaciones "
            " WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1",
                (producto or '',)).fetchall():
            for c in r:
                c = str(c or '').strip().upper()
                if c:
                    codigos.add(c)
    except Exception as _e:
        # Sin la lista no se puede filtrar · se DICE en el log y se devuelve vacío, que deja el
        # comportamiento anterior en vez de esconder material en silencio (M4/M94).
        __import__('logging').getLogger('brd').warning(
            'no pude leer los códigos de envasado de %s: %s', producto, _e)
    return codigos


def _materiales_envase_planeados(conn, producto, ebr_produccion_id=None, lote='',
                                 excluir_envasado=False):
    """Material de envase PLANEADO de un producto desde la PROGRAMACIÓN (paridad MyBatch ·
    11-jun): por cada presentación, el envase + sus componentes (tapa/gotero/etiqueta vía
    sku_mee_config) con cant. REQUERIDA = unidades de esa presentación. Auto-carga la
    sección 'Materiales de Envase' del legajo cuando aún no hay envasado real. READ-ONLY.

    ⚠ `excluir_envasado=True` lo usa el legajo de ACONDICIONAMIENTO (17-ago). Sin eso, esa
    pantalla listaba el FRASCO como su material de empaque -- porque cae a este helper y, sin
    `sku_mee_config` para el SKU, devuelve sólo el envase --, o sea justo lo que el envasado YA
    consumió. Quien llenara ahí la conciliación lo estaría contando dos veces. En
    acondicionamiento el material es la etiqueta y el estuche; el frasco, la tapa y la caja son
    del envasado (Sebastián 20-jul)."""
    if not producto:
        return []
    cur = conn.cursor()
    pp_id = _pp_id_para_producto(cur, producto, ebr_produccion_id)
    if not pp_id:
        return []
    try:
        from blueprints.programacion import _composicion_envases_lote
    except Exception:
        try:
            from api.blueprints.programacion import _composicion_envases_lote
        except Exception:
            return []
    try:
        comp = _composicion_envases_lote(cur, pp_id) or {}
    except Exception:
        return []
    variantes = comp.get('variantes') or []
    if not variantes:
        return []
    # sku_mee_config: sku_codigo(upper) -> [(mee_codigo, cant_por_unidad)]
    sku_mee = {}
    try:
        for r in cur.execute(
            "SELECT UPPER(TRIM(sku_codigo)), mee_codigo, COALESCE(cantidad_por_unidad,1) "
            "FROM sku_mee_config WHERE COALESCE(aplica,1)=1").fetchall():
            if r[1]:
                sku_mee.setdefault(r[0], []).append((str(r[1]).strip(), float(r[2] or 1)))
    except Exception:
        sku_mee = {}
    acc = {}  # codigo_mee -> requerida total
    for v in variantes:
        uds = int(v.get('unidades_estimadas') or 0)
        if uds <= 0:
            continue
        sku = (v.get('sku_shopify') or '').strip().upper()
        comps = sku_mee.get(sku)
        if comps:  # envase + tapa + gotero + etiqueta… definidos por SKU
            for cod, cx in comps:
                if cod:
                    acc[cod] = acc.get(cod, 0.0) + uds * cx
        else:  # sin config MEE · al menos el envase de la presentación
            env = (v.get('envase_codigo') or '').strip()
            if env:
                acc[env] = acc.get(env, 0.0) + uds
    if excluir_envasado:
        _del_envasado = _codigos_de_envasado(cur, producto)
        acc = {c: v for c, v in acc.items() if str(c).strip().upper() not in _del_envasado}
    if not acc:
        return []
    out = []
    for cod, req in sorted(acc.items(), key=lambda x: -x[1]):
        nom = ''
        try:
            n = cur.execute("SELECT COALESCE(descripcion,'') FROM maestro_mee WHERE codigo=?",
                            (cod,)).fetchone()
            nom = (n[0] if n else '') or ''
        except Exception:
            pass
        out.append({
            'lote_envasado': lote, 'lote_acond': lote,
            'material': (cod + (' ' + nom if nom else '')),
            'lote_material': '', 'requerida': round(req, 0),
            'recibida': None, 'devuelta': None, 'utilizada': None,
            'averiada': None, 'diferencia': None,
        })
    return out


def _presentaciones_planeadas(conn, producto, ebr_produccion_id=None):
    """Presentaciones PLANEADAS (estado 'Programado') de un producto desde la
    PROGRAMACIÓN · para auto-cargar el legajo de Envasado/Acondicionamiento cuando aún
    no hay envasado/acond real registrado (paridad MyBatch · 10-jun-2026).

    Una sola producción de granel → N presentaciones = envase × cliente:
      - Animus (DTC): variantes por ratio de ventas (helper canónico
        `_composicion_envases_lote`) MENOS la porción que va a clientes B2B (no doble
        contar).
      - B2B: una fila por aporte de pedido (`pedidos_b2b_lote`: cliente + envase + uds).

    Best-effort y READ-ONLY: si no hay programación enlazable o algo falla → []
    (el legajo queda como antes, sin presentaciones). NO escribe nada."""
    if not producto:
        return []
    cur = conn.cursor()
    pp_id = _pp_id_para_producto(cur, producto, ebr_produccion_id)
    if not pp_id:
        return []
    # Reusar las funciones CANÓNICAS de programación (mismas que el modal "Plan de
    #    envasado") para que el legajo muestre EXACTO lo mismo: Animus DTC (composición −
    #    B2B) + una fila por cada cliente B2B (ej. Kelly/Fernando Meza). 10-jun-2026.
    try:
        from blueprints.programacion import _composicion_envases_lote, _plan_envasado_por_cliente
    except Exception:
        try:
            from api.blueprints.programacion import _composicion_envases_lote, _plan_envasado_por_cliente
        except Exception:
            return []
    try:
        comp = _composicion_envases_lote(cur, pp_id) or {}
        plan = _plan_envasado_por_cliente(cur, pp_id, comp.get('variantes') or [])
    except Exception:
        return []
    out = []
    for grupo in (plan or []):
        cli = grupo.get('cliente') or 'Animus'
        for env in (grupo.get('envases') or []):
            uds = int(env.get('uds') or 0)
            ml = float(env.get('ml') or 0)
            out.append({
                'presentacion': env.get('etiqueta') or (f'{int(ml)}ml' if ml else '·'),
                'lote': '', 'unidades': uds, 'area': '',
                'cantidad_ml': (uds * ml) if (uds and ml) else None,
                'unidades_final': None, 'rend_pct': None,
                'estado': 'Programado', 'cliente': cli,
            })
    return out


def _mbr_desactualizados(conn):
    """Legajos ABIERTOS que quedaron colgados de una versión de MBR que ya no es la aprobada.

    Cuando se aprueba una versión nueva del MBR (por ejemplo, al cargar el instructivo real de
    fabricación), la anterior pasa a `obsoleto` — pero los legajos YA ABIERTOS siguen apuntando
    a la vieja. Caso real (26-jul): las órdenes en curso mostraban 3 pasos genéricos de relleno
    mientras la v2 aprobada tenía el procedimiento completo. El instructivo existía y no llegaba
    al piso. Los legajos NUEVOS sí toman la aprobada (`crear_ebr_desde_mbr`).

    Núcleo COMPARTIDO por la vista previa y el apply: el número que se muestra es el que decide.
    """
    # OJO: `ebr_ejecuciones` NO tiene `producto_nombre` — el producto vive en el MBR
    # (`mbr_templates.producto_nombre`). Escribirlo como columna del EBR daba "no such column"
    # (M12a · columna fantasma). Lo cazó el test antes de que llegara a producción.
    filas = conn.execute(
        """SELECT e.id, e.numero_op, COALESCE(m.producto_nombre,'') AS producto_nombre,
                  e.estado, e.mbr_template_id,
                  e.mbr_version, COALESCE(m.estado,'') AS estado_mbr,
                  COALESCE(e.lote_codigo, e.lote) AS lote, COALESCE(e.fase,'fabricacion') AS fase
             FROM ebr_ejecuciones e
             LEFT JOIN mbr_templates m ON m.id = e.mbr_template_id
            WHERE LOWER(COALESCE(e.estado,'')) NOT IN ('liberado','rechazado','completado','cancelado')
            ORDER BY e.id DESC""",
    ).fetchall()
    out = []
    for f in filas:
        # El MBR aprobado de HOY para ese producto · mismo criterio que crear_ebr_desde_mbr
        # (UPPER/TRIM · si acá resolviera distinto, la herramienta propondría otra versión).
        mejor = conn.execute(
            """SELECT id, version FROM mbr_templates
                WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND estado='aprobado'
                ORDER BY version DESC, id DESC LIMIT 1""",
            (f['producto_nombre'],),
        ).fetchone()
        if not mejor or int(mejor['id']) == int(f['mbr_template_id'] or 0):
            continue
        # ¿Ya se ejecutó algún paso? Cambiar el procedimiento con el lote en marcha NO es una
        # corrección automática: es una desviación que decide Calidad. Se reporta, no se toca.
        ejecutados = conn.execute(
            "SELECT COUNT(*) FROM ebr_pasos_ejecutados WHERE ebr_id=? "
            "AND LOWER(COALESCE(estado,'pendiente'))<>'pendiente'", (f['id'],)).fetchone()[0]
        # Los pasos que REALMENTE va a recibir: sólo los de SU fase. Contar todos los del MBR
        # miente — y con consecuencias: un MBR con el instructivo de fabricación no tiene pasos
        # de envasado, así que re-vincular ahí un legajo de ENVASADO lo deja en CERO pasos.
        # Pasó de verdad el 26-jul con OP-2026-0027 y hubo que revertirlo. El clon filtra por
        # fase, así que la cuenta tiene que filtrar por fase también (M5: el número que se
        # muestra tiene que ser el que decide).
        _fase_ebr = f['fase'] if f['fase'] in _FASES_VALIDAS else 'fabricacion'
        pasos_nuevos = sum(
            1 for r in conn.execute(
                "SELECT COALESCE(fase,'') FROM mbr_pasos WHERE mbr_template_id=?",
                (mejor['id'],)).fetchall()
            if _fase_canonica(r[0]) == _fase_ebr)
        out.append({
            'ebr_id': f['id'], 'numero_op': f['numero_op'], 'producto': f['producto_nombre'],
            'lote': f['lote'], 'fase': f['fase'], 'estado_ebr': f['estado'],
            'mbr_actual': f['mbr_template_id'], 'version_actual': f['mbr_version'],
            'estado_mbr_actual': f['estado_mbr'] or '(no existe)',
            'mbr_aprobado': mejor['id'], 'version_aprobada': mejor['version'],
            'pasos_actuales': conn.execute(
                "SELECT COUNT(*) FROM ebr_pasos_ejecutados WHERE ebr_id=?", (f['id'],)).fetchone()[0],
            'pasos_nuevos': pasos_nuevos,
            'pasos_ya_ejecutados': ejecutados,
            'movible': ejecutados == 0 and pasos_nuevos > 0,
            'motivo': ('' if (ejecutados == 0 and pasos_nuevos > 0) else
                       ('el lote ya ejecutó %s paso(s): cambiar el procedimiento en marcha es una '
                        'desviación que decide Calidad, no un ajuste automático' % ejecutados)
                       if ejecutados else
                       ('el MBR aprobado no tiene pasos de fase %s · re-vincular dejaría el '
                        'legajo VACÍO' % _fase_ebr)),
        })
    return out


@bp.route("/api/brd/mbr-desactualizados", methods=["GET"])
def brd_mbr_desactualizados():
    """Vista previa: legajos abiertos colgados de una versión de MBR que ya no es la aprobada."""
    err = _require_login()
    if err:
        return err
    plan = _mbr_desactualizados(get_db())
    return jsonify({'ok': True, 'total': len(plan),
                    'movibles': sum(1 for x in plan if x['movible']), 'plan': plan})


@bp.route("/api/brd/revincular-mbr", methods=["POST"])
def brd_revincular_mbr():
    """Re-vincula legajos abiertos a la versión APROBADA de su MBR (trae el instructivo real).

    Body: {ebr_ids:[...] (opcional · default todos los movibles), aplicar:bool (default false)}.

    Reglas duras (GMP):
      · NUNCA toca un legajo liberado/rechazado/completado (mig 111: son inmutables).
      · NUNCA toca un legajo que ya ejecutó un paso — eso es una desviación de Calidad.
      · Reemplaza sólo pasos en estado `pendiente`, así que no puede borrar una firma.
      · Todo queda en audit_log, antes del commit.
    """
    err = _require_qa_or_admin()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    aplicar = bool(d.get('aplicar', False))
    pedidos = d.get('ebr_ids')
    usuario = session.get('compras_user', '')
    conn = get_db()
    cur = conn.cursor()
    plan = _mbr_desactualizados(conn)
    if pedidos:
        _ids = {int(x) for x in pedidos}
        plan = [p for p in plan if p['ebr_id'] in _ids]
    if not aplicar:
        return jsonify({'ok': True, 'dry_run': True, 'plan': plan,
                        'movibles': sum(1 for x in plan if x['movible'])})
    hechos, saltados = [], []
    for p in plan:
        if not p['movible']:
            saltados.append({'numero_op': p['numero_op'], 'motivo': p['motivo']})
            continue
        try:
            # CAS: reclamar el legajo con la condición de que SIGA en la versión vieja. Dos
            # clicks concurrentes (3 workers) pasarían ambos el chequeo de arriba y clonarían
            # los pasos dos veces (M27/M31).
            cur.execute(
                "UPDATE ebr_ejecuciones SET mbr_template_id=?, mbr_version=? "
                "WHERE id=? AND mbr_template_id=? "
                "AND LOWER(COALESCE(estado,'')) NOT IN ('liberado','rechazado','completado','cancelado')",
                (p['mbr_aprobado'], p['version_aprobada'], p['ebr_id'], p['mbr_actual']))
            if cur.rowcount != 1:
                saltados.append({'numero_op': p['numero_op'],
                                 'motivo': 'ya lo re-vinculó otro usuario o cambió de estado'})
                continue
            # Sólo los PENDIENTES: si hubiera un paso firmado, el guard de arriba ya excluyó el
            # legajo, y este WHERE es la segunda red — una firma no se puede borrar nunca.
            cur.execute("DELETE FROM ebr_pasos_ejecutados WHERE ebr_id=? "
                        "AND LOWER(COALESCE(estado,'pendiente'))='pendiente'", (p['ebr_id'],))
            borrados = cur.rowcount
            _fase = p['fase'] if p['fase'] in _FASES_VALIDAS else 'fabricacion'
            nuevos = 0
            for s in cur.execute(
                """SELECT id, orden, descripcion, tipo_paso, equipo_requerido,
                          requiere_e_sign, requiere_qc, COALESCE(fase,'') AS fase
                     FROM mbr_pasos WHERE mbr_template_id=? ORDER BY orden""",
                    (p['mbr_aprobado'],)).fetchall():
                if _fase_canonica(s[7]) != _fase:
                    continue
                cur.execute(
                    """INSERT INTO ebr_pasos_ejecutados
                         (ebr_id, mbr_paso_id, orden, descripcion, tipo_paso,
                          equipo_requerido, requiere_e_sign, requiere_qc, estado, fase)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)""",
                    (p['ebr_id'], s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7]))
                nuevos += 1
            audit_log(cur, usuario=usuario, accion='REVINCULAR_MBR_EBR',
                      tabla='ebr_ejecuciones', registro_id=str(p['ebr_id']),
                      antes={'mbr': p['mbr_actual'], 'version': p['version_actual'],
                             'estado_mbr': p['estado_mbr_actual'], 'pasos': borrados},
                      despues={'mbr': p['mbr_aprobado'], 'version': p['version_aprobada'],
                               'pasos': nuevos},
                      detalle='Trae el procedimiento aprobado al legajo abierto (ningún paso '
                              'estaba ejecutado)')
            hechos.append({'numero_op': p['numero_op'], 'producto': p['producto'],
                           'de_v': p['version_actual'], 'a_v': p['version_aprobada'],
                           'pasos_antes': borrados, 'pasos_ahora': nuevos})
        except Exception as e:
            conn.rollback()
            log.warning('revincular MBR ebr=%s falló: %s', p['ebr_id'], e)
            saltados.append({'numero_op': p['numero_op'], 'motivo': str(e)[:180]})
    conn.commit()
    return jsonify({'ok': True, 'dry_run': False, 'revinculados': hechos,
                    'saltados': saltados, 'restante': _mbr_desactualizados(conn)})


@bp.route("/api/brd/revincular-mbr/revertir", methods=["POST"])
def brd_revincular_mbr_revertir():
    """Deshace una re-vinculación usando el rastro que ella misma dejó.

    Toda acción que reemplaza pasos de un legajo necesita vuelta atrás: el 26-jul la
    re-vinculación dejó en CERO pasos un legajo de ENVASADO (el MBR nuevo sólo tenía los de
    fabricación) y hubo que devolverlo a mano. Ahora se revierte con un click, leyendo el
    `antes` de `audit_log` — que es exactamente para lo que se guarda.

    Body: {ebr_ids:[...], aplicar:bool}. Mismas líneas rojas: nada de tocar un legajo liberado
    ni uno con pasos ya ejecutados.
    """
    err = _require_qa_or_admin()
    if err:
        return err
    d = request.get_json(silent=True) or {}
    aplicar = bool(d.get('aplicar', False))
    ids = [int(x) for x in (d.get('ebr_ids') or [])]
    if not ids:
        return jsonify({'error': 'faltan ebr_ids'}), 400
    usuario = session.get('compras_user', '')
    conn = get_db()
    cur = conn.cursor()
    plan, hechos, saltados = [], [], []
    for ebr_id in ids:
        fila = conn.execute(
            "SELECT antes, despues FROM audit_log WHERE accion='REVINCULAR_MBR_EBR' "
            "AND registro_id=? ORDER BY id DESC LIMIT 1", (str(ebr_id),)).fetchone()
        if not fila:
            saltados.append({'ebr_id': ebr_id, 'motivo': 'no tiene una re-vinculación que revertir'})
            continue
        try:
            antes = _json.loads(fila[0]) if fila[0] else {}
        except Exception:
            antes = {}
        mbr_prev, ver_prev = antes.get('mbr'), antes.get('version')
        if not mbr_prev:
            saltados.append({'ebr_id': ebr_id, 'motivo': 'el rastro no guardó el MBR anterior'})
            continue
        e = conn.execute(
            "SELECT numero_op, COALESCE(fase,'fabricacion'), estado, mbr_template_id "
            "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        if not e:
            saltados.append({'ebr_id': ebr_id, 'motivo': 'el legajo no existe'})
            continue
        if str(e[2] or '').lower() in ('liberado', 'rechazado', 'completado', 'cancelado'):
            saltados.append({'ebr_id': ebr_id, 'motivo': 'legajo %s: es inmutable' % e[2]})
            continue
        ejec = conn.execute(
            "SELECT COUNT(*) FROM ebr_pasos_ejecutados WHERE ebr_id=? "
            "AND LOWER(COALESCE(estado,'pendiente'))<>'pendiente'", (ebr_id,)).fetchone()[0]
        if ejec:
            saltados.append({'ebr_id': ebr_id, 'motivo': 'ya ejecutó %s paso(s)' % ejec})
            continue
        plan.append({'ebr_id': ebr_id, 'numero_op': e[0], 'fase': e[1],
                     'mbr_actual': e[3], 'volver_a_mbr': mbr_prev, 'volver_a_version': ver_prev})
        if not aplicar:
            continue
        _fase = e[1] if e[1] in _FASES_VALIDAS else 'fabricacion'
        cur.execute("UPDATE ebr_ejecuciones SET mbr_template_id=?, mbr_version=? WHERE id=?",
                    (mbr_prev, ver_prev, ebr_id))
        cur.execute("DELETE FROM ebr_pasos_ejecutados WHERE ebr_id=? "
                    "AND LOWER(COALESCE(estado,'pendiente'))='pendiente'", (ebr_id,))
        n = 0
        for s in cur.execute(
            """SELECT id, orden, descripcion, tipo_paso, equipo_requerido,
                      requiere_e_sign, requiere_qc, COALESCE(fase,'') AS fase
                 FROM mbr_pasos WHERE mbr_template_id=? ORDER BY orden""", (mbr_prev,)).fetchall():
            if _fase_canonica(s[7]) != _fase:
                continue
            cur.execute(
                """INSERT INTO ebr_pasos_ejecutados
                     (ebr_id, mbr_paso_id, orden, descripcion, tipo_paso,
                      equipo_requerido, requiere_e_sign, requiere_qc, estado, fase)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?)""",
                (ebr_id, s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7]))
            n += 1
        audit_log(cur, usuario=usuario, accion='REVERTIR_REVINCULAR_MBR',
                  tabla='ebr_ejecuciones', registro_id=str(ebr_id),
                  antes={'mbr': e[3]}, despues={'mbr': mbr_prev, 'version': ver_prev, 'pasos': n},
                  detalle='Deshace la re-vinculación anterior desde el rastro de audit_log')
        hechos.append({'ebr_id': ebr_id, 'numero_op': e[0], 'mbr': mbr_prev, 'pasos': n})
    if aplicar:
        conn.commit()
    return jsonify({'ok': True, 'dry_run': not aplicar, 'plan': plan,
                    'revertidos': hechos, 'saltados': saltados})


def _ebr_audit_rows(conn, ebr_id):
    """Audit trail del lote (Part 11 §11.10(e)): quién hizo qué y cuándo.

    A nivel orden (`registro_id=ebr_id`) y por hijo (pesaje/paso/IPC/despeje, que llevan el
    ebr_id dentro del JSON `despues`). UN solo productor para las dos vistas del legajo — el
    embebido en Planta y `/vista-completa` — porque tener la query duplicada es justo cómo una
    de las dos se queda vieja (M1/M87).
    """
    return conn.execute(
        """SELECT fecha, usuario, accion, COALESCE(detalle,''),
                  COALESCE(antes,''), COALESCE(despues,''), COALESCE(tabla,'')
           FROM audit_log
           WHERE (tabla='ebr_ejecuciones' AND registro_id = ?)
              OR (tabla IN ('ebr_pesajes','ebr_pasos_ejecutados','ipc_resultados',
                            'ipc_estandar_resultados','ebr_despeje_items','ebr_despeje_linea')
                  AND (despues LIKE ? OR despues LIKE ?))
           ORDER BY fecha DESC LIMIT 200""",
        (str(ebr_id), '%"ebr_id": ' + str(ebr_id) + ',%',
         '%"ebr_id": ' + str(ebr_id) + '}%'),
    ).fetchall()


@bp.route("/api/brd/ebr/<int:ebr_id>/audit", methods=["GET"])
def ebr_audit(ebr_id):
    """Trazabilidad de responsables del lote · sección INVIMA del legajo.

    FIX 25-jul (Sebastián, revisando el batch digital): la sección 11 del legajo decía
    "Sin acciones registradas todavía" en TODOS los lotes — incluso en uno con 13/13
    verificaciones firmadas y 47 acciones en el audit trail. Causa: el legajo embebido en
    Planta se arma con `/api/brd/ebr/<id>` + 11 sub-recursos, y el `audit` sólo existía en
    `/vista-completa`, que ese camino NUNCA llama → `d.audit` siempre undefined → el `else`
    del render pintaba el texto de vacío. Los datos estaban; la pantalla no los pedía.
    (Misma familia que M94: el consumidor lee una clave que su productor no entrega, y el
    resultado es indistinguible de "no hay nada".)
    """
    conn = get_db()
    try:
        rows = _ebr_audit_rows(conn, ebr_id)
    except Exception as e:
        log.warning('ebr_audit %s falló: %s', ebr_id, e)
        return jsonify({'items': [], 'error': str(e)[:200]}), 200
    # `_persona` (nombre completo) es un helper LOCAL de `ebr_vista_completa`, no del módulo:
    # usarlo acá daba NameError → 500. El legajo muestra el username, que es la firma real.
    return jsonify({'items': [{
        'fecha': r[0], 'usuario': r[1], 'accion': r[2], 'detalle': r[3],
    } for r in rows]})


@bp.route("/api/brd/ebr/<int:ebr_id>/vista-completa", methods=["GET"])
def ebr_vista_completa(ebr_id):
    """MyBatch parity Sprint B · 21-may-2026 · Sebastián.

    Vista BR de 8 secciones unificada · 1 request en lugar de N round-trips
    (la pantalla que MyBatch tiene como núcleo del día a día):
    1. Header (lote, producto, fecha, operario, estado)
    2. Pesajes MP (con firmas si hay)
    3. Pasos del proceso (con timestamps real vs estimado)
    4. IPC resultados (in-process checks)
    5. Despejes de línea firmados (BPM)
    6. Observaciones acumuladas
    7. Estado cuarentena/liberación (post-completar)
    8. Audit log filtrado por ebr_id
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    out = {'ebr_id': ebr_id}
    # 1. Header · INVIMA-FIX 21-may-2026 · usar columnas originales + COALESCE
    # con aliases (mig 153) para que funcione antes y después de la migración.
    try:
        row = conn.execute(
            """SELECT id, mbr_template_id, produccion_id,
                      COALESCE(lote_codigo, lote) AS lote_codigo,
                      estado,
                      iniciado_at_utc, completado_at_utc,
                      COALESCE(operario, iniciado_por) AS operario,
                      COALESCE(tiempo_total_min,
                               CASE WHEN completado_at_utc IS NOT NULL
                                    THEN (julianday(completado_at_utc) - julianday(iniciado_at_utc)) * 24 * 60
                                    ELSE 0 END) AS tiempo_total_min,
                      COALESCE(observaciones, notas) AS observaciones,
                      liberado_at_utc, liberado_por,
                      COALESCE(rechazado_at_utc, '') AS rechazado_at_utc,
                      rechazado_motivo,
                      COALESCE(numero_op,'') AS numero_op,
                      COALESCE(fase,'fabricacion') AS fase,
                      COALESCE(area_codigo,'') AS area_codigo,
                      COALESCE(cantidad_objetivo_g,0) AS cantidad_objetivo_g,
                      cantidad_real_g, yield_pct,
                      COALESCE(densidad_g_ml,0) AS densidad_g_ml,
                      COALESCE(ml_envasable,0) AS ml_envasable
               FROM ebr_ejecuciones WHERE id=?""",
            (ebr_id,),
        ).fetchone()
        if not row:
            return jsonify({'error': 'EBR no existe'}), 404
        out['header'] = {
            'id': row[0], 'mbr_template_id': row[1],
            'produccion_id': row[2], 'lote_codigo': row[3] or '',
            'estado': row[4] or '', 'iniciado_at_utc': row[5] or '',
            'completado_at_utc': row[6] or '', 'operario': row[7] or '',
            'tiempo_total_min': row[8] or 0, 'observaciones': row[9] or '',
            'liberado_at_utc': row[10] or '', 'liberado_por': row[11] or '',
            'rechazado_at_utc': row[12] or '', 'rechazado_motivo': row[13] or '',
            'numero_op': row[14] or '', 'fase': row[15] or 'fabricacion',
            'area_codigo': row[16] or '',
            'cantidad_objetivo_g': float(row[17] or 0),
            'cantidad_real_g': (float(row[18]) if row[18] is not None else None),
            'yield_pct': (float(row[19]) if row[19] is not None else None),
            'densidad_g_ml': (float(row[20]) if row[20] else None),
            'ml_envasable': (float(row[21]) if row[21] else None),
        }
        # Columnas de las migs 392/393 en su PROPIO SELECT: si una instancia todavía no
        # migró, se pierde el bloque nuevo y NO el legajo entero (que es el documento
        # regulado). El except loguea, nunca calla (M94).
        try:
            _rr = conn.execute(
                "SELECT remanente_g, COALESCE(remanente_destino,''), COALESCE(remanente_observaciones,''), "
                "COALESCE(remanente_por,''), COALESCE(remanente_at_utc,''), "
                "COALESCE(aprobada_orden_por,''), COALESCE(aprobada_orden_at_utc,''), "
                "COALESCE(aprobada_orden_rol,'') FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
            if _rr:
                out['header'].update({
                    'remanente_g': (float(_rr[0]) if _rr[0] is not None else None),
                    'remanente_destino': _rr[1], 'remanente_observaciones': _rr[2],
                    'remanente_por': _rr[3], 'remanente_at_utc': _rr[4],
                    'aprobada_orden_por': _rr[5], 'aprobada_orden_at_utc': _rr[6],
                    'aprobada_orden_rol': _rr[7],
                })
        except Exception as _e:
            log.warning("columnas mig 392/393 no disponibles en ebr=%s: %s", ebr_id, _e)
        # Orden madre (mig 395) · None para los legajos anteriores, que siguen igual.
        out['orden'] = _orden_de_ebr(conn, ebr_id)
        # Objetivo EN VIVO (M67 punto 4): mientras el EBR NO esté liberado/completado/rechazado,
        # la magnitud del lote la manda la fuente de verdad produccion_programada.cantidad_kg · no
        # el cantidad_objetivo_g congelado (que pudo nacer con el default del MBR o quedar stale si
        # se corrigió la cantidad). Así la hoja de pesaje teórica y el rendimiento salen correctos.
        # Una vez liberado/completado, se respeta el valor congelado (batch comprometido, inmutable).
        try:
            _pid_h = out['header'].get('produccion_id')
            _est_h = (out['header'].get('estado') or '').lower()
            if (_pid_h and not out['header'].get('liberado_at_utc')
                    and _est_h not in ('liberado', 'rechazado', 'completado')
                    and out['header'].get('fase', 'fabricacion') == 'fabricacion'):
                _ckv = conn.execute(
                    "SELECT COALESCE(cantidad_kg,0) FROM produccion_programada WHERE id=?",
                    (_pid_h,)).fetchone()
                if _ckv and _ckv[0]:
                    out['header']['cantidad_objetivo_g'] = round(float(_ckv[0]) * 1000, 1)
        except Exception:
            pass
        # Área o Línea: resolver el nombre legible desde areas_planta.
        try:
            _ac = out['header'].get('area_codigo') or ''
            if _ac:
                _ar = conn.execute(
                    "SELECT id, nombre FROM areas_planta WHERE codigo=?", (_ac,)).fetchone()
                out['header']['area_linea'] = (
                    (str(_ar[1]) + ' (' + _ac + ')') if _ar and _ar[1] else _ac)
                # area_id para enlazar el rótulo de limpieza F02 del área.
                out['header']['area_id'] = (_ar[0] if _ar else None)
        except Exception:
            pass
    except Exception as e:
        return jsonify({'error': f'header fallo: {e}'}), 500
    # Producto del MBR
    try:
        mbr = conn.execute(
            "SELECT producto_nombre, version, titulo, lote_size_g FROM mbr_templates WHERE id=?",
            (out['header']['mbr_template_id'],),
        ).fetchone()
        if mbr:
            out['header']['producto'] = mbr[0]
            out['header']['mbr_version'] = mbr[1]
            out['header']['titulo'] = mbr[2]
            out['header']['lote_size_g'] = float(mbr[3] or 0)
    except Exception:
        pass
    # Fase a top-level (el front ramifica por d.fase) + presentaciones de envasado.
    # Para un legajo de ENVASADO, el cuerpo es "Lotes de Producto por Presentación"
    # (envase × unidades × área), leído de la tabla `envasado` por el lote físico.
    out['fase'] = out['header'].get('fase', 'fabricacion')
    # Rol del usuario + permisos (segregación de funciones GMP · la UI se adapta · 9-jun).
    # El backend YA bloquea (403); esto es para que la UI muestre el rol y oculte lo que no le
    # toca.
    #
    # ⚠ 16-ago · esto era un SEGUNDO mapa de roles escrito a mano, y divergía del canónico
    # `_batch_role_info` de dos formas que nadie veía:
    #   · no conocía a ASEGURAMIENTO, así que a Miguel -que SÍ pasa el gate real- la pantalla
    #     le escondía lo que tiene permitido hacer (M121 al revés: la capacidad existe y la
    #     vista la tapa);
    #   · y sobre todo emitía `puede_verificar` mientras la pantalla de envasado lee
    #     `d.mi_rol.verifica` (línea ~11364) -- una llave que este dict NUNCA tuvo, así que
    #     `PUEDE_VERIF` daba false para TODO el mundo y el botón de verificar el material de
    #     envase no aparecía nunca, sin un solo error a la vista (M94).
    #
    # Ahora sale del resolvedor único (M1/M3) y se le agrega el alias `puede_corregir` que este
    # camino ya publicaba, para no romper a quien lo lea.
    out['mi_rol'] = _batch_role_info(session.get("compras_user", ""))
    out['mi_rol']['puede_corregir'] = out['mi_rol'].get('corrige', False)
    # El visto bueno del Director Técnico (mig 286) · esta vista alimenta las pantallas PROPIAS
    # del legajo, y la de ACONDICIONAMIENTO es la del producto terminado, o sea exactamente
    # donde el DT firma (`PRD-PRO-001-F01` · acta del 27-jul). El dato no viajaba, así que en
    # esa pantalla no había por dónde darlo: la firma existía y era inalcanzable (M121).
    try:
        _dt = conn.execute(
            "SELECT COALESCE(aprobado_dt_por,''), COALESCE(aprobado_dt_at_utc,'') "
            "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        out['aprobado_dt_por'] = (_dt[0] if _dt else '')
        out['aprobado_dt_at'] = (_dt[1] if _dt else '')
    except Exception as _e:
        # se declara el fallo en vez de mandar '' -- un vacío mudo se lee como "nadie firmó",
        # que es lo contrario de "no se pudo leer" (M100/M154)
        log.warning("visto bueno del DT no legible para ebr=%s: %s", ebr_id, _e)
        out['aprobado_dt_por'] = ''
        out['aprobado_dt_at'] = ''
        out['aprobado_dt_error'] = True
    if out['fase'] == 'envasado':
        out['envasado_presentaciones'] = []
        try:
            _lote = (out['header'].get('lote_codigo') or '').strip()
            if _lote:
                _rows = conn.execute(
                    """SELECT COALESCE(e.presentacion,'') AS presentacion,
                              COALESCE(e.lote,'') AS lote, COALESCE(e.unidades,0) AS unidades,
                              COALESCE(ap.nombre, e.area_codigo, '') AS area,
                              COALESCE(e.estado,'') AS estado, COALESCE(e.envase_codigo,'') AS envase
                         FROM envasado e
                         LEFT JOIN areas_planta ap ON ap.codigo = e.area_codigo
                        WHERE UPPER(TRIM(e.lote))=UPPER(TRIM(?))
                        ORDER BY e.id ASC""",
                    (_lote,),
                ).fetchall()
                for r in _rows:
                    rd = dict(r)
                    out['envasado_presentaciones'].append({
                        'presentacion': rd.get('presentacion') or rd.get('envase') or '·',
                        'lote': rd.get('lote') or _lote,
                        'unidades': int(rd.get('unidades') or 0),
                        'area': rd.get('area') or '',
                        'cantidad_ml': None, 'unidades_final': None, 'rend_pct': None,
                        'estado': rd.get('estado') or 'En proceso',
                    })
        except Exception as _ep:
            __import__('logging').getLogger('brd').warning('envasado_presentaciones fallo: %s', _ep)
        # Auto-carga (MyBatch · 10-jun): si aún no hay envasado real registrado, mostrar
        # las presentaciones PLANEADAS desde la programación (Animus + B2B · 'Programado').
        if not out['envasado_presentaciones']:
            try:
                out['envasado_presentaciones'] = _presentaciones_planeadas(
                    conn, out['header'].get('producto'), out['header'].get('produccion_id'))
            except Exception as _epp:
                __import__('logging').getLogger('brd').warning('presentaciones planeadas OF fallo: %s', _epp)
        # + presentaciones agregadas/editadas A MANO (se suman a lo auto-cargado · editables).
        try:
            out['envasado_presentaciones'] = (out['envasado_presentaciones'] or []) + _presentaciones_manuales(conn, ebr_id)
        except Exception:
            pass
        # Materiales de Envase (envase + tapa usados) · conciliación de empaque (MyBatch):
        # cant. requerida vs devuelta/utilizada/averiada/diferencia. Iteración 2 · requerida.
        out['envasado_materiales'] = []
        try:
            _lote2 = (out['header'].get('lote_codigo') or '').strip()
            if _lote2:
                _erows = conn.execute(
                    "SELECT COALESCE(envase_codigo,''), COALESCE(tapa_codigo,''), "
                    "COALESCE(unidades,0) FROM envasado "
                    "WHERE UPPER(TRIM(lote))=UPPER(TRIM(?))", (_lote2,)).fetchall()
                _acc = {}
                for er in _erows:
                    _env = (er[0] or '').strip(); _tapa = (er[1] or '').strip()
                    _uds = int(er[2] or 0)
                    if _env:
                        _acc[_env] = _acc.get(_env, 0) + _uds
                    if _tapa:
                        _acc[_tapa] = _acc.get(_tapa, 0) + _uds
                for _cod, _req in _acc.items():
                    _nom = ''
                    try:
                        _n = conn.execute(
                            "SELECT nombre_comercial FROM maestro_mps WHERE codigo_mp=?",
                            (_cod,)).fetchone()
                        _nom = (_n[0] if _n else '') or ''
                    except Exception:
                        pass
                    out['envasado_materiales'].append({
                        'lote_envasado': _lote2,
                        'material': (_cod + (' ' + _nom if _nom else '')),
                        'lote_material': '', 'requerida': _req,
                        'devuelta': None, 'utilizada': None, 'averiada': None, 'diferencia': None,
                    })
        except Exception as _em:
            __import__('logging').getLogger('brd').warning('envasado_materiales fallo: %s', _em)
        # Auto-carga (MyBatch · 11-jun): si aún no hay envasado real, mostrar el material
        # de envase PLANEADO del producto (envase + tapa/gotero/etiqueta · cant requerida).
        if not out['envasado_materiales']:
            try:
                out['envasado_materiales'] = _materiales_envase_planeados(
                    conn, out['header'].get('producto'),
                    out['header'].get('produccion_id'), out['header'].get('lote_codigo') or '')
            except Exception as _emp:
                __import__('logging').getLogger('brd').warning('materiales envase planeados OF fallo: %s', _emp)
        # + materiales agregados/editados A MANO (se suman a lo auto-cargado · editables).
        try:
            out['envasado_materiales'] = (out['envasado_materiales'] or []) + _materiales_envase_manuales(conn, ebr_id)
        except Exception as _emm:
            # Antes era `except: pass` y por eso un error en la consulta hacía DESAPARECER
            # las filas de material de la pantalla sin dejar rastro: indistinguible de "no
            # hay material cargado" (M4/M94).
            log.warning('materiales de envase manuales no se pudieron sumar (ebr=%s): %s', ebr_id, _emm)
    # Acondicionamiento (OA · 10-jun) · el cuerpo del legajo es "Unidades por
    # Presentación" (lo acondicionado del lote) + "Materiales de Empaque" (etiquetas,
    # plegadizas, insertos · leídos del mee_consumido). Espeja la rama de envasado.
    if out['fase'] == 'acondicionamiento':
        out['acond_presentaciones'] = []
        out['acond_materiales'] = []
        try:
            _loa = (out['header'].get('lote_codigo') or '').strip()
            if _loa:
                _arows = conn.execute(
                    """SELECT COALESCE(presentacion,'') AS presentacion,
                              COALESCE(lote,'') AS lote,
                              COALESCE(unidades_producidas,0) AS unidades,
                              COALESCE(estado,'') AS estado,
                              COALESCE(mee_consumido,'[]') AS mee_consumido,
                              COALESCE(sku,'') AS sku
                         FROM acondicionamiento
                        WHERE UPPER(TRIM(lote))=UPPER(TRIM(?))
                        ORDER BY id ASC""",
                    (_loa,),
                ).fetchall()
                _acc_oa = {}  # codigo -> unidades acumuladas (material de empaque)
                for r in _arows:
                    rd = dict(r)
                    out['acond_presentaciones'].append({
                        'presentacion': rd.get('presentacion') or rd.get('sku') or '·',
                        'lote': rd.get('lote') or _loa,
                        'unidades': int(rd.get('unidades') or 0),
                        'estado': rd.get('estado') or 'En proceso',
                    })
                    try:
                        # ⚠ 17-ago · acá decía `json.loads` y el módulo importa `json as _json`,
                        # así que lanzaba NameError SIEMPRE. El `except` de abajo lo convertía en
                        # lista vacía, o sea que la sección **Material de Empaque del legajo de
                        # acondicionamiento nunca mostró nada, para ningún lote** -- y nadie lo
                        # notó porque la fase no se había caminado todavía (M94/M4: un except
                        # mudo convierte un bug en "no hay datos", que es indistinguible de la
                        # realidad). Las otras tres llamadas del archivo sí usan `_json`.
                        _mlist = _json.loads(rd.get('mee_consumido') or '[]')
                    except Exception as _emee:
                        __import__('logging').getLogger('brd').warning(
                            'acond material de empaque ilegible en el lote %s: %s', _loa, _emee)
                        _mlist = []
                    for _m in (_mlist or []):
                        _c = str(_m.get('codigo', _m.get('codigo_mee', '')) or '').strip()
                        _q = float(_m.get('cantidad', 0) or 0)
                        if _c:
                            _acc_oa[_c] = _acc_oa.get(_c, 0) + _q
                for _cod, _req in _acc_oa.items():
                    _nom = ''
                    try:
                        _n = conn.execute(
                            "SELECT descripcion FROM maestro_mee WHERE codigo=?",
                            (_cod,)).fetchone()
                        _nom = (_n[0] if _n else '') or ''
                    except Exception:
                        pass
                    out['acond_materiales'].append({
                        'lote_acond': _loa,
                        'material': (_cod + (' ' + _nom if _nom else '')),
                        'lote_material': '', 'requerida': _req,
                        'devuelta': None, 'utilizada': None, 'averiada': None, 'diferencia': None,
                    })
        except Exception as _ea:
            __import__('logging').getLogger('brd').warning('acond_presentaciones fallo: %s', _ea)
        # Auto-carga (MyBatch · 10-jun): si aún no hay acondicionamiento real, mostrar
        # las presentaciones PLANEADAS desde la programación (Animus + B2B · 'Programado').
        if not out['acond_presentaciones']:
            try:
                out['acond_presentaciones'] = _presentaciones_planeadas(
                    conn, out['header'].get('producto'), out['header'].get('produccion_id'))
            except Exception as _epp:
                __import__('logging').getLogger('brd').warning('presentaciones planeadas OA fallo: %s', _epp)
        # + presentaciones agregadas/editadas A MANO (se suman a lo auto-cargado · editables).
        try:
            out['acond_presentaciones'] = (out['acond_presentaciones'] or []) + _presentaciones_manuales(conn, ebr_id)
        except Exception:
            pass
        # Auto-carga del material de empaque planeado si aún no hay acond real.
        if not out['acond_materiales']:
            try:
                out['acond_materiales'] = _materiales_envase_planeados(
                    conn, out['header'].get('producto'),
                    out['header'].get('produccion_id'), out['header'].get('lote_codigo') or '',
                    excluir_envasado=True)
            except Exception as _emp:
                __import__('logging').getLogger('brd').warning('materiales envase planeados OA fallo: %s', _emp)
        # + materiales agregados/editados A MANO (se suman a lo auto-cargado · editables).
        try:
            out['acond_materiales'] = (out['acond_materiales'] or []) + _materiales_envase_manuales(conn, ebr_id)
        except Exception:
            pass
    # Elaborado por (enriquecido) + Supervisado por · Sebastián 5-jun-2026:
    # "el área productiva la supervisa el Jefe de Producción; calidad el Jefe de
    # Control de Calidad". Resolvemos nombre+cargo desde usuarios_identidad
    # (fallback operarios.es_jefe_produccion). Solo lectura.
    try:
        op = out['header'].get('operario', '')
        if op:
            ir = conn.execute(
                "SELECT COALESCE(nombre_completo,''), COALESCE(cargo,'') "
                "FROM usuarios_identidad WHERE username=? AND COALESCE(activo,1)=1",
                (op,)).fetchone()
            if ir:
                # El nombre sale del resolvedor único: `usuarios_identidad` lo tiene vacío
                # para todos, y las personas están en `empleados` / `operarios_planta`.
                try:
                    from blueprints.identidad import nombre_de as _nombre_de
                    _nom_op = _nombre_de(conn, op)
                except Exception:
                    _nom_op = ''
                _partes = [p for p in (_nom_op or ir[0], ir[1])
                           if p and p != 'Por definir']
                if _partes:
                    out['header']['operario'] = ', '.join(_partes) + f' ({op})'
        # Supervisado por = Jefe de Producción (fases productivas).
        sup = ''
        # FIX 26-jul · `LIMIT 1` sin `ORDER BY` devuelve una fila ARBITRARIA (y en PostgreSQL,
        # distinta entre corridas). Si hay más de un registro con cargo de jefe de producción y
        # el que sale primero no tiene `nombre_completo`, el batch record imprime "Supervisado
        # por: Jefe de Producción" — el CARGO sin la PERSONA, que en un documento regulado no
        # sirve como firma. Se prefiere explícitamente el que TIENE nombre y se desempata por
        # username para que sea determinista.
        jp = conn.execute(
            "SELECT COALESCE(nombre_completo,''), COALESCE(cargo,'') FROM usuarios_identidad "
            "WHERE LOWER(cargo) LIKE '%jefe%produc%' AND COALESCE(activo,1)=1 "
            "ORDER BY CASE WHEN COALESCE(nombre_completo,'')<>'' THEN 0 ELSE 1 END, username "
            "LIMIT 1").fetchone()
        # Sebastián 16-ago: *"tú tienes el nombre de cada jefe, ellos se loguean"*. El nombre
        # se resuelve con el resolvedor único (`identidad.nombre_de`), que además busca en
        # `empleados` y `operarios_planta` -- ahí están los nombres reales, y `usuarios_identidad`
        # los tiene vacíos. Se cruza por PERSONA (el username del jefe), nunca por cargo:
        # buscar "el jefe de producción" devuelve a Luis Enrique, dado de baja (mig 375), y un
        # legajo firmado por quien ya no trabaja acá es peor que uno sin nombre.
        # ⚠ Si hay más de un jefe de producción activo, gana EL QUE TIENE NOMBRE: ordenar por
        # username a secas devuelve al primero alfabético, que puede ser justo el que no lo
        # tiene cargado -- y ahí el legajo vuelve a imprimir el cargo pelado (es el fix del
        # 26-jul, que se perdió al reescribir esto y lo cazó su propio test · M97).
        jefes = conn.execute(
            "SELECT username, COALESCE(cargo,'') FROM usuarios_identidad "
            "WHERE LOWER(cargo) LIKE '%jefe%produc%' AND COALESCE(activo,1)=1 "
            "ORDER BY username").fetchall()
        jpu = None
        _nom = ''
        if jefes:
            try:
                from blueprints.identidad import nombre_de as _nombre_de
            except Exception:
                _nombre_de = lambda _c, _u: ''
            for _j in jefes:
                _n = _nombre_de(conn, _j[0])
                if _n:
                    jpu, _nom = _j, _n
                    break
            if jpu is None:
                jpu = jefes[0]
        if jpu:
            _u, _cargo = jpu[0], (jpu[1] or 'Jefe de Producción')
            # Sin nombre cargado se DICE: poner el cargo solo se lee como si eso fuera la
            # firma, y en un registro regulado la pregunta es quién supervisó (M100/M124).
            sup = ('%s, %s' % (_nom, _cargo)) if _nom else ('%s · falta cargar el nombre '
                                                            'de %s' % (_cargo, _u))
        elif jp and (jp[0] or jp[1]):
            sup = ((jp[0] + ', ') if jp[0] else '') + (jp[1] or 'Jefe de Producción')
        out['header']['supervisado_por'] = sup
    except Exception:
        pass
    # Aprobado por (Calidad) enriquecido · MyBatch parity (Sebastián 5-jun-2026):
    # "calidad la libera el Jefe de Control de Calidad". liberado_por es el username
    # firmante → resolvemos Nombre, Cargo (username) + fecha de liberación.
    try:
        lp = (out['header'].get('liberado_por') or '').strip()
        if lp:
            qr = conn.execute(
                "SELECT COALESCE(nombre_completo,''), COALESCE(cargo,'') "
                "FROM usuarios_identidad WHERE username=? AND COALESCE(activo,1)=1",
                (lp,)).fetchone()
            full = lp
            if qr:
                _pq = [p for p in (qr[0], qr[1]) if p and p != 'Por definir']
                if _pq:
                    full = ', '.join(_pq) + f' ({lp})'
            _la = (out['header'].get('liberado_at_utc') or '')
            if _la:
                full += ' · ' + _la[:16].replace('T', ' ')
            out['header']['liberado_por_full'] = full
    except Exception:
        pass
    # Cantidad Disponible (mL) · MyBatch parity: granel producido menos el granel
    # ya envasado/acondicionado del MISMO lote (OF/OA). Sin envasado registrado =>
    # disponible = producido. Cálculo honesto sobre la propia data EOS (no inventado).
    try:
        prod_ml = out['header'].get('ml_envasable')
        lote_b = (out['header'].get('lote_codigo') or '').strip()
        if prod_ml is not None and lote_b:
            cons = conn.execute(
                "SELECT COALESCE(SUM(COALESCE(ml_envasable,0)),0) FROM ebr_ejecuciones "
                "WHERE lote_codigo=? AND id<>? AND COALESCE(fase,'') IN ('envasado','acondicionamiento')",
                (lote_b, ebr_id)).fetchone()
            consumido = float(cons[0] or 0) if cons else 0.0
            out['header']['cantidad_disponible_ml'] = max(0.0, round(float(prod_ml) - consumido, 2))
    except Exception:
        pass
    # Conciliación del granel (mig 392) · sólo envasado. Es DERIVADA salvo el remanente,
    # así que se calcula acá y no se guarda (M71). El except loguea: un except mudo
    # convierte un bug en "no hay datos", que es indistinguible de la realidad (M94).
    try:
        out['conciliacion_granel'] = _conciliacion_granel(conn, ebr_id, out['header'])
    except Exception as _e:
        log.warning("conciliacion_granel ebr=%s no disponible: %s", ebr_id, _e)
        out['conciliacion_granel'] = None
    # 2. Pesajes MP
    # Resolver username → "Nombre, Cargo (user)" para Realizado/Verificado por
    # (MyBatch "Detalle del Pesaje"). Cache por request · solo lectura.
    _persona_cache = {}

    def _persona(u):
        u = (u or '').strip()
        if not u:
            return ''
        if u in _persona_cache:
            return _persona_cache[u]
        txt = u
        try:
            ir = conn.execute(
                "SELECT COALESCE(nombre_completo,''), COALESCE(cargo,'') "
                "FROM usuarios_identidad WHERE username=? AND COALESCE(activo,1)=1", (u,)).fetchone()
            if ir:
                partes = [p for p in (ir[0], ir[1]) if p and p != 'Por definir']
                if partes:
                    txt = ', '.join(partes) + ' (' + u + ')'
        except Exception:
            pass
        _persona_cache[u] = txt
        return txt
    try:
        rows = conn.execute(
            """SELECT p.material_id, COALESCE(p.material_nombre,''),
                      p.cantidad_teorica_g, p.cantidad_real_g, COALESCE(p.lote_mp,''),
                      COALESCE(p.pesado_por,''), COALESCE(p.pesado_at_utc,''),
                      COALESCE(p.notas,''), p.id,
                      COALESCE(p.verificado_por,''), COALESCE(p.verificado_at_utc,''),
                      COALESCE(mm.nombre_inci,'')
               FROM ebr_pesajes p LEFT JOIN maestro_mps mm ON mm.codigo_mp=p.material_id
               WHERE p.ebr_id=? ORDER BY p.id""",
            (ebr_id,),
        ).fetchall()
        out['pesajes'] = [{
            'material_id': r[0], 'material_nombre': r[1], 'nombre_inci': r[11],
            'esperada_g': float(r[2] or 0), 'real_g': float(r[3] or 0),
            'lote_mp': r[4], 'operario': r[5], 'fecha': r[6],
            'observaciones': r[7], 'pesaje_id': r[8],
            'verificado_por': r[9], 'verificado_at': r[10],
            'realizado_por_full': _persona(r[5]),
            'verificado_por_full': _persona(r[9]),
            'delta_pct': round(((r[3] - r[2]) / r[2] * 100) if r[2] else 0, 2),
        } for r in rows]
    except Exception:
        out['pesajes'] = []
    # 2b. HOJA DE PESAJE (MyBatch parity · Sebastián 5-jun): TODAS las MP de la
    # fórmula con cant a pesar (teórico), lote FEFO (resuelto + producible) y la
    # cant pesada/operario si ya se registró. Es la "Pesaje de Materias Primas".
    try:
        prod_nom = out['header'].get('producto') or ''
        obj_g = float(out['header'].get('cantidad_objetivo_g') or 0)
        recorded = {}
        for p in out.get('pesajes', []):
            recorded.setdefault(p['material_id'], p)
        try:
            from blueprints.inventario import _fefo_lote_rotulo as _fefo
        except Exception:
            _fefo = None
        # Presupuesto de tiempo · el resolver FEFO escanea maestro_mps por cada MP
        # (en prod son miles de filas) → sin tope, una fórmula grande cuelga la
        # página. Tras ~2.5s dejamos de resolver lotes (se muestra '·'); el resto
        # de la hoja (%, cant a pesar, pesados) sale igual y el descuento real en
        # producción sigue usando el resolver completo. Sebastián 5-jun-2026.
        import time as _time
        _fefo_deadline = _time.monotonic() + 2.5
        _fefo_cache = {}
        sheet = []
        if prod_nom:
            fitems = conn.execute(
                "SELECT fi.material_id, COALESCE(fi.material_nombre,''), COALESCE(fi.porcentaje,0), "
                "COALESCE(mm.nombre_inci,'') "
                "FROM formula_items fi LEFT JOIN maestro_mps mm ON mm.codigo_mp=fi.material_id "
                "WHERE fi.producto_nombre=? ORDER BY fi.porcentaje DESC", (prod_nom,)).fetchall()
            for fr in fitems:
                mid = str(fr[0] or '').strip()
                if not mid:
                    continue
                pct = float(fr[2] or 0)
                cant_a_pesar = round(pct / 100.0 * obj_g, 2) if obj_g else None
                rec = recorded.get(mid)
                lote = (rec['lote_mp'] if rec and rec.get('lote_mp') else '')
                if not lote and _fefo:
                    if mid in _fefo_cache:
                        lote = _fefo_cache[mid]
                    elif _time.monotonic() < _fefo_deadline:
                        try:
                            lote = _fefo(conn, mid, fr[1]) or ''
                        except Exception:
                            lote = ''
                        _fefo_cache[mid] = lote
                    else:
                        lote = ''  # presupuesto agotado · no colgar la página
                sheet.append({
                    'material_id': mid, 'material_nombre': fr[1] or '',
                    'nombre_inci': fr[3] or '',
                    'porcentaje': pct,
                    'cant_a_pesar_g': cant_a_pesar,
                    'lote': lote or '·',
                    'cant_pesada_g': (rec['real_g'] if rec else None),
                    'pesado_por': (rec['operario'] if rec else ''),
                    'pesado_at': (rec['fecha'] if rec else ''),
                    'pesado': bool(rec),
                    'pesaje_id': (rec.get('pesaje_id') if rec else None),
                    'realizado_por_full': (rec.get('realizado_por_full') if rec else ''),
                    'verificado_por': (rec.get('verificado_por') if rec else ''),
                    'verificado_at': (rec.get('verificado_at') if rec else ''),
                    'verificado_por_full': (rec.get('verificado_por_full') if rec else ''),
                    'obs_pesaje': (rec.get('observaciones') if rec else ''),
                })
        out['pesaje_sheet'] = sheet
    except Exception:
        out['pesaje_sheet'] = []
    # 2c. Precauciones / equipos (MyBatch "Instrucción de Manufactura" · estación ①)
    try:
        prows = conn.execute(
            "SELECT COALESCE(tipo,'precaucion'), descripcion, COALESCE(registrado_por,''), "
            "COALESCE(registrado_at_utc,'') FROM ebr_precauciones WHERE ebr_id=? ORDER BY id",
            (ebr_id,)).fetchall()
        out['precauciones'] = [{'tipo': r[0], 'descripcion': r[1],
                                'registrado_por': r[2], 'fecha': r[3]} for r in prows]
    except Exception:
        out['precauciones'] = []
    # 2d. Despeje de Línea · checklist 13 ítems (MyBatch · Sebastián 5/6-jun).
    # DOS etapas independientes con el mismo template: 'dispensacion' (sección 2)
    # y 'fabricacion' (sección 4). CUMPLE: 1=Sí, 0=No, None=pendiente.
    def _despeje_por_etapa(etapa):
        return despeje_checklist(conn, ebr_id, etapa)
    try:
        out['despeje_checklist'] = _despeje_por_etapa('dispensacion')
        out['despeje_checklist_fab'] = _despeje_por_etapa('fabricacion')
    except Exception:
        out['despeje_checklist'] = []
        out['despeje_checklist_fab'] = []
    # Sebastián 7-jul (v3): TIEMPO DE RESPUESTA de Calidad = desde el AVISO (iniciado_at_utc · cuando se manda la
    # alerta de inicio) hasta la 1ª VERIFICACIÓN de cualquier ítem del despeje. Mide qué tan al lado está Calidad.
    out['despeje_respuesta_min'] = None
    out['despeje_espera_min'] = None
    try:
        from datetime import datetime as _dtm
        def _parse_utc(s):
            s = (s or '').strip().replace('Z', '').replace('T', ' ').split('.')[0]
            return _dtm.fromisoformat(s) if s else None
        _ini = _parse_utc(out.get('iniciado_at_utc'))
        _pvr = conn.execute(
            "SELECT MIN(verificado_at_utc) FROM ebr_despeje_items "
            "WHERE ebr_id=? AND COALESCE(verificado_por,'')<>'' AND COALESCE(verificado_at_utc,'')<>''",
            (ebr_id,)).fetchone()
        _primera = _parse_utc(_pvr[0] if _pvr else '')
        if _ini and _primera:
            out['despeje_respuesta_min'] = round((_primera - _ini).total_seconds() / 60.0, 1)
        elif _ini and (out.get('estado') in ('iniciado', 'en_proceso')):
            out['despeje_espera_min'] = round((_dtm.utcnow() - _ini).total_seconds() / 60.0, 1)
    except Exception:
        pass
    # 3. Pasos (Fabricación/Mezcla) · FIX 6-jun: la tabla real es
    # ebr_pasos_ejecutados (no 'ebr_pasos', que no existe → la sección 5 salía
    # siempre vacía). Realizado por = operario_username; Verificado por = qc_username.
    try:
        rows = conn.execute(
            """SELECT orden, descripcion, COALESCE(estado,''),
                      COALESCE(iniciado_at_utc,''), COALESCE(completado_at_utc,''),
                      COALESCE(operario_username,''), COALESCE(observaciones,''),
                      COALESCE(qc_username,'')
               FROM ebr_pasos_ejecutados WHERE ebr_id=? ORDER BY orden""",
            (ebr_id,),
        ).fetchall()
        out['pasos'] = [{
            'orden': r[0], 'descripcion': r[1], 'estado': r[2],
            'iniciado': r[3], 'completado': r[4],
            'operario': r[5], 'observaciones': r[6],
            'verificado_por': r[7],
            'realizado_por_full': _persona(r[5]),
            'verificado_por_full': _persona(r[7]),
            'completado_flag': bool(r[4]),
        } for r in rows]
    except Exception:
        out['pasos'] = []
    # 4. IPC resultados
    # 4. Controles en Proceso (IPC) · FIX 6-jun: la tabla real es ipc_resultados +
    # ipc_specs (no 'ebr_ipc_resultados', inexistente → la sección 6 salía vacía).
    # Specs por producto (MBR) + resultado por lote. CONTROL/RESULTADO/conforme/
    # observaciones/Realizado por (Calidad).
    try:
        mbr_tpl = out['header'].get('mbr_template_id')
        rows = conn.execute(
            """SELECT s.parametro, COALESCE(s.unidad,''), s.valor_min, s.valor_max,
                      r.valor_medido, COALESCE(r.valor_texto,''), r.conforme,
                      COALESCE(r.medido_por,''), COALESCE(r.medido_at_utc,''),
                      COALESCE(r.notas,''), COALESCE(s.obligatorio,1), s.id
               FROM ipc_specs s
               LEFT JOIN ipc_resultados r ON r.ipc_spec_id=s.id AND r.ebr_id=?
               WHERE s.mbr_template_id=? ORDER BY s.id""",
            (ebr_id, mbr_tpl),
        ).fetchall()
        ipc = []
        nombres_mbr = set()
        for r in rows:
            vmin, vmax = r[2], r[3]
            rango = ''
            if vmin is not None and vmax is not None:
                rango = f"{vmin} – {vmax} {r[1]}".strip()
            elif vmin is not None:
                rango = f"≥ {vmin} {r[1]}".strip()
            elif vmax is not None:
                rango = f"≤ {vmax} {r[1]}".strip()
            resultado = (f"{r[4]} {r[1]}".strip() if r[4] is not None else (r[5] or ''))
            ipc.append({
                'control': r[0], 'unidad': r[1], 'rango': rango,
                'resultado': resultado,
                'conforme': (int(r[6]) if r[6] is not None else None),
                'observaciones': r[9] or 'No aplica',
                'realizado_por': r[7], 'realizado_por_full': _persona(r[7]),
                'fecha': r[8], 'obligatorio': bool(r[10]),
                'tipo': 'mbr', 'spec_id': r[11],
            })
            nombres_mbr.add((r[0] or '').strip().lower())
        # Controles ESTÁNDAR siempre presentes (los que el MBR no define).
        est = {}
        try:
            for er in conn.execute(
                """SELECT r.control_codigo, COALESCE(r.valor_texto,''), r.conforme,
                          COALESCE(r.observaciones,''), COALESCE(r.medido_por,''),
                          COALESCE(r.medido_at_utc,''), COALESCE(d.codigo,''),
                          COALESCE(d.estado,'')
                   FROM ipc_estandar_resultados r
                   LEFT JOIN desviaciones d ON d.id = r.desviacion_id
                   WHERE r.ebr_id=?""",
                (ebr_id,),
            ).fetchall():
                est[er[0]] = er
        except Exception as _e:
            log.warning("ipc estandar (vista) ebr=%s: %s", ebr_id, _e)
            est = {}
        for cod, nom, uni in _ipc_estandar_ebr(conn, ebr_id):
            if nom.strip().lower() in nombres_mbr:
                continue  # el MBR ya define este control · no duplicar
            er = est.get(cod)
            conf = (int(er[2]) if er and er[2] is not None else None)
            ipc.append({
                'control': nom, 'unidad': uni, 'rango': '',
                'resultado': (er[1] if er else ''),
                'conforme': conf,
                'observaciones': (er[3] if er and er[3] else ('No aplica' if conf == 2 else '')),
                'realizado_por': (er[4] if er else ''),
                'realizado_por_full': _persona(er[4] if er else ''),
                'fecha': (er[5] if er else ''), 'obligatorio': False,
                'tipo': 'estandar', 'codigo': cod,
                'desviacion': (er[6] if er else ''),
                'desviacion_estado': (er[7] if er else ''),
            })
        out['ipc'] = ipc
    except Exception:
        out['ipc'] = []
    # 7. Observaciones Generales del Proceso (MyBatch ⑦) · bitácora.
    try:
        rows = conn.execute(
            "SELECT descripcion, COALESCE(registrado_por,''), COALESCE(registrado_at_utc,'') "
            "FROM ebr_observaciones WHERE ebr_id=? ORDER BY id", (ebr_id,)).fetchall()
        out['observaciones_proceso'] = [{
            'descripcion': r[0], 'registrado_por': r[1],
            'registrado_por_full': _persona(r[1]), 'fecha': r[2],
        } for r in rows]
    except Exception:
        out['observaciones_proceso'] = []
    # 8. Registros Físicos del Proceso (MyBatch ⑧) · PDFs adjuntos.
    try:
        rows = conn.execute(
            "SELECT id, descripcion, COALESCE(tipo,''), "
            "(CASE WHEN COALESCE(archivo_b64,'')!='' THEN 1 ELSE 0 END) AS tiene_pdf, "
            "COALESCE(registrado_por,''), COALESCE(registrado_at_utc,'') "
            "FROM ebr_registros_fisicos WHERE ebr_id=? ORDER BY id DESC", (ebr_id,)).fetchall()
        out['registros_fisicos'] = [{
            'id': r[0], 'descripcion': r[1], 'tipo': r[2],
            'tiene_pdf': bool(r[3]), 'registrado_por': r[4], 'fecha': r[5],
        } for r in rows]
    except Exception:
        out['registros_fisicos'] = []
    # 5. Despejes (referenciados por lote o produccion_id)
    try:
        rows = conn.execute(
            """SELECT area_codigo, marcado_por, ts, COALESCE(observaciones,'')
               FROM despeje_linea_checklist
               ORDER BY ts DESC LIMIT 5""",
        ).fetchall()
        out['despejes_recientes'] = [{
            'area': r[0], 'marcado_por': r[1], 'fecha': r[2],
            'observaciones': r[3],
        } for r in rows]
    except Exception:
        out['despejes_recientes'] = []
    # 6. Audit log filtrado + Correcciones (Audit Trail Part 11 · MyBatch parity).
    # A nivel orden (registro_id=ebr_id) y por MP/paso/IPC (despues contiene ebr_id).
    try:
        rows = _ebr_audit_rows(conn, ebr_id)
        out['audit'] = [{
            'fecha': r[0], 'usuario': r[1], 'accion': r[2], 'detalle': r[3],
        } for r in rows]
        # Correcciones con diff campo/anterior/nuevo (parse antes/despues JSON).
        correcciones = []
        for r in rows:
            try:
                antes = _json.loads(r[4]) if r[4] else {}
            except Exception:
                antes = {}
            try:
                despues = _json.loads(r[5]) if r[5] else {}
            except Exception:
                despues = {}
            campos = []
            if isinstance(despues, dict):
                for k, vn in despues.items():
                    if k == 'ebr_id':
                        continue
                    va = antes.get(k) if isinstance(antes, dict) else None
                    if str(va) != str(vn):  # solo cambios reales
                        campos.append({'campo': k,
                                       'anterior': ('' if va is None else str(va)),
                                       'nuevo': ('' if vn is None else str(vn))})
            correcciones.append({
                'fecha': r[0], 'usuario': r[1],
                'usuario_full': _persona(r[1]), 'accion': r[2],
                'detalle': r[3], 'tabla': r[6], 'campos': campos,
            })
        out['correcciones'] = correcciones
    except Exception:
        out['audit'] = []
        out['correcciones'] = []
    # Resumen métricas
    completados = sum(1 for p in out['pasos'] if p['completado_flag'])
    out['progreso_pasos_pct'] = round((completados / len(out['pasos']) * 100) if out['pasos'] else 0, 1)
    out['pesajes_count'] = len(out['pesajes'])
    out['ipc_dentro_rango'] = sum(1 for i in out['ipc'] if i.get('conforme') == 1)
    out['ipc_total'] = len(out['ipc'])
    return jsonify(out)


@bp.route("/api/brd/ebr/<int:ebr_id>", methods=["GET"])
def detalle_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    row = conn.execute(
        """SELECT * FROM ebr_ejecuciones WHERE id = ?""", (ebr_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "EBR no encontrado"}), 404
    pasos = conn.execute(
        """SELECT * FROM ebr_pasos_ejecutados
           WHERE ebr_id = ? ORDER BY orden""", (ebr_id,),
    ).fetchall()
    d = _ebr_to_dict(row, pasos)
    # producto + área para el header del legajo (alinear con MyBatch · Sebastián 25-jun)
    try:
        mb = conn.execute("SELECT producto_nombre FROM mbr_templates WHERE id=?",
                          (d.get("mbr_template_id"),)).fetchone()
        d["producto_nombre"] = (mb[0] if mb else "")
    except Exception:
        d["producto_nombre"] = ""
    try:
        ar = conn.execute(
            "SELECT COALESCE(ap.nombre,'') FROM produccion_programada pp "
            "LEFT JOIN areas_planta ap ON ap.id=pp.area_id WHERE pp.id=?",
            (d.get("produccion_id"),)).fetchone()
        d["area_nombre"] = (ar[0] if ar else "")
    except Exception:
        d["area_nombre"] = ""
    # Rol del usuario en el batch (segregación de funciones GMP · el runner se adapta)
    d["mi_rol"] = _batch_role_info(session.get("compras_user", ""))
    # CONCILIACIÓN DEL GRANEL · cuánto entró, cuánto se envasó, cuánto quedó y qué
    # diferencia hay. Estaba calculada y expuesta sólo en /vista-completa, que el
    # legajo no llama: el número existía y nadie lo veía (M115). Es lo que MyBatch
    # muestra como "Cantidad por Envasar" y "% rendimiento", y acá es más completo
    # (incluye el remanente y si la cuenta CUADRA dentro de la tolerancia).
    try:
        d["conciliacion_granel"] = _conciliacion_granel(conn, ebr_id, d)
    except Exception as _e:
        log.warning("conciliacion_granel (detalle) ebr=%s: %s", ebr_id, _e)
        d["conciliacion_granel"] = None
    # Cierre · 3ª firma Director Técnico + correcciones (Part 11) + ajustes de MP
    try:
        dt = conn.execute("SELECT COALESCE(aprobado_dt_por,''), COALESCE(aprobado_dt_at_utc,'') "
                          "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        d["aprobado_dt_por"] = (dt[0] if dt else "")
        d["aprobado_dt_at"] = (dt[1] if dt else "")
    except Exception:
        d["aprobado_dt_por"] = ""
        d["aprobado_dt_at"] = ""
    try:
        d["correcciones"] = [dict(r) for r in conn.execute(
            "SELECT COALESCE(campo_afectado,'') AS campo_afectado, COALESCE(motivo,'') AS motivo, "
            "COALESCE(descripcion,'') AS descripcion, COALESCE(registrado_por,'') AS registrado_por, "
            "COALESCE(registrado_at_utc,'') AS registrado_at_utc FROM ebr_correcciones "
            "WHERE ebr_id=? ORDER BY id DESC", (ebr_id,)).fetchall()]
    except Exception:
        d["correcciones"] = []
    try:
        d["ajustes_mp"] = [dict(r) for r in conn.execute(
            "SELECT COALESCE(material,'') AS material, COALESCE(cantidad_g,0) AS cantidad_g, "
            "COALESCE(motivo,'') AS motivo, COALESCE(registrado_por,'') AS registrado_por, "
            "COALESCE(registrado_at_utc,'') AS registrado_at_utc FROM ebr_ajustes_mp "
            "WHERE ebr_id=? ORDER BY id DESC", (ebr_id,)).fetchall()]
    except Exception:
        d["ajustes_mp"] = []
    return jsonify(d)


@bp.route("/api/brd/ebr/<int:ebr_id>/pasos/<int:orden>/iniciar", methods=["POST"])
def iniciar_paso_ebr(ebr_id, orden):
    err = _require_brd_ejecutor()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    paso = cur.execute(
        """SELECT id, estado FROM ebr_pasos_ejecutados
           WHERE ebr_id = ? AND orden = ?""", (ebr_id, orden),
    ).fetchone()
    if not paso:
        return jsonify({"error": "paso no encontrado"}), 404
    if paso["estado"] != "pendiente":
        return jsonify({"error": f"paso ya iniciado (estado: {paso['estado']})"}), 409

    user = session.get("compras_user", "")
    cur.execute(
        """UPDATE ebr_pasos_ejecutados
             SET estado = 'en_proceso',
                 operario_username = ?,
                 iniciado_at_utc = datetime('now', 'utc')
           WHERE id = ?""",
        (user, paso["id"]),
    )
    cur.execute(
        """UPDATE ebr_ejecuciones SET estado = 'en_proceso'
           WHERE id = ? AND estado = 'iniciado'""", (ebr_id,),
    )
    audit_log(cur, usuario=user, accion="INICIAR_PASO_EBR",
              tabla="ebr_pasos_ejecutados", registro_id=paso["id"],
              despues={"ebr_id": ebr_id, "orden": orden, "operario": user})
    conn.commit()
    return jsonify({"ok": True, "estado": "en_proceso"})


@bp.route("/api/brd/ebr/<int:ebr_id>/pasos/<int:orden>/completar", methods=["POST"])
def completar_paso_ebr(ebr_id, orden):
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    observaciones = (body.get("observaciones") or "").strip()[:500]
    signature_id = body.get("signature_id")
    qc_signature_id = body.get("qc_signature_id")

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    paso = cur.execute(
        """SELECT id, estado, requiere_e_sign, requiere_qc, operario_username
           FROM ebr_pasos_ejecutados
           WHERE ebr_id = ? AND orden = ?""", (ebr_id, orden),
    ).fetchone()
    if not paso:
        return jsonify({"error": "paso no encontrado"}), 404
    if paso["estado"] not in ("en_proceso", "pendiente"):
        return jsonify({"error": f"paso ya completado (estado: {paso['estado']})"}), 409

    user = session.get("compras_user", "")

    if paso["requiere_e_sign"]:
        if not signature_id:
            return jsonify({
                "error": "paso requiere e-signature · meaning='ejecuta' "
                          "record_table='ebr_pasos_ejecutados'",
                "paso_id": paso["id"],
            }), 400
        if not _validar_signature(
            cur, signature_id, record_table="ebr_pasos_ejecutados",
            record_id=paso["id"], meaning="ejecuta", signer_username=user,
        ):
            return jsonify({"error": "signature_id inválido para este paso"}), 400

    qc_username = ""
    if paso["requiere_qc"]:
        if not qc_signature_id:
            return jsonify({
                "error": "paso requiere QC e-signature · meaning='supervisa'",
            }), 400
        qc_sig = cur.execute(
            """SELECT signer_username FROM e_signatures
               WHERE id = ? AND record_table = 'ebr_pasos_ejecutados'
                 AND record_id = ? AND meaning = 'supervisa'""",
            (int(qc_signature_id), str(paso["id"])),
        ).fetchone()
        if not qc_sig:
            return jsonify({"error": "qc_signature_id inválido"}), 400
        qc_username = qc_sig["signer_username"]
        # Segregación de funciones GMP · el QC (supervisa) no puede ser la
        # misma persona que ejecuta el paso · auto-aprobación rompe el control.
        if qc_username and qc_username == (paso["operario_username"] or user):
            return jsonify({"error": "El QC (supervisa) no puede ser el mismo operario que ejecutó el paso"}), 409

    op_username = paso["operario_username"] or user
    # CAS (race · M27): solo completar si el paso sigue pendiente/en_proceso ·
    # evita que dos completados concurrentes se pisen la e-firma/QC.
    cur.execute(
        """UPDATE ebr_pasos_ejecutados
             SET estado = 'completado',
                 operario_username = ?,
                 iniciado_at_utc = COALESCE(iniciado_at_utc, datetime('now', 'utc')),
                 completado_at_utc = datetime('now', 'utc'),
                 observaciones = ?,
                 e_sign_id = ?,
                 qc_username = ?,
                 qc_e_sign_id = ?
           WHERE id = ? AND estado IN ('en_proceso', 'pendiente')""",
        (op_username, observaciones,
         int(signature_id) if signature_id else None,
         qc_username,
         int(qc_signature_id) if qc_signature_id else None,
         paso["id"]),
    )
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "paso ya completado (concurrencia) · refrescá",
                        "codigo": "ESTADO_CAMBIO"}), 409
    audit_log(cur, usuario=user, accion="COMPLETAR_PASO_EBR",
              tabla="ebr_pasos_ejecutados", registro_id=paso["id"],
              despues={"ebr_id": ebr_id, "orden": orden,
                       "operario": op_username, "qc": qc_username or None})
    conn.commit()
    return jsonify({"ok": True, "estado": "completado"})


@bp.route("/api/brd/ebr/<int:ebr_id>/completar", methods=["POST"])
def completar_ebr(ebr_id):
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    try:
        cantidad_real = float(body.get("cantidad_real_g") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_real_g inválida"}), 400
    if cantidad_real <= 0:
        return jsonify({"error": "cantidad_real_g debe ser > 0"}), 400

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, cantidad_objetivo_g, COALESCE(fase,'fabricacion') AS fase, "
        "COALESCE(lote_codigo, lote) AS lote "
        "FROM ebr_ejecuciones WHERE id = ?",
        (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no completable (estado: {ebr['estado']})"}), 409
    # DEMO (Sebastián 20-jul): un lote DEMO (lote 'DEMO-...') se puede TERMINAR sin todos los
    # pasos/IPCs completos (es un sandbox para caminar el flujo). Los lotes reales exigen TODO (GMP).
    _es_demo = es_lote_demo(ebr["lote"] or "")

    pendientes = cur.execute(
        """SELECT COUNT(*) FROM ebr_pasos_ejecutados
           WHERE ebr_id = ? AND estado NOT IN ('completado', 'omitido')""",
        (ebr_id,),
    ).fetchone()[0]
    if pendientes and not _es_demo:
        return jsonify({"error": f"hay {pendientes} paso(s) sin completar"}), 409

    # IPCs obligatorios deben estar reportados Y conformes (Part 11 + GMP).
    # mbr_template_id viene de ebr_ejecuciones · re-leemos para no asumir.
    # FIX 1-jun-2026 audit Planta (P0 INVIMA) · ANTES seleccionaba solo
    # mbr_template_id pero abajo (cuarentena) accedía ebr_full['lote'] / .get('lote')
    # → KeyError/AttributeError SIEMPRE → la Entrada en CUARENTENA NUNCA se creaba
    # (lote PT no pasaba por cuarentena · liberar_ebr no tenía qué promover).
    # Ahora cargamos lote + lote_codigo (lote FISICO) y lo dejamos como dict.
    # FIX 12-jun: lote_codigo SI existe (ALTER ebr_ejecuciones · database.py:7933,
    # backfill COALESCE(lote_codigo,lote)). El PT se keyea por el lote fisico, no
    # por la llave sufijada -OF/-OA (antes inflaba el PT una vez por fase · A-3).
    _ef = cur.execute(
        "SELECT mbr_template_id, lote, lote_codigo FROM ebr_ejecuciones WHERE id = ?", (ebr_id,)
    ).fetchone()
    ebr_full = dict(_ef) if _ef else {}
    ipcs_faltantes = cur.execute(
        """SELECT s.parametro
           FROM ipc_specs s
           LEFT JOIN ipc_resultados r
             ON r.ipc_spec_id = s.id AND r.ebr_id = ?
           WHERE s.mbr_template_id = ?
             AND s.obligatorio = 1
             AND r.id IS NULL""",
        (ebr_id, ebr_full["mbr_template_id"]),
    ).fetchall()
    if ipcs_faltantes and not _es_demo:
        return jsonify({
            "error": "IPCs obligatorios sin reportar",
            "parametros": [r["parametro"] for r in ipcs_faltantes],
        }), 409
    # Audit 3-jun · incluir conforme IS NULL: un IPC cualitativo obligatorio
    # reportado pero SIN adjudicar (Conforme/No conforme) por QC no debe dejar
    # completar el lote (antes solo bloqueaba conforme=0 → cualitativo NULL pasaba).
    ipcs_no_conformes = cur.execute(
        """SELECT s.parametro, r.valor_medido, s.valor_min, s.valor_max, r.conforme
           FROM ipc_resultados r
           JOIN ipc_specs s ON s.id = r.ipc_spec_id
           WHERE r.ebr_id = ?
             AND s.obligatorio = 1
             AND (r.conforme = 0 OR r.conforme IS NULL)""",
        (ebr_id,),
    ).fetchall()
    if ipcs_no_conformes and not _es_demo:
        return jsonify({
            "error": "IPCs obligatorios fuera de spec o sin adjudicar QC "
                     "(conforme=NULL) · debe resolverse antes de completar",
            "parametros": [{
                "parametro": r["parametro"],
                "medido": r["valor_medido"],
                "min": r["valor_min"], "max": r["valor_max"],
                "conforme": r["conforme"],
            } for r in ipcs_no_conformes],
        }), 409

    # 29-jul · los 5 controles ESTÁNDAR (densidad/pH/olor/color/apariencia) son los que
    # de hecho se usan (ningún MBR define specs). Exigirlos antes de completar es la
    # posición GMP, pero nace APAGADO: encenderlo a ciegas traba el piso el mismo día.
    # Registrado = con valor adjudicado o marcado 'No aplica'; una fila con el valor
    # anotado y sin adjudicar cuenta como PENDIENTE (falta la firma de Calidad).
    if not _es_demo and _exige_ipc_estandar(conn):
        try:
            _regs = {r[0]: r[1] for r in cur.execute(
                "SELECT control_codigo, conforme FROM ipc_estandar_resultados WHERE ebr_id=?",
                (ebr_id,)).fetchall()}
        except Exception as _ee:
            log.warning("ipc_estandar_resultados no legible (ebr %s): %s", ebr_id, _ee)
            _regs = {}
        _falt = [nom for cod, nom, _u in _ipc_estandar_ebr(conn, ebr_id)
                 if _regs.get(cod) not in (0, 1, 2)]
        if _falt:
            return jsonify({
                "error": ("Faltan controles en proceso por registrar: "
                          + " · ".join(_falt)
                          + ". Registralos con su resultado o marcalos 'No aplica'."),
                "codigo": "IPC_ESTANDAR_PENDIENTES",
                "controles": _falt,
            }), 409

    yield_pct = round((cantidad_real / ebr["cantidad_objetivo_g"]) * 100, 2) if ebr["cantidad_objetivo_g"] else None
    # Puente OP→OF · densidad (g/mL) opcional → mL envasable = real_g / densidad.
    try:
        densidad = float(body.get("densidad_g_ml") or 0)
    except (ValueError, TypeError):
        densidad = 0.0
    densidad = densidad if densidad > 0 else None
    ml_envasable = round(cantidad_real / densidad, 2) if densidad else None
    # Batch C · rendimiento por UNIDADES (Envasado/Acondicionamiento). El yield de
    # granel (yield_pct) sigue igual; acá se calcula yield_uds_pct si el body trae
    # unidades. Aplica a cualquier fase pero típicamente OF/OA.
    def _num_opt(k):
        v = body.get(k)
        if v in (None, ""):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None
    uds_teoricas = _num_opt("unidades_teoricas")
    uds_buenas = _num_opt("unidades_buenas_real")
    yield_uds_pct = (round(uds_buenas / uds_teoricas * 100, 2)
                     if uds_teoricas and uds_buenas is not None and uds_teoricas > 0
                     else None)
    user = session.get("compras_user", "")
    cur.execute(
        """UPDATE ebr_ejecuciones
             SET estado = 'completado',
                 completado_at_utc = datetime('now', 'utc'),
                 cantidad_real_g = ?,
                 yield_pct = ?,
                 densidad_g_ml = ?,
                 ml_envasable = ?,
                 unidades_teoricas = ?,
                 unidades_buenas_real = ?,
                 yield_uds_pct = ?
           WHERE id = ? AND estado IN ('iniciado', 'en_proceso')""",
        (cantidad_real, yield_pct, densidad, ml_envasable,
         uds_teoricas, uds_buenas, yield_uds_pct, ebr_id),
    )
    if cur.rowcount == 0:
        # CAS (race · regla M-race): otro worker ya completó este EBR · evita
        # doble Entrada PT en CUARENTENA (infla el PT · A-3/M10).
        conn.rollback()
        return jsonify({
            "error": "El EBR ya fue completado o cambió de estado · refrescá",
            "codigo": "ESTADO_CAMBIO",
        }), 409
    # INVIMA-FIX · 21-may-2026 · cuarentena explícita auto al completar
    # Antes: lote PT quedaba 'completado' pero NO había movimiento de
    # Entrada con estado_lote='CUARENTENA' · podía usarse antes de QC.
    # Ahora: INSERT movimientos · libera_ebr promueve a VIGENTE (Fix prev).
    cuarentena_creada = False
    try:
        # A-3 (Sebastian 12-jun): el PT vendible se cuenta al terminar la fase FINAL
        # del lote + liberar. Keyear por LOTE FISICO (lote_codigo), no la llave
        # sufijada. Gate de fase terminal: si existe un EBR de una fase POSTERIOR
        # para el mismo lote fisico, esta fase NO crea el PT (lo creara la final) ->
        # evita 2-3 Entradas PT del mismo lote (una por OP/OF/OA · M10/M3).
        lote_ref = (ebr_full.get('lote_codigo') or ebr_full.get('lote') or '').strip()
        _FASE_ORDEN = {'fabricacion': 1, 'envasado': 2, 'acondicionamiento': 3}
        _orden_actual = _FASE_ORDEN.get(ebr['fase'] or 'fabricacion', 1)
        _hay_fase_posterior = False
        if lote_ref:
            for _r in cur.execute(
                "SELECT DISTINCT COALESCE(fase,'fabricacion') FROM ebr_ejecuciones "
                "WHERE COALESCE(NULLIF(lote_codigo,''), lote) = ? AND id != ?",
                (lote_ref, ebr_id)).fetchall():
                if _FASE_ORDEN.get(_r[0], 1) > _orden_actual:
                    _hay_fase_posterior = True
                    break
        if lote_ref and cantidad_real and cantidad_real > 0 and not _hay_fase_posterior:
            # Buscar producto del producción para material_id (puede ser PT)
            prod_row = cur.execute(
                """SELECT pp.producto FROM produccion_programada pp
                   WHERE pp.id = (SELECT produccion_id FROM ebr_ejecuciones WHERE id=?)""",
                (ebr_id,),
            ).fetchone()
            prod_nombre = prod_row[0] if prod_row else ''
            # Check si ya existe el movimiento PT para no duplicar.
            # Audit 3-jun · scopear por material_id PT (LIKE 'PT_%') · antes filtraba
            # solo por lote → una Entrada MP con el MISMO string de lote bloqueaba la
            # creación del PT (y viceversa en liberar/asignar-lote).
            existe = cur.execute(
                "SELECT 1 FROM movimientos WHERE lote=? AND tipo='Entrada' "
                "AND COALESCE(material_id,'') LIKE 'PT\\_%' ESCAPE '\\' LIMIT 1",
                (lote_ref,),
            ).fetchone()
            if not existe:
                cur.execute(
                    """INSERT INTO movimientos
                       (material_id, material_nombre, cantidad, tipo, fecha,
                        observaciones, operador, lote, estado_lote)
                       VALUES (?, ?, ?, 'Entrada', datetime('now','-5 hours'),
                               ?, ?, ?, 'CUARENTENA')""",
                    ('PT_' + (prod_nombre[:20] if prod_nombre else 'GENERICO'),
                     prod_nombre or 'PT',
                     cantidad_real,
                     f'Granel BRD completado · EBR #{ebr_id} · pendiente liberación QC',
                     user, lote_ref),
                )
                cuarentena_creada = True
    except Exception as _e:
        import logging as _logc
        _logc.getLogger('inventario.brd').warning('cuarentena auto completar_ebr fallo: %s', _e)
    conn.commit()
    audit_log(None, usuario=user, accion="COMPLETAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"cantidad_real_g": cantidad_real, "yield_pct": yield_pct,
                       "cuarentena_auto_creada": cuarentena_creada})
    return jsonify({"ok": True, "estado": "completado", "yield_pct": yield_pct,
                    "densidad_g_ml": densidad, "ml_envasable": ml_envasable,
                    "yield_uds_pct": yield_uds_pct,
                    "cuarentena_creada": cuarentena_creada})


@bp.route("/api/brd/ebr/<int:ebr_id>/asignar-lote-fisico", methods=["POST"])
def asignar_lote_fisico_ebr(ebr_id):
    """Reemplaza el lote provisional 'PP<id>' por el lote físico/comercial real
    (audit 3-jun). QC firma y libera el lote REAL, no un código interno; y la
    Entrada de PT en el kardex queda bajo el mismo lote. Solo antes de liberar.

    Body: {lote_fisico}
    """
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    nuevo = (body.get("lote_fisico") or "").strip()
    if not nuevo:
        return jsonify({"error": "lote_fisico requerido"}), 400
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, lote FROM ebr_ejecuciones WHERE id=?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"EBR {ebr['estado']} es inmutable · no se puede "
                                 f"reasignar el lote"}), 409
    anterior = ebr["lote"] or ""
    if nuevo == anterior:
        return jsonify({"ok": True, "lote": nuevo, "sin_cambios": True})
    # Unicidad: ningún otro EBR puede tener ese lote
    dup = cur.execute(
        "SELECT id FROM ebr_ejecuciones WHERE lote=? AND id<>?", (nuevo, ebr_id),
    ).fetchone()
    if dup:
        return jsonify({"error": f"el lote '{nuevo}' ya está en uso por otro EBR",
                        "codigo": "LOTE_DUPLICADO"}), 409
    cur.execute(
        "UPDATE ebr_ejecuciones SET lote=?, lote_codigo=? WHERE id=?",
        (nuevo, nuevo, ebr_id),
    )
    # Propagar al movimiento de Entrada PT creado con el lote provisional, para
    # que la promoción a VIGENTE (al liberar) y el kardex apunten al lote real.
    mov_actualizados = 0
    if anterior:
        try:
            cur.execute(
                "UPDATE movimientos SET lote=? WHERE lote=? AND tipo='Entrada' "
                "AND COALESCE(material_id,'') LIKE 'PT\\_%' ESCAPE '\\'",
                (nuevo, anterior),
            )
            mov_actualizados = cur.rowcount or 0
        except Exception:
            pass  # deploy-safe
    audit_log(cur, usuario=session.get("compras_user", ""),
              accion="ASIGNAR_LOTE_FISICO_EBR", tabla="ebr_ejecuciones",
              registro_id=ebr_id,
              antes={"lote": anterior}, despues={"lote": nuevo,
                                                 "movimientos_actualizados": mov_actualizados})
    conn.commit()
    return jsonify({"ok": True, "lote": nuevo, "lote_anterior": anterior,
                    "movimientos_actualizados": mov_actualizados})


@bp.route("/api/brd/ebr/<int:ebr_id>/firmar-rapido", methods=["POST"])
def firmar_ebr_rapido(ebr_id):
    """Crea una e-firma server-side (identidad de la sesión · 21 CFR Part 11 §11.200(a)(1)(ii)
    acceso continuo) para una acción del lote, y devuelve signature_id para encadenar con
    liberar/etc. 'libera'/'verifica' requieren Calidad/Dirección Técnica. Botones de cierre
    del batch (9-jun-2026)."""
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    meaning = (body.get("meaning") or "").strip()
    # `aprueba_dt` faltaba acá, y es el visto bueno del Director Técnico sobre el producto
    # terminado: sin él, la pantalla del legajo no tenía forma de pedir esa firma (M116 otra vez
    # -- el mismo meaning que en julio faltaba en la whitelist de `/api/sign`).
    if meaning not in ("libera", "ejecuta", "verifica", "aprueba", "aprueba_dt"):
        return jsonify({"ok": False, "error": "meaning inválido"}), 400
    user = session.get("compras_user", "")
    # Quién puede firmar CADA acto sale del resolvedor único, no de una lista a mano (M1).
    # La lista de antes era `ADMIN ∪ CALIDAD` y el mensaje prometía "Calidad / Dirección
    # Técnica" -- o sea que **el Director Técnico no podía firmar la liberación** que el propio
    # endpoint `/liberar` sí le permite, y Aseguramiento tampoco: el gate de la FIRMA y el de la
    # ACCIÓN decían cosas distintas, así que la pantalla se trababa sin explicar por qué (M32).
    _rol = _batch_role_info(user)
    _QUIEN_FIRMA = {
        "libera": "puede_liberar",
        "verifica": "verifica",
        "aprueba": "puede_aprobar",
        "aprueba_dt": "aprueba_dt",
    }
    _flag = _QUIEN_FIRMA.get(meaning)
    if _flag and not _rol.get(_flag):
        return jsonify({
            "ok": False,
            "error": ("Tu rol (%s) no puede firmar esta acción." % (_rol.get("rol") or "sin rol")
                      if meaning != "aprueba_dt" else
                      "El visto bueno final lo da la Dirección Técnica."),
        }), 403
    conn = get_db(); cur = conn.cursor()
    if not cur.execute("SELECT id FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone():
        return jsonify({"ok": False, "error": "EBR no encontrado"}), 404
    try:
        from blueprints.firmas import crear_firma_directa
    except Exception:
        from api.blueprints.firmas import crear_firma_directa
    sig_id = crear_firma_directa(conn, username=user, record_table="ebr_ejecuciones",
                                 record_id=str(ebr_id), meaning=meaning,
                                 comment="Firma de cierre/verificación de lote")
    conn.commit()
    return jsonify({"ok": True, "signature_id": sig_id})


@bp.route("/api/brd/ebr/<int:ebr_id>/liberar", methods=["POST"])
def liberar_ebr(ebr_id):
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, COALESCE(lote_codigo, lote, '') AS _lote FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    # DEMO (lote 'DEMO-...') · sandbox para caminar el flujo: un click, sin e-firma
    # (Part 11). Los lotes REALES siguen exigiendo signature_id 'libera'. Los gates
    # regulatorios de abajo (desviación/IPC OOS/micro/pesajes) siguen aplicando.
    _es_demo = es_lote_demo(ebr["_lote"] or "")
    if not signature_id and not _es_demo:
        return jsonify({
            "error": "signature_id requerido · meaning='libera' record_table='ebr_ejecuciones'",
        }), 400
    if ebr["estado"] not in ("completado", "en_revision_qc"):
        return jsonify({"error": f"solo completado puede liberarse (actual: {ebr['estado']})"}), 409

    # Reemplazo MyBatch fase 2 · no liberar un lote con una desviación ABIERTA
    # (la que abre un IPC OOS, u otra del lote). Debe cerrarse/anularse antes.
    try:
        _lr = cur.execute("SELECT lote FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        _lote = (_lr[0] if _lr else '') or ''
        if _lote:
            # FIX 1-jun-2026 (audit): bloquear también desviaciones CERRADAS con CAPA
            # NO EFECTIVO (efectividad_ok=0) · antes una cerrada-no-efectiva desbloqueaba
            # la liberación. (El LIKE '%lote%' se mantiene a propósito: afinarlo a token
            # exacto podría NO ver una desviación real si lotes_afectados es texto libre →
            # liberaría producto no conforme. El falso positivo bloquea de más = lado seguro.)
            desv_open = cur.execute(
                """SELECT codigo, COALESCE(estado,''), COALESCE(efectividad_ok,1)
                     FROM desviaciones
                    WHERE lotes_afectados LIKE ?
                      AND ( COALESCE(estado,'') NOT IN ('cerrada', 'anulada')
                            OR (COALESCE(estado,'') = 'cerrada'
                                AND COALESCE(efectividad_ok,1) = 0) )
                    ORDER BY id DESC LIMIT 1""",
                (f'%{_lote}%',),
            ).fetchone()
            if desv_open:
                _cerrada_inef = (desv_open[1] == 'cerrada')
                return jsonify({
                    "error": (f"No se puede liberar: desviación {desv_open[0]} "
                              + ("CERRADA con CAPA NO EFECTIVO" if _cerrada_inef else "ABIERTA")
                              + f" para el lote {_lote}. "
                              + ("Reabrí/resolvé con un CAPA efectivo antes de liberar."
                                 if _cerrada_inef else
                                 "Cerrá/resolvé la desviación (clasificar→investigar→CAPA→cerrar) primero.")),
                    "codigo": ("DESVIACION_CAPA_INEFECTIVO" if _cerrada_inef
                               else "DESVIACION_ABIERTA"),
                }), 409
    except Exception:
        pass  # deploy-safe (tabla/columna ausente no debe romper liberación)

    # Audit 3-jun · GATE DIRECTO IPC OOS (fail-closed, independiente del texto del
    # lote). El gate por desviación de arriba depende del matching textual de
    # lotes_afectados y de que la auto-desviación se haya creado. Acá chequeamos
    # por ebr_id directo: si hay IPC no-conforme o sin adjudicar, bloquear salvo
    # que CADA uno tenga su desviación resuelta (cerrada + CAPA efectivo).
    try:
        _oos_n = cur.execute(
            "SELECT COUNT(*) FROM ipc_resultados "
            "WHERE ebr_id=? AND (conforme=0 OR conforme IS NULL)", (ebr_id,),
        ).fetchone()[0]
    except Exception:
        _oos_n = 0
    if _oos_n:
        try:
            _sin_resolver = cur.execute(
                """SELECT COUNT(*) FROM ipc_resultados r
                     LEFT JOIN desviaciones d ON d.id = r.desviacion_id
                    WHERE r.ebr_id = ?
                      AND (r.conforme = 0 OR r.conforme IS NULL)
                      AND ( r.desviacion_id IS NULL
                            OR COALESCE(d.estado,'') NOT IN ('cerrada','anulada')
                            OR (COALESCE(d.estado,'') = 'cerrada'
                                AND COALESCE(d.efectividad_ok,1) = 0) )""",
                (ebr_id,),
            ).fetchone()[0]
        except Exception:
            # No se pudo verificar el enlace (p.ej. desviacion_id ausente en PG):
            # hay OOS y no podemos probar que esté resuelto → bloquear (fail-closed).
            _sin_resolver = _oos_n
        if _sin_resolver:
            return jsonify({
                "error": (f"No se puede liberar: {_sin_resolver} IPC fuera de "
                          f"especificación o sin adjudicar QC sin desviación "
                          f"resuelta (cerrada con CAPA efectivo)."),
                "codigo": "IPC_OOS_SIN_RESOLVER",
            }), 409

    # 29-jul · EL MISMO GATE PARA LOS CONTROLES ESTÁNDAR. El de arriba mira sólo
    # `ipc_resultados` (specs del MBR) y hoy NINGÚN MBR define specs → todo pasa por la
    # vía estándar, así que el control de OOS estaba de hecho inerte: se reprodujo un
    # lote con el pH marcado 'No cumple' saliendo 'liberado'. Espeja el de arriba:
    #  · conforme=0 (no conformidad DECLARADA) → sólo pasa con su desviación cerrada y
    #    CAPA efectivo. Nadie marca 'No cumple' por accidente.
    #  · valor anotado y NADIE adjudicó (conforme NULL con resultado) → tampoco: es la
    #    firma de Calidad que falta, igual que el cualitativo del MBR.
    # Lo que NO bloquea acá es un control sin registrar (fila ausente): eso lo gobierna
    # el toggle `exigir_ipc_estandar` en `completar`, o este gate sería el estricto
    # encendido por la puerta de atrás (M68).
    _est_bloq = []
    try:
        _est_bloq = cur.execute(
            """SELECT r.control_nombre, r.conforme, COALESCE(r.valor_texto,''),
                      COALESCE(d.codigo,''), COALESCE(d.estado,'')
                 FROM ipc_estandar_resultados r
                 LEFT JOIN desviaciones d ON d.id = r.desviacion_id
                WHERE r.ebr_id = ?
                  AND ( ( r.conforme = 0
                          AND ( r.desviacion_id IS NULL
                                OR COALESCE(d.estado,'') NOT IN ('cerrada','anulada')
                                OR (COALESCE(d.estado,'') = 'cerrada'
                                    AND COALESCE(d.efectividad_ok,1) = 0) ) )
                        OR ( r.conforme IS NULL
                             AND COALESCE(TRIM(r.valor_texto),'') != '' ) )""",
            (ebr_id,)).fetchall()
    except Exception as _ee:
        # No se pudo verificar (columna/tabla ausente): si hay estándar no conformes no
        # podemos probar que estén resueltos → fail-closed, igual que el gate de arriba.
        log.warning("gate IPC estándar no verificable: %s", _ee)
        try:
            _n = cur.execute(
                "SELECT COUNT(*) FROM ipc_estandar_resultados "
                "WHERE ebr_id=? AND conforme=0", (ebr_id,)).fetchone()[0]
        except Exception:
            _n = 0
        if _n:
            return jsonify({
                "error": (f"No se puede liberar: {_n} control(es) estándar NO CONFORME(S) "
                          f"y no se pudo verificar su desviación."),
                "codigo": "IPC_ESTANDAR_NO_VERIFICABLE",
            }), 409
        _est_bloq = []
    if _est_bloq:
        _nc = [r for r in _est_bloq if r[1] == 0]
        _sa = [r for r in _est_bloq if r[1] is None]
        if _nc:
            return jsonify({
                "error": ("No se puede liberar: control(es) en proceso NO CONFORME(S) sin "
                          "desviación resuelta (cerrada con CAPA efectivo) · "
                          + " · ".join(f"{r[0]} = {r[2]}" + (f" [{r[3]}]" if r[3] else "")
                                       for r in _nc)),
                "codigo": "IPC_ESTANDAR_NO_CONFORME",
                "controles": [{"control": r[0], "resultado": r[2],
                               "desviacion": r[3], "estado_desviacion": r[4]} for r in _nc],
            }), 409
        return jsonify({
            "error": ("No se puede liberar: control(es) en proceso con resultado anotado y "
                      "SIN adjudicar por Calidad (Cumple / No cumple) · "
                      + " · ".join(f"{r[0]} = {r[2]}" for r in _sa)),
            "codigo": "IPC_ESTANDAR_SIN_ADJUDICAR",
            "controles": [{"control": r[0], "resultado": r[2]} for r in _sa],
        }), 409

    # Batch B · Acondicionamiento · no liberar con arte/etiqueta sin aprobar
    # (gate de etiquetado GMP). Aplica si hay artes registradas (costo nulo si no).
    try:
        _artes_sin = cur.execute(
            "SELECT COUNT(*) FROM ebr_artes_codificacion "
            "WHERE ebr_id=? AND COALESCE(aprobado_por,'')=''", (ebr_id,),
        ).fetchone()[0]
    except Exception:
        _artes_sin = 0
    if _artes_sin:
        return jsonify({
            "error": f"No se puede liberar: {_artes_sin} arte/etiqueta sin aprobar "
                     f"(aprobá la codificación/etiqueta antes de liberar).",
            "codigo": "ARTES_SIN_APROBAR",
        }), 409

    # GATE MICRO · Fase 2 (14-jun · decisión Sebastián = bloqueo duro). El lote NO se
    # libera si tiene un resultado micro FUERA DE SPEC DE INDUSTRIA sin resolver (OOS
    # abierto) · esto es incondicional y seguro (solo dispara con dato real de OOS, no
    # rompe lotes sin micro). El requisito de que el análisis micro ESTÉ PRESENTE
    # ("faltante") es más estricto y se enciende por fases con BRD_MICRO_GATE='strict'
    # (igual que EBR_MODE off→warn→strict), para no frenar la operación antes de que
    # estén cargando micro consistentemente.
    try:
        _mr = cur.execute("SELECT lote FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        _lote_pt = (_mr[0] if _mr else '') or ''
    except Exception:
        _lote_pt = ''
    if _lote_pt:
        try:
            micro_oos = cur.execute(
                "SELECT mr.microorganismo, mr.valor, mr.valor_texto, mr.unidad "
                "FROM calidad_micro_resultados mr "
                "LEFT JOIN calidad_oos o ON o.id = mr.oos_id "
                "WHERE (mr.ebr_id=? OR mr.lote=?) AND mr.estado='fuera_industria' "
                "AND (mr.oos_id IS NULL OR LOWER(COALESCE(o.estado,'')) NOT IN ('cerrado','rechazado','descartado')) "
                "ORDER BY mr.id DESC LIMIT 1",
                (ebr_id, _lote_pt),
            ).fetchone()
        except Exception:
            micro_oos = None  # tabla/columna ausente · deploy-safe
        if micro_oos:
            return jsonify({
                "error": (f"No se puede liberar: análisis microbiológico FUERA DE SPEC "
                          f"({micro_oos[0]}: {micro_oos[1] if micro_oos[1] is not None else micro_oos[2]} "
                          f"{micro_oos[3] or ''}) sin OOS resuelto para el lote {_lote_pt}. "
                          f"Resolvé el OOS micro antes de liberar."),
                "codigo": "MICRO_OOS",
            }), 409
        # Modo del gate "micro presente": app_settings.micro_gate_mode (toggle desde la
        # UI de Calidad, sin tocar Render) → fallback env BRD_MICRO_GATE → 'off'.
        _gate_mode = 'off'
        try:
            _gm = cur.execute("SELECT valor FROM app_settings WHERE clave='micro_gate_mode' LIMIT 1").fetchone()
            if _gm and _gm[0]:
                _gate_mode = str(_gm[0]).lower()
            else:
                import os as _os_micro
                _gate_mode = _os_micro.environ.get('BRD_MICRO_GATE', 'off').lower()
        except Exception:
            import os as _os_micro
            _gate_mode = _os_micro.environ.get('BRD_MICRO_GATE', 'off').lower()
        if _gate_mode == 'strict':
            try:
                _micro_ok = cur.execute(
                    "SELECT COUNT(*) FROM calidad_micro_resultados "
                    "WHERE (ebr_id=? OR lote=?) AND estado IN ('ok','fuera_meta')",
                    (ebr_id, _lote_pt),
                ).fetchone()[0]
            except Exception:
                _micro_ok = 1  # deploy-safe
            if not _micro_ok:
                return jsonify({
                    "error": (f"No se puede liberar: falta el análisis microbiológico del "
                              f"lote {_lote_pt} (BRD_MICRO_GATE=strict). Registrá el resultado "
                              f"micro conforme antes de liberar."),
                    "codigo": "MICRO_FALTANTE",
                }), 409

    # RENDIMIENTO ANÓMALO · un yield fuera del 80-115% (pérdida de batch, error de tara,
    # unidades sumadas de otra orden) no se libera sin explicación.
    #
    # El control ya existía, pero vivía DENTRO del bloque `EBR_MODE == 'strict'` de abajo
    # y el modo real es warn: no corría nunca, o sea que hoy un lote al 127% se libera en
    # silencio (M119 · un control que vive en un camino por el que no pasa el tráfico no
    # es un control). Ahora corre SIEMPRE, y bloquea si el modo es strict -igual que
    # antes, y en el mismo orden respecto de los otros gates- o si se prende su
    # interruptor propio, que nace apagado para no trabar la liberación el mismo día
    # (M126). Con el interruptor apagado, liberar sin justificar DEJA RASTRO (M100).
    _yjust_pre = (body.get('yield_justificacion') or '').strip()
    try:
        _yp = (cur.execute("SELECT yield_pct FROM ebr_ejecuciones WHERE id=?",
                           (ebr_id,)).fetchone() or [None])[0]
    except Exception:
        _yp = None
    _libera_sin_justificar = bool(_yp is not None and (_yp < 80 or _yp > 115)
                                  and not _yjust_pre)
    if _libera_sin_justificar and (_exige_justificacion_yield(conn)
                                   or _ebr_mode_now(cur) == 'strict'):
        return jsonify({"error": f"Rendimiento fuera de rango ({_yp}%) · GMP exige justificar "
                                 f"un yield anómalo (<80% o >115%) antes de liberar.",
                        "codigo": "YIELD_FUERA_RANGO", "yield_pct": _yp}), 409

    # Audit 3-jun · GATE DE COMPLETITUD del legajo · solo EBR_MODE='strict' (BPM
    # duro). En 'warn' (piloto) NO bloquea, para no frenar mientras se adopta.
    if _ebr_mode_now(cur) == 'strict':
        # #5/#6 (27-jun · auditoría de planta · solo FABRICACIÓN del granel) · cerrar 2 huecos del gate.
        _fase_lib = str((cur.execute("SELECT COALESCE(fase,'fabricacion') FROM ebr_ejecuciones WHERE id=?",
                                     (ebr_id,)).fetchone() or ['fabricacion'])[0]).strip().lower()
        if _fase_lib == 'fabricacion':
            # #5 · sin registro de pesaje/dispensado de MP no se libera (antes un EBR con CERO pesajes pasaba:
            # el gate de 2ª firma de abajo cuenta 0 sin-verificar → ok). Un lote sin dispensado es inadmisible.
            try:
                _n_pes = cur.execute("SELECT COUNT(*) FROM ebr_pesajes WHERE ebr_id=?", (ebr_id,)).fetchone()[0]
            except Exception:
                _n_pes = 0
            if _n_pes == 0:
                return jsonify({"error": "No se puede liberar: no hay registro de pesaje/dispensado de "
                                "materias primas del lote.", "codigo": "SIN_PESAJES"}), 409

        try:
            _pes_sin_verif = cur.execute(
                "SELECT COUNT(*) FROM ebr_pesajes "
                "WHERE ebr_id=? AND COALESCE(verificado_por,'')=''", (ebr_id,),
            ).fetchone()[0]
        except Exception:
            _pes_sin_verif = 0
        if _pes_sin_verif:
            return jsonify({
                "error": f"No se puede liberar: {_pes_sin_verif} pesaje(s) sin "
                         f"2ª firma de verificación.",
                "codigo": "PESAJES_SIN_VERIFICAR",
            }), 409
        try:
            _n_concil = cur.execute(
                "SELECT COUNT(*) FROM ebr_conciliacion_material WHERE ebr_id=?",
                (ebr_id,),
            ).fetchone()[0]
        except Exception:
            _n_concil = 0
        if _n_concil == 0:
            return jsonify({
                "error": "No se puede liberar: falta la conciliación de material "
                         "(envase/empaque) del lote.",
                "codigo": "CONCILIACION_FALTANTE",
            }), 409
        # MyBatch ② · despeje de línea conforme obligatorio (GMP)
        try:
            _despeje_ok = cur.execute(
                "SELECT COUNT(*) FROM ebr_despeje_linea WHERE ebr_id=? AND conforme=1",
                (ebr_id,),
            ).fetchone()[0]
        except Exception:
            _despeje_ok = 1  # tabla ausente · no bloquear (deploy-safe)
        if not _despeje_ok:
            return jsonify({
                "error": "No se puede liberar: falta el despeje de línea CONFORME.",
                "codigo": "DESPEJE_FALTANTE",
            }), 409

    # INVIMA-FIX · 21-may-2026 · tiempo mínimo cuarentena antes de liberar
    # Antes: QA podía liberar EBR completado inmediatamente
    # Default: 0 días (sin gate) · env BRD_CUARENTENA_MIN_DIAS=N para gate
    try:
        import os as _os_brd
        min_dias_cuarentena = int(_os_brd.environ.get('BRD_CUARENTENA_MIN_DIAS', '0'))
    except Exception:
        min_dias_cuarentena = 0
    if min_dias_cuarentena > 0:
        try:
            row_t = cur.execute(
                "SELECT completado_at_utc FROM ebr_ejecuciones WHERE id=?",
                (ebr_id,),
            ).fetchone()
            if row_t and row_t[0]:
                from datetime import datetime as _dtbrd
                completado_dt = _dtbrd.fromisoformat(str(row_t[0]).replace('Z', '+00:00').split('.')[0])
                horas_transc = (_dtbrd.utcnow() - completado_dt).total_seconds() / 3600
                if horas_transc < min_dias_cuarentena * 24:
                    return jsonify({
                        'error': f'Tiempo mínimo cuarentena: {min_dias_cuarentena} días · transcurridos {horas_transc/24:.1f}d',
                        'codigo': 'CUARENTENA_TIEMPO_MINIMO',
                    }), 409
        except Exception:
            pass  # graceful

    user = session.get("compras_user", "")
    if not _es_demo and not _validar_signature(
        cur, signature_id, record_table="ebr_ejecuciones",
        record_id=ebr_id, meaning="libera", signer_username=user,
    ):
        return jsonify({"error": "signature_id no corresponde a una firma 'libera' de este EBR por vos"}), 400

    # CAS (race multi-worker · regla M-race): transicionar SOLO si sigue en un
    # estado liberable. Sin esto, un liberar y un rechazar concurrentes (ambos
    # pasan el check-then-act de arriba) podían dejar el EBR 'rechazado' pero con
    # el PT ya promovido a VIGENTE = producto rechazado vendible (riesgo INVIMA).
    # RENDIMIENTO ANÓMALO · un yield fuera del 80-115% (pérdida de batch, error de tara,
    # unidades que se sumaron de otra orden) no se libera sin explicación. El control
    # existía pero vivía dentro del bloque `EBR_MODE == 'strict'` y el modo real es warn:
    # o sea que no corría nunca (M119). Ahora corre siempre, con su propio interruptor
    # -apagado de fábrica, para no trabar la liberación el mismo día (M126)- y cuando está
    # apagado igual DEJA RASTRO de que se liberó sin justificar (M100).
    _yjust = (body.get('yield_justificacion') or '').strip()[:600]
    cur.execute(
        """UPDATE ebr_ejecuciones
             SET estado = 'liberado',
                 liberado_por = ?,
                 liberado_at_utc = datetime('now', 'utc'),
                 liberado_signature_id = ?,
                 yield_justificacion = CASE WHEN ? <> '' THEN ?
                                            ELSE COALESCE(yield_justificacion, '') END
           WHERE id = ? AND estado IN ('completado', 'en_revision_qc')""",
        (user, (int(signature_id) if signature_id else None), _yjust, _yjust, ebr_id),
    )
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({
            "error": "El EBR ya fue liberado/rechazado o cambió de estado · refrescá",
            "codigo": "ESTADO_CAMBIO",
        }), 409
    # INVIMA-FIX · 21-may-2026 · promociona lote PT a VIGENTE
    # Antes: estado solo cambiaba en ebr_ejecuciones · movimientos PT
    # seguía CUARENTENA · Compras/Despachos no podía facturarlo aunque
    # QC firmó · doble operación manual + riesgo despacho sin liberación.
    pt_lote_promovidos = 0
    try:
        lote_row = cur.execute(
            "SELECT lote, lote_codigo FROM ebr_ejecuciones WHERE id=?",
            (ebr_id,),
        ).fetchone()
        # A-3 (12-jun): el PT ahora se crea bajo el LOTE FISICO (lote_codigo) en la
        # fase final · liberar debe promoverlo por ese mismo lote fisico (antes
        # usaba la llave sufijada 'lote' y no encontraba el PT tras el fix).
        lote_ref = ((lote_row['lote_codigo'] or lote_row['lote']) if lote_row else '') or ''
        if lote_ref:
            cur.execute(
                """UPDATE movimientos SET estado_lote='VIGENTE'
                   WHERE lote=? AND tipo='Entrada'
                     AND COALESCE(material_id,'') LIKE 'PT\\_%' ESCAPE '\\'
                     AND estado_lote IN ('CUARENTENA','CUARENTENA_EXTENDIDA')""",
                (lote_ref,),
            )
            pt_lote_promovidos = cur.rowcount or 0
    except Exception as _e:
        import logging as _log
        _log.getLogger('inventario.brd').warning('liberar_ebr promocion PT fallo: %s', _e)
    # Expediente por lote (INVIMA · zero-paper): inscribir el BATCH RECORD (EBR liberado) en el registro central
    try:
        _einfo = cur.execute("SELECT COALESCE(e.numero_op,''), COALESCE(m.producto_nombre,''), "
                             "COALESCE(e.lote_codigo, e.lote, '') FROM ebr_ejecuciones e "
                             "LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id WHERE e.id=?", (ebr_id,)).fetchone()
        if _einfo:
            registrar_documento(cur, tipo_doc='EBR', formato='Batch Record', titulo='Registro de lote (batch record)',
                                url='/api/brd/ebr/%s/vista-completa' % ebr_id, entidad='PT',
                                codigo=(_einfo[0] or ''), producto_nombre=(_einfo[1] or ''), lote=(_einfo[2] or ''),
                                ref_tabla='ebr_ejecuciones', ref_id=ebr_id,
                                firma_id=(int(signature_id) if signature_id else None), generado_por=user)
    except Exception:
        pass
    conn.commit()
    audit_log(None, usuario=user, accion="LIBERAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"liberado_por": user, "signature_id": signature_id,
                       "pt_lotes_promovidos": pt_lote_promovidos,
                       "yield_pct": _yp,
                       "yield_justificacion": _yjust or None,
                       # Con el control apagado esto es lo único que queda: que se sepa
                       # que se liberó un rendimiento anómalo sin explicarlo.
                       "liberado_sin_justificar_yield": _libera_sin_justificar or None})
    # ENVASADO Fase 2 (26-jun · Sebastián) · al LIBERAR el granel de FABRICACIÓN (QC aprobó → PT VIGENTE)
    # se HABILITA automático el legajo de Envasado del MISMO lote físico (idempotente vía crear_ebr_desde_mbr
    # · best-effort · NO bloquea la liberación si falla). SOLO fase='fabricacion' (no encadenar al liberar un
    # envasado/acondicionamiento). Así Envasado queda "en blanco" hasta que algo se libera (no autocarga prod).
    _envasado_habilitado = None
    try:
        _erow = conn.execute(
            "SELECT COALESCE(e.fase,'fabricacion'), COALESCE(m.producto_nombre,''), "
            "COALESCE(e.lote_codigo, e.lote) "
            "FROM ebr_ejecuciones e LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id "
            "WHERE e.id=?", (ebr_id,)).fetchone()
        if _erow and str(_erow[0]).strip().lower() == 'fabricacion' and _erow[1] and _erow[2]:
            _res_env = crear_ebr_desde_mbr(conn.cursor(), producto_nombre=_erow[1],
                                           lote=_erow[2], usuario=user, fase='envasado')
            conn.commit()
            if _res_env.get('ok'):
                _envasado_habilitado = _res_env.get('id')
                if not _res_env.get('reusado'):
                    audit_log(None, usuario=user, accion="AUTO_CREAR_EBR_ENVASADO",
                              tabla="ebr_ejecuciones", registro_id=_res_env.get('id'),
                              despues={"origen_fabricacion_ebr": ebr_id, "lote": _erow[2]})
    except Exception as _e2:
        import logging as _log2
        _log2.getLogger('inventario.brd').warning(
            'auto-crear EBR envasado al liberar fallo (no bloquea): %s', _e2)
    return jsonify({"ok": True, "estado": "liberado",
                    "pt_lotes_promovidos": pt_lote_promovidos,
                    "envasado_ebr_id": _envasado_habilitado})


@bp.route("/api/brd/ebr/<int:ebr_id>/habilitar-envasado", methods=["POST"])
def habilitar_envasado_ebr(ebr_id):
    """Re-crea (o reusa) el legajo de ENVASADO de un lote de FABRICACIÓN ya liberado, por si el hook
    automático del liberar falló silenciosamente (best-effort). Idempotente · devuelve el error REAL
    si no se puede (M4 · no lo traga). Sebastián 20-jul."""
    err = _require_brd_ejecutor()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT COALESCE(e.fase,'fabricacion'), COALESCE(m.producto_nombre,''), "
        "COALESCE(e.lote_codigo, e.lote), e.estado "
        "FROM ebr_ejecuciones e LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id WHERE e.id=?",
        (ebr_id,)).fetchone()
    if not row:
        return jsonify({"error": "EBR no encontrado"}), 404
    _fase = str(row[0]).strip().lower()
    _prod = row[1]
    _lote = row[2]
    if _fase != 'fabricacion':
        return jsonify({"error": "Solo un legajo de FABRICACIÓN habilita el envasado."}), 400
    # El envasado se habilita SOLO cuando Calidad LIBERÓ el granel (igual que el hook automático de
    # liberar_ebr · GMP: no envasar producto no liberado). Sin esto, el botón crearía el legajo de
    # envasado de un lote que QC aún no aprobó (hallazgo review 20-jul · P1).
    _est_fab = str(row[3] or '').strip().lower()
    if _est_fab != 'liberado':
        return jsonify({"error": "La fabricación debe estar LIBERADA por Calidad antes de habilitar el "
                                 "envasado (estado actual: " + (_est_fab or 'sin estado') + ").",
                        "codigo": "FABRICACION_NO_LIBERADA"}), 409
    if not _prod or not _lote:
        return jsonify({"error": "El legajo no tiene producto/lote resueltos (¿el MBR quedó sin producto?)."}), 400
    user = session.get("compras_user", "")
    try:
        res = crear_ebr_desde_mbr(cur, producto_nombre=_prod, lote=_lote, usuario=user, fase='envasado')
    except Exception as e:
        conn.rollback()
        return jsonify({"error": "No se pudo crear el legajo de envasado: " + str(e)[:220]}), 500
    if not res.get('ok'):
        # LOTE_DUPLICADO = el legajo de envasado YA existe → devolver su id para abrirlo.
        if res.get('error') == 'LOTE_DUPLICADO':
            env = cur.execute(
                "SELECT id FROM ebr_ejecuciones WHERE COALESCE(lote_codigo,lote)=? "
                "AND COALESCE(fase,'fabricacion')='envasado'", (_lote,)).fetchone()
            return jsonify({"ok": True, "envasado_ebr_id": (env[0] if env else None), "ya_existia": True})
        # NO_MBR_APROBADO u otro → devolver la causa REAL (no silencio).
        return jsonify({"error": res.get('detail') or "No se pudo habilitar el envasado.",
                        "codigo": res.get('error')}), 409
    conn.commit()
    if not res.get('reusado'):
        audit_log(None, usuario=user, accion="AUTO_CREAR_EBR_ENVASADO", tabla="ebr_ejecuciones",
                  registro_id=res.get('id'),
                  despues={"origen_fabricacion_ebr": ebr_id, "lote": _lote, "manual": True})
    return jsonify({"ok": True, "envasado_ebr_id": res.get('id'), "reusado": res.get('reusado', False)})


@bp.route("/api/brd/ebr/<int:ebr_id>/rechazar", methods=["POST"])
def rechazar_ebr(ebr_id):
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    motivo = (body.get("motivo") or "").strip()
    signature_id = body.get("signature_id")
    if not motivo:
        return jsonify({"error": "motivo requerido"}), 400
    if not signature_id:
        return jsonify({"error": "signature_id requerido (meaning='rechaza')"}), 400

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("completado", "en_revision_qc"):
        return jsonify({"error": f"solo completado puede rechazarse (actual: {ebr['estado']})"}), 409

    user = session.get("compras_user", "")
    if not _validar_signature(
        cur, signature_id, record_table="ebr_ejecuciones",
        record_id=ebr_id, meaning="rechaza", signer_username=user,
    ):
        return jsonify({"error": "signature_id no corresponde a una firma 'rechaza' de este EBR por vos"}), 400

    # INVIMA-FIX · 21-may-2026 · grabar timestamp rechazo (KPI 30d en dashboard)
    # CAS (race · igual que liberar): no rechazar si ya se liberó/rechazó.
    cur.execute(
        """UPDATE ebr_ejecuciones
             SET estado = 'rechazado',
                 rechazado_motivo = ?,
                 rechazado_at_utc = datetime('now', 'utc')
           WHERE id = ? AND estado IN ('completado', 'en_revision_qc')""",
        (motivo, ebr_id),
    )
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({
            "error": "El EBR ya fue liberado/rechazado o cambió de estado · refrescá",
            "codigo": "ESTADO_CAMBIO",
        }), 409
    # FIX 7-jul (audit ultracode · INVIMA · máquina de estados): DEGRADAR el PT a RECHAZADO (espejo exacto de
    # liberar_ebr que lo promueve a VIGENTE). Sin esto, un lote RECHAZADO por Calidad dejaba su PT en
    # CUARENTENA/VIGENTE → producto rechazado quedaba VENDIBLE/usable (Res. INVIMA 2214). Por el lote FÍSICO.
    pt_lote_rechazados = 0
    try:
        _lr = cur.execute(
            "SELECT COALESCE(lote_codigo,'') AS lote_codigo, COALESCE(lote,'') AS lote "
            "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        _lote_ref = ((_lr['lote_codigo'] or _lr['lote']) if _lr else '') or ''
        if _lote_ref:
            cur.execute(
                """UPDATE movimientos SET estado_lote='RECHAZADO'
                   WHERE lote=? AND tipo='Entrada'
                     AND COALESCE(material_id,'') LIKE 'PT\\_%' ESCAPE '\\'
                     AND UPPER(COALESCE(estado_lote,'')) IN ('CUARENTENA','CUARENTENA_EXTENDIDA','VIGENTE')""",
                (_lote_ref,))
            pt_lote_rechazados = cur.rowcount or 0
    except Exception as _epr:
        import logging as _log
        _log.getLogger('inventario.brd').warning('rechazar_ebr degradacion PT fallo: %s', _epr)
    conn.commit()
    audit_log(None, usuario=user, accion="RECHAZAR_EBR",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"motivo": motivo, "signature_id": signature_id})
    return jsonify({"ok": True, "estado": "rechazado"})


@bp.route("/api/brd/ebr/<int:ebr_id>/descartar", methods=["POST"])
def descartar_ebr(ebr_id):
    """Elimina un legajo (EBR) creado POR ERROR del sistema (artefacto de bug, sin
    ejecución real) · solo Admin. HARD delete (sin rastro en la lista ni en el legajo):
    borra el EBR y sus filas hijas. CANDADO: solo aplica a iniciado/en_proceso/cancelado
    · un completado/liberado/rechazado representa un LOTE REAL y NO se elimina (409).
    Deja un audit_log de mantenimiento (quién/qué/cuándo · no es un lote en la lista).
    Sebastián 10-jun-2026."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in ADMIN_USERS:
        return jsonify({"error": "solo Admin puede eliminar un legajo"}), 403
    body = request.get_json(silent=True) or {}
    motivo = (body.get("motivo") or "Legajo inventado por error del sistema").strip()
    conn = get_db(); cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, COALESCE(numero_op,'') AS numero_op, "
        "COALESCE(lote_codigo, lote) AS lote, COALESCE(fase,'fabricacion') AS fase "
        "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    estado = ebr["estado"]
    if estado in ("completado", "liberado", "rechazado"):
        return jsonify({"error": f"este legajo es un lote REAL ({estado}) · no se elimina"}), 409
    # audit de mantenimiento ANTES de borrar (rastro interno · no un batch en la lista).
    audit_log(cur, usuario=user, accion="ELIMINAR_EBR_ERRONEO",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              antes={"estado": estado, "numero_op": ebr["numero_op"],
                     "lote": ebr["lote"], "fase": ebr["fase"]},
              despues={"motivo": motivo})
    # Hijas (best-effort · según migraciones algunas tablas pueden no existir).
    for _t in ("ebr_pasos_ejecutados", "ipc_resultados", "ebr_pesajes",
               "ebr_despeje_items", "ebr_artes_codificacion", "ebr_observaciones",
               "ebr_registros_fisicos", "ebr_conciliacion_material", "ebr_precauciones"):
        try:
            cur.execute(f"DELETE FROM {_t} WHERE ebr_id=?", (ebr_id,))
        except Exception:
            pass
    try:
        cur.execute("DELETE FROM e_signatures WHERE record_table='ebr_ejecuciones' AND record_id=?",
                    (str(ebr_id),))
    except Exception:
        pass
    cur.execute("DELETE FROM ebr_ejecuciones WHERE id=?", (ebr_id,))
    conn.commit()
    return jsonify({"ok": True, "eliminado": True, "id": ebr_id})


# ════════════════════════════════════════════════════════════════════════════
# Materiales de envase MANUALES del legajo (Sebastián 11-jun) · elegir/agregar/editar
# desde el desplegable de TODOS los envases (maestro_mee). Tabla aparte
# (ebr_envase_materiales) · no toca el envasado real ni la inmutabilidad del EBR.
# ════════════════════════════════════════════════════════════════════════════
@bp.route("/api/brd/envase-opciones", methods=["GET"])
def brd_envase_opciones():
    """Catálogo de TODOS los materiales de envase (maestro_mee) para el desplegable del
    legajo. Solo lectura. ?q= filtra por código/descripción."""
    err = _require_login()
    if err:
        return err
    conn = get_db(); cur = conn.cursor()
    try:
        rows = cur.execute(
            "SELECT codigo, COALESCE(descripcion,'') FROM maestro_mee ORDER BY codigo").fetchall()
    except Exception:
        rows = []
    out = [{"codigo": r[0], "descripcion": r[1],
            "label": (str(r[0]) + (" · " + r[1] if r[1] else ""))} for r in rows if r[0]]
    q = (request.args.get("q") or "").strip().upper()
    if q:
        out = [o for o in out if q in (o["label"] or "").upper()]
    return jsonify({"ok": True, "opciones": out})


def _ebr_estado_lote(cur, ebr_id):
    r = cur.execute(
        "SELECT estado, COALESCE(lote_codigo, lote, '') AS lote FROM ebr_ejecuciones WHERE id=?",
        (ebr_id,)).fetchone()
    return r


@bp.route("/api/brd/ebr/<int:ebr_id>/material-envase", methods=["POST"])
def brd_material_envase_upsert(ebr_id):
    """Agrega o EDITA a mano un material de envase del legajo (elegido del desplegable de
    maestro_mee). Bloqueado si el lote está liberado/rechazado (inmutable · Part 11)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    cod = (body.get("material_codigo") or "").strip()
    if not cod:
        return jsonify({"error": "Elegí un material de envase del desplegable"}), 400
    conn = get_db(); cur = conn.cursor()
    ebr = _ebr_estado_lote(cur, ebr_id)
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"el lote está {ebr['estado']} (inmutable) · no se edita"}), 409

    def _num(k):
        v = body.get(k)
        try:
            return float(v) if v not in (None, "") else None
        except Exception:
            return None

    nom = (body.get("material_nombre") or "").strip()
    if not nom:
        try:
            r = cur.execute("SELECT COALESCE(descripcion,'') FROM maestro_mee WHERE codigo=?",
                            (cod,)).fetchone()
            nom = (r[0] if r else "") or ""
        except Exception:
            nom = ""
    requerida = _num("requerida") or 0
    # Quién recibió y cuándo se sellan en el momento en que se declara la cantidad
    # RECIBIDA (sección 3 del envasado de MyBatch). Si no se declara, no se inventa
    # un receptor: un nombre puesto por defecto en un registro regulado es peor que
    # el campo vacío.
    from datetime import datetime as _dt_rec
    _hay_recibida = _num("recibida") is not None
    _recibido_por = user if _hay_recibida else ""
    _recibido_at = (_dt_rec.utcnow().replace(microsecond=0).isoformat()
                    if _hay_recibida else "")
    lote_mat = (body.get("lote_material") or "").strip()
    lote_env = (body.get("lote_envasado") or ebr["lote"] or "").strip()
    row_id = body.get("id")
    if row_id:
        # Una firma cubre LOS DATOS QUE SE FIRMARON. Si la edición cambia lo que la 2ª
        # firma certificó -qué material, de qué lote y cuánto llegó- la verificación se
        # CAE y hay que rehacerla; si sólo se ajusta la conciliación (devuelta/utilizada/
        # averiada), que es un momento posterior, la firma de recepción sigue valiendo.
        # Dejarla en pie tras cambiar la cantidad sería una firma sobre otro dato (Part 11).
        _anula_verif = False
        try:
            _prev = cur.execute(
                "SELECT COALESCE(material_codigo,''), COALESCE(lote_material,''), recibida, "
                "COALESCE(verificado_por,'') FROM ebr_envase_materiales WHERE id=? AND ebr_id=?",
                (int(row_id), ebr_id)).fetchone()
            if _prev and (_prev[3] or "").strip():
                _anula_verif = (
                    (_prev[0] or "") != cod
                    or (_prev[1] or "") != lote_mat
                    or (_prev[2] if _prev[2] is None else float(_prev[2])) != _num("recibida"))
        except Exception as _e:                 # columnas de la mig 394 · nunca callar (M94)
            log.warning("material-envase: verificación previa no legible (ebr=%s): %s", ebr_id, _e)
        _sql_v = (", verificado_por='', verificado_at_utc=''" if _anula_verif else "")
        cur.execute(
            "UPDATE ebr_envase_materiales SET material_codigo=?, material_nombre=?, "
            "lote_material=?, requerida=?, recibida=?, devuelta=?, utilizada=?, averiada=?, "
            "lote_envasado=?, recibido_por=?, recibido_at_utc=?" + _sql_v + " "
            "WHERE id=? AND ebr_id=?",
            (cod, nom, lote_mat, requerida, _num("recibida"), _num("devuelta"),
             _num("utilizada"), _num("averiada"), lote_env,
             _recibido_por, _recibido_at, int(row_id), ebr_id))
        if cur.rowcount != 1:
            return jsonify({"error": "fila no encontrada"}), 404
        nuevo_id = int(row_id); accion = "EDITAR_MATERIAL_ENVASE_EBR"
    else:
        cur.execute(
            "INSERT INTO ebr_envase_materiales (ebr_id, lote_envasado, material_codigo, "
            "material_nombre, lote_material, requerida, recibida, devuelta, utilizada, "
            "averiada, creado_por, recibido_por, recibido_at_utc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ebr_id, lote_env, cod, nom, lote_mat, requerida, _num("recibida"),
             _num("devuelta"), _num("utilizada"), _num("averiada"), user,
             _recibido_por, _recibido_at))
        nuevo_id = cur.lastrowid; accion = "AGREGAR_MATERIAL_ENVASE_EBR"
    audit_log(cur, usuario=user, accion=accion, tabla="ebr_envase_materiales",
              registro_id=nuevo_id, despues={"material": cod, "requerida": requerida})
    conn.commit()
    return jsonify({"ok": True, "id": nuevo_id})


@bp.route("/api/brd/ebr/<int:ebr_id>/material-envase/<int:row_id>/verificar", methods=["POST"])
def brd_material_envase_verificar(ebr_id, row_id):
    """2ª firma sobre el material de envase RECIBIDO (mig 394 · regla de 2 personas · GMP).

    En MyBatch recibir y verificar son dos pasos separados (`material_received` y
    `material_verified`), y esa separación ES el control: quien cuenta lo que llegó no
    puede ser el mismo que certifica que está bien. Espeja `despeje-verificar`.
    """
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    if not _batch_role_info(user).get("verifica"):
        return jsonify({"error": "Verificar el material recibido es atribución de Calidad / Jefe de "
                                 "Producción / Dirección Técnica. El operario sólo registra la recepción.",
                        "codigo": "SOLO_VERIFICA_MATERIAL"}), 403
    conn = get_db(); cur = conn.cursor()
    ebr = _ebr_estado_lote(cur, ebr_id)
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"el lote está {ebr['estado']} (inmutable) · no se verifica"}), 409
    fila = cur.execute(
        "SELECT COALESCE(recibido_por,''), recibida, COALESCE(verificado_por,''), "
        "COALESCE(material_codigo,'') FROM ebr_envase_materiales WHERE id=? AND ebr_id=?",
        (row_id, ebr_id)).fetchone()
    if not fila:
        return jsonify({"error": "fila no encontrada"}), 404
    if fila[1] is None or not (fila[0] or "").strip():
        return jsonify({"error": "todavía no se registró cuánto material llegó · no hay nada que verificar",
                        "codigo": "SIN_RECEPCION"}), 409
    if (fila[2] or "").strip():
        return jsonify({"error": "ya fue verificado por " + fila[2], "codigo": "YA_VERIFICADO"}), 409
    # DEMO: un lote de demostración se camina con una sola persona (igual que el despeje).
    _es_demo = es_lote_demo(ebr["lote"] or "")
    if not _es_demo and (fila[0] or "").strip() == user:
        return jsonify({
            "error": "No podés verificar tu propia recepción: la 2ª firma debe ser de OTRA persona "
                     "distinta a quien recibió el material (regla de las 2 personas · GMP).",
            "codigo": "AUTOVERIFICACION_BLOQUEADA"}), 409
    cur.execute(
        "UPDATE ebr_envase_materiales SET verificado_por=?, verificado_at_utc=datetime('now','utc') "
        "WHERE id=? AND ebr_id=? AND COALESCE(verificado_por,'')=''",
        (user, row_id, ebr_id))
    if cur.rowcount != 1:                      # CAS: otro worker la verificó primero (M27)
        conn.rollback()
        return jsonify({"error": "ya fue verificada · refrescá", "codigo": "YA_VERIFICADO"}), 409
    audit_log(cur, usuario=user, accion="VERIFICAR_MATERIAL_ENVASE_EBR",
              tabla="ebr_envase_materiales", registro_id=row_id,
              despues={"ebr_id": ebr_id, "material": fila[3], "recibida": fila[1],
                       "recibido_por": fila[0], "verificado_por": user})
    conn.commit()
    return jsonify({"ok": True, "verificado_por": user})


@bp.route("/api/brd/ebr/<int:ebr_id>/material-envase/<int:row_id>", methods=["DELETE"])
def brd_material_envase_delete(ebr_id, row_id):
    """Elimina una fila de material de envase agregada a mano (no toca las auto-cargadas
    del plan, que no tienen id). Bloqueado si el lote está liberado/rechazado."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    conn = get_db(); cur = conn.cursor()
    ebr = _ebr_estado_lote(cur, ebr_id)
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"el lote está {ebr['estado']} (inmutable)"}), 409
    cur.execute("DELETE FROM ebr_envase_materiales WHERE id=? AND ebr_id=?", (row_id, ebr_id))
    if cur.rowcount != 1:
        return jsonify({"error": "fila no encontrada"}), 404
    audit_log(cur, usuario=user, accion="ELIMINAR_MATERIAL_ENVASE_EBR",
              tabla="ebr_envase_materiales", registro_id=row_id)
    conn.commit()
    return jsonify({"ok": True, "eliminado": True})


def _materiales_envase_manuales(conn, ebr_id):
    """Filas de material de envase agregadas/editadas a mano (ebr_envase_materiales).
    Tienen `id` y `fuente='manual'` → la UI permite editarlas/borrarlas."""
    # `recibida`/`recibido_por` (mig 391) y `verificado_por` (mig 394) SE CONSULTAN acá:
    # sin eso la sección 3 del envasado de MyBatch (MATERIAL | N° LOTE | REQUERIDA |
    # RECIBIDA | RECIBIDO POR) queda a medias en pantalla aunque el dato esté guardado.
    # Es M115: un dato capturado que no llega al consumidor no existe.
    try:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT id, lote_envasado, material_codigo, material_nombre, lote_material, "
            # Los COALESCE VAN CON ALIAS: sin `AS`, la columna se llama "COALESCE(x,'')" y
            # el acceso por nombre revienta -- y acá lo tapaba un `except` mudo aguas arriba,
            # así que la fila desaparecía de la pantalla sin un solo error (M94).
            "requerida, devuelta, utilizada, averiada, recibida, "
            "COALESCE(recibido_por,'') AS recibido_por, "
            "COALESCE(recibido_at_utc,'') AS recibido_at_utc, "
            "COALESCE(verificado_por,'') AS verificado_por, "
            "COALESCE(verificado_at_utc,'') AS verificado_at_utc "
            "FROM ebr_envase_materiales WHERE ebr_id=? ORDER BY id", (ebr_id,)).fetchall()
    except Exception as _e:
        log.warning("materiales de envase manuales no legibles (ebr=%s): %s", ebr_id, _e)
        return []
    out = []
    for r in rows:
        req = r["requerida"]; dev = r["devuelta"]; uti = r["utilizada"]
        dif = None
        if req is not None and uti is not None:
            dif = round(float(req) - float(uti), 2)
        nom = r["material_nombre"] or ""
        # Faltante de ENTREGA (lo que no mandaron) vs merma: son cosas distintas y sin
        # esta resta se confunden -- el reclamo al proveedor se pierde dentro de "utilizada".
        rec = r["recibida"]
        falta_entrega = (round(float(req) - float(rec), 2)
                         if (req is not None and rec is not None) else None)
        out.append({
            "id": r["id"], "fuente": "manual",
            "lote_envasado": r["lote_envasado"] or "", "lote_acond": r["lote_envasado"] or "",
            "material": (r["material_codigo"] + (" " + nom if nom else "")),
            "material_codigo": r["material_codigo"], "material_nombre": nom,
            "lote_material": r["lote_material"] or "",
            "requerida": req, "recibida": rec, "faltante_entrega": falta_entrega,
            "recibido_por": r["recibido_por"], "recibido_at_utc": r["recibido_at_utc"],
            "verificado_por": r["verificado_por"], "verificado_at_utc": r["verificado_at_utc"],
            "devuelta": dev, "utilizada": uti,
            "averiada": r["averiada"], "diferencia": dif,
        })
    return out


# ── Presentaciones MANUALES del legajo (gemelo de los materiales · 11-jun) ──────
@bp.route("/api/brd/ebr/<int:ebr_id>/presentacion", methods=["POST"])
def brd_presentacion_upsert(ebr_id):
    """Agrega o EDITA a mano una presentación del legajo (por si no cargó del plan).
    Bloqueado si el lote está liberado/rechazado (inmutable · Part 11)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    pres = (body.get("presentacion") or "").strip()
    if not pres:
        return jsonify({"error": "Indicá la presentación (ej. 30 ml)"}), 400
    conn = get_db(); cur = conn.cursor()
    ebr = _ebr_estado_lote(cur, ebr_id)
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"el lote está {ebr['estado']} (inmutable) · no se edita"}), 409

    def _num(k):
        v = body.get(k)
        try:
            return float(v) if v not in (None, "") else None
        except Exception:
            return None

    cliente = (body.get("cliente") or "Animus DTC").strip()
    envase = (body.get("envase_codigo") or "").strip()
    area = (body.get("area") or "").strip()
    lote = (body.get("lote") or ebr["lote"] or "").strip()
    vol = _num("volumen_ml"); uds = _num("unidades")
    row_id = body.get("id")
    if row_id:
        cur.execute(
            "UPDATE ebr_presentaciones_manual SET presentacion=?, cliente=?, volumen_ml=?, "
            "envase_codigo=?, unidades=?, area=?, lote=? WHERE id=? AND ebr_id=?",
            (pres, cliente, vol, envase, uds, area, lote, int(row_id), ebr_id))
        if cur.rowcount != 1:
            return jsonify({"error": "fila no encontrada"}), 404
        nuevo_id = int(row_id); accion = "EDITAR_PRESENTACION_EBR"
    else:
        cur.execute(
            "INSERT INTO ebr_presentaciones_manual (ebr_id, presentacion, cliente, volumen_ml, "
            "envase_codigo, unidades, area, lote, creado_por) VALUES (?,?,?,?,?,?,?,?,?)",
            (ebr_id, pres, cliente, vol, envase, uds, area, lote, user))
        nuevo_id = cur.lastrowid; accion = "AGREGAR_PRESENTACION_EBR"
    audit_log(cur, usuario=user, accion=accion, tabla="ebr_presentaciones_manual",
              registro_id=nuevo_id, despues={"presentacion": pres, "unidades": uds, "cliente": cliente})
    conn.commit()
    return jsonify({"ok": True, "id": nuevo_id})


@bp.route("/api/brd/ebr/<int:ebr_id>/presentacion/<int:row_id>", methods=["DELETE"])
def brd_presentacion_delete(ebr_id, row_id):
    """Elimina una presentación agregada a mano (no toca las auto-cargadas del plan)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    conn = get_db(); cur = conn.cursor()
    ebr = _ebr_estado_lote(cur, ebr_id)
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] in ("liberado", "rechazado"):
        return jsonify({"error": f"el lote está {ebr['estado']} (inmutable)"}), 409
    cur.execute("DELETE FROM ebr_presentaciones_manual WHERE id=? AND ebr_id=?", (row_id, ebr_id))
    if cur.rowcount != 1:
        return jsonify({"error": "fila no encontrada"}), 404
    audit_log(cur, usuario=user, accion="ELIMINAR_PRESENTACION_EBR",
              tabla="ebr_presentaciones_manual", registro_id=row_id)
    conn.commit()
    return jsonify({"ok": True, "eliminado": True})


def _presentaciones_manuales(conn, ebr_id):
    """Presentaciones agregadas/editadas a mano (ebr_presentaciones_manual). Tienen `id`
    y `fuente='manual'` → la UI permite editarlas/borrarlas. Estado 'Programado (manual)'.

    El RENDIMIENTO va en vivo (Sebastián 16-ago: *"es el número que dice si el envasado va
    bien"*): antes la columna quedaba vacía hasta el cierre, o sea que el dato aparecía
    cuando ya no servía para decidir nada. Se calcula contra el granel que entró a la orden:
    unidades registradas ÷ (granel ÷ volumen del frasco).

    ⚠ Sólo con UNA presentación. Con varias, el granel se reparte entre ellas y atribuirlo
    entero a cada una daría rendimientos inventados -- la misma regla que ya usa el teórico
    del legajo: si no se puede repartir bien, no se reparte (M8/M124).
    """
    try:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT id, presentacion, cliente, volumen_ml, envase_codigo, unidades, area, lote "
            "FROM ebr_presentaciones_manual WHERE ebr_id=? ORDER BY id", (ebr_id,)).fetchall()
    except Exception:
        return []

    granel_ml = None
    if len(rows) == 1:
        try:
            g = cur.execute(
                "SELECT ml_envasable, cantidad_objetivo_g, densidad_g_ml "
                "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
            if g:
                granel_ml = g["ml_envasable"]
                if not granel_ml and g["cantidad_objetivo_g"] and g["densidad_g_ml"]:
                    granel_ml = float(g["cantidad_objetivo_g"]) / float(g["densidad_g_ml"])
        except Exception as e:
            log.warning("rendimiento en vivo · no se pudo leer el granel de %s: %s", ebr_id, e)

    out = []
    for r in rows:
        uds = r["unidades"]; ml = r["volumen_ml"]
        teoricas = rend = None
        if granel_ml and ml and float(ml) > 0:
            teoricas = int(float(granel_ml) // float(ml))
            if teoricas and uds:
                rend = round(float(uds) / teoricas * 100, 2)
        out.append({
            "id": r["id"], "fuente": "manual",
            "presentacion": r["presentacion"] or "·", "cliente": r["cliente"] or "Animus DTC",
            "lote": r["lote"] or "", "unidades": uds, "area": r["area"] or "",
            "envase_codigo": r["envase_codigo"] or "", "volumen_ml": ml,
            "cantidad_ml": (uds * ml) if (uds and ml) else None,
            # `unidades_final` es lo que se confirma AL CERRAR: mientras el lote va en curso
            # se muestran las teóricas, que es contra lo que se compara el rendimiento.
            "unidades_final": teoricas, "rend_pct": rend,
            "estado": "Programado (manual)",
        })
    return out


# ════════════════════════════════════════════════════════════════════════════
# IPCs · In-Process Controls (specs en MBR + resultados en EBR)
# ════════════════════════════════════════════════════════════════════════════
# specs: pH, viscosidad, T°, apariencia, etc. con rangos de aceptación.
# resultados: medición real durante la ejecución del lote.
# Si un spec obligatorio queda sin medir o NO conforme, el endpoint
# /api/brd/ebr/<id>/completar (lo veremos abajo en la ampliación) bloquea.

def _spec_to_dict(row):
    return {
        "id": row["id"],
        "mbr_template_id": row["mbr_template_id"],
        "mbr_paso_id": row["mbr_paso_id"],
        "parametro": row["parametro"],
        "unidad": row["unidad"] or "",
        "valor_min": row["valor_min"],
        "valor_max": row["valor_max"],
        "metodo": row["metodo"] or "",
        "obligatorio": int(row["obligatorio"] or 0),
        "notas": row["notas"] or "",
    }


def _resultado_to_dict(row):
    return {
        "id": row["id"],
        "ebr_id": row["ebr_id"],
        "ipc_spec_id": row["ipc_spec_id"],
        "valor_medido": row["valor_medido"],
        "valor_texto": row["valor_texto"] or "",
        "conforme": row["conforme"],
        "medido_por": row["medido_por"],
        "medido_at_utc": row["medido_at_utc"],
        "qc_username": row["qc_username"] or "",
        "qc_e_sign_id": row["qc_e_sign_id"],
        "notas": row["notas"] or "",
    }


# ── /api/brd/mbr/<id>/ipc-specs · CRUD specs (solo en draft) ──────────────

@bp.route("/api/brd/mbr/<int:mbr_id>/ipc-specs", methods=["GET"])
def listar_ipc_specs(mbr_id):
    err = _require_login()
    if err:
        return err
    rows = get_db().execute(
        """SELECT id, mbr_template_id, mbr_paso_id, parametro, unidad,
                  valor_min, valor_max, metodo, obligatorio, notas
           FROM ipc_specs WHERE mbr_template_id = ? ORDER BY id""",
        (mbr_id,),
    ).fetchall()
    return jsonify({"items": [_spec_to_dict(r) for r in rows]})


@bp.route("/api/brd/mbr/<int:mbr_id>/ipc-specs", methods=["POST"])
def crear_ipc_spec(mbr_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute("SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "draft":
        return jsonify({"error": "solo se agregan specs IPC en MBR draft"}), 409

    body = request.get_json(silent=True) or {}
    parametro = (body.get("parametro") or "").strip()
    if not parametro:
        return jsonify({"error": "parametro requerido"}), 400

    def _f(v):
        try:
            return float(v) if v is not None and v != "" else None
        except (ValueError, TypeError):
            return None

    cur.execute(
        """INSERT INTO ipc_specs
             (mbr_template_id, mbr_paso_id, parametro, unidad,
              valor_min, valor_max, metodo, obligatorio, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (mbr_id,
         body.get("mbr_paso_id"),
         parametro,
         (body.get("unidad") or "").strip(),
         _f(body.get("valor_min")),
         _f(body.get("valor_max")),
         (body.get("metodo") or "").strip(),
         1 if body.get("obligatorio", 1) else 0,
         (body.get("notas") or "").strip()),
    )
    spec_id = cur.lastrowid
    conn.commit()
    return jsonify({"ok": True, "id": spec_id}), 201


@bp.route("/api/brd/mbr/<int:mbr_id>/ipc-specs/<int:spec_id>", methods=["DELETE"])
def borrar_ipc_spec(mbr_id, spec_id):
    err = _require_login()
    if err:
        return err
    conn = get_db()
    cur = conn.cursor()
    tpl = cur.execute("SELECT estado FROM mbr_templates WHERE id = ?", (mbr_id,)).fetchone()
    if not tpl:
        return jsonify({"error": "MBR no encontrado"}), 404
    if tpl["estado"] != "draft":
        return jsonify({"error": "solo se borran specs en MBR draft"}), 409
    cur.execute(
        "DELETE FROM ipc_specs WHERE id = ? AND mbr_template_id = ?",
        (spec_id, mbr_id),
    )
    if cur.rowcount == 0:
        return jsonify({"error": "spec no encontrado"}), 404
    conn.commit()
    return jsonify({"ok": True})


# ── /api/brd/ebr/<id>/ipc-resultados · reportar mediciones ────────────────

@bp.route("/api/brd/ebr/<int:ebr_id>/ipc-resultados", methods=["GET"])
def listar_ipc_resultados(ebr_id):
    err = _require_login()
    if err:
        return err
    # JOIN con specs para devolver detalle del parámetro
    rows = get_db().execute(
        """SELECT r.*, s.parametro AS spec_parametro, s.unidad AS spec_unidad,
                  s.valor_min AS spec_min, s.valor_max AS spec_max,
                  s.obligatorio AS spec_obligatorio
           FROM ipc_resultados r
           JOIN ipc_specs s ON s.id = r.ipc_spec_id
           WHERE r.ebr_id = ?
           ORDER BY r.medido_at_utc""",
        (ebr_id,),
    ).fetchall()
    items = []
    for r in rows:
        d = _resultado_to_dict(r)
        d["spec"] = {
            "parametro": r["spec_parametro"],
            "unidad": r["spec_unidad"] or "",
            "valor_min": r["spec_min"],
            "valor_max": r["spec_max"],
            "obligatorio": int(r["spec_obligatorio"] or 0),
        }
        items.append(d)
    return jsonify({"items": items})


@bp.route("/api/brd/ebr/<int:ebr_id>/ipc-resultados", methods=["POST"])
def reportar_ipc_resultado(ebr_id):
    """Operario reporta medición de un IPC. Calcula conforme automáticamente
    si hay rango numérico; para parámetros cualitativos QC debe firmar después."""
    # SEC-FIX · 21-may-2026 · solo ejecutores BRD (planta/admin/QC)
    # Antes: cualquier compras_user podía falsificar IPCs
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    spec_id = body.get("ipc_spec_id")
    if not spec_id:
        return jsonify({"error": "ipc_spec_id requerido"}), 400

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, mbr_template_id FROM ebr_ejecuciones WHERE id = ?",
        (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    spec = cur.execute(
        "SELECT * FROM ipc_specs WHERE id = ? AND mbr_template_id = ?",
        (int(spec_id), ebr["mbr_template_id"]),
    ).fetchone()
    if not spec:
        return jsonify({"error": "spec no pertenece al MBR del EBR"}), 400

    # Validar valor_medido vs rango si aplica
    valor = body.get("valor_medido")
    valor_texto = (body.get("valor_texto") or "").strip()
    try:
        valor_f = float(valor) if valor is not None and valor != "" else None
    except (ValueError, TypeError):
        return jsonify({"error": "valor_medido inválido"}), 400

    if body.get("no_aplica"):
        # "No aplica" (conforme=2): el control no corresponde a este producto.
        # No bloquea la liberación y NO abre desviación.
        conforme = 2
        valor_f = None
        valor_texto = valor_texto or "No aplica"
    elif spec["valor_min"] is not None or spec["valor_max"] is not None:
        if valor_f is None:
            return jsonify({"error": "valor_medido requerido (spec numérico)"}), 400
        conforme = 1
        if spec["valor_min"] is not None and valor_f < float(spec["valor_min"]):
            conforme = 0
        if spec["valor_max"] is not None and valor_f > float(spec["valor_max"]):
            conforme = 0
    else:
        # Cualitativo: pendiente de validación QC (NULL hasta que firme)
        conforme = body.get("conforme")
        if conforme is not None:
            conforme = 1 if conforme else 0

    user = session.get("compras_user", "")
    try:
        cur.execute(
            """INSERT INTO ipc_resultados
                 (ebr_id, ipc_spec_id, valor_medido, valor_texto, conforme,
                  medido_por, medido_at_utc, notas)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'utc'), ?)""",
            (ebr_id, int(spec_id), valor_f, valor_texto, conforme,
             user, (body.get("notas") or "").strip()),
        )
    except Exception as e:
        if "UNIQUE" in str(e):
            return jsonify({"error": "ya existe resultado para este spec en este EBR"}), 409
        raise
    rid = cur.lastrowid
    # Reemplazo MyBatch fase 2 · IPC NO conforme → abre desviación/CAPA
    # automática (aseguramiento) ligada a este resultado y al lote del EBR.
    # Deploy-safe: si la mig 203 (desviacion_id) o el helper no están, no rompe.
    desviacion = None
    if conforme == 0:
        try:
            lr = cur.execute("SELECT lote FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
            lote = (lr[0] if lr else '') or f'EBR{ebr_id}'
            _vis = valor_f if valor_f is not None else (valor_texto or '?')
            desc = (f"IPC fuera de especificación · lote {lote} (EBR #{ebr_id}) · "
                    f"{spec['parametro']} = {_vis} {spec['unidad'] or ''} "
                    f"(rango {spec['valor_min']}–{spec['valor_max']}). "
                    f"Desviación abierta automáticamente desde el EBR.")
            from blueprints.aseguramiento import crear_desviacion_auto
            cod, desv_id = crear_desviacion_auto(
                cur, tipo='proceso', descripcion=desc, lotes_afectados=lote,
                detectado_por=user, area_origen='Producción', impacto_producto=1)
            try:
                cur.execute("UPDATE ipc_resultados SET desviacion_id=? WHERE id=?", (desv_id, rid))
            except Exception:
                pass  # mig 203 aún no aplicada · enlace opcional
            desviacion = {"codigo": cod, "id": desv_id}
        except Exception as _ed:
            # FAIL-CLOSED (audit 3-jun): un IPC OOS DEBE quedar con su desviación.
            # Si la auto-desviación falla, NO persistir el resultado en silencio
            # (dejaría un OOS sin trazabilidad y el gate de liberación, que mira
            # desviaciones, no lo vería → liberaría producto no conforme).
            logging.getLogger('brd').error('auto-desviación IPC OOS fallo: %s', _ed)
            try:
                conn.rollback()
            except Exception:
                pass
            return jsonify({
                "error": "El IPC quedó fuera de especificación pero no se pudo "
                         "abrir la desviación automática. No se guardó el "
                         "resultado · reintentá o avisá a Calidad.",
                "codigo": "DESVIACION_AUTO_FALLO",
            }), 500
    conn.commit()
    audit_log(cur, usuario=user, accion="REPORTAR_IPC",
              tabla="ipc_resultados", registro_id=rid,
              despues={"ebr_id": ebr_id, "spec_id": spec_id,
                        "valor": valor_f, "conforme": conforme,
                        "desviacion": (desviacion or {}).get("codigo")})
    return jsonify({"ok": True, "id": rid, "conforme": conforme,
                     "desviacion": desviacion}), 201


# ════════════════════════════════════════════════════════════════════════════
# Equipment cleaning log (F6)
# ════════════════════════════════════════════════════════════════════════════

VALID_TIPO_LIMPIEZA = {"rutinaria", "profunda", "cambio_producto"}


def _cleaning_to_dict(row):
    return {
        "id": row["id"],
        "equipo_codigo": row["equipo_codigo"],
        "lote_anterior": row["lote_anterior"] or "",
        "lote_siguiente": row["lote_siguiente"] or "",
        "tipo_limpieza": row["tipo_limpieza"],
        "operario_username": row["operario_username"],
        "operario_e_sign_id": row["operario_e_sign_id"],
        "qc_username": row["qc_username"] or "",
        "qc_e_sign_id": row["qc_e_sign_id"],
        "visual_ok": row["visual_ok"],
        "iniciado_at_utc": row["iniciado_at_utc"],
        "completado_at_utc": row["completado_at_utc"],
        "observaciones": row["observaciones"] or "",
    }


@bp.route("/api/brd/ebr/<int:ebr_id>/ipc-estandar", methods=["GET", "POST"])
def reportar_ipc_estandar(ebr_id):
    """GET: lista los 5 controles ESTÁNDAR con su resultado (para el legajo).
    POST: registra/actualiza uno. Soporta 'No aplica' (conforme=2). Upsert por
    (ebr_id, control_codigo). No abre desviación.

    Body POST: {control_codigo, control_nombre?, valor_texto?, conforme?(bool),
                no_aplica?(bool), observaciones?}
    """
    if request.method == "GET":
        if not session.get("compras_user"):
            return jsonify({"error": "No autorizado"}), 401
        cur = get_db().cursor()
        est = {}
        try:
            for er in cur.execute(
                """SELECT r.control_codigo, COALESCE(r.valor_texto,''), r.conforme,
                          COALESCE(r.observaciones,''), COALESCE(r.medido_por,''),
                          COALESCE(r.medido_at_utc,''), COALESCE(d.codigo,''),
                          COALESCE(d.estado,'')
                   FROM ipc_estandar_resultados r
                   LEFT JOIN desviaciones d ON d.id = r.desviacion_id
                   WHERE r.ebr_id=?""",
                (ebr_id,),
            ).fetchall():
                est[er[0]] = er
        except Exception as _e:
            # Nunca mudo: un except que traga vuelve el legajo "sin controles", que es
            # indistinguible de la realidad (M4/M94).
            log.warning("ipc-estandar GET ebr=%s: %s", ebr_id, _e)
            est = {}
        items = []
        for cod, nom, uni in _ipc_estandar_ebr(cur, ebr_id):
            er = est.get(cod)
            items.append({
                "control_codigo": cod, "control_nombre": nom, "unidad": uni,
                "valor_texto": (er[1] if er else ""),
                "conforme": (int(er[2]) if er and er[2] is not None else None),
                "observaciones": (er[3] if er else ""),
                "medido_por": (er[4] if er else ""),
                "medido_at_utc": (er[5] if er else ""),
                "desviacion": (er[6] if er else ""),
                "desviacion_estado": (er[7] if er else ""),
            })
        return jsonify({"items": items})
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    cod = (body.get("control_codigo") or "").strip().lower()
    # Se aceptan los controles de la fase del legajo Y los de fabricación: un legajo
    # viejo puede tener registrados los cinco de siempre, y rechazarlos ahora dejaría
    # sin poder corregir lo ya escrito (aditivo · M117).
    _de_fase = _ipc_estandar_ebr(get_db(), ebr_id)
    validos = {c[0]: c[1] for c in list(_de_fase) + list(IPC_ESTANDAR)}
    if cod not in validos:
        return jsonify({"error": "control_codigo inválido"}), 400
    nombre = (body.get("control_nombre") or validos[cod]).strip()[:120]
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, COALESCE(lote_codigo, lote, '') AS _lote "
        "FROM ebr_ejecuciones WHERE id = ?", (ebr_id,)
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    user = session.get("compras_user", "")
    valor_texto = (body.get("valor_texto") or "").strip()[:200]
    obs = (body.get("observaciones") or "").strip()[:300]
    if body.get("no_aplica"):
        conforme = 2
        valor_texto = valor_texto or "No aplica"
    else:
        conf = body.get("conforme")
        conforme = (1 if conf else 0) if conf is not None else None
    # EL QUE REGISTRA NO PUEDE APROBAR (Sebastián 29-jul · mig 400). En MyBatch la sección 5
    # la firma CALIDAD, y acá cualquier ejecutor podía anotar el valor Y declarar 'Cumple'
    # sobre su propia medición. Espeja la 2ª firma del material de envase (INV-14):
    #  · ANOTAR el valor (sin adjudicar) lo puede hacer quien mide;
    #  · ADJUDICAR (Cumple / No cumple / No aplica) es de quien VERIFICA por rol;
    #  · y nunca sobre su propia medición (regla de las 2 personas · GMP).
    # Los lotes DEMO- se caminan con una sola persona, igual que el despeje.
    _adjudica = (conforme is not None)
    _prev = None
    try:
        _prev = cur.execute(
            "SELECT COALESCE(medido_por,''), COALESCE(valor_texto,'') "
            "FROM ipc_estandar_resultados WHERE ebr_id=? AND control_codigo=?",
            (ebr_id, cod)).fetchone()
    except Exception as _e:
        log.warning("registro previo de %s no legible: %s", cod, _e)
    _es_demo_ipc = es_lote_demo(ebr["_lote"] or '')
    if _adjudica and not _es_demo_ipc:
        if not _batch_role_info(user).get("verifica"):
            return jsonify({
                "error": ("Declarar si un control CUMPLE es atribución del Analista o del Jefe "
                          "de Control de Calidad (y de Aseguramiento). Registrá el valor medido "
                          "y Calidad lo adjudica."),
                "codigo": "SOLO_CALIDAD_ADJUDICA",
            }), 403
        _midio = (_prev[0].strip() if _prev else '')
        if _midio and _midio == user:
            return jsonify({
                "error": ("No podés adjudicar tu propia medición: quien mide y quien declara "
                          "que cumple deben ser personas distintas (regla de las 2 personas · "
                          "GMP). Que lo adjudique otra persona de Calidad."),
                "codigo": "AUTOADJUDICACION_BLOQUEADA",
            }), 409
    # Adjudicar (Cumple / No cumple) SIN resultado dejaba la fila diciendo "pendiente" y
    # "✓" a la vez (M5: el número que se muestra es el que decide) — y una conformidad
    # firmada sobre un dato que no existe no es un registro. Se corta en el ORIGEN, no en
    # la vista: si se arregla sólo la pantalla, la base queda igual de rota (M115).
    # 'No aplica' sí es una respuesta completa en sí misma y no exige valor.
    if conforme in (0, 1) and not valor_texto:
        return jsonify({
            "error": ("Falta el resultado de %s. Un control no se puede declarar "
                      "%s sin el dato que lo respalda; si el control no corresponde "
                      "a este producto, marcalo 'No aplica'."
                      % (nombre, 'Cumple' if conforme == 1 else 'No cumple')),
            "codigo": "IPC_ESTANDAR_SIN_RESULTADO",
        }), 400
    # Reclamar la desviación ABIERTA de un registro previo del MISMO control: re-registrar
    # el valor (corregir un tipeo) no puede abrir una segunda desviación del mismo hecho.
    _desv_previa = None
    try:
        _dp = cur.execute(
            """SELECT r.desviacion_id FROM ipc_estandar_resultados r
                 JOIN desviaciones d ON d.id = r.desviacion_id
                WHERE r.ebr_id=? AND r.control_codigo=?
                  AND COALESCE(d.estado,'') NOT IN ('cerrada','anulada')""",
            (ebr_id, cod)).fetchone()
        _desv_previa = _dp[0] if _dp else None
    except Exception as _e:
        log.warning("desviacion previa de %s no legible: %s", cod, _e)
    # Upsert por (ebr_id, control_codigo): borra el previo y reinserta.
    cur.execute(
        "DELETE FROM ipc_estandar_resultados WHERE ebr_id=? AND control_codigo=?",
        (ebr_id, cod),
    )
    # QUIÉN MIDIÓ se conserva; el que adjudica va en su propia columna (mig 400). Antes el
    # upsert pisaba `medido_por` con quien adjudicaba y se perdía al medidor — sin ese dato
    # la regla de las 2 personas no se puede sostener ni auditar.
    _medio_por = (_prev[0].strip() if (_prev and _prev[0]) else '') or (user if not _adjudica else '')
    _adj_por = user if _adjudica else ''
    cur.execute(
        """INSERT INTO ipc_estandar_resultados
             (ebr_id, control_codigo, control_nombre, valor_texto, conforme,
              observaciones, medido_por, medido_at_utc, desviacion_id,
              adjudicado_por, adjudicado_at_utc)
           VALUES (?,?,?,?,?,?,?, datetime('now','utc'), ?, ?,
                   CASE WHEN ?='' THEN '' ELSE datetime('now','utc') END)""",
        (ebr_id, cod, nombre, valor_texto, conforme, obs, _medio_por, _desv_previa,
         _adj_por, _adj_por),
    )
    rid = cur.lastrowid
    # El MISMO hecho físico (pH fuera de spec) tiene que abrir desviación por las DOS
    # vías: si sólo la abre el camino del MBR, el gate de liberación —que mira
    # desviaciones— no ve nada y el lote sale (M45: un control que vive en dos caminos
    # y sólo uno lo aplica). Espeja `reportar_ipc_resultado`, incluido el fail-closed.
    desviacion = None
    if conforme == 0 and not _desv_previa:
        try:
            lr = cur.execute("SELECT lote FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
            lote = (lr[0] if lr else '') or f'EBR{ebr_id}'
            desc = (f"Control en proceso estándar NO CONFORME · lote {lote} (EBR #{ebr_id}) · "
                    f"{nombre} = {valor_texto}. "
                    + (f"Observación: {obs}. " if obs else "")
                    + "Desviación abierta automáticamente desde el legajo.")
            try:
                from blueprints.aseguramiento import crear_desviacion_auto
            except Exception:
                from api.blueprints.aseguramiento import crear_desviacion_auto
            _cod_desv, _desv_id = crear_desviacion_auto(
                cur, tipo='proceso', descripcion=desc, lotes_afectados=lote,
                detectado_por=user, area_origen='Producción', impacto_producto=1)
            cur.execute("UPDATE ipc_estandar_resultados SET desviacion_id=? WHERE id=?",
                        (_desv_id, rid))
            desviacion = {"codigo": _cod_desv, "id": _desv_id}
        except Exception as _ed:
            # FAIL-CLOSED (igual que el IPC del MBR): un NO CONFORME sin su desviación
            # es un OOS sin trazabilidad, y el gate de liberación no lo vería.
            log.error('auto-desviación IPC estándar %s falló: %s', cod, _ed)
            try:
                conn.rollback()
            except Exception:
                pass
            return jsonify({
                "error": ("El control quedó NO CONFORME pero no se pudo abrir la "
                          "desviación automática. No se guardó el resultado · "
                          "reintentá o avisá a Calidad."),
                "codigo": "DESVIACION_AUTO_FALLO",
            }), 500
    elif conforme == 0 and _desv_previa:
        try:
            _c = cur.execute("SELECT codigo FROM desviaciones WHERE id=?",
                             (_desv_previa,)).fetchone()
            desviacion = {"codigo": (_c[0] if _c else ''), "id": _desv_previa,
                          "reusada": True}
        except Exception:
            desviacion = {"codigo": '', "id": _desv_previa, "reusada": True}
    try:
        audit_log(cur, usuario=user, accion='IPC_ESTANDAR_REGISTRAR',
                  tabla='ipc_estandar_resultados', registro_id=rid,
                  despues={'ebr_id': ebr_id, 'control': cod, 'conforme': conforme,
                           'valor': valor_texto,
                           'desviacion': (desviacion or {}).get('codigo')})
    except Exception:
        pass
    conn.commit()
    estado_txt = {1: 'Cumple', 0: 'No cumple', 2: 'No aplica'}.get(conforme, 'pendiente')
    return jsonify({"ok": True, "id": rid, "conforme": conforme, "estado": estado_txt,
                    "desviacion": desviacion})


@bp.route("/api/brd/cleaning", methods=["POST"])
def reportar_cleaning():
    """Operario reporta INICIO de limpieza de un equipo."""
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    equipo = (body.get("equipo_codigo") or "").strip()
    if not equipo:
        return jsonify({"error": "equipo_codigo requerido"}), 400
    tipo = (body.get("tipo_limpieza") or "rutinaria").strip().lower()
    if tipo not in VALID_TIPO_LIMPIEZA:
        return jsonify({"error": f"tipo_limpieza inválido · use {sorted(VALID_TIPO_LIMPIEZA)}"}), 400

    user = session.get("compras_user", "")
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO equipo_limpieza_log
             (equipo_codigo, lote_anterior, lote_siguiente, tipo_limpieza,
              operario_username, iniciado_at_utc, observaciones)
           VALUES (?, ?, ?, ?, ?, datetime('now', 'utc'), ?)""",
        (equipo,
         (body.get("lote_anterior") or "").strip(),
         (body.get("lote_siguiente") or "").strip(),
         tipo, user,
         (body.get("observaciones") or "").strip()),
    )
    cl_id = cur.lastrowid
    conn.commit()
    audit_log(cur, usuario=user, accion="INICIAR_LIMPIEZA",
              tabla="equipo_limpieza_log", registro_id=cl_id,
              despues={"equipo": equipo, "tipo": tipo})
    return jsonify({"ok": True, "id": cl_id}), 201


@bp.route("/api/brd/cleaning/<int:cl_id>/completar", methods=["POST"])
def completar_cleaning(cl_id):
    """Operario marca limpieza como completada con e-sign opcional."""
    err = _require_login()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT operario_username, completado_at_utc FROM equipo_limpieza_log WHERE id = ?",
        (cl_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "cleaning log no encontrado"}), 404
    if row["completado_at_utc"]:
        return jsonify({"error": "limpieza ya completada"}), 409

    user = session.get("compras_user", "")
    # Validar e-sign si se pasa
    if signature_id:
        if not _validar_signature(
            cur, signature_id, record_table="equipo_limpieza_log",
            record_id=cl_id, meaning="ejecuta", signer_username=user,
        ):
            return jsonify({"error": "signature_id inválido"}), 400

    cur.execute(
        """UPDATE equipo_limpieza_log
             SET completado_at_utc = datetime('now', 'utc'),
                 operario_e_sign_id = ?
           WHERE id = ?""",
        (int(signature_id) if signature_id else None, cl_id),
    )
    # La limpieza de un equipo es un registro GMP: es lo que sostiene que no hubo contaminación
    # cruzada entre lotes. Esta era la ÚNICA acción de cierre del batch record que mutaba sin
    # dejar rastro -- lo encontró el barrido del 17-ago recorriendo las funciones que liberan,
    # completan o aprueban. Sin el audit no se puede contestar quién marcó esa limpieza, que es
    # exactamente lo que pregunta una auditoría (M22 · el audit va ANTES del commit).
    audit_log(cur, usuario=user, accion="COMPLETAR_LIMPIEZA_EQUIPO",
              tabla="equipo_limpieza_log", registro_id=cl_id,
              despues={"completado_por": user,
                       "con_firma": bool(signature_id),
                       "operario_asignado": (row["operario_username"] or "")})
    conn.commit()
    return jsonify({"ok": True})


@bp.route("/api/brd/cleaning/<int:cl_id>/validar", methods=["POST"])
def validar_cleaning_qc(cl_id):
    """QC firma inspección visual y marca visual_ok=1/0."""
    err = _require_qa_or_admin()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    visual_ok = body.get("visual_ok")
    signature_id = body.get("signature_id")
    if visual_ok is None:
        return jsonify({"error": "visual_ok requerido (1=conforme, 0=no)"}), 400
    if not signature_id:
        return jsonify({
            "error": "signature_id requerido · meaning='supervisa' record_table='equipo_limpieza_log'",
        }), 400

    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT qc_e_sign_id FROM equipo_limpieza_log WHERE id = ?",
        (cl_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "cleaning log no encontrado"}), 404
    if row["qc_e_sign_id"]:
        return jsonify({"error": "ya validado por QC (inmutable)"}), 409

    user = session.get("compras_user", "")
    if not _validar_signature(
        cur, signature_id, record_table="equipo_limpieza_log",
        record_id=cl_id, meaning="supervisa", signer_username=user,
    ):
        return jsonify({"error": "signature_id no corresponde a 'supervisa' tuya en este log"}), 400

    cur.execute(
        """UPDATE equipo_limpieza_log
             SET qc_username = ?,
                 qc_e_sign_id = ?,
                 visual_ok = ?
           WHERE id = ?""",
        (user, int(signature_id), 1 if visual_ok else 0, cl_id),
    )
    conn.commit()
    audit_log(cur, usuario=user, accion="VALIDAR_LIMPIEZA_QC",
              tabla="equipo_limpieza_log", registro_id=cl_id,
              despues={"visual_ok": visual_ok, "signature_id": signature_id})
    return jsonify({"ok": True, "visual_ok": int(bool(visual_ok))})


@bp.route("/api/brd/cleaning", methods=["GET"])
def listar_cleaning():
    err = _require_login()
    if err:
        return err
    equipo = (request.args.get("equipo") or "").strip()
    where, params = [], []
    if equipo:
        where.append("equipo_codigo = ?")
        params.append(equipo)
    sql = """SELECT * FROM equipo_limpieza_log"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY iniciado_at_utc DESC LIMIT 200"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify({"items": [_cleaning_to_dict(r) for r in rows]})


@bp.route("/api/brd/cleaning/equipo/<equipo>/ultima", methods=["GET"])
def ultima_cleaning(equipo):
    """Última limpieza del equipo (validada o no). Útil para wizard que
    decide si el equipo puede usarse en un lote nuevo."""
    err = _require_login()
    if err:
        return err
    row = get_db().execute(
        """SELECT * FROM equipo_limpieza_log
           WHERE equipo_codigo = ?
           ORDER BY iniciado_at_utc DESC LIMIT 1""",
        (equipo,),
    ).fetchone()
    if not row:
        return jsonify({"equipo_codigo": equipo, "ultima": None,
                         "apto_para_uso": False,
                         "razon": "sin registros de limpieza"})
    apto = (row["completado_at_utc"] is not None
             and int(row["visual_ok"] or 0) == 1)
    return jsonify({
        "equipo_codigo": equipo,
        "ultima": _cleaning_to_dict(row),
        "apto_para_uso": apto,
        "razon": "" if apto else "limpieza pendiente o no validada por QC",
    })


# ════════════════════════════════════════════════════════════════════════════
# PDF maestro auditable EBR (F8)
# ════════════════════════════════════════════════════════════════════════════

def _safe_pdf(text):
    """fpdf2 latin-1 compatible (replica de api/comprobante_pago._safe)."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    repl = {"·": "-", "–": "-", "…": "...", "“": '"', "”": '"',
            "‘": "'", "’": "'", "•": "·", "→": "->", "≥": ">=", "≤": "<="}
    for k, v in repl.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


@bp.route("/api/brd/ebr/<int:ebr_id>/pdf", methods=["GET"])
def pdf_ebr(ebr_id):
    """Genera el PDF maestro del EBR para auditoría INVIMA / archivo regulatorio.

    Estructura:
      1. Header: producto, lote, MBR version, estado
      2. Identificación: iniciado/completado/liberado por con timestamps
      3. Reconciliación cantidad objetivo vs real + yield_pct
      4. Tabla de pasos ejecutados con operarios + e-signature IDs
      5. Tabla de IPCs reportados con conformidad
      6. Tabla de firmas electrónicas asociadas (de e_signatures)
      7. Footer: hash SHA256 del cuerpo + timestamp de generación
    """
    err = _require_login()
    if err:
        return err

    import hashlib
    import io
    from datetime import datetime, timezone
    from flask import send_file
    try:
        from fpdf import FPDF
    except ImportError:
        return jsonify({"error": "fpdf2 no instalado · agregar a requirements.txt"}), 500

    conn = get_db()
    ebr = conn.execute("SELECT * FROM ebr_ejecuciones WHERE id = ?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404

    mbr = conn.execute(
        "SELECT producto_nombre, version, lote_size_g FROM mbr_templates WHERE id = ?",
        (ebr["mbr_template_id"],),
    ).fetchone()
    pasos = conn.execute(
        "SELECT * FROM ebr_pasos_ejecutados WHERE ebr_id = ? ORDER BY orden",
        (ebr_id,),
    ).fetchall()
    ipcs = conn.execute(
        """SELECT r.*, s.parametro AS p, s.unidad AS u,
                  s.valor_min AS vmin, s.valor_max AS vmax
           FROM ipc_resultados r JOIN ipc_specs s ON s.id = r.ipc_spec_id
           WHERE r.ebr_id = ?
           ORDER BY r.medido_at_utc""",
        (ebr_id,),
    ).fetchall()
    # Audit 3-jun · el legajo debe incluir TODAS las estaciones (no solo pasos/
    # IPC): pesajes con 2ª firma, conciliación de material, artes/codificación y
    # observaciones. Deploy-safe: si una tabla no existe, queda lista vacía.
    def _q(sql, *p):
        try:
            return conn.execute(sql, p).fetchall()
        except Exception as _e:
            # Nunca mudo (M4/M94): si una sección del legajo desaparece del PDF, el
            # documento archivado se ve completo y no lo es. Deploy-safe, pero con rastro.
            log.warning("PDF EBR %s · sección omitida por error de consulta: %s", ebr_id, _e)
            return []
    pesajes = _q(
        "SELECT p.material_id, p.material_nombre, p.cantidad_teorica_g, p.cantidad_real_g, "
        "p.delta_g, p.delta_pct, p.lote_mp, p.pesado_por, p.verificado_por, p.verificado_at_utc, "
        "COALESCE(mm.nombre_inci,'') AS nombre_inci "
        "FROM ebr_pesajes p LEFT JOIN maestro_mps mm ON mm.codigo_mp=p.material_id "
        "WHERE p.ebr_id=? ORDER BY p.id", ebr_id)
    concil = _q(
        "SELECT tipo, material_nombre, lote_material, cant_requerida, cant_recibida, "
        "cant_devuelta, cant_utilizada, registrado_por FROM ebr_conciliacion_material "
        "WHERE ebr_id=? ORDER BY id", ebr_id)
    artes = _q(
        "SELECT descripcion, codigo_lote, codigo_vencimiento, aprobado_por, "
        "aprobado_at_utc FROM ebr_artes_codificacion WHERE ebr_id=? ORDER BY id", ebr_id)
    observs = _q(
        "SELECT descripcion, registrado_por, registrado_at_utc "
        "FROM ebr_observaciones WHERE ebr_id=? ORDER BY id", ebr_id)
    # MyBatch ①②⑦ · precauciones, despeje, registros físicos (audit 3-jun)
    precs = _q("SELECT tipo, descripcion, registrado_por FROM ebr_precauciones "
               "WHERE ebr_id=? ORDER BY id", ebr_id)
    despejes = _q("SELECT area_limpia, sin_producto_anterior, equipos_limpios, "
                  "documentacion_ok, conforme, observaciones, realizado_por, "
                  "realizado_at_utc FROM ebr_despeje_linea WHERE ebr_id=? ORDER BY id", ebr_id)

    # Despeje GRANULAR por ítem (13 verificaciones × 2 etapas · Realizó/Verificó · MyBatch §2/§4 · 25-jun)
    def _despeje_items_pdf(etapa):
        # el PDF es el documento que se archiva: usa el MISMO resolvedor que la pantalla, o el
        # papel diría una cosa y el sistema otra
        return [(f['texto'], f['cumple'], f['registrado_por'], f['verificado_por'])
                for f in despeje_checklist(conn, ebr_id, etapa)]
    despeje_gran = [("Dispensación", _despeje_items_pdf("dispensacion")),
                    ("Fabricación", _despeje_items_pdf("fabricacion"))]

    regfis = _q("SELECT descripcion, archivo_nombre, registrado_por, registrado_at_utc "
                "FROM ebr_registros_fisicos WHERE ebr_id=? ORDER BY id", ebr_id)
    firmas = conn.execute(
        """SELECT meaning, signer_username, signer_full_name, signer_cedula,
                  signer_cargo, signed_at_utc, comment
           FROM e_signatures
           WHERE (record_table='ebr_ejecuciones' AND record_id=?)
              OR (record_table='ebr_pasos_ejecutados' AND record_id IN
                  (SELECT CAST(id AS TEXT) FROM ebr_pasos_ejecutados WHERE ebr_id=?))
              OR (record_table='ipc_resultados' AND record_id IN
                  (SELECT CAST(id AS TEXT) FROM ipc_resultados WHERE ebr_id=?))
              OR (record_table='ebr_pesajes' AND record_id IN
                  (SELECT CAST(id AS TEXT) FROM ebr_pesajes WHERE ebr_id=?))
              OR (record_table='ebr_pesajes' AND record_id LIKE ? )
              OR (record_table='ebr_artes_codificacion' AND record_id IN
                  (SELECT CAST(id AS TEXT) FROM ebr_artes_codificacion WHERE ebr_id=?))
           ORDER BY signed_at_utc""",
        (str(ebr_id), ebr_id, ebr_id, ebr_id, f"{ebr_id}:%", ebr_id),
    ).fetchall()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header · banda de marca violeta (premium · consistente con los rótulos HTML)
    pdf.set_fill_color(109, 40, 217)            # violeta de marca ANIMUS
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 7, _safe_pdf("ESPAGIRIA Laboratorio SAS  ·  ANIMUS Lab"),
             new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.set_fill_color(245, 243, 255)           # pale violeta
    pdf.set_text_color(76, 29, 149)             # violeta oscuro
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, _safe_pdf(f"Executed Batch Record  ·  Lote {ebr['lote']}"),
             new_x="LMARGIN", new_y="NEXT", align="C", fill=True)
    pdf.set_text_color(60, 60, 67)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, _safe_pdf(
        f"Producto: {mbr['producto_nombre']}  ·  MBR v{ebr['mbr_version']}  ·  Estado: {ebr['estado'].upper()}"),
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)

    # Identificación
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _safe_pdf("1. Identificación del lote"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    # Aprobación de la ORDEN (mig 393) · va PRIMERO porque es lo primero que pasa:
    # se autoriza, se le entrega al operario, y recién ahí empieza el proceso. Que
    # falte se imprime igual: un renglón vacío en el legajo archivado es el hallazgo.
    try:
        _ap_por = ebr["aprobada_orden_por"] or ""
        _ap_at = ebr["aprobada_orden_at_utc"] or ""
        _ap_rol = ebr["aprobada_orden_rol"] or ""
        _ap_sig = ebr["aprobada_orden_signature_id"]
    except Exception:
        _ap_por = _ap_at = _ap_rol = ""
        _ap_sig = None
    if _ap_por:
        pdf.cell(0, 5, _safe_pdf(
            f"Orden aprobada por: {_ap_por}"
            + (f" ({_ap_rol})" if _ap_rol else "")
            + f"  ·  {_ap_at} UTC"
            + (f"  ·  firma e-sig #{_ap_sig}" if _ap_sig else "")),
                 new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 5, _safe_pdf("Orden aprobada por: SIN APROBAR"),
                 new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _safe_pdf(f"Iniciado por: {ebr['iniciado_por']}  ·  {ebr['iniciado_at_utc']} UTC"),
             new_x="LMARGIN", new_y="NEXT")
    if ebr["completado_at_utc"]:
        pdf.cell(0, 5, _safe_pdf(f"Completado: {ebr['completado_at_utc']} UTC"),
                 new_x="LMARGIN", new_y="NEXT")
    if ebr["liberado_at_utc"]:
        pdf.cell(0, 5, _safe_pdf(
            f"Liberado por: {ebr['liberado_por']}  ·  {ebr['liberado_at_utc']} UTC  ·  "
            f"firma e-sig #{ebr['liberado_signature_id']}"),
                 new_x="LMARGIN", new_y="NEXT")
    if ebr["rechazado_motivo"]:
        pdf.cell(0, 5, _safe_pdf(f"RECHAZADO · motivo: {ebr['rechazado_motivo']}"),
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Reconciliación
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _safe_pdf("2. Reconciliación cantidad"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    obj = ebr["cantidad_objetivo_g"]
    real = ebr["cantidad_real_g"]
    yld = ebr["yield_pct"]
    # FIX 28-jul · esto daba 500 en el PDF -el documento regulado- cuando había
    # cantidad real SIN yield: `yield_pct` queda en NULL si el objetivo es 0
    # (brd.py:4304 `... if ebr["cantidad_objetivo_g"] else None`), y formatear None
    # con `:.2f` revienta. Un dato faltante se imprime como faltante, no tumba el
    # legajo entero (M12a: formatear None es un 500 seguro, no un caso raro).
    def _num(v, suf=""):
        return f"{v:,.2f}{suf}" if v is not None else "-"

    pdf.cell(0, 5, _safe_pdf(
        f"Objetivo: {_num(obj, ' g')}   ·   Real: "
        + (f"{_num(real, ' g')}   ·   Yield: {_num(yld, ' %')}" if real is not None else "pendiente")),
        new_x="LMARGIN", new_y="NEXT")
    # Batch C · rendimiento por unidades (Envasado/Acondicionamiento)
    try:
        _uds_t = ebr["unidades_teoricas"]; _uds_b = ebr["unidades_buenas_real"]
        _yld_u = ebr["yield_uds_pct"]
    except Exception:
        _uds_t = _uds_b = _yld_u = None
    if _uds_b is not None or _yld_u is not None:
        pdf.cell(0, 5, _safe_pdf(
            f"Unidades buenas: {_uds_b or 0:,.0f}   ·   teóricas: {_uds_t or 0:,.0f}"
            + (f"   ·   Yield uds: {_yld_u:.2f} %" if _yld_u is not None else "")),
            new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def _line(text, h=5, font_size=9, italic=False):
        """multi_cell que siempre arranca al margen izquierdo (evita FPDFException)."""
        pdf.set_x(pdf.l_margin)
        if italic:
            pdf.set_font("Helvetica", "I", font_size)
        else:
            pdf.set_font("Helvetica", "", font_size)
        pdf.multi_cell(0, h, _safe_pdf(text))

    # Pasos ejecutados (formato lista)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _safe_pdf(f"3. Pasos ejecutados ({len(pasos)})"),
             new_x="LMARGIN", new_y="NEXT")
    for p in pasos:
        sig_str = f"#{p['e_sign_id']}" if p["e_sign_id"] else "-"
        if p["qc_e_sign_id"]:
            sig_str += f" QC#{p['qc_e_sign_id']}"
        _line(f"Paso {p['orden']}: {p['descripcion']}", h=5, font_size=9)
        _line(
            f"   operario: {p['operario_username'] or '-'}  "
            f"completado: {(p['completado_at_utc'] or '-')[:19]} UTC  "
            f"e-sign: {sig_str}",
            h=4, font_size=8,
        )
        if p["observaciones"]:
            _line(f"   obs: {p['observaciones']}", h=4, font_size=8, italic=True)
    pdf.ln(2)

    # IPCs (formato lista)
    if ipcs:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4. In-Process Controls ({len(ipcs)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for ipc in ipcs:
            conf = "Conforme" if ipc["conforme"] == 1 else ("NO conforme" if ipc["conforme"] == 0 else "pendiente")
            rango = ""
            if ipc["vmin"] is not None or ipc["vmax"] is not None:
                rango = f" [rango: {ipc['vmin']} - {ipc['vmax']} {ipc['u'] or ''}]"
            _line(
                f"{ipc['p']}: {ipc['valor_medido']} {ipc['u'] or ''}"
                f"{rango}  ·  {conf}  ·  {ipc['medido_por']}  ·  "
                f"{(ipc['medido_at_utc'] or '')[:19]} UTC",
                h=5, font_size=9,
            )
        pdf.ln(2)

    # 4-bis · Controles en proceso ESTÁNDAR (29-jul). La sección 4 de arriba imprime sólo
    # los IPC del MBR y hoy NINGÚN MBR define specs → el legajo archivado salía SIN un
    # solo control en proceso, aunque en pantalla estuvieran registrados. Un bloque que
    # sólo vive en la pantalla no es un registro: el que ve la auditoría es este (INV-13).
    _ipc_est = _q(
        """SELECT r.control_nombre, COALESCE(r.valor_texto,''), r.conforme,
                  COALESCE(r.observaciones,''), COALESCE(r.medido_por,''),
                  COALESCE(r.medido_at_utc,''), COALESCE(d.codigo,''), COALESCE(d.estado,'')
             FROM ipc_estandar_resultados r
             LEFT JOIN desviaciones d ON d.id = r.desviacion_id
            WHERE r.ebr_id = ? ORDER BY r.id""",
        ebr_id)
    if _ipc_est:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4-bis. Controles en proceso estándar ({len(_ipc_est)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for _c in _ipc_est:
            _cf = {1: "Cumple", 0: "NO CUMPLE", 2: "No aplica"}.get(_c[2], "sin adjudicar")
            _ln = (f"{_c[0]}: {_c[1] or '-'}  ·  {_cf}  ·  {_c[4] or '-'}  ·  "
                   f"{(_c[5] or '')[:19]} UTC")
            if _c[6]:
                _ln += f"  ·  desviación {_c[6]} ({_c[7] or 'abierta'})"
            _line(_ln, h=5, font_size=9)
            if _c[3]:
                _line(f"   obs: {_c[3]}", h=4, font_size=8, italic=True)
        pdf.ln(2)

    # Pesajes de materias primas (con 2ª firma de verificación)
    if pesajes:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4b. Pesajes de materias primas ({len(pesajes)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for w in pesajes:
            dp = w["delta_pct"]
            dp_s = f"{dp:+.2f}%" if dp is not None else "-"
            verif = (f"verificó: {w['verificado_por']} ({(w['verificado_at_utc'] or '')[:19]} UTC)"
                     if w["verificado_por"] else "SIN 2ª firma")
            # UI por INCI (regulado · INCI + comercial para trazabilidad)
            _nm = w['nombre_inci'] or w['material_nombre'] or ''
            if w['nombre_inci'] and w['material_nombre'] and w['nombre_inci'] != w['material_nombre']:
                _nm = f"{w['nombre_inci']} ({w['material_nombre']})"
            _line(
                f"{w['material_id']} {_nm}: teórico "
                f"{w['cantidad_teorica_g']} g · real {w['cantidad_real_g']} g · "
                f"delta {w['delta_g']} g ({dp_s}) · lote MP {w['lote_mp'] or '-'}",
                h=5, font_size=9)
            _line(f"   pesó: {w['pesado_por'] or '-'}  ·  {verif}", h=4, font_size=8)
        pdf.ln(2)

    # Conciliación de material de envase/empaque
    if concil:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4c. Conciliación de material ({len(concil)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for m in concil:
            _line(
                f"[{m['tipo']}] {m['material_nombre']} (lote {m['lote_material'] or '-'}): "
                f"requerida {m['cant_requerida']} · recibida {m['cant_recibida']} · "
                f"devuelta {m['cant_devuelta']} · utilizada {m['cant_utilizada']}  ·  "
                f"{m['registrado_por'] or '-'}",
                h=5, font_size=9)
        pdf.ln(2)

    # Material de envase del legajo · sección 3 de MyBatch: qué se pidió, qué ENTREGARON,
    # quién lo recibió y quién lo VERIFICÓ (las dos firmas). Si no está acá, la regla de
    # las 2 personas no se puede auditar sobre el papel.
    try:
        _mats_pdf = _materiales_envase_manuales(conn, ebr_id)
    except Exception as _e:
        log.warning("PDF ebr=%s sin materiales de envase: %s", ebr_id, _e)
        _mats_pdf = []
    if _mats_pdf:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4c-ter. Material de envase recibido ({len(_mats_pdf)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for m in _mats_pdf:
            def _q(v):
                return f"{v:,.0f}" if v is not None else "-"

            _falta = (f"  [FALTARON {m['faltante_entrega']:,.0f}]"
                      if m.get("faltante_entrega") else "")
            _line(
                f"{m['material']} (lote {m['lote_material'] or '-'}): "
                f"requerida {_q(m['requerida'])} · recibida {_q(m['recibida'])}{_falta}",
                h=5, font_size=9)
            _line(
                f"   Recibido por: {m['recibido_por'] or 'SIN REGISTRAR'}"
                + (f" ({m['recibido_at_utc'][:16]} UTC)" if m["recibido_at_utc"] else "")
                + f"   ·   Verificado por: {m['verificado_por'] or 'SIN VERIFICAR'}"
                + (f" ({m['verificado_at_utc'][:16]} UTC)" if m["verificado_at_utc"] else ""),
                h=5, font_size=9)
        pdf.ln(2)

    # Conciliación del GRANEL (mig 392) · sólo envasado. Es la sección que contesta
    # "el granel que entró, ¿en qué terminó?" · si no está en el imprimible, no está
    # en el legajo que se archiva, que es el que ve la auditoría.
    try:
        _cg = _conciliacion_granel(conn, ebr_id)
    except Exception as _e:
        log.warning("PDF ebr=%s sin conciliación de granel: %s", ebr_id, _e)
        _cg = None
    if _cg and _cg.get("aplica"):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf("4c-bis. Conciliación del granel"),
                 new_x="LMARGIN", new_y="NEXT")

        def _ml(v):
            return f"{v:,.2f} mL" if v is not None else "-"

        _line(f"Granel disponible: {_ml(_cg['disponible_ml'])}", h=5, font_size=9)
        _det = " · ".join(
            f"{p['codigo']} {p['unidades']:,.0f} x {p['volumen_ml']:,.2f} mL"
            for p in _cg["presentaciones"]) or "sin unidades registradas"
        _line(f"Envasado: {_ml(_cg['envasado_ml'])}  ({_det})", h=5, font_size=9)
        if _cg["remanente_g"] is not None:
            _line(
                f"Remanente: {_ml(_cg['remanente_ml'])}  "
                f"({_cg['remanente_g']:,.1f} g pesados · "
                f"{_REMANENTE_DESTINOS.get(_cg['remanente_destino'], _cg['remanente_destino'] or '-')})"
                + (f" · declarado por {_cg['remanente_por']}" if _cg["remanente_por"] else ""),
                h=5, font_size=9)
            if _cg["remanente_observaciones"]:
                _line(f"   Obs.: {_cg['remanente_observaciones']}", h=5, font_size=9, italic=True)
        else:
            _line("Remanente: SIN DECLARAR", h=5, font_size=9)
        _dif = _ml(_cg["diferencia_ml"])
        if _cg["diferencia_pct"] is not None:
            _dif += f" ({_cg['diferencia_pct']:,.2f} %)"
        _line(f"Diferencia sin explicar: {_dif}   ·   tolerancia {_cg['tolerancia_pct']:,.2f} %"
              + ("   [CONCILIADO]" if _cg["cuadra"] else "   [SIN CONCILIAR]"), h=5, font_size=9)
        pdf.ln(2)

    # Artes / codificación (acondicionamiento)
    if artes:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4d. Artes / codificación ({len(artes)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for a in artes:
            ap = (f"APROBADO por {a['aprobado_por']} ({(a['aprobado_at_utc'] or '')[:19]} UTC)"
                  if a["aprobado_por"] else "SIN aprobar")
            _line(
                f"{a['descripcion']} · cód. lote {a['codigo_lote'] or '-'} · "
                f"venc. {a['codigo_vencimiento'] or '-'}  ·  {ap}",
                h=5, font_size=9)
        pdf.ln(2)

    # Observaciones / bitácora
    if observs:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4e. Observaciones / bitácora ({len(observs)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for o in observs:
            _line(f"{(o['registrado_at_utc'] or '')[:19]} UTC · {o['registrado_por'] or '-'}: "
                  f"{o['descripcion']}", h=5, font_size=9)
        pdf.ln(2)

    # Precauciones y equipos (MyBatch ①)
    if precs:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4f. Precauciones y equipos ({len(precs)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for p in precs:
            _line(f"[{p['tipo']}] {p['descripcion']}  ·  {p['registrado_por'] or '-'}",
                  h=5, font_size=9)
        pdf.ln(2)

    # Despeje de línea (MyBatch ②)
    if despejes:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf("4g. Despeje de línea"), new_x="LMARGIN", new_y="NEXT")
        for dl in despejes:
            def _sn(v):
                return "SI" if v else "NO"
            _line(f"Área limpia: {_sn(dl['area_limpia'])} · Sin producto anterior: "
                  f"{_sn(dl['sin_producto_anterior'])} · Equipos limpios: "
                  f"{_sn(dl['equipos_limpios'])} · Documentación: {_sn(dl['documentacion_ok'])}",
                  h=5, font_size=9)
            _line(f"   Resultado: {'CONFORME' if dl['conforme'] else 'NO CONFORME'} · "
                  f"{dl['realizado_por'] or '-'} · {(dl['realizado_at_utc'] or '')[:19]} UTC"
                  + (f" · {dl['observaciones']}" if dl['observaciones'] else ""),
                  h=4, font_size=8)
        pdf.ln(2)

    # Despeje granular · 13 verificaciones × 2 etapas (MyBatch §2 Dispensación + §4 Fabricación)
    for _et_nom, _et_items in despeje_gran:
        if any(it[1] is not None for it in _et_items):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, _safe_pdf(f"Despeje de Línea · {_et_nom} (Realizó / Verificó)"),
                     new_x="LMARGIN", new_y="NEXT")
            for texto, cumple, reg_por, ver_por in _et_items:
                _est = "SI" if cumple == 1 else ("NO" if cumple == 0 else "-")
                _line(f"[{_est}] {texto}", h=4, font_size=8)
                _line(f"      Realizo: {reg_por or '-'}  |  Verifico: {ver_por or '-'}",
                      h=4, font_size=7)
            pdf.ln(2)

    # Registros físicos (MyBatch ⑦)
    if regfis:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"4h. Registros físicos ({len(regfis)})"),
                 new_x="LMARGIN", new_y="NEXT")
        for rg in regfis:
            _adj = f" [PDF: {rg['archivo_nombre']}]" if rg['archivo_nombre'] else ""
            _line(f"{rg['descripcion']}{_adj}  ·  {rg['registrado_por'] or '-'}",
                  h=5, font_size=9)
        pdf.ln(2)

    # Firmas electrónicas
    if firmas:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _safe_pdf(f"5. Firmas electrónicas ({len(firmas)}) · Part 11 §11.50"),
                 new_x="LMARGIN", new_y="NEXT")
        # Manifestación visible §11.50 · estampar la firma MANUSCRITA del firmante.
        import base64 as _b64f
        from io import BytesIO as _BIOf
        try:
            from blueprints.firmas import firma_img_de_usuario as _firma_img_u
        except Exception:
            from api.blueprints.firmas import firma_img_de_usuario as _firma_img_u
        _firma_cache_pdf = {}
        for f in firmas:
            _line(
                f"{f['signed_at_utc']} UTC · {f['meaning']} · "
                f"{f['signer_username']} ({f['signer_full_name'] or '-'}, "
                f"cédula {f['signer_cedula'] or '-'}, {f['signer_cargo'] or '-'})",
                h=5, font_size=9,
            )
            if f["comment"]:
                _line(f'   "{f["comment"]}"', h=4, font_size=8, italic=True)
            _su = f['signer_username'] or ''
            if _su not in _firma_cache_pdf:
                _firma_cache_pdf[_su] = _firma_img_u(conn, _su)
            _uri = _firma_cache_pdf[_su]
            if _uri and ',' in _uri:
                try:
                    _png = _b64f.b64decode(_uri.split(',', 1)[1])
                    pdf.image(_BIOf(_png), x=pdf.l_margin + 6, h=9)
                    pdf.ln(2)
                except Exception:
                    pass

    # 6. Disposición del lote / Certificado de liberación
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, _safe_pdf("6. Disposición del lote"), new_x="LMARGIN", new_y="NEXT")
    _est = (ebr["estado"] or "").upper()
    if ebr["estado"] == "liberado":
        _line(f"DECISIÓN QC: LIBERADO · por {ebr['liberado_por']} · "
              f"{(ebr['liberado_at_utc'] or '')[:19]} UTC · firma e-sig "
              f"#{ebr['liberado_signature_id']}", h=6, font_size=10)
    elif ebr["estado"] == "rechazado":
        _line(f"DECISIÓN QC: RECHAZADO · motivo: {ebr['rechazado_motivo'] or '-'}",
              h=6, font_size=10)
    else:
        _line(f"DECISIÓN QC: PENDIENTE (estado actual: {_est})", h=6, font_size=10)
    if yld is not None:
        _line(f"Rendimiento: {yld:.2f} %", h=5, font_size=9)
        # Si el rendimiento se salió de rango, el sistema EXIGIÓ justificarlo para poder
        # liberar: ese texto tiene que salir en el PDF, que es el documento que se le
        # muestra a la auditoría. Sin él, el legajo deja un 127% sin explicación.
        try:
            _yj = (ebr["yield_justificacion"] or "").strip() if (
                "yield_justificacion" in ebr.keys()) else ""
        except Exception:
            _yj = ""
        if _yj:
            _line(f"Justificación del rendimiento: {_yj}", h=5, font_size=9)

    # Hash de contenido (NO de los bytes del PDF · esos cambian con timestamp).
    # Este hash es estable: depende solo de los datos del EBR. Sirve para que
    # el auditor verifique que el PDF que tiene en mano corresponde a un EBR
    # específico y no fue alterado el record fuente.
    payload = "|".join([
        str(ebr["id"]), ebr["lote"], str(ebr["mbr_template_id"]),
        str(ebr["mbr_version"]), ebr["estado"], ebr["iniciado_at_utc"],
        str(ebr["cantidad_objetivo_g"]),
        str(ebr["cantidad_real_g"]) if ebr["cantidad_real_g"] is not None else "-",
        str(ebr["yield_pct"]) if ebr["yield_pct"] is not None else "-",
        str(ebr["liberado_signature_id"] or "-"),
        str(len(pasos)), str(len(ipcs)), str(len(firmas)),
        # Audit 3-jun · sellar también las estaciones nuevas en el hash
        str(len(pesajes)), str(len(concil)), str(len(artes)), str(len(observs)),
        str(len(precs)), str(len(despejes)), str(len(regfis)),
    ])
    content_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    gen_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Footer con hash · agregar ANTES de output() final
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 4, _safe_pdf(f"Generado: {gen_at}  ·  EOS app.eossuite.com  ·  EBR id #{ebr_id}"),
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 4, _safe_pdf(f"SHA-256 del contenido EBR: {content_hash}"),
             new_x="LMARGIN", new_y="NEXT", align="C")
    final_bytes = bytes(pdf.output())
    pdf_hash = content_hash

    # Audit log de la descarga (importante para Part 11 evidencia)
    audit_log(None, usuario=session.get("compras_user", ""),
              accion="DOWNLOAD_EBR_PDF", tabla="ebr_ejecuciones",
              registro_id=ebr_id,
              detalle=f"hash={pdf_hash[:16]} bytes={len(final_bytes)}")

    return send_file(
        io.BytesIO(final_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"EBR_{ebr['lote']}.pdf",
    )


# ════════════════════════════════════════════════════════════════════════════
# Reconciliación granular pesajes MP (F7)
# ════════════════════════════════════════════════════════════════════════════
# Captura cada pesaje individual del operario durante un paso de
# dispensación. Compara contra el teórico calculado de formula_items
# (porcentaje × cantidad_objetivo_g del lote).

def _calcular_teoricos_mp(conn, producto_nombre, lote_size_g):
    """Devuelve {material_id: cantidad_teorica_g} desde formula_items.

    Si la fórmula no existe (producto no fórmula-driven), devuelve dict vacío.
    """
    rows = conn.execute(
        """SELECT fi.material_id, fi.material_nombre, fi.porcentaje,
                  COALESCE(mm.nombre_inci,'') AS nombre_inci
           FROM formula_items fi LEFT JOIN maestro_mps mm ON mm.codigo_mp=fi.material_id
           WHERE fi.producto_nombre = ?""",
        (producto_nombre,),
    ).fetchall()
    teoricos = {}
    for r in rows:
        teoricos[r["material_id"]] = {
            "material_id": r["material_id"],
            "material_nombre": r["material_nombre"] or "",
            "nombre_inci": r["nombre_inci"] or "",
            "porcentaje": r["porcentaje"],
            "cantidad_teorica_g": (r["porcentaje"] / 100.0) * lote_size_g,
        }
    return teoricos


@bp.route("/api/brd/ebr/<int:ebr_id>/pesajes", methods=["POST"])
def reportar_pesaje(ebr_id):
    """Operario reporta el pesaje real de un MP.

    Body: {material_id, cantidad_real_g, lote_mp?, ebr_paso_id?,
           signature_id?, notas?}
    El cantidad_teorica_g se calcula del lado del servidor desde
    formula_items + cantidad_objetivo_g del EBR (no se acepta del cliente
    para evitar manipulación). delta_g y delta_pct también se calculan acá.
    """
    # Audit 3-jun · era _require_login (cualquier usuario logueado). Es una
    # mutación de registro de lote regulado → exige ejecutor (Planta/Calidad/
    # Admin), igual que pasos/conciliación. Evita escalada de privilegios.
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    material_id = (body.get("material_id") or "").strip()
    if not material_id:
        return jsonify({"error": "material_id requerido"}), 400
    try:
        real = float(body.get("cantidad_real_g") or 0)
    except (ValueError, TypeError):
        return jsonify({"error": "cantidad_real_g inválido"}), 400
    if real < 0:
        return jsonify({"error": "cantidad_real_g debe ser >= 0"}), 400

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        """SELECT e.estado, e.cantidad_objetivo_g, m.producto_nombre
           FROM ebr_ejecuciones e
           JOIN mbr_templates m ON m.id = e.mbr_template_id
           WHERE e.id = ?""",
        (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    # Calcular teórico desde formula_items
    teoricos = _calcular_teoricos_mp(conn, ebr["producto_nombre"],
                                     ebr["cantidad_objetivo_g"])
    spec = teoricos.get(material_id)
    if not spec:
        return jsonify({
            "error": f"material_id '{material_id}' no está en formula_items "
                      f"de '{ebr['producto_nombre']}'",
        }), 400

    teorico = spec["cantidad_teorica_g"]
    delta = real - teorico
    delta_pct = (delta / teorico * 100.0) if teorico > 0 else None

    # Validar e-sign. Audit 3-jun · con el motor encendido (EBR_MODE != off)
    # la 1ª firma del pesaje es OBLIGATORIA (Part 11 / dato de lote regulado).
    user = session.get("compras_user", "")
    signature_id = body.get("signature_id")
    # El legajo DEMO se camina de un click, igual que el despeje, los controles y la liberación:
    # es para comprobar el flujo, y una firma por pesaje lo traba en el primer paso.
    # se resuelve por ID y no por `ebr["lote"]`: esta consulta no trae esa columna, así que
    # leerla habría reventado -- el helper por id no depende de qué campos traiga cada SELECT
    if not signature_id and _ebr_mode_now(cur) != "off" and not _es_demo_ebr(cur, ebr_id):
        return jsonify({
            "error": "Falta la e-firma del pesaje (firmá como ejecutor).",
            "codigo": "FIRMA_REQUERIDA",
            "record_table": "ebr_pesajes",
            "record_id": f"{ebr_id}:{material_id}",
            "meaning": "ejecuta",
        }), 400
    if signature_id:
        if not _validar_signature(
            cur, signature_id, record_table="ebr_pesajes",
            record_id=f"{ebr_id}:{material_id}",
            meaning="ejecuta", signer_username=user,
        ):
            return jsonify({"error": "signature_id inválido para este pesaje"}), 400

    cur.execute(
        """INSERT INTO ebr_pesajes
             (ebr_id, ebr_paso_id, material_id, material_nombre,
              cantidad_teorica_g, cantidad_real_g, delta_g, delta_pct,
              lote_mp, pesado_por, pesado_at_utc, e_sign_id, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'utc'), ?, ?)""",
        (ebr_id, body.get("ebr_paso_id"), material_id, spec["material_nombre"],
         teorico, real, delta, delta_pct,
         (body.get("lote_mp") or "").strip(), user,
         int(signature_id) if signature_id else None,
         (body.get("notas") or "").strip()),
    )
    pid = cur.lastrowid
    conn.commit()
    audit_log(cur, usuario=user, accion="REPORTAR_PESAJE",
              tabla="ebr_pesajes", registro_id=pid,
              despues={"ebr_id": ebr_id, "material_id": material_id,
                        "real": real, "teorico": teorico, "delta_pct": delta_pct})

    # ── Conteo cíclico OPCIONAL en el pesaje (Sebastián 20-jul) ───────────────────────────────
    # El operario cuenta cuánto QUEDA físicamente de esta MP tras sacar lo pesado. Corrección =
    # (contado + pesado) − stock_sistema. |dif| ≤5% → Ajuste AUTO auditado; >5% → NO ajusta:
    # requiere verificación del Jefe de Producción + alerta a gerencia (campana).
    conteo_out = None
    _scr = body.get("stock_fisico_restante")
    if _scr is not None and str(_scr).strip() != "":
        try:
            contado = float(str(_scr).replace(",", "."))
        except (TypeError, ValueError):
            contado = None
        if contado is not None and contado >= 0:
            try:
                from datetime import datetime as _dtc, timedelta as _tdc
                from blueprints.programacion import _resolver_material_bodega, _get_mp_stock
                cod = (_resolver_material_bodega(cur, material_id, spec["material_nombre"]) or material_id)
                _st = _get_mp_stock(conn) or {}
                sistema = float(_st.get(str(cod).strip().upper(), _st.get(cod, 0)) or 0)
                real_total = contado + real
                diff = round(real_total - sistema, 2)
                base = sistema if sistema > 0.01 else max(real_total, 1.0)
                pct = (abs(diff) / base * 100.0) if base > 0 else 0.0
                _hoy = (_dtc.utcnow() - _tdc(hours=5)).isoformat(timespec="seconds")
                if abs(diff) < 0.01:
                    conteo_out = {"estado": "cuadra", "diferencia_g": 0, "sistema_g": round(sistema, 2), "pct": 0}
                elif pct <= 5.0:
                    _tipo = "Ajuste +" if diff > 0 else "Ajuste -"
                    _lote = (body.get("lote_mp") or "").strip() or ("CONTEO-PESAJE-" + str(ebr_id))
                    cur.execute(
                        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
                        "observaciones, lote, operador, estado_lote) VALUES (?,?,?,?,?,?,?,?, 'VIGENTE')",
                        (cod, spec["material_nombre"], abs(diff), _tipo, _hoy,
                         "Conteo cíclico en pesaje EBR-" + str(ebr_id) + " · contó " + str(contado) + "g", _lote, user))
                    conn.commit()
                    audit_log(None, usuario=user, accion="CONTEO_CICLICO_PESAJE_AJUSTE",
                              tabla="movimientos", registro_id=ebr_id,
                              despues={"material": cod, "diferencia_g": diff, "pct": round(pct, 1), "auto": True})
                    conteo_out = {"estado": "ajustado", "diferencia_g": diff, "pct": round(pct, 1), "sistema_g": round(sistema, 2)}
                else:
                    audit_log(None, usuario=user, accion="CONTEO_CICLICO_PESAJE_DISCREPANCIA",
                              tabla="ebr_pesajes", registro_id=pid,
                              despues={"material": cod, "diferencia_g": diff, "pct": round(pct, 1),
                                       "contado": contado, "sistema": round(sistema, 2)})
                    try:
                        from blueprints.notif import push_notif_multi
                        from config import ADMIN_USERS as _ADM
                        push_notif_multi(sorted(set(_ADM)), "conteo_ciclico",
                            "Discrepancia de conteo en pesaje (" + str(round(pct, 1)) + "%)",
                            body=("MP " + str(cod) + " · sistema " + str(round(sistema, 2)) + "g vs físico "
                                  + str(round(real_total, 2)) + "g (dif " + str(diff) + "g). Requiere verificación del Jefe de Producción."),
                            link="/inventarios", remitente=user, importante=True)
                    except Exception:
                        pass
                    conteo_out = {"estado": "requiere_jefe", "diferencia_g": diff, "pct": round(pct, 1), "sistema_g": round(sistema, 2)}
            except Exception as _ecc:
                log.warning("conteo cíclico en pesaje falló (no bloquea el pesaje): %s", _ecc)
                try:
                    conn.rollback()
                except Exception:
                    pass

    return jsonify({
        "ok": True, "id": pid,
        "cantidad_teorica_g": teorico,
        "cantidad_real_g": real,
        "delta_g": delta,
        "delta_pct": delta_pct,
        "conteo_ciclico": conteo_out,
    }), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/pesajes", methods=["GET"])
def listar_pesajes(ebr_id):
    err = _require_login()
    if err:
        return err
    rows = get_db().execute(
        """SELECT id, ebr_id, ebr_paso_id, material_id, material_nombre,
                  cantidad_teorica_g, cantidad_real_g, delta_g, delta_pct,
                  lote_mp, pesado_por, pesado_at_utc, e_sign_id, notas,
                  COALESCE(verificado_por,'') AS verificado_por,
                  verificado_at_utc, verificado_e_sign_id
           FROM ebr_pesajes WHERE ebr_id = ?
           ORDER BY pesado_at_utc""",
        (ebr_id,),
    ).fetchall()
    return jsonify({"items": [dict(r) for r in rows]})


@bp.route("/api/brd/ebr/<int:ebr_id>/pesajes-plan", methods=["GET"])
def pesajes_plan_ebr(ebr_id):
    """Lista COMPLETA de MP a dispensar (teóricos de la fórmula) + estado de pesaje de cada una.
    Sección 3 'Dispensado de MP' (MyBatch §3): muestra QUÉ pesar ANTES de pesarlo (no solo lo ya
    pesado). Los teóricos se calculan de formula_items × tamaño de lote (no se crean filas en BD)."""
    err = _require_login()
    if err:
        return err
    conn = get_db()
    ebr = conn.execute(
        "SELECT mbr_template_id, COALESCE(cantidad_objetivo_g,0) AS objetivo "
        "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"items": []})
    producto = ""
    lote_size = ebr["objetivo"] or 0
    try:
        mb = conn.execute("SELECT producto_nombre, COALESCE(lote_size_g,0) FROM mbr_templates WHERE id=?",
                          (ebr["mbr_template_id"],)).fetchone()
        if mb:
            producto = mb[0] or ""
            if not lote_size:
                lote_size = mb[1] or 0
    except Exception:
        pass
    teoricos = _calcular_teoricos_mp(conn, producto, lote_size)
    pesados = {}
    try:
        for p in conn.execute(
            "SELECT id, material_id, material_nombre, cantidad_teorica_g, cantidad_real_g, "
            "COALESCE(lote_mp,'') AS lote_mp, COALESCE(pesado_por,'') AS pesado_por, "
            "COALESCE(verificado_por,'') AS verificado_por FROM ebr_pesajes WHERE ebr_id=?",
            (ebr_id,)).fetchall():
            pesados[p["material_id"]] = dict(p)
    except Exception:
        pesados = {}
    # INCI + lote(s) FEFO sugeridos por MP (Sebastián 20-jul): el INCI sale del maestro; el lote se
    # ARRASTRA del FEFO (mismo motor que descuenta al cerrar · muestra 70g de un lote + 30g de otro).
    try:
        from blueprints.programacion import _resolver_material_bodega as _rmb, _distribuir_fefo as _dfefo
    except Exception:
        _rmb = _dfefo = None
    items = []
    for mid, t in teoricos.items():
        pp = pesados.get(mid)
        _inci = ""; _fefo = ""
        if _rmb:
            try:
                _cod = _rmb(conn.cursor(), mid, t["material_nombre"]) or mid
                _ir = conn.execute("SELECT COALESCE(nombre_inci,'') FROM maestro_mps WHERE codigo_mp=?", (_cod,)).fetchone()
                _inci = (_ir[0] if _ir else "") or ""
                if _dfefo and t["cantidad_teorica_g"]:
                    _dist = _dfefo(conn.cursor(), _cod, round(t["cantidad_teorica_g"], 3)) or []
                    _parts = []
                    for _d in _dist[:4]:
                        _l = str(_d.get("lote") or "").strip()
                        _q = round(float(_d.get("cantidad") or 0), 1)
                        _parts.append((_l if (_l and not _d.get("sin_lote")) else "s/lote") + " " + str(_q) + "g")
                    _fefo = " + ".join(_parts)
            except Exception:
                pass
        items.append({
            "material_id": mid,
            "material_nombre": t["material_nombre"] or mid,
            "nombre_inci": _inci,
            "lote_fefo": _fefo,
            "porcentaje": t["porcentaje"],
            "cantidad_teorica_g": round(t["cantidad_teorica_g"], 3),
            "id": (pp["id"] if pp else None),
            "cantidad_real_g": (pp["cantidad_real_g"] if pp else None),
            "lote_mp": (pp["lote_mp"] if pp else ""),
            "pesado_por": (pp["pesado_por"] if pp else ""),
            "verificado_por": (pp["verificado_por"] if pp else ""),
        })
    for mid, pp in pesados.items():
        if mid not in teoricos:
            items.append({
                "material_id": mid, "material_nombre": pp.get("material_nombre") or mid,
                "porcentaje": None, "cantidad_teorica_g": pp.get("cantidad_teorica_g"),
                "id": pp["id"], "cantidad_real_g": pp.get("cantidad_real_g"),
                "lote_mp": pp.get("lote_mp", ""), "pesado_por": pp.get("pesado_por", ""),
                "verificado_por": pp.get("verificado_por", ""),
            })
    items.sort(key=lambda x: -((x["porcentaje"] or 0)))
    return jsonify({"items": items, "producto": producto, "lote_size_g": lote_size})


@bp.route("/api/brd/ebr/<int:ebr_id>/pesajes/<int:pesaje_id>/verificar",
          methods=["POST"])
def verificar_pesaje_ebr(ebr_id, pesaje_id):
    """2ª firma GMP: una 2ª persona (Calidad/Admin) VERIFICA un pesaje ya
    reportado. Reemplazo del `verified_weight` de MyBatch.

    Reglas (cero-error / GMP):
      · Solo Calidad o Admin verifican (segregación de funciones).
      · El verificador NO puede ser quien pesó.
      · Solo sobre EBR iniciado/en_proceso (post-liberación es inmutable).
      · Requiere e-firma meaning='supervisa' sobre record_table='ebr_pesajes',
        record_id=pesaje_id (mismo patrón que la QC de pasos).
      · Un pesaje ya verificado no se re-verifica.
    """
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in (CALIDAD_USERS | ADMIN_USERS):
        return jsonify({
            "error": "Solo Calidad o Admin pueden verificar pesajes (2ª firma GMP)"
        }), 403
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    pes = cur.execute(
        """SELECT id, pesado_por, COALESCE(verificado_por,'') AS verificado_por
           FROM ebr_pesajes WHERE id = ? AND ebr_id = ?""",
        (pesaje_id, ebr_id),
    ).fetchone()
    if not pes:
        return jsonify({"error": "pesaje no encontrado"}), 404
    if (pes["verificado_por"] or "").strip():
        return jsonify({"error": "pesaje ya verificado"}), 409
    # Segregación de funciones GMP · quien verifica ≠ quien pesó (igual que la
    # regla de la QC de pasos en completar_paso_ebr).
    if user == (pes["pesado_por"] or ""):
        return jsonify({
            "error": "El verificador no puede ser quien pesó (segregación de funciones GMP)"
        }), 409

    if not signature_id:
        return jsonify({
            "error": "verificación requiere e-signature · meaning='supervisa' "
                      "record_table='ebr_pesajes'",
            "pesaje_id": pesaje_id,
        }), 400
    if not _validar_signature(
        cur, signature_id, record_table="ebr_pesajes",
        record_id=pesaje_id, meaning="supervisa", signer_username=user,
    ):
        return jsonify({"error": "signature_id inválido para esta verificación"}), 400

    cur.execute(
        """UPDATE ebr_pesajes
             SET verificado_por = ?,
                 verificado_at_utc = datetime('now', 'utc'),
                 verificado_e_sign_id = ?
           WHERE id = ?""",
        (user, int(signature_id), pesaje_id),
    )
    audit_log(cur, usuario=user, accion="VERIFICAR_PESAJE_EBR",
              tabla="ebr_pesajes", registro_id=pesaje_id,
              despues={"ebr_id": ebr_id, "verificado_por": user})
    conn.commit()
    return jsonify({"ok": True, "verificado_por": user})


def _conc_diferencia(requerida, recibida, devuelta, utilizada, averiada):
    """Lo que no se puede explicar de una línea de conciliación.

    Se mide contra lo que ENTRÓ a la línea (lo recibido; si nadie cargó recibido,
    lo requerido), porque es de ahí que tiene que salir todo: lo que se usó, lo que
    volvió a bodega y lo que se rompió. Lo que sobra es el faltante sin explicar,
    y ése es justamente el número que mira una auditoría.

    NO se guarda en la tabla: un total guardado al lado de sus sumandos diverge el
    día que alguien corrige uno solo (M99).
    """
    base = recibida if (recibida or 0) > 0 else (requerida or 0)
    return round((base or 0) - (utilizada or 0) - (devuelta or 0) - (averiada or 0), 3)


@bp.route("/api/brd/ebr/<int:ebr_id>/conciliacion-material", methods=["GET"])
def listar_conciliacion_material(ebr_id):
    """Conciliación de material de envase/empaque del legajo (MyBatch OF/OA):
    cuánto se requirió / recibió / devolvió / utilizó / se averió, y qué diferencia
    queda sin explicar."""
    err = _require_login()
    if err:
        return err
    rows = get_db().execute(
        """SELECT id, ebr_id, tipo, material_codigo, material_nombre, lote_material,
                  cant_requerida, cant_recibida, cant_devuelta, cant_utilizada,
                  COALESCE(cant_averiada, 0) AS cant_averiada,
                  registrado_por, registrado_at_utc, e_sign_id, notas
           FROM ebr_conciliacion_material WHERE ebr_id = ? ORDER BY id""",
        (ebr_id,),
    ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["diferencia"] = _conc_diferencia(
            d.get("cant_requerida"), d.get("cant_recibida"), d.get("cant_devuelta"),
            d.get("cant_utilizada"), d.get("cant_averiada"))
        items.append(d)
    return jsonify({"items": items})


@bp.route("/api/brd/ebr/<int:ebr_id>/conciliacion-material", methods=["POST"])
def registrar_conciliacion_material(ebr_id):
    """Registra una línea de conciliación de material (envase/etiqueta/estuche...).

    utilizada = recibida - devuelta si no se especifica. Solo sobre EBR
    iniciado/en_proceso (post-liberación es inmutable · guard + trigger)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    nombre = (body.get("material_nombre") or "").strip()
    if not nombre:
        return jsonify({"error": "material_nombre requerido"}), 400

    def _num(k):
        try:
            return max(0.0, float(body.get(k) or 0))
        except (ValueError, TypeError):
            return 0.0

    requerida = _num("cant_requerida")
    recibida = _num("cant_recibida")
    devuelta = _num("cant_devuelta")
    # Lo AVERIADO no es lo devuelto: lo devuelto vuelve a bodega y lo averiado no
    # vuelve de ninguna forma. Mezclarlos deja la conciliación cuadrando con un
    # material que ya no existe (mig 433 · clon de MyBatch).
    averiada = _num("cant_averiada")
    if body.get("cant_utilizada") not in (None, ""):
        utilizada = _num("cant_utilizada")
    else:
        utilizada = max(0.0, recibida - devuelta - averiada)

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409

    tipo = (body.get("tipo") or "envase").strip().lower()
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_conciliacion_material
             (ebr_id, tipo, material_codigo, material_nombre, lote_material,
              cant_requerida, cant_recibida, cant_devuelta, cant_utilizada,
              cant_averiada, registrado_por, registrado_at_utc, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'utc'), ?)""",
        (ebr_id, tipo, (body.get("material_codigo") or "").strip(), nombre,
         (body.get("lote_material") or "").strip(),
         requerida, recibida, devuelta, utilizada, averiada, user,
         (body.get("notas") or "").strip()),
    )
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_CONCILIACION_MATERIAL",
              tabla="ebr_conciliacion_material", registro_id=rid,
              despues={"ebr_id": ebr_id, "material": nombre,
                        "utilizada": utilizada, "averiada": averiada})
    conn.commit()
    return jsonify({"ok": True, "id": rid, "cant_utilizada": utilizada,
                    "cant_averiada": averiada,
                    "diferencia": _conc_diferencia(requerida, recibida, devuelta,
                                                   utilizada, averiada)}), 201


# ── ENVASADO Fase 3 (Sebastián 26-jun) · captura de unidades por presentación + descuento de envases ──
# Modelo: las presentaciones (15/30/50ml) salen de producto_presentaciones (envase/tapa/caja · MISMA
# fuente que la compra → compra==descuento · M55/M56). El operario entra UNIDADES por presentación; al
# CERRAR se descuenta envase+tapa+caja × unidades de movimientos_mee (canónico M26) UNA sola vez (CAS).
@bp.route("/api/brd/ebr/<int:ebr_id>/envases-plan", methods=["GET"])
def envases_plan_ebr(ebr_id):
    """Plan de envasado · SOLO lectura: presentaciones del producto + unidades ya registradas."""
    err = _require_login()
    if err:
        return err
    conn = get_db()
    erow = conn.execute(
        "SELECT COALESCE(m.producto_nombre,''), COALESCE(e.lote_codigo, e.lote), "
        "COALESCE(e.fase,'fabricacion'), COALESCE(e.envases_descontados_at,''), "
        "COALESCE(e.produccion_id, 0) "
        "FROM ebr_ejecuciones e LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id WHERE e.id=?",
        (ebr_id,)).fetchone()
    if not erow:
        return jsonify({"error": "EBR no encontrado"}), 404
    producto = erow[0] or ""
    # EL ENVASE QUE ELIGIÓ COMPRAS, no el del catálogo · Sebastián 16-ago: *"la lógica dice:
    # Catalina en compras selecciona, si algo cambia se autocarga en calendario para que lo jale
    # a envasado, así lo construimos"*.
    #
    # Esta pantalla leía `producto_presentaciones` directo, o sea el frasco HABITUAL del
    # producto, e ignoraba el `envase_codigo_override` que se fija por LOTE cuando no alcanza el
    # habitual o se decide otro. La compra y el descuento sí lo honran desde el 7-jul (M73), así
    # que el legajo mostraba un frasco y la planta descontaba otro -- y el operario alista lo que
    # ve en la pantalla. Si un lado de la cadena honra un override, el otro también (M55/M73).
    _override_lote = ""
    try:
        if erow[4]:
            _o = conn.execute(
                "SELECT COALESCE(envase_codigo_override,'') FROM produccion_programada WHERE id=?",
                (erow[4],)).fetchone()
            _override_lote = (_o[0] or "").strip() if _o else ""
    except Exception as _eo:
        # se sigue con el envase del catálogo, pero queda dicho: un override que no se pudo leer
        # es distinto de no tener override (M100)
        log.warning("envases-plan: override del lote %s no legible: %s", erow[4], _eo)
    reg = {}
    try:
        for r in conn.execute(
            "SELECT COALESCE(presentacion_codigo,''), COALESCE(unidades,0), COALESCE(registrado_por,''), "
            "COALESCE(no_envasada,0), COALESCE(motivo_no_envasada,'') "
            "FROM ebr_envasado_unidades WHERE ebr_id=?", (ebr_id,)).fetchall():
            reg[r[0]] = {"unidades": r[1], "registrado_por": r[2],
                         "no_envasada": bool(r[3]), "motivo_no_envasada": r[4]}
    except Exception as _e:
        # columnas de la mig 382 · si la instancia no migró todavía, seguir sin la marca
        log.warning("envases-plan: unidades registradas no disponibles: %s", _e)
    # FOTO y PARTES del frasco (Sebastián 26-jul: *"quiero que allí sugiera con foto el envase"*).
    # El operario tiene que RECONOCER el frasco en el estante; un código como MEE-ENV-012 no le
    # dice nada. La foto ya existía en el modelo (`maestro_mee.imagen_url`, mig 298 · se llamaba
    # "foto + partes" y pedía que se viera en bodega, dropdown y composición) pero nunca llegó
    # acá. Las partes vienen de `mee_partes`, la MISMA tabla que usan el abastecimiento para
    # comprarlas y el cierre para descontarlas.
    _fotos, _desc_mee, _partes = {}, {}, {}
    try:
        for r in conn.execute(
            "SELECT UPPER(TRIM(codigo)), COALESCE(imagen_url,''), COALESCE(descripcion,'') "
            "FROM maestro_mee").fetchall():
            if r[1]:
                _fotos[r[0]] = r[1]
            _desc_mee[r[0]] = r[2]
        for r in conn.execute(
            "SELECT UPPER(TRIM(mee_codigo)), UPPER(TRIM(COALESCE(parte_codigo,''))), "
            "COALESCE(descripcion,''), COALESCE(cantidad,1) FROM mee_partes "
            "WHERE COALESCE(parte_codigo,'')<>''").fetchall():
            _partes.setdefault(r[0], []).append(
                {"codigo": r[1], "descripcion": r[2], "cantidad": float(r[3] or 1)})
    except Exception as _e:
        log.warning("envases-plan: foto/partes no disponibles: %s", _e)

    def _mee(cod):
        c = (cod or "").strip().upper()
        return {"codigo": (cod or "").strip(), "descripcion": _desc_mee.get(c, ""),
                "foto": _fotos.get(c, "")} if c else None

    items = []
    try:
        for p in conn.execute(
            "SELECT COALESCE(presentacion_codigo,''), COALESCE(etiqueta,''), COALESCE(volumen_ml,0), "
            "COALESCE(envase_codigo,''), COALESCE(tapa_codigo,''), COALESCE(caja_codigo,'') "
            "FROM producto_presentaciones "
            "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1 "
            "ORDER BY volumen_ml", (producto,)).fetchall():
            pc = p[0]
            # el override manda sobre el frasco del catálogo · se marca para que la pantalla
            # pueda decir que ESTE lote lleva otro envase (si no, se ve como si siempre
            # hubiera sido ése y nadie se entera de la decisión de Compras)
            _env_cod = (_override_lote or p[3] or "")
            _es_override = bool(_override_lote and _override_lote.upper() != (p[3] or "").upper())
            _env = _env_cod.strip().upper()
            # las partes que se van a descontar de verdad: las del frasco, sin repetir tapa/caja
            _ya = {x for x in ((p[4] or "").strip().upper(), (p[5] or "").strip().upper()) if x}
            _pt = [dict(x, foto=_fotos.get(x["codigo"], ""))
                   for x in _partes.get(_env, []) if x["codigo"] not in _ya]
            items.append({
                "presentacion_codigo": pc, "etiqueta": p[1], "volumen_ml": p[2],
                "envase_codigo": _env_cod, "tapa_codigo": p[4], "caja_codigo": p[5],
                "envase": _mee(_env_cod), "tapa": _mee(p[4]), "caja": _mee(p[5]),
                "envase_override": _es_override,
                "envase_catalogo": (p[3] or "") if _es_override else "",
                "partes": _pt,
                "unidades": reg.get(pc, {}).get("unidades", 0),
                "registrado_por": reg.get(pc, {}).get("registrado_por", ""),
                "no_envasada": reg.get(pc, {}).get("no_envasada", False),
                "motivo_no_envasada": reg.get(pc, {}).get("motivo_no_envasada", ""),
            })
    except Exception as _e:
        log.warning("envases-plan fallo: %s", _e)

    # CLIENTES del lote (Sebastián 26-jul: *"esto está solo para ánimus, recuerda que tenemos
    # varios clientes"*). `pedidos_b2b_lote` ya guarda qué cliente aporta cuántas unidades y CON
    # QUÉ ENVASE PROPIO, y el cierre del envasado ya lo respeta: descuenta el frasco del cliente
    # por sus unidades y el de ÁNIMUS por el resto. Lo que faltaba era MOSTRARLO: el operario
    # envasaba un lote con unidades de un cliente sin verlo en pantalla.
    clientes = []
    try:
        _pid = conn.execute("SELECT COALESCE(produccion_id,0) FROM ebr_ejecuciones WHERE id=?",
                            (ebr_id,)).fetchone()
        _pid = int((_pid[0] if _pid else 0) or 0)
        if _pid:
            for r in conn.execute(
                "SELECT COALESCE(cliente_nombre,''), COALESCE(unidades_aporte,0), "
                "COALESCE(ml_unidad,0), COALESCE(envase_codigo,''), COALESCE(modo,'') "
                "FROM pedidos_b2b_lote WHERE lote_produccion_id=? ORDER BY id", (_pid,)).fetchall():
                clientes.append({
                    "cliente": r[0] or "(sin nombre)", "unidades": int(r[1] or 0),
                    "volumen_ml": float(r[2] or 0), "modo": r[4],
                    "envase": _mee(r[3]),
                    # sin envase propio, ese cliente se lleva el frasco de ÁNIMUS
                    "usa_envase_propio": bool((r[3] or "").strip()),
                })
    except Exception as _e:
        log.warning("envases-plan: clientes del lote no disponibles: %s", _e)
    return jsonify({"ok": True, "producto": producto, "lote": erow[1],
                    "descontado": bool((erow[3] or "").strip()), "items": items,
                    "clientes": clientes,
                    "unidades_clientes": sum(c["unidades"] for c in clientes)})


@bp.route("/api/brd/envase/<path:codigo>/parte", methods=["POST"])
def brd_envase_agregar_parte(codigo):
    """Agrega una PIEZA a un envase desde el legajo (Sebastián 26-jul).

    *"falta allí en envasado la opción de agregar partes por si no están mapeadas"*. Quien envasa
    es quien DESCUBRE que al frasco le falta declarar el gotero, y mandarlo a otra pantalla (o a
    pedirle el favor a un admin) es lo que hace que el dato nunca se cargue: hoy sólo 2 de 92
    envases tienen sus piezas.

    Escribe en `mee_partes`, la misma tabla que usan el abastecimiento (para comprarlas) y el
    cierre del envasado (para descontarlas), así que declarar la pieza acá arregla las dos puntas.
    Mismo permiso que ejecutar el legajo (Planta/Calidad/Admin) y **auditado**: cambia lo que se
    compra y lo que se descuenta, tiene que quedar quién lo declaró.
    """
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    env = (codigo or "").strip().upper()
    body = request.get_json(silent=True) or {}
    parte = (body.get("parte_codigo") or "").strip().upper()
    desc = (body.get("descripcion") or "").strip()[:120]
    try:
        cant = float(body.get("cantidad") or 1)
    except (TypeError, ValueError):
        cant = 1
    if not env:
        return jsonify({"error": "envase requerido"}), 400
    if not parte:
        return jsonify({"error": "el código de la pieza es obligatorio · sin él no se puede "
                                 "descontar del kardex"}), 400
    if cant <= 0:
        return jsonify({"error": "la cantidad debe ser mayor que cero"}), 400
    conn = get_db(); cur = conn.cursor()
    # el helper ÚNICO valida contra el maestro, no deja duplicar y audita · los 4 caminos que
    # escriben `mee_partes` pasan por acá para que no vuelvan a divergir (M1)
    from audit_helpers import agregar_parte_envase
    ok, motivo = agregar_parte_envase(cur, envase=env, parte=parte, descripcion=desc,
                                      cantidad=cant, usuario=user)
    if not ok:
        conn.rollback()
        codigo_err = ("YA_EXISTE" if 'ya está declarada' in (motivo or '')
                      else ("PIEZA_INEXISTENTE" if 'no existe' in (motivo or '') else "INVALIDO"))
        return jsonify({"error": motivo, "codigo": codigo_err}), (409 if codigo_err == "YA_EXISTE" else 400)
    conn.commit()
    return jsonify({"ok": True, "envase": env, "parte": parte, "cantidad": cant}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/presentacion-no-envasada", methods=["POST"])
def brd_presentacion_no_envasada(ebr_id):
    """Marca que una presentación NO se envasó en este lote (Sebastián 26-jul).

    Él preguntó: *"la opción de eliminar presentación de este envasado, o con sólo dejarlo en
    cero?"*. Ninguna de las dos: **el cero es ambiguo** — no distingue "todavía no conté" de "no
    salió ninguna", y quien firma después no puede saber cuál de las dos fue. Y borrar la fila
    haría desaparecer que esa presentación estaba planeada, que es justo lo que un registro
    regulado no puede perder.

    Así que se marca explícito, con quién y cuándo. La fila se atenúa, no se descuenta nada de
    esa presentación (unidades=0) y el registro conserva la decisión.
    """
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    pc = (body.get("presentacion_codigo") or "").strip()
    marcar = bool(body.get("no_envasada", True))
    motivo = (body.get("motivo") or "").strip()[:200]
    if not pc:
        return jsonify({"error": "presentacion_codigo requerido"}), 400
    conn = get_db(); cur = conn.cursor()
    d = cur.execute("SELECT COALESCE(envases_descontados_at,'') FROM ebr_ejecuciones WHERE id=?",
                    (ebr_id,)).fetchone()
    if not d:
        return jsonify({"error": "EBR no encontrado"}), 404
    if (d[0] or "").strip():
        return jsonify({"error": "el envasado ya se cerró · no editable",
                        "codigo": "YA_CERRADO"}), 409
    cur.execute(
        "INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, volumen_ml, "
        "unidades, no_envasada, motivo_no_envasada, registrado_por, registrado_at_utc) "
        "VALUES (?,?,'',0,0,?,?,?, datetime('now','utc')) "
        "ON CONFLICT(ebr_id, presentacion_codigo) DO UPDATE SET "
        "no_envasada=excluded.no_envasada, motivo_no_envasada=excluded.motivo_no_envasada, "
        "unidades=CASE WHEN excluded.no_envasada=1 THEN 0 ELSE ebr_envasado_unidades.unidades END, "
        "registrado_por=excluded.registrado_por, registrado_at_utc=excluded.registrado_at_utc",
        (ebr_id, pc, 1 if marcar else 0, motivo, user))
    audit_log(cur, usuario=user,
              accion=("MARCAR_PRESENTACION_NO_ENVASADA" if marcar else "REVERTIR_NO_ENVASADA"),
              tabla="ebr_envasado_unidades", registro_id=ebr_id,
              despues={"presentacion": pc, "no_envasada": marcar, "motivo": motivo})
    conn.commit()
    return jsonify({"ok": True, "presentacion_codigo": pc, "no_envasada": marcar})


@bp.route("/api/brd/ebr/<int:ebr_id>/registrar-unidades", methods=["POST"])
def registrar_unidades_envasado(ebr_id):
    """Guarda las unidades envasadas de una presentación (operario/ejecutor)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    pc = (body.get("presentacion_codigo") or "").strip()
    if not pc:
        return jsonify({"error": "presentacion_codigo requerido"}), 400
    try:
        unidades = float(body.get("unidades") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "unidades inválida"}), 400
    if unidades < 0:
        return jsonify({"error": "unidades no puede ser negativa"}), 400
    conn = get_db(); cur = conn.cursor()
    drow = cur.execute("SELECT COALESCE(envases_descontados_at,'') FROM ebr_ejecuciones WHERE id=?",
                       (ebr_id,)).fetchone()
    if drow and (drow[0] or "").strip():
        return jsonify({"error": "el envasado ya se cerró/descontó · no editable", "codigo": "YA_CERRADO"}), 409
    try:
        volumen = float(body.get("volumen_ml") or 0)
    except (TypeError, ValueError):
        volumen = 0
    cur.execute(
        "INSERT INTO ebr_envasado_unidades (ebr_id, presentacion_codigo, etiqueta, volumen_ml, "
        "unidades, registrado_por, registrado_at_utc) VALUES (?, ?, ?, ?, ?, ?, datetime('now','utc')) "
        "ON CONFLICT(ebr_id, presentacion_codigo) DO UPDATE SET unidades=excluded.unidades, "
        "etiqueta=excluded.etiqueta, volumen_ml=excluded.volumen_ml, "
        "registrado_por=excluded.registrado_por, registrado_at_utc=excluded.registrado_at_utc",
        (ebr_id, pc, (body.get("etiqueta") or "").strip(), volumen, unidades, user))
    audit_log(cur, usuario=user, accion="REGISTRAR_UNIDADES_ENVASADO",
              tabla="ebr_envasado_unidades", registro_id=ebr_id,
              despues={"presentacion": pc, "unidades": unidades})
    conn.commit()
    return jsonify({"ok": True, "presentacion_codigo": pc, "unidades": unidades})


def _stock_lote_g(c, material_id, lote):
    """Stock del kardex para un (material, lote) con el CASE canónico de la regla #4.

    No se usa `_get_mp_stock` porque ese agrega por material y acá hace falta POR LOTE,
    que es la granularidad del conteo. Los estados excluidos son los mismos 6, con UPPER
    (M23: el writer y todos los lectores en el mismo case)."""
    r = c.execute(
        "SELECT COALESCE(SUM(CASE "
        "  WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad "
        "  WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END),0) "
        "FROM movimientos WHERE material_id=? AND COALESCE(lote,'')=? "
        "AND UPPER(COALESCE(estado_lote,'')) NOT IN "
        "('CUARENTENA','CUARENTENA_EXTENDIDA','VENCIDO','RECHAZADO','AGOTADO','BLOQUEADO')",
        (material_id, lote or "")).fetchone()
    return float(r[0] or 0) if r else 0.0


@bp.route("/api/brd/ebr/<int:ebr_id>/devolucion-mp", methods=["POST"])
def brd_devolucion_mp(ebr_id):
    """Devuelve al inventario la materia prima que SOBRÓ, pesada.

    Cierra la mitad que faltaba del ciclo: hasta hoy la MP salía por FEFO al arrancar y
    lo que volvía al estante no movía nada, así que el stock quedaba subestimado.

    Y trae el CONTEO CÍCLICO de regalo (Sebastián: *"sin ser obligatorio"*): si el
    operario declara además cuánto queda EN TOTAL de ese lote, el sistema lo contrasta
    contra el kardex y reporta la discrepancia. Un conteo real sin hacer un conteo.
    """
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    material_id = (body.get("material_id") or "").strip()
    if not material_id:
        return jsonify({"error": "indicá el código de la materia prima"}), 400
    lote = (body.get("lote") or "").strip()
    try:
        cant = float(str(body.get("cantidad_g") or 0).replace(",", "."))
    except (TypeError, ValueError):
        return jsonify({"error": "cantidad_g inválida"}), 400
    # El trigger de PG rechaza cantidad <= 0 y con razón: una devolución de 0 no es un
    # hecho, es un formulario mal llenado (M18).
    if cant <= 0:
        return jsonify({"error": "la cantidad devuelta tiene que ser mayor que cero",
                        "codigo": "CANTIDAD_INVALIDA"}), 400
    conn = get_db(); cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado, COALESCE(lote_codigo, lote,'') FROM ebr_ejecuciones WHERE id=?",
        (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if str(ebr[0] or "").lower() in ("liberado", "rechazado"):
        return jsonify({"error": "el lote está %s (inmutable)" % ebr[0],
                        "codigo": "LEGAJO_INMUTABLE"}), 409
    nombre = (body.get("material_nombre") or "").strip()
    _vto = ""
    try:
        _r = cur.execute(
            "SELECT COALESCE(nombre_comercial, nombre_inci,'') FROM maestro_mps WHERE codigo_mp=?",
            (material_id,)).fetchone()
        nombre = nombre or ((_r[0] if _r else "") or "")
        # La Entrada de vuelta CONSERVA el vencimiento del lote: si se pierde, el lote
        # devuelto queda sin fecha y el cron de vencidos y el FEFO dejan de verlo (M25).
        _v = cur.execute(
            "SELECT MAX(fecha_vencimiento) FROM movimientos WHERE material_id=? "
            "AND COALESCE(lote,'')=? AND fecha_vencimiento IS NOT NULL", (material_id, lote)).fetchone()
        _vto = (_v[0] if _v else "") or ""
    except Exception as _e:
        log.warning("devolucion-mp: no se pudo resolver nombre/vencimiento de %s: %s", material_id, _e)
    stock_antes = _stock_lote_g(cur, material_id, lote)
    from datetime import datetime as _dt, timezone as _tz
    ahora = _dt.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%S")
    cur.execute(
        "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
        "observaciones, lote, fecha_vencimiento, estado_lote, operador) "
        "VALUES (?,?,?,'Entrada',?,?,?,?, 'VIGENTE', ?)",
        (material_id, nombre, cant, ahora,
         "Devolucion de sobrante · legajo #%d lote %s" % (ebr_id, ebr[1]),
         lote, _vto, user))
    mov_id = cur.lastrowid
    # Conteo cíclico OPCIONAL: sólo si el operario declara el físico TOTAL del lote.
    # Sin ese dato no se infiere nada -- un conteo inventado es peor que no contar.
    fisico = None
    discrepancia = None
    if body.get("fisico_declarado_g") not in (None, ""):
        try:
            fisico = float(str(body.get("fisico_declarado_g")).replace(",", "."))
            discrepancia = round(fisico - (stock_antes + cant), 2)
        except (TypeError, ValueError):
            fisico = None
    cur.execute(
        "INSERT INTO ebr_devoluciones_mp (ebr_id, material_id, material_nombre, lote, "
        "cantidad_g, stock_sistema_g, fisico_declarado_g, discrepancia_g, mov_id, "
        "observaciones, pesado_por, pesado_at_utc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (ebr_id, material_id, nombre, lote, cant, stock_antes, fisico, discrepancia,
         mov_id, (body.get("observaciones") or "").strip()[:500], user, ahora))
    audit_log(cur, usuario=user, accion="DEVOLVER_MP_SOBRANTE",
              tabla="movimientos", registro_id=mov_id,
              despues={"ebr_id": ebr_id, "material_id": material_id, "lote": lote,
                       "cantidad_g": cant, "stock_antes": stock_antes,
                       "fisico_declarado_g": fisico, "discrepancia_g": discrepancia})
    conn.commit()
    return jsonify({"ok": True, "mov_id": mov_id, "stock_antes_g": stock_antes,
                    "stock_despues_g": round(stock_antes + cant, 2),
                    "discrepancia_g": discrepancia}), 201


@bp.route("/api/brd/lote-sugerido", methods=["GET"])
def brd_lote_sugerido():
    """El número de lote que TOCA hoy, con la numeración de la planta (año + día juliano).

    Se SUGIERE, no se impone: la pantalla lo pre-llena y la persona puede cambiarlo. El
    número de lote es la llave de la trazabilidad y quien lo decide es quien fabrica -- lo
    que estaba mal es que EOS propusiera un formato que no existe en el rótulo (`260815-42`),
    obligando a corregirlo a mano cada vez o, peor, dejando el legajo con un lote que no
    coincide con el del producto.

    ?fecha=YYYY-MM-DD para el lote de otro día (una producción que se registra al día
    siguiente lleva el juliano del día en que se fabricó, no el de hoy).
    """
    if 'compras_user' not in session:
        return jsonify({"error": "No autorizado"}), 401
    conn = get_db()
    fecha = None
    _f = (request.args.get('fecha') or '').strip()
    if _f:
        try:
            from datetime import datetime as _dtl
            fecha = _dtl.strptime(_f[:10], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "fecha inválida · usá YYYY-MM-DD"}), 400
    try:
        from audit_helpers import lote_juliano
        sugerido = lote_juliano(conn.cursor(), fecha)
    except Exception as e:
        log.warning('lote sugerido: %s', e)
        return jsonify({"error": "no se pudo calcular el lote"}), 500
    if not sugerido:
        # Se DICE por qué no hay número, en vez de devolver uno inventado.
        return jsonify({
            "sugerido": None,
            "motivo": "ese día ya tiene 9 lotes y la numeración admite un dígito · "
                      "escribí el número a mano",
        }), 200
    from datetime import datetime as _dt2, timedelta as _td2
    _f2 = fecha or (_dt2.utcnow() - _td2(hours=5)).date()
    return jsonify({
        "sugerido": sugerido,
        "fecha": _f2.isoformat(),
        "dia_juliano": _f2.timetuple().tm_yday,
        "consecutivo": int(sugerido[-1]),
        "explicacion": "año %02d · día %d del año · lote %s del día"
                       % (_f2.year % 100, _f2.timetuple().tm_yday, sugerido[-1]),
    })


@bp.route("/api/brd/ordenes", methods=["GET", "POST"])
def brd_ordenes(ebr_id=None):
    """GET: listado de órdenes (filtros `fase` y `estado`). POST: crea una orden.

    La orden es lo que se le entrega al operario: dice QUÉ y CUÁNTO hay que hacer. Los
    lotes se le cuelgan después con `adicionar-lote`.
    """
    if request.method == "GET":
        err = _require_login()
        if err:
            return err
        conn = get_db()
        sql = ("SELECT o.*, (SELECT COUNT(*) FROM ebr_ejecuciones e WHERE e.orden_id=o.id) AS n_lotes "
               "FROM ordenes_produccion o WHERE 1=1")
        params = []
        _f = (request.args.get("fase") or "").strip().lower()
        if _f in _FASES_VALIDAS:
            sql += " AND o.fase=?"; params.append(_f)
        _e = (request.args.get("estado") or "").strip().lower()
        if _e in _ORDEN_ESTADOS:
            sql += " AND o.estado=?"; params.append(_e)
        sql += " ORDER BY o.id DESC LIMIT 300"
        out = []
        for r in conn.execute(sql, tuple(params)).fetchall():
            d = _orden_dict(r)
            d["n_lotes"] = r["n_lotes"]
            out.append(d)
        return jsonify({"ordenes": out, "total": len(out)})

    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    fase = (body.get("fase") or "fabricacion").strip().lower()
    if fase not in _FASES_VALIDAS:
        return jsonify({"error": "fase inválida · " + ", ".join(sorted(_FASES_VALIDAS))}), 400
    producto = (body.get("producto_nombre") or "").strip()
    if not producto:
        return jsonify({"error": "indicá el producto de la orden"}), 400

    def _n(k):
        try:
            v = body.get(k)
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None

    conn = get_db(); cur = conn.cursor()
    from datetime import datetime as _dt, timezone as _tz
    ahora = _dt.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%S")
    # Reintento por el UNIQUE de `numero`: el correlativo se calcula leyendo, así que dos
    # workers pueden sacar el mismo · el índice es el árbitro y acá se vuelve a intentar.
    ultimo = None
    for _ in range(5):
        numero = _orden_numero_siguiente(cur, fase)
        try:
            cur.execute(
                "INSERT INTO ordenes_produccion (numero, fase, producto_nombre, lote_bulk, "
                "cantidad_g, densidad_g_ml, estado, observaciones, creado_por, creado_at_utc, "
                "elaborado_por) VALUES (?,?,?,?,?,?, 'borrador', ?,?,?,?)",
                (numero, fase, producto, (body.get("lote_bulk") or "").strip(),
                 _n("cantidad_g"), _n("densidad_g_ml"),
                 (body.get("observaciones") or "").strip()[:500], user, ahora, user))
            break
        except Exception as _e:
            ultimo = _e
            conn.rollback()
    else:
        log.warning("no se pudo numerar la orden (%s): %s", fase, ultimo)
        return jsonify({"error": "no se pudo asignar el número de orden · reintentá"}), 409
    oid = cur.lastrowid
    audit_log(cur, usuario=user, accion="CREAR_ORDEN_PRODUCCION",
              tabla="ordenes_produccion", registro_id=oid,
              despues={"numero": numero, "fase": fase, "producto": producto})
    conn.commit()
    return jsonify({"ok": True, "id": oid, "numero": numero}), 201


@bp.route("/api/brd/ordenes/<int:orden_id>", methods=["GET"])
def brd_orden_detalle(orden_id):
    """Encabezado de la orden + sus lotes (con el estado de cada legajo)."""
    err = _require_login()
    if err:
        return err
    conn = get_db()
    row = conn.execute("SELECT * FROM ordenes_produccion WHERE id=?", (orden_id,)).fetchone()
    if not row:
        return jsonify({"error": "orden no encontrada"}), 404
    lotes = []
    for r in conn.execute(
        "SELECT id, COALESCE(lote_codigo, lote) AS lote, estado, COALESCE(operario,'') AS operario, "
        "COALESCE(iniciado_at_utc,'') AS ini, COALESCE(completado_at_utc,'') AS fin, "
        "cantidad_objetivo_g, cantidad_real_g "
        "FROM ebr_ejecuciones WHERE orden_id=? ORDER BY id", (orden_id,)).fetchall():
        lotes.append({"ebr_id": r["id"], "lote": r["lote"] or "", "estado": r["estado"] or "",
                      "operario": r["operario"], "iniciado_at_utc": r["ini"],
                      "completado_at_utc": r["fin"],
                      "cantidad_objetivo_g": r["cantidad_objetivo_g"],
                      "cantidad_real_g": r["cantidad_real_g"]})
    return jsonify({"orden": _orden_dict(row, lotes=lotes),
                    "mi_rol": _batch_role_info(session.get("compras_user", ""))})


def _aprobar_orden_generico(orden_id, *, campo, meaning, rol_requerido, etiqueta):
    """Núcleo de las DOS aprobaciones de una orden (producción y calidad).

    Un solo resolver para las dos (M1): si se escribieran por separado, la de calidad
    -que sólo usa acondicionamiento- sería la que se quede vieja."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    if rol_requerido and not _batch_role_info(user).get(rol_requerido):
        return jsonify({"error": "%s es atribución de Calidad / Dirección Técnica." % etiqueta,
                        "codigo": "ROL_NO_AUTORIZADO"}), 403
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")
    conn = get_db(); cur = conn.cursor()
    row = cur.execute("SELECT * FROM ordenes_produccion WHERE id=?", (orden_id,)).fetchone()
    if not row:
        return jsonify({"error": "orden no encontrada"}), 404
    if (row["estado"] or "") == "anulada":
        return jsonify({"error": "la orden está anulada", "codigo": "ORDEN_ANULADA"}), 409
    if (row[campo] or "").strip():
        return jsonify({"error": "%s ya la dio %s" % (etiqueta, row[campo]),
                        "codigo": "YA_APROBADA"}), 409
    if campo == "aprobada_calidad_por" and (row["fase"] or "") != "acondicionamiento":
        return jsonify({"error": "la aprobación de Calidad sobre la orden es de acondicionamiento",
                        "codigo": "FASE_SIN_APROBACION_CALIDAD"}), 400
    if not signature_id:
        return jsonify({"error": "signature_id requerido · meaning='%s' "
                                 "record_table='ordenes_produccion'" % meaning}), 400
    if not _validar_signature(cur, signature_id, record_table="ordenes_produccion",
                              record_id=orden_id, meaning=meaning, signer_username=user):
        return jsonify({"error": "signature_id no corresponde a una firma '%s' de esta orden "
                                 "por vos" % meaning}), 400
    cur.execute(
        "UPDATE ordenes_produccion SET %s=?, %s=datetime('now','utc'), %s=? "
        "WHERE id=? AND COALESCE(%s,'')=''" % (campo, campo.replace("_por", "_at_utc"),
                                               campo.replace("_por", "_signature_id"), campo),
        (user, signature_id, orden_id))
    if cur.rowcount == 0:                      # CAS: otro worker aprobó primero (M27)
        conn.rollback()
        return jsonify({"error": "la orden ya fue aprobada · refrescá", "codigo": "YA_APROBADA"}), 409
    # La orden pasa a 'aprobada' sólo cuando TIENE todas sus firmas: en acondicionamiento
    # son dos, y con una sola todavía no está autorizada a arrancar.
    _o = cur.execute("SELECT fase, COALESCE(aprobada_por,''), COALESCE(aprobada_calidad_por,''), "
                     "estado FROM ordenes_produccion WHERE id=?", (orden_id,)).fetchone()
    _completa = bool(_o[1]) and (_o[0] != "acondicionamiento" or bool(_o[2]))
    if _completa and (_o[3] or "") == "borrador":
        cur.execute("UPDATE ordenes_produccion SET estado='aprobada' WHERE id=? AND estado='borrador'",
                    (orden_id,))
    audit_log(cur, usuario=user, accion="APROBAR_ORDEN_" + ("CALIDAD" if "calidad" in campo else "PRODUCCION"),
              tabla="ordenes_produccion", registro_id=orden_id,
              despues={"por": user, "signature_id": signature_id, "completa": _completa})
    conn.commit()
    return jsonify({"ok": True, "aprobada_por": user, "orden_aprobada": _completa})


@bp.route("/api/brd/ordenes/<int:orden_id>/aprobar", methods=["POST"])
def brd_orden_aprobar(orden_id):
    """Aprobación de PRODUCCIÓN sobre la orden · vale para TODOS sus lotes."""
    return _aprobar_orden_generico(
        orden_id, campo="aprobada_por", meaning="aprueba_orden",
        rol_requerido=None, etiqueta="La aprobación de la orden")


@bp.route("/api/brd/ordenes/<int:orden_id>/aprobar-calidad", methods=["POST"])
def brd_orden_aprobar_calidad(orden_id):
    """2ª aprobación (CALIDAD) · sólo acondicionamiento, como en MyBatch."""
    return _aprobar_orden_generico(
        orden_id, campo="aprobada_calidad_por", meaning="aprueba_orden_calidad",
        rol_requerido="puede_aprobar", etiqueta="La aprobación de Calidad")


@bp.route("/api/brd/ordenes/<int:orden_id>/adicionar-lote", methods=["POST"])
def brd_orden_adicionar_lote(orden_id):
    """"Adicionar Lote" de MyBatch: crea un legajo NUEVO colgado de esta orden.

    Delega en `crear_ebr_desde_mbr` (M3: una sola ruta canónica de creación de legajo ·
    acá sólo se le pone el `orden_id`). Una orden puede tener N lotes; un lote, una orden.
    """
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    lote = (body.get("lote") or "").strip()
    if not lote:
        return jsonify({"error": "indicá el número de lote"}), 400
    conn = get_db(); cur = conn.cursor()
    row = cur.execute("SELECT * FROM ordenes_produccion WHERE id=?", (orden_id,)).fetchone()
    if not row:
        return jsonify({"error": "orden no encontrada"}), 404
    if (row["estado"] or "") in ("anulada", "cerrada"):
        return jsonify({"error": "la orden está %s · no admite lotes nuevos" % row["estado"],
                        "codigo": "ORDEN_CERRADA"}), 409
    try:
        res = crear_ebr_desde_mbr(
            cur, producto_nombre=row["producto_nombre"], lote=lote,
            cantidad_objetivo_g=row["cantidad_g"], usuario=user,
            fase=row["fase"], notas="Lote de la orden " + (row["numero"] or ""))
    except Exception as _e:
        conn.rollback()
        log.warning("adicionar lote a la orden %s falló: %s", orden_id, _e)
        return jsonify({"error": "no se pudo crear el legajo: %s" % _e}), 500
    # El contrato de `crear_ebr_desde_mbr` es {'ok': bool, 'id': int, 'error': str} · la
    # llave es `id`, NO `ebr_id` (M94: leer el return antes de indexarlo · con la llave
    # equivocada esto crearía el legajo y devolvería error, que es una feature muerta).
    if not (isinstance(res, dict) and res.get("ok")):
        conn.rollback()
        _err = (res or {}).get("error", "") if isinstance(res, dict) else ""
        _msg = {"NO_MBR_APROBADO": "el producto no tiene un MBR aprobado para esta fase",
                "LOTE_DUPLICADO": "ese lote ya tiene legajo en esta fase",
                "SIN_FORMULA": "el producto no tiene fórmula activa"}.get(_err, _err or "desconocido")
        return jsonify({"error": "no se pudo crear el legajo del lote: " + _msg,
                        "codigo": _err or "SIN_LEGAJO"}), 409
    ebr_id = res.get("id")
    cur.execute("UPDATE ebr_ejecuciones SET orden_id=? WHERE id=?", (orden_id, ebr_id))
    # La orden ya aprobada vale para TODOS sus lotes: el lote nuevo hereda esa autorización
    # (es el sentido de aprobar UNA vez el encabezado). Se copia para que el gate y el
    # imprimible del legajo la vean sin tener que ir a buscar a la madre.
    if (row["aprobada_por"] or "").strip():
        cur.execute(
            "UPDATE ebr_ejecuciones SET aprobada_orden_por=?, aprobada_orden_at_utc=?, "
            "aprobada_orden_rol='orden' WHERE id=? AND COALESCE(aprobada_orden_por,'')=''",
            (row["aprobada_por"], row["aprobada_at_utc"] or "", ebr_id))
    audit_log(cur, usuario=user, accion="ADICIONAR_LOTE_A_ORDEN",
              tabla="ordenes_produccion", registro_id=orden_id,
              despues={"ebr_id": ebr_id, "lote": lote, "numero": row["numero"]})
    conn.commit()
    return jsonify({"ok": True, "ebr_id": ebr_id, "lote": lote}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/remanente-granel", methods=["POST"])
def remanente_granel_ebr(ebr_id):
    """Cierra la conciliación del granel: cuánto SOBRÓ y en qué terminó.

    Es el único dato de la cuenta que hay que ir a medir; el resto se deriva
    (ver `_conciliacion_granel`). Se pesa en gramos porque así se mide en piso.
    """
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    destino = (body.get("destino") or "").strip()
    if destino not in _REMANENTE_DESTINOS:
        return jsonify({"error": "destino inválido · " + ", ".join(sorted(_REMANENTE_DESTINOS)),
                        "codigo": "DESTINO_INVALIDO"}), 400
    try:
        remanente_g = float(body.get("remanente_g") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "remanente_g inválido"}), 400
    if remanente_g < 0:
        return jsonify({"error": "el remanente no puede ser negativo"}), 400
    if destino == "sin_remanente" and remanente_g > 0:
        return jsonify({"error": "declaraste 'no quedó remanente' pero cargaste un peso · corregí uno de los dos",
                        "codigo": "DESTINO_CONTRADICE_PESO"}), 400
    conn = get_db(); cur = conn.cursor()
    row = cur.execute(
        "SELECT COALESCE(fase,'fabricacion'), estado, COALESCE(remanente_g,-1) "
        "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not row:
        return jsonify({"error": "EBR no encontrado"}), 404
    if str(row[0]).strip().lower() != "envasado":
        return jsonify({"error": "la conciliación de granel es de los legajos de envasado"}), 400
    if str(row[1] or "").lower() in ("liberado", "rechazado"):
        return jsonify({"error": "el legajo ya está liberado/rechazado · es inmutable (Part 11)",
                        "codigo": "LEGAJO_INMUTABLE"}), 409
    _antes = {"remanente_g": (None if float(row[2]) < 0 else float(row[2]))}
    cur.execute(
        "UPDATE ebr_ejecuciones SET remanente_g=?, remanente_destino=?, remanente_observaciones=?, "
        "remanente_por=?, remanente_at_utc=datetime('now','utc') "
        "WHERE id=? AND LOWER(COALESCE(estado,'')) NOT IN ('liberado','rechazado')",
        (remanente_g, destino, (body.get("observaciones") or "").strip()[:500], user, ebr_id))
    if cur.rowcount == 0:                     # CAS: el estado cambió mientras tanto (M27)
        conn.rollback()
        return jsonify({"error": "el legajo cambió de estado · refrescá", "codigo": "ESTADO_CAMBIO"}), 409
    conc = _conciliacion_granel(conn, ebr_id)
    audit_log(cur, usuario=user, accion="CONCILIAR_GRANEL_ENVASADO",
              tabla="ebr_ejecuciones", registro_id=ebr_id, antes=_antes,
              despues={"remanente_g": remanente_g, "destino": destino,
                       "diferencia_ml": (conc or {}).get("diferencia_ml"),
                       "diferencia_pct": (conc or {}).get("diferencia_pct")})
    conn.commit()
    return jsonify({"ok": True, "conciliacion": conc})


@bp.route("/api/brd/ebr/<int:ebr_id>/aprobar-orden", methods=["POST"])
def aprobar_orden_ebr(ebr_id):
    """Aprobación de la ORDEN antes de arrancar (Part 11 §11.50 · e-firma).

    Es la firma que faltaba: el legajo ya guardaba quién lo INICIÓ, quién lo LIBERÓ y
    el visto bueno final del DT (mig 286), pero no quién AUTORIZÓ que empezara -que en
    MyBatch es una firma propia de la orden, y en acondicionamiento son dos (producción
    y calidad)-. Sólo Producción/Calidad/Admin, y nunca uno se aprueba a sí mismo el
    arranque sin dejar rastro: va con firma validada y audit_log.
    """
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")
    conn = get_db(); cur = conn.cursor()
    row = cur.execute(
        "SELECT estado, COALESCE(aprobada_orden_por,''), COALESCE(lote_codigo, lote, ''), "
        "COALESCE(fase,'fabricacion') FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not row:
        return jsonify({"error": "EBR no encontrado"}), 404
    if (row[1] or "").strip():
        return jsonify({"error": "la orden ya fue aprobada por " + row[1], "codigo": "YA_APROBADA"}), 409
    if str(row[0] or "").lower() in ("liberado", "rechazado"):
        return jsonify({"error": "el legajo ya está cerrado", "codigo": "LEGAJO_INMUTABLE"}), 409
    _es_demo = es_lote_demo(row[2] or "")
    if not signature_id and not _es_demo:
        return jsonify({"error": "signature_id requerido · meaning='aprueba_orden' "
                                 "record_table='ebr_ejecuciones'"}), 400
    if not _es_demo and not _validar_signature(
            cur, signature_id, record_table="ebr_ejecuciones", record_id=ebr_id,
            meaning="aprueba_orden", signer_username=user):
        return jsonify({"error": "signature_id no corresponde a una firma 'aprueba_orden' "
                                 "de este legajo por vos"}), 400
    # El ROL con el que firma queda en el registro: en acondicionamiento la orden lleva
    # la de producción Y la de calidad, y sin el rol las dos firmas serían indistinguibles.
    rol = "calidad" if user in CALIDAD_USERS and user not in PLANTA_USERS else "produccion"
    cur.execute(
        "UPDATE ebr_ejecuciones SET aprobada_orden_por=?, aprobada_orden_at_utc=datetime('now','utc'), "
        "aprobada_orden_signature_id=?, aprobada_orden_rol=? "
        "WHERE id=? AND COALESCE(aprobada_orden_por,'')=''",
        (user, signature_id, rol, ebr_id))
    if cur.rowcount == 0:                     # CAS: otro worker la aprobó primero (M27)
        conn.rollback()
        return jsonify({"error": "la orden ya fue aprobada · refrescá", "codigo": "YA_APROBADA"}), 409
    audit_log(cur, usuario=user, accion="APROBAR_ORDEN",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"aprobada_por": user, "rol": rol, "fase": row[3],
                       "signature_id": signature_id})
    conn.commit()
    return jsonify({"ok": True, "aprobada_por": user, "rol": rol})


@bp.route("/api/brd/ebr/<int:ebr_id>/cerrar-envasado", methods=["POST"])
def cerrar_envasado_ebr(ebr_id):
    """Cierra el envasado: descuenta envase+tapa+caja × unidades (movimientos_mee) UNA vez (CAS) y marca
    completado. Reversa segura: si el descuento falla, rollback (no queda marcado) y se puede reintentar."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    conn = get_db(); cur = conn.cursor()
    erow = cur.execute(
        "SELECT COALESCE(m.producto_nombre,''), COALESCE(e.lote_codigo, e.lote), COALESCE(e.fase,'fabricacion'), "
        "COALESCE(e.produccion_id, 0) "
        "FROM ebr_ejecuciones e LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id WHERE e.id=?",
        (ebr_id,)).fetchone()
    if not erow:
        return jsonify({"error": "EBR no encontrado"}), 404
    if str(erow[2]).strip().lower() != "envasado":
        return jsonify({"error": "este cierre es solo para legajos de envasado"}), 400
    producto = erow[0] or ""
    lote = erow[1] or ""
    _prod_id = int(erow[3] or 0)
    uds = {}
    _uds_ya_descontadas = False
    for r in cur.execute(
        "SELECT COALESCE(presentacion_codigo,''), COALESCE(unidades,0) FROM ebr_envasado_unidades "
        "WHERE ebr_id=?", (ebr_id,)).fetchall():
        if (r[1] or 0) > 0:
            uds[r[0]] = r[1]
    if not uds:
        # ── LAS UNIDADES SE REGISTRAN POR DOS CAMINOS, Y ESTE LEÍA UNO SOLO (17-ago) ────────
        # `POST /api/envasado` -- la pantalla que usa la planta -- escribe en `envasado`; el
        # formulario del propio legajo escribe en `ebr_envasado_unidades`. El cierre miraba sólo
        # el segundo, así que quien envasaba por la pantalla veía **sus unidades listadas en el
        # legajo** ("DEMO30 · 30 unidades · Completado") y el botón le contestaba *"registrá las
        # unidades envasadas antes de cerrar"*: la pantalla y el botón diciendo cosas opuestas
        # sobre el mismo hecho, sin forma de entender por qué (M37/M83 · el dato se escribe en un
        # sitio y se lee en otro · M161 · dos partes de la misma pantalla contradiciéndose).
        #
        # Se lee la MISMA fuente que el legajo MUESTRA primero.
        for r in cur.execute(
            "SELECT COALESCE(NULLIF(TRIM(presentacion),''), COALESCE(envase_codigo,'')), "
            "       COALESCE(unidades,0) "
            "  FROM envasado WHERE UPPER(TRIM(lote))=UPPER(TRIM(?))", (lote,)).fetchall():
            if (r[1] or 0) > 0 and (r[0] or ''):
                uds[r[0]] = uds.get(r[0], 0) + r[1]
        # ⚠ Y si las unidades salieron de ahí, los materiales YA SE DESCONTARON: ese mismo
        #   registro (`POST /api/envasado`) saca el frasco, la tapa y la caja del kardex al
        #   guardarse. Volver a descontarlos acá los sacaría DOS VECES -- medido caminando el
        #   lote completo: 60 unidades de frasco y de tapa donde se envasaron 30.
        #   El cierre sigue haciendo todo lo demás (marca completado, encadena el
        #   acondicionamiento) y DECLARA por qué no movió el kardex (M124).
        _uds_ya_descontadas = bool(uds)
    if not uds:
        # ⚠ NO se cae a las presentaciones PLANEADAS, que es la tercera fuente que la pantalla
        #   usa cuando todavía no hay nada envasado: lo planeado no es lo producido, y cerrar
        #   contra un plan descontaría envases por unidades que nadie llenó.
        return jsonify({"error": "registrá las unidades envasadas (al menos una presentación) antes de cerrar"}), 400
    # CAS idempotente: reclamar el descuento · solo 1 vez y solo si está en proceso (race multi-worker · M27)
    cur.execute(
        "UPDATE ebr_ejecuciones SET envases_descontados_at=datetime('now','utc'), estado='completado', "
        "completado_at_utc=datetime('now','utc') "
        "WHERE id=? AND COALESCE(fase,'')='envasado' AND COALESCE(envases_descontados_at,'')='' "
        "AND estado IN ('iniciado','en_proceso')", (ebr_id,))
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "El envasado ya se cerró/descontó o no está en proceso · refrescá",
                        "codigo": "YA_CERRADO"}), 409
    if _uds_ya_descontadas:
        # Las unidades salieron del REGISTRO de envasado, que ya sacó sus materiales del kardex.
        # El cierre marca completado y encadena el acondicionamiento, pero NO vuelve a descontar.
        conn.commit()
        audit_log(None, usuario=user, accion="CERRAR_ENVASADO_SIN_DESCONTAR",
                  tabla="ebr_ejecuciones", registro_id=ebr_id,
                  despues={"lote": lote, "motivo": "los materiales ya los descontó el registro "
                                                   "de envasado de este lote"})
        _acond = None
        try:
            if producto and lote:
                _r = crear_ebr_desde_mbr(conn.cursor(), producto_nombre=producto, lote=lote,
                                         usuario=user, fase='acondicionamiento')
                conn.commit()
                if _r.get('ok'):
                    _acond = _r.get('id')
                else:
                    _y = conn.execute(
                        "SELECT id FROM ebr_ejecuciones "
                        " WHERE COALESCE(NULLIF(lote_codigo,''), lote)=? "
                        "   AND COALESCE(fase,'')='acondicionamiento' "
                        " ORDER BY id DESC LIMIT 1", (lote,)).fetchone()
                    _acond = _y[0] if _y else None
        except Exception as _e_ch:
            log.warning("cerrar-envasado (sin descontar): no se habilitó acondicionamiento: %s", _e_ch)
        return jsonify({"ok": True, "estado": "completado", "descuentos": [], "n_descuentos": 0,
                        "acond_ebr_id": _acond,
                        "materiales_ya_descontados": True,
                        "motivo": "los materiales de este lote ya salieron del kardex al "
                                  "registrar el envasado"})
    # El ENVASE puede variar por lote (Sebastián 20-jul): honrar el override del lote
    # (produccion_programada.envase_codigo_override) y el envase custom por cliente B2B
    # (pedidos_b2b_lote.envase_codigo) · igual que _descontar_mee_envasado (M55/M73). Tapa/caja
    # siempre el default. Etiqueta NO va acá (se pone en Acondicionamiento · Sebastián 20-jul).
    _env_override = ''
    _b2b_custom = []   # [(env_cod, uds)]
    if _prod_id:
        try:
            _eo = cur.execute("SELECT COALESCE(envase_codigo_override,'') FROM produccion_programada WHERE id=?",
                              (_prod_id,)).fetchone()
            _env_override = ((_eo[0] if _eo else '') or '').strip().upper()
        except Exception:
            _env_override = ''
        try:
            for _br in cur.execute(
                "SELECT COALESCE(envase_codigo,''), COALESCE(unidades_aporte,0) FROM pedidos_b2b_lote "
                "WHERE lote_produccion_id=? AND COALESCE(envase_codigo,'')<>''", (_prod_id,)).fetchall():
                _ec = (_br[0] or '').strip().upper(); _un = int(_br[1] or 0)
                if _ec and _un > 0:
                    _b2b_custom.append((_ec, _un))
        except Exception:
            _b2b_custom = []
    _b2b_rem = sum(u for _, u in _b2b_custom)  # uds B2B a restar del descuento del envase default

    # ── PARTES DEL FRASCO (mee_partes) · Sebastián 26-jul ─────────────────────────────────────
    # Un frasco arrastra sus componentes (gotero, tapa, inner cup). El ABASTECIMIENTO ya los
    # compraba leyendo `mee_partes`, pero el envasado descontaba SOLO lo que estuviera en
    # `producto_presentaciones.tapa_codigo/caja_codigo` — y medido en producción, las 43
    # presentaciones activas estaban SIN tapa: el sistema **nunca descontó una tapa, en ningún
    # producto**. Se compraban, entraban a bodega, se usaban, y no salían jamás del kardex.
    # Es el patrón M55/M73 otra vez: lo que se compra tiene que ser lo que se descuenta. Ahora
    # ambos lados leen la MISMA tabla, así que cargar las partes de un frasco sincroniza compra y
    # descuento de una sola vez y no pueden volver a divergir.
    _partes = {}
    try:
        for _r in cur.execute(
            "SELECT UPPER(TRIM(mee_codigo)), UPPER(TRIM(COALESCE(parte_codigo,''))), "
            "COALESCE(cantidad,1) FROM mee_partes WHERE COALESCE(parte_codigo,'')<>''").fetchall():
            _partes.setdefault(_r[0], []).append((_r[1], float(_r[2] or 1)))
    except Exception as _e_pt:
        # nunca romper el cierre por esto, pero dejar rastro (un except mudo esconde el bug · M94)
        log.warning("cerrar-envasado: no se pudieron leer las partes del envase: %s", _e_pt)
        _partes = {}

    descuentos = []

    # ── EL FRASCO QUE VOLVIÓ SERIGRAFIADO ES EL QUE SE USA (Catalina 4-ago) ────────────────
    # Cuando un envase se manda a marcar, su Salida YA se registró al enviarlo y vuelve como
    # OTRO código. Descontar el base otra vez acá lo cuenta dos veces Y deja el serigrafiado
    # -- el que de verdad se pone en la línea -- sin consumirse nunca (M147 causa (a)).
    #
    # No se adivina: la orden guarda `produccion_id` + `base_codigo` + `serigrafiado_codigo`,
    # así que "este base, para ESTA producción, volvió como aquel" es un hecho REGISTRADO (M19).
    # Sólo cuenta si está **liberado**: mientras está afuera -- o adentro en cuarentena -- ese
    # envase no está para usarse y el stock canónico no lo cuenta (M153).
    _redirigidos = []

    def _envase_efectivo(cod):
        """Devuelve (código a descontar, código del que se redirigió o '')."""
        cod = (cod or "").strip()
        if not cod or not _prod_id:
            return cod, ''
        try:
            _mo = cur.execute(
                "SELECT serigrafiado_codigo FROM marcacion_ordenes "
                " WHERE produccion_id=? AND UPPER(TRIM(base_codigo))=UPPER(TRIM(?)) "
                "   AND LOWER(COALESCE(estado,''))='liberado' "
                "   AND UPPER(TRIM(COALESCE(serigrafiado_codigo,'')))<>UPPER(TRIM(base_codigo)) "
                " ORDER BY id DESC LIMIT 1", (_prod_id, cod)).fetchone()
            if _mo and (_mo[0] or '').strip():
                return (_mo[0] or '').strip(), cod
        except Exception as _e_mo:
            # Un fallo mudo acá vuelve a descontar doble sin que nadie lo note (M4/M94).
            log.warning("cerrar-envasado: no pude revisar la marcación de %s (prod %s): %s",
                        cod, _prod_id, _e_mo)
        return cod, ''

    # ── EL LIBRO MAYOR DE LO YA CONSUMIDO (Sebastián 5-ago) ───────────────────────────────
    # `produccion_checklist.consumido_at` es el registro de "este envase, para esta producción,
    # ya salió del kardex". Lo escribía SÓLO el cierre de acondicionamiento del Kanban, y este
    # cierre ni lo leía ni lo escribía -- con los dos corriendo sobre el mismo lote físico
    # (envasar y después acondicionar) el frasco, la tapa y la caja salían DOS VECES.
    #
    # No se agrega un tercer candado: los dos caminos pasan a usar el que ya existe. Acá se lee
    # para SALTAR lo que ya bajó, y más abajo se RECLAMA con CAS lo que este cierre sí descuenta.
    _ya_consumido = set()      # códigos que el checklist ya marcó · no se vuelven a descontar
    _reclamables = {}          # código -> [id de fila del checklist] · para reclamar después
    _sin_libro = not _prod_id
    if _prod_id:
        try:
            for _cid, _ccod, _cons in cur.execute(
                    "SELECT id, UPPER(TRIM(COALESCE(mee_codigo_asignado,''))), "
                    "       COALESCE(consumido_at,'') "
                    "  FROM produccion_checklist "
                    " WHERE produccion_id=? AND COALESCE(mee_codigo_asignado,'')<>''",
                    (_prod_id,)).fetchall():
                if not _ccod:
                    continue
                if str(_cons or '').strip():
                    _ya_consumido.add(_ccod)
                else:
                    _reclamables.setdefault(_ccod, []).append(_cid)
        except Exception as _e_lib:
            # Sin el libro mayor NO se puede coordinar · se declara y se sigue descontando (que
            # un envase no salga del kardex es peor que arriesgar el doble), pero la respuesta
            # lo dice para que el descuadre no aparezca sin explicación (M100/M124).
            log.warning("cerrar-envasado: no pude leer el checklist de la producción %s: %s",
                        _prod_id, _e_lib)
            _sin_libro = True
            _ya_consumido = set(); _reclamables = {}

    _saltados = []

    def _salida_mee(cod, cantidad, etiqueta, presentacion):
        """Una Salida de MEE. Nunca cantidad <= 0 (el trigger de PG la rechaza · M18)."""
        cod = (cod or "").strip()
        if not cod or cantidad is None or cantidad <= 0:
            return
        _k = cod.upper()
        if _k in _ya_consumido:
            # Ya salió del kardex por el cierre de acondicionamiento · descontarlo otra vez es
            # inventar un consumo que no ocurrió.
            _saltados.append({"mee_codigo": cod, "tipo": etiqueta,
                              "motivo": "ya consumido en el checklist de esta producción"})
            return
        # RECLAMO con CAS: si otro worker (o el Kanban) lo marcó entre la lectura y ahora,
        # `rowcount` es 0 y este cierre NO descuenta. El check-then-act no alcanza con 3
        # workers (M27/M73: se reclama ANTES de tocar el kardex, no después).
        _ids = _reclamables.get(_k) or []
        if _ids:
            cur.execute(
                "UPDATE produccion_checklist SET consumido_at=datetime('now','-5 hours'), "
                "       consumido_por=?, consumido_contexto='envasado_ebr' "
                " WHERE id=? AND COALESCE(consumido_at,'')=''", (user, _ids[0]))
            if cur.rowcount == 0:
                _ya_consumido.add(_k)
                _saltados.append({"mee_codigo": cod, "tipo": etiqueta,
                                  "motivo": "otro cierre lo reclamó primero"})
                return
            _ids.pop(0)
        _obs = ("Envasado EBR-" + str(ebr_id) + " lote " + lote + " · "
                + etiqueta + (" " + presentacion if presentacion else ""))
        # ⚠ NO se usa `aplicar_movimiento_mee` acá, y la razón importa: ese helper **clampea la
        # Salida contra `maestro_mee.stock_actual`**, que es un CACHE -- y M26 dice explícitamente
        # que el stock canónico es la SUMA DEL KARDEX, no el cache. Probarlo con el cache en 0
        # (como hace el fixture de `test_envase_partes_se_descuentan`, a propósito) registra una
        # Salida de CERO: el envase se usó y el kardex sigue diciendo que está en bodega. Eso es
        # peor que el doble descuento, y ya pasó una vez (M153).
        #
        # Entonces: el KARDEX registra lo que de verdad se consumió (completo), y el cache se
        # mueve con el MISMO delta. En el caso sano (cache == kardex) queda exacto y sin drift;
        # si el cache venía mal, el kardex igual dice la verdad y el cron de las 3 AM lo realinea.
        # Lo único que se conserva del helper es la validación: un código que no está en el
        # maestro NO entra (antes creaba stock fantasma que nadie puede reponer · M100).
        if not cur.execute("SELECT 1 FROM maestro_mee WHERE UPPER(TRIM(codigo))=UPPER(TRIM(?))",
                           (cod,)).fetchone():
            log.warning("cerrar-envasado: %s no existe en maestro_mee · no se descuenta", cod)
            _saltados.append({"mee_codigo": cod, "tipo": etiqueta,
                              "motivo": "no existe en el maestro de envases"})
            return
        cur.execute(
            "INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, observaciones, responsable, "
            " fecha, lote_ref, batch_ref) "
            "VALUES (?, 'Salida', ?, ?, ?, datetime('now','utc'), ?, ?)",
            (cod, cantidad, _obs, user, str(_prod_id or ''), lote or ''))
        # `MAX(a,b)` es escalar en SQLite y AGREGADA en PG · va con CASE (M51).
        cur.execute(
            "UPDATE maestro_mee SET stock_actual = CASE WHEN COALESCE(stock_actual,0) - ? < 0 "
            "  THEN 0 ELSE COALESCE(stock_actual,0) - ? END WHERE codigo=?",
            (cantidad, cantidad, cod))
        descuentos.append({"mee_codigo": cod, "tipo": etiqueta, "cantidad": cantidad,
                           "presentacion": presentacion})

    def _salida_partes(envase_cod, unidades, presentacion, ya_descontados):
        """Los componentes del frasco realmente usado, sin repetir lo que ya bajó por tapa/caja."""
        for _pc, _pcant in _partes.get((envase_cod or "").strip().upper(), []):
            if not _pc or _pc in ya_descontados:
                continue
            _salida_mee(_pc, round(unidades * (_pcant or 1), 4), "parte", presentacion)

    try:
        for p in cur.execute(
            "SELECT COALESCE(presentacion_codigo,''), COALESCE(envase_codigo,''), COALESCE(tapa_codigo,''), "
            "COALESCE(caja_codigo,'') FROM producto_presentaciones "
            "WHERE UPPER(TRIM(producto_nombre))=UPPER(TRIM(?)) AND COALESCE(activo,1)=1", (producto,)).fetchall():
            n = uds.get(p[0], 0)
            if n <= 0:
                continue
            # el envase REALMENTE usado en este lote (override del lote manda)
            _env_efectivo = (_env_override or (p[1] or "")).strip()
            _qty_envase = n
            if _b2b_rem > 0:                     # restar las uds que van a envase B2B custom
                _sub = min(_b2b_rem, _qty_envase)
                _qty_envase -= _sub; _b2b_rem -= _sub
            # La redirección aplica al FRASCO, no a la tapa ni a la caja: a serigrafía va el
            # envase, y redirigir una tapa por parecido sería adivinar.
            _env_efectivo, _de = _envase_efectivo(_env_efectivo)
            if _de:
                _redirigidos.append({"de": _de, "a": _env_efectivo, "presentacion": p[0]})
            _salida_mee(_env_efectivo, _qty_envase, "envase", p[0])
            _salida_mee(p[2], n, "tapa", p[0])
            _salida_mee(p[3], n, "caja", p[0])
            # las partes acompañan al FRASCO, así que van por las unidades del frasco
            _salida_partes(_env_efectivo, _qty_envase, p[0],
                           {(c or "").strip().upper() for c in (_env_efectivo, p[2], p[3]) if c})
        # Envases custom por cliente B2B · 1:1 con sus unidades (aparte del default)
        for _ec, _un in _b2b_custom:
            _ec, _de_b2b = _envase_efectivo(_ec)
            if _de_b2b:
                _redirigidos.append({"de": _de_b2b, "a": _ec, "presentacion": "B2B"})
            _salida_mee(_ec, _un, "envase_b2b", "")
            _salida_partes(_ec, _un, "", {(_ec or "").strip().upper()})
    except Exception as _e:
        conn.rollback()
        log.warning("cerrar-envasado descuento MEE fallo (rollback): %s", _e)
        return jsonify({"error": "falló el descuento de envases · reintentá", "detalle": str(_e)}), 500
    conn.commit()
    audit_log(None, usuario=user, accion="CERRAR_ENVASADO_DESCONTAR_MEE",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"lote": lote, "descuentos": descuentos,
                       "saltados": _saltados, "sin_libro_mayor": _sin_libro,
                       "redirigidos_a_serigrafiado": _redirigidos})
    # CADENA OF→OA (27-jun · Sebastián) · al CERRAR el envasado se HABILITA automático el legajo de
    # ACONDICIONAMIENTO del mismo lote físico (idempotente vía crear_ebr_desde_mbr · best-effort · NO
    # bloquea el cierre si falla). Espeja el hook fabricación→envasado de liberar_ebr. Así OF→OA deja de
    # ser manual/silencioso (hueco #1): el operario ve el siguiente paso al terminar el envasado.
    _acond_habilitado = None
    try:
        if producto and lote:
            _res_oa = crear_ebr_desde_mbr(conn.cursor(), producto_nombre=producto,
                                          lote=lote, usuario=user, fase='acondicionamiento')
            conn.commit()
            if _res_oa.get('ok'):
                _acond_habilitado = _res_oa.get('id')
            else:
                # ⚠ 17-ago · el caso NORMAL caía acá y devolvía None. El legajo de
                # acondicionamiento suele existir ANTES de cerrar el envasado (lo crea el demo,
                # y el flujo real al aceptar la producción), y entonces `crear_ebr_desde_mbr`
                # contesta LOTE_DUPLICADO -- que no es un error: es "ya está habilitado".
                # Con `acond_ebr_id: None` el operario cierra el envasado y NO recibe el enlace
                # al paso siguiente, que es exactamente lo que este hook vino a resolver
                # (M121/M129: un registro que sale de una pantalla tiene que decir a dónde se fue).
                _ya = conn.execute(
                    "SELECT id FROM ebr_ejecuciones "
                    " WHERE COALESCE(NULLIF(lote_codigo,''), lote)=? "
                    "   AND COALESCE(fase,'')='acondicionamiento' "
                    " ORDER BY id DESC LIMIT 1", (lote,)).fetchone()
                if _ya:
                    _acond_habilitado = _ya[0]
                else:
                    log.warning("cerrar-envasado: no se pudo habilitar el acondicionamiento del "
                                "lote %s: %s", lote, _res_oa.get('error'))
                if not _res_oa.get('reusado'):
                    audit_log(None, usuario=user, accion="AUTO_CREAR_EBR_ACONDICIONAMIENTO",
                              tabla="ebr_ejecuciones", registro_id=_res_oa.get('id'),
                              despues={"origen_envasado_ebr": ebr_id, "lote": lote})
    except Exception as _e2:
        log.warning("auto-crear EBR acondicionamiento al cerrar envasado fallo (no bloquea): %s", _e2)
    return jsonify({"ok": True, "estado": "completado", "descuentos": descuentos,
                    "n_descuentos": len(descuentos), "acond_ebr_id": _acond_habilitado})


# ── ACONDICIONAMIENTO · cierre canónico (27-jun · Sebastián · hueco #2) ──────────────────────────────
# El operario lista los materiales de acondicionamiento consumidos (etiquetas/estuches/insertos · código +
# cantidad); al CERRAR se descuentan vía movimientos_mee (canónico M26 · NUNCA el cache stock_actual) UNA
# sola vez (CAS · M27). Reemplaza el descuento de la ruta legacy /api/acondicionamiento (que tocaba el cache
# sin CAS → drift + doble descuento). Reusa la marca envases_descontados_at como "materiales descontados".
def descontar_mee_del_lote(cur, *, produccion_id, lote, items, usuario, origen):
    """UNA sola puerta para sacar del kardex el material de envase/acondicionamiento de un lote.

    Devuelve `(descuentos, saltados, sin_libro_mayor)`.

    El libro mayor es `produccion_checklist.consumido_at`: dice *"este envase, para esta
    producción, YA salió del kardex"*. Quien descuenta lo RECLAMA con CAS antes de mover nada, así
    que dos caminos distintos sobre el mismo lote no pueden sacar el material dos veces.

    ⚠ Existe porque el patrón ya se pagó dos veces (M162): primero entre el cierre de envasado y
    el del Kanban, y después entre el cierre del legajo de acondicionamiento y el registro de la
    pantalla vieja (`POST /api/acondicionamiento`), que descontaba directo sin mirar el libro
    mayor. **La salida nunca es un candado más: es que todos pasen por el que ya existe** (M3), y
    por eso esto es un helper y no una tercera copia del idiom (M45).

    Reglas que NO se pueden aflojar:
      · El KARDEX registra lo consumido y el cache se mueve con el mismo delta; la Salida **no**
        se clampea contra `maestro_mee.stock_actual`, porque el stock canónico es la suma del
        kardex y clampear ahí registra Salidas en CERO sin un solo error a la vista (M26/M153).
      · Un código que no está en el maestro **no se descuenta y se DECLARA**: los teclea el
        operario, así que uno mal escrito entraría como stock fantasma (M100).
      · Sin `produccion_id` no hay libro mayor que reclamar: se descuenta igual y se declara
        `sin_libro_mayor`. Que un envase no salga del kardex es peor que arriesgar el doble, pero
        un descuento sin coordinar no se puede presentar como coordinado (M124).
    """
    descuentos, saltados = [], []
    _pid = int(produccion_id or 0)
    _ya_consumido, _reclamables = set(), {}
    sin_libro = not _pid
    if _pid:
        try:
            _filas = cur.execute(
                    "SELECT id, UPPER(TRIM(COALESCE(mee_codigo_asignado,''))), "
                    "       COALESCE(consumido_at,'') "
                    "  FROM produccion_checklist "
                    " WHERE produccion_id=? AND COALESCE(mee_codigo_asignado,'')<>''",
                    (_pid,)).fetchall()
            # Tener `produccion_id` no alcanza: si esa producción no tiene NINGÚN envase en el
            # checklist, no hay nada que reclamar y el descuento sigue siendo sin coordinar.
            # Declarar "coordinado" ahí sería la mentira que este campo existe para evitar.
            sin_libro = not _filas
            for _cid, _ccod, _cons in _filas:
                if not _ccod:
                    continue
                if str(_cons or '').strip():
                    _ya_consumido.add(_ccod)
                else:
                    _reclamables.setdefault(_ccod, []).append(_cid)
        except Exception as _e_lib:
            log.warning("descontar_mee_del_lote: no pude leer el checklist de la producción "
                        "%s: %s", _pid, _e_lib)
            sin_libro = True
            _ya_consumido, _reclamables = set(), {}

    for cod, cant in items:
        _obs = "%s lote %s" % (origen, lote or "")
        if not cur.execute("SELECT 1 FROM maestro_mee WHERE UPPER(TRIM(codigo))=UPPER(TRIM(?))",
                           (cod,)).fetchone():
            log.warning("descontar_mee_del_lote: %s no existe en maestro_mee", cod)
            saltados.append({"mee_codigo": cod, "motivo": "no existe en el maestro de envases"})
            continue
        _k = cod.strip().upper()
        if _k in _ya_consumido:
            saltados.append({"mee_codigo": cod,
                             "motivo": "ya consumido en el checklist de esta producción"})
            continue
        _ids = _reclamables.get(_k) or []
        if _ids:
            # RECLAMO con CAS: si el otro camino lo marcó entre la lectura y ahora, `rowcount`
            # es 0 y acá NO se descuenta (M27/M73).
            cur.execute(
                "UPDATE produccion_checklist SET consumido_at=datetime('now','utc') "
                " WHERE id=? AND COALESCE(consumido_at,'')=''", (_ids[0],))
            if cur.rowcount == 0:
                saltados.append({"mee_codigo": cod, "motivo": "otro cierre lo reclamó primero"})
                continue
            _ya_consumido.add(_k)
        cur.execute(
            "INSERT INTO movimientos_mee (mee_codigo, tipo, cantidad, observaciones, "
            " responsable, fecha, batch_ref) "
            "VALUES (?, 'Salida', ?, ?, ?, datetime('now','utc'), ?)",
            (cod, cant, _obs, usuario, lote or ''))
        cur.execute(
            "UPDATE maestro_mee SET stock_actual = CASE WHEN COALESCE(stock_actual,0) - ? < 0 "
            "  THEN 0 ELSE COALESCE(stock_actual,0) - ? END WHERE codigo=?",
            (cant, cant, cod))
        descuentos.append({"mee_codigo": cod, "cantidad": cant})
    return descuentos, saltados, bool(sin_libro)


@bp.route("/api/brd/ebr/<int:ebr_id>/cerrar-acondicionamiento", methods=["POST"])
def cerrar_acondicionamiento_ebr(ebr_id):
    """Cierra el acondicionamiento: descuenta los materiales listados × cantidad (movimientos_mee) UNA vez
    (CAS) y marca completado. Body: {materiales:[{codigo, cantidad}]}. Reversa segura: si el descuento falla,
    rollback (no queda marcado) y se puede reintentar."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    body = request.get_json(silent=True) or {}
    conn = get_db(); cur = conn.cursor()
    erow = cur.execute(
        "SELECT COALESCE(e.lote_codigo, e.lote), COALESCE(e.fase,'fabricacion'), "
        "COALESCE(e.produccion_id, 0) "
        "FROM ebr_ejecuciones e WHERE e.id=?", (ebr_id,)).fetchone()
    if not erow:
        return jsonify({"error": "EBR no encontrado"}), 404
    if str(erow[1]).strip().lower() != "acondicionamiento":
        return jsonify({"error": "este cierre es solo para legajos de acondicionamiento"}), 400
    lote = erow[0] or ""
    items = []
    for it in (body.get("materiales") or []):
        cod = str((it or {}).get("codigo") or (it or {}).get("mee_codigo") or "").strip()
        try:
            cant = float((it or {}).get("cantidad") or 0)
        except (TypeError, ValueError):
            cant = 0
        if cod and cant > 0:
            items.append((cod, cant))
    if not items:
        return jsonify({"error": "listá al menos un material consumido (código + cantidad) antes de cerrar"}), 400
    # CAS idempotente (M27): reclamar el cierre · solo 1 vez y solo si está en proceso (race multi-worker).
    cur.execute(
        "UPDATE ebr_ejecuciones SET envases_descontados_at=datetime('now','utc'), estado='completado', "
        "completado_at_utc=datetime('now','utc') "
        "WHERE id=? AND COALESCE(fase,'')='acondicionamiento' AND COALESCE(envases_descontados_at,'')='' "
        "AND estado IN ('iniciado','en_proceso')", (ebr_id,))
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "El acondicionamiento ya se cerró/descontó o no está en proceso · refrescá",
                        "codigo": "YA_CERRADO"}), 409
    # UNA sola puerta al kardex (M3): el mismo helper que usa el registro de acondicionamiento
    # de la pantalla vieja, así los dos caminos reclaman el MISMO libro mayor y el material no
    # puede salir dos veces (M162).
    try:
        descuentos, saltados, _sin_libro = descontar_mee_del_lote(
            cur, produccion_id=int(erow[2] or 0), lote=lote, items=items, usuario=user,
            origen="Acondicionamiento EBR-" + str(ebr_id))
    except Exception as _e:
        conn.rollback()
        log.warning("cerrar-acondicionamiento descuento MEE fallo (rollback): %s", _e)
        return jsonify({"error": "falló el descuento de materiales · reintentá", "detalle": str(_e)}), 500
    conn.commit()
    audit_log(None, usuario=user, accion="CERRAR_ACONDICIONAMIENTO_DESCONTAR_MEE",
              tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"lote": lote, "descuentos": descuentos, "saltados": saltados})
    return jsonify({"ok": True, "estado": "completado", "descuentos": descuentos,
                    "n_descuentos": len(descuentos), "saltados": saltados,
                    # Lo que NO se pudo coordinar se DECLARA: un descuento sin libro mayor no
                    # se puede presentar como coordinado, y si mañana aparece un descuadre
                    # tiene que haber quedado dicho por qué (M100/M124).
                    "sin_libro_mayor": bool(_sin_libro)})


# ── DEMO de planta (27-jun · Sebastián) · seeder one-click para ver el flujo fabricación→envasado ─────────
_DEMO_PLANTA_PROD = "DEMO PLANTA (BORRAR)"
_DEMO_PLANTA_LOTE = "DEMO-PLANTA-1"
# Lote de la materia prima que el demo siembra en bodega · prefijo DEMO- para poder retirarlo
# entero y para que se distinga a simple vista de un lote real en el kardex.
_DEMO_MP_LOTE = "DEMO-MP-1"


@bp.route("/api/admin/planta-demo/crear", methods=["POST"])
def crear_planta_demo():
    """Crea (idempotente) un legajo DEMO de planta: producto+fórmula+MBR aprobado+presentación, y los legajos
    de FABRICACIÓN y ENVASADO del mismo lote, para ver el flujo paso a paso. Producto/lote claramente marcados
    DEMO → se borran luego con 🗑️. Solo admin."""
    try:
        from config import ADMIN_USERS as _ADM
    except Exception:
        _ADM = {"sebastian", "alejandro"}
    if session.get("compras_user", "") not in _ADM:
        return jsonify({"error": "solo admin"}), 403
    user = session.get("compras_user", "")
    PROD, LOTE = _DEMO_PLANTA_PROD, _DEMO_PLANTA_LOTE
    conn = get_db(); cur = conn.cursor()
    try:
        for c_, n_ in (("MP-DEMO1", "Demo Base"), ("MP-DEMO2", "Demo Activo")):
            cur.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) VALUES (?,?,1)", (c_, n_))
        # Las CUATRO piezas del empaque, no sólo el frasco. Sin la tapa, la caja y la etiqueta,
        # el legajo de envasado abre con "Materiales de Envase" VACÍO y el de acondicionamiento
        # con "Materiales de Empaque" vacío -- que es justo lo que se quiere mirar en el demo.
        for _c_mee, _d_mee in (("ENV-DEMO", "Frasco demo 30ml"),
                               ("TAPA-DEMO", "Tapa demo"),
                               ("CAJA-DEMO", "Estuche demo"),
                               ("ETIQ-DEMO", "Etiqueta demo")):
            cur.execute("INSERT OR IGNORE INTO maestro_mee (codigo, descripcion, stock_actual, estado) "
                        "VALUES (?,?,1000,'Activo')", (_c_mee, _d_mee))
        if not cur.execute("SELECT 1 FROM formula_headers WHERE producto_nombre=?", (PROD,)).fetchone():
            cur.execute("INSERT INTO formula_headers (producto_nombre, lote_size_kg, activo) VALUES (?, 1, 1)", (PROD,))
        if not cur.execute("SELECT 1 FROM formula_items WHERE producto_nombre=?", (PROD,)).fetchone():
            for c_, n_, pct in (("MP-DEMO1", "Demo Base", 90), ("MP-DEMO2", "Demo Activo", 10)):
                cur.execute("INSERT INTO formula_items (producto_nombre, material_id, material_nombre, porcentaje, "
                            "cantidad_g_por_lote) VALUES (?,?,?,?,?)", (PROD, c_, n_, pct, pct * 10))
        if not cur.execute("SELECT 1 FROM producto_presentaciones WHERE producto_nombre=?", (PROD,)).fetchone():
            cur.execute("INSERT INTO producto_presentaciones (producto_nombre, presentacion_codigo, etiqueta, "
                        "volumen_ml, envase_codigo, tapa_codigo, caja_codigo, activo) "
                        "VALUES (?, 'DEMO30', '30ml', 30, 'ENV-DEMO', 'TAPA-DEMO', 'CAJA-DEMO', 1)", (PROD,))
        else:
            # Un demo sembrado ANTES de que existieran las partes se queda sin tapa ni caja para
            # siempre: se completan sin pisar nada que ya tenga valor.
            cur.execute("UPDATE producto_presentaciones "
                        "   SET tapa_codigo=COALESCE(NULLIF(tapa_codigo,''),'TAPA-DEMO'), "
                        "       caja_codigo=COALESCE(NULLIF(caja_codigo,''),'CAJA-DEMO') "
                        " WHERE producto_nombre=?", (PROD,))
        mbr = cur.execute("SELECT id FROM mbr_templates WHERE producto_nombre=? AND estado='aprobado'",
                          (PROD,)).fetchone()
        if not mbr:
            cur.execute("INSERT INTO mbr_templates (producto_nombre, version, estado, lote_size_g, creado_por) "
                        "VALUES (?, 1, 'draft', 1000, ?)", (PROD, user))
            mbr_id = cur.lastrowid
            # Pasos POR FASE · Sebastián, mirando el legajo de envasado del demo: *"Este MBR no
            # tiene pasos"* y arriba **0/5 pasos**. Los cuatro pasos se creaban SIN `fase`, así
            # que el legajo de envasado no encontraba ninguno y no había flujo que caminar --
            # que era justamente el punto del demo (M205: los pasos se declaran por fase).
            #
            # Llevan `tiempo_estimado_min` para que el plano pueda comparar real contra estimado
            # mientras se camina el demo, que es lo que Sebastián quiere mirar con Alejandro.
            _pasos_demo = (
                ("Fabricación", "mezclado", (
                    ("Dispensar materias primas", 20),
                    ("Mezclar 20 min a 40°C", 20),
                    ("Control de pH y viscosidad", 10),
                    ("Enfriar hasta 25°C", 15))),
                ("Envasado", "envasado", (
                    ("Despeje de línea de envasado", 10),
                    ("Purgar y ajustar el llenado", 15),
                    ("Envasar y sellar", 45),
                    ("Control de llenado por muestreo", 10))),
                ("Acondicionamiento", "acondicionamiento", (
                    ("Etiquetar las unidades", 25),
                    ("Estuchar y codificar", 20),
                    ("Inspección final del producto terminado", 15))),
            )
            _o = 0
            for _fase_p, _tipo_p, _lista in _pasos_demo:
                for _dsc, _min in _lista:
                    _o += 1
                    cur.execute(
                        "INSERT INTO mbr_pasos (mbr_template_id, orden, fase, descripcion, "
                        "                       tipo_paso, tiempo_estimado_min) "
                        "VALUES (?,?,?,?,?,?)",
                        (mbr_id, _o, _fase_p, _dsc, _tipo_p, _min))
            cur.execute("UPDATE mbr_templates SET estado='aprobado' WHERE id=?", (mbr_id,))
        # Materia prima EN BODEGA para el demo · Sebastián, caminándolo: *"ahora dice stock
        # insuficiente para el demo"*. El demo creaba las MP en el maestro y NINGUNA entrada al
        # kardex, así que nacía con stock CERO y se trababa al arrancar la producción: un demo
        # que no se puede caminar no sirve para nada (M121, otra vez).
        #
        # Es seguro sembrar acá porque `MP-DEMO1`/`MP-DEMO2` son códigos PROPIOS del demo -- no
        # existen en la realidad --, así que esto no infla el inventario de ninguna materia prima
        # de verdad. El lote lleva el prefijo DEMO- para poder retirarlo entero después.
        # Se siembra lo que LA FÓRMULA PIDE, no una lista fija de códigos · Sebastián, dos veces
        # seguidas: *"Stock insuficiente para producir DEMO PLANTA (BORRAR): 2 MP(s) sin stock"*,
        # incluso después de sembrar MP-DEMO1/2.
        #
        # La primera versión sembraba esos dos códigos a mano, y `crear_planta_demo` sólo crea la
        # fórmula SI NO EXISTE: un demo creado antes (con otros materiales) se queda con SU
        # fórmula, así que el stock caía en códigos que nadie pedía. Leerlo de `formula_items` lo
        # hace correcto sea cual sea la fórmula que el demo tenga hoy (M1: preguntarle a la
        # fuente, no repetir una lista).
        #
        # Y se REPONE cuando está bajo, no sólo la primera vez: cada vuelta del demo consume MP,
        # así que un guard de "¿ya hay algún movimiento?" lo dejaba seco a la segunda. El umbral
        # mira el stock CANÓNICO (suma del kardex sin lo retenido), que es lo que ve producción.
        _mp_demo = [r[0] for r in cur.execute(
            "SELECT DISTINCT material_id FROM formula_items "
            "WHERE producto_nombre=? AND COALESCE(material_id,'')<>''", (PROD,)).fetchall()]
        if not _mp_demo:
            _mp_demo = ["MP-DEMO1", "MP-DEMO2"]
        for _c in _mp_demo:
            # el material tiene que existir en el maestro o el trigger rechaza el movimiento
            cur.execute("INSERT OR IGNORE INTO maestro_mps (codigo_mp, nombre_inci, activo) "
                        "VALUES (?, 'Demo', 1)", (_c,))
            try:
                _st = cur.execute(
                    "SELECT COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA',"
                    "        'Ajuste +','Ajuste') THEN cantidad "
                    "        WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') "
                    "        THEN -cantidad ELSE 0 END),0) "
                    "FROM movimientos WHERE material_id=? "
                    "  AND UPPER(COALESCE(estado_lote,'')) NOT IN "
                    "      ('CUARENTENA','CUARENTENA_EXTENDIDA','VENCIDO','RECHAZADO',"
                    "       'AGOTADO','BLOQUEADO')", (_c,)).fetchone()[0] or 0
            except Exception:
                _st = 0
            if float(_st) < 5000:
                cur.execute(
                    "INSERT INTO movimientos (material_id, material_nombre, tipo, cantidad, lote, "
                    "                         fecha, fecha_vencimiento, estado_lote, operador, "
                    "                         observaciones) "
                    "VALUES (?, 'Materia prima de demostración', 'Entrada', 50000, ?, "
                    "        date('now','-5 hours'), date('now','-5 hours','+2 years'), "
                    "        'VIGENTE', ?, 'Stock sembrado por el demo de planta')",
                    (_c, _DEMO_MP_LOTE, user))

        def _legajo(_fase):
            # Idempotente: si el legajo del lote demo ya existe, reusarlo (crear_ebr_desde_mbr solo reusa por
            # produccion_id, que acá es None → sin esto daría LOTE_DUPLICADO al re-crear el demo).
            _ex = cur.execute("SELECT id, COALESCE(estado,'') FROM ebr_ejecuciones "
                              "WHERE COALESCE(lote_codigo,lote)=? "
                              "AND COALESCE(fase,'fabricacion')=?", (LOTE, _fase)).fetchone()
            if _ex:
                # El legajo se REACTIVA si quedó descartado o cerrado · Sebastián abrió el demo
                # y arriba decía `descartado`: un legajo muerto no se puede caminar, así que
                # "crear el demo" tiene que devolverlo utilizable o el botón no sirve para nada.
                # Sólo aplica a lotes DEMO- (un legajo real descartado NO se revive así).
                if str(_ex[1]).lower() in ("descartado", "rechazado", "liberado", "completado"):
                    cur.execute("UPDATE ebr_ejecuciones SET estado='iniciado', "
                                "    liberado_at_utc=NULL, liberado_por=NULL, "
                                "    completado_at_utc=NULL, aprobado_dt_por=NULL, "
                                "    aprobado_dt_at_utc=NULL "
                                "WHERE id=? AND COALESCE(lote_codigo,lote) LIKE 'DEMO-%'",
                                (_ex[0],))
                return {'ok': True, 'id': _ex[0], 'reusado': True,
                        'reactivado': str(_ex[1]).lower() in ("descartado", "rechazado",
                                                              "liberado", "completado")}
            return crear_ebr_desde_mbr(cur, producto_nombre=PROD, lote=LOTE, usuario=user, fase=_fase)
        op = _legajo('fabricacion')
        of = _legajo('envasado')
        # y el de ACONDICIONAMIENTO, que faltaba: sin él no se puede caminar hasta el final ni
        # ver el visto bueno del Director Técnico, que es justo donde vive ahora
        oa = _legajo('acondicionamiento')
        if not op.get('ok') or not of.get('ok') or not oa.get('ok'):
            conn.rollback()
            return jsonify({"error": "no se pudieron crear los legajos",
                            "op": op, "of": of, "oa": oa}), 500
        audit_log(cur, usuario=user, accion="CREAR_PLANTA_DEMO", tabla="ebr_ejecuciones",
                  registro_id=op.get('id'), despues={"producto": PROD, "lote": LOTE})
        conn.commit()
        return jsonify({"ok": True, "producto": PROD, "lote": LOTE,
                        "fabricacion_ebr": op.get('id'), "envasado_ebr": of.get('id'),
                        "acondicionamiento_ebr": oa.get('id'),
                        # Con qué caminar las dos fases siguientes POR LOS ENDPOINTS REALES
                        # (`/api/envasado` y `/api/acondicionamiento`), que es lo que hace la
                        # planta: el demo no siembra filas a mano en las tablas de esas fases,
                        # porque entonces mostraría una pantalla que nadie llenó así (M153).
                        "caminar": {
                            "presentacion": "DEMO30", "envase_codigo": "ENV-DEMO",
                            "tapa_codigo": "TAPA-DEMO", "caja_codigo": "CAJA-DEMO",
                            "etiqueta_codigo": "ETIQ-DEMO",
                            "batch_g": 900, "unidades": 30,
                        },
                        "reusado": bool(op.get('reusado') and of.get('reusado')
                                        and oa.get('reusado')),
                        # se DICE si habia que revivir un legajo muerto, en vez de que el
                        # boton conteste "ok" y el usuario descubra el `descartado` adentro
                        "reactivados": [k for k, v in (('fabricacion', op), ('envasado', of),
                                                       ('acondicionamiento', oa))
                                        if v.get('reactivado')]})
    except Exception as e:
        conn.rollback()
        log.warning("crear_planta_demo fallo: %s", e)
        return jsonify({"error": str(e)}), 500


@bp.route("/admin/planta-demo", methods=["GET"])
def planta_demo_pagina():
    if 'compras_user' not in session:
        return redirect('/login?next=/admin/planta-demo')
    try:
        from config import ADMIN_USERS as _ADM
    except Exception:
        _ADM = {"sebastian", "alejandro"}
    if session.get('compras_user', '') not in _ADM:
        return ("<html><body style='font-family:system-ui;padding:48px'><h2>Solo admin</h2></body></html>"), 403
    return Response(_PLANTA_DEMO_HTML, mimetype='text/html')


_PLANTA_DEMO_HTML = """<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Demo de planta &middot; EOS</title><style>
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;background:var(--cx-primary-pale, #f5f3ff);color:var(--cx-text, #1e1b4b);padding:32px;max-width:720px;margin:0 auto}
h1{font-size:22px;color:var(--cx-primary-text, #5b21b6);margin-bottom:4px}
.sub{color:var(--cx-text-mute, #64748b);font-size:13.5px;margin:0 0 4px}
.card{background:var(--cx-card, #fff);border:1px solid var(--cx-border-soft, #e9d5ff);border-radius:14px;padding:20px;margin-top:16px}
.card h2{font-size:15px;margin:0 0 6px;color:var(--cx-text, #1e1b4b)}
.paso{display:flex;align-items:center;gap:8px;font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--cx-primary-text, #6d28d9);margin-bottom:8px}
button{background:var(--cx-primary-grad, linear-gradient(135deg,#a78bfa,#6d28d9));color:#fff;border:none;border-radius:10px;padding:12px 20px;font-size:14px;font-weight:700;cursor:pointer}
button[disabled]{opacity:.45;cursor:not-allowed}
.ok{background:var(--cx-success-pale, #ecfdf5);border:1px solid var(--cx-success-light, #6ee7b7);border-radius:10px;padding:14px;margin-top:14px;font-size:13px;display:none;line-height:1.55}
.bad{background:var(--cx-danger-pale, #fee2e2);border-color:var(--cx-danger-light, #fca5a5)}
.datos{font-size:12.5px;color:var(--cx-text-mute, #64748b);margin-top:10px;line-height:1.6}
code{background:var(--cx-bg-alt, #f1f5f9);border-radius:4px;padding:1px 5px;font-size:12px}
a{color:var(--cx-primary-text, #6d28d9);font-weight:700}</style></head><body>
<h1>&#127916; Demo de planta</h1>
<p class="sub">Un lote <b>DEMO</b> que recorre las tres fases. Se camina por los <b>mismos endpoints
que usa la planta</b>, as&iacute; que lo que ves es lo que ver&iacute;a un operario.</p>

<div class="card">
  <div class="paso">Paso 1 &middot; el lote</div>
  <h2>Crear el lote y sus tres legajos</h2>
  <p class="sub">Producto "DEMO PLANTA (BORRAR)" &middot; lote DEMO-PLANTA-1, con materia prima en
  bodega, las cuatro piezas del empaque y un instructivo con pasos por fase.</p>
  <button id="b1" onclick="crear()">Crear el lote demo</button>
  <div class="ok" id="ok1"></div>
</div>

<div class="card">
  <div class="paso">Paso 2 &middot; envasado</div>
  <h2>Caminar el envasado</h2>
  <p class="sub">Registra el envasado real del lote. Con esto el legajo de envasado deja de abrir
  vac&iacute;o: aparecen las <b>unidades por presentaci&oacute;n</b> y los <b>materiales de envase</b>.</p>
  <button id="b2" onclick="caminarEnvasado()" disabled>Caminar envasado</button>
  <div class="ok" id="ok2"></div>
</div>

<div class="card">
  <div class="paso">Paso 3 &middot; acondicionamiento</div>
  <h2>Caminar el acondicionamiento</h2>
  <p class="sub">Registra el acondicionamiento y consume la etiqueta y el estuche. Con esto el
  legajo de acondicionamiento muestra sus <b>unidades</b> y su <b>material de empaque</b>.</p>
  <button id="b3" onclick="caminarAcond()" disabled>Caminar acondicionamiento</button>
  <div class="ok" id="ok3"></div>
</div>

<p class="datos">Cuando termines de verlo, borralo con el bot&oacute;n de la papelera en la lista de
&oacute;rdenes. Todo lo que siembra el demo lleva <code>DEMO</code> en el producto, el lote y los
c&oacute;digos, para que no se confunda con nada real.</p>

<script>
var DEMO=null, ENVID=0, BUSY=false;
function pinta(id, html, malo){
  var e=document.getElementById(id);
  e.style.display='block';
  if(malo){ e.className='ok bad'; } else { e.className='ok'; }
  e.innerHTML=html;
}
async function tok(){
  try{ return (await (await fetch('/api/csrf-token',{credentials:'same-origin'})).json()).csrf_token||''; }
  catch(e){ return ''; }
}
async function pide(url, body){
  var t=await tok();
  var r=await fetch(url,{method:'POST',credentials:'same-origin',
    headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify(body||{})});
  var d={}; try{ d=await r.json(); }catch(e){}
  return {ok:r.ok, d:d, status:r.status};
}
function conBoton(id, fn){
  // Un demo se aprieta dos veces por costumbre: sin esto, el segundo click registra
  // OTRO envasado del mismo lote (M63 - toda accion que INSERTA necesita su guard).
  return async function(){
    if(BUSY) return; BUSY=true;
    var b=document.getElementById(id); if(b) b.disabled=true;
    try{ await fn(); } finally { BUSY=false; if(b) b.disabled=false; }
  };
}
var crear = conBoton('b1', async function(){
  var r=await pide('/api/admin/planta-demo/crear', {});
  if(!r.ok){ pinta('ok1', r.d.error||('Error '+r.status), true); return; }
  DEMO=r.d;
  var c=DEMO.caminar||{};
  pinta('ok1', '&#10004; Demo '+(DEMO.reusado?'ya exist&iacute;a':'creado')+
    ' &middot; producto <b>'+DEMO.producto+'</b> &middot; lote <b>'+DEMO.lote+'</b>.'+
    '<br>Legajos: <a href="/planta/orden/'+DEMO.fabricacion_ebr+'" target="_blank">fabricaci&oacute;n</a>'+
    ' &middot; <a href="/planta/legajo-envasado/'+DEMO.envasado_ebr+'" target="_blank">envasado</a>'+
    ' &middot; <a href="/planta/legajo-acondicionamiento/'+DEMO.acondicionamiento_ebr+'" target="_blank">acondicionamiento</a>'+
    '<div class="datos">Va a envasar <b>'+(c.unidades||0)+' unidades</b> de '+(c.presentacion||'')+
    ' con <code>'+(c.envase_codigo||'')+'</code> y <code>'+(c.tapa_codigo||'')+'</code>.</div>');
  document.getElementById('b2').disabled=false;
});
var caminarEnvasado = conBoton('b2', async function(){
  if(!DEMO){ pinta('ok2','Primero cre&aacute; el lote (paso 1).', true); return; }
  var c=DEMO.caminar||{};
  var r=await pide('/api/envasado', {lote:DEMO.lote, producto:DEMO.producto,
    presentacion:c.presentacion, batch_g:c.batch_g, unidades:c.unidades,
    envase_codigo:c.envase_codigo, tapa_codigo:c.tapa_codigo,
    observaciones:'Envasado del demo de planta'});
  if(!r.ok){ pinta('ok2', r.d.error||('Error '+r.status), true); return; }
  ENVID=r.d.id||0;
  pinta('ok2','&#10004; Envasado registrado &middot; '+(c.unidades||0)+' unidades de '+c.presentacion+
    '.<br><a href="/planta/legajo-envasado/'+DEMO.envasado_ebr+'" target="_blank">Abrir el legajo de envasado &rarr;</a>'+
    ' &mdash; ahora tiene unidades por presentaci&oacute;n y materiales de envase.');
  document.getElementById('b3').disabled=false;
});
var caminarAcond = conBoton('b3', async function(){
  if(!DEMO){ pinta('ok3','Primero cre&aacute; el lote (paso 1).', true); return; }
  var c=DEMO.caminar||{};
  var r=await pide('/api/acondicionamiento', {envasado_id:ENVID, lote:DEMO.lote,
    producto:DEMO.producto, presentacion:c.presentacion, batch_g:c.batch_g,
    unidades:c.unidades, observaciones:'Acondicionamiento del demo de planta',
    mee_consumido:[{codigo:c.etiqueta_codigo, cantidad:c.unidades},
                   {codigo:c.caja_codigo, cantidad:c.unidades}]});
  if(!r.ok){ pinta('ok3', r.d.error||('Error '+r.status), true); return; }
  var n=(r.d.descuentos||[]).length, salt=(r.d.saltados||[]).length;
  pinta('ok3','&#10004; Acondicionamiento registrado &middot; '+n+' material(es) descontado(s)'+
    (salt?(' &middot; '+salt+' saltado(s) porque ya los consumi&oacute; el legajo'):'')+
    '.<br><a href="/planta/legajo-acondicionamiento/'+DEMO.acondicionamiento_ebr+'" target="_blank">Abrir el legajo de acondicionamiento &rarr;</a>');
});
</script></body></html>"""


@bp.route("/api/brd/lote/<lote>/fases", methods=["GET"])
def lote_fases_ebr(lote):
    """Trazabilidad de un LOTE físico end-to-end (#8 auditoría planta · INVIMA) · sus legajos de Fabricación
    (OP) + Envasado (OF) + Acondicionamiento (OA) JUNTOS, ordenados por fase. Antes el mismo lote aparecía
    3 veces aislado (ordenes-unificadas filtra por UNA fase)."""
    err = _require_login()
    if err:
        return err
    conn = get_db()
    _ORD = {'fabricacion': 1, 'envasado': 2, 'acondicionamiento': 3}
    rows = conn.execute(
        "SELECT id, COALESCE(fase,'fabricacion'), COALESCE(numero_op,''), COALESCE(estado,''), "
        "COALESCE(iniciado_por,''), COALESCE(iniciado_at_utc,''), COALESCE(completado_at_utc,''), "
        "COALESCE(yield_pct,0) FROM ebr_ejecuciones "
        "WHERE COALESCE(NULLIF(lote_codigo,''), lote)=?", (lote,)).fetchall()
    items = sorted([{
        'ebr_id': r[0], 'fase': r[1], 'numero_op': r[2], 'estado': r[3],
        'iniciado_por': r[4], 'iniciado_at': r[5], 'completado_at': r[6], 'yield_pct': r[7],
    } for r in rows], key=lambda x: _ORD.get(x['fase'], 9))
    return jsonify({"ok": True, "lote": lote, "fases": items, "total": len(items)})


@bp.route("/api/brd/ebr/<int:ebr_id>/artes", methods=["GET"])
def listar_artes_codificacion(ebr_id):
    """Artes/codificación del legajo (gate de etiquetado · MyBatch OA)."""
    err = _require_login()
    if err:
        return err
    rows = get_db().execute(
        """SELECT id, ebr_id, descripcion, codigo_lote, codigo_vencimiento,
                  COALESCE(aprobado_por,'') AS aprobado_por, aprobado_at_utc,
                  e_sign_id, creado_por, creado_at_utc, notas
           FROM ebr_artes_codificacion WHERE ebr_id = ? ORDER BY id""",
        (ebr_id,),
    ).fetchall()
    return jsonify({"items": [dict(r) for r in rows]})


@bp.route("/api/brd/ebr/<int:ebr_id>/artes", methods=["POST"])
def registrar_arte_codificacion(ebr_id):
    """Registra una línea de arte/codificación (descripción + código lote/venc).
    Aún sin aprobar · la aprobación va por /artes/<id>/aprobar con e-firma."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    desc = (body.get("descripcion") or "").strip()
    if not desc:
        return jsonify({"error": "descripcion requerida"}), 400
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_artes_codificacion
             (ebr_id, descripcion, codigo_lote, codigo_vencimiento,
              creado_por, creado_at_utc, notas)
           VALUES (?, ?, ?, ?, ?, datetime('now', 'utc'), ?)""",
        (ebr_id, desc, (body.get("codigo_lote") or "").strip(),
         (body.get("codigo_vencimiento") or "").strip(), user,
         (body.get("notas") or "").strip()),
    )
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_ARTE_CODIFICACION",
              tabla="ebr_artes_codificacion", registro_id=rid,
              despues={"ebr_id": ebr_id, "descripcion": desc})
    conn.commit()
    return jsonify({"ok": True, "id": rid}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/artes/<int:arte_id>/aprobar",
          methods=["POST"])
def aprobar_arte_codificacion(ebr_id, arte_id):
    """Aprueba el arte/codificación (gate de etiquetado). Solo Calidad/Admin,
    con e-firma meaning='aprueba'. No re-aprueba."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    if user not in (CALIDAD_USERS | ADMIN_USERS):
        return jsonify({
            "error": "Solo Calidad o Admin aprueban artes/codificación"
        }), 403
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")

    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    arte = cur.execute(
        """SELECT id, COALESCE(aprobado_por,'') AS aprobado_por
           FROM ebr_artes_codificacion WHERE id = ? AND ebr_id = ?""",
        (arte_id, ebr_id),
    ).fetchone()
    if not arte:
        return jsonify({"error": "arte/codificación no encontrada"}), 404
    if (arte["aprobado_por"] or "").strip():
        return jsonify({"error": "arte/codificación ya aprobada"}), 409
    if not signature_id:
        return jsonify({
            "error": "aprobación requiere e-signature · meaning='aprueba' "
                      "record_table='ebr_artes_codificacion'",
            "arte_id": arte_id,
        }), 400
    if not _validar_signature(
        cur, signature_id, record_table="ebr_artes_codificacion",
        record_id=arte_id, meaning="aprueba", signer_username=user,
    ):
        return jsonify({"error": "signature_id inválido para esta aprobación"}), 400

    cur.execute(
        """UPDATE ebr_artes_codificacion
             SET aprobado_por = ?, aprobado_at_utc = datetime('now', 'utc'),
                 e_sign_id = ?
           WHERE id = ?""",
        (user, int(signature_id), arte_id),
    )
    audit_log(cur, usuario=user, accion="APROBAR_ARTE_CODIFICACION",
              tabla="ebr_artes_codificacion", registro_id=arte_id,
              despues={"ebr_id": ebr_id, "aprobado_por": user})
    conn.commit()
    return jsonify({"ok": True, "aprobado_por": user})


@bp.route("/api/brd/ebr/<int:ebr_id>/observaciones", methods=["GET"])
def listar_observaciones_ebr(ebr_id):
    """Bitácora de observaciones generales del proceso (MyBatch)."""
    err = _require_login()
    if err:
        return err
    rows = get_db().execute(
        """SELECT id, ebr_id, descripcion, registrado_por, registrado_at_utc
           FROM ebr_observaciones WHERE ebr_id = ? ORDER BY id""",
        (ebr_id,),
    ).fetchall()
    return jsonify({"items": [dict(r) for r in rows]})


@bp.route("/api/brd/ebr/<int:ebr_id>/observaciones", methods=["POST"])
def registrar_observacion_ebr(ebr_id):
    """Agrega una observación general al legajo (append-only · solo EBR editable)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    desc = (body.get("descripcion") or "").strip()
    if not desc:
        return jsonify({"error": "descripcion requerida"}), 400
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute(
        "SELECT estado FROM ebr_ejecuciones WHERE id = ?", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_observaciones
             (ebr_id, descripcion, registrado_por, registrado_at_utc)
           VALUES (?, ?, ?, datetime('now', 'utc'))""",
        (ebr_id, desc[:1000], user),
    )
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_OBSERVACION_EBR",
              tabla="ebr_observaciones", registro_id=rid,
              despues={"ebr_id": ebr_id})
    conn.commit()
    return jsonify({"ok": True, "id": rid}), 201


# ── MyBatch ② · Despeje de línea ────────────────────────────────────────────
@bp.route("/api/brd/ebr/<int:ebr_id>/despeje", methods=["GET"])
def listar_despeje_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    try:
        rows = get_db().execute(
            "SELECT * FROM ebr_despeje_linea WHERE ebr_id=? ORDER BY id DESC",
            (ebr_id,)).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    except Exception:
        return jsonify({"items": []})


@bp.route("/api/brd/ebr/<int:ebr_id>/despeje-items", methods=["GET"])
def listar_despeje_items_ebr(ebr_id):
    """Checklist granular de despeje (13 ítems GMP estándar) por etapa: dispensacion + fabricacion
    (MyBatch secciones 2 y 4). Cada ítem: idx, texto, cumple (1/0/None), observaciones, registrado_por."""
    err = _require_login()
    if err:
        return err
    conn = get_db()

    def _chk(etapa):
        return despeje_checklist(conn, ebr_id, etapa)

    return jsonify({"dispensacion": _chk("dispensacion"), "fabricacion": _chk("fabricacion")})


@bp.route("/api/brd/ebr/<int:ebr_id>/despeje", methods=["POST"])
def registrar_despeje_ebr(ebr_id):
    """Registra el despeje de línea del legajo (checklist CUMPLE · MyBatch ②)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    def _b(k):
        return 1 if body.get(k) in (1, True, '1', 'true', 'on') else 0
    al, sp, eq, doc = _b("area_limpia"), _b("sin_producto_anterior"), _b("equipos_limpios"), _b("documentacion_ok")
    conforme = 1 if (al and sp and eq and doc) else 0
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_despeje_linea
             (ebr_id, area_limpia, sin_producto_anterior, equipos_limpios,
              documentacion_ok, conforme, observaciones, realizado_por,
              realizado_at_utc)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now','utc'))""",
        (ebr_id, al, sp, eq, doc, conforme,
         (body.get("observaciones") or "").strip()[:500], user))
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_DESPEJE_EBR",
              tabla="ebr_despeje_linea", registro_id=rid,
              despues={"ebr_id": ebr_id, "conforme": conforme})
    conn.commit()
    return jsonify({"ok": True, "id": rid, "conforme": conforme}), 201


# ── MyBatch ② detalle · Despeje de línea por ÍTEM (checklist 13 verificaciones) ──
@bp.route("/api/brd/ebr/<int:ebr_id>/despeje-item", methods=["POST"])
def registrar_despeje_item_ebr(ebr_id):
    """Registra el CUMPLE (Sí/No) de UNA verificación del despeje de línea.
    Botón ✏️ de la tabla VERIFICACIÓN/CUMPLE/ACCIONES (MyBatch ② detalle)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    try:
        idx = int(body.get("item_idx"))
    except (TypeError, ValueError):
        return jsonify({"error": "item_idx inválido"}), 400
    if idx < 0 or idx >= len(DESPEJE_LINEA_ITEMS):
        return jsonify({"error": "item_idx fuera de rango"}), 400
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    cumple = 1 if body.get("cumple") in (1, True, '1', 'true', 'on', 'si', 'Si', 'sí') else 0
    obs = (body.get("observaciones") or "").strip()[:500]
    etapa = (body.get("etapa") or "dispensacion").strip().lower()
    if etapa not in ("dispensacion", "fabricacion"):
        etapa = "dispensacion"
    user = session.get("compras_user", "")
    texto = DESPEJE_LINEA_ITEMS[idx]
    # DOS ROLES (Sebastián 6-jun-2026): el despeje lo REGISTRA el operario; SOLO
    # Calidad/Dirección Técnica puede CORREGIR un resultado ya registrado (botón
    # "Corregir Resultado" de MyBatch). Trazabilidad INVIMA: queda en audit_log
    # quién registró y quién corrigió.
    prev = cur.execute(
        "SELECT cumple, COALESCE(observaciones,''), COALESCE(registrado_por,'') "
        "FROM ebr_despeje_items WHERE ebr_id=? AND item_idx=? AND COALESCE(etapa,'dispensacion')=?",
        (ebr_id, idx, etapa)).fetchone()
    es_correccion = bool(prev and prev[0] is not None)
    # Corregir un resultado ya registrado = atribución de quien CORRIGE (Calidad / Aseguramiento /
    # Dir. Técnica / Admin · resolver canónico _batch_role_info, consistente con la sección Correcciones).
    es_calidad = bool(_batch_role_info(user).get("corrige"))
    # el legajo DEMO lo camina una sola persona: corregir un ítem ahí es parte de lo que se
    # viene a comprobar, no un acto sobre un registro real
    if es_correccion and not es_calidad and not _es_demo_ebr(cur, ebr_id):
        return jsonify({
            "error": "Corregir un resultado ya registrado es atribución de Calidad / "
                     "Dirección Técnica. El operario solo registra el despeje inicial.",
            "codigo": "SOLO_CALIDAD_CORRIGE",
        }), 403
    # SUPERVISIÓN por ALERTA, no por bloqueo (Sebastián 7-jul · v2): el operario VA HACIENDO sin trabarse; cada
    # ítem que marca le AVISA a Calidad (campana) para que esté al lado verificando. La firma dual sigue: nadie
    # libera el lote sin que Calidad verifique todo (gate de liberar_ebr). Se quitó el "marcar todo" (riesgo de
    # diligenciar sin mirar) → el operario marca uno por uno, pero sin esperar. Ver el push_notif tras el commit.
    # Upsert por (ebr_id, item_idx, etapa) · índice único de mig 222.
    cur.execute(
        """INSERT INTO ebr_despeje_items
             (ebr_id, item_idx, item_texto, cumple, observaciones,
              registrado_por, registrado_at_utc, etapa)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now','utc'), ?)
           ON CONFLICT(ebr_id, item_idx, etapa) DO UPDATE SET
             cumple=excluded.cumple, observaciones=excluded.observaciones,
             registrado_por=excluded.registrado_por,
             registrado_at_utc=excluded.registrado_at_utc""",
        (ebr_id, idx, texto, cumple, obs, user, etapa))
    audit_log(cur, usuario=user,
              accion=("CORREGIR_DESPEJE_ITEM_EBR" if es_correccion else "REGISTRAR_DESPEJE_ITEM_EBR"),
              tabla="ebr_despeje_items", registro_id=ebr_id,
              antes=({"cumple": prev[0], "observaciones": prev[1], "registrado_por": prev[2]} if es_correccion else None),
              despues={"ebr_id": ebr_id, "item_idx": idx, "cumple": cumple, "por": user})
    conn.commit()
    # Sebastián 7-jul (v3): SIN aviso por-ítem (evita fatiga de campana) · la ÚNICA alerta es la de inicio de
    # fabricación (iniciar_ebr). Los pendientes los ve Calidad en su bandeja "Mi trabajo". El tiempo de respuesta
    # (aviso → 1ª verificación) se mide server-side desde iniciado_at_utc vs MIN(verificado_at_utc).
    return jsonify({"ok": True, "item_idx": idx, "cumple": cumple,
                    "correccion": es_correccion}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/despeje-verificar", methods=["POST"])
def verificar_despeje_item_ebr(ebr_id):
    """2ª firma de Calidad sobre el despeje (regla 2 personas · MyBatch · 25-jun).
    El operario marca CUMPLE (registrado_por); Calidad/Jefe de Producción VERIFICA después
    (verificado_por). body: {item_idx, etapa} verifica uno · {todos:true, etapa} verifica todos
    los cumple sin verificar. Solo verifica ítems ya marcados cumple=1 (no se verifica lo no hecho)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    etapa = (body.get("etapa") or "dispensacion").strip().lower()
    if etapa not in ("dispensacion", "fabricacion"):
        etapa = "dispensacion"
    user = session.get("compras_user", "")
    if not _batch_role_info(user).get("verifica"):
        return jsonify({"error": "Verificar el despeje es atribución de Calidad / Jefe de Producción / "
                                 "Dirección Técnica. El operario solo registra el despeje.",
                        "codigo": "SOLO_VERIFICA_DESPEJE"}), 403
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    # No autoverificación: quien verifica no puede ser quien registró (2 personas).
    # Sebastián 7-jul: la verificación es UNA POR UNA (supervisión secuencial · sin "verificar todos") · así
    # Calidad revisa cada ítem antes de que el operario habilite el siguiente. El path masivo queda deshabilitado.
    if body.get("todos"):
        return jsonify({
            "error": "La verificación del despeje es UNA POR UNA (Calidad revisa cada ítem antes de habilitar "
                     "el siguiente). Verificá el ítem que corresponde.",
            "codigo": "VERIFICAR_UNO_A_UNO",
        }), 409
    if False:  # (rama masiva desactivada · se conserva la estructura por claridad)
        n = 0
    else:
        try:
            idx = int(body.get("item_idx"))
        except (TypeError, ValueError):
            return jsonify({"error": "item_idx inválido"}), 400
        # DEMO (Sebastián 20-jul): en un lote DEMO se permite AUTO-verificar (mismo usuario marca y verifica)
        # para poder CAMINAR el demo con una sola persona. En lotes reales rige la regla de 2 personas (GMP).
        _lr = cur.execute("SELECT COALESCE(lote_codigo, lote) FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        _es_demo = es_lote_demo((_lr[0] if _lr else "") or "")
        if _es_demo:
            cur.execute(
                "UPDATE ebr_despeje_items SET verificado_por=?, verificado_at_utc=datetime('now','utc') "
                "WHERE ebr_id=? AND item_idx=? AND COALESCE(etapa,'dispensacion')=? AND cumple=1 "
                "AND COALESCE(verificado_por,'')=''",
                (user, ebr_id, idx, etapa))
        else:
            cur.execute(
                "UPDATE ebr_despeje_items SET verificado_por=?, verificado_at_utc=datetime('now','utc') "
                "WHERE ebr_id=? AND item_idx=? AND COALESCE(etapa,'dispensacion')=? AND cumple=1 "
                "AND COALESCE(verificado_por,'')='' AND COALESCE(registrado_por,'')<>?",
                (user, ebr_id, idx, etapa, user))
        n = cur.rowcount
        if n == 0 and not _es_demo:
            # Nada verificado en un lote real: casi siempre porque intentás verificar tu propio registro.
            conn.rollback()
            return jsonify({
                "error": "No podés verificar tu propio despeje: la 2ª firma (Calidad) debe ser de OTRA persona "
                         "distinta al operario que lo marcó (regla de las 2 personas · GMP).",
                "codigo": "AUTOVERIFICACION_BLOQUEADA", "verificados": 0}), 409
    audit_log(cur, usuario=user, accion="VERIFICAR_DESPEJE_ITEM_EBR",
              tabla="ebr_despeje_items", registro_id=ebr_id,
              despues={"ebr_id": ebr_id, "etapa": etapa, "verificados": n, "por": user})
    conn.commit()
    return jsonify({"ok": True, "verificados": n}), 200


@bp.route("/api/brd/mi-trabajo", methods=["GET"])
def mi_trabajo_brd():
    """Bandeja por ROL (Nivel 2 · 25-jun): tareas pendientes del usuario en TODOS los legajos en curso.
    realiza (operario/jefe) → despeje por marcar + pasos por ejecutar · verifica (calidad) → despeje y
    pesajes por verificar. Una sola pantalla: cada quien ve SU cola de trabajo."""
    err = _require_login()
    if err:
        return err
    user = session.get("compras_user", "")
    rinfo = _batch_role_info(user)
    conn = get_db()

    def _ct(sql, *p):
        try:
            r = conn.execute(sql, p).fetchone()
            return int(r[0]) if r and r[0] is not None else 0
        except Exception:
            return 0

    ebrs = conn.execute(
        "SELECT id, COALESCE(numero_op,'') AS numero_op, COALESCE(lote_codigo,lote,'') AS lote, "
        "mbr_template_id, COALESCE(fase,'fabricacion') AS fase "
        "FROM ebr_ejecuciones WHERE estado IN ('iniciado','en_proceso') ORDER BY id DESC").fetchall()
    items = []
    n_items = len(DESPEJE_LINEA_ITEMS) * 2  # 12 verificaciones x 2 etapas
    for e in ebrs:
        eid = e["id"]
        prod = ""
        try:
            mb = conn.execute("SELECT producto_nombre FROM mbr_templates WHERE id=?",
                              (e["mbr_template_id"],)).fetchone()
            prod = (mb[0] if mb else "")
        except Exception:
            prod = ""
        tareas = []
        if rinfo.get("realiza"):
            np = _ct("SELECT COUNT(*) FROM ebr_pasos_ejecutados WHERE ebr_id=? AND estado IN ('pendiente','en_proceso')", eid)
            if np:
                tareas.append({"tipo": "pasos", "n": np, "txt": f"{np} paso(s) por ejecutar"})
            marc = _ct("SELECT COUNT(*) FROM ebr_despeje_items WHERE ebr_id=? AND cumple IS NOT NULL", eid)
            dpend = n_items - marc
            if dpend > 0:
                tareas.append({"tipo": "despeje", "n": dpend, "txt": f"{dpend} verificación(es) de despeje por marcar"})
        if rinfo.get("verifica"):
            dv = _ct("SELECT COUNT(*) FROM ebr_despeje_items WHERE ebr_id=? AND cumple=1 AND COALESCE(verificado_por,'')=''", eid)
            if dv:
                tareas.append({"tipo": "verif_despeje", "n": dv, "txt": f"{dv} ítem(s) de despeje por verificar"})
            pv = _ct("SELECT COUNT(*) FROM ebr_pesajes WHERE ebr_id=? AND COALESCE(pesado_por,'')<>'' AND COALESCE(verificado_por,'')=''", eid)
            if pv:
                tareas.append({"tipo": "verif_pesaje", "n": pv, "txt": f"{pv} pesaje(s) por verificar"})
        if tareas:
            items.append({"ebr_id": eid, "numero_op": e["numero_op"], "lote": e["lote"],
                          "producto": prod, "fase": e["fase"], "tareas": tareas,
                          "total": sum(t["n"] for t in tareas)})
    return jsonify({"rol": rinfo, "items": items, "total_legajos": len(items)})


@bp.route("/api/brd/ebr/<int:ebr_id>/aprobar-dt", methods=["POST"])
def aprobar_dt_ebr(ebr_id):
    """3ª firma · Director Técnico: visto bueno final (responsable INVIMA), además de Producción +
    Calidad. Requiere e-firma (signature_id · meaning='aprueba_dt')."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    if not _batch_role_info(user).get("aprueba_dt"):
        return jsonify({"error": "El visto bueno final es atribución del Director Técnico.",
                        "codigo": "SOLO_DIRECTOR_TECNICO"}), 403
    body = request.get_json(silent=True) or {}
    signature_id = body.get("signature_id")
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado, COALESCE(aprobado_dt_por,''), COALESCE(lote_codigo,lote,'') FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    _es_demo = es_lote_demo(ebr[2] or "")
    if not signature_id and not _es_demo:
        return jsonify({"error": "signature_id requerido · meaning='aprueba_dt' record_table='ebr_ejecuciones'"}), 400
    # VALIDAR la firma contra e_signatures en lote REAL (espejo de liberar_ebr · Part 11: la firma debe ser
    # una 'aprueba_dt' de ESTE EBR por este usuario, no un id cualquiera). DEMO no firma (hallazgo review 20-jul).
    if not _es_demo and not _validar_signature(
            cur, signature_id, record_table="ebr_ejecuciones",
            record_id=ebr_id, meaning="aprueba_dt", signer_username=user):
        return jsonify({"error": "signature_id no corresponde a una firma 'aprueba_dt' de este EBR por vos"}), 400
    if (ebr[1] or "").strip():
        return jsonify({"error": "Ya tiene visto bueno del Director Técnico"}), 409
    cur.execute("UPDATE ebr_ejecuciones SET aprobado_dt_por=?, aprobado_dt_at_utc=datetime('now','utc'), "
                "aprobado_dt_signature_id=? WHERE id=? AND COALESCE(aprobado_dt_por,'')=''",
                (user, signature_id, ebr_id))
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"error": "Ya aprobado o EBR cambió de estado"}), 409
    audit_log(cur, usuario=user, accion="APROBAR_DT_EBR", tabla="ebr_ejecuciones", registro_id=ebr_id,
              despues={"aprobado_dt_por": user})
    conn.commit()
    return jsonify({"ok": True, "aprobado_dt_por": user}), 200


@bp.route("/api/brd/ebr/<int:ebr_id>/correcciones", methods=["GET"])
def listar_correcciones_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    try:
        rows = get_db().execute(
            "SELECT COALESCE(campo_afectado,'') AS campo_afectado, COALESCE(motivo,'') AS motivo, "
            "COALESCE(descripcion,'') AS descripcion, COALESCE(registrado_por,'') AS registrado_por, "
            "COALESCE(registrado_at_utc,'') AS registrado_at_utc FROM ebr_correcciones "
            "WHERE ebr_id=? ORDER BY id DESC", (ebr_id,)).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    except Exception:
        return jsonify({"items": []})


@bp.route("/api/brd/ebr/<int:ebr_id>/correcciones", methods=["POST"])
def agregar_correccion_ebr(ebr_id):
    """Registra una corrección/enmienda al registro (21 CFR Part 11): motivo + descripción + autor + fecha.
    Atribución de Calidad / Aseguramiento / Dirección Técnica."""
    err = _require_brd_ejecutor()
    if err:
        return err
    user = session.get("compras_user", "")
    if not _batch_role_info(user).get("corrige") and not _es_demo_ebr(get_db(), ebr_id):
        return jsonify({"error": "Registrar una corrección es atribución de Calidad / Aseguramiento / "
                                 "Dirección Técnica.", "codigo": "SOLO_CALIDAD_CORRIGE"}), 403
    body = request.get_json(silent=True) or {}
    motivo = (body.get("motivo") or "").strip()[:500]
    desc = (body.get("descripcion") or "").strip()[:1000]
    campo = (body.get("campo_afectado") or "").strip()[:200]
    if not motivo and not desc:
        return jsonify({"error": "Indicá el motivo de la corrección"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO ebr_correcciones (ebr_id, campo_afectado, motivo, descripcion, registrado_por, "
                "registrado_at_utc, signature_id) VALUES (?, ?, ?, ?, ?, datetime('now','utc'), ?)",
                (ebr_id, campo, motivo, desc, user, body.get("signature_id")))
    audit_log(cur, usuario=user, accion="CORRECCION_EBR", tabla="ebr_correcciones", registro_id=ebr_id,
              despues={"motivo": motivo, "campo": campo, "por": user})
    conn.commit()
    return jsonify({"ok": True}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/ajustes-mp", methods=["GET"])
def listar_ajustes_mp_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    try:
        rows = get_db().execute(
            "SELECT COALESCE(material,'') AS material, COALESCE(cantidad_g,0) AS cantidad_g, "
            "COALESCE(motivo,'') AS motivo, COALESCE(registrado_por,'') AS registrado_por, "
            "COALESCE(registrado_at_utc,'') AS registrado_at_utc FROM ebr_ajustes_mp "
            "WHERE ebr_id=? ORDER BY id DESC", (ebr_id,)).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    except Exception:
        return jsonify({"items": []})


@bp.route("/api/brd/ebr/<int:ebr_id>/ajustes-mp", methods=["POST"])
def agregar_ajuste_mp_ebr(ebr_id):
    """Registra un ajuste de materia prima durante la fabricación (MyBatch §3 'Ajustes de MP' ·
    ej. + Trietanolamina para ajustar pH). Lo hace el operario que ejecuta."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    material = (body.get("material") or "").strip()[:200]
    motivo = (body.get("motivo") or "").strip()[:500]
    try:
        cant = float(str(body.get("cantidad_g") or 0).replace(",", "."))
    except (TypeError, ValueError):
        cant = 0.0
    if not material:
        return jsonify({"error": "Indicá la materia prima ajustada"}), 400
    user = session.get("compras_user", "")
    conn = get_db()
    cur = conn.cursor()
    # ── El ajuste ahora DESCUENTA del kardex (mig 396) ──────────────────────────
    # Hasta hoy esto sólo dejaba una NOTA: la MP que el operario agrega para corregir
    # pH quedaba escrita en el legajo y NUNCA salía del stock. El sistema creía que
    # seguía ahí. No era una función faltante, era un agujero de inventario silencioso
    # -- invisible porque el legajo se ve completo.
    # Se descuenta por el FEFO CANÓNICO (M1/M3: no se reimplementa el descuento), y sólo
    # cuando el caller manda `material_id`: sin el código de bodega no hay a qué imputar,
    # y adivinarlo por el nombre libre sería descontar la molécula equivocada (M19).
    material_id = (body.get("material_id") or "").strip()
    mov_ids, lotes_tocados = [], []
    _desc_at = ""            # `datetime` NO está importado a nivel de módulo en brd.py (M78)
    if material_id and cant > 0:
        try:
            from blueprints.programacion import _distribuir_fefo
        except ImportError:
            from programacion import _distribuir_fefo
        _nom = material
        try:
            _r = cur.execute("SELECT COALESCE(nombre_comercial, nombre_inci,'') "
                             "FROM maestro_mps WHERE codigo_mp=?", (material_id,)).fetchone()
            _nom = ((_r[0] if _r else "") or "") or material
        except Exception as _e:
            log.warning("ajuste-mp: nombre de %s no legible: %s", material_id, _e)
        from datetime import datetime as _dt, timezone as _tz
        _ahora = _dt.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%S")
        _desc_at = _ahora
        for _d in _distribuir_fefo(cur, material_id, cant):
            _q = float(_d.get("cantidad") or 0)
            if _q <= 0:          # un descuento de 0 es no-op y el trigger PG lo rechaza (M18)
                continue
            cur.execute(
                "INSERT INTO movimientos (material_id, material_nombre, cantidad, tipo, fecha, "
                "observaciones, lote, estado_lote, operador) "
                "VALUES (?,?,?,'Salida',?,?,?, 'VIGENTE', ?)",
                (material_id, _nom, _q, _ahora,
                 "Ajuste de MP en proceso · legajo #%d · %s" % (ebr_id, motivo or "sin motivo"),
                 _d.get("lote") or "", user))
            mov_ids.append(cur.lastrowid)
            if _d.get("lote"):
                lotes_tocados.append(_d.get("lote"))
    cur.execute("INSERT INTO ebr_ajustes_mp (ebr_id, material, cantidad_g, motivo, registrado_por, "
                "registrado_at_utc, material_id, lote, mov_id, descontado_at_utc) "
                "VALUES (?, ?, ?, ?, ?, datetime('now','utc'), ?, ?, ?, ?)",
                (ebr_id, material, cant, motivo, user, material_id,
                 ", ".join(lotes_tocados), (mov_ids[0] if mov_ids else None),
                 (_desc_at if mov_ids else "")))
    audit_log(cur, usuario=user, accion="AJUSTE_MP_EBR", tabla="ebr_ajustes_mp", registro_id=ebr_id,
              despues={"material": material, "material_id": material_id, "cantidad_g": cant,
                       "motivo": motivo, "por": user, "movimientos": mov_ids,
                       "lotes": lotes_tocados})
    conn.commit()
    return jsonify({"ok": True, "descontado": bool(mov_ids), "movimientos": mov_ids,
                    "lotes": lotes_tocados}), 201


# ── MyBatch ① · Precauciones + Equipos ──────────────────────────────────────
@bp.route("/api/brd/ebr/<int:ebr_id>/precauciones", methods=["GET"])
def listar_precauciones_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    try:
        rows = get_db().execute(
            "SELECT * FROM ebr_precauciones WHERE ebr_id=? ORDER BY id",
            (ebr_id,)).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    except Exception:
        return jsonify({"items": []})


@bp.route("/api/brd/ebr/<int:ebr_id>/precauciones", methods=["POST"])
def registrar_precaucion_ebr(ebr_id):
    """Agrega una precaución o equipo usado al legajo (MyBatch ①)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    desc = (body.get("descripcion") or "").strip()
    if not desc:
        return jsonify({"error": "descripcion requerida"}), 400
    tipo = (body.get("tipo") or "precaucion").strip().lower()
    if tipo not in ("precaucion", "equipo"):
        tipo = "precaucion"
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_precauciones
             (ebr_id, tipo, descripcion, registrado_por, registrado_at_utc)
           VALUES (?, ?, ?, ?, datetime('now','utc'))""",
        (ebr_id, tipo, desc[:500], user))
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_PRECAUCION_EBR",
              tabla="ebr_precauciones", registro_id=rid,
              despues={"ebr_id": ebr_id, "tipo": tipo})
    conn.commit()
    return jsonify({"ok": True, "id": rid}), 201


# ── MyBatch ⑦ · Registros físicos (adjuntar PDF/referencia) ─────────────────
@bp.route("/api/brd/ebr/<int:ebr_id>/registros-fisicos", methods=["GET"])
def listar_registros_fisicos_ebr(ebr_id):
    err = _require_login()
    if err:
        return err
    try:
        rows = get_db().execute(
            "SELECT id, ebr_id, descripcion, tipo, archivo_nombre, "
            "(CASE WHEN COALESCE(archivo_b64,'')!='' THEN 1 ELSE 0 END) AS tiene_pdf, "
            "registrado_por, registrado_at_utc "
            "FROM ebr_registros_fisicos WHERE ebr_id=? ORDER BY id",
            (ebr_id,)).fetchall()
        return jsonify({"items": [dict(r) for r in rows]})
    except Exception:
        return jsonify({"items": []})


@bp.route("/api/brd/ebr/<int:ebr_id>/registros-fisicos", methods=["POST"])
def registrar_registro_fisico_ebr(ebr_id):
    """Adjunta un registro físico al legajo: descripción + PDF opcional (base64)."""
    err = _require_brd_ejecutor()
    if err:
        return err
    body = request.get_json(silent=True) or {}
    desc = (body.get("descripcion") or "").strip()
    if not desc:
        return jsonify({"error": "descripcion requerida"}), 400
    b64 = body.get("archivo_b64") or None
    if b64 and len(b64) > 8 * 1024 * 1024:  # ~6MB PDF
        return jsonify({"error": "archivo muy grande (max ~6MB)"}), 413
    conn = get_db()
    cur = conn.cursor()
    ebr = cur.execute("SELECT estado FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404
    if ebr["estado"] not in ("iniciado", "en_proceso"):
        return jsonify({"error": f"EBR no editable (estado: {ebr['estado']})"}), 409
    user = session.get("compras_user", "")
    cur.execute(
        """INSERT INTO ebr_registros_fisicos
             (ebr_id, descripcion, tipo, archivo_nombre, archivo_b64,
              registrado_por, registrado_at_utc)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now','utc'))""",
        (ebr_id, desc[:300], (body.get("tipo") or "registro").strip()[:40],
         (body.get("archivo_nombre") or "").strip()[:120], b64, user))
    rid = cur.lastrowid
    audit_log(cur, usuario=user, accion="REGISTRAR_REGISTRO_FISICO_EBR",
              tabla="ebr_registros_fisicos", registro_id=rid,
              despues={"ebr_id": ebr_id, "tiene_pdf": bool(b64)})
    conn.commit()
    return jsonify({"ok": True, "id": rid}), 201


@bp.route("/api/brd/ebr/<int:ebr_id>/registros-fisicos/<int:rid>/pdf", methods=["GET"])
def descargar_registro_fisico_pdf(ebr_id, rid):
    err = _require_login()
    if err:
        return err
    import base64 as _b64
    from flask import send_file
    import io as _io
    row = get_db().execute(
        "SELECT archivo_b64, archivo_nombre FROM ebr_registros_fisicos "
        "WHERE id=? AND ebr_id=?", (rid, ebr_id)).fetchone()
    if not row or not row["archivo_b64"]:
        return jsonify({"error": "sin PDF"}), 404
    try:
        raw = _b64.b64decode(row["archivo_b64"])
    except Exception:
        return jsonify({"error": "archivo inválido"}), 500
    # Detectar tipo por extensión del nombre (las fotos de rótulos son imágenes,
    # no PDF) y servir INLINE para verlo en el navegador (como el modal de MyBatch).
    nombre = (row["archivo_nombre"] or f"registro_{rid}").lower()
    if nombre.endswith(('.jpg', '.jpeg')):
        mime = "image/jpeg"
    elif nombre.endswith('.png'):
        mime = "image/png"
    elif nombre.endswith('.webp'):
        mime = "image/webp"
    elif nombre.endswith('.gif'):
        mime = "image/gif"
    elif nombre.endswith('.pdf'):
        mime = "application/pdf"
    else:
        # Sin extensión clara: inferir por los primeros bytes (magic number).
        if raw[:4] == b'%PDF':
            mime = "application/pdf"
        elif raw[:3] == b'\xff\xd8\xff':
            mime = "image/jpeg"
        elif raw[:8] == b'\x89PNG\r\n\x1a\n':
            mime = "image/png"
        else:
            mime = "application/octet-stream"
    return send_file(_io.BytesIO(raw), mimetype=mime, as_attachment=False,
                     download_name=(row["archivo_nombre"] or f"registro_{rid}"))


@bp.route("/api/brd/ebr/<int:ebr_id>/reconciliacion", methods=["GET"])
def reconciliacion_ebr(ebr_id):
    """Resumen MP-por-MP de teórico vs real.

    Threshold de outlier: |delta_pct| > 5% se marca para revisión QC.
    Se exponen 3 listas: ok (sin outliers), outliers (>5% delta),
    no_pesados (MPs de la fórmula que no tienen pesaje todavía).
    """
    err = _require_login()
    if err:
        return err
    conn = get_db()
    ebr = conn.execute(
        """SELECT e.cantidad_objetivo_g, e.cantidad_real_g, e.yield_pct,
                  e.estado, m.producto_nombre
           FROM ebr_ejecuciones e
           JOIN mbr_templates m ON m.id = e.mbr_template_id
           WHERE e.id = ?""", (ebr_id,),
    ).fetchone()
    if not ebr:
        return jsonify({"error": "EBR no encontrado"}), 404

    teoricos = _calcular_teoricos_mp(conn, ebr["producto_nombre"],
                                     ebr["cantidad_objetivo_g"])
    pesajes_rows = conn.execute(
        """SELECT material_id, SUM(cantidad_real_g) AS suma_real,
                  COUNT(*) AS n_pesajes,
                  GROUP_CONCAT(DISTINCT lote_mp) AS lotes_mp
           FROM ebr_pesajes WHERE ebr_id = ? AND material_id != ''
           GROUP BY material_id""",
        (ebr_id,),
    ).fetchall()
    pesajes = {r["material_id"]: dict(r) for r in pesajes_rows}

    OUTLIER_THRESHOLD_PCT = 5.0
    ok, outliers, no_pesados = [], [], []
    total_teorico = 0.0
    total_real = 0.0
    for mid, spec in teoricos.items():
        teorico = spec["cantidad_teorica_g"]
        total_teorico += teorico
        p = pesajes.get(mid)
        if not p:
            no_pesados.append({
                "material_id": mid,
                "material_nombre": spec["material_nombre"],
                "nombre_inci": spec.get("nombre_inci", ""),
                "cantidad_teorica_g": teorico,
            })
            continue
        real = p["suma_real"] or 0
        total_real += real
        delta = real - teorico
        delta_pct = (delta / teorico * 100.0) if teorico > 0 else None
        item = {
            "material_id": mid,
            "material_nombre": spec["material_nombre"],
            "nombre_inci": spec.get("nombre_inci", ""),
            "cantidad_teorica_g": teorico,
            "cantidad_real_g": real,
            "delta_g": delta,
            "delta_pct": delta_pct,
            "n_pesajes": p["n_pesajes"],
            "lotes_mp": (p["lotes_mp"] or "").split(",") if p["lotes_mp"] else [],
        }
        if delta_pct is not None and abs(delta_pct) > OUTLIER_THRESHOLD_PCT:
            outliers.append(item)
        else:
            ok.append(item)

    return jsonify({
        "ebr_id": ebr_id,
        "producto_nombre": ebr["producto_nombre"],
        "cantidad_objetivo_g": ebr["cantidad_objetivo_g"],
        "cantidad_real_g_lote": ebr["cantidad_real_g"],
        "yield_pct_lote": ebr["yield_pct"],
        "totales_pesajes": {
            "total_teorico_g": total_teorico,
            "total_real_g": total_real,
            "delta_g": total_real - total_teorico,
            "delta_pct": ((total_real - total_teorico) / total_teorico * 100.0) if total_teorico > 0 else None,
        },
        "ok": ok,
        "outliers": outliers,
        "no_pesados": no_pesados,
        "outlier_threshold_pct": OUTLIER_THRESHOLD_PCT,
        "estado_ebr": ebr["estado"],
    })


# ──────────────────────────────────────────────────────────────────────────
# Órdenes de Producción · vista unificada estilo MyBatch (Sebastián 4-jun-2026)
#
# PASO 1 (100% aditivo · SOLO LECTURA): surface las "Órdenes de Producción"
# como MyBatch (N° orden OP-AAAA-NNNN · lote · producto · cant teórica/producida/
# aprobada · estado). Une los DOS mundos que hoy están separados:
#   - ebr_ejecuciones  → legajos formales (ya tienen numero_op, fase, estados).
#   - producciones      → registros simples del formulario "Registrar Producción"
#                         (sin N° de orden ni legajo · se muestran como 'simple').
# NO toca el formulario, ni el descuento, ni el motor EBR. Solo lee y presenta.
# ──────────────────────────────────────────────────────────────────────────

def _estado_orden_norm(origen, estado):
    """Mapea el estado interno al vocabulario MyBatch (En Proceso / Aprobado /
    Cancelado / Completado)."""
    e = (estado or "").strip().lower()
    if origen == "legajo":
        return {
            "iniciado": "En Proceso",
            "en_proceso": "En Proceso",
            "completado": "En Proceso · Cuarentena",
            "liberado": "Aprobado",
            "rechazado": "Rechazado",
        }.get(e, estado or "·")
    # registro simple (producciones)
    if e in ("completado", "completada"):
        return "Completado (registro simple)"
    if e in ("cancelado", "cancelada"):
        return "Cancelado"
    return estado or "Completado (registro simple)"


@bp.route("/aseguramiento/maestro-lotes", methods=["GET"])
def maestro_lotes_page():
    """Redirige al maestro de lotes REAL · esta pantalla fue un duplicado mío (17-ago).

    ⚠ Construí un maestro de lotes acá sin ver que ya existía uno en `/calidad/maestro-lotes`
    desde el 15-ago, y mucho más completo: trae las tres fases del lote con su rendimiento, los
    clientes, el material de envase y declara de dónde saca la teórica. El mío era un
    subconjunto pobre.

    Lo busqué con `/api/brd/maestro-lotes` -- una URL que inventé yo --, vi el 404 y concluí
    que faltaba. Es el mismo error que M220 acababa de escribir: **antes de anotar que falta
    algo, hay que medir qué tiene EOS, no preguntarle por el nombre que uno le pondría** (M170).

    Dos pantallas con el mismo nombre no son dos vistas: son dos verdades que divergen, y quien
    las mira no tiene forma de saber cuál creer (M99/M161). Se retira la mía. La ruta queda
    redirigiendo porque estuvo enlazada desde Dirección Técnica (M120: una URL ya enlazada no
    se borra, se redirige).
    """
    return redirect("/calidad/maestro-lotes")


@bp.route("/api/brd/ordenes-unificadas", methods=["GET"])
def ordenes_unificadas():
    """Lista unificada de Órdenes de Producción (legajos EBR + registros simples).

    Query: ?fase=fabricacion|envasado|acondicionamiento (default fabricacion).
    Los registros simples (tabla producciones) solo aplican a 'fabricacion'.
    SOLO LECTURA · no escribe nada."""
    err = _require_login()
    if err:
        return err
    fase = (request.args.get("fase") or "fabricacion").strip().lower()
    if fase not in _FASES_VALIDAS:
        fase = "fabricacion"
    conn = get_db()
    items = []

    # 0) Fabricaciones EN CURSO (produccion_programada · inicio sin fin) → para mostrar Finalizar en la
    # orden. Si ya tienen legajo, se anota su produccion_id en la fila del legajo; si no, fila propia.
    _enp = {}
    if fase == "fabricacion":
        try:
            for r in conn.execute(
                "SELECT pp.id, COALESCE(pp.producto,''), COALESCE(pp.cantidad_kg,0), pp.inicio_real_at, "
                "COALESCE(o.nombre,'') FROM produccion_programada pp "
                "LEFT JOIN operarios_planta o ON o.id=pp.operario_elaboracion_id "
                "WHERE COALESCE(pp.inicio_real_at,'')<>'' AND COALESCE(pp.fin_real_at,'')='' "
                "AND LOWER(COALESCE(pp.estado,'')) NOT IN ('completado','cancelado')").fetchall():
                _enp[r[0]] = {'producto': r[1], 'kg': float(r[2] or 0),
                              'inicio': r[3], 'operador': r[4]}
        except Exception as _e:
            log.warning("ordenes-unificadas en-curso query fallo: %s", _e)

    # 1) Legajos EBR (ya MyBatch-shaped) · producto vía mbr_templates
    try:
        ebr_rows = conn.execute(
            """SELECT e.id, e.numero_op, e.produccion_id,
                      COALESCE(e.lote_codigo, e.lote) AS lote, e.estado,
                      e.cantidad_objetivo_g, e.cantidad_real_g,
                      COALESCE(e.ml_envasable, NULL) AS ml_envasable,
                      e.iniciado_at_utc, e.liberado_at_utc,
                      COALESCE(e.fase,'fabricacion') AS fase,
                      COALESCE(m.producto_nombre,'') AS producto
               FROM ebr_ejecuciones e
               LEFT JOIN mbr_templates m ON m.id = e.mbr_template_id
               WHERE COALESCE(e.fase,'fabricacion') = ?
                 AND COALESCE(e.estado,'') != 'cancelado'
               ORDER BY e.iniciado_at_utc DESC""",
            (fase,),
        ).fetchall()
    except Exception as _e:
        log.warning("ordenes-unificadas EBR query fallo: %s", _e)
        ebr_rows = []
    _lotes_con_legajo = set()  # para no duplicar la fila simple si ya tiene EBR
    for r in ebr_rows:
        rd = dict(r)
        liberado = bool(rd.get("liberado_at_utc"))
        if rd.get("lote"):
            _lotes_con_legajo.add(str(rd["lote"]).strip())
        _ppid = rd.get("produccion_id")
        _en_curso = _ppid in _enp
        _kg_pp = None
        if _en_curso:
            _kg_pp = _enp[_ppid].get('kg')
            _enp.pop(_ppid, None)  # se muestra como esta orden (con Finalizar)
        items.append({
            "origen": "legajo",
            "numero_op": rd.get("numero_op") or f"EBR-{rd['id']}",
            "lote_bulk": rd.get("lote") or "",
            "producto": rd.get("producto") or "",
            # En-curso: la cantidad REAL a producir manda (produccion_programada.cantidad_kg);
            # el cantidad_objetivo_g del EBR puede haber quedado con el default del MBR.
            "teorica_g": (round(_kg_pp * 1000, 1) if (_en_curso and _kg_pp) else rd.get("cantidad_objetivo_g")),
            "producida_g": rd.get("cantidad_real_g"),
            "aprobada": (rd.get("cantidad_real_g") if liberado else None),
            "ml_envasable": rd.get("ml_envasable"),
            "estado": ("En proceso" if _en_curso else _estado_orden_norm("legajo", rd.get("estado"))),
            # La fecha se muestra y se compara en hora COLOMBIA. `iniciado_at_utc` es UTC: cortarlo
            # con [:10] daba la fecha UTC, que después de las 7 de la tarde local ya es MAÑANA. Con
            # eso, una orden abierta hoy a la noche calculaba "hace -1 días" (M24: el que escribe y
            # el que lee tienen que estar en la misma base).
            "fecha": _fecha_colombia(rd.get("iniciado_at_utc")),
            "link": f"/planta/orden/{rd['id']}",
            "ebr_id": rd["id"],
            "produccion_id": (_ppid if _en_curso else None),
        })

    # 2) Registros simples (producciones) · solo en fabricación
    if fase == "fabricacion":
        try:
            prod_rows = conn.execute(
                """SELECT id, producto, COALESCE(cantidad,0) AS cantidad,
                          fecha, COALESCE(estado,'') AS estado,
                          COALESCE(lote,'') AS lote, COALESCE(operador,'') AS operador
                   FROM producciones
                   ORDER BY fecha DESC
                   LIMIT 300""",
            ).fetchall()
        except Exception as _e:
            log.warning("ordenes-unificadas producciones query fallo: %s", _e)
            prod_rows = []
        for r in prod_rows:
            rd = dict(r)
            # dedup: si esta producción YA tiene legajo (mismo lote), no la repetimos
            # como fila 'simple' · gana la fila LEGAJO (el legajo automático).
            if str(rd.get("lote") or "").strip() in _lotes_con_legajo:
                continue
            kg = float(rd.get("cantidad") or 0)
            items.append({
                "origen": "simple",
                "numero_op": rd.get("lote") or f"PROD-{rd['id']:05d}",
                "lote_bulk": rd.get("lote") or "",
                "producto": rd.get("producto") or "",
                "teorica_g": round(kg * 1000, 1),
                "producida_g": round(kg * 1000, 1),
                "aprobada": None,
                "ml_envasable": None,
                "estado": _estado_orden_norm("simple", rd.get("estado")),
                "fecha": (rd.get("fecha") or "")[:10],
                "link": None,
                "operador": rd.get("operador") or "",
            })

    # 2b) Registros simples de ENVASADO (tabla envasado · 9-jun) → la OF muestra las
    # órdenes de envasado CON su estado (como MyBatch), no solo legajos EBR. Agrupa por
    # lote+producto (la modal registra 1 fila por presentación · 1 orden por lote).
    if fase == "envasado":
        try:
            env_rows = conn.execute(
                """SELECT MIN(id) AS id, COALESCE(producto,'') AS producto,
                          COALESCE(lote,'') AS lote, MAX(COALESCE(estado,'Completado')) AS estado,
                          MAX(COALESCE(fecha,'')) AS fecha, MAX(COALESCE(operador,'')) AS operador,
                          SUM(COALESCE(unidades,0)) AS unidades
                   FROM envasado
                   GROUP BY producto, lote
                   ORDER BY id DESC LIMIT 300""",
            ).fetchall()
        except Exception as _e:
            log.warning("ordenes-unificadas envasado query fallo: %s", _e)
            env_rows = []
        for r in env_rows:
            rd = dict(r)
            if str(rd.get("lote") or "").strip() in _lotes_con_legajo:
                continue
            items.append({
                "origen": "simple",
                "numero_op": rd.get("lote") or f"ENV-{rd['id']:05d}",
                # El SQL de arriba ya suma las unidades y este dict las TIRABA.
                "unidades_simple": int(rd.get("unidades") or 0),
                "lote_bulk": rd.get("lote") or "",
                "producto": rd.get("producto") or "",
                "teorica_g": None, "producida_g": None, "aprobada": None,
                "ml_envasable": None,
                "estado": _estado_orden_norm("simple", rd.get("estado")),
                "fecha": (rd.get("fecha") or "")[:10],
                "link": None,
                "operador": rd.get("operador") or "",
            })

    # 2c) Registros simples de ACONDICIONAMIENTO (tabla acondicionamiento · 10-jun) →
    # la OA muestra las órdenes con su estado (como MyBatch), aunque aún no tengan
    # legajo EBR. Agrupa por lote+producto.
    if fase == "acondicionamiento":
        try:
            ac_rows = conn.execute(
                """SELECT MIN(id) AS id, COALESCE(producto,'') AS producto,
                          COALESCE(lote,'') AS lote, MAX(COALESCE(estado,'En proceso')) AS estado,
                          MAX(COALESCE(fecha,'')) AS fecha, MAX(COALESCE(operador,'')) AS operador,
                          SUM(COALESCE(unidades_producidas,0)) AS unidades
                   FROM acondicionamiento
                   GROUP BY producto, lote
                   ORDER BY id DESC LIMIT 300""",
            ).fetchall()
        except Exception as _e:
            log.warning("ordenes-unificadas acondicionamiento query fallo: %s", _e)
            ac_rows = []
        for r in ac_rows:
            rd = dict(r)
            if str(rd.get("lote") or "").strip() in _lotes_con_legajo:
                continue
            items.append({
                "origen": "simple",
                "numero_op": rd.get("lote") or f"ACOND-{rd['id']:05d}",
                # El SQL de arriba ya suma las unidades y este dict las TIRABA.
                "unidades_simple": int(rd.get("unidades") or 0),
                "lote_bulk": rd.get("lote") or "",
                "producto": rd.get("producto") or "",
                "teorica_g": None, "producida_g": None, "aprobada": None,
                "ml_envasable": None,
                "estado": _estado_orden_norm("simple", rd.get("estado")),
                "fecha": (rd.get("fecha") or "")[:10],
                "link": None,
                "operador": rd.get("operador") or "",
            })

    # en-curso SIN legajo (productos sin MBR aprobado) → fila propia "En proceso" con Finalizar
    for _pid, _v in _enp.items():
        items.append({
            "origen": "en_proceso",
            "numero_op": f"PROD-{_pid:05d}",
            "lote_bulk": "",
            "producto": _v['producto'],
            "teorica_g": round(_v['kg'] * 1000, 1),
            "producida_g": None, "aprobada": None, "ml_envasable": None,
            "estado": "En proceso",
            "fecha": (_v['inicio'] or "")[:10],
            "link": None,
            "produccion_id": _pid,
            "operador": _v['operador'],
        })
    # 3) ENRIQUECER las órdenes con legajo · avance, presentaciones, quién y hace cuánto (26-jul).
    # Sebastián, mirando la lista de Envasado: "¿es premium? ¿qué hay para mejorar acá?". La lista
    # mostraba número, producto, lote y estado — nada de lo que hace falta para DECIDIR: cuánto
    # lleva la orden, cuántos frascos de cada presentación salen, quién la tiene, hace cuántos días.
    # Se calcula acá y NO en el navegador: pedir el detalle por fila serían N fetch desde una vista
    # de lista, que es exactamente lo que satura los 3 workers y deja la pantalla en "Cargando" (M43
    # /M59/M86). Son 2 consultas AGREGADAS para toda la lista, no una por orden.
    _ids = [i["ebr_id"] for i in items if i.get("ebr_id")]
    if _ids:
        _ph = ",".join("?" for _ in _ids)
        _avance, _pres = {}, {}
        try:
            for r in conn.execute(
                "SELECT ebr_id, COUNT(*) AS n, "
                "SUM(CASE WHEN LOWER(COALESCE(estado,''))='completado' THEN 1 ELSE 0 END) AS hechos "
                "FROM ebr_pasos_ejecutados WHERE ebr_id IN (%s) GROUP BY ebr_id" % _ph,
                _ids).fetchall():
                _avance[r[0]] = (int(r[1] or 0), int(r[2] or 0))
        except Exception as _e:
            log.warning("ordenes-unificadas avance de pasos fallo: %s", _e)
        if fase in ("envasado", "acondicionamiento"):
            try:
                for r in conn.execute(
                    "SELECT ebr_id, COALESCE(etiqueta,''), COALESCE(volumen_ml,0), "
                    "COALESCE(unidades,0) FROM ebr_envasado_unidades WHERE ebr_id IN (%s) "
                    "ORDER BY volumen_ml DESC" % _ph, _ids).fetchall():
                    if (r[3] or 0) > 0:
                        _pres.setdefault(r[0], []).append({
                            "etiqueta": r[1], "volumen_ml": float(r[2] or 0),
                            "unidades": int(r[3] or 0)})
            except Exception as _e:
                log.warning("ordenes-unificadas presentaciones fallo: %s", _e)
        # CLIENTES del lote, en la LISTA (Sebastián 15-ago-2026: "que aparezca foto con
        # cantidades que son para cada cliente en el envasado"). El dato ya se mostraba
        # dentro del legajo, pero para verlo había que abrir orden por orden; en el piso
        # lo que se mira es esta lista. Van DOS consultas agregadas para toda la lista, no
        # una por fila: pedir el detalle por orden desde el navegador es lo que satura los
        # tres workers y deja la pantalla en "Cargando" (M43).
        _clientes = {}
        if fase in ("envasado", "acondicionamiento"):
            try:
                _codigos = set()
                for r in conn.execute(
                    "SELECT e.id, COALESCE(p.cliente_nombre,''), "
                    "       SUM(COALESCE(p.unidades_aporte,0)), "
                    "       MAX(COALESCE(p.envase_codigo,'')), MAX(COALESCE(p.ml_unidad,0)) "
                    "  FROM ebr_ejecuciones e "
                    "  JOIN pedidos_b2b_lote p ON p.lote_produccion_id = e.produccion_id "
                    " WHERE e.id IN (%s) AND COALESCE(e.produccion_id,0) > 0 "
                    " GROUP BY e.id, p.cliente_nombre" % _ph, _ids).fetchall():
                    if (r[2] or 0) <= 0:
                        continue
                    cod = (r[3] or "").strip()
                    if cod:
                        _codigos.add(cod.upper())
                    _clientes.setdefault(r[0], []).append({
                        "cliente": r[1] or "(sin nombre)",
                        "unidades": int(r[2] or 0),
                        "volumen_ml": float(r[4] or 0),
                        "envase_codigo": cod, "envase_foto": "", "envase_desc": "",
                    })
                if _codigos:
                    _fp = ",".join("?" for _ in _codigos)
                    _fotos = {}
                    for r in conn.execute(
                        "SELECT UPPER(TRIM(codigo)), COALESCE(imagen_url,''), "
                        "COALESCE(descripcion,'') FROM maestro_mee "
                        "WHERE UPPER(TRIM(codigo)) IN (%s)" % _fp,
                            sorted(_codigos)).fetchall():
                        _fotos[r[0]] = (r[1], r[2])
                    for filas in _clientes.values():
                        for c in filas:
                            f = _fotos.get((c["envase_codigo"] or "").upper())
                            if f:
                                c["envase_foto"], c["envase_desc"] = f[0], f[1]
            except Exception as _e:
                # Que la lista siga saliendo aunque esto falle · pero se DICE en el log:
                # un except mudo convierte "no pude leer" en "no hay clientes" (M4/M94).
                log.warning("ordenes-unificadas clientes del lote fallo: %s", _e)
        # import local: este archivo no importa datetime a nivel de módulo (cada función lo hace)
        from datetime import date as _dfecha, datetime as _dnow, timedelta as _dtd
        _hoy = (_dnow.utcnow() - _dtd(hours=5)).date()  # ancla Colombia, nunca UTC crudo (M24)
        for it in items:
            eid = it.get("ebr_id")
            if not eid:
                continue
            tot, hechos = _avance.get(eid, (0, 0))
            it["pasos_total"] = tot
            it["pasos_hechos"] = hechos
            it["avance_pct"] = (round(100.0 * hechos / tot) if tot else None)
            it["presentaciones"] = _pres.get(eid, [])
            it["unidades_total"] = sum(p["unidades"] for p in _pres.get(eid, []))
            it["clientes"] = _clientes.get(eid, [])
            it["unidades_clientes"] = sum(c["unidades"] for c in _clientes.get(eid, []))
            # Edad en días: una orden de envasado parada 6 días es el dato que hace falta ver de
            # un vistazo, y hoy había que abrir el legajo para deducirlo de la fecha.
            it["dias"] = None
            f = (it.get("fecha") or "").strip()
            if len(f) >= 10:
                try:
                    it["dias"] = (_hoy - _dfecha.fromisoformat(f[:10])).days
                except ValueError:
                    pass

    # orden: en-curso PRIMERO, luego por fecha desc (sort estable)
    items.sort(key=lambda x: (x.get("fecha") or ""), reverse=True)
    items.sort(key=lambda x: 0 if (x.get("estado") or "").lower().startswith("en proceso") else 1)
    # Los legajos DEMO no son producción: se marcan y NO entran a los indicadores. Con un
    # demo abierto hace 26 días, Envasado mostraba "1 orden abierta · 1 atrasada" cuando no
    # había ni una orden real, y ese número no se apaga nunca -- un indicador que grita por
    # algo que nadie va a cerrar enseña a ignorar el tablero (M129/M154).
    #
    # Se DECLARAN, no se esconden: el demo sigue en la lista con su marca, porque una fila
    # que desaparece sin explicación manda a buscarla (M124).
    for _i in items:
        # ⚠ En esta respuesta el lote viaja como `lote_bulk`, no como `lote`: mirar la
        # llave equivocada devuelve None y TODO queda marcado como no-demo, sin un solo
        # error a la vista (M94 · me pasó al escribir esto).
        _lt = str(_i.get("lote_bulk") or _i.get("lote") or "").upper()
        _i["es_demo"] = es_lote_demo(_lt)
    _reales = [i for i in items if not i["es_demo"]]
    _abiertas = [i for i in _reales if not (i.get("estado") or "").lower().startswith(
        ("complet", "liberad", "cerrad", "rechaz"))]
    # ── LO QUE EL ENRIQUECIMIENTO DE LEGAJOS NO TOCA (17-ago) ───────────────────────────────
    # El bloque de arriba vive dentro de `if _ids:` y arranca con `if not eid: continue`, o sea
    # que sólo mira LEGAJOS. Una orden registrada por la vía SIMPLE -- la pantalla que usa la
    # planta -- entraba a la lista sin `unidades_total` y sin `dias`:
    #
    #   · su tarjeta decía "Sin unidades registradas todavía" con el trabajo hecho y registrado,
    #   · el KPI "Unidades acondicionadas" la contaba como CERO,
    #   · y "3 días o más sin cerrar" no la podía ver envejecer.
    #
    # Y con una lista compuesta SÓLO por registros simples -- ninguna con legajo -- el bloque
    # entero no corría: la pantalla quedaba ciega justo donde la planta todavía no abre legajos,
    # que es hoy acondicionamiento. Es la mitad de EOS que le faltaba a la vista de MyBatch: la
    # ORDEN ya se mostraba, sin el número que la hace útil (M115).
    from datetime import datetime as _dn2, timedelta as _td2
    _hoy2 = (_dn2.utcnow() - _td2(hours=5)).date()   # ancla Colombia, nunca UTC crudo (M24)
    for _it in items:
        _us = int(_it.pop("unidades_simple", 0) or 0)
        if _us > 0 and not _it.get("unidades_total"):
            _it["unidades_total"] = _us
        if _it.get("dias") is None:
            _f2 = (_it.get("fecha") or "").strip()
            if _f2:
                try:
                    _it["dias"] = (_hoy2 - _dn2.strptime(_f2[:10], "%Y-%m-%d").date()).days
                except Exception:
                    _it["dias"] = None

    resumen = {
        "total": len(_reales),
        "legajos": sum(1 for i in _reales if i["origen"] == "legajo"),
        "simples": sum(1 for i in _reales if i["origen"] in ("simple", "en_proceso")),
        "en_proceso": sum(1 for i in _reales if i.get("produccion_id")),
        "abiertas": len(_abiertas),
        # Lo que de verdad pide una acción: órdenes abiertas que llevan 3 días o más sin cerrar.
        "atrasadas": sum(1 for i in _abiertas if (i.get("dias") or 0) >= 3),
        "unidades_total": sum(int(i.get("unidades_total") or 0) for i in _reales),
        # Lo que se dejó afuera, dicho: un total que excluye cosas sin nombrarlas se lee
        # como un faltante (M148).
        "demos": sum(1 for i in items if i["es_demo"]),
        "total_con_demos": len(items),
    }
    return jsonify({"ok": True, "fase": fase, "resumen": resumen, "ordenes": items})


_ORDENES_PROD_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Órdenes de Producción · EOS</title>
<style>
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:#f4f4f7;color:#18181b;margin:0;padding:20px;-webkit-font-smoothing:antialiased}
/* 96vw = la regla de EOS para los modulos. Estaban clavadas en 1100-1200px: en un monitor de 1990 dejaban el 40% en blanco y la tabla de materiales -7 columnas- se desbordaba cortando 'Diferencia'. La orden madre ya usaba 96vw; se alinean las de DATOS. Los dos INSTRUCTIVOS quedan angostos a proposito: son formatos que se leen y se imprimen. */.wrap{max-width:96vw;margin:0 auto}
h1{color:var(--cx-primary-text, #7c3aed);font-size:22px;margin:0 0 4px}
.sub{color:var(--cx-text-mute, #64748b);font-size:13px;margin-bottom:14px}
.tabs{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.tab{padding:8px 16px;border-radius:8px;background:var(--cx-primary-soft, #ede9fe);color:var(--cx-primary-text, #5b21b6);font-weight:700;font-size:13px;cursor:pointer;border:none}
.tab.active{background:var(--cx-primary, #7c3aed);color:#fff}
.card{background:var(--cx-card, #fff);border-radius:12px;padding:16px;box-shadow:0 2px 6px rgba(0,0,0,.05)}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;padding:9px 8px;background:var(--cx-border-soft, #f1f5f9);color:var(--cx-text-soft, #475569);font-weight:700;font-size:11.5px;position:sticky;top:0}
td{padding:9px 8px;border-bottom:1px solid var(--cx-border-soft, #f1f5f9);vertical-align:middle}
.mono{font-family:ui-monospace,monospace;font-weight:700;color:var(--cx-info-text, #1e40af)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.pill{padding:2px 9px;border-radius:11px;font-size:10.5px;font-weight:700;white-space:nowrap}
.proc{background:#fef9c3;color:#854d0e}.cuar{background:var(--cx-info-pale, #dbeafe);color:var(--cx-info-text, #1e40af)}
.apr{background:var(--cx-success-pale, #dcfce7);color:var(--cx-success-text, #166534)}.rech{background:var(--cx-danger-pale, #fee2e2);color:var(--cx-danger-text, #991b1b)}.simp{background:var(--cx-border-soft, #f1f5f9);color:var(--cx-text-soft, #475569)}
.org{font-size:10px;padding:1px 6px;border-radius:8px;font-weight:700}
.org-l{background:var(--cx-primary-soft, #ede9fe);color:var(--cx-primary-text, #6d28d9)}.org-s{background:var(--cx-border-soft, #f1f5f9);color:var(--cx-text-mute, #64748b)}
.muted{color:var(--cx-text-faint, #94a3b8)}a.legajo{color:var(--cx-primary-text, #7c3aed);font-weight:700;text-decoration:none}
.summary{display:flex;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.box{padding:7px 12px;border-radius:8px;font-size:12px;font-weight:700;background:var(--cx-primary-soft, #ede9fe);color:var(--cx-primary-text, #5b21b6)}
</style></head><body>
<div class="wrap">
<a href="/inventarios" style="color:var(--cx-primary-text, #7c3aed);font-size:13px">&larr; Planta</a>
<h1>📋 Órdenes de Producción</h1>
<div class="sub">Vista unificada (solo lectura) · legajos EBR + registros de Fabricación · equivalente a MyBatch.</div>
<div class="tabs">
  <button class="tab active" data-fase="fabricacion" onclick="ver('fabricacion',this)">🏭 Fabricación (OP)</button>
  <button class="tab" data-fase="envasado" onclick="ver('envasado',this)">📦 Envasado (OF)</button>
  <button class="tab" data-fase="acondicionamiento" onclick="ver('acondicionamiento',this)">🎨 Acondicionamiento (OA)</button>
</div>
<div style="margin-bottom:12px">
  <button onclick="crearLegajoRapido()" style="background:var(--cx-success, #16a34a);color:#fff;border:none;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:700;cursor:pointer">+ Nueva orden de esta fase</button>
  <span style="font-size:12px;color:var(--cx-text-mute, #64748b);margin-left:8px">crea el legajo (requiere MBR aprobado del producto)</span>
</div>
<div id="summary" class="summary"></div>
<div class="card"><div id="out">Cargando…</div></div>
</div>
<script>
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function gfmt(n){return n==null?'·':Number(n).toLocaleString('es-CO')+' g';}
function pill(estado){
  var e=(estado||'').toLowerCase(); var c='simp';
  if(e.indexOf('cuarentena')>=0)c='cuar'; else if(e.indexOf('proceso')>=0)c='proc';
  else if(e.indexOf('aprob')>=0)c='apr'; else if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)c='rech';
  return '<span class="pill '+c+'">'+esc(estado)+'</span>';
}
var _FASE_ACTUAL='fabricacion';
async function crearLegajoRapido(){
  var f=_FASE_ACTUAL||'envasado';
  var fl=({fabricacion:'fabricación (OP)',envasado:'envasado (OF)',acondicionamiento:'acondicionamiento (OA)'})[f]||f;
  var prod=prompt('Producto para la orden de '+fl+' (nombre exacto):');
  if(!prod)return;
  var lote=prompt('N° de lote:');
  if(!lote)return;
  try{
    var r=await fetch('/api/brd/legajo-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto:prod,lote:lote,fase:f})});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo crear el legajo: '+((d&&d.error)||r.status));return;}
    location.href=d.link||('/planta/orden/'+d.id);
  }catch(e){alert('Error de red: '+(e.message||e));}
}
async function ver(fase,btn){
  _FASE_ACTUAL=fase;
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active');});
  if(btn)btn.classList.add('active');
  var out=document.getElementById('out'); out.innerHTML='Cargando…';
  // Envasado se gestiona en UN solo lugar (Planta → Envasado) · este tab ya NO
  // duplica la lista · redirige al lugar canónico (9-jun · quitar redundancia).
  if(fase==='envasado'){
    document.getElementById('summary').innerHTML='';
    out.innerHTML='<div style="text-align:center;padding:34px 20px"><div style="font-size:34px;margin-bottom:8px">&#128230;</div><b style="font-size:15px;color:var(--cx-primary-text, #6d28d9)">Las Órdenes de Envasado viven en un solo lugar</b><br><span style="color:var(--cx-text-mute, #64748b);font-size:13px">Planta &rarr; Envasado (la cola, el estado y el legajo) &middot; sin duplicados.</span><br><br><a href="/inventarios#envasado" style="display:inline-block;background:var(--cx-primary, #7c3aed);color:#fff;padding:11px 24px;border-radius:9px;text-decoration:none;font-weight:700">Ir a Envasado &rarr;</a></div>';
    return;
  }
  try{
    var r=await fetch('/api/brd/ordenes-unificadas?fase='+encodeURIComponent(fase),{credentials:'same-origin'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok||!d.ok){out.innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error: '+esc((d&&d.error)||r.status)+'</span>';return;}
    document.getElementById('summary').innerHTML=
      '<div class="box">'+d.resumen.total+' órdenes</div>'+
      '<div class="box">'+d.resumen.legajos+' con legajo EBR</div>'+
      '<div class="box">'+d.resumen.simples+' registro simple</div>';
    if(!d.ordenes.length){out.innerHTML='<div class="muted">Sin órdenes en esta fase.</div>';return;}
    var h='<table><thead><tr>'+
      '<th>N° de orden</th><th>N° lote</th><th>Producto</th>'+
      '<th class="num">Cant. teórica</th><th class="num">Cant. producida</th>'+
      '<th class="num">Cant. aprobada</th><th>Estado</th><th>Origen</th><th>Fecha</th><th></th>'+
      '</tr></thead><tbody>';
    d.ordenes.forEach(function(o){
      var aprob = o.aprobada!=null ? gfmt(o.aprobada) : (o.ml_envasable!=null? (Number(o.ml_envasable).toLocaleString('es-CO')+' mL') : '·');
      var acc = o.link ? '<a class="legajo" href="'+o.link+'">Abrir legajo →</a>' : '<span class="muted">·</span>';
      var org = o.origen==='legajo' ? '<span class="org org-l">LEGAJO</span>' : '<span class="org org-s">SIMPLE</span>';
      h+='<tr>'+
        '<td class="mono">'+esc(o.numero_op)+'</td>'+
        '<td class="mono">'+esc(o.lote_bulk||'·')+'</td>'+
        '<td>'+esc(o.producto||'·')+'</td>'+
        '<td class="num">'+gfmt(o.teorica_g)+'</td>'+
        '<td class="num">'+gfmt(o.producida_g)+'</td>'+
        '<td class="num">'+aprob+'</td>'+
        '<td>'+pill(o.estado)+'</td>'+
        '<td>'+org+'</td>'+
        '<td class="muted">'+esc(o.fecha||'·')+'</td>'+
        '<td>'+acc+'</td>'+
      '</tr>';
    });
    h+='</tbody></table>';
    out.innerHTML=h;
  }catch(e){out.innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error red: '+esc(e.message)+'</span>';}
}
ver('fabricacion',document.querySelector('.tab'));
</script>
</body></html>"""


@bp.route("/planta/ordenes-produccion", methods=["GET"])
def ordenes_produccion_page():
    """Página (solo lectura) · Órdenes de Producción unificadas estilo MyBatch."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/planta/ordenes-produccion"</script>',
                        mimetype="text/html")
    return Response(_ORDENES_PROD_HTML, mimetype="text/html")


# ──────────────────────────────────────────────────────────────────────────
# Detalle de Orden de Producción · layout estilo MyBatch (Sebastián 4-jun-2026)
# Sub-pasos A+B: cabecera + 5 botones + tabla "Pesaje de Materias Primas".
# Reusa /api/brd/ebr/<id>/vista-completa (datos ya existentes). Aditivo.
# El Timeline cronológico queda como uno de los botones.
# ──────────────────────────────────────────────────────────────────────────

_ORDEN_DETALLE_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Orden de Producción · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<script>
/* Capturador de errores VISIBLE (6-jun-diag) · corre antes que todo. Si el
   script principal de la página falla al parsear/ejecutar, el error se pinta
   en pantalla (sin DevTools) para diagnosticar el "Cargando…" eterno. */
window.addEventListener('error',function(e){
  try{
    var m=document.getElementById('cxerr');
    if(!m){m=document.createElement('div');m.id='cxerr';
      m.style.cssText='background:var(--cx-danger-pale, #fee2e2);color:var(--cx-danger-text, #991b1b);padding:12px 16px;margin:8px 0;border-radius:10px;font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap;border:1px solid #fca5a5';
      (document.body||document.documentElement).insertBefore(m,(document.body||document.documentElement).firstChild);}
    m.textContent='⚠ ERROR JS (por esto no carga): '+(e.message||(e.error&&e.error.message)||'desconocido')+
      '\\n@ '+((e.filename||'').split('/').pop())+' línea '+e.lineno+':'+e.colno;
  }catch(_){}
},true);
window.addEventListener('unhandledrejection',function(e){
  try{
    var m=document.getElementById('cxerr');
    if(!m){m=document.createElement('div');m.id='cxerr';
      m.style.cssText='background:var(--cx-warn-pale, #fef3c7);color:var(--cx-warn-text, #92400e);padding:12px 16px;margin:8px 0;border-radius:10px;font:12px/1.5 ui-monospace,monospace;white-space:pre-wrap;border:1px solid #fcd34d';
      (document.body||document.documentElement).insertBefore(m,(document.body||document.documentElement).firstChild);}
    var r=e&&e.reason; m.textContent='⚠ Promesa rechazada: '+((r&&r.message)||r||'?');
  }catch(_){}
});
</script>
<style>
/*__TOOLTIP_CSS__*/
*{box-sizing:border-box}
body{font-family:var(--cx-font);background:var(--cx-bg);color:var(--cx-text);margin:0;padding:24px}
/* 96vw = la regla de EOS para los modulos. Estaban clavadas en 1100-1200px: en un monitor de 1990 dejaban el 40% en blanco y la tabla de materiales -7 columnas- se desbordaba cortando 'Diferencia'. La orden madre ya usaba 96vw; se alinean las de DATOS. Los dos INSTRUCTIVOS quedan angostos a proposito: son formatos que se leen y se imprimen. */.wrap{max-width:96vw;margin:0 auto}
a.back{display:inline-flex;align-items:center;gap:8px;background:var(--cx-card, #fff);color:var(--cx-primary-text, #7c3aed);font-size:13px;font-weight:700;text-decoration:none;padding:10px 18px;border-radius:11px;border:1px solid #e9d5ff;box-shadow:0 2px 10px rgba(124,58,237,.10);transition:all .14s ease}
a.back:hover{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;border-color:transparent;box-shadow:0 6px 18px rgba(124,58,237,.30);transform:translateY(-1px)}
a.back .arw{font-size:15px;line-height:1}
.card{background:var(--cx-card, #fff);border-radius:16px;padding:0;box-shadow:0 4px 16px rgba(76,29,149,.07);margin-bottom:18px;overflow:hidden}
.card.pad{padding:22px}
#head{padding:0}
.hbar{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;padding:22px 26px}
.hkicker{font-size:12px;font-weight:700;opacity:.85;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
h1{font-size:28px;margin:0;color:#fff;letter-spacing:.5px}
.prod{font-size:16px;color:var(--cx-primary-soft, #ede9fe);font-weight:600;margin-top:4px}
.estado-badge{padding:6px 14px;border-radius:20px;font-size:12px;font-weight:800;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,.12)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:18px;font-size:13px;padding:22px 26px}
.grid .lbl{color:var(--cx-text-faint, #94a3b8);font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.4px}
.grid .val{color:var(--cx-text, #1e293b);margin-top:3px;font-weight:600;font-size:14px}
.liber-line{margin:0 26px 4px;padding:10px 14px;background:var(--cx-success-pale, #dcfce7);color:var(--cx-success-text, #166534);border-radius:8px;font-size:13px;font-weight:600}
.btns{display:flex;gap:10px;flex-wrap:wrap;padding:6px 26px 24px}
.btns a,.btns button{border:1px solid transparent;border-radius:var(--cx-r-md);padding:11px 18px;font-size:13px;font-weight:600;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;transition:background var(--cx-tr-fast),color var(--cx-tr-fast),border-color var(--cx-tr-fast),box-shadow var(--cx-tr-fast),transform .06s}
.btns a:active,.btns button:active{transform:translateY(1px)}
/* Toolbar RESTRINGIDO (premium): los secundarios son ghost neutro · solo
   "Instrucción de Manufactura" (la acción de trabajo) lleva el acento violeta.
   Antes: 5 colores saturados (arcoíris) = el tell #1 de amateur. */
.b-time,.b-pdf,.b-rot,.b-aj{background:var(--cx-card);color:var(--cx-text-soft);border-color:var(--cx-border)}
.b-time:hover,.b-pdf:hover,.b-rot:hover,.b-aj:hover{border-color:var(--cx-primary-light);color:var(--cx-primary-text);background:var(--cx-primary-pale)}
.b-mbr{background:var(--cx-primary);color:#fff}
.b-mbr:hover{background:var(--cx-primary-dark);box-shadow:var(--cx-sh-violet-sm)}
.b-soon{background:var(--cx-border, #e2e8f0);color:var(--cx-text-faint, #94a3b8);cursor:not-allowed}
.b-mini{background:#14b8a6;color:#fff;border:none;border-radius:8px;padding:7px 14px;font-size:12px;font-weight:700;cursor:pointer}
.b-i{background:var(--cx-info, #0ea5e9);color:#fff;border:none;border-radius:7px;width:30px;height:30px;font-style:italic;font-weight:800;cursor:pointer}
.b-e{background:var(--cx-warn, #f59e0b);color:#fff;border:none;border-radius:7px;width:30px;height:30px;cursor:pointer}
.b-pdf-sm{display:inline-flex;align-items:center;gap:5px;background:var(--cx-danger, #ef4444);color:#fff;text-decoration:none;font-size:11px;font-weight:700;padding:4px 10px;border-radius:7px;margin-left:10px;vertical-align:middle}
.cxmodal{display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);z-index:99998;align-items:center;justify-content:center;padding:20px}
.cxbox{background:var(--cx-card);border-radius:var(--cx-r-lg);max-width:560px;width:100%;box-shadow:var(--cx-sh-lg);overflow:hidden}
.cxhead{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;padding:16px 22px;display:flex;justify-content:space-between;align-items:center}
.cxhead h3{margin:0;font-size:16px}
.cxx{background:rgba(255,255,255,.25);border:none;color:#fff;width:30px;height:30px;border-radius:50%;font-size:16px;cursor:pointer;font-weight:700}
.cxbody{padding:18px 22px}
.mrow{display:flex;gap:14px;padding:9px 0;border-bottom:1px solid var(--cx-border-soft, #f1f5f9)}
.mrow:last-child{border-bottom:none}
.mk{flex:0 0 120px;color:var(--cx-text-faint, #94a3b8);font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.3px;padding-top:2px}
.mv{flex:1;color:var(--cx-text, #1e293b);font-size:14px;font-weight:500}
.st-fin{color:var(--cx-success-text, #166534);font-weight:800}.st-no{color:var(--cx-danger-text, #b91c1c);font-weight:800}.st-pend{color:var(--cx-text-faint, #94a3b8);font-weight:700}
h2{font-size:18px;color:var(--cx-primary-text, #7c3aed);margin:0 0 14px}
table{width:100%;border-collapse:collapse;font-size:12.5px}
th{text-align:left;padding:10px 9px;background:var(--cx-primary-pale, #f5f3ff);color:var(--cx-primary-text, #6d28d9);font-weight:800;font-size:11px;text-transform:uppercase;letter-spacing:.3px}
td{padding:10px 9px;border-bottom:1px solid var(--cx-border-soft, #f1f5f9);vertical-align:middle}
tbody tr:hover{background:#faf5ff}
.mono{font-family:ui-monospace,monospace;font-weight:700;color:var(--cx-info-text, #1e40af)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.delta-ok{color:var(--cx-success-text, #166534)}.delta-warn{color:var(--cx-warn-text, #b45309);font-weight:700}
.muted{color:var(--cx-text-faint, #94a3b8)}
#pasos-sec{display:block}
.printonly{display:none}
.btn-print{display:inline-flex;align-items:center;gap:6px;background:#ea580c;color:#fff;border:none;border-radius:8px;padding:9px 16px;font-size:13px;font-weight:700;cursor:pointer;margin-bottom:12px}
@media print{
  body{padding:0;background:var(--cx-card, #fff);color:var(--cx-text, #18181b)}
  .back,.btn-print,.noprint,.cxmodal,.b-time,.b-mbr,.b-pdf,.b-rot,.b-aj,.b-soon,.b-mini,.b-i,.b-e,.b-pdf-sm{display:none !important}
  .printonly{display:block;text-align:center;border-bottom:2px solid var(--cx-text, #0f172a);margin-bottom:12px;padding-bottom:8px}
  .printonly b{font-size:16px;letter-spacing:.5px}
  .printonly span{font-size:12px;color:var(--cx-text-soft, #334155)}
  .wrap{max-width:100%;margin:0}
  .card{box-shadow:none;border:1px solid var(--cx-border, #cbd5e1);break-inside:avoid;page-break-inside:avoid}
  h2{font-size:14px}
  table{font-size:10px;width:100%}
  tr{break-inside:avoid;page-break-inside:avoid}
  th,td{padding:4px 6px !important}
}
</style></head><body>
<div class="wrap">
<a class="back" href="/inventarios#fabricacion"><span class="arw">&larr;</span> Volver a Producción</a>
<div class="printonly"><b>Espagiria Laboratorio SAS</b><br><span>INSTRUCTIVO DE MANUFACTURA &middot; PRD-PRO-001-F01</span></div>
<div style="height:10px"></div>
<button class="btn-print" onclick="window.print()">&#128196; Descargar / Imprimir instructivo (PDF)</button>
<div class="card" id="head">Cargando…</div>
<div class="card pad" id="pasos-sec"><h2>📖 Instrucción de Manufactura</h2><div id="pasos"></div></div>
</div>
<div class="cxmodal" id="cxmodal" onclick="if(event.target===this)cerrarModal()">
  <div class="cxbox">
    <div class="cxhead"><h3>ℹ️ Detalles de la Verificación</h3><button class="cxx" onclick="cerrarModal()">×</button></div>
    <div class="cxbody" id="cxmbody"></div>
  </div>
</div>
<input type="file" id="reg-file" accept="image/*,application/pdf" capture="environment" style="display:none" onchange="_subirRegistroFile(this.files&&this.files[0])">
<div class="cxmodal" id="pesomodal" onclick="if(event.target===this)cerrarPeso()">
  <div class="cxbox">
    <div class="cxhead" style="background:linear-gradient(135deg,#f59e0b,#d97706)"><h3>✏️ Materia Prima Dispensada</h3><button class="cxx" onclick="cerrarPeso()">×</button></div>
    <div class="cxbody">
      <div id="peso-mp" style="font-weight:700;color:var(--cx-text, #1e293b);margin-bottom:4px"></div>
      <div id="peso-apesar" class="muted" style="font-size:12px;margin-bottom:12px"></div>
      <label style="display:block;font-size:11px;font-weight:800;color:var(--cx-text-faint, #94a3b8);text-transform:uppercase;letter-spacing:.3px;margin-bottom:4px">Cantidad pesada (g)</label>
      <input id="peso-cant" type="number" step="0.01" min="0" style="width:100%;padding:10px;border:1px solid var(--cx-border, #e2e8f0);border-radius:8px;font-size:15px;margin-bottom:12px">
      <label style="display:block;font-size:11px;font-weight:800;color:var(--cx-text-faint, #94a3b8);text-transform:uppercase;letter-spacing:.3px;margin-bottom:4px">N° de lote</label>
      <input id="peso-lote" type="text" style="width:100%;padding:9px;border:1px solid var(--cx-border, #e2e8f0);border-radius:8px;font-size:13px;margin-bottom:12px">
      <label style="display:block;font-size:11px;font-weight:800;color:var(--cx-text-faint, #94a3b8);text-transform:uppercase;letter-spacing:.3px;margin-bottom:4px">Observaciones</label>
      <textarea id="peso-obs" rows="2" style="width:100%;padding:9px;border:1px solid var(--cx-border, #e2e8f0);border-radius:8px;font-size:13px;resize:vertical"></textarea>
      <div id="peso-msg" style="font-size:12px;margin-top:8px"></div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:14px">
        <button onclick="cerrarPeso()" style="background:var(--cx-border-soft, #f1f5f9);color:var(--cx-text-soft, #475569);border:none;border-radius:8px;padding:9px 18px;font-weight:700;cursor:pointer">Cerrar</button>
        <button id="peso-save" onclick="guardarPeso()" style="background:var(--cx-success, #16a34a);color:#fff;border:none;border-radius:8px;padding:9px 22px;font-weight:700;cursor:pointer">Guardar</button>
      </div>
    </div>
  </div>
</div>
<script>
var EBR_ID = __EBR_ID__;
// DIAGNÓSTICO VISIBLE (6-jun) · prueba que el script SÍ corre en el navegador.
// Marca #head con un contador en vivo apenas arranca; load() lo reemplaza al
// recibir datos. Si el usuario ve "⏳ Conectando… Ns" subiendo, el JS está vivo.
(function(){
  try{
    var s=0;
    var el=document.getElementById('head');
    if(el) el.innerHTML='⏳ Conectando al servidor… <b id="cxsec">0</b>s';
    window.__cxTick=setInterval(function(){s++;var c=document.getElementById('cxsec');if(c)c.textContent=s;},1000);
  }catch(e){}
})();
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function gfmt(n){return (n==null||n==='')?'·':Number(n).toLocaleString('es-CO',{maximumFractionDigits:1})+' g';}
function estadoColor(e){var s=(e||'').toLowerCase();
  if(s.indexOf('liber')>=0||s.indexOf('aprob')>=0)return '#166534';
  if(s.indexOf('rechaz')>=0)return '#991b1b';
  if(s.indexOf('cuarentena')>=0)return '#1e40af';
  if(s.indexOf('complet')>=0)return '#0e7490';
  return '#854d0e';}
function estadoBg(e){var s=(e||'').toLowerCase();
  if(s.indexOf('liber')>=0||s.indexOf('aprob')>=0)return '#dcfce7';
  if(s.indexOf('rechaz')>=0)return '#fee2e2';
  if(s.indexOf('cuarentena')>=0)return '#dbeafe';
  if(s.indexOf('complet')>=0)return '#cffafe';
  return '#fef9c3';}
function togglePasos(){var s=document.getElementById('pasos-sec');s.style.display=s.style.display==='none'?'block':'none';if(s.style.display==='block')s.scrollIntoView({behavior:'smooth'});}
// 3. Dispensado · botón "✏️" → modal "Corregir Peso" (Cantidad + lote + obs)
var _pesoIdx=null;
function cerrarPeso(){var m=document.getElementById('pesomodal');if(m)m.style.display='none';}
function registrarPesaje(idx){
  var it=(window._pesajeSheet||[])[idx]; if(!it) return;
  _pesoIdx=idx;
  document.getElementById('peso-mp').innerHTML='<span class="mono">'+esc(it.material_id)+'</span> '+esc(it.material_nombre||'');
  document.getElementById('peso-apesar').textContent='Cantidad a pesar: '+(it.cant_a_pesar_g!=null?Number(it.cant_a_pesar_g).toLocaleString('es-CO',{maximumFractionDigits:1})+' g':'·');
  document.getElementById('peso-cant').value=(it.cant_pesada_g!=null?it.cant_pesada_g:(it.cant_a_pesar_g!=null?it.cant_a_pesar_g:''));
  document.getElementById('peso-lote').value=(it.lote&&it.lote!=='·'?it.lote:'');
  document.getElementById('peso-obs').value=it.obs_pesaje||'';
  document.getElementById('peso-msg').innerHTML='';
  document.getElementById('pesomodal').style.display='flex';
}
async function guardarPeso(){
  if(_pesoIdx===null) return;
  var it=(window._pesajeSheet||[])[_pesoIdx]; if(!it) return;
  var msg=document.getElementById('peso-msg');
  var real=parseFloat(document.getElementById('peso-cant').value);
  if(isNaN(real)||real<0){msg.innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Cantidad inválida</span>';return;}
  var lote=(document.getElementById('peso-lote').value||'').trim();
  var obs=(document.getElementById('peso-obs').value||'').trim();
  var btn=document.getElementById('peso-save'); btn.disabled=true; btn.textContent='Guardando…';
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/pesajes',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({material_id:it.material_id,cantidad_real_g:real,lote_mp:lote,notas:obs})});
    var d=await r.json();
    if(!r.ok){
      if(d&&d.codigo==='FIRMA_REQUERIDA'){msg.innerHTML='<span style="color:var(--cx-warn-text, #b45309)">🔒 Requiere e-firma (motor EBR estricto). Regístralo desde el runner de legajos.</span>';}
      else{msg.innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error: '+esc((d&&d.error)||r.status)+'</span>';}
      btn.disabled=false; btn.textContent='Guardar'; return;
    }
    cerrarPeso(); load();
  }catch(e){ msg.innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error de red: '+esc(e.message)+'</span>'; btn.disabled=false; btn.textContent='Guardar'; }
}
// 3. Dispensado · botón "i" → "Detalle del Pesaje" (Realizado por / Verificado por)
function infoPesaje(idx){
  var it=(window._pesajeSheet||[])[idx]; if(!it) return;
  function dpct(){ if(it.cant_a_pesar_g&&it.cant_pesada_g!=null){var dl=(it.cant_pesada_g-it.cant_a_pesar_g)/it.cant_a_pesar_g*100; return dl.toLocaleString('es-CO',{maximumFractionDigits:2})+'%';} return '·';}
  function fdt(s){return s?esc(s.substring(0,16).replace('T',' ')):'';}
  var realizado = it.pesado ? (esc(it.realizado_por_full||it.pesado_por||'·')+(it.pesado_at?' · '+fdt(it.pesado_at):'')) : '<span class="st-pend">· sin registrar</span>';
  var verificado = (it.verificado_por&&it.verificado_por.trim()) ? (esc(it.verificado_por_full||it.verificado_por)+(it.verificado_at?' · '+fdt(it.verificado_at):'')) : '<span class="st-pend">pendiente de verificación (Calidad)</span>';
  var rows=''
    +'<div class="mrow"><div class="mk">Materia Prima</div><div class="mv"><span class="mono">'+esc(it.material_id)+'</span> '+esc(it.material_nombre||'')+'</div></div>'
    +'<div class="mrow"><div class="mk">N° Lote</div><div class="mv mono">'+esc(it.lote||'·')+'</div></div>'
    +'<div class="mrow"><div class="mk">Cant. a pesar</div><div class="mv">'+gfmt(it.cant_a_pesar_g)+'</div></div>'
    +'<div class="mrow"><div class="mk">Cantidad Pesada</div><div class="mv"><b>'+(it.cant_pesada_g!=null?gfmt(it.cant_pesada_g):'<span class="st-pend">pendiente</span>')+'</b> <span class="muted">(desv '+dpct()+')</span></div></div>'
    +'<div class="mrow"><div class="mk">Realizado por</div><div class="mv">'+realizado+'</div></div>'
    +'<div class="mrow"><div class="mk">Verificado por</div><div class="mv">'+verificado+'</div></div>'
    +(it.obs_pesaje?'<div class="mrow"><div class="mk">Observación</div><div class="mv">'+esc(it.obs_pesaje)+'</div></div>':'');
  var b=document.getElementById('cxmbody'); if(b) b.innerHTML=rows;
  var ht=document.querySelector('#cxmodal .cxhead h3'); if(ht) ht.textContent='ℹ️ Detalle del Pesaje';
  var m=document.getElementById('cxmodal'); if(m) m.style.display='flex';
}
// 3. Dispensado · "✓ Verificar Dispensado" → valida completitud + tolerancia
function verificarDispensado(){
  var sh=window._pesajeSheet||[];
  if(!sh.length){alert('Esta orden no tiene fórmula con materias primas.');return;}
  var pend=sh.filter(function(x){return !x.pesado;});
  var fuera=sh.filter(function(x){return x.pesado && x.cant_a_pesar_g && x.cant_pesada_g!=null && Math.abs((x.cant_pesada_g-x.cant_a_pesar_g)/x.cant_a_pesar_g*100)>5;});
  if(pend.length){
    alert('⚠ Dispensado INCOMPLETO · faltan '+pend.length+' de '+sh.length+' materias primas por pesar:\\n\\n'+pend.slice(0,12).map(function(x){return '· '+(x.material_nombre||x.material_id);}).join('\\n')+(pend.length>12?'\\n…':''));
    return;
  }
  if(fuera.length){
    alert('⚠ Dispensado completo PERO '+fuera.length+' MP con desviación > 5% (revisar):\\n\\n'+fuera.map(function(x){return '· '+(x.material_nombre||x.material_id)+' ('+((x.cant_pesada_g-x.cant_a_pesar_g)/x.cant_a_pesar_g*100).toFixed(1)+'%)';}).join('\\n'));
    return;
  }
  alert('✓ Dispensado VERIFICADO · las '+sh.length+' materias primas están pesadas y dentro de tolerancia (±5%).');
}
// 5. Fabricación/Mezcla · botón "i" → detalle del paso (reusa el modal)
function infoPaso(i){
  var p=(window._pasos||[])[i]; if(!p) return;
  function fdt(s){return s?esc(s.substring(0,16).replace('T',' ')):'';}
  var realizado = p.completado_flag ? (esc(p.realizado_por_full||p.operario||'·')+(p.completado?' · '+fdt(p.completado):'')) : '<span class="st-pend">· pendiente</span>';
  var verificado = (p.verificado_por&&p.verificado_por.trim()) ? esc(p.verificado_por_full||p.verificado_por) : '<span class="st-pend">pendiente de verificación (Calidad)</span>';
  var rows=''
    +'<div class="mrow"><div class="mk">Paso</div><div class="mv"><b>'+esc(p.orden)+'</b></div></div>'
    +'<div class="mrow"><div class="mk">Actividad</div><div class="mv">'+esc(p.descripcion||'')+'</div></div>'
    +'<div class="mrow"><div class="mk">Realizado por</div><div class="mv">'+realizado+'</div></div>'
    +'<div class="mrow"><div class="mk">Verificado por</div><div class="mv">'+verificado+'</div></div>'
    +(p.observaciones?'<div class="mrow"><div class="mk">Observación / Resultado</div><div class="mv">'+esc(p.observaciones)+'</div></div>':'');
  var b=document.getElementById('cxmbody'); if(b) b.innerHTML=rows;
  var ht=document.querySelector('#cxmodal .cxhead h3'); if(ht) ht.textContent='ℹ️ Detalle del Paso';
  var m=document.getElementById('cxmodal'); if(m) m.style.display='flex';
}
// 5. Fabricación/Mezcla · botón "✏️" → registrar/completar el paso
async function completarPaso(i){
  var p=(window._pasos||[])[i]; if(!p) return;
  var obs=prompt('Resultado / observación del paso '+p.orden+':', p.observaciones||'');
  if(obs===null) return;
  var r=await fetch('/api/brd/ebr/'+EBR_ID+'/pasos/'+p.orden+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({observaciones:obs})});
  var d=await r.json();
  if(!r.ok){
    if(d&&(''+(d.error||'')).indexOf('e-signature')>=0){alert('🔒 Este paso requiere e-firma (motor EBR estricto). Regístralo desde el runner de legajos.');}
    else{alert('Error: '+((d&&d.error)||r.status));}
    return;
  }
  load();
}
// 6. Controles en Proceso · botón "i" → detalle del control (reusa el modal)
function infoIpc(i){
  var c=(window._ipc||[])[i]; if(!c) return;
  function fdt(s){return s?esc(s.substring(0,16).replace('T',' ')):'';}
  var conf = c.conforme===1?'<span class="st-fin">Cumple ✓</span>':c.conforme===0?'<span class="st-no">No cumple ✗</span>':c.conforme===2?'<span class="st-pend">No aplica</span>':'<span class="st-pend">pendiente</span>';
  var realizado = c.realizado_por ? (esc(c.realizado_por_full||c.realizado_por)+(c.fecha?' · '+fdt(c.fecha):'')) : '<span class="st-pend">· sin registrar</span>';
  var rows=''
    +'<div class="mrow"><div class="mk">Control</div><div class="mv">'+esc(c.control||'')+'</div></div>'
    +(c.rango?'<div class="mrow"><div class="mk">Rango / Spec</div><div class="mv">'+esc(c.rango)+'</div></div>':'')
    +'<div class="mrow"><div class="mk">Resultado</div><div class="mv"><b>'+esc(c.resultado||'pendiente')+'</b></div></div>'
    +'<div class="mrow"><div class="mk">Conforme</div><div class="mv">'+conf+'</div></div>'
    +'<div class="mrow"><div class="mk">Observaciones</div><div class="mv">'+esc(c.observaciones||'No aplica')+'</div></div>'
    +'<div class="mrow"><div class="mk">Realizado por</div><div class="mv">'+realizado+'</div></div>';
  var b=document.getElementById('cxmbody'); if(b) b.innerHTML=rows;
  var ht=document.querySelector('#cxmodal .cxhead h3'); if(ht) ht.textContent='ℹ️ Detalle del Control';
  var m=document.getElementById('cxmodal'); if(m) m.style.display='flex';
}
// Registrar un Control en Proceso (sección 6) · valor + Cumple/No cumple, o
// marcar "No aplica". Enruta a /ipc-resultados (MBR) o /ipc-estandar (estándar).
async function registrarIpc(i){
  var cc=(window._ipc||[])[i]; if(!cc) return;
  var aplica=confirm('Control: '+(cc.control||'')+'\\n\\n¿APLICA a este producto?\\n\\nAceptar = Sí (registrar resultado)\\nCancelar = NO APLICA');
  var body={};
  if(!aplica){
    body.no_aplica=true;
  } else if(cc.rango){
    var v=prompt('Valor medido ('+(cc.rango||'')+'):'); if(v===null)return; v=(v||'').trim(); if(v==='')return;
    if(isNaN(parseFloat(v.replace(',','.')))){alert('Valor numérico inválido');return;}
    body.valor_medido=parseFloat(v.replace(',','.'));
  } else {
    var conf=confirm('¿El control CUMPLE?\\n\\nAceptar = Cumple · Cancelar = No cumple');
    var txt=prompt('Resultado / observación (ej: 1,056 g/mL · Inodoro · Amarillento…):')||'';
    body.conforme=conf?1:0; body.valor_texto=txt.trim();
  }
  var url;
  if(cc.tipo==='estandar'){
    url='/api/brd/ebr/'+EBR_ID+'/ipc-estandar';
    body.control_codigo=cc.codigo; body.control_nombre=cc.control;
  } else {
    url='/api/brd/ebr/'+EBR_ID+'/ipc-resultados';
    body.ipc_spec_id=cc.spec_id;
  }
  try{
    var r=await fetch(url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok){alert((d&&d.error)||'No se pudo registrar el control');return;}
    if(d.desviacion){alert('⚠ Fuera de especificación · se abrió la desviación '+((d.desviacion&&d.desviacion.codigo)||'')+' automáticamente.');}
    load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
// 8. Registros Físicos · subir foto/PDF (el rótulo se imprime, se diligencia y se
// sube la foto · MyBatch). En el celular abre la cámara (capture=environment).
var _regDesc='';
function subirRegistroPick(){
  // El Estado de Limpieza de Áreas ya NO se sube como foto: es DIGITAL (rótulo
  // F02 auto-rellenado, ver arriba "rótulo de limpieza"). Aquí solo se suben los
  // registros que SÍ son evidencia física: rótulos de pesaje / MP dispensada.
  var c=prompt('¿Qué registro vas a subir?\\n\\n1 = Materia Prima Dispensada / Rótulo de pesaje\\n2 = Otro (escribir)\\n\\nNota: el Estado de Limpieza de Áreas es DIGITAL · usá el rótulo F02 (no subir foto).','1');
  if(c===null) return;
  var map={'1':'Materia Prima Dispensada / Rótulo de pesaje'};
  _regDesc = map[(c||'').trim()];
  if(!_regDesc){ _regDesc = prompt('Describe el registro:','') || 'Registro físico'; }
  var f=document.getElementById('reg-file'); if(f){f.value='';f.click();}
}
async function _subirRegistroFile(file){
  if(!file) return;
  if(file.size > 6*1024*1024){ alert('Archivo muy grande (máx ~6MB). Toma la foto en menor resolución.'); return; }
  var desc=_regDesc || file.name;
  var reader=new FileReader();
  reader.onload=async function(){
    var b64=((reader.result||'')+'').split(',')[1]||'';
    if(!b64){ alert('No se pudo leer el archivo'); return; }
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/registros-fisicos',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({descripcion:(desc||file.name),tipo:'foto',archivo_nombre:file.name,archivo_b64:b64})});
    var d=await r.json(); if(!r.ok){ alert('Error: '+((d&&d.error)||r.status)); return; }
    load();
  };
  reader.onerror=function(){ alert('Error al leer el archivo'); };
  reader.readAsDataURL(file);
}
// 7. Observaciones Generales · "+ Registrar"
async function registrarObservacion(){
  var desc=prompt('Observación general del proceso:');
  if(!desc) return;
  var r=await fetch('/api/brd/ebr/'+EBR_ID+'/observaciones',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({descripcion:desc})});
  var d=await r.json(); if(!r.ok){alert('Error: '+((d&&d.error)||r.status));return;}
  load();
}
// 1. Precauciones · "+ Agregar Equipo" (MyBatch ①)
async function agregarEquipo(){
  var desc=prompt('Equipo / precaución a registrar:');
  if(!desc) return;
  var tipo=confirm('¿Es un EQUIPO? (Aceptar=Equipo · Cancelar=Precaución)')?'equipo':'precaucion';
  var r=await fetch('/api/brd/ebr/'+EBR_ID+'/precauciones',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({tipo:tipo,descripcion:desc})});
  var d=await r.json(); if(!r.ok){alert('Error: '+(d.error||r.status));return;}
  load();
}
// 2/4. Despeje · botón "i" → modal "Detalles de la Verificación" (MyBatch parity)
function cerrarModal(){var m=document.getElementById('cxmodal');if(m)m.style.display='none';}
function _despArr(fab){return fab?(window._despejeChkFab||[]):(window._despejeChk||[]);}
function infoDespeje(idx, fab){
  var it=_despArr(fab).find(function(x){return x.idx===idx;}); if(!it) return;
  var estadoTxt = it.cumple===1?'<span class="st-fin">Sí cumple ✓</span>'
                : it.cumple===0?'<span class="st-no">No cumple ✗</span>'
                : '<span class="st-pend">Pendiente de verificar</span>';
  var rows=''
    + '<div class="mrow"><div class="mk">Verificación</div><div class="mv">'+esc(it.texto)+'</div></div>'
    + '<div class="mrow"><div class="mk">Cumple</div><div class="mv">'+estadoTxt+'</div></div>'
    + '<div class="mrow"><div class="mk">Responsable</div><div class="mv">'+esc(it.registrado_por||'· sin registrar')+'</div></div>'
    + '<div class="mrow"><div class="mk">Fecha / Hora</div><div class="mv">'+(it.fecha?esc(it.fecha.substring(0,16).replace('T',' ')):'·')+'</div></div>'
    + '<div class="mrow"><div class="mk">Observación</div><div class="mv">'+esc(it.observaciones||'Ninguna')+'</div></div>';
  var body=document.getElementById('cxmbody');
  if(body) body.innerHTML=rows;
  var m=document.getElementById('cxmodal'); if(m) m.style.display='flex';
}
// 2/4. Despeje · botón "✏️" · operario REGISTRA / Calidad CORRIGE
async function editDespeje(idx, fab){
  var etapa = fab?'fabricacion':'dispensacion';
  var it=_despArr(fab).find(function(x){return x.idx===idx;}); if(!it) return;
  var esCorreccion = it.cumple!=null;
  var titulo = esCorreccion ? 'CORREGIR RESULTADO (solo Calidad / Dirección Técnica)' : 'REGISTRAR VERIFICACIÓN (operario)';
  var c=confirm(titulo+'\\n\\n'+it.texto+'\\n\\n¿CUMPLE? (Aceptar=Sí · Cancelar=No)');
  var obs=prompt('Observación'+(esCorreccion?' / motivo de la corrección':' (opcional)')+':', it.observaciones||'')||'';
  var r=await fetch('/api/brd/ebr/'+EBR_ID+'/despeje-item',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({item_idx:idx,cumple:c?1:0,observaciones:obs,etapa:etapa})});
  var d=await r.json();
  if(!r.ok){
    if(r.status===403){alert('🔒 '+(d.error||'Solo Calidad / Dirección Técnica puede corregir un resultado ya registrado.'));}
    else{alert('Error: '+(d.error||r.status));}
    return;
  }
  load();
}
async function ajustarOrden(){
  // + Ajuste: corrige la cantidad de la producción asociada (re-escala MP por FEFO).
  // Reusa /api/produccion/<pid>/ajustar-cantidad (admin · audit INVIMA).
  try{
    var pr=await fetch('/api/brd/ebr/'+EBR_ID+'/produccion-id',{credentials:'same-origin'});
    var pd=await pr.json();
    if(!pd.produccion_id){alert('Esta orden no tiene una producción asociada para ajustar (legajo sin registro de producción).');return;}
    var nv=prompt('Nueva cantidad a fabricar (kg):'); if(nv===null)return; nv=parseFloat(nv);
    if(!nv||nv<=0){alert('Cantidad inválida');return;}
    var mot=(prompt('Motivo del ajuste (mínimo 10 caracteres · audit INVIMA):')||'').trim();
    if(mot.length<10){alert('El motivo debe tener al menos 10 caracteres');return;}
    var t=''; try{var cr=await fetch('/api/csrf-token',{credentials:'same-origin'});t=(await cr.json()).csrf_token||'';}catch(e){}
    var r=await fetch('/api/produccion/'+pd.produccion_id+'/ajustar-cantidad',{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':t},body:JSON.stringify({nueva_cantidad_kg:nv,motivo:mot})});
    var d=await r.json();
    if(!r.ok){alert('No se pudo ajustar: '+((d&&d.error)||r.status));return;}
    alert('✓ Ajustado a '+nv+' kg. '+(d.mensaje||''));
    location.reload();
  }catch(e){alert('Error de red: '+(e&&e.message||e));}
}
async function load(){
  var headEl=document.getElementById('head');
  try{
    // Timeout duro 25s · una orden nunca debe quedarse en "Cargando…" eterno.
    var ctrl=new AbortController();
    var to=setTimeout(function(){ctrl.abort();},15000);
    var r;
    try{
      r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store',signal:ctrl.signal});
    }catch(fe){
      clearTimeout(to); try{clearInterval(window.__cxTick);}catch(e){}
      var msg=(fe&&fe.name==='AbortError')
        ? 'El servidor no respondió en 15s (posible cuelgue del lote '+EBR_ID+'). Avísame para revisarlo.'
        : 'No se pudo contactar el servidor: '+esc((fe&&fe.message)||fe);
      headEl.innerHTML='<div style="padding:24px;color:var(--cx-danger-text, #b91c1c)"><b>⏱ '+msg+'</b><br><button onclick="load()" style="margin-top:10px;background:var(--cx-primary, #7c3aed);color:#fff;border:none;border-radius:8px;padding:8px 16px;font-weight:700;cursor:pointer">Reintentar</button></div>';
      return;
    }
    clearTimeout(to);
    if(r.status===401){location.href='/login';return;}
    var d;
    try{ d=await r.json(); }
    catch(je){
      var txt=''; try{txt=await r.text();}catch(e2){}
      headEl.innerHTML='<div style="padding:24px;color:var(--cx-danger-text, #b91c1c)"><b>Error '+r.status+' del servidor.</b><br><span style="font-size:12px;color:var(--cx-text-mute, #64748b)">'+esc((txt||'').substring(0,300))+'</span></div>';
      return;
    }
    if(!r.ok){headEl.innerHTML='<div style="padding:24px;color:var(--cx-danger-text, #b91c1c)"><b>Error '+r.status+': '+esc(d.error||'fallo')+'</b></div>';return;}
    var h=d.header||{};
    var numop = h.numero_op || ('EBR-'+EBR_ID);
    var estado = h.estado||'·';
    var fase = h.fase||'fabricacion';
    var faseLbl = ({fabricacion:'Fabricación · OP',envasado:'Envasado · OF',acondicionamiento:'Acondicionamiento · OA'})[fase]||fase;
    // Rótulos de pesaje: reusa el generador existente /rotulos/<producto>/<kg>
    var prodRot = encodeURIComponent(h.producto||h.titulo||'');
    var kgRot = (Number(h.lote_size_g||0)/1000) || 1;
    try{clearInterval(window.__cxTick);}catch(e){}
    document.getElementById('head').innerHTML =
      '<div class="hbar">'+
        '<div class="htitle">'+
          '<div class="hkicker">📋 Orden de Producción · '+esc(faseLbl)+'</div>'+
          '<h1>'+esc(numop)+'</h1>'+
          '<div class="prod">'+esc(h.producto||h.titulo||'·')+'</div>'+
          ((d.mi_rol&&d.mi_rol.rol)?'<div style="margin-top:6px"><span style="display:inline-flex;align-items:center;gap:5px;background:var(--cx-primary-pale, #f5f3ff);color:var(--cx-primary-text, #6d28d9);font-size:12px;font-weight:700;padding:4px 11px;border-radius:20px;border:1px solid var(--cx-primary-light, #a78bfa)">&#128100; '+esc(d.mi_rol.rol)+'</span></div>':'')+
        '</div>'+
        '<span class="estado-badge" style="background:'+estadoBg(estado)+';color:'+estadoColor(estado)+'">'+esc(estado)+'</span>'+
      '</div>'+
      bandaAprobacion(h,d.mi_rol)+
      '<div class="grid">'+
        '<div><div class="lbl">N° de Lote Bulk</div><div class="val mono">'+esc(h.lote_codigo||'·')+'</div></div>'+
        '<div><div class="lbl">Tamaño de Lote</div><div class="val">'+gfmt(h.lote_size_g)+'</div></div>'+
        '<div><div class="lbl">Fecha / Hora</div><div class="val">'+esc((h.iniciado_at_utc||'·').substring(0,16).replace("T"," "))+'</div></div>'+
        '<div><div class="lbl">Área o Línea</div><div class="val">'+esc(h.area_linea||'·')+'</div></div>'+
        '<div><div class="lbl">Elaborado por</div><div class="val">'+esc(h.operario||'·')+'</div></div>'+
        '<div><div class="lbl">Supervisado por</div><div class="val">'+esc(h.supervisado_por||'·')+'</div></div>'+
        '<div style="grid-column:1/-1"><div class="lbl">Observaciones</div><div class="val" style="font-weight:400">'+esc(h.observaciones||'Ninguna')+'</div></div>'+
      '</div>'+
      (h.liberado_por ? '<div class="liber-line">✅ Liberado por <b>'+esc(h.liberado_por)+'</b>'+(h.liberado_at_utc?(' · '+esc(h.liberado_at_utc.substring(0,16).replace("T"," "))):'')+'</div>' : '')+
      '<div class="btns">'+
        '<a class="b-time" data-tip="Línea de tiempo del lote: cada evento del legajo (inicio, pesajes, pasos, IPC, firmas) en orden cronológico." href="/brd/timeline/'+EBR_ID+'">📜 Timeline Batch Record</a>'+
        '<button class="b-mbr" data-tip="Abre la instrucción de manufactura: cabecera del lote, precauciones, despeje de línea y pasos del proceso." onclick="togglePasos()">📖 Instrucción de Manufactura</button>'+
        '<a class="b-pdf" data-tip="Descarga el legajo completo del lote en PDF (Batch Record) para imprimir o archivar." href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">📄 Descargar PDF</a>'+
        '<a class="b-rot" data-tip="Genera los rótulos de pesaje de materias primas para imprimir y pegar en cada recipiente." href="/rotulos/'+prodRot+'/'+kgRot+'" target="_blank">🖨 Rótulos de Pesaje</a>'+
        '<button class="b-aj" data-tip="Corrige la cantidad fabricada del lote y re-escala las materias primas (queda auditado · INVIMA)." onclick="ajustarOrden()">➕ Ajuste</button>'+
      '</div>';
    // Instrucción de Manufactura (MyBatch parity): cabecera de manufactura
    // (cantidades · densidad · rendimiento · aprobado calidad) + precauciones + pasos.
    function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
    function dt(s){return s? esc(String(s).substring(0,16).replace("T"," ")) : '·';}
    function mlf(v){return v!=null? (Number(v).toLocaleString('es-CO',{minimumFractionDigits:2,maximumFractionDigits:2})+' mL') : '·';}
    // Cantidad Producida/Aprobada = "X Gr - Y mL" (granel en gramos y su equivalente mL).
    var prodAprob = (h.cantidad_real_g!=null? gfmt(h.cantidad_real_g):'·') +
                    (h.ml_envasable!=null? (' - '+mlf(h.ml_envasable)) : '');
    var estManuf = h.estado||'·';
    // Cabecera fiel a "INSTRUCCIONES DE MANUFACTURA" (MyBatch · Sebastián 5-jun).
    var manuf='<div class="grid" style="padding:0;margin-bottom:16px">'+
      fld('N° de Lote Bulk', '<span class="mono">'+esc(h.lote_codigo||'·')+'</span>')+
      fld('Cantidad Ordenada', gfmt(h.cantidad_objetivo_g))+
      fld('Área o Línea', esc(h.area_linea||'·'))+
      fld('Fecha Inicio', dt(h.iniciado_at_utc))+
      fld('Fecha Final', dt(h.completado_at_utc))+
      fld('Estado Actual', '<b style="color:'+estadoColor(estManuf)+'">'+esc(estManuf)+'</b>')+
      fld('Cantidad Producida/Aprobada', prodAprob)+
      fld('Densidad', h.densidad_g_ml? (Number(h.densidad_g_ml).toLocaleString('es-CO',{maximumFractionDigits:3})+' g/mL'):'·')+
      fld('Rendimiento', h.yield_pct!=null? (Number(h.yield_pct).toLocaleString('es-CO',{maximumFractionDigits:2})+'%'):'·')+
      fld('Cantidad Disponible', mlf(h.cantidad_disponible_ml))+
      fld('Supervisado por', esc(h.supervisado_por||'·'))+
      fld('Aprobado por (Calidad)', esc(h.liberado_por_full||h.liberado_por||'·'))+
      '</div>';
    var editable = (estado==='iniciado'||estado==='en_proceso') && !!(d.mi_rol && d.mi_rol.puede_ejecutar);
    // 1. Precauciones (MyBatch ① · texto + "+ Agregar Equipo" + lista de equipos/precauciones)
    var prec=d.precauciones||[];
    var precHtml='<div style="display:flex;align-items:center;gap:12px;margin:14px 0 8px">'+
        '<h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:0">1. Precauciones</h3>'+
        (editable?'<button class="b-mini" data-tip="Registra un equipo usado o una precaución del proceso en este lote." onclick="agregarEquipo()">+ Agregar Equipo</button>':'')+
      '</div>'+
      '<div style="font-size:13px;color:var(--cx-text-soft, #334155);margin-bottom:8px">Tenga en cuenta las siguientes precauciones antes de iniciar el proceso de fabricación:</div>'+
      (prec.length
        ? '<ul style="margin:0 0 14px 18px;font-size:13px;color:var(--cx-text-soft, #334155)">'+prec.map(function(p){
            var et=(p.tipo==='equipo')?'🛠 Equipo':'⚠ Precaución';
            return '<li><b>'+et+':</b> '+esc(p.descripcion||'')+(p.registrado_por?' <span class="muted">('+esc(p.registrado_por)+')</span>':'')+'</li>';}).join('')+'</ul>'
        : '<div class="muted" style="margin-bottom:14px">Sin equipos/precauciones registrados.</div>');
    // 2/4. Despeje de Línea · MISMO checklist, dos etapas (dispensación + fabricación).
    window._despejeChk=d.despeje_checklist||[];
    window._despejeChkFab=d.despeje_checklist_fab||[];
    function cumpleCell(c){
      if(c===1) return '<span style="color:var(--cx-success-text, #166534);font-weight:700">Sí ✓</span>';
      if(c===0) return '<span style="color:var(--cx-danger-text, #b91c1c);font-weight:700">No ✗</span>';
      return '<span class="muted">Pendiente</span>';
    }
    // num=número de sección, titulo=Dispensación/Fabricación, etapa=string, fab=0/1
    function buildDespeje(arr, num, titulo, etapa, fab){
      return '<h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:18px 0 6px">'+num+'. Despeje de Línea - '+titulo+
        '<a class="b-pdf-sm" href="/brd/despeje/'+EBR_ID+'?etapa='+etapa+'" target="_blank" data-tip="Descarga/imprime el formato del despeje de '+titulo.toLowerCase()+' (registro GMP firmable).">📄 PDF</a>'+
        '</h3>'+
        '<div style="font-size:13px;color:var(--cx-text-soft, #334155);margin-bottom:8px">Realizar despeje en el área de '+titulo.toLowerCase()+' de acuerdo a los procedimientos internos, y realice las siguientes verificaciones:</div>'+
        '<table><thead><tr><th>Verificación</th><th style="text-align:center">Cumple</th><th style="text-align:center">Acciones</th></tr></thead><tbody>'+
        arr.map(function(it,n){
          // items RETIRADOS del procedimiento: se conservan (Part 11) pero no se re-registran
          var marca = it.historico ? ' <span style="font-size:11px;font-weight:700;color:var(--cx-warn-text,#b45309);background:var(--cx-warn-pale,#fffbeb);padding:2px 7px;border-radius:999px;white-space:nowrap">retirado del procedimiento</span>' : '';
          return '<tr'+(it.historico?' style="opacity:.72"':'')+'><td><b style="color:var(--cx-text-mute,#6b6b74)">'+(it.historico?'·':(n+1))+'</b> '+esc(it.texto)+marca+'</td>'+
            '<td style="text-align:center">'+cumpleCell(it.cumple)+'</td>'+
            '<td style="text-align:center;white-space:nowrap">'+
              '<button class="b-i tip-r" data-tip="Detalles de la verificación: texto completo, si cumple, quién lo verificó y cuándo." onclick="infoDespeje('+it.idx+','+fab+')">i</button> '+
              ((editable&&!it.historico)?'<button class="b-e tip-r" data-tip="'+(it.cumple!=null?'Corregir Resultado · solo Calidad / Dirección Técnica puede cambiar un resultado ya registrado.':'Registrar verificación (operario): marca si cumple Sí/No + observación.')+'" onclick="editDespeje('+it.idx+','+fab+')">✏️</button>':'')+
            '</td></tr>';
        }).join('')+'</tbody></table>'+
        '<div style="font-size:11px;color:var(--cx-text-faint, #94a3b8);margin:6px 0 14px">Sí = cumple · No = no cumple · Pendiente = sin verificar. Cada verificación queda con responsable y hora.</div>';
    }
    var despHtml=buildDespeje(window._despejeChk, '2', 'Dispensación', 'dispensacion', 0);
    var despFabHtml=buildDespeje(window._despejeChkFab, '4', 'Fabricación', 'fabricacion', 1);
    // 3. Dispensado de Materias Primas · INTEGRADO en el instructivo (en secuencia,
    // como en MyBatch · ya no es una tarjeta aparte). % · N° Lote · Cant. a pesar ·
    // Cant. pesada · Acciones (i / ✏️) + Verificar Dispensado + PDF.
    var sheet=d.pesaje_sheet||[];
    window._pesajeSheet=sheet;
    var dispHtml;
    if(sheet.length){
      var pend=sheet.filter(function(x){return !x.pesado;}).length;
      dispHtml='<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:18px 0 6px">'+
          '<h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:0">3. Dispensado de Materias Primas'+
            '<a class="b-pdf-sm" href="/brd/dispensado/'+EBR_ID+'" target="_blank" data-tip="Descarga/imprime la hoja de dispensado (registro GMP).">📄 PDF</a></h3>'+
          (editable?'<button class="b-mini" data-tip="Valida que todas las MP estén pesadas y dentro de tolerancia (±5%)." onclick="verificarDispensado()">✓ Verificar Dispensado</button>':'')+
        '</div>'+
        '<div style="font-size:12px;color:var(--cx-text-mute, #64748b);margin-bottom:6px">'+sheet.length+' materias primas · '+(sheet.length-pend)+' pesadas · '+pend+' pendientes</div>'+
        '<div style="font-size:12.5px;color:var(--cx-text-soft, #334155);margin-bottom:8px">Realizar el dispensado de materias primas según las cantidades de la orden y los procedimientos internos.</div>'+
        '<table><thead><tr><th>Materia Prima</th><th class="num">%</th><th>N° Lote</th>'+
        '<th class="num">Cant. a pesar</th><th class="num">Cant. pesada</th><th style="text-align:center">Acciones</th></tr></thead><tbody>'+
        sheet.map(function(p,i){
          var pesadaCol;
          if(p.pesado){
            var delta = (p.cant_a_pesar_g&&p.cant_pesada_g!=null)?((p.cant_pesada_g-p.cant_a_pesar_g)/p.cant_a_pesar_g*100):null;
            var dcl = (delta!=null&&Math.abs(delta)>5)?'delta-warn':'delta-ok';
            pesadaCol='<span class="'+dcl+'">'+gfmt(p.cant_pesada_g)+' ✓</span>';
          } else { pesadaCol='<span style="color:var(--cx-border, #cbd5e1)">pendiente</span>'; }
          return '<tr>'+
            '<td><span class="mono">'+esc(p.material_id)+'</span> '+esc(p.material_nombre||'')+'</td>'+
            '<td class="num">'+(p.porcentaje!=null?Number(p.porcentaje).toLocaleString('es-CO',{maximumFractionDigits:3})+'%':'·')+'</td>'+
            '<td class="mono">'+esc(p.lote||'·')+'</td>'+
            '<td class="num">'+gfmt(p.cant_a_pesar_g)+'</td>'+
            '<td class="num">'+pesadaCol+'</td>'+
            '<td style="text-align:center;white-space:nowrap">'+
              '<button class="b-i tip-r" data-tip="Detalle del Pesaje: cantidad pesada, realizado por (operario) y verificado por (Calidad)." onclick="infoPesaje('+i+')">i</button> '+
              (editable?'<button class="b-e tip-r" data-tip="Corregir Peso: ajusta la cantidad pesada y agrega observación." onclick="registrarPesaje('+i+')">✏️</button>':'')+
            '</td>'+
          '</tr>';
        }).join('')+'</tbody></table>'+
        '<div class="muted" style="margin:6px 0 14px;font-size:11px">El pesaje queda con tu usuario y la hora. Con el motor EBR en modo estricto, además exige e-firma (se registra desde el runner de legajos).</div>';
    } else {
      dispHtml='<h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:18px 0 6px">3. Dispensado de Materias Primas</h3>'+
        '<div class="muted" style="margin-bottom:14px">Esta orden no tiene fórmula con materias primas.</div>';
    }
    // Ajustes de materias primas (MyBatch · subsección entre dispensado y despeje fab)
    var ajustesHtml='<h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:18px 0 6px">Ajustes</h3>'+
      '<div class="muted" style="margin-bottom:14px;font-size:13px">Sin registro de ajustes de materias primas.</div>';
    // 5. Fabricación / Mezclado · ACTIVIDAD / Realizado por / Verificado por / Acciones
    // (MyBatch) · los pasos vienen del MBR del producto (mbr_pasos → ebr_pasos_ejecutados).
    var pasos=d.pasos||[];
    window._pasos=pasos;
    var pasosHtml='<h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:18px 0 6px">5. Fabricación / Mezclado</h3>'+
      '<div style="font-size:13px;color:var(--cx-text-soft, #334155);margin-bottom:8px">Realizar las siguientes actividades de acuerdo al orden establecido.</div>'+
      (pasos.length
      ? '<table><thead><tr><th>Actividad</th><th>Realizado por</th><th>Verificado por</th><th style="text-align:center">Acciones</th></tr></thead><tbody>'+
        pasos.map(function(p,i){
          var realizado = p.completado_flag ? (esc(p.realizado_por_full||p.operario||'·')+(p.completado?' <span class="muted">'+esc(p.completado.substring(0,16).replace("T"," "))+'</span>':'')) : '<span class="muted">pendiente</span>';
          var verificado = (p.verificado_por&&p.verificado_por.trim()) ? esc(p.verificado_por_full||p.verificado_por) : '<span class="muted">·</span>';
          return '<tr><td style="font-size:12.5px"><b>Paso '+esc(p.orden)+'.</b> '+esc(p.descripcion)+'</td>'+
            '<td style="font-size:11.5px">'+realizado+'</td>'+
            '<td style="font-size:11.5px">'+verificado+'</td>'+
            '<td style="text-align:center;white-space:nowrap">'+
              '<button class="b-i tip-r" data-tip="Detalles del paso: actividad, realizado por y verificado por." onclick="infoPaso('+i+')">i</button> '+
              (editable?'<button class="b-e tip-r" data-tip="Registrar / corregir este paso (queda con tu usuario y la hora)." onclick="completarPaso('+i+')">✏️</button>':'')+
            '</td></tr>';
        }).join('')+'</tbody></table>'
      : '<div class="muted">Sin pasos registrados · los pasos de fabricación se definen en el MBR del producto y se copian al crear el legajo.</div>');
    // 6. Controles en Proceso (IPC) · CONTROL / RESULTADO / OBSERVACIONES / Realizado por
    var ipc=d.ipc||[];
    window._ipc=ipc;
    function cumpleBadge(c){
      if(c===1) return ' <span style="background:var(--cx-success-pale, #dcfce7);color:var(--cx-success-text, #166534);padding:1px 8px;border-radius:10px;font-size:10px;font-weight:800">CUMPLE</span>';
      if(c===0) return ' <span style="background:var(--cx-danger-pale, #fee2e2);color:var(--cx-danger-text, #991b1b);padding:1px 8px;border-radius:10px;font-size:10px;font-weight:800">NO CUMPLE</span>';
      if(c===2) return ' <span style="background:var(--cx-border, #e2e8f0);color:var(--cx-text-soft, #475569);padding:1px 8px;border-radius:10px;font-size:10px;font-weight:800">NO APLICA</span>';
      return '';
    }
    var ipcHtml='<h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:18px 0 6px">6. Controles en Proceso</h3>'+
      '<div style="font-size:13px;color:var(--cx-text-soft, #334155);margin-bottom:8px">Realizar muestreo y registrar el control en proceso:</div>'+
      (ipc.length
      ? '<table><thead><tr><th>Control</th><th>Resultado</th><th>Observaciones</th><th>Realizado por</th><th style="text-align:center">Acciones</th></tr></thead><tbody>'+
        ipc.map(function(cc,i){
          var resCol = cc.conforme===2 ? cumpleBadge(2)
                     : (cc.resultado ? (esc(cc.resultado)+cumpleBadge(cc.conforme)) : '<span class="muted">pendiente</span>');
          var regBtn = editable ? '<button class="b-e tip-r" data-tip="Registrar el control: valor + Cumple/No cumple, o marcar No aplica." onclick="registrarIpc('+i+')">✏️</button>' : '';
          return '<tr><td style="font-size:12.5px">'+esc(cc.control)+(cc.rango?' <span class="muted" style="font-size:10px">('+esc(cc.rango)+')</span>':'')+'</td>'+
            '<td style="font-size:12.5px">'+resCol+'</td>'+
            '<td style="font-size:11.5px">'+esc(cc.observaciones||'No aplica')+'</td>'+
            '<td style="font-size:11.5px">'+(cc.realizado_por?esc(cc.realizado_por_full||cc.realizado_por):'<span class="muted">·</span>')+'</td>'+
            '<td style="text-align:center;white-space:nowrap"><button class="b-i tip-r" data-tip="Detalle del control: rango, resultado, conforme, quién y cuándo." onclick="infoIpc('+i+')">i</button> '+regBtn+'</td>'+
          '</tr>';
        }).join('')+'</tbody></table>'
      : '<div class="muted">Sin controles en proceso · se definen en el MBR del producto (parámetros como densidad, pH, color…).</div>');
    // 7. Observaciones Generales del Proceso (bitácora · + Registrar)
    var obsP=d.observaciones_proceso||[];
    var obsHtml='<div style="display:flex;align-items:center;gap:12px;margin:18px 0 6px">'+
        '<h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:0">7. Observaciones Generales del Proceso</h3>'+
        (editable?'<button class="b-mini" data-tip="Registra una observación general del proceso (queda con tu usuario y la hora)." onclick="registrarObservacion()">+ Registrar</button>':'')+
      '</div>'+
      (obsP.length
      ? '<table><thead><tr><th>Descripción de la observación</th><th>Realizada por</th><th>Fecha y hora</th></tr></thead><tbody>'+
        obsP.map(function(o){return '<tr><td style="font-size:12.5px">'+esc(o.descripcion||'')+'</td>'+
          '<td style="font-size:11.5px">'+esc(o.registrado_por_full||o.registrado_por||'·')+'</td>'+
          '<td class="muted" style="font-size:11px">'+esc((o.fecha||'').substring(0,16).replace("T"," "))+'</td></tr>';}).join('')+'</tbody></table>'
      : '<div class="muted">Sin observaciones registradas.</div>');
    // 8. Registros Físicos del Proceso Manufactura (fotos/PDF adjuntos)
    var regs=d.registros_fisicos||[];
    var regHtml='<div style="display:flex;align-items:center;gap:12px;margin:18px 0 6px">'+
        '<h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:0">8. Registros Físicos del Proceso Manufactura</h3>'+
        (editable?'<button class="b-mini" data-tip="Sube una foto o PDF del registro físico diligenciado (ej: rótulo de pesaje firmado). En el celular abre la cámara." onclick="subirRegistroPick()">📷 Subir registro</button>':'')+
      '</div>'+
      (regs.length
      ? '<table><thead><tr><th>Código</th><th>Descripción</th><th style="text-align:center">Acciones</th></tr></thead><tbody>'+
        regs.map(function(g){return '<tr><td class="mono">'+esc(g.id)+'</td><td style="font-size:12.5px">'+esc(g.descripcion||'')+'</td>'+
          '<td style="text-align:center">'+(g.tiene_pdf?'<a class="b-pdf-sm" href="/api/brd/ebr/'+EBR_ID+'/registros-fisicos/'+g.id+'/pdf" target="_blank" data-tip="Ver el registro físico (foto o PDF).">📄 Ver</a>':'<span class="muted">·</span>')+'</td></tr>';}).join('')+'</tbody></table>'
      : '<div class="muted">Sin registros físicos adjuntos.</div>');
    // Rótulo de limpieza del área (PRD-PRO-002-F02) · enlace al rótulo virtual.
    var _aid=(d.header&&d.header.area_id)?d.header.area_id:null;
    var rotuloHtml=_aid
      ? '<div style="display:flex;align-items:center;gap:12px;margin:18px 0 6px"><h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:0">🏷️ Rótulo de limpieza del área</h3></div>'
        + '<div class="muted" style="font-size:12.5px;margin-bottom:6px">Estado de limpieza de '+esc(d.header.area_linea||'')+' (formato PRD-PRO-002-F02). El estado fluye con la producción · se opera desde «Estado salas en vivo».</div>'
        + '<a class="b-pdf-sm" href="/planta/rotulo-limpieza/'+_aid+'/pdf" target="_blank" data-tip="Abre el rótulo de limpieza F02 del área de esta orden.">🖨️ Ver / imprimir rótulo F02</a>'
      : '';
    // 9. Correcciones / Auditoría (Audit Trail · Part 11 · MyBatch parity).
    var corrs=d.correcciones||[];
    var corrHtml='<div style="display:flex;align-items:center;gap:12px;margin:18px 0 6px"><h3 style="font-size:15px;color:var(--cx-primary-text, #7c3aed);margin:0">📝 Correcciones / Auditoría</h3></div>'+
      (corrs.length
       ? corrs.map(function(cr){
           var hd='<div style="font-weight:700;font-size:12.5px;margin-top:10px">'+esc(cr.usuario_full||cr.usuario)+' · '+esc(cr.accion)+' <span class="muted" style="font-weight:400">'+dt(cr.fecha)+'</span></div>';
           if(cr.campos && cr.campos.length){
             hd+='<table style="margin-top:4px"><thead><tr><th>Campo</th><th>Valor anterior</th><th>Valor nuevo</th></tr></thead><tbody>'+
               cr.campos.map(function(cp){return '<tr><td style="font-size:11.5px">'+esc(cp.campo)+'</td><td style="font-size:11.5px;color:var(--cx-text-faint, #94a3b8)">'+esc(cp.anterior||'·')+'</td><td style="font-size:11.5px;color:var(--cx-success-text, #166534)">'+esc(cp.nuevo||'·')+'</td></tr>';}).join('')+'</tbody></table>';
           } else if(cr.detalle){
             hd+='<div class="muted" style="font-size:11.5px">'+esc(cr.detalle)+'</div>';
           }
           return hd;
         }).join('')
       : '<div class="muted">Sin correcciones registradas.</div>');
    document.getElementById('pasos').innerHTML = manuf + precHtml + despHtml + dispHtml + ajustesHtml + despFabHtml + pasosHtml + ipcHtml + obsHtml + regHtml + rotuloHtml + corrHtml;
  }catch(e){document.getElementById('head').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error red: '+esc(e.message)+'</span>';}
}
load();
</script>
</body></html>"""


@bp.route("/planta/orden/<int:ebr_id>", methods=["GET"])
def orden_detalle_page(ebr_id):
    """Detalle de Orden de Producción (legajo EBR) estilo MyBatch · solo lectura.
    Sub-pasos A+B: cabecera + botones + pesaje. Reusa vista-completa.
    El ENVASADO tiene su PROPIA página (aislada de producción · 9-jun) → redirige."""
    if not session.get("compras_user"):
        return Response(f'<script>location.href="/login?next=/planta/orden/{ebr_id}"</script>',
                        mimetype="text/html")
    try:
        _f = get_db().execute(
            "SELECT COALESCE(fase,'fabricacion') FROM ebr_ejecuciones WHERE id=?",
            (ebr_id,)).fetchone()
        if _f and (_f[0] or '') == 'envasado':
            return Response(
                f'<script>location.href="/planta/legajo-envasado/{ebr_id}"</script>',
                mimetype="text/html")
        if _f and (_f[0] or '') == 'acondicionamiento':
            return Response(
                f'<script>location.href="/planta/legajo-acondicionamiento/{ebr_id}"</script>',
                mimetype="text/html")
    except Exception:
        pass
    return Response(_ORDEN_DETALLE_HTML
                    .replace("/*__TOOLTIP_CSS__*/", TOOLTIP_CSS)
                    .replace("__EBR_ID__", str(ebr_id)),
                    mimetype="text/html")


_ENVASADO_LEGAJO_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Orden de Envasado · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
/* 96vw = la regla de EOS para los modulos. Estaban clavadas en 1100-1200px: en un monitor de 1990 dejaban el 40% en blanco y la tabla de materiales -7 columnas- se desbordaba cortando 'Diferencia'. La orden madre ya usaba 96vw; se alinean las de DATOS. Los dos INSTRUCTIVOS quedan angostos a proposito: son formatos que se leen y se imprimen. */.wrap{max-width:96vw;margin:0 auto}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:28px 32px;box-shadow:0 1px 3px rgba(24,24,27,.04),0 8px 24px -14px rgba(24,24,27,.10);margin-bottom:18px}
a.back{color:var(--cx-primary-text,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
.ortit{font-size:26px;font-weight:800;color:var(--cx-text,#18181b);margin:6px 0 6px;letter-spacing:-.4px}
.prod{color:var(--cx-text-mute,#71717a);font-size:17px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:24px 22px}
.lbl{font-size:12.5px;font-weight:700;color:var(--cx-text-soft,#3f3f46);margin-bottom:5px}
.val{font-size:14px;color:var(--cx-text-mute,#71717a);line-height:1.45}
.mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.btnrow{display:flex;gap:12px;justify-content:flex-start;flex-wrap:wrap;margin-top:24px}
.bt{padding:11px 20px;border-radius:10px;font-size:13px;font-weight:600;border:1px solid transparent;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:7px;transition:all .15s ease}
.bt-add{background:var(--cx-primary,#6d28d9);color:#fff}.bt-add:hover{background:var(--cx-primary-dark,#4c1d95)}
.bt-pdf{background:var(--cx-bg-alt,#fbfbfd);color:var(--cx-text-soft,#3f3f46);border-color:var(--cx-border,#e6e6ea)}.bt-pdf:hover{border-color:var(--cx-primary,#6d28d9);color:var(--cx-primary-text,#6d28d9)}
.bt-back{background:transparent;color:var(--cx-text-mute,#71717a);border-color:var(--cx-border,#e6e6ea)}.bt-back:hover{background:var(--cx-bg-alt,#fbfbfd)}
.sectit{font-size:18px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.2px;margin:0 0 16px}
.tw{overflow-x:auto}
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th,table.t td{padding:13px 12px;text-align:left;vertical-align:middle;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
table.t thead th{color:var(--cx-text-mute,#71717a);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;border-bottom:1px solid var(--cx-border,#e6e6ea)}
table.t thead th .ar{color:var(--cx-text-faint,#a1a1aa);font-size:10px;margin-left:3px}
table.t tbody td{color:var(--cx-text-soft,#3f3f46)}
table.t tbody tr:hover td{background:var(--cx-primary-pale,#f5f3ff)}
table.t tfoot td{font-weight:800;color:var(--cx-text,#18181b);border-top:2px solid var(--cx-border,#e6e6ea)}
.tnum{text-align:right}
.regfoot{color:var(--cx-text-faint,#a1a1aa);font-size:12.5px;margin-top:14px}
.act{display:inline-flex;gap:6px;flex-wrap:wrap}
.ab{width:32px;height:32px;border-radius:8px;border:none;cursor:pointer;color:#fff;font-size:14px;line-height:1;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;transition:filter .15s ease}.ab:hover{filter:brightness(1.08)}
.ab-play{background:var(--cx-success,#15803d)}.ab-plus{background:var(--cx-primary,#6d28d9)}.ab-x{background:var(--cx-danger,#dc2626)}.ab-ed{background:var(--cx-warn,#f59e0b)}.ab-ed2{background:var(--cx-success,#15803d)}.ab-i{background:var(--cx-info,#2563eb)}
@media(max-width:760px){.grid{grid-template-columns:repeat(2,1fr)}}

/* ── Instrucciones de Envasado EMBEBIDAS · CSS encapsulado bajo .ie-emb para que
   no pise al legajo: las dos pantallas comparten 18 clases y 6 estan definidas
   distinto (.grid 4 vs 5 columnas, .bt otro padding). ── */
.ie-emb{margin-top:4px}
.ie-emb{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.ie-emb /* 96vw = la regla de EOS para los modulos. Estaban clavadas en 1100-1200px: en un monitor de 1990 dejaban el 40% en blanco y la tabla de materiales -7 columnas- se desbordaba cortando 'Diferencia'. La orden madre ya usaba 96vw; se alinean las de DATOS. Los dos INSTRUCTIVOS quedan angostos a proposito: son formatos que se leen y se imprimen. */.wrap{max-width:96vw;margin:0 auto}
.ie-emb .card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:28px 32px;box-shadow:0 1px 3px rgba(24,24,27,.04),0 8px 24px -14px rgba(24,24,27,.10);margin-bottom:18px}
.ie-emb a.back{color:var(--cx-primary-text,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
.ie-emb .htop{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.ie-emb .htit{font-size:25px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.4px}
.ie-emb .btns{display:flex;gap:10px;flex-wrap:wrap}
.ie-emb .bt{padding:10px 16px;border-radius:10px;font-size:12px;font-weight:600;border:1px solid var(--cx-border,#e6e6ea);cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;background:var(--cx-bg-alt,#fbfbfd);color:var(--cx-text-soft,#3f3f46);transition:all .15s ease}
.ie-emb .bt:hover{border-color:var(--cx-primary,#6d28d9);color:var(--cx-primary-text,#6d28d9)}
.ie-emb .bt-up{background:var(--cx-primary,#6d28d9);color:#fff;border-color:transparent}
.ie-emb .bt-up:hover{background:var(--cx-primary-dark,#4c1d95);color:#fff}
.ie-emb .subl{font-size:16px;color:var(--cx-text-soft,#3f3f46);font-weight:600;margin:2px 0 4px}
.ie-emb .prod{font-size:17px;color:var(--cx-text,#18181b);font-weight:700;margin-bottom:22px}
.ie-emb .grid{display:grid;grid-template-columns:repeat(5,1fr);gap:20px}
.ie-emb .lbl{font-size:12.5px;font-weight:700;color:var(--cx-text-soft,#3f3f46);margin-bottom:5px}
.ie-emb .val{font-size:13.5px;color:var(--cx-text-mute,#71717a);line-height:1.45}
.ie-emb .sectit{font-size:18px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.2px;margin:0 0 12px}
.ie-emb .muted{color:var(--cx-text-faint,#a1a1aa)}
.ie-emb .npaso{display:inline-block;min-width:20px;font-weight:800;font-variant-numeric:tabular-nums;color:var(--cx-text-mute,#6b6b74)}
.ie-emb .hist{font-size:11px;font-weight:700;color:var(--cx-warn-text,#b45309);background:var(--cx-warn-pale,#fffbeb);padding:2px 7px;border-radius:999px;white-space:nowrap}
.ie-emb .fila-hist td{opacity:.72}
.ie-emb .mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.ie-emb .sechead{display:flex;align-items:center;gap:12px;justify-content:space-between;flex-wrap:wrap;margin-bottom:6px}
.ie-emb .sechead .sectit{margin:0}
.ie-emb .sechint{font-size:13.5px;color:var(--cx-text-mute,#71717a);margin:6px 0 14px;line-height:1.5}
.ie-emb .btreg{padding:9px 15px;border-radius:9px;font-size:12px;font-weight:600;border:none;cursor:pointer;background:var(--cx-primary,#6d28d9);color:#fff;display:inline-flex;align-items:center;gap:6px;text-decoration:none;white-space:nowrap}
.ie-emb .btreg:hover{background:var(--cx-primary-dark,#4c1d95)}
.ie-emb .tw{overflow-x:auto}
.ie-emb table.t{width:100%;border-collapse:collapse;font-size:13.5px}
.ie-emb table.t th, .ie-emb table.t td{padding:12px;text-align:left;vertical-align:middle;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
.ie-emb table.t thead th{color:var(--cx-text-mute,#71717a);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;border-bottom:1px solid var(--cx-border,#e6e6ea)}
.ie-emb table.t tbody td{color:var(--cx-text-soft,#3f3f46)}
.ie-emb table.t tbody tr:hover td{background:var(--cx-primary-pale,#f5f3ff)}
.ie-emb .regfoot{color:var(--cx-text-faint,#a1a1aa);font-size:12.5px;margin-top:14px}
.ie-emb .ok{color:var(--cx-success-text,#15803d);font-weight:700}
.ie-emb .no{color:var(--cx-danger-text,#dc2626);font-weight:700}
.ie-emb .pend{color:var(--cx-text-faint,#a1a1aa)}
.ie-emb .bdg{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.3px}
.ie-emb .bdg-ok{background:var(--cx-success-pale,#f0fdf4);color:var(--cx-success-text,#15803d)}
.ie-emb .bdg-no{background:var(--cx-danger-pale,#fef2f2);color:var(--cx-danger-text,#dc2626)}
.ie-emb .pasonum{font-weight:700;color:var(--cx-primary-text,#6d28d9);margin-right:5px}
.ie-emb .act{display:inline-flex;gap:6px}
.ie-emb .ab{width:30px;height:30px;border-radius:7px;border:none;cursor:pointer;color:#fff;font-size:13px;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;transition:filter .15s ease}
.ie-emb .ab:hover{filter:brightness(1.08)}
.ie-emb .ab-i{background:var(--cx-info,#2563eb)}
.ie-emb .ab-ed{background:var(--cx-warn,#f59e0b)}
.ie-emb .ab-pdf{background:var(--cx-danger,#dc2626)}
.ie-emb .grid{grid-template-columns:repeat(2,1fr)}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/inventarios#envasado">&larr; Envasado</a>
  <div class="card" id="cab"><div class="muted">Cargando…</div></div>
  <div id="cuerpo"></div>
<div id="seccion-instrucciones" class="ie-emb">
<div class="wrap">
  <a class="back" href="/planta/legajo-envasado/__EBR_ID__">&larr; Orden de Envasado</a>
  <div class="card" id="ie_cab"><div class="muted">Cargando…</div></div>
  <div id="ie_cuerpo"></div>
</div>
</div>
</div>
<script>
var EBR_ID=__EBR_ID__;
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function gfmt(n){return n==null?'·':Number(n).toLocaleString('es-CO',{maximumFractionDigits:1})+' g';}
function mlf(n){return n==null?'·':Number(n).toLocaleString('es-CO',{maximumFractionDigits:2})+' mL';}
function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
function estCol(e){e=(e||'').toLowerCase();if(e.indexOf('aprob')>=0||e.indexOf('liber')>=0)return '#166534';if(e.indexOf('proceso')>=0)return '#b45309';if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)return '#b91c1c';return '#475569';}
async function load(){
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){document.getElementById('cab').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error: '+esc(d.error||r.status)+'</span>';return;}
    var h=d.header||{};
    var estado=h.estado||'·';
    var densi=h.densidad_g_ml?Number(h.densidad_g_ml):null;
    var gB=(Number(h.lote_size_g||0)>0)?Number(h.lote_size_g):(h.cantidad_objetivo_g!=null?Number(h.cantidad_objetivo_g):null);
    var mlB=(gB!=null&&densi)?(gB/densi):null;
    var tamBulk=(gB!=null?gfmt(gB):'·')+(mlB!=null?(' - '+mlf(mlB)):'');
    document.getElementById('cab').innerHTML=
      '<div class="ortit">ORDEN DE ENVASADO N°: '+esc(h.numero_op||('OF-'+EBR_ID))+'</div>'+
      '<div class="prod">'+esc(h.producto||h.titulo||'·')+'</div>'+
      '<div style="margin:-10px 0 18px"><span style="display:inline-flex;align-items:center;gap:5px;background:var(--cx-primary-pale,#f5f3ff);color:var(--cx-primary-text,#6d28d9);font-size:12px;font-weight:700;padding:5px 12px;border-radius:20px;border:1px solid var(--cx-primary-light,#a78bfa)">&#128100; '+esc((d.mi_rol&&d.mi_rol.rol)||'Usuario')+'</span></div>'+
      bandaAprobacion(h,d.mi_rol)+
      '<div class="grid">'+
        fld('N° Lote Bulk','<span class="mono">'+esc(h.lote_codigo||'·')+'</span>')+
        fld('Tamaño Bulk',esc(tamBulk))+
        fld('Estado Actual','<b style="color:'+estCol(estado)+'">'+esc(estado)+'</b>')+
        fld('Elaborado por',esc(h.operario||'·'))+
        fld('Observaciones',esc(h.observaciones||'Ninguna'))+
        // "Cantidad por Envasar" repetía los mismos mililitros que ya dice "Tamaño Bulk"
        // (Sebastián 16-ago, mirando la pantalla: *"deja uno"*). El tamaño se queda, porque
        // trae las dos unidades -- los gramos que entraron y los mL que se envasan.
        fld('Densidad Bulk',densi?(densi.toLocaleString('es-CO',{maximumFractionDigits:3})+' g/mL'):'·')+
        fld('Supervisado por',esc(h.supervisado_por||'·'))+
      '</div>'+
      '<div class="btnrow">'+
        '<a class="bt bt-add" href="#seccion-instrucciones">&#9654; Ir a las Instrucciones</a>'+
        ((d.mi_rol&&d.mi_rol.puede_ejecutar&&(estado==='iniciado'||estado==='en_proceso'))?'<button class="bt bt-pdf" onclick="terminarLote()" title="Operario: termina el lote (cantidad real · todos los pasos completos)">&#10003; Terminar lote</button>':'')+
        ((d.mi_rol&&d.mi_rol.puede_liberar&&(estado==='completado'||estado==='en_revision_qc'))?'<button class="bt bt-add" onclick="liberarLote()" style="background:var(--cx-success,#15803d)" title="Calidad/Aseguramiento: libera el lote con e-firma (cierra el batch record)">&#128275; Liberar lote</button>':'')+
        '<button class="bt bt-pdf" onclick="adicionarLote()">+ Adicionar Lote</button>'+
        '<a class="bt bt-pdf" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">&#128196; Descargar</a>'+
        ((d.mi_rol&&d.mi_rol.puede_aprobar)?'<button class="bt bt-pdf" onclick="regenerarMBR()" title="Crea una nueva versión del MBR con los pasos de envasado actualizados (GMP · obsoleta el anterior · solo Calidad/Dirección Técnica)">&#8635; Regenerar MBR</button>':'')+
        '<a class="bt bt-back" href="/inventarios#envasado">&#9198; Atrás</a>'+
      '</div>';
    window._prod=h.producto||h.titulo||''; window._lote=h.lote_codigo||'';
    // Paso 2 · Lotes de Producto por Presentación + Materiales de Envase (tal cual MyBatch).
    function ar(){return '<span class="ar">&#8645;</span>';}
    var pres=d.envasado_presentaciones||[];
    window._pres=pres;
    var puedeEdPres=(estado!=='liberado'&&estado!=='rechazado');
    var totUds=pres.reduce(function(a,p){return a+(Number(p.unidades)||0);},0);
    var totCant=pres.reduce(function(a,p){return a+(Number(p.cantidad_ml)||0);},0);
    var presRows=pres.length
      ? pres.map(function(p,i){
          var acc='<a class="ab ab-play" href="/planta/instrucciones-envasado/'+EBR_ID+'" title="Ejecutar / Instrucciones de Envasado">&#9654;</a>';
          if(puedeEdPres){
            acc+='<button class="ab ab-ed" onclick="presModal('+i+')" title="Editar">&#9998;</button>';
            if(p.id){acc='<button class="ab ab-x" onclick="borrarPres('+p.id+')" title="Eliminar">&#215;</button>'+acc;}
          }
          return '<tr>'+
            '<td>'+esc(p.presentacion||'·')+(p.cliente?' <span style="color:var(--cx-text-faint, #94a3b8);font-size:11px">· '+esc(p.cliente)+'</span>':'')+(p.fuente==='manual'?' <span style="color:var(--cx-primary-text, #7c3aed);font-size:10px;font-weight:700">·manual</span>':'')+'</td>'+
            '<td class="mono">'+esc(p.lote||'·')+'</td>'+
            '<td>'+(p.unidades!=null?Number(p.unidades).toLocaleString('es-CO'):'')+'</td>'+
            '<td>'+esc(p.area||'·')+'</td>'+
            '<td>'+(p.cantidad_ml!=null?mlf(p.cantidad_ml):'')+'</td>'+
            '<td>'+(p.unidades_final!=null?Number(p.unidades_final).toLocaleString('es-CO'):'')+'</td>'+
            '<td>'+(p.rend_pct!=null?(Number(p.rend_pct).toLocaleString('es-CO',{maximumFractionDigits:2})+'%'):'')+'</td>'+
            '<td>'+esc(p.estado||'·')+'</td>'+
            '<td><div class="act">'+acc+'</div></td>'+
          '</tr>';
        }).join('')
      : '<tr><td colspan="9" class="muted" style="text-align:center;background:var(--cx-card, #fff)">Sin presentaciones registradas aún.</td></tr>';
    var presCard='<div class="card"><div class="sechead" style="display:flex;justify-content:space-between;align-items:center;gap:8px"><div class="sectit">Lotes de Producto por Presentación</div>'+
      (puedeEdPres?'<button class="bt bt-pdf" onclick="presModal(-1)" title="Agregar una presentación a mano (por si no cargó del plan)">+ Presentación</button>':'')+'</div>'+
      '<div class="tw"><table class="t"><thead><tr>'+
        '<th>Presentación'+ar()+'</th><th>N° de lote'+ar()+'</th><th>Unid.'+ar()+'</th><th>Área/Línea'+ar()+'</th><th>Cantidad'+ar()+'</th><th>Te&oacute;ricas'+ar()+'</th><th>%Rend.'+ar()+'</th><th>Estado'+ar()+'</th><th>Acciones</th>'+
      '</tr></thead><tbody>'+presRows+'</tbody>'+
      (pres.length?('<tfoot><tr><td><b>Total</b></td><td></td><td>'+totUds.toLocaleString('es-CO')+'</td><td></td><td>'+(totCant>0?mlf(totCant):'')+'</td><td></td><td></td><td></td><td></td></tr></tfoot>'):'')+
      '</table></div>'+
      '<div class="regfoot">Mostrando '+pres.length+' de '+pres.length+' registro'+(pres.length===1?'':'s')+'</div></div>';
    var mats=d.envasado_materiales||[];
    window._mats=mats;
    var puedeEditarMat=(estado!=='liberado'&&estado!=='rechazado');
    // Quién puede poner la 2ª firma y quién soy. El backend YA bloquea con 403/409: esto
    // sólo evita ofrecer un botón que va a fallar (el control real nunca vive en la vista).
    var PUEDE_VERIF=!!(d.mi_rol&&d.mi_rol.verifica);
    var YO=(d.mi_rol&&d.mi_rol.usuario)||'';
    function mc(v){return v!=null?Number(v).toLocaleString('es-CO'):'';}
    var matRows=mats.length
      ? mats.map(function(m,i){
          var acc='<button class="ab ab-i" onclick="prox()" title="Detalle">i</button>';
          if(puedeEditarMat){
            acc='<button class="ab ab-ed" onclick="matModal('+i+')" title="Editar / registrar cantidades">&#9998;</button>'+acc;
            if(m.id){acc='<button class="ab ab-x" onclick="borrarMat('+m.id+')" title="Eliminar">&#215;</button>'+acc;}
          }
          // Recepción y su 2ª firma. Lo que NO se recibió todavía no se puede verificar, y
          // quien recibió no puede verificarse a sí mismo (el backend lo bloquea · acá sólo
          // se evita ofrecer un botón que va a dar 409).
          var recTxt = (m.recibida!=null)
            ? (mc(m.recibida)+(m.faltante_entrega ? ' <span style="color:var(--cx-danger-text,#b91c1c);font-size:11px;font-weight:700" title="No entregaron esta cantidad">(-'+mc(m.faltante_entrega)+')</span>' : ''))
            : '<span class="muted">pendiente</span>';
          var verTxt;
          if(m.verificado_por){
            verTxt='<span style="color:var(--cx-success-text,#166534);font-weight:700" title="'+esc(String(m.verificado_at_utc||'').substring(0,16).replace("T"," "))+'">&#10003; '+esc(m.verificado_por)+'</span>';
          } else if(m.recibida==null){
            verTxt='<span class="muted">·</span>';
          } else if(puedeEditarMat && m.id && PUEDE_VERIF && m.recibido_por!==YO){
            verTxt='<button class="ab ab-ed" onclick="verificarMat('+m.id+')" title="2ª firma: certificás que lo recibido está conforme (no podés verificar tu propia recepción)">&#10003; Verificar</button>';
          } else {
            verTxt='<span style="color:var(--cx-warn-text,#b45309);font-weight:700">pendiente</span>';
          }
          return '<tr>'+
            '<td class="mono">'+esc(m.lote_envasado||'·')+'</td>'+
            '<td>'+esc(m.material||'·')+(m.fuente==='manual'?' <span style="color:var(--cx-primary-text, #7c3aed);font-size:10px;font-weight:700">·manual</span>':'')+'</td>'+
            '<td class="mono">'+esc(m.lote_material||'·')+'</td>'+
            '<td>'+mc(m.requerida)+'</td>'+
            '<td>'+recTxt+'</td>'+
            '<td>'+esc(m.recibido_por||'·')+'</td>'+
            '<td>'+verTxt+'</td>'+
            '<td>'+mc(m.devuelta)+'</td>'+
            '<td>'+mc(m.utilizada)+'</td>'+
            '<td>'+mc(m.averiada)+'</td>'+
            '<td>'+mc(m.diferencia)+'</td>'+
            '<td><div class="act">'+acc+'</div></td>'+
          '</tr>';
        }).join('')
      : '<tr><td colspan="12" class="muted" style="text-align:center;background:var(--cx-card, #fff)">Sin materiales de envase registrados aún.</td></tr>';
    var matCard='<div class="card"><div class="sechead" style="display:flex;justify-content:space-between;align-items:center;gap:8px"><div class="sectit">Materiales de Envase</div>'+
      (puedeEditarMat?'<button class="bt bt-pdf" onclick="matModal(-1)" title="Elegir un material de envase del catálogo completo">+ Material de envase</button>':'')+'</div>'+
      '<div class="tw"><table class="t"><thead><tr>'+
        '<th>N° lote envasado'+ar()+'</th><th>Material de envase'+ar()+'</th><th>N° de lote material'+ar()+'</th><th>Cant. requerida'+ar()+'</th><th>Cant. recibida'+ar()+'</th><th>Recibido por'+ar()+'</th><th>Verificado por'+ar()+'</th><th>Cant. devuelta'+ar()+'</th><th>Cant. utilizada'+ar()+'</th><th>Cant. averiada'+ar()+'</th><th>Diferencia'+ar()+'</th><th>Acciones</th>'+
      '</tr></thead><tbody>'+matRows+'</tbody></table></div>'+
      '<div class="regfoot">Mostrando '+mats.length+' de '+mats.length+' registro'+(mats.length===1?'':'s')+'</div></div>';
    // ── Conciliación del granel · ¿en qué terminó el bulk que entró? ────────────
    // entró = envasado (Σ uds × mL) + remanente + diferencia sin explicar.
    // Todo derivado salvo el remanente, que es lo único que se va a pesar.
    var cg=d.conciliacion_granel; window._cg=cg;
    var concCard='';
    if(cg&&cg.aplica){
      var puedeConc=(estado!=='liberado'&&estado!=='rechazado')&&!!(d.mi_rol&&d.mi_rol.puede_ejecutar);
      var okCol='var(--cx-success-text,#166534)', maCol='var(--cx-danger-text,#b91c1c)', avCol='var(--cx-warn-text,#b45309)';
      var difCol=cg.cuadra?okCol:(cg.completa?maCol:avCol);
      var chip, chipBg, chipTx;
      if(cg.cuadra){chip='&#10003; Conciliado';chipBg='var(--cx-success-pale,#f0fdf4)';chipTx=okCol;}
      else if(cg.falta_remanente){chip='&#9888; Falta declarar el remanente';chipBg='var(--cx-warn-pale,#fffbeb)';chipTx=avCol;}
      else if(cg.falta_densidad){chip='&#9888; Falta la densidad del granel';chipBg='var(--cx-warn-pale,#fffbeb)';chipTx=avCol;}
      else if(cg.presentaciones_sin_volumen){chip='&#9888; Hay presentaciones sin volumen';chipBg='var(--cx-warn-pale,#fffbeb)';chipTx=avCol;}
      else {chip='&#9888; Granel sin explicar';chipBg='var(--cx-danger-pale,#fef2f2)';chipTx=maCol;}
      function lin(et,val,col,sub,neg){
        return '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:14px;padding:11px 0;border-bottom:1px solid var(--cx-border-soft,#f1f5f9)">'+
          '<div><div style="font-size:13px;font-weight:600;color:var(--cx-text,#0f172a)">'+(neg?'&#8722; ':'')+et+'</div>'+
          (sub?('<div style="font-size:11px;color:var(--cx-text-faint,#94a3b8);margin-top:2px">'+sub+'</div>'):'')+'</div>'+
          '<div style="font-size:16px;font-weight:800;white-space:nowrap;color:'+(col||'var(--cx-text,#0f172a)')+'">'+val+'</div></div>';
      }
      var detPres=cg.presentaciones.map(function(p){
        return esc(p.codigo)+' &#183; '+Number(p.unidades).toLocaleString('es-CO')+' &#215; '+mlf(p.volumen_ml);}).join(' &#183; ');
      var remSub=(cg.remanente_g!=null)
        ? (Number(cg.remanente_g).toLocaleString('es-CO',{maximumFractionDigits:1})+' g pesados'+
           (cg.densidad_g_ml?(' &#247; '+Number(cg.densidad_g_ml).toLocaleString('es-CO',{maximumFractionDigits:3})+' g/mL'):'')+
           (cg.remanente_destino?(' &#183; '+esc((window._DEST_REM||{})[cg.remanente_destino]||cg.remanente_destino)):''))
        : 'Sin declarar &#183; hay que pesar lo que sobró';
      concCard='<div class="card"><div class="sechead" style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">'+
          '<div class="sectit">Conciliación del Granel</div>'+
          '<div style="display:flex;gap:8px;align-items:center">'+
            '<span style="background:'+chipBg+';color:'+chipTx+';font-size:12px;font-weight:800;padding:5px 13px;border-radius:20px;white-space:nowrap">'+chip+'</span>'+
            (puedeConc?'<button class="bt bt-pdf" onclick="concModal()" title="Registrá cuánto granel sobró y en qué terminó (queda firmado y auditado)">'+(cg.falta_remanente?'+ Declarar remanente':'&#9998; Corregir remanente')+'</button>':'')+
          '</div></div>'+
        '<div style="padding:4px 18px 16px">'+
          '<div style="font-size:12.5px;color:var(--cx-text-soft,#475569);margin:2px 0 10px">El granel que entró a la orden tiene que terminar explicado: lo que se envasó, lo que sobró, y lo que no cuadra.</div>'+
          lin('Granel disponible',mlf(cg.disponible_ml),null,'Bulk de la orden',false)+
          lin('Envasado',mlf(cg.envasado_ml),null,(detPres||'Sin unidades registradas todavía'),true)+
          lin('Remanente',(cg.remanente_ml!=null?mlf(cg.remanente_ml):'&#183;'),null,remSub,true)+
          '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:14px;padding:13px 0 2px">'+
            '<div><div style="font-size:13.5px;font-weight:800;color:'+difCol+'">Diferencia sin explicar</div>'+
            '<div style="font-size:11px;color:var(--cx-text-faint,#94a3b8);margin-top:2px">Tolerancia '+Number(cg.tolerancia_pct).toLocaleString('es-CO',{maximumFractionDigits:2})+'%</div></div>'+
            '<div style="text-align:right"><div style="font-size:20px;font-weight:800;color:'+difCol+';white-space:nowrap">'+(cg.diferencia_ml!=null?mlf(cg.diferencia_ml):'&#183;')+'</div>'+
            (cg.diferencia_pct!=null?('<div style="font-size:12px;font-weight:700;color:'+difCol+'">'+Number(cg.diferencia_pct).toLocaleString('es-CO',{maximumFractionDigits:2})+'%</div>'):'')+'</div></div>'+
          (cg.remanente_observaciones?('<div style="margin-top:12px;background:var(--cx-bg-alt,#f8fafc);border-radius:10px;padding:10px 13px;font-size:12.5px;color:var(--cx-text-soft,#475569)"><b>Observaciones:</b> '+esc(cg.remanente_observaciones)+'</div>'):'')+
          (cg.remanente_por?('<div style="margin-top:10px;font-size:11.5px;color:var(--cx-text-faint,#94a3b8)">Declarado por <b>'+esc(cg.remanente_por)+'</b>'+(cg.remanente_at_utc?(' &#183; '+esc(String(cg.remanente_at_utc).substring(0,16).replace("T"," "))):'')+'</div>'):'')+
        '</div></div>';
    }
    document.getElementById('cuerpo').innerHTML = presCard + concCard + matCard;
  }catch(e){document.getElementById('cab').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error de red: '+esc(e.message)+'</span>';}
}
window._DEST_REM={otra_orden:'Queda en bodega para otra orden',devuelto_granel:'Devuelto al granel del lote',muestra_retenida:'Muestra de retención / contramuestra',descartado:'Descartado (merma)',sin_remanente:'No quedó remanente'};
function concModal(){
  var cg=window._cg||{};
  var ov=document.getElementById('concov');
  if(!ov){ov=document.createElement('div');ov.id='concov';ov.style.cssText='position:fixed;inset:0;background:rgba(15,23,42,.55);display:flex;align-items:center;justify-content:center;z-index:9999';document.body.appendChild(ov);}
  var opts='';
  for(var k in window._DEST_REM){
    opts+='<option value="'+k+'"'+((cg.remanente_destino===k)?' selected':'')+'>'+esc(window._DEST_REM[k])+'</option>';}
  var falta=(cg.disponible_ml!=null)?(Number(cg.disponible_ml)-Number(cg.envasado_ml||0)):null;
  var sug=(falta!=null&&cg.densidad_g_ml)?(falta*Number(cg.densidad_g_ml)):null;
  ov.innerHTML='<div style="background:var(--cx-card, #fff);border-radius:14px;padding:24px;max-width:560px;width:92%;box-shadow:0 10px 40px rgba(0,0,0,.3)">'+
    '<div style="font-weight:800;font-size:18px;margin-bottom:4px">Remanente de granel</div>'+
    '<div style="font-size:12.5px;color:var(--cx-text-soft,#475569);margin-bottom:16px">Pesá lo que quedó sin envasar y decí en qué terminó. Los mL se calculan solos con la densidad del lote.</div>'+
    (sug!=null?('<div style="background:var(--cx-info-pale,#eff6ff);border-radius:10px;padding:10px 13px;font-size:12.5px;color:var(--cx-info-text,#1e40af);margin-bottom:14px">Sin explicar hoy: <b>'+mlf(falta)+'</b>. Si todo eso quedó como remanente, serían <b>'+Number(sug).toLocaleString('es-CO',{maximumFractionDigits:1})+' g</b> en balanza.</div>'):'')+
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Remanente pesado (g) *</label><input id="cg_g" type="number" step="0.1" value="'+(cg.remanente_g!=null?cg.remanente_g:'')+'" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">¿En qué terminó? *</label><select id="cg_dest" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px">'+opts+'</select></div>'+
      '<div style="grid-column:1/-1"><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Observaciones</label><input id="cg_obs" value="'+esc(cg.remanente_observaciones||'')+'" placeholder="ej. queda en bodega para la siguiente orden del mismo lote" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
    '</div>'+
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:20px">'+
      '<button onclick="cerrarConc()" style="padding:9px 16px;border:1px solid var(--cx-border, #cbd5e1);background:var(--cx-border-soft, #f1f5f9);border-radius:8px;cursor:pointer">Cancelar</button>'+
      '<button id="cg_ok" onclick="guardarConc()" style="padding:9px 16px;border:0;background:var(--cx-primary, #7c3aed);color:#fff;border-radius:8px;cursor:pointer;font-weight:700">Guardar</button>'+
    '</div></div>';
  ov.style.display='flex';
}
function cerrarConc(){var ov=document.getElementById('concov');if(ov)ov.style.display='none';}
async function verificarMat(id){
  if(window._vmBusy)return; window._vmBusy=true;                 /* doble-click = doble firma */
  try{
    if(!confirm('2a firma: certificás que el material recibido está conforme. Queda con tu nombre y auditado (GMP · regla de las 2 personas). ¿Confirmás?'))return;
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/material-envase/'+id+'/verificar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin'});
    var dd=await r.json();
    if(!r.ok||!dd.ok){alert('No se pudo verificar: '+((dd&&dd.error)||r.status));return;}
    load();
  }catch(e){alert('Error: '+(e.message||e));}
  finally{window._vmBusy=false;}
}
async function guardarConc(){
  if(window._cgBusy)return; window._cgBusy=true;                 // doble-click crea/mueve datos (M63)
  var b=document.getElementById('cg_ok'); if(b){b.disabled=true;}
  try{
    var g=document.getElementById('cg_g').value;
    var body={remanente_g:(g===''?0:parseFloat(g)),destino:document.getElementById('cg_dest').value,
              observaciones:document.getElementById('cg_obs').value};
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/remanente-granel',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
    var dd=await r.json();
    if(!r.ok||!dd.ok){alert('No se pudo guardar: '+((dd&&dd.error)||r.status));return;}
    cerrarConc();load();
  }catch(e){alert('Error: '+(e.message||e));}
  finally{window._cgBusy=false; if(b){b.disabled=false;}}
}
function adicionarLote(){alert('“Adicionar Lote” lo construimos en el siguiente paso.');}
async function regenerarMBR(){
  var prod=(window._prod||'');
  if(!prod){alert('No identifiqué el producto.');return;}
  if(!confirm('¿Regenerar el MBR de "'+prod+'" con los pasos de envasado actualizados (los 5 reales) y abrir un legajo NUEVO para verlos?\\n\\nObsoleta el MBR anterior (forma GMP correcta · queda auditado).'))return;
  try{
    var r=await fetch('/api/brd/mbr/preparar-aprobado',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto_nombre:prod,regenerar:true})});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo regenerar: '+((d&&d.error)||r.status));return;}
    // Crea un legajo nuevo (lote + sufijo) que clona la versión nueva del MBR → 5 pasos.
    var base=(window._lote||prod).replace(/-R\\d+$/,'');
    var nuevoLote=base+'-R'+(Math.floor(Date.now()/1000)%100000);
    var rl=await fetch('/api/brd/legajo-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto:prod,lote:nuevoLote,fase:'envasado'})});
    var dl=await rl.json();
    if(rl.ok&&dl.ok&&dl.id){location.href='/planta/legajo-envasado/'+dl.id;return;}
    alert('✅ MBR regenerado (v'+(d.version||'?')+'). No pude abrir el legajo nuevo automáticamente; créalo desde Envasado.');
  }catch(e){alert('Error: '+(e.message||e));}
}
async function terminarLote(){
  // Operario · termina el lote (cantidad real · requiere todos los pasos completos).
  var cant=prompt('Terminar el lote · cantidad real producida (g):');
  if(cant===null)return; cant=parseFloat(cant);
  if(!cant||cant<=0){alert('Cantidad inválida');return;}
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({cantidad_real_g:cant})});
    var d=await r.json();
    if(!r.ok){alert('No se pudo terminar: '+(d.error||r.status));return;}
    alert('✅ Lote terminado. Ahora Calidad/Aseguramiento puede liberarlo.'); location.reload();
  }catch(e){alert('Error: '+(e.message||e));}
}
async function liberarLote(){ _libAbrir(); }

// Modal de liberacion · propio de EOS, no el cuadro gris del navegador.
// Trae el motivo del rechazo y el campo para resolverlo SIN salir: el control sigue siendo
// obligatorio, pero ahora se puede cumplir donde aparece (Sebastian 16-ago-2026).
function _libAbrir(motivo, yieldPct){
  var ov=document.getElementById('libov');
  if(!ov){
    ov=document.createElement('div'); ov.id='libov';
    ov.style.cssText='position:fixed;inset:0;background:rgba(15,12,35,.55);display:flex;'+
      'align-items:center;justify-content:center;z-index:9999;padding:20px';
    ov.innerHTML='<div style="background:var(--cx-card,#fff);color:var(--cx-text,#0f172a);'+
      'border-radius:16px;max-width:640px;width:100%;box-shadow:0 24px 60px rgba(15,12,35,.35);'+
      'overflow:hidden">'+
      '<div style="padding:24px 26px 6px"><div style="font-size:20px;font-weight:800;'+
      'letter-spacing:-.01em">Liberar el lote</div>'+
      '<div id="libsub" style="margin-top:6px;font-size:14px;line-height:1.55;'+
      'color:var(--cx-text-soft,#475569)">Cierra el batch record con tu firma electr&oacute;nica. '+
      'Queda auditado (Calidad / Aseguramiento &middot; 21 CFR Part 11).</div>'+
      '<div id="libwarn" style="display:none;margin-top:14px;padding:14px 16px;border-radius:10px;'+
      'background:var(--cx-warn-pale,#fef3c7);border:1px solid var(--cx-warn,#f59e0b)">'+
      '<div id="libwarntxt" style="font-size:13.5px;line-height:1.55;color:var(--cx-warn-text,#92400e)"></div>'+
      '<label style="display:block;margin-top:12px;font-size:12px;font-weight:700;'+
      'text-transform:uppercase;letter-spacing:.06em;color:var(--cx-text-soft,#475569)">'+
      'Por qu&eacute; dio ese rendimiento</label>'+
      '<textarea id="libjust" rows="3" placeholder="Ej: se perdi&oacute; producto al trasvasar el '+
      'recipiente 2 · o la balanza estaba destarada" style="width:100%;margin-top:6px;'+
      'padding:10px 12px;border:1px solid var(--cx-border,#cbd5e1);border-radius:9px;'+
      'font:inherit;font-size:14px;background:var(--cx-card,#fff);color:var(--cx-text,#0f172a);'+
      'resize:vertical"></textarea>'+
      '<div style="margin-top:6px;font-size:12px;color:var(--cx-text-faint,#94a3b8)">'+
      'Queda en el legajo y en el PDF: es la explicaci&oacute;n que va a leer quien audite.</div>'+
      '</div></div>'+
      '<div style="display:flex;gap:10px;justify-content:flex-end;padding:18px 26px 22px">'+
      '<button onclick="_libCerrar()" style="padding:10px 18px;border-radius:9px;'+
      'border:1px solid var(--cx-border,#cbd5e1);background:var(--cx-card,#fff);'+
      'color:var(--cx-text,#0f172a);font:inherit;font-weight:600;cursor:pointer">Cancelar</button>'+
      '<button id="libok" onclick="_libConfirmar()" style="padding:10px 20px;border-radius:9px;'+
      'border:none;background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;font:inherit;'+
      'font-weight:700;cursor:pointer">Liberar el lote</button></div></div>';
    document.body.appendChild(ov);
  }
  ov.style.display='flex';
  var w=document.getElementById('libwarn');
  if(motivo){
    w.style.display='block';
    document.getElementById('libwarntxt').innerHTML=motivo;
    setTimeout(function(){var t=document.getElementById('libjust'); if(t)t.focus();},60);
  }else{
    w.style.display='none';
  }
}
function _libCerrar(){var o=document.getElementById('libov'); if(o)o.style.display='none';}

async function _libConfirmar(){
  var btn=document.getElementById('libok');
  var just=(document.getElementById('libjust')||{}).value||'';
  var warn=document.getElementById('libwarn');
  if(warn&&warn.style.display==='block'&&just.trim().length<10){
    document.getElementById('libwarntxt').innerHTML=
      'Escrib&iacute; por qu&eacute; dio ese rendimiento (al menos 10 caracteres): es lo que va a leer quien audite.';
    return;
  }
  if(btn){btn.disabled=true; btn.textContent='Liberando...';}
  try{
    var rf=await fetch('/api/brd/ebr/'+EBR_ID+'/firmar-rapido',{method:'POST',
      headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({meaning:'libera'})});
    var df=await rf.json();
    if(!rf.ok||!df.ok){
      document.getElementById('libsub').innerHTML='No se pudo firmar la liberaci&oacute;n: '+
        _escLib((df&&df.error)||rf.status);
      if(btn){btn.disabled=false; btn.textContent='Liberar el lote';}
      return;
    }
    var cuerpo={};
    if(just.trim()){cuerpo.yield_justificacion=just.trim();}
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/liberar',{method:'POST',
      headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify(cuerpo)});
    var d=await r.json();
    if(!r.ok){
      if(btn){btn.disabled=false; btn.textContent='Liberar el lote';}
      // El rendimiento fuera de rango no es un error del usuario: es un dato que falta.
      // Se pide en el mismo modal en vez de mandarlo a buscar donde se justifica.
      if(d&&d.codigo==='YIELD_FUERA_RANGO'){
        _libAbrir('El lote rindi&oacute; <b>'+_escLib(d.yield_pct)+'%</b> y lo normal es entre 80% '+
          'y 115%. Puede ser p&eacute;rdida de producto, un error de tara o unidades de otra orden. '+
          'GMP pide explicarlo antes de liberar.', d.yield_pct);
        return;
      }
      document.getElementById('libsub').innerHTML='No se pudo liberar: '+
        _escLib((d&&d.error)||r.status);
      return;
    }
    _libCerrar();
    location.reload();
  }catch(e){
    if(btn){btn.disabled=false; btn.textContent='Liberar el lote';}
    document.getElementById('libsub').innerHTML='Error: '+_escLib(e.message||e);
  }
}
function _escLib(s){var d=document.createElement('div');d.textContent=(s==null?'':String(s));return d.innerHTML;}

var _envOpc=null;
async function cargarEnvaseOpc(){
  if(_envOpc)return _envOpc;
  try{var r=await fetch('/api/brd/envase-opciones',{credentials:'same-origin'});var d=await r.json();_envOpc=(d&&d.opciones)||[];}catch(e){_envOpc=[];}
  return _envOpc;
}
async function matModal(i){
  var m=(i>=0&&window._mats)?window._mats[i]:null;
  var opc=await cargarEnvaseOpc();
  var ov=document.getElementById('matov');
  if(!ov){ov=document.createElement('div');ov.id='matov';ov.style.cssText='position:fixed;inset:0;background:rgba(15,23,42,.55);display:flex;align-items:center;justify-content:center;z-index:9999';document.body.appendChild(ov);}
  var selCod=(m&&m.material_codigo)||'';
  var opciones='<option value="">· elegí un material de envase ·</option>'+opc.map(function(o){return '<option value="'+esc(o.codigo)+'"'+(o.codigo===selCod?' selected':'')+'>'+esc(o.label)+'</option>';}).join('');
  function v(x){return (x==null?'':x);}
  ov.innerHTML='<div style="background:var(--cx-card, #fff);border-radius:14px;padding:22px;max-width:520px;width:92%;box-shadow:0 10px 40px rgba(0,0,0,.3)">'+
    '<div style="font-weight:800;font-size:17px;margin-bottom:14px">'+(m?'Editar material de envase':'Agregar material de envase')+'</div>'+
    '<input type="hidden" id="m_id" value="'+v(m&&m.id)+'">'+
    '<label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Material de envase (catálogo completo)</label>'+
    '<select id="m_cod" style="width:100%;padding:9px;margin:4px 0 12px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px">'+opciones+'</select>'+
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">N° lote material</label><input id="m_lote" value="'+esc(v(m&&m.lote_material))+'" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Cant. requerida</label><input id="m_req" type="number" value="'+v(m&&m.requerida)+'" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Cant. devuelta</label><input id="m_dev" type="number" value="'+v(m&&m.devuelta)+'" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Cant. utilizada</label><input id="m_uti" type="number" value="'+v(m&&m.utilizada)+'" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Cant. averiada</label><input id="m_ave" type="number" value="'+v(m&&m.averiada)+'" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
    '</div>'+
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px">'+
      '<button onclick="cerrarMat()" style="padding:9px 16px;border:1px solid var(--cx-border, #cbd5e1);background:var(--cx-border-soft, #f1f5f9);border-radius:8px;cursor:pointer">Cancelar</button>'+
      '<button onclick="guardarMat()" style="padding:9px 16px;border:0;background:var(--cx-primary, #7c3aed);color:#fff;border-radius:8px;cursor:pointer;font-weight:700">Guardar</button>'+
    '</div></div>';
  ov.style.display='flex';
}
function cerrarMat(){var ov=document.getElementById('matov');if(ov)ov.style.display='none';}
async function guardarMat(){
  var cod=document.getElementById('m_cod').value;
  if(!cod){alert('Elegí un material del desplegable.');return;}
  function n(id){var x=document.getElementById(id).value;return x===''?null:parseFloat(x);}
  var body={material_codigo:cod,lote_material:document.getElementById('m_lote').value,requerida:n('m_req'),devuelta:n('m_dev'),utilizada:n('m_uti'),averiada:n('m_ave')};
  var idv=document.getElementById('m_id').value;if(idv)body.id=parseInt(idv,10);
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/material-envase',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo guardar: '+((d&&d.error)||r.status));return;}
    cerrarMat();load();
  }catch(e){alert('Error: '+(e.message||e));}
}
async function borrarMat(id){
  if(!confirm('¿Eliminar este material de envase agregado a mano?'))return;
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/material-envase/'+id,{method:'DELETE',credentials:'same-origin'});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo eliminar: '+((d&&d.error)||r.status));return;}
    load();
  }catch(e){alert('Error: '+(e.message||e));}
}
function presModal(i){
  var p=(i>=0&&window._pres)?window._pres[i]:null;
  var ov=document.getElementById('presov');
  if(!ov){ov=document.createElement('div');ov.id='presov';ov.style.cssText='position:fixed;inset:0;background:rgba(15,23,42,.55);display:flex;align-items:center;justify-content:center;z-index:9999';document.body.appendChild(ov);}
  function v(x){return (x==null?'':x);}
  ov.innerHTML='<div style="background:var(--cx-card, #fff);border-radius:14px;padding:22px;max-width:520px;width:92%;box-shadow:0 10px 40px rgba(0,0,0,.3)">'+
    '<div style="font-weight:800;font-size:17px;margin-bottom:14px">'+(p?'Editar presentación':'Agregar presentación')+'</div>'+
    '<input type="hidden" id="p_id" value="'+v(p&&p.id)+'">'+
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Presentación *</label><input id="p_pres" value="'+esc(v(p&&p.presentacion))+'" placeholder="ej. 30 ml" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Cliente</label><input id="p_cli" value="'+esc(v((p&&p.cliente)||"Animus DTC"))+'" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Unidades</label><input id="p_uds" type="number" value="'+v(p&&p.unidades)+'" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Volumen (mL/ud)</label><input id="p_vol" type="number" value="'+v(p&&p.volumen_ml)+'" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;color:var(--cx-text-soft, #475569);font-weight:600">Área/Línea</label><input id="p_area" value="'+esc(v(p&&p.area))+'" style="width:100%;padding:9px;border:1px solid var(--cx-border, #cbd5e1);border-radius:8px"></div>'+
    '</div>'+
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px">'+
      '<button onclick="cerrarPres()" style="padding:9px 16px;border:1px solid var(--cx-border, #cbd5e1);background:var(--cx-border-soft, #f1f5f9);border-radius:8px;cursor:pointer">Cancelar</button>'+
      '<button onclick="guardarPres()" style="padding:9px 16px;border:0;background:var(--cx-primary, #7c3aed);color:#fff;border-radius:8px;cursor:pointer;font-weight:700">Guardar</button>'+
    '</div></div>';
  ov.style.display='flex';
}
function cerrarPres(){var ov=document.getElementById('presov');if(ov)ov.style.display='none';}
async function guardarPres(){
  var pres=document.getElementById('p_pres').value.trim();
  if(!pres){alert('Indicá la presentación (ej. 30 ml).');return;}
  function n(id){var x=document.getElementById(id).value;return x===''?null:parseFloat(x);}
  var body={presentacion:pres,cliente:document.getElementById('p_cli').value,unidades:n('p_uds'),volumen_ml:n('p_vol'),area:document.getElementById('p_area').value};
  var idv=document.getElementById('p_id').value;if(idv)body.id=parseInt(idv,10);
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/presentacion',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo guardar: '+((d&&d.error)||r.status));return;}
    cerrarPres();load();
  }catch(e){alert('Error: '+(e.message||e));}
}
async function borrarPres(id){
  if(!confirm('¿Eliminar esta presentación agregada a mano?'))return;
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/presentacion/'+id,{method:'DELETE',credentials:'same-origin'});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo eliminar: '+((d&&d.error)||r.status));return;}
    load();
  }catch(e){alert('Error: '+(e.message||e));}
}
function prox(){alert('Esta acción la construimos en el siguiente paso.');}
load();

/* ── Instrucciones de Envasado embebidas · sus 5 funciones que chocaban
   (esc/estCol/fld/load/prox) van con prefijo ie_ · se RENOMBRAN y no se
   borran porque no son identicas: su estCol trata completado distinto. ── */

function ie_esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function dt(s){return s?ie_esc(String(s).substring(0,16).replace('T',' ')):'·';}
function ie_estCol(e){e=(e||'').toLowerCase();if(e.indexOf('aprob')>=0||e.indexOf('liber')>=0||e.indexOf('complet')>=0)return '#166534';if(e.indexOf('proceso')>=0)return '#0d9488';if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)return '#b91c1c';return '#475569';}
function ie_fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
async function ie_load(){
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){document.getElementById('ie_cab').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error: '+ie_esc(d.error||r.status)+'</span>';return;}
    var h=d.header||{};
    var estado=h.estado||'·';
    var pres=d.envasado_presentaciones||[];
    var uds=pres.reduce(function(a,p){return a+(Number(p.unidades)||0);},0);
    document.getElementById('ie_cab').innerHTML=
      '<div class="htop">'+
        '<div><div class="htit">INSTRUCCIONES DE ENVASADO</div>'+
          '<div style="margin-top:7px"><span style="display:inline-flex;align-items:center;gap:5px;background:var(--cx-primary-pale,#f5f3ff);color:var(--cx-primary-text,#6d28d9);font-size:12px;font-weight:700;padding:5px 12px;border-radius:20px;border:1px solid var(--cx-primary-light,#a78bfa)">&#128100; '+ie_esc((d.mi_rol&&d.mi_rol.rol)||'Usuario')+'</span></div></div>'+
        '<div class="btns">'+
          '<a class="bt bt-tl" href="/brd/timeline/'+EBR_ID+'">&#9198; Timeline Batch Record</a>'+
          '<a class="bt bt-oe" href="/planta/legajo-envasado/'+EBR_ID+'">&#128196; Orden de Envase</a>'+
          '<a class="bt bt-dl" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">&#128196; Descargar</a>'+
          '<button class="bt bt-up" onclick="location.reload()">&#8635; Actualizar</button>'+
        '</div>'+
      '</div>'+
      '<div class="subl">'+ie_esc(h.numero_op||('OF-'+EBR_ID))+'. Lote N°: '+ie_esc(h.lote_codigo||'·')+'</div>'+
      '<div class="prod">'+ie_esc(h.producto||h.titulo||'·')+(pres.length&&pres[0].presentacion?(', '+ie_esc(pres[0].presentacion)):'')+'</div>'+
      '<div class="grid">'+
        ie_fld('Programado por',ie_esc(h.operario||'·'))+
        ie_fld('Unidades',uds?uds.toLocaleString('es-CO'):'·')+
        ie_fld('N° de Lote Bulk','<span style="font-family:ui-monospace,monospace">'+ie_esc(h.lote_codigo||'·')+'</span>')+
        ie_fld('Fecha Inicio',dt(h.iniciado_at_utc))+
        ie_fld('Fecha Final',dt(h.completado_at_utc))+
        ie_fld('Estado Actual','<b style="color:'+ie_estCol(estado)+'">'+ie_esc(estado)+'</b>')+
      '</div>';
    var editable=(estado==='iniciado'||estado==='en_proceso') && !!(d.mi_rol && d.mi_rol.puede_ejecutar);
    function cumpleCell(c){if(c===1)return '<span class="ok">Sí &#10003;</span>';if(c===0)return '<span class="no">No &#10007;</span>';return '<span class="pend">Pendiente</span>';}
    function regBtn(t){return editable?('<button class="btreg" onclick="ie_prox()">+ '+t+'</button>'):'';}
    function abI(){return '<button class="ab ab-i" onclick="ie_prox()" title="Detalle">i</button>';}
    function abEd(){return editable?'<button class="ab ab-ed" onclick="ie_prox()" title="Registrar">&#9998;</button>':'';}
    function bdgC(c){if(c===1)return ' <span class="bdg bdg-ok">Cumple</span>';if(c===0)return ' <span class="bdg bdg-no">No cumple</span>';return '';}
    var html='';
    // Leyenda de responsabilidades (segregación de funciones GMP · diseño por roles).
    html+='<div class="card" style="padding:15px 20px"><div style="font-size:13px;color:var(--cx-text-soft,#3f3f46);line-height:1.7">'+
      '<b>Responsabilidades:</b> &nbsp;'+
      '<span style="color:var(--cx-primary-text,#6d28d9);font-weight:800">●</span> <b>Operario</b> ejecuta y registra (precauciones, despeje, recepción, envasado). &nbsp;'+
      '<span style="color:var(--cx-success-text,#15803d);font-weight:800">●</span> <b>Calidad / Aseguramiento</b> verifica los controles, corrige resultados y <b>libera el lote</b>. &nbsp;'+
      '<span style="color:var(--cx-warn-text,#f59e0b);font-weight:800">●</span> <b>Dirección Técnica</b> aprueba el MBR.'+
      '</div></div>';
    var prec=d.precauciones||[];
    html+='<div class="card"><div class="sectit">1. Precauciones</div>'+
      '<div class="sechint">Tenga en cuenta las siguientes precauciones antes de iniciar el proceso de envasado:</div>'+
      (prec.length?('<ul style="margin:0;padding-left:18px;color:var(--cx-text-soft);font-size:13.5px;line-height:1.95">'+prec.map(function(p){return '<li><b>'+(p.tipo==='equipo'?'&#128296; Equipo':'&#9888; Precaución')+':</b> '+ie_esc(p.descripcion||'')+'</li>';}).join('')+'</ul>'):'<div class="muted">Sin precauciones registradas (se definen en el MBR).</div>')+
      '</div>';
    var dch=d.despeje_checklist||[]; window._dch=dch;
    html+='<div class="card"><div class="sectit">2. Despejes de Línea</div>'+
      '<div class="sechint">Realizar despeje en el área de acuerdo a los procedimientos internos, y realice las siguientes verificaciones:</div>'+
      (dch.length?('<div class="tw"><table class="t"><thead><tr><th>Verificación</th><th>Cumple</th><th>Acciones</th></tr></thead><tbody>'+
        dch.map(function(it,n){
          // un item RETIRADO del procedimiento (registrado antes del cambio) se sigue mostrando:
          // un registro regulado no desaparece porque el procedimiento cambie despues. Se marca y
          // no se puede registrar de nuevo.
          var marca = it.historico ? ' <span class="hist">retirado del procedimiento</span>' : '';
          var acciones = '<button class="ab ab-i" onclick="infoDespeje('+it.idx+')" title="Detalle">i</button>'
            + ((editable && !it.historico) ? '<button class="ab ab-ed" onclick="regDespeje('+it.idx+')" title="Registrar verificación">&#9998;</button>' : '');
          return '<tr'+(it.historico?' class="fila-hist"':'')+'><td><span class="npaso">'+(it.historico?'·':(n+1))+'</span> '+ie_esc(it.texto||'')+marca+'</td><td>'+cumpleCell(it.cumple)+'</td><td><div class="act">'+acciones+'</div></td></tr>';
        }).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin verificaciones de despeje (se definen en el MBR).</div>')+
      '</div>';
    var mats=d.envasado_materiales||[];
    html+='<div class="card"><div class="sectit">3. Recepción de Material de Envase</div>'+
      '<div class="sechint">Verificar contra la orden de envasado y la etiqueta o rótulo de identificación de los siguientes materiales de envase:</div>'+
      '<div class="tw"><table class="t"><thead><tr><th>Material</th><th>N° lote</th><th>Cant. requerida</th><th>Cant. recibida</th><th>Acciones</th></tr></thead><tbody>'+
      (mats.length?mats.map(function(m){return '<tr><td>'+ie_esc(m.material||'·')+'</td><td class="mono">'+ie_esc(m.lote_material||m.lote_envasado||'·')+'</td><td>'+(m.requerida!=null?Number(m.requerida).toLocaleString('es-CO'):'')+'</td><td>'+(m.recibida!=null?Number(m.recibida).toLocaleString('es-CO'):'<span class="pend">pendiente</span>')+'</td><td><div class="act">'+abI()+abEd()+'</div></td></tr>';}).join('')
        :'<tr><td colspan="5" class="muted" style="text-align:center">Sin materiales registrados.</td></tr>')+
      '</tbody></table></div>'+
      '<div class="regfoot">Mostrando '+mats.length+' de '+mats.length+' registro'+(mats.length===1?'':'s')+'</div></div>';
    var pasos=d.pasos||[]; window._pasos=pasos;
    html+='<div class="card"><div class="sechead"><div class="sectit">4. Envasado</div>'+(editable?'<button class="btreg" onclick="registrarActividades()">&#10003; Registrar Actividades</button>':'')+'</div>'+
      '<div class="sechint">Realizar las siguientes actividades de acuerdo al orden establecido:</div>'+
      (pasos.length?('<div class="tw"><table class="t"><thead><tr><th>Actividad</th><th>Realizado por</th><th>Verificado por</th><th>Acciones</th></tr></thead><tbody>'+
        pasos.map(function(p,i){var ts=p.completado?('<br><span class="muted" style="font-size:11.5px">'+dt(p.completado)+'</span>'):'';return '<tr><td><span class="pasonum">Paso '+(i+1)+'.</span>'+ie_esc(p.descripcion||'')+'</td><td>'+(p.realizado_por_full?(ie_esc(p.realizado_por_full)+ts):'<span class="pend">·</span>')+'</td><td>'+(p.verificado_por_full?(ie_esc(p.verificado_por_full)+ts):'<span class="pend">·</span>')+'</td><td><div class="act"><button class="ab ab-i" onclick="infoPaso('+p.orden+')" title="Detalles de la Verificación">i</button></div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin pasos de envasado (se definen en el MBR).</div>')+
      '</div>';
    var ipc=d.ipc||[];
    html+='<div class="card"><div class="sechead"><div class="sectit">5. Controles en Proceso</div>'+(editable?'<button class="btreg" onclick="ie_prox()">+ Control de Volumen</button>':'')+'</div>'+
      '<div class="sechint">Realizar muestreo y registrar control en proceso:</div>'+
      (ipc.length?('<div class="tw"><table class="t"><thead><tr><th>Control</th><th>Resultado</th><th>Observaciones</th><th>Realizado por</th><th>Acciones</th></tr></thead><tbody>'+
        ipc.map(function(c){var res=c.conforme===2?'<span class="bdg" style="background:var(--cx-bg-alt);color:var(--cx-text-mute)">No aplica</span>':(c.resultado?(ie_esc(c.resultado)+bdgC(c.conforme)):'<span class="pend">pendiente</span>');return '<tr><td>'+ie_esc(c.control||'')+(c.rango?' <span class="muted" style="font-size:11px">('+ie_esc(c.rango)+')</span>':'')+'</td><td>'+res+'</td><td>'+ie_esc(c.observaciones||'No aplica')+'</td><td>'+(c.realizado_por?ie_esc(c.realizado_por_full||c.realizado_por):'<span class="pend">·</span>')+'</td><td><div class="act">'+abI()+abEd()+'</div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin controles en proceso (se definen en el MBR).</div>')+
      '</div>';
    var obs=d.observaciones_proceso||[];
    html+='<div class="card"><div class="sechead"><div class="sectit">6. Observaciones Generales del Proceso</div>'+regBtn('Registrar')+'</div>'+
      (obs.length?('<div class="tw"><table class="t"><thead><tr><th>Descripción de la observación</th><th>Realizada por</th><th>Fecha y hora</th></tr></thead><tbody>'+
        obs.map(function(o){return '<tr><td>'+ie_esc(o.descripcion||'')+'</td><td>'+ie_esc(o.registrado_por_full||o.registrado_por||'·')+'</td><td class="muted">'+dt(o.fecha)+'</td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin observaciones registradas.</div>')+
      '</div>';
    var regs=d.registros_fisicos||[];
    html+='<div class="card"><div class="sectit">7. Registros Físicos del Proceso de Envasado</div>'+
      (regs.length?('<div class="tw"><table class="t"><thead><tr><th>Código</th><th>Descripción</th><th>Documento</th></tr></thead><tbody>'+
        regs.map(function(g){return '<tr><td class="mono">'+ie_esc(g.id)+'</td><td>'+ie_esc(g.descripcion||'')+'</td><td>'+(g.tiene_pdf?('<a class="ab ab-pdf" href="/api/brd/ebr/'+EBR_ID+'/registros-fisicos/'+g.id+'/pdf" target="_blank" title="Ver">&#128196;</a>'):'<span class="pend">·</span>')+'</td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin registros físicos adjuntos.</div>')+
      '</div>';
    document.getElementById('ie_cuerpo').innerHTML=html;
  }catch(e){document.getElementById('ie_cab').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error de red: '+ie_esc(e.message)+'</span>';}
}
function ie_prox(){alert('Esta acción la construimos en el siguiente paso.');}
async function regDespeje(idx){
  // Registrar la verificación de despeje (operario) · Cumple Sí/No + observación.
  // Mismo endpoint GMP que producción (e-firma/audit en el backend).
  var it=(window._dch||[]).find(function(x){return x.idx===idx;}); if(!it)return;
  var esCorr=(it.cumple!=null);
  var titulo=esCorr?'CORREGIR RESULTADO (solo Calidad / Dirección Técnica)':'REGISTRAR VERIFICACIÓN (operario)';
  var c=confirm(titulo+'\\n\\n'+it.texto+'\\n\\n¿CUMPLE? (Aceptar = Sí · Cancelar = No)');
  var obs=prompt('Observación'+(esCorr?' / motivo de la corrección':' (opcional)')+':', it.observaciones||'')||'';
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/despeje-item',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({item_idx:idx,cumple:c?1:0,observaciones:obs,etapa:'dispensacion'})});
    var d=await r.json();
    if(!r.ok){alert((r.status===403?'🔒 ':'Error: ')+(d.error||r.status));return;}
    ie_load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
function infoDespeje(idx){
  var it=(window._dch||[]).find(function(x){return x.idx===idx;}); if(!it)return;
  var res=it.cumple===1?'Sí cumple':(it.cumple===0?'No cumple':'Pendiente');
  alert('VERIFICACIÓN DE DESPEJE\\n\\n'+it.texto+'\\n\\nResultado: '+res+(it.observaciones?('\\nObservación: '+it.observaciones):'')+(it.registrado_por?('\\nRegistrado por: '+it.registrado_por):''));
}
function infoPaso(orden){
  // Detalles de la Verificación (sección 4 · read-only). Numera 1..N dentro de la fase.
  var pasos=(window._pasos||[]);
  var i=pasos.findIndex(function(x){return x.orden===orden;}); if(i<0)return;
  var p=pasos[i];
  var est=p.completado_flag?'Completado':(p.iniciado?'En proceso':'Pendiente');
  alert('DETALLES DE LA VERIFICACIÓN\\n\\nPaso '+(i+1)+': '+p.descripcion+'\\n\\nEstado: '+est+'\\nRealizado por: '+(p.realizado_por_full||'·')+'\\nVerificado por: '+(p.verificado_por_full||'·')+(p.observaciones?('\\nObservaciones: '+p.observaciones):''));
}
async function registrarActividades(){
  // Registra (completa) la siguiente actividad pendiente · endpoint GMP con audit/e-firma.
  var pend=(window._pasos||[]).filter(function(p){return !p.completado_flag;});
  if(!pend.length){alert('Todas las actividades ya están registradas.');return;}
  var p=pend[0];
  var _i=(window._pasos||[]).findIndex(function(x){return x.orden===p.orden;});
  var obs=prompt('Registrar Paso '+(_i+1)+':\\n'+p.descripcion+'\\n\\nResultado / observación:', p.observaciones||'');
  if(obs===null)return;
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/pasos/'+p.orden+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({observaciones:obs||''})});
    var d=await r.json();
    if(!r.ok){alert((r.status===403?'🔒 ':'Error: ')+(d.error||r.status));return;}
    ie_load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
ie_load();

ie_load();
</script>
</body></html>"""


@bp.route("/planta/legajo-envasado/<int:ebr_id>", methods=["GET"])
def legajo_envasado_page(ebr_id):
    """Legajo de Envasado · página PROPIA, aislada de producción · se construye paso a
    paso con Sebastián (9-jun-2026). Reusa vista-completa para la cabecera."""
    if not session.get("compras_user"):
        return Response(
            f'<script>location.href="/login?next=/planta/legajo-envasado/{ebr_id}"</script>',
            mimetype="text/html")
    return Response(_ENVASADO_LEGAJO_HTML.replace("__EBR_ID__", str(ebr_id)),
                    mimetype="text/html")


_ACOND_LEGAJO_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Orden de Acondicionamiento · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
/* 96vw = la regla de EOS para los modulos. Estaban clavadas en 1100-1200px: en un monitor de 1990 dejaban el 40% en blanco y la tabla de materiales -7 columnas- se desbordaba cortando 'Diferencia'. La orden madre ya usaba 96vw; se alinean las de DATOS. Los dos INSTRUCTIVOS quedan angostos a proposito: son formatos que se leen y se imprimen. */.wrap{max-width:96vw;margin:0 auto}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:28px 32px;box-shadow:0 1px 3px rgba(24,24,27,.04),0 8px 24px -14px rgba(24,24,27,.10);margin-bottom:18px}
a.back{color:var(--cx-primary-text,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
.ortit{font-size:26px;font-weight:800;color:var(--cx-text,#18181b);margin:6px 0 6px;letter-spacing:-.4px}
.prod{color:var(--cx-text-mute,#71717a);font-size:17px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:24px 22px}
.lbl{font-size:12.5px;font-weight:700;color:var(--cx-text-soft,#3f3f46);margin-bottom:5px}
.val{font-size:14px;color:var(--cx-text-mute,#71717a);line-height:1.45}
.mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.btnrow{display:flex;gap:12px;justify-content:flex-start;flex-wrap:wrap;margin-top:24px}
.bt{padding:11px 20px;border-radius:10px;font-size:13px;font-weight:600;border:1px solid transparent;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:7px;transition:all .15s ease}
.bt-add{background:var(--cx-primary,#6d28d9);color:#fff}.bt-add:hover{background:var(--cx-primary-dark,#4c1d95)}
.bt-pdf{background:var(--cx-bg-alt,#fbfbfd);color:var(--cx-text-soft,#3f3f46);border-color:var(--cx-border,#e6e6ea)}.bt-pdf:hover{border-color:var(--cx-primary,#6d28d9);color:var(--cx-primary-text,#6d28d9)}
.bt-back{background:transparent;color:var(--cx-text-mute,#71717a);border-color:var(--cx-border,#e6e6ea)}.bt-back:hover{background:var(--cx-bg-alt,#fbfbfd)}
.sectit{font-size:18px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.2px;margin:0 0 16px}
.tw{overflow-x:auto}
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th,table.t td{padding:13px 12px;text-align:left;vertical-align:middle;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
table.t thead th{color:var(--cx-text-mute,#71717a);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;border-bottom:1px solid var(--cx-border,#e6e6ea)}
table.t thead th .ar{color:var(--cx-text-faint,#a1a1aa);font-size:10px;margin-left:3px}
table.t tbody td{color:var(--cx-text-soft,#3f3f46)}
table.t tbody tr:hover td{background:var(--cx-primary-pale,#f5f3ff)}
table.t tfoot td{font-weight:800;color:var(--cx-text,#18181b);border-top:2px solid var(--cx-border,#e6e6ea)}
.regfoot{color:var(--cx-text-faint,#a1a1aa);font-size:12.5px;margin-top:14px}
.act{display:inline-flex;gap:6px;flex-wrap:wrap}
.ab{width:32px;height:32px;border-radius:8px;border:none;cursor:pointer;color:#fff;font-size:14px;line-height:1;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;transition:filter .15s ease}.ab:hover{filter:brightness(1.08)}
.ab-play{background:var(--cx-success,#15803d)}.ab-plus{background:var(--cx-primary,#6d28d9)}.ab-x{background:var(--cx-danger,#dc2626)}.ab-ed{background:var(--cx-warn,#f59e0b)}.ab-ed2{background:var(--cx-success,#15803d)}.ab-i{background:var(--cx-info,#2563eb)}
@media(max-width:760px){.grid{grid-template-columns:repeat(2,1fr)}}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/inventarios#acondicionamiento">&larr; Acondicionamiento</a>
  <div class="card" id="cab"><div class="muted">Cargando…</div></div>
  <div id="cuerpo"></div>
</div>
<div id="arte-ov" style="display:none;position:fixed;inset:0;background:rgba(15,23,42,.55);align-items:center;justify-content:center;z-index:70;padding:20px">
  <div style="background:var(--cx-card,#fff);border:1px solid var(--cx-border,#e4e4e7);border-radius:16px;padding:26px;max-width:520px;width:100%;box-shadow:0 24px 60px rgba(15,23,42,.28)">
    <div style="font-size:17px;font-weight:800;color:var(--cx-text,#18181b);margin-bottom:4px">Registrar arte / codificaci&oacute;n</div>
    <div style="font-size:12.5px;color:var(--cx-text-soft,#52525b);margin-bottom:18px">Queda pendiente de aprobaci&oacute;n &middot; Calidad la firma antes de etiquetar.</div>
    <div style="display:grid;gap:12px">
      <div><label style="font-size:12px;font-weight:700;color:var(--cx-text-soft,#52525b)">Arte / presentaci&oacute;n *</label>
        <input id="arte-desc" placeholder="Etiqueta frasco 30 mL" style="width:100%;margin-top:5px;padding:10px;border:1px solid var(--cx-border,#e4e4e7);border-radius:9px;font-size:14px;background:var(--cx-bg-alt,#fafafa);color:var(--cx-text,#18181b)"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div><label style="font-size:12px;font-weight:700;color:var(--cx-text-soft,#52525b)">C&oacute;digo de lote impreso</label>
          <input id="arte-lote" style="width:100%;margin-top:5px;padding:10px;border:1px solid var(--cx-border,#e4e4e7);border-radius:9px;font-size:14px;background:var(--cx-bg-alt,#fafafa);color:var(--cx-text,#18181b)"></div>
        <div><label style="font-size:12px;font-weight:700;color:var(--cx-text-soft,#52525b)">C&oacute;digo de vencimiento</label>
          <input id="arte-venc" style="width:100%;margin-top:5px;padding:10px;border:1px solid var(--cx-border,#e4e4e7);border-radius:9px;font-size:14px;background:var(--cx-bg-alt,#fafafa);color:var(--cx-text,#18181b)"></div>
      </div>
    </div>
    <div id="arte-msg" style="color:var(--cx-danger-text,#b91c1c);font-size:12.5px;min-height:18px;margin-top:12px"></div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px">
      <button class="bt bt-back" onclick="cerrarArte()">Cancelar</button>
      <button class="bt bt-add" id="arte-ok" onclick="guardarArte()">Registrar</button>
    </div>
  </div>
</div>
<script>
var EBR_ID=__EBR_ID__;
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function ufmt(n){return n==null?'·':Number(n).toLocaleString('es-CO');}
function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
function estCol(e){e=(e||'').toLowerCase();if(e.indexOf('aprob')>=0||e.indexOf('liber')>=0)return '#166534';if(e.indexOf('proceso')>=0)return '#b45309';if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)return '#b91c1c';return '#475569';}
async function load(){
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){document.getElementById('cab').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error: '+esc(d.error||r.status)+'</span>';return;}
    var h=d.header||{};
    var estado=h.estado||'·';
    var pres=d.acond_presentaciones||[];
    var totUds=pres.reduce(function(a,p){return a+(Number(p.unidades)||0);},0);
    // El encabezado decia "Unidades acondicionadas: 333" mientras la fila de abajo decia
    // "Programado": sin acondicionamiento registrado la lista cae a las presentaciones
    // PLANEADAS, o sea que el rotulo prometia un hecho que no habia ocurrido. El estado se
    // DERIVA de lo que hay registrado, no se afirma (M19/M5).
    var _hayReal=pres.some(function(p){
      var e=String(p.estado||'').toLowerCase();
      return e && e.indexOf('program')<0 && e.indexOf('planead')<0;
    });
    var rotUds=(_hayReal?'Unidades acondicionadas':'Unidades a acondicionar (plan)');
    document.getElementById('cab').innerHTML=
      '<div class="ortit">ORDEN DE ACONDICIONAMIENTO N°: '+esc(h.numero_op||('OA-'+EBR_ID))+'</div>'+
      '<div class="prod">'+esc(h.producto||h.titulo||'·')+(pres.length&&pres[0].presentacion?(', '+esc(pres[0].presentacion)):'')+'</div>'+
      '<div style="margin:-10px 0 18px"><span style="display:inline-flex;align-items:center;gap:5px;background:var(--cx-primary-pale,#f5f3ff);color:var(--cx-primary-text,#6d28d9);font-size:12px;font-weight:700;padding:5px 12px;border-radius:20px;border:1px solid var(--cx-primary-light,#a78bfa)">&#128100; '+esc((d.mi_rol&&d.mi_rol.rol)||'Usuario')+'</span></div>'+
      bandaAprobacion(h,d.mi_rol)+
      '<div class="grid">'+
        fld('N° Lote','<span class="mono">'+esc(h.lote_codigo||'·')+'</span>')+
        fld(rotUds,ufmt(totUds))+
        fld('Estado Actual','<b style="color:'+estCol(estado)+'">'+esc(estado)+'</b>')+
        fld('Elaborado por',esc(h.operario||'·'))+
        fld('Observaciones',esc(h.observaciones||'Ninguna'))+
        fld('Área / Línea',esc(h.area_linea||'·'))+
        fld('Supervisado por',esc(h.supervisado_por||'·'))+
        fld('Liberado por',esc(h.liberado_por_full||'·'))+
        fld('Visto bueno · Dirección Técnica', (d.aprobado_dt_por?('<b>'+esc(d.aprobado_dt_por)+'</b>'+(d.aprobado_dt_at?('<div style="font-size:11px;color:#71717a">'+esc(String(d.aprobado_dt_at).replace('T',' ').slice(0,16))+'</div>'):'')):'<span style="color:#a1a1aa">pendiente · lo firma el Director Técnico al liberar el producto terminado</span>'))+
      '</div>'+
      '<div class="btnrow">'+
        '<a class="bt bt-add" href="/planta/instrucciones-acondicionamiento/'+EBR_ID+'">&#9654; Instrucciones de Acondicionamiento</a>'+
        ((d.mi_rol&&d.mi_rol.puede_ejecutar&&(estado==='iniciado'||estado==='en_proceso'))?'<button class="bt bt-pdf" onclick="terminarLote()" title="Operario: termina el acondicionamiento (todos los pasos completos)">&#10003; Terminar</button>':'')+
        ((d.mi_rol&&d.mi_rol.puede_liberar&&(estado==='completado'||estado==='en_revision_qc'))?'<button class="bt bt-add" onclick="liberarLote()" style="background:var(--cx-success,#15803d)" title="Calidad/Aseguramiento: libera el lote con e-firma (cierra el batch record)">&#128275; Liberar lote</button>':'')+
        ((d.mi_rol&&d.mi_rol.aprueba_dt&&!d.aprobado_dt_por&&(estado==='liberado'||estado==='completado'||estado==='en_revision_qc'))?'<button class="bt bt-add" id="vb-btn" onclick="aprobarDtAcond()" style="background:var(--cx-primary,#6d28d9)" title="Visto bueno final de Direccion Tecnica sobre el producto terminado (PRD-PRO-001-F01)">&#9989; Dar visto bueno</button>':'')+
        '<a class="bt bt-pdf" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">&#128196; Descargar</a>'+
        ((d.mi_rol&&d.mi_rol.puede_aprobar)?'<button class="bt bt-pdf" onclick="regenerarMBR()" title="Crea una nueva versión del MBR con los pasos de acondicionamiento actualizados (GMP · obsoleta el anterior · solo Calidad/Dirección Técnica)">&#8635; Regenerar MBR</button>':'')+
        '<a class="bt bt-back" href="/inventarios#acondicionamiento">&#9198; Atrás</a>'+
      '</div>';
    window._prod=h.producto||h.titulo||''; window._lote=h.lote_codigo||'';
    function ar(){return '<span class="ar">&#8645;</span>';}
    var presRows=pres.length
      ? pres.map(function(p){
          return '<tr>'+
            '<td>'+esc(p.presentacion||'·')+(p.cliente?' <span style="color:var(--cx-text-faint, #94a3b8);font-size:11px">· '+esc(p.cliente)+'</span>':'')+'</td>'+
            '<td class="mono">'+esc(p.lote||'·')+'</td>'+
            '<td>'+(p.unidades!=null?Number(p.unidades).toLocaleString('es-CO'):'')+'</td>'+
            '<td>'+esc(p.estado||'·')+'</td>'+
            '<td><div class="act"><a class="ab ab-play" href="/planta/instrucciones-acondicionamiento/'+EBR_ID+'" title="Ejecutar / Instrucciones de Acondicionamiento">&#9654;</a></div></td>'+
          '</tr>';
        }).join('')
      : '<tr><td colspan="5" class="muted" style="text-align:center;background:var(--cx-card, #fff)">Sin presentaciones acondicionadas aún.</td></tr>';
    var presCard='<div class="card"><div class="sectit">Unidades por Presentación</div>'+
      '<div class="tw"><table class="t"><thead><tr>'+
        '<th>Presentación'+ar()+'</th><th>N° de lote'+ar()+'</th><th>Unidades'+ar()+'</th><th>Estado'+ar()+'</th><th>Acciones</th>'+
      '</tr></thead><tbody>'+presRows+'</tbody>'+
      (pres.length?('<tfoot><tr><td><b>Total</b></td><td></td><td>'+totUds.toLocaleString('es-CO')+'</td><td></td><td></td></tr></tfoot>'):'')+
      '</table></div>'+
      '<div class="regfoot">Mostrando '+pres.length+' de '+pres.length+' registro'+(pres.length===1?'':'s')+'</div></div>';
    var mats=d.acond_materiales||[];
    function mc(v){return v!=null?Number(v).toLocaleString('es-CO'):'';}
    var matRows=mats.length
      ? mats.map(function(m){
          return '<tr>'+
            '<td class="mono">'+esc(m.lote_acond||'·')+'</td>'+
            '<td>'+esc(m.material||'·')+'</td>'+
            '<td class="mono">'+esc(m.lote_material||'·')+'</td>'+
            '<td>'+mc(m.requerida)+'</td>'+
            '<td>'+mc(m.devuelta)+'</td>'+
            '<td>'+mc(m.utilizada)+'</td>'+
            '<td>'+mc(m.averiada)+'</td>'+
            '<td>'+mc(m.diferencia)+'</td>'+
          '</tr>';
        }).join('')
      : '<tr><td colspan="8" class="muted" style="text-align:center;background:var(--cx-card, #fff)">Sin materiales de empaque registrados aún.</td></tr>';
    var matCard='<div class="card"><div class="sectit">Materiales de Empaque</div>'+
      '<div class="tw"><table class="t"><thead><tr>'+
        '<th>N° lote acond.'+ar()+'</th><th>Material de empaque'+ar()+'</th><th>N° de lote material'+ar()+'</th><th>Cant. requerida'+ar()+'</th><th>Cant. devuelta'+ar()+'</th><th>Cant. utilizada'+ar()+'</th><th>Cant. averiada'+ar()+'</th><th>Diferencia'+ar()+'</th>'+
      '</tr></thead><tbody>'+matRows+'</tbody></table></div>'+
      '<div class="regfoot">Mostrando '+mats.length+' de '+mats.length+' registro'+(mats.length===1?'':'s')+'</div></div>';
    // ARTES Y CODIFICACION · en MyBatch la accion "Aprobar Etiqueta" vive en la orden de
    // ACONDICIONAMIENTO, que es donde se etiqueta. En EOS el endpoint existe para las tres
    // fases desde junio, pero el unico lugar desde donde se podia llegar era el modal del
    // dashboard: en la pantalla del producto terminado la aprobacion era inalcanzable (M121,
    // el mismo hueco que tenia el visto bueno del DT). Se pide aparte y no rompe la carga si
    // falla: un error de esta lectura no puede dejar la orden sin verse (M94).
    var artes=[];
    try{
      var ra=await fetch('/api/brd/ebr/'+EBR_ID+'/artes',{credentials:'same-origin',cache:'no-store'});
      if(ra.ok){ var da=await ra.json(); artes=(da&&da.items)||[]; }
    }catch(e2){ artes=null; }
    var puedeAprobarArte=!!(d.mi_rol&&(d.mi_rol.verifica||d.mi_rol.puede_aprobar));
    var editableArte=(estado==='iniciado'||estado==='en_proceso');
    var arteCard='';
    if(artes===null){
      arteCard='<div class="card"><div class="sectit">Artes y Codificacion</div>'+
        '<div class="muted">No se pudo leer las artes de este lote &middot; volve a cargar la pagina.</div></div>';
    }else{
      var arteRows=artes.length
        ? artes.map(function(a){
            var aprob=(a.aprobado_por||'').trim();
            return '<tr>'+
              '<td>'+esc(a.descripcion||'&middot;')+'</td>'+
              '<td class="mono">'+esc(a.codigo_lote||'&middot;')+'</td>'+
              '<td class="mono">'+esc(a.codigo_vencimiento||'&middot;')+'</td>'+
              '<td>'+(aprob
                  ? ('<b style="color:var(--cx-success-text,#166534)">&#10003; '+esc(aprob)+'</b>'+
                     (a.aprobado_at_utc?('<div style="font-size:11px;color:var(--cx-text-faint,#a1a1aa)">'+esc(String(a.aprobado_at_utc).replace('T',' ').slice(0,16))+'</div>'):''))
                  : '<span class="muted">pendiente</span>')+'</td>'+
              '<td><div class="act">'+
                ((!aprob&&puedeAprobarArte&&editableArte)
                  ? '<button class="ab ab-ed2" onclick="aprobarArte('+a.id+')" title="Aprobar la etiqueta / codificacion de esta presentacion (queda firmada · Part 11)">&#10003;</button>'
                  : '')+
              '</div></td>'+
            '</tr>';
          }).join('')
        : '<tr><td colspan="5" class="muted" style="text-align:center;background:var(--cx-card, #fff)">Sin artes registradas a&uacute;n &middot; se registra el arte de cada presentaci&oacute;n y Calidad la aprueba antes de etiquetar.</td></tr>';
      arteCard='<div class="card"><div class="sectit">Artes y Codificacion</div>'+
        '<div class="tw"><table class="t"><thead><tr>'+
          '<th>Arte / presentaci&oacute;n'+ar()+'</th><th>C&oacute;digo de lote'+ar()+'</th><th>C&oacute;digo de vencimiento'+ar()+'</th><th>Aprobada por'+ar()+'</th><th>Acciones</th>'+
        '</tr></thead><tbody>'+arteRows+'</tbody></table></div>'+
        ((d.mi_rol&&d.mi_rol.puede_ejecutar&&editableArte)
          ? '<div style="margin-top:12px"><button class="bt bt-add" onclick="registrarArte()">+ Registrar arte</button></div>'
          : '')+
        '<div class="regfoot">Mostrando '+artes.length+' de '+artes.length+' registro'+(artes.length===1?'':'s')+'</div></div>';
    }
    document.getElementById('cuerpo').innerHTML = presCard + matCard + arteCard;
  }catch(e){document.getElementById('cab').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error de red: '+esc(e.message)+'</span>';}
}

function registrarArte(){
  // Registrar el arte NO es aprobarlo: lo carga quien ejecuta y Calidad lo aprueba despues.
  // Un formulario, no tres prompt() encadenados: encadenarlos obliga a empezar de cero si te
  // equivocas en el segundo, y no deja ver lo que ya escribiste (M199).
  var ov=document.getElementById('arte-ov');
  if(ov){ ov.style.display='flex'; var f=document.getElementById('arte-desc'); if(f){f.value='';f.focus();}
          var l=document.getElementById('arte-lote'); if(l){l.value='';}
          var v=document.getElementById('arte-venc'); if(v){v.value='';}
          var m=document.getElementById('arte-msg'); if(m){m.textContent='';} }
}
function cerrarArte(){var o=document.getElementById('arte-ov');if(o)o.style.display='none';}

async function guardarArte(){
  if(window._arteBusy) return;
  var g=function(id){var el=document.getElementById(id);return el?(el.value||'').trim():'';};
  var msg=document.getElementById('arte-msg');
  var desc=g('arte-desc');
  if(!desc){ if(msg){msg.textContent='Escribi que arte se registra.';} return; }
  window._arteBusy=true;
  var b=document.getElementById('arte-ok'); if(b){b.disabled=true;}
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/artes',{method:'POST',
      headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({descripcion:desc,codigo_lote:g('arte-lote'),codigo_vencimiento:g('arte-venc')})});
    var d=await r.json();
    if(!r.ok||d.error){ if(msg){msg.textContent='No se pudo registrar: '+((d&&d.error)||r.status);} return; }
    location.reload();
  }catch(e){ if(msg){msg.textContent='Error de red.';} }
  finally { window._arteBusy=false; if(b){b.disabled=false;} }
}

async function aprobarArte(arteId){
  // ⚠ El arte NO se firma con `firmar-rapido`: ese endpoint firma SIEMPRE sobre
  // `ebr_ejecuciones`, y el aprobador valida la firma contra `ebr_artes_codificacion` -- una
  // firma rapida seria rechazada y el boton quedaria mudo (M219). El contrato correcto es la
  // firma completa (challenge + sign) apuntando al registro del arte, que es el que ya usa el
  // modal del dashboard: mismo contrato o ninguno (M166).
  if(window._arteBusy) return; window._arteBusy=true;
  try{
    var pwd=prompt('Firma electronica (21 CFR Part 11) · tu contrasena para aprobar la etiqueta:');
    if(!pwd) return;
    var totp=prompt('Codigo MFA de 6 digitos (si no usas MFA, dejalo vacio y OK):')||'';
    var rc=await fetch('/api/sign/challenge',{method:'POST',
      headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({password:pwd,totp_token:totp})});
    var dc=await rc.json();
    if(!rc.ok){ alert(dc.error||'Credenciales invalidas'); return; }
    var rs=await fetch('/api/sign',{method:'POST',
      headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({record_table:'ebr_artes_codificacion',record_id:String(arteId),
                           meaning:'aprueba',challenge_token:dc.token})});
    var ds=await rs.json();
    if(!rs.ok){ alert(ds.error||'Error al firmar'); return; }
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/artes/'+arteId+'/aprobar',{method:'POST',
      headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({signature_id:ds.signature_id})});
    var d=await r.json();
    if(!r.ok||d.error){ alert('Error: '+(d.error||r.status)); return; }
    location.reload();
  } finally { window._arteBusy=false; }
}
async function aprobarDtAcond(){
  // El acto del Director Tecnico sobre el PRODUCTO TERMINADO (PRD-PRO-001-F01 · acta con
  // Hernando del 27-jul). El endpoint existia desde junio (mig 286) y esta pantalla no lo
  // ofrecia: la unica forma de darlo era el modal del dashboard, asi que en el legajo del
  // producto terminado la firma era inalcanzable (M121).
  //
  // Firma con el MISMO contrato que usa liberar en esta pantalla (firmar-rapido y despues
  // la accion), no con helpers de otra: un bloque compartido tiene que traer su propia
  // dependencia, y llamar a una que no existe deja el boton mudo (M166).
  if(window._vbBusy) return; window._vbBusy=true;
  var b=document.getElementById('vb-btn');
  try{
    if(!confirm('Dar el visto bueno de Direccion Tecnica a este lote? Queda firmado con tu identidad (Part 11).')){return;}
    if(b){b.disabled=true;}
    var rf=await fetch('/api/brd/ebr/'+EBR_ID+'/firmar-rapido',{method:'POST',
      headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({meaning:'aprueba_dt'})});
    var df=await rf.json();
    if(!rf.ok||!df.ok){ alert('No se pudo firmar: '+((df&&df.error)||rf.status)); return; }
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/aprobar-dt',{method:'POST',
      headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({signature_id:df.signature_id})});
    var d=await r.json();
    if(!r.ok||d.error){ alert('Error: '+(d.error||r.status)); return; }
    location.reload();
  } finally { window._vbBusy=false; if(b){b.disabled=false;} }
}

async function regenerarMBR(){
  var prod=(window._prod||'');
  if(!prod){alert('No identifiqué el producto.');return;}
  if(!confirm('¿Regenerar el MBR de "'+prod+'" con los pasos de acondicionamiento actualizados y abrir un legajo NUEVO para verlos?\\n\\nObsoleta el MBR anterior (forma GMP correcta · queda auditado).'))return;
  try{
    var r=await fetch('/api/brd/mbr/preparar-aprobado',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto_nombre:prod,regenerar:true})});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo regenerar: '+((d&&d.error)||r.status));return;}
    var base=(window._lote||prod).replace(/-R\\d+$/,'');
    var nuevoLote=base+'-OA'+(Math.floor(Date.now()/1000)%100000);
    var rl=await fetch('/api/brd/legajo-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({producto:prod,lote:nuevoLote,fase:'acondicionamiento'})});
    var dl=await rl.json();
    if(rl.ok&&dl.ok&&dl.id){location.href='/planta/legajo-acondicionamiento/'+dl.id;return;}
    alert('✅ MBR regenerado (v'+(d.version||'?')+'). No pude abrir el legajo nuevo automáticamente; créalo desde Acondicionamiento.');
  }catch(e){alert('Error: '+(e.message||e));}
}
async function terminarLote(){
  var cant=prompt('Terminar el acondicionamiento · cantidad real (g, opcional · Enter para usar el objetivo):');
  if(cant===null)return;
  var body={};
  if(String(cant).trim()!==''){var n=parseFloat(cant);if(n>0)body.cantidad_real_g=n;}
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok){alert('No se pudo terminar: '+(d.error||r.status));return;}
    alert('✅ Acondicionamiento terminado. Ahora Calidad/Aseguramiento puede liberarlo.'); location.reload();
  }catch(e){alert('Error: '+(e.message||e));}
}
async function liberarLote(){ _libAbrir(); }

// Modal de liberacion · propio de EOS, no el cuadro gris del navegador.
// Trae el motivo del rechazo y el campo para resolverlo SIN salir: el control sigue siendo
// obligatorio, pero ahora se puede cumplir donde aparece (Sebastian 16-ago-2026).
function _libAbrir(motivo, yieldPct){
  var ov=document.getElementById('libov');
  if(!ov){
    ov=document.createElement('div'); ov.id='libov';
    ov.style.cssText='position:fixed;inset:0;background:rgba(15,12,35,.55);display:flex;'+
      'align-items:center;justify-content:center;z-index:9999;padding:20px';
    ov.innerHTML='<div style="background:var(--cx-card,#fff);color:var(--cx-text,#0f172a);'+
      'border-radius:16px;max-width:640px;width:100%;box-shadow:0 24px 60px rgba(15,12,35,.35);'+
      'overflow:hidden">'+
      '<div style="padding:24px 26px 6px"><div style="font-size:20px;font-weight:800;'+
      'letter-spacing:-.01em">Liberar el lote</div>'+
      '<div id="libsub" style="margin-top:6px;font-size:14px;line-height:1.55;'+
      'color:var(--cx-text-soft,#475569)">Cierra el batch record con tu firma electr&oacute;nica. '+
      'Queda auditado (Calidad / Aseguramiento &middot; 21 CFR Part 11).</div>'+
      '<div id="libwarn" style="display:none;margin-top:14px;padding:14px 16px;border-radius:10px;'+
      'background:var(--cx-warn-pale,#fef3c7);border:1px solid var(--cx-warn,#f59e0b)">'+
      '<div id="libwarntxt" style="font-size:13.5px;line-height:1.55;color:var(--cx-warn-text,#92400e)"></div>'+
      '<label style="display:block;margin-top:12px;font-size:12px;font-weight:700;'+
      'text-transform:uppercase;letter-spacing:.06em;color:var(--cx-text-soft,#475569)">'+
      'Por qu&eacute; dio ese rendimiento</label>'+
      '<textarea id="libjust" rows="3" placeholder="Ej: se perdi&oacute; producto al trasvasar el '+
      'recipiente 2 · o la balanza estaba destarada" style="width:100%;margin-top:6px;'+
      'padding:10px 12px;border:1px solid var(--cx-border,#cbd5e1);border-radius:9px;'+
      'font:inherit;font-size:14px;background:var(--cx-card,#fff);color:var(--cx-text,#0f172a);'+
      'resize:vertical"></textarea>'+
      '<div style="margin-top:6px;font-size:12px;color:var(--cx-text-faint,#94a3b8)">'+
      'Queda en el legajo y en el PDF: es la explicaci&oacute;n que va a leer quien audite.</div>'+
      '</div></div>'+
      '<div style="display:flex;gap:10px;justify-content:flex-end;padding:18px 26px 22px">'+
      '<button onclick="_libCerrar()" style="padding:10px 18px;border-radius:9px;'+
      'border:1px solid var(--cx-border,#cbd5e1);background:var(--cx-card,#fff);'+
      'color:var(--cx-text,#0f172a);font:inherit;font-weight:600;cursor:pointer">Cancelar</button>'+
      '<button id="libok" onclick="_libConfirmar()" style="padding:10px 20px;border-radius:9px;'+
      'border:none;background:linear-gradient(135deg,#a78bfa,#6d28d9);color:#fff;font:inherit;'+
      'font-weight:700;cursor:pointer">Liberar el lote</button></div></div>';
    document.body.appendChild(ov);
  }
  ov.style.display='flex';
  var w=document.getElementById('libwarn');
  if(motivo){
    w.style.display='block';
    document.getElementById('libwarntxt').innerHTML=motivo;
    setTimeout(function(){var t=document.getElementById('libjust'); if(t)t.focus();},60);
  }else{
    w.style.display='none';
  }
}
function _libCerrar(){var o=document.getElementById('libov'); if(o)o.style.display='none';}

async function _libConfirmar(){
  var btn=document.getElementById('libok');
  var just=(document.getElementById('libjust')||{}).value||'';
  var warn=document.getElementById('libwarn');
  if(warn&&warn.style.display==='block'&&just.trim().length<10){
    document.getElementById('libwarntxt').innerHTML=
      'Escrib&iacute; por qu&eacute; dio ese rendimiento (al menos 10 caracteres): es lo que va a leer quien audite.';
    return;
  }
  if(btn){btn.disabled=true; btn.textContent='Liberando...';}
  try{
    var rf=await fetch('/api/brd/ebr/'+EBR_ID+'/firmar-rapido',{method:'POST',
      headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify({meaning:'libera'})});
    var df=await rf.json();
    if(!rf.ok||!df.ok){
      document.getElementById('libsub').innerHTML='No se pudo firmar la liberaci&oacute;n: '+
        _escLib((df&&df.error)||rf.status);
      if(btn){btn.disabled=false; btn.textContent='Liberar el lote';}
      return;
    }
    var cuerpo={};
    if(just.trim()){cuerpo.yield_justificacion=just.trim();}
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/liberar',{method:'POST',
      headers:{'Content-Type':'application/json'},credentials:'same-origin',
      body:JSON.stringify(cuerpo)});
    var d=await r.json();
    if(!r.ok){
      if(btn){btn.disabled=false; btn.textContent='Liberar el lote';}
      // El rendimiento fuera de rango no es un error del usuario: es un dato que falta.
      // Se pide en el mismo modal en vez de mandarlo a buscar donde se justifica.
      if(d&&d.codigo==='YIELD_FUERA_RANGO'){
        _libAbrir('El lote rindi&oacute; <b>'+_escLib(d.yield_pct)+'%</b> y lo normal es entre 80% '+
          'y 115%. Puede ser p&eacute;rdida de producto, un error de tara o unidades de otra orden. '+
          'GMP pide explicarlo antes de liberar.', d.yield_pct);
        return;
      }
      document.getElementById('libsub').innerHTML='No se pudo liberar: '+
        _escLib((d&&d.error)||r.status);
      return;
    }
    _libCerrar();
    location.reload();
  }catch(e){
    if(btn){btn.disabled=false; btn.textContent='Liberar el lote';}
    document.getElementById('libsub').innerHTML='Error: '+_escLib(e.message||e);
  }
}
function _escLib(s){var d=document.createElement('div');d.textContent=(s==null?'':String(s));return d.innerHTML;}

load();
</script>
</body></html>"""


@bp.route("/planta/legajo-acondicionamiento/<int:ebr_id>", methods=["GET"])
def legajo_acondicionamiento_page(ebr_id):
    """Legajo de Acondicionamiento (OA) · página propia, aislada de producción ·
    espeja el legajo de envasado (10-jun-2026). Reusa vista-completa."""
    if not session.get("compras_user"):
        return Response(
            f'<script>location.href="/login?next=/planta/legajo-acondicionamiento/{ebr_id}"</script>',
            mimetype="text/html")
    return Response(_ACOND_LEGAJO_HTML.replace("__EBR_ID__", str(ebr_id)),
                    mimetype="text/html")


# ──────────────────────────────────────────────────────────────────────────
# Aprobación de la ORDEN · una sola copia para las TRES fases (mig 393)
#
# Sebastián: *"tanto fabricación, envasado como acondicionamiento, todas inician con
# una ORDEN; esa orden se le entrega al operario, y después empieza el proceso"*. La
# firma es la misma en las tres, así que el JS vive UNA vez y se inyecta (M1: tres
# copias divergen; la de acondicionamiento sería la que se quede vieja).
# ──────────────────────────────────────────────────────────────────────────

_JS_APROBACION_ORDEN = r"""
/* Firma electrónica Part 11 (§11.100/11.200): reto con contraseña -y TOTP si el
   usuario tiene MFA- y después la firma sobre ESTE legajo. Devuelve {signature_id}. */
async function _firmarOrden(meaning){
  var pwd=prompt('Firma electrónica (21 CFR Part 11) · tu contraseña para firmar:');
  if(!pwd)return null;
  var totp=prompt('Código MFA de 6 dígitos (si no usás MFA, dejalo vacío y aceptá):')||'';
  try{
    var rc=await fetch('/api/sign/challenge',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({password:pwd,totp_token:totp})});
    var dc=await rc.json();
    if(!rc.ok)return {error:(dc&&dc.error)||'Credenciales inválidas'};
    var rs=await fetch('/api/sign',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({record_table:'ebr_ejecuciones',record_id:String(EBR_ID),meaning:meaning,challenge_token:dc.token})});
    var ds=await rs.json();
    if(!rs.ok)return {error:(ds&&ds.error)||'No se pudo firmar'};
    return {signature_id:ds.signature_id};
  }catch(e){return {error:'Error de red al firmar'};}
}
/* Banda de estado de la orden. Se muestra SIEMPRE (aprobada o no): que falte la
   autorización tiene que verse en la orden que se le entrega al operario, no en un log. */
function bandaAprobacion(h,rol){
  h=h||{}; var ap=(h.aprobada_orden_por||'');
  var est=(h.estado||'').toLowerCase();
  if(ap){
    var quien=esc(ap)+(h.aprobada_orden_rol?(' &#183; '+esc(h.aprobada_orden_rol)):'');
    var cuando=h.aprobada_orden_at_utc?(' &#183; '+esc(String(h.aprobada_orden_at_utc).substring(0,16).replace("T"," "))):'';
    return '<div style="display:flex;align-items:center;gap:9px;background:var(--cx-success-pale,#f0fdf4);border:1px solid var(--cx-success-light,#86efac);color:var(--cx-success-text,#166534);border-radius:11px;padding:10px 15px;margin:0 0 16px;font-size:13px">'+
      '<span style="font-size:15px">&#10003;</span><div><b>Orden aprobada para arrancar</b> &#183; '+quien+cuando+'</div></div>';
  }
  var puede=!!(rol&&rol.puede_ejecutar)&&est!=='liberado'&&est!=='rechazado';
  return '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;background:var(--cx-warn-pale,#fffbeb);border:1px solid var(--cx-warn-light,#fcd34d);color:var(--cx-warn-text,#b45309);border-radius:11px;padding:10px 15px;margin:0 0 16px;font-size:13px">'+
    '<div style="display:flex;align-items:center;gap:9px"><span style="font-size:15px">&#9888;</span>'+
    '<div><b>Orden sin aprobar</b> &#183; nadie autorizó todavía que este lote arranque</div></div>'+
    (puede?'<button onclick="aprobarOrden()" style="padding:7px 15px;border:0;background:var(--cx-primary,#7c3aed);color:#fff;border-radius:8px;cursor:pointer;font-weight:700;font-size:12.5px;white-space:nowrap">&#9998; Aprobar orden</button>':'')+
  '</div>';
}
async function aprobarOrden(){
  if(window._apBusy)return; window._apBusy=true;                 /* doble-click = doble firma */
  try{
    if(!confirm('Vas a APROBAR esta orden para que arranque. Queda firmada con tu identidad y auditada (21 CFR Part 11). ¿Confirmás?')){return;}
    var f=await _firmarOrden('aprueba_orden');
    if(!f)return;
    if(f.error){alert('No se pudo firmar: '+f.error);return;}
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/aprobar-orden',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({signature_id:f.signature_id})});
    var dd=await r.json();
    if(!r.ok||!dd.ok){alert('No se pudo aprobar: '+((dd&&dd.error)||r.status));return;}
    load();
  }catch(e){alert('Error: '+(e.message||e));}
  finally{window._apBusy=false;}
}
"""


def _inyectar_aprobacion_orden(nombre, plantilla):
    """Mete el bloque compartido al FINAL del último <script> de la página.

    El assert no es decoración: un `.replace`/`rfind` que no matchea no falla, deja el
    original y la pantalla queda con un botón que llama a una función inexistente
    (M96/M111/M112 · es exactamente así como se desplegó Marketing con los modales
    borrados y los botones vivos)."""
    i = plantilla.rfind("</script>")
    assert i > 0, "no encontré el <script> principal de " + nombre
    return plantilla[:i] + _JS_APROBACION_ORDEN + plantilla[i:]


_ORDEN_DETALLE_HTML = _inyectar_aprobacion_orden("_ORDEN_DETALLE_HTML", _ORDEN_DETALLE_HTML)
_ENVASADO_LEGAJO_HTML = _inyectar_aprobacion_orden("_ENVASADO_LEGAJO_HTML", _ENVASADO_LEGAJO_HTML)
_ACOND_LEGAJO_HTML = _inyectar_aprobacion_orden("_ACOND_LEGAJO_HTML", _ACOND_LEGAJO_HTML)



# ──────────────────────────────────────────────────────────────────────────
# ORDENES de produccion · listado + detalle (mig 395)
#
# La orden es lo que se le entrega al operario. Esta pantalla es donde se crea, se
# aprueba (una vez para todos sus lotes) y se le adicionan lotes.
# ──────────────────────────────────────────────────────────────────────────

_ORDENES_BATCH_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Ordenes de Produccion &middot; EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{background:var(--cx-bg,#f6f7fb);color:var(--cx-text,#18181b);font-family:Inter,system-ui,-apple-system,sans-serif;margin:0}
.wrap{max-width:96vw;margin:0 auto;padding:26px 22px 60px}
.hero{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:20px}
h1{font-size:27px;font-weight:800;letter-spacing:-.5px;margin:0 0 4px}
.sub{color:var(--cx-text-soft,#475569);font-size:13.5px;margin:0}
.bt{padding:9px 17px;border:0;border-radius:10px;cursor:pointer;font-weight:700;font-size:13px;background:var(--cx-primary-grad,linear-gradient(135deg,#7c3aed,#a855f7));color:#fff;text-decoration:none;display:inline-block}
.bt.sec{background:var(--cx-border-soft,#f1f5f9);color:var(--cx-text,#18181b);border:1px solid var(--cx-border,#cbd5e1)}
.tabs{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:16px}
.tb{padding:7px 15px;border-radius:20px;border:1px solid var(--cx-border,#cbd5e1);background:var(--cx-card,#fff);cursor:pointer;font-size:12.5px;font-weight:700;color:var(--cx-text-soft,#475569)}
.tb.on{background:var(--cx-primary,#7c3aed);color:#fff;border-color:var(--cx-primary,#7c3aed)}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#e8e8ef);border-radius:15px;overflow:hidden;box-shadow:0 1px 3px rgba(16,16,24,.05)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:11px 14px;background:var(--cx-bg-alt,#f8fafc);color:var(--cx-text-soft,#475569);font-size:11.5px;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid var(--cx-border-soft,#e8e8ef)}
td{padding:12px 14px;border-bottom:1px solid var(--cx-border-soft,#f1f5f9)}
tr:last-child td{border-bottom:0}
tr:hover td{background:var(--cx-bg-alt,#f8fafc)}
.mono{font-family:ui-monospace,SFMono-Regular,monospace;font-weight:700}
.chip{display:inline-block;padding:3px 11px;border-radius:20px;font-size:11px;font-weight:800;white-space:nowrap}
.muted{color:var(--cx-text-faint,#94a3b8)}
.tw{overflow-x:auto}
</style></head><body>
<div class="wrap">
  <div class="hero">
    <div><h1>Ordenes de Produccion</h1>
    <p class="sub">La orden dice QUE y CUANTO hay que hacer, se aprueba una vez y se le entrega al operario. Cada orden agrupa uno o varios lotes.</p></div>
    <div style="display:flex;gap:8px"><button class="bt" onclick="nuevaOrden()">+ Nueva orden</button>
    <a class="bt sec" href="/inventarios">&#9198; Atras</a></div>
  </div>
  <div class="tabs" id="tabs"></div>
  <div class="card"><div class="tw"><table>
    <thead><tr><th>N&deg; de orden</th><th>Fase</th><th>Producto</th><th>Lote bulk</th><th>Cantidad</th><th>Lotes</th><th>Estado</th><th>Aprobada por</th></tr></thead>
    <tbody id="filas"><tr><td colspan="8" class="muted" style="text-align:center;padding:26px">Cargando...</td></tr></tbody>
  </table></div></div>
</div>
<script>
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function gf(n){return n==null?'&middot;':Number(n).toLocaleString('es-CO',{maximumFractionDigits:1});}
var FASE='';
var FASES=[['','Todas'],['fabricacion','Fabricacion'],['envasado','Envasado'],['acondicionamiento','Acondicionamiento']];
function pintarTabs(){
  document.getElementById('tabs').innerHTML=FASES.map(function(f){
    return '<button class="tb'+(FASE===f[0]?' on':'')+'" onclick="setFase(&#39;'+f[0]+'&#39;)">'+esc(f[1])+'</button>';}).join('');
}
function setFase(f){FASE=f;pintarTabs();cargar();}
function chipEstado(e){
  var m={borrador:['var(--cx-warn-pale,#fffbeb)','var(--cx-warn-text,#b45309)'],
         aprobada:['var(--cx-success-pale,#f0fdf4)','var(--cx-success-text,#166534)'],
         cerrada:['var(--cx-bg-alt,#f8fafc)','var(--cx-text-soft,#475569)'],
         anulada:['var(--cx-danger-pale,#fef2f2)','var(--cx-danger-text,#b91c1c)']}[e]||['var(--cx-bg-alt,#f8fafc)','var(--cx-text-soft,#475569)'];
  return '<span class="chip" style="background:'+m[0]+';color:'+m[1]+'">'+esc(e||'&middot;')+'</span>';
}
async function cargar(){
  try{
    var r=await fetch('/api/brd/ordenes'+(FASE?('?fase='+FASE):''),{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    var os=d.ordenes||[];
    document.getElementById('filas').innerHTML = os.length ? os.map(function(o){
      var apr=o.aprobada_por?esc(o.aprobada_por):'<span class="muted">sin aprobar</span>';
      if(o.exige_calidad&&o.aprobada_por){apr+=o.aprobada_calidad_por?(' + '+esc(o.aprobada_calidad_por)):' <span style="color:var(--cx-warn-text,#b45309);font-weight:700">(falta Calidad)</span>';}
      return '<tr style="cursor:pointer" onclick="location.href=&#39;/planta/orden-batch/'+o.id+'&#39;">'+
        '<td class="mono">'+esc(o.numero)+'</td>'+
        '<td>'+esc(o.fase)+'</td>'+
        '<td>'+esc(o.producto_nombre)+'</td>'+
        '<td class="mono">'+esc(o.lote_bulk||'&middot;')+'</td>'+
        '<td>'+gf(o.cantidad_g)+' g'+(o.cantidad_ml!=null?(' &middot; '+gf(o.cantidad_ml)+' mL'):'')+'</td>'+
        '<td>'+(o.n_lotes||0)+'</td>'+
        '<td>'+chipEstado(o.estado)+'</td>'+
        '<td>'+apr+'</td></tr>';
    }).join('') : '<tr><td colspan="8" class="muted" style="text-align:center;padding:26px">Todavia no hay ordenes. Crea la primera con el boton de arriba.</td></tr>';
  }catch(e){document.getElementById('filas').innerHTML='<tr><td colspan="8" style="color:var(--cx-danger-text,#b91c1c);padding:20px">Error de red: '+esc(e.message)+'</td></tr>';}
}
function nuevaOrden(){
  var ov=document.getElementById('nov');
  if(!ov){ov=document.createElement('div');ov.id='nov';ov.style.cssText='position:fixed;inset:0;background:rgba(15,23,42,.55);display:flex;align-items:center;justify-content:center;z-index:9999';document.body.appendChild(ov);}
  ov.innerHTML='<div style="background:var(--cx-card,#fff);border-radius:15px;padding:24px;max-width:560px;width:92%;box-shadow:0 10px 40px rgba(0,0,0,.3)">'+
    '<div style="font-weight:800;font-size:18px;margin-bottom:4px">Nueva orden</div>'+
    '<div style="font-size:12.5px;color:var(--cx-text-soft,#475569);margin-bottom:16px">Los lotes se le agregan despues, desde el detalle de la orden.</div>'+
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'+
      '<div><label style="font-size:12px;font-weight:600;color:var(--cx-text-soft,#475569)">Fase *</label><select id="n_fase" style="width:100%;padding:9px;border:1px solid var(--cx-border,#cbd5e1);border-radius:8px"><option value="fabricacion">Fabricacion</option><option value="envasado" selected>Envasado</option><option value="acondicionamiento">Acondicionamiento</option></select></div>'+
      '<div><label style="font-size:12px;font-weight:600;color:var(--cx-text-soft,#475569)">N&deg; lote bulk</label><input id="n_lote" style="width:100%;padding:9px;border:1px solid var(--cx-border,#cbd5e1);border-radius:8px"></div>'+
      '<div style="grid-column:1/-1"><label style="font-size:12px;font-weight:600;color:var(--cx-text-soft,#475569)">Producto *</label><input id="n_prod" placeholder="nombre exacto del producto" style="width:100%;padding:9px;border:1px solid var(--cx-border,#cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;font-weight:600;color:var(--cx-text-soft,#475569)">Cantidad (g)</label><input id="n_cant" type="number" step="0.1" style="width:100%;padding:9px;border:1px solid var(--cx-border,#cbd5e1);border-radius:8px"></div>'+
      '<div><label style="font-size:12px;font-weight:600;color:var(--cx-text-soft,#475569)">Densidad (g/mL)</label><input id="n_dens" type="number" step="0.001" style="width:100%;padding:9px;border:1px solid var(--cx-border,#cbd5e1);border-radius:8px"></div>'+
      '<div style="grid-column:1/-1"><label style="font-size:12px;font-weight:600;color:var(--cx-text-soft,#475569)">Observaciones</label><input id="n_obs" style="width:100%;padding:9px;border:1px solid var(--cx-border,#cbd5e1);border-radius:8px"></div>'+
    '</div>'+
    '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:20px">'+
      '<button class="bt sec" onclick="cerrarNueva()">Cancelar</button>'+
      '<button class="bt" id="n_ok" onclick="guardarNueva()">Crear orden</button>'+
    '</div></div>';
  ov.style.display='flex';
}
function cerrarNueva(){var o=document.getElementById('nov');if(o)o.style.display='none';}
async function guardarNueva(){
  if(window._noBusy)return; window._noBusy=true;
  var b=document.getElementById('n_ok'); if(b)b.disabled=true;
  try{
    var prod=document.getElementById('n_prod').value.trim();
    if(!prod){alert('Indica el producto de la orden.');return;}
    function n(id){var v=document.getElementById(id).value;return v===''?null:parseFloat(v);}
    var body={fase:document.getElementById('n_fase').value,producto_nombre:prod,
              lote_bulk:document.getElementById('n_lote').value,cantidad_g:n('n_cant'),
              densidad_g_ml:n('n_dens'),observaciones:document.getElementById('n_obs').value};
    var r=await fetch('/api/brd/ordenes',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(body)});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo crear: '+((d&&d.error)||r.status));return;}
    cerrarNueva(); location.href='/planta/orden-batch/'+d.id;
  }catch(e){alert('Error: '+(e.message||e));}
  finally{window._noBusy=false; if(b)b.disabled=false;}
}
pintarTabs(); cargar();
</script></body></html>"""


_ORDEN_DETALLE_BATCH_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Orden &middot; EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{background:var(--cx-bg,#f6f7fb);color:var(--cx-text,#18181b);font-family:Inter,system-ui,-apple-system,sans-serif;margin:0}
.wrap{max-width:96vw;margin:0 auto;padding:26px 22px 60px}
.ortit{font-size:27px;font-weight:800;letter-spacing:-.5px;margin:2px 0 4px}
.prod{font-size:16px;color:var(--cx-text-soft,#475569);margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:14px;background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#e8e8ef);border-radius:15px;padding:18px;margin-bottom:16px}
.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.4px;color:var(--cx-text-faint,#94a3b8);font-weight:700;margin-bottom:3px}
.val{font-size:14.5px;font-weight:700}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#e8e8ef);border-radius:15px;overflow:hidden;margin-bottom:16px}
.sechead{padding:15px 18px;border-bottom:1px solid var(--cx-border-soft,#e8e8ef);display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.sectit{font-size:15.5px;font-weight:800}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:11px 14px;background:var(--cx-bg-alt,#f8fafc);color:var(--cx-text-soft,#475569);font-size:11.5px;text-transform:uppercase;letter-spacing:.4px}
td{padding:12px 14px;border-bottom:1px solid var(--cx-border-soft,#f1f5f9)}
tr:last-child td{border-bottom:0}
.mono{font-family:ui-monospace,SFMono-Regular,monospace;font-weight:700}
.bt{padding:9px 17px;border:0;border-radius:10px;cursor:pointer;font-weight:700;font-size:13px;background:var(--cx-primary-grad,linear-gradient(135deg,#7c3aed,#a855f7));color:#fff;text-decoration:none;display:inline-block}
.bt.sec{background:var(--cx-border-soft,#f1f5f9);color:var(--cx-text,#18181b);border:1px solid var(--cx-border,#cbd5e1)}
.muted{color:var(--cx-text-faint,#94a3b8)}
.tw{overflow-x:auto}
</style></head><body>
<div class="wrap"><div id="cab"><p class="muted">Cargando...</p></div><div id="cuerpo"></div></div>
<script>
var ORDEN_ID=__ORDEN_ID__;
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function gf(n){return n==null?'&middot;':Number(n).toLocaleString('es-CO',{maximumFractionDigits:1});}
function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
function dt(s){return s?esc(String(s).substring(0,16).replace("T"," ")):'&middot;';}
function firmaLinea(tit,quien,cuando,accion,puede){
  if(quien){return '<div style="display:flex;align-items:center;gap:8px;background:var(--cx-success-pale,#f0fdf4);border:1px solid var(--cx-success-light,#86efac);color:var(--cx-success-text,#166534);border-radius:11px;padding:10px 15px;font-size:13px">'+
    '<span style="font-size:15px">&#10003;</span><div><b>'+esc(tit)+'</b> &middot; '+esc(quien)+(cuando?(' &middot; '+dt(cuando)):'')+'</div></div>';}
  return '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;background:var(--cx-warn-pale,#fffbeb);border:1px solid var(--cx-warn-light,#fcd34d);color:var(--cx-warn-text,#b45309);border-radius:11px;padding:10px 15px;font-size:13px">'+
    '<div style="display:flex;align-items:center;gap:8px"><span style="font-size:15px">&#9888;</span><div><b>'+esc(tit)+'</b> &middot; pendiente</div></div>'+
    (puede?('<button class="bt" style="padding:7px 15px;font-size:12.5px" onclick="'+accion+'">&#9998; Firmar</button>'):'')+'</div>';
}
async function _firmarOrden(meaning){
  var pwd=prompt('Firma electronica (21 CFR Part 11) &middot; tu contrasena para firmar:');
  if(!pwd)return null;
  var totp=prompt('Codigo MFA de 6 digitos (si no usas MFA, dejalo vacio y acepta):')||'';
  try{
    var rc=await fetch('/api/sign/challenge',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({password:pwd,totp_token:totp})});
    var dc=await rc.json();
    if(!rc.ok)return {error:(dc&&dc.error)||'Credenciales invalidas'};
    var rs=await fetch('/api/sign',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({record_table:'ordenes_produccion',record_id:String(ORDEN_ID),meaning:meaning,challenge_token:dc.token})});
    var ds=await rs.json();
    if(!rs.ok)return {error:(ds&&ds.error)||'No se pudo firmar'};
    return {signature_id:ds.signature_id};
  }catch(e){return {error:'Error de red al firmar'};}
}
async function _aprobar(ruta,meaning,texto){
  if(window._apBusy)return; window._apBusy=true;
  try{
    if(!confirm(texto))return;
    var f=await _firmarOrden(meaning);
    if(!f)return;
    if(f.error){alert('No se pudo firmar: '+f.error);return;}
    var r=await fetch('/api/brd/ordenes/'+ORDEN_ID+'/'+ruta,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({signature_id:f.signature_id})});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo aprobar: '+((d&&d.error)||r.status));return;}
    cargar();
  }catch(e){alert('Error: '+(e.message||e));}
  finally{window._apBusy=false;}
}
function aprobarOrden(){_aprobar('aprobar','aprueba_orden','Vas a APROBAR esta orden para que arranque. Vale para TODOS sus lotes y queda firmada con tu identidad (21 CFR Part 11). Confirmas?');}
function aprobarCalidad(){_aprobar('aprobar-calidad','aprueba_orden_calidad','Aprobacion de CALIDAD sobre la orden de acondicionamiento. Queda firmada con tu identidad. Confirmas?');}
async function adicionarLote(){
  var lote=prompt('N&deg; de lote del nuevo legajo:');
  if(!lote)return;
  try{
    var r=await fetch('/api/brd/ordenes/'+ORDEN_ID+'/adicionar-lote',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({lote:lote})});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo adicionar el lote: '+((d&&d.error)||r.status));return;}
    cargar();
  }catch(e){alert('Error: '+(e.message||e));}
}
function rutaLegajo(fase,eid){
  if(fase==='envasado')return '/planta/legajo-envasado/'+eid;
  if(fase==='acondicionamiento')return '/planta/legajo-acondicionamiento/'+eid;
  return '/planta/orden-detalle/'+eid;
}
async function cargar(){
  try{
    var r=await fetch('/api/brd/ordenes/'+ORDEN_ID,{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){document.getElementById('cab').innerHTML='<span style="color:var(--cx-danger-text,#b91c1c)">Error: '+esc(d.error||r.status)+'</span>';return;}
    var o=d.orden||{}; var rol=d.mi_rol||{};
    var puedeEd=(o.estado!=='anulada');
    document.getElementById('cab').innerHTML=
      '<div class="ortit">ORDEN N&deg;: '+esc(o.numero||'')+'</div>'+
      '<div class="prod">'+esc(o.producto_nombre||'')+' &middot; '+esc(o.fase||'')+'</div>'+
      firmaLinea('Aprobacion de Produccion',o.aprobada_por,o.aprobada_at_utc,'aprobarOrden()',puedeEd&&!!rol.puede_ejecutar)+
      (o.exige_calidad?('<div style="height:8px"></div>'+firmaLinea('Aprobacion de Calidad',o.aprobada_calidad_por,o.aprobada_calidad_at_utc,'aprobarCalidad()',puedeEd&&!!rol.puede_aprobar)):'')+
      '<div style="height:14px"></div>'+
      '<div class="grid">'+
        fld('Estado','<b>'+esc(o.estado||'')+'</b>')+
        fld('N&deg; Lote Bulk','<span class="mono">'+esc(o.lote_bulk||'&middot;')+'</span>')+
        fld('Tamano Bulk',gf(o.cantidad_g)+' g'+(o.cantidad_ml!=null?(' - '+gf(o.cantidad_ml)+' mL'):''))+
        fld('Densidad',o.densidad_g_ml?(Number(o.densidad_g_ml).toLocaleString('es-CO',{maximumFractionDigits:3})+' g/mL'):'&middot;')+
        fld('Elaborado por',esc(o.elaborado_por||o.creado_por||'&middot;'))+
        fld('Creada',dt(o.creado_at_utc))+
        '<div style="grid-column:1/-1"><div class="lbl">Observaciones</div><div class="val" style="font-weight:400">'+esc(o.observaciones||'Ninguna')+'</div></div>'+
      '</div>'+
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px">'+
        (puedeEd?'<button class="bt" onclick="adicionarLote()">+ Adicionar lote</button>':'')+
        '<a class="bt sec" href="/planta/ordenes-batch">&#9198; Todas las ordenes</a>'+
      '</div>';
    var ls=o.lotes||[];
    document.getElementById('cuerpo').innerHTML=
      '<div class="card"><div class="sechead"><div class="sectit">Lotes de la orden ('+ls.length+')</div></div>'+
      '<div class="tw"><table><thead><tr><th>N&deg; de lote</th><th>Estado</th><th>Operario</th><th>Inicio</th><th>Fin</th><th>Objetivo</th><th>Real</th></tr></thead><tbody>'+
      (ls.length?ls.map(function(l){
        return '<tr style="cursor:pointer" onclick="location.href=&#39;'+rutaLegajo(o.fase,l.ebr_id)+'&#39;">'+
          '<td class="mono">'+esc(l.lote)+'</td><td>'+esc(l.estado)+'</td><td>'+esc(l.operario||'&middot;')+'</td>'+
          '<td>'+dt(l.iniciado_at_utc)+'</td><td>'+dt(l.completado_at_utc)+'</td>'+
          '<td>'+gf(l.cantidad_objetivo_g)+' g</td><td>'+gf(l.cantidad_real_g)+' g</td></tr>';
      }).join(''):'<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">Todavia no hay lotes. Agrega el primero con "Adicionar lote".</td></tr>')+
      '</tbody></table></div></div>';
  }catch(e){document.getElementById('cab').innerHTML='<span style="color:var(--cx-danger-text,#b91c1c)">Error de red: '+esc(e.message)+'</span>';}
}
cargar();
</script></body></html>"""


@bp.route("/planta/ordenes-batch", methods=["GET"])
def ordenes_batch_page():
    """Listado de ordenes de produccion (las tres fases)."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/planta/ordenes-batch"</script>',
                        mimetype="text/html")
    return Response(_ORDENES_BATCH_HTML, mimetype="text/html")


@bp.route("/planta/orden-batch/<int:orden_id>", methods=["GET"])
def orden_batch_detalle_page(orden_id):
    """Detalle de una ORDEN madre: encabezado, sus firmas y los lotes que agrupa.

    ⚠ Esta pantalla vivía en `/planta/orden/<orden_id>`, la MISMA URL que el legajo de un lote
    (`orden_detalle_page`, declarada antes en el archivo). Werkzeug se queda con la primera, así
    que esta pantalla estaba MUERTA -- y peor: el listado "Todas las órdenes" mandaba el id de
    la ORDEN a una pantalla que lo lee como id de LEGAJO, o sea que abría el lote ajeno cuyo id
    coincidía, con cara de correcto (M200/M161). Son dos unidades de trabajo distintas (la orden
    agrupa N lotes · M117) y cada una necesita su propia URL.

    No lleva redirect desde la URL vieja: esta pantalla NUNCA se sirvió ahí, así que no hay
    marcador que rescatar; la URL vieja sigue siendo del legajo, que es quien la venía usando.
    """
    if not session.get("compras_user"):
        return Response(
            '<script>location.href="/login?next=/planta/orden-batch/%d"</script>' % orden_id,
            mimetype="text/html")
    return Response(_ORDEN_DETALLE_BATCH_HTML.replace("__ORDEN_ID__", str(orden_id)),
                    mimetype="text/html")


_INSTRUCCIONES_ENVASADO_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Instrucciones de Envasado · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.wrap{max-width:1180px;margin:0 auto}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:28px 32px;box-shadow:0 1px 3px rgba(24,24,27,.04),0 8px 24px -14px rgba(24,24,27,.10);margin-bottom:18px}
a.back{color:var(--cx-primary-text,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
.htop{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.htit{font-size:25px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.4px}
.btns{display:flex;gap:10px;flex-wrap:wrap}
.bt{padding:10px 16px;border-radius:10px;font-size:12px;font-weight:600;border:1px solid var(--cx-border,#e6e6ea);cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;background:var(--cx-bg-alt,#fbfbfd);color:var(--cx-text-soft,#3f3f46);transition:all .15s ease}
.bt:hover{border-color:var(--cx-primary,#6d28d9);color:var(--cx-primary-text,#6d28d9)}
.bt-up{background:var(--cx-primary,#6d28d9);color:#fff;border-color:transparent}.bt-up:hover{background:var(--cx-primary-dark,#4c1d95);color:#fff}
.subl{font-size:16px;color:var(--cx-text-soft,#3f3f46);font-weight:600;margin:2px 0 4px}
.prod{font-size:17px;color:var(--cx-text,#18181b);font-weight:700;margin-bottom:22px}
.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:20px}
.lbl{font-size:12.5px;font-weight:700;color:var(--cx-text-soft,#3f3f46);margin-bottom:5px}
.val{font-size:13.5px;color:var(--cx-text-mute,#71717a);line-height:1.45}
.sectit{font-size:18px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.2px;margin:0 0 12px}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.npaso{display:inline-block;min-width:20px;font-weight:800;font-variant-numeric:tabular-nums;color:var(--cx-text-mute,#6b6b74)}
.hist{font-size:11px;font-weight:700;color:var(--cx-warn-text,#b45309);background:var(--cx-warn-pale,#fffbeb);padding:2px 7px;border-radius:999px;white-space:nowrap}
.fila-hist td{opacity:.72}
.mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.sechead{display:flex;align-items:center;gap:12px;justify-content:space-between;flex-wrap:wrap;margin-bottom:6px}
.sechead .sectit{margin:0}
.sechint{font-size:13.5px;color:var(--cx-text-mute,#71717a);margin:6px 0 14px;line-height:1.5}
.btreg{padding:9px 15px;border-radius:9px;font-size:12px;font-weight:600;border:none;cursor:pointer;background:var(--cx-primary,#6d28d9);color:#fff;display:inline-flex;align-items:center;gap:6px;text-decoration:none;white-space:nowrap}.btreg:hover{background:var(--cx-primary-dark,#4c1d95)}
.tw{overflow-x:auto}
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th,table.t td{padding:12px;text-align:left;vertical-align:middle;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
table.t thead th{color:var(--cx-text-mute,#71717a);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;border-bottom:1px solid var(--cx-border,#e6e6ea)}
table.t tbody td{color:var(--cx-text-soft,#3f3f46)}
table.t tbody tr:hover td{background:var(--cx-primary-pale,#f5f3ff)}
.regfoot{color:var(--cx-text-faint,#a1a1aa);font-size:12.5px;margin-top:14px}
.ok{color:var(--cx-success-text,#15803d);font-weight:700}.no{color:var(--cx-danger-text,#dc2626);font-weight:700}.pend{color:var(--cx-text-faint,#a1a1aa)}
.bdg{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.3px}
.bdg-ok{background:var(--cx-success-pale,#f0fdf4);color:var(--cx-success-text,#15803d)}.bdg-no{background:var(--cx-danger-pale,#fef2f2);color:var(--cx-danger-text,#dc2626)}
.pasonum{font-weight:700;color:var(--cx-primary-text,#6d28d9);margin-right:5px}
.act{display:inline-flex;gap:6px}
.ab{width:30px;height:30px;border-radius:7px;border:none;cursor:pointer;color:#fff;font-size:13px;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;transition:filter .15s ease}.ab:hover{filter:brightness(1.08)}
.ab-i{background:var(--cx-info,#2563eb)}.ab-ed{background:var(--cx-warn,#f59e0b)}.ab-pdf{background:var(--cx-danger,#dc2626)}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/planta/legajo-envasado/__EBR_ID__">&larr; Orden de Envasado</a>
  <div class="card" id="cab"><div class="muted">Cargando…</div></div>
  <div id="cuerpo"></div>
</div>
<script>
var EBR_ID=__EBR_ID__;
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function dt(s){return s?esc(String(s).substring(0,16).replace('T',' ')):'·';}
function estCol(e){e=(e||'').toLowerCase();if(e.indexOf('aprob')>=0||e.indexOf('liber')>=0||e.indexOf('complet')>=0)return '#166534';if(e.indexOf('proceso')>=0)return '#0d9488';if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)return '#b91c1c';return '#475569';}
function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
async function load(){
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){document.getElementById('cab').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error: '+esc(d.error||r.status)+'</span>';return;}
    var h=d.header||{};
    var estado=h.estado||'·';
    var pres=d.envasado_presentaciones||[];
    var uds=pres.reduce(function(a,p){return a+(Number(p.unidades)||0);},0);
    document.getElementById('cab').innerHTML=
      '<div class="htop">'+
        '<div><div class="htit">INSTRUCCIONES DE ENVASADO</div>'+
          '<div style="margin-top:7px"><span style="display:inline-flex;align-items:center;gap:5px;background:var(--cx-primary-pale,#f5f3ff);color:var(--cx-primary-text,#6d28d9);font-size:12px;font-weight:700;padding:5px 12px;border-radius:20px;border:1px solid var(--cx-primary-light,#a78bfa)">&#128100; '+esc((d.mi_rol&&d.mi_rol.rol)||'Usuario')+'</span></div></div>'+
        '<div class="btns">'+
          '<a class="bt bt-tl" href="/brd/timeline/'+EBR_ID+'">&#9198; Timeline Batch Record</a>'+
          '<a class="bt bt-oe" href="/planta/legajo-envasado/'+EBR_ID+'">&#128196; Orden de Envase</a>'+
          '<a class="bt bt-dl" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">&#128196; Descargar</a>'+
          '<button class="bt bt-up" onclick="location.reload()">&#8635; Actualizar</button>'+
        '</div>'+
      '</div>'+
      '<div class="subl">'+esc(h.numero_op||('OF-'+EBR_ID))+'. Lote N°: '+esc(h.lote_codigo||'·')+'</div>'+
      '<div class="prod">'+esc(h.producto||h.titulo||'·')+(pres.length&&pres[0].presentacion?(', '+esc(pres[0].presentacion)):'')+'</div>'+
      '<div class="grid">'+
        fld('Programado por',esc(h.operario||'·'))+
        fld('Unidades',uds?uds.toLocaleString('es-CO'):'·')+
        fld('N° de Lote Bulk','<span style="font-family:ui-monospace,monospace">'+esc(h.lote_codigo||'·')+'</span>')+
        fld('Fecha Inicio',dt(h.iniciado_at_utc))+
        fld('Fecha Final',dt(h.completado_at_utc))+
        fld('Estado Actual','<b style="color:'+estCol(estado)+'">'+esc(estado)+'</b>')+
      '</div>';
    var editable=(estado==='iniciado'||estado==='en_proceso') && !!(d.mi_rol && d.mi_rol.puede_ejecutar);
    function cumpleCell(c){if(c===1)return '<span class="ok">Sí &#10003;</span>';if(c===0)return '<span class="no">No &#10007;</span>';return '<span class="pend">Pendiente</span>';}
    function regBtn(t){return editable?('<button class="btreg" onclick="prox()">+ '+t+'</button>'):'';}
    function abI(){return '<button class="ab ab-i" onclick="prox()" title="Detalle">i</button>';}
    function abEd(){return editable?'<button class="ab ab-ed" onclick="prox()" title="Registrar">&#9998;</button>':'';}
    function bdgC(c){if(c===1)return ' <span class="bdg bdg-ok">Cumple</span>';if(c===0)return ' <span class="bdg bdg-no">No cumple</span>';return '';}
    var html='';
    // Leyenda de responsabilidades (segregación de funciones GMP · diseño por roles).
    html+='<div class="card" style="padding:15px 20px"><div style="font-size:13px;color:var(--cx-text-soft,#3f3f46);line-height:1.7">'+
      '<b>Responsabilidades:</b> &nbsp;'+
      '<span style="color:var(--cx-primary-text,#6d28d9);font-weight:800">●</span> <b>Operario</b> ejecuta y registra (precauciones, despeje, recepción, envasado). &nbsp;'+
      '<span style="color:var(--cx-success-text,#15803d);font-weight:800">●</span> <b>Calidad / Aseguramiento</b> verifica los controles, corrige resultados y <b>libera el lote</b>. &nbsp;'+
      '<span style="color:var(--cx-warn-text,#f59e0b);font-weight:800">●</span> <b>Dirección Técnica</b> aprueba el MBR.'+
      '</div></div>';
    var prec=d.precauciones||[];
    html+='<div class="card"><div class="sectit">1. Precauciones</div>'+
      '<div class="sechint">Tenga en cuenta las siguientes precauciones antes de iniciar el proceso de envasado:</div>'+
      (prec.length?('<ul style="margin:0;padding-left:18px;color:var(--cx-text-soft);font-size:13.5px;line-height:1.95">'+prec.map(function(p){return '<li><b>'+(p.tipo==='equipo'?'&#128296; Equipo':'&#9888; Precaución')+':</b> '+esc(p.descripcion||'')+'</li>';}).join('')+'</ul>'):'<div class="muted">Sin precauciones registradas (se definen en el MBR).</div>')+
      '</div>';
    var dch=d.despeje_checklist||[]; window._dch=dch;
    html+='<div class="card"><div class="sectit">2. Despejes de Línea</div>'+
      '<div class="sechint">Realizar despeje en el área de acuerdo a los procedimientos internos, y realice las siguientes verificaciones:</div>'+
      (dch.length?('<div class="tw"><table class="t"><thead><tr><th>Verificación</th><th>Cumple</th><th>Acciones</th></tr></thead><tbody>'+
        dch.map(function(it,n){
          // un item RETIRADO del procedimiento (registrado antes del cambio) se sigue mostrando:
          // un registro regulado no desaparece porque el procedimiento cambie despues. Se marca y
          // no se puede registrar de nuevo.
          var marca = it.historico ? ' <span class="hist">retirado del procedimiento</span>' : '';
          var acciones = '<button class="ab ab-i" onclick="infoDespeje('+it.idx+')" title="Detalle">i</button>'
            + ((editable && !it.historico) ? '<button class="ab ab-ed" onclick="regDespeje('+it.idx+')" title="Registrar verificación">&#9998;</button>' : '');
          return '<tr'+(it.historico?' class="fila-hist"':'')+'><td><span class="npaso">'+(it.historico?'·':(n+1))+'</span> '+esc(it.texto||'')+marca+'</td><td>'+cumpleCell(it.cumple)+'</td><td><div class="act">'+acciones+'</div></td></tr>';
        }).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin verificaciones de despeje (se definen en el MBR).</div>')+
      '</div>';
    var mats=d.envasado_materiales||[];
    html+='<div class="card"><div class="sectit">3. Recepción de Material de Envase</div>'+
      '<div class="sechint">Verificar contra la orden de envasado y la etiqueta o rótulo de identificación de los siguientes materiales de envase:</div>'+
      '<div class="tw"><table class="t"><thead><tr><th>Material</th><th>N° lote</th><th>Cant. requerida</th><th>Cant. recibida</th><th>Acciones</th></tr></thead><tbody>'+
      (mats.length?mats.map(function(m){return '<tr><td>'+esc(m.material||'·')+'</td><td class="mono">'+esc(m.lote_material||m.lote_envasado||'·')+'</td><td>'+(m.requerida!=null?Number(m.requerida).toLocaleString('es-CO'):'')+'</td><td>'+(m.recibida!=null?Number(m.recibida).toLocaleString('es-CO'):'<span class="pend">pendiente</span>')+'</td><td><div class="act">'+abI()+abEd()+'</div></td></tr>';}).join('')
        :'<tr><td colspan="5" class="muted" style="text-align:center">Sin materiales registrados.</td></tr>')+
      '</tbody></table></div>'+
      '<div class="regfoot">Mostrando '+mats.length+' de '+mats.length+' registro'+(mats.length===1?'':'s')+'</div></div>';
    var pasos=d.pasos||[]; window._pasos=pasos;
    html+='<div class="card"><div class="sechead"><div class="sectit">4. Envasado</div>'+(editable?'<button class="btreg" onclick="registrarActividades()">&#10003; Registrar Actividades</button>':'')+'</div>'+
      '<div class="sechint">Realizar las siguientes actividades de acuerdo al orden establecido:</div>'+
      (pasos.length?('<div class="tw"><table class="t"><thead><tr><th>Actividad</th><th>Realizado por</th><th>Verificado por</th><th>Acciones</th></tr></thead><tbody>'+
        pasos.map(function(p,i){var ts=p.completado?('<br><span class="muted" style="font-size:11.5px">'+dt(p.completado)+'</span>'):'';return '<tr><td><span class="pasonum">Paso '+(i+1)+'.</span>'+esc(p.descripcion||'')+'</td><td>'+(p.realizado_por_full?(esc(p.realizado_por_full)+ts):'<span class="pend">·</span>')+'</td><td>'+(p.verificado_por_full?(esc(p.verificado_por_full)+ts):'<span class="pend">·</span>')+'</td><td><div class="act"><button class="ab ab-i" onclick="infoPaso('+p.orden+')" title="Detalles de la Verificación">i</button></div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin pasos de envasado (se definen en el MBR).</div>')+
      '</div>';
    var ipc=d.ipc||[];
    html+='<div class="card"><div class="sechead"><div class="sectit">5. Controles en Proceso</div>'+(editable?'<button class="btreg" onclick="prox()">+ Control de Volumen</button>':'')+'</div>'+
      '<div class="sechint">Realizar muestreo y registrar control en proceso:</div>'+
      (ipc.length?('<div class="tw"><table class="t"><thead><tr><th>Control</th><th>Resultado</th><th>Observaciones</th><th>Realizado por</th><th>Acciones</th></tr></thead><tbody>'+
        ipc.map(function(c){var res=c.conforme===2?'<span class="bdg" style="background:var(--cx-bg-alt);color:var(--cx-text-mute)">No aplica</span>':(c.resultado?(esc(c.resultado)+bdgC(c.conforme)):'<span class="pend">pendiente</span>');return '<tr><td>'+esc(c.control||'')+(c.rango?' <span class="muted" style="font-size:11px">('+esc(c.rango)+')</span>':'')+'</td><td>'+res+'</td><td>'+esc(c.observaciones||'No aplica')+'</td><td>'+(c.realizado_por?esc(c.realizado_por_full||c.realizado_por):'<span class="pend">·</span>')+'</td><td><div class="act">'+abI()+abEd()+'</div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin controles en proceso (se definen en el MBR).</div>')+
      '</div>';
    var obs=d.observaciones_proceso||[];
    html+='<div class="card"><div class="sechead"><div class="sectit">6. Observaciones Generales del Proceso</div>'+regBtn('Registrar')+'</div>'+
      (obs.length?('<div class="tw"><table class="t"><thead><tr><th>Descripción de la observación</th><th>Realizada por</th><th>Fecha y hora</th></tr></thead><tbody>'+
        obs.map(function(o){return '<tr><td>'+esc(o.descripcion||'')+'</td><td>'+esc(o.registrado_por_full||o.registrado_por||'·')+'</td><td class="muted">'+dt(o.fecha)+'</td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin observaciones registradas.</div>')+
      '</div>';
    var regs=d.registros_fisicos||[];
    html+='<div class="card"><div class="sectit">7. Registros Físicos del Proceso de Envasado</div>'+
      (regs.length?('<div class="tw"><table class="t"><thead><tr><th>Código</th><th>Descripción</th><th>Documento</th></tr></thead><tbody>'+
        regs.map(function(g){return '<tr><td class="mono">'+esc(g.id)+'</td><td>'+esc(g.descripcion||'')+'</td><td>'+(g.tiene_pdf?('<a class="ab ab-pdf" href="/api/brd/ebr/'+EBR_ID+'/registros-fisicos/'+g.id+'/pdf" target="_blank" title="Ver">&#128196;</a>'):'<span class="pend">·</span>')+'</td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin registros físicos adjuntos.</div>')+
      '</div>';
    document.getElementById('cuerpo').innerHTML=html;
  }catch(e){document.getElementById('cab').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error de red: '+esc(e.message)+'</span>';}
}
function prox(){alert('Esta acción la construimos en el siguiente paso.');}
async function regDespeje(idx){
  // Registrar la verificación de despeje (operario) · Cumple Sí/No + observación.
  // Mismo endpoint GMP que producción (e-firma/audit en el backend).
  var it=(window._dch||[]).find(function(x){return x.idx===idx;}); if(!it)return;
  var esCorr=(it.cumple!=null);
  var titulo=esCorr?'CORREGIR RESULTADO (solo Calidad / Dirección Técnica)':'REGISTRAR VERIFICACIÓN (operario)';
  var c=confirm(titulo+'\\n\\n'+it.texto+'\\n\\n¿CUMPLE? (Aceptar = Sí · Cancelar = No)');
  var obs=prompt('Observación'+(esCorr?' / motivo de la corrección':' (opcional)')+':', it.observaciones||'')||'';
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/despeje-item',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({item_idx:idx,cumple:c?1:0,observaciones:obs,etapa:'dispensacion'})});
    var d=await r.json();
    if(!r.ok){alert((r.status===403?'🔒 ':'Error: ')+(d.error||r.status));return;}
    load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
function infoDespeje(idx){
  var it=(window._dch||[]).find(function(x){return x.idx===idx;}); if(!it)return;
  var res=it.cumple===1?'Sí cumple':(it.cumple===0?'No cumple':'Pendiente');
  alert('VERIFICACIÓN DE DESPEJE\\n\\n'+it.texto+'\\n\\nResultado: '+res+(it.observaciones?('\\nObservación: '+it.observaciones):'')+(it.registrado_por?('\\nRegistrado por: '+it.registrado_por):''));
}
function infoPaso(orden){
  // Detalles de la Verificación (sección 4 · read-only). Numera 1..N dentro de la fase.
  var pasos=(window._pasos||[]);
  var i=pasos.findIndex(function(x){return x.orden===orden;}); if(i<0)return;
  var p=pasos[i];
  var est=p.completado_flag?'Completado':(p.iniciado?'En proceso':'Pendiente');
  alert('DETALLES DE LA VERIFICACIÓN\\n\\nPaso '+(i+1)+': '+p.descripcion+'\\n\\nEstado: '+est+'\\nRealizado por: '+(p.realizado_por_full||'·')+'\\nVerificado por: '+(p.verificado_por_full||'·')+(p.observaciones?('\\nObservaciones: '+p.observaciones):''));
}
async function registrarActividades(){
  // Registra (completa) la siguiente actividad pendiente · endpoint GMP con audit/e-firma.
  var pend=(window._pasos||[]).filter(function(p){return !p.completado_flag;});
  if(!pend.length){alert('Todas las actividades ya están registradas.');return;}
  var p=pend[0];
  var _i=(window._pasos||[]).findIndex(function(x){return x.orden===p.orden;});
  var obs=prompt('Registrar Paso '+(_i+1)+':\\n'+p.descripcion+'\\n\\nResultado / observación:', p.observaciones||'');
  if(obs===null)return;
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/pasos/'+p.orden+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({observaciones:obs||''})});
    var d=await r.json();
    if(!r.ok){alert((r.status===403?'🔒 ':'Error: ')+(d.error||r.status));return;}
    load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
load();
</script>
</body></html>"""


@bp.route("/planta/instrucciones-envasado/<int:ebr_id>", methods=["GET"])
def instrucciones_envasado_page(ebr_id):
    """Instrucciones de Envasado · ejecución de la presentación (abre desde el ▶ de la
    Orden de Envasado) · página propia, aislada · se construye paso a paso (9-jun-2026)."""
    if not session.get("compras_user"):
        return Response(
            f'<script>location.href="/login?next=/planta/instrucciones-envasado/{ebr_id}"</script>',
            mimetype="text/html")
    return Response(_INSTRUCCIONES_ENVASADO_HTML.replace("__EBR_ID__", str(ebr_id)),
                    mimetype="text/html")


_INSTRUCCIONES_ACOND_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Instrucciones de Acondicionamiento · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
.wrap{max-width:1180px;margin:0 auto}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:28px 32px;box-shadow:0 1px 3px rgba(24,24,27,.04),0 8px 24px -14px rgba(24,24,27,.10);margin-bottom:18px}
a.back{color:var(--cx-primary-text,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
.htop{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:16px}
.htit{font-size:25px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.4px}
.btns{display:flex;gap:10px;flex-wrap:wrap}
.bt{padding:10px 16px;border-radius:10px;font-size:12px;font-weight:600;border:1px solid var(--cx-border,#e6e6ea);cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:6px;background:var(--cx-bg-alt,#fbfbfd);color:var(--cx-text-soft,#3f3f46);transition:all .15s ease}
.bt:hover{border-color:var(--cx-primary,#6d28d9);color:var(--cx-primary-text,#6d28d9)}
.bt-up{background:var(--cx-primary,#6d28d9);color:#fff;border-color:transparent}.bt-up:hover{background:var(--cx-primary-dark,#4c1d95);color:#fff}
.subl{font-size:16px;color:var(--cx-text-soft,#3f3f46);font-weight:600;margin:2px 0 4px}
.prod{font-size:17px;color:var(--cx-text,#18181b);font-weight:700;margin-bottom:22px}
.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:20px}
.lbl{font-size:12.5px;font-weight:700;color:var(--cx-text-soft,#3f3f46);margin-bottom:5px}
.val{font-size:13.5px;color:var(--cx-text-mute,#71717a);line-height:1.45}
.sectit{font-size:18px;font-weight:800;color:var(--cx-text,#18181b);letter-spacing:-.2px;margin:0 0 12px}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.sechead{display:flex;align-items:center;gap:12px;justify-content:space-between;flex-wrap:wrap;margin-bottom:6px}
.sechead .sectit{margin:0}
.sechint{font-size:13.5px;color:var(--cx-text-mute,#71717a);margin:6px 0 14px;line-height:1.5}
.btreg{padding:9px 15px;border-radius:9px;font-size:12px;font-weight:600;border:none;cursor:pointer;background:var(--cx-primary,#6d28d9);color:#fff;display:inline-flex;align-items:center;gap:6px;text-decoration:none;white-space:nowrap}.btreg:hover{background:var(--cx-primary-dark,#4c1d95)}
.tw{overflow-x:auto}
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th,table.t td{padding:12px;text-align:left;vertical-align:middle;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
table.t thead th{color:var(--cx-text-mute,#71717a);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap;border-bottom:1px solid var(--cx-border,#e6e6ea)}
table.t tbody td{color:var(--cx-text-soft,#3f3f46)}
table.t tbody tr:hover td{background:var(--cx-primary-pale,#f5f3ff)}
.regfoot{color:var(--cx-text-faint,#a1a1aa);font-size:12.5px;margin-top:14px}
.ok{color:var(--cx-success-text,#15803d);font-weight:700}.no{color:var(--cx-danger-text,#dc2626);font-weight:700}.pend{color:var(--cx-text-faint,#a1a1aa)}
.bdg{display:inline-block;padding:2px 9px;border-radius:20px;font-size:10.5px;font-weight:800;text-transform:uppercase;letter-spacing:.3px}
.bdg-ok{background:var(--cx-success-pale,#f0fdf4);color:var(--cx-success-text,#15803d)}.bdg-no{background:var(--cx-danger-pale,#fef2f2);color:var(--cx-danger-text,#dc2626)}
.pasonum{font-weight:700;color:var(--cx-primary-text,#6d28d9);margin-right:5px}
.act{display:inline-flex;gap:6px}
.ab{width:30px;height:30px;border-radius:7px;border:none;cursor:pointer;color:#fff;font-size:13px;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;transition:filter .15s ease}.ab:hover{filter:brightness(1.08)}
.ab-i{background:var(--cx-info,#2563eb)}.ab-ed{background:var(--cx-warn,#f59e0b)}.ab-pdf{background:var(--cx-danger,#dc2626)}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/planta/legajo-acondicionamiento/__EBR_ID__">&larr; Orden de Acondicionamiento</a>
  <div class="card" id="cab"><div class="muted">Cargando…</div></div>
  <div id="cuerpo"></div>
</div>
<script>
var EBR_ID=__EBR_ID__;
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function dt(s){return s?esc(String(s).substring(0,16).replace('T',' ')):'·';}
function estCol(e){e=(e||'').toLowerCase();if(e.indexOf('aprob')>=0||e.indexOf('liber')>=0||e.indexOf('complet')>=0)return '#166534';if(e.indexOf('proceso')>=0)return '#0d9488';if(e.indexOf('rechaz')>=0||e.indexOf('cancel')>=0)return '#b91c1c';return '#475569';}
function fld(l,v){return '<div><div class="lbl">'+l+'</div><div class="val">'+v+'</div></div>';}
async function load(){
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/vista-completa',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    var d=await r.json();
    if(!r.ok){document.getElementById('cab').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error: '+esc(d.error||r.status)+'</span>';return;}
    var h=d.header||{};
    var estado=h.estado||'·';
    var pres=d.acond_presentaciones||[];
    var uds=pres.reduce(function(a,p){return a+(Number(p.unidades)||0);},0);
    document.getElementById('cab').innerHTML=
      '<div class="htop">'+
        '<div><div class="htit">INSTRUCCIONES DE ACONDICIONAMIENTO</div>'+
          '<div style="margin-top:7px"><span style="display:inline-flex;align-items:center;gap:5px;background:var(--cx-primary-pale,#f5f3ff);color:var(--cx-primary-text,#6d28d9);font-size:12px;font-weight:700;padding:5px 12px;border-radius:20px;border:1px solid var(--cx-primary-light,#a78bfa)">&#128100; '+esc((d.mi_rol&&d.mi_rol.rol)||'Usuario')+'</span></div></div>'+
        '<div class="btns">'+
          '<a class="bt bt-tl" href="/brd/timeline/'+EBR_ID+'">&#9198; Timeline Batch Record</a>'+
          '<a class="bt bt-oe" href="/planta/legajo-acondicionamiento/'+EBR_ID+'">&#128196; Orden de Acondicionamiento</a>'+
          '<a class="bt bt-dl" href="/api/brd/ebr/'+EBR_ID+'/pdf" target="_blank">&#128196; Descargar</a>'+
          '<button class="bt bt-up" onclick="location.reload()">&#8635; Actualizar</button>'+
        '</div>'+
      '</div>'+
      '<div class="subl">'+esc(h.numero_op||('OA-'+EBR_ID))+'. Lote N°: '+esc(h.lote_codigo||'·')+'</div>'+
      '<div class="prod">'+esc(h.producto||h.titulo||'·')+(pres.length&&pres[0].presentacion?(', '+esc(pres[0].presentacion)):'')+'</div>'+
      '<div class="grid">'+
        fld('Programado por',esc(h.operario||'·'))+
        fld('Unidades',uds?uds.toLocaleString('es-CO'):'·')+
        fld('N° de Lote','<span style="font-family:ui-monospace,monospace">'+esc(h.lote_codigo||'·')+'</span>')+
        fld('Fecha Inicio',dt(h.iniciado_at_utc))+
        fld('Fecha Final',dt(h.completado_at_utc))+
        fld('Estado Actual','<b style="color:'+estCol(estado)+'">'+esc(estado)+'</b>')+
      '</div>';
    var editable=(estado==='iniciado'||estado==='en_proceso') && !!(d.mi_rol && d.mi_rol.puede_ejecutar);
    function cumpleCell(c){if(c===1)return '<span class="ok">Sí &#10003;</span>';if(c===0)return '<span class="no">No &#10007;</span>';return '<span class="pend">Pendiente</span>';}
    function regBtn(t){return editable?('<button class="btreg" onclick="prox()">+ '+t+'</button>'):'';}
    function abI(){return '<button class="ab ab-i" onclick="prox()" title="Detalle">i</button>';}
    function abEd(){return editable?'<button class="ab ab-ed" onclick="prox()" title="Registrar">&#9998;</button>':'';}
    function bdgC(c){if(c===1)return ' <span class="bdg bdg-ok">Cumple</span>';if(c===0)return ' <span class="bdg bdg-no">No cumple</span>';return '';}
    var html='';
    html+='<div class="card" style="padding:15px 20px"><div style="font-size:13px;color:var(--cx-text-soft,#3f3f46);line-height:1.7">'+
      '<b>Responsabilidades:</b> &nbsp;'+
      '<span style="color:var(--cx-primary-text,#6d28d9);font-weight:800">●</span> <b>Operario</b> ejecuta y registra (despeje, recepción de empaque, etiquetado, encajado). &nbsp;'+
      '<span style="color:var(--cx-success-text,#15803d);font-weight:800">●</span> <b>Calidad / Aseguramiento</b> verifica los controles, corrige resultados y <b>libera el lote</b>. &nbsp;'+
      '<span style="color:var(--cx-warn-text,#f59e0b);font-weight:800">●</span> <b>Dirección Técnica</b> aprueba el MBR.'+
      '</div></div>';
    var prec=d.precauciones||[];
    html+='<div class="card"><div class="sectit">1. Precauciones</div>'+
      '<div class="sechint">Tenga en cuenta las siguientes precauciones antes de iniciar el proceso de acondicionamiento:</div>'+
      (prec.length?('<ul style="margin:0;padding-left:18px;color:var(--cx-text-soft);font-size:13.5px;line-height:1.95">'+prec.map(function(p){return '<li><b>'+(p.tipo==='equipo'?'&#128296; Equipo':'&#9888; Precaución')+':</b> '+esc(p.descripcion||'')+'</li>';}).join('')+'</ul>'):'<div class="muted">Sin precauciones registradas (se definen en el MBR).</div>')+
      '</div>';
    var dch=d.despeje_checklist||[]; window._dch=dch;
    html+='<div class="card"><div class="sectit">2. Despeje de Área</div>'+
      '<div class="sechint">Realizar despeje en el área de acuerdo a los procedimientos internos, y realice las siguientes verificaciones:</div>'+
      (dch.length?('<div class="tw"><table class="t"><thead><tr><th>Verificación</th><th>Cumple</th><th>Acciones</th></tr></thead><tbody>'+
        dch.map(function(it){return '<tr><td>'+esc(it.texto||'')+'</td><td>'+cumpleCell(it.cumple)+'</td><td><div class="act"><button class="ab ab-i" onclick="infoDespeje('+it.idx+')" title="Detalle">i</button>'+(editable?'<button class="ab ab-ed" onclick="regDespeje('+it.idx+')" title="Registrar verificación">&#9998;</button>':'')+'</div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin verificaciones de despeje (se definen en el MBR).</div>')+
      '</div>';
    var mats=d.acond_materiales||[];
    html+='<div class="card"><div class="sectit">3. Recepción de Material de Empaque</div>'+
      '<div class="sechint">Verificar contra la orden de acondicionamiento y la etiqueta o rótulo de identificación de los siguientes materiales de empaque (etiquetas, plegadizas, insertos):</div>'+
      '<div class="tw"><table class="t"><thead><tr><th>Material</th><th>N° lote</th><th>Cant. requerida</th><th>Cant. recibida</th><th>Acciones</th></tr></thead><tbody>'+
      (mats.length?mats.map(function(m){return '<tr><td>'+esc(m.material||'·')+'</td><td class="mono">'+esc(m.lote_material||m.lote_acond||'·')+'</td><td>'+(m.requerida!=null?Number(m.requerida).toLocaleString('es-CO'):'')+'</td><td><span class="pend">pendiente</span></td><td><div class="act">'+abI()+abEd()+'</div></td></tr>';}).join('')
        :'<tr><td colspan="5" class="muted" style="text-align:center">Sin materiales registrados.</td></tr>')+
      '</tbody></table></div>'+
      '<div class="regfoot">Mostrando '+mats.length+' de '+mats.length+' registro'+(mats.length===1?'':'s')+'</div></div>';
    var pasos=d.pasos||[]; window._pasos=pasos;
    html+='<div class="card"><div class="sechead"><div class="sectit">4. Acondicionamiento</div>'+(editable?'<button class="btreg" onclick="registrarActividades()">&#10003; Registrar Actividades</button>':'')+'</div>'+
      '<div class="sechint">Realizar las siguientes actividades de acuerdo al orden establecido:</div>'+
      (pasos.length?('<div class="tw"><table class="t"><thead><tr><th>Actividad</th><th>Realizado por</th><th>Verificado por</th><th>Acciones</th></tr></thead><tbody>'+
        pasos.map(function(p,i){var ts=p.completado?('<br><span class="muted" style="font-size:11.5px">'+dt(p.completado)+'</span>'):'';return '<tr><td><span class="pasonum">Paso '+(i+1)+'.</span>'+esc(p.descripcion||'')+'</td><td>'+(p.realizado_por_full?(esc(p.realizado_por_full)+ts):'<span class="pend">·</span>')+'</td><td>'+(p.verificado_por_full?(esc(p.verificado_por_full)+ts):'<span class="pend">·</span>')+'</td><td><div class="act"><button class="ab ab-i" onclick="infoPaso('+p.orden+')" title="Detalles de la Verificación">i</button></div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin pasos de acondicionamiento (se definen en el MBR).</div>')+
      '</div>';
    var ipc=d.ipc||[];
    html+='<div class="card"><div class="sechead"><div class="sectit">5. Controles en Proceso</div>'+(editable?'<button class="btreg" onclick="prox()">+ Control</button>':'')+'</div>'+
      '<div class="sechint">Realizar muestreo y registrar control en proceso:</div>'+
      (ipc.length?('<div class="tw"><table class="t"><thead><tr><th>Control</th><th>Resultado</th><th>Observaciones</th><th>Realizado por</th><th>Acciones</th></tr></thead><tbody>'+
        ipc.map(function(c){var res=c.conforme===2?'<span class="bdg" style="background:var(--cx-bg-alt);color:var(--cx-text-mute)">No aplica</span>':(c.resultado?(esc(c.resultado)+bdgC(c.conforme)):'<span class="pend">pendiente</span>');return '<tr><td>'+esc(c.control||'')+(c.rango?' <span class="muted" style="font-size:11px">('+esc(c.rango)+')</span>':'')+'</td><td>'+res+'</td><td>'+esc(c.observaciones||'No aplica')+'</td><td>'+(c.realizado_por?esc(c.realizado_por_full||c.realizado_por):'<span class="pend">·</span>')+'</td><td><div class="act">'+abI()+abEd()+'</div></td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin controles en proceso (se definen en el MBR).</div>')+
      '</div>';
    var obs=d.observaciones_proceso||[];
    html+='<div class="card"><div class="sechead"><div class="sectit">6. Observaciones Generales del Proceso</div>'+regBtn('Registrar')+'</div>'+
      (obs.length?('<div class="tw"><table class="t"><thead><tr><th>Descripción de la observación</th><th>Realizada por</th><th>Fecha y hora</th></tr></thead><tbody>'+
        obs.map(function(o){return '<tr><td>'+esc(o.descripcion||'')+'</td><td>'+esc(o.registrado_por_full||o.registrado_por||'·')+'</td><td class="muted">'+dt(o.fecha)+'</td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin observaciones registradas.</div>')+
      '</div>';
    var regs=d.registros_fisicos||[];
    html+='<div class="card"><div class="sectit">7. Registros Físicos del Proceso de Acondicionamiento</div>'+
      (regs.length?('<div class="tw"><table class="t"><thead><tr><th>Código</th><th>Descripción</th><th>Documento</th></tr></thead><tbody>'+
        regs.map(function(g){return '<tr><td class="mono">'+esc(g.id)+'</td><td>'+esc(g.descripcion||'')+'</td><td>'+(g.tiene_pdf?('<a class="ab ab-pdf" href="/api/brd/ebr/'+EBR_ID+'/registros-fisicos/'+g.id+'/pdf" target="_blank" title="Ver">&#128196;</a>'):'<span class="pend">·</span>')+'</td></tr>';}).join('')+
        '</tbody></table></div>'):'<div class="muted">Sin registros físicos adjuntos.</div>')+
      '</div>';
    document.getElementById('cuerpo').innerHTML=html;
  }catch(e){document.getElementById('cab').innerHTML='<span style="color:var(--cx-danger-text, #b91c1c)">Error de red: '+esc(e.message)+'</span>';}
}
function prox(){alert('Esta acción la construimos en el siguiente paso.');}
async function regDespeje(idx){
  var it=(window._dch||[]).find(function(x){return x.idx===idx;}); if(!it)return;
  var esCorr=(it.cumple!=null);
  var titulo=esCorr?'CORREGIR RESULTADO (solo Calidad / Dirección Técnica)':'REGISTRAR VERIFICACIÓN (operario)';
  var c=confirm(titulo+'\\n\\n'+it.texto+'\\n\\n¿CUMPLE? (Aceptar = Sí · Cancelar = No)');
  var obs=prompt('Observación'+(esCorr?' / motivo de la corrección':' (opcional)')+':', it.observaciones||'')||'';
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/despeje-item',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({item_idx:idx,cumple:c?1:0,observaciones:obs,etapa:'dispensacion'})});
    var d=await r.json();
    if(!r.ok){alert((r.status===403?'🔒 ':'Error: ')+(d.error||r.status));return;}
    load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
function infoDespeje(idx){
  var it=(window._dch||[]).find(function(x){return x.idx===idx;}); if(!it)return;
  var res=it.cumple===1?'Sí cumple':(it.cumple===0?'No cumple':'Pendiente');
  alert('VERIFICACIÓN DE DESPEJE\\n\\n'+it.texto+'\\n\\nResultado: '+res+(it.observaciones?('\\nObservación: '+it.observaciones):'')+(it.registrado_por?('\\nRegistrado por: '+it.registrado_por):''));
}
function infoPaso(orden){
  var pasos=(window._pasos||[]);
  var i=pasos.findIndex(function(x){return x.orden===orden;}); if(i<0)return;
  var p=pasos[i];
  var est=p.completado_flag?'Completado':(p.iniciado?'En proceso':'Pendiente');
  alert('DETALLES DE LA VERIFICACIÓN\\n\\nPaso '+(i+1)+': '+p.descripcion+'\\n\\nEstado: '+est+'\\nRealizado por: '+(p.realizado_por_full||'·')+'\\nVerificado por: '+(p.verificado_por_full||'·')+(p.observaciones?('\\nObservaciones: '+p.observaciones):''));
}
async function registrarActividades(){
  var pend=(window._pasos||[]).filter(function(p){return !p.completado_flag;});
  if(!pend.length){alert('Todas las actividades ya están registradas.');return;}
  var p=pend[0];
  var _i=(window._pasos||[]).findIndex(function(x){return x.orden===p.orden;});
  var obs=prompt('Registrar Paso '+(_i+1)+':\\n'+p.descripcion+'\\n\\nResultado / observación:', p.observaciones||'');
  if(obs===null)return;
  try{
    var r=await fetch('/api/brd/ebr/'+EBR_ID+'/pasos/'+p.orden+'/completar',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({observaciones:obs||''})});
    var d=await r.json();
    if(!r.ok){alert((r.status===403?'🔒 ':'Error: ')+(d.error||r.status));return;}
    load();
  }catch(e){alert('Error de red: '+(e.message||e));}
}
load();
</script>
</body></html>"""


@bp.route("/planta/instrucciones-acondicionamiento/<int:ebr_id>", methods=["GET"])
def instrucciones_acondicionamiento_page(ebr_id):
    """Instrucciones de Acondicionamiento (OA) · ejecución (abre desde el ▶ de la Orden
    de Acondicionamiento) · página propia, aislada · espeja envasado (10-jun-2026)."""
    if not session.get("compras_user"):
        return Response(
            f'<script>location.href="/login?next=/planta/instrucciones-acondicionamiento/{ebr_id}"</script>',
            mimetype="text/html")
    return Response(_INSTRUCCIONES_ACOND_HTML.replace("__EBR_ID__", str(ebr_id)),
                    mimetype="text/html")


@bp.route("/api/brd/analitica-lotes", methods=["GET"])
def analitica_lotes():
    """Analítica operativa del batch (gerencia + Dirección Técnica): tiempo de ciclo, duración
    de procedimientos (cuellos de botella), rendimiento, productividad · derivado de los
    timestamps que el EBR YA captura (no inventa nada). Solo Dir.Téc/Calidad/Admin · 9-jun-2026."""
    err = _require_login()
    if err:
        return err
    u = session.get("compras_user", "")
    if u not in ADMIN_USERS:
        return jsonify({"error": "Privado · solo Gerencia / Dirección"}), 403
    from datetime import datetime as _DT

    def _pd(s):
        if not s:
            return None
        try:
            return _DT.fromisoformat(str(s).strip().replace('Z', '').replace(' ', 'T', 1)[:26])
        except Exception:
            return None

    def _horas(a, b):
        da, db = _pd(a), _pd(b)
        if not da or not db:
            return None
        h = (db - da).total_seconds() / 3600.0
        return h if h >= 0 else None

    def _avg(xs):
        return round(sum(xs) / len(xs), 2) if xs else None

    conn = get_db()
    try:
        lotes = conn.execute(
            """SELECT e.id, COALESCE(e.fase,'fabricacion') AS fase,
                      COALESCE(m.producto_nombre,'') AS producto, COALESCE(e.estado,'') AS estado,
                      e.iniciado_at_utc, e.completado_at_utc, e.liberado_at_utc,
                      e.yield_pct, COALESCE(e.cantidad_objetivo_g,0) AS obj, e.cantidad_real_g
                 FROM ebr_ejecuciones e
                 LEFT JOIN mbr_templates m ON m.id = e.mbr_template_id""").fetchall()
    except Exception:
        lotes = []
    estados, ciclo_fase, rend_prod, libera = {}, {}, {}, []
    for r in lotes:
        d = dict(r)
        est = (d.get('estado') or '').lower()
        estados[est] = estados.get(est, 0) + 1
        c = _horas(d.get('iniciado_at_utc'), d.get('completado_at_utc'))
        if c is not None:
            ciclo_fase.setdefault(d.get('fase') or 'fabricacion', []).append(c)
        y = d.get('yield_pct')
        if y is None and d.get('obj') and d.get('cantidad_real_g'):
            try:
                y = float(d['cantidad_real_g']) / float(d['obj']) * 100
            except Exception:
                y = None
        if y is not None:
            rend_prod.setdefault(d.get('producto') or '·', []).append(float(y))
        lh = _horas(d.get('completado_at_utc'), d.get('liberado_at_utc'))
        if lh is not None:
            libera.append(lh)
    try:
        pasos = conn.execute(
            """SELECT p.descripcion, COALESCE(p.operario_username,'') AS operario,
                      p.iniciado_at_utc, p.completado_at_utc
                 FROM ebr_pasos_ejecutados p
                WHERE p.completado_at_utc IS NOT NULL""").fetchall()
    except Exception:
        pasos = []
    cuellos, prod_op = {}, {}
    for r in pasos:
        d = dict(r)
        m = _horas(d.get('iniciado_at_utc'), d.get('completado_at_utc'))
        if m is not None:
            cuellos.setdefault((d.get('descripcion') or '·')[:70], []).append(m * 60.0)
        op = d.get('operario') or ''
        if op:
            prod_op[op] = prod_op.get(op, 0) + 1
    return jsonify({
        'ok': True,
        'resumen': {
            'total': len(lotes),
            'en_proceso': sum(v for k, v in estados.items() if k in ('iniciado', 'en_proceso')),
            'completados': estados.get('completado', 0) + estados.get('en_revision_qc', 0),
            'liberados': estados.get('liberado', 0),
            'rechazados': estados.get('rechazado', 0),
        },
        'ciclo_por_fase': sorted(
            [{'fase': f, 'lotes': len(v), 'ciclo_horas_prom': _avg(v)} for f, v in ciclo_fase.items()],
            key=lambda x: -(x['ciclo_horas_prom'] or 0)),
        'cuellos': sorted(
            [{'paso': p, 'n': len(v), 'duracion_min_prom': _avg(v)} for p, v in cuellos.items()],
            key=lambda x: -(x['duracion_min_prom'] or 0))[:10],
        'rendimiento': sorted(
            [{'producto': p, 'lotes': len(v), 'yield_prom': _avg(v)} for p, v in rend_prod.items()],
            key=lambda x: -(x['yield_prom'] or 0))[:12],
        'productividad': sorted(
            [{'operario': o, 'pasos': n} for o, n in prod_op.items()], key=lambda x: -x['pasos'])[:12],
        'completar_a_liberar_horas_prom': _avg(libera),
    })


_ANALITICA_BATCH_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Analítica del Batch · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;font-variant-numeric:tabular-nums}
/* 96vw = la regla de EOS para los modulos. Estaban clavadas en 1100-1200px: en un monitor de 1990 dejaban el 40% en blanco y la tabla de materiales -7 columnas- se desbordaba cortando 'Diferencia'. La orden madre ya usaba 96vw; se alinean las de DATOS. Los dos INSTRUCTIVOS quedan angostos a proposito: son formatos que se leen y se imprimen. */.wrap{max-width:96vw;margin:0 auto}
a.back{color:var(--cx-primary-text,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
h1{font-size:24px;font-weight:800;letter-spacing:-.4px;margin:8px 0 2px}
.sub{color:var(--cx-text-mute,#71717a);font-size:13px;margin-bottom:20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin-bottom:22px}
.kpi{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:18px 20px;box-shadow:0 1px 3px rgba(24,24,27,.04)}
.kpi .v{font-size:27px;font-weight:800;color:var(--cx-text,#18181b)}
.kpi .l{font-size:11.5px;font-weight:700;color:var(--cx-text-mute,#71717a);text-transform:uppercase;letter-spacing:.4px;margin-top:2px}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:22px 26px;box-shadow:0 1px 3px rgba(24,24,27,.04);margin-bottom:18px}
.sectit{font-size:16px;font-weight:800;color:var(--cx-text,#18181b);margin:0 0 3px}
.sechint{font-size:12.5px;color:var(--cx-text-mute,#71717a);margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:11px 12px;text-align:left;border-bottom:1px solid var(--cx-border-soft,#f1f1f4)}
th{color:var(--cx-text-mute,#71717a);font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:700}
td{color:var(--cx-text-soft,#3f3f46)}
.num{text-align:right;font-weight:700}
.bar{height:8px;border-radius:6px;background:var(--cx-primary,#6d28d9);display:inline-block;vertical-align:middle}
.bartrk{background:var(--cx-primary-pale,#f5f3ff);border-radius:6px;width:122px;display:inline-block;vertical-align:middle;margin-right:8px}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:820px){.cols{grid-template-columns:1fr}}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/gerencia">&larr; Gerencia</a>
  <h1>&#128202; Analítica del Batch</h1>
  <div class="sub">&#128274; Privado &middot; Gerencia &nbsp;-&nbsp; tiempos, rendimiento y productividad, derivado de los registros de lote (EBR) en vivo.</div>
  <div id="cont"><div class="muted">Cargando&hellip;</div></div>
</div>
<script>
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function nf(n,dec){return n==null?'·':Number(n).toLocaleString('es-CO',{maximumFractionDigits:dec==null?1:dec});}
function kpi(v,l){return '<div class="kpi"><div class="v">'+(typeof v==='number'?nf(v,0):esc(v))+'</div><div class="l">'+l+'</div></div>';}
function tbl(heads,rows){var h='<table><thead><tr>';heads.forEach(function(x,i){h+='<th'+(i>0?' class="num"':'')+'>'+esc(x)+'</th>';});h+='</tr></thead><tbody>';
  if(!rows.length){h+='<tr><td colspan="'+heads.length+'" class="muted">Sin datos aún.</td></tr>';}
  else{rows.forEach(function(r){h+='<tr>';r.forEach(function(c,i){h+='<td'+(i>0?' class="num"':'')+'>'+(c==null?'·':esc(c))+'</td>';});h+='</tr>';});}
  return h+'</tbody></table>';}
async function load(){
  try{
    var r=await fetch('/api/brd/analitica-lotes',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    if(r.status===403){document.getElementById('cont').innerHTML='<div class="card">&#128274; Privado · solo Gerencia / Dirección.</div>';return;}
    var d=await r.json();
    if(!d.ok){document.getElementById('cont').innerHTML='<div class="card" style="color:var(--cx-danger-text, #b91c1c)">Error</div>';return;}
    var R=d.resumen||{};
    var h='<div class="kpis">'+
      kpi(R.total,'Lotes totales')+kpi(R.en_proceso,'En proceso')+kpi(R.completados,'Completados')+
      kpi(R.liberados,'Liberados')+kpi(R.rechazados,'Rechazados')+
      kpi(d.completar_a_liberar_horas_prom!=null?(nf(d.completar_a_liberar_horas_prom)+' h'):'·','Completar→Liberar')+
    '</div>';
    h+='<div class="cols">';
    h+='<div class="card"><div class="sectit">&#9201;&#65039; Tiempo de ciclo por fase</div><div class="sechint">Horas promedio de inicio a completado.</div>'+
      tbl(['Fase','Lotes','Horas prom'],(d.ciclo_por_fase||[]).map(function(x){return [x.fase,x.lotes,nf(x.ciclo_horas_prom)+' h'];}))+'</div>';
    h+='<div class="card"><div class="sectit">&#128200; Rendimiento (yield) por producto</div><div class="sechint">% real vs objetivo · ¿se pierde granel?</div>'+
      tbl(['Producto','Lotes','Yield prom'],(d.rendimiento||[]).map(function(x){return [x.producto,x.lotes,nf(x.yield_prom)+'%'];}))+'</div>';
    h+='</div>';
    var cu=d.cuellos||[]; var maxc=cu.length?Math.max.apply(null,cu.map(function(x){return x.duracion_min_prom||0;})):1;
    h+='<div class="card"><div class="sectit">&#128269; Cuellos de botella · duración por procedimiento</div><div class="sechint">Los pasos que más tardan (minutos promedio). Ahí se pierde tiempo.</div>'+
      '<table><thead><tr><th>Procedimiento</th><th class="num">Veces</th><th>Duración prom</th></tr></thead><tbody>'+
      (cu.length?cu.map(function(x){var w=Math.round((x.duracion_min_prom||0)/(maxc||1)*120);return '<tr><td>'+esc(x.paso)+'</td><td class="num">'+x.n+'</td><td><span class="bartrk"><span class="bar" style="width:'+w+'px"></span></span>'+nf(x.duracion_min_prom)+' min</td></tr>';}).join(''):'<tr><td colspan="3" class="muted">Sin pasos con tiempos aún.</td></tr>')+
      '</tbody></table></div>';
    h+='<div class="card"><div class="sectit">&#128119; Productividad por operario</div><div class="sechint">Pasos ejecutados (registrados).</div>'+
      tbl(['Operario','Pasos'],(d.productividad||[]).map(function(x){return [x.operario,x.pasos];}))+'</div>';
    document.getElementById('cont').innerHTML=h;
  }catch(e){document.getElementById('cont').innerHTML='<div class="card" style="color:var(--cx-danger-text, #b91c1c)">Error de red: '+esc(e.message)+'</div>';}
}
load();
</script>
</body></html>"""


@bp.route("/planta/analitica-batch", methods=["GET"])
def analitica_batch_page():
    """Tablero de analítica del batch (gerencia / Dirección Técnica) · premium · 9-jun-2026."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/planta/analitica-batch"</script>',
                        mimetype="text/html")
    return Response(_ANALITICA_BATCH_HTML, mimetype="text/html")


@bp.route("/api/brd/mbr/<int:mbr_id>/aprobar-rapido", methods=["POST"])
def aprobar_mbr_rapido(mbr_id):
    """Aprueba un MBR en_revision con la e-firma del usuario (Bandeja DT · 9-jun). Solo
    Calidad/Dir.Téc/Admin. Crea firma 'aprueba' + estado=aprobado + audit."""
    err = _require_qa_or_admin()
    if err:
        return err
    conn = get_db(); cur = conn.cursor()
    user = session.get("compras_user", "")
    row = cur.execute("SELECT estado FROM mbr_templates WHERE id=?", (mbr_id,)).fetchone()
    if not row:
        return jsonify({"ok": False, "error": "MBR no encontrado"}), 404
    est = (row[0] if not hasattr(row, 'keys') else row['estado'])
    if est != 'en_revision':
        return jsonify({"ok": False, "error": f"solo en_revision puede aprobarse (actual: {est})"}), 409
    try:
        from blueprints.firmas import crear_firma_directa
    except Exception:
        from api.blueprints.firmas import crear_firma_directa
    sig_id = crear_firma_directa(conn, username=user, record_table="mbr_templates",
                                 record_id=str(mbr_id), meaning="aprueba",
                                 comment="Aprobación desde bandeja DT")
    cur.execute("""UPDATE mbr_templates SET estado='aprobado', aprobado_por=?,
                     aprobado_at_utc=datetime('now','utc'), aprobado_signature_id=?
                   WHERE id=? AND estado='en_revision'""", (user, sig_id, mbr_id))
    # FIX 7-jul (audit ultracode · M27 CAS): estado en el WHERE + rowcount (aprobar vs obsoletar concurrente ·
    # mismo riesgo que motivó el fix del canónico aprobar_mbr).
    if cur.rowcount == 0:
        conn.rollback()
        return jsonify({"ok": False, "error": "El MBR cambió de estado · refrescá", "codigo": "ESTADO_CAMBIO"}), 409
    audit_log(cur, usuario=user, accion="APROBAR_MBR", tabla="mbr_templates",
              registro_id=mbr_id, antes={"estado": "en_revision"},
              despues={"estado": "aprobado", "signature_id": sig_id})
    conn.commit()
    return jsonify({"ok": True, "estado": "aprobado"})


@bp.route("/api/brd/bandeja-dt", methods=["GET"])
def bandeja_dt():
    """Bandeja del Director Técnico / Calidad: decisiones que requieren su firma · MBRs por
    aprobar + lotes por liberar (9-jun). Solo Dir.Téc/Calidad/Admin."""
    err = _require_login()
    if err:
        return err
    u = session.get("compras_user", "")
    if u not in ADMIN_USERS and u not in CALIDAD_USERS:
        return jsonify({"error": "solo Dirección Técnica / Calidad / Admin"}), 403
    conn = get_db()
    try:
        mbrs = conn.execute(
            "SELECT id, COALESCE(producto_nombre,'') AS producto, COALESCE(version,1) AS version, "
            "COALESCE(creado_por,'') AS creado_por FROM mbr_templates "
            "WHERE estado='en_revision' ORDER BY id DESC LIMIT 100").fetchall()
    except Exception:
        mbrs = []
    try:
        lotes = conn.execute(
            "SELECT e.id, COALESCE(e.numero_op,'') AS numero_op, COALESCE(e.lote,'') AS lote, "
            "COALESCE(e.fase,'fabricacion') AS fase, COALESCE(m.producto_nombre,'') AS producto, "
            "COALESCE(e.completado_at_utc,'') AS completado_at FROM ebr_ejecuciones e "
            "LEFT JOIN mbr_templates m ON m.id=e.mbr_template_id "
            "WHERE COALESCE(e.estado,'') IN ('completado','en_revision_qc') "
            "ORDER BY e.completado_at_utc DESC LIMIT 100").fetchall()
    except Exception:
        lotes = []
    return jsonify({"ok": True,
                    "mbr_pendientes": [dict(r) for r in mbrs],
                    "lotes_por_liberar": [dict(r) for r in lotes]})


_BANDEJA_DT_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Bandeja · Dirección Técnica · EOS</title>
<link rel="stylesheet" href="/static/cortex.css">
<style>
body{font-family:var(--cx-font,'Inter',system-ui,sans-serif);background:var(--cx-bg,#f4f4f7);color:var(--cx-text,#18181b);margin:0;padding:24px;font-variant-numeric:tabular-nums}
/* 96vw = la regla de EOS para los modulos. Estaban clavadas en 1100-1200px: en un monitor de 1990 dejaban el 40% en blanco y la tabla de materiales -7 columnas- se desbordaba cortando 'Diferencia'. La orden madre ya usaba 96vw; se alinean las de DATOS. Los dos INSTRUCTIVOS quedan angostos a proposito: son formatos que se leen y se imprimen. */.wrap{max-width:96vw;margin:0 auto}
a.back{color:var(--cx-primary-text,#6d28d9);font-size:13px;font-weight:600;text-decoration:none}
h1{font-size:24px;font-weight:800;letter-spacing:-.4px;margin:8px 0 2px}
.sub{color:var(--cx-text-mute,#71717a);font-size:13px;margin-bottom:20px}
.card{background:var(--cx-card,#fff);border:1px solid var(--cx-border-soft,#f1f1f4);border-radius:14px;padding:22px 26px;box-shadow:0 1px 3px rgba(24,24,27,.04);margin-bottom:18px}
.sectit{font-size:17px;font-weight:800;color:var(--cx-text,#18181b);margin:0 0 3px}
.sectit .badge{font-size:12px;background:var(--cx-warn-pale,#fffbeb);color:var(--cx-warn-text,#f59e0b);font-weight:800;padding:2px 10px;border-radius:20px;margin-left:8px;vertical-align:middle}
.sechint{font-size:12.5px;color:var(--cx-text-mute,#71717a);margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{padding:12px;text-align:left;border-bottom:1px solid var(--cx-border-soft,#f1f1f4);vertical-align:middle}
th{color:var(--cx-text-mute,#71717a);font-size:11px;text-transform:uppercase;letter-spacing:.5px;font-weight:700}
td{color:var(--cx-text-soft,#3f3f46)}
.mono{font-family:var(--cx-font-mono,ui-monospace,monospace)}
.muted{color:var(--cx-text-faint,#a1a1aa)}
.bt{padding:8px 15px;border-radius:9px;font-size:12.5px;font-weight:600;border:none;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:5px;color:#fff}
.bt-ap{background:var(--cx-success,#15803d)}.bt-ver{background:var(--cx-primary,#6d28d9)}
</style></head>
<body>
<div class="wrap">
  <a class="back" href="/inventarios">&larr; Planta</a>
  <h1>&#128203; Bandeja &middot; Dirección Técnica</h1>
  <div class="sub">Decisiones que requieren tu firma &middot; aprobar procedimientos (MBR) y liberar lotes.</div>
  <div style="margin:-6px 0 16px"><a href="/calidad/expediente" style="display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:700;color:var(--cx-primary-text, #6d28d9);text-decoration:none;border:1px solid #e9d5ff;background:var(--cx-card, #fff);border-radius:10px;padding:8px 14px" title="Expediente por lote: todos los documentos regulados de un lote (F01, F02, COA, rótulo, batch record) para auditoría INVIMA">&#128193; Expediente por lote</a></div>
  <div id="cont"><div class="muted">Cargando&hellip;</div></div>
</div>
<script>
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function dt(s){return s?esc(String(s).substring(0,16).replace('T',' ')):'·';}
async function load(){
  try{
    var r=await fetch('/api/brd/bandeja-dt',{credentials:'same-origin',cache:'no-store'});
    if(r.status===401){location.href='/login';return;}
    if(r.status===403){document.getElementById('cont').innerHTML='<div class="card">Solo Dirección Técnica / Calidad / Admin.</div>';return;}
    var d=await r.json();
    var mbr=d.mbr_pendientes||[], lot=d.lotes_por_liberar||[];
    var h='<div class="card"><div class="sectit">&#128221; MBR por aprobar'+(mbr.length?'<span class="badge">'+mbr.length+'</span>':'')+'</div>'+
      '<div class="sechint">Procedimientos maestros en revisión esperando tu aprobación (e-firma).</div>'+
      '<table><thead><tr><th>Producto</th><th>Versión</th><th>Creado por</th><th>Acción</th></tr></thead><tbody>'+
      (mbr.length?mbr.map(function(m){return '<tr><td>'+esc(m.producto)+'</td><td>v'+esc(m.version)+'</td><td>'+esc(m.creado_por||'·')+'</td><td><button class="bt bt-ap" onclick="aprobar('+m.id+',this)">&#10003; Aprobar</button></td></tr>';}).join(''):'<tr><td colspan="4" class="muted">Nada pendiente de aprobar.</td></tr>')+
      '</tbody></table></div>';
    h+='<div class="card"><div class="sectit">&#128275; Lotes por liberar'+(lot.length?'<span class="badge">'+lot.length+'</span>':'')+'</div>'+
      '<div class="sechint">Lotes completados esperando liberación de Calidad/Dirección Técnica.</div>'+
      '<table><thead><tr><th>N&deg; orden</th><th>Producto</th><th>N&deg; lote</th><th>Fase</th><th>Completado</th><th>Acción</th></tr></thead><tbody>'+
      (lot.length?lot.map(function(l){var url=(l.fase==='envasado'?'/planta/legajo-envasado/':'/planta/orden/')+l.id;return '<tr><td class="mono">'+esc(l.numero_op||('EBR-'+l.id))+'</td><td>'+esc(l.producto)+'</td><td class="mono">'+esc(l.lote)+'</td><td>'+esc(l.fase)+'</td><td class="muted">'+dt(l.completado_at)+'</td><td><a class="bt bt-ver" href="'+url+'">Abrir &amp; liberar &rarr;</a></td></tr>';}).join(''):'<tr><td colspan="6" class="muted">Ningún lote esperando liberación.</td></tr>')+
      '</tbody></table></div>';
    document.getElementById('cont').innerHTML=h;
  }catch(e){document.getElementById('cont').innerHTML='<div class="card" style="color:var(--cx-danger-text, #b91c1c)">Error de red: '+esc(e.message)+'</div>';}
}
async function aprobar(id,btn){
  if(!confirm('¿Aprobar este MBR con tu firma electrónica? (queda auditado · Part 11)'))return;
  btn.disabled=true; btn.textContent='Aprobando…';
  try{
    var r=await fetch('/api/brd/mbr/'+id+'/aprobar-rapido',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:'{}'});
    var d=await r.json();
    if(!r.ok||!d.ok){alert('No se pudo aprobar: '+((d&&d.error)||r.status));btn.disabled=false;btn.textContent='Aprobar';return;}
    load();
  }catch(e){alert('Error: '+(e.message||e));btn.disabled=false;btn.textContent='Aprobar';}
}
load();
</script>
</body></html>"""


@bp.route("/planta/bandeja-dt", methods=["GET"])
def bandeja_dt_page():
    """Bandeja de Dirección Técnica · decisiones pendientes · premium · 9-jun-2026."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/planta/bandeja-dt"</script>',
                        mimetype="text/html")
    return Response(_BANDEJA_DT_HTML, mimetype="text/html")


@bp.route("/brd/despeje/<int:ebr_id>", methods=["GET"])
def despeje_imprimible(ebr_id):
    """Formato IMPRIMIBLE del Despeje de Línea - Dispensación (MyBatch: el ícono
    PDF junto al título). Registro GMP con las 13 verificaciones, CUMPLE,
    responsable, fecha y firmas. Server-side (sin JS) · Ctrl+P o auto-print.
    Sebastián 6-jun-2026."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/brd/despeje/' + str(ebr_id) + '"</script>',
                        mimetype="text/html")
    etapa = (request.args.get("etapa") or "dispensacion").strip().lower()
    if etapa not in ("dispensacion", "fabricacion"):
        etapa = "dispensacion"
    etapa_label = "FABRICACIÓN" if etapa == "fabricacion" else "DISPENSACIÓN"
    etapa_area = "fabricación" if etapa == "fabricacion" else "dispensación"
    conn = get_db()
    import html as _h
    # Cabecera del legajo
    hdr = {}
    try:
        row = conn.execute(
            "SELECT COALESCE(lote,''), COALESCE(numero_op,''), COALESCE(area_codigo,''), "
            "mbr_template_id, COALESCE(estado,''), COALESCE(iniciado_at_utc,'') "
            "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        if row:
            hdr = {'lote': row[0], 'numero_op': row[1], 'area_codigo': row[2],
                   'mbr': row[3], 'estado': row[4], 'iniciado': row[5]}
    except Exception:
        hdr = {}
    producto = ''
    try:
        if hdr.get('mbr'):
            mr = conn.execute("SELECT producto_nombre FROM mbr_templates WHERE id=?", (hdr['mbr'],)).fetchone()
            producto = (mr[0] if mr else '') or ''
    except Exception:
        pass
    area = hdr.get('area_codigo', '')
    try:
        if area:
            ar = conn.execute("SELECT nombre FROM areas_planta WHERE codigo=?", (area,)).fetchone()
            if ar and ar[0]:
                area = str(ar[0]) + ' (' + hdr['area_codigo'] + ')'
    except Exception:
        pass
    def _cumple_txt(c):
        if c == 1:
            return '<span style="color:var(--cx-success-text, #166534);font-weight:800">Sí</span>'
        if c == 0:
            return '<span style="color:var(--cx-danger-text, #b91c1c);font-weight:800">No</span>'
        return '<span style="color:var(--cx-text-faint, #94a3b8)">·</span>'

    filas = []
    for n, f in enumerate(despeje_checklist(conn, ebr_id, etapa), start=1):
        fecha = (f['fecha'][:16].replace('T', ' ') if f['fecha'] else '')
        # un ítem retirado del procedimiento se imprime igual (el registro no se borra) y se marca
        marca = ' <span class="hist">(retirado del procedimiento)</span>' if f['historico'] else ''
        filas.append(
            '<tr><td class="n">' + str(n) + '</td>'
            '<td>' + _h.escape(f['texto']) + marca + '</td>'
            '<td class="c">' + _cumple_txt(f['cumple']) + '</td>'
            '<td class="c">' + _h.escape(f['registrado_por']) + '</td>'
            '<td class="c">' + _h.escape(fecha) + '</td>'
            '<td>' + _h.escape(f['observaciones']) + '</td></tr>')
    filas_html = ''.join(filas)
    e = _h.escape
    html = (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<title>Despeje de Línea · ' + e(hdr.get('numero_op') or str(ebr_id)) + '</title>'
        '<style>'
        '@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap");'
        '*{box-sizing:border-box;font-family:"Inter",system-ui,Arial,sans-serif}'
        'body{margin:0;background:#f4f4f7;color:#18181b;padding:28px;-webkit-font-smoothing:antialiased}'
        '.sheet{max-width:980px;margin:0 auto;background:var(--cx-card, #fff);padding:30px 34px;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.08)}'
        '.topacc{height:5px;margin:-30px -34px 16px;background:linear-gradient(90deg,#a78bfa,#6d28d9)}'
        '.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e4e4e7;padding-bottom:14px;margin-bottom:16px}'
        '.top h1{font-size:18px;margin:0;letter-spacing:.5px}'
        '.top .co{font-size:13px;font-weight:700;color:var(--cx-text-soft, #334155)}'
        '.meta{display:grid;grid-template-columns:repeat(3,1fr);gap:8px 18px;font-size:12.5px;margin-bottom:16px}'
        '.meta b{color:var(--cx-text-mute, #64748b);font-weight:700;display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.3px}'
        '.intro{font-size:12.5px;color:var(--cx-text-soft, #334155);margin-bottom:10px}'
        'table{width:100%;border-collapse:collapse;font-size:12px}'
        'th{background:var(--cx-primary-pale, #f5f3ff);color:var(--cx-primary-text, #4c1d95);padding:9px 10px;text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.3px;font-weight:700}'
        'td{padding:8px;border-bottom:1px solid var(--cx-border, #e2e8f0);vertical-align:top}'
        'td.n{text-align:center;color:var(--cx-text-faint, #94a3b8);width:26px}td.c{text-align:center;white-space:nowrap}'
        '.firmas{display:grid;grid-template-columns:repeat(3,1fr);gap:30px;margin-top:42px;font-size:12px}'
        '.firma{text-align:center}.firma .ln{border-top:1px solid var(--cx-text, #0f172a);margin-bottom:5px;padding-top:5px}'
        '.no-print{text-align:center;margin:16px 0}'
        '.btn{background:var(--cx-primary, #7c3aed);color:#fff;border:none;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:700;cursor:pointer}'
        '@media print{.no-print{display:none}body{background:var(--cx-card, #fff);padding:0}.sheet{box-shadow:none;border-radius:0}}'
        '</style></head><body>'
        '<div class="no-print"><button class="btn" onclick="window.print()">🖨 Imprimir / Guardar PDF</button></div>'
        '<div class="sheet">'
        '<div class="topacc"></div>'
        '<div class="top"><div><h1>DESPEJE DE LÍNEA · ' + etapa_label + '</h1>'
        '<div style="font-size:11px;color:#71717a;margin-top:3px">Registro de verificación previo a fabricación · BPM / INVIMA · 21 CFR Part 11</div></div>'
        '<div class="co" style="display:flex;align-items:center;gap:10px"><span style="width:38px;height:38px;border-radius:11px;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#a78bfa,#6d28d9);box-shadow:0 4px 12px rgba(109,40,217,.2)"><svg viewBox="0 0 32 32" width="22" height="22" fill="none" stroke="#fff"><circle cx="16" cy="12" r="3" fill="#fff"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.6" stroke-linecap="round" opacity=".7"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.6" stroke-linecap="round" opacity=".4"/></svg></span><div style="text-align:left;line-height:1.2">ESPAGIRIA Laboratorio SAS<br><span style="font-weight:400;color:#71717a;font-size:11px">ÁNIMUS Lab</span></div></div></div>'
        '<div class="meta">'
        '<div><b>Orden de Producción</b>' + e(hdr.get('numero_op') or ('EBR-' + str(ebr_id))) + '</div>'
        '<div><b>N° de Lote Bulk</b>' + e(hdr.get('lote') or '·') + '</div>'
        '<div><b>Producto</b>' + e(producto or '·') + '</div>'
        '<div><b>Área o Línea</b>' + e(area or '·') + '</div>'
        '<div><b>Estado</b>' + e(hdr.get('estado') or '·') + '</div>'
        '<div><b>Fecha</b>' + e((hdr.get('iniciado') or '')[:16].replace('T', ' ') or '·') + '</div>'
        '</div>'
        '<div class="intro">Realizar despeje en el área de ' + etapa_area + ' de acuerdo a los procedimientos internos, y realice las siguientes verificaciones:</div>'
        '<table><thead><tr><th>#</th><th>Verificación</th><th style="text-align:center">Cumple</th>'
        '<th style="text-align:center">Responsable</th><th style="text-align:center">Fecha</th><th>Observación</th></tr></thead>'
        '<tbody>' + filas_html + '</tbody></table>'
        '<div class="firmas">'
        '<div class="firma"><div class="ln">&nbsp;</div>Realizó (Operario)</div>'
        '<div class="firma"><div class="ln">&nbsp;</div>Revisó (Jefe de Producción)</div>'
        '<div class="firma"><div class="ln">&nbsp;</div>Aprobó (Calidad)</div>'
        '</div>'
        '</div></body></html>')
    return Response(html, mimetype='text/html')


@bp.route("/brd/dispensado/<int:ebr_id>", methods=["GET"])
def dispensado_imprimible(ebr_id):
    """Hoja IMPRIMIBLE del Dispensado de Materias Primas (MyBatch: ícono PDF de la
    sección 3). Lista todas las MP de la fórmula con %, lote, cant. a pesar y cant.
    pesada (lo registrado) + firmas. Server-side · Sebastián 6-jun-2026."""
    if not session.get("compras_user"):
        return Response('<script>location.href="/login?next=/brd/dispensado/' + str(ebr_id) + '"</script>',
                        mimetype="text/html")
    conn = get_db()
    import html as _h
    hdr = {}
    try:
        row = conn.execute(
            "SELECT COALESCE(lote,''), COALESCE(numero_op,''), mbr_template_id, "
            "COALESCE(estado,''), COALESCE(iniciado_at_utc,''), COALESCE(cantidad_objetivo_g,0), "
            "produccion_id, COALESCE(liberado_at_utc,''), COALESCE(fase,'fabricacion') "
            "FROM ebr_ejecuciones WHERE id=?", (ebr_id,)).fetchone()
        if row:
            hdr = {'lote': row[0], 'numero_op': row[1], 'mbr': row[2],
                   'estado': row[3], 'iniciado': row[4], 'obj_g': float(row[5] or 0),
                   'produccion_id': row[6], 'liberado': row[7], 'fase': row[8]}
            # Objetivo EN VIVO (M67 punto 4): la hoja de dispensado imprimible es un documento
            # regulado que el operario sigue en piso · mientras el EBR no esté liberado/completado,
            # el peso teórico a pesar sale de la fuente de verdad cantidad_kg, no del valor congelado.
            try:
                if (hdr['produccion_id'] and not hdr['liberado']
                        and hdr['estado'].lower() not in ('liberado', 'rechazado', 'completado')
                        and hdr['fase'] == 'fabricacion'):
                    _ckd = conn.execute(
                        "SELECT COALESCE(cantidad_kg,0) FROM produccion_programada WHERE id=?",
                        (hdr['produccion_id'],)).fetchone()
                    if _ckd and _ckd[0]:
                        hdr['obj_g'] = round(float(_ckd[0]) * 1000, 1)
            except Exception:
                pass
    except Exception:
        hdr = {}
    producto = ''
    try:
        if hdr.get('mbr'):
            mr = conn.execute("SELECT producto_nombre FROM mbr_templates WHERE id=?", (hdr['mbr'],)).fetchone()
            producto = (mr[0] if mr else '') or ''
    except Exception:
        pass
    # Recordado (cant. pesada) por material · última fila por material.
    recorded = {}
    try:
        for pr in conn.execute(
            "SELECT material_id, cantidad_real_g, COALESCE(lote_mp,''), COALESCE(pesado_por,''), "
            "COALESCE(pesado_at_utc,'') FROM ebr_pesajes WHERE ebr_id=? ORDER BY id", (ebr_id,)).fetchall():
            recorded[str(pr[0])] = pr  # la última gana
    except Exception:
        recorded = {}
    obj_g = hdr.get('obj_g', 0)
    # VENCIMIENTO de la MP que se está usando (Sebastián 30-jul: *"en el rótulo de pesaje que
    # vaya la fecha de vencimiento de la materia prima que usan"*). Sale del KARDEX para el
    # (material, lote) que se pesó de verdad — no del maestro, que no tiene lotes. Es un
    # control en el punto de uso: el operario ve en la hoja que sigue si el lote que tiene en
    # la mano está vencido, sin tener que ir a buscarlo a otra pantalla (M25).
    _venc = {}
    try:
        _pares = [(str(pr[0]), str(pr[2] or '')) for pr in
                  conn.execute("SELECT material_id, cantidad_real_g, COALESCE(lote_mp,'') "
                               "FROM ebr_pesajes WHERE ebr_id=?", (ebr_id,)).fetchall()
                  if str(pr[2] or '').strip()]
        for _mid, _lt in set(_pares):
            _r = conn.execute(
                "SELECT MAX(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA') "
                "            THEN fecha_vencimiento END) "
                "FROM movimientos WHERE material_id=? AND UPPER(TRIM(COALESCE(lote,'')))=UPPER(TRIM(?))",
                (_mid, _lt)).fetchone()
            if _r and _r[0]:
                _venc[(_mid, _lt.upper())] = str(_r[0])[:10]
    except Exception as _ev:
        log.warning('vencimiento de MP para la hoja de dispensado ebr=%s: %s', ebr_id, _ev)
    try:
        from datetime import date as _d_hoy
        _hoy_iso = _d_hoy.today().isoformat()
    except Exception:
        _hoy_iso = ''
    filas = []
    try:
        fitems = conn.execute(
            "SELECT material_id, COALESCE(material_nombre,''), COALESCE(porcentaje,0) "
            "FROM formula_items WHERE producto_nombre=? ORDER BY porcentaje DESC", (producto,)).fetchall()
        for i, fr in enumerate(fitems):
            mid = str(fr[0] or '').strip()
            if not mid:
                continue
            pct = float(fr[2] or 0)
            a_pesar = round(pct / 100.0 * obj_g, 1) if obj_g else 0
            rec = recorded.get(mid)
            pesada = ('{:,.1f}'.format(rec[1]) if rec and rec[1] is not None else '')
            lote = (rec[2] if rec else '') or ''
            por = (rec[3] if rec else '') or ''
            # Vence: sólo se muestra si HAY lote pesado y ese lote tiene fecha en el kardex.
            # Sin dato va una raya, no una fecha inventada (M115); y si ya venció, se marca:
            # una MP vencida no puede entrar al producto (INVIMA Res. 2214 · M25).
            _fv = _venc.get((mid, (lote or '').upper()), '')
            if not _fv:
                _venc_cell = ('<span style="color:var(--cx-text-faint, #94a3b8)">'
                              + ('sin fecha' if lote else '__________') + '</span>')
            elif _hoy_iso and _fv < _hoy_iso:
                _venc_cell = ('<b style="color:var(--cx-danger-text, #991b1b)">' + _h.escape(_fv)
                              + ' &middot; VENCIDO</b>')
            else:
                _venc_cell = _h.escape(_fv)
            filas.append(
                '<tr><td class="n">' + str(i + 1) + '</td>'
                '<td><span class="mono">' + _h.escape(mid) + '</span> ' + _h.escape(fr[1] or '') + '</td>'
                '<td class="c">' + ('{:.3f}'.format(pct)).rstrip('0').rstrip('.') + '%</td>'
                '<td class="mono">' + _h.escape(lote or '________') + '</td>'
                '<td class="c">' + _venc_cell + '</td>'
                '<td class="r">' + ('{:,.1f}'.format(a_pesar)) + ' g</td>'
                '<td class="r">' + (pesada + ' g' if pesada else '__________') + '</td>'
                '<td class="c">' + _h.escape(por or '______') + '</td></tr>')
    except Exception:
        pass
    filas_html = ''.join(filas) or '<tr><td colspan="8" style="text-align:center;color:var(--cx-text-faint, #94a3b8)">Sin fórmula con materias primas.</td></tr>'
    e = _h.escape
    html = (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<title>Dispensado · ' + e(hdr.get('numero_op') or str(ebr_id)) + '</title><style>'
        '@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap");'
        '*{box-sizing:border-box;font-family:"Inter",system-ui,Arial,sans-serif}'
        'body{margin:0;background:#f4f4f7;color:#18181b;padding:28px;-webkit-font-smoothing:antialiased}'
        '.sheet{max-width:1000px;margin:0 auto;background:var(--cx-card, #fff);padding:30px 34px;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.08)}'
        '.top{display:flex;justify-content:space-between;border-bottom:2px solid var(--cx-text, #0f172a);padding-bottom:10px;margin-bottom:14px}'
        '.top h1{font-size:18px;margin:0}.top .co{font-size:13px;font-weight:700;color:var(--cx-text-soft, #334155);text-align:right}'
        '.meta{display:grid;grid-template-columns:repeat(3,1fr);gap:8px 18px;font-size:12.5px;margin-bottom:14px}'
        '.meta b{color:var(--cx-text-mute, #64748b);font-weight:700;display:block;font-size:10.5px;text-transform:uppercase}'
        'table{width:100%;border-collapse:collapse;font-size:12px}'
        'th{background:var(--cx-primary-pale, #f5f3ff);color:var(--cx-primary-text, #4c1d95);padding:9px 10px;text-align:left;font-size:10.5px;text-transform:uppercase;font-weight:700}'
        'td{padding:7px 8px;border-bottom:1px solid var(--cx-border, #e2e8f0)}'
        'td.n{text-align:center;color:var(--cx-text-faint, #94a3b8);width:26px}td.c{text-align:center}td.r{text-align:right;font-variant-numeric:tabular-nums}'
        '.mono{font-family:ui-monospace,monospace}'
        '.firmas{display:grid;grid-template-columns:repeat(3,1fr);gap:30px;margin-top:40px;font-size:12px}'
        '.firma{text-align:center}.firma .ln{border-top:1px solid var(--cx-text, #0f172a);margin-bottom:5px;padding-top:5px}'
        '.no-print{text-align:center;margin:16px 0}.btn{background:var(--cx-primary, #7c3aed);color:#fff;border:none;border-radius:8px;padding:10px 20px;font-weight:700;cursor:pointer}'
        '@media print{.no-print{display:none}body{background:var(--cx-card, #fff);padding:0}.sheet{box-shadow:none}}'
        '</style></head><body>'
        '<div class="no-print"><button class="btn" onclick="window.print()">🖨 Imprimir / Guardar PDF</button></div>'
        '<div class="sheet">'
        '<div class="topacc"></div>'
        '<div class="top"><div><h1>DISPENSADO DE MATERIAS PRIMAS</h1>'
        '<div style="font-size:11px;color:#71717a;margin-top:3px">Hoja de pesaje · BPM / INVIMA · 21 CFR Part 11</div></div>'
        '<div class="co" style="display:flex;align-items:center;gap:10px"><span style="width:38px;height:38px;border-radius:11px;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#a78bfa,#6d28d9);box-shadow:0 4px 12px rgba(109,40,217,.2)"><svg viewBox="0 0 32 32" width="22" height="22" fill="none" stroke="#fff"><circle cx="16" cy="12" r="3" fill="#fff"/><path d="M 5 19 Q 16 17, 27 19" stroke-width="1.6" stroke-linecap="round" opacity=".7"/><path d="M 5 23 Q 16 21, 27 23" stroke-width="1.6" stroke-linecap="round" opacity=".4"/></svg></span><div style="text-align:left;line-height:1.2">ESPAGIRIA Laboratorio SAS<br><span style="font-weight:400;color:#71717a;font-size:11px">ÁNIMUS Lab</span></div></div></div>'
        '<div class="meta">'
        '<div><b>Orden</b>' + e(hdr.get('numero_op') or ('EBR-' + str(ebr_id))) + '</div>'
        '<div><b>N° de Lote</b>' + e(hdr.get('lote') or '·') + '</div>'
        '<div><b>Producto</b>' + e(producto or '·') + '</div>'
        '<div><b>Tamaño de lote</b>' + ('{:,.0f} g'.format(obj_g) if obj_g else '·') + '</div>'
        '<div><b>Estado</b>' + e(hdr.get('estado') or '·') + '</div>'
        '<div><b>Fecha</b>' + e((hdr.get('iniciado') or '')[:16].replace('T', ' ') or '·') + '</div>'
        '</div>'
        '<table><thead><tr><th>#</th><th>Materia Prima</th><th style="text-align:center">%</th><th>N° Lote</th><th style="text-align:center">Vence</th>'
        '<th style="text-align:right">Cant. a pesar</th><th style="text-align:right">Cant. pesada</th>'
        '<th style="text-align:center">Pesó</th></tr></thead><tbody>' + filas_html + '</tbody></table>'
        '<div class="firmas">'
        '<div class="firma"><div class="ln">&nbsp;</div>Dispensó (Operario)</div>'
        '<div class="firma"><div class="ln">&nbsp;</div>Verificó</div>'
        '<div class="firma"><div class="ln">&nbsp;</div>Revisó (Calidad)</div>'
        '</div></div></body></html>')
    return Response(html, mimetype='text/html')


# ──────────────────────────────────────────────────────────────────────────
# Activación de legajos automáticos · Sebastián 5-jun-2026
# Pantalla limpia (no popups) que genera+aprueba todos los MBR de una sola firma
# (password + MFA). Después, con EBR_MODE=warn, cada producción crea su legajo.
# ──────────────────────────────────────────────────────────────────────────

_ACTIVAR_LEGAJOS_HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Activar legajos automáticos · EOS</title>
<style>
*{box-sizing:border-box}
body{font-family:'Inter',system-ui,-apple-system,sans-serif;background:#f4f4f7;color:#18181b;margin:0;padding:24px;-webkit-font-smoothing:antialiased}
.wrap{max-width:760px;margin:0 auto}
a.back{display:inline-flex;align-items:center;gap:8px;background:var(--cx-card, #fff);color:var(--cx-primary-text, #7c3aed);font-size:13px;font-weight:700;text-decoration:none;padding:10px 18px;border-radius:11px;border:1px solid #e9d5ff;box-shadow:0 2px 10px rgba(124,58,237,.10)}
.card{background:var(--cx-card, #fff);border-radius:16px;box-shadow:0 4px 16px rgba(76,29,149,.07);margin:14px 0;overflow:hidden}
.hbar{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;padding:22px 26px}
.hbar h1{margin:0;font-size:22px}.hbar p{margin:6px 0 0;font-size:13px;opacity:.9}
.body{padding:24px 26px}
.step{display:flex;gap:12px;margin-bottom:14px;font-size:13.5px;color:var(--cx-text-soft, #475569)}
.step b{color:var(--cx-text, #1e293b)}
.num{flex:none;width:24px;height:24px;border-radius:50%;background:var(--cx-primary-soft, #ede9fe);color:var(--cx-primary-text, #6d28d9);font-weight:800;display:flex;align-items:center;justify-content:center;font-size:12px}
label{display:block;font-size:12px;font-weight:700;color:var(--cx-text-mute, #64748b);margin:14px 0 5px;text-transform:uppercase;letter-spacing:.3px}
input{width:100%;padding:12px 14px;border:1.5px solid var(--cx-border, #e2e8f0);border-radius:10px;font-size:15px}
input:focus{outline:none;border-color:var(--cx-primary, #7c3aed)}
.btn{margin-top:20px;width:100%;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;border:none;border-radius:11px;padding:14px;font-size:15px;font-weight:800;cursor:pointer;box-shadow:0 6px 18px rgba(124,58,237,.28)}
.btn:disabled{opacity:.6;cursor:wait}
.note{background:var(--cx-info-pale, #eff6ff);border:1px solid #bfdbfe;color:var(--cx-info-text, #1e40af);border-radius:10px;padding:12px 14px;font-size:12.5px;margin-top:16px}
#out{margin-top:18px}
.res{padding:14px 16px;border-radius:10px;font-size:14px;margin-bottom:10px}
.res.ok{background:var(--cx-success-pale, #dcfce7);color:var(--cx-success-text, #166534)}.res.err{background:var(--cx-danger-pale, #fee2e2);color:var(--cx-danger-text, #991b1b)}
.kpi{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}
.kpi div{background:var(--cx-primary-pale, #f5f3ff);border-radius:9px;padding:9px 14px;font-size:13px;font-weight:700;color:var(--cx-primary-text, #5b21b6)}
.fail{font-size:12px;color:var(--cx-danger-text, #991b1b);margin-top:8px}
</style></head><body>
<div class="wrap">
<a class="back" href="/inventarios#fabricacion"><span>&larr;</span> Volver a Producción</a>
<div class="card">
  <div class="hbar"><h1>🏭 Activar legajos automáticos</h1>
    <p>Aprobá todos los procedimientos maestros (MBR) de una sola firma. Luego cada producción crea su legajo solo, como MyBatch.</p></div>
  <div class="body">
    <div class="step"><div class="num">1</div><div>Se <b>generan</b> los MBR faltantes desde tus fórmulas (procedimiento por componente).</div></div>
    <div class="step"><div class="num">2</div><div>Se <b>aprueban todos</b> con tu firma electrónica (tu contraseña + código MFA · 21 CFR Part 11).</div></div>
    <div class="step"><div class="num">3</div><div>Quedan como <b>procedimiento oficial</b>. Desde ahí, producir crea el legajo automático.</div></div>
    <label>Tu contraseña de EOS</label>
    <input id="pass" type="password" autocomplete="off" placeholder="Contraseña">
    <label>Código MFA de 6 dígitos (vacío si no usás MFA)</label>
    <input id="totp" type="text" inputmode="numeric" autocomplete="off" placeholder="123456">
    <button class="btn" id="go" onclick="activar()">✅ Generar y aprobar todos los MBR</button>
    <div class="note">Es una sola vez. Tu firma queda registrada (quién, qué, cuándo) como exige INVIMA. La contraseña no se guarda.</div>
    <div id="out"></div>
  </div>
</div>
</div>
<script>
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
async function activar(){
  var pass=document.getElementById('pass').value;
  var totp=document.getElementById('totp').value.trim();
  if(!pass){alert('Escribí tu contraseña');return;}
  var btn=document.getElementById('go'), out=document.getElementById('out');
  btn.disabled=true; btn.textContent='Procesando… (puede tardar unos segundos)';
  out.innerHTML='';
  try{
    var t='';
    try{var cr=await fetch('/api/csrf-token',{credentials:'same-origin'});t=(await cr.json()).csrf_token||'';}catch(e){}
    var r=await fetch('/api/brd/mbr/aprobar-todas',{method:'POST',credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRF-Token':t},
      body:JSON.stringify({password:pass,totp_token:totp})});
    var d=await r.json();
    if(!r.ok){
      var hint = d.codigo==='MFA' ? ' (revisá el código de 6 dígitos · cambia cada 30s)' : (d.codigo==='PWD'?' (revisá la contraseña)':'');
      out.innerHTML='<div class="res err">❌ '+esc(d.error||r.status)+hint+'</div>';
      btn.disabled=false; btn.textContent='✅ Generar y aprobar todos los MBR'; return;
    }
    out.innerHTML='<div class="res ok">✅ ¡Listo! Procedimientos aprobados.</div>'+
      '<div class="kpi">'+
        '<div>'+(d.mbr_aprobados||0)+' aprobados ahora</div>'+
        '<div>'+(d.ya_estaban_aprobados||0)+' ya estaban</div>'+
        '<div>'+(d.mbr_generados||0)+' generados</div>'+
        '<div>'+(d.total_productos||0)+' productos</div>'+
      '</div>'+
      ((d.fallidos&&d.fallidos.length)?('<div class="fail">⚠ '+d.fallidos.length+' sin fórmula o con problema: '+d.fallidos.slice(0,8).map(function(f){return esc(f.producto);}).join(', ')+(d.fallidos.length>8?'…':'')+'</div>'):'')+
      '<div class="note">Siguiente: activar <b>EBR_MODE=warn</b> para que cada producción cree su legajo sola. Avisale a tu equipo técnico o pedímelo y lo dejo activo.</div>';
    btn.textContent='✅ Hecho';
  }catch(e){out.innerHTML='<div class="res err">Error de red: '+esc(e.message)+'</div>';btn.disabled=false;btn.textContent='✅ Generar y aprobar todos los MBR';}
}
</script>
</body></html>"""


@bp.route("/planta/activar-legajos", methods=["GET"])
def activar_legajos_page():
    """Pantalla de activación masiva de legajos automáticos (Admin/Calidad)."""
    u = session.get("compras_user", "")
    if not u:
        return Response('<script>location.href="/login?next=/planta/activar-legajos"</script>',
                        mimetype="text/html")
    if u not in ADMIN_USERS and u not in CALIDAD_USERS:
        return Response('<div style="font-family:sans-serif;padding:40px;color:var(--cx-danger-text, #991b1b)">Solo Admin o Calidad pueden activar legajos automáticos.</div>',
                        mimetype="text/html")
    return Response(_ACTIVAR_LEGAJOS_HTML, mimetype="text/html")


@bp.route("/api/brd/ebr/<int:ebr_id>/produccion-id", methods=["GET"])
def ebr_produccion_id(ebr_id):
    """Devuelve el id de la producción (tabla producciones) asociada a este EBR,
    matcheando por su lote. Permite ajustar la cantidad desde el detalle de orden
    (botón "+ Ajuste") reusando /api/produccion/<pid>/ajustar-cantidad."""
    err = _require_login()
    if err:
        return err
    conn = get_db()
    row = conn.execute(
        "SELECT COALESCE(lote_codigo, lote) FROM ebr_ejecuciones WHERE id=?",
        (ebr_id,)).fetchone()
    if not row:
        return jsonify({"error": "EBR no existe"}), 404
    lote = (row[0] or "").strip()
    pid = None
    if lote:
        pr = conn.execute(
            "SELECT id FROM producciones WHERE lote=? ORDER BY id DESC LIMIT 1",
            (lote,)).fetchone()
        pid = pr[0] if pr else None
    return jsonify({"ok": True, "produccion_id": pid, "lote": lote})


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURACION DE LAS VERIFICACIONES · el director tecnico las edita (15-ago-2026)
#
# En MyBatch los items del despeje de linea y los controles de atributos son pantallas
# de configuracion del DT. En EOS eran constantes del codigo: cambiar un item exigia un
# despliegue, y el DT dependia de que alguien lo hiciera por el.
#
# Se hace configurable SIN perder lo que el codigo daba gratis:
#   · cada cambio queda en `audit_log` con el ANTES y el DESPUES (Part 11 §11.10(e));
#   · el texto de lo YA FIRMADO no se toca nunca -la vista muestra el texto guardado
#     con cada registro, no el que hoy ocupe esa posicion (M105);
#   · un item RETIRADO no se borra: deja de pedirse y sigue apareciendo en los lotes
#     donde se registro, marcado como historico;
#   · la identidad de un item es su CLAVE, no su posicion, asi que reordenar la pantalla
#     no le cambia el significado a ningun `item_idx` ya firmado.
#
# La tabla nace VACIA: sin filas manda la lista de fabrica y todo funciona igual que
# antes de este cambio (aditivo · M117).
# ─────────────────────────────────────────────────────────────────────────────

_CHECKLIST_AMBITOS = {
    'despeje': ('dispensacion', 'fabricacion', 'envasado', 'acondicionamiento'),
    'ipc': ('fabricacion', 'envasado', 'acondicionamiento'),
}


def _checklist_puede_configurar(usuario):
    """Quien puede cambiar un procedimiento GMP: el director tecnico, Aseguramiento y
    admin. NO Calidad ni produccion: ellos EJECUTAN el procedimiento, no lo definen
    (segregacion de funciones · el mismo criterio con el que MyBatch se lo da al DT)."""
    try:
        return (_batch_role_info(usuario) or {}).get('tipo') in (
            'director_tecnico', 'aseguramiento', 'admin')
    except Exception:
        return False


def _checklist_fabrica(tipo, ambito):
    """La lista de fabrica del ambito, normalizada a (clave, texto, unidad)."""
    if tipo == 'ipc':
        return [(c, t, u) for c, t, u in _ipc_estandar_fabrica(ambito)]
    return [(str(i), t, '') for i, t in enumerate(DESPEJE_LINEA_ITEMS)]


def _checklist_filas(conn, tipo, ambito):
    """Las filas configuradas del ambito, activas e inactivas, en orden."""
    try:
        return conn.execute(
            "SELECT clave, texto, COALESCE(unidad,''), COALESCE(orden,0), COALESCE(activo,1), "
            "       COALESCE(actualizado_por, creado_por, ''), "
            "       COALESCE(actualizado_at, creado_at, '') "
            "  FROM checklist_items WHERE tipo=? AND ambito=? ORDER BY orden, id",
            (tipo, ambito)).fetchall()
    except Exception as _e:
        log.warning('checklist_filas(%s,%s) fallo: %s', tipo, ambito, _e)
        return []


@bp.route('/api/brd/checklists', methods=['GET'])
def brd_checklists_ver():
    """Las verificaciones vigentes de un ambito, y de donde salen."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    tipo = (request.args.get('tipo') or 'despeje').strip().lower()
    if tipo not in _CHECKLIST_AMBITOS:
        return jsonify({'error': 'tipo invalido', 'validos': sorted(_CHECKLIST_AMBITOS)}), 400
    ambito = (request.args.get('ambito') or _CHECKLIST_AMBITOS[tipo][0]).strip().lower()
    conn = get_db()
    filas = _checklist_filas(conn, tipo, ambito)
    usuario = session.get('compras_user', '')

    if filas:
        items = [{'clave': r[0], 'texto': r[1], 'unidad': r[2], 'orden': int(r[3] or 0),
                  'activo': bool(int(r[4] or 0))} for r in filas]
        cambios = [(r[6], r[5]) for r in filas if r[6]]
        ultimo = max(cambios)[0] if cambios else ''
        por = max(cambios)[1] if cambios else ''
        origen = 'configurado'
    else:
        items = [{'clave': c, 'texto': t, 'unidad': u, 'orden': i, 'activo': True}
                 for i, (c, t, u) in enumerate(_checklist_fabrica(tipo, ambito))]
        ultimo, por, origen = '', '', 'fabrica'

    # Cuantos lotes ya firmaron con esta lista: cambiar un procedimiento con lotes
    # abiertos es una decision, y quien la toma tiene que ver el numero ANTES (M126).
    abiertos = 0
    try:
        if tipo == 'ipc':
            abiertos = int(conn.execute(
                "SELECT COUNT(*) FROM ebr_ejecuciones WHERE COALESCE(fase,'fabricacion')=? "
                "AND estado NOT IN ('liberado','rechazado','cancelado')", (ambito,)
            ).fetchone()[0] or 0)
        else:
            abiertos = int(conn.execute(
                "SELECT COUNT(DISTINCT ebr_id) FROM ebr_despeje_items "
                "WHERE COALESCE(etapa,'dispensacion')=?", (ambito,)).fetchone()[0] or 0)
    except Exception as _e:
        log.warning('checklists abiertos(%s,%s) fallo: %s', tipo, ambito, _e)

    return jsonify({
        'ok': True, 'tipo': tipo, 'ambito': ambito, 'items': items,
        'origen': origen, 'ultimo_cambio': ultimo, 'ultimo_por': por,
        'legajos_en_curso': abiertos,
        'puede_configurar': _checklist_puede_configurar(usuario),
        'ambitos': list(_CHECKLIST_AMBITOS[tipo]),
    })


@bp.route('/api/brd/checklists', methods=['POST'])
def brd_checklists_guardar():
    """Guarda las verificaciones de un ambito. Reemplaza el ambito completo.

    Un item NUEVO se agrega SIEMPRE con una clave que nunca se uso: para el despeje eso
    es el siguiente `item_idx` libre, contando tambien los que ya se retiraron. Reciclar
    una clave le cambiaria el significado a lo que ya se firmo con ella.
    """
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if not _checklist_puede_configurar(user):
        return jsonify({'error': 'Solo el director tecnico, Aseguramiento o admin pueden '
                                 'cambiar un procedimiento GMP',
                        'codigo': 'SIN_PERMISO_CHECKLIST'}), 403
    d = request.get_json(silent=True) or {}
    tipo = (d.get('tipo') or '').strip().lower()
    if tipo not in _CHECKLIST_AMBITOS:
        return jsonify({'error': 'tipo invalido'}), 400
    ambito = (d.get('ambito') or '').strip().lower()
    if ambito not in _CHECKLIST_AMBITOS[tipo]:
        return jsonify({'error': 'ambito invalido para %s' % tipo,
                        'validos': list(_CHECKLIST_AMBITOS[tipo])}), 400
    entrantes = d.get('items')
    if not isinstance(entrantes, list):
        return jsonify({'error': 'items debe ser una lista'}), 400
    limpios = []
    for it in entrantes:
        if not isinstance(it, dict):
            continue
        texto = (it.get('texto') or '').strip()
        if not texto:
            continue
        limpios.append({
            'clave': (str(it.get('clave') or '').strip()),
            'texto': texto[:600],
            'unidad': (str(it.get('unidad') or '').strip())[:20],
        })
    if not limpios:
        # Una lista vacia dejaria el legajo SIN verificaciones y se veria igual que uno
        # bien configurado: eso no es relajar un control, es borrarlo (M124/M126).
        return jsonify({'error': 'La lista no puede quedar vacia: un legajo sin '
                                 'verificaciones no es un legajo',
                        'codigo': 'CHECKLIST_VACIO'}), 400

    conn = get_db()
    cur = conn.cursor()
    antes_filas = _checklist_filas(conn, tipo, ambito)
    antes = [{'clave': r[0], 'texto': r[1], 'unidad': r[2], 'activo': bool(int(r[4] or 0))}
             for r in antes_filas]
    if not antes:
        # Primera vez que se configura: la base es la lista de fabrica, para no perder
        # los items que nadie toco en esta edicion.
        antes = [{'clave': c, 'texto': t, 'unidad': u, 'activo': True}
                 for c, t, u in _checklist_fabrica(tipo, ambito)]
    claves_usadas = {a['clave'] for a in antes}

    # Claves que YA se firmaron alguna vez: no se reciclan jamas.
    if tipo == 'despeje':
        try:
            for r in cur.execute(
                "SELECT DISTINCT item_idx FROM ebr_despeje_items "
                "WHERE COALESCE(etapa,'dispensacion')=?", (ambito,)).fetchall():
                claves_usadas.add(str(int(r[0])))
        except Exception as _e:
            log.warning('checklists claves firmadas(%s) fallo: %s', ambito, _e)
    else:
        try:
            for r in cur.execute(
                "SELECT DISTINCT control_codigo FROM ipc_estandar_resultados").fetchall():
                if r[0]:
                    claves_usadas.add(str(r[0]).strip())
        except Exception as _e:
            log.warning('checklists codigos usados fallo: %s', _e)

    def _clave_nueva(texto):
        if tipo == 'despeje':
            n = 0
            for k in claves_usadas:
                try:
                    n = max(n, int(k) + 1)
                except (TypeError, ValueError):
                    continue
            return str(n)
        base = ''
        import unicodedata as _ud
        plano = ''.join(ch for ch in _ud.normalize('NFKD', texto.lower())
                        if not _ud.combining(ch))
        for ch in plano:
            base += ch if (ch.isalnum()) else '_'
        base = '_'.join(x for x in base.split('_') if x)[:28] or 'control'
        cand, i = base, 2
        while cand in claves_usadas:
            cand = '%s_%d' % (base[:24], i)
            i += 1
        return cand

    finales = []
    for orden, it in enumerate(limpios):
        clave = it['clave']
        if not clave or clave not in claves_usadas:
            clave = _clave_nueva(it['texto'])
        claves_usadas.add(clave)
        finales.append((clave, it['texto'], it['unidad'], orden))

    # import local: este archivo no importa datetime a nivel de modulo
    from datetime import datetime as _dch, timedelta as _tdch
    ahora = (_dch.utcnow() - _tdch(hours=5)).isoformat(timespec='seconds')  # ancla Colombia (M24)
    vivos = {f[0] for f in finales}
    try:
        cur.execute("DELETE FROM checklist_items WHERE tipo=? AND ambito=?", (tipo, ambito))
        for clave, texto, unidad, orden in finales:
            cur.execute(
                "INSERT INTO checklist_items (tipo, ambito, clave, texto, unidad, orden, "
                "activo, creado_por, creado_at, actualizado_por, actualizado_at) "
                "VALUES (?,?,?,?,?,?,1,?,?,?,?)",
                (tipo, ambito, clave, texto, unidad, orden, user, ahora, user, ahora))
        # Lo RETIRADO se conserva inactivo, al final: los lotes donde se registro lo
        # siguen mostrando. Un registro regulado no se borra porque el procedimiento
        # haya cambiado despues.
        base = len(finales)
        for i, a in enumerate(antes):
            if a['clave'] in vivos:
                continue
            cur.execute(
                "INSERT INTO checklist_items (tipo, ambito, clave, texto, unidad, orden, "
                "activo, creado_por, creado_at, actualizado_por, actualizado_at) "
                "VALUES (?,?,?,?,?,?,0,?,?,?,?)",
                (tipo, ambito, a['clave'], a['texto'], a.get('unidad', ''), base + i,
                 user, ahora, user, ahora))
    except Exception as e:
        conn.rollback()
        log.warning('checklists guardar(%s,%s) fallo: %s', tipo, ambito, e)
        return jsonify({'error': 'No se pudo guardar: %s' % e}), 500

    audit_log(cur, usuario=user, accion='CONFIGURAR_CHECKLIST',
              tabla='checklist_items', registro_id='%s:%s' % (tipo, ambito),
              antes={'items': antes},
              despues={'items': [{'clave': c, 'texto': t, 'unidad': u, 'orden': o}
                                 for c, t, u, o in finales],
                       'motivo': (d.get('motivo') or '')[:400]})
    conn.commit()
    return jsonify({'ok': True, 'tipo': tipo, 'ambito': ambito,
                    'items': len(finales),
                    'retirados': len([a for a in antes if a['clave'] not in vivos])})


@bp.route('/api/brd/checklists/restaurar', methods=['POST'])
def brd_checklists_restaurar():
    """Vuelve el ambito a la lista de FABRICA (borra la personalizacion, no los registros)."""
    if 'compras_user' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    user = session.get('compras_user', '')
    if not _checklist_puede_configurar(user):
        return jsonify({'error': 'Solo el director tecnico, Aseguramiento o admin',
                        'codigo': 'SIN_PERMISO_CHECKLIST'}), 403
    d = request.get_json(silent=True) or {}
    tipo = (d.get('tipo') or '').strip().lower()
    ambito = (d.get('ambito') or '').strip().lower()
    if tipo not in _CHECKLIST_AMBITOS or ambito not in _CHECKLIST_AMBITOS[tipo]:
        return jsonify({'error': 'tipo o ambito invalido'}), 400
    conn = get_db()
    cur = conn.cursor()
    antes = [{'clave': r[0], 'texto': r[1], 'unidad': r[2], 'activo': bool(int(r[4] or 0))}
             for r in _checklist_filas(conn, tipo, ambito)]
    if not antes:
        return jsonify({'ok': True, 'ya_era_de_fabrica': True, 'tipo': tipo, 'ambito': ambito})
    cur.execute("DELETE FROM checklist_items WHERE tipo=? AND ambito=?", (tipo, ambito))
    audit_log(cur, usuario=user, accion='RESTAURAR_CHECKLIST',
              tabla='checklist_items', registro_id='%s:%s' % (tipo, ambito),
              antes={'items': antes}, despues={'origen': 'fabrica'})
    conn.commit()
    return jsonify({'ok': True, 'tipo': tipo, 'ambito': ambito, 'restaurados': len(antes)})
