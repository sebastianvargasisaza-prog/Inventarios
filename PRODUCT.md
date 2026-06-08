# Product

## Register

product

## Users

Equipo interno de **ÁNIMUS Lab + Espagiria Laboratorio** (fabricante colombiano de
cosmética/skincare, regulado INVIMA/GMP). Perfiles que lo usan TODO el día:
- **Planta** (operarios, dispensación, fabricación, envasado): pantallas densas,
  kanban, lotes, en piso de planta con luz fuerte → legibilidad es crítica.
- **Compras** (Catalina): solicitudes, OCs, proveedores, tablas largas.
- **Calidad** (Laura/Alejandro): registros regulados, EBR/MyBatch, liberaciones,
  desviaciones · cero ambigüedad, trazabilidad visible.
- **Dirección** (Sebastián CEO MD MPH, Alejandro): dashboards, decisiones rápidas.

Contexto: trabajo real, alta frecuencia, mucha data por pantalla. La interfaz
debe **desaparecer en la tarea**, no pedir atención.

## Product Purpose

ERP interno (EOS) que cubre inventario (kardex), compras, programación de
producción, calidad regulada (INVIMA/GMP/Part 11), CRM, RRHH y contabilidad.
Reemplaza hojas de cálculo y sistemas externos (MyBatch). Éxito = el equipo
confía en los números, ejecuta sin fricción y la app se siente **de laboratorio
serio**, no de "software interno improvisado".

## Brand Personality

Preciso · confiable · de laboratorio. Calma bajo carga de datos. Identidad ÁNIMUS:
**violeta** (`#6d28d9`) como color de marca + **ámbar** (`#fbbf24`, del logo) como
acento. Tres palabras: **impecable, técnico, sereno.**

## Anti-references

- **SaaS genérico de startup**: hero-métrica, azul-marino corporativo, plantilla
  de Stripe-clon sin identidad.
- **"Hecho por IA"**: eyebrows minúsculas en cada sección, grids de tarjetas
  idénticas, gradientes en texto, glassmorphism decorativo, emojis por todos lados.
- **De juguete**: colores sobre-saturados, bordes excesivamente redondeados,
  sensación infantil.
- **Editorial/marketing**: tipografía display gigante, scroll-driven — esto es una
  herramienta, no una landing.

## Design Principles

1. **La herramienta desaparece en la tarea.** Familiaridad ganada (Linear/Stripe/
   Notion): el usuario confía a la primera, no duda ante cada componente.
2. **Premium por precisión, no por decoración.** Se siente caro porque es
   impecable (jerarquía, espaciado, foco, sombras sutiles), no porque grite.
3. **Densidad con claridad.** Mucha data por pantalla está bien; la jerarquía y el
   aire la hacen legible, no las tarjetas vacías.
4. **Consistencia sobre sorpresa.** Mismo botón, mismo input, mismo patrón en las
   ~36 pantallas. El deleite es para momentos, no para cada página.
5. **Confianza regulada.** En pantallas de Calidad/INVIMA, el estado (liberado,
   cuarentena, OOS) debe leerse sin ambigüedad. La estética nunca compromete la
   trazabilidad.

## Accessibility & Inclusion

- **WCAG AA**: texto cuerpo ≥4.5:1, texto grande ≥3:1. Crítico en piso de planta
  con luz fuerte. Nada de gris claro "por elegancia".
- `prefers-reduced-motion`: toda animación con alternativa (crossfade/instantáneo).
- Estados de foco visibles (teclado) en todo control interactivo.
- No depender solo del color para estado regulado (icono/etiqueta además del color).
