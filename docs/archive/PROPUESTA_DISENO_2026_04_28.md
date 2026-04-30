# Propuesta de mejoras de diseño — 2026-04-28

> Honestidad técnica: el sistema funciona muy bien (245 tests, 19 módulos) pero el diseño visual creció orgánicamente. Cada módulo tiene su propio look. Esto es lo que vale la pena mejorar — y lo que NO.

---

## ❌ Problemas reales detectados (priorizado)

### 1. **Inconsistencia visual entre módulos** (alto impacto, bajo esfuerzo)
Cada blueprint usa su propia paleta y estilos:
- `dashboard_html` (Planta) → tonos beige/marrón corporativo
- `marketing_html` → indigo/violeta neón
- `animus_html` → dorado + crema
- `espagiria_html` (nuevo) → cian/teal
- `comunicacion_html` (nuevo) → ámbar
- `gerencia_html` → mix grises sin identidad clara
- `financiero_html` → marrón/crema (similar a planta pero más oscuro)

**Resultado:** cuando un usuario salta de un módulo a otro, parece que cambió de aplicación. Botones, badges, cards, tablas se ven distintos.

**Solución sugerida:** sistema de tokens compartidos en un `static/styles/tokens.css` con variables CSS:
```css
:root {
  --color-primario: #1e293b;
  --color-acento-marca: #d4af37;     /* Animus dorado */
  --color-acento-planta: #2B7A78;    /* Espagiria teal */
  --color-acento-comercial: #818cf8; /* Marketing indigo */
  --bg-card: #1e293b;
  --bg-input: #0f172a;
  --border: #334155;
  --text-primary: #e2e8f0;
  --text-muted: #94a3b8;
  --radius: 10px;
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
}
```
Y refactorizar gradualmente los HTML para usar esas variables. **No urgente** — el sistema es funcional.

### 2. **Mobile no responsive** (alto impacto en uso real)
La mayoría de módulos están pensados para desktop. Si Luz Adriana o Catalina abren desde el celular, las tablas se desbordan, los modales son enormes, los botones se solapan.

**Solución:** auditoría visual con Chrome DevTools en mobile, y agregar `@media (max-width: 768px)` en cada template para:
- Tablas con scroll horizontal o cards stack
- Modales de ancho 95vw en mobile
- Botones full-width en mobile
- Tabs en scroll horizontal

Esto vale la pena especialmente para el **módulo Comunicación** (Luz lo va a usar desde el celular cuando esté en planta).

### 3. **No hay búsqueda global** (medio impacto)
Si Sebastián quiere buscar "OC-2026-0033" no sabe en qué módulo está. Lo mismo para influencers, clientes, fórmulas, MPs.

**Solución:** una barra de búsqueda en el header del hub `/modulos` que llame a un endpoint `/api/search?q=...` que consulte todas las tablas relevantes y devuelva resultados agrupados:
- "OC-2026-0033 → Compras → Pagada"
- "MP00245 → 1,2-Hexanediol → Inventario"
- "CLI-002 → Fernando Mesa → Clientes"

Tipo Spotlight/Cmd+K. No urgente pero gran QoL.

### 4. **Notificaciones dispersas** (medio impacto)
Hay alertas en gerencia, alertas en marketing, alertas en planta, alertas en espagiria — cada una en su panel. Sebastián tiene que entrar a cada módulo para ver qué urge.

**Solución:** centro de notificaciones en el hub:
- Endpoint `/api/notificaciones/centro` que agregue alertas críticas de todos los módulos
- Badge rojo con número en el header de `/modulos`
- Click → modal con TODO lo crítico de hoy ordenado por severidad

### 5. **Navegación inconsistente** (bajo impacto pero molesta)
Algunos módulos tienen breadcrumb "← Volver al Hub", otros un botón "Módulos" arriba a la derecha, otros nada. Tab bars: algunos al tope, otros laterales.

**Solución:** un componente `<header>` común que se incluya por servidor en todos los templates, con:
- Logo HHA Group siempre arriba a la izquierda
- Breadcrumbs (Hub / Módulo / Sub-tab)
- Avatar usuario + logout a la derecha
- Notificaciones (campana con badge)

### 6. **Modales ad-hoc** (bajo impacto)
Cada módulo implementa sus propios modales con su propio CSS. Algunos cierran al click fuera, otros no. Algunos tienen botón X, otros no. El UX es inconsistente.

**Solución:** función JS global `openModal({title, body, actions})` reutilizable.

---

## ✅ Cosas que SÍ funcionan bien (no tocar)

- **Color en KPI cards** — los gradientes con colores semánticos (rojo crítico, verde OK, ámbar pendiente) son útiles y consistentes en cards
- **Iconos emoji** — funcionan bien sin requerir librerías (FontAwesome, etc.). Mantener.
- **Tablas con scroll** — la mayoría tienen `overflow-x: auto`, no se rompen
- **Login flow** — claro, simple, sin sobre-ingeniería
- **Hub `/modulos`** — categorización por área (Productivo / Comercial / Coordinación / Administrativo) es buena UX

---

## 🎯 Qué recomiendo hacer (en orden)

### Sprint 1 (4-6 horas, impacto inmediato visible)
1. **Sistema de tokens CSS unificado** — crear `static/css/tokens.css` y refactorizar **solo los 3 módulos nuevos** (Espagiria, Comunicación, panel admin). Los demás van quedando con su look actual hasta que toques cada uno.
2. **Componente header común** — incluido server-side, breadcrumbs + avatar + campana notificaciones.

### Sprint 2 (6-8 horas, impacto operacional)
3. **Mobile responsive en Comunicación + Espagiria** — son los que Luz y Sebastián usarán desde celular durante el comité semanal y supervisión.
4. **Centro de notificaciones** — agregar alertas críticas de todos los módulos en una sola vista.

### Sprint 3 (4-6 horas, nice-to-have)
5. **Búsqueda global Cmd+K** — un endpoint que cruce todas las tablas y un modal tipo Spotlight.
6. **Modales globales reutilizables**.

### Sprint 4 (refactor lento, no urgente)
7. **Refactor gradual de los 16 HTML restantes** para usar tokens — uno por uno cuando toques cada módulo por otro motivo. NO hacer un big-bang refactor, alto riesgo.

---

## ❓ Mi recomendación honesta

El sistema **funciona muy bien para el tamaño actual del equipo (8-12 personas)**. La inconsistencia visual NO te está costando productividad — todos saben usar sus módulos. Lo que SÍ te está costando es:

1. **Mobile no responsive** → Luz pierde tiempo cuando supervisa en planta
2. **No hay búsqueda global** → tú gastas 30 segundos buscando una OC específica varias veces al día
3. **Notificaciones dispersas** → no tienes una vista única de "qué urge hoy"

Los demás son nice-to-have estéticos.

**Mi voto: hacer Sprint 1 + Sprint 2 cuando tengas tiempo libre (1-2 días concentrados).** El resto puede esperar y el tiempo se invierte mejor en construir más features (Gap 1 ✓, Comunicación, etc.).

---

*Estructura propuesta sin tocar código todavía. Espero tu visto bueno antes de empezar Sprint 1.*
