#!/usr/bin/env bash
# INSTALL HOOKS · Sebastián 7-may-2026
#
# Instala git hooks que ejecutan Guardian (pre-push) y Reviewer (pre-commit).
# Ejecutar UNA VEZ después de clonar el repo.
#
# Uso:
#   bash scripts/install_hooks.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
  echo "❌ $HOOKS_DIR no existe · ¿estás en un repo git?"
  exit 1
fi

echo "Instalando hooks en $HOOKS_DIR ..."

# Pre-commit · Reviewer
cat > "$HOOKS_DIR/pre-commit" <<'EOF'
#!/usr/bin/env bash
# Auto-generated por scripts/install_hooks.sh
PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" &>/dev/null; then
  PYTHON_BIN="python3"
fi
"$PYTHON_BIN" "$(git rev-parse --show-toplevel)/scripts/reviewer.py"
EOF
chmod +x "$HOOKS_DIR/pre-commit"

# Pre-push · Guardian (solo golden paths · rápido)
cat > "$HOOKS_DIR/pre-push" <<'EOF'
#!/usr/bin/env bash
# Auto-generated por scripts/install_hooks.sh
#
# Sebastian 3-ago: "quiero que resolvamos tantas demoras porque no avanzamos mucho".
# El gate corria DOS veces por cada despliegue -- una a mano y otra aca -- sobre el MISMO
# arbol, ~17 minutos duplicados que no agregaban ninguna seguridad. Ahora, si el guardian ya
# aprobo EXACTAMENTE este arbol hace poco, no se repite.
#
# El hash del arbol (`git write-tree`) es exacto: si cambio un byte de un archivo, cambia el
# hash y la suite corre completa. Y el sello CADUCA a la hora, para que un "ya paso" viejo
# nunca autorice un push del dia siguiente.
ROOT="$(git rev-parse --show-toplevel)"
SELLO="$ROOT/.git/eos/gate-ok"
TREE=$(git write-tree 2>/dev/null || echo "")

if [ -n "$TREE" ] && [ -f "$SELLO" ]; then
  read -r SELLO_TREE SELLO_TS < "$SELLO"
  AHORA=$(date +%s)
  EDAD=$(( AHORA - ${SELLO_TS:-0} ))
  if [ "$SELLO_TREE" = "$TREE" ] && [ "$EDAD" -lt 3600 ]; then
    echo "OK: el guardian ya aprobo este arbol hace ${EDAD}s, no se repite la suite."
    echo "    Si cambia un solo archivo, el hash cambia y vuelve a correr completa."
    exit 0
  fi
fi

bash "$ROOT/scripts/guardian.sh" --quick
EOF
chmod +x "$HOOKS_DIR/pre-push"

echo ""
echo "✅ Hooks instalados:"
echo "   $HOOKS_DIR/pre-commit  → reviewer.py (warnings + critical errors)"
echo "   $HOOKS_DIR/pre-push    → guardian.sh --quick (golden paths)"
echo ""
echo "Test manual:"
echo "   bash scripts/guardian.sh --quick    # debe pasar 5/5"
echo "   python scripts/reviewer.py           # debe imprimir 'todo OK' o warnings"
echo ""
echo "Para deshabilitar temporalmente un commit:"
echo "   git commit --no-verify ..."
echo ""
echo "Para deshabilitar temporalmente un push:"
echo "   git push --no-verify ..."
echo ""
