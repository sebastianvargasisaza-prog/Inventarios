# Decisión: Técnica vs Inventario — dominio de fórmulas

> Punto #14 del roadmap. Hay 2 tablas que conceptualmente representan
> "fórmula" en el sistema y eso confunde. Esta es la propuesta para
> consolidar sin romper nada.

---

## El problema actual

| Tabla | Owner | Contiene | Usado por |
|---|---|---|---|
| `formulas_maestras` | técnica.py | codigo, nombre, version, tipo, estado, descripcion | Hub Hernando: crear fórmula nueva, versionar, INVIMA |
| `formula_headers` + `formula_items` | inventario.py / programacion.py | producto_nombre, material_id, material_nombre, porcentaje, cantidad_g_por_lote | Producción real: calcular déficit MPs, descontar stock |

**No se cruzan.** Cuando Hernando crea una fórmula nueva en `/tecnica`, NO aparece en producción hasta que alguien la replique en `formula_headers` manualmente. Errores frecuentes.

---

## Veredicto arquitectónico

**Mantener las dos tablas, pero con dominios claros y un puente automático.**

### Domain ownership

```
formulas_maestras (técnica)        formula_headers + items (inventario)
═══════════════════════════════    ═══════════════════════════════════
RESPONSABLE: Hernando              RESPONSABLE: Programación
PROPÓSITO:   Documento legal       PROPÓSITO:   BOM productivo
FUENTE DE:   versionado, INVIMA    FUENTE DE:   producir, descontar stock
```

- **Técnica** = la "definición intelectual" de la fórmula (registro INVIMA, versionado, cambios documentados, aprobación QA, estado regulatorio Vigente/Suspendida)
- **Inventario** = la "receta de planta" (% de cada MP, peso por lote, fases, orden de adición)

### Puente automático: `mp_formula_bridge`

Tabla que relaciona ambas:
```sql
CREATE TABLE mp_formula_bridge (
  formula_maestra_id INTEGER,  -- FK a formulas_maestras
  producto_nombre TEXT,        -- referencia a formula_headers
  version_aprobada TEXT,       -- version que está en producción
  fecha_promovida TEXT,
  promovido_por TEXT,
  PRIMARY KEY (formula_maestra_id)
);
```

**Workflow:**
1. Hernando crea fórmula en `formulas_maestras` (estado=Borrador) — solo definición
2. QA revisa y aprueba — estado=Vigente
3. Hernando hace click "Promover a producción" → endpoint `POST /api/tecnica/formulas/<id>/promover`
4. El endpoint:
   - Crea/actualiza el `formula_headers` con el `producto_nombre` correspondiente
   - Inserta en `mp_formula_bridge` la relación
   - Versionado_aprobada = la versión que se promovió
5. Programación usa `formula_headers` normalmente (no cambia su lógica)
6. Si Hernando cambia la fórmula maestra, el `bridge` muestra que hay versión nueva pero la productiva sigue siendo la anterior hasta nueva promoción explícita

### Beneficios

- Producción NUNCA usa fórmula no aprobada por error
- Cambio en `formulas_maestras` no rompe producciones programadas
- BPM cumplido: trazabilidad de qué versión se usó en cada lote
- Decisión sigue siendo Hernando (no programación)

---

## Roadmap de implementación

**Fase 1 (1-2h):** Schema migration #42
- Crear `mp_formula_bridge`
- Backfill: para cada `formula_headers` existente, intentar match con `formulas_maestras` por nombre similar; si no hay, crear stub

**Fase 2 (2-3h):** Endpoint promover
- `POST /api/tecnica/formulas/<id>/promover`
- Body: `{producto_nombre, items: [{material_id, %, fase}]}`
- Crea `formula_headers` + items + bridge

**Fase 3 (1-2h):** UI en `/tecnica`
- Botón "Promover a producción" en cada fórmula vigente
- Modal: selecciona producto destino + ajusta items finales

**Fase 4 (1h):** Validación en programación
- En `_get_formulas`, agregar JOIN con `mp_formula_bridge` para ver versión aprobada
- Mostrar warning si hay versión nueva esperando promoción

**Total estimado: 5-8h cuando se implemente.**

---

## Por ahora (decisión interim)

NO implementamos esto en TANDA 4. Lo dejamos documentado y atacamos cuando:
- Hernando opere `/tecnica` activamente (hoy es esporádico)
- Tengamos primer caso real de "cambié fórmula maestra y producción quedó desincronizada"

**Lo que SÍ hacemos en esta tanda:** documentar la decisión + agregar el "Director Técnico" como label aclaratoria + dejar las dos tablas funcionar paralelas como hoy.
