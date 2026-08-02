# CONTRACT · `programacion.py`

> **Para agentes IA · LEER ANTES de modificar este blueprint.**

Última revisión: 2026-06-06 (Rótulo virtual de limpieza PRD-PRO-002-F02 · mig 223)

---

## Tablas que ESCRIBE

| Tabla | Operación | Cuándo |
|---|---|---|
| `produccion_programada` | INSERT | Sync Calendar, manual nueva |
| `produccion_programada` | UPDATE | Iniciar, cambiar área, descontar inventario |
| `produccion_programada` | DELETE | Limpiar duplicados, espejo Calendar, admin borra |
| `areas_planta` | UPDATE estado | Iniciar (→ocupada), terminar (→sucia), rótulo realizar (→limpiando) |
| `rotulos_limpieza` | INSERT/UPDATE | Rótulo de limpieza F02 · operario realiza · Calidad verifica (mig 223) |
| `area_eventos` | INSERT | Bitácora de transiciones de estado de sala |
| `solicitudes_compra` | INSERT | Bulk solicitar faltantes (agrupado por proveedor) |
| `solicitudes_compra_items` | INSERT | Faltantes detectados |
| `mp_lead_time_config` | INSERT/UPDATE | Configuración manual o sync desde compras |
| `produccion_checklist` | INSERT/UPDATE/DELETE | Pre-producción items |
| `movimientos` | INSERT | Salida MP al iniciar/completar (con `produccion_id`); Entrada compensatoria al revertir |
| `_sync_log` | INSERT | Cada corrida del sync Calendar |
| `audit_log` | INSERT | Operaciones destructivas + crear producción (`CREAR_PRODUCCION_PROGRAMADA`) |

## Tablas que LEE

- TODAS las del módulo + `formula_headers`, `formula_items`,
  `sku_producto_map`, `maestro_mps`, `maestro_mee`, `sku_mee_config`,
  `volumen_unitario_producto`, `areas_planta`, `operarios_planta`.

## APIs externas que llama

- **Google Calendar** vía iCal (env `GCAL_ICAL_URL`) o API (env
  `GCAL_API_KEY`). Función: `_fetch_calendar_events(days_ahead)`.
- Devuelve `{events:[], error:str|None, source:str}`.
- Si error → NO destruir nada.

---

## Invariantes CRÍTICAS · NO romper

### INV-1 · Calendar = ÚNICA fuente de verdad
- App lee Calendar, NO escribe.
- `produccion_programada` se sincroniza con Calendar.
- Si Calendar dice X y DB dice Y → Calendar gana.

### INV-2 · Sync respeta guard inicio/descontado
- `inicio_real_at` set → producción en curso, NO TOCAR jamás.
- `inventario_descontado_at` set → ya descontó MPs, NO TOCAR.
- Si Calendar borra un evento que ya estaba en curso, audit_log
  `SYNC_CALENDAR_SKIP_EN_CURSO` y dejar para revisión manual.

### INV-3 · force_mirror solo lo dispara user explícito
- Default behavior (`force_mirror=False`): solo cancela `origen='calendar'`.
- `force_mirror=True`: HARD DELETE de cualquier orfan (manual + calendar).
- Solo se dispara desde el botón "📅 Re-sync Calendar" (admin).

### INV-4 · Rótulo de limpieza F02 · estado y liberación
- **Estado físico de la sala = `areas_planta.estado`** (libre/ocupada/sucia/
  limpiando). El rótulo lo MAPEA a Limpio/En uso/Sucio para mostrar — NO crea
  estado paralelo. `rotulos_limpieza` solo guarda el registro F02 (snapshot
  inmutable Part 11): producto/lote, sanitizante, equipos, y las dos firmas.
- **Una sola ruta de liberación `sucia/limpiando → libre`** (M3):
  `auto_plan.liberar_sala_con_despeje()` (inserta `despeje_linea_checklist` +
  marca libre). La usan tanto `marcar-limpia-con-despeje` como el endpoint
  `rotulo-limpieza/<area_id>/verificar`. NO crear una segunda ruta a `libre`.
- **Dos roles** (PRD-PRO-002): operario `realizar` (sucia→limpiando, e-firma no
  requerida) · Calidad `verificar` (limpiando→libre, **e-firma `meaning='revisa'`
  obligatoria** validada con `_validar_e_sign`).
- Endpoints: `GET/POST /api/planta/rotulo-limpieza/<area_id>[/realizar|/verificar]`,
  imprimible `GET /planta/rotulo-limpieza/<area_id>/pdf`. Tests:
  `tests/test_rotulo_limpieza.py`.
- Background cron NUNCA debe pasar force_mirror=True.

### INV-4 · Idempotencia
- INSERT a `produccion_programada` idempotente por `(producto, fecha_programada)`.
- INSERT a `_sync_log` registra timestamp de cada corrida.

### INV-5 · Faltantes calculados en kardex
- `/producciones-faltantes` usa `_get_mp_stock(conn)` (NO query directo a tabla).
- Aggregación por `material_id` + nombre normalizado (acentos, etc.).

### INV-6 · Fijo vs Sugerido en `produccion_programada` (19-may-2026)
- **Fijo**: `origen IN ('eos_plan', 'eos_b2b', 'eos_retroactivo')`. Lo que el
  usuario arrastró/editó, pedidos B2B, backfills. **Intocable** por procesos
  automáticos.
- **Sugerido**: `origen IN ('eos_canonico', 'calendar', 'manual', 'auto_plan',
  'sugerido')`. Mutable por regeneradores.
- Cualquier UPDATE/DELETE bulk en `produccion_programada` que no sea
  iniciado-por-usuario-explícito debe incluir
  `AND COALESCE(origen,'') NOT IN ('eos_plan','eos_b2b','eos_retroactivo')`
  tanto en SELECT de candidatos como en el UPDATE/DELETE.
- `limpiar_duplicados_producciones` ahora hace **soft cancel** (UPDATE
  estado='cancelado' + observaciones marcadas) en lugar de DELETE duro, para
  preservar evidencia y permitir recuperación.
- Test que protege: `test_golden_limpiar_duplicados_respeta_fijo`.

### INV-8 · Solo operario asignado / jefe / admin puede iniciar/terminar/completar (19-may-2026)

`POST /api/programacion/programar/<id>/iniciar`, `/terminar` y `/completar` validan
con `_caller_puede_operar_produccion()`:
- `ADMIN_USERS` (sebastian / alejandro) → siempre OK
- `es_jefe_produccion=1` (Luis Enrique) → OK
- Operario mapeado desde `compras_user` cuyo `id` figure en uno de los 4
  `operario_*_id` de la producción → OK
- Cualquier otro caso → 403 con código `no_asignado`

Antes los endpoints solo chequeaban login → operario A descontaba MPs de
producciones asignadas a operario B. Test: `test_golden_operario_no_puede_iniciar_produccion_ajena`.

### INV-10 · Abastecimiento = Calendar completo (Fix #3 · 23-may-2026)

`abastecimiento_consumo_horizontes` (`/api/abastecimiento/consumo-horizontes`)
ahora lee TODO el Calendar, no solo Fijo. Sebastián: "el abastecimiento
debería ser tomado desde el calendario donde tenemos programado todo por
varios meses".

- **Default** (sin param): `origen IN ('eos_plan','eos_b2b','eos_retroactivo',
  'eos_canonico','auto_plan','sugerido')` · TODO lo del Calendar.
- **`?solo_fijo=1`** (legacy): solo `eos_plan/b2b/retroactivo`.
- Antes (`comprometido` default) → solo Fijo · causaba que Abastecimiento
  mostrara números distintos al Calendar (3 fuentes paralelas divergentes).
- Promoción a Fijo: REPROGRAMAR_PRODUCCION_PROGRAMADA y EDITAR_KG_PRODUCCION
  promueven Sugerida → eos_plan al moverla · sin duplicar consumo MP.

`modo=run_rate` sigue agregando proyección velocidad×días encima del Calendar
(para análisis what-if), descontando Calendar para evitar doble-conteo.

SELECT incluye `pp.origen` como 7° campo · unpack en ambos loops
(`for ... in prod_rows` líneas 8158 + 8303). Tests:
`test_golden_abastecimiento_consumo_horizontes` valida default + solo_fijo.

### INV-9 · `_auto_asignar_operarios` es atómico (todo-o-nada) (19-may-2026)

La función valida que los 4 roles tengan candidato antes de tocar la BD.
Si el pool no alcanza (todos fijos o jefes), aborta retornando `None` sin
modificar la producción, preservando el estado previo. El UPDATE final usa
valores absolutos (no COALESCE) porque los 4 están garantizados.

Antes el caller NULLeaba los 4 operarios ANTES de invocar el helper · si el
helper no podía llenar todos, quedaba la producción con roles parciales NULL.
Test: `test_golden_auto_asignar_operarios_no_deja_roles_null_parcial`.

### INV-7 · Auditoría bulk-mutaciones a `produccion_programada` (19-may-2026)

Auditoría completa post-incidente del 19-may. Lista de TODOS los puntos
que mutan en bulk + status. Si agregas uno nuevo, debe entrar acá.

| Endpoint / función | Tipo | ¿Respeta Fijo? | Notas |
|---|---|---|---|
| `programacion.py limpiar_duplicados_producciones` (~7211) | soft UPDATE | ✅ (commit b5edbc0) | era DELETE duro; fix 19-may |
| `programacion.py _sync_calendar_a_produccion_programada` espejo (~9222) | DELETE bulk | ✅ | `NOT IN (Fijos)` cuando `force_mirror=True` |
| `programacion.py _sync_calendar_a_produccion_programada` legacy (~9230) | UPDATE cancel | ✅ | solo `origen='calendar'` |
| `admin.py` SKU remapeado cleanup (~10356) | UPDATE cancel | ✅ | solo `origen='calendar'` |
| `admin.py limpiar_produccion_zombies` cancel-viejas (~21086) | DELETE | ✅ | filtra >30d cancelados (no afecta presente) |
| `admin.py limpiar_produccion_zombies` prog-viejas (~21094) | UPDATE cancel | ✅ | `NOT IN (Fijos)` + >7d sin iniciar |
| `admin.py limpiar_produccion_zombies` dedup gcal (~21116) | UPDATE cancel | ✅ | `NOT IN (Fijos)` |
| `plan.py limpiar_duplicados_plan` (~3702) | UPDATE cancel | ✅ | `origen IN (canonico,calendar,manual)` |
| `plan.py generar_plan_perfecto` (~3854) | UPDATE cancel | ✅ | `origen IN (canonico,calendar,manual)` |
| `plan.py regenerar_canonicos` (~4233) | UPDATE cancel | ✅ | `origen IN (canonico,calendar,manual)` |
| `plan.py aplicar_ia_bulk` (~10698) | UPDATE cancel | ✅ | `origen IN (canonico,calendar,manual)` |
| `plan.py aplicar_ia_anual` (~10869) | UPDATE cancel | ✅ | `origen IN (canonico,calendar,manual)` |

Single-row UPDATE/DELETE `WHERE id=?` son seguros por diseño (user-driven
explícito, con guard de `inicio_real_at`/`inventario_descontado_at` cuando
aplica). No necesitan filter por origen.

Tests goldens que protegen:
- `test_golden_plan_fijo_sobrevive_regenerar` (plan.py regeneradores)
- `test_golden_limpiar_duplicados_respeta_fijo` (programacion.py limpiar_duplicados)
- `test_golden_limpiar_duplicados_respeta_guard` (no toca iniciadas)

---

## Endpoints downstream que CONSUMEN sus datos

| Endpoint externo | Lee | Si rompo `programacion.py`... |
|---|---|---|
| Tab Plan en `/planta` | `/producciones-faltantes` | ...Luis Enrique no ve qué producir |
| `compras.py /agrupadas` | `solicitudes_compra_items` | ...Catalina ve duplicados |
| `auto_plan.py crons` | `produccion_programada`, `mp_lead_time_config` | ...IA propone mal |
| Operación Live | `produccion_programada` | ...turno arranca con info errada |

---

## Endpoints que expone

- `GET  /api/programacion/sugerencia-produccion?producto=X` · SOLO LECTURA · panel
  Programación v4: recordá (kg producidos mes pasado/año + `historial[]` fecha/kg/fuente,
  calendario+Fabricación dedup-por-día) + venta blended + horizontes kg 1/2/3 meses +
  guardrails ½×–2× (90d) + config (decisión guardada). Reusa `velocidad_blended_uds_dia`
  + `_factor_g_por_unidad_detalle` (paridad con Necesidades/cadencia · M70).
- `POST /api/programacion/decision-produccion` · Fase B paso 2 · GUARDA la decisión por
  producto (cadencia_dias/horizonte_dias/kg_objetivo_lote/mix_mode) en `sku_planeacion_config`
  (mig 350 · patch parcial · valida mix auto/crece/fijo · auditado · NO toca el calendario).
- `GET  /api/programacion/confrontar-calendario-productos` · SOLO LECTURA · cruza producción
  real (calendario+Fabricación) vs fórmulas activas → productos[] + huerfanos[] (nombres que
  no cruzan · M13/M37) + resumen. Diagnóstico de mapeo.
- `GET  /planta/programar` · PÁGINA (premium) · panel de programación por producto (recordá +
  historial + venta + kg 1/2/3 meses + guardar decisión). Lee sugerencia-produccion, escribe
  decision-produccion. NO toca el calendario.
- `GET  /api/programacion/producciones-faltantes` · vista plana
- `GET  /api/programacion/producciones-agrupadas` · una fila por producto
- `POST /api/programacion/solicitar-faltantes-bulk` · crea SOLs por proveedor
- `POST /api/programacion/limpiar-duplicados-producciones` · respeta guard
- `POST /api/programacion/checklist/sync-calendar` · sync · `?force_mirror=true`
- `DELETE /api/programacion/produccion-programada/<id>/borrar` · admin
- `GET  /api/programacion/debug-producto/<producto>` · diagnóstico admin
- `POST /api/planta/auto-asignar-hoy` · admin · bulk re-asignación IA del día
  (área + 4 operarios). Excluye orígenes Fijos · respeta lo Fijo · escribe
  `auto_asignacion_log` y `audit_log` (`AUTO_ASIGNAR_HOY_BULK`).

---

## Cambios recientes (post-mortems)

### 2026-05-07 · Sync espejo no borraba orfanos manuales
- **Bug**: filtro `WHERE origen='calendar'` excluía manuales.
- **Síntoma**: AZHC Lun 11 manual fantasma sobrevivía aunque Calendar
  lo movió a Jue 14.
- **Fix**: param `force_mirror=True` quita el filtro. UI lo dispara
  desde el botón explícito.
- **Test que cazaría**: `test_golden_sync_calendar_espejo_borra_orfan_manual`.

### 2026-05-07 · Sync early-return con events vacíos
- **Bug**: `if not events: return 0` impedía cleanup en force_mirror.
- **Síntoma**: en tests sin Calendar API, force_mirror no hacía nada.
- **Fix**: solo return early si hay error API (`cal.get('error')`).
  Events vacíos legítimos siguen al cleanup.

### 2026-05-12 · Hook auto-EBR al iniciar producción (Fase 1 BRD)
- `prog_iniciar_produccion` ahora llama `_intentar_crear_ebr_auto()`
  después del audit_log de INICIAR_PRODUCCION.
- Si hay MBR aprobado para el producto, crea EBR vinculado por
  `produccion_id` con pasos clonados (estado='pendiente').
- **NON-FATAL**: si falla la creación del EBR (excepción cualquiera),
  loguea warning pero NO bloquea el inicio de producción. Esto es
  invariante crítica: el flujo Mayerlin/operario aprieta 'Iniciar' NO
  debe romperse por bugs del BRD.
- Idempotente vs `produccion_id` (re-iniciar no duplica EBR).
- Lote auto-generado: `<prod-short>-<evento_id>-<YYYYMMDD>` (UTC).
- Response incluye campo `brd_ebr` con resultado.
- Tablas escritas adicionales (delegadas a brd.py vía cursor compartido):
  `ebr_ejecuciones`, `ebr_pasos_ejecutados`.
- **Test que cazaría regresión**:
  `test_golden_brd_hook_auto_ebr_al_iniciar_produccion`.

### 2026-05-28 · Reversión precisa de MP por `produccion_id` (mig 201)
- `revertir-completado` revertía las Salidas de MP filtrando por
  `observaciones LIKE 'Producción ... {producto} — {fecha}%'`. Dos
  producciones del MISMO producto+fecha colisionaban → revertir una
  devolvía el MP de ambas (inventario fantasma · drift +).
- **Mig 201**: `movimientos.produccion_id` (+ índice). Las Salidas de
  `_descontar_mp_produccion` (iniciar) y `prog_completar_evento` (completar)
  guardan `produccion_id = evento_id`.
- La reversión filtra por `produccion_id` EXACTO; el LIKE por texto queda
  solo como fallback para movimientos legacy (`produccion_id IS NULL`).
- Mismo patrón que ya usaba la reversión MEE vía `lote_ref`.
- **Test que cazaría regresión**:
  `test_revertir_completado_no_cross_reversal_mp`.

### 2026-05-29 · Auditoría ronda 2 · audit_log en mutaciones de produccion_programada
- **`prog_revertir_completado`**: agregado `audit_log(accion='REVERTIR_COMPLETADO')`
  antes del commit (operación inversa de COMPLETAR_PRODUCCION, regulada INVIMA).
- **`planta_aceptar_produccion`**: agregado `audit_log(accion='ACEPTAR_PRODUCCION')`
  tras asignar área + crear tareas (registra quién aceptó/cuándo).

### 2026-05-30 · planta_aceptar_produccion crea/vincula EBR (MyBatch fase 1)
- Al aceptar, si `config.EBR_MODE` ∈ ('warn','strict'), llama
  `brd.crear_ebr_desde_mbr` para crear/vincular el EBR del lote (audit
  CREAR_EBR_AUTO). Con 'strict' BLOQUEA (409 SIN_MBR_APROBADO) antes de mutar si
  el producto no tiene MBR aprobado. Default 'off' = sin cambios. Ver CONTRACT_brd.md.

### 2026-06-18 · Envases SECUNDARIos (tapa/caja) por presentación (mig 278 · A+)
- `producto_presentaciones` gana `tapa_codigo` + `caja_codigo` (mig 278).
- **Fuente ÚNICA envase↔producción** = `producto_presentaciones` para COMPRA y
  DESCUENTO de TODOS los componentes: `abastecimiento_consumo_horizontes` emite
  envase + tapa + caja (share-split por `ventas_mes_referencia`); el checklist
  (`_generar_checklist_produccion`) pre-llena `mee_codigo_asignado` del item
  envase_primario→envase_codigo, tapa→tapa_codigo, caja_exterior→caja_codigo.
  Lo COMPRADO == lo DESCONTADO (M5/M55/M56), sin asignación manual.
- POST/PUT `/api/planta/presentaciones` aceptan/validan tapa_codigo+caja_codigo
  contra `maestro_mee` (igual que envase_codigo). UI en Planta›Configuración›
  Presentaciones (campos "Código tapa MEE" / "Código caja MEE").
- Tests: `test_envases_abastecimiento.py::test_tapa_caja_aparecen_en_abastecimiento`,
  `test_envase_checklist_autopreset.py::test_checklist_tapa_caja_se_prellenan_desde_presentaciones`.

### 2026-07-25 · Auditoría CERO-ERROR · el motor de demanda deja de sub-comprar

Tres cambios en `_consumo_horizontes_core` (el ÚNICO motor de demanda · pantalla y
generar-OC comparten núcleo desde el M47). Los tres corrigen SUB-COMPRA:

- **Lo FIJO ya no se deduplica.** El dedup por `(producto, fecha)` se quedaba con UNA
  fila (la de más kg) sin mirar el origen → dos tandas FIJAS legítimas del mismo
  producto el mismo día (dos clics en el calendario, o un `eos_plan` junto a un
  `eos_b2b`) pedían la MP de una sola. **Invariante nuevo:** cada fila con
  `origen IN ('eos_plan','eos_b2b','eos_retroactivo')` cuenta SIEMPRE; las sugeridas
  se siguen deduplicando por `(producto, fecha)` **y** se descartan si ese día ya
  tiene una tanda fija (es la misma producción que el usuario ya fijó). La protección
  del M49 contra planes solapados queda intacta.
- **El backlog B2B vuelve a contar.** El loop de `pedidos_b2b` filtraba desde
  `hoy_iso` mientras las producciones usaban `piso_iso` → un pedido de cliente
  ATRASADO (sigue pendiente de entregar) desaparecía de la demanda. Ahora ambos
  usan `piso_iso`.
- **Paridad pantalla ↔ generar-OC (M5).** `atrasadas_dias` pasa a tener un default
  ÚNICO (`ATRASADAS_DIAS_DEFAULT = 7`). Antes la pantalla usaba 0 y generar-OC 7: un
  lote programado hace 2 días y no iniciado daba 0 g en la pantalla y 2000 g en la
  OC. **Invariante:** el número que se MUESTRA es el que DECIDE.

Tests: `tests/test_abastecimiento_dedup_fijo.py` (6 · incluye las 3 regresiones del
M49 y la paridad), `tests/test_dedup_mismo_dia_respeta_fijo.py` (3).

## 🔏 La asignación automática de operarios deja rastro (26-jul)

`_auto_asignar_operarios` decide QUIÉN dispensa, elabora, envasa y acondiciona cada lote, y
escribía los 4 operarios en `produccion_programada` **sin `audit_log`** — la tabla donde una
mutación sin auditar hizo desaparecer la programación del 19-may sin dejar rastro. Quién dispensó
un lote es dato regulado.

Ahora audita `AUTO_ASIGNAR_OPERARIOS` con el estado previo (leído ANTES del UPDATE, o el "antes"
sería el "después") y el nuevo. Va con el cursor del caller, antes de su commit (M22), y es
best-effort con log: un fallo del audit no puede tumbar la asignación. Si la función ABORTA por
falta de candidatos no toca la BD, así que tampoco audita — auditar un no-cambio ensucia la
evidencia. Era el último pendiente vivo del roadmap zero-error de mayo (los otros 5 ya estaban
cerrados · verificados uno por uno). Test: `tests/test_auto_asignar_operarios_audita.py`.

## 🔒 El gate de MBR en modo estricto usa el MISMO criterio que quien crea el legajo (26-jul)

`EBR_MODE='strict'` bloquea aceptar producción sin MBR aprobado. Resolvía el MBR por nombre
EXACTO mientras `crear_ebr_desde_mbr` ahora lo resuelve con `UPPER(TRIM(...))`: con criterios
distintos, el gate bloquearía una producción cuyo MBR SÍ existe, sólo porque el nombre está
guardado con otras mayúsculas. Los dos usan el mismo criterio (M2/M5).


## Configuración: `app_settings` conserva QUIÉN la cambió (30-jul)

Los `INSERT OR REPLACE INTO app_settings (clave, valor)` de este blueprint
(`por_entrar_manual`, `estacionalidad_plan_activa`, `estacionalidad_tope`,
`envases_no_requiere`) **borraban `actualizado_por` y `descripcion`**: se perdía quién cambió una
configuración (M20 · `INSERT OR REPLACE` devuelve al default toda columna que no listes).
Pasados a `ON CONFLICT (clave) DO UPDATE` conservando la auditoría. Regla: ninguna escritura a
`app_settings` usa `INSERT OR REPLACE` — hay un guard en el barrido que lo verifica.


## 👁️ `_lotes_de_material(c, cod)` · el detalle que sostiene el total (30-jul)

Helper canónico que devuelve `{usables, retenidos}` de un código: lo que el FEFO va a consumir
(en orden de vencimiento) y lo que existe en bodega pero producción **no puede tocar**, con el
motivo (cuarentena sin liberar, rechazado, bloqueado, o vencido POR FECHA aunque el cron todavía
no lo haya marcado · mismo criterio que el FEFO, M25).

Lo usan `_validar_stock_para_produccion` (arranque programado), el camino directo de
`/api/produccion` (inventario.py) y el diagnóstico `/api/admin/mp-diag`. **Uno solo a propósito**:
si cada camino armara su lista, dos pantallas contarían historias distintas del mismo lote (M5).

Nació de un reporte de piso: la verificación sumaba bien todos los lotes usables pero sólo
imprimía `necesita / hay / falta`, así que un lote en cuarentena se veía como si no existiera y el
operario, con dos lotes enfrente, leía "sin stock" (M124 · INV-15 de `CONTRACT_inventario.md`).


## 🔧 `_equipos_de_area` excluye lo que todavía no está calificado (30-jul)

Un equipo recién recibido nace `estado_calificacion='PENDIENTE'` (mig 402 · INV-16 de
`CONTRACT_inventario.md`) y esta función lo SACA de la lista del área: mientras no lo califique
Aseguramiento, producción no lo puede elegir. Es la cuarentena del equipo, y si sólo fuera una
etiqueta de color no controlaría nada.

Los equipos que ya existían quedan en `NO_APLICA` y siguen saliendo igual. Si la columna no
estuviera (base sin la migración), la función NO devuelve vacío: cae a la consulta de siempre y
loguea — un área sin equipos por un `except` mudo es indistinguible de un área sin equipos de
verdad (M94).


## 🔎 `/api/programacion/diag-por-que-no-sale?q=<nombre|codigo>` · explicar una AUSENCIA (30-jul)

Alejandro: *"lauryl glucoside no sale en abastecimiento"*. La tabla de Abastecimiento **no es un
catálogo**: `items_out_mp` recorre `consumo_mp`, o sea sólo las MP que alguna producción
PROGRAMADA va a consumir. Que una MP no aparezca puede significar cuatro cosas muy distintas, y
había que adivinar cuál:

1. no existe en `maestro_mps` (nadie la dio de alta);
2. existe pero **ninguna fórmula activa la usa** (a la fórmula le falta el ingrediente);
3. está en una fórmula pero **ese producto no tiene lotes programados** (correcto: nada que consumir);
4. aporta 0 g — `porcentaje=0` y `cantidad_g_por_lote=0`, o `controla_stock=0` (agua), o el
   nombre del PLAN no cruza con el de la FÓRMULA (ver `lotes_sin_formula` del endpoint).

El diagnóstico busca por **nombre** (no sólo por código: justo lo que se investiga es si el
material está bajo otro código o no está) y devuelve un **veredicto en una frase**. Mira también
el `material_nombre` escrito en la fórmula, porque un ítem puede traer un código heredado cuyo
nombre en el maestro es otro.

**Descartado con el código en la mano:** el resolver NO puede plegar la demanda de un material
dentro de otro — el match por nombre/INCI es exacto (normalizado), y con dos candidatos del mismo
INCI se frena a propósito en vez de elegir por stock (M17/M19).

**5ª respuesta posible, agregada el 1-ago:** *ese CÓDIGO no se usa, pero un PARIENTE sí.*
Sebastián, al leer el veredicto del día anterior: *"el lauryl glucoside se usa en varias fórmulas,
¿cómo así?"* — y las dos cosas eran ciertas. `MP00070` no aparece en ninguna fórmula, pero las
fórmulas usan **decyl** glucoside (MP00092) y **caprylyl/capryl** glucoside (MP00050): misma
familia, moléculas distintas (C12 / C10 / C8). *"Nadie lo usa"* a secas manda a agregar a la
fórmula un ingrediente que quizá ya está ahí con otro nombre.

La respuesta trae ahora `parientes[]` (otros códigos del maestro que comparten una palabra
significativa del nombre/INCI), con `usos_en_formulas_activas` y `kardex` de cada uno, y
`kardex` también para los códigos buscados.

- **NO empareja ni sugiere fusionar.** Cuál es cuál lo decide Alejandro (M19: emparejar por
  parecido termina descontando la molécula equivocada). El endpoint pone los candidatos sobre la
  mesa y se calla.
- **El `kardex` es lo que separa las dos explicaciones OPUESTAS:** si en planta se vierte éste y
  la fórmula nombra al otro, éste tiene entradas y **cero salidas** mientras el otro sale; si son
  materiales genuinamente distintos, los dos se mueven.
- **Una palabra que matchea con ≥40 códigos se descarta como criterio** (`acid`, `extract`,
  `oil`…): un "pariente" que lo es de todos no informa nada.

**6ª respuesta, y la más grave (1-ago):** *la fórmula SÍ lo lleva, pero con OTRO CÓDIGO.* Ahí el
otro código se lleva la demanda y el stock de éste no baja nunca. Los dos arreglos posibles son
**opuestos** — unificar códigos duplicados (`/admin/renombrar-codigo-mp`, reversible) vs corregir
el ítem de la fórmula — así que el endpoint lo declara y decide Alejandro (M19).

Ese caso no se veía porque **el cruce sólo conocía la palabra tecleada**: MP00070 se llama
comercialmente *"Plantaren Lauryl 1200 / Eversoft 1200"*, y una fórmula que lo nombre *"Plantaren
1200"* con otro código no matcheaba ni por código ni por nombre. **Encontrar necesita UN nombre;
descartar necesita todos.** Ahora cruza además por la MARCA, con dos reglas duras:

- **MARCA = lo que está en el nombre comercial y NO en el INCI.** El INCI es la molécula
  ("glucoside"): cruzar por ahí traería a todos los parientes como si fueran usos y el veredicto
  diría lo contrario de la verdad.
- **La corroboración es la IDENTIDAD, no un umbral:** un match por marca cuenta sólo si el código
  del ítem tiene el MISMO INCI (o es un fantasma ausente del maestro, que es el caso sospechoso).
  Contar apariciones del token pasaba en aislamiento y el gate lo tumbó.
- **Sin INCI el cruce se APAGA y se declara** (`sin_cruce_por_marca_porque_no_tienen_INCI` +
  `aviso`): sin INCI no hay forma de separar marca de química, y adivinar da una respuesta segura
  y equivocada.

Tests: `tests/test_diag_por_que_no_sale.py` (en el gate · los 4 casos + la búsqueda por nombre +
el aviso de parientes con su prueba de que NO se dispara cuando no los hay + el cruce por marca
con su prueba de que NO confunde a un pariente con un uso + la limitación declarada sin INCI).

## 📄 `/api/programacion/reconciliar-batch-record` · EOS contra la verdad EXTERNA (1-ago)

Sebastián: *"ya varias veces me has dicho que es perfecto, pero hoy hay cosas que no sabíamos"*.
La razón de fondo: **todas las verificaciones anteriores comparaban EOS consigo mismo** (motores
entre sí, display vs cálculo, un endpoint vs su gemelo). Eso encuentra inconsistencias internas y
**nunca** un dato que esté mal en los dos lados. Faltaba una fuente externa.

`api/data/formulas_batch_record.json` son los 28 batch records **firmados** (lo que se pesó de
verdad, con quién pesó y quién verificó · 645 líneas, 173 códigos). Se genera del PDF, no se
teclea. **Control de integridad: los 28 suman 100,000%** — si alguno no lo hiciera, el dato está
mal extraído y NO se puede usar para acusar a una fórmula.

Informa cuatro diferencias con arreglos **opuestos**: `falta_en_eos` (se descuenta de MENOS),
`sobra_en_eos` (de MÁS), `porcentaje_difiere` (potencia equivocada), `sin_formula_en_eos`.
**No corrige nada** — cambiar una fórmula es dato regulado y lo decide Alejandro (M19).

- El emparejamiento por nombre va con **umbral alto** (0.70 + 0.20 de ventaja sobre el segundo).
  Con 0.50 unía *"Suero Vitamina C+"* con *"SUERO ANTIOXIDANTE VITAMINA C+B3"*: comparar el par
  equivocado **inventa** diferencias. Lo que no llega sale como `candidatos_en_eos`.
- El informe **siempre dice cómo cruzó** (`match_por`): un emparejamiento que no se puede auditar
  no sirve para GMP.

Hallazgos que dejó al construirlo: el lauryl glucoside **no aparece en ningún batch record** (se
pesan decyl, caprylyl y ascorbyl), o sea que EOS tenía razón; y los 645 renglones no usan **ni un**
código fantasma `MPxxxSO01`, así que todo fantasma con saldo en EOS es residuo a limpiar.

Tests: `tests/test_reconciliar_batch_record.py` (en el gate · la referencia sana + las 4 clases de
diferencia + que el umbral no baje + que siempre diga cómo cruzó).

## 📦 `/api/programacion/mp-sin-formula` · MP con stock que ninguna fórmula declara (1-ago)

La forma general de la pregunta del lauryl: no *"¿por qué no sale ésta?"* sino *"¿cuántas más hay
así?"*. Cada una es una de dos cosas, y las dos importan: **plata parada** (se compró y no entra a
ningún producto) o **el kardex mintiendo** (en planta se usa, ninguna fórmula la descuenta, el
stock queda inflado y nadie la vuelve a comprar porque el sistema cree que no se consume).

- No decide cuál es: lista con la evidencia. `salio_alguna_vez` es la señal que separa las dos —
  lo que nunca salió es compra parada; lo que salió sin que ninguna fórmula lo declare se está
  consumiendo por fuera.
- **El puente `mp_formula_bridge` cuenta como uso** (M1): una fórmula puede nombrar el material
  con un código fantasma que puentea a éste. Sin eso, media bodega saldría como huérfana y la
  lista no serviría.
- Stock por `_get_mp_stock` (regla #4, nunca un SUM propio) · excluye `controla_stock=0` (el agua
  del lab no se compra) y lo que está por debajo del umbral de polvo (M21).

Tests: `tests/test_mp_sin_formula.py` (en el gate · incluye los dientes: la que SÍ está en una
fórmula no aparece, y el puente cuenta como uso).

## 🩺 PROG-N · Vigía diario de materias primas · el detector que faltaba (2-ago)

La colisión de códigos del 9-jul estuvo **tres semanas a la vista** y nadie la vio: un kardex con
un descuento de más se ve igual que uno sano. Todo este frente se verificaba **abriendo** un
endpoint, o sea sólo cuando alguien se acordaba. Lo que faltaba no era el arreglo: era el detector
(M127 · una integración muda y un inventario mal descontado fallan igual de silenciosos).

`_salud_mp_core(c)` (read-only) es el núcleo ÚNICO de `GET /api/programacion/salud-materias-primas`
y del cron `salud_mp` (diario 7:40 · `job_salud_materias_primas`). Seis firmas, cinco **graves**
que tienen que dar CERO:

| Firma | Qué significa si deja de dar cero |
|---|---|
| `formula_no_suma_100` | el control de integridad que trajo el batch record; antes sólo corría a mano |
| `formula_apunta_a_codigo_muerto` | ese ítem NO descuenta: la producción se lleva el material y el sistema no se entera |
| `colision_a_medio_corregir` | quedó un consumo contado dos veces (INV-20) |
| `codigo_con_espacios_en_kardex` | clave distinta → stock invisible, sin un solo error (M100) |
| `stock_negativo_por_lote` | se descontó algo que no estaba |

La sexta, `salidas_que_ninguna_formula_declara`, es **informativa** (hay bajas y consumos manuales
legítimos) pero es **la firma exacta de la colisión**: es lo que había que mirar el 10-jul.

Detalles que hacen que sirva:
- **Un chequeo que no puede correr se DECLARA** en `checks_fallidos`. Si devolviera lista vacía en
  silencio, su resultado se leería como "todo limpio" y estaría mintiendo (M100).
- **`colision_a_medio_corregir` reusa `_plan_colisiones_net_zero`**, no una copia: dos versiones
  del mismo cálculo divergen en silencio (M1).
- **El cron avisa cuando el resultado CAMBIA** (huella en `app_settings.salud_mp_firma`), no todos
  los días: una alerta que suena igual siempre deja de mirarse justo el día que importa. La huella
  incluye los chequeos caídos, así que un chequeo que se rompe también es novedad.
- `formula_apunta_a_codigo_muerto` **complementa al trigger**, no lo reemplaza: el trigger de
  `formula_items` (M38) impide APUNTAR a un código inexistente al insertar y al actualizar, pero no
  puede hacer nada cuando el código se **desactiva después**, con la fórmula ya escrita. Ése es el
  hueco que este chequeo tapa, y el test lo reproduce por ese camino.

Tests: `tests/test_salud_materias_primas.py` (en el gate · cada firma probada con dientes + que el
trigger siga mordiendo + que el cron esté registrado).

## 🚫 PROG-N+1 · Dos códigos que conviven en una fórmula NO son el mismo material (2-ago)

Sebastián: *"cruzar fórmulas de EOS contra batch, así vamos a resolver el problema de la centella"*.
El cruce ya existía; lo que le faltaba era el descalificador.

`_pares_que_conviven(productos_ref)` devuelve los pares de códigos que aparecen como **renglones
separados de una misma fórmula** del batch record. Una receta no lista dos veces el mismo material,
así que ese par **no puede ser el mismo material** -- por más que compartan INCI o porcentaje. Es un
**descalificador duro**, no una señal más.

**Lo que escondía:** el reconciliador emparejaba `MP00252 → MP00176` ("Centella Asiatica Extract" →
"triterpenos 80%") en 8 productos, y la `ESENCIA DE CENTELLA ASIATICA FULL` los lleva a los **dos**
(0,15% + 0,10%). O sea que en esos 8 productos **EOS descuenta otro grado del que pide el batch
record, con la misma dosis**: mismo INCI, potencia distinta (M19). El emparejamiento convertía el
hallazgo en "es el mismo material con otro código", que es exactamente lo contrario.

Va en los **dos** sitios (M45 · el emparejador está duplicado):
- `prog_reconciliar_batch_record` → los rechazados salen en `no_son_el_mismo_material`, con el
  producto que lo **prueba** (un hallazgo tiene que ser auditable, no una afirmación · M132).
- `_plan_unificar_codigos` → entran al plan como `bloqueado_no_es_el_mismo_material`. Acá importa
  más: esa herramienta **renombra códigos de verdad**, y el apply sólo toca los `seguro`.

**Segundo defecto del mismo bloque:** la corroboración por INCI leía los dos códigos con un
`IN (?,?)` y aceptaba `len(set)==1` como "mismo INCI". Si uno de los dos **no existe en el maestro**
(el caso de `MP00252`), la consulta trae UN solo INCI y el chequeo daba **corroborado sin haber
comparado nada**. Ahora exige que los dos tengan INCI; si no, queda `solo_porcentaje` + `aviso` que
dice cuál falta. El `aviso` va en campo aparte para no romper el vocabulario de `confirmado_por`,
que otros consumen (M116).

Efecto lateral bueno: al sacar los pares basura, un par legítimo que estaba bloqueado *de rebote*
por ambigüedad se destrabó (`MP00301 → MP00030`, propylheptyl, que también figuraba apuntando a
`MP00195` glicerina).

Tests: `test_reconciliar_batch_record.py` (invariante: ningún par del mapa puede convivir · probada
con dientes) + `test_unificar_codigos_batch.py::test_un_par_DESCALIFICADO_nunca_puede_quedar_seguro`.
