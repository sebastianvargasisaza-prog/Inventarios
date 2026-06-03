# 🏭 Integración MyBatch → EOS · Mapa maestro

> **Objetivo:** reemplazar MyBatch (Electronic Batch Record externo) integrando su funcionalidad
> **dentro del tab Producción de EOS**, que ya tiene las 4 pestañas necesarias.
> Fiel a cero-error: un solo motor probado, reutilizando lo que ya existe.
> Fecha: 2026-06-02 · En construcción colaborativa (tour de pantallas MyBatch).

---

## 0. Hallazgo arquitectónico clave ⭐

MyBatch usa **el MISMO esqueleto de EBR** para OP (fabricación), OF (envasado) y OA (acondicionamiento).
Solo cambia el **contenido de los pasos** y el **tipo de material**. Por tanto:

> **EOS necesita UN solo motor de EBR, parametrizado por FASE (`tipo`), no tres módulos.**

```
EBR (1 motor) · estaciones compartidas:
  ① Precauciones + Equipos
  ② Despeje de línea (checklist CUMPLE)
  ③ Recepción/Dispensado de material (teórico vs real, lote, recibió)
  ④ Pasos de proceso  →  Realizó por + VERIFICÓ por (2ª firma) + Resultado
  ⑤ Controles en proceso (IPC)  →  valor + CUMPLE/NO
  ⑥ Observaciones generales
  ⑦ Registros físicos (adjuntar PDF)
  →  Gate de liberación: no libera hasta estaciones obligatorias ✓
  →  Cada estación gateada por ROL (segregación de funciones GMP)

FASE = FABRICACIÓN (OP) | ENVASADO (OF) | ACONDICIONAMIENTO (OA)
```

Cada estación es un **botón de acción** que abre un **modal de captura mínimo** (dato + observación + guardar/firmar).
Lo que se ve "Aprobado" es el resultado lleno; durante la ejecución cada estación va `pendiente → registrado → verificado`.

---

## 1. Las 4 pestañas de EOS YA existen (`bar-prodHub`)

| Pestaña EOS (ya existe) | = MyBatch | Contenido a integrar |
|---|---|---|
| 🧪 **Fórmulas** | Instrucción de Manufactura (plantilla) | MBR: pasos + IPC por fase · **Paso 1 HECHO** |
| 🏭 **Fabricación** | **OP** · Órdenes Producción | Lista + Registrar + **Abrir EBR (fase fabricación)** |
| 📦 **Envasado** | **OF** · Órdenes Envasado | Lista + crear (de OP / +Bulk) + **Abrir EBR (fase envasado)** |
| 🔧 **Acondicionamiento** | **OA** · Órdenes Acondicionamiento | Lista + **Abrir EBR (fase acondicionamiento)** ⏳ por mapear |

→ **No se crean pestañas nuevas.** El motor EBR se invoca con un botón "▶ Abrir EBR" en cada producción.

---

## 2. Mapa MyBatch → EOS (módulo por módulo)

### MANUFACTURA

| MyBatch | EOS destino | Estado mapeo |
|---|---|---|
| **PP** · Programa Producción | Producción → Programación / Calendario | ✅ ya existe |
| **OP** · lista (orden, producto, lote bulk, cant. teórica/producida/aprobada, estado) | 🏭 Fabricación → Historial | ✅ ~80% (falta N° OP formateado, lote bulk vs PT, cant. aprobada) |
| **OP** · crear (+Nuevo: producto, lote, cant, fechas, **área/línea**, **uso premezcla**) | "Registrar Producción" | ✅ + área/línea y premezcla pendientes |
| **OP** · interior = **EBR fabricación** (10 secciones) | 🏭 Fabricación → "Abrir EBR" | ⚠️ ~75% (ver huecos §4) |
| **OF** · lista | 📦 Envasado → lista | ✅ mapeado |
| **OF** · crear (+Nuevo = elige OP y hereda cant.; +Bulk = granel sin OP) | 📦 Envasado | ⚠️ falta "mL disponibles post-fabricación" (puente OP→OF) |
| **OF** · interior (presentaciones+unidades, %rend, conciliación empaque) | 📦 Envasado → "Abrir EBR" | ✅ mapeado · 3 huecos |
| **OA** · lista (orden, producto, estado, elaborado) | 🔧 Acondicionamiento → lista | ✅ mapeado |
| **OA** · interior (presentaciones+unid empacadas, materiales empaque, **Aprobación Artes/Codificación**, Aprobar Etiqueta) | 🔧 Acondicionamiento → "Abrir EBR" (fase acond.) | ✅ mapeado · gate etiquetado nuevo |
| **PM** · Premezclas (columnas idénticas a OP; tabla VACÍA) | 🏭 Fabricación con output = producto intermedio | ✅ mapeado · = OP-para-intermedio · **sin uso hoy → prioridad mínima** |

### ASEGURAMIENTO (Calidad) — EOS YA LO SUPERA ✅

> **Sorpresa del mapa:** el stack de Calidad de EOS es **más completo que MyBatch**.
> Reemplazar MyBatch **NO** requiere construir Calidad — ya existe y excede.

| Función Calidad | EOS (blueprint) | Estado |
|---|---|---|
| Liberación de lote (doble firma) | `brd.py` gate + `firmas.py` (e-firma Part 11) | ✅ |
| Desviaciones (clasificar/investigar/CAPA/cerrar) | `aseguramiento.py` | ✅ |
| Control de cambios (+ notificar INVIMA) | `aseguramiento.py` / `tecnica.py` | ✅ |
| Quejas / PQR | `aseguramiento.py` | ✅ |
| Recalls (notificar INVIMA/distribuidores) | `aseguramiento.py` | ✅ |
| No conformidades · CAPA · auditorías | `calidad.py` / `compliance.py` | ✅ |
| Especificaciones · COA · estabilidades | `calidad.py` | ✅ |
| Micro (specs/resultados/heatmap) · Agua · OOS | `calidad.py` | ✅ |
| Gestión documental (SGD) + capacitaciones+firma | `aseguramiento.py` | ✅ |
| Fichas técnicas · INVIMA · vencimientos doc | `tecnica.py` | ✅ |
| Audit trail Part 11 | `firmas.py` + `audit_log` | ✅ |

### SOPORTE TÉCNICO (Equipos)

| Función | EOS | Estado |
|---|---|---|
| Hoja de vida de equipos · cronograma · eventos | `calidad.py /api/calidad/equipos/*` | ✅ existe |
| Calibraciones · cronograma | `calidad.py` | ✅ existe |
| Limpieza de equipos (cleaning log) | `brd.py /api/brd/cleaning` | ✅ existe |
| Áreas/Líneas físicas de planta | — | ❌ **falta** (feature Asignaciones) |

---

## 3. Lo que EOS YA tiene como base (no reconstruir)

Tablas/endpoints existentes en `brd.py` que sostienen el motor EBR:
- `mbr_templates`, `mbr_pasos`, `ipc_specs` — plantillas (qué hacer)
- `ebr_ejecuciones`, `ebr_pasos_ejecutados`, `ebr_pesajes` — ejecución (qué se hizo)
- `despeje_linea_checklist` — despejes (soporta varios por EBR)
- `equipo_limpieza_log`, `cleaning` — limpieza de equipos
- `firmas.py /api/sign` — e-firma Part 11 (challenge + sign + consulta)
- Gate de liberación + cuarentena explícita + dashboard-estados
- PDF legajo + rótulos de pesaje

---

## 4. Huecos REALES a construir (para igualar MyBatch)

Aplican al **motor EBR unificado** (las 3 fases comparten):

1. **2ª firma de verificación** ⭐ (por paso y por material) — hoy EOS firma 1 vez (`ejecuta`); falta `verifica`. Corazón GMP.
2. **Discriminador de fase** (`tipo` = fabricación/envasado/acondicionamiento) en `ebr_ejecuciones` + plantillas por fase.
3. **Conciliación de material** (requerida / recibida / devuelta / utilizada) + **% rendimiento** por presentación.
4. **Secciones de cabecera/cierre**: Precauciones+Equipos · Observaciones generales · Registros físicos (adjuntar PDF).
5. **Runner UI**: botón "▶ Abrir EBR" por producción + estaciones con modal de captura **gateadas por rol** + máquina de estados `pendiente→registrado→verificado`.

**Específico de Acondicionamiento (OA):**
6. **Aprobación de Artes / Codificación** + **Aprobar Etiqueta** por presentación — gate GMP de etiquetado (verificar arte correcto + codificación lote/vencimiento antes de liberar).
7. **Unidades empacadas** (conciliación acondicionamiento: unidades recibidas de envasado → empacadas).

Extras menores:
- mL envasable + densidad tras fabricar (puente OP→OF)
- N° de orden formateado (OP/OF/OA-AÑO-NN)
- Lote Bulk separado de Lote PT
- Cantidad aprobada (post-QC)

Feature futura (no bloquea): **Áreas/Líneas físicas + Asignaciones** (qué OP en qué área/operario).

---

## 5. TOUR COMPLETADO ✅ (mapa al 100%)

- [x] **OP · Producción** — lista + crear + interior (EBR fabricación, 10 secciones)
- [x] **OF · Envasado** — lista + crear (+Nuevo/+Bulk) + interior (EBR envasado)
- [x] **OA · Acondicionamiento** — lista + interior (EBR acond. + Artes/Codificación)
- [x] **PM · Premezclas** — tabla vacía, columnas = OP → OP-para-intermedio, sin uso hoy
- [x] **ASEGURAMIENTO / SOPORTE** — confirmado: EOS ya lo cubre y excede (§2)

Opcional (no bloquea construcción):
- [ ] Maestros MyBatch: Áreas/Líneas, Equipos, Presentaciones, Materiales de envase (para la feature futura Asignaciones)

---

## 5.bis · PROGRESO DE CONSTRUCCIÓN

- [x] **Batch fase + motor base** · mig 209 (`ebr_ejecuciones.fase` + `ebr_pasos_ejecutados.fase`) · commit 065da8e · prod
- [x] **Batch 2ª firma de pesajes** · mig 208 (`verificado_por/at/e_sign_id`) + endpoint `/pesajes/<id>/verificar` · commit 53ad15c · prod
- [x] **Batch Runner UI** · sección "Legajos EBR" en tab Fabricación (filtro fase, abrir EBR, verificar pesaje, iniciar/completar paso con doble firma) · commit fe9d8fe · prod
- [ ] Batch conciliación material + %rend (Envasado)
- [ ] Batch Acondicionamiento + Artes/Codificación
- [ ] Batch cabecera/cierre + puente OP→OF (mL envasable)
- [ ] Batch PM Premezclas (prioridad mínima)

Nota: la 2ª firma de PASOS ya existía (qc_username/qc_e_sign_id en completar_paso_ebr).

## 6. Plan de construcción sugerido (cuando se apruebe)

Orden por valor GMP y dependencias, en batches cero-error:

1. **Fase + motor base**: añadir `tipo` a `ebr_ejecuciones`; plantillas MBR por fase (extiende Paso 1).
2. **2ª firma de verificación**: en pesajes y pasos (la pieza GMP #1).
3. **Runner UI en 🏭 Fabricación**: botón "Abrir EBR" + estaciones (despeje, dispensado, pasos, IPC) con modales + roles.
4. **Conciliación + %rend en 📦 Envasado**: material requerida/recibida/devuelta/utilizada + presentaciones.
5. **🔧 Acondicionamiento**: misma fase EBR (tras mapear OA).
6. **Cabecera/cierre**: precauciones, observaciones, registros físicos (PDF), puente OP→OF (mL).
7. **PM Premezclas**: según lo que revele el tour.

Cada batch: `ast.parse` + `node --check` + `pytest test_golden_paths` verde + commit + deploy + verificar /api/health.
