# Golden Paths Inventory · Cobertura anti-regresión EOS

> **Para agentes IA y devs:** lista exhaustiva de flujos críticos que
> NO pueden romperse. Cada uno debe tener test E2E en
> `tests/test_golden_paths.py`. Si no está cubierto → pendiente.

Última actualización: 2026-05-07

---

## Estados

- ✅ **Cubierto** · test E2E que valida el flujo completo desde POV del usuario
- 🔶 **Parcial** · hay tests unitarios pero falta E2E que conecte usuario → DB → downstream
- ⏳ **Pendiente** · sin cobertura · agregar
- 🚫 **No aplica** · flujo eliminado o redundante con otro

---

## Módulo: Auth & Sesión

| # | Flujo | Estado | Test |
|---|---|---|---|
| AUTH-1 | Login con credencial válida | 🔶 | `test_csrf_token.py` parcial |
| AUTH-2 | Login con MFA enrolado | 🔶 | `test_admin_mfa.py` |
| AUTH-3 | Reset password (admin) | 🔶 | `test_admin_panel.py` |
| AUTH-4 | Diag-login (Mayerlin caso) | 🔶 | tests existen, no marcados golden |
| AUTH-5 | Logout invalida sesión | ⏳ | falta |
| AUTH-6 | CSRF token enforcement | ✅ | `test_csrf_token.py` |
| AUTH-7 | Rate limit login (lock 15min) | ⏳ | falta E2E |

## Módulo: Inventario / Bodega MP

| # | Flujo | Estado | Test |
|---|---|---|---|
| INV-1 | Recepción MP → kardex → Bodega refleja | ⏳ | golden path nuevo |
| INV-2 | Eliminar lote con motivo → audit + kardex | ⏳ | golden path nuevo |
| INV-3 | Cambiar proveedor lote → propaga | ⏳ | falta |
| INV-4 | Conteo cíclico → ajuste afecta lote real | ✅ | `test_golden_paths.py` GP-1 |
| INV-5 | Conteo >5% diff → bloqueo gerencia → admin aprueba | 🔶 | parcial |
| INV-6 | Stock por material_id agregado correcto (helper) | 🔶 | unitario |
| INV-7 | Auditoría diferencia kardex vs físico | ⏳ | falta |
| INV-8 | Audit log SIEMPRE en operaciones de inventario | ⏳ | golden path nuevo |

## Módulo: Bodega MEE

| # | Flujo | Estado | Test |
|---|---|---|---|
| MEE-1 | Recepción MEE → maestro_mee.stock | 🔶 | parcial |
| MEE-2 | Auto-SC mensual MEE (cron) | 🔶 | tests existen |
| MEE-3 | Faltantes MEE para próximas producciones | 🔶 | en producciones-faltantes |

## Módulo: Programación / Plan

| # | Flujo | Estado | Test |
|---|---|---|---|
| PRG-1 | Sync Calendar espejo borra orfanos | ✅ | `test_golden_paths.py` GP-2 |
| PRG-2 | Limpiar duplicados respeta guard | ✅ | `test_golden_paths.py` GP-4 |
| PRG-3 | Producciones-faltantes calcula deficit MP+MEE | 🔶 | `test_producciones_faltantes.py` |
| PRG-4 | Solicitar-faltantes-bulk crea SOLs por proveedor | 🔶 | `test_producciones_faltantes.py` |
| PRG-5 | Calendar-first: app no escribe a Calendar | ⏳ | golden path nuevo |
| PRG-6 | Auto-plan cron: aplicar_plan respeta COALESCE | 🔶 | `test_auto_plan_consolida_proveedor.py` |

## Módulo: Producción

| # | Flujo | Estado | Test |
|---|---|---|---|
| PRO-1 | Iniciar producción → descontar inventario | ⏳ | golden path nuevo |
| PRO-2 | Completar producción → estado=completado | ⏳ | falta |
| PRO-3 | Cancelar producción en curso (admin) | ⏳ | falta |
| PRO-4 | Auto-asignar áreas + operarios (Mayerlin fija) | 🔶 | tests existen |
| PRO-5 | Mayerlin enforced en dispensación (DB triggers) | 🔶 | `test_planta_audit.py` |

## Módulo: Compras

| # | Flujo | Estado | Test |
|---|---|---|---|
| COM-1 | 3 fuentes SOL filtran (planta/usuarios/influencer) | ✅ | `test_golden_paths.py` GP-5 |
| COM-2 | PATCH SOL sincroniza global | ✅ | `test_golden_paths.py` GP-3 |
| COM-3 | Crear OC desde SOL → estado=Borrador | ⏳ | golden path nuevo |
| COM-4 | Aprobar OC (admin) → estado=Autorizada | ⏳ | falta |
| COM-5 | Pagar OC → estado=Pagada → no revertible | ⏳ | golden path nuevo |
| COM-6 | Comprobante PDF se genera | 🔶 | `test_compras_smoke.py` |
| COM-7 | Recepción contra OC → kardex | ⏳ | golden path nuevo |
| COM-8 | Limpiar SOLs planta (dry_run + ejecutar) | 🔶 | `test_compras_3fuentes.py` |
| COM-9 | Pago Influencer (CC) flow | 🔶 | tests existen |

## Módulo: Calidad / Aseguramiento

| # | Flujo | Estado | Test |
|---|---|---|---|
| ASG-1 | Desviación: crear → clasificar → investigar → CAPA → cerrar | ✅ | `test_reportes_invima.py::test_audit_trail_filtro_accion` (hardened) |
| ASG-2 | Quejas ASG-PRO-013 lifecycle | 🔶 | `test_aseguramiento_quejas.py` |
| ASG-3 | Recalls ASG-PRO-004 | 🔶 | `test_aseguramiento_recalls.py` |
| ASG-4 | Cambios ASG-PRO-007 | 🔶 | `test_aseguramiento_cambios.py` |
| ASG-5 | Audit log regulatorio (mig 91) | 🔶 | tests existen |

## Módulo: Animus (Skincare)

| # | Flujo | Estado | Test |
|---|---|---|---|
| ANI-1 | Inventario físico baseline (Daniela) | 🔶 | `test_animus_inv_fisico.py` |
| ANI-2 | Conteo diario asignado por cron | 🔶 | tests existen |
| ANI-3 | Discrepancia esperado vs físico → revisión | 🔶 | tests existen |
| ANI-4 | Ajuste manual con motivo | ⏳ | falta |

## Módulo: Comercial / Maquila / Clientes

| # | Flujo | Estado | Test |
|---|---|---|---|
| CMR-1 | Pipeline Maquila B2B (deals) | ⏳ | falta E2E |
| CMR-2 | Cliente Aliado Animus | ⏳ | falta |

## Módulo: Operaciones críticas

| # | Flujo | Estado | Test |
|---|---|---|---|
| OPS-1 | Backup automático nocturno | 🔶 | `test_backup.py` |
| OPS-2 | /api/health responde | ✅ | tests core |
| OPS-3 | /api/admin/health/critical-paths 8 checks | ✅ | `test_health_critical_paths.py` |
| OPS-4 | Cron Watcher horario | ✅ | mig + endpoint |
| OPS-5 | agent_memory CRUD | ✅ | `test_agent_memory.py` |
| OPS-6 | Health degrada → 503 → uptime monitor | ✅ | `test_health_critical_paths.py` |
| OPS-7 | Migrations idempotentes | 🔶 | tests existen |
| OPS-8 | WAL mode + concurrent writes | 🔶 | parcial |

---

## Resumen de cobertura (post-sprint 7-may-2026)

```
✅ Cubierto E2E (15 golden paths verdes en CI):
   GP-1  · Conteo cíclico ajuste afecta lote real      [INV-4]
   GP-2  · Sync Calendar espejo borra orfanos          [PRG-1]
   GP-3  · PATCH SOL sincroniza global                 [COM-2]
   GP-4  · Limpiar duplicados respeta guard            [PRG-2]
   GP-5  · 3 fuentes SOL no se mezclan                 [COM-1]
   GP-6  · Login básico funciona                       [AUTH-1]
   GP-7  · Recepción MP actualiza kardex               [INV-1]
   GP-8  · Audit log siempre en operaciones            [INV-8]
   GP-9  · Calendar-first · app no escribe Calendar    [PRG-5]
   GP-10 · Iniciar producción descuenta inventario     [PRO-1]
   GP-11 · Crear OC desde SOL                          [COM-3]
   GP-12 · Endpoints públicos responden (health/login) [OPS-2]
   GP-13 · Migrations idempotentes                     [OPS-7]
   GP-14 · CSRF protección cross-origin                [AUTH-6]
   GP-15 · Aseguramiento endpoints básicos             [ASG-1]

🔶 Parcial: 27 flujos · tests unitarios sin marca golden
⏳ Pendiente: 18 flujos restantes
```

**Antes del sprint**: 5 flujos cubiertos.
**Después del sprint**: 15 flujos cubiertos · +200%.

## Plan de expansión

**Sprint 7-may-2026** · agregar 10 golden paths nuevos:
1. AUTH-1 · login básico
2. INV-1 · recepción MP → Bodega
3. INV-2 · eliminar lote con motivo
4. INV-8 · audit log siempre presente
5. PRG-5 · Calendar-first invariant
6. PRO-1 · iniciar producción descuenta inventario
7. COM-3 · crear OC desde SOL
8. COM-5 · pagar OC no revertible
9. COM-7 · recepción contra OC
10. OPS-2 · /api/health basic + smoke endpoints públicos

Después de este sprint: 22 golden paths cubriendo todos los flujos
de uso diario (Catalina, Mayerlin, Luis Enrique, Sebastián).

---

## Cómo agregar un nuevo golden path

1. Identificá el flujo crítico (¿qué hace el usuario? ¿qué espera?)
2. Agregá test en `tests/test_golden_paths.py` con prefijo
   `test_golden_<modulo>_<accion>`.
3. El test:
   - Seedea estado inicial limpio
   - Ejecuta acción de usuario (POST/PATCH/DELETE)
   - Valida efecto downstream (otra tabla cambió, otro endpoint refleja)
   - Cleanup completo en `finally`
4. Actualizá este archivo: cambiá ⏳ → ✅ con link al test.
5. Si tocás un blueprint, actualizá su `CONTRACT_*.md`.
6. `bash scripts/guardian.sh --quick` debe pasar.
