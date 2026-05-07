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
bash "$(git rev-parse --show-toplevel)/scripts/guardian.sh" --quick
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
