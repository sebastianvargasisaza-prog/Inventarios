# ROADMAP · EOS

> **Único roadmap.** Antes había cinco (`ROADMAP_ZERO_ERROR`, `ROADMAP_SAAS_2026`,
> `ROADMAP_ARQUITECTURA_RELEASE`, `ROADMAP_MOVIL_NATIVO`, `COMPRAS_ROADMAP`) y ninguno sabía del
> otro, así que había que abrir los cinco para saber qué faltaba — y varios daban por pendiente
> algo que ya estaba hecho. Los originales quedan en `archive/roadmaps/` como historia.
>
> Última verificación contra el código real: **26-jul-2026**.
> Lo que dice "hecho" acá se comprobó ejecutando o leyendo el código, no de memoria.

## Cómo se lee

| Marca | Significa |
|---|---|
| 🔴 | Toca producto que se vende, dinero o registro INVIMA. Va primero. |
| 🟡 | Deuda que muerde pronto. |
| 🟢 | Mejora. No urgente. |
| 💭 | Decisión de negocio de Sebastián, no trabajo técnico. |

---

## 🔴 Abierto · riesgo real

### Instructivos de fabricación
- ~~`SUERO HIDRATANTE AH 1.5%` sin instructivo~~ **CARGADO 26-jul.** Su PDF exportado (formato
  viejo de abril) traía sólo las 2 páginas de pesajes; Sebastián lo encontró en MyBatch. Queda
  **pendiente que Calidad apruebe la v2 con e-firma** para que entre en vigor.
- Ya están los 28 de 28 productos con fórmula activa (test que lo vigila:
  `tests/test_instructivos_completos.py`).
- Los MBR **no tienen IPCs definidos**, así que el legajo cae a los controles estándar. Cargar
  specs por producto en `/brd` sigue pendiente (es dato de Calidad, no código).
  ⚠ Lo que sí era código está **cerrado el 29-jul** (mig 397 · INV-17): el "pendiente con ✓ a la
  vez" era la punta de un hueco estructural — los dos gates de IPC miraban sólo las specs del MBR,
  así que la vía estándar (la que se usa) no tenía control: un pH marcado *No cumple* no abría
  desviación, **no frenaba la liberación** (reproducido: el lote salió `liberado`) y el PDF
  archivado no imprimía ni un control. Ahora bloquea, abre desviación y va al legajo.

### Producción sin batch record
- ~~35 de 56 órdenes sin legajo~~ **No es un hueco** (Sebastián 26-jul): esas 35 son de **antes**
  de que existiera el batch record, que se está construyendo ahora. Es historia previa.
- Sí queda **1 orden EN PROCESO sin legajo y sin lote**: `PROD-03764` (ESENCIA ILUMINADORA, 30-jun).

### Datos del kardex que INVIMA va a pedir
- **21 lotes sin fecha de vencimiento** (12 en cuarentena → se completa al liberar; **9 vigentes**
  urgen, el mayor Silicona BM 956 con 19.387 g) · **62 sin ubicación** (47 en cuarentena, 15
  vigentes) · **30 MPs sin INCI** pero sólo **1 con stock**.
  Se listan en `/api/admin/auditoria-lotes` con el estado de cada lote (26-jul).
  ⚠ Los números que estaban acá antes (11/17/3) salieron de una consulta parcial y eran míos, mal.
- 30 duplicados y 65 lotes nuevos que destapó `/api/admin/auditoria-lotes` cuando se arregló
  (llevaba tiempo devolviendo "0 duplicados" porque dos queries reventaban en PostgreSQL).

### Fórmulas con datos raros (todas INACTIVAS hoy, pero conviene limpiarlas)
- `CREMA FACIAL UREA 10%` con **0 ingredientes** (duplicado vacío de `CREMA FACIAL UREA 10`).
- `Suero RETINAL +` con **base 100 g** cuando todas las demás están en miles.
- `EMULSION HIDRATANTE  B3+BHA` con doble espacio en el nombre.

---

## 🟡 Abierto · deuda que muerde

### Release y operación
- ~~Quitar el disco persistente de Render~~ **YA ESTÁ HECHO** (verificado 26-jul: no hay bloque
  `disk:` en `render.yaml` y los COA viven en R2 desde el 24-jul). Este punto lo arrastré del
  roadmap viejo sin verificarlo — era mi error, no un pendiente.
- `--preload` en gunicorn (ojo: los daemons arrancan en el import → con `--preload` correrían en
  el master, verificar antes).
- Watchdog en `_loop_multi_cron`: hoy un job colgado en I/O bloquea los 78 crons y el supervisor
  no lo recupera (`is_alive()` sigue en True).
- Branch protection en GitHub para que el CI sea bloqueante.

### Diseño · lo que queda tras la migración a tokens del 26-jul
Contexto: se migraron **9.685 declaraciones de color a tokens `--cx-*`** en 58 archivos y se
separaron los pares relleno/texto (`--cx-primary` vs `--cx-primary-text`), porque el tema oscuro
estaba a medio construir. Medido en el navegador, **antes** ninguna vista de Planta respetaba el
tema oscuro; **ahora** sí, con esto pendiente:
- **18,2% del texto del dashboard sigue bajo 3:1 en tema oscuro** (163 de 895 elementos medidos).
  Dos fuentes, ambas identificadas:
  1. **Capas de variables propias de cada página** (`--gm-ac:#6d28d9`, `--line`, `--mut`, `--txt`…
     · 124 declaraciones). No las migré a propósito: una variable propia puede usarse como texto
     Y como fondo, así que mapearla a ciegas es peor que dejarla. Hay que revisar caso por caso
     cuál es (el nombre ayuda: `--bg`/`--line`/`--mut` son claros, `--c`/`--v`/`--gm-ac` no).
  2. **Colores asignados a una variable de JS** (`bg='#dbeafe'`, `col='#1e40af'`): **1.774**, de los
     cuales 874 en `dashboard_html.py`. El migrador no los vio porque su regex pide `propiedad:#hex`
     y una asignación no lo es. **No se pueden barrer a ciegas**: la mayoría termina dentro de un
     `style="..."` (y ahí el token funciona) pero otros van a un gráfico de canvas o a una
     comparación, donde el literal hace falta. Hay que ir por función, viendo dónde aterriza el
     valor. Los chips de estado de Fabricación ya se migraron así (uno por uno, verificando).
  3. **Cola larga de colores sin token** (`#1e63a8`, `#a21caf`, `#c0392b`, `#0f766e`…). O se les
     asigna un token del sistema, o se agrega el token que falte a `cortex.css`.
- **NO borrar en bloque los 201 `display:none`.** Estaba en mi plan y es un error: M86 ya advierte
  que las pestañas se ocultan con `display:none` **sin quitar el nodo**, porque `goTab` mapea por
  ÍNDICE del `.tab` en el DOM y borrar un nodo desalinea el resaltado. Hay que ir uno por uno
  distinguiendo "pantalla vieja escondida" (se borra) de "pestaña oculta a propósito" (se queda).
- Las 3 vistas del día (Fabricación · Envasado · Acondicionamiento) siguen pendientes de rediseño
  (fila de KPIs, chips de estado, avance 3/5, desglose de presentaciones visible en la fila, edad
  en días con color, operario/área). Va junto con la construcción de fabricación.
- Vigilado por `tests/test_deuda_diseno_no_crece.py` (en el gate): si el número sube, falla.

### Arquitectura
- Sacar el HTML/JS de los strings de Python. `dashboard_html.py` tiene **1,9 MB**; cada edición
  ahí exige node-check manual del valor evaluado. Es el cambio de mayor impacto en mantenibilidad.
- Partir los mega-archivos (`admin.py` 1,7 MB · `plan.py` 1,4 MB · `programacion.py` 1,2 MB).
- Linter + formato + tipos incrementales.

### Motor
- **Unificar los dos motores de demanda.** La pantalla de Abastecimiento usa
  `abastecimiento_consumo_horizontes` (verificado) y "Generar OC" usa
  `_compute_mp_deficit_aggregated` (el viejo). Se vienen alineando fix por fix desde junio; el
  arreglo de fondo es que generar-OC consuma el motor verificado.
- **Paridad compra ↔ descuento de envases**: la compra reparte multi-presentación 15/30 ml y el
  checklist descuenta todo a la dominante; y el motor de compra no reserva `cantidad_fija_uds`.
  Alcance mapeado el 18-jul, es rediseño money-critical, necesita test de paridad.
- IA síncrona en endpoints de acción: falta el helper con lock "1 IA en vuelo" y el job en
  background. Dos de los peores (`autoplan-ia`, `ocr-factura`) están deshabilitados.

### Higiene de permisos
- **432 rutas mutan y sólo piden estar logueado** (ver `MAPA_PERMISOS.md`). No todas son un
  problema, pero ahí es donde aparecen los agujeros: el 25-jul se encontraron dos controles que
  parecían control y no lo eran. Revisar las que tocan dinero, inventario o registros regulados.

---

## 🟢 Abierto · mejoras

- Móvil: la PWA ya funciona. El siguiente escalón real es TWA (Android) + Capacitor (iOS),
  2-4 semanas. **Reescribir en React Native está descartado** (6-9 meses, sobre-ingeniería).
- Auditar responsive en los módulos que aún no lo son.
- Push notifications nativas · splash screens · ícono profesional.
- 11 tablas que **nadie lee ni escribe** (ver `MAPA_ESQUEMA.md`): o son histórico a propósito o
  son features muertas.
- 33 tablas con **4+ módulos que las escriben** — ahí nace el drift; cada una debería tener un
  dueño y que el resto delegue.

---

## 💭 Decisión de negocio (no es trabajo técnico)

- **Factura electrónica DIAN** vía PSP: hay que elegir proveedor y firmar
  (FacturaTech desde ~$90K/mes · Carvajal ~$200K · The Factory HKA ~$180K · Siigo ya exporta).
- **SaaS multi-tenant**: vender EOS a otros laboratorios. Requiere refactor multi-tenant (3-4
  meses) + billing. Planes esbozados: Starter $290K / Pro $590K / Enterprise $1.290K COP mes.
- **Validación CSV / GAMP 5 por un tercero**: INVIMA la va a exigir para el sistema computarizado.

---

## ✅ Cerrado y verificado (para no volver a levantarlo)

Verificado contra el código el 26-jul, no de memoria:

- **audit_log en las mutaciones críticas** — el roadmap zero-error de mayo listaba 6 huecos.
  Cinco ya estaban cerrados (`pagar_oc`, `autorizar_oc`, `cont_factura_anular`,
  `cont_factura_pago`, `prog_completar_evento`) y `compliance.py` audita en 6 sitios. El sexto
  (`_auto_asignar_operarios`) se cerró el 26-jul.
- **Helper de auditoría centralizado** — existe en `api/audit_helpers.py`.
- **Paridad PostgreSQL en CI** — el job `test-postgres` corre en cada push y el harness auto-sana
  el esquema (crea tablas y columnas que falten). `bash scripts/guardian.sh --pg` local.
- **Bugs B1/B2 de compras** (OC automática vacía, form sin `nombre_mp`) — cerrados en el sprint
  de Compras junto con 55+ bugs y 194 tests.
- **Las 18 rutas `/diag/*` abiertas a internet** — cerradas con `before_request` a ADMIN (25-jul).
- **`/api/formulas` servía las recetas a cualquier usuario logueado** — cerrado (26-jul).
- **Mapa de permisos y mapa de esquema** — generados, no escritos a mano:
  `python scripts/generar_mapa_permisos.py` y `scripts/generar_mapa_esquema.py`.
