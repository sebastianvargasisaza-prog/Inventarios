# SESSION_LOG · Bitácora de sesiones IA

> Archivo por sesión: `YYYY-MM-DD.md` (si hay varias en el mismo día,
> sufijo `-am`/`-pm` o número incremental).

## Propósito

Resolver el problema de "memoria entre sesiones" de los agentes IA.
Cada sesión que toca código debe escribir aquí un resumen ANTES de
cerrar (hook epilogue obligatorio):

1. **Qué pidió el usuario** — request original textual
2. **Qué cambió en el código** — archivos + síntesis del cambio
3. **Qué reglas nuevas se decidieron** (si aplica) → actualizar `MEMORY.md`
4. **Qué bugs se cazaron** — síntoma + causa + fix + test
5. **Qué quedó pendiente** — para la próxima sesión
6. **Commits creados**

## Para el agente al ABRIR sesión

Antes de aceptar instrucciones del usuario:
1. Lee `MEMORY.md` (reglas estáticas)
2. Lee `CONTRACT_<modulo>.md` del módulo a tocar
3. Lee últimos **3 SESSION_LOG/*.md** (contexto reciente)
4. Lee `tests/test_golden_paths.py` (qué NO debe romperse)

## Para el agente al CERRAR sesión

Antes de dar respuesta final:
1. Confirma que **golden paths** siguen verdes localmente.
2. Escribe un nuevo `SESSION_LOG/YYYY-MM-DD-N.md` con la estructura.
3. Si decidiste reglas nuevas → actualiza `MEMORY.md` con justificación
   + mencionalo en el SESSION_LOG.
4. Si tocaste un blueprint → actualiza su `CONTRACT_*.md`.

## Política

- NO borrar SESSION_LOG viejos (son auditoría).
- Si una sesión queda incompleta (timeout, error), agregar nota
  "INCOMPLETA" al inicio del archivo.
- Los `SESSION_LOG/*.md` van versionados en git.
