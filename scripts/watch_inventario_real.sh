#!/bin/bash
# Watcher en vivo · Sebastian 8-may-2026 inventario REAL en vuelo.
# Verifica cada 90s: integrity_check, conteos de tablas (NO deben bajar),
# app responde. Si algo regresa, lo grita en stdout para alerta inmediata.

URL="https://app.eossuite.com/api/health/debug"
LOG="${1:-/tmp/inventario_watch.log}"

echo "==> Watcher arrancado · $(date '+%H:%M:%S')"
echo "    URL:  $URL"
echo "    LOG:  $LOG"
echo ""

# Baseline inicial
prev_movs=0
prev_animus=0
prev_sols=0
prev_ocs=0
prev_mps=0
iter=0

while true; do
  iter=$((iter+1))
  ts=$(date '+%H:%M:%S')
  resp=$(curl -s --max-time 10 "$URL" 2>/dev/null)

  if [ -z "$resp" ]; then
    echo "[$ts] !!! APP NO RESPONDE — alerta"
    echo "[$ts] APP_DOWN" >> "$LOG"
    sleep 90
    continue
  fi

  integrity=$(echo "$resp" | python -c "import sys,json; print(json.load(sys.stdin).get('integrity_check','?'))" 2>/dev/null)
  movs=$(echo "$resp"     | python -c "import sys,json; print(json.load(sys.stdin).get('tables',{}).get('movimientos','?'))" 2>/dev/null)
  animus=$(echo "$resp"   | python -c "import sys,json; print(json.load(sys.stdin).get('tables',{}).get('animus_inventario_movimientos','?'))" 2>/dev/null)
  sols=$(echo "$resp"     | python -c "import sys,json; print(json.load(sys.stdin).get('tables',{}).get('solicitudes_compra','?'))" 2>/dev/null)
  ocs=$(echo "$resp"      | python -c "import sys,json; print(json.load(sys.stdin).get('tables',{}).get('ordenes_compra','?'))" 2>/dev/null)
  mps=$(echo "$resp"      | python -c "import sys,json; print(json.load(sys.stdin).get('tables',{}).get('maestro_mps','?'))" 2>/dev/null)

  # Detectar regresion (un conteo que BAJA)
  alert=""
  if [ $iter -gt 1 ]; then
    [ "$movs" != "?" ] && [ "$movs" -lt "$prev_movs" ] 2>/dev/null && alert="$alert MOVS_BAJO($prev_movs→$movs)"
    [ "$animus" != "?" ] && [ "$animus" -lt "$prev_animus" ] 2>/dev/null && alert="$alert ANIMUS_BAJO($prev_animus→$animus)"
    [ "$sols" != "?" ] && [ "$sols" -lt "$prev_sols" ] 2>/dev/null && alert="$alert SOLS_BAJO($prev_sols→$sols)"
    [ "$ocs" != "?" ] && [ "$ocs" -lt "$prev_ocs" ] 2>/dev/null && alert="$alert OCS_BAJO($prev_ocs→$ocs)"
    [ "$mps" != "?" ] && [ "$mps" -lt "$prev_mps" ] 2>/dev/null && alert="$alert MPS_BAJO($prev_mps→$mps)"
  fi

  if [ "$integrity" != "ok" ]; then
    alert="$alert INTEGRITY=$integrity"
  fi

  line="[$ts] integrity=$integrity movs=$movs animus=$animus sols=$sols ocs=$ocs mps=$mps"
  if [ -n "$alert" ]; then
    echo "$line  !!! ALERTA:$alert"
    echo "$line ALERT:$alert" >> "$LOG"
  else
    echo "$line  ok"
    echo "$line" >> "$LOG"
  fi

  prev_movs=$movs
  prev_animus=$animus
  prev_sols=$sols
  prev_ocs=$ocs
  prev_mps=$mps

  sleep 90
done
