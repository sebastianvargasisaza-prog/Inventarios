export const meta = {
  name: 'audit-que-mas-danado',
  description: 'Cazar qué más está dañado: números silenciosamente mal, datos que divergen de su fuente de verdad, unidades, agregaciones',
  phases: [
    { title: 'Cazar', detail: 'agentes por área buscan números/datos silenciosamente mal en el código real' },
    { title: 'Verificar', detail: 'verificación adversarial de cada hallazgo' },
    { title: 'Sintetizar', detail: 'confirmados priorizados + plan de fix' },
  ],
}

const CONTEXT = `
EOS · ERP Flask (SQLite local / PostgreSQL prod en Render · app.eossuite.com). Cosmética INVIMA, todo en español.
Stock = SUM(movimientos) canónico (_get_mp_stock). Fórmula→bodega vía _resolver_material_bodega (tiers+mp_formula_bridge).

QUÉ BUSCAMOS (la lente que acaba de revelar errores GRAVES · generaliza a TODO el sistema):
Esta semana encontramos una familia de bugs que producen NÚMEROS SILENCIOSAMENTE MAL (no crashean, "funcionan" pero
mienten · los peores para un ERP). Casos confirmados y ARREGLADOS (NO re-reportar):
- Fórmulas de PROD divergieron del Excel maestro: MP00116 'Epi-On' al 50-90% (el agua quedó codificada como el activo),
  MP00175 péptido a 0.5-1.5% (no estaba en el maestro) → compra Y descuento de producción inflados ~30-130x. (mig 272/273)
- Solicitudes de compra ~130x: el mismo producto planificado por 3 generadores (eos_plan + auto_plan cron + eos_proyeccion)
  y el motor SUMABA los planes solapados sin dedup. Fix prefer-Fijo (M49).
- Mapeo: stock cargado bajo código distinto al de la fórmula por INCI escrito distinto (Biosure/Solbrol, Pantenol). Bridges.
- Factibilidad mezclaba físico + en-camino (M6). Motor de compra contaba doble lotes iniciados / OC Pagada no acreditada (M47).

AHORA: con esa MISMA lente, ¿QUÉ MÁS está dañado? Buscá números que mienten en CUALQUIER módulo:
ARCHIVOS: inventario.py (kardex, conteo, MEE, recepción), programacion.py (stock canónico, resolver, abastecimiento,
deficit, FEFO), plan.py (factibilidad, _demanda_stock_gramos, generadores, presentaciones, volumen), auto_plan.py
(velocidad, demanda), brd.py (EBR, pesajes, rendimiento), compras.py (OC, precios, IVA, pendientes), admin.py
(diagnósticos, KPIs), financiero/gerencia (P&L, costos), calidad.py (KPIs, COA), marketing.py (KPIs, pagos),
clientes.py (B2B, aliados). database.py (MIGRATIONS, columnas DEFAULT date('now')).

PATRONES DE "NÚMERO MAL" a cazar:
1. DATOS que divergen de su fuente de verdad: formula_items vs Excel maestro (% / ingredientes), sku_mee_config /
   producto_presentaciones (volumen ml/g), precios maestro vs OC, Shopify snapshot vs vivo. ¿Hay otras tablas-espejo
   que pueden driftear en silencio?
2. UNIDADES mezcladas: g vs kg, ml vs g (densidad), % como fracción (0.05) vs número (5), $/kg vs $/g, ×1000 de más/menos.
3. AGREGACIÓN indebida: SUMAR cosas que no se deben (planes solapados, items duplicados de fórmula, multi-location Shopify,
   B2B contado 2×, OC pagada+recibida). ¿Falta dedup o un DISTINCT?
4. CACHE vs CANÓNICO: leer un stock_actual/contador cacheado en vez de SUM(movimientos) → drift (MP ya alineado · ¿MEE? ¿PT? ¿KPIs?).
5. FÓRMULA/BOM: items duplicados sin dedup (×N), % que no suman ~100 sin agua, un activo a >30% (agua mal codificada).
6. FILTRO que decide ≠ número que muestra (M5): la alerta/urgencia/color usa una métrica y el display otra.
7. SNAPSHOT viejo servido como vivo (M9), TZ UTC vs Colombia en "hoy" (M24), case en estado_lote.
8. PG drift que da número distinto a SQLite (GROUP BY arbitrario, CAST, redondeo).

Reportá SOLO con file:line del código real + el ESCENARIO concreto y el número equivocado que produce. NO edites (solo lectura).
`

const FINDINGS = {
  type: 'object', additionalProperties: false,
  properties: { findings: { type: 'array', items: {
    type: 'object', additionalProperties: false,
    properties: {
      title: { type: 'string' }, file: { type: 'string' }, line: { type: 'string' }, symbol: { type: 'string' },
      escenario: { type: 'string', description: 'qué dato/acción produce el número equivocado, concreto' },
      numero_mal: { type: 'string', description: 'qué número sale mal y aprox cuánto (ej. compra 2x, stock -, KPI inflado)' },
      severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3'] },
    }, required: ['title', 'file', 'escenario', 'severity'] } } },
  required: ['findings'],
}
const VERDICT = {
  type: 'object', additionalProperties: false,
  properties: {
    isReal: { type: 'boolean' }, confidence: { type: 'number' },
    severity: { type: 'string', enum: ['P0', 'P1', 'P2', 'P3'] },
    reason: { type: 'string' }, fix: { type: 'string' },
  }, required: ['isReal', 'reason'],
}

const DIMS = [
  { key: 'fuente-verdad-divergencia', prompt: 'Tablas-ESPEJO que pueden divergir de su fuente de verdad en silencio (como formula_items vs Excel maestro). Buscá: sku_producto_map / producto_presentaciones (volumen ml/g por SKU · ¿coincide con Shopify/lo cargado?), precios maestro_mps vs precio en OC, mp_lead_time_config, snapshots Shopify, mp_formula_bridge con destino fantasma o INCI equivocado. ¿Qué cálculo confía en una tabla-espejo que nadie revalida?' },
  { key: 'unidades', prompt: 'Mezclas de unidades que dan números 10-1000x mal: ml vs g (densidad ≠1), kg vs g, % como fracción (0.05) vs número (5), $/kg vs $/g, ×1000 de más/menos. Revisá _demanda_stock_gramos/_volumen_sku (ml→g), cálculos de costo (precio×cantidad), conversiones en abastecimiento/factibilidad/MEE. Da el factor.' },
  { key: 'formula-bom-integridad', prompt: 'formula_items: items DUPLICADOS (mismo producto+material_id en >1 fila → el motor suma ×N), % que no suman ~100% (sin contar agua/controla_stock=0), un activo NO-agua a >30% (probable agua mal codificada como el activo). _get_formulas (programacion.py) NO deduplica. ¿Qué fórmulas tienen suma de % anómala o duplicados?' },
  { key: 'agregacion-doble', prompt: 'SUMAR lo que no se debe (sin dedup/DISTINCT): planes solapados (ya prefer-Fijo · ¿quedan vías?), B2B contado como pedido Y como lote, OC pagada+recibida contada doble, Shopify multi-location sumado (debe ser ÁNIMUS solo o MAX), conteo cíclico doble ajuste, PT inflado por fase. Buscá GROUP BY que falte o LEFT JOIN anti-doble roto.' },
  { key: 'cache-vs-canonico', prompt: 'Leer un cache/contador en vez del SUM canónico → drift. MP ya está canónico; revisá MEE (movimientos_mee vs maestro_mee.stock_actual en TODAS las vistas/KPIs/gerencia), PT (stock_pt vs SUM), contadores de dashboard, KPIs de calidad/marketing/financiero que cacheen. ¿Qué número se lee de un cache que puede driftear?' },
  { key: 'mee-envases', prompt: 'MEE/envases (la otra mitad del inventario · menos auditada que MP): stock canónico SUM(movimientos_mee) con mee_codigo, sku_mee_config (qué envase por SKU · ¿bien?), cantidad de envase por lote (multi-volumen), mínimos MEE, descuento de envases al terminar producción. ¿Números de envase mal (compra/alerta/descuento)?' },
  { key: 'precios-costos-iva', prompt: 'Dinero: precio_kg vs precio_unitario (×1000), IVA ×1.19 aplicado/omitido inconsistente entre paths que escriben valor_total, costo de producción (precio × consumo), P&L/EBITDA (empresa case, egresos espejados con/sin IVA), márgenes. ¿Qué monto sale mal?' },
  { key: 'produccion-descuento', prompt: 'Descuento de MP/MEE al producir: doble descuento (iniciar+completar, hooks Kanban/calendario/directa), FEFO que consume vencido/cuarentena, snapshot de fórmula al iniciar vs fórmula viva (si editan la fórmula entre iniciar y completar), rendimiento/yield, reversión cruzada. ¿Se descuenta de más/de menos?' },
  { key: 'velocidad-plan', prompt: 'Velocidad de venta y generación de plan: velocidad sobreestimada (dias_creacion, es_regalo, B2B, multi-volumen) → cadencia corta → demasiados lotes; los 3 generadores y los crons (auto_plan_diario, job_proyeccion, self_heal re-habilita pese a pausa). ¿El plan se sigue inflando por algún lado tras prefer-Fijo?' },
  { key: 'pt-stock-shopify', prompt: 'Stock de producto terminado y Shopify: multi-location (solo ÁNIMUS LAB · no sumar), CC manda sobre Shopify (no doble contar), pipeline (≤7d), snapshot stale servido como vivo (M9), Available vs On-hand vs Committed. ¿El stock PT que ve Necesidades/factibilidad miente?' },
  { key: 'tz-fechas-regulatorias', prompt: 'DEFAULT date(\'now\') UTC en columnas de tablas de auditoría regulatoria (coa_resultados, capa_desviaciones, hallazgos, rotulo_limpieza, etc · ~17 en database.py) + INSERTs que omiten la fecha → registro con fecha UTC invisible a lecturas ancladas a Colombia -5h (INVIMA). Listá cada tabla+INSERT afectado (M24).' },
  { key: 'kpis-mienten', prompt: 'KPIs/indicadores que muestran un número MAL (no crashean): cuadros de mando (calidad, aseguramiento, marketing, financiero, gerencia), denominador 0 → None vs 0 (gris vs rojo falso), date-diff con julianday (SQLite-only) en PG, GROUP BY incompleto que en PG da arbitrario, conteos que no excluyen cancelado/anulado. ¿Qué KPI engaña?' },
  { key: 'race-cas', prompt: 'Race multi-worker (3 gunicorn) que corrompe números: transiciones estado check-then-act sin CAS (cancelar/liberar/anular/conteo/pago), over-payment AR/AP, idempotencia de recepción/OC. ¿Queda alguna que deje stock negativo/fantasma o doble registro?' },
  { key: 'pg-drift', prompt: 'Drift SQLite↔PG que cambia el número en prod: GROUP BY incompleto (PG arbitrario), CAST(SUBSTR) sobre texto con sufijo, alias en HAVING, "" vs \'\', date()/julianday en DML, columna fantasma en SELECT, redondeo. Cazá los que den número distinto entre local y prod.' },
  { key: 'descuento-formula-activo', prompt: 'M29/M38: producir/descontar desde fórmula descontinuada (activo=0) o con material_id inactivo; las 3 rutas de descuento (directa, programada, EBR) ¿todas filtran header activo? ¿Una fórmula con código inactivo rompe o descuenta mal?' },
]

phase('Cazar')
const lotes = await parallel(DIMS.map(d => () =>
  agent(
    `${CONTEXT}\n\nCazador especializado en: ${d.key}.\n${d.prompt}\n\nBuscá en el CÓDIGO REAL (Read/Grep) ` +
    `dónde se produce un NÚMERO silenciosamente MAL. file:line + escenario concreto + qué número sale mal. ` +
    `NO re-reportes lo ya arreglado (ver contexto). Si no hay nada real, findings vacío (mejor 0 que inventar).`,
    { label: `caza:${d.key}`, phase: 'Cazar', schema: FINDINGS, agentType: 'Explore' }
  ).then(r => (r && r.findings ? r.findings.map(f => ({ ...f, _dim: d.key })) : []))
))
const cand = lotes.filter(Boolean).flat()
const seen = new Set(); const uniq = []
for (const f of cand) {
  const k = ((f.file || '') + '|' + (f.title || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().slice(0, 48))
  if (seen.has(k)) continue; seen.add(k); uniq.push(f)
}
log(`${cand.length} candidatos · ${uniq.length} únicos`)

phase('Verificar')
const ver = await parallel(uniq.map(f => () =>
  agent(
    `${CONTEXT}\n\nVERIFICACIÓN ADVERSARIAL. Hallazgo:\n${f.title}\n${f.file}:${f.line || '?'} (${f.symbol || ''})\n` +
    `Escenario: ${f.escenario}\nNúmero mal: ${f.numero_mal || '?'}\n\nLEÉ el código real. isReal=true SÓLO si verificás ` +
    `que produce un número equivocado HOY (no ya arreglado, no falso positivo, no teórico). Si dudás → isReal=false. ` +
    `Evidencia file:line + fix concreto.`,
    { label: `ver:${(f.title || '').slice(0, 26)}`, phase: 'Verificar', schema: VERDICT, agentType: 'Explore' }
  ).then(v => (v ? { ...f, verdict: v } : null))
))
const conf = ver.filter(Boolean).filter(x => x.verdict && x.verdict.isReal)
log(`${conf.length} confirmados de ${uniq.length}`)

phase('Sintetizar')
const orden = { P0: 0, P1: 1, P2: 2, P3: 3 }
conf.sort((a, b) => (orden[a.verdict.severity || a.severity] ?? 9) - (orden[b.verdict.severity || b.severity] ?? 9))
const sint = await agent(
  `${CONTEXT}\n\nConfirmados:\n` + conf.map(c => `- [${c.verdict.severity || c.severity}] ${c.file}: ${c.title} · fix: ${c.verdict.fix || ''}`).join('\n') +
  `\n\nAgrupá por causa raíz, prioriza los que dan números MUY mal o tocan inventario/compra/dinero, y da un plan de fix ordenado.`,
  { label: 'sintesis' }
).catch(e => 'err:' + e)

return {
  candidatos: cand.length,
  confirmados: conf.map(c => ({ severity: c.verdict.severity || c.severity, area: c._dim, file: c.file, line: c.line,
    symbol: c.symbol, title: c.title, escenario: c.escenario, numero_mal: c.numero_mal, reason: c.verdict.reason, fix: c.verdict.fix })),
  sintesis: sint,
}
