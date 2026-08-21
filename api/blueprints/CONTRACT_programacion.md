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
- **Encabezado de control documental (Aseguramiento 19-ago-2026).** El F02 se imprime
  desde DOS pantallas -- el rótulo operativo (`/planta/rotulos-limpieza`) y el snapshot
  inmutable del expediente (`/planta/rotulo-limpieza/registro/<id>/pdf`, el que se le
  muestra a INVIMA) -- y las dos DEBEN llevar la estructura corporativa de Espagiria,
  que no es decorativa: es la evidencia de que se está usando la versión vigente
  (ISO 22716 · Res. 2214/2021).

      [ logo + nombre ] | [ FORMATO / título ] | [ Código · Versión · Página · Vigencia ]

  Etiquetas EXACTAS (`Código:`, `Versión:`, `Página:`, `Vigencia:`) y la vigencia lleva
  sus dos subcampos `Desde:` y `Hasta:` -- **nunca resumida en un rango**. La palabra
  `FORMATO` va literal y separada del título.
- **Los datos de control salen de `F02_CONTROL` (una constante) vía
  `_encabezado_formato_zonas()`**, que usan las dos pantallas y el registro en el
  expediente. Dos copias divergen, y el día que Aseguramiento libere la versión 03 una
  seguiría diciendo 02 -- las dos viéndose igual de oficiales (M3/M1).
- ⚠ El rótulo se imprime en **etiqueta de 100×100 mm**: cualquier cambio al encabezado se
  verifica MIDIENDO (simular `@media print` como hoja normal y medir milímetros), no a
  ojo. Al 19-ago: 72,6 mm de alto y columnas 24 / 43,5 / 29 mm.
  Tests: `tests/test_f02_encabezado_control_documental.py`.

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

## ✏️ PROG-N+2 · Re-apuntar un ingrediente de UNA fórmula (2-ago)

`POST /api/programacion/editar-formula-items` (ADMIN · dry-run por defecto). Nace de la respuesta
de Alejandro sobre la centella: en 13 productos el batch record pide el **extracto** y EOS descuenta
**triterpenos 80 %**; la Esencia lleva los **dos** (0,15 % + 0,10 %) y EOS los fundió en 0,25 %.

**Por qué no sirve el `reapuntar-formula` que ya existía:** ése cambia el código en TODAS las
fórmulas, y Hydrapeptide y la Esencia sí llevan triterpenos. En bloque se rompen (M19: el scope es
el ítem, nunca el `material_id` a secas).

Cada cambio es `{producto, de, a, pct_a, pct_de}`:
- `pct_de = 0` → el ingrediente pasa de `de` a `a` con el mismo %
- `pct_de > 0` → se **parte**: `de` se queda con `pct_de` y nace `a` con `pct_a`

**`pct_a + pct_de` tiene que dar el % que ese ingrediente tiene HOY.** Con esa regla la fórmula no
puede dejar de sumar 100 por un error de tipeo -- y sumar 100 es el control de integridad de todo
este frente. La respuesta devuelve además `sumas_despues` y `formulas_fuera_de_100`.

**El guard que más importa: un PUENTE activo sobre el destino BLOQUEA.** Si existe
`mp_formula_bridge` activo mandando `a → otro`, la fórmula diría `a` y el descuento seguiría
sacando `otro`, **sin un solo error a la vista** -- la feature quedaría construida y muerta. Es
literalmente lo que pasó con la centella: el puente 184 (18-jun) manda `MP00181 → MP00176` con la
nota *"maestro usa extracto MP00181 · stock está bajo MP00176"*.

Otros bloqueos: el ingrediente no está en la fórmula activa; el destino no existe o está inactivo;
la fórmula ya tiene el destino (eso sería fusionar dos ingredientes y se decide aparte).

Auditado con el valor previo (`EDITAR_FORMULA_ITEM`) → reversible. Tests:
`tests/test_editar_formula_items.py` (en el gate · cada guard probado con dientes).

## 🔡 PROG-N+3 · Un typo de una letra dejaba un batch record sin comparar (2-ago)

`_emparejar_producto_eos` cruzaba por nombre exacto → prefijo → **conjuntos de palabras**. Para el
tercer nivel `HYBRID` y `HIBRID` son dos palabras distintas, así que *"AZ Hybrid Clear"* contra
*"AZ HIBRID CLEAR"* daba **33 %** y ese batch record **no se comparaba con nada** -- y adentro tiene
un ingrediente al 4 %.

Nivel nuevo **`casi_igual`**, letra por letra (`SequenceMatcher` sobre el nombre normalizado), con
umbral **0,90 + 0,10 de ventaja**. Medido: `AZ HYBRID/HIBRID CLEAR` = 0,93 (une); *"Suero Vitamina
C+"* contra sus dos candidatos = 0,67 y 0,65 (**sigue ambiguo**, que es lo correcto: lo confirma una
persona · M132). Va DESPUÉS de exacto y prefijo, así que no le gana a un cruce seguro.

### El INTERCAMBIO CRUZADO (resuelto 2-ago)

El emparejador de códigos resuelve pares de a uno. Cuando dos códigos **se intercambian entre sí**
no puede: en `EMULSION HIDRATANTE`, `GEL HIDRATANTE` y `HYDRAPEPTIDE` el batch usa `MP00301`
(propylheptyl, 3 %) y `MP00302` (ethylhexylglycerin, 0,4 %), mientras EOS usa `MP00030` (3 %) y
`MP00301` (0,4 %). Como `MP00301` aparece de los **dos** lados, no entra ni en `falta_en_eos` ni en
`sobra_en_eos`: cae en `porcentaje_difiere`, y `MP00302` se queda sin propuesta.

**Cómo se resolvió.** Un código que aparece en los dos lados con porcentajes **distintos** está
sirviendo para dos cosas distintas, así que se **descompone**: su uso en el batch queda sin pareja y
el de EOS también. Con eso el ciclo lo resuelve el emparejamiento por porcentaje único que ya
existía:

```
falta:  MP00302 @0,4  ·  MP00301 @3,0
sobra:  MP00030 @3,0  ·  MP00301 @0,4
        → 0,4:  MP00302 ↔ MP00301
        → 3,0:  MP00301 ↔ MP00030
```

**Sin umbral y con reversión.** Sólo se descompone si en el otro lado hay un código libre con
**exactamente** ese porcentaje; y si las dos mitades no llegan a formar par, se **revierte** y el
código vuelve a `porcentaje_difiere` -- que es lo correcto para una diferencia real de dosis (el
`MP00062` de Renova Body). Los dos intentos anteriores fallaron por preguntar *"¿se parecen?"*; éste
pregunta *"¿cierra la cuenta?"*.

Invariante que lo protege: **un código no puede FALTAR y SOBRAR a la vez en el mismo producto** --
eso significaría que la descomposición quedó a medias.

Se intentaron dos reglas automáticas para taparlo (código que el batch usa donde EOS no lo lleva; y
lo mismo exigiendo un sustituto al porcentaje exacto) y **las dos marcaban códigos sanos**: a
niveles de traza (0,05 · 0,1 · 0,3) que dos ingredientes coincidan en porcentaje es casualidad. Se
descartaron -- una lista con ruido se descarta entera, incluidas las correcciones que sí importan.
El test `test_NO_marca_por_parecido_de_NOMBRE` es el que las tumbó las dos.

Tests: `test_reconciliar_batch_record.py::test_une_un_nombre_con_UNA_letra_distinta` +
`::test_NO_une_dos_productos_distintos_que_comparten_palabras`.

### El MISMO código dos veces en una fórmula (2-ago)

`formula_items` **no tiene UNIQUE(producto, material_id)**, y la Crema Renova Body tiene `MP00062`
al 0,2 % **y** al 0,1 %: la segunda es en realidad la **Fresa Cremosa** (`MP00019`) cargada con el
código del pistacho. Los totales cuadran con el batch (0,3 %), lo que está mal es el código.

Un `fetchone()` sobre `(producto, código)` elegiría una de las dos **al azar**, y en PostgreSQL
puede cambiar entre corridas (M102). `editar-formula-items` trae **todas** las filas en orden
determinista y, si hay más de una, **bloquea** hasta que el caller diga a cuál se refiere con
`pct_actual`. Cambiar la línea equivocada de una fórmula regulada no se deshace mirándola.

## 🌸 PROG-N+4 · Un INCI que comparten MUCHOS materiales no identifica a ninguno (2-ago)

Sebastián: *"que ninguna materia prima tenga error, que descuente, abastecimiento contando"*.
Al verificarlo apareció que la **Fresa Cremosa** (`MP00019`, 0,1 % en Crema Renova Body) **no salía
en Abastecimiento**, con producción programada y stock 0. Nadie la compraría.

No estaba perdida: **se la llevaba el Pistacho**. La aritmética lo prueba —
`MP00062` aparecía con **88,5 g** = sus 59 g (0,2 % × 29,5 kg) **+ los 29,5 g de la fresa** (0,1 %).

**Causa.** `_resolver_material_bodega_impl` cae al tier INCI cuando el código de fórmula tiene
stock 0. El guard contra INCI ambiguo **ya existía** (25-jul · `PARFUM` está listado como grupo
peligroso), pero medía la ambigüedad sobre los códigos **con stock**:

```python
_inci_cands = [cod for cod in activos if mismo_inci and stock > 0.01]
if len(_inci_cands) > 1: ...   # no dispara si sólo UNO tiene stock
```

De las **diez** fragancias con INCI `PARFUM` sólo el pistacho se ha comprado alguna vez → un solo
candidato → el guard no dispara y el resolver elige con total confianza.

**Fix:** la ambigüedad es del **INCI**, no del stock. Si más de un material ACTIVO comparte ese
INCI, el INCI no identifica al material y no sirve para redirigir → el código se resuelve a sí
mismo y su déficit aparece con su propio nombre.

**Estrictamente más conservador**: sólo puede impedir redirecciones, nunca agregarlas. El duplicado
legítimo de dos códigos (pantenol líquido/polvo) sigue cruzando -- probado en el mismo archivo.

**Golpea a las MP que NUNCA se compraron**, que son justo las que tienen que salir en la tabla para
poder comprarlas. Tests: `tests/test_resolver_inci_generico.py` (en el gate · probado con dientes:
sin el guard, la fresa se va al pistacho).

## 🌉 PROG-N+5 · Desactivar un puente de MP se AUDITA (2-ago)

`DELETE /api/programacion/mp-bridge/<id>` hacía `UPDATE ... SET activo=0` **sin dejar rastro**. Un
puente decide **de qué código sale el material** cuando se produce, así que quitarlo cambia el
descuento del inventario: es una mutación regulada.

Lo destapó desactivar el **puente 184** (`MP00181 → MP00176`), que a su vez alguien había creado en
junio **sin constancia** — por eso nadie sabía que existía y la centella se descontaba del frasco
equivocado durante semanas.

Ahora: CAS (`WHERE ... AND activo=1` + `rowcount`), `audit_log` con el **destino previo** (sin él no
se puede revertir: el puente se recrearía a ciegas), y 404 si no existe. La respuesta dice qué
cambia. Tests: `tests/test_puente_desactivar_audita.py`.

## 📄 BRD · El MBR aprobado conserva el nombre viejo (2-ago)

Un MBR aprobado es **INMUTABLE** (mig 109), así que al renombrar un producto se queda con el nombre
viejo y `crear_ebr_desde_mbr` — que lo busca con `UPPER(TRIM)` — **deja de encontrarlo**: el
producto renombrado **no puede generar su batch record**. `UPPER(TRIM)` no colapsa el espacio de
adentro (`"HYDRA BALANCE"` ≠ `"HYDRABALANCE"`).

`renombrar-producto` lo reportaba como `aprobados_inmutables: N`, que se lee como un pendiente de
Calidad — y era una rotura. **Cuando una herramienta dice que salteó algo, hay que preguntarse qué
se rompe por haberlo salteado.**

Dos mitades:
- **La causa**: el rename ahora **deja el puente** en `producto_formula_alias` (nombre nuevo →
  nombre viejo, que es donde vive el documento aprobado).
- **El síntoma**: el lookup sigue el alias y, si no hay, prueba por **nombre sin espacios ni
  puntuación** — sólo si es INEQUÍVOCO (con dos candidatos no elige: es un dato regulado · M19/M132).
  Siempre declara por cuál cruzó en el log.

Re-versionar sigue siendo un acto de Calidad; mientras tanto la planta no se queda sin legajo. Y
cuando lo re-versionen con el nombre nuevo, el match exacto gana y el alias deja de usarse solo.
Tests: `tests/test_mbr_sobrevive_al_rename.py`.

### El descalificador NO aplica sobre un código en COLISIÓN (2-ago)

El descalificador por convivencia asume algo que en una **colisión** no se cumple: que un código
significa lo mismo en los dos sistemas. `MP00301` es **propylheptyl** en el batch record y
**ethylhexylglycerin** en EOS — dos cosas distintas con el mismo número. Así que *"MP00301 y
MP00302 conviven en el batch"* **no prueba** que el `MP00302` del batch no sea el `MP00301` de EOS,
y bloqueaba un mapeo correcto.

**La evidencia de que un código ES una colisión ya la dio la aritmética**: apareció de los dos lados
con porcentajes distintos y su descomposición cerró con parejas exactas (`_cruzados`). No depende de
ningún nombre ni umbral — por eso no es circular.

El par resultante se **declara** como `confirmado_por: 'intercambio_cruzado'`: es la única clase de
par que puede convivir en una fórmula del batch sin ser un error, y la invariante
"ningún par del mapa puede convivir" lo exceptúa explícitamente. El informe siempre dice **cómo**
cruzó, y acá el cómo cambia la lectura del hallazgo (M132).

## 🏷️ PROG-N+6 · El envase que fue a serigrafía se descuenta UNA vez (4-ago)

Catalina: *"descuenta doble"*. El ciclo es: Compras manda el envase BASE a marcar → sale de la
planta → vuelve con OTRO código (el serigrafiado) → Calidad lo libera → se usa para producir.
Dos causas independientes, las dos verificadas contra el código:

**A · El descuento de envasado seguía apuntando al BASE.** `_descontar_mee_envasado` toma el
código de `produccion_checklist`, que se pre-llena desde `producto_presentaciones` — y ése es el
base. Pero el base **ya salió del kardex** cuando se envió a marcar, así que descontarlo otra vez
lo cuenta dos veces; y el serigrafiado, que es el que de verdad se consume, **no se descontaba
nunca**: su stock sólo crecía. `marcacion_cambiar_envase` existía, pero es manual y nada lo ataba
al ciclo.

**Invariante:** si para ESA producción hay una `marcacion_ordenes` con ese `base_codigo` en
estado `recibido` o `liberado`, el descuento del ítem de envase se redirige al
`serigrafiado_codigo` de esa orden. La redirección **no adivina** (M19): la orden guarda
`produccion_id` + `base_codigo` + `serigrafiado_codigo`, así que "este base, para esta
producción, volvió como aquel" es un hecho registrado. Y **sólo cuenta si ya volvió**: con la
orden en `enviado` el envase todavía está afuera y no está para usarse, así que se sigue
descontando el base. El resultado declara `codigo_descontado` y `redirigido_de_marcacion` — si el
código cambia en silencio, nadie puede entender el kardex después.

**B · Crear la orden no tenía guard anti-duplicado.** "Solicitar alistamiento" (admin.py) llama
al **mismo** endpoint `POST /api/programacion/marcacion-orden/enviar`, que insertaba sin mirar si
ya había una orden abierta: dos clics = dos órdenes = dos Salidas del base. **El CAS protege
TRANSICIONES, no la CREACIÓN (M63).** Ahora, si ya existe una orden `enviado` para el mismo
(base, serigrafiado, producción), responde **409 `MARCACION_YA_ABIERTA`** con la cantidad y la
fecha de la que ya está. No prohíbe: mandar otra tanda del mismo envase es legítimo, y se pasa
con `forzar: true`.

⚠ **Trampa de fixture (costó tres corridas):** `aplicar_movimiento_mee` clampea la Salida contra
`maestro_mee.stock_actual`, **no** contra `SUM(movimientos_mee)`. Sembrar el stock sólo como
movimiento y dejar la columna en 0 hace que registre una **Salida de 0** — sin un solo error a la
vista, y el test mide otra cosa.

Tests: `tests/test_marcacion_no_descuenta_doble.py` (en el gate).

## 📉 PROG-N+7 · La salud de la cadena la calcula el SERVIDOR (4-ago)

Sebastián, revisando Necesidades: nueve de once cadenas decían **"sobra-stock"**. El rótulo era
correcto, pero **la cuenta vivía sólo en el navegador** (`_saludCadena` en `dashboard_html.py`):
se veía lote por lote adentro del modal, y nada del servidor podía contar cuántos productos
estaban mal dimensionados, alertarlo, ni testearlo. Un número que decide plata y que ningún test
puede tocar es un número sin red.

**Helper canónico:** `plan.salud_cadena(lotes, *, velocidad_uds_dia, ml_unidad, stock_uds, hoy)`
— función PURA (sin BD, testeable sola). Modelo, lote por lote en orden de fecha:

- la cobertura de hoy se agota en `stock_uds / velocidad`;
- un lote producido el día F entra a la góndola el día `F + PIPELINE_GONDOLA_DIAS` (7);
- `colchon` = días entre esa llegada y el agotamiento de la cobertura previa;
- el lote extiende la cobertura desde `max(cobertura_previa, llegada)` — si llegó tarde, la
  cobertura arranca en su llegada, no antes.

**Estados:** `tarde` (colchón < 0 · quiebre) · `justo` (< `BUFFER_REORDEN_DIAS`) · `sano` (entre
el buffer y lo que dura un lote) · `sobra` (colchón > lo que dura un lote · la cadencia va a más
del doble de la velocidad real).

**Medido antes de creerle:** una cadena con cadencia = duración del lote deja **exactamente 20
días** de colchón y sale sana en los 6 lotes; a la mitad de cadencia marca 6 de 8 en `sobra`; con
cadencia más larga que el lote marca `tarde`, nunca `sobra`. O sea que el clasificador discrimina
y no dispara de más: cuando dice "sobra-stock", se produce de verdad más seguido de lo que dura
un lote.

**Invariantes:**
- Sin velocidad **no hay veredicto**: devuelve `medible: False` + `motivo`. Un "todo bien"
  inventado sobre un producto sin ventas es peor que la ausencia del dato (M100).
- Los lotes `cancelado`/`completado` **no aportan cobertura** (un cancelado no va a llegar).
- Un lote con fecha pasada **no recibe veredicto** (no se puede adelantar el pasado) pero **sí
  suma cobertura**: su producto está en la góndola.
- Devuelve `fecha_sugerida` por lote (`cobertura − buffer − pipeline`) porque el botón
  "⏩ Adelantar" la necesita: al mover el cálculo al servidor, sin ese campo el botón quedaba
  vivo y mudo (M112).
- La sobre-producción **deliberada** (`sku_planeacion_config.sobreproduccion_deliberada`, mig
  378) se cuenta aparte y **no alerta**: una alerta sobre lo ya decidido se vuelve ruido (M98).

**En el resumen de `/api/plan/necesidades`:** `n_cadenas_sobreproducen`, `n_cadenas_tarde`,
`n_cadenas_sobreproducen_a_proposito`, `n_cadenas_sin_medir`. La pantalla pinta lo que el backend
dice; su cálculo local queda sólo como respaldo para una respuesta vieja en caché.

**+ El punto ciego del mapeo, ahora visible.** Las tarjetas de Necesidades sumaban 26 sobre 28
SKU: los dos que faltaban eran `SIN_MAPEO`, o sea productos que **venden en Shopify y el plan no
ve**. Estaban en un chip chiquito al costado de la fila. Ahora hay tarjeta propia, y debajo se
dice en **unidades** cuánto se vendió bajo SKU huérfanos en 30 días — el conteo de SKU no dice
cuánto duele; las unidades sí (M124).

Tests: `tests/test_salud_cadena_necesidades.py` (en el gate).

## 🔎 PROG-N+8 · "¿Alcanza para ESTE lote?" · MP y envases (4-ago)

Sebastián, sobre el modal Programar: *"que diga la materia prima si alcanza para la próxima
producción y los envases"*. El bloque verde que había decía **"Materias primas OK · 26 items con
stock suficiente para 1 lote · listo para producir"** y era la afirmación más confiada de la
pantalla siendo la más incompleta:

- calculaba contra **un lote del `lote_size_kg` del maestro**, no contra los kilos que el usuario
  está por programar (fórmula de 35 kg + cadena de 60 → contestaba por 35);
- sumaba el stock con un `SUM` **crudo que NO excluye** cuarentena, cuarentena extendida, vencido,
  rechazado, agotado ni bloqueado → decía "listo" con material que el FEFO no puede consumir;
- usaba `cantidad_g_por_lote` en vez del **porcentaje** (la base que ya produjo descuentos ~1000×
  cortos · M16/M50/M71);
- **no miraba los envases**: se podía tener las 26 materias primas y no tener con qué envasar.

**Helper canónico:** `plan.disponibilidad_para_kg(conn, producto, kg)` → `{kg, mp{...},
envases{...}}`, y el endpoint `GET /api/plan/disponibilidad-para-kg?producto=&kg=`.

**Invariantes:**
- La regla de explosión es la MISMA que usa el descuento real: **porcentaje-first reescalado al
  kg pedido**; `cantidad_g_por_lote` sólo de fallback y siempre reescalado por `kg / lote_base`,
  nunca crudo. Si el modal usara otra regla, aprobaría un lote que después no descuenta igual.
- El stock sale de `_get_mp_stock` (canónico, 6 estados excluidos) y de `_get_mee_stock`. Lo que
  se excluye **se enumera** en `mp['excluye']` (M124).
- Lo pendiente en compras se lee **en bloque** (`_pendiente_en_compras_bulk`): este endpoint se
  llama en cada tecla de kg y por-ítem serían ~30 consultas por pulsación (M43).
- Las MP con `controla_stock=0` (el agua del lab) no se chequean.
- **Envases:** frasco, tapa, caja y **etiqueta** (mig 346) desde `producto_presentaciones`. El
  bulk se reparte entre presentaciones **pesando por volumen** (uds × ml, M72), no por share de
  unidades. Sin ventas de referencia el reparto cae a estimado-por-volumen y **lo declara** en
  `fuente_reparto`. Sin presentación o sin envase asignado devuelve `SIN_PRESENTACION` /
  `SIN_ENVASE` con motivo, nunca un número inventado.
- **⚠ La serigrafía se INFORMA, no se resta.** Cuando un envase se manda a marcar, su Salida ya se
  registró, así que `_get_mee_stock` **no lo cuenta**. Restarlo otra vez sería descontarlo dos
  veces: exactamente el doble descuento que reportó Catalina (PROG-N+6). Se muestran dos
  cantidades aparte: `en_marcacion` (afuera, estado `enviado`) y `esperando_arte` (volvió, entró
  en cuarentena, estado `recibido`).

Tests: `tests/test_disponibilidad_para_kg.py` (en el gate · el de cuarentena probado con el bug
viejo reintroducido a propósito).

## 💾 PROG-N+9 · La decisión de producción se GUARDA (4-ago)

Sebastián: *"digo 30 kilos cada 2 meses, guardar · ¿cómo garantizamos que se replique y que
cuando se abra aparezca?"*.

No se guardaba. El modal la **reconstruía** midiendo los días entre los dos primeros lotes
futuros (`_cadenaExistente`), así que mentía en cinco escenarios: al mover un lote la cadencia
cambiaba sola; al quedar un solo lote futuro volvía al default de 2 meses; al cancelar lotes,
igual; una cadena creada por los generadores (`eos_canonico`/`eos_proyeccion`) era **invisible**;
y el corrimiento a día hábil ya distorsionaba la medición ("cada 60 días" se leía 1,9 ó 2,1
meses).

**Lo llamativo: el modal GEMELO del calendario sí la guardaba**, en `sku_planeacion_config` vía
`POST /api/programacion/decision-produccion`. Dos pantallas que hacen lo mismo con dos
comportamientos distintos: el arreglo no fue inventar una tabla, fue que ésta escriba donde la
otra ya escribía.

**Invariantes:**
- Al crear la cadena, el modal guarda `cadencia_dias`, `kg_objetivo_lote` y `horizonte_dias`.
  Va **después** de crear la cadena y es best-effort: si falla, la cadena ya quedó bien y no se
  le tumba al usuario lo que sí funcionó.
- **NUNCA manda `mix_mode`.** Ese endpoint descongela el mix cuando el campo CAMBIA, y mandar el
  default desde acá borraría un mix puesto en `fijo` a propósito (M85).
- Al abrir, la precedencia es: **decisión guardada → lo que se deduce de los lotes → default**.
  El payload de `/api/plan/necesidades` trae `decision_guardada` por producto (`None` si el
  producto no tiene: no se inventa una decisión que nadie tomó).
- El cruce producto↔decisión usa `_norm_prod_fuerte` en los dos lados (M2): con otro
  normalizador la decisión existiría en la base y no llegaría nunca a la pantalla.

Tests: `tests/test_decision_se_guarda.py` (en el gate).

## 📐 PROG-N+10 · Las reglas de programación, escritas donde se aplican (4-ago)

Sebastián las dictó así: *"el sistema automático coloca las producciones 20 días antes de que se
agote, esa es la regla primordial · no programa sábados, domingos ni festivos · intenta un lote
por día, si es necesario dos · no pone más de 200 kilos por día"*, y después: *"no es tope duro,
se puede pasar · incluso siempre prefiere producir lunes, miércoles y viernes para que tengan
martes y jueves de otras actividades"*.

**Lo que se encontró antes de tocar nada:**

| Regla | Estado real |
|---|---|
| 20 días antes de agotarse | El modal la aplicaba · **"recalcular horizonte desde este lote" NO** (ponía el primer lote a una cadencia exacta del ancla) · el cron de sugeridas usa 25 · el plan automático diario, ninguno |
| Ni fin de semana ni festivo | Correcto en la cadena · el calendario de festivos verificado hasta 2028 |
| Preferir lun/mié/vie | **Construida en `_proxima_fecha_habil(prefer_mwf=True)` y la cadena llamaba SIN ella** (M121: una capacidad que nadie activa no existe) |
| Máximo 200 kg/día | **No existía.** Sólo "2 lotes/día" + "≥100 kg va solo". En `_proxima_fecha_habil` eso implica <200 de rebote, pero **los generadores tienen su propio contador** y sólo miraban cantidad de lotes: dos de 150 kg = 300 kg en una jornada |

**Invariantes:**
- `BUFFER_REORDEN_DIAS = 20` es la fuente única. `first_offset_dias` por defecto es
  `interval_dias − BUFFER_REORDEN_DIAS` en los dos caminos que crean cadena.
- `MAX_KG_POR_DIA_PREFERIDO = 200.0` es **preferencia, no muro**: se saltean los días que se
  pasarían, y si no aparece ninguno se acepta igual (`_respetar_kg=False` en la segunda vuelta,
  con log). Un lote que por sí solo pasa el tope se coloca: frenar una producción por una
  preferencia de carga es peor que el problema.
- El cupo por kilos vive en **tres** lugares y los tres tienen que moverse juntos (M45):
  `_proxima_fecha_habil`, `_tomar_slot` (proyección 2 años) y `_slot` (plan desde hoy).
- Los dos caminos que crean cadena pasan `prefer_mwf=True`.

**+ El kilaje, y por qué tuvo que cambiar en DOS pantallas a la vez.** El default era
`velocidad × (cadencia + 20)`: cada lote duraba 20 días más que la cadencia y el siguiente
llegaba a la cadencia, así que se ganaban 20 días de stock **por ciclo** y se acumulaban
(colchón 20 → 40 → 60 → … → 200 al lote 11 · medido con los números de HYDRABALANCE). Eso es lo
que marcaba 23 de 28 productos como "sobra-stock".

El buffer es del **cuándo**, no del **cuánto**: ya se aplica al fijar la primera producción.
Ahora el **primer** lote de la cadena va más grande (`kg_primer_lote`, trae el colchón) y de ahí
en adelante cada uno repone lo que se vende en la cadencia — el colchón se queda **plano en 20**.

⚠ El tablero `/api/plan/salud-cadenas` comparaba contra `vel × (cad + 20)`. Cambiar sólo el modal
habría dejado las cadenas nuevas leídas como **CORTAS**, gritando al revés. Se movió la
referencia **a la vez**, y además el veredicto de ese tablero ahora sale de `salud_cadena` — la
misma simulación que pinta Necesidades — para que las dos pantallas no puedan volver a decir
cosas distintas del mismo producto (M1/M5/M99).

⚠ **Defecto propio que encontró la medición, no la lectura:** `salud_cadena` llevaba la cobertura
como FECHA y le sumaba timedeltas con fracción de día. Cada vuelta truncaba las horas y el
redondeo se **acumulaba**: una cadena perfectamente dimensionada perdía ~1 día de colchón por
ciclo y a los diez lotes parecía degradarse sola (19 → 18 → … → 10). Ahora la cobertura se lleva
como días (float) y sólo se convierte a fecha al reportar.

Tests: `tests/test_reglas_programacion.py` (en el gate · los tres guards probados desactivando
la regla y viendo el rojo).

## ⚠️ PROG-N+11 · El doble descuento se había vuelto CERO descuento (4-ago · revisión adversarial)

El arreglo de PROG-N+6 se probó con un fixture que ponía `maestro_mee.stock_actual` **a mano**.
Producción no hace eso, y ahí estaba el bug nuevo:

- `marcacion_orden_enviar` **decrementa** el cache del base (`programacion.py:16429`);
- `marcacion_orden_recibir` inserta la Entrada del serigrafiado **sin volver a subirlo**;
- `aplicar_movimiento_mee` **clampea toda Salida contra ese cache**, no contra `SUM(movimientos_mee)`.

Con el cache del serigrafiado en 0, el descuento de envasado registraba una **Salida de CERO**:
sin error, sin log, y con el ítem del checklist marcado como consumido. **El doble descuento se
convirtió en cero descuento, que es peor**: el kardex dice que el envase sigue en bodega.

**Los tres arreglos:**
1. **El cache se sincroniza al LIBERAR**, no al recibir: hasta la liberación el material está en
   CUARENTENA y el stock canónico la excluye, así que subirlo antes lo dejaría discrepando.
2. **La redirección exige `liberado`**, no `recibido`. Recibido = sigue en cuarentena esperando a
   Calidad, o sea no se puede usar; redirigir ahí manda el descuento contra un stock que no existe.
3. **Una Salida que se registra CORTA se declara** (`cantidad_registrada` + `descuento_incompleto`
   + `log.warning`). El clamp la vuelve invisible por diseño: si no se dice, cualquier drift
   futuro del cache vuelve a producir descuentos en cero en silencio (M4/M100).
   Y el `except` ya no atrapa sólo `OperationalError`: `aplicar_movimiento_mee` lanza `ValueError`
   si el código no está en `maestro_mee` con match EXACTO (sin UPPER/TRIM), así que un
   serigrafiado cargado en minúscula tumbaba el cierre del envasado con un 500.

**+ Un flag por control.** El guard anti-duplicado usa `forzar_marcacion`, no `forzar`: ese flag
ya apagaba el guard de `STOCK_INSUFICIENTE` (kardex negativo) y el gate de arte de Dirección
Técnica, así que confirmar una segunda tanda legítima habría apagado los tres. El 409 devuelve
`flag: 'forzar_marcacion'` para que la UI no tenga que adivinar.

**Regla general: cuando un fixture necesite un ajuste que el flujo real no hace, ESE ajuste es el
bug.** El test que vale recorre el ciclo por los ENDPOINTS
(enviar → recibir → liberar → producir) — y de paso apareció que el endpoint de liberar que el
test usaba está **deprecado**: el real es el checklist de arte.

Tests: `tests/test_marcacion_ciclo_real.py` (en el gate).

**+ `slots_kg` se siembra desde la BD.** El tope de 200 kg/día de los generadores contaba sólo
los lotes creados en esa corrida: `slots` (cantidad) sí leía lo ya agendado y `slots_kg` arrancaba
vacío, así que el tope se cumplía dentro de la tanda y se incumplía contra el calendario real.

## 🚦 PROG-N+12 · La urgencia de una orden de marcación se DERIVA de la fecha (4-ago)

`marcacion-ordenes` devolvía `'urgencia': (r[13] or _urg)`, donde `r[13]` es la columna
`urgencia` — que se escribe **una sola vez** al crear la orden, con el valor `'media'`, y nunca
se recalcula. Como `'media'` siempre es truthy, el `or` **jamás llegaba al cálculo real**
(`vencido` / `urgente` / `proximo` / `ok`, derivado de `fecha_alistar`).

Resultado: el semáforo de "Alistar envases" estaba **muerto**. Todo salía amarillo, y una orden
vencida hace cinco días se pintaba igual que una recién creada — con el texto "hace 5d" al lado,
en amarillo.

**Invariante:** `urgencia` se calcula SIEMPRE desde `fecha_alistar` contra hoy-Colombia. La marca
manual viaja aparte en `urgencia_manual` y **no puede tapar el cálculo**. Es M109: un indicador
que alguien tiene que acordarse de actualizar termina viejo y deja de mirarse.

Tests: `tests/test_calendario_no_miente.py` (en el gate).

## 🔗 PROG-N+13 · UN solo bloque de disponibilidad para las dos pantallas (4-ago)

Sebastián: *"quisiera que se viera igual que el de Necesidades, colocando eso que decimos
adicional, así hacemos que crucen perfecto y no tengamos cosas diferentes"*.

Los dos modales contestaban la misma pregunta preguntándole a **endpoints distintos**:

| | Necesidades | Calendario |
|---|---|---|
| Materia prima | `disponibilidad-para-kg` · **los kg de la cadena** | `listo-producir?lotes=1` · **un lote del maestro de fórmulas** |
| Envases | mismo endpoint | `listo-envases` (por lote) |

Dos respuestas distintas del mismo producto, y el que abría cada pantalla no tenía forma de
saber cuál creer. Ahora los dos llaman a `plan.disponibilidad_para_kg`. El bloque viejo del
calendario queda **sólo como respaldo dentro del `catch`**: si el nuevo falla, se ve el anterior
en vez de un hueco (M112).

**+ Lo que el bloque muestra ahora (los tres pedidos del dueño):**
- **Las presentaciones del producto**, cada una con sus unidades: *"de este lote salen 3.093 uds
  de 30 ml y 732 de 10 ml"*.
- **La foto del envase de bodega** al lado de cada presentación. El dato ya existía
  (`maestro_mee.imagen_url`, mig 298, se carga desde la grilla de Bodega) y no llegaba a esta
  pantalla: sólo hubo que pedirlo. Si el envase no tiene foto se muestra un marcador, nunca una
  imagen inventada.
- **Cuánto se envasa de cada una**, con el reparto **pesado por volumen** (uds × ml, M72): una
  unidad de 30 ml se lleva el triple de granel que una de 10, así que aplicar el share de
  unidades al kg sub-asignaba la presentación grande. Test con dientes: con ventas 800/200 el
  30 ml se lleva >90% del bulk y las unidades quedan 4 a 1, como las ventas.
- Y se **declara** cuando una presentación apunta a un envase **descontinuado** (hoy nada lo
  bloquea) o cuando no tiene envase asignado.

**Invariantes:** el reparto se pesa por volumen, nunca por share de unidades · la foto se LEE
del maestro, no se guarda acá · el endpoint se llama con debounce y token de secuencia porque
se dispara al cambiar los kg (M43) · lo que está en serigrafía se informa, no se resta
(PROG-N+11).

Tests: `tests/test_modal_unificado.py` (en el gate · foto y pesado por volumen probados
revirtiendo cada uno).

## 🧮 PROG-N+14 · El desglose cuadra, y el truncado se declara (4-ago)

**El encabezado de Abastecimiento no sumaba su propio total.** `eos_proyeccion` — el plan rodante
a 2 años, que suele ser la MAYORÍA de los lotes — no caía ni en `n_fijas` ni en `n_sugeridas` y
se iba a `n_otras`, que la pantalla nunca pintaba: se leía *"1.400 lotes · 120 Fijas · 60
Sugeridas"* y el resto no aparecía por ningún lado. Un desglose que no suma el total obliga a
desconfiar de los tres números. La proyección es una Sugerida más (así la trata el resto del
motor) y `'calendar'` se sacó de la lista: ese origen se eliminó el 7-jul.

**Y `n_b2b` son PEDIDOS, no lotes.** Iba en la misma suma que dos conteos de lotes, así que el
renglón nunca cerraba. Ahora va aparte, con su palabra.

**El truncado silencioso.** El SELECT del calendario corta en 6.000 filas ordenando por
`fecha_programada ASC`, así que lo que se pierde al llegar al tope es **el futuro** — justo lo
que el calendario existe para mostrar. La respuesta ahora trae `truncado`, `tope` y `aviso`, y
deja un `log.warning`. Un total que se cortó y no lo dice es un total falso (M100/M124).

## 🚦 PROG-N+15 · La urgencia de marcación (ver PROG-N+12) y el semáforo vivo

Complemento operativo de PROG-N+12: el campo `urgencia_manual` viaja en la respuesta de
`marcacion-ordenes` para no perder la marca que alguien haya puesto, pero **no participa del
color**. El semáforo sale siempre de `fecha_alistar` contra hoy-Colombia:
`vencido` (< 0 días) · `urgente` (≤ 3) · `proximo` (≤ 8) · `ok`.

## 📦 PROG-N+16 · El lead time de un ENVASE sale de `mee_lead_time_config` (5-ago)

`abastecimiento_consumo_horizontes` emitía **14 días para todos los envases**, con un
`TODO leer de mee_lead_time_config` al lado. Esa tabla existe desde la mig 71 y está sembrada con
los datos reales: frasco de China **180 días con MOQ 5.000**, tapa local 30, etiqueta 15,
serigrafía 20. O sea que el motor le decía a Compras que un frasco importado se pide con dos
semanas de anticipación cuando son seis meses — no es un número feo, es una decisión de compra
equivocada esperando a pasar.

**Invariante:** el `lead_time_dias` de un ítem MEE sale de `mee_lead_time_config`; el 14 queda
sólo como respaldo. La tabla se lee **en bloque, una sola vez** antes del loop (nunca una consulta
por envase · M43), y el ítem declara `lead_time_medido` (bool), `origen_compra` y `moq_unidades`.
Lo que no tiene fila se DECLARA: un 14 inventado se lee igual que un 14 medido, y esa es la
diferencia que importa (M124). Si la tabla no se puede leer, se avisa por log — no se cae al
default en silencio, porque el default es justo el número que estaba mal.

## 🧴 PROG-N+17 · El checklist de envasado se abre por PRESENTACIÓN (5-ago)

`_generar_checklist_produccion` creaba **una sola fila de envase**, con el código y el volumen de
la presentación por defecto. Para un producto que sale en dos presentaciones (30 ml y 10 ml, con
frascos distintos) eso descontaba todo contra un único código usando un volumen promedio que no
existe físicamente: el desglose que la pantalla promete y lo que la planta consume eran dos cosas
distintas.

**Invariante:** si `producto_presentaciones` tiene más de una presentación activa con envase y
volumen, el checklist emite **una fila por presentación**, y el reparto pesa por **volumen
(uds × ml)**, igual que el resto del sistema (M72) — una unidad de 30 ml se lleva el triple de
granel que una de 10.

⚠ **Y la trampa que trajo abrir el checklist:** `_descontar_mee_envasado` le restaba el total de
envases B2B con envase propio a **CADA** fila marcada como envase. Con una sola fila daba igual;
con varias restaba el mismo B2B dos veces y **descontaba de menos**. Ahora el remanente
(`_b2b_por_restar`) se consume entre las filas, no se repite en cada una. Regla general: cuando
un total se resta dentro de un loop, preguntá si el loop puede tener más de una vuelta.

## 🖥️ PROG-N+18 · Los dos modales tienen la MISMA cara (5-ago)

Necesidades y Calendario ya compartían el **cálculo** (`/api/plan/disponibilidad-para-kg`). Desde
hoy comparten también la **cara**, que es la que Sebastián aprobó:

    veredicto en una línea → ① Cómo va → ② Qué decido (dominante) → ③ Con qué cuento → ④ Qué queda agendado

En el del calendario eso significó dos movimientos, no un maquillaje: el **selector de envase y
las presentaciones** dejaron de abrir el modal (un detalle de configuración no puede ser lo
primero que se ve) y el **chequeo de materiales** bajó al bloque ③ — antes salía antes de que el
usuario eligiera los kilos, o sea contestaba *"alcanza"* sobre un kilaje que todavía no había
decidido.

**Cómo se hace un reordenamiento así sin perder HTML** (M156): se captura el bloque en una
variable (`_htmlConQue`) y se emite después, cambiando SÓLO el acumulador dentro de un rango
acotado por contenido. Borrar un `<div>` **no** rompe la sintaxis, así que el node-check pasa
verde con la pantalla partida: las verificaciones que sí lo cazan son contar las marcas conocidas
antes y después, el balance de `<div>`, y que el bloque se declare y se emita exactamente una vez.
Todo eso vive en `tests/test_modal_calendario_cara.py`, dentro del gate.

## 🔒 PROG-N+19 · La disposición de un lote de PT va con CAS (5-ago)

`planta_cola_liberacion_disposicion` hacía `UPDATE cola_liberacion SET disposicion=… WHERE id=?`
sin repetir el estado ni mirar `rowcount`. Consecuencia: **un lote que Calidad ya RECHAZÓ se
podía volver a poner en `liberado` con un clic posterior**, sin un solo 409 — un control INVIMA
que se elude en silencio. Y dos decisiones simultáneas (liberar + rechazar) pasaban las dos,
quedando la que commiteara último. Es el hermano sin arreglar de lo que M27 cerró en `brd.py`.

**Invariante:** no se sale de un estado TERMINAL. El `WHERE` exige
`LOWER(COALESCE(disposicion,'')) NOT IN ('aprobado','rechazado')`; si `rowcount==0` → rollback y
**409 `LOTE_YA_DISPUESTO`**, diciendo qué disposición tiene y quién la firmó. `reanalizar` sigue
siendo re-disponible, que es exactamente para lo que existe ese estado.

Cambiar una disposición ya firmada es un acto de Calidad, no un clic: si hace falta, va por el
camino documentado (desviación / control de cambios), no sobrescribiendo la fila.

## ⚡ PROG-N+20 · El plan semanal precarga en vez de consultar por MP (5-ago)

`/api/planta/plan-semanal` hacía, por cada producción de la ventana (~30) **y por cada MP de su
fórmula** (~20), dos consultas: el nombre del material y su stock. Del orden de **1.200-2.000
consultas por request**. Con 3 workers Gunicorn eso no es "una pantalla lenta": dos personas
abriéndola a la vez dejan la app entera sin atender y el resto empieza a devolver "Unexpected
token '<'", que es el 502 servido como HTML (M43/M59).

**Invariante (M128): el atajo ACELERA la respuesta, NO la cambia.**
- El SUM precargado usa el CASE **idéntico** al de `stock_mp_total` — que **incluye cuarentena a
  propósito**, porque el plan mira consumo FUTURO y esos lotes, si salen de QC a tiempo, cuentan.
  Excluirlos inventaría déficits.
- Lo que no esté en el precalculado **cae al helper de siempre**, no se asume cero: un stock en
  cero es un déficit inventado.
- Si la precarga entera falla, se avisa por log y el endpoint va por el camino lento — más
  lento, pero correcto.

**+ la columna de días de inventario dejó de estar muerta.** La consulta de velocidad estaba
apagada con `if False` porque apunta a `ordenes_shopify_items`, que no existe, y nadie la
reemplazó: `velocidad_dia` valía 0 SIEMPRE y la columna salía en gris en todas las filas desde
que se escribió. Ahora sale de `ventas_diarias`, la tabla que el cron precalcula y que el resto
del sistema ya usa para esto.

Tests: `tests/test_plan_semanal_rapido.py` y `tests/test_bugs_5ago.py` (los dos en el gate).
⚠ El test de equivalencia siembra un lote **en cuarentena** a propósito: sin él la comparación
contra el helper es ciega justo a la diferencia que la invariante protege — lo descubrí probando
los dientes, que la primera versión no tenía.


## 📦 INV-11 · El diagnóstico de envases mide la unión COMPLETA, no sólo el frasco (5-ago)

`GET /api/abastecimiento/envases-cobertura` contestaba media pregunta (*"¿el producto tiene
frasco?"*), pero el motor de compra también lee la **tapa**, la **caja** y las **piezas** del
frasco (`mee_partes`). Un producto con frasco y sin tapa salía en VERDE mientras su tapa no se
pedía nunca — la capacidad de comprarla está construida desde el 18-jun y sin un solo dato, que es
igual a no existir (M121).

La respuesta agrega `union`: por presentación, `envase`/`tapa`/`caja`/`piezas`/`serigrafiado` y
**`falta`** enumerando pieza por pieza lo que impide comprar o descontar. Un código que existe pero
no está en `maestro_mee` cuenta como faltante: *"tiene tapa"* y *"tiene una tapa que existe"* no
son lo mismo. `serigrafiado` es `maestro_mee.material_referencia` (el puente base → impreso); vacío
significa que lo que vuelve de serigrafía no queda atado a ese producto.

Reglas: los contadores del encabezado (`n_completas`, `n_sin_tapa`…) salen del **mismo recorrido**
que el detalle — contados aparte, un día dicen cosas distintas y no se puede creer en ninguno
(M5/M161). Si el detalle no se pudo calcular, `union` viene en `null` y `aviso` lo dice: una lista
vacía se leería como *"está todo bien"* (M100). El cambio es **aditivo** — la pantalla de Reparto
ya consumía `sin_envase`/`no_aplica` y no puede romperse (M117).

Además marca **qué frascos hay que mandar a serigrafiar**: los que están EN BLANCO y todavía no
tienen su impreso. ⚠ La señal NO puede ser la palabra *"blanco"*: medido en el maestro real,
`FRASCO BLANCO CUADRADO`, `FRASCO BLANCO PUFF` y `ENVASE REDONDO BLANCO` son frascos de **color**
blanco, no frascos sin marcar — detectarlos así haría gritar la alerta por medio inventario, y una
alerta que suena siempre deja de mirarse justo el día que importa (M129/M144). Las señales reales
(`NO PRINT`, `SIN SERIG`…) viven en `app_settings.envase_blanco_patron` para ajustarlas sin
desplegar cuando aparezca una forma nueva de escribirlo (M108/M122), y el resultado DEVUELVE cuál
señal coincidió — no un booleano pelado — para poder auditar por qué se marcó un envase.

Los **dos** hechos juntos son la alerta: un frasco en blanco que ya tiene su serigrafiado asignado
está resuelto, y un pre-impreso de China sin puente no necesita marcarse.

**Dónde se mira: POR PRODUCTO, en un modal de Planta.** Sebastián, al no encontrarlo:
*"preferiría que revisemos por productos no crees? que quede un modal para eso"*. La primera
versión vivía en `/planta` › Configuración › Reparto envases -- tres niveles -- y ordenada por
PRESENTACIÓN, que no es como se piensa el negocio ("este producto, ¿tiene todo su empaque?").
El modal (`empqAbrir`, botón en la barra de **Necesidades**) agrupa por producto, filtra por
defecto a los que les falta algo y pone lo incompleto primero: un tablero que hay que leer entero
para encontrar el problema no se lee. Los productos SIN ninguna presentación entran igual — son el
peor hueco (su empaque no se compra en absoluto) y listando sólo `union` desaparecerían (M124).
Los KPI se cuentan sobre TODOS, no sobre lo filtrado, o cambiarían al escribir en el buscador (M5).

Tests: `tests/test_union_producto_envase.py` y `tests/test_modal_empaque_por_producto.py`
(los dos en el gate).


## 📦 INV-12 · Las VENTAS deciden qué presentación existe · y se arregla ahí mismo (5-ago)

Sebastián, viendo el modal con datos reales: *"deberías ver cuál de esos realmente tiene ventas en
Shopify y me los pones allí para mapear todo perfectamente, es parte fundamental"*. Y en su
pantalla se veía por qué: RENOVA C10 con **dos filas de 15 ml y el MISMO frasco**, AH 1.5% con dos
de 10 ml. Una de las dos es un duplicado que **dobla la demanda** de ese envase. Cuál sobra no se
adivina por el nombre: se mira cuál vende.

`union` devuelve por presentación `ventas_180d` + los `skus` que vendieron, por el **MISMO camino
que el motor de reparto** (`_ventas_sku_180d` + `sku_producto_map` por producto/volumen · M58/M72):
el número que se muestra tiene que ser el que DECIDE, o pantalla y motor cuentan historias
distintas (M5). `None` = no se pudo medir, `0` = no vendió — un cero inventado se lee como "esta
presentación no se usa", que es justo la decisión que se está tomando (M100).
⚠ Sin ventas NO se apaga nada solo: un producto nuevo todavía no vende y apagarlo lo sacaría del
plan. Se marca (`n_sin_ventas`) y decide la persona.

**`POST /api/programacion/presentacion-empaque`** (id + `activo`/`envase`/`tapa`/`caja`) permite
elegir cuál se usa y completar el empaque sin salir del modal. Reglas:
- **PATCH parcial**: sólo se toca lo que viene en el body. Mandar el objeto entero desde una
  pantalla que no muestra todos los campos los pisaría con vacío (M85).
- **Apagar es `activo=0`, NUNCA DELETE**: puede haber histórico colgando y el borrado no se
  deshace. Encender de vuelta es un clic.
- Un código que **no está en `maestro_mee` se RECHAZA** (400): dejarlo entrar convierte un hueco
  visible en uno invisible — el campo se ve lleno y el motor no encuentra nada que comprar (M100).
- Audita con el valor **previo**: sin el `antes` no se puede revertir (regla 5 del cerebro).

La `union` incluye ahora las presentaciones **apagadas** (marcadas `activo:false`): para elegir
*cuál se usa* hay que ver las que no se usan, y sin eso apagar sería una operación de un solo
sentido. Una presentación apagada **no reporta huecos** — no se compra ni se descuenta, así que
exigirle tapa sería ruido — y no entra en los contadores.

⚠ Trampa propia al escribirlo: usé `_u` como variable del loop de ventas y `_u` era el alias de
`unicodedata` en esa misma función. Rompió el normalizador tres líneas más abajo y sólo se vio
porque el `except` lo DECLARA en vez de devolver una lista vacía.

**"No lleva" es una RESPUESTA, no un hueco** (mig 419 · `sin_tapa`/`sin_caja`). Sebastián, viendo
un envase redondo de 150 ml en rojo por tapa y caja: *"digamos este no tiene ni tapa ni caja, cómo
hacemos con esos"*. El diagnóstico trataba VACÍO como FALTA, así que un envase que de verdad no
lleva caja se quedaba en rojo para siempre — y un tablero que grita siempre deja de mirarse justo
el día que importa (M129/M144).

Tres estados distinguibles: **con código** (resuelto) · **vacío** (falta cargarlo) · **"no lleva"**
(decisión registrada). El MOTOR no cambia: sigue leyendo `tapa_codigo`, y sin código no hay nada
que comprar en los dos casos — la bandera sólo cambia lo que el DIAGNÓSTICO reporta, que es donde
estaba el ruido. Son EXCLUYENTES: poner un código apaga la bandera y declarar "no lleva" borra el
código, porque si quedaran los dos el diagnóstico tendría que elegir a cuál creerle (M5). El
centinela `__NO__` de la pantalla se traduce a la bandera y NUNCA viaja al campo del código: ahí
quedaría guardado como un material a comprar que no existe (M100).

Tests: `tests/test_union_producto_envase.py` (en el gate).

### INV-17 · Toda edición de `producto_presentaciones` deja QUIÉN (8-ago-2026)

De esta tabla salen el envase, la tapa, la caja y la etiqueta que se **compran** y se
**descuentan**. Cambiar acá el frasco de un producto no da error: da una compra equivocada, y sin
rastro no hay forma de saber quién ni cuándo. Regla de Sebastián al dictar los permisos: *"los
cambios quedan con el usuario que lo modifica"*.

Los diez endpoints que la escriben pasan por `_pres_rastro`, que guarda una **foto ANTES y otra
DESPUÉS de las mismas columnas** (no campo por campo): así el rastro alcanza para deshacer, porque
ante un frasco equivocado la pregunta es *"¿cuál era antes?"*, no *"¿cuál es ahora?"*. Es
best-effort -- nunca tumba la operación -- pero su fallo se loguea, no se traga.

Enumerar los sitios a mano no alcanza: el guard **recorre el fuente** y falla si alguna función
con ruta escribe la tabla sin llamar al rastro (así encontró dos que se habían pasado por alto, y
así el endpoint que se escriba mañana no nace mudo).

También dejan rastro las dos decisiones del maestro de envases que viven en este blueprint: el
método de marcación (`marcacion_tipo`/`marcacion_proveedor`, que decide si el envase sale a
serigrafía y a qué proveedor se le paga).

Tests: `tests/test_rastro_empaque.py`, `tests/test_rastro_maestro_envases.py` (en el gate).

### INV-11 · Registro en contingencia · la fecha del HECHO y la de CARGA son dos cosas (12-ago-2026)

Tarea B-13 del ASG-PRO-014 (numeral 5.6.2). Cuando no hay energía ni conectividad la planta
registra en los formatos impresos; `registros_contingencia` es la puerta por la que ese papel
entra al sistema.

**La invariante:** `fecha_hecho` sale del papel y `cargado_at` / `cargado_por` los pone el
SERVIDOR, nunca el cliente. Un registro cargado de manera que aparente haber sido capturado en el
momento convertiría una contingencia legítima en un registro falso, y eso es peor que el hueco que
el mecanismo viene a tapar.

**Qué se rechaza y qué se avisa** (la distinción es deliberada): se rechaza lo IMPOSIBLE (fecha
futura, tipo fuera de la lista blanca, archivo que no puede ser evidencia) y se AVISA lo demás
(sin foto del papel, carga fuera del plazo de 24 h, sin lote) sin bloquear. El dato ya existe en
papel: impedir su entrada no lo mejora, sólo lo deja afuera del expediente.

**Con lote se inscribe en `documentos_regulados`** vía `registrar_documento`. Sin ese paso el
registro viviría en una tabla propia y el expediente del lote seguiría teniendo el mismo hueco,
que es justamente lo que se venía a resolver.

Puede cargar quien estuvo en el turno: PLANTA ∪ CALIDAD ∪ ASEGURAMIENTO ∪ ADMIN. Restringirlo a un
solo rol dejaría al que firmó el papel sin poder subirlo (M171/M32).

Endpoints: `POST/GET /api/planta/contingencia`, `GET /api/planta/contingencia/<id>/soporte`,
pantalla `GET /planta/contingencia` (enlazada desde la barra principal de Planta · M121).

Tests: `tests/test_contingencia.py` (en el gate), incluidos los dos bordes de permiso y el guard
de que el cliente no puede dictar la fecha de carga.

### INV-12 · El paquete de contingencia usa la MISMA lista que el legajo (12-ago-2026)

Tarea B-12 (numeral 5.6.1 del ASG-PRO-014). `GET /planta/contingencia/paquete` imprime los seis
formatos en blanco que la planta llena a mano cuando no hay energía ni conexión.

**La invariante:** los 12 ítems del despeje salen de `brd.DESPEJE_LINEA_ITEMS`, la misma constante
que usa el legajo electrónico. Si el papel trajera otra lista, el operario verificaría una cosa en
el piso y el registro cargado después diría otra, y esa diferencia no la detecta nadie. Igual los
campos de cada formato: son los que exige el COC-LMA-003 para el registro que reemplazan, porque
un formato con menos campos produce un papel que no se puede cargar completo.

Imprimible de verdad (M123): `print-color-adjust: exact` y bordes en negro explícito dentro de
`@media print`. Sin eso el navegador no pinta los fondos y el formato llega al piso sin sus
divisiones, que es exactamente lo que ya se reportó con los rótulos.

Enlazado desde `/planta/contingencia`, que es donde se entra a cargar: el paquete tiene que estar
impreso ANTES de la falla, porque el día de la contingencia no hay con qué imprimirlo.

Tests: `tests/test_contingencia.py` (en el gate).

### INV-13 · La cola de contingencia reintenta, y reintentar no puede duplicar (12-ago-2026)

Tarea B-14, primera etapa. Si la conexión se interrumpe al enviar el registro de contingencia, lo
escrito queda en el navegador y se manda solo cuando la conexión vuelve.

**La invariante:** `registros_contingencia.token` es único y lo genera el CLIENTE, uno por
registro, estable entre reintentos. Es lo que impide que un reintento cree un segundo registro del
mismo hecho.

**Por qué el servidor no puede resolverlo solo:** un reintento ocurre cuando se pierde la
RESPUESTA, no la petición, y desde el cliente esos dos casos son idénticos. El servidor tampoco
puede distinguirlo comparando los datos, porque dos dispensaciones iguales el mismo día son dos
hechos distintos y colapsarlas perdería registros reales, que es peor que duplicar (M45). Por eso
la unicidad la declara quien origina, igual que la recepción (mig 265).

Con token repetido el endpoint responde `duplicado: true` con el id del registro que ya existe, y
no inserta. Sin token, dos envíos son dos registros.

**Alcance declarado:** la cola cubre el formulario YA ABIERTO. No permite abrir la pantalla sin
conexión, así que la planta no puede considerarse capaz de operar desconectada y la contingencia
en papel sigue siendo el mecanismo previsto (ASG-PRO-014 numeral 5.6.3).

Tests: `tests/test_contingencia.py` (los dos bordes del token) · mig 425.

---

## INV · El material de MARCA DEL CLIENTE se DERIVA de los pedidos, nunca se copia

**Desde el 15-ago-2026.** Catalina define al aceptar un pedido B2B **si** lleva etiqueta y
**si** lleva caja (`pedidos_b2b.lleva_etiqueta` / `lleva_caja`, mig 432) y **cuál**
(`etiqueta_codigo` / `caja_codigo`, mig 436). Esa etiqueta lleva la marca del cliente, así
que **nunca sale de `producto_presentaciones`** — esa es la de ÁNIMUS.

- **UN solo resolvedor:** `_material_cliente_lotes(c, produccion_ids)` (y
  `_material_cliente_lote` para uno, que delega en él). Dos copias de la misma regla
  divergen el día que alguien corrige una (M3/M99).
- **Se DERIVA en cada lectura**, no se copia al `produccion_checklist`: un total guardado
  al lado de sus sumandos diverge (M99).
- **Resuelve la LISTA en UNA consulta.** Pedirlo lote por lote desde una pantalla es lo
  que satura los tres workers (M43/M63) — se escribió mal la primera vez, dentro del
  recorrido, y hay un guard que lo impide.
- **Sin código se DECLARA** (`falta_definir: True`), nunca se adivina un código parecido:
  así es como se termina comprando el material de otro cliente (M19/M100). Y al guardar,
  un código que no está en `maestro_mee` se **rechaza** (400 `MATERIAL_INEXISTENTE`):
  apuntar al vacío no da error, da un material que nadie ve hasta el día que falta.
- Lo consume el maestro de lotes (`/calidad/maestro-lotes`), que lo muestra por lote junto
  al resto del material de envase.

Tests: `tests/test_material_cliente_lote.py` (en el gate).

---

## INV · El rótulo F02 que se IMPRIME es un formato, no un registro

**Desde el 15-ago-2026.** `/planta/rotulos-limpieza` y `/planta/rotulo-limpieza/<area>/pdf`
imprimen un **formato para llenar**. El **registro** firmado tiene su propia URL estable
por-registro (`/planta/rotulo-limpieza/registro/<id>/pdf`), que es la que va al expediente
por lote.

- **La firma sólo se preimprime si la limpieza es reciente** (`_ROTULO_FIRMA_VIGENTE_DIAS`,
  hoy 3 días · helper `_rotulo_firma_vigente`). El F02 acompaña la producción del momento.
  Antes se tomaba el último ciclo del área sin mirar la fecha: en producción ése era una
  demo de junio, así que **todas las salas salían prefirmadas por quien no ejecutó esa
  limpieza** — un registro regulado prefirmado es un registro falso.
- **Si el ciclo es viejo se descarta ENTERO**, no sólo la firma: el producto, el lote y los
  equipos de un ciclo de hace dos meses no hablan de este lote (M19).
- **Se elige qué equipos se imprimen.** Sin parámetros, la ruta muestra el selector
  (`_rotulos_limpieza_selector`); con `?equipos=COD1,COD2` imprime ésos;
  `?todos=1` conserva el comportamiento anterior y es lo que usa el botón "Imprimir TODOS"
  del dashboard — esa URL está enlazada y no se rompe (M120). `_rotulos_de_area` acepta
  `solo_codigos` para acotar.
- Nada viene marcado de fábrica en el selector: marcar todo por defecto reproduce el
  problema con un paso extra.
- **El rótulo de un EQUIPO no lleva área, y el ÁREA tiene el suyo** (Sebastián 21-ago-2026:
  *"los rótulos de equipo no llevan área, entonces debe decir sólo equipo sin área; pero
  además necesito rótulos para el área"*). El encabezado dice `Equipo · código` o
  `Área · código` según qué se pidió, y el renglón de área existe **sólo** en el del área,
  una vez. Razón: el rótulo del equipo se pega en la máquina y **la máquina se mueve entre
  salas**, así que nombrar el área ahí afirma algo que puede dejar de ser cierto — es la
  misma razón por la que el 20-ago se quitó *"Sala / área"*.
  - La sala se pide como un ítem más: `?equipos=AREA:<codigo>` (el selector la emite con
    `value="AREA:<cod>"`). Se resuelve **por código y FUERA** del loop que recorre las áreas:
    ese loop deduplica por NOMBRE para no imprimir dos veces la misma sala cuando conviven
    códigos gemelos (`FAB2`/`PROD2` se llaman igual), y con la gemela primero **se comía la
    sala pedida en silencio** (M261).
  - La sala sigue en el **índice de búsqueda** de cada fila de equipo (`data-buscar`) aunque
    no se pinte: se puede buscar por *"fabricación 2"* sin que el papel prometa un área.

Tests: `tests/test_rotulo_limpieza_firma_y_equipos.py` (en el gate) + `test_rotulo_limpieza.py`.

**Quién firma el F02 es QUIEN LIMPIA, no quien fabrica** (Sebastián 15-ago-2026: *"el que
limpia no siempre es el que fabrica... tenemos operaria de limpieza"*). El selector lo
pregunta y propone al operario con `rol_predeterminado='limpieza'`, **sólo si hay uno**
(con dos no hay forma de saber cuál va · M179). El nombre se imprime en la línea para no
escribirlo a mano, **sin la marca de firma electrónica** — ésa certifica que la persona
ejecutó el acto. El operario de FABRICACIÓN no viaja a este rótulo.

⚠ El rol `limpieza` se valida en **DOS** whitelists (`POST` y `PATCH` de
`/api/planta/operarios`): agregarlo en una sola lo convierte en `todero` en silencio
(M116/M45). Hay un guard que recorre todas.

---

## El ciclo de la SALA · sucia → limpiando → libre (16-ago-2026)

Sebastián, trabado al arrancar el demo: *"no me deja, porque dice que las áreas de fabricación
están sucias · creo que eso no está siendo útil el plano y limitar eso, ¿será que lo eliminamos?"*.

**No se eliminó, y por una razón concreta:** el despeje de línea está en `PRD-PRO-001` (lo ejecuta
y firma el Jefe de Producción, y Control de Calidad lo verifica de forma independiente), y el
rótulo F02 se apoya en el mismo `areas_planta.estado`. Lo que estaba mal no era el control sino
que **no había por dónde cerrarlo**.

El ciclo, y quién mueve cada paso:

| De → a | Quién lo mueve |
|---|---|
| libre → **ocupada** | `prog_iniciar_produccion` |
| ocupada → **sucia** | `prog_terminar_produccion` |
| sucia → **limpiando** | `planta_rotulo_limpieza_realizar` (el operario registra la limpieza) |
| limpiando → **libre** | `liberar_sala_con_despeje` — **ruta ÚNICA** (M3), la llaman el rótulo verificado por Calidad y la pantalla `/planta/despeje-linea` |

**Reglas:**

- **`liberar_sala_con_despeje` es el único punto que pone una sala en LIBRE.** Ningún endpoint
  escribe ese estado por su cuenta: si hace falta liberar desde otro flujo, se llama al helper.
- **Sólo se libera desde SUCIA o LIMPIANDO.** El UPDATE iba `WHERE id=? AND activo=1` a secas, así
  que verificar una limpieza sobre una sala **OCUPADA** la ponía libre y borraba que había un lote
  adentro — el plano diría que se puede arrancar otra producción encima. Una sala con producción en
  curso no está despejada, por definición.
- **La respuesta DICE si el área quedó libre** (`area_liberada`). Antes el mensaje afirmaba
  *"liberada"* pasara lo que pasara. Y el dato se **relee de la tabla**, nunca del `rowcount` del
  UPDATE: acá el rowcount da 0 con la fila actualizada, así que la respuesta diría lo contrario de
  lo que pasó (M161).
- **La pantalla del despeje está ENLAZADA** desde Rótulos de Limpieza. Existía desde mayo, marcada
  como *"accesible directo, oculto"*, y **ningún enlace en todo el código**: la única forma de
  llegar era escribir la URL de memoria (M121).
- **El aviso `DESPEJE_REQUERIDO` manda a una ruta que existe.** Decía *"usar
  /api/planta/despeje-linea"* y esa ruta nunca existió — la real no lleva `/api`. Ahora incluye la
  `url` y hay un guard que la valida contra el `url_map` real (M202).

⚠ **Al diagnosticar esto casi meto un UPDATE duplicado** "porque el endpoint no liberaba": lo había
buscado DENTRO de la función y la liberación ocurre en el helper que llama una línea más arriba
(M94). Lo cazó el test del borde — el de la sala ocupada —, que es justo el que parece que no
aporta. Fijado en `tests/test_la_limpieza_libera_el_area.py` (en el gate).

---

## El PLANO de planta · la distribución real, en vivo (16-ago-2026)

Sebastián dibujó la planta en Paint y pidió que el plano fuera así: *"la idea es que fuera súper
inteligente · si salía sucia el área le daban click encima para limpiar"*, y *"que apenas la
producción se monte aparezca allí el producto y la cantidad con el operario · recordá los tiempos
… así Alejandro y yo sabemos en tiempo real qué hacen"*.

Era una grilla que acomodaba las tarjetas sola (no decía dónde queda nada) y **no estaba enlazada
desde ninguna pantalla**.

**Reglas:**

- **El mapa es fijo** (`grid-template-areas`), con las nueve salas del dibujo en su lugar. El
  bloque de *otras áreas* sí se acomoda solo: ahí no hay posición física que respetar.
- **Las salas del mapa se declaran por CÓDIGO y se verifican contra la base.** Dibujar una sala
  que el sistema no tiene sería inventar planta; si falta, la pantalla lo dice y hay un test que
  falla.
- **Ninguna sala se esconde.** Las que existen y no están en el dibujo se muestran abajo: una sala
  sucia que nadie ve no se limpia nunca (M124).
- **El clic hace lo que toca según el estado** — sucia → registrar la limpieza · limpiando →
  verificar (Calidad) · ocupada → abrir su legajo · libre → programar. Es lo que convierte el
  cartel de "área sucia" en la salida.
- **El estado va también en TEXTO**, no sólo en color.

**De dónde salen los tiempos** (lo que decide si la pantalla sirve):

| Dato | Fuente | Base horaria |
|---|---|---|
| arranque de la producción | `produccion_programada.inicio_real_at` | **Colombia** |
| etapa en curso y su duración | `ebr_ejecuciones` de esa fase (`iniciado_at_utc`) | **UTC** |
| paso actual | `ebr_pasos_ejecutados` | UTC |
| estimado de la fase | `SUM(mbr_pasos.tiempo_estimado_min)` | minutos |

⚠ **NO se usan `produccion_programada.etapa_disp/elab/env_*_at`**: están en el esquema y **nadie
las escribe**, así que un plano que las leyera mostraría tiempos vacíos para siempre (M154).

⚠ **El "ahora" se ancla a `datetime.now(timezone.utc)`, nunca a `datetime.now()`.** Ese devuelve
la hora LOCAL del servidor, así que sólo daba bien porque Render corre en UTC; en una máquina en
hora Colombia restaba 5 horas de más y el plano mostraba *"hace 0 min"* para un lote de dos horas.
Lo mostró la previa con datos sembrados, no la lectura del código (M24).

Fijado por `tests/test_plano_de_planta.py` (en el gate).


---

## La alerta de MP de China tiene que poder sonar (17-ago-2026)

`_get_china_mps` alimenta DOS alertas de `_project_stock`: la de *"MP de China sin stock ·
comprar HOY o se detiene la línea"* (escala a **crítico**, porque con 60 días de lead time ya
estás tarde) y la anticipada cuando la cobertura proyectada cae por debajo del lead time.

Devolvía **siempre un set vacío**: pedía `SELECT id` y `maestro_mps` no tiene esa columna (su
llave es `codigo_mp`). Reventaba en cada llamada, un `except: pass` lo tragaba, y las dos
alertas nunca se dispararon. **Una alerta que no suena se ve igual que una que no tiene motivo
para sonar** — por eso nadie lo reportó.

Invariantes:
- La consulta se llavea por **`codigo_mp`**, nunca por `id`.
- El set incluye también los **códigos de fórmula** que llegan a esas MPs por
  `mp_formula_bridge` activo: la comparación se hace contra `formula_items.material_id`, que
  puede ser un código fantasma (M1). Un puente inactivo NO cuenta.
- El `except` **loguea**: un set vacío acá apaga una alerta crítica sin dejar rastro (M4).

Guard: `tests/test_alerta_mp_china.py` (probado con dientes reintroduciendo `SELECT id`).

---

## 🏷️ El rótulo F02 sale a una TÉRMICA (20-ago-2026)

Tres cosas que decidió la etiqueta impresa, no la pantalla:

1. **El logo se binariza en el servidor** (`_logo_mono_datauri`), reduciendo PRIMERO al tamaño de
   impresión y binarizando DESPUÉS: al revés, la interpolación del navegador vuelve a inventar
   los grises y el logo sale rayado. Va con `image-rendering: pixelated` y
   `print-color-adjust: exact` (sin eso el chip del estado activo se imprime sin relleno y su
   texto blanco queda invisible). El logo se declara UNA vez en el CSS del documento: embebido
   por hoja eran 180 copias del mismo PNG.
2. **El rótulo por equipo NO lleva la sala.** Se pega EN la máquina y la máquina se mueve entre
   salas; la sala del ciclo queda en el registro `rotulos_limpieza`, que es lo que va al
   expediente.
3. **La línea de la firma va vacía.** El asignado y el que termina limpiando no siempre son el
   mismo, y un nombre ya impreso empuja a que firme quien no hizo el acto. Con eso el
   desplegable de "quién limpia" dejó de cambiar lo que sale de la impresora y se retiró.

**Un rótulo por ESTADO** (`?estados=limpio,en_uso,sucio`): el área pasa de limpia a en uso y a
sucia en la misma jornada, así que se imprime el juego y se cambia la etiqueta pegada. Sin el
parámetro sale una sola con el estado real del área -- la URL vieja no cambia de comportamiento.

Guard: `tests/test_areas_y_rotulo_20ago.py` + `tests/test_rotulo_limpieza_firma_y_equipos.py`.

### El rótulo, ajustado en el piso (21-ago-2026)

- **Nunca nombra un lote de demostración.** El derivador saltea las producciones demo (nombre o
  lote) y toma la primera REAL; si el ciclo de limpieza guardado habla de un demo, sus datos de
  proceso tampoco se imprimen. Guard: `tests/test_rotulo_sin_demo.py`.
- **Todo lo que imprime se puede escribir antes** (producto, lote, producto anterior, lote
  anterior, sanitizante, detergente). Se autocarga con lo que el sistema ya sabe -- la sala
  elegida, o el lote que está corriendo -- y lo escrito MANDA sobre lo derivado. Vacío es una
  decisión: deja el renglón para llenarlo a mano. Lo único físico es la firma.
- **Un campo sin dato va en blanco, no con raya**, y con alto propio (6mm) para escribir encima.
- **El encabezado lleva sólo el logo**: el nombre de la empresa ocupaba una zona entera y el logo
  ya lo dice (queda en el `aria-label`). ⚠ Aseguramiento definió las tres zonas del encabezado
  (M251) con logo + nombre: este cambio lo pidió Sebastián el 21-ago y conviene que Miguel lo
  valide contra el formato oficial.
- **La pantalla previa es UNA lista con buscador**, no tarjetas por sala. "Marcar todos" marca lo
  que se está viendo, y lo seleccionado fuera de la búsqueda se declara en la cuenta.
- **Desde la hoja se vuelve al selector** sin cerrar la pestaña.
- Medido con el `@media print` simulado: **97 × 77,5 mm** sobre una etiqueta de 100×100.
- **El ÁREA volvió como campo que se ELIGE** (21-ago), no derivada: un desplegable con las salas
  reales, pre-cargado con la que venga de Registrar Producción, y en blanco si nadie la elige.
  No contradice el retiro de "Sala / área" del 20-ago: aquélla la afirmaba el sistema y podía
  nombrar una sala donde el equipo ya no está; ésta la decide quien imprime.
