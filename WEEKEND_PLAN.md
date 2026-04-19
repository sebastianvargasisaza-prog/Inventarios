# Plan de Implementación — Fin de Semana 2026-04-19
**Ventana:** Sábado 19 + Domingo 20 de abril 2026
**Repo:** GitHub → auto-deploy Render
**Regla:** No tocar el repo en producción hasta sábado con app offline o en ventana baja-actividad

---

## CHECKLIST DE EJECUCIÓN

### BLOQUE 0 — Pre-flight (antes de tocar código)
- [ ] Hacer backup manual de la DB en Render (descargar `/var/data/inventario.db`)
- [ ] Verificar que el repo local está en sync con main (`git pull`)
- [ ] Clonar fresh: `git clone [repo] /tmp/inv_weekend`
- [ ] Confirmar que los scripts patch estén actualizados

---

### BLOQUE 1 — Bugs críticos (SÁBADO MAÑANA — ~45 min)

**T0-1: Fix `recibir_oc()` tipo='ingreso' → tipo='Entrada'**
```python
# Archivo: api/index.py ~línea 3373
# Buscar:
(codigo, nombre, cantidad, 'ingreso', fecha,
# Reemplazar:
(codigo, nombre, cantidad, 'Entrada', fecha,
```
- [ ] Fix aplicado
- [ ] Verificado con grep: `grep -n "'ingreso'" api/index.py` → 0 resultados

**T0-2: Fix `generar_oc_automatica()` columna inexistente**
- [ ] Correr `patch_fase1.py` (ya contiene este fix + otros 8)
- [ ] Verificar: `grep -n "cantidad_solicitada" api/index.py` → 0 resultados

**T0-3: Proteger `/api/reset-movimientos`**
```python
# Agregar al inicio de reset_mov():
if 'compras_user' not in session or session.get('compras_user','') not in ADMIN_USERS:
    return jsonify({'error': 'No autorizado'}), 401
```
- [ ] Fix aplicado

---

### BLOQUE 2 — patch_fase1.py completo (SÁBADO MAÑANA — ~30 min)
- [ ] Correr: `python patch_fase1.py`
- [ ] Verificar salida: "9/9 patches aplicados"
- [ ] Test manual: abrir Compras, crear OC de prueba, verificar ver detalle OC con total

---

### BLOQUE 3 — Módulo Clientes (SÁBADO TARDE — ~3-4 horas)

**3a. Schema SQL (init_db)**
- [ ] Agregar 6 tablas nuevas a `init_db()`: clientes, pedidos, pedidos_items, stock_pt, despachos, despachos_items
- [ ] Agregar ALTER TABLE producciones para cliente_destino, sku, unidades
- [ ] Agregar seed data (CLI-001 ÁNIMUS Lab, CLI-002 Fernando Mesa con precios)
- [ ] Deploy prueba → verificar que init_db no rompe nada

**3b. API endpoints**
- [ ] `GET/POST /api/clientes`
- [ ] `GET/PUT /api/clientes/<id>`
- [ ] `GET /api/clientes/<id>/stats` (facturación acumulada)
- [ ] `GET/POST /api/pedidos`
- [ ] `GET/PATCH /api/pedidos/<numero>`
- [ ] `GET/POST /api/stock-pt`
- [ ] `POST /api/despachos`

**3c. Integración con producción**
- [ ] Modificar `handle_produccion()` para aceptar `cliente_destino`, `sku`, `unidades`
- [ ] Auto-crear entrada en `stock_pt` cuando viene cliente_destino
- [ ] Agregar checkbox + campos en formulario de producción (Dashboard HTML)

**3d. Módulo HTML (CLIENTES_HTML)**
- [ ] Tarjeta en HUB_HTML: "👥 CLIENTES"
- [ ] CLIENTES_HTML con 4 tabs: Dashboard | Clientes | Pedidos | Stock PT
- [ ] Ruta `/clientes` → Response(CLIENTES_HTML)

---

### BLOQUE 4 — Testing integrado (DOMINGO MAÑANA — ~2 horas)

**Flujo A — Ciclo completo Compras:**
- [ ] Crear solicitud desde `/solicitudes`
- [ ] Aprobar desde Compras → generar OC
- [ ] Marcar OC como recibida → verificar que stock MP sube en Dashboard

**Flujo B — Ciclo completo Producción → Clientes:**
- [ ] Registrar producción de TRX con `cliente_destino=Fernando Mesa`, 500 unidades
- [ ] Verificar entrada en stock_pt
- [ ] Crear pedido para FM con 500 unidades TRX
- [ ] Marcar pedido despachado → stock_pt baja a 0

**Flujo C — Verificar que nada se rompió:**
- [ ] Dashboard carga sin errores
- [ ] Inventario MP muestra stocks correctos
- [ ] MEE carga correctamente
- [ ] Fórmulas y producción sin cambios

---

### BLOQUE 5 — Deploy y validación final (DOMINGO TARDE)
- [ ] `git add -A && git commit -m "Sprint 1: bugs T0, Compras mejorado, módulo Clientes"`
- [ ] `git push origin main` → esperar auto-deploy Render (~2 min)
- [ ] Verificar app en producción: todos los módulos cargan
- [ ] Verificar con Alejandro que el sistema funciona

---

## ARCHIVOS DE REFERENCIA

| Documento | Contenido |
|---|---|
| `patch_fase1.py` | 9 patches Compras listos para correr |
| `COMPRAS_ROADMAP.md` | Diseño completo 6 fases Compras |
| `CLIENTES_MODULO.md` | SQL, API, HTML del módulo Clientes |
| `ANALISIS_ECOSISTEMA.md` | Todos los bugs y brechas documentados |
| `HOLDING_ECOSISTEMA.md` | Roadmap estratégico completo HHA Group |

---

## NOTAS TÉCNICAS

**Bash paths para el fin de semana:**
- Repo en producción: `/tmp/inv_weekend/api/index.py`
- DB backup: descargar desde panel Render antes de empezar
- Test local: `python api/index.py` (port 5000)

**Orden de commit recomendado:**
1. Primero Bugs T0 + patch_fase1 → commit individual → push → verificar en prod
2. Luego Clientes (schema + API) → commit → push → verificar
3. Luego Clientes (HTML + UI) → commit → push → verificar final

**Si algo se rompe:**
```bash
git revert HEAD  # revierte último commit
git push origin main  # Render redeploya versión anterior
```
