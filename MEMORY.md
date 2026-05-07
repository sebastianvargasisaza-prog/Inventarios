# MEMORY · Reglas estáticas EOS Inventarios

> **Para agentes IA · LEER ANTES de cualquier modificación.** Este archivo
> persiste reglas inmutables del dominio. Si una regla cambia, el cambio
> debe quedar registrado en `SESSION_LOG/` con justificación.

Última revisión: 2026-05-07

---

## 🏭 Arquitectura

### Calendar Producciones = ÚNICA fuente de verdad
- Google Calendar (animuslb.com) define qué se produce y cuándo.
- La app **lee** Calendar y sincroniza a `produccion_programada`.
- La app **NO escribe** al Calendar — eso lo hace Alejandro manualmente.
- Sync bidireccional: `_sync_calendar_a_produccion_programada()` en
  `api/blueprints/programacion.py`.
- **`force_mirror=True`** hace HARD DELETE de orfanos (cualquier origen)
  excepto los protegidos por guard.

### Stock = SUMA de movimientos (kardex)
- Tabla canónica: `movimientos` con campos `material_id`, `cantidad`,
  `tipo` ('Entrada'|'Salida'), `lote`, `estado_lote`.
- Helper canónico: `_get_mp_stock(conn)` en `programacion.py`.
- **NUNCA** calcular stock por otro medio — siempre kardex.
- **NUNCA** insertar movimientos sin `lote` — siempre lote real, jamás sintético
  cuando exista (excepción: `AJUSTE-CICLICO-<id>` solo si conteo no tiene lote).

### Stock planeación = Available (no On hand)
- Para MRP / forecast usar columna **Available** de Shopify, NO On hand.
- Committed ya está vendido y debe restarse del On hand.

### Pipeline producción → stock 7d
- Lote fabricado tarda **~7 días** en quedar disponible en Shopify.
- Sumar pipeline al stock efectivo cuando se planee producción.

---

## 📊 Conteo cíclico

### Threshold gerencia: 5%
- Diferencia ≥5% del stock_sistema → marca `requiere_gerencia=1`.
- No puede aplicarse sin `aprobado_gerencia=1`.
- Solo `ADMIN_USERS` (sebastian, alejandro) pueden auto-aprobar.
- Norma: BDG-PRO-002 num 8.

### Ajuste se aplica al lote REAL
- `INSERT INTO movimientos` con `lote = it['lote']` del conteo_items.
- Fallback `'AJUSTE-CICLICO-<id>'` SOLO si lote vacío.
- Razón: Bodega Materias Primas muestra stock por lote individual; un
  lote sintético deja el lote original con stock viejo.

### Guard inicio/descontado
- Si `inicio_real_at` o `inventario_descontado_at` set, NO tocar la fila.
- Aplica a: sync espejo, limpiar duplicados, cancelar orfanos.

---

## 🛒 Compras · 3 fuentes de SOLs

| Fuente | Categorías | Tab UI |
|---|---|---|
| **planta** | Materia Prima, Empaque, Material de Empaque | 🏭 Planta |
| **usuarios** | Papelería, Servicios, EPP, etc. (NO planta NO influencer) | 📋 Solicitudes |
| **influencers** | Influencer/Marketing Digital, Cuenta de Cobro | 💸 Influencers |

- Filtro vía `?fuente=` en `/api/solicitudes-compra` y
  `/api/compras/solicitudes-agrupadas-por-proveedor`.
- Sin `?fuente=` = legacy compatible (todas).

### PATCH SOL items sincroniza GLOBAL
Al editar un item de SOL (`PATCH /api/solicitudes-compra/<num>/items`):
- Si cambia `proveedor` → actualiza `maestro_mps.proveedor` Y
  `mp_lead_time_config.proveedor_principal` (crea row si no existe con
  defaults: lead 14d, buffer 30d, origen 'local').
- Si cambia `precio_unit_g` → actualiza `maestro_mps.precio_referencia`
  (= precio_unit_g × 1000 · g/g → $/kg).
- Audit log: `SYNC_PROVEEDOR_GLOBAL`.

---

## 📦 Unidades · SIEMPRE en gramos

- Display de cantidades MP **siempre gramos** con separador de miles.
- **NUNCA** mostrar kg en UI principal (Alejandro 2026).
- Excepción: el campo `cantidad_kg` de `produccion_programada` (es para producción, no display).
- Tanques grandes (Glicerina/Aerosil/etc.): cientos de kg son normales, no inflados.

---

## 👥 Equipo planta (post-INVIMA abril 2026)

### Operarios
- **Mayerlin** — fija dispensación (no rota a otras áreas).
- **3 operarios rotantes** — Elaboración, Envasado, Acondicionamiento.
- Total: **4 operarios** + Luis Enrique (jefe).

### 5 Salas (post-INVIMA)
- PROD1, PROD2, PROD3, PROD4 (alias FAB1, FYE2, FYE3, ENV2 en Calendar).
- ENV1 (envasado).

### Convención Calendar
- Eventos empiezan con `[CODIGO]` para auto-asignar sala. Ej:
  `[FAB1] Gel Hidratante 50ml ~5kg`.
- Si no tiene código, auto-asignador IA lo decide (cron 6:30 AM).

---

## 🤝 Permisos / Roles

| Rol | Users | Capacidades |
|---|---|---|
| `ADMIN_USERS` | sebastian, alejandro | TODO + aprobar gerencia, hard delete, reset password |
| `COMPRAS_USERS` | catalina, luis, sebastian, alejandro, ... | Crear/editar SOL/OC, sync, limpiar, etc. |
| Usuario normal | resto | Crear solicitudes, ver kardex, recepción |

---

## 🚨 Lo que NUNCA debe romperse (golden paths)

1. **Conteo cíclico** → ajuste afecta el lote REAL · Bodega refleja.
2. **Sync Calendar espejo** → borra orfanos manuales sin tocar iniciados.
3. **PATCH SOL** → sincroniza global maestro_mps + mp_lead_time_config.
4. **Limpiar duplicados** → respeta guard inicio_real_at/descontado.
5. **3 fuentes SOL** → no se mezclan (Catalina ve cada tab limpio).

Tests E2E: `tests/test_golden_paths.py` · 5 tests obligatorios pre-push.

---

## 📚 Para profundizar

- `~/.claude/projects/.../memory/MEMORY.md` (perfil usuario Sebastián)
- `~/.claude/projects/.../memory/project_inventarios.md` (stack)
- `~/.claude/projects/.../memory/project_animus_arquitectura_planeacion.md` (Calendar=verdad)
- `tests/conftest.py` (fixtures de test)
- `RUNBOOK.md` (operación)
