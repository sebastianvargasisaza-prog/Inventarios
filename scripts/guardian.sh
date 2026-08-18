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
# ── PARALELO · 17-ago-2026 · el corazon SI paralela, pero por ARCHIVO ────────────────────
# Sebastian: *"si quiero que resolvamos lo del tiempo para que avancemos mas rapido"*.
#
# La nota que estaba aca decia "el corazon completo no paralela bien (medido)" y quedo VIEJA:
# lo que no paralela bien es repartir por TEST. Medido hoy sobre los mismos 2359 tests, los
# tres verdes y con el mismo conteo:
#
#   serie (lo que corria el hook)          924 s   15m24
#   -n 8  --dist loadfile  (por ARCHIVO)   411 s    6m51   <- 2,25x
#   -n 12 --dist load      (por TEST)      508 s    8m28   <- PEOR, y con mas workers
#
# Por que por archivo le gana a por test: casi todos los archivos del corazon siembran en un
# test y leen en otro, asi que repartir sus tests obliga a cada worker a re-sembrar lo mismo.
# `loadfile` manda el archivo ENTERO a un worker, conserva el orden de adentro, y cada worker
# levanta su propia base (`test_workspace` es un mkdtemp por sesion y con xdist cada worker es
# un proceso) -- o sea MAS aislamiento del que hay corriendo todo junto, no menos.
#
# Piezas medidas por separado, por si alguien quiere seguir apretando: el golden ya NO es el
# cuello (245 tests en 44 s repartidos por test); el corazon solo son 453 s. Y separarlos en dos
# invocaciones da peor (45 + 453 = 498 s) que la corrida unica, asi que se dejan juntos.
#
# ⚠ El modo --pg NO paralela: ahi los workers comparten UNA sola base de PostgreSQL y se
#   pisarian entre ellos. Ahi el aislamiento no sale gratis como en SQLite.
PARALELO=""
# ── POR QUE 8 WORKERS Y `loadfile` · lo medido, incluido lo que NO funciono (17-ago) ──────
# El trabajo total del gate son ~7.700 s repartidos en 276 archivos, y `test_golden_paths.py`
# solo pesa ~970 s: el 12,5 % en UN archivo (le siguen matriz_permisos_rapida 439 s,
# ninguna_pantalla_revienta 339 s, matriz_coherente 192 s). Con `loadfile` ese archivo entero
# cae en un worker, asi que el piso lo pone el -- y por eso subir de 8 workers no baja nada.
#
# Se intento romper ese piso con `--dist loadgroup` (cada archivo con su grupo, golden SIN
# grupo para que sus 245 tests se repartan). En teoria el piso pasaba a ser trabajo/workers.
# QUEDO SIN MEDIR: cuatro corridas cortadas por tiempo del entorno.
#
# ⚠ Y la primera version de esta nota decia que `loadfile` "completo TODAS las veces" y que por
#   eso `loadgroup` era el problema. ES FALSO: la corrida siguiente, con `loadfile`, tambien la
#   cortaron. Los cortes son del ENTORNO (sesiones largas), no de la forma de repartir. Atribuir
#   una causa a partir de una racha es exactamente el error que M110 castiga -- se deja anotado
#   asi, sin veredicto, porque un "no sirve" sin medicion vale menos que un "no se pudo medir".
#
# Lo que SI esta medido y sostiene la configuracion de abajo: serie 924 s · `-n 8 --dist
# loadfile` 411 s (verde dos veces) · `-n 12 --dist load` 508 s (peor, con mas workers).
#
# ⚠ El modo --pg NO paralela: ahi los workers comparten UNA sola base de PostgreSQL y se
#   pisarian entre ellos. Ahi el aislamiento no sale gratis como en SQLite.
# Se puede BAJAR con EOS_PARALELO cuando la maquina esta ahogada. No es cosmetico:
# con menos de ~1 GB libre el mismo archivo pasa de 44 s a mas de 600 y el gate no
# termina -- y un gate que no se puede correr deja de proteger (M105/M223). El default
# NO cambia: 8 workers por archivo, que es lo medido.
PARALELO_CORAZON="${EOS_PARALELO:--n 8 --dist loadfile}"

# ── SET DEL CORAZÓN (25-jul-2026) ─────────────────────────────────────────────
# Lo que NO puede romperse en silencio: el descuento de MP, el motor de demanda,
# el resolver de material y las propiedades de inventario/fórmulas. Entran al gate
# porque la auditoría CERO-ERROR encontró 11 de estos tests EN ROJO desde hacía
# tiempo, invisibles por correr solo los golden. ~40s.
# ─────────────────────────────────────────────────────────────────────────────────────────
# MODO --rapido · el gate que se puede correr en cada tanda sin perder la tarde
#
# Sebastian (9-ago): *"llevas mas de una hora y no has resuelto esto... tenemos que trabajar en
# esos tiempos"*. Tenia razon y el numero lo confirma: el gate completo tarda entre 10 y 30
# minutos, lo corri una docena de veces en el dia, y casi todos esos cambios tocaban DOS archivos.
#
# Medido hoy:
#   arranque de pytest (esquema + 400 migraciones)   10,6 s  ->  0,8 s  (plantilla en conftest)
#   golden paths                                     4m23s   ->  1m51s (8 procesos)
#   corazon completo (186 archivos)                  ~15 min  (no paralela bien)
#
# Entonces --rapido corre:
#   · los golden EN PARALELO, que son la red de seguridad de los flujos criticos;
#   · los tests del corazon que TOCAN lo que cambio (por nombre de modulo y por archivo tocado);
#   · y DICE cuales quedaron afuera.
#
# ⚠ Lo ultimo no es cosmetico: un gate mas angosto que no declara su alcance se lee como si
# hubiera probado todo (M155). El completo (--quick) sigue existiendo y es el que manda antes de
# una tanda grande o si el diff toca el corazon del descuento.
_seleccion_rapida() {
  local cambiados
  cambiados=$(git diff --name-only HEAD 2>/dev/null; git diff --cached --name-only 2>/dev/null; \
              git ls-files --others --exclude-standard 2>/dev/null)
  cambiados=$(echo "$cambiados" | sort -u | grep -E '\.py$' || true)
  [ -z "$cambiados" ] && return 0
  local pistas=""
  local f base
  for f in $cambiados; do
    base=$(basename "$f" .py)
    case "$f" in
      tests/*) echo "$f" ;;                       # el test tocado corre siempre
      *) pistas="$pistas $base" ;;
    esac
  done
  [ -z "$pistas" ] && return 0
  # Un test "toca" un modulo si lo nombra en su fuente. Es una heuristica y se declara como tal:
  # por eso los golden corren SIEMPRE, para que la red no dependa de que la heuristica acierte.
  local p
  for p in $pistas; do
    grep -rl --include='*.py' -e "$p" tests/ 2>/dev/null || true
  done
}

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
  "tests/test_portal_facturas_pagos.py"
  "tests/test_portal_mensajes_bandeja.py"
  "tests/test_aliados_scores.py"
  "tests/test_programacion_abre_con_panel.py"
  "tests/test_pedido_del_portal_cae_en_necesidades.py"
  "tests/test_pedido_del_portal_avisa.py"
  "tests/test_catalina_acepta_pedido.py"
  "tests/test_calendario_premium.py"
  "tests/test_solicitar_lote_ids_propios.py"
  # Las tres fases del batch record recorridas de punta a punta. Es lo que se le
  # muestra a INVIMA al pedir la certificación, así que un rojo acá bloquea el
  # push igual que un golden. El de fabricación existía desde junio y NO corría
  # en ningún gate (M95: un test del corazón fuera del gate no protege nada).
  "tests/test_ebr_e2e_demo.py"
  "tests/test_ebr_e2e_envasado_acond.py"
  "tests/test_conciliacion_averiada.py"
  "tests/test_ipc_estandar_por_fase.py"
  "tests/test_envasado_para_que_cliente.py"
  "tests/test_yield_justificacion_queda.py"
  "tests/test_conciliacion_granel_visible.py"
  "tests/test_cola_controles_calidad.py"
  "tests/test_login_premium.py"
  "tests/test_envasado_lista_premium.py"
  "tests/test_despeje_orden_mybatch.py"
  "tests/test_diag_envases_partes.py"
  "tests/test_envase_partes_se_descuentan.py"
  "tests/test_envase_cliente_y_partes_helper.py"
  "tests/test_recepcion_partes_envase.py"
  "tests/test_recepcion_oc_envases.py"
  "tests/test_union_producto_envase.py"
  "tests/test_modal_empaque_por_producto.py"
  "tests/test_presentaciones_vs_shopify.py"
  "tests/test_memo_geometria_envase.py"
  "tests/test_memo_por_producto.py"
  "tests/test_ninguna_pantalla_revienta.py"
  "tests/test_rastro_empaque.py"
  "tests/test_rastro_maestro_envases.py"
  "tests/test_matriz_permisos_rapida.py"
  "tests/test_impreso_no_alcanza.py"
  "tests/test_duplicados_por_tamano.py"
  "tests/test_tono_desde_shopify.py"
  "tests/test_expandir_por_tono.py"
  "tests/test_reparto_por_tono.py"
  "tests/test_presentacion_volumen_clonado.py"
  "tests/test_cola_marcacion_agrupa.py"
  "tests/test_reparto_envases_lote.py"
  "tests/test_alta_cliente_maquila.py"
  "tests/test_progresion_cliente.py"
  "tests/test_leads_correo.py"
  "tests/test_filas_sobrantes.py"
  "tests/test_sku_map_csrf.py"
  "tests/test_resolver_tonos.py"
  "tests/test_operario_no_archiva.py"
  "tests/test_pago_creador_no_se_paga_solo.py"
  "tests/test_reversa_pago_deja_rastro.py"
  "tests/test_caches_con_techo.py"
  "tests/test_kpis_calidad_memo.py"
  "tests/test_matriz_permisos.py"
  "tests/test_limpiar_flujo_reversible.py"
  "tests/test_quien_entra_a_cada_modulo.py"
  "tests/test_centro_decisiones_sin_repetir.py"
  "tests/test_salud_cadena_envase.py"
  "tests/test_empaque_por_frasco.py"
  "tests/test_sku_por_tono.py"
  "tests/test_onclick_no_rompe_el_html.py"
  "tests/test_normalizacion_mee.py"
  "tests/test_js_de_las_pantallas_compila.py"
  "tests/test_normalizar_tabla.py"
  "tests/test_kit_visible_en_inventario.py"
  "tests/test_doble_descuento_envase.py"
  "tests/test_serigrafiado_se_consume.py"
  "tests/test_salida_envasado_canonica.py"
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
  "tests/test_caja_respaldo_y_rechazo.py"
  "tests/test_financiero_pestanas_conectadas.py"
  "tests/test_comprobante_llega_al_creador.py"
  "tests/test_comprobante_muestra.py"
  "tests/test_caja_libro_contadora.py" "tests/test_tesoreria_caja_menor.py" "tests/test_caja_llega_al_libro_central.py" "tests/test_ingreso_se_cuenta_una_vez.py" "tests/test_gastos_llegan_al_libro.py" "tests/test_acondicionamiento_no_descuenta_doble.py" "tests/test_cadena_envase_una_sola_vez.py" "tests/test_rotulos_en_bloque.py" "tests/test_f01_f02_estibas_y_fechas.py" "tests/test_pagos_no_recargan_la_bandeja.py" "tests/test_factibilidad_no_promete_vencido.py" "tests/test_abono_b2b_llega_al_libro.py" "tests/test_comprobante_encuentra_el_correo.py" "tests/test_recepcion_avisa_filas_sin_lote.py" "tests/test_cc_review_funciona_en_las_dos_pantallas.py" "tests/test_botones_apuntan_a_algo_real.py" "tests/test_saldo_caja_dice_de_cuando_es.py" "tests/test_financiero_sin_residuo.py"
  # La caja también PAGA (3-ago): solicitar → autorizar → pagar, con los controles que le dan
  # sentido -- nadie se autoriza a sí mismo, no se paga dos veces, no se paga más de lo que hay,
  # y consignar no cuenta como gasto. Es plata saliendo de una gaveta: sin gate no está protegido.
  "tests/test_caja_solicitudes_pago.py"
  "tests/test_animus_solicitudes_novedades.py"
  "tests/test_animus_inventario_fusion.py"
  "tests/test_animus_pqr_premium.py"
  "tests/test_rrhh_permiso_cuenta.py"
  "tests/test_sin_consultas_fantasma.py"
  "tests/test_planta_kpis_dicen_la_verdad.py"
  # Lo que vuelve CONFIABLE la caja: el ARQUEO contra el efectivo real (el saldo era una suma
  # que nadie habia contado nunca), el espejo a Tesoreria (la plata dejaba de verse al salir),
  # la trazabilidad de un recibo y el cierre de periodo. Es plata: sin gate no esta protegido.
  "tests/test_caja_arqueo_cierre.py"
  "tests/test_animus_audit.py"
  # La plata de contraentrega: incluye el guard de que ningún sync de Shopify borre la
  # marca que escribe otro (era lo que se la comía en silencio).
  "tests/test_contraentrega_caja.py"
  # Módulo /animus (2-ago): mide el contraste de cada par (fondo, texto) en los DOS temas
  # -el título del módulo y los 7 títulos de modal daban 1.00 en claro, y el botón Eliminar
  # y el banner de error tenían fondo y texto en el MISMO token- y exige que toda acción que
  # INSERTA pase por el guard anti doble-click (un doble click creaba DOS recibos de caja).
  # No toca la BD: corre en 0,2 s.
  "tests/test_animus_modulo_premium.py"
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
  # El envase que va a serigrafia se descontaba DOS veces (Catalina): produccion volvia a
  # descontar el BASE, que ya habia salido al enviarlo a marcar, y el serigrafiado -- el que
  # de verdad se usa -- no se consumia nunca. Ademas "Solicitar alistamiento" llama al MISMO
  # endpoint que enviar, sin guard: dos clics = dos ordenes = dos Salidas.
  "tests/test_marcacion_no_descuenta_doble.py"
  # El ciclo COMPLETO de marcacion por los endpoints reales. El arreglo del doble descuento se
  # habia probado con un fixture que ponia el cache `maestro_mee.stock_actual` A MANO; produccion
  # no hace eso, y sin ese cache la Salida del serigrafiado se registraba en CERO. El doble
  # descuento se habia convertido en CERO descuento, que es peor.
  "tests/test_marcacion_ciclo_real.py"
  # Las tarjetas de la caja sumaban transferencia/Nequi/tarjeta como si fueran billetes: la
  # pantalla mostraba un saldo y el servidor decidia con otro (caja_saldo), y ese hero es el
  # numero contra el que se valida un pago. Solo el EFECTIVO entra a la gaveta.
  "tests/test_caja_kpis_solo_efectivo.py"
  # La salud de la cadena (llega tarde / sobra-stock) se calculaba SOLO en el navegador: se
  # veia lote por lote dentro del modal y nada del servidor podia contarla, alertarla ni
  # testearla. Y las tarjetas de Necesidades sumaban 26 sobre 28 SKUs: los 2 que faltaban
  # eran productos que VENDEN y el plan no ve por falta de mapeo.
  "tests/test_salud_cadena_necesidades.py"
  # El modal Programar decia "materias primas OK, listo para producir" contestando por UN lote
  # del maestro de formulas y sumando stock EN CUARENTENA como si fuera usable -- y sin mirar
  # los envases. Ahora contesta por los kg que se van a programar, con el stock que la
  # produccion puede consumir de verdad, y con frasco/tapa/caja/etiqueta.
  "tests/test_disponibilidad_para_kg.py"
  # La decision "30 kg cada 2 meses" no se guardaba: el modal la reconstruia midiendo los dias
  # entre los dos primeros lotes futuros, asi que al mover un lote cambiaba sola y con un solo
  # lote volvia al default. El modal gemelo del calendario SI la guardaba: la asimetria era el bug.
  "tests/test_decision_se_guarda.py"
  # Las reglas de programacion que dicto Sebastian, escritas donde se aplican: 20 dias antes de
  # agotarse (el camino "recalcular horizonte" NO la aplicaba), preferir lun/mie/vie (el helper
  # lo tenia y la cadena llamaba sin ello), y el tope de 200 kg/dia (que no existia: los
  # generadores contaban lotes, no kilos, asi que dos de 150 dejaban 300 kg en un dia).
  "tests/test_reglas_programacion.py"
  # El Calendario afirmaba cosas que nadie habia comprobado: Factibilidad decia "nada que
  # comprar" contando SOLO lo fijado a mano mientras Abastecimiento (la pestana de al lado)
  # mostraba deficit; el semaforo de Alistar envases estaba muerto (todo amarillo, una orden
  # vencida hace 5 dias igual que una al dia); Estacionalidad marcaba pico en TODOS y promediaba
  # el mes en curso como si estuviera completo; y una lista decia "todo cubierto" sin calcular.
  "tests/test_calendario_no_miente.py"
  # El calendario dejo de CARGAR ("Cannot set properties of null"): al retirar el autoplan se
  # borraron los botones y quedo vivo el codigo que los toca. El node-check NO lo ve: un
  # getElementById sobre un id inexistente es sintaxis valida y solo revienta al EJECUTAR.
  "tests/test_calendario_carga.py"
  # Los dos modales (Necesidades y Calendario) contestaban lo mismo preguntandole a endpoints
  # DISTINTOS: uno por un lote del maestro de formulas y el otro por los kg reales de la cadena.
  # Ahora comparten el calculo, y ese bloque muestra las presentaciones con la foto del envase
  # de bodega y cuantas unidades salen de cada una.
  "tests/test_modal_unificado.py"
  # La CARA del modal Programar, la que Sebastian aprobo: veredicto en una linea, diagnostico
  # comprimido a fila de numeros, la DECISION como bloque dominante, y el chequeo de materiales
  # DESPUES de decidir (antes contestaba por un kilaje que el usuario todavia no habia elegido).
  # El reordenamiento se hizo capturando el bloque en una variable, sin reescribir su contenido.
  "tests/test_modal_cuatro_bloques.py"
  # Los cinco pendientes que quedaban en cola. El que mas importa del archivo NO es de texto:
  # recorre el endpoint real de la alerta D-20 con un lote sembrado, y por eso caza lo que
  # leer el fuente no ve -- el reemplazo del titulo, hecho sin anclar, habia caido en OTRA
  # funcion 3.000 lineas antes y dejaba la alerta llamando a una variable inexistente (M96/M151).
  "tests/test_cinco_pendientes.py"
  # El modal del CALENDARIO tomo la misma cara de 4 bloques que el de Necesidades. Lo que este
  # archivo vigila no es la estetica: el reordenamiento se hizo capturando bloques en variables,
  # y un <div> de menos NO rompe la sintaxis -- el node-check pasaria verde con la pantalla
  # partida. Las cuentas de marcas conocidas y el balance de <div> son las que lo cazan.
  "tests/test_modal_calendario_cara.py"
  # La solicitud de pago de caja decia CUANTO y A QUIEN, nunca COMO. Daniela recibia una orden
  # de pago que no se puede ejecutar (transferencia sin cuenta, Nequi sin celular) y eso se
  # resolvia por WhatsApp: fuera del sistema y sin rastro. La validacion vive en el BACKEND
  # porque dos pantallas mandan al mismo endpoint. + el picker no vuelca el maestro de cuentas.
  "tests/test_caja_como_se_paga.py"
  # El tablero del CEO MENTIA en 13 numeros. El peor: /api/gerencia/dashboard-extra devolvia 500
  # en produccion por un ORDER BY con alias dentro de una expresion, asi que los 8 paneles de
  # "Metas estrategicas" llevaban meses en "Cargando...". Y `date` nunca se importo: los dias de
  # transito de TODAS las OCs daban 0 y el SGSST daba 999 (todo verde). + caja menor, que no
  # estaba en una sola linea del modulo, y los pagos a creadores con nombre en vez de dos
  # agregados (uno en cero permanente por una columna que no existe).
  "tests/test_ceo_no_miente.py"
  # Los bugs que PASAN en los tests y ROMPEN en produccion: la suite corre SQLite y produccion es
  # PostgreSQL. Una columna proyectada sin agrupar ni agregar -- SQLite elige un valor cualquiera,
  # PG rechaza. Los que estaban dentro de un `try` no daban error: dejaban la seccion VACIA, y lo
  # que no aparecia era justo lo que habia que atender (equipos con calibracion vencida, productos
  # que el planificador debia programar). + dos CAS de dinero e INVIMA: aprobar dos veces un pago
  # a creador creaba DOS ordenes, y un lote RECHAZADO se podia volver a liberar con un clic.
  # Estos tests EJECUTAN la consulta contra el esquema real: leer el SQL es lo que los dejo pasar.
  "tests/test_bugs_5ago.py"
  # El plan semanal hacia ~1.500 consultas por request (una por MP por produccion). Con 3 workers,
  # dos personas abriendolo a la vez dejaban la app entera sin atender. Lo que este test protege
  # NO es la velocidad sino que el atajo NO cambie la respuesta (M128): compara contra el helper
  # que reemplaza, con un lote EN CUARENTENA sembrado a proposito -- el plan lo cuenta porque mira
  # consumo futuro, y sin ese lote la comparacion es ciega a la diferencia que importa.
  "tests/test_plan_semanal_rapido.py"
  # Las TRES pantallas del CEO mostraban el mismo hecho con numeros distintos, y el usuario no
  # tiene forma de saber cual creer -- que es peor que no mostrarlo, porque termina desconfiando
  # de los tres. Los kg producidos se dividian por 1000 en /hoy (mostraba 0 kg), "MP bajo minimo"
  # se contaba de CUATRO formas y solo una era la canonica, "lotes por vencer" contaba movimientos
  # (un lote en tres partidas contaba tres veces) y "Registros INVIMA: 0" mentia dos veces.
  # + el guard general: ningun getElementById('gx-...') sin su id -- eso son consultas que corren
  # para nadie cada 5 minutos.
  "tests/test_ceo_pantallas_coherentes.py"
  # El tablero del CEO se puede LEER en los dos temas. Mide el contraste de cada par (fondo,
  # texto) EXTRAYENDOLOS de la pagina, no de una lista escrita a mano -- que es lo que hizo que
  # la primera version siguiera reportando fallos ya corregidos (M142). Los tres que aparecieron
  # estaban en tema CLARO, que es el default: el boton "Panel Central" daba 1.03, o sea era
  # literalmente invisible.
  "tests/test_ceo_premium.py"
  # El CEO tiene UNA sola pantalla: /gerencia y /mi-bandeja REDIRIGEN al Centro de Mando. Lo que
  # este archivo protege no es la consolidacion sino sus dos formas de romperse en silencio: una
  # pestaña sin su panel deja la pantalla EN BLANCO (el conmutador apaga todo antes de encender,
  # y no da error), y una URL vieja que muere en la nada es peor que la pantalla vieja. + el
  # guard de boton muerto mira la DEFINICION, no el nombre: renombrar la funcion y dejar el
  # onclick pasaba el test anterior, que es exactamente el bug.
  "tests/test_ceo_una_sola_pantalla.py"
  # El cierre de la auditoria: el CAS que faltaba al cerrar una NO CONFORMIDAD (dos cierres
  # simultaneos dejaban dos rastros del mismo cierre, en un registro regulado), el GROUP BY de
  # alertas-stock que revienta en PG, y la estacionalidad que re-escaneaba 24 meses en cada
  # worker frio. + deja por escrito que el CAS de la DESVIACION ya existia -- el informe lo
  # reporto como faltante y no lo era, y este test impide "arreglar" codigo sano.
  "tests/test_auditoria_cierre_5ago.py"
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
  # El legajo de envasado es UNA vista continua (las 7 secciones seguidas, como MyBatch).
  # Unir dos pantallas que comparten 18 clases CSS -6 definidas DISTINTO- se rompe en
  # silencio: una seccion que desaparece, una funcion que se pisa, un boton que apunta
  # a la nada. Nada de eso lanza un error ni lo caza el node-check.
  "tests/test_legajo_vista_continua.py"
  # El kardex sabe lo que pasa ADENTRO del lote. Lo mas importante: `ebr_ajustes_mp` YA
  # existia y solo dejaba una NOTA -- la MP agregada para corregir pH quedaba escrita en
  # el legajo y NUNCA salia del stock. Agujero de inventario invisible, porque el legajo
  # se ve completo. Incluye la devolucion pesada (que conserva el vencimiento del lote) y
  # el puente que lleva el granel real de fabricacion a envasado como teorico.
  "tests/test_kardex_ciclo_lote.py"
  # Los controles en proceso ESTANDAR son controles de verdad. Los dos gates de IPC
  # miraban solo las specs del MBR -- que NINGUN producto define -- asi que un pH marcado
  # 'No cumple' no abria desviacion, no frenaba la liberacion (reproducido: el lote salio
  # liberado) y el PDF archivado no imprimia ni uno. Fija los dos lados del trinquete:
  # bloquea la no conformidad y NO traba un lote conforme.
  "tests/test_ipc_estandar_gate.py"
  # Recepcion de envases por lineas (sin OC) · lo que llega en CAJAS y el rotulo va por
  # caja numerado. Fija ademas que la pantalla de envases NO cuente la cuarentena como
  # disponible: el canonico la excluye y la pantalla no, asi que un contenedor recien
  # recibido se veia usable antes de que Calidad lo liberara.
  "tests/test_recepcion_envases_lineas.py"
  # Recepcion de EQUIPOS: quien registra (Catalina y Luz) vs quien califica (Aseguramiento),
  # y sobre todo que un equipo PENDIENTE de calificacion NO aparezca como usable en su area.
  # Incluye que los 102 equipos que ya estaban (NO_APLICA) sigan saliendo igual.
  "tests/test_recepcion_equipos.py"
  # Libro de activos: el valor en libros se DERIVA del estado (de baja/hurto/fuera de uso no
  # suman, danado SI), la baja exige motivo y conserva la fila, el import no borra nada y NO
  # pierde filas en silencio (3 activos reales venian sin descripcion y se descartaban).
  "tests/test_libro_activos.py"
  # Consulta rapida en planta: "Verificar stock" dice DE QUE LOTE y DONDE esta cada MP (y cual
  # no se puede tocar), los lotes vencidos traen ubicacion, y la cola de calificacion de Calidad
  # la decide quien recibe (antes toda referencia nueva caia ahi y la bandeja se dejaba de mirar).
  "tests/test_consulta_rapida_planta.py"
  # El buzon de PQR que se queda MUDO avisa solo. El ultimo PQR habia entrado el 15-jun y
  # nadie se entero: una bandeja vacia se ve igual que una bandeja al dia, y la queja de un
  # cliente es un registro regulado cuyo plazo corre igual.
  "tests/test_pqr_mudo.py"
  # Un fast-path puede acelerar la respuesta; NO puede cambiarla. `ventas_diarias` (precalculada
  # por cron) se leia TODO-O-NADA: con una sola fila, las ordenes no se consultaban nunca y un
  # SKU que el cron no habia procesado -- un producto NUEVO -- daba cero ventas teniendo ordenes
  # reales. Cero ventas = velocidad cero = el motor no lo programa. Estaba en 3 lugares.
  "tests/test_fastpath_no_cambia_la_respuesta.py"
  # "Se me perdio una orden de compra" se contestaba con una teoria. El rastro lee audit_log y
  # dice en una frase si existe, si la fusionaron (y con cual) o si la borraron (quien y cuando).
  "tests/test_rastro_oc.py"
  "tests/test_mp_sin_formula.py"
  "tests/test_reconciliar_batch_record.py"
  "tests/test_unificar_codigos_batch.py"
  "tests/test_codigos_para_director_tecnico.py"
  "tests/test_agua_no_bloquea_fabricar.py"
  "tests/test_goldens_no_caducan.py"
  "tests/test_salud_formulas.py"
  "tests/test_renombrar_producto_completo.py"
  "tests/test_kardex_material.py"
  # Calidad dispone CAJA POR CAJA: de 24 cajas pueden pasar 22 y venir 2 golpeadas. Fija que
  # el rotulo de cada caja diga la verdad (y que NO se renumeren las cajas fisicas al partir
  # el movimiento) + el escaneo del codigo de barras.
  "tests/test_cajas_disposicion_calidad.py"
  # El que REGISTRA no puede APROBAR el control en proceso. Fija ademas que Aseguramiento y
  # Direccion Tecnica ENTRAN al batch record: el gate de entrada los rechazaba y por eso su
  # 2a firma y el visto bueno del DT estaban construidos y eran inalcanzables.
  "tests/test_ipc_estandar_sod.py"
  # ?La materia prima SE RECEPCIONA? El recorrido REAL por los endpoints: OC -> recepcion
  # administrativa -> cuarentena que no cuenta como stock -> F01 con el lote real al kardex
  # -> firma Part 11 -> F02 -> stock disponible. Mas los guards que ya costaron caidas.
  "tests/test_mp_recepcion_e2e.py"
  # La hoja de pesaje dice el VENCIMIENTO del lote que se esta usando (punto de uso).
  "tests/test_hoja_pesaje_vencimiento.py"
  # Un nombre de indice repetido es un indice que NO existe: el 2o CREATE IF NOT EXISTS es
  # un no-op silencioso y la tabla se queda en scan completo. Trinquete de M96.
  "tests/test_indices_no_se_pisan.py"
  # Caja menor y cargos fijos por sus endpoints reales: recibo numerado, saldo, anular que
  # CONSERVA la fila, y no pagar dos veces el mismo periodo de un cargo fijo.
  "tests/test_caja_cargos_e2e.py"
  # El rotulo de pesaje reparte por LOTE con el MISMO FEFO que el descuento, y lo que no
  # alcanza se declara faltante. Antes sacaba UN lote con el peso completo aunque ese lote
  # no lo tuviera: un registro regulado diciendo lo que no es.
  "tests/test_rotulo_pesaje_reparto_lotes.py"
  # Los 15 numeradores sin CAST(SUBSTR): ese patron revienta en PG con cualquier sufijo y ya
  # tumbo la creacion de OC de todo un ano. Incluye el guard de que el helper este en scope
  # (usarlo sin importarlo es un NameError = 500 silencioso).
  "tests/test_correlativos_pg_safe_todos.py"
  # Tres endpoints que mutaban sin permiso de rol · probados en los DOS sentidos (el dueno
  # entra, el ajeno no): poner un permiso sin probar el borde cambia un control por una traba.
  "tests/test_permisos_barrido_30jul.py"
  # La verificacion de MP muestra LOS LOTES (los usables y los bloqueados con su motivo). El
  # motor sumaba bien; lo que faltaba era decirlo: un lote en cuarentena se veia como si no
  # existiera y el operario, con dos lotes enfrente, leia "sin stock".
  "tests/test_lotes_visibles_verificacion.py"
  # Por que una MP no sale en Abastecimiento: la tabla lista lo que las producciones
  # PROGRAMADAS van a consumir, no un catalogo. Una ausencia sin explicacion se lee como
  # un error del sistema aunque sea correcta, y cuando SI es un error se lee como normal.
  "tests/test_diag_por_que_no_sale.py"
  # La correccion de colisiones del 15-jul quedo de UN SOLO LADO: agrego el descuento al codigo
  # correcto y nunca lo devolvio al equivocado, asi que esos materiales muestran menos stock del
  # que hay en el estante. La devolucion es net-zero, al mismo lote, con su vencimiento, y con
  # tope duro (nunca devolver mas de lo que la correccion movio = inventar material).
  "tests/test_colisiones_net_zero.py"
  # El vigia diario de materias primas: las 5 firmas graves tienen que dar CERO. La
  # colision de codigos estuvo tres semanas a la vista y nadie la vio porque todo se
  # verificaba abriendo un endpoint. Cada firma probada con dientes.
  "tests/test_salud_materias_primas.py"
  # Re-apuntar un ingrediente de UNA formula (la decision de Alejandro sobre la centella).
  # El reapuntar-formula que ya existia es BLANKET y aca romperia Hydrapeptide y la Esencia,
  # que si llevan triterpenos. Incluye el guard de que un PUENTE activo sobre el destino
  # BLOQUEA: si no, la formula diria un codigo y el descuento seguiria sacando otro.
  "tests/test_editar_formula_items.py"
  # Un INCI que comparten MUCHOS materiales no identifica a ninguno. PARFUM lo comparten 10
  # fragancias y solo una se compro alguna vez: el resolver mandaba la demanda de la Fresa
  # Cremosa al Pistacho, asi que EOS compraria la fragancia equivocada. Golpea a las MP que
  # NUNCA se compraron, que son justo las que tienen que salir para comprarlas.
  "tests/test_resolver_inci_generico.py"
  # Al buzon de PQR solo entra lo que ES un PQR. El disparador de GHL entra con CADA respuesta
  # del cliente, asi que la bandeja se lleno de "Buena tarde" y "Perfecto": un registro
  # REGULADO lleno de saludos no queda incompleto, queda FALSO. Lo descartado NO se pierde.
  "tests/test_pqr_solo_lo_que_es_pqr.py"
  # Un MBR aprobado es INMUTABLE, asi que al renombrar un producto queda con el nombre viejo y
  # crear_ebr_desde_mbr deja de encontrarlo: el producto NO puede generar su legajo. El rename
  # ahora DEJA el puente, y con dos candidatos ambiguos no elige (dato regulado).
  "tests/test_mbr_sobrevive_al_rename.py"
  # Desactivar un puente cambia de QUE codigo sale el material: es mutacion regulada y se
  # hacia sin dejar rastro. El audit guarda a donde apuntaba, o no se puede revertir.
  "tests/test_puente_desactivar_audita.py"
  # La copia de la base FUERA del proveedor (tarea B-01 del ASG-PRO-014). Los documentos
  # regulados ya viajaban a R2; los DATOS vivos existian en un solo proveedor, y el codigo que
  # debia cubrirlo estaba MUERTO (do_backup sale en su primera linea con PostgreSQL).
  # Lo que se protege no es "el respaldo corre" sino que se pueda VOLVER A LEER: el test de ida
  # y vuelta vuelca, cifra, descifra y carga en una base nueva comparando fila por fila.
  "tests/test_respaldo_base.py"
  # Lo que se registro en PAPEL durante un apagon entra al expediente del lote, y entra diciendo
  # la verdad: la fecha del HECHO sale del papel y la de CARGA la pone el servidor. Si se pudiera
  # cargar como contemporaneo, una contingencia legitima se volveria un registro falso.
  "tests/test_contingencia.py"
  # audit_log solo admite el cursor como posicional. Habia SIETE llamadas posicionales vivas en
  # admin.py -- ninguna dejaba rastro y todas devolvian 500 en la ultima linea del endpoint,
  # despues de haber hecho el trabajo. El golden no abre paginas de admin, asi que nadie las vio.
  "tests/test_audit_log_firma.py"
  # El expediente tiene que poder leerse dentro de diez anos con un navegador y nada mas. El
  # archivo conserva los documentos, pero saber CUALES componen el expediente de un lote sale de
  # la base: sin indice, perder el sistema deja miles de archivos sin forma de saber cual es de
  # quien. Y el indice enumera lo que FALTA: uno que solo liste lo que salio bien se lee como
  # completo justo cuando le falta lo unico que importaba senalar.
  "tests/test_exportar_expediente.py"
  # Cuales presentaciones FRENAN una produccion real. El resumen contaba todas las filas por
  # igual, asi que lo que traba el cierre del batch record se mezclaba con lo que puede
  # esperar, y una lista que no cierra deja de mirarse.
  "tests/test_mee_que_frena.py"
  # El tono NO vive siempre en el mismo componente: en el lip serum lo lleva el frasco (uno
  # por color) y en el blush la etiqueta (un solo frasco para los ocho). Una expansion que
  # asuma uno deja al otro sin resolver, y desde afuera se ve igual que si no hiciera nada.
  "tests/test_tonos_diagnostico.py"
  # Ocho tonos que comparten volumen y frasco salian ocho tarjetas IDENTICAS en el reparto
  # del lote: sin saber cual es cual, el numero no se puede revisar. El dato ya viajaba del
  # backend; faltaba pintarlo. Se verifican las DOS puntas.
  "tests/test_presentacion_identificada.py"
  # Maestro de lotes (lo unico funcional que MyBatch tenia y EOS no armaba): por lote,
  # cuantas unidades debian salir de ese granel, cuantas se envasaron y cuantas se
  # liberaron. Un lote fisico es UN renglon aunque tenga tres legajos, la teorica se
  # reparte por VOLUMEN, y sin granel medido se declara en vez de estimarse.
  "tests/test_maestro_lotes.py"
  # El director tecnico configura el despeje y los controles, como en MyBatch, pero el
  # texto de lo YA FIRMADO nunca cambia y una clave firmada no se recicla. Sin configurar,
  # todo sigue igual que antes: la tabla nace vacia a proposito.
  "tests/test_checklists_configurables.py"
  # La matriz de permisos y la puerta de cada modulo tienen que decir LO MISMO. Habia seis
  # personas a las que el menu les ofrecia un modulo y la pagina les contestaba "sin
  # acceso": dos gates del mismo modulo con criterios distintos.
  "tests/test_matriz_permisos_coherente.py"
  # El audit trail en lenguaje humano (MyBatch muestra el JSON crudo de Django). El crudo
  # sigue viajando como prueba, lo que no se pudo traducir se declara, y el TOTAL se cuenta
  # aparte del recorte -el reporte viejo decia "total: 500" con 3.000 cambios en el rango.
  "tests/test_audit_trail_legible.py"
  # Que falta para reemplazar MyBatch, medido contra la base: un batch record completo pero
  # OCULTO y con los controles apagados se ve, desde afuera, igual que uno que no existe.
  "tests/test_estado_reemplazo_mybatch.py"
  # El aviso de contrasenas miraba SOLO las env vars y desde ahi afirmaba que esos usuarios
  # "NO pueden entrar" -- falso para quien tiene su clave en users_passwords, que es lo que
  # el login mira primero. Un aviso HIGH que miente en cada arranque ensena a ignorar todos.
  "tests/test_aviso_claves_no_miente.py"
  # La etiqueta y la caja del cliente eran una marca sin efecto: sin el CODIGO no se compra,
  # ni se alista, ni se descuenta. Ahora el lote lo dice, y lo que falta definir se DECLARA
  # en vez de adivinarse con un codigo parecido (que es como se compra lo de otro cliente).
  "tests/test_material_cliente_lote.py"
  # El enlace de facturacion se SUGIERE cuando el cruce es inequivoco y lo confirma una
  # persona: enlazar mal deja a un cliente viendo las facturas de otro.
  "tests/test_enlace_facturacion_sugerido.py"
  # El rotulo F02 sale PARA FIRMAR: traia el ultimo ciclo del area, que en produccion era
  # una demo de junio, asi que todas las salas salian prefirmadas por quien no ejecuto esa
  # limpieza. Y ahora pregunta QUE EQUIPOS se van a usar antes de imprimir.
  "tests/test_rotulo_limpieza_firma_y_equipos.py"
  # La linea de tiempo del legajo hablaba SIEMPRE de fabricacion ("Batch Record Bulk",
  # "Pesaje de Materias Primas") aunque el lote fuera de envasado -- y es la pantalla a la
  # que llega Calidad desde su cola de controles. Incluye verificacion del DOM real.
  "tests/test_legajo_habla_de_su_fase.py"
  # Los legajos DEMO contaban como produccion: Envasado mostraba "1 orden abierta, 1
  # atrasada hace 26 dias" y era un demo que nadie va a cerrar nunca.
  "tests/test_demos_no_cuentan_como_produccion.py"
  # VELOCIDAD (15-ago) · 18 pantallas se refrescaban solas cada 20-300s sin mirar si la
  # pestana estaba visible: varias pestanas abiertas multiplicaban el trafico contra los
  # TRES workers. El guard ejercita el comportamiento en un navegador simulado.
  "tests/test_pollers_no_gastan_worker_oculto.py"
  # VELOCIDAD (15-ago) · la cola de decisiones leia el historial y el estado del creador de
  # a UNO por pago (22 de sus 55 consultas). El tope de 60 es POR CREADOR: con un limite
  # global las alertas de doble pago se apagarian para los creadores con mas movimiento.
  "tests/test_precarga_alertas_creadores.py"
  # VELOCIDAD (15-ago) · /compras servia 685 KB por carga y 551 KB eran JS incrustado (no
  # cacheable). Ahora va como archivo aparte: el guard exige que la pantalla siga completa
  # (ningun boton llamando a una funcion que ya no existe) y que los datos por usuario NO
  # viajen dentro del archivo cacheado.
  "tests/test_compras_bundle.py"
  # REVISION DE PLANTA (16-ago) · el widget del chat y el de la campana definian las MISMAS
  # funciones y se cargan juntos en ocho pantallas: ganaba la ultima y el contador de
  # mensajes sin leer no se pintaba nunca. El guard mira lo que el navegador CARGA.
  "tests/test_widgets_no_se_pisan.py"
  # Las pantallas de Planta no se contradicen sobre el mismo lote (cada test cubre su pieza;
  # esto cubre la costura entre pantallas).
  "tests/test_planta_no_se_contradice.py"
  # El legajo nace con los kg que el usuario fijo, no con un default generico del MBR: el
  # test existia desde el 30-jun y no corria en ningun gate (M95).
  "tests/test_ebr_objetivo_m67.py"
  # El legajo dice QUIEN, no el cargo (16-ago) · y nunca el nombre de OTRA persona: emparejar
  # por nombre de pila resolvia "sebastian" al operario de envasado, o sea una firma falsa.
  "tests/test_legajo_dice_quien_fue.py"
  # El numero de lote como lo numera la planta: anio + dia juliano + consecutivo (16-ago).
  # Verificado contra los batch records firmados: el 11-jun-2026 da 261621, que es el lote
  # real de ANIMUSLASH. Si el sistema numera distinto, el legajo no coincide con el rotulo.
  "tests/test_lote_juliano.py"
  # Liberar un lote: el aviso explica y deja escribir la justificacion AHI (16-ago).
  # Antes salia el cuadro gris del navegador, que frena y no ofrece la salida.
  "tests/test_liberar_pide_la_justificacion.py"
  # Quien firma el cierre del batch record (16-ago), corregido contra el sistema documental de
  # la empresa: las verificaciones son de Control de Calidad (analista y jefe), el Jefe de
  # Produccion REALIZA y por eso no da su propia 2a firma, y el visto bueno del Director
  # Tecnico va con el PRODUCTO TERMINADO, no en fabricacion ni en envasado.
  "tests/test_quien_firma_el_cierre.py"
  # Quien recibe la materia prima NO la libera (Res. 2214/2021 art. 10) + los topes de compra
  # de Catalina. Llevaba tiempo rojo fuera del gate con la expectativa de junio.
  "tests/test_catalina_sin_tope.py"
  # La pantalla de Calidad carga sus helpers de CSRF y su paginacion, y NINGUN POST que muta
  # sale sin token. Se mira el HTML + su bundle: el JS dejo de viajar inline el 16-ago.
  "tests/test_calidad_ux.py"
  # Las rubricas manuscritas que se estampan en los documentos regulados (Part 11 §11.50) y el
  # offboarding: una fila con activo=0 cierra la puerta aunque quede la clave en el entorno.
  "tests/test_firmas_usuarios.py"
  # El visto bueno del Director Tecnico vive en la pantalla del PRODUCTO TERMINADO, el camino de
  # la firma dice lo mismo que el de la accion, y la verificacion de Calidad va POR ETAPA y no
  # renglon por renglon (Sebastian 16-ago: "entonces por etapa").
  "tests/test_visto_bueno_dt_acondicionamiento.py"
  # Abrir un legajo: el numero de lote se PROPONE con la numeracion de la planta y se puede
  # cambiar; si no se puede calcular queda vacio con el motivo, nunca un numero inventado.
  # Y los tres prompt() del navegador se fueron (Sebastian 16-ago).
  "tests/test_nuevo_legajo_lote_propuesto.py"
  # El ciclo de la sala CIERRA: limpiar y verificar la devuelve a LIBRE, una sala con lote
  # adentro NO se libera, hay por donde llegar al despeje, y el demo nace con materia prima.
  "tests/test_la_limpieza_libera_el_area.py"
  # El plano dibuja la planta REAL (la distribucion que dibujo Sebastian), dice que hace el
  # click en cada sala segun su estado, y calcula los tiempos con el ancla UTC explicita.
  "tests/test_plano_de_planta.py"
  # El legajo DEMO se camina de punta a punta por UNA persona, sin pedir firmas ni
  # autorizaciones ajenas -- y un lote REAL las sigue pidiendo todas.
  "tests/test_demo_se_camina_solo.py"
  # El legajo de envasado muestra el envase que ELIGIO Compras para ese lote (con su foto), no
  # el habitual del catalogo: la compra y el descuento ya lo honraban y la pantalla no.
  "tests/test_envase_que_eligio_compras.py"
  # Las herramientas del Director Tecnico viven en SU modulo, y ningun enlace lleva a una ruta
  # que no existe (se valida contra el url_map real).
  "tests/test_config_direccion_tecnica.py"
  # "Productos con instructivo aprobado" cuenta los que PUEDEN abrir legajo: antes sumaba los
  # instructivos de productos DESCONTINUADOS y el punto salia verde con productos faltando.
  "tests/test_cuantos_pueden_abrir_legajo.py"
  # Tres secciones de Calidad/Aseguramiento devolvian VACIO por una columna que no existe, y un
  # vacio se lee igual que "no hay nada que hacer" (auditorias programadas, muestreo micro, las
  # OCs con que se pago una calibracion) + la limpieza de equipo que se cerraba sin dejar rastro.
  "tests/test_lo_que_calidad_no_veia.py"
  # "Aprobar Etiqueta" vive en la orden de acondicionamiento (MyBatch) y en EOS solo se llegaba
  # por el modal del dashboard. Y el guard fija el CONTRATO: la firma rapida va sobre
  # ebr_ejecuciones y el aprobador la rechazaria, o sea boton visible y aprobacion imposible.
  "tests/test_aprobar_etiqueta_acondicionamiento.py"
  # Maestro de lotes (lote x presentacion, teoricas vs liberadas): lo ultimo que MyBatch tenia
  # y EOS no armaba. Fija que 'liberadas' salga de lo que ENTRO al stock (no de lo que queda),
  # que un cero declare su motivo, y que el total no se cuente sobre la ventana recortada.
  "tests/test_maestro_de_lotes.py"
  # La alerta de MP de China (60 dias de lead time, escala a CRITICO) NUNCA se disparo: el set
  # salia vacio porque la consulta pedia `SELECT id` y maestro_mps se llavea por codigo_mp.
  "tests/test_alerta_mp_china.py"
  # PRE-VUELO de `brd_visible`: cuando el registro de lote deje de nacer oculto, el piso tiene
  # que llegar a CADA pantalla del batch record y ninguna puede compartir URL con otra (una
  # queda muerta y el listado manda al lote ajeno). Abre las 19 paginas con las 11 personas
  # del piso -- jose y milton incluidos, que hasta hoy el harness no podia loguear.
  "tests/test_preflight_brd_visible.py"
  # El gate corre en paralelo repartiendo por ARCHIVO (924s -> 411s). El guard existe porque
  # la nota anterior afirmaba que el corazon "no paralela bien" y esa frase, sin nada que la
  # midiera, es lo que haria que alguien lo devuelva a la serie.
  "tests/test_gate_paralelo.py"
  # Acondicionamiento: el legajo y la pantalla vieja descontaban el MISMO envase por separado.
  # Reproducido por los dos endpoints (2 salidas donde habia 100 uds). Un doble descuento no da
  # sintoma -- el kardex simplemente dice menos de lo que hay -- asi que solo lo caza esto.
  "tests/test_acondicionamiento_doble_descuento.py"
  # Estaba FUERA de todo gate y llevaba tiempo en rojo (el demo pasó a armar las tres fases).
  "tests/test_acondicionamiento_cierre.py"
  # El demo se camina hasta envasado y acondicionamiento POR LOS ENDPOINTS REALES, y ahi se
  # ve si las pantallas se llenan. Fue lo que destapo que el Material de Empaque del legajo
  # de acondicionamiento nunca mostro nada (json.loads con el nombre equivocado, tapado por
  # un except mudo): no lo veia nadie porque la fase no se habia caminado todavia.
  "tests/test_demo_camina_envasado_y_acond.py"
  "tests/test_demo_se_puede_caminar_dos_veces.py"
  "tests/test_conciliacion_no_contradice_al_legajo.py"
  "tests/test_acondicionamiento_legajo.py"
  "tests/test_material_empaque_acondicionamiento.py"
  "tests/test_programar_cualquier_producto.py"
  "tests/test_indicadores_despachos.py"
  "tests/test_sin_rastro_de_ia_global.py"
  "tests/test_pantallas_sanas.py"
  "tests/test_cron_hora_colombia.py"
  "tests/test_reporte_semanal_llega_solo.py"
  # UN lote atravesando las TRES fases en orden. Hay E2E de cada fase por separado, pero lo que
  # vive ENTRE ellas no lo ejercia nadie -- y ahi estaban los tres bugs del 17-ago: el cierre no
  # veia las unidades que registro la planta, el enlace al paso siguiente volvia vacio en el caso
  # normal, y frasco y tapa salian del kardex DOS veces (60 donde se envasaron 30).
  "tests/test_lote_completo_tres_fases.py"
  # La pestana de acondicionamiento decia menos de lo que sabia: una orden registrada por la via
  # SIMPLE entraba sin `unidades_total` (tarjeta "sin unidades registradas" con el trabajo hecho,
  # KPI en cero) y la tarjeta hablaba de "g de granel" en una fase donde ya no hay granel. Y el
  # formulario de EXCEPCION ocupaba mas pantalla que la cola, que es el camino normal.
  "tests/test_orden_simple_cuenta_sus_unidades.py"
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
elif [ "$MODE" = "--rapido" ] || [ "$MODE" = "rapido" ]; then
  # Golden SIEMPRE (la red de seguridad) + lo que el cambio puede romper. Se corre en paralelo:
  # medido hoy, 245 golden pasan de 4m23s a 1m51s con 8 procesos, y el arranque de cada worker
  # bajo de 10,6 s a 0,8 s con la plantilla de la base.
  _SEL=$(_seleccion_rapida | sort -u | grep -E '^tests/.*\.py$' || true)
  TESTS=("tests/test_golden_paths.py")
  if [ -n "$_SEL" ]; then
    while IFS= read -r _t; do
      [ -n "$_t" ] && [ "$_t" != "tests/test_golden_paths.py" ] && TESTS+=("$_t")
    done <<< "$_SEL"
  fi
  PARALELO="-n 8 --dist load"
  echo "    modo RAPIDO · golden + ${#TESTS[@]} archivo(s) relacionados con lo que cambio"
  echo "    ⚠ NO corre el corazon completo (186 archivos · ~15 min). Antes de una tanda grande,"
  echo "      o si tocaste el descuento/abastecimiento, corre: bash scripts/guardian.sh --quick"
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
  # Son 20 archivos independientes: reparten perfecto por archivo.
  PARALELO="$PARALELO_CORAZON"
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
  # 17-ago: 924 s -> 411 s repartiendo por ARCHIVO (ver la nota de PARALELO arriba).
  PARALELO="$PARALELO_CORAZON"
fi

# Ejecutar · pipefail para que el exit code de pytest llegue al if
# (sin pipefail, el pipe a tail siempre exit 0 y el bug se traga).
set -o pipefail
START=$(date +%s)
# El hash del arbol se toma ANTES de correr, porque es el arbol que la suite VA A PROBAR.
# 5-ago: se tomaba al final, y una corrida de 18 min en la que se sigue editando terminaba
# sellando archivos que la suite nunca vio -- el mismo hueco de M143 por el otro lado. Si el
# arbol cambio durante la corrida, el sello no coincide con el de ahora y el hook vuelve a
# correr la suite, que es exactamente lo que tiene que pasar.
_TMPIDX_PRE="$(mktemp)"
GIT_INDEX_FILE="$_TMPIDX_PRE" git read-tree HEAD 2>/dev/null
GIT_INDEX_FILE="$_TMPIDX_PRE" git add -A 2>/dev/null
_TREE_PRE=$(GIT_INDEX_FILE="$_TMPIDX_PRE" git write-tree 2>/dev/null || echo "")
rm -f "$_TMPIDX_PRE"
if "$PYTHON_BIN" -m pytest "${TESTS[@]}" $PARALELO -q --tb=line 2>&1 | tail -10; then
  END=$(date +%s)
  echo ""
  echo "✅ GUARDIAN APROBÓ · golden paths verdes en $((END - START))s"
  echo "    push permitido."
  echo ""
  # Sello del ARBOL que aprobó (3-ago · el gate corría DOS veces por despliegue: una a mano y
  # otra en el hook del push, sobre el mismo árbol y sin agregar nada · ~17 min duplicados).
  # El hash del árbol es exacto: si cambia un byte de un archivo, cambia el hash, y el hook
  # vuelve a correr la suite completa. No es un atajo: es no repetir la MISMA verificación.
  # El hash va sobre los ARCHIVOS EN DISCO (indice temporal), que es lo que la suite acaba de
  # probar. Con `git write-tree` a secas seria el del indice, y un cambio sin `git add` dejaria
  # el sello valido para un codigo que nunca se testeo.
  # Se sella el arbol de ANTES de correr (el que se probo), no el de ahora: si alguien edito
  # durante los 18 minutos, ese codigo no lo vio nadie y no puede quedar aprobado.
  _TREE="$_TREE_PRE"
  _TREE_POST="$( { _t="$(mktemp)"; GIT_INDEX_FILE="$_t" git read-tree HEAD 2>/dev/null; \
                   GIT_INDEX_FILE="$_t" git add -A 2>/dev/null; \
                   GIT_INDEX_FILE="$_t" git write-tree 2>/dev/null; rm -f "$_t"; } )"
  if [ -n "$_TREE_POST" ] && [ "$_TREE_POST" != "$_TREE" ]; then
    echo "    ⚠ el arbol CAMBIO durante la corrida · se sella lo que se probo, no lo de ahora"
    echo "      (el proximo push vuelve a correr la suite completa · asi debe ser)"
  fi
  if [ -n "$_TREE" ]; then
    mkdir -p "$REPO_ROOT/.git/eos"
    printf '%s %s
' "$_TREE" "$(date +%s)" > "$REPO_ROOT/.git/eos/gate-ok"
  fi
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
