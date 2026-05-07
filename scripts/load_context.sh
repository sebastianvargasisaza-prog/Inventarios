#!/usr/bin/env bash
# LOAD CONTEXT · Sebastián 7-may-2026
#
# Para usar al INICIO de una sesión IA (prologue).
# Imprime los archivos de memoria que el agente debe leer antes de
# aceptar instrucciones del usuario.
#
# Uso desde Claude Code:
#   bash scripts/load_context.sh
#   # → output va al pipe; copialo a la sesión nueva

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "════════════════════════════════════════════════════════════════"
echo "  CONTEXT LOAD · $(date '+%Y-%m-%d %H:%M')"
echo "  repo: $REPO_ROOT"
echo "════════════════════════════════════════════════════════════════"
echo ""

echo "── MEMORY.md (reglas estáticas) ─────────────────────────────────"
echo ""
cat MEMORY.md
echo ""

echo "── Últimos 3 SESSION_LOG ────────────────────────────────────────"
echo ""
ls -1t SESSION_LOG/*.md 2>/dev/null | grep -v README | head -3 | while read -r logfile; do
  echo ""
  echo "════ $logfile ════"
  cat "$logfile"
  echo ""
done

echo ""
echo "── CONTRACT files disponibles ───────────────────────────────────"
ls -1 api/blueprints/CONTRACT_*.md 2>/dev/null | sed 's|^|  · |'
echo ""

echo "── Golden paths (LO QUE NO SE PUEDE ROMPER) ─────────────────────"
echo ""
grep -E "^def test_golden_" tests/test_golden_paths.py | sed 's|def \(test_[^(]*\)(.*|  · \1|'
echo ""

echo "── Estado git ───────────────────────────────────────────────────"
git log --oneline -5
echo ""
echo "Cambios sin commit:"
git status --short || echo "  (limpio)"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "  FIN CONTEXT · listo para recibir instrucciones del usuario."
echo "════════════════════════════════════════════════════════════════"
