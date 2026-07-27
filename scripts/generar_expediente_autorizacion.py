#!/usr/bin/env python3
"""Genera `EXPEDIENTE_AUTORIZACION_EOS.md` · el documento que pide la Dirección Técnica.

Sebastián 26-jul-2026: *"el director técnico, para permitir el uso de la app e ir implementando,
pide que le envíe como la matriz de aprobación, qué se permite a cada usuario, cómo es todo lo de
INVIMA y seguridad, y un manual de uso e instructivo donde se explique todo. Me pide un documento
con eso para autorizar el uso."*

Es el expediente estándar que un director técnico necesita antes de autorizar un sistema
computarizado en un entorno GMP: control de accesos, integridad de datos y manual de operación.

**Por qué GENERADO y no escrito a mano.** Un documento de control de accesos escrito a mano queda
desactualizado el día que alguien cambia un permiso, y un documento de cumplimiento que no
coincide con el sistema es peor que no tenerlo: la Dirección Técnica autoriza sobre algo que no
es. Acá los roles salen de `config.py`, los gates del `url_map` REAL de Flask, y los controles de
integridad de `pg_triggers.sql` y del código. Se vuelve a correr y queda al día:

    python scripts/generar_expediente_autorizacion.py

**Lo que este documento NO dice.** No dice que EOS esté validado. Tener los controles
implementados y verificables es una cosa; la validación formal de un sistema computarizado
(GAMP 5 / anexo 11) es otra, la hace un tercero y todavía está pendiente. El documento lo declara
explícitamente en su propia sección, porque ayudar a que alguien autorice sobre una premisa falsa
sería el peor resultado posible de este trabajo.
"""
import ast
import io
import os
import re
import sys
from collections import defaultdict

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, 'api'))
os.environ.setdefault('DB_PATH', os.path.join(RAIZ, '_expediente_tmp.db'))
os.environ.setdefault('EOS_DISABLE_DAEMONS', '1')

SALIDA = os.path.join(RAIZ, 'EXPEDIENTE_AUTORIZACION_EOS.md')

# Personas del sistema · el cargo lo define el negocio, no el código, así que va acá y se revisa
# a mano. Si aparece alguien en config.py que no esté en esta tabla, el documento lo señala en vez
# de omitirlo (una persona con acceso y sin cargo declarado es justo lo que hay que ver).
CARGOS = {
    'sebastian': 'Dirección General',
    'alejandro': 'Dirección / Socio',
    'hernando': 'Director Técnico',
    'miguel': 'Aseguramiento de Calidad',
    'laura': 'Jefe de Control de Calidad',
    'yuliel': 'Analista de Control de Calidad',
    'catalina': 'Asistente de Compras',
    'mayra': 'Contadora',
    'gloria': 'Gestión Humana',
    'daniela': 'Asistente',
    'luz': 'Comercial / B2B',
    'felipe': 'Marketing',
    'jefferson': 'Marketing',
    'mayerlin': 'Operaria de Dispensación',
    'camilo': 'Operario de Producción',
    'sergio': 'Operario de Producción',
    'smurillo': 'Operario de Producción',
    'jose': 'Jefe de Producción',
    'milton': 'Operario de Envasado',
    'luis': 'Operario (retirado · acceso desactivado)',
}

# Módulos del sistema en el lenguaje de la planta, y de qué conjunto de config.py dependen.
MODULOS = [
    ('Fórmulas maestras (receta)', 'FORMULAS_VER_USERS',
     'Ver la composición y los porcentajes de cada producto'),
    ('Batch record electrónico (legajo de lote)', 'PLANTA_USERS|CALIDAD_USERS|ADMIN_USERS',
     'Ejecutar los pasos del lote: despeje, pesaje, envasado, controles'),
    ('Control de Calidad', 'CALIDAD_USERS', 'Liberar o rechazar lotes, registrar CoA e IPC'),
    ('Aseguramiento de Calidad', 'ASEGURAMIENTO_USERS',
     'Desviaciones, CAPA, control de cambios, calificación de equipos'),
    ('Dirección Técnica', 'TECNICA_USERS', 'Aprobar procedimientos maestros (MBR) y dar visto bueno'),
    ('Planta / Producción', 'PLANTA_USERS', 'Programar, iniciar y cerrar producciones'),
    ('Compras y proveedores', 'COMPRAS_ACCESS', 'Solicitudes, órdenes de compra, recepción'),
    ('Autorización de órdenes de compra', 'OC_AUTORIZA_USERS',
     'Autorizar y pagar OC (con límite · ver segregación de funciones)'),
    ('Liberación de materia prima', 'MP_LIBERA_USERS', 'Pasar una MP de cuarentena a disponible'),
    ('Gestión humana', 'RRHH_USERS', 'Nómina y datos de personal'),
    ('Marketing', 'MARKETING_USERS', 'Campañas y contenido (sin acceso a datos regulados)'),
    ('Administración del sistema', 'ADMIN_USERS',
     'Configuración, correcciones auditadas, gestión de usuarios'),
]


def _conjuntos():
    import config as C
    out = {}
    for n in dir(C):
        v = getattr(C, n)
        if n.endswith('_USERS') or n == 'COMPRAS_ACCESS':
            if isinstance(v, (set, frozenset, list, tuple)):
                out[n] = set(v)
    return out


def _resolver(expr, conj):
    """'A|B' → unión de los conjuntos."""
    r = set()
    for parte in expr.split('|'):
        r |= conj.get(parte.strip(), set())
    return r


def _gates_por_ruta():
    """El control de accesos medido, REUSANDO el generador que ya lo hace bien.

    Primero intenté recalcularlo acá y salió mal: todas las rutas quedaron en `?` y el documento
    igual imprimió "ninguna función queda sin control de acceso" — una medición rota que se lee
    como un visto bueno, que es el peor resultado posible en un documento de cumplimiento. La
    forma correcta es no duplicar la lógica (M1): se corre `generar_mapa_permisos.py`, que lee el
    `url_map` real, y se lee su tabla resumen. Si algo falla, se dice; no se inventa un número.
    """
    import subprocess
    mapa = os.path.join(RAIZ, 'MAPA_PERMISOS.md')
    try:
        subprocess.run([sys.executable, os.path.join(RAIZ, 'scripts', 'generar_mapa_permisos.py')],
                       cwd=RAIZ, capture_output=True, timeout=300)
    except Exception as e:
        return None, 'no se pudo regenerar el mapa de permisos: %s' % str(e)[:100]
    if not os.path.exists(mapa):
        return None, 'no existe MAPA_PERMISOS.md'
    s = io.open(mapa, encoding='utf-8').read()
    conteo = {}
    m = re.search(r'## Resumen\s*\n\s*\n\|.*?\n\|[-\s|:]+\n((?:\|.*\n)+)', s)
    if m:
        for fila in m.group(1).strip().splitlines():
            celdas = [c.strip() for c in fila.strip().strip('|').split('|')]
            if len(celdas) >= 3 and celdas[1].isdigit():
                conteo[celdas[0].strip('`'), celdas[2]] = int(celdas[1])
    # rutas sin ningún gate (la sección que el mapa ya calcula)
    sin_gate = []
    m2 = re.search(r'## 🚨 Rutas SIN NINGÚN gate.*?\n\|.*?\n\|[-\s|:]+\n((?:\|.*\n)*)', s, re.S)
    if m2:
        for fila in m2.group(1).strip().splitlines():
            celdas = [c.strip() for c in fila.strip().strip('|').split('|')]
            if celdas and celdas[0].startswith('`'):
                sin_gate.append(celdas[0].strip('`'))
    if not conteo:
        return None, 'no se pudo leer la tabla resumen de MAPA_PERMISOS.md'
    return (conteo, sin_gate), None


def _controles_integridad():
    """Los controles que sostienen Part 11, contados sobre el código real."""
    out = {}
    triggers = []
    p = os.path.join(RAIZ, 'api', 'pg_triggers.sql')
    if os.path.exists(p):
        s = io.open(p, encoding='utf-8').read()
        triggers = sorted(set(re.findall(r'trg_[a-z0-9_]+', s)))
    out['triggers'] = triggers
    out['triggers_audit'] = [t for t in triggers if 'audit' in t]
    out['triggers_inmutable'] = [t for t in triggers
                                 if any(k in t for k in ('no_edit', 'no_delete', 'inmut', 'liberado'))]
    n_audit = n_sign = 0
    for base, _, files in os.walk(os.path.join(RAIZ, 'api')):
        if '__pycache__' in base:
            continue
        for f in files:
            if not f.endswith('.py'):
                continue
            try:
                s = io.open(os.path.join(base, f), encoding='utf-8').read()
            except OSError:
                continue
            n_audit += len(re.findall(r'\baudit_log\(', s))
            n_sign += len(re.findall(r'e_signatures', s))
    out['audit_calls'] = n_audit
    out['esign_refs'] = n_sign
    mig = os.path.join(RAIZ, 'api', 'database.py')
    out['migraciones'] = len(re.findall(r'^\s*\(\d+,\s*"', io.open(mig, encoding='utf-8').read(), re.M))
    tests = os.path.join(RAIZ, 'tests')
    out['archivos_test'] = len([f for f in os.listdir(tests) if f.startswith('test_')]) \
        if os.path.isdir(tests) else 0
    return out


def main():
    conj = _conjuntos()
    ctrl = _controles_integridad()
    gates, err_gates = _gates_por_ruta()

    L = []
    A = L.append
    A('# Expediente de autorización de uso · EOS')
    A('')
    A('**Sistema:** EOS · Sistema de gestión de producción, inventarios y calidad')
    A('**Empresa:** ÁNIMUS Lab · Espagiria Laboratorio SAS')
    A('**Destinatario:** Dirección Técnica')
    A('**Propósito:** aportar la información necesaria para decidir la autorización de uso.')
    A('')
    A('> **Documento GENERADO desde el código fuente del sistema.** Los roles salen de la')
    A('> configuración real, los permisos por ruta del enrutador real de la aplicación, y los')
    A('> controles de integridad de los disparadores reales de la base de datos. Se regenera con')
    A('> `python scripts/generar_expediente_autorizacion.py`. Un documento de accesos escrito a')
    A('> mano queda desactualizado el día que alguien cambia un permiso, y uno que no coincide con')
    A('> el sistema es peor que no tenerlo.')
    A('')
    A('---')
    A('')
    A('## 1 · Alcance y estado de validación · LEER PRIMERO')
    A('')
    A('EOS **no cuenta con validación formal de sistema computarizado** (GAMP 5 / PIC-S Anexo 11)')
    A('realizada por un tercero independiente. Eso está pendiente y es una tarea aparte.')
    A('')
    A('Lo que este documento sí acredita es que **los controles de integridad de datos exigidos por')
    A('21 CFR Part 11 están implementados y son verificables en el código**: rastro de auditoría')
    A('inmutable, firma electrónica con identidad, control de accesos por rol y bloqueo de edición')
    A('sobre registros liberados. Cada afirmación de la sección 3 dice **dónde** se hace cumplir,')
    A('para que pueda comprobarse y no haya que creer en la palabra de nadie.')
    A('')
    A('La decisión de autorizar un uso progresivo con estos controles, mientras se gestiona la')
    A('validación formal, es de la Dirección Técnica. Este documento existe para que esa decisión')
    A('se tome con la información completa, incluido lo que falta.')
    A('')
    A('---')
    A('')
    A('## 2 · Matriz de accesos y aprobaciones')
    A('')
    A('### 2.1 · Qué habilita cada módulo, y a quién')
    A('')
    A('| Módulo | Qué permite | Personas autorizadas |')
    A('|---|---|---|')
    faltan_cargo = set()
    for nombre, expr, desc in MODULOS:
        gente = sorted(_resolver(expr, conj))
        for g in gente:
            if g not in CARGOS:
                faltan_cargo.add(g)
        etiquetas = ', '.join('%s (%s)' % (g, CARGOS.get(g, 'CARGO NO DECLARADO')) for g in gente) or '—'
        A('| **%s** | %s | %s |' % (nombre, desc, etiquetas))
    A('')
    if faltan_cargo:
        A('> ⚠ **Personas con acceso y sin cargo declarado en este documento:** %s.'
          % ', '.join(sorted(faltan_cargo)))
        A('> Hay que asignarles cargo o retirarles el acceso antes de autorizar.')
        A('')
    A('### 2.2 · Qué firma cada quién')
    A('')
    A('La firma electrónica es nominal: queda registrada la persona, su cargo y su cédula al')
    A('momento de firmar, junto con el significado de la firma. No es un "aprobado" anónimo.')
    A('')
    A('| Acto | Quién lo firma | Registro donde queda |')
    A('|---|---|---|')
    A('| Aprobación del procedimiento maestro (MBR) | Dirección Técnica | `e_signatures` + `audit_log` |')
    A('| Liberación de materia prima | Control de Calidad | `e_signatures` + kardex |')
    A('| Liberación de lote de producto terminado | Control de Calidad | `e_signatures` + `ebr_ejecuciones` |')
    A('| Rechazo de lote | Control de Calidad | `e_signatures` + degradación del PT |')
    A('| Verificación del despeje de línea | Operario registra · Calidad corrige | `ebr_despeje_items` |')
    A('| Autorización de orden de compra | Compras (con límite) | `audit_log` |')
    A('')
    A('### 2.3 · Segregación de funciones')
    A('')
    A('| Control | Cómo está resuelto |')
    A('|---|---|')
    A('| Quien produce no libera | Producción ejecuta el lote; sólo Control de Calidad lo libera |')
    A('| Quien aprueba el procedimiento no lo ejecuta | La Dirección Técnica aprueba el MBR; Planta ejecuta el EBR |')
    A('| Límite de gasto | Las órdenes por encima del límite las autoriza Dirección |')
    A('| Corrección de un registro firmado | No se edita: se registra una enmienda con motivo, autor y fecha |')
    A('')
    # ── Conflictos detectados automáticamente ────────────────────────────────────────────────
    # Se calculan cruzando los conjuntos de config.py en vez de escribirlos a mano: un conflicto
    # que depende de que alguien se acuerde de anotarlo, tarde o temprano no se anota. La Dirección
    # Técnica tiene que ver esto ANTES de autorizar, no descubrirlo en una auditoría.
    compras = conj.get('COMPRAS_ACCESS', set()) | conj.get('CONTADORA_USERS', set())
    admin = conj.get('ADMIN_USERS', set())
    conflictos = []
    for quien in sorted((compras & conj.get('MP_LIBERA_USERS', set())) - admin):
        conflictos.append((
            quien, CARGOS.get(quien, '?'),
            'Compra la materia prima **y** la libera de cuarentena',
            'La Resolución 2214/2021 art. 10 asigna la disposición del lote a Calidad. Hoy quien '
            'gestiona la compra también decide si el material entra a producción.',
            'Sacar a la persona de `MP_LIBERA_USERS` y dejar la liberación en Control de Calidad. '
            'Es reversible: es un conjunto en `config.py`.'))
    for quien in sorted((conj.get('OC_AUTORIZA_USERS', set()) & conj.get('CONTADORA_USERS', set())) - admin):
        conflictos.append((
            quien, CARGOS.get(quien, '?'),
            'Autoriza la orden de compra **y** registra el pago',
            'Concentra autorización y ejecución del desembolso.',
            'Decisión de gerencia ya tomada, con el rastro de auditoría como control '
            'compensatorio: cada autorización y cada pago quedan registrados con autor y fecha.'))
    for quien in sorted((conj.get('PLANTA_USERS', set()) & conj.get('CALIDAD_USERS', set())) - admin):
        conflictos.append((
            quien, CARGOS.get(quien, '?'),
            'Ejecuta el lote **y** puede liberarlo',
            'Quien fabrica no debería aprobar su propio trabajo.',
            'Separar los conjuntos `PLANTA_USERS` y `CALIDAD_USERS` para esa persona.'))
    A('#### Conflictos de segregación detectados en la configuración actual')
    A('')
    if conflictos:
        A('El sistema **detecta y declara** estos cruces; no están ocultos. Requieren una decisión')
        A('explícita de la Dirección Técnica antes de autorizar el uso.')
        A('')
        A('| Persona | Cargo | Conflicto | Por qué importa | Cómo se resuelve |')
        A('|---|---|---|---|---|')
        for c in conflictos:
            A('| **%s** | %s | %s | %s | %s |' % c)
        A('')
    else:
        A('No se detectan cruces de funciones incompatibles en la configuración actual.')
        A('')
    # Personas con rol asignado pero acceso desactivado: no son un conflicto, pero la matriz
    # tiene que decirlo o parece que un retirado conserva permisos.
    retirados = sorted(q for q, c in CARGOS.items() if 'retirado' in c.lower())
    con_rol = set()
    for _, expr, _ in MODULOS:
        con_rol |= _resolver(expr, conj)
    ret_con_rol = [q for q in retirados if q in con_rol]
    if ret_con_rol:
        A('> ⚠ **%s** figura(n) todavía en conjuntos de rol de `config.py` pese a estar dado(s) de'
          % ', '.join(ret_con_rol))
        A('> baja. El acceso está bloqueado a nivel de contraseña (no puede iniciar sesión), pero')
        A('> conviene retirarlo de los roles para que la matriz no muestre permisos de una persona')
        A('> que ya no está.')
        A('')
    A('---')
    A('')
    A('## 3 · Integridad de datos y cumplimiento')
    A('')
    A('Cada control indica dónde se hace cumplir, para que sea comprobable.')
    A('')
    A('| Requisito | Cómo lo cumple EOS | Dónde se verifica |')
    A('|---|---|---|')
    A('| **Rastro de auditoría** (§11.10 e) | Toda operación sobre inventario, lotes, órdenes y '
      'registros de calidad deja usuario, acción, fecha y valores antes/después | `audit_log` · '
      '**%d** puntos de registro en el código |' % ctrl['audit_calls'])
    A('| **Rastro inalterable** | El propio rastro **no se puede editar ni borrar**, ni siquiera '
      'por un administrador: lo impide la base de datos | Disparadores `%s` |'
      % '`, `'.join(ctrl['triggers_audit'] or ['(no encontrados)']))
    A('| **Firma electrónica** (§11.50) | Firma nominal con nombre, cargo y cédula capturados al '
      'firmar, más el significado del acto | `e_signatures` · **%d** referencias en el código |'
      % ctrl['esign_refs'])
    A('| **Registros liberados inmutables** | Un lote liberado o rechazado no admite cambios en sus '
      'pasos, pesajes ni controles | **%d** disparadores de inmutabilidad |'
      % len(ctrl['triggers_inmutable']))
    A('| **Control de accesos** (§11.10 d) | Cada función exige un rol; no alcanza con tener sesión '
      'iniciada | Sección 2 · verificado sobre el enrutador real |')
    A('| **Datos exactos y completos** (ALCOA+) | El inventario se calcula sumando los movimientos '
      'del kardex, nunca un total guardado que pueda desviarse | `movimientos` / `movimientos_mee` |')
    A('| **Trazabilidad del lote** | De producto terminado a materia prima y viceversa, con sus '
      'documentos | Expediente por lote · `documentos_regulados` |')
    A('| **Control de cambios del sistema** | Cada cambio de esquema queda numerado y registrado | '
      '**%d** migraciones registradas |' % ctrl['migraciones'])
    A('| **Verificación continua** | Batería automática que se ejecuta antes de cada publicación | '
      '**%d** archivos de prueba |' % ctrl['archivos_test'])
    A('')
    if gates:
        conteo, sin_gate = gates
        A('### 3.1 · Control de accesos medido sobre el sistema real')
        A('')
        A('Medido recorriendo el enrutador real de la aplicación, no una lista escrita a mano.')
        A('')
        A('| Nivel de acceso | Quién entra | Funciones |')
        A('|---|---|---:|')
        for (gate, quien), v in sorted(conteo.items(), key=lambda x: -x[1]):
            A('| `%s` | %s | %d |' % (gate, quien or '—', v))
        A('')
        if sin_gate:
            A('> ⚠ **%d función(es) sin control de acceso.** Deben revisarse antes de autorizar:'
              % len(sin_gate))
            for r in sin_gate[:20]:
                A('> - `%s`' % r)
        else:
            A('> **Ninguna función queda sin control de acceso.**')
        A('')
    elif err_gates:
        A('> ⚠ No se pudo medir el control de accesos automáticamente (%s). Ver `MAPA_PERMISOS.md`.'
          % err_gates[:120])
        A('')
    A('---')
    A('')
    A(MANUAL)
    A('')
    A('---')
    A('')
    A('## 6 · Constancia')
    A('')
    A('Documento generado automáticamente desde el código fuente de EOS.')
    A('Regenerar con `python scripts/generar_expediente_autorizacion.py` después de cualquier')
    A('cambio de permisos, para que la matriz siga reflejando el sistema.')
    A('')
    A('| | Nombre | Cargo | Fecha | Firma |')
    A('|---|---|---|---|---|')
    A('| Elabora | | | | |')
    A('| Revisa | | Aseguramiento de Calidad | | |')
    A('| **Autoriza el uso** | | **Dirección Técnica** | | |')

    with io.open(SALIDA, 'w', encoding='utf-8', newline='') as fh:
        fh.write('\n'.join(L) + '\n')
    print('Generado: %s (%d líneas)' % (SALIDA, len(L)))
    if faltan_cargo:
        print('⚠ personas con acceso y sin cargo declarado: %s' % ', '.join(sorted(faltan_cargo)))


MANUAL = """## 4 · Manual de uso por rol

El sistema se usa distinto según el puesto. Cada rol ve sólo lo que necesita.

### 4.1 · Operario de producción

1. **Abrir la orden del día** en Planta › Producción. Cada orden muestra el producto, el lote,
   cuánto avanzó y hace cuántos días está abierta.
2. **Despeje de línea.** Antes de tocar nada se recorren las 12 verificaciones, en el orden en que
   están: primero que no quede nada del producto anterior, después limpieza, después los rótulos y
   formatos, y al final las condiciones, los equipos y el elemento de protección personal. Cada una
   se marca Sí o No; un No abre el aviso correspondiente.
3. **Pesaje.** El sistema muestra la cantidad teórica de cada materia prima calculada sobre el
   tamaño real del lote. Se registra lo pesado; la diferencia queda a la vista.
4. **Ejecutar los pasos** del procedimiento en orden. Cada paso se inicia y se cierra; queda
   registrado quién lo hizo y cuándo.
5. **Envasado.** Se registran las unidades realmente obtenidas de cada presentación. Si una
   presentación no salió, se marca como no envasada indicando el motivo: dejarla en cero no sirve,
   porque no distingue "todavía no conté" de "no salió ninguna".
6. **Cerrar.** Al cerrar el envasado el sistema descuenta del inventario el frasco y todas sus
   piezas (tapa, caja, gotero) por las unidades registradas.

**Lo que un operario no puede hacer:** liberar un lote, aprobar un procedimiento, ver las fórmulas
maestras ni modificar un registro ya firmado.

### 4.2 · Control de Calidad

1. **Recepción de materia prima.** Todo lo que entra queda en cuarentena. Calidad revisa y libera
   o rechaza; hasta que no libere, esa materia prima no se puede usar en producción: el sistema la
   excluye del cálculo de disponible.
2. **Controles en proceso.** Se registran los valores medidos contra la especificación. Un
   resultado fuera de especificación abre una desviación automáticamente y bloquea la liberación.
3. **Liberación del lote.** Requiere firma electrónica. El sistema no deja liberar si hay una
   desviación abierta, un control fuera de especificación o un paso obligatorio sin ejecutar.
4. **Corrección de un registro.** Un resultado ya registrado sólo lo corrige Calidad o Dirección
   Técnica, y la corrección queda como enmienda: se conserva el valor anterior, el motivo y el
   autor.

### 4.3 · Dirección Técnica

1. **Aprobar el procedimiento maestro (MBR)** de cada producto. Una vez aprobado **no se puede
   modificar**: para cambiarlo se obsoleta la versión y se crea la siguiente. Los lotes en curso
   siguen con la versión con la que empezaron.
2. **Visto bueno** en los puntos del proceso que lo requieren.
3. **Consultar el expediente de cualquier lote**: materias primas y sus lotes, quién hizo cada
   paso, controles, desviaciones y documentos, en una sola pantalla.

### 4.4 · Compras

1. **Necesidades.** El sistema calcula qué falta cruzando el plan de producción con la fórmula de
   cada producto y el inventario disponible, descontando lo que ya está pedido.
2. **Solicitud y orden de compra.** Con autorización según el monto.
3. **Recepción.** Lo recibido entra en cuarentena a nombre de Calidad.

### 4.5 · Dirección

Acceso completo, incluidas las correcciones administrativas. **Toda corrección queda auditada**:
el administrador puede corregir un error, pero no puede hacerlo sin dejar rastro.

---

## 5 · Instructivo: reglas de operación que el sistema hace cumplir

Estas no son recomendaciones; el sistema las impide.

| Regla | Qué pasa si se intenta |
|---|---|
| No se produce con materia prima en cuarentena | El sistema la excluye del disponible y bloquea el inicio |
| No se produce con materia prima vencida | El descuento la rechaza aunque el estado no se haya actualizado |
| Un procedimiento aprobado no se modifica | La base de datos rechaza el cambio |
| Un lote liberado no se modifica | La base de datos rechaza el cambio |
| El rastro de auditoría no se borra | La base de datos rechaza el borrado y la edición |
| Un lote con desviación abierta no se libera | La liberación se bloquea con el motivo |
| No se descuenta dos veces el mismo material | Reclamo atómico: la segunda vez se rechaza |
| Una anulación no deja el inventario descuadrado | Se registra el movimiento inverso, nunca se borra el original |

**Qué hacer cuando el sistema bloquea algo.** El bloqueo indica la causa concreta. No hay forma de
saltarlo desde la pantalla, y es deliberado: si un control se pudiera omitir con un clic, no sería
un control. Cuando una situación legítima queda bloqueada, se resuelve corrigiendo la causa (por
ejemplo, liberando la materia prima que falta), no anulando la verificación.
"""


if __name__ == '__main__':
    main()
