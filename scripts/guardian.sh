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
  "tests/test_tendencia_numerica.py"
  "tests/test_calendario_dias_habiles.py"
  "tests/test_plan_festivos_clamp.py"
  "tests/test_plan_primer_lote_buffer.py"
  "tests/test_mover_lote_cadena.py"
  "tests/test_abastecimiento_vencimiento.py"
  "tests/test_codigo_kardex_limpio.py"
  "tests/test_auditoria_lotes_pg.py"
  "tests/test_envases_kardex_mp.py"
  "tests/test_formulas_permiso_invima.py"
  "tests/test_mbr_instructivo_llega_al_piso.py"
  "tests/test_revincular_mbr.py"
  "tests/test_auto_asignar_operarios_audita.py"
  "tests/test_facturas_proveedor_rol.py"
  "tests/test_instructivos_completos.py"
  "tests/test_instructivo_por_fase.py"
  "tests/test_deuda_diseno_no_crece.py"
  "tests/test_legajo_trazabilidad_responsables.py"
  "tests/test_inci_ambiguos.py"
  "tests/test_cron_mee_cuarentena.py"
  "tests/test_descuento_kg_editado.py"
  "tests/test_en_transito_azul.py"
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

  # ── RECREAR EL ESQUEMA ANTES DE CORRER (26-jul) ──────────────────────────────
  # Por qué: la BD de PG local PERSISTE entre corridas, y 96 archivos de test siembran en las
  # tablas del corazón SIN limpiar (QAFORMULA-*, CASEDUP SERUM, PROD-KGEDIT-X, QAB2B…). Con esa
  # basura acumulada, `test_P6` (toda fórmula activa suma 95-101) y varios golden fallan CON EL
  # CÓDIGO SANO. El 26-jul interpreté ese rojo como "rompí algo" tres veces seguidas antes de
  # entender que era basura de corridas anteriores. Un gate que da rojo por su propia basura es
  # peor que no tenerlo: enseña a ignorarlo.
  # CI no lo sufre (contenedor nuevo cada vez); esto le da a local la MISMA garantía.
  # El harness reconstruye todo solo: carga pg_schema.sql y auto-sana tablas/columnas faltantes.
  case "$PGDATABASE" in
    *test*|*TEST*) ;;
    *)
      echo ""
      echo "❌ ABORTO: PGDATABASE='$PGDATABASE' no parece una base de TEST."
      echo "   Este paso BORRA el esquema completo. Sólo corre contra una base con 'test' en el"
      echo "   nombre, para que no exista forma de apuntarle a producción por accidente."
      echo ""
      exit 1
      ;;
  esac
  PSQL_BIN="${PSQL_BIN:-}"
  if [ -z "$PSQL_BIN" ]; then
    if command -v psql &>/dev/null; then
      PSQL_BIN="psql"
    elif [ -x "C:/Users/sebas/pgdev/pg2/pgsql/bin/psql.exe" ]; then
      PSQL_BIN="C:/Users/sebas/pgdev/pg2/pgsql/bin/psql.exe"
    fi
  fi
  if [ -n "$PSQL_BIN" ]; then
    echo "    esquema: recreando $PGDATABASE desde cero (evita basura de corridas anteriores)"
    if ! "$PSQL_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -q \
         -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" >/dev/null 2>&1; then
      echo "    ⚠ no se pudo recrear el esquema · el resultado puede traer basura acumulada"
    fi
  else
    # Ruidoso a propósito: si no se pudo limpiar, quien lea el verde tiene que saber que el
    # rojo/verde puede venir de datos viejos y no del código.
    echo "    ⚠ psql NO encontrado · NO se recreó el esquema"
    echo "      El resultado puede dar rojo por fixtures de corridas anteriores, no por tu código."
    echo "      Definí PSQL_BIN=/ruta/psql para que el gate se limpie solo."
  fi
  TESTS=("tests/test_golden_paths.py" "${CORAZON[@]}")
elif [ "$MODE" = "--full" ] || [ "$MODE" = "full" ]; then
  TESTS=(
    "tests/test_golden_paths.py"
    "tests/test_compras_smoke.py::test_all_pages_js_parses_with_node"
    "tests/test_compras_smoke.py::test_compras_no_orphan_fetch_urls"
    "tests/test_compras_3fuentes.py"
    # 26-jul · los 16 que el barrido nocturno encontró EN ROJO fuera del gate. Ninguno era
    # regresión: 3 usaban a un usuario dado de baja, 2 buscaban JS que se movió a un archivo
    # externo, 3 esperaban comportamientos que una decisión posterior cambió, 1 tenía fechas
    # hardcodeadas que envejecieron, 1 no controlaba su universo y 1 destapó un bug real
    # (LIMIT 1 sin ORDER BY en "Supervisado por"). Entran acá para que su rojo vuelva a verse.
    "tests/test_fabricacion_cuenta_en_plan.py"
    "tests/test_financiero_mom_12.py"
    "tests/test_lotes_retenido.py"
    "tests/test_marketing_smoke.py"
    "tests/test_ordenes_unificadas.py"
    "tests/test_planta_audit.py"
    "tests/test_planta_extension.py"
    "tests/test_producciones_faltantes.py"
    "tests/test_proyeccion_2anios.py"
    "tests/test_rbac_negative.py"
    "tests/test_reportes_invima.py"
    "tests/test_revisar_minimos_planta.py"
    "tests/test_shopify_necesidades.py"
    "tests/test_solicitar_lote_bodega.py"
    "tests/test_sugerencia_solo_animus.py"
    "tests/test_trail_explosion.py"
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
