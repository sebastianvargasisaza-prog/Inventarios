# config.py -- constantes y credenciales del sistema
import os

# Contraseñas por usuario. Cada PASS_<USER> en Render debe ser un hash
# PBKDF2 (ver scripts/gen_password_hashes.py).
#
# Si una env var falta, el usuario queda con string vacío — el flujo de
# login en core.py rechaza correctamente (no matchea ninguna contraseña),
# por lo que ese usuario simplemente no puede entrar hasta que se
# configure su PASS_<USER>. validate_config() reporta cuáles faltan en
# logs estructurados al startup.
def _pwd(env_var):
    """Lee password (hash) desde env var, retorna '' si falta."""
    return os.environ.get(env_var, "").strip()

COMPRAS_USERS = {
    "sebastian":  _pwd("PASS_SEBASTIAN"),
    "alejandro":  _pwd("PASS_ALEJANDRO"),
    "hernando":   _pwd("PASS_HERNANDO"),
    "catalina":   _pwd("PASS_CATALINA"),
    "luz":        _pwd("PASS_LUZ"),
    "daniela":    _pwd("PASS_DANIELA"),
    "valentina":  _pwd("PASS_VALENTINA"),
    "jefferson":  _pwd("PASS_JEFFERSON"),
    "felipe":     _pwd("PASS_FELIPE"),
    "mayra":      _pwd("PASS_MAYRA"),
    "gloria":     _pwd("PASS_GLORIA"),
    "laura":      _pwd("PASS_LAURA"),
    "miguel":     _pwd("PASS_MIGUEL"),
    "yuliel":     _pwd("PASS_YULIEL"),
    "luis":       _pwd("PASS_LUIS"),
    "smurillo":   _pwd("PASS_SMURILLO"),
    "sergio":     _pwd("PASS_SERGIO"),
    "mayerlin":   _pwd("PASS_MAYERLIN"),
    "camilo":     _pwd("PASS_CAMILO"),
    "jose":       _pwd("PASS_JOSE"),
    "milton":     _pwd("PASS_MILTON"),
}
ADMIN_USERS     = {"sebastian", "alejandro"}
# Mayra (contadora) + Catalina (asistente compras): mismo perfil financiero/contable
CONTADORA_USERS = {"mayra", "catalina"}
# Gloria (sólo RRHH), + asistentes de gerencia (daniela ÁNIMUS, luz Espagiria),
# + contadora/asist. compras (mayra, catalina), + admins.
RRHH_USERS      = {"gloria", "daniela", "luz", "mayra", "catalina", "alejandro", "sebastian"}
# Control de Calidad (CC · Jefe de Control de Calidad = Laura, analista = Yulieth) ·
# análisis, liberación, micro, fisicoquímico, agua, calibraciones, estabilidades, OOS.
# Módulo /calidad. (Miguel NO va acá: es Aseguramiento · división de cargos 14-jun.)
# Backup de liberación de MP: Miguel (Aseguramiento) y Hernando (Dir. Técnica)
# pueden liberar materias primas vía QC_USERS (inventario.py) SIN estar en
# CALIDAD_USERS · mantiene la separación QA/QC (Sebastián 16-jul).
CALIDAD_USERS   = {"laura", "yuliel", "alejandro", "sebastian"}
# Aseguramiento de la Calidad (AC · responsable = Miguel) · CARGO DISTINTO al de Control de
# Calidad: gobierna el SISTEMA de calidad — SGD (control de documentos), desviaciones, control
# de cambios, CAPA, quejas, recalls, auditorías/autoinspección, capacitaciones. Módulo
# /aseguramiento. Override con env ASEGURAMIENTO_USERS_OVERRIDE.
ASEGURAMIENTO_USERS = {
    u.strip().lower() for u in os.environ.get(
        "ASEGURAMIENTO_USERS_OVERRIDE", "miguel,alejandro,sebastian"
    ).split(",") if u.strip()
}
# 'luis' salió del set el 26-jul-2026: está dado de baja desde la mig 375 (su login ya estaba
# bloqueado con `users_passwords.activo=0`), pero seguía figurando acá, así que la matriz de
# accesos del expediente lo mostraba con permisos sobre el batch record. Un empleado retirado que
# aparece con permisos en un documento de autorización es una objeción segura. NO se borra su
# usuario ni su historial: GMP/Part 11 conservan quién hizo qué (sus firmas y registros siguen).
# Sergio salio el 7-ago-2026 (Sebastian: *"sergio inhabilitalo ya no trabaja"*) · su login
# queda bloqueado por la mig 421 y sale de la lista para no figurar con permisos en la
# matriz. Su historial NO se borra: Part 11 conserva quien hizo que.
PLANTA_USERS    = {"smurillo", "mayerlin", "camilo", "jose", "milton"}


def puede_archivar(usuario):
    """¿Este usuario puede ELIMINAR o ARCHIVAR un registro maestro?

    Sebastián 7-ago-2026: *"los operarios pueden modificar un inventario, ingresar un producto,
    pero no eliminar ni archivar, y los cambios quedan con el usuario que lo modifica"*.

    Se escribe por EXCLUSIÓN (todos menos los operarios de planta) y NO con una lista de
    permitidos por endpoint. Una lista de permitidos escrita a mano siempre deja afuera a alguien
    que nadie se acordó de incluir, y eso no se descubre revisando código: se descubre con la
    persona trabada en pleno turno (M32/M121). Por exclusión, agregar un rol nuevo mañana no
    rompe nada, y el único conjunto que hay que mantener al día es el que ya existe.

    ⚠ Vale para el MAESTRO (archivar un envase, borrar una presentación, dar de baja un equipo),
    no para el trabajo del día: el operario sigue registrando producción, recepción, consumo y
    conteo, y sigue pudiendo CORREGIR lo que carga. Lo que no puede es hacer desaparecer una
    ficha, que es lo irreversible desde su silla.
    """
    u = (usuario or '').strip()
    if not u:
        return False          # sin sesión no se decide acá · el 401 lo da el endpoint
    return u not in PLANTA_USERS


# ══════════════════════════════════════════════════════════════════════════════════════
# QUIEN ENTRA A CADA MODULO · dictado por Sebastian el 7-ago-2026
# ══════════════════════════════════════════════════════════════════════════════════════
#
# Una sola fuente para todo el sistema: el menu esconde lo que la persona no puede abrir y el
# gate de entrada usa ESTE mismo mapa. Si estuvieran separados, un dia el menu mostraria una
# tarjeta que al abrirse da 403 -- o peor, al reves (M1: un solo resolver por entidad).
#
# ⚠ Esto controla ENTRAR A UN MODULO. Los permisos finos de adentro (autorizar una OC, firmar una
# liberacion, archivar una ficha) siguen donde estaban: son otra pregunta y tienen sus propios
# guards. Mezclarlos aca haria que cambiar quien VE una pantalla cambie quien puede FIRMAR, que
# es justo lo que no se quiere en un sistema INVIMA.

# Lo que ve todo el mundo: pedir algo, registrar lo que llega y hablar con el equipo.
_TODOS = set(COMPRAS_USERS)

MODULOS_ACCESO = {
    # --- para todos ---
    'solicitudes':   set(_TODOS),
    'recepcion':     set(_TODOS),
    'chat':          set(_TODOS),

    # --- planta ---
    # Jose es el jefe de produccion (reemplazo a Luis, despedido el 24-jul · mig 375).
    'planta': {'sebastian', 'alejandro', 'jose',
               'camilo', 'mayerlin', 'smurillo', 'milton',      # operarios
               'miguel', 'laura', 'yuliel', 'catalina', 'luz', 'hernando'},

    # --- calidad y regulatorio ---
    # Miguel entra a Calidad ademas de Aseguramiento (Sebastian: *"es mas, miguel deberia poder
    # entrar a calidad tambien"*).
    'calidad':       {'sebastian', 'alejandro', 'laura', 'yuliel', 'miguel', 'hernando',
                      'catalina', 'luz'},
    'aseguramiento': {'sebastian', 'alejandro', 'miguel', 'hernando', 'luz'},
    'tecnica':       {'sebastian', 'alejandro', 'hernando', 'luz'},

    # --- administracion ---
    'compras':       {'sebastian', 'alejandro', 'catalina', 'mayra', 'luz'},
    'tesoreria':     {'sebastian', 'alejandro', 'mayra'},
    'rrhh':          {'sebastian', 'alejandro', 'gloria', 'luz', 'mayra'},
    'bienestar':     {'sebastian', 'alejandro', 'gloria', 'luz'},

    # --- comercial / marcas ---
    'marketing':     {'sebastian', 'alejandro', 'jefferson'},
    'clientes':      {'sebastian', 'alejandro', 'valentina', 'luz'},
    'animus':        {'sebastian', 'alejandro', 'daniela'},
    'espagiria':     {'sebastian', 'alejandro', 'luz'},

    # --- solo direccion ---
    # Los que Sebastian no nombro quedan de admin a proposito: si despues falta alguien se agrega
    # en un minuto y se ve en /admin/permisos. Abrir de mas no se nota; abrir de menos se reporta
    # el mismo dia.
    'gerencia':      set(ADMIN_USERS),
    'centro':        set(ADMIN_USERS),
    'comercial':     set(ADMIN_USERS),
    'compliance':    set(ADMIN_USERS),
    'inteligencia':  set(ADMIN_USERS),
    'invima':        set(ADMIN_USERS),
    'seguridad':     set(ADMIN_USERS),
    'admin':         set(ADMIN_USERS),
}

# Que prefijo de URL pertenece a que modulo · se evalua EN ORDEN (el mas especifico primero).
#
# ⚠ Lo que NO esta en esta lista NO se bloquea. Es deliberado: un default-deny sobre 1.700 rutas
# cerraria en silencio cosas que hoy funcionan, y el sintoma seria alguien trabado en pleno turno
# sin que nadie sepa por que (M121). Lo que no esta listado conserva el gate que ya tenia.
MODULO_POR_RUTA = (
    # ⚠ `/admin` y `/diag` NO se mapean acá a propósito: ya tienen su propio gate y responden
    # **404**, no 403, para no revelar siquiera que la ruta existe (es como se cerró la fuga de
    # `/diag/*` a internet · M95). Si este gate se metiera antes, contestaría 403 y volvería a
    # delatar que están ahí. Un gate duplicado no suma seguridad: le cambia la respuesta al que
    # ya funcionaba.
    ('/seguridad',          'seguridad'),
    ('/comunicacion',       'admin'),      # 'Compromisos (legacy)' · no esta en uso
    ('/compromisos',        'admin'),
    ('/aseguramiento',      'aseguramiento'),
    ('/calidad',            'calidad'),
    ('/tecnica',            'tecnica'),
    ('/compras',            'compras'),
    ('/tesoreria',          'tesoreria'),
    ('/financiero',         'tesoreria'),
    ('/contabilidad',       'tesoreria'),
    ('/gerencia-financiero', 'tesoreria'),
    ('/gerencia',           'gerencia'),
    ('/centro',             'centro'),
    ('/hoy',                'centro'),
    ('/comercial',          'comercial'),
    ('/compliance',         'compliance'),
    ('/rrhh',               'rrhh'),
    ('/bienestar',          'bienestar'),
    ('/marketing',          'marketing'),
    ('/clientes',           'clientes'),
    ('/animus',             'animus'),
    ('/espagiria',          'espagiria'),
    ('/planta',             'planta'),
    ('/inventarios',        'planta'),
    ('/brd',                'planta'),
    ('/programacion',       'planta'),
    ('/asignar-areas',      'planta'),
    ('/artes',              'planta'),
    ('/solicitudes',        'solicitudes'),
    ('/recepcion',          'recepcion'),
    ('/chat',               'chat'),
)

# Paginas que NUNCA se bloquean aunque caigan bajo un prefijo: la propia sesion, lo publico y lo
# que el navegador pide solo. Si el logout quedara detras de un permiso, alguien sin acceso no
# podria ni salir.
RUTAS_SIEMPRE_ABIERTAS = {
    '/', '/login', '/logout', '/login/mfa', '/login/mfa-backup', '/modulos', '/hub',
    '/cambiar-password', '/healthz', '/sw.js', '/manifest.json', '/reportar',
    '/portal', '/portal/login', '/portal/logout',
}


def modulo_de_ruta(ruta):
    """A que modulo pertenece una pagina · None si no esta mapeada (y entonces no se bloquea)."""
    r = (ruta or '').split('?')[0].rstrip('/') or '/'
    if r in RUTAS_SIEMPRE_ABIERTAS or (r + '/') in RUTAS_SIEMPRE_ABIERTAS:
        return None
    for pref, mod in MODULO_POR_RUTA:
        if r == pref or r.startswith(pref + '/'):
            return mod
    return None


def puede_ver_modulo(usuario, modulo):
    """El unico resolver de 'esta persona entra a este modulo'."""
    u = (usuario or '').strip().lower()
    if not u:
        return False
    if u in ADMIN_USERS:
        return True                      # fundador y CEO entran a todo
    return u in MODULOS_ACCESO.get(modulo, set())


DB_PATH = os.environ.get("DB_PATH", "/var/data/inventario.db")

# URL pública canónica de la app. Se usa para construir links absolutos
# en correos de notificación (asignación de tareas, etc.). Si la env var
# falta, defaulteamos a app.eossuite.com (dominio oficial desde abr-2026).
# El dominio antiguo inventarios-0363.onrender.com sigue funcionando como
# backup pero NO debe aparecer hardcodeado en ninguna parte.
APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://app.eossuite.com").rstrip("/")

# Reemplazo de MyBatch · fase 1 · EBR (batch record) automático al aceptar
# producción. Modo de transición controlado por env para no frenar planta antes
# de tener todos los MBR cargados:
#   'off'    → no fuerza e-firma en pesajes/pasos · NO bloquea (default seguro)
#   'warn'   → exige e-firma en pesajes/pasos (BPM) · no bloquea aceptar sin MBR
#   'strict' → además BLOQUEA aceptar producción si no hay MBR aprobado
# 5-jun-2026: el LEGAJO AUTOMÁTICO ya NO depende de EBR_MODE (se crea siempre que
# el producto tenga MBR aprobado · ver _handle_produccion_inner). EBR_MODE quedó
# SOLO para el rigor de firmas/bloqueo. Default 'off' = legajos automáticos sin
# forzar que cada operario firme cada pesaje (eso se activa con 'warn' cuando el
# equipo esté listo). Pasar a 'strict' cuando TODOS los MBR estén aprobados.
EBR_MODE = os.environ.get("EBR_MODE", "off").strip().lower()
if EBR_MODE not in ("off", "warn", "strict"):
    EBR_MODE = "off"


def recepcion_auto_vigente_env():
    """Parte ENV del interruptor (fallback). El valor efectivo lo resuelve
    `database.recepcion_auto_vigente(conn)`, que da prioridad al toggle en BD
    (app_settings · botón en la UI, sin tocar Render). Default OFF = INVIMA
    cuarentena-first."""
    return os.environ.get("RECEPCION_AUTO_VIGENTE", "0").strip().lower() in (
        "1", "true", "yes", "si", "sí", "on")


# Contraseñas plaintext conocidas que NUNCA deben usarse en producción.
# validate_config() las detecta y emite un warning por cada usuario afectado.
_INSECURE_PLAINTEXT_DEFAULTS = {"hha2026", "espagiria2026", "animus2026"}

# Compras: contabilidad/finanzas + admins. (Daniela y Luz se movieron a marketing
# de su empresa — ya no participan del flujo de compras del holding.)
COMPRAS_ACCESS  = {"catalina", "mayra", "alejandro", "sebastian"}
FINANZAS_ACCESS = {"mayra", "catalina", "sebastian", "alejandro"}
# Clientes: contabilidad + asistentes (ventas, gerencias) + admins.
CLIENTES_ACCESS = {"mayra", "catalina", "valentina", "daniela", "luz", "alejandro", "sebastian"}
TECNICA_USERS   = {"hernando", "miguel", "alejandro", "sebastian"}
# ── Quién puede VER una fórmula maestra (Sebastián 25-jul) ────────────────────
# La receta (código de MP + porcentaje) es el activo regulado más sensible de la
# planta: define qué se dispensa, alimenta el descuento FEFO, la compra y el MBR.
# Hasta hoy CUALQUIER usuario logueado la leía: el candado de la pantalla era un
# PIN de navegador (cosmético) y `GET /api/formulas` no pedía rol — verificado
# con una sesión de un usuario común, que recibió las 40 recetas completas.
# El set es el de permiso INVIMA: Dirección Técnica (dueña de la fórmula),
# Control de Calidad (verifica la dispensación), Aseguramiento (gobierna el SGC)
# y Dirección. Quien no está acá sigue viendo los NOMBRES de producto (para
# elegir en Fabricación o en un pedido B2B), nunca los ingredientes.
# Override por env sin redeploy: FORMULAS_VER_USERS_OVERRIDE="a,b,c".
_FORMULAS_VER_OVERRIDE = os.environ.get("FORMULAS_VER_USERS_OVERRIDE", "").strip()
FORMULAS_VER_USERS = (
    {u.strip().lower() for u in _FORMULAS_VER_OVERRIDE.split(",") if u.strip()}
    if _FORMULAS_VER_OVERRIDE
    else (TECNICA_USERS | CALIDAD_USERS | ASEGURAMIENTO_USERS | ADMIN_USERS)
)
# Marketing: equipo de marketing + asistentes de gerencia (cada una para su empresa).
# Marketing quedo en Jefferson (Sebastian 7-ago) · Felipe salio de la empresa y Daniela y Luz
# pasaron a sus propios modulos (ANIMUS y Espagiria).
MARKETING_USERS = {"jefferson", "alejandro", "sebastian"}
# Acceso al módulo ÁNIMUS Lab (skincare): asistente de gerencia + admins.
ANIMUS_ACCESS   = {"daniela", "alejandro", "sebastian"}
# Acceso al módulo Espagiria (pendiente de crear blueprint): asist. gerencia + admins.
ESPAGIRIA_ACCESS = {"luz", "alejandro", "sebastian"}

# ── Límites de aprobación de OC por usuario (en COP) ──────────────────────────
# Operación que excede el límite del usuario requiere aprobación de admin.
# Sebastian/Alejandro (admins): sin límite (None = ilimitado).
# Mayra/Catalina: pueden autorizar OCs hasta 5M COP solas; mayor → admin.
# Otros: no autorizan OCs, solo crean solicitudes.
LIMITES_APROBACION_OC = {
    "sebastian": None,           # Admin: sin límite
    "alejandro": None,           # Admin: sin límite
    "mayra":     5_000_000,
    "catalina":  5_000_000,
}

# ── Quién puede AUTORIZAR/PAGAR OCs aunque comparta el perfil contable ────────
# Sebastián 13-jun-2026: Catalina (asistente de COMPRAS) debe poder autorizar y
# pagar OCs (hasta su límite de LIMITES_APROBACION_OC; mayor → admin). Está en
# CONTADORA_USERS solo por el perfil financiero/bancario compartido, pero su rol
# operativo es compras. El gate _require_authorize_oc (segregación de funciones)
# bloquea a las contadoras EXCEPTO a quienes estén en este set explícito.
# Sebastián 18-jun-2026: gerencia decide que Catalina, Mayra (y los admins) TODOS pueden
# autorizar Y pagar OCs — operación chica, equipo de confianza. Se relaja la SoD a propósito.
# ⚠ Nota SoD: que el mismo usuario autorice Y pague una OC concentra funciones; el control
#   compensatorio es el audit_log (cada autorizar/pagar queda con usuario/fecha) + el límite
#   de monto por usuario (LIMITES_APROBACION_OC: 5M Catalina/Mayra · admins sin tope).
OC_AUTORIZA_USERS = {"catalina", "mayra"}

# ── Quién autoriza/paga OCs SIN tope de monto (cualquier valor) ───────────────
# Sebastián 26-jun-2026: Catalina autoriza OCs "sin importar el monto" — equipo de confianza, maneja
# compras de punta a punta. Se la trata como admin SOLO para el límite de monto de OC (NO le da admin
# general · sigue sin reset-password, hard-delete, etc.). Control compensatorio: audit_log (cada
# autorizar/pagar queda con usuario+fecha+monto). Reversible: sacarla de este set → vuelve su tope de
# LIMITES_APROBACION_OC (5M). Mayra NO está acá (mantiene su tope 5M).
OC_SIN_LIMITE_MONTO = {"catalina"}

# ── Quién puede LIBERAR / APROBAR lotes de Materia Prima (además de Calidad) ──
# VACÍO A PROPÓSITO · Sebastián 26-jul-2026: *"Catalina no libera ya, fue mientras hacíamos
# pruebas"*.
#
# Del 26-jun al 26-jul Catalina (Asistente de Compras) estuvo en este conjunto para poder probar
# el flujo de recepción. Al generar el expediente para la Dirección Técnica, el propio documento
# lo detectó y lo declaró como conflicto de segregación: **quien compra la materia prima no puede
# ser quien la libera de cuarentena.** La Resolución 2214/2021 art. 10 asigna la disposición del
# lote a Calidad, y el docstring de `aprobar_lote` (despachos.py) ya lo decía — o sea que el
# permiso real contradecía la documentación del propio código.
#
# La liberación queda donde corresponde: Control de Calidad, Aseguramiento, Dirección Técnica y
# Dirección (ver el gate en `despachos.py` y `QC_USERS` en `inventario.py`).
#
# Si alguna vez hay que volver a ampliarlo, tiene que ser una decisión explícita de la Dirección
# Técnica y quedar reflejada en `EXPEDIENTE_AUTORIZACION_EOS.md`, que detecta este cruce solo.
MP_LIBERA_USERS = set()

# PIN para desbloquear vista de cantidades en Fórmulas.
# DEBE setearse via env var FORMULA_PIN. Si falta, se genera un PIN
# aleatorio efímero (cambia en cada redeploy) — equivalente a deshabilitar
# el desbloqueo hasta que se configure correctamente.
import secrets as _secrets
_formula_pin_env = os.environ.get("FORMULA_PIN", "").strip()
if _formula_pin_env and _formula_pin_env != "7531":
    FORMULA_PIN = _formula_pin_env
else:
    # PIN aleatorio de 12 dígitos: nadie lo conoce, efectivamente bloquea
    # el desbloqueo hasta que el admin configure FORMULA_PIN en Render.
    FORMULA_PIN = "".join(_secrets.choice("0123456789") for _ in range(12))
    _FORMULA_PIN_INSECURE = True
del _formula_pin_env, _secrets

# Emails de usuarios para notificaciones (configurar via env vars en Render)
USER_EMAILS = {
    "jefferson":  os.environ.get("EMAIL_JEFFERSON",  "jermun1992@gmail.com"),
    "hernando":   os.environ.get("EMAIL_HERNANDO",   ""),
    "catalina":   os.environ.get("EMAIL_CATALINA",   ""),
    "luz":        os.environ.get("EMAIL_LUZ",        ""),
    "daniela":    os.environ.get("EMAIL_DANIELA",    ""),
    "sebastian":  os.environ.get("EMAIL_SEBASTIAN",  "sebastianvargasisaza@gmail.com"),
    "alejandro":  os.environ.get("EMAIL_ALEJANDRO",  ""),
    "miguel":     os.environ.get("EMAIL_MIGUEL",     ""),
    "felipe":     os.environ.get("EMAIL_FELIPE",     ""),
    "valentina":  os.environ.get("EMAIL_VALENTINA",  ""),
    "mayra":      os.environ.get("EMAIL_MAYRA",      ""),
    "evelin":     os.environ.get("EMAIL_EVELIN",     ""),
    "gisseth":    os.environ.get("EMAIL_GISSETH",    ""),
    "laura":      os.environ.get("EMAIL_LAURA",      ""),
}

# Mapeo area -> usuarios responsables. Usado por modulo Comunicacion para
# permitir asignacion masiva a un area completa (todas las personas que
# operan ese dominio reciben la tarea/notificacion).
AREA_USERS = {
    "Produccion":     ["evelin", "luz", "alejandro"],
    "Calidad":        ["laura", "gisseth", "alejandro"],
    "Tecnica":        ["hernando", "miguel", "alejandro"],
    "Compras":        ["catalina", "mayra", "alejandro"],
    "Marketing":      ["jefferson", "felipe", "daniela"],
    "Comercial":      ["daniela", "valentina", "luz"],
    "Gerencia":       ["sebastian", "alejandro", "luz"],
    "RRHH":           ["mayra", "alejandro"],
    "Financiero":     ["mayra", "catalina", "sebastian", "alejandro"],
    "Contabilidad":   ["mayra", "catalina"],
    "Animus":         ["daniela", "alejandro"],
    "Espagiria":      ["luz", "alejandro"],
}


def validate_config():
    """Valida configuración de seguridad al startup.

    No crashea la app — emite warnings estructurados (JSON line) que aparecen
    en los logs de Render/Datadog. El admin los ve y puede priorizar el fix
    sin que se caiga producción.

    Retorna lista de issues encontrados (cada uno: dict con severity, code, msg).
    """
    import json as _json
    import logging as _logging
    from datetime import datetime as _dt, timezone as _tz

    issues = []

    # SECRET_KEY
    if not os.environ.get("SECRET_KEY"):
        issues.append({
            "severity": "CRITICAL",
            "code": "MISSING_SECRET_KEY",
            "msg": "SECRET_KEY no definido en env. Sesiones falsificables. "
                   "Defínelo en Render → Environment con un valor aleatorio "
                   "(>= 32 chars). Ej: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
        })

    # Passwords: detectar plaintext, faltantes (env var no configurada),
    # y usar hash legacy. Sin hash → usuario no puede entrar.
    missing_users = []
    plaintext_users = []
    for user, pwd in COMPRAS_USERS.items():
        if not pwd:
            missing_users.append(user)
        elif pwd in _INSECURE_PLAINTEXT_DEFAULTS:
            plaintext_users.append(user)
        elif not (pwd.startswith("pbkdf2:") or pwd.startswith("scrypt:")):
            # Password custom pero plaintext (no hash) — alguien pegó el
            # password en lugar del hash en la env var. Inseguro.
            plaintext_users.append(user)

    if missing_users:
        issues.append({
            "severity": "HIGH",
            "code": "MISSING_USER_PASSWORD",
            "msg": f"{len(missing_users)} usuario(s) sin password configurada "
                   f"(env var PASS_<USER> ausente). Estos usuarios NO pueden "
                   f"entrar hasta que se configure su variable en Render. "
                   f"Usuarios afectados: {', '.join(missing_users)}"
        })

    if plaintext_users:
        issues.append({
            "severity": "CRITICAL",
            "code": "PLAINTEXT_PASSWORDS",
            "msg": f"{len(plaintext_users)} usuario(s) con password en plaintext "
                   f"en env vars. Las PASS_<USER> deben ser hashes pbkdf2: o "
                   f"scrypt:. Corre 'python scripts/gen_password_hashes.py' y "
                   f"pega los hashes (no las passwords) en Render → Environment. "
                   f"Usuarios afectados: {', '.join(plaintext_users)}"
        })

    # FORMULA_PIN
    if globals().get("_FORMULA_PIN_INSECURE"):
        issues.append({
            "severity": "MEDIUM",
            "code": "MISSING_FORMULA_PIN",
            "msg": "FORMULA_PIN no definido (o usa fallback público '7531'). "
                   "Se generó un PIN aleatorio efímero — el desbloqueo de "
                   "fórmulas no funcionará hasta definir FORMULA_PIN en Render."
        })

    # API keys de servicios externos (advertencia, no crítico)
    optional_keys = {
        "ANTHROPIC_API_KEY": "Agencia Ads no funcionará",
        "GHL_API_KEY":       "GoHighLevel sync deshabilitado",
        "SHOPIFY_TOKEN":     "Shopify sync deshabilitado",
        "INSTAGRAM_TOKEN":   "Instagram sync deshabilitado",
        "META_APP_ID":       "Meta refresh token deshabilitado",
        "EMAIL_PASSWORD":    "Notificaciones por email deshabilitadas",
        "SENTRY_DSN":        "Alertas proactivas de errores deshabilitadas",
    }
    missing_optional = [
        f"{k} ({desc})"
        for k, desc in optional_keys.items()
        if not os.environ.get(k)
    ]
    if missing_optional:
        issues.append({
            "severity": "INFO",
            "code": "MISSING_INTEGRATIONS",
            "msg": f"{len(missing_optional)} integración(es) opcional(es) sin "
                   f"credenciales: {'; '.join(missing_optional)}"
        })

    # Loguear cada issue como línea JSON estructurada
    logger = _logging.getLogger("inventario.config")
    for issue in issues:
        log_entry = {
            "ts":       _dt.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level":    issue["severity"],
            "category": "config_validation",
            **issue,
        }
        if issue["severity"] in ("CRITICAL", "HIGH"):
            logger.error(_json.dumps(log_entry, ensure_ascii=False))
        else:
            logger.warning(_json.dumps(log_entry, ensure_ascii=False))

    return issues
