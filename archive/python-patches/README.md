# ⚠ ARCHIVE — NO EJECUTAR EN PRODUCCIÓN

Estos scripts fueron usados durante el bootstrap del sistema (15-abr-2026)
para cargar inventario inicial, fórmulas y migraciones. **No están diseñados
para ser idempotentes** y son la causa documentada del **incidente de doble
carga** que detectamos el 27-abr-2026 (3× sobre-inflado del kardex).

## Por qué NO correrlos

- ❌ Sin verificación de "ya cargado" — `INSERT INTO movimientos` directo
- ❌ Sin lock contra ejecución concurrente
- ❌ Sin audit log de quién corrió qué y cuándo
- ❌ Path hardcoded (`C:\Users\sebas\OneDrive\Documentos\...`) que no aplica
  al servidor en Render
- ❌ Schema asumido puede ser legacy

Si alguien los ejecuta contra producción ahora:
- Se duplicarán entradas existentes
- Se inflará el stock total
- El sistema reportará anomalías en `/admin → 🔥 Monitor anomalías`
- Se requerirá un nuevo reset+replay para limpiar

## El flujo correcto para cargar inventario hoy

1. **Carga incremental** (recepción normal): vía `/planta` → "Recepciones"
   o vía `/compras` → aprobar OC → recepción física. Estos generan
   movimientos con `numero_oc` y `operador` correctos.

2. **Reseteo total** (solo cuando hay incidente probado): vía
   `/admin → Auditar Inventario → Reset+Replay`. Pide:
   - Token textual exacto
   - Backup automático previo verificado
   - Excel verde como fuente de verdad
   - Snapshot pre-reset descargado fuera de Render

3. **Auditoría continua**: `/admin → 🔥 Monitor anomalías` corre las
   invariantes (BURST, MULTI_ENTRADAS, SIN_OC_RATIO, STOCK_ANOMALO) y
   alerta antes de que la duplicación sea masiva.

## Scripts que vive aquí (todos legacy / one-shot)

```
patch_*.py          — patches al index.py monolítico (pre-blueprints)
generar_fase*.py    — generadores SQL de las fases iniciales
cargar_*.py         — cargadores Excel→SQLite del bootstrap
fix_*.py            — fixes one-shot ya aplicados al schema
run_refactor_*.py   — orquestadores del refactor en fases
extract_*.py        — extracción de datos legacy
analizar_excels.py  — análisis pre-import
```

Todos fueron **archivados el 27-abr-2026** (commit `02288db`).

## Si necesitas referencia histórica

Lee el código pero NO LO EJECUTES. Para entender qué hacía cada uno:

```bash
git log --all --pretty=format:"%h %s" -- archive/python-patches/<archivo>
```

Si necesitas el comportamiento de alguno (ej. cargar un Excel de fórmulas
nuevo), discútelo primero — la lógica nueva debe ir vía endpoint admin
con audit log.

---
**Mantenedor:** equipo HHA Group
**Última revisión:** 2026-04-27
