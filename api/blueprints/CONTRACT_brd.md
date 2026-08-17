# CONTRACT · `brd.py` (Batch Record Digital)

> **Para agentes IA · LEER ANTES de modificar este blueprint.**
> Este blueprint contiene los datos regulatorios más críticos del sistema
> (records de fabricación INVIMA / GMP). Cualquier cambio que rompa
> inmutabilidad o trazabilidad es BLOQUEANTE.

Última revisión: 2026-05-12

---

## Contexto

`brd.py` reemplaza progresivamente a **MYBATCH** (sistema externo de batch
records que HHA usaba). Implementa Part 11 §11.10(e), §11.50, §11.70,
§11.100(b), §11.200 + buenas prácticas GMP.

Capas:
1. **MBR** (Master Batch Record) · procedimiento aprobado por QA.
2. **EBR** (Executed Batch Record) · ejecución de UN lote real.
3. **IPCs** · in-process controls con specs y bloqueo OOS.
4. **Cleaning log** · limpieza de equipos con validación QC visual.
5. **Pesajes** · reconciliación granular MP teórico vs real.
6. **PDF maestro** · legajo auditable descargable.

---

## Tablas que ESCRIBE

| Tabla | Operación | Cuándo |
|---|---|---|
| `mbr_templates` | INSERT/UPDATE | crear draft, editar, transición de estado |
| `mbr_pasos` | INSERT/UPDATE/DELETE | gestión pasos del MBR (solo en draft) |
| `ipc_specs` | INSERT/DELETE | gestión specs IPC (solo en draft) |
| `ebr_ejecuciones` | INSERT/UPDATE | iniciar EBR, completar, liberar/rechazar |
| `ebr_pasos_ejecutados` | INSERT/UPDATE | clonar al iniciar EBR, ejecutar paso |
| `ipc_resultados` | INSERT | reportar medición IPC |
| `ebr_pesajes` | INSERT | reportar pesaje granular MP |
| `equipo_limpieza_log` | INSERT/UPDATE | ciclo limpieza operario+QC |
| `e_signatures` | (LEE solamente) | valida signature_id de aprobaciones |
| `audit_log` | INSERT | cada operación crítica |

## Tablas que LEE

- `mbr_templates`, `mbr_pasos`, `ipc_specs`, `ebr_*`, `ipc_resultados`,
  `ebr_pesajes`, `equipo_limpieza_log`, `e_signatures`,
  `usuarios_identidad` (para identity snapshot en firmas),
  `formula_items` (para cálculo de teóricos en reconciliación).

---

## Invariantes CRÍTICAS · NO romper

### INV-1 · MBR aprobado es INMUTABLE
Migración 109 trigger `trg_mbr_aprobado_no_edit` bloquea UPDATE de
`titulo`, `descripcion`, `lote_size_g`, `formula_version_id` cuando
`estado='aprobado'`. `mbr_pasos` también inmutable post-aprobación
(triggers `trg_mbr_pasos_no_*_aprobado`). Si necesitás cambiar algo
APROBADO, el flujo es: `obsoletar` la versión actual + `crear` nueva
con `version+1`.

### INV-2 · IPC specs siguen el estado del MBR
Migración 112 trigger `trg_ipcspec_no_*_aprobado`. Igual razón que INV-1.

### INV-3 · EBR liberado/rechazado es INMUTABLE
Migración 111 trigger `trg_ebr_liberado_no_edit` bloquea UPDATE de
`cantidad_real_g`, `yield_pct`, `liberado_signature_id`, `notas`,
`estado` cuando `estado IN ('liberado','rechazado')`. Pasos, IPCs y
pesajes asociados también inmutables (triggers correspondientes).

### INV-4 · Aprobación/liberación REQUIERE e-signature válida
- `POST /api/brd/mbr/<id>/aprobar` valida signature_id contra
  `e_signatures WHERE meaning='aprueba' AND record_table='mbr_templates'
  AND record_id=mbr_id AND signer_username=user`.
- `POST /api/brd/ebr/<id>/liberar` análogo con `meaning='libera'`.
- `POST /api/brd/ebr/<id>/rechazar` análogo con `meaning='rechaza'`.
- Sin firma válida → 400 (no 401 — el user está autenticado pero no firmó).

### INV-5 · Pasos críticos del EBR REQUIEREN e-sign
Si `mbr_pasos.requiere_e_sign=1`, el endpoint
`POST /api/brd/ebr/<id>/pasos/<orden>/completar` exige `signature_id`
con `meaning='ejecuta'` y `record_table='ebr_pasos_ejecutados'`. Si
`requiere_qc=1`, también `qc_signature_id` con `meaning='supervisa'`.

### INV-6 · IPCs obligatorios bloquean completar EBR
`POST /api/brd/ebr/<id>/completar` rechaza con 409 si:
- Hay `ipc_specs WHERE obligatorio=1` sin resultado en `ipc_resultados`.
- Hay `ipc_resultados WHERE conforme=0 AND spec.obligatorio=1`.

GMP: out-of-spec debe abrir desviación antes de continuar. Hoy bloqueamos
completar; el siguiente release puede agregar workflow desviación-link.

### INV-7 · Cantidad teórica se calcula SERVER-SIDE
`POST /api/brd/ebr/<id>/pesajes` NO acepta `cantidad_teorica_g` del
cliente. Se calcula como `formula_items.porcentaje × cantidad_objetivo_g`.
Esto evita que el operario manipule el teórico para ocultar deltas
fuera de spec.

### INV-8 · Cleaning log validado por QC es INMUTABLE
Migración 113 trigger `trg_limpieza_no_edit_qc`: una vez `qc_e_sign_id`
está set, no se puede cambiar `visual_ok`, `qc_e_sign_id`,
`completado_at_utc`, ni `equipo_codigo`. Errores se documentan abriendo
nuevo log.

### INV-9 · audit_log captura todas las transiciones de estado
Cada cambio de estado en MBR/EBR/cleaning genera audit. Las descargas
de PDF EBR también (acción `DOWNLOAD_EBR_PDF`).

### INV-10 · PDF EBR contiene SHA-256 estable del CONTENIDO
El hash del footer NO es el hash del PDF (eso cambia con timestamp gen).
Es hash de campos estables del EBR (id, lote, cantidad, signature_id,
counts). Permite verificar que el PDF se generó desde un EBR específico
no alterado.

### INV-11 · Transiciones de estado del EBR van con CAS (no check-then-act)
`completar`/`liberar`/`rechazar` llevan la condición de estado en el WHERE
del UPDATE (`WHERE id=? AND estado IN (...)`) + `if rowcount==0 → rollback
+ 409 ESTADO_CAMBIO`. Sin CAS, con 3 workers un liberar y un rechazar
concurrentes dejaban el EBR 'rechazado' con el PT ya promovido a VIGENTE
(producto rechazado vendible). Regla M27.

---

## Endpoints downstream que CONSUMEN sus datos

| Endpoint externo | Lee | Si rompo `brd.py`... |
|---|---|---|
| `programacion.py` (futuro) | `ebr_ejecuciones.produccion_id` | ...producciones planificadas pierden ref a su EBR |
| `inventario.py` (futuro) | `ebr_pesajes.lote_mp` | ...trazabilidad lote MP → producto terminado se rompe |
| `aseguramiento.py` (futuro) | desviaciones podrían linkear ipc_resultados | ...desviaciones huérfanas |
| Calidad UI | `/api/brd/ebr?estado=en_revision_qc` | ...QC no ve los pendientes a liberar |
| INVIMA auditor (manual) | descarga PDF EBR | ...evidencia regulatoria no se entrega |

---

## Endpoints que expone

### MBR
- `GET    /api/brd/mbr` · listar (filtros producto, estado)
- `GET    /api/brd/mbr/<id>` · detalle con pasos
- `POST   /api/brd/mbr` · crear draft
- `PATCH  /api/brd/mbr/<id>` · editar header (solo draft)
- `POST   /api/brd/mbr/<id>/pasos` · agregar paso
- `PATCH  /api/brd/mbr/<id>/pasos/<paso_id>` · editar paso
- `DELETE /api/brd/mbr/<id>/pasos/<paso_id>` · borrar paso
- `POST   /api/brd/mbr/<id>/submit` · draft → en_revision
- `POST   /api/brd/mbr/<id>/aprobar` · requiere signature_id
- `POST   /api/brd/mbr/<id>/obsoletar` · aprobado → obsoleto + motivo

### IPC specs (parte del MBR)
- `GET    /api/brd/mbr/<id>/ipc-specs`
- `POST   /api/brd/mbr/<id>/ipc-specs` · solo draft
- `DELETE /api/brd/mbr/<id>/ipc-specs/<spec_id>` · solo draft

### EBR
- `GET    /api/brd/ebr` · listar (filtros estado, lote)
- `GET    /api/brd/ebr/<id>` · detalle con pasos
- `POST   /api/brd/ebr` · iniciar (clona **solo los pasos de la fase** del MBR aprobado · Batch B). `lote` es UNIQUE: para el mismo lote físico en varias fases, usar sufijo (·-OF/-OA) y `asignar-lote-fisico` para el lote real.
- `POST   /api/brd/ebr/<id>/pasos/<orden>/iniciar`
- `POST   /api/brd/ebr/<id>/pasos/<orden>/completar` · valida e-sign
- `POST   /api/brd/ebr/<id>/completar` · valida IPCs (bloquea conforme=0 **o NULL** obligatorio) + calcula yield
- `POST   /api/brd/ebr/<id>/asignar-lote-fisico` · reemplaza el lote provisional `PP<id>` por el lote físico real (propaga a `movimientos` Entrada). Solo antes de liberar. (audit 3-jun)
- `POST   /api/brd/ebr/<id>/liberar` · QC firma `meaning='libera'`. Gates: desviación abierta, **IPC OOS sin desviación resuelta (fail-closed, por ebr_id)**, y en `EBR_MODE=strict` exige pesajes verificados + conciliación.
- `POST   /api/brd/ebr/<id>/rechazar` · QC firma `meaning='rechaza'` + motivo

### IPC resultados (parte del EBR)
- `GET  /api/brd/ebr/<id>/ipc-resultados`
- `POST /api/brd/ebr/<id>/ipc-resultados` · operario reporta medición · OOS abre desviación auto

### Estaciones MyBatch en el runner (reemplazo completo)
- `GET/POST /api/brd/ebr/<id>/despeje` · despeje de línea (checklist CUMPLE · MyBatch ②) · mig 215
- `GET/POST /api/brd/ebr/<id>/precauciones` · precauciones + equipos (MyBatch ①) · mig 216
- `GET/POST /api/brd/ebr/<id>/registros-fisicos` + `GET .../<rid>/pdf` · adjuntar PDF/referencia (MyBatch ⑦) · mig 217
- `GET/POST /api/brd/ebr/<id>/conciliacion-material` · conciliación envase/empaque (mig 210)
- `GET/POST /api/brd/ebr/<id>/artes` + `/artes/<id>/aprobar` · artes/codificación (mig 211)
- `GET/POST /api/brd/ebr/<id>/observaciones` · bitácora (mig 213)
- `POST /api/brd/ebr/<id>/pesajes/<pid>/verificar` · 2ª firma de pesaje (mig 208)

### Pesajes (reconciliación granular)
- `GET  /api/brd/ebr/<id>/pesajes` · listado
- `POST /api/brd/ebr/<id>/pesajes` · operario reporta pesaje
- `GET  /api/brd/ebr/<id>/reconciliacion` · ok / outliers / no_pesados

### Cleaning log
- `GET  /api/brd/cleaning?equipo=X` · listado
- `GET  /api/brd/cleaning/equipo/<X>/ultima` · última + apto_para_uso
- `POST /api/brd/cleaning` · operario inicia limpieza
- `POST /api/brd/cleaning/<id>/completar` · operario marca fin
- `POST /api/brd/cleaning/<id>/validar` · QC firma visual_ok

### PDF maestro
- `GET /api/brd/ebr/<id>/pdf` · descarga legajo completo (audit_log captura)

---

## Permisos

| Acción | Roles permitidos |
|---|---|
| Crear/editar MBR draft | cualquier user logueado |
| Submit MBR a revisión | creador o ADMIN_USERS |
| Aprobar/obsoletar MBR | ADMIN_USERS o CALIDAD_USERS |
| Iniciar EBR | cualquier user logueado |
| Ejecutar pasos EBR | cualquier user logueado (paso requiere e-sign del propio user) |
| Liberar/rechazar EBR | ADMIN_USERS o CALIDAD_USERS |
| QC validar cleaning | ADMIN_USERS o CALIDAD_USERS |

---

## Cambios recientes

### 2026-05-12 · Fase 1 BRD completa (F1-F8 sin C2)
- Migraciones 109-114.
- Blueprint nuevo `brd.py` (~1.700 LoC).
- 7 golden paths nuevos (GP-55 a GP-60 + reconciliación).
- F2 lock post-aprobación con triggers en producciones/OC postergado
  (necesita análisis caso por caso de workflows existentes).

### Pendiente para próxima iteración
- UI dashboard `/brd` (listados read-only mínimos hechos en otra commit).
- Desviación auto-link cuando IPC sale fuera spec.
- Importar más fórmulas reales como MBR draft (hoy solo Blush Balm).
- Hookear `produccion_programada.iniciar` para crear EBR auto.
- Pack CSV (URS / IQ / OQ / PQ) cuando se vaya a auditoría INVIMA.

### 2026-05-30 · Reemplazo MyBatch fase 1 · EBR automático al aceptar producción
- Helper nuevo `crear_ebr_desde_mbr(cur, *, producto_nombre, lote, produccion_id,
  cantidad_objetivo_g, usuario, notas)`: crea (o reusa, idempotente por
  produccion_id) un EBR desde el MBR APROBADO más reciente del producto, clona
  sus pasos. NO commitea ni audita (lo hace el caller). Devuelve
  {ok, id, numero_op, pasos} o {ok:False, error:'NO_MBR_APROBADO'|'LOTE_DUPLICADO'}.
- `programacion.planta_aceptar_produccion` lo invoca según `config.EBR_MODE`:
  - 'off' (default): no crea EBR (sin cambios).
  - 'warn': crea EBR si hay MBR aprobado; si falta, deja aceptar con aviso en log.
  - 'strict': BLOQUEA aceptar (409 SIN_MBR_APROBADO) si el producto no tiene MBR
    aprobado · BPM. El chequeo es ANTES de mutar.
  - lote del EBR provisional = 'PP<produccion_id>'; el lote físico real se
    enlazará al completar (refinamiento fase futura). Modelo: 1 EBR por
    produccion_programada.
- Activar 'strict' SOLO cuando todos los MBR estén cargados/aprobados (sino frena
  planta). Cubierto por golden GP-62 test_golden_ebr_auto_al_aceptar_produccion.

### 2026-06-10 · Módulo OA (Órdenes de Acondicionamiento) + llave EBR por fase
- **`crear_ebr_desde_mbr` ahora sufija la llave `lote` por fase** (fabricación=''/
  envasado='-OF'/acondicionamiento='-OA') y guarda el lote FÍSICO real en
  `lote_codigo`. Idempotencia y dedup van por `(COALESCE(lote_codigo,lote), fase)`,
  NO por `lote` crudo (que es UNIQUE en BD). Resuelve colisión del UNIQUE con
  contador. Efecto: el MISMO lote físico tiene OP+OF+OA conviviendo (órdenes
  distintas, como MyBatch). Arregla bug latente: el legajo de Envasado solo nacía
  cuando el lote no chocaba con fabricación. **Toda lectura del lote para mostrar/
  cruzar usa `COALESCE(lote_codigo, lote)`** (vista-completa, ordenes-unificadas,
  JOIN con envasado/acondicionamiento). `POST /api/brd/ebr` (iniciar_ebr) NO sufija
  (el caller pasa el lote ya sufijado).
- Hook nuevo: `POST /api/acondicionamiento` (inventario.py) crea EBR
  `fase='acondicionamiento'` auto si hay MBR aprobado (audit `CREAR_EBR_OA_AUTO`,
  no bloquea · espeja el hook de envasado).
- `vista-completa`: rama `acondicionamiento` → `acond_presentaciones` (unidades/
  presentación del lote) + `acond_materiales` (empaque desde `mee_consumido`).
- Páginas nuevas (HTML server-side, aisladas de producción · espejan Envasado):
  - `GET /planta/legajo-acondicionamiento/<id>` · la "Orden de Acondicionamiento".
  - `GET /planta/instrucciones-acondicionamiento/<id>` · ejecución 7 secciones.
  - `/planta/orden/<id>` redirige fase acond → legajo-acondicionamiento.
- `ordenes-unificadas?fase=acondicionamiento` agrega filas simples desde la tabla
  `acondicionamiento` (OA sin legajo aún).
- Golden: test_acondicionamiento_legajo (nuevo · OP/OF/OA conviven, legajo carga,
  idempotencia). test_golden_envasado_hook_crea_legajo_of adaptado a
  COALESCE(lote_codigo,lote). Suite golden 247/247 verde.

### 2026-07-26 · `ordenes-unificadas` enriquece las órdenes CON legajo (solo lectura)

Sebastián, mirando la lista de Envasado: *"¿es premium? ¿qué hay para mejorar acá?"*. La lista
decía QUÉ órdenes hay (n°, producto, lote, estado) pero nunca CÓMO van, así que para saber si una
orden iba a la mitad, cuántos frascos salían o hacía cuántos días estaba parada había que abrir
los legajos uno por uno.

Cada orden con `ebr_id` ahora trae, además de lo anterior:
`pasos_total` · `pasos_hechos` · `avance_pct` (de `ebr_pasos_ejecutados`),
`presentaciones` [{etiqueta, volumen_ml, unidades}] y `unidades_total` (de
`ebr_envasado_unidades`, solo envasado/acondicionamiento), y `dias` (edad, anclada a Colombia).
El `resumen` suma `abiertas`, `atrasadas` (abiertas con 3 días o más) y `unidades_total`.

**INVARIANTE · se calcula con consultas AGREGADAS, nunca una por fila.** Son 2 queries con
`IN (...)` + `GROUP BY` para toda la lista. Si alguien mueve esto a un endpoint por orden, la
vista vuelve a ser N+1 fetch desde una lista, que es exactamente lo que satura los 3 workers y
deja la pantalla en "Cargando" (M43/M59/M86). Lo protege
`tests/test_envasado_lista_premium.py::test_la_lista_sigue_siendo_UNA_sola_consulta_por_pantalla`.

Sigue siendo **solo lectura**: no escribe nada. El resto de campos no cambió (los consumidores
existentes no se tocan).

### 2026-05-30 · Fase 2 · IPC fuera de spec → desviación/CAPA automática (mig 203)
- `reportar_ipc_resultado`: si conforme=0, abre desviación automática vía
  `aseguramiento.crear_desviacion_auto` (tipo proceso, lotes_afectados=lote EBR,
  descripción con parámetro+valor+rango) y enlaza en `ipc_resultados.desviacion_id`
  (mig 203). Devuelve {desviacion:{codigo,id}}. Deploy-safe.
- `liberar_ebr`: GATE nuevo · 409 DESVIACION_ABIERTA si existe una desviación con
  el lote del EBR en lotes_afectados y estado NOT IN ('cerrada','anulada'). El
  lote no se libera hasta resolver la desviación (clasificar→investigar→CAPA→cerrar).
- Golden GP-64. La desviación sigue su workflow normal en /aseguramiento.

## Despeje de línea · supervisión por ALERTA (Sebastián 7-jul · v2)
- Modelo v2: el operario VA HACIENDO sin trabarse (NO hay gate bloqueante); cada ítem
  que marca dispara un `push_notif_multi` a Calidad (campana) para que esté AL LADO
  verificando. La firma dual sigue garantizada por el gate de `liberar_ebr` (no se
  libera sin despeje conforme + verificado). Se quitó "Marcar TODO" (riesgo de
  diligenciar sin mirar) → el operario marca uno por uno, pero sin esperar.
- v3 (7-jul): UNA sola alerta (no por-ítem · evita fatiga de campana). `iniciar_ebr` manda
  la alerta IMPORTANTE (sonido) a `_qc_verificadores()`; `registrar_despeje_item_ebr` YA NO
  notifica (los pendientes se ven en la bandeja "Mi trabajo").
- MÉTRICA de respuesta de Calidad (en `ebr_vista_completa`/`out`): `despeje_respuesta_min` =
  MIN(verificado_at_utc de despeje) − iniciado_at_utc (aviso → 1ª verificación); mientras no
  haya verificación, `despeje_espera_min` = ahora − iniciado_at_utc. Se muestra como badge en
  la sección Dispensación del legajo. Sin columnas nuevas (todo derivado).
- `_qc_verificadores()` = (CALIDAD_USERS ∪ ASEGURAMIENTO_USERS ∪ TECNICA_USERS) − ADMIN
  = {laura, yuliel, miguel, hernando}. Best-effort (nunca rompe el registro/inicio).
- `verificar_despeje_item_ebr` (`/despeje-verificar` POST): path masivo `{todos:true}`
  DESHABILITADO (409 `VERIFICAR_UNO_A_UNO`) — Calidad verifica una por una.
- `_batch_role_info.verifica` ahora incluye `aseguramiento` → Miguel verifica igual que
  Calidad (Laura/Yuliel) y Director Técnico (Hernando), SIN cambiar el acceso a los
  módulos de cada rol (separación de cargos intacta).

## 📕 El instructivo aprobado tiene que LLEGAR al legajo (26-jul)

Sebastián había cargado el procedimiento real (fases, °C, hidratación, pH) en 27 de los 30 MBR
aprobados y el operario seguía viendo 3 pasos genéricos de relleno. El instructivo existía; no
llegaba al piso. Tres causas independientes:

1. **`crear_ebr_desde_mbr` resolvía el MBR por nombre EXACTO** (case-sensitive). La fórmula dice
   `BLUSH BALM` y el MBR está guardado `Blush Balm`; igual `SUERO EXFOLIANTE NOVA PHA` vs
   `Suero Exfoliante Nova PHA` → `NO_MBR_APROBADO` → la orden nacía sin legajo y caía a "registro
   simple". Ahora `UPPER(TRIM(...))` a ambos lados (M2) + `ORDER BY version DESC, id DESC` (sin el
   desempate por id, dos MBR de la misma versión salen en orden no determinista en PG). **El gate
   de EBR_MODE=strict en `programacion.py` usa el MISMO criterio** — si resolviera distinto,
   bloquearía una producción cuyo MBR sí existe.
2. **Los legajos ABIERTOS quedan colgados de la versión vieja** cuando se aprueba una nueva (la
   anterior pasa a `obsoleto`). Herramienta: `GET /api/brd/mbr-desactualizados` (preview) +
   `POST /api/brd/revincular-mbr` (`aplicar:true`). Reglas duras: nunca toca un legajo
   liberado/rechazado/completado (mig 111); **nunca toca un legajo que ya ejecutó un paso** (eso
   es una desviación que decide Calidad, no un ajuste automático); sólo reemplaza pasos en estado
   `pendiente`, así que **una firma no se puede borrar**; CAS sobre `mbr_template_id` para que dos
   clicks concurrentes no clonen los pasos dos veces; audit `REVINCULAR_MBR_EBR` antes del commit.
3. **El paso de dispensación NO puede llevar un peso absoluto congelado.** El texto se escribe una
   vez y sirve para lotes de cualquier tamaño: un lote de 10 kg mostraba
   `Dispensar AGUA · 77,79 g` mientras la hoja de pesaje decía **7.779 g** — 100× de diferencia,
   los dos números en el MISMO legajo (M5). Encima salía de `cantidad_g_por_lote`, columna
   DERIVADA que puede quedar stale (M71) y relativa a la base de la FÓRMULA, no al lote. Ahora el
   paso expresa el **porcentaje** y remite a la hoja de pesaje, que lo calcula desde la cantidad
   real (M67).

⚠ `mbr_pasos` de un MBR aprobado es INMUTABLE por trigger (UPDATE/DELETE/INSERT). Corregir el
texto de un MBR ya aprobado exige obsoletar + versión nueva, nunca un UPDATE.

Tests: `tests/test_mbr_instructivo_llega_al_piso.py`, `tests/test_revincular_mbr.py` (en el gate).

## 🧩 El instructivo se carga POR FASE (26-jul)

Sebastián: *"tenemos envasado de emulsiones, limpiadores, sueros…"* → hace falta instructivo de
**envasado** y de **acondicionamiento** por producto, no sólo el de fabricación.

`POST /api/brd/mbr/cargar-instructivo` acepta `fase` (`fabricacion` default · `envasado` ·
`acondicionamiento`), validada contra `_FASES_VALIDAS`. Dos bugs que tenía y **los dos eran
silenciosos** — habrían hecho que el operario leyera los pasos equivocados sin un solo error:

1. escribía **siempre** `fase='fabricacion'` hardcodeado → un instructivo de envasado entraba como
   pasos de MEZCLA y corrompía la receta del producto;
2. al reemplazar en un borrador borraba **TODOS** los pasos del MBR → cargar envasado **borraba**
   el instructivo de fabricación del mismo borrador.

Ahora: borra/reemplaza **sólo la fase que se carga** (comparando con `_fase_canonica`, porque la
fase se guarda con etiquetas distintas según quién la escribió), el `orden` arranca después de lo
que ya hay para no chocar entre fases, y **al versionar un MBR aprobado la v+1 copia las fases que
NO se cargaron** — si no, aprobar el instructivo de envasado dejaría al producto sin instructivo de
mezcla. Tests: `tests/test_instructivo_por_fase.py` (en el gate · verificados 3 corridas en PG).

⚠ Los pasos genéricos de envasado (5) y acondicionamiento (3) que siembra
`_generar_mbr_desde_formula` son iguales para TODO producto. Sirven de esqueleto; el instructivo
real por producto (o por familia) entra por este endpoint.

---

## INV-12 · La ORDEN se aprueba antes de arrancar (mig 393)

Sebastián (28-jul, describiendo MyBatch): *"tanto fabricación, envasado como acondicionamiento,
todas inician con una ORDEN; esa orden se le entrega al operario, y después empieza el proceso"*.

El legajo ya guardaba quién lo **inició**, quién lo **liberó** y el visto bueno final del Director
Técnico (mig 286) — pero no quién **autorizó que empezara**. En MyBatch esa firma es propia de la
orden (`approved/<pk>`), y en acondicionamiento son dos (`approved` de producción y
`approved_quality` de calidad), lo que coincide con la OA-2026-102 real: *"Supervisado por: Jefe de
producción"* **y** *"Aprobado por: Laura González, Jefe de calidad"*.

- `POST /api/brd/ebr/<id>/aprobar-orden` · e-firma `meaning='aprueba_orden'` validada contra
  `e_signatures` (este legajo, este usuario), CAS sobre `aprobada_orden_por` (no se aprueba dos
  veces), `audit_log`. Guarda además el **rol** con el que se firmó: sin eso, en acondicionamiento
  las dos firmas serían indistinguibles.
- El gate vive **dentro de `_require_brd_ejecutor`** (default-deny), no pegado endpoint por
  endpoint: así todo endpoint de ejecución —incluidos los que se escriban después— lo hereda sin
  que nadie se acuerde (M45). Lo que se enumera es lo **exento**: `_APROBACION_ORDEN_EXENTOS`,
  que es la aprobación misma más lo que **documenta o corrige** (bitácora, correcciones, registros
  físicos, precauciones, conciliación de granel, visto bueno del DT). Un registro regulado no se
  puede quedar sin anotar por un permiso administrativo.
- **Toggle `app_settings.exigir_aprobacion_orden`, default `0`** → NO-OP TOTAL (M68: un beta que
  igual bloquea en un caso es una traba fantasma esperando a aparecer). Se enciende desde
  `/admin/seguridad-planta`, con efecto inmediato y auditado.
- La banda de estado se pinta en las **tres** páginas de orden desde una sola copia del JS
  (`_JS_APROBACION_ORDEN`, inyectado con assert): tres copias divergen y la de acondicionamiento
  sería la que quede vieja.

⚠ **`aprueba_dt` faltaba en `firmas.VALID_MEANINGS` desde que se creó (mig 286, 25-jun).** La
pantalla firmaba con ese meaning y `/api/sign` devolvía 400 → **el visto bueno del Director Técnico
nunca se pudo dar desde la UI**. El backend que lo valida estaba bien; el hueco vivía en la
whitelist del firmador. Fijado en `test_aprobacion_orden.py`.

Tests: `tests/test_aprobacion_orden.py` (en el gate).

## INV-13 · Conciliación del granel en el envasado (mig 392)

    granel disponible (mL) = envasado (Σ unidades × mL) + remanente + diferencia sin explicar

Es la pregunta que hace una auditoría INVIMA y que el legajo no contestaba: en la **OF-2026-77**
entraron 12.658,95 mL y se envasaron 100 unidades de 10 mL = 1.000 mL; los otros **11.658,95 mL**
no los explicaba ningún registro. Puede ser perfectamente legítimo (queda granel para otra orden),
pero eso hay que **escribirlo**.

- Resolver canónico único: `_conciliacion_granel(conn, ebr_id, header=None)` (M1). Lo consumen la
  vista (`vista-completa` → `conciliacion_granel`) y el PDF; no hay una segunda cuenta que pueda
  divergir de la que se muestra (M5).
- **Todo se DERIVA salvo el remanente** (M71): lo único que hay que ir a medir. Se captura en
  **gramos**, que es como se pesa en piso, y los mL salen de `densidad_g_ml` — igual que el granel
  de entrada. Sin densidad **no se inventa la conversión**: se declara `falta_densidad` (M109).
- `cuadra` sólo puede ser `True` con la cuenta **completa** (remanente declarado, densidad, y
  ninguna presentación sin volumen). Sin remanente, un 0 de diferencia sería casualidad, no
  conciliación.
- `POST /api/brd/ebr/<id>/remanente-granel` · destino contra whitelist (`_REMANENTE_DESTINOS`; el
  texto libre va en observaciones, que es donde no rompe una agrupación · M115), rechaza la
  contradicción "no quedó remanente" + peso > 0, CAS contra liberado/rechazado, `audit_log` con la
  diferencia declarada.
- **Va en el PDF** (sección 4c-bis). Un bloque que sólo vive en la pantalla no es un registro: el
  legajo que se archiva es el que ve la auditoría.
- Tolerancia en `app_settings.conciliacion_granel_tolerancia_pct` (default 2%), porque el %
  razonable depende del producto — no es una constante de dominio.

Tests: `tests/test_conciliacion_granel.py` (en el gate).

## INV-14 · Material de envase: recibir y VERIFICAR son dos firmas (mig 394)

En MyBatch son dos pasos separados (`material_received` y `material_verified`) y esa separación
**es** el control: quien cuenta lo que llegó no puede ser el mismo que certifica que está bien.
La mig 391 trajo `recibida`/`recibido_por`; faltaba el paso siguiente.

- `POST /api/brd/ebr/<id>/material-envase/<row_id>/verificar` · espeja `despeje-verificar`
  (mig 285): sólo quien VERIFICA por rol (`_batch_role_info(...)['verifica']` = Calidad /
  Aseguramiento / Jefe de Producción / Director Técnico), nunca sobre la propia recepción, nunca
  sobre lo que todavía no llegó, CAS + `audit_log`. Los lotes `DEMO-` se pueden caminar con una
  sola persona, igual que el despeje.
- **La firma cubre LOS DATOS QUE SE FIRMARON.** Editar `material_codigo`, `lote_material` o
  `recibida` **anula** la verificación (hay que rehacerla); ajustar la conciliación posterior
  (`devuelta`/`utilizada`/`averiada`) NO la toca. Dejarla en pie tras cambiar la cantidad sería
  una firma sobre otro dato — falsear un registro Part 11.
- Va en la pantalla (columnas *Cant. recibida · Recibido por · Verificado por*) y en el PDF
  (4c-ter), con el faltante de ENTREGA a la vista: lo que no mandaron y la merma son cosas
  distintas y sin esa resta el reclamo al proveedor se pierde dentro de "utilizada".

⚠ **Hueco que se cerró en el mismo commit:** `recibida`/`recibido_por` se guardaban desde el
28-jul pero `_materiales_envase_manuales` NO los consultaba y la tabla del legajo no tenía esas
columnas → la sección 3 quedaba a medias en pantalla con el dato ya en la base (M115). Y el
`except: pass` que envolvía la suma de esas filas escondía cualquier error de la consulta: la
fila desaparecía sin un solo mensaje, indistinguible de "no hay material cargado" (M4/M94).

Tests: `tests/test_material_envase_verificado.py` (en el gate).

## INV-15 · La ORDEN es un objeto propio y el vínculo es ADITIVO (mig 395)

Decisión de Sebastián (29-jul): *"sí, desde los nuevos"*. Una orden agrupa **N lotes**
(`add_batch/<pk>` de MyBatch), se aprueba **una vez para todos** y su número es lo que se
imprime y se le entrega al operario.

- `ordenes_produccion` (numero UNIQUE, fase, producto, lote_bulk, cantidad_g, densidad) +
  `ebr_ejecuciones.orden_id` **NULEABLE**. Esa nulabilidad ES el diseño: los legajos anteriores
  se quedan sin orden madre y **siguen funcionando exactamente igual**. No se migra ni un
  registro firmado — colgar retroactivamente un legajo ya ejecutado de una orden inventada sería
  fabricar historia en un registro regulado.
- Numeración `OP-`/`OF-`/`OA-` con `siguiente_correlativo` + **retry por el UNIQUE** (jamás
  `CAST(SUBSTR(...))`, que revienta en PG con cualquier sufijo · M45/M96).
- **`cantidad_ml` se DERIVA** de `cantidad_g / densidad_g_ml` y no se guarda (M71). Sin densidad
  queda en `None` y la pantalla muestra un punto, no un cero que miente.
- **Acondicionamiento lleva DOS aprobaciones** (producción + calidad), como la OA-2026-102 real.
  La orden pasa a `aprobada` **sólo con todas sus firmas**: con una sola todavía no autoriza a
  arrancar. Un único resolver `_aprobar_orden_generico` para las dos (M1) — separadas, la de
  calidad sería la que quede vieja.
- **El gate de arranque acepta la firma del legajo O la de su orden madre.** Si mirara sólo el
  legajo, aprobar el encabezado no serviría de nada y habría que firmar lote por lote.
- `adicionar-lote` **delega en `crear_ebr_desde_mbr`** (M3) y sólo le pone el `orden_id`; el lote
  nuevo **hereda** la aprobación de la orden. ⚠ El contrato de ese helper devuelve `{'ok','id'}`
  — la llave es `id`, **no** `ebr_id`: indexarlo mal crearía el legajo y devolvería error (M94).

Pantallas: `/planta/ordenes-batch` (listado + crear) y **`/planta/orden-batch/<orden_id>`**
(encabezado, las dos firmas, lotes y "Adicionar lote"). Tests: `tests/test_orden_produccion.py`
(en el gate).

⚠ **La orden madre y el legajo de un lote son DOS unidades de trabajo y cada una tiene su URL.**
Hasta el 17-ago-2026 el detalle de la orden vivía en `/planta/orden/<orden_id>`, la misma URL que
el legajo de un lote (`orden_detalle_page`, declarada antes en el archivo). Werkzeug se queda con
la primera, así que **la pantalla de la orden madre estaba muerta** -- y el listado "Todas las
órdenes" mandaba el id de la ORDEN a una pantalla que lo lee como id de LEGAJO: abría el lote
ajeno cuyo id coincidía, con cara de correcto (M200/M161). El test que la cubría pasaba por la
razón equivocada (verificaba que el id apareciera en el HTML, y la otra pantalla también lo
interpola · M152). No lleva redirect desde la URL vieja: esa pantalla nunca se sirvió ahí, y la
URL sigue siendo del legajo, que es quien la venía usando. `test_preflight_brd_visible.py` falla
si dos pantallas del batch record vuelven a compartir URL.

**Toda pantalla del batch record tiene que tener por dónde llegar** (M121). Encender
`brd_visible` sin eso revela pantallas que nadie puede abrir: pasó con `/planta/ordenes-produccion`
(el listado estilo MyBatch, sin un solo enlace desde junio · hoy sale del bloque de legajos del
dashboard) y con `/planta/bandeja-dt` (lo que espera la firma del Director Técnico · hoy sale de
`/tecnica`, con sus otras herramientas). El guard recorre lo que el navegador CARGA -- incluidos
`/planta-core.js` y `/planta-app.js`, donde viven los enlaces que arma el JS (M166) -- y **nunca
mira la propia pantalla**: una página que sólo se enlaza a sí misma sigue siendo inalcanzable.
Las que se abren tecleando la URL se ENUMERAN con su motivo.

## INV-16 · El kardex sabe lo que pasa ADENTRO del lote (mig 396)

Hasta el 29-jul la MP salía por FEFO al arrancar y ahí se acababa la conversación: lo que
sobraba, lo que se agregaba y lo que volvía **no movía un solo movimiento**. Entre producción
y producción el stock era una estimación.

- **`ebr_ajustes_mp` ya existía y sólo dejaba una NOTA.** La MP que el operario agrega para
  corregir pH quedaba escrita en el legajo y **nunca salía del stock**: el sistema creía que
  seguía ahí. No era una función faltante, era un **agujero de inventario silencioso** —
  invisible porque el legajo se ve completo. Ahora descuenta por `_distribuir_fefo` (M1/M3: no
  se reimplementa el descuento), guarda `material_id` / `lote` / `mov_id` y audita.
  ⚠ **Sin `material_id` NO descuenta y lo declara** (`descontado: false`): el nombre es texto
  libre y descontar por nombre parecido es descontar la molécula equivocada (M19).
- **`POST /devolucion-mp`** · lo que sobra vuelve al kardex como **Entrada**, y **conserva el
  vencimiento del lote**: si se pierde, el material devuelto queda sin fecha, el cron de
  vencidos y el FEFO dejan de verlo y vuelve a producción vencido (M25). Tiene test propio.
- **Conteo cíclico OPCIONAL** (Sebastián: *"sin ser obligatorio"*): si el operario declara el
  físico total del lote, se reporta `discrepancia_g = físico − (kardex + devuelto)`. Si no lo
  declara **no se infiere nada** — un conteo inventado es peor que no contar (M109).
- **El granel real viaja solo de fabricación a envasado.** `_conciliacion_granel` cae al legajo
  de FABRICACIÓN del mismo lote físico (`lote_codigo` · M10) cuando el de envasado no trae su
  propio `ml_envasable`, y expone `origen_granel`. De ahí derivan `unidades_teoricas` y el
  rendimiento. **Es un fallback, no una sobreescritura**: si el envasado tiene su dato, manda.
  ⚠ Con **varias presentaciones NO se calcula un teórico por presentación**: repartir el granel
  exige un criterio que nadie definió (M8). Se da el rendimiento en volumen, que sí vale.

Tests: `tests/test_kardex_ciclo_lote.py` (en el gate).

## INV-17 · Los controles en proceso ESTÁNDAR son controles de verdad (mig 397)

El roadmap lo tenía anotado como un detalle de pantalla (*"muestra 'pendiente' con ✓ a la vez"*).
Al medirlo contra el código el hueco era estructural: **los dos gates de IPC miraban sólo
`ipc_specs` / `ipc_resultados`**, y como **ningún MBR define specs**, todo pasa por la vía
ESTÁNDAR (`ipc_estandar_resultados`) — que no tenía ningún control encima. Reproducido antes de
tocar nada: un lote con el pH marcado **No cumple** salió `{"estado":"liberado","ok":true}`.

Las cinco piezas, y por qué son la misma:

1. **`conforme=1/0` exige resultado.** Adjudicar sin dato dejaba la fila diciendo "pendiente" y
   "✓" a la vez (M5), y una conformidad firmada sobre un dato que no existe no es un registro. Se
   corta en el ORIGEN (400 `IPC_ESTANDAR_SIN_RESULTADO`), no en la vista: arreglar sólo la
   pantalla deja la base igual de rota (M115). `no_aplica` (conforme=2) **sí** es una respuesta
   completa en sí misma y no exige valor.
2. **Un NO CONFORME abre desviación, fail-closed**, por el helper canónico
   `crear_desviacion_auto` (M1/M3: no se reimplementa). El mismo hecho físico por las dos vías
   tiene que dejar el mismo rastro; si sólo lo abre el camino del MBR, el gate de liberación —que
   mira desviaciones— no ve nada. Si la desviación no se puede abrir, **el resultado no se
   guarda** (un OOS sin trazabilidad es peor que un error). Re-registrar el mismo control
   **reusa** su desviación abierta: corregir un tipeo no puede abrir una segunda del mismo hecho.
3. **`liberar_ebr` tiene el gate directo por `ebr_id`**, espejo del de `ipc_resultados`:
   `conforme=0` sólo pasa con su desviación cerrada y CAPA efectivo (409
   `IPC_ESTANDAR_NO_CONFORME`), y un valor anotado que **nadie adjudicó** tampoco (409
   `IPC_ESTANDAR_SIN_ADJUDICAR` · es la firma de Calidad que falta, igual que el cualitativo del
   MBR). Es directo *a propósito*: el gate por desviación depende de que `lotes_afectados`
   matchee el lote como texto libre — hay un test que rompe ese cruce para probar que el directo
   queda en pie. Lo que **no** bloquea acá es un control sin registrar (fila ausente): eso lo
   gobierna el toggle, o sería el estricto encendido por la puerta de atrás (M68).
4. **`completar_ebr` puede exigir los 5**, detrás de `app_settings.exigir_ipc_estandar` **default
   `0` → NO-OP TOTAL** (M68). Hoy casi ningún lote los registra: encenderlo a ciegas traba el piso
   el mismo día. Se prende desde `/admin/seguridad-planta` (efecto inmediato, auditado). El
   bloqueo por NO CONFORMIDAD **no** depende del toggle: nadie marca "No cumple" por accidente.
5. **Van en el PDF (sección 4-bis).** La sección 4 imprime sólo los IPC del MBR, así que el
   legajo archivado —el que lee la auditoría— salía **sin un solo control en proceso** aunque en
   pantalla estuvieran registrados. Es INV-13 otra vez: un bloque que sólo vive en la pantalla no
   es un registro. De paso, el `_q` del PDF dejó de tragar en silencio: si una sección se cae por
   un error de consulta, el documento se veía completo y no lo era (M4/M94).

⚠ **Decisión abierta (de Sebastián, no técnica):** hoy `POST /ipc-estandar` lo puede usar
cualquier ejecutor de BRD, así que el mismo operario que mide puede declarar "Cumple". En MyBatch
la sección 5 la firma **Calidad**, y la UI ya sólo le muestra el botón a quien verifica — el
backend es el que no lo exige. Separarlo es un cambio de quién puede trabajar, así que no se
tocó por cuenta propia.

Tests: `tests/test_ipc_estandar_gate.py` (en el gate · 13 casos, con los dos lados del trinquete).


## INV-18 · El que REGISTRA no puede APROBAR el control en proceso (mig 400)

Sebastián (29-jul): *"sí, pues eso debemos hacerlo, el que registra no puede aprobar"*. En MyBatch
la sección 5 la firma **Calidad**; acá cualquier ejecutor del batch podía anotar el valor Y
declarar "Cumple" sobre su propia medición.

- **Dos actos separados**: anotar el valor lo hace quien mide; **adjudicar** (Cumple / No cumple /
  No aplica) es de quien VERIFICA por rol (403 `SOLO_CALIDAD_ADJUDICA`), y **nunca sobre su propia
  medición** (409 `AUTOADJUDICACION_BLOQUEADA`). Espeja la 2ª firma del material de envase
  (INV-14), incluida la exención de los lotes `DEMO-`.
- **Hacía falta la migración**: el upsert pisaba `medido_por` con quien adjudicaba, así que sin
  `adjudicado_por` no quedaba constancia de quién midió — la regla no se podía ni auditar. Ahora
  la fila guarda a los dos.
- El gate de liberación ya bloqueaba "valor anotado sin adjudicar" (`IPC_ESTANDAR_SIN_ADJUDICAR`),
  que es justo el estado normal entre la medición y la firma de Calidad.

### ⚠ Y el hueco de 3 capas que esto destapó (M121)
`_batch_role_info` le da a **Aseguramiento (Miguel)** y a **Dirección Técnica (Hernando)**
`verifica`, `corrige`, `puede_liberar` y al DT `aprueba_dt` desde el 7-jul. Pero
`_require_brd_ejecutor` —la puerta de **36 endpoints**— sólo admitía `PLANTA ∪ CALIDAD ∪ ADMIN`:
ninguno de los dos estaba. **Todo lo construido para ellos era inalcanzable**: la 2ª firma del
despeje (mig 285), la del material de envase (mig 394) y el visto bueno del DT (mig 286), que
M116 ya había encontrado roto por el meaning faltante — se arregló el meaning y seguía sin
funcionar, porque el bloqueo estaba una capa más arriba. El gate ahora incluye
`ASEGURAMIENTO_USERS | TECNICA_USERS`; `realiza=False` los mantiene fuera de ejecutar pasos de
producción, y hay un test que verifica que **compras sigue afuera** (ampliar un permiso sin probar
el borde es cambiar un control por una puerta abierta).

Tests: `tests/test_ipc_estandar_sod.py` (en el gate · 9 casos).


## 📦 INV-19 · El envase sale UNA vez del kardex · un solo libro mayor (5-ago)

Había **dos cierres** que descontaban el mismo empaque, desde la misma fuente, cada uno con su
propio candado, y ninguno miraba el del otro:

| cierre | de dónde saca los códigos | qué marca |
|---|---|---|
| `POST /api/brd/ebr/<id>/cerrar-envasado` (OF) | `producto_presentaciones` | `ebr_ejecuciones.envases_descontados_at` |
| cierre de acondicionamiento del Kanban (OA) | `produccion_checklist` | `produccion_checklist.consumido_at` |

Y el checklist **se pre-llena desde `producto_presentaciones`** (`programacion.py:21371`), o sea
exactamente los mismos códigos. Cada CAS impedía que SU camino repitiera; en el flujo normal
(envasar → acondicionar) los dos corren sobre el mismo lote físico, así que **el frasco, la tapa y
la caja salían DOS VECES**: el kardex mostraba menos envases de los que hay en el estante y
abastecimiento los volvía a pedir.

**La regla: un hecho, un libro mayor.** `produccion_checklist.consumido_at` es el registro de
*"este envase, para esta producción, ya salió"*, y los DOS caminos lo leen y lo escriben. El cierre
de envasado:
1. **salta** lo que el checklist ya marcó (`_ya_consumido`) — descontarlo otra vez es inventar un
   consumo que no ocurrió;
2. **reclama con CAS** lo que sí descuenta (`WHERE id=? AND COALESCE(consumido_at,'')=''` +
   `rowcount`), ANTES de tocar el kardex. Con 3 workers, leer-y-después-marcar deja pasar los dos
   (M27/M73).

No se agregó un tercer candado: el problema era justamente que había dos candados distintos para el
mismo hecho. Sin `produccion_id` no hay libro que consultar (legajo suelto): descuenta como antes
pero lo **DECLARA** (`sin_libro_mayor` en la respuesta y en el audit) — un descuento que no se pudo
coordinar no se puede presentar como coordinado (M124).



Tests: `tests/test_doble_descuento_envase.py` (en el gate · incluye el recorrido de los DOS cierres
contando el kardex).


## 📦 INV-20 · El frasco que volvió SERIGRAFIADO es el que se consume (5-ago)

Catalina (4-ago) lo reportó como *"descuenta doble"*. Cuando un envase se manda a marcar, su
**Salida YA se registró al enviarlo** y vuelve como OTRO código. `cerrar-envasado` descontaba el
BASE otra vez — porque `producto_presentaciones` sigue apuntando a él — así que el base salía dos
veces y el **serigrafiado, que es el que de verdad se pone en la línea, no se consumía nunca**: su
stock sólo crecía. Es la causa (a) de M147, que estaba arreglada en `_descontar_mee_envasado`… una
función **sin llamador vivo**: el arreglo existía y no corría (M121).

La redirección **no adivina**: la orden guarda `produccion_id` + `base_codigo` +
`serigrafiado_codigo`, así que *"este base, para ESTA producción, volvió como aquel"* es un hecho
REGISTRADO (M19). Reglas:
- Sólo si la orden está **`liberado`**. Mientras está afuera — o volvió y sigue en cuarentena — ese
  envase no está para usarse y el stock canónico no lo cuenta (M153).
- Sólo de **esta** `produccion_id`. Emparejar por código a secas convertiría el hecho registrado en
  una coincidencia de nombres.
- Sólo el **frasco**: a serigrafía no va la tapa ni la caja, y redirigirlas sería adivinar.
- La redirección se **DECLARA** (`redirigidos_a_serigrafiado` en el audit): un descuento que cambió
  de código sin decirlo es indistinguible de un error de carga.

Tests: `tests/test_serigrafiado_se_consume.py` (en el gate · 7 casos, incluidos los tres que NO
deben redirigir).


## 📦 INV-21 · Los DOS cierres mueven KARDEX y CACHE juntos, y validan el código (5-ago)

`cerrar-envasado` y `cerrar-acondicionamiento` insertaban la Salida con un `INSERT INTO
movimientos_mee` a mano y **no tocaban `maestro_mee.stock_actual`** (M45: el patrón vivía en los
dos). El cache quedaba alto después de cada cierre y sólo lo realineaba el cron de las 3 AM; entre
medias, todo lo que clampea contra ese cache trabajaba inflado. Tampoco validaban que el código
existiera, así que uno mal escrito entraba como stock fantasma que nadie puede reponer (M100) — y
en acondicionamiento los códigos los **teclea el operario** en el body.

Ahora los dos: **validan** que el código esté en `maestro_mee` (si no, va a `saltados` y NO frena
el cierre), registran la Salida en el kardex y mueven el cache con el **mismo delta**.

**⚠ Por qué NO se usa `aplicar_movimiento_mee`, que sería lo obvio.** Ese helper **clampea la
Salida contra `maestro_mee.stock_actual`**, y M26 dice que el stock canónico es la SUMA DEL KARDEX,
no el cache. Se intentó y el gate lo cazó: con el cache en 0 y stock real en el kardex — que es como
siembra a propósito el fixture de `test_envase_partes_se_descuentan`, con el comentario *"stock real
por kardex (canónico · M26), no por el cache"* — la Salida se registraba en **CERO**. El envase se
usaba y el kardex seguía diciendo que estaba en bodega: peor que el doble descuento, y ya había
pasado una vez (M153).

Con el delta directo: en el caso sano (cache == kardex) queda exacto y sin drift; si el cache venía
mal, el kardex igual dice la verdad y el cron lo realinea. El cache se clampea a 0 (nunca negativo)
con `CASE WHEN`, no con `MAX(a,b)`, que es escalar en SQLite y agregada en PG (M51).

Tests: `tests/test_salida_envasado_canonica.py` (en el gate · el guard cubre los DOS cierres y fue
el que encontró el hermano de acondicionamiento).

---

## INV-14 · Las verificaciones GMP son CONFIGURABLES, pero la clave de un ítem es inmutable

**Desde el 15-ago-2026** el director técnico configura los ítems del despeje de línea y los
controles en proceso de cada fase (`/aseguramiento/checklists` → `POST /api/brd/checklists`),
igual que en MyBatch. Antes eran constantes del código y cambiar un ítem exigía un despliegue.

Reglas duras, todas cubiertas por `tests/test_checklists_configurables.py` (en el gate):

- **`checklist_items` nace VACÍA.** Sin filas para un ámbito, mandan las constantes
  (`DESPEJE_LINEA_ITEMS`, `IPC_ESTANDAR*`). La tabla es la personalización, no la fuente: sin
  configurar, el sistema se comporta exactamente como antes (aditivo · M117).
- **UN solo resolvedor por familia.** `despeje_checklist()` y `_ipc_estandar_de_fase(fase, conn)`
  leen la configuración y caen a la lista de fábrica. Todo consumidor pasa la conexión: sin ella
  el resolvedor responde la de fábrica, y una pantalla que pide controles distintos a los del
  legajo se contradice con él (M161 · pasó con la cola de Calidad).
- **La identidad de un ítem es su CLAVE, no su posición.** Para el despeje la clave es el
  `item_idx`; **nunca se recicla** — el siguiente libre se calcula contando también los retirados
  y los que alguna vez se firmaron en `ebr_despeje_items`. El orden de visualización es una
  columna aparte, así que reordenar la pantalla no le cambia el significado a nada firmado.
- **El texto de lo ya firmado NO cambia** (Part 11): la vista muestra el `item_texto` guardado con
  cada registro, no el que hoy ocupe esa posición.
- **Retirar no borra.** El ítem queda `activo=0`: deja de pedirse y sigue apareciendo, marcado
  como histórico, en los lotes donde se registró.
- **Una lista vacía se rechaza** (400 `CHECKLIST_VACIO`): dejar un legajo sin verificaciones no es
  relajar un control, es borrarlo, y se ve igual que uno bien configurado.
- **Quien ejecuta el procedimiento no lo define**: configurar es del director técnico,
  Aseguramiento o admin (403 `SIN_PERMISO_CHECKLIST` al resto). Cada cambio va a `audit_log` con
  el antes y el después completos.

---

## INV-19 · Quién firma cada acto del batch record (16-ago-2026)

Corregido contra el **sistema documental de la empresa** (Drive), a pedido de Sebastián:
*"el director técnico solo libera el producto terminado"* · *"todas las verificaciones las pueden
hacer analista y jefe de control de calidad"* · *"aquí solo debería ser jefe y calidad"*.

| Acto | Quién | Fuente documental |
|---|---|---|
| Registrar / ejecutar el paso | Operario, Jefe de Producción | `COC-PRO-010` §3.5 y §3.3 |
| **Verificar** (2ª firma: despeje, pesaje, control en proceso) | **Analista y Jefe de Control de Calidad** + Aseguramiento | `COC-PRO-010` §3.4 y §3.2 · `PRD-INS-001-004` ("diligenciamiento EXCLUSIVO de Control de Calidad") |
| Aprobar el proceso (fabricación, envasado) | Producción **+** Calidad | `PRD-PRO-001-F01` ("RESPONSABLES DEL PROCESO") |
| **Liberar el producto terminado** + visto bueno | **Director Técnico** | acta de revisión con Hernando Acevedo, 27-jul-2026 · `PRD-PRO-001-F01` ("VBO DIRECCIÓN TÉCNICA") |

La frase que ordena todo la dijo el propio Director Técnico en esa acta: **"la liberación es una
responsabilidad del director técnico, mientras que el envasado requiere aprobación en lugar de
liberación"**. Fabricación y envasado se **aprueban**; el producto terminado se **libera**. Son dos
actos regulatorios distintos y la pantalla usa cada palabra donde corresponde.

**Reglas duras:**

- **`_batch_role_info` es el ÚNICO resolvedor de rol del batch record** (M1/M3). Antes había un
  segundo mapa escrito a mano en `ebr_vista_completa` y divergía en silencio: publicaba
  `puede_verificar` mientras la pantalla de envasado lee `d.mi_rol.verifica` — una llave que ese
  dict nunca tuvo, así que **el botón de verificar el material de envase (INV-14) no aparecía
  nunca, para nadie**. Cualquier vista nueva pide el rol a ese helper; nunca arma el suyo.
- **Quien REALIZA no da su propia 2ª firma.** El Jefe de Producción ejecuta el despeje y firma
  como ejecutor; Control de Calidad lo verifica *"de forma independiente al Jefe de Producción"*
  (`PRD-PRO-001` §4). Por eso está en `realiza` y NO en `verifica`.
- **El Director Técnico conserva `aprueba_dt`.** Su firma no se quita: se mueve al lugar que el
  formato le da. En *Cierre y Aprobaciones* su bloque aparece sólo en la fase de
  **acondicionamiento** (producto terminado) — o si ya firmó, porque una firma registrada de un
  documento regulado nunca se esconde.
- **Lo que no se muestra se explica.** En fabricación y envasado la sección dice que esa etapa se
  aprueba entre Producción y Calidad y que el visto bueno del DT va al liberar el producto
  terminado: una tarjeta que desaparece sin decir por qué se lee como un faltante.
- **A quién se le avisa = quién puede firmar.** `_qc_verificadores` (la campana de verificación) y
  `verifica` salen del mismo conjunto: un aviso que lleva a algo que no se puede hacer enseña a
  ignorar todos los demás.

Fijado por `tests/test_quien_firma_el_cierre.py` (en el gate), con la prueba de dientes hecha en
las dos direcciones.

**RESUELTO (Sebastián, 16-ago: *"entonces por etapa"*):** los instructivos marcaban
`requiere_qc=1` en **todos** sus pasos, y ese flag **bloquea el registro del paso** (400) hasta
que otra persona firme `supervisa` — con ~20 pasos por lote, 20 firmas de Calidad por lote. El
procedimiento no pide eso: pide las verificaciones **por etapa**. Ahora el default es
`_REQUIERE_QC_INSTRUCTIVO = 0` (una constante con el porqué al lado) y la **mig 438** bajó los que
ya estaban cargados, con dos guards duros: **no toca MBR aprobados** (inmutables · mig 109, y son
documentos firmados: ahí hay que re-versionar) y **no toca ningún paso ya ejecutado con la firma
dada** (bajarle la exigencia a un registro firmado sería reescribir su historia). Sigue siendo
editable paso por paso desde el MBR, así que volver a exigirlo en un paso crítico es un clic.

**Lo que se firma por etapa, y sigue intacto — son cinco actos, no veinte:** el despeje (con la
verificación independiente de CC), los controles en proceso (sólo Calidad adjudica · INV-18), los
pesajes, el material de envase (INV-14) y la liberación.

**El camino de la FIRMA tiene que decir lo mismo que el de la ACCIÓN.** `firmar-rapido` no aceptaba
el meaning `aprueba_dt` (el mismo defecto que M116 encontró en `/api/sign`, en el otro endpoint) y
su gate era `ADMIN ∪ CALIDAD` mientras el mensaje prometía *"Calidad / Dirección Técnica"*: el
Director Técnico **no podía firmar ni la liberación** que `/liberar` sí le permite, y Aseguramiento
tampoco. Los dos gates salen ahora de `_batch_role_info`.

**Y el legajo de acondicionamiento ofrece el visto bueno del DT**, que es la pantalla del producto
terminado: el endpoint existía desde junio y esa pantalla no lo tenía (la única vía era el modal
del dashboard), porque `/vista-completa` ni siquiera mandaba `aprobado_dt_por`.

⚠ **Hueco preexistente, todavía abierto:** `/api/sign` con `meaning='supervisa'` **no gatea rol** —
cualquiera con login puede dar esa 2ª firma (el único control es que no sea el mismo operario que
ejecutó). Con la verificación ahora por etapa pesa menos, pero sigue ahí.

---

## INV-20 · La firma está atada a SU registro · y el maestro de lotes (17-ago-2026)

**Una firma no es genérica: pertenece a la tabla y la fila que firma.** `firmar-rapido` emite
SIEMPRE una firma sobre `ebr_ejecuciones` (record_id = el legajo). Sirve para los actos del
legajo -liberar, aprobar la orden, el visto bueno del DT- y **no sirve para un sub-registro**:
`aprobar_arte_codificacion` valida contra `record_table='ebr_artes_codificacion'`, así que una
firma rápida se rechaza. Un botón que la use se ve perfecto y la aprobación lo niega, que es la
peor forma de negar un permiso (M219, tercera aparición).

- Acto del LEGAJO → `POST /api/brd/ebr/<id>/firmar-rapido` + la acción.
- Acto de un SUB-REGISTRO (arte, paso, pesaje) → `POST /api/sign/challenge` + `POST /api/sign`
  con `record_table` y `record_id` del sub-registro, y después la acción.

**Antes de reusar un firmador, leé sobre qué tabla firma.** Guard:
`tests/test_aprobar_etiqueta_acondicionamiento.py` (además exige que el bloque exista EN la
pantalla de acondicionamiento, que es donde MyBatch pone *"Aprobar Etiqueta"* · antes sólo se
llegaba por el modal del dashboard · M121).

### Maestro de lotes · vive en `/calidad/maestro-lotes`, y hay UNO solo

⚠ El 17-ago construí un segundo maestro de lotes en `/aseguramiento/maestro-lotes` sin ver que
ya existía uno desde el 15-ago en `/calidad/maestro-lotes` -- y más completo: trae las tres
fases del lote con su rendimiento, los clientes, el material de envase y **declara de dónde saca
la teórica**. Lo busqué preguntándole a EOS por `/api/brd/maestro-lotes`, una URL que inventé
yo, vi el 404 y lo di por faltante (M170/M220).

**Dos pantallas con el mismo nombre no son dos vistas: son dos verdades que divergen**, y quien
las mira no tiene forma de saber cuál creer (M99/M161). El duplicado se retiró; su ruta quedó
**redirigiendo** porque llegó a estar enlazada desde Dirección Técnica (M120).

Invariante: **una sola pantalla sirve un maestro de lotes**. El guard recorre el `url_map` REAL
y ABRE cada ruta que lo mencione -- no lee el fuente, porque la primera versión encontró el
`redirect` del login dentro de la pantalla buena y reportó cero (M170).

Guard: `tests/test_maestro_de_lotes.py` (probado con dientes sirviendo una segunda pantalla).
