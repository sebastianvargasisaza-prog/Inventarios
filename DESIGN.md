# Design

Sistema visual de EOS. Fuente única: `api/static/cortex.css` (tokens `--cx-*` +
clases `.cx-*`). Dirección: **técnico-premium** (Linear/Stripe/Notion) conservando
la identidad ÁNIMUS violeta + ámbar. Premium por precisión, no por decoración.

## Theme

Light por defecto (uso diario en piso de planta con luz fuerte · legibilidad).
Dark disponible vía `data-theme="dark"`. Estrategia de color: **Restrained** —
neutrales + violeta como acento de acciones/estado, ámbar como acento secundario
(marca). El color no decora; señala.

## Color (tokens `--cx-*`)

- **Marca**: violeta `--cx-primary #6d28d9` (light/dark/pale/soft), ámbar
  `--cx-accent #fbbf24` (del logo).
- **Superficie**: bg limpio neutro-frío con un susurro de violeta (no crema cálida
  "default de IA"); `--cx-card #fff`; hairlines `--cx-hairline` para bordes casi
  invisibles (premium > bordes duros).
- **Texto**: rampa stone `--cx-text`→`--cx-text-faint`. Cuerpo ≥4.5:1 (WCAG AA).
- **Semánticos**: success/warn/danger/info + variantes `-pale`. Estado regulado
  (liberado/cuarentena/OOS) nunca depende solo del color → icono/etiqueta también.

### RELLENO vs TEXTO · la regla que más se incumple (26-jul-2026)

Un color de relleno y **el mismo color como texto necesitan tokens DISTINTOS**, porque al
invertir el tema tiran en direcciones opuestas: el relleno se queda oscuro para que el texto
blanco encima se lea, y el texto tiene que aclararse para leerse sobre el fondo oscuro. Con un
solo token, el violeta como texto daba **2,06:1** sobre la tarjeta oscura (ilegible).

| en `background:` / `border:` | en `color:` |
|---|---|
| `--cx-primary` | `--cx-primary-text` |
| `--cx-success` | `--cx-success-text` |
| `--cx-danger` | `--cx-danger-text` |
| `--cx-info` | `--cx-info-text` |
| `--cx-warn` | `--cx-warn-text` (el ámbar puro sobre blanco es 2,15:1) |

Los 5 pares están medidos: pasan AA (4,5:1) en tema claro **y** en oscuro.

**`color:#fff` se queda literal.** El texto blanco sobre un relleno de color no depende del tema;
mandarlo a `--cx-card` lo vuelve oscuro sobre oscuro en el tema oscuro. `--cx-card` es una
SUPERFICIE: va en `background`, nunca en `color`.

**Dónde `var()` NO funciona** (ahí el literal es correcto): atributos SVG (`fill=`/`stroke=`),
`<meta name="theme-color">`, comparaciones en JS y colores de canvas/Chart.js.

**En `api/blueprints/` se escribe con respaldo**: `color:var(--cx-text-mute, #64748b)`. Ahí viven
los rótulos y los imprimibles regulados, y algunos no enlazan `cortex.css` — el respaldo garantiza
que un documento impreso nunca pierda color.

**Esto lo vigila un test**, no la buena memoria: `tests/test_deuda_diseno_no_crece.py` cuenta los
colores hardcodeados y falla si suben (la regla estaba escrita desde hace meses y se incumplió
8.077 veces). Si migrás y el número baja, **bajá el techo** en el test para fijar la mejora.

### Las 3 vistas del día comparten UN renderizador (26-jul-2026)

Envasado, Fabricación y Acondicionamiento usan `ordenesRenderLista` / `ordenChipEstado` /
`ordenKpi` (`dashboard_html.py`). Nacieron como tres tablas distintas escritas en momentos
distintos, y así es exactamente como aparecieron las cuatro paletas de grises: cada pantalla se
inventó la suya. Una pieza compartida es lo que impide que vuelvan a divergir.

- El **verbo del chip** sigue a la fase (`ENVASANDO` / `FABRICANDO` / `ACONDICIONANDO`) y el
  rótulo del KPI también (`Unidades envasadas` vs `acondicionadas`): se pasa `fase` como 3er
  argumento, no se duplica la función.
- **Fabricación conserva su tabla** a propósito: sus datos son números que se comparan entre sí
  (teórica / producida / aprobada) y una tabla alinea columnas mejor que una tarjeta. Comparte los
  KPIs y los chips, no el layout. La forma sigue al dato, no a la uniformidad.
- Lo que cada fila tiene que responder sin abrir el legajo: **cuánto avanzó** (3/5 pasos),
  **qué sale** (282 × 30 ml), **hace cuánto** (ámbar a los 3 días, rojo a los 6) y **quién**.

## Typography

- Familia única: **Inter** (`--cx-font`) + JetBrains Mono para datos crudos/código.
- **Números tabulares** (`font-variant-numeric: tabular-nums`) en KPIs, tablas y
  montos → columnas alineadas, señal técnica de precisión.
- Escala fija (no fluida) razón ~1.2; jerarquía por peso (400/500/600/700/800) +
  escala. Headings letter-spacing negativo (-0.4px display). Sin display fonts en
  labels/botones/datos.

## Motion

- 150–200ms, curva **ease-out** (`--cx-ease` cubic-bezier). Transmite estado
  (hover/focus/active/loading), no decora. Sin secuencias de carga orquestadas.
- `prefers-reduced-motion`: crossfade/instantáneo. Obligatorio.

## Components (`.cx-*`)

Cada control interactivo: default · hover · focus-visible · active · disabled ·
loading. Vocabulario consistente en las ~36 pantallas: mismo botón, input, card,
chip, tab, badge, KPI. Foco visible único (`--cx-ring`). Skeletons para carga
(no spinners). Empty states que enseñan. Densidad permitida (tablas largas).

## Layout

- Grid responsive sin breakpoints: `repeat(auto-fit, minmax(...))`.
- Responsive estructural (colapsar sidebar, tabla con scroll, stack en móvil) — no
  tipografía fluida. Escala de espaciado 8pt (`--cx-s1`..`--cx-s8`). Z-index
  semántica (base<sticky<dropdown<modal<toast<tooltip).

## Anti-patterns (no hacer)

Side-stripe borders decorativos, gradient text, glassmorphism por defecto,
hero-métrica, grids de cards idénticas, eyebrows min en cada sección, modal como
primera opción. Ver PRODUCT.md anti-references.
