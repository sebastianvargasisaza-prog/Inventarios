# MAP · `admin.py` (jump table)

> **Para agentes IA.** `admin.py` tiene ~27.700 líneas y 176 rutas. NO lo leas entero.
> Usa esta tabla para saltar al rango aproximado, luego `Read` con `offset`/`limit`
> sobre esa zona. Las líneas son aproximadas (se mueven al editar) — confirma con
> `grep -n '<ruta>' api/blueprints/admin.py` antes de editar.

Generado: 2026-06-08 · 176 rutas · `grep -nE '\.route\(' api/blueprints/admin.py` regenera la lista cruda.

| Rango aprox. | Tema | Rutas representativas |
|---|---|---|
| 43–1145 | **Backups / restore / DB health** | `/api/admin/backups`, `backup-now`, `cron-db-integrity-check`, `db-health-historial`, `emergency-restore`, `restore-backup` |
| 1147–2900 | **Usuarios / seguridad / zero-error / agent-memory** | `users`, `reset-password`, `security-events`, `config-status`, `test-email`, `diag-login`, `zero-error/status`, `health/critical-paths`, `agent-memory` |
| 1198–1672 · 12620–12800 | **SKU mapping** | `skus-pendientes`, `sku-producto-map`, `sku-map` |
| 3021–3340 · 5236 · 15643–15868 | **Import / siembra maestro MP desde Excel** | `import-mps-nombres-excel`, `sembrar-maestro-desde-excel`, `crear-mps-faltantes-excel`, `verificar-mps-maestro` |
| 3339–3900 · 5362–5820 | **Inventario: reset / snapshot / audit vs Excel** | `audit-inventario-vs-excel`, `inventario-snapshot-pre-reset`, `inventario-reset-preview`, `inventario-reset-aplicar`, `inventario-health-monitor`, `health-check-post-reset` |
| 4172–5235 · 14005–14432 · 17269–17460 · 18002–18392 · 21816 | **Fórmulas: diagnóstico / corrección / revert / huérfanos** | `diagnosticar-formulas`, `corregir-formulas`, `revertir-correcciones-*`, `eliminar-formulas-obsoletas`, `formulas-mismapeo`, `formula-duplicados`, `formula-limpiar-duplicados`, `formula-huerfanos-con-sugerencias`, `auditoria-formulas` |
| 5952–6312 · 13851–14000 · 16547–17000 · 17641–18001 | **MPs: proveedores / abreviaturas / duplicados / unificar / sin-uso** | `mps-proveedores-status`, `mps-asignar-proveedor`, `mps-abreviaturas-audit/fix`, `mps-duplicados-stock`, `maestro-mps-unificar(-bulk)`, `mps-sin-uso`, `archivar-mps-sin-uso-bulk` |
| 6313–7200 · 12801–13093 · 24706–24948 | **MEEs (envases): abreviaturas / huérfanos / diagnóstico / fugas** | `mees-abreviaturas-audit/fix`, `mees-huerfanos-*`, `mees-diagnostico`, `maestro-mees-list`, `mee-fugas-check`, `investigar-mee`, `reconciliar-mee` |
| 6855–7198 | **Productos: volumen / presentaciones** | `producto-volumen-upsert`, `producto-presentaciones(-upsert)`, `presentaciones-sku-diagnostico` |
| 7727–8022 | **Migraciones PostgreSQL** | `/admin/migraciones-pg`, `aplicar-migraciones-pg` |
| 8079–8997 · 12030–12620 | **Influencers (marketing)** | `sync-influencers-excel`, `import-pagos-influencers-excel`, `influencers-limpieza/reset/bulk-import/cargar-29abr/hoy` |
| 8997–9100 · 19287–19844 · 20353 | **Mínimos / stock mínimos** | `auditar-minimos`, `aplicar-minimos`, `explicar-stock-min`, `sugerir-stock-minimos`, `aplicar-stock-minimos-sugeridos`, `stock-minimos` |
| 13433–13850 · 20976 | **Auditoría de catálogo** | `auditoria-catalogo` |
| 14432–15348 | **Cruce maestro (inventario↔maestro Excel / INCI)** | `cruce-maestro(-archivar/pares/reapuntar-formula)`, `reparar-stock-formula`, `diag-produccion`, `auto-unir-por-inci` |
| 14193–14431 | **MPs INCI sospechoso** | `mps-inci-sospechoso`, `/admin/mps-inci`, `mp-actualizar-inci` (23964) |
| 15877–16228 · 17461–17640 | **Lotes: stock atrapado / vencidos** | `lotes-stock-atrapado`, `marcar-lotes-vencidos`, `marcar-vencidos-bulk-todos` |
| 16229–16370 | **Diagnóstico producción global** | `diagnostico-produccion-global` |
| 16371–16546 | **Schema doctor / ficha MP** | `schema-doctor`, `mp-ficha/<codigo>` |
| 11350–11800 · 18393–19174 · 22161–23090 | **Auditorías kardex / lotes / producciones / FEFO** | `auditoria-lotes`, `auditoria-kardex-drift`, `auditoria-producciones-descuento`, `reconciliar-produccion-mp`, `producciones-inconsistentes`, `auditoria-fefo-descuento` |
| 22329–22706 · 25262 | **Reportes INVIMA / audit-trail** | `reportes/invima/lote/<material_id>/<lote>(/pdf)`, `reportes/audit-trail.csv`, `/admin/reportes-invima` |
| 23091–23598 · 26212–26441 | **mp-alcanza (factibilidad)** | `mp-alcanza-multi`, `cron-snapshot-mp-alcanza`, `mp-alcanza-historial` |
| 25827–27000 | **Programación vs Calendar / zombies / debug** | `programacion-vs-calendar`, `limpiar-produccion-zombies`, `productos-calendar-sin-formula`, `debug-calendar-producto`, `debug-consumo-mp` |
| 24153–24563 | **Forense / validación profunda** | `forensic-trazabilidad`, `validacion-profunda`, `completar-info-lote-bulk` |
| 27112–27465 | **Unidad base** | `auditoria-unidad-base`, `corregir-unidad-base-bulk` |

**Nota:** muchas rutas `/api/admin/...` (JSON) tienen una página `/admin/...` (HTML) gemela más abajo en el archivo. Si buscas la UI de una herramienta, busca el path sin `/api/`.
