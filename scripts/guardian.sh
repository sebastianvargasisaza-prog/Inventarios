#!/usr/bin/env bash
# GUARDIAN · Sebastián 7-may-2026
#
# Corre golden paths (E2E críticos) antes de permitir push.
# Si cualquier test rojo → exit 1 → git push abortado.
#
# Uso:
#   bash scripts/guardian.sh           · run normal
#   bash scripts/guardian.sh --quick   · solo golden paths
#   bash scripts/guardian.sh --full    · golden + tests críticos relacionados
#   bash scripts/guardian.sh --pg      · golden EN MODO PostgreSQL (paridad prod)
#
# El modo --pg corre la suite contra el Postgres local (pgdev) para cazar el
# drift SQLite↔PG (causa #1 de reprocesos · ver .claude/CERO_ERROR.md). Requiere
# el PG local levantado y la BD eos_test. El CI lo corre automático en cada push.
#
# Instalación como pre-push hook:
#   bash scripts/install_hooks.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODE="${1:-quick}"

# ── SET DEL CORAZÓN (25-jul-2026) ─────────────────────────────────────────────
# Lo que NO puede romperse en silencio: el descuento de MP, el motor de demanda,
# el resolver de material y las propiedades de inventario/fórmulas. Entran al gate
# porque la auditoría CERO-ERROR encontró 11 de estos tests EN ROJO desde hacía
# tiempo, invisibles por correr solo los golden. ~40s.
CORAZON=(
  "tests/test_descuento_perfecto.py"
  "tests/test_descuento_dedup_codigo.py"
  "tests/test_case_dup_formula_descuento.py"
  "tests/test_prop_descuento.py"
  "tests/test_prop_abastecimiento.py"
  "tests/test_prop_inventario.py"
  "tests/test_corazon_deficit.py"
  "tests/test_corazon_pedir.py"
  "tests/test_corazon_revisor_huecos.py"
  "tests/test_corazon_acumula.py"
  "tests/test_corazon_b2b_e2e.py"
  "tests/test_corazon_formula.py"
  "tests/test_corazon_agua_excluida.py"
  "tests/test_abastecimiento_dedup_fijo.py"
  "tests/test_resolver_inci_ambiguo.py"
  "tests/test_generar_oc_correlativo.py"
  "tests/test_dedup_mismo_dia_respeta_fijo.py"
  "tests/test_cron_no_cancela_fijo.py"
  "tests/test_paridad_motores.py"
  "tests/test_salud_cadenas.py"
  "tests/test_inci_ambiguos.py"
  "tests/test_e2e_mp_chain.py"
  "tests/test_diag_solo_admin.py"
)

echo ""
echo "🛡️  GUARDIAN · golden paths + corazón (descuento · demanda · fórmulas · inventario)"
echo "    repo: $REPO_ROOT"
echo "    mode: $MODE"
echo ""

# Detectar python (Windows uses python, Unix may use python3)
PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" &>/dev/null; then
  PYTHON_BIN="python3"
fi

# Modo PostgreSQL · paridad con producción (caza drift SQLite↔PG)
if [ "$MODE" = "--pg" ] || [ "$MODE" = "pg" ]; then
  export EOS_DB_BACKEND=postgres
  export PGHOST="${PGHOST:-127.0.0.1}"
  export PGPORT="${PGPORT:-5432}"
  export PGUSER="${PGUSER:-postgres}"
  export PGDATABASE="${PGDATABASE:-eos_test}"
  echo "    backend: PostgreSQL ($PGHOST:$PGPORT/$PGDATABASE)"
  # Verificar que PG responde antes de correr (mensaje claro si está apagado)
  if ! "$PYTHON_BIN" -c "import socket,sys; s=socket.socket(); s.settimeout(2); sys.exit(0 if s.connect_ex(('$PGHOST',int('$PGPORT')))==0 else 1)" 2>/dev/null; then
    echo ""
    echo "❌ PostgreSQL no responde en $PGHOST:$PGPORT"
    echo "   Levantá el PG local:  pg_ctl -D <data_dir> -l pg.log start"
    echo "   (En esta máquina: C:/Users/sebas/pgdev/pg2/pgsql/bin/pg_ctl.exe -D C:/Users/sebas/pgdev/data start)"
    echo ""
    exit 1
  fi
  TESTS=("tests/test_golden_paths.py" "${CORAZON[@]}")
elif [ "$MODE" = "--full" ] || [ "$MODE" = "full" ]; then
  TESTS=(
    "tests/test_golden_paths.py"
    "tests/test_compras_smoke.py::test_all_pages_js_parses_with_node"
    "tests/test_compras_smoke.py::test_compras_no_orphan_fetch_urls"
    "tests/test_compras_3fuentes.py"
    "tests/test_producciones_faltantes.py"
  )
else
  # Quick mode (default · el que corre el hook pre-push).
  #
  # 25-jul-2026 · LECCIÓN CARA de la auditoría CERO-ERROR: el gate corría SOLO los golden,
  # así que 11 tests del CORAZÓN (descuento de MP, abastecimiento, resolver) llevaban tiempo
  # EN ROJO y nadie podía enterarse. Un test que no corre en el gate no protege nada.
  # Por eso el quick mode ahora incluye el set del corazón (~40s extra, vale la pena).
  # Regla: si escribís un test que protege el descuento, la demanda, las fórmulas o el
  # inventario, AGREGALO ACÁ o su rojo será invisible.
  TESTS=("tests/test_golden_paths.py" "${CORAZON[@]}")
fi

# Ejecutar · pipefail para que el exit code de pytest llegue al if
# (sin pipefail, el pipe a tail siempre exit 0 y el bug se traga).
set -o pipefail
START=$(date +%s)
if "$PYTHON_BIN" -m pytest "${TESTS[@]}" -q --tb=line 2>&1 | tail -10; then
  END=$(date +%s)
  echo ""
  echo "✅ GUARDIAN APROBÓ · golden paths verdes en $((END - START))s"
  echo "    push permitido."
  echo ""
  exit 0
else
  END=$(date +%s)
  echo ""
  echo "❌ GUARDIAN BLOQUEÓ EL PUSH · $((END - START))s"
  echo ""
  echo "Algún golden path rompió. Esto significa que el cambio actual"
  echo "rompe un flujo crítico que ANTES funcionaba."
  echo ""
  echo "Pasos:"
  echo "  1. Lee el output arriba para ver qué test falló."
  echo "  2. Corre el test específico para debug:"
  echo "     pytest tests/test_golden_paths.py::<test_name> -xvs --tb=long"
  echo "  3. Arregla el código (NO el test) hasta que pase."
  echo "  4. Vuelve a intentar git push."
  echo ""
  echo "Si necesitás bypass URGENTE (NO recomendado):"
  echo "  git push --no-verify"
  echo "  Pero después arregla el bug que introdujiste."
  echo ""
  exit 1
fi
