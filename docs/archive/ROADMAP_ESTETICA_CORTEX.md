# 🎨 Roadmap de unificación estética — Cortex Labs

**Para:** Sebastián
**Fecha:** Abril 2026
**Diagnóstico:** Cortex Labs tiene branding pulido en `/modulos`, `/login`,
`/home` y `/hub`, pero los **18 módulos internos** mantienen estilos viejos
inconsistentes (verde teal Espagiria, naranja, azul, etc.) que rompen la
sensación de "producto único".

---

## TL;DR

| Sprint | Alcance | Tiempo | Hecho |
|---|---|---|---|
| 0 (HOY) | Hub `/modulos` con SVG icons + logo único | 30 min | ✅ |
| 0 (HOY) | Helper `branding.icon()` con 26 iconos line-style | 30 min | ✅ |
| 1 | Top-3 módulos: Planta + Compras + Calidad | 4-6 h | ⏸ |
| 2 | Tier-2: Técnica, Solicitudes, Programación, Recepción | 4-6 h | ⏸ |
| 3 | Tier-3: Marketing, ÁNIMUS, Espagiria, Tesorería, RRHH, Compromisos, Clientes, Maquila | 6-8 h | ⏸ |
| 4 | Wallpaper paleta + tipografía global + dark mode | 4 h | ⏸ |

**Total:** ~3 días distribuidos. Empuja en cada sprint, no big-bang.

---

## ✅ Lo que ya está hecho (Sprint 0)

### `/modulos` (hub principal de navegación)
- Logo Cortex Labs en header (no duplicado)
- 16 emojis reemplazados por **SVG monocromos violeta** (Heroicons line-style)
- Saludo personalizado: *"Hola Sebastián · Selecciona un módulo..."*
- Tarjetas más limpias, sin sobrecargas

### `/login` `/home` `/hub` (entradas)
- Branding violeta consistente
- Logo cerebro/red neuronal
- Footer con copyright HHA Group

### `api/branding.py` (helper reutilizable)
- 26 iconos SVG inline disponibles via `branding.icon('planta', size=32, color='#6d28d9')`
- Lista: hoy, gerencia, planta, calidad, tecnica, compras, solicitudes,
  clientes, marketing, animus, espagiria, tesoreria, rrhh, compromisos,
  recepcion, maquila, dashboard, bodega, produccion, programacion,
  modulos, volver, logout, config, campana, lupa
- Función `icon(name, size, color, stroke_width, css_class)`

---

## 🔨 Sistema de diseño Cortex Labs

### Paleta principal

| Token | Hex | Uso |
|---|---|---|
| `--cx-primary` | `#6d28d9` | Brand violeta — botones primarios, headers |
| `--cx-primary-light` | `#a78bfa` | Hover, acentos |
| `--cx-primary-pale` | `#f5f3ff` | Fondos sutiles |
| `--cx-primary-dark` | `#4c1d95` | Textos sobre fondo claro |
| `--cx-bg` | `#f5f4f0` | Fondo página (warm gray) |
| `--cx-card` | `#ffffff` | Tarjetas |
| `--cx-text` | `#1c1917` | Texto principal (stone-900) |
| `--cx-text-mute` | `#78716c` | Texto secundario (stone-500) |
| `--cx-border` | `#e7e5e4` | Bordes (stone-200) |
| `--cx-success` | `#15803d` | OK / Tesorería |
| `--cx-warn` | `#f59e0b` | Atención |
| `--cx-danger` | `#dc2626` | Error / crítico |

### Tipografía

- **Sistema:** `-apple-system, "Segoe UI", BlinkMacSystemFont, sans-serif`
- **Headings:** weight 700-800, letter-spacing -0.3px
- **Body:** weight 400-500, line-height 1.5
- **Mono:** Consolas (códigos MP, lotes, montos)

### Iconografía

- **Library:** Heroicons line-style (vía `branding.icon()`)
- **Tamaño default:** 24px en cards, 32px en headers, 16px en botones
- **Stroke:** 1.6 (más fino que default)
- **Color:** `currentColor` (hereda del padre — mantiene consistencia con texto)

### Componentes esperables

| Componente | Spec |
|---|---|
| Header de módulo | Bg blanco, padding 18px 28px, logo Cortex 32x32 + nombre módulo + Volver a Módulos + Usuario |
| Card | Border 1px stone-200, radius 12px, padding 16px, hover -2px translate + shadow |
| Botón primario | Bg violeta, white text, padding 10px 20px, radius 8px, weight 600 |
| Botón secundario | Bg transparente, border violeta, text violeta |
| Tab | Border-bottom 2px violeta cuando activa, sin fondo |
| KPI | Bg blanco, padding 16-24px, número grande 24-32px, label uppercase 11px |
| Tabla | Header bg `#f5f3ff` color violeta, rows alterna `#fafaf9`, border stone-200 |
| Modal | Bg blanco, border-radius 14px, max-width 600-900px, shadow grande, backdrop blur |

---

## 📋 Sprint 1 — Top 3 módulos (4-6 horas)

Los más visitados. Toca los archivos:

### 1. `/inventarios` (Planta) → `api/templates_py/dashboard_html.py`

**Cambios:**
- Header verde teal viejo → header blanco con logo Cortex Labs + título "Planta" + botón "← Módulos"
- Subtítulo: "Espagiria Laboratorios · Control de materias primas"
- Tabs (Dashboard, Bodega MP, Bodega MEE, Producción, Calidad, Programación):
  - Reemplazar emojis por `branding.icon('dashboard')`, `icon('bodega')`, etc.
  - Color activo: violeta `#6d28d9` (no verde)
- KPI cards verde teal → blanco con border violeta
- Botón "Actualizar" naranja → violeta primario

### 2. `/compras` → `api/templates_py/compras_html.py`

**Cambios:**
- Header → consistente con Planta
- Wizard de OC (multistep) → botones violeta
- Lista de OCs → tabla con estilo Cortex
- Estados (Borrador/Pendiente/Pagada) → chips de color con la paleta nueva
- Botón "Nueva OC" → primario violeta

### 3. `/calidad` → `api/templates_py/calidad_html.py`

**Cambios:**
- Header consistente
- Cards de NCs → estilo Cortex
- Cuarentena/Aprobado → chips colores nueva paleta

**Aporte global del Sprint 1:** crear macro `_render_module_header(modulo, subtitulo, icono)`
en `api/branding.py` para que los próximos módulos sean copy-paste.

---

## 📋 Sprint 2 — Tier 2 módulos (4-6 horas)

| Módulo | Archivo |
|---|---|
| Dirección Técnica | `tecnica_html.py` |
| Solicitudes | `solicitudes_html.py` |
| Programación | parte de `dashboard_html.py` |
| Recepción | `recepcion_html.py` |

Misma estrategia que Sprint 1, copiando el macro de header.

---

## 📋 Sprint 3 — Tier 3 módulos (6-8 horas)

| Módulo | Archivo |
|---|---|
| Marketing | `marketing_html.py` |
| ÁNIMUS Lab | `animus_html.py` |
| Espagiria | (panel asistente) |
| Tesorería | `tesoreria_html.py` (recién hecho, ya casi consistente) |
| RRHH | `rrhh_html.py` |
| Compromisos | `compromisos_html.py` |
| Clientes | `clientes_html.py` |
| Maquila | `salida_html.py` (oculto del hub pero código vive) |

---

## 📋 Sprint 4 — Refinamiento global (4 horas)

- **Tipografía:** importar Inter o Plus Jakarta Sans (Google Fonts) para más sofisticación
- **Dark mode:** toggle en header → CSS variables permite cambio instantáneo
- **Animaciones:** transitions suaves al cambiar de tab/sección
- **Empty states:** ilustraciones simples para "sin datos"
- **Loading skeletons:** en lugar de spinners

---

## ⚠️ Decisiones que necesito de Sebastián

1. **¿Cuándo arrancamos Sprint 1?** ¿Esta semana o cuando termine Brecha #11 (backup)?
2. **¿Mantenemos el verde de Tesorería?** (es código de color para "dinero/OK").
   Sugerencia: sí, pero el verde Cortex (`#15803d`) en lugar del Espagiria viejo.
3. **¿Logo HHA Group lo dejamos en algún lado?** Ya no aparece — propongo dejarlo solo
   en el footer y en `/home` como "by HHA Group" como hoy.
4. **¿Dark mode?** Se ve premium pero es 4 horas extra. ¿Vale ahora o después de SaaS launch?
5. **¿Tipografía custom?** Inter / Plus Jakarta cuestan 0 (Google Fonts) pero
   agregan ~30KB primer load. Recomiendo sí.

---

## 🎯 Después del Roadmap Estético

Cuando los 18 módulos tengan branding Cortex Labs unificado, la app se siente
**1 producto** y no "19 módulos pegados". Eso es lo que distingue un Odoo
clónico de un SaaS premium vendible.

Estimación combinada: **~22 horas dev** distribuidas en 4 semanas (5-6 h/sem).

Mi recomendación: **Sprint 1 esta semana mientras el deploy del backup runbook
(Brecha #11) corre en paralelo.**
