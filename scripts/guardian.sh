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
  "tests/test_envasado_lista_premium.py"
  "tests/test_despeje_orden_mybatch.py"
  "tests/test_diag_envases_partes.py"
  "tests/test_envase_partes_se_descuentan.py"
  "tests/test_envase_cliente_y_partes_helper.py"
  "tests/test_segregacion_funciones.py"
  "tests/test_densidad_puente_op_of.py"
  "tests/test_legajo_trazabilidad_responsables.py"
  "tests/test_inci_ambiguos.py"
  "tests/test_cron_mee_cuarentena.py"
  "tests/test_descuento_kg_editado.py"
  "tests/test_en_transito_azul.py"
  "tests/test_e2e_mp_chain.py"
  "tests/test_diag_solo_admin.py"
  # Dinero con la fecha corrida (27-jul): el "hoy" del server es UTC y después de las 19:00 en
  # Colombia un pago de fin de mes caía en el período contable siguiente. Cubre los 5 módulos.
  "tests/test_hoy_colombia_dinero.py"
  "tests/test_caja_recibo_numerado.py"
  "tests/test_animus_audit.py"
  # La plata de contraentrega: incluye el guard de que ningún sync de Shopify borre la
  # marca que escribe otro (era lo que se la comía en silencio).
  "tests/test_contraentrega_caja.py"
  # La recepcion ADMINISTRATIVA no puede exigir datos que solo Calidad toma, y el control
  # INVIMA vive en la liberacion (no se libera un lote con numero provisional).
  "tests/test_recepcion_administrativa.py"
  "tests/test_recepcion_audit.py"
  # El F01 escribe al kardex lo que Calidad verifica contra el envase (si no, el rotulo
  # sale con los datos viejos y el lote provisional nunca se puede liberar).
  "tests/test_f01_escribe_kardex.py"
  # El desempeno del proveedor se DERIVA de las recepciones · incluye la regla de que una
  # dimension sin dato va en gris y no en cero (si no, califica injusto).
  "tests/test_proveedor_desempeno.py"
  # Pago a influencers: sin paso de aprobacion, las alertas anti doble-pago son LO UNICO que
  # separa un pago legitimo de pagar dos veces el mismo contenido. Y son de dinero real.
  "tests/test_pago_influencer_antidup.py"
  "tests/test_solicitar_pago_influencer.py"
  "tests/test_influencer_pago_e2e.py"
  # Directorio de creadores: es la vista con la que el CEO decide el pago del mes. Sus
  # numeros tienen que significar lo mismo que en el centro de pagos, y el historico sin
  # influencer_id tiene que seguir contando (si no, subestima lo que se le lleva pagado).
  "tests/test_directorio_creadores.py"
  # Un boton vivo no puede abrir un modal que ya no existe: al recortar Marketing borre los
  # 8 modales y deje los botones, y "Solicitar pago" -- lo unico que ese modulo tiene que
  # hacer -- quedo sin hacer nada. Ningun test lo cazo porque el endpoint estaba bien.
  "tests/test_marketing_modales_vivos.py"
  # Pagos › Influencers en el Centro de Mando · y sobre todo: rechazar MARCA la fila con el
  # motivo, nunca la borra. Antes se borraba y por eso la bandeja de Rechazados salia en 0:
  # quien pidio el pago no tenia forma de saber por que no se lo pagaron.
  "tests/test_centro_pagos_bandeja.py"
  # El panel fabricaba creadores duplicados (~700 copias). Guard de la causa raiz: el set de
  # "conocidos" NUNCA se arma desde la consulta filtrada -- lo que el filtro esconde parece
  # que no existe, y se re-inserta con cada tecla del buscador.
  "tests/test_influencers_no_se_duplican.py"
  # Anular una factura de proveedor YA PAGADA dejaba los pagos colgando de un registro
  # anulado: el libro decia "anulada" con la plata afuera. El hermano fp_pagar si rechazaba
  # pagar una anulada -- la asimetria es la firma de M45.
  "tests/test_factura_proveedor_anular.py"
  # Fusionar creadores duplicados MUEVE los pagos, nunca los borra. Los duplicados reales de
  # Sebastian eran la misma persona con nombres distintos (misma cedula), y borrarlos a mano
  # habria perdido sus pagos. Incluye el guard de que la cuenta bancaria compartida NO fusiona.
  "tests/test_dedup_por_cedula.py"
  # La ubicacion del F01 llega COMPLETA al kardex (estanteria Y posicion). Antes solo escribia
  # estanteria: la mitad de la ubicacion se perdia en cada recepcion, y en inventario se veia
  # incompleta. Incluye la nevera, que no existia en el sistema.
  "tests/test_f01_ubicacion_estructurada.py"
  # La OC decia GRAMOS de cosas que no se miden en gramos (un servicio de calibracion salia
  # como "1 g"). La unidad se capturaba en la SOL y se perdia al crear la OC; la pantalla,
  # sin dato, le pegaba una g a todo. Un numero con la unidad equivocada se lee como cierto.
  "tests/test_oc_unidad_real.py"
  # Material de envase del legajo: cuanto ENTREGARON de verdad y quien lo recibio. Sin eso,
  # si llegan 95 de 100 la conciliacion cierra igual y el faltante se lo come "utilizada":
  # el reclamo al proveedor y la merma real quedan indistinguibles.
  "tests/test_envase_material_recibido.py"
  # Conciliacion del granel: el bulk que entro a la orden tiene que terminar EXPLICADO
  # (envasado + remanente + diferencia). En la OF-2026-77 entraron 12.658,95 mL, salieron
  # 1.000 envasados y los otros 11.658,95 no los explicaba ningun registro del legajo.
  "tests/test_conciliacion_granel.py"
  # La ORDEN se aprueba antes de arrancar (firma Part 11) + el gate default-deny que
  # heredan todos los endpoints de ejecucion. Incluye el guard de que 'aprueba_dt' siga
  # en la whitelist del firmador: faltaba, y por eso esa firma nunca se pudo dar.
  "tests/test_aprobacion_orden.py"
  # 2a firma sobre el material de envase recibido: quien cuenta lo que llego no puede ser
  # quien certifica que esta bien. Incluye el guard de que corregir la cantidad recibida
  # TUMBA la firma (una firma cubre los datos que se firmaron) y que el dato LLEGUE a la
  # pantalla: se guardaba desde la mig 391 y la tabla del legajo no lo mostraba.
  "tests/test_material_envase_verificado.py"
  # La ORDEN como objeto propio: una orden agrupa N lotes y se aprueba UNA vez para todos.
  # El test que mas importa es el ADITIVO: un legajo SIN orden madre (todos los anteriores
  # a la mig 395) tiene que seguir abriendo y ejecutando exactamente igual.
  "tests/test_orden_produccion.py"
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
    # ── PLANTILLA (26-jul) · por qué existe ────────────────────────────────────────────────
    # Recrear el esquema en cada corrida obliga al harness a rearmar TODO: el SQLite con las 381
    # migraciones + copiar los datos a PG fila por fila. Son ~8 minutos por corrida, contra ~50
    # segundos de tests. Sebastián: "eso harta que comas muchos créditos, además de que hará más
    # lento el trabajo · para eso tienes cerebro".
    #
    # PostgreSQL ya resuelve esto: `CREATE DATABASE x TEMPLATE y` copia a nivel de archivos.
    # Se construye la base UNA vez, se guarda como plantilla, y cada corrida la restaura en
    # segundos. La plantilla se reconstruye sola cuando cambia el esquema (hash de database.py +
    # pg_schema.sql + conftest.py), así que NO puede quedar vieja: si el hash no coincide, se
    # rearma. Eso conserva la garantía de la limpieza (cada corrida arranca de una base idéntica
    # y sin basura) y le saca los 8 minutos.
    # ⚠ El atajo de la plantilla queda OPT-IN (`EOS_PG_PLANTILLA=1`) hasta terminar de depurarlo:
    # saltear la construcción deja la base sin algo que el login necesita (345 pruebas caen con
    # "login failed"). Y resultó que NO era lo que hacía lento al gate: los 8 minutos eran las
    # conexiones huérfanas bloqueando el DROP SCHEMA. Con eso barrido, la corrida completa baja a
    # ~3 minutos SIN plantilla. Primero lo correcto, después lo rápido.
    if [ "${EOS_PG_PLANTILLA:-0}" != "1" ]; then
      _matar_conexiones_simple() {
        "$PSQL_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -q -t -A \
          -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname LIKE 'eos_test%' AND pid<>pg_backend_pid()" >/dev/null 2>&1 || true
      }
      _matar_conexiones_simple
      echo "    esquema: recreando $PGDATABASE desde cero (conexiones huérfanas barridas)"
      "$PSQL_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -q \
        -v ON_ERROR_STOP=1 -c "SET lock_timeout='30s'" \
        -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" >/dev/null 2>&1 \
        || echo "    ⚠ no se pudo recrear el esquema (¿candado?) · el resultado puede traer basura"
      TESTS=("tests/test_golden_paths.py" "${CORAZON[@]}")
      # (se salta todo el bloque de plantilla de abajo)
      PG_TPL=""
    fi
    if [ -n "${PG_TPL+x}" ] && [ "${EOS_PG_PLANTILLA:-0}" = "1" ]; then
    PG_TPL="${PGDATABASE}_tpl"
    _psql_adm() { "$PSQL_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d postgres -q -t -A "$@"; }
    HASH_ACTUAL="$("$PYTHON_BIN" - <<'PYHASH'
import hashlib, io, os
h = hashlib.sha256()
for f in ('api/database.py', 'api/pg_schema.sql', 'tests/conftest.py'):
    try:
        h.update(io.open(f, 'rb').read())
    except OSError:
        h.update(b'?')
print(h.hexdigest()[:16])
PYHASH
)"
    HASH_TPL="$(_psql_adm -c "SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname='$PG_TPL'" 2>/dev/null | tr -d '\r')"

    _matar_conexiones() {
      _psql_adm -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$1' AND pid<>pg_backend_pid()" >/dev/null 2>&1 || true
    }

    # ── ANTI-BLOQUEO (26-jul · me pasó y perdí más de una hora) ────────────────────────────────
    # Matar un pytest a la fuerza deja su conexión `idle in transaction` reteniendo candados. El
    # `DROP SCHEMA` de la corrida siguiente se queda esperando ESE candado **para siempre**, y
    # desde afuera se ve idéntico a "todavía está corriendo": sin salida, sin CPU, sin error.
    # Encontré cinco sesiones encoladas detrás de una huérfana de 69 minutos.
    # Dos defensas, porque una sola no alcanza:
    #   1. barrer las conexiones viejas ANTES de tocar el esquema (abajo);
    #   2. `lock_timeout` en cada statement destructivo: si aun así hay un candado, el comando
    #      FALLA en 30s con mensaje. **Un paso que puede colgarse indefinidamente es peor que uno
    #      que falla: el silencio no se distingue del progreso.**
    _matar_conexiones "$PGDATABASE"
    _matar_conexiones "$PG_TPL"
    _psql_ddl() {   # psql para DDL destructivo: nunca se cuelga
      "$PSQL_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$1" -q \
        -v ON_ERROR_STOP=1 -c "SET lock_timeout='30s'" -c "$2"
    }

    if [ -n "$HASH_TPL" ] && [ "$HASH_TPL" = "$HASH_ACTUAL" ]; then
      echo "    esquema: restaurando $PGDATABASE desde la plantilla (segundos, no minutos)"
      _matar_conexiones "$PGDATABASE"
      _matar_conexiones "$PG_TPL"
      if _psql_adm -c "DROP DATABASE IF EXISTS \"$PGDATABASE\"" >/dev/null 2>&1 &&
         _psql_adm -c "CREATE DATABASE \"$PGDATABASE\" TEMPLATE \"$PG_TPL\"" >/dev/null 2>&1; then
        export EOS_PG_LISTA=1     # el harness NO reconstruye: la base ya viene armada
      else
        echo "    ⚠ no se pudo restaurar la plantilla · se reconstruye desde cero"
        _psql_ddl "$PGDATABASE" "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" >/dev/null 2>&1 || true
      fi
    else
      # Primera vez, o el esquema cambió: se arma una vez y se guarda como plantilla.
      echo "    esquema: la plantilla no existe o quedó vieja · construyendo (una sola vez)"
      _psql_ddl "$PGDATABASE" "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" >/dev/null 2>&1 || true
      # Un test que USA EL FIXTURE `app` fuerza al harness a construir la base entera. Ojo: tiene
      # que ser uno que de verdad levante la app · con `test_pg_compat.py` (que no toca la BD) la
      # plantilla salió VACÍA, se guardó igual, y las 441 pruebas siguientes reventaron. Fallar en
      # silencio y parecer éxito es el peor resultado posible para un paso de infraestructura.
      "$PYTHON_BIN" -m pytest tests/test_diag_solo_admin.py -q >/dev/null 2>&1 || true
      N_TABLAS="$("$PSQL_BIN" -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" -q -t -A \
        -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" \
        2>/dev/null | tr -d '\r')"
      # VERIFICAR antes de guardar: una plantilla vacía envenena TODAS las corridas siguientes.
      if [ "${N_TABLAS:-0}" -gt 100 ]; then
        echo "    base construida ($N_TABLAS tablas) · guardando plantilla"
        _matar_conexiones "$PGDATABASE"
        _matar_conexiones "$PG_TPL"
        if _psql_adm -c "DROP DATABASE IF EXISTS \"$PG_TPL\"" >/dev/null 2>&1 &&
           _psql_adm -c "CREATE DATABASE \"$PG_TPL\" TEMPLATE \"$PGDATABASE\"" >/dev/null 2>&1; then
          _psql_adm -c "COMMENT ON DATABASE \"$PG_TPL\" IS '$HASH_ACTUAL'" >/dev/null 2>&1
          echo "    plantilla guardada · las próximas corridas arrancan en segundos"
          # la corrida real arranca de una copia limpia de la plantilla
          _matar_conexiones "$PGDATABASE"
          if _psql_adm -c "DROP DATABASE IF EXISTS \"$PGDATABASE\"" >/dev/null 2>&1 &&
             _psql_adm -c "CREATE DATABASE \"$PGDATABASE\" TEMPLATE \"$PG_TPL\"" >/dev/null 2>&1; then
            export EOS_PG_LISTA=1
          fi
        else
          echo "    ⚠ no se pudo guardar la plantilla · esta corrida reconstruye igual"
        fi
      else
        echo "    ⚠ la construcción dejó la base con ${N_TABLAS:-0} tablas · NO se guarda plantilla"
        echo "      (guardar una vacía haría fallar todas las corridas siguientes)"
      fi
    fi
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
