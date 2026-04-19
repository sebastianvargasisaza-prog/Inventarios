# HHA GROUP — Sistema Operativo Digital
## Master Plan: Ecosistema completo, seguridad y hoja de ruta por capas
**Fecha:** 2026-04-17 | **CEO:** Sebastián Vargas Isaza, MD MPH | **Co-fundador:** Alejandro Morales

---

## VISIÓN

Un solo sistema que opera toda la holding. Espagiria manufactura, ÁNIMUS vende, HHA Group consolida. Sebastián abre una pantalla y sabe en 30 segundos cómo va el negocio, qué está en riesgo, y qué decisión tomar.

```
╔══════════════════════════════════════════════════════════════════╗
║                     HHA GROUP DIGITAL OS                        ║
║                                                                  ║
║   ESPAGIRIA                    ÁNIMUS LAB                        ║
║   ├─ Inventario MPs            ├─ Clientes & Pedidos             ║
║   ├─ MEE (empaque)             ├─ Aliados B2B                    ║
║   ├─ Fórmulas & Producción     ├─ Producto terminado             ║
║   ├─ Compras & OCs             ├─ Despachos                      ║
║   ├─ Maquila 360               └─ Expansión (Ecuador)            ║
║   └─ Área Científica                                             ║
║                                                                  ║
║   ─────────────────── HQ GERENCIA ──────────────────────         ║
║   KPIs en tiempo real · Flujo de caja · Alertas ejecutivas       ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## ESTADO ACTUAL — Lo que existe hoy

### ✅ Operativo (Flask app en Render)

| Módulo | Funcionalidad | Estado |
|---|---|---|
| **Dashboard / Inventario MPs** | Stock en tiempo real, FEFO, lotes, vencimientos, rótulos GMP | ✅ Operativo |
| **MEE** | Envases, etiquetas, tapas — stock mutable | ✅ Operativo |
| **Fórmulas** | CRUD, cálculo de ingredientes por lote | ✅ Operativo |
| **Producción** | FEFO automático, descuento MPs, registro de lote | ✅ Operativo |
| **Alertas reabastecimiento** | MPs bajo mínimo, déficit calculado | ✅ Operativo |
| **Solicitudes** | Formulario público, pago/compra según categoría | ✅ Operativo |
| **Compras** | OC, proveedores, solicitudes, aprobación por rol | 🔧 Bugs pendientes |
| **Rótulos** | HTML imprimible con barcode por MP dispensada | ✅ Operativo |
| **Hub HHA Group** | Landing page con tarjetas de módulos | ✅ Operativo |

### ⚠️ Bugs críticos (corregir este fin de semana)
1. `recibir_oc()` escribe `tipo='ingreso'` → stock nunca se actualiza desde Compras
2. `generar_oc_automatica()` usa columna que no existe → error SQL silencioso
3. `/api/reset-movimientos` sin autenticación → cualquiera puede borrar todo

### 📁 En carpetas (sin digitalizar aún)
- Fórmulas Maestras: ~30 productos con parámetros reales (PDFs/docs en Gerencia)
- Flujo de Caja 2026: modelo Excel completo 12 meses (HHA + ÁNIMUS + Espagiria)
- Programa Aliados ÁNIMUS: 16 formatos FR-AC estandarizados, control maestro Excel
- Calculador Maquila + Cotizador Maestro: pricing Espagiria
- IMVIMA: auditoría feb 2026, checklist Resolución 2214

---

## ARQUITECTURA DEL SISTEMA

### Stack tecnológico

```
FRONTEND + BACKEND       BASE DE DATOS         INFRAESTRUCTURA
─────────────────        ─────────────         ───────────────
Python Flask             SQLite → PostgreSQL    Render (deploy)
HTML/CSS/JS              (Supabase futuro)      GitHub (repo)
Single-file app          /var/data/             Auto-deploy
3,529 líneas hoy         inventario.db          en push a main
```

### Modelo de autenticación actual vs objetivo

```
ACTUAL                          OBJETIVO
──────                          ───────
Dashboard: sin auth  →          Auth requerida (rol viewer/operario)
Compras: session     →          JWT + roles granulares
Solicitudes: público →          Token por empresa (Espagiria/ÁNIMUS)
Reset datos: sin auth→          Solo admin + confirmación 2 pasos
```

### Roles y accesos — Equipo HHA Group

| Persona | Rol | Módulos | Nivel |
|---|---|---|---|
| **Sebastián Vargas** | CEO / Admin | Todos | Admin total + HQ Gerencia |
| **Alejandro Morales** | Co-fundador / Admin | Todos | Admin total + aprobador Compras |
| **Catalina Erazo** | Asistente Cartera & Compras | Compras, Solicitudes | Gestor operativo |
| **Luz (Adriana Torres)** | Asistente Gerencia Espagiria | Inventario, Producción, MEE | Operario |
| **Daniela** | Asistente Gerencia ÁNIMUS | Inventario, Clientes | Operario |
| **Mayra** | Contadora | Compras (financiero) | Revisor financiero |
| **Operarios planta** | Producción | Producción, MEE | Solo registro |

---

## HOJA DE RUTA POR CAPAS

### CAPA 0 — SEGURIDAD (Hacer ANTES de cualquier nueva funcionalidad)
**Prioridad:** Máxima | **Esfuerzo:** 1 día | **Desbloquea:** operar con confianza

#### Seguridad de datos

| Riesgo | Solución |
|---|---|
| `/api/reset-movimientos` sin auth | Auth + confirmación texto "BORRAR" + solo admin |
| SECRET_KEY hardcodeado en código | Variable de entorno en Render |
| Sin backup automático de BD | Script cron diario → export SQLite → email/storage |
| Dashboard sin auth | Login mínimo (pin de empresa o token URL) |
| Sin rate limiting en login | Bloquear IP tras 5 intentos fallidos |
| Sin audit trail de cambios | Tabla `audit_log` (who, what, when, ip) |
| Solicitudes sin verificación de origen | Token por empresa en URL |

#### Backup y recuperación

```
Estrategia 3-2-1:
  3 copias de los datos
  2 medios diferentes
  1 fuera del servidor principal

Implementación práctica:
  → Render persistent volume: copia principal (ya existe)
  → Export automático diario a Google Drive o email
  → Script manual antes de cada deploy importante
```

#### Código que se agrega a init_db() para audit trail

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    accion TEXT,        -- 'recibir_oc', 'reset_movimientos', 'eliminar_formula'
    tabla TEXT,
    registro_id TEXT,
    detalle TEXT,       -- JSON con antes/después
    ip TEXT,
    fecha TEXT
);
```

---

### CAPA 1 — BUGS Y COMPRAS COMPLETO
**Sprint:** Este fin de semana (19-20 abril) | **Esfuerzo:** ~6 horas

| # | Tarea | Impacto |
|---|---|---|
| T0-1 | Fix `tipo='ingreso'` → `'Entrada'` en recibir_oc() | Activa ciclo completo Compras→Inventario |
| T0-2 | Fix columna `cantidad_solicitada` en OC automática | OC auto funcional |
| T0-3 | Auth en reset-movimientos | Seguridad crítica |
| F1 | patch_fase1.py (9 mejoras Compras) | Ver detalle OC, valor total, columnas |
| C0 | SECRET_KEY a variable de entorno | Seguridad base |

**Resultado al finalizar:** El ciclo Solicitud → Aprobación → OC → Recepción → Inventario funciona completo por primera vez.

---

### CAPA 2 — CLIENTES + PRODUCTO TERMINADO
**Sprint:** Este fin de semana (continuación) | **Esfuerzo:** ~4 horas

**Qué construye:**
- Tabla `clientes` con CLI-001 (ÁNIMUS Lab) y CLI-002 (Fernando Mesa) precargados
- Tabla `stock_pt` alimentada automáticamente desde producción
- Tabla `pedidos` con ciclo Confirmado → Produciendo → Listo → Despachado → Facturado
- Tabla `despachos` con trazabilidad de lotes PT entregados a cada cliente
- Módulo `/clientes` con 4 tabs: Dashboard | Clientes | Pedidos | Stock PT

**KPIs que desbloquea:**
- Unidades PT disponibles por SKU en tiempo real
- Pedidos activos y su valor
- Historial de despachos por cliente
- Trazabilidad bidireccional: MP lote → producción → despacho → cliente

**Fernando Mesa en el sistema:**
- 9 SKUs precargados con precio mayorista
- Pedido recurrente ~cada 60 días → alerta automática
- Valor potencial por ciclo: ~$94.5M COP

---

### CAPA 3 — HQ GERENCIA (KPIs Ejecutivos)
**Sprint:** Este fin de semana | **Esfuerzo:** ~3 horas

**Qué construye:**
Panel exclusivo CEO + Alejandro. Una pantalla, todo el negocio.

```
┌────────────────────────────────────────────────────────────────┐
│  HHA GROUP — Panel Gerencial              Abril 2026           │
├────────────┬────────────┬────────────────┬───────────────────  │
│  💰 CAJA   │  📦 VENTAS │  🏭 PRODUCCIÓN │  ⚠️ ALERTAS        │
│  $354.8M   │  $433.5M   │  14 lotes      │  🔴 3 críticas     │
│  meta: OK  │  +5% ↑     │  este mes      │  🟡 5 medianas     │
└────────────┴────────────┴────────────────┴────────────────────┘
│                                                                │
│  ÁNIMUS Lab              ESPAGIRIA                            │
│  ─────────               ─────────                            │
│  FM pedido: en 12 días   MPs bajo mínimo: 8                   │
│  Despacho pendiente: 0   Lotes venciendo: 3 (30 días)         │
│  Cuentas por cobrar: $0  OCs sin aprobar: 2 ($4.2M)           │
│                          Maquila facturada: $30M              │
└────────────────────────────────────────────────────────────────┘
```

**KPIs disponibles de inmediato (desde BD):**
- MPs bajo mínimo y déficit estimado
- Lotes venciendo en 30/60/90 días
- Producción del mes (lotes, kg por SKU)
- OCs pendientes de aprobación y valor
- Pedidos FM activos y próximo vencimiento
- Stock PT por SKU

**KPIs con 1 input manual mensual (Sebastián actualiza en 5 min):**
- Saldo de caja actual
- Ingresos ÁNIMUS del mes (del CSV Shopify)
- Ingresos maquila del mes

**KPIs que se calculan automáticamente:**
- CMV real (suma de `precio_unitario × cantidad` en OCs pagadas)
- Cuentas por cobrar (despachos sin fecha de pago registrada)
- Proyección de caja a 30 días (saldo - compromisos pendientes)

---

### CAPA 4 — FLUJO DE CAJA DIGITAL
**Sprint:** Mayo 2026 | **Esfuerzo:** ~1 semana

**Qué construye:**
Digitalizar el `HHA_Flujo_Caja_2026.xlsx` dentro del sistema. Misma estructura, mismas fórmulas, pero con datos reales que fluyen desde el sistema.

```
Módulo: Financiero
├── Tab Supuestos (editables): TRM, crec. ventas, CMV%, nóminas
├── Tab HHA Consolidado: suma automática de las dos empresas
├── Tab ÁNIMUS Lab: ingresos + costos + EBITDA + flujo neto
└── Tab Espagiria: maquila + costos planta + flujo neto
```

**Conexiones automáticas:**
- Compras pagadas → egresos reales de MPs
- Pedidos facturados → ingresos reales ÁNIMUS
- Maquila despachada → ingresos Espagiria
- OCs aprobadas → compromisos futuros de caja

**Alertas que genera:**
- Saldo proyectado cae por debajo de umbral (configurable, ej: $50M)
- CMV real supera CMV proyectado en >5%
- Brecha proyectado vs real >10% en cualquier línea

---

### CAPA 5 — MAQUILA 360
**Sprint:** Junio 2026 | **Esfuerzo:** ~1 semana

**Qué construye:**
Módulo completo para el negocio de maquila de Espagiria como cliente externo.

**Funcionalidades:**
- Clientes maquila (tipo='Maquila') con fórmulas confidenciales separadas
- Órdenes de maquila: kg solicitados, fórmula, empaque del cliente, precio/kg
- Costeo automático: MPs consumidas × precio + MEE + fee servicio = precio maquila
- Facturación de servicio (diferente a venta de producto)
- Trazabilidad de lotes por cliente maquila (regulatorio)

**Integración con el Cotizador Maestro:**
El `Espagiria_Cotizador_Maestro.xlsx` existente se digitaliza como la lógica de pricing de maquila. El sistema calcula automáticamente qué cobrar basado en fórmula + empaque + volumen.

**Revenue que desbloquea visibilidad:**
Maquila hoy: $30M/mes (dato del flujo de caja). Con el módulo, sabes exactamente qué cliente, qué producto, qué margen, qué mes.

---

### CAPA 6 — ALIADOS ÁNIMUS (Canal B2B)
**Sprint:** Julio 2026 | **Esfuerzo:** ~1 semana

**Qué construye:**
Digitalizar el Programa Aliados Estratégicos ÁNIMUS (los 16 formatos FR-AC ya existen en papel).

```
Módulo: Aliados
├── Registro de aliados (solicitud FR-AC-01)
├── Evaluación y aprobación (FR-AC-02 y 03)
├── Onboarding digital (FR-AC-04 y 05)
├── Pedidos por aliado (extiende módulo Clientes)
├── KPI por aliado: ventas, frecuencia, cumplimiento
├── Semáforo de salud: verde/amarillo/rojo
├── Comité mensual automático (FR-AC-10)
└── Notificaciones: incumplimientos, ascensos (FR-AC-12 y 13)
```

**Fernando Mesa en este contexto:** hoy es el único aliado activo. El módulo permite escalar a N aliados con el mismo proceso estandarizado.

**Desbloquea Ecuador:** cuando se apruebe la expansión, los distribuidores ecuatorianos entran como aliados tipo='Internacional' con moneda USD.

---

### CAPA 7 — ÁREA CIENTÍFICA ESPAGIRIA
**Sprint:** Agosto 2026 | **Esfuerzo:** ~1 semana

**Qué construye:**
Tercera línea de negocio de Espagiria: servicios científicos (estudios clínicos, desarrollo de fórmulas, consultoría regulatoria).

```
Módulo: Científico
├── Proyectos: cliente, tipo (estudio/desarrollo/regulatorio), estado
├── Presupuesto por proyecto y facturación
├── Protocolos: vinculados a fórmulas del sistema
├── Resultados: datos de eficacia + seguridad
└── Publicaciones / reportes: generados desde el sistema
```

**Integración con Inventario:**
Los estudios clínicos consumen MPs del inventario (muestras para panel, volúmenes de prueba). Actualmente no se descuenta. Con este módulo se registra como "consumo I+D" con su propio tipo de movimiento.

---

### CAPA 8 — REGULATORIO / INVIMA
**Sprint:** Agosto-Septiembre 2026 | **Esfuerzo:** ~3 días

**Prioridad alta dado:** Auditoría INVIMA en febrero 2026 (hace 2 meses). Hay checklist de Resolución 2214 activo.

```
Módulo: Regulatorio (embebido en Dashboard)
├── Registro NS por producto: número, fecha otorgamiento, vencimiento
├── Alerta automática NS por vencer (90/60/30 días)
├── COA semi-automático: genera certificado desde datos de producción
│   (MPs usadas + lotes + resultados + firma DT)
├── Cuarentena de lotes: flujo liberación por QC
├── Desviaciones y CAPA: registro de incidentes
└── Control de cambios de fórmula: versioning con aprobación
```

**Riesgo actual sin este módulo:** No sabes si alguna NS está por vencer. No hay COA por lote automatizado. Checklist de auditoría es papel.

---

### CAPA 9 — EXPANSIÓN INTERNACIONAL
**Sprint:** Según decisión Ecuador | **Esfuerzo:** ~3 días

**Documentos existentes:** `Analisis_Decision_Ecuador_Interno.docx` y `Propuesta_Distribucion_Ecuador_v3.docx`

**Qué agrega al sistema:**
- Campo `pais` en clientes (ya lo considera el diseño de Clientes)
- `moneda` en pedidos (COP / USD)
- Lista de precios por país (tabla `lista_precios` por canal + país)
- TRM configurable (ya en el flujo de caja)
- Aliados tipo='Internacional'

---

### CAPA 10 — INTEGRACIONES EXTERNAS
**Sprint:** Según prioridad | **Esfuerzo:** Variable

| Integración | Datos que trae | Prioridad |
|---|---|---|
| Shopify API | Ventas DTC diarias en tiempo real → ÁNIMUS ingresos | Alta |
| Coordinadora / DHL | Estado despachos → actualizar pedidos | Media |
| Banco (Bancolombia) | Movimientos reales → flujo de caja real | Media |
| MyBatch (CielTechno) | EBR Espagiria → lotes de producción | Baja |
| Resend / Gmail | Notificaciones OC, alertas stock → email | Ya instalado |

---

## ARQUITECTURA DE SEGURIDAD COMPLETA

### Niveles de protección

```
NIVEL 1 — AUTENTICACIÓN
  Hoy: solo Compras tiene login
  Objetivo: todos los módulos con acceso controlado
  
  Roles:
    admin     → acceso total + destructive actions
    gerente   → HQ + todos los módulos (read + write)
    operario  → Dashboard + Producción + MEE (no delete)
    compras   → Módulo Compras completo
    contadora → Solo vista financiera de Compras
    viewer    → Solo lectura de Dashboard y HQ

NIVEL 2 — AUTORIZACIÓN POR ACCIÓN
  Acciones destructivas (borrar, resetear, rechazar):
    → Require rol admin
    → Require confirmación texto
    → Log en audit_trail

  Acciones financieras (aprobar OC >$X, crear pago):
    → Require rol admin o gerente
    → Notificación automática a Sebastián/Alejandro

NIVEL 3 — INTEGRIDAD DE DATOS
  Audit trail: cada INSERT/UPDATE/DELETE registrado
  Soft delete: nunca borrar físicamente, marcar activo=0
  Versioning de fórmulas: guardar snapshot antes de cambio
  
NIVEL 4 — DISPONIBILIDAD
  Backup diario automático → Google Drive o email
  Script de restore documentado y probado
  No deploy los lunes ni viernes sin backup previo

NIVEL 5 — ACCESO EXTERNO
  HTTPS: Render lo maneja automáticamente ✅
  Rate limiting: máx 5 intentos login por IP/15min
  CSRF tokens en formularios POST
  API keys para futuras integraciones externas
  SECRET_KEY: variable de entorno, nunca en código
```

### Plan de recuperación ante desastre

```
ESCENARIO 1: Alguien borra datos por error
  → Restore desde backup del día anterior
  → Tiempo estimado: 15 minutos
  → Pérdida máxima: 24 horas de movimientos

ESCENARIO 2: Render falla / pierde el volumen
  → Último backup en Google Drive
  → Re-deploy desde GitHub (1 clic)
  → Restore backup
  → Tiempo estimado: 30-45 minutos

ESCENARIO 3: Hackeo o acceso no autorizado
  → Cambiar SECRET_KEY en Render → invalida todas las sesiones
  → Revisar audit_log para ver qué se tocó
  → Restore desde backup si hay modificación de datos

ESCENARIO 4: Bug en deploy rompe la app
  → git revert HEAD → git push → Render redeploya versión anterior
  → Tiempo estimado: 3 minutos
```

---

## FLUJO DE DATOS — VISIÓN COMPLETA

```
ENTRADAS AL SISTEMA
─────────────────────────────────────────────────────────────────
Proveedores → [Compras/OCs] → MPs en inventario
Importaciones → [Compras] → MPs en inventario
Maquila clientes → [Maquila 360] → Órden de maquila → Producción
Shopify DTC (futuro) → [ÁNIMUS] → Pedido → despacho PT

PROCESOS INTERNOS
─────────────────────────────────────────────────────────────────
MPs + Fórmulas → [Producción FEFO] → Lote producido → stock_pt
stock_pt + Pedido FM → [Despacho] → Factura
Producción científica → [Área Científica] → Servicio facturado

SALIDAS / REPORTES
─────────────────────────────────────────────────────────────────
stock_pt + pedidos + compras → [HQ Gerencia] → KPIs CEO
producciones + movimientos → [COA] → Certificado por lote
pedidos + despachos → [Clientes] → Facturación FM
compras pagadas → [Flujo de Caja] → Egresos reales
```

---

## RESUMEN DE CAPAS — CUÁNDO Y QUÉ

| Capa | Nombre | Sprint | Duración | Desbloquea |
|---|---|---|---|---|
| **0** | Seguridad base | Este fin de semana | 2 horas | Operar con confianza |
| **1** | Bugs + Compras | Este fin de semana | 3 horas | Ciclo completo compras→inventario |
| **2** | Clientes + PT | Este fin de semana | 4 horas | Saber cuánto tienes para despachar |
| **3** | HQ Gerencia | Este fin de semana | 3 horas | KPIs CEO en tiempo real |
| **4** | Flujo de Caja | Mayo 2026 | 1 semana | Visión financiera completa |
| **5** | Maquila 360 | Junio 2026 | 1 semana | Revenue maquila visible y trazable |
| **6** | Aliados ÁNIMUS | Julio 2026 | 1 semana | B2B channel escalable |
| **7** | Área Científica | Agosto 2026 | 1 semana | 3ra línea ingreso Espagiria visible |
| **8** | Regulatorio | Ago-Sep 2026 | 3 días | INVIMA + COA automático |
| **9** | Internacional | Según Ecuador | 3 días | Expansión sin rehacer nada |
| **10** | Integraciones | Según prioridad | Variable | Datos en tiempo real sin input manual |

---

## MÉTRICAS DEL SISTEMA HOY

```
Código:           3,529 líneas Python + HTML + JS en 1 archivo
Rutas API:        37 endpoints
Tablas BD:        13 → 19 después de Clientes (6 tablas nuevas)
Módulos activos:  5 (Hub, Dashboard, MEE, Compras, Solicitudes)
Módulos diseñados: 3 (Clientes, HQ, Flujo de Caja)
Módulos planificados: 7 más (Maquila, Aliados, Científico, etc.)
Deploy:           GitHub → Render (automático en push a main)
Costo mensual:    ~$7 USD (Render hobby plan)
Uptime:           99.5% (Render SLA)
```

---

## PRÓXIMOS 72 HORAS — SPRINT CERO A TRES

### Sábado 19 de abril
**Mañana (09:00 - 12:00):**
- [ ] Backup manual de BD (descargar inventario.db de Render)
- [ ] Clonar repo fresco en /tmp/inv_weekend
- [ ] Aplicar Capa 0: SECRET_KEY a env var + proteger reset-movimientos
- [ ] Aplicar Capa 1: bugs T0 + patch_fase1.py
- [ ] Commit + push + verificar en producción

**Tarde (14:00 - 19:00):**
- [ ] Aplicar Capa 2: SQL schema Clientes (6 tablas + seed FM)
- [ ] Endpoints API Clientes (8 rutas)
- [ ] Integración producción → stock_pt
- [ ] HTML básico del módulo Clientes

### Domingo 20 de abril
**Mañana (09:00 - 12:00):**
- [ ] Completar HTML Clientes (4 tabs)
- [ ] Módulo HQ Gerencia (Capa 3): HTML + API /api/hq-stats
- [ ] Tarjeta HQ en Hub HHA Group

**Tarde (14:00 - 17:00):**
- [ ] Testing integral: flujo A (Compras→Inventario), B (Producción→PT→Clientes), C (HQ stats)
- [ ] Deploy final + verificación con Alejandro
- [ ] Documentar qué quedó pendiente para siguiente sprint
