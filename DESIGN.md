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
