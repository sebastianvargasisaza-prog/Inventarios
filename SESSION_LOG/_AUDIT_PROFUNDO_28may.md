# Auditoría profunda multi-agente · 28-may-2026

16 finders por dominio + verificación adversarial. **64 hallazgos · 54 confirmados · 10 refutados.** 80 agentes, ~4.2M tokens.


## P0 (1)

### P0.1 [rrhh-financiero/data-correctness] Comprobante de pago y export Excel calculan nómina MENSUAL completa ignorando dias_trabajados, mientras el endpoint de pantalla calcula QUINCENAL prorrateado — netos inconsistentes entre lo que se ve, lo que se imprime y lo que se exporta
**Ubicación:** `api/blueprints/rrhh.py:410-412 (export) y 483-485 (comprobante) vs 244-251 (pantalla)` · confianza alta

**Por qué es bug:** El mismo período de nómina produce tres netos distintos: la pantalla muestra ~mitad del salario (quincenal prorrateado), pero el comprobante de pago impreso y el Excel exportado muestran el salario MENSUAL completo (sal entero, aux entero, descuento 4% sobre salario mensual). El comprobante es el documento legal que recibe el empleado y el Excel es lo que se rutea a Tesorería/Contadora para pagar; ambos reportan ~el doble del neto real quincenal y además ignoran por completo dias_trabajados (incapacidades/ingresos a mitad de quincena no se descuentan). Esto causa sobre-pago directo y un comprobante laboral que no concuerda con la nómina del sistema (riesgo laboral/contable).

**Fix propuesto:** Unificar la fórmula de nómina en un único helper (p.ej. _calc_fila_nomina(sal, dias, aux, vhe, bonos, otros, periodo)) que respete quincenal+prorrateo por dias/15, y llamarlo desde los tres endpoints (pantalla, export y comprobante). El comprobante y el export deben usar sal_prop = round(sal/2 * dias/15) y aux prorrateado, exactamente igual que la pantalla.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. El modelo de nómina es QUINCENAL (comentario línea 239 "Quincenal: base de pago es la mitad del salario mensual", campo salario_quincenal, periodo formato YYYY-MM-Q1/Q2 con es_q2). El endpoint de pantalla (rrhh.py:240-251) calcula correctamente: sal_q=round(sal/2), sal_prop=round(sal_q*dias/15), aux=round(AUX/2) prorrateado, descuentos 4% sobre sal_prop quincenal prorrateado, neto = sal_prop+aux_prop+... En cambio el export Excel (rrhh.py:408-412) usa aux=AUX entero, ds=round(sal*0.04) y dp=round(sal*0.04) sobre el salario MENSUAL completo, y neto = sal + aux + vhe + bonos - ds - dp - otros usando sal mensual entero; dias se lee (línea 408, default 30) y hasta se imprime en la columna "Dias" (línea 416) pero NUNCA entra al cálculo del neto. El comprobante (rrhh.py:477-485) es idéntico: aux=AUX entero, ds/dp sobre sal mensual, neto sobre sal mensual, dias ignorado. Resultado: el mismo periodo produce tres netos distintos — la pantalla ~la mitad (quincenal prorrateado), pero el comprobante legal impreso y el Excel que va a Tesorería/Contadora muestran el doble (mensual completo) e ignoran por completo dias_trabajados, por lo que incapacidades/ingresos a mitad de quincena no se descuentan. Esto causa sobre-pago directo y un comprobante laboral que no concuerda con la nómina del sistema. No es falso positivo: el FP confirmado solo valida que la TASA 4% salud/pensión es correcta como aporte del empleado (cierto), pero aquí el defecto es la BASE mensual vs quincenal prorrateada y la omisión de dias. Único matiz de confianza: depende de que el modelo intencional sea quincenal, lo cual el propio código confirma en múltiples lugares, así que la pantalla es la fórmula canónica y export+comprobante son los erróneos.

</details>

---


## P1 (21)

### P1.1 [admin/data-correctness] anular_movimiento invierte mal los movimientos tipo 'Ajuste -' / 'Ajuste +' y duplica el delta en vez de neutralizarlo
**Ubicación:** `api/blueprints/admin.py:14290` · confianza alta

**Por qué es bug:** El sistema usa tipos 'Ajuste +' (suma cantidad) y 'Ajuste -' (resta cantidad) — animus.py:1341 los crea y el query canonico _get_mp_stock (programacion.py:660-666) los trata asi. anular_movimiento solo distingue 'Salida' vs el resto: al anular un movimiento 'Ajuste -' (que resta cantidad), genera tipo_contra='Salida' que RESTA otra vez la misma cantidad, duplicando el deficit en lugar de revertirlo (deberia crear una Entrada). Al anular un 'Ajuste +' acierta solo por coincidencia. Resultado: drift de stock de MP introducido por una operacion cuya proposito declarado es 'llevar saldo a 0' (caso MP00112 documentado en el docstring). Viola la invariante de stock=SUM(movimientos) y corrompe el kardex INVIMA.

**Fix propuesto:** Determinar el efecto neto del movimiento original sobre el stock (Entrada/Ajuste +/Ajuste = +cantidad; Salida/Ajuste - = -cantidad) y crear el contra-movimiento con el efecto opuesto exacto, p.ej. mapear tipo_contra a 'Salida' si el original sumaba y 'Entrada' si restaba, cubriendo explicitamente 'Ajuste -' y 'Ajuste +' en la logica.

<details><summary>Veredicto del verificador</summary>

CONFIRMADO. admin.py:14290 usa `tipo_contra = 'Entrada' if (orig['tipo'] == 'Salida') else 'Salida'`, que solo distingue 'Salida' del resto. El tipo 'Ajuste -' es real y se escribe en animus.py:1341 (`tipo_mov = 'Ajuste +' if diferencia > 0 else 'Ajuste -'`, guardando siempre `cantidad_abs` positiva). El query canónico de stock (programacion.py:660-666, replicado en inventario.py y compras.py) trata 'Ajuste -' como RESTA (-cantidad) y 'Ajuste +'/'Ajuste'/'Entrada' como SUMA (+cantidad). Tabla de verificación con cantidad siempre positiva: Salida(−c)→Entrada(+c)=0 OK; Entrada(+c)→Salida(−c)=0 OK; 'Ajuste +'(+c)→Salida(−c)=0 OK por casualidad del else; 'Ajuste'(+c)→Salida(−c)=0 OK; pero 'Ajuste -'(−c)→cae al else→Salida(−c)→neto −2c, DUPLICA el déficit en vez de neutralizarlo (debería generar 'Entrada'). Esto viola la invariante dura stock=SUM(movimientos) y corrompe el kardex INVIMA con un movimiento que el audit_log marca como anulación legítima. El docstring del propio endpoint declara como caso de uso 'llevar saldo a 0' corrigiendo movimientos de ajuste fantasma (MP00112 lote AJUSTE-4), justo el escenario donde es probable encontrar 'Ajuste -'. La misma falla de patrón existe en inventario.py:9033 (`'Salida' if tipo=='Entrada' else 'Entrada'`), que al anular un 'Salida' o un 'Ajuste -' produciría 'Entrada' — ahí 'Ajuste -' por casualidad sí se neutraliza, pero 'Ajuste +' se duplicaría; ambas funciones comparten la raíz: no mapean explícitamente el efecto neto de los 4 tipos de Ajuste. Severidad P1 (no P0): es endpoint admin-only (_require_admin, ADMIN_USERS) disparado manualmente, y el caso más común documentado (anular Salida fantasma) funciona bien; pero la corrupción es silenciosa, audit-firmada y de datos de inventario regulado. Fix: derivar el efecto neto del original (Entrada/Ajuste +/Ajuste = +; Salida/Ajuste - = −) y crear el contra con efecto opuesto, cubriendo 'Ajuste -' y 'Ajuste +' explícitamente.

</details>

---

### P1.2 [admin/data-correctness] import-inventario-envase registra disminuciones de stock MEE como 'Ajuste' POSITIVO (abs), generando drift en el ledger movimientos_mee
**Ubicación:** `api/blueprints/admin.py:13159` · confianza alta

**Por qué es bug:** El query que reconstruye stock MEE desde movimientos (admin.py:12684 y la reconciliacion drift admin.py:11549/12684) trata tipo='Ajuste' como POSITIVO (suma cantidad). Aqui se inserta abs(diferencia) siempre positiva incluso cuando el stock BAJA (it['stock'] < stock_anterior). Esto hace que SUM(movimientos_mee) suba cuando deberia bajar -> drift de 2x|diff| respecto a stock_actual persistido. reconciliar_mee (admin.py:21963-21970) confirma el contrato correcto: inserta 'Ajuste' con cantidad=drift CON SIGNO. El import rompe ese contrato e introduce el mismo drift que el endpoint limpiar-drift-mee intenta corregir.

**Fix propuesto:** Insertar el delta con signo: usar (it['stock'] - stock_anterior) en vez de abs(...), igual que reconciliar_mee; o emitir tipo 'Ajuste +'/'Ajuste -' segun el signo y mantener cantidad positiva, consistente con el CASE de admin.py:12684-12685.

<details><summary>Veredicto del verificador</summary>

Confirmado en código real. admin.py:13159-13164 inserta movimientos_mee con tipo='Ajuste' y cantidad=abs(it['stock']-stock_anterior) — siempre positivo, incluso cuando el stock BAJA. El contrato del ledger MEE es inequívoco en todo el archivo: tipo='Ajuste' (sin signo +/-) se SUMA. Ver admin.py:12684 (Entrada,Ajuste +,Ajuste → +cantidad), 21943 (reconciliar_mee: WHEN tipo='Ajuste' THEN cantidad), 11604, 15024, etc. El patrón canónico de inserción está en reconciliar_mee admin.py:21963-21967, que inserta 'Ajuste' con cantidad=drift CON SIGNO (drift puede ser negativo). El import rompe ese contrato. Impacto concreto: el UPDATE (línea 13151) deja stock_actual = nuevo valor (correcto, menor), pero el ledger recibe +abs(diff), de modo que SUM(movimientos) = saldo_previo + |disminución|. El desfase resultante entre stock_actual persistido y SUM(movimientos) es de 2*|diff| en cada disminución. Esto coincide exactamente con la invariante dura del dominio ('un movimiento Ajuste guarda DELTA con signo; si un query/inserción trata Ajuste siempre como suma de un valor absoluto cuando debe restar, ES BUG'). Además el endpoint de reconciliación (21943) lee 'Ajuste' como positivo, por lo que no puede auto-sanar estos casos: para corregir hacia abajo habría que usar 'subir_calculado' con drift negativo o 'bajar_calculado'. No es falso positivo: no está protegido en otro lado y el import es una mutación manual real de inventario MEE. Fix correcto: usar (it['stock']-stock_anterior) con signo, igual que reconciliar_mee, o emitir 'Ajuste +'/'Ajuste -' según el signo. P1 apropiado: drift silencioso del ledger de envases, recuperable pero corrompe la reconciliación; no es P0 porque stock_actual persistido queda correcto y no hay pérdida dura ni crash.

</details>

---

### P1.3 [admin/regulatory] influencers-reset-pendientes hace DELETE masivo de pagos/SOL/OC sin audit_log
**Ubicación:** `api/blueprints/admin.py:11986` · confianza alta

**Por qué es bug:** Borra en bloque pagos_influencers, OCs y SOLs (mutaciones de OC/SOL que MEMORY/CLAUDE.md marcan como audit OBLIGATORIO) sin ningun audit_log ni snapshot. Es justo el tipo de borrado masivo que el endpoint hermano influencers-limpieza (admin.py:11941) SI auditó tras el incidente del 19-may ('imposible disputar borrado posterior'). Aqui no queda rastro de que OCs/SOLs/pagos se eliminaron ni de sus montos, impidiendo trazabilidad/recuperacion y disputa.

**Fix propuesto:** Capturar snapshot (numeros, montos, estados) de pagos/SOL/OC a borrar ANTES del DELETE y escribir audit_log(accion='ADMIN_RESET_PENDIENTES_INFLUENCERS', antes=snapshot, ...) dentro de la misma transaccion, igual que en influencers-limpieza.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo admin.py:11985-12054. La función admin_influencers_reset_pendientes ejecuta DELETE en bloque sobre pagos_influencers (12003), ordenes_compra_items (12025), ordenes_compra (12029), solicitudes_compra_items (12038) y solicitudes_compra (12042), terminando en conn.commit(); conn.close() (12047) SIN ningún audit_log ni snapshot. Verifiqué con Grep que no hay audit_log entre las líneas 11986 y 12054: la última llamada previa es en 11966 (endpoint hermano influencers-limpieza) y la siguiente recién en 12474. El endpoint hermano influencers-limpieza (11940-11982) SÍ captura snapshot (id, influencer, numero_oc, valor, estado) y escribe audit_log ADMIN_LIMPIEZA_PAGOS_INFLUENCERS ANTES del DELETE, agregado el 25-may tras el incidente documentado 'imposible disputar borrado posterior'. CLAUDE.md/MEMORY marcan audit_log como OBLIGATORIO en toda mutación de OC/SOL/inventario; aquí se borran OCs y SOLs reguladas sin rastro ni montos, impidiendo trazabilidad/disputa (riesgo regulatorio INVIMA). La lógica de exclusión sí es correcta (no toca OCs Pagada/Recibida/Parcial en 12020, solo pagos pendientes), por lo que el alcance del borrado es intencional; el bug es exclusivamente la ausencia de audit. No es falso positivo. Es admin-only (authz en 11996), lo que acota exposición, por eso P1 (trazabilidad/regulatorio) y no P0.

</details>

---

### P1.4 [auth-seguridad/security] Replay protection de TOTP NO se aplica en el flujo de login MFA (el más crítico)
**Ubicación:** `api/blueprints/mfa.py:187-192 (consumido por login_mfa_verify en 988)` · confianza alta

**Por qué es bug:** El registro anti-replay cross-worker (INSERT en mfa_tokens_usados con UNIQUE(username, token_hash)) solo se ejecuta si session['compras_user'] ya está seteado. Pero durante el login de 2 pasos, en /login/mfa POST (login_mfa_verify, mfa.py:973-988) el usuario aún NO tiene 'compras_user' en sesión — solo 'mfa_pending_user'. Por lo tanto _verify_totp ve uname='' y retorna True en la línea 190-192 sin grabar el token usado. Resultado: en el ÚNICO punto donde la replay protection realmente importa (autenticación de login), está completamente desactivada. Un atacante en posición de red (MITM, hombro, phishing del código) que capture el TOTP de 6 dígitos puede reusarlo en una sesión paralela dentro de la ventana de ±90s (valid_window=1 sobre periodo 30s). El comentario del propio código (SEC-FIX 25-may, líneas 174-183) describe exactamente este ataque cross-worker como el motivo de la tabla mfa_tokens_usados, pero el login lo elude. Misma laguna aplica a mfa_disable y verify_setup, aunque ahí ya hay compras_user en sesión (esos sí protegidos).

**Fix propuesto:** Pasar explícitamente el username a _verify_totp en lugar de depender de session['compras_user']. En login_mfa_verify y login_mfa_backup usar el 'pending' (mfa_pending_user) como identidad para el registro anti-replay: cambiar la firma a _verify_totp(secret, token, username=None) y, cuando se llame desde el login, pasar username=pending. Eliminar el fail-open 'if not uname: return True' o reservarlo solo para tests reales (p.ej. condicionar a app.testing/PYTEST_CURRENT_TEST), no a la mera ausencia de compras_user.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. En login_mfa_verify (mfa.py:973-998) la sesión solo tiene 'mfa_pending_user' (línea 976); 'compras_user' NO se setea hasta la línea 998, DESPUÉS de llamar _verify_totp(rec['secret'], token) en la línea 988. Dentro de _verify_totp, la línea 187 lee session.get('compras_user') → vacío, y la línea 190-192 hace fail-open `if not uname: return True`, SALTANDO el INSERT anti-replay en mfa_tokens_usados (líneas 202-207). Por lo tanto la protección anti-replay cross-worker que el propio comentario SEC-FIX 25-may (líneas 174-183) construyó para frenar un MITM con 3 workers gunicorn queda completamente desactivada justo en el flujo de login, que es donde más importa. Verifiqué que verify_setup (call en 752, username de session compras_user en 739) y mfa_disable (call en 821, username en 791) SÍ tienen compras_user en sesión, así que esos sí quedan protegidos — coincide con lo que reporta el hallazgo. La firma _verify_totp(secret, token) (línea 151) no recibe username, confirmando que depende 100% de la sesión. El flujo de backup code (1059-1113) usa un mecanismo de un solo uso separado (_consume_backup_code), no la tabla TOTP, así que ahí el replay TOTP no aplica (matiz menor del reporte, no afecta el core). Impacto real: un atacante que capture un TOTP de 6 dígitos vivo (phishing/MITM/hombro) puede reusarlo dentro de ±90s (valid_window=1, periodo 30s) en una sesión paralela en cualquier worker, porque el token usado nunca se graba durante el login. No está en la lista de falsos positivos confirmados. Hay rate limiting (_is_locked/_record_failure líneas 984/989) que mitiga ataques ciegos, pero NO mitiga el replay de un código ya válido. Anula un control de seguridad construido deliberadamente en la ruta de autenticación → P1 correcto. Fix recomendado: pasar el username explícito (pending) a _verify_totp y condicionar el fail-open a app.testing/PYTEST_CURRENT_TEST, no a la ausencia de compras_user.

</details>

---

### P1.5 [auth-seguridad/regulatory] admin_mfa_reset (reset de MFA de otro usuario) no escribe audit_log
**Ubicación:** `api/blueprints/mfa.py:608-664` · confianza alta

**Por qué es bug:** admin_mfa_reset desactiva el MFA de OTRO usuario (mutación sobre users_mfa + invalida backup codes), una de las acciones más sensibles del sistema: deja al objetivo accesible solo con password, sin segundo factor. La invariante del dominio exige audit_log obligatorio en toda mutación de seguridad/inventario/etc.; su ausencia es bug. El endpoint hermano mfa_admin_disable (mfa.py:895-901) SÍ llama audit_log via audit_helpers; admin_mfa_reset solo registra en security_events con _log_sec, que no es la traza de auditoría canónica (audit_log) usada para reconstruir quién cambió qué. Inconsistencia que deja un hueco de trazabilidad regulatoria precisamente en una acción que debilita la postura de seguridad de una cuenta admin/operativa.

**Fix propuesto:** Agregar, dentro de la misma transacción antes del commit, una llamada a audit_helpers.audit_log(cur, usuario=caller, accion='MFA_ADMIN_RESET', tabla='users_mfa', registro_id=username, despues={'enabled':0,'reset_by':caller,'prev_enabled':had_enabled}, detalle=f'Admin {caller} reseteó MFA de {username}'), espejando el patrón ya usado en mfa_admin_disable. Mantener además el _log_sec existente.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. admin_mfa_reset (api/blueprints/mfa.py:608-664) ejecuta una mutación de seguridad muy sensible: UPDATE users_mfa SET enabled=0, secret='', backup_code_hash=NULL (líneas 643-648) MÁS invalidación de todos los backup codes no usados (líneas 649-653), dejando la cuenta objetivo accesible solo con password. Sin embargo solo registra vía _log_sec("mfa_admin_reset", ...) (línea 658), y _log_sec (api/auth.py:223-235) inserta en la tabla security_events, NO en audit_log. NUNCA llama audit_helpers.audit_log. El endpoint hermano mfa_admin_disable (mfa.py:886-904) hace una mutación equivalente y SÍ llama audit_helpers.audit_log con accion='MFA_ADMIN_DISABLE' (líneas 895-901), confirmando el patrón canónico que falta aquí. audit_helpers.audit_log (audit_helpers.py:75-95) es la traza inmutable para evidencia regulatoria Part 11 §11.10(e) protegida por trigger de mig 105. La invariante de dominio exige audit_log obligatorio en toda mutación de seguridad. Hay inconsistencia real y hueco en la traza canónica regulatoria precisamente en la acción que debilita la postura de seguridad de una cuenta. Atenuante: el evento sí queda en security_events (actor, target, ip, prev_enabled), así que no es ausencia total de registro, sino ausencia en el trail canónico audit_log que es el usado para reconstrucción regulatoria. P1 correcto: gap regulatorio/trazabilidad inmutable sobre acción de seguridad de alto impacto, parcialmente mitigado pero inconsistente con su endpoint hermano. El fix propuesto (espejar audit_log dentro de la misma transacción antes del commit) es el patrón correcto.

</details>

---

### P1.6 [calidad-inminva/authz] POST de resultados microbiológicos sin RBAC: cualquier usuario logueado puede inyectar lecturas micro y disparar OOS/cuarentena
**Ubicación:** `api/blueprints/calidad.py:1264-1320` · confianza alta

**Por qué es bug:** Todos los demás POST de Calidad (CoA, agua, especificaciones, estabilidades, capa) pasan por _require_calidad() (CALIDAD_USERS|ADMIN_USERS) precisamente porque registrar evidencia regulatoria es decisión técnica. Aquí solo se valida que haya sesión, así que cualquier compras_user (operario, marketing, compras) puede registrar un resultado microbiológico que dispara la creación automática de OOS y la cuarentena del lote (líneas 1322-1346: 'Lote {lote} pasa a CUARENTENA'). Es inyección de evidencia regulatoria falsa por personal no autorizado (21 CFR Part 11 / INVIMA Res 2214/2021), exactamente la clase de hueco que motivó _require_calidad según su propio docstring (líneas 19-31).

**Fix propuesto:** En el bloque POST, antes de procesar el body, llamar a la misma guarda RBAC: `err, code = _require_calidad(); if err: return err, code` (o reusar la verificación CALIDAD_USERS|ADMIN_USERS), igual que en coa_list/especificaciones_list/estabilidades_list.

<details><summary>Veredicto del verificador</summary>

Confirmado en código real. calidad_micro_resultados (api/blueprints/calidad.py:1264-1270) solo valida `if 'compras_user' not in session` y NUNCA llama a _require_calidad(), a diferencia de sus endpoints hermanos que sí gatean el POST: auditorias_list (1140-1142) y calidad_agua_registros (1516-1519) hacen `err,code=_require_calidad(); if err: return err,code` con el comentario explícito "POST requiere Calidad/Admin · evidencia INVIMA". El docstring de _require_calidad (lineas 22-25) lista textualmente "micro" entre los endpoints que debían quedar protegidos — este quedó sin arreglar. Impacto verificado: cualquier compras_user (operario/marketing/compras) puede POSTear un resultado micro; si valor>spec, _calc_estado_micro devuelve 'fuera_industria' (1301,1327) y el código auto-crea un OOS (1337-1349) y envía el lote a CUARENTENA con accion_inmediata 'Lote {lote} pasa a CUARENTENA. No liberar hasta cierre OOS.' (1345). Es inyección de evidencia regulatoria por personal no autorizado + bloqueo de liberación del lote (21 CFR Part 11 / INVIMA). No está en la lista de falsos positivos. Fix correcto: en el bloque POST anteponer `err,code=_require_calidad(); if err: return err,code`, exactamente el patrón ya usado en los dos endpoints vecinos. P1: requiere sesión autenticada (no es bypass total de auth) pero permite mutación de registro regulado y cuarentena por usuarios sin rol Calidad.

</details>

---

### P1.7 [calidad-inminva/authz] POST de especificaciones micro (limite_industria) sin RBAC: un no-Calidad puede mover los límites que definen el veredicto OOS
**Ubicación:** `api/blueprints/calidad.py:1211-1240` · confianza alta

**Por qué es bug:** especificacion_update (FQ specs) sí exige _require_calidad porque 'alterar/borrar specs cambia los rangos que auto-validan los CoA'. Las specs micro tienen exactamente el mismo rol: _calc_estado_micro usa limite_industria para decidir fuera_industria → OOS → cuarentena. Sin RBAC, cualquier usuario logueado puede subir limite_industria y hacer que un lote contaminado pase como 'ok', enmascarando un OOS. Además este POST no escribe audit_log pese a alterar un parámetro regulatorio (invariante: toda mutación de calidad requiere audit).

**Fix propuesto:** Aplicar _require_calidad() al método POST y agregar audit_log(accion='UPSERT_MICRO_SPEC') tras el INSERT/UPDATE, espejando especificacion_update.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el codigo real. En api/blueprints/calidad.py:1211-1240 el endpoint POST /api/calidad/micro/specs solo valida `if 'compras_user' not in session` (401, linea 1216-1217) y NO llama a `_require_calidad()`. Esto contrasta con TODOS los endpoints hermanos que mutan datos regulatorios de calidad, que si usan _require_calidad() en POST: especificaciones_list (linea 723), especificacion_update (linea 774), coa_list (linea 809), estabilidades (974), CAPA (1028/1083), auditorias (1141). El micro specs POST es el unico sin RBAC de Calidad/Admin. Impacto real verificado: _calc_estado_micro (linea 1184) hace `li = spec.get('limite_industria')` y en lineas 1197/1203 usa `li` directamente para devolver 'fuera_industria' (OOS). El POST upsertea limite_industria via ON CONFLICT DO UPDATE (lineas 1229-1234). Por tanto cualquier compras_user (operario, no solo Calidad) puede subir limite_industria y hacer que un resultado contaminado pase de 'fuera_industria' a 'ok', enmascarando un OOS y evitando la cuarentena — exactamente el riesgo que el propio comentario de especificacion_update (linea 772-773) cita como razon para exigir RBAC. Ademas el POST hace conn.commit() (linea 1239) sin ningun audit_log, violando el invariante de auditoria obligatoria en mutaciones de calidad (comparar con CREAR_SPEC_MP linea 746 y MODIFICAR_SPEC_MP linea 793). No es falso positivo: _require_calidad ya existe y se aplica a sus pares, asi que el fix (aplicar _require_calidad al POST + audit_log UPSERT_MICRO_SPEC) es coherente con el patron establecido. Severidad P1 correcta: alteracion de parametro regulatorio INVIMA por usuario no autorizado + falta de audit, sin ser explotacion remota anonima (requiere login).

</details>

---

### P1.8 [compras/data-correctness] maestro_mps.precio_referencia escrito en $/g en 4 rutas (debe ser $/kg) — drift 1000x vs INV-2
**Ubicación:** `api/blueprints/compras.py:1031, 3585, 5701, 6296` · confianza alta

**Por qué es bug:** INV-2 del CONTRACT dice precio_referencia = precio_unit_g * 1000 ($/kg). La unidad canónica $/kg está confirmada por: (a) compras.py:4860 calcula valor_estimado = cant_g/1000.0 * precio_referencia (divide a kg antes de multiplicar), y (b) inventario.py:2160 comentario 'precio_referencia (COP/kg)'. solo update_sol_items multiplica por 1000; recibir_oc, crear_oc_desde_solicitudes, handle_ordenes_compra POST y pagar_oc escriben el precio_unitario crudo ($/g) → valor 1000x menor. recibir_oc corre en CADA recepción y SOBRESCRIBE el valor correcto que dejó la edición de SOL. Impacto: la valoración financiera de inventario (Pareto stock × precio_referencia en inventario.py:2980/3191/3458) y el auto-estimado de valor (4860) quedan subvaluados 1000x; el sugeridor de proveedor y validar_precios muestran precios incoherentes. Drift de dato monetario regulado.

**Fix propuesto:** Unificar la unidad: en recibir_oc:5701, crear_oc_desde_solicitudes:3585, handle_ordenes_compra:1031 y pagar_oc:6296 escribir precio_referencia = precio_unitario * 1000.0 (igual que update_sol_items:8705). Idealmente extraer un helper _sync_precio_referencia(c, codigo_mp, precio_por_g) que centralice la conversión a $/kg y se use en los 5 sitios.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. Las 4 rutas escriben precio_unitario (en $/g) crudo en maestro_mps.precio_referencia, que es canónicamente $/kg → drift 1000x.

UNIDAD DE precio_unitario = $/g (probado): subtotal/valor_total = cantidad_g * precio_unitario en compras.py:126, :1038 (valor_total_calc), :3491 (valor_total_preview). Como cantidad_g está en gramos y el producto da COP total, precio_unitario es $/g. Además crear_oc_desde_solicitudes asigna precio_unitario = it['precio_unit_g'] (compras.py:3463/3475), explícitamente por gramo.

UNIDAD DE precio_referencia = $/kg (probado por 3 fuentes independientes): (a) inventario.py:2160-2167 comentario 'precio_referencia (COP/kg)' y costo = precio_referencia * (g_total/1000.0); (b) compras.py:4860 valor_estimado = cant_g/1000.0 * precio_referencia; (c) path canónico de recepción de inventario inventario.py:6716-6757 toma precio_kg del usuario (mostrado $/kg en :6734), lo guarda en precios_mp_historico.precio_kg y lo escribe RAW en precio_referencia (:6757); (d) update_sol_items compras.py:8705 escribe precio_nuevo * 1000.0 con comentario 'precio en pesos por kg · precio_unit_g está en pesos/g · multiplicar por 1000'.

LAS 4 RUTAS BUGGY (verificadas línea a línea):
- compras.py:1031-1033 handle_ordenes_compra POST: precio_referencia=? con precio_u ($/g), sin *1000.
- compras.py:3584-3588 crear_oc_desde_solicitudes: precio_referencia=? con pu ($/g), sin *1000.
- compras.py:5700-5702 recibir_oc: precio_referencia=? con float(precio_item) de ordenes_compra_items.precio_unitario ($/g), sin *1000.
- compras.py:6295-6297 pagar_oc: precio_referencia=? con float(precio) de ordenes_compra_items.precio_unitario ($/g), sin *1000.

IMPACTO: recibir_oc corre en CADA recepción y sobrescribe el valor correcto que dejó update_sol_items o el path de inventario, dejando precio_referencia 1000x subvaluado. Consumidores afectados: Pareto financiero (inventario.py:2980/3191/3350/3458), costo de producción (inventario.py:2167), valor_estimado de SOL (compras.py:4860), sugeridor de proveedor/validar_precios. Valoración financiera de inventario regulado queda 1000x menor. El kardex/stock NO se afecta (es SUM movimientos), solo la valoración monetaria → por eso P1, no P0 (no hay pérdida de stock, crash ni brecha de seguridad). No está en la lista de falsos positivos y ninguna invariante lo justifica. Fix correcto: multiplicar precio_unitario por 1000.0 en las 4 rutas (idealmente helper _sync_precio_referencia centralizando la conversión $/g → $/kg, igual que :8705 y :6757).

</details>

---

### P1.9 [core-resto/authz] gerencia.py: /api/gerencia/aliados-feed expone financieros B2B del CEO a CUALQUIER usuario logueado (sin FINANZAS_ACCESS)
**Ubicación:** `api/blueprints/gerencia.py:775-781` · confianza alta

**Por qué es bug:** TODOS los demas endpoints de gerencia (kpis, flujo-operacional, dashboard-extra) empiezan con 'if session.get("compras_user","") not in FINANZAS_ACCESS: return 401'. Este endpoint NO tiene check de rol alguno: el before_request global solo exige sesion (cualquier user: operario, marketing, planta). Devuelve revenue mensual/anual por canal, ranking de top-3 aliados con %, concentracion de riesgo, valor en riesgo y MoM — datos estrategicos confidenciales del holding. Cualquier empleado logueado puede leerlos via GET directo. Inconsistencia de autorizacion = fuga de datos financieros.

**Fix propuesto:** Anteponer al cuerpo: 'from config import FINANZAS_ACCESS; if session.get("compras_user","") not in FINANZAS_ACCESS: return jsonify({"error":"No autorizado"}),401' igual que los otros endpoints gerencia.

<details><summary>Veredicto del verificador</summary>

Confirmado. gerencia.py:775-930 (gerencia_aliados_feed) NO tiene ningun check de rol: el cuerpo arranca directo en conn=get_db() (L781) sin el guard 'if session.get(\"compras_user\",\"\") not in FINANZAS_ACCESS: return 401'. Verifique que NO existe @bp.before_request en gerencia.py (grep sin matches), por lo que el unico gate es el global require_auth_for_api (auth.py:268-309) que solo exige session.get('compras_user') = CUALQUIER usuario logueado. En contraste, los endpoints hermanos SI gatean: kpis (L55), flujo-operacional (L170), dashboard-extra (L253) con FINANZAS_ACCESS; input-manual (L524) con ADMIN_USERS. Ademas la pagina HTML que consume este feed, /gerencia-financiero, esta gateada con FINANZAS_ACCESS (L49), evidenciando que el dato es FINANZAS-only por diseno. El payload retornado (L904-928) expone datos estrategicos confidenciales: revenue mensual/anual por canal aliados vs Shopify, MoM, top-3 aliados NOMBRADOS con revenue y %, concentracion de riesgo top1/top3, valor en riesgo, ticket trend 6 meses. Cualquier operario/planta/marketing puede leerlo via GET /api/gerencia/aliados-feed. Es una inconsistencia de autorizacion real (broken access control) con fuga de datos financieros del holding. No coincide con ningun falso positivo confirmado. El fix propuesto (anteponer el guard FINANZAS_ACCESS identico al resto) es correcto. Severidad P1 adecuada: fuga de confidencialidad sin escalada de privilegio de escritura.

</details>

---

### P1.10 [core-resto/regulatory] firmas.py: _verify_password solo valida contra COMPRAS_USERS (env), ignora users_passwords (BD) -> usuarios reales no pueden e-firmar (Part 11)
**Ubicación:** `api/blueprints/firmas.py:67-79` · confianza alta

**Por qué es bug:** El login real usa core._resolve_password_hash(), que prioriza el hash en la tabla users_passwords (BD) y solo cae a COMPRAS_USERS (env PASS_<USER>) como fallback. El modulo Usuarios (core.py admin_usuarios_crear / reset-password) crea/resetea passwords SOLO en users_passwords, sin tocar env vars. Resultado: un usuario creado o que cambio su clave via /api/cambiar-password tiene el hash unicamente en BD; firmas._verify_password lo busca solo en COMPRAS_USERS -> devuelve '' -> sign_challenge responde 401 'Credenciales invalidas' aunque la clave sea correcta. Ese usuario QUEDA IMPOSIBILITADO de firmar electronicamente (aprobar MBR, liberar lote, autorizar) — bloqueo total del workflow regulado 21 CFR Part 11 / INVIMA para todo el personal no migrado a env vars. mfa.py linea 803 ya usa _resolve_password_hash correctamente; firmas quedo desincronizado.

**Fix propuesto:** Reemplazar 'stored = COMPRAS_USERS.get(username,"")' por 'from blueprints.core import _resolve_password_hash; stored = _resolve_password_hash(username)' para usar la misma fuente de verdad que el login.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. firmas.py:75 `_verify_password` lee SOLO `COMPRAS_USERS.get(username,"")` (env PASS_<USER>), nunca consulta la tabla users_passwords. En contraste, el login real (core.py:1468) y mfa.py:803-804 usan `_resolve_password_hash` (core.py:34-76), cuya prioridad #1 es el hash en users_passwords (BD) y solo cae a env como fallback. Todas las rutas que mutan password escriben EXCLUSIVAMENTE en users_passwords (BD), nunca env: self-service /api/cambiar-password (core.py:1811-1818), admin crear (697), admin editar (758), admin reset-password (811). Por tanto un usuario creado por el módulo Usuarios o que cambió su clave tiene el hash solo en BD: hace login normal (que chequea BD) pero firmas._verify_password obtiene '' -> False -> sign_challenge devuelve 401 'Credenciales inválidas' (firmas.py:142-144), y sin challenge_token /api/sign no procede (firmas.py:202). Resultado: bloqueo total de la firma electrónica regulada (aprobar MBR, liberar lote, autorizar — Part 11/INVIMA) para todo el personal cuyo hash vive solo en BD, que en la práctica es la mayoría tras usar el módulo Usuarios o el self-service. No es ningún falso positivo de la lista. El fix propuesto (usar _resolve_password_hash) es correcto y alinea firmas con login/mfa. Mantengo P1 (no corrompe datos ni abre brecha de seguridad; existe workaround admin de setear env vars), aunque roza P0 por ser bloqueo de capacidad regulada.

</details>

---

### P1.11 [finanzas-cartera/crash] pnl_por_empresa usa date.today() sin importar 'date' → NameError 500 en cada llamada *(verificador bajó de P0)*
**Ubicación:** `api/blueprints/financiero.py:601-602` · confianza alta

**Por qué es bug:** El módulo solo importa `from datetime import datetime, timedelta` (línea 7). Las demás funciones que usan date la importan localmente (`from datetime import date` en líneas 972, 1014, 1056, 1116), pero pnl_por_empresa NO lo hace. Las llamadas a date.today() en las líneas 601-602 están en el cuerpo de la función ANTES del primer try/except (línea 609), por lo que lanzan NameError: name 'date' is not defined. El endpoint /api/financiero/pnl-por-empresa devuelve 500 en TODA invocación — el P&L por empresa del holding está completamente roto.

**Fix propuesto:** Agregar `from datetime import date` dentro de pnl_por_empresa (igual que las otras funciones) o añadir `date` al import de módulo en la línea 7: `from datetime import datetime, date, timedelta`.

<details><summary>Veredicto del verificador</summary>

Confirmado en código real. financiero.py:7 importa solo `from datetime import datetime, timedelta` — NO importa `date`. No existe ningún otro import de `date` a nivel módulo (grep confirma que las demás funciones lo importan localmente: línea 158 `as _d`, y 972/1014/1056/1116 `from datetime import date`). La función pnl_por_empresa (líneas 592-602) NO tiene import local de `date`, y usa `date.today()` en líneas 601-602. Estas líneas están en el cuerpo de la función, después del guard de auth (línea 599) pero ANTES del primer try/except (línea 609). Resultado: NameError: name 'date' is not defined → 500. Además, en Python el valor por defecto de request.args.get() se evalúa eagermente aunque se pasen los parámetros desde/hasta, así que ni siquiera enviar ?desde=&hasta= evita el crash. El endpoint /api/financiero/pnl-por-empresa está roto en TODA invocación de un usuario autorizado (ADMIN/CONTADORA). Matiz que justifica P1 en vez de P0: el guard de auth en línea 599 devuelve 401 antes del crash para usuarios no autorizados, y el bug es un crash de un endpoint de reporting (no corrupción de datos ni pérdida de stock ni brecha de seguridad), pero para el consumidor legítimo (Sebastián viendo el P&L del holding) el módulo está 100% inutilizable. Fix correcto: agregar `from datetime import date` dentro de la función o `date` al import de la línea 7.

</details>

---

### P1.12 [finanzas-cartera/authz] cont_login compara hash almacenado contra password en texto plano (login roto + viola política de hash) *(verificador bajó de P0)*
**Ubicación:** `api/blueprints/contabilidad.py:302` · confianza alta

**Por qué es bug:** ALL_PASSES es COMPRAS_USERS, cuyos valores son hashes pbkdf2/scrypt (config.py: `_pwd('PASS_X')`). La comparación directa `ALL_PASSES.get(u) == p` confronta el HASH contra el password en claro `p`, no usa check_password_hash. Consecuencias: (1) con la política correcta (hash en PASS_*), el login de contabilidad NUNCA puede tener éxito porque hash != plaintext; (2) si alguien dejara un PASS_* en texto plano, esto haría un bypass plaintext==plaintext saltándose la política de seguridad. El patrón canónico del resto del sistema es check_password_hash(expected, password) (core.py:1474, mfa.py:568, etc.). werkzeug.security ya está importado en este archivo vía http_helpers/otros, pero aquí no se usa.

**Fix propuesto:** Reemplazar por: `from werkzeug.security import check_password_hash; ph = ALL_PASSES.get(u); if u in CONT_USERS and ph and check_password_hash(ph, p):`. Replicar el manejo de bloqueo/intentos del login principal si aplica.

<details><summary>Veredicto del verificador</summary>

Confirmado en código real. contabilidad.py:298 importa COMPRAS_USERS as ALL_PASSES; sus valores son hashes (config.py:12-36, _pwd lee PASS_* que por política deben ser pbkdf2/scrypt). En contabilidad.py:302 la comparación es `ALL_PASSES.get(u) == p` (hash almacenado == password en texto plano), sin check_password_hash. El patrón canónico (core.py:1473-1474) exige expected.startswith('pbkdf2:'/'scrypt:') y usa check_password_hash, rechazando plaintext. CONT_USERS = CONTADORA_USERS|ADMIN_USERS = {mayra,catalina,sebastian,alejandro} (contabilidad.py:16), todos con hash en COMPRAS_USERS. Consecuencia verificada: bajo config correcta (PASS_* = hash) hash != plaintext, por lo que el endpoint /api/contabilidad/login NUNCA autentica (login roto, falla cerrado). Si algún PASS_* quedara en plaintext, haría bypass plaintext==plaintext saltándose la política de hash que el resto del sistema enforce. Es bug real (login funcional roto + violación de política de hash de auth). Rebajo de P0 a P1: NO es un bypass de authz abierto bajo config correcta (falla cerrado, nadie entra), y el escenario de bypass requiere misconfig plaintext; además cont_me (contabilidad.py:314) acepta session compras_user de CONT_USERS, mitigando para quien ya entró por /login. El fix propuesto (check_password_hash sobre el hash) es correcto.

</details>

---

### P1.13 [finanzas-cartera/data-correctness] cont_kpis excluye el saldo de facturas 'Parcial' de la cartera → cartera y cartera vencida subreportadas
**Ubicación:** `api/blueprints/contabilidad.py:754-760` · confianza alta

**Por qué es bug:** En cont_factura_pago una factura con pago parcial pasa a estado 'Parcial' (línea 528), no sigue como 'Emitida'. Los KPIs de cartera filtran SOLO estado='Emitida', por lo que el saldo pendiente de TODAS las facturas parcialmente pagadas queda fuera de cartera_total y cartera_vencida. La contadora ve una cartera menor a la real (riesgo financiero: subestima lo que falta cobrar). Además para las 'Emitida' suma el `total` completo (correcto, porque Emitida implica 0 pagos), pero el hueco de las Parcial es real.

**Fix propuesto:** Incluir estados pendientes y descontar lo pagado, p.ej.: `SELECT COALESCE(SUM(f.total - COALESCE(p.pagado,0)),0) FROM facturas f LEFT JOIN (SELECT numero_factura, SUM(monto) pagado FROM facturas_pagos GROUP BY numero_factura) p ON p.numero_factura=f.numero WHERE f.estado IN ('Emitida','Parcial')`, y análogo con el filtro de fecha_vencimiento para la vencida.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. En contabilidad.py:528-529 un pago parcial mueve la factura a estado='Parcial' (UPDATE facturas SET estado='Parcial'). Los KPIs de cartera en cont_kpis (contabilidad.py:754-760) filtran SOLO estado='Emitida', por lo que el saldo pendiente de TODAS las facturas parcialmente pagadas queda excluido de cartera_total y cartera_vencida: la contadora ve una cartera (y cartera vencida) menor a la real. El propio código demuestra que 'Parcial' es un estado pendiente con saldo: el listado en contabilidad.py:333-355 calcula saldo = total - monto_pagado (LEFT JOIN a facturas_pagos), y otros consumidores SÍ lo incluyen correctamente: hub.py:825 usa WHERE estado IN ('Emitida','Parcial') y tesoreria_html.py:369 filtra estado==='Emitida' || 'Parcial' como pendientes. El cont_kpis quedó inconsistente con esos dos lugares. Nota: para las 'Emitida' sumar total completo es correcto (Emitida implica 0 pagos; cualquier pago la pasa a Parcial/Pagada), pero el hueco de las 'Parcial' es real y además ni siquiera descuenta lo ya pagado. Impacto: subreporte de cartera y cartera vencida (visibilidad financiera incorrecta), data-correctness. No es crash ni viola invariante de stock/INVIMA, por eso P1 (no P0) es correcto. No coincide con ningún falso positivo confirmado. Fix propuesto válido: estado IN ('Emitida','Parcial') con SUM(total - pagado) vía LEFT JOIN a facturas_pagos, análogo para la vencida.

</details>

---

### P1.14 [inventario/data-correctness] alertas_all calcula stock MP tratando 'Ajuste'/'Ajuste +' como salida (resta) → falsas alertas de reabastecimiento
**Ubicación:** `api/blueprints/inventario.py:3645-3646, 3680-3681` · confianza alta

**Por qué es bug:** El invariante canónico (y /api/stock línea 4001-4005) suma 'Entrada','Ajuste +','Ajuste' y resta 'Salida','Ajuste -'. Aquí cualquier tipo distinto de 'Entrada' (incluidos 'Ajuste' positivo y 'Ajuste +') se trata como negativo. Un 'Ajuste' positivo (que el endpoint manual SÍ permite insertar, línea 1705/1711 con cantidad>0) se RESTA, subestimando el stock. Esto dispara falsas alertas 'mps_sin_stock'/'mps_bajo_minimo' y alimenta sugerencias de compra erróneas. Es exactamente el patrón que MEMORY.md marca como bug ('si un query trata Ajuste siempre como resta, ES BUG').

**Fix propuesto:** Usar la forma canónica en ambos SUM: SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END), idéntica a /api/stock y get_lotes.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. En api/blueprints/inventario.py las dos queries de alertas usan el patrón defectuoso SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA') THEN cantidad ELSE -cantidad END): líneas 3645-3646 (cálculo de stock para mps_sin_stock / mps_bajo_minimo) y 3680-3681 (stock por lote para lotes_vencidos / lotes_proximos). Esto trata como RESTA cualquier tipo distinto de 'Entrada', incluidos 'Ajuste' positivo y 'Ajuste +'. Verifiqué que un 'Ajuste' positivo realmente existe en el kardex: el POST /api/movimientos (línea 1705-1711) admite tipo='Ajuste' con cantidad>0, y el endpoint de ajuste guarda un delta con signo (línea 9918-9922: mov_cantidad = round(cantidad - stock_ant) para 'Ajuste'), confirmando el invariante de MEMORY.md de que 'Ajuste' es un delta con signo (puede ser positivo). El patrón canónico correcto aparece en el MISMO archivo en 20+ queries, p.ej. /api/stock líneas 4001-4005 y la línea 201, que suman ('Entrada','Ajuste +','Ajuste') y restan ('Salida','Ajuste -'). Impacto: un MP/lote con Ajustes positivos o 'Ajuste +' verá su stock subestimado en estas alertas, disparando falsas alertas mps_sin_stock/mps_bajo_minimo y alimentando sugerencias de compra erróneas; además el HAVING stock>0 de la query de lotes (línea 3687) puede ocultar lotes con stock real positivo. Coincide exactamente con el anti-patrón que MEMORY.md marca como bug. No es corrupción del kardex (endpoint de solo lectura) pero sí afecta decisiones de negocio (reabastecimiento), por lo que P1 data-correctness es correcto. Fix propuesto es idéntico al patrón canónico ya usado en el resto del archivo.

</details>

---

### P1.15 [inventario/data-correctness] Seed de conteo cíclico (POST /api/conteos) calcula stock_sistema ignorando movimientos 'Ajuste' → diferencia artificial que puede escalar a gerencia o auto-ajustar
**Ubicación:** `api/blueprints/inventario.py:9526-9527` · confianza alta

**Por qué es bug:** Este stock_sistema se persiste en conteo_items.stock_sistema y luego en conteo_cerrar/conteo_ajustar se compara contra el físico para calcular 'diferencia' y decidir el umbral 5% gerencia (UMBRAL_ESCALA). Como omite 'Ajuste','Ajuste +','Ajuste -', un MP con un 'Ajuste' previo arranca con stock_sistema distinto del kardex real (_get_mp_stock / /api/stock). La función hermana conteo_materiales_estanteria (línea 7299) SÍ incluye Ajuste, evidenciando la inconsistencia. Resultado: diferencias fantasma que o bien auto-ajustan el kardex (drift) o escalan innecesariamente a Gerencia.

**Fix propuesto:** Alinear el SUM con la forma canónica incluyendo 'Ajuste +','Ajuste' (suma) y 'Ajuste -' (resta), igual que conteo_materiales_estanteria y /api/stock.

<details><summary>Veredicto del verificador</summary>

Confirmado en código real. En api/blueprints/inventario.py:9525-9530 el seed de POST /api/conteos calcula stock_sistema con SUM(CASE WHEN tipo='Entrada' THEN cantidad WHEN tipo='Salida' THEN -cantidad ELSE 0 END) — trata todo 'Ajuste'/'Ajuste +'/'Ajuste -' como 0 y NO excluye estados de lote bloqueados. Esto contradice la forma canónica _get_mp_stock (programacion.py:662-672: Entrada/Ajuste/Ajuste + suman, Salida/Ajuste - restan, excluye CUARENTENA/VENCIDO/RECHAZADO/AGOTADO) y a la función hermana conteo_materiales_estanteria (inventario.py:7299,7315) que ya fue corregida (comentario fix 24-may en 7285-7294 sobre justamente esta clase de diferencia artificial). El impacto es concreto: stock_sistema se persiste en conteo_items (9533); registrar_fisico computa diferencia=stock_fisico-stock_sistema (9564); y aplicar_ajustes (9582-9593) inserta movimientos compensatorios reales en el kardex para cualquier ABS(diferencia)>0.1 con requiere_gerencia=0. Para cualquier MP con un 'Ajuste' previo (patrón común del dominio: 'Ajuste' guarda delta con signo), el stock_sistema arranca desfasado exactamente por el neto de los Ajuste, produciendo diferencias fantasma que o bien auto-ajustan el kardex (drift de stock — violación de invariante) o escalan falsamente a Gerencia vía el UMBRAL_ESCALA 5%. No es falso positivo: la ruta legacy aplicar_ajustes sigue escribiendo movimientos. P1 data-correctness/drift de stock correcto.

</details>

---

### P1.16 [maquila-comercial/security] XSS almacenado en clientes_html: la función esc() existe pero NO se aplica a campos de texto libre del backend en casi todas las tablas
**Ubicación:** `api/templates_py/clientes_html.py:968, 992, 1000-1001, 1378-1380, 1420-1421, 1487, 1498` · confianza alta

**Por qué es bug:** Los campos nombre, empresa, contacto, ciudad, producto, producto_tipo, categoria_profesional, descripcion son texto libre persistido por POST /api/clientes, /api/maquila/prospectos, /api/maquila/ordenes, PATCH /api/aliados sin sanitización HTML en servidor. Se insertan crudos vía innerHTML. Un valor como <img src=x onerror=...> en el nombre de un cliente/prospecto/orden ejecuta JS en la sesión de cualquier usuario con CLIENTES_ACCESS que abra la página (incluye admins). XSS almacenado real, no nit: el comentario de L862 afirma 'XSS-safe' dando falsa seguridad mientras casi ningún render llama esc().

**Fix propuesto:** Envolver todo valor de texto del backend con esc() en los renderers: esc(a.nombre), esc(cl.nombre), esc(cl.ciudad), esc(p.empresa), esc(p.contacto), esc(p.producto_tipo), esc(o.empresa), esc(o.producto). En los template-literals de segmentos usar una versión esc equivalente para seg.categoria, sk.sku, sk.descripcion. Para el <option> de L992 escapar cl.nombre.

<details><summary>Veredicto del verificador</summary>

Verificado como XSS almacenado real. La función esc() existe (clientes_html.py:863) y SÍ se usa, pero solo en strings de mensajes del servidor (L1035, L1125, L1245). Los renderers de tablas que interpolan texto libre del backend vía innerHTML/template-literals NO la llaman: L968 (a.nombre), L992 (cl.nombre en <option>), L1000-1001 (cl.nombre, cl.ciudad), L1378-1380 (p.empresa, p.contacto, p.producto_tipo), L1420-1421 (o.empresa, o.producto), L1487/1498 (sk.descripcion, sk.sku, seg.categoria). Confirmé en el backend que esos campos se persisten CRUDOS sin sanitización HTML: maquila.py:62-83 (empresa/contacto/producto_tipo solo .strip()), maquila.py:167-184 (empresa/producto), clientes.py:66-74 (nombre, ciudad, contacto, observaciones via d['nombre']/d.get(...) sin escape) y se devuelven tal cual en los GET. Un valor como <img src=x onerror=...> en nombre de cliente/empresa de prospecto/orden ejecuta JS al renderizar la tabla. El comentario L862 'XSS-safe · innerHTML con data backend' da falsa seguridad. No está en la lista de falsos positivos confirmados. Severidad: mantengo P1, no P0, porque maquila.py:39-54 ahora exige login + COMPRAS_USERS/ADMIN para escribir (ya no es anónimo como antes del audit 2-may); el impacto real es XSS almacenado con cruce de privilegios (un usuario compras de bajo privilegio inyecta payload que se dispara en la sesión de un admin que abra la página de clientes, permitiendo acciones como admin sobre inventario/OC/nómina). Audiencia interna autenticada, no pública.

</details>

---

### P1.17 [maquila-comercial/regulatory] Generación de factura de maquila (FM) sin audit_log, pese a que toda mutación de facturas/OC es auditable obligatoria
**Ubicación:** `api/blueprints/maquila.py:261-350` · confianza alta

**Por qué es bug:** El endpoint crea una factura fiscal (tipo FM) que alimenta flujo_ingresos y numeración fiscal vía _next_numero, modifica el estado de la orden y persiste items, pero no escribe en audit_log. La invariante del dominio exige audit_log en toda mutación de OC/facturas/inventario. Sin rastro no se puede responder '¿quién facturó la orden de maquila X y por cuánto?', y una factura fiscal sin trazabilidad es un hueco regulatorio/contable.

**Fix propuesto:** Tras los INSERT/UPDATE y antes de commit, llamar audit_log(c, usuario=session.get('compras_user','sistema'), accion='FACTURAR_MAQUILA', tabla='facturas', registro_id=numero, despues={'orden':oid,'total':total,'cliente':cliente_nombre[:120]}, detalle=...).

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. api/blueprints/maquila.py:261-350 (api_maquila_facturar) genera una factura fiscal FM: INSERT INTO facturas (L312-321), INSERT INTO facturas_items (L328-334), UPDATE maquila_ordenes (L339-341) y conn.commit() (L343), SIN ninguna llamada a audit_log en toda la función. El grep confirma que las únicas audit_log en maquila.py están en L249-255, que pertenecen al endpoint PATCH de orden, no a facturar. La invariante dura del dominio (MEMORY.md y CLAUDE.md) exige audit_log obligatorio en toda mutación de facturas/OC. La prueba de que es un hueco y no un patrón intencional: el endpoint hermano en contabilidad.py que también hace INSERT INTO facturas (L426) SÍ escribe audit_log accion='CREAR_FACTURA' (L446) con el comentario explícito 'creación de factura es operación financiera regulada', y también auditan pago (L532) y anulación (L602). Impacto real: la factura FM alimenta numeración fiscal (_next_numero L296) y flujo_ingresos, por lo que queda un hueco de trazabilidad regulatorio/contable. No coincide con ningún falso positivo confirmado. Severidad P1 adecuada: violación de invariante de auditoría sobre mutación fiscal, sin corrupción de datos ni crash que justifique P0.

</details>

---

### P1.18 [plan-autoplan/data-correctness] _check_mp_para_pedido_b2b trata 'Ajuste' como Salida (viola invariante canónica de stock MP)
**Ubicación:** `api/blueprints/plan.py:692-700` · confianza alta

**Por qué es bug:** El patrón canónico (programacion._get_mp_stock e inventario_helpers.stock_mp_disponible) suma 'Entrada','Ajuste +','Ajuste' como positivo y resta solo 'Salida','Ajuste -'. Aquí TODO lo que no es 'Entrada' se resta (ELSE -cantidad), por lo que un movimiento 'Ajuste' con delta POSITIVO se resta del stock. Esto subestima el stock real de MP y genera falsos 'mps_faltantes' al crear pedidos B2B, alarmando a Catalina/admin con déficits inexistentes y empujando compras innecesarias. Es exactamente la violación de invariante MEMORY 'si un query trata Ajuste siempre como resta, ES BUG'.

**Fix propuesto:** Reemplazar el query inline por el helper canónico stock_mp_disponible(c, mid) (ya importado en el proyecto) o usar el CASE canónico: WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el codigo real. En api/blueprints/plan.py:692-700 el query de _check_mp_para_pedido_b2b usa CASE WHEN tipo IN ('Entrada','entrada','ENTRADA') THEN cantidad ELSE -cantidad END. El patron canonico verificado en programacion.py:664-665 (_get_mp_stock) y en inventario_helpers.py:88-93 (stock_mp_disponible) suma 'Entrada','Ajuste +','Ajuste' como positivo, resta 'Salida','Ajuste -', y deja ELSE 0. La rama ELSE -cantidad de plan.py resta TODO lo que no es Entrada, incluyendo 'Ajuste +' y 'Ajuste'. Verifique en animus.py:1341-1350 que el conteo ciclico inserta tipo 'Ajuste +' con cantidad_abs = abs(diferencia) (siempre positivo) cuando se encuentra MAS stock fisico; ese ajuste positivo queda restado, subestimando el stock por 2x cantidad. Igual con 'Ajuste' que guarda delta con signo (invariante MEMORY). Resultado: stock MP subestimado -> falsos mps_faltantes al crear pedidos B2B -> alarmas/compras innecesarias. Es exactamente la violacion del invariante MEMORY 'si un query trata Ajuste siempre como resta, ES BUG'. No es falso positivo conocido. El query es solo lectura (no persiste drift de stock ni muta inventario), por eso P1 data-correctness y no P0. Fix propuesto correcto: usar el CASE canonico o stock_mp_disponible (que ademas excluye estado_lote no-disponible, carencia adicional de este query inline).

</details>

---

### P1.19 [plan-autoplan/data-loss] Triggers manual/page-load de auto-plan ejecutan aplicar_plan SIN cron_lock → duplican SOLs y producciones entre 3 workers
**Ubicación:** `api/blueprints/auto_plan.py:1234-1239 y 1284-1289` · confianza alta

**Por qué es bug:** ejecutar_auto_plan_diario llama generar_plan + aplicar_plan, que CREA solicitudes_compra (numero AUTO-XXXX vía MAX+1) y produccion_programada. Solo _loop_cron adquiere _adquirir_lock_cron('auto_plan_diario'); estos dos endpoints (auto_plan_ejecutar_ahora y auto_plan_asegurar_actualizado, este último disparado en cada carga de /planta) lanzan el thread directamente sin lock. Con 3 workers gunicorn, dos cargas concurrentes (o concurrencia con el cron de las 7am) ejecutan aplicar_plan en paralelo sobre conexiones distintas: el chequeo 'existing' de producción por producto+fecha y el MAX(numero)+1 de SOL no ven los INSERT no commiteados del otro worker, produciendo producciones y SOLs AUTO-XXXX duplicadas. Es precisamente la race que cron_locks (mig 81) debía cubrir.

**Fix propuesto:** Antes de lanzar el thread (o dentro de ejecutar_auto_plan_diario), adquirir _adquirir_lock_cron(conn,'auto_plan_diario',ttl_horas=1) y abortar si ya está tomado; liberar en finally. Centralizar el lock dentro de ejecutar_auto_plan_diario para cubrir TODOS los call sites.

<details><summary>Veredicto del verificador</summary>

El núcleo del hallazgo es REAL pero el vector descrito está parcialmente equivocado. Verificado en código:

1) ejecutar_auto_plan_diario (auto_plan_jobs.py:414-513) y aplicar_plan (auto_plan.py:939-1167) NO adquieren ningún lock internamente. El cron_lock (_adquirir_lock_cron/_liberar_lock_cron) vive SOLO en _loop_cron (auto_plan_jobs.py:563-604), envolviendo la llamada — no dentro de la función. Por tanto los triggers manuales lo bypassean.

2) auto_plan_ejecutar_ahora (auto_plan.py:1235) lanza el thread directo a ejecutar_auto_plan_diario sin lock, y auto_plan_aplicar (auto_plan.py:1207) llama aplicar_plan inline sin lock. Ambos son admin-only (ADMIN_USERS), pero el lock del cron NO excluye mutuamente al path manual: dos admins simultáneos, un doble-click en ejecutar-ahora (dispara 2 threads sin debounce), o un manual concurrente con el cron de las 7am ejecutan aplicar_plan en paralelo sobre conexiones distintas.

3) Impacto real en produccion_programada: el chequeo 'existing' por producto+fecha (auto_plan.py:952-959) NO tiene unique constraint que lo respalde (confirmado: no existe uq sobre produccion_programada). Dos runs concurrentes ven ambos 'sin existing' y ambos INSERT → DUPLICA producciones para el mismo producto+fecha. Esto es el riesgo de integridad genuino.

4) Impacto real en SOLs: SÍ existe uq_solicitudes_compra_numero (database.py:6515, mig 82 que además dedupea históricos con -DUP-). Por eso NO se duplican SOLs como dice el hallazgo; en su lugar el segundo worker que computa el mismo AUTO-XXXX (MAX+1, auto_plan.py:1062-1066) recibe IntegrityError. En SQLite se traga en el except (auto_plan.py:1133, pierde ese grupo de SOL). En PostgreSQL (prod) el INSERT fallido ABORTA la transacción → los INSERT de conteos, el INSERT auto_plan_runs (1150) y el conn.commit() (1161) fallan con 'transaction is aborted', perdiéndose TODO el trabajo aplicado en esa transacción (incluidas las producciones ya insertadas en el mismo tx). Eso es data-loss real del plan aplicado.

REFUTADO del hallazgo: la afirmación 'auto_plan_asegurar_actualizado disparado en cada carga de /planta × 3 workers' NO se sostiene — el endpoint (auto_plan.py:1245) no tiene NINGÚN caller en todo el repo (grep en .py/.js/.html vacío); es código muerto. La amplificación por page-load concurrente está sobrevalorada.

Veredicto: bug real de integridad/data-loss (duplica produccion_programada + aborta tx PG perdiendo el plan), exactamente la race que cron_locks debía cubrir y que el fix de 25-may aplicó solo a _loop_cron olvidando los call sites manuales. El fix propuesto (centralizar _adquirir_lock_cron('auto_plan_diario') dentro de ejecutar_auto_plan_diario / aplicar_plan para cubrir TODOS los call sites, liberar en finally) es correcto. Mantengo P1 (no P0: triggers son admin-only y ventana de overlap estrecha; no es explotable por usuarios anónimos).

</details>

---

### P1.20 [programacion/data-loss] revertir-completado revierte MP de TODAS las producciones del mismo producto+fecha (drift de inventario por cross-reversal)
**Ubicación:** `api/blueprints/programacion.py:6576-6582 (patrón de obs en 5897 y 6350)` · confianza alta

**Por qué es bug:** El movimiento de Salida de MP se escribe con observaciones que SOLO contienen producto + fecha (ver _descontar_mp_produccion L5897 y prog_completar_evento L6350), nunca el id de la producción. La reversión de UN evento busca por LIKE 'Producción INICIADA: {producto} — {fecha}%'. POST /api/programacion/programar (L2518) permite crear varias filas con el mismo (producto, fecha_programada) -no hay unicidad-, y los pedidos B2B/Fijo también generan duplicados legítimos del mismo producto el mismo día. Si dos producciones del mismo producto se inician/descuentan el mismo día y un admin revierte solo UNA, el query devuelve los Salida de AMBAS y genera Entradas compensatorias por las dos, inflando el stock real (drift positivo) por las MP de la producción que NO se revirtió. Viola el invariante de stock canónico = SUM(movimientos) y deja inventario fantasma. Además limpia inventario_descontado_at de una sola fila mientras devuelve MP de dos.

**Fix propuesto:** Vincular la reversión por id de producción, no por texto. Añadir el produccion_id a un campo trazable del movimiento (p.ej. incluir un token '· prod#{pid}' en observaciones al descontar en iniciar/completar, o mejor una columna produccion_id en movimientos) y revertir filtrando exactamente ese id. Como mínimo, incluir lotes y cantidad_kg en el patrón LIKE no basta (siguen colisionando); usar un identificador único de la producción es obligatorio para evitar el cross-reversal.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. La Salida de MP escrita en _descontar_mp_produccion (programacion.py:5908-5914) y la obs base en :5897 ("Producción INICIADA: {producto} — {fecha} — {lotes} lote(s) × {kg}kg | FEFO...") y en prog_completar_evento :6350 ("Producción COMPLETADA: ...") NO incluyen el produccion_id ni se persisten en ninguna columna trazable: la tabla movimientos (database.py:7803-7811 y pg_schema.sql:1962-1967) no tiene lote_ref/produccion_id/referencia, solo el texto libre observaciones. La reversión en /revertir-completado (programacion.py:6576-6582) filtra exclusivamente por observaciones LIKE 'Producción INICIADA: {producto} — {fecha}%' OR LIKE 'Producción COMPLETADA: {producto} — {fecha}%'. Como el patrón LIKE usa solo producto+fecha y un '%' final (descarta lotes/kg), dos producciones distintas del MISMO producto en la MISMA fecha matchean ambas. POST /api/programacion/programar (:2518-2522) inserta en produccion_programada sin restricción de unicidad sobre (producto, fecha_programada), y los pedidos B2B/Fijo generan duplicados legítimos del mismo producto el mismo día. Al revertir UNA sola producción, el query devuelve los Salida de AMBAS y genera Entradas compensatorias por las dos (loop :6583-6595 sin dedup), mientras solo se limpia inventario_descontado_at de la fila revertida (:6667-6674). Resultado: drift positivo de stock (inventario fantasma) por las MP de la producción no revertida, violando el invariante stock = SUM(movimientos). Contraste decisivo: la reversión de MEE en el mismo handler (:6605-6611) SÍ usa lote_ref=produccion_id (escrito en :6163/6197/6425) y por eso es precisa — el camino MP nunca recibió ese ancla. El fix propuesto (persistir produccion_id en movimientos, p.ej. reusar/añadir columna y filtrar por id exacto en la reversión) es correcto; el LIKE por texto no puede desambiguar. Severidad P1 adecuada: requiere dos producciones mismo producto+fecha con MP descontada y una reversión parcial — escenario realista (split B2B/DTC) pero no diario; impacto = corrupción de inventario regulado INVIMA.

</details>

---

### P1.21 [rrhh-financiero/data-correctness] rrhh_nomina_guardar persiste el neto/descuentos enviados por el cliente sin recalcular ni validar, y default dias_trabajados=30 sobre nómina quincenal
**Ubicación:** `api/blueprints/rrhh.py:274-276` · confianza alta

**Por qué es bug:** El servidor guarda directamente salario_neto, descuento_salud y descuento_pension tal como llegan en el JSON del cliente, sin recomputarlos ni validarlos contra salario_base/dias. Un cliente (o request manipulado) puede persistir un neto arbitrario que luego se aprueba, se espeja a flujo_egresos (NOM-<periodo>) y se rutea a pago — sin control servidor. Además el default dias_trabajados=30 es incoherente con el cálculo quincenal del resto del módulo (base 15 días), por lo que registros sin dias quedan mal prorrateados aguas abajo.

**Fix propuesto:** Recalcular en el servidor desc_salud, desc_pension y neto a partir de salario_base, dias_trabajados (base 15) y conceptos validados, ignorando los valores de neto/descuentos del cliente. Validar 0<=dias_trabajados<=15 (o 31 si fuese mensual) y rechazar 400 si no cuadra.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo api/blueprints/rrhh.py. En rrhh_nomina_guardar (líneas 274-276) el INSERT OR REPLACE persiste salario_base, descuento_salud (r["desc_salud"]), descuento_pension (r["desc_pension"]) y salario_neto (r["neto"]) EXACTAMENTE como llegan en el JSON del cliente, sin recomputar. La lógica autoritativa de cálculo SÍ existe pero solo en el GET rrhh_nomina (líneas 236-265: sal_prop por días/15, desc_salud/pension=0.04, neto=...), y el POST de guardado NO la reutiliza. Aguas abajo el valor manipulado pasa sin re-validación: rrhh_nomina_aprobar (línea 578) solo hace SUM(salario_neto) y aprueba; rrhh_nomina_pagar espeja ese mismo total a flujo_egresos con referencia NOM-{periodo} (líneas 622-647), inyectando un egreso contable arbitrario. Por tanto un neto/descuento adulterado (p.ej. editando el JSON en devtools) entra al ledger sin control servidor. Claim 2 también verificado: el GET default dias=15 y prorratea sobre 15 (líneas 241,244), pero el POST hace r.get("dias_trabajados",30) (línea 276), incoherente con la base quincenal de 15. Matización adversarial: NO es hueco authz para cualquier usuario logueado — _rrhh_gate (línea 64) restringe a RRHH_USERS|ADMIN_USERS|CONTADORA_USERS, y aprobar/pagar son admin-only; el actor debe ser un usuario ya privilegiado de RRHH/contaduría manipulando el request. Eso baja el riesgo de P0 pero sigue siendo defecto real de integridad financiera/data-correctness en nómina regulada que fluye a contabilidad: jamás se debe confiar en cifras de neto/deducciones calculadas en el cliente. P1 correcto. No coincide con ningún falso positivo confirmado (el FP de salud/pensión 4% valida la TASA, no la confianza ciega en el valor enviado).

</details>

---


## P2 (32)

### P2.1 [admin/security] _log_sec llamado con argumentos en orden incorrecto en mps-asignar-proveedor (corrompe el registro de seguridad)
**Ubicación:** `api/blueprints/admin.py:5936` · confianza alta

**Por qué es bug:** La firma es _log_sec(event, username=None, ip=None, details=None) (auth.py:223). Aqui se pasa event=u (el username), username=_client_ip() (la IP), ip='admin_mp_asignar_proveedor' (el nombre del evento). El evento de seguridad queda con columnas cruzadas: el campo 'event' contiene el usuario, el campo 'ip' contiene el nombre de la accion. Toda busqueda/filtro por event en security_events para esta accion falla y el rastro de seguridad de una mutacion de maestro_mps queda inutilizable.

**Fix propuesto:** Reordenar a _log_sec('admin_mp_asignar_proveedor', u, _client_ip(), f'codigo={codigo} proveedor={proveedor}'), siguiendo la convencion del resto del archivo (p.ej. admin.py:2710).

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el codigo real. La firma es _log_sec(event, username=None, ip=None, details=None) (api/auth.py:223) que inserta directamente en security_events(event,username,ip,...). El uso canonico correcto en el mismo archivo es _log_sec("evento", u, _client_ip(), detalle) (admin.py:90, 1097, 2707, 2710). En admin.py:5936 se llama _log_sec(u, _client_ip(), "admin_mp_asignar_proveedor", ...), por lo que event=username(u), username=IP, ip="admin_mp_asignar_proveedor": las columnas quedan cruzadas. Toda busqueda/filtro por event='admin_mp_asignar_proveedor' en security_events falla y el rastro de esa mutacion de maestro_mps queda inutilizable. Matices: (1) el audit_log canonico SI se graba correctamente en linea 5925-5929, asi que el rastro regulatorio principal de la mutacion esta intacto; solo se corrompe el log secundario security_events. (2) _log_sec va envuelto en try/except (auth.py:224-235) asi que no hay crash. P2 es correcto: corrupcion de registro de seguridad sin perdida de datos ni drift de stock ni crash. Nota adicional: el mismo orden invertido se repite en al menos 3001, 3140, 6181, 6420, 6731, 6785, 7033, 7869, 8075, 8551 — es un patron, no un caso aislado.

</details>

---

### P2.2 [calidad-inminva/data-correctness] coa_list devuelve el id equivocado y crea NC duplicada en cada CoA no conforme
**Ubicación:** `api/blueprints/calidad.py:908-925` · confianza alta

**Por qué es bug:** Dos defectos reales: (1) El comentario dice 'si no hay NC abierta para este lote+parametro' pero NO hay ningún SELECT de deduplicación: cada registro de un CoA no conforme inserta una NC nueva, así que re-analizar el mismo parámetro fuera de spec genera NCs duplicadas que inflan el backlog de Calidad. (2) La respuesta retorna `c.lastrowid` (línea 924) DESPUÉS del INSERT de la NC, por lo que el `id` devuelto al cliente es el rowid de la no_conformidad, no el del coa_resultados (que era `coa_id` capturado en la línea 894). El frontend que use ese id para refrescar/enlazar el CoA apuntará al registro equivocado.

**Fix propuesto:** (1) Antes de insertar la NC, verificar existencia: SELECT 1 FROM no_conformidades WHERE lote=? AND codigo_mp=? AND descripcion LIKE 'CoA fuera de spec%' AND estado='Abierta'. (2) Devolver el id correcto: `'id': coa_id` en el jsonify final. Además agregar audit_log de la NC auto-creada (las otras NCs automáticas, p.ej. OOS de cronograma, sí auditan).

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo api/blueprints/calidad.py:894-925. (1) DEDUP AUSENTE: las líneas 908-922 ejecutan INSERT INTO no_conformidades de forma incondicional cuando conforme=0; NO existe ningún SELECT previo que verifique una NC 'Abierta' para el mismo lote+parametro, pese a que el comentario de la línea 908 afirma 'no hay NC abierta para este lote+parametro'. Re-analizar el mismo parámetro fuera de spec (retest legítimo de QC) crea NCs duplicadas, inflando el backlog. (2) ID EQUIVOCADO: coa_id se captura en la línea 894 (c.lastrowid tras INSERT en coa_resultados), pero el return de la línea 924 usa c.lastrowid OTRA VEZ, ahora DESPUÉS del INSERT de la NC (líneas 911-920). Para CoAs no conformes el id devuelto es el rowid de no_conformidades, no el de coa_resultados; solo coincide cuando conforme=1 (no se inserta NC). El impacto frontend es bajo (loadCOA re-fetch no usa el id), pero el contrato de la API devuelve un id incorrecto/engañoso. (3) FALTA AUDIT_LOG: la NC auto-creada en 911-922 no llama a audit_log, en contraste directo con la otra NC automática del mismo archivo (OOS de cronograma, líneas 665-682) que SÍ audita con accion='CREAR_NC_OOS'. MEMORY/CLAUDE.md exige audit_log obligatorio en toda mutación de no_conformidades; esta omisión viola esa invariante regulatoria INVIMA. Los tres defectos son reales y verificados en código; P2 es la severidad adecuada (inflación de backlog + id engañoso + brecha de auditoría, sin corrupción de stock ni pérdida de datos).

</details>

---

### P2.3 [calidad-inminva/data-correctness] KPI de lotes en cuarentena del dashboard discrepa de la bandeja: cuenta como cuarentena todo lote con estado_lote NULL
**Ubicación:** `api/blueprints/calidad.py:65-69` · confianza media

**Por qué es bug:** El dashboard (calidad_dashboard) cuenta como 'en cuarentena' cualquier Entrada con estado_lote NULL que tenga lote, mientras que la bandeja oficial (calidad_bandeja, líneas 176-183) cuenta SOLO los estados explícitos CUARENTENA/CUARENTENA_EXTENDIDA. En un kardex histórico la mayoría de las Entradas viejas tienen estado_lote NULL (nunca pasaron por el flujo de liberación), de modo que el KPI del dashboard infla masivamente el número de lotes en cuarentena frente al número real que ve el equipo en la bandeja. Dos pantallas del mismo módulo muestran cifras contradictorias del mismo indicador regulatorio.

**Fix propuesto:** Unificar el criterio: en calidad_dashboard usar el mismo filtro que la bandeja (solo UPPER(estado_lote) IN ('CUARENTENA','CUARENTENA_EXTENDIDA')), o si el negocio considera NULL=pendiente de liberar, alinear ambas consultas a una sola fuente/función compartida.

<details><summary>Veredicto del verificador</summary>

Confirmado en código real. El KPI de cuarentena del dashboard (api/blueprints/calidad.py:65-69) usa el filtro amplio `... IN ('CUARENTENA','CUARENTENA_EXTENDIDA') OR (estado_lote IS NULL AND lote IS NOT NULL AND lote != '')`, mientras que la bandeja oficial de Calidad (calidad.py:176-183) y la función de KPI usan SOLO `UPPER(estado_lote) IN ('CUARENTENA','CUARENTENA_EXTENDIDA')`. La discrepancia es real y además contradice la interpretación canónica del stock: api/inventario_helpers.py:89 trata `COALESCE(NULLIF(TRIM(estado_lote),''),'Aprobado')` -> NULL/vacío = APROBADO (disponible), y ESTADOS_LOTE_NO_DISPONIBLES (helpers:35) NO incluye NULL/vacío; stock_mp_cuarentena (helpers:110-117) cuenta cuarentena solo por UPPER(estado_lote)='CUARENTENA'. Las recepciones modernas via OC ya escriben explícitamente 'CUARENTENA' (compras.py:5520,5536), por lo que la rama `estado_lote IS NULL AND lote!=''` NO captura lotes recién recibidos pendientes de QC, sino Entradas históricas/manuales/legacy sin estado seteado — las cuales canónicamente son Aprobadas. Resultado: el KPI infla el número de lotes 'en cuarentena' frente a la bandeja oficial y frente al modelo de stock. Matiz que atenúa el framing 'dos pantallas del mismo módulo': el mismo filtro amplio existe en despachos.py:152 (recepcion_lotes_cuarentena), o sea es un criterio compartido por la vista de Recepción, no un outlier puro; pero sigue siendo un defecto compartido, no una justificación. No es drift de stock ni pérdida de datos (el stock real usa el helper canónico, no este KPI), por eso P2 es correcto. El fix propuesto (alinear al filtro explícito de la bandeja/helper) es válido.

</details>

---

### P2.4 [compras/data-loss] limpiar_influencer_no_pagadas borra items con columna inexistente 'numero_solicitud' → items huérfanos silenciosos *(verificador bajó de P1)*
**Ubicación:** `api/blueprints/compras.py:793` · confianza alta

**Por qué es bug:** La columna real de solicitudes_compra_items es 'numero' (usada en las otras 12 referencias del archivo: 909, 3072, 4092, 4241, 5072, 8721, etc.). Aquí se usa 'numero_solicitud', que no existe → OperationalError capturada y tragada por el except. Resultado: el DELETE de items NUNCA se ejecuta, pero el DELETE de la SOL padre (línea 796) SÍ. Cada limpieza masiva de influencers deja filas huérfanas en solicitudes_compra_items (sin SOL padre) que inflan _pendiente_en_compras_g/_bulk (que suman sci.cantidad_g con JOIN a sc — aunque el JOIN las filtra, quedan registros zombie acumulándose) y corrompen reportes/valor_estimado. Es exactamente el patrón de borrado-sin-rastro que el resto del módulo intenta evitar.

**Fix propuesto:** Cambiar la línea 793 a: c.execute("DELETE FROM solicitudes_compra_items WHERE numero=?", (numero,)). Además, NO tragar OperationalError sobre el nombre de columna correcto (eso enmascaró el bug 27+ días); reservar el except solo para tabla faltante en esquemas legacy.

<details><summary>Veredicto del verificador</summary>

Confirmado el defecto pero con impacto sobredimensionado. La columna real es `numero` — el esquema de `solicitudes_compra_items` (api/database.py:7856-7859) define `id, numero, codigo_mp, nombre_mp, cantidad_g, unidad, justificacion` (+ migradas valor_estimado, precio_unit_g, proveedor_sugerido...), sin `numero_solicitud`. `numero_solicitud` aparece UNA sola vez en todo el repo: compras.py:793. Las otras ~30 referencias usan `numero`. En SQLite el `DELETE ... WHERE numero_solicitud=?` lanza OperationalError (no such column); en PG (prod) lanza psycopg UndefinedColumn que pg_adapter._map_error (pg_adapter.py:96-109) convierte a sqlite3.OperationalError, y el SAVEPOINT/ROLLBACK TO (pg_adapter.py:221-237) mantiene viva la transacción. En ambos backends el `except sqlite3.OperationalError: pass` (línea 794) traga el error, el DELETE de items NUNCA corre, pero el DELETE de la SOL padre (línea 796) SÍ → ítems huérfanos en cada limpieza masiva de influencers. Defecto REAL. SIN EMBARGO, la justificación P1 data-loss es incorrecta: _pendiente_en_compras_g/_bulk (compras.py:308-313, 353-355) usan INNER JOIN `solicitudes_compra sc ON sc.numero = sci.numero`, así que los huérfanos NO matchean y NO inflan pendientes ni provocan sobre-compra ni drift de stock. Los reportes per-SOL (3072, 8074, 8597) consultan items por `numero` de una SOL padre existente; como el padre fue borrado, ningún path los surfacea. El daño real es acumulación silenciosa de filas zombie muertas (higiene de integridad/leak), no corrupción activa ni pérdida de datos del usuario. Eso lo ubica en P2, no P1. El fix propuesto (usar `numero` y no tragar OperationalError sobre columna válida) es correcto.

</details>

---

### P2.5 [compras/data-correctness] solicitudes-agrupadas-por-proveedor no filtra planta para fuente=usuarios (bleed INV-1)
**Ubicación:** `api/blueprints/compras.py:3132-3153` · confianza alta

**Por qué es bug:** INV-1 exige que las 3 fuentes no se mezclen, y el endpoint /api/solicitudes-compra sí maneja fuente='usuarios' excluyendo planta+influencer (líneas 2979-2986). Aquí solo se maneja fuente='planta'; cualquier otro valor de fuente (incluido 'usuarios') solo excluye Influencer/CC pero NO excluye Materia Prima/Empaque. Si la UI pide ?fuente=usuarios en la vista agrupada, mezcla las SOLs de planta (MP/Empaque) en el tab de usuarios, contradiciendo el contrato y el comportamiento del endpoint hermano.

**Fix propuesto:** Agregar rama simétrica: elif fuente == 'usuarios': sql += " AND s.categoria NOT IN ('Materia Prima','Empaque','Material de Empaque')" (Influencer/CC ya está excluido arriba), espejando la lógica de handle_solicitudes_compra.

<details><summary>Veredicto del verificador</summary>

Verifiqué el código real en compras.py:3132-3153. El endpoint solo maneja fuente=='planta' (línea 3149 añade AND categoria IN MP/Empaque); cualquier otro valor de fuente, incluido 'usuarios', solo excluye Influencer/CC (línea 3148) pero NO excluye Materia Prima/Empaque/Material de Empaque. El endpoint hermano handle_solicitudes_compra SÍ tiene la rama simétrica elif fuente=='usuarios' (líneas 2979-2986) que excluye _CATS_PLANTA + _CATS_INFLUENCER. La asimetría es real y el comentario en 3129 ('filtro de fuente alineado con /api/solicitudes-compra') es inexacto: solo el branch planta está alineado. Esto viola el contrato INV-1 (las 3 fuentes no se mezclan) descrito en CLAUDE.md:72.\n\nSin embargo, al revisar los call sites de la UI (compras_html.py): el call site de línea 4684 hardcodea fuente=planta, y renderSolicitudesAgrupadas (línea 5586/5602) NUNCA envía fuente — solo estado y categoria. Es decir, NINGÚN caller actual envía fuente=usuarios a este endpoint, por lo que hoy no hay bleed real de SOLs de planta al tab usuarios en producción. Es un defecto LATENTE/defensivo: se dispararía si alguien llama el endpoint directo con ?fuente=usuarios o si un tab futuro lo agrega. Confirmo is_real=true por el defecto verificado y la asimetría con el endpoint hermano, manteniendo P2 dado que no hay impacto activo de corrección de datos hoy (sin caller). El fix propuesto (añadir elif fuente=='usuarios' con NOT IN MP/Empaque/Material de Empaque) es correcto y espeja la lógica existente.

</details>

---

### P2.6 [compras/data-correctness] pagar_oc inserta precio_unitario ($/g) en columna precios_mp_historico.precio_kg
**Ubicación:** `api/blueprints/compras.py:6287-6290` · confianza alta

**Por qué es bug:** precio = ordenes_compra_items.precio_unitario está en $/g (subtotal = cantidad_g * precio_unitario, con cantidad en gramos). Se inserta en una columna llamada precio_kg, que por nombre/semántica debe ser $/kg. validar_precios_bulk (10863) y proveedor_recomendado promedian sobre precio_kg y precio_unitario indistintamente; mezclar valores en $/g dentro de precio_kg sesga el promedio 90d 1000x para ese registro, generando falsos 'sospechoso_bajo'/'inflado' en la validación de precios. Mismo error de unidad que el hallazgo de precio_referencia.

**Fix propuesto:** Si la columna es realmente $/kg, insertar precio*1000.0 en precio_kg; si la intención es guardar $/g, usar la columna precio_unitario (como hacen 1024 y 3574). Unificar a la misma convención que el resto de inserts a precios_mp_historico.

<details><summary>Veredicto del verificador</summary>

Confirmado el bug de unidad. (1) El esquema de precios_mp_historico (database.py:8009 y pg_schema.sql:2450) tiene SOLO la columna precio_kg — no existe precio_unitario en esa tabla en ningún motor ni migración. (2) La semántica canónica de precio_kg es genuinamente $/kg: el ingreso de inventario guarda un valor $/kg ingresado por el usuario (inventario.py:6743 y 6802) y lo lee dividiendo /1000 para obtener $/g (inventario.py:3001; frontend compras_html.py:4903 'precio_kg / 1000'). (3) pagar_oc en compras.py:6287-6290 toma ordenes_compra_items.precio_unitario, que está en $/g (subtotal = cantidad_g * precio_unitario; verificado en compras.py:1013 y 1700), y lo inserta en la columna precio_kg → desajuste de unidad ×1000. (4) Los consumidores validar_precios_bulk (compras.py:10863-10878) y proveedor_recomendado (10924-10945) intentan primero la columna precio_unitario (que SIEMPRE lanza excepción porque no existe → rollback silencioso) y caen al fallback que promedia precio_kg. Por tanto sí promedian sobre precio_kg, ahora contaminado con registros $/g 1000× más pequeños que los registros reales $/kg del ingreso. (5) Impacto: el promedio 90d queda sesgado y genera falsos veredictos 'sospechoso_bajo'/'inflado' en la validación de precios. Es exactamente la corrupción de dato advisory descrita. P2 correcto: afecta una señal de validación de precios (sugerencia/alerta), no stock, dinero contable ni dato regulatorio INVIMA; no hay drift de kardex ni pérdida de datos. Matiz: el detalle del reporte de que 'se promedia precio_unitario indistintamente' es técnicamente inexacto (esa columna no existe en la tabla, la query falla), pero la tesis central —$/g escrito en una columna leída como $/kg por los promediadores— está verificada y el impacto se sostiene. Fix recomendado: en compras.py:6287 insertar precio*1000.0 en precio_kg, alineando con la convención $/kg del resto de inserts a precio_kg (inventario.py:6802 y 9669).

</details>

---

### P2.7 [core-resto/crash] chat.py: NameError por 'logger' no definido al fallar push_notif en POST de mensaje *(verificador bajó de P1)*
**Ubicación:** `api/blueprints/chat.py:797` · confianza alta

**Por qué es bug:** El modulo chat.py NO importa logging ni define 'logger' en ninguna parte (verificado por grep: la unica ocurrencia es la linea 797). El bloque envolvente (push_notif a todos los miembros del hilo) esta dentro del handler POST /api/chat/threads/<id>/messages. Si push_notif lanza cualquier excepcion (p.ej. tabla notificaciones_app inaccesible, columna faltante, lock), el except intenta 'logger.warning(...)' y levanta NameError, que NO esta capturado por ningun try externo -> el endpoint devuelve 500 y, peor, el conn.commit() del mensaje YA ocurrio (linea 769) pero el cliente recibe error y reintenta -> mensajes duplicados. Convierte un fallo benigno de notificacion en un 500 con doble-envio.

**Fix propuesto:** Agregar 'import logging' y 'logger = logging.getLogger(__name__)' al tope de chat.py (como en notif.py linea 22-25), o reemplazar la linea 797 por un import local: 'import logging as _lg; _lg.getLogger("chat").warning(...)'.

<details><summary>Veredicto del verificador</summary>

Confirmado: en C:/Users/sebas/Downloads/Claude/Inventarios/api/blueprints/chat.py el simbolo `logger` NO esta definido. Grep muestra que la unica referencia a `logger` es la linea 797 (`logger.warning('push_notif chat fallo: %s', _e)`); no hay `import logging`/`logger=` a nivel de modulo, ni star-imports, ni `logger` exportado por database/config (solo imports de flask, database.get_db, config en lineas 22-24). Las otras dos zonas que logean (lineas 831 y 1057) usan correctamente un `import logging` local + `logging.getLogger('chat')`, justo lo que falta aqui. El handler POST /api/chat/threads/<id>/messages (def chat_messages, linea 702) hace conn.commit() del mensaje en linea 769 ANTES del bloque de notificacion, y NO tiene try/except externo que envuelva el cuerpo del POST. Por tanto, si el `try` interno (lineas 773-795) lanza, el `except` (796-797) ejecuta `logger.warning` -> NameError no capturado -> Flask 500 con el mensaje YA commiteado -> reintento del cliente puede duplicar mensaje. Bug real de symbol indefinido en path de error. AJUSTE DE SEVERIDAD a P2 (no P1): el reporte asume que un fallo de push_notif dispara el except, pero push_notif (notif.py:30-60) es auto-protegido — captura sus propias excepciones internamente y retorna None sin propagar (docstring 'cualquier excepcion se logea pero no propaga'). Por eso el except de 796 solo se activa ante fallos del codigo circundante (el import, o los c.execute de SELECT miembros/nombre del thread post-commit, p.ej. drop de conexion o lock en PostgreSQL), no en operacion rutinaria. Es un crash latente en path de error de baja frecuencia, no un fallo de ruta comun. No viola falsos positivos confirmados ni invariantes; el fix propuesto (import logging local como en 831/1057) es correcto.

</details>

---

### P2.8 [core-resto/authz] hub.py: KPIs de nivel gerencia (valor OCs por pagar, stock critico, pagado semana) accesibles a cualquier usuario logueado sin check de rol
**Ubicación:** `api/blueprints/hub.py:30-77` · confianza alta

**Por qué es bug:** hub_resumen y hub_alertas no validan rol (solo el before_request global exige sesion). Exponen valor monetario total de OCs por autorizar/pagar, monto pagado en la semana, conteo de stock critico y compromisos a CUALQUIER empleado logueado (planta, marketing, operario), datos que en gerencia.py se restringen a FINANZAS_ACCESS. Es fuga de informacion financiera por inconsistencia de autorizacion. (No es 'sin auth' porque el before_request bloquea anonimos, pero falta el gate de rol.)

**Fix propuesto:** Agregar al inicio de hub_resumen/hub_alertas un check de rol coherente (p.ej. FINANZAS_ACCESS o ADMIN_USERS) o reducir los campos sensibles para roles no-finanzas.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el codigo real. El unico gate que cubre /api/hub/resumen (hub.py:30-77) y /api/hub/alertas (hub.py:79-155) es el before_request global require_auth_for_api (auth.py:268-309), que SOLO exige que exista session['compras_user'] (cualquier empleado logueado: planta, operario, marketing). No hay @bp.before_request en hub.py (a diferencia de rrhh.py:43 y maquila.py:39 que si tienen gate de rol), ni check de rol dentro de las funciones. Ambos endpoints devuelven cifras financieras: valor_autorizar y valor_pagar de OCs, pagado_semana, y en alertas el valor_total + proveedor por OC (lineas 71-74, 91-108).

La inconsistencia de autorizacion es real y verificable: la MISMA clase de dato (valor de OCs por autorizar/pagar) esta explicitamente restringida a FINANZAS_ACCESS={mayra,catalina,sebastian,alejandro} en gerencia.py (gerencia_kpis L55, flujo_operacional L170, dashboard_extra L253), y la pagina /gerencia-financiero redirige a /hub a quien no es FINANZAS (L49-50). Ademas, el propio autor SI sabe gatear datos financieros en este mismo archivo: centro_notificaciones gatea las OCs por pagar tras 'u in ADMIN_USERS or u in CONTADORA_USERS' (L416), igual centro_operaciones_data exige ADMIN_USERS (L709) y reporte_semanal_ceo (L1050). Por tanto hub_resumen/hub_alertas son un descuido coherente con fuga de informacion financiera a roles que no deberian verla.

No es falso positivo: no esta en la lista confirmada, no toca invariantes de stock/Fijo/audit. NO es 'sin auth' (anonimos los bloquea el before_request) por eso no es P0/P1. Es lectura-solo, solo usuarios internos logueados, sin corrupcion de datos ni PII (no aplica Habeas Data como en rrhh) ni invariante INVIMA. Severidad P2 correcta: fuga de KPIs financieros agregados a empleados internos por inconsistencia de gate de rol. Fix: agregar al inicio de hub_resumen y hub_alertas un gate FINANZAS_ACCESS para los campos monetarios, o recortar valor_autorizar/valor_pagar/pagado_semana/valor para roles no-finanzas dejando solo conteos.

</details>

---

### P2.9 [core-resto/data-correctness] hub.py centro_notificaciones: alerta de SGDs consulta tabla legacy documentos_sgd en vez de sgd_documentos (donde Tecnica escribe ahora) -> alertas regulatorias fantasma
**Ubicación:** `api/blueprints/hub.py:612-635` · confianza alta

**Por qué es bug:** tecnica.py unifico SGD en la tabla sgd_documentos (rich) y migro/escribe ahi (ver _init_tecnica y todos los endpoints /api/tecnica/documentos que usan sgd_documentos). El bloque de centro_notificaciones de hub.py sigue leyendo la tabla legacy 'documentos_sgd', que ya no recibe SOPs nuevos. El query esta envuelto en try/except: pass, asi que no crashea pero retorna 0 alertas siempre -> los SOPs/PRO que vencen su revision NUNCA aparecen en el Centro de Notificaciones del CEO. Riesgo regulatorio: documentos BPM vencidos pasan desapercibidos. Ademas usa estado='Vigente' (capitalizado, schema legacy) mientras sgd_documentos usa 'vigente' minuscula. KPI/alerta fantasma.

**Fix propuesto:** Cambiar el FROM a sgd_documentos y mapear columnas: titulo (no nombre), aprobado_por (no responsable_revision), estado='vigente' minuscula, proxima_revision; identico al query que ya usa hub.py /api/centro/operaciones linea 906 (documentos_sgd ahi tambien deberia revisarse) y a tecnica.documentos_vencimientos.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el codigo real. hub.py:617 (bloque 613-635) consulta FROM documentos_sgd con estado='Vigente' (capitalizado) y columnas nombre/responsable_revision = schema LEGACY. La fuente activa de SGD es sgd_documentos (creada en migracion 86, database.py:6347) con titulo/aprobado_por/proxima_revision y estado='vigente' en minuscula. Toda la escritura de SGD en tecnica.py va a sgd_documentos (CREAR_SGD tecnica.py:761, REVISAR_SGD :863, UPDATE :954) y la migracion one-shot (database.py:112-176) movio los legacy a sgd_documentos. Verifique que NINGUN code path inserta/actualiza documentos_sgd salvo la migracion muerta 38 (database.py:4717): la tabla legacy quedo congelada con solo filas pre-3-may-2026 ya migradas afuera. El try/except: pass (hub.py:609/634) evita crash pero la consulta retorna un conjunto stale/vacio: los SOPs/PRO que vencen su revision NUNCA aparecen en el Centro de Notificaciones del CEO. Doble verificado el mismatch de schema y el de estado capitalizado vs minuscula. El mismo defecto se repite en hub.py:906 (KPI sgd_vencen_30d en /api/centro/operaciones), tambien apunta a documentos_sgd. Impacto: perdida de visibilidad regulatoria INVIMA/BPM (documentos vencidos pasan desapercibidos), pero NO hay mutacion ni perdida de datos ni crash, por eso P2 es correcto. El julianday se usa en todo el repo y esta shimmed para PG (pg_functions.sql), no es el problema. No cae en ningun falso positivo confirmado.

</details>

---

### P2.10 [db-pg-migraciones/data-correctness] run_migrations silencia "no such table" y marca la migración como aplicada, saltándola para siempre *(verificador bajó de P1)*
**Ubicación:** `api/database.py:7704-7759` · confianza alta

**Por qué es bug:** Cuando un statement falla con 'no such table' (tabla mal escrita, o tabla que una migración anterior no llegó a crear), el except hace `continue` SIN poner `migration_ok=False`. La migración se registra como aplicada en schema_migrations y NUNCA se reintenta. Este es exactamente el incidente documentado en los comentarios (líneas 7710-7716: 'CREATE INDEX fallaba silenciosamente por no such table y los indexes nunca se creaban'); el fix de ordenar por versión no elimina la causa raíz — cualquier migración futura que referencie una tabla genuinamente ausente/con typo queda permanentemente sin aplicar, dejando esquema incompleto (índice/columna/tabla faltante) sin error visible. Riesgo directo de drift de esquema en arranques de prod.

**Fix propuesto:** Quitar 'no such table' de BENIGN_PATTERNS. Si se necesita tolerar un ALTER sobre tabla aún no creada, hacerlo explícito por versión (set BEST_EFFORT) y, ante 'no such table', poner migration_ok=False para que NO se registre y se reintente en el siguiente arranque (cuando la tabla ya exista). Loguear WARNING en lugar de tragar en silencio.

<details><summary>Veredicto del verificador</summary>

Verificado en código real. En database.py:7704-7708 BENIGN_PATTERNS incluye "no such table". En el bucle 7729-7749, cuando un stmt lanza "no such table" la rama 7734-7735 hace `continue` SIN poner migration_ok=False; como el for termina, migration_ok queda True y la migración se registra en schema_migrations (7753-7757) y NUNCA se reintenta. El propio comentario 7710-7716 documenta que este mismo patrón ya causó que CREATE INDEX fallara en silencio y los índices nunca se crearan: confirma que NO es teórico. Esto reintroduce exactamente el anti-patrón que MEMORY/CLAUDE.md prohíbe ("nunca DDL en try/except:pass porque silencia typos") y que safe_alter (database.py:100-129) fue creado para evitar; run_migrations lo reintroduce a nivel de statement individual. Un typo en nombre de tabla o una dependencia inter-versión no satisfecha queda tragada sin error visible y con esquema permanentemente incompleto. MATIZ que baja a P2: el runner de PRODUCCIÓN es PG (index.py:300-396); init_db() retorna early en PG (database.py:7769-7770), y PG lanza 'relation "..." does not exist', NO la frase SQLite 'no such table' — por lo que en PG ese stmt SÍ cae a _v_ok=False+break y NO se registra (comportamiento correcto). El riesgo real activo está en el camino SQLite: dev, la suite de tests, y crucialmente el build SQLite del proceso de cutover a PG (database.py:7766-7768 construye un SQLite con init_db y copia datos a PG), donde una migración silenciosamente saltada propagaría esquema incompleto al cutover. La afirmación del hallazgo de "drift en arranques de prod" es imprecisa (prod=PG no matchea la cadena), pero el bug latente de corrección/no-reintento es real. Fix propuesto correcto: quitar "no such table" de BENIGN_PATTERNS o, ante ese error, poner migration_ok=False + WARNING para que se reintente cuando la tabla exista.

</details>

---

### P2.11 [finanzas-cartera/data-correctness] Dashboard Espagiria omite tipo 'Ajuste' (delta con signo) al calcular stock → alertas de stock incorrectas *(verificador bajó de P1)*
**Ubicación:** `api/blueprints/espagiria.py:76-78` · confianza alta

**Por qué es bug:** La invariante de dominio (y la fórmula canónica en programacion.py líneas 664/708/1879/5768: `tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad`) suma el tipo bare 'Ajuste' como delta POSITIVO con signo. Estas dos queries de espagiria (dashboard 'mps_bajo_minimo' L76-78 y alertas 'stock_cero' L230-232) solo contemplan 'Ajuste +'/'Ajuste -' y mandan cualquier movimiento 'Ajuste' al `ELSE 0`, ignorándolo. Para MPs cuyos ajustes de inventario se registraron con tipo 'Ajuste' (signed), el stock mostrado a Luz queda mal: puede generar falsas alertas de 'MP en cero'/'bajo mínimo' o, al revés, ocultar faltantes reales. Es drift de stock contra la fuente canónica.

**Fix propuesto:** Alinear el CASE con la fórmula canónica de programacion.py: `WHEN mov.tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN mov.cantidad WHEN mov.tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -mov.cantidad`. Aplicar en ambas queries (L76-78 y L230-232).

<details><summary>Veredicto del verificador</summary>

Confirmado en código real. espagiria.py:76-78 (dashboard mps_bajo_minimo) y 230-232 (alertas stock_cero) hacen LEFT JOIN movimientos ON mov.material_id=m.codigo_mp y calculan stock con CASE WHEN tipo IN ('Entrada','Ajuste +') THEN cantidad / WHEN tipo IN ('Salida','Ajuste -') THEN -cantidad / ELSE 0. El tipo bare 'Ajuste' cae en ELSE 0 y se ignora. Esto viola la fórmula canónica de stock MP que aparece idéntica en ~40 queries del codebase: programacion.py:664/708/1879/5768, inventario.py:201/3917/etc, admin.py, compras.py, gerencia.py:58, core.py:371 — todas incluyen 'Ajuste' (bare) en la rama POSITIVA. La invariante de dominio dice que un movimiento 'Ajuste' guarda DELTA con signo y se suma como positivo; tratarlo como ELSE 0 (o como resta) es bug. Verifiqué que filas bare 'Ajuste' SÍ existen en la tabla movimientos: inventario.py:10207-10211 documenta explícitamente que tipo='Ajuste' es legacy pre-may-2026 con signo, y bloquea su anulación automática porque 'el signo del ajuste se perdía' — prueba de que esas filas persisten en movimientos. Para MPs con esos ajustes legacy, el stock mostrado a Luz queda mal y genera falsas alertas de bajo-mínimo/cero o esconde faltantes. Refuté la parte de la severidad: es una vista de lectura (dashboard/alertas), no muta stock almacenado ni registros INVIMA, y los flujos actuales de MP ya usan Entrada/Salida (bare 'Ajuste' es mayormente legacy), por lo que el impacto es operativo moderado, no P1. Fix correcto: alinear ambos CASE con la fórmula canónica añadiendo 'Ajuste' a la rama positiva (y opcionalmente las variantes de mayúsculas).

</details>

---

### P2.12 [inventario/data-correctness] analisis-abc (MP) y consumo calculan stock tratando 'Ajuste'/'Ajuste +' como resta → valoración y clasificación ABC sesgadas
**Ubicación:** `api/blueprints/inventario.py:3433-3434` · confianza alta

**Por qué es bug:** Mismo patrón: 'Ajuste' positivo y 'Ajuste +' se restan en vez de sumar. El stock_map alimenta valor_cop (valoración de inventario) y la clasificación ABC que orienta decisiones de compra/criticidad. Para MPs con ajustes positivos el valor del inventario queda subvalorado. Diverge de la fuente canónica /api/stock dentro del mismo archivo.

**Fix propuesto:** Usar SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') THEN cantidad WHEN tipo IN ('Salida','salida','SALIDA','Ajuste -') THEN -cantidad ELSE 0 END).

<details><summary>Veredicto del verificador</summary>

Confirmado en api/blueprints/inventario.py:3431-3440 (endpoint análisis-ABC, path MP). El query de stock usa COALESCE(SUM(CASE WHEN tipo IN ('Entrada','entrada','ENTRADA') THEN cantidad ELSE -cantidad END),0), que mete 'Ajuste' (delta positivo, canónico = sumar) y 'Ajuste +' en el ELSE -cantidad, restándolos. Viola la invariante dura: el patrón canónico suma 'Ajuste'/'Ajuste +'. El propio archivo usa el patrón correcto 11+ veces (líneas 201, 208, 215, 230, 1967, 2017, 2405, 2553, 2571, 2675, 2697: SUM(CASE WHEN tipo IN ('Entrada',...,'Ajuste +','Ajuste') THEN cantidad WHEN tipo IN ('Salida',...,'Ajuste -') THEN -cantidad ELSE 0 END)), confirmando la divergencia. El stock_map (línea 3440, con clamp max(...,0)) alimenta valor_cop = stock*precio (3484) y la métrica de clasificación ABC/Pareto (3508-3538), que orienta decisiones de compra/criticidad. Para MPs con ajustes positivos netos, el inventario queda subvalorado y el ranking ABC sesgado. No es mutación de stock ni toca _get_mp_stock, es una vista de análisis/decisión, por lo que P2 es la severidad correcta. No aplica ningún falso positivo confirmado.

</details>

---

### P2.13 [inventario/data-correctness] eliminar_lote calcula saldo_neto tratando 'Ajuste'/'Ajuste +' como negativo → contra-movimiento incorrecto deja stock residual o negativo
**Ubicación:** `api/blueprints/inventario.py:5502-5505` · confianza alta

**Por qué es bug:** Al 'eliminar' un lote ya no se hace DELETE sino un contra-movimiento del saldo neto (línea 5550-5559). El saldo_neto solo suma 'Entrada' y resta TODO lo demás. Si el lote tiene un movimiento 'Ajuste' (positivo) o 'Ajuste +', se cuenta como negativo y el contra-movimiento generado no cancela el saldo real → tras 'eliminar' el lote queda con stock residual (o negativo) en el kardex en lugar de cero. Rompe la intención de cancelar el saldo del lote.

**Fix propuesto:** Calcular saldo_neto con la regla canónica: + para tipo in ('Entrada','Ajuste +','Ajuste'), - para tipo in ('Salida','Ajuste -').

<details><summary>Veredicto del verificador</summary>

Confirmado. En api/blueprints/inventario.py:5502-5505, eliminar_lote calcula saldo_neto con la regla `(+cantidad si tipo=='Entrada' else -cantidad)`, tratando TODO lo que no sea 'Entrada' como negativo. Esto contradice la regla canonica de stock usada en ~30 queries del propio archivo y en _get_mp_stock (programacion.py:664-666): tipo IN ('Entrada','Ajuste +','Ajuste') suman; tipo IN ('Salida','Ajuste -') restan. MEMORY tambien lo fija: 'Ajuste' es un delta con signo que SUMA.

Verifique que existe un productor real de filas tipo 'Ajuste'/'Ajuste +'/'Ajuste -' en la tabla movimientos CON lote: el endpoint de movimiento manual (inventario.py:1700-1749) acepta tipo='Ajuste' y permite lote (comentario linea 1731-1733: 'Para Salida/Ajuste sigue opcional'), insertando cantidad>0 tal cual. El path de conteo ciclico (lineas 7705, 7950) usa Entrada/Salida, asi que ese path NO se ve afectado, pero el manual si.

Aritmetica del bug, lote con una fila tipo='Ajuste', cantidad=100, lote='L1' (saldo canonico real del lote = +100): linea 5503 da saldo_neto = -100; linea 5550 abs(-100)>0.01 true; tipo_contra='Entrada' (saldo<0) inserta Entrada 100. El stock canonico del lote pasa de +100 a +200 en lugar de 0. En vez de cancelar, DUPLICA el saldo en direccion equivocada. Con 'Ajuste +' ocurre lo mismo; con 'Ajuste -' (negativo real) lo trata como -cantidad y genera un contra-mov errado tambien. Ademas el contra-mov se inserta con estado_lote='ELIMINADO', que NO esta en la lista de exclusion de _get_mp_stock (CUARENTENA/VENCIDO/RECHAZADO/AGOTADO), por lo que cuenta en stock. El clamp max(...,0) por material_id en _get_mp_stock enmascara parcialmente el residual a nivel material, pero las vistas por-lote (lineas 2405, 2553, 2675, 7250, etc.) no tienen clamp y muestran el residuo/duplicado.

El fix propuesto (regla canonica: + para Entrada/Ajuste +/Ajuste, - para Salida/Ajuste -) es correcto y consistente con el resto del codigo. Severidad P2 confirmada: bug real de correctness/integridad de kardex en lote trazado INVIMA, pero requiere combinacion poco frecuente (lote con fila Ajuste manual + borrado manual de lote) y el path comun de conteo ciclico no se ve afectado, por lo que no es P0/P1.

</details>

---

### P2.14 [inventario/data-correctness] Pre-check de stock en POST /api/movimientos (Salida) ignora 'Ajuste' → permite oversell o bloquea salidas legítimas
**Ubicación:** `api/blueprints/inventario.py:1718-1724` · confianza alta

**Por qué es bug:** El guard que evita stock negativo en una Salida calcula el saldo solo con Entrada/Salida, ignorando 'Ajuste','Ajuste +','Ajuste -'. Si hubo un 'Ajuste -' (resta real) el saldo aquí queda sobreestimado y permite una Salida que deja stock negativo (el bug que el propio comentario dice evitar). Inversamente, un 'Ajuste'/'Ajuste +' positivo no se suma y puede bloquear una Salida legítima por 'stock insuficiente'. No coincide con el cálculo canónico de stock.

**Fix propuesto:** Reemplazar el CASE por la forma canónica con los cinco tipos (suma Entrada/Ajuste+/Ajuste, resta Salida/Ajuste-), consistente con stock_mp_total en inventario_helpers.py.

<details><summary>Veredicto del verificador</summary>

Confirmado en api/blueprints/inventario.py:1718-1723. El pre-check de Salida calcula saldo con CASE solo de Entrada (+) y Salida (-), con ELSE 0 para todo lo demás. Esto descarta por completo las filas 'Ajuste', 'Ajuste +' y 'Ajuste -'. Contrasta con el cálculo CANÓNICO usado en todo el resto del sistema: stock_mp_total (inventario_helpers.py:52-62) y _get_mp_stock (programacion.py:661-668, y ~6 sitios más: 708, 1879, 5768, 5969, 6008) que suman Entrada/Ajuste+/Ajuste y restan Salida/Ajuste-. Las filas de variantes 'Ajuste +'/'Ajuste -'/'Ajuste' SÍ existen en BD (creadas por otros endpoints, p.ej. el ajuste con direccion en programacion.py:6783; por eso los cálculos canónicos las manejan explícitamente y un comentario en 655 documenta que antes 'Ajuste contaba como Salida' fue bug). Impacto real: (1) un 'Ajuste -' previo (merma/conteo) se ignora → saldo sobreestimado → permite una Salida que deja stock negativo, justo el oversell que el comentario dice evitar — drift de stock en inventario regulado INVIMA; (2) un 'Ajuste'/'Ajuste +' positivo no se suma → saldo subestimado → bloquea una Salida legítima con falso 'stock insuficiente' (422). No coincide con la invariante de stock canónico (Ajuste = delta con signo). Nota: el propio endpoint restringe tipo a ('Entrada','Salida','Ajuste') en línea 1705, así que él no crea variantes +/-, pero el saldo se computa sobre TODO el histórico de movimientos del material, que sí contiene esas variantes. El fix propuesto (usar la forma canónica de cinco tipos) es correcto. Severidad P2 adecuada: es un guard inexacto que solo se desvía cuando hay filas Ajuste sobre el material, no corrupción en la ruta común.

</details>

---

### P2.15 [inventario/data-loss] Movimiento MEE 'Salida' clampa stock_actual a 0 pero registra la cantidad completa en movimientos_mee → drift permanente cache vs kardex
**Ubicación:** `api/blueprints/inventario.py:9927, 9933` · confianza alta

**Por qué es bug:** El kardex MEE tiene dos fuentes que deben cuadrar (maestro_mee.stock_actual y SUM(movimientos_mee)). Una Salida mayor que el stock disponible: el movimiento registra cantidad completa (Salida resta cantidad en stock_mee_calculated) pero stock_actual se clampa a MAX(0,...). Tras eso, stock_mee_persisted (0) != stock_mee_calculated (negativo): drift permanente, justo lo que detect_drift_mee marca como bug operacional. El clamp además oculta una salida imposible en lugar de rechazarla. Mismo defecto existe en el helper aplicar_movimiento_mee (inventario_helpers.py línea 238-247: clampa stock_nuevo a 0 pero inserta cantidad completa).

**Fix propuesto:** Rechazar la Salida cuando cantidad > stock_actual (HTTP 422, como el pre-check de MP), o registrar en movimientos_mee solo la cantidad efectivamente descontada. No clampar el persisted mientras se registra el total en el log. Aplicar el mismo arreglo en aplicar_movimiento_mee.

<details><summary>Veredicto del verificador</summary>

Confirmado en código real. En mee_registrar_movimiento (api/blueprints/inventario.py:9924-9933) el INSERT a movimientos_mee guarda mov_cantidad completa (=cantidad para Salida) pero el UPDATE clampa: "UPDATE maestro_mee SET stock_actual = MAX(0, stock_actual - ?)" (línea 9933). NO hay pre-check de stock antes del INSERT. Cuando cantidad > stock_actual, queda stock_mee_persisted=0 pero stock_mee_calculated negativo → drift permanente. Esto es exactamente lo que detect_drift_mee (api/inventario_helpers.py:309-340) está construido para marcar como bug operacional (persisted - calculated != 0). El mismo defecto existe en aplicar_movimiento_mee (api/inventario_helpers.py:238-248): clampa stock_nuevo a 0.0 pero inserta cantidad completa; este helper lo usa _descontar_mee_envasado (programacion.py:6147). Asimetría verificada: el endpoint de movimiento MP SÍ rechaza con HTTP 422 'stock insuficiente' cuando saldo < cantidad (inventario.py:1717-1730), mientras MEE solo clampa silenciosamente. El test test_descontar_mee_envasado_clamp_no_negativo (tests/test_produccion_drift_invariante.py:105-139) asevera el clamp (stock==0, stock>=0) pero NO verifica drift==0 en ese caso, confirmando que el clamp con drift no está cubierto/protegido. Impacto real pero acotado: solo dispara en el edge case de Salida que excede stock disponible; corrompe la consistencia cache vs kardex y oculta una salida imposible en lugar de rechazarla. P2 correcto (integridad de datos / drift, no pérdida catastrófica). No es falso positivo confirmado de la lista.

</details>

---

### P2.16 [maquila-comercial/authz] Reanimación de OC de maquila en estado terminal (Cancelada/Completada) accesible a cualquier compras_user con force=true, pese a que el código lo documenta como 'admin' *(verificador bajó de P1)*
**Ubicación:** `api/blueprints/maquila.py:241-247` · confianza alta

**Por qué es bug:** El gate _maquila_gate (L39-54) solo exige pertenecer a COMPRAS_USERS|ADMIN_USERS. El único obstáculo para reanimar una OC terminal es enviar force=true en el body; NO hay verificación de ADMIN_USERS. El mensaje '(admin)' es engañoso: cualquier usuario de compras (p.ej. Mayerlin, Catalina) puede pasar Cancelada→Completada (lo que la docstring L223 dice que se intentó prevenir). Eludir un control de estado terminal sin el rol previsto es un bug de autorización/integridad.

**Fix propuesto:** Antes del UPDATE, si estado_ant es terminal y se usa force, exigir admin: if d.get('force') and session.get('compras_user') not in ADMIN_USERS: return jsonify({'error':'Solo admin puede reanimar OC terminal con force'}), 403. Registrar override en audit_log (ya se hace) marcando force.

<details><summary>Veredicto del verificador</summary>

Confirmado en código real. En api/blueprints/maquila.py:241-247 el guard de estado terminal solo verifica `not d.get('force')`; no hay chequeo de ADMIN_USERS. El gate global _maquila_gate (L39-54) solo exige pertenecer a COMPRAS_USERS|ADMIN_USERS, y COMPRAS_USERS (config.py L16-22) incluye no-admins (hernando, catalina, luz, daniela), mientras ADMIN_USERS={sebastian,alejandro} (config.py L37). Por tanto cualquier compras_user puede reanimar una OC terminal (Cancelada/Completada → otro estado) enviando force=true. El comentario L234-235 ('sin admin override') y el mensaje L243-244 ('(admin)') afirman que se requiere admin, pero el código NO lo impone — control engañoso. Prueba de que el patrón correcto existe en el mismo archivo: L564 sí valida `session.get('compras_user') not in ADMIN_USERS` para el endpoint de recall. El fix propuesto (exigir ADMIN_USERS cuando force=true sobre estado terminal) es correcto y factible (ADMIN_USERS ya importado L10). Rebajo de P1 a P2: es un defecto authz/integridad real pero de impacto moderado — requiere usuario interno autenticado de compras, la override YA queda auditada con flag force (audit_log L250-255, force registrado L254), afecta solo órdenes de maquila (lado comercial, no stock/kardex ni dato regulado INVIMA), y no implica SQLi/XSS, pérdida de datos ni drift de stock. No es falso positivo: el comportamiento contradice explícitamente la intención documentada del propio código.

</details>

---

### P2.17 [maquila-comercial/data-correctness] facturar maquila: descuento e iva_pct sin validación permiten factura con base/total negativo
**Ubicación:** `api/blueprints/maquila.py:303-307` · confianza alta

**Por qué es bug:** descuento e iva_pct se toman crudos sin validate_money ni límites. Un descuento mayor que valor_servicio produce base_iva e iva_valor negativos y un total negativo persistido en la tabla facturas (factura fiscal con valores negativos). iva_pct negativo o astronómico también pasa. El resto del módulo usa validate_money justamente para evitar esto; aquí se omitió en un endpoint que escribe contabilidad fiscal.

**Fix propuesto:** Validar: descuento con validate_money(allow_zero=True) y exigir descuento <= valor_servicio; iva_pct acotado a un rango razonable (0..100). Rechazar con 400 si base_iva < 0.

<details><summary>Veredicto del verificador</summary>

Confirmado en api/blueprints/maquila.py:303-307. El endpoint /api/maquila/ordenes/<oid>/facturar toma iva_pct y descuento crudos con float() sin validate_money: iva_pct=float(d.get('iva_pct',19)); descuento=float(d.get('descuento',0)); base_iva=valor_servicio-descuento; total=base_iva+iva_valor. Estos valores se persisten directamente en la tabla fiscal facturas (líneas 312-321) con estado='Emitida'. El mismo módulo SÍ usa validate_money en sus otros endpoints (líneas 66, 172, 176), confirmando que la omisión aquí es inconsistente y no intencional. Impactos verificados: (1) descuento > valor_servicio produce base_iva e iva_valor negativos y total negativo persistido en una factura fiscal; (2) descuento negativo infla artificialmente el total; (3) iva_pct negativo o astronómico pasa sin tope; (4) float('nan')/float('inf') en iva_pct o descuento NO lanza excepción y persiste NaN/Infinity en columnas fiscales (validate_money sí bloquea esto vía math.isnan/isinf en http_helpers.py:94). Según el docstring (línea 264-265) estas facturas alimentan flujo_ingresos al cobrarse, propagando los valores corruptos a contabilidad. NO es falso positivo: no está cubierto por ninguno de los FP confirmados. La severidad P2 es correcta: es data-correctness/integridad fiscal, no hay crash 500 (la aritmética float no falla), no es drift de stock ni bypass de auth, y el endpoint está protegido por el gate before_request que exige login + rol COMPRAS/ADMIN (líneas 39-54), por lo que el atacante debe ser staff autenticado, no externo. Fix correcto: validar descuento con validate_money(allow_zero=True) y exigir descuento<=valor_servicio, acotar iva_pct a 0..100, y rechazar con 400 si base_iva<0.

</details>

---

### P2.18 [maquila-comercial/data-correctness] PATCH prospecto y cotizar maquila persisten montos crudos con float() sin validate_money (NaN/Infinity/negativos)
**Ubicación:** `api/blueprints/maquila.py:137-138, 357-364` · confianza alta

**Por qué es bug:** El POST de prospectos (L66) usa validate_money para valor_estimado, pero el PATCH (L137) lo persiste con float() crudo: float('nan')/float('inf') o un negativo entran a valor_estimado_lote, que luego se suma en api_maquila_kpis (SUM(valor_estimado_lote)) contaminando el pipeline. Igual en /api/maquila/cotizar: todos los montos van crudos. float() también lanza ValueError → 500 si el cliente manda texto. Inconsistencia que reintroduce justo lo que validate_money fue creado para tapar.

**Fix propuesto:** En el PATCH usar validate_money(d['valor_estimado'], allow_zero=True) y retornar 400 si err. En cotizar validar costo_mp, costo_proceso, margen_pct y valor_total con validate_money antes del INSERT.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. validate_money (api/http_helpers.py:71-106) rechaza NaN/Infinity/negativos/fuera-de-rango y devuelve error sin lanzar. El POST de prospectos (maquila.py:66-69) y el POST de órdenes (172-179) lo usan correctamente, pero dos rutas lo omiten: (1) PATCH prospecto maquila.py:137-138 persiste float(d['valor_estimado']) crudo en valor_estimado_lote, columna que se suma en api_maquila_kpis (maquila.py:375: COALESCE(SUM(valor_estimado_lote),0)) para valor_pipeline → un NaN/Infinity/negativo contamina el KPI; además float() crudo lanza ValueError → 500 si el cliente envía texto no numérico. (2) /api/maquila/cotizar maquila.py:361-364 inserta batch_size_kg, costo_mp, costo_proceso, margen_pct y valor_total todos con float() crudo sin validación. Es exactamente el caso que validate_money fue creado para tapar (su docstring lo dice). Impacto moderado: el SUM filtra estado='Activo', y maquila es CRM comercial (no toca stock/kardex ni invariante INVIMA/SOL), por lo que P2 es la severidad correcta. No es falso positivo confirmado en la lista. Fix: usar validate_money(allow_zero=True) en ambos endpoints y retornar 400 ante err.

</details>

---

### P2.19 [maquila-comercial/crash] PATCH solicitud de producción ANIMUS sin validación de estado ni audit_log
**Ubicación:** `api/blueprints/maquila.py:474-481` · confianza alta

**Por qué es bug:** A diferencia del resto del módulo (que tras la auditoría zero-error añadió snapshot+audit_log+whitelist en cada PATCH), este endpoint hace UPDATE de estado sin whitelist de valores y sin audit_log. solicitudes_produccion alimenta el flujo de abastecimiento/planta; un estado arbitrario o un cambio sin rastro de quién/cuándo rompe la trazabilidad operativa que el propio módulo exige.

**Fix propuesto:** Validar d['estado'] contra una whitelist (Pendiente/Aprobada/Rechazada/Completada/etc.), capturar snapshot previo y registrar audit_log con antes/después como en los demás PATCH del archivo.

<details><summary>Veredicto del verificador</summary>

Confirmado, pero la categoría "crash" es incorrecta (no hay riesgo de 500: 'estado' es columna TEXT, acepta cualquier string; y el endpoint SÍ está autenticado por el gate before_request L39-54 que exige compras_user en COMPRAS_USERS|ADMIN_USERS → no es hueco de authz). El bug REAL es de trazabilidad/consistencia: api/blueprints/maquila.py:474-481 hace UPDATE solicitudes_produccion SET estado=? sin whitelist ni audit_log. Esto viola dos cosas verificadas en el código: (1) la invariante "audit_log OBLIGATORIO en toda mutación de SOL/produccion" — nótese que el INSERT de esta misma tabla SÍ audita (L451-456) pero el cambio de estado no deja rastro; (2) la consistencia del propio módulo: el endpoint hermano api_maquila_orden_patch (L219-259), endurecido en la auditoría zero-error del 25-may-2026, tiene whitelist {'Borrador','En proceso','Completada','Cancelada'}, guard de estado terminal y audit_log — animus_update_solicitud quedó fuera de ese pase. La tabla alimenta abastecimiento (estado='Pendiente' se consulta para dedup en L433), así que un estado arbitrario o un cambio sin rastro de quién/cuándo es un gap operativo real. P2 correcto: requiere login, no es pérdida de datos ni drift de stock, pero sí incumple la regla de audit obligatorio. Fix: snapshot previo + whitelist + audit_log igual que L228-257.

</details>

---

### P2.20 [marketing-cmo/data-correctness] Urgencia de pagos: comparación date vs datetime marca como 'vencido' un pago que vence HOY (off-by-one)
**Ubicación:** `api/blueprints/marketing.py:701-704` · confianza alta

**Por qué es bug:** `v` se parsea a medianoche (00:00:00) mientras `hoy = _dt.now()` trae la hora actual del día. Para un pago cuyo `vence_pago_at` es la fecha de HOY, `v - hoy` resulta negativo (p.ej. -0.6 días → `.days == -1`), por lo que se clasifica como 'vencido' y suma a `valor_vencido_total`/`kpis['vencidos']`. El panel le muestra a Jefferson '🚨 N pago(s) ATRASADO(s)' incluyendo pagos que en realidad vencen hoy y aún están a tiempo. El mismo desfase corre la frontera 'urgente'/'proximo' un día antes de lo definido en el docstring. Es la promesa de 30 días (feature 27-may) calculando mal el estado de mora.

**Fix propuesto:** Comparar fechas, no datetimes: `hoy = _dt.now().date()` y `dias_para_vencer = (v.date() - hoy).days`, o parsear `vence` y `hoy` ambos a `.date()` antes de restar. Así un pago que vence hoy da `dias_para_vencer == 0` → 'urgente', no 'vencido'.

<details><summary>Veredicto del verificador</summary>

Confirmado en api/blueprints/marketing.py:691,701-704. `hoy = _dt.now()` (línea 691) incluye la hora actual del día; `v = _dt.strptime(vence,'%Y-%m-%d')` (línea 701) queda a medianoche 00:00:00. Para un pago que vence HOY: v=2026-05-28 00:00:00, hoy=2026-05-28 HH:MM. La resta `v - hoy` (línea 702) da un timedelta negativo (p.ej. -14h), y `.days` de un timedelta negativo en Python redondea hacia -infinito, dando -1. Por tanto `dias_para_vencer == -1 < 0` (línea 703) clasifica el pago como 'vencido' cuando aún está a tiempo. Esto contradice el propio docstring (líneas 669-673: 'vencido: vence_pago_at < hoy', 'urgente: vence en próximos 7 días'). Infla kpis['vencidos'] (línea 713) y valor_vencido_total (línea 718), y dispara el mensaje '🚨 N pago(s) ATRASADO(s)' (líneas 720-724) incluyendo pagos que vencen hoy. Además corre las fronteras urgente(<=7)/proximo(<=15) un día antes. Impacto: solo display/KPI del panel de pagos influencer — no hay drift de stock, pérdida de datos, ni violación de invariante INVIMA. El fix propuesto (usar .date() en ambos lados: hoy=_dt.now().date() y (v.date()-hoy).days) es correcto y haría que un pago que vence hoy dé dias_para_vencer==0 → 'urgente'. No coincide con ningún falso positivo confirmado. Severidad P2 adecuada.

</details>

---

### P2.21 [marketing-cmo/security] mkt_atribucion_influencers filtra traceback completo del servidor al cliente en el catch
**Ubicación:** `api/blueprints/marketing.py:6173-6174` · confianza alta

**Por qué es bug:** Ante cualquier excepción el endpoint devuelve `traceback.format_exc()` (últimos 500 chars) en el JSON de respuesta. El traceback expone rutas internas de archivos, nombres de funciones/tablas y fragmentos de SQL al cliente autenticado de marketing — divulgación de información que facilita reconnaissance de la estructura interna (tablas pagos_influencers, animus_shopify_orders, columnas). No es un crash pero sí fuga de detalles internos en un módulo que maneja datos financieros y bancarios.

**Fix propuesto:** Loguear el traceback server-side (`log.exception(...)`) y devolver al cliente solo un mensaje genérico: `return jsonify({'error': 'Error interno al calcular atribución'}), 500`. No incluir `traceback.format_exc()` en la respuesta JSON.

<details><summary>Veredicto del verificador</summary>

Confirmado en código real: api/blueprints/marketing.py:6173-6174 el except devuelve `jsonify({"error": str(e), "trace": traceback.format_exc()[-500:]}), 500`, exponiendo el traceback (rutas de archivos, nombres de funciones, fragmentos de SQL y nombres de tablas como pagos_influencers / animus_shopify_orders) al cliente. El endpoint mkt_atribucion_influencers exige _auth() (linea 6077), que solo permite usuarios autenticados pertenecientes a MARKETING_USERS (linea 167-173), por lo que NO es una fuga a usuarios anónimos/externos sino divulgación de internos a staff de marketing ya confiado — esto reduce el impacto practico. Es information disclosure de higiene, no SQLi/XSS/authz bypass, sin perdida de datos, sin drift de stock, sin crash. Ademas es un patron deliberado y extendido en todo el codebase (9+ ocurrencias en programacion.py, auto_plan.py, admin.py, marketing.py 3780/3008), lo que indica que es una conveniencia diagnostica intencional del ERP interno y no un descuido aislado. Bug real pero de bajo impacto; P2 es la severidad correcta. El fix propuesto (log.exception server-side + mensaje generico) es valido pero deberia aplicarse de forma consistente a todo el patron, no solo a esta linea.

</details>

---

### P2.22 [perf-n1/performance] N+1 en scoring RFM de clientes B2B: 4 queries por cliente *(verificador bajó de P1)*
**Ubicación:** `api/blueprints/clientes.py:503-561` · confianza alta

**Por qué es bug:** Endpoint de scoring de aliados (CRM). Por cada cliente activo se ejecutan 4 queries a la tabla pedidos (lista de fechas + revenue mes + revenue mes anterior + LTV). Con N clientes son 4*N round-trips. Todo es calculable en 1-2 queries agrupadas: SELECT cliente_id, MIN/MAX(fecha), SUM(CASE WHEN fecha>=mes_ini...), SUM(valor_total) ... GROUP BY cliente_id. Escala mal a medida que crece la base B2B.

**Fix propuesto:** Reemplazar el loop por una unica query GROUP BY cliente_id que devuelva ultima_fecha, conteo, rev_mes (SUM con CASE WHEN fecha>=mes_ini), rev_ant (SUM con CASE WHEN entre fechas) y ltv (SUM total). Las fechas para frecuencia se pueden traer en una sola query ORDER BY cliente_id, fecha y agrupar en Python.

<details><summary>Veredicto del verificador</summary>

Confirmado en clientes.py:503-561. El loop `for (aid, nombre) in aliados:` ejecuta exactamente 4 queries contra `pedidos` por cada aliado: (1) lista de fechas ordenadas (línea 507-509), (2) revenue mes actual (544-547), (3) revenue mes anterior (550-553) y (4) LTV total (558-561). Con N aliados = 4*N round-trips. Es colapsable a 1 query GROUP BY cliente_id para los 3 SUMs + 1 query ORDER BY cliente_id,fecha para frecuencia/recencia, tal como propone el fix. La tabla pedidos tiene índice idx_pedidos_cliente(cliente_id, fecha DESC) (database.py:6021), así que cada query individual es barata y no hay riesgo de full-scan. No viola ninguna invariante ni cae en falsos positivos confirmados. Rebajo de P1 a P2: es un endpoint de CRM/scoring de baja frecuencia (no hot path de checkout/stock), la base B2B de un solo fabricante cosmético es pequeña (decenas, quizá baja centena de aliados activos con activo=1 y empresa='ANIMUS'), y todas las queries están indexadas — el impacto real es latencia moderada del dashboard que crece linealmente, no un crash ni degradación severa actual. Optimización legítima pero P2.

</details>

---

### P2.23 [perf-n1/performance] N+1 en detector de codigos_mp huerfanos: 1-2 queries de stock por cada ingrediente de cada formula *(verificador bajó de P1)*
**Ubicación:** `api/blueprints/inventario.py:2400-2436` · confianza alta

**Por qué es bug:** Endpoint diagnostico que itera TODOS los formula_items (todos los ingredientes de todas las formulas, potencialmente cientos de filas). Por cada uno ejecuta una agregacion de stock sobre movimientos, y para los huerfanos una segunda query con JOIN a movimientos + doble LIKE (full scan). Es O(filas_formula) queries pesadas — facilmente cientos de agregaciones sobre la tabla movimientos en una sola request.

**Fix propuesto:** Calcular el stock por material_id una sola vez con un GROUP BY material_id sobre movimientos en un dict, y filtrar en Python los que tienen stock<=0 antes de buscar candidatos. La busqueda de candidato por LIKE solo para los pocos huerfanos restantes.

<details><summary>Veredicto del verificador</summary>

El patron N+1 existe tal cual se reporta en api/blueprints/inventario.py:2400-2436. El loop itera TODAS las filas de formula_items con material_id (linea 2393-2398) y por cada una ejecuta una agregacion de stock sobre movimientos (2403-2411). Para los huerfanos ejecuta una segunda query con LEFT JOIN a movimientos y doble LIKE '%...%' (2422-2436). El LIKE con wildcard inicial NO puede usar indice, por lo que es un scan completo de maestro_mps x movimientos por cada huerfano. Confirmado is_real.

PERO la severidad P1 esta sobrestimada, por dos razones verificadas en el codigo:
1) La query de stock por fila (2403-2411) SI esta respaldada por indices: idx_mov_material y idx_mov_material_id (database.py:5914, 7313) e idx_mov_lote sobre (material_id, lote). Asi que el caso comun (linea 2415-2416: stock_fefo>0 -> continue) es una sola agregacion index-backed por fila, no una query pesada.
2) La query cara con LIKE solo corre para los pocos huerfanos restantes (rows con stock<=0 y nombre>=4 chars), que por definicion del endpoint son un subconjunto pequeno.

Ademas es un endpoint de SOLO LECTURA (dry-run global), disparado MANUALMENTE por un boton del dashboard (auditarFormulasHuerfanas en dashboard_html.py:6044-6046), no en un hot-path, ni en page-load, ni en cron. La escala de formula_items esta acotada a los ingredientes de todas las formulas (decenas a pocos cientos en un fabricante de cosmetica), no decenas de miles. El costo real es: ~cientos de agregaciones index-backed + un punado de scans LIKE en una request diagnostica ocasional. Es una ineficiencia real y el fix propuesto (precomputar stock por material_id con un GROUP BY unico y filtrar en Python) es valido, pero no es un N+1 severo que degrade operaciones normales -> P2, no P1. No viola ninguna invariante de dominio (el CASE de Ajuste suma con signo correctamente, no toca Fijo, es read-only).

</details>

---

### P2.24 [perf-n1/performance] N+1 en export Siigo: 2 queries por factura dentro del loop de export
**Ubicación:** `api/blueprints/contabilidad.py:633-639` · confianza alta

**Por qué es bug:** Export contable por rango de fechas: por cada factura del periodo ejecuta 2 queries (items + pagos). Para un export de un mes con cientos de facturas son 2*N round-trips. Patron clasico de N+1 en endpoint de exportacion que puede crecer sin limite con el rango solicitado.

**Fix propuesto:** Traer todos los items y pagos del rango en 2 queries con WHERE numero_factura IN (SELECT numero FROM facturas WHERE fecha entre...) (o JOIN), y agrupar en Python por numero_factura en dicts.

<details><summary>Veredicto del verificador</summary>

Confirmado en código real. api/blueprints/contabilidad.py:633-639 ejecuta exactamente 2 queries por factura dentro del loop `for f in facturas` (SELECT * FROM facturas_items WHERE numero_factura=? y SELECT * FROM facturas_pagos WHERE numero_factura=?). `facturas` viene de un SELECT por rango de fechas (línea 624: fecha_emision entre desde/hasta, default mes actual), así que para un export mensual con cientos de facturas son 2*N round-trips. Agravante verificado en database.py:9013-9032: las tablas facturas_items y facturas_pagos NO tienen índice sobre numero_factura (solo existe idx sobre pagos_oc, otra tabla), por lo que en PostgreSQL de producción cada una de esas 2*N consultas es un seq scan completo, escalando ~O(N^2). El patrón N+1 reportado es correcto y el fix propuesto (2 queries batched con WHERE numero_factura IN (...) o JOIN + agrupar en Python) es válido. No coincide con ningún falso positivo confirmado ni viola invariantes. Severidad P2 correcta: es un endpoint de exportación (disparado manualmente por contable/admin, no hot path) y el rango de fechas acota el volumen, así que el impacto es moderado, no crítico — no hay corrupción de datos, seguridad, ni violación regulatoria.

</details>

---

### P2.25 [perf-n1/performance] N+1 en listado de campanas de marketing: 2 COUNT por campana
**Ubicación:** `api/blueprints/marketing.py:3031-3041` · confianza alta

**Por qué es bug:** Endpoint de listado de campanas: por cada campana ejecuta 2 COUNT (influencers + contenido). Son 2*N round-trips para una vista de lista. Trivialmente reemplazable por subqueries correlacionadas o LEFT JOIN ... GROUP BY en la query principal.

**Fix propuesto:** Anadir a la query de campanas dos subqueries escalares: (SELECT COUNT(*) FROM marketing_campana_influencer WHERE campana_id=marketing_campanas.id) AS num_influencers, idem para contenido; o LEFT JOIN con GROUP BY.

<details><summary>Veredicto del verificador</summary>

El código en api/blueprints/marketing.py:3031-3041 coincide exactamente con la evidencia. El endpoint GET /api/marketing/campanas itera cada fila de marketing_campanas y ejecuta dos COUNT separados (marketing_campana_influencer y marketing_contenido) por campaña = 2*N round-trips, sin paginación. El patrón N+1 es REAL y confirmado. El fix propuesto (subqueries escalares correlacionadas en la query principal) es correcto y trivial. Sin embargo el impacto práctico es bajo: marketing_campanas es una tabla de baja cardinalidad (un laboratorio cosmético tiene decenas de campañas a lo largo de su vida, no miles), por lo que no es un N+1 severo sino el extremo leve del patrón. Se confirma como P2 (no escala a P1 porque no hay crecimiento ilimitado de la tabla que provoque degradación seria; ningún crash 500, ni drift de stock, ni violación de invariante INVIMA).

</details>

---

### P2.26 [perf-n1/performance] N+1 por SKU en dashboards de marketing/estrategia: 2 queries con LIKE por cada SKU
**Ubicación:** `api/blueprints/marketing.py:1656-1669` · confianza alta

**Por qué es bug:** Por cada SKU disponible se lanzan 2 agregaciones; la de animus_shopify_orders usa LIKE '%sku%' que fuerza un full scan por SKU. Con decenas/cientos de SKUs son cientos de scans en una sola request de dashboard. El mismo patron exacto se repite en api/blueprints/marketing.py:2547-2561 (deteccion de SKUs en riesgo), duplicando el problema.

**Fix propuesto:** Agregar liberaciones por sku en una sola query GROUP BY sku a un dict. Para shopify, idealmente normalizar sku_items en una tabla relacional y agregar por sku; mientras tanto, traer las ordenes de la ventana una vez y agregar en Python en lugar de un LIKE por SKU.

<details><summary>Veredicto del verificador</summary>

Verificado en código real. marketing.py:1656-1669 (_build_reporte_ejecutivo_data) y marketing.py:2547-2561 (/api/marketing/kpis-hoy) ejecutan ambos el mismo patrón: un bucle sobre `SELECT sku ... FROM stock_pt WHERE estado='Disponible' GROUP BY sku` y, por CADA sku, dos agregaciones individuales — una a `liberaciones` (sku=?, indexable, barata) y una a `animus_shopify_orders WHERE sku_items LIKE '%sku%'`. Confirmé en database.py:8899 que `sku_items` es una sola columna TEXT (SKUs serializados/concatenados, sin tabla relacional), por lo que el LIKE con comodín inicial '%...%' NO puede usar índice y fuerza un full table scan de animus_shopify_orders por cada SKU. Con N SKUs disponibles son N escaneos completos por request. El índice existente idx_aso_creado(creado_en) no ayuda porque el filtro discriminante es el LIKE sobre otra columna. El caso 2547-2561 es el más serio: su propio docstring lo describe como 'endpoint rápido para la pestaña Hoy', o sea se dispara en cada carga de la pestaña Hoy del dashboard. El caso 1656 es cron semanal + endpoint manual (menor frecuencia, mismo patrón). No está en la lista de falsos positivos confirmados, ninguna invariante lo justifica, y no es problema de corrección/seguridad/datos. Es N+1 real con full scans que se degrada al crecer la tabla de órdenes. Severidad P2 correcta: degrada latencia del dashboard pero no causa 500, pérdida de datos ni drift de stock; a escala de PYME cosmética (decenas de SKUs, volumen de órdenes moderado) el impacto hoy es tolerable pero el patrón es legítimamente reportable.

</details>

---

### P2.27 [plan-autoplan/authz] auto_plan_asegurar_actualizado dispara aplicación completa del plan sin requerir admin
**Ubicación:** `api/blueprints/auto_plan.py:1256-1289` · confianza alta

**Por qué es bug:** Los disparadores explícitos auto_plan_aplicar y auto_plan_ejecutar_ahora exigen 'u not in ADMIN_USERS -> 403'. Este endpoint (POST, invocado automáticamente al cargar /planta) solo exige sesión 'compras_user', de modo que cualquier usuario logueado no-admin puede gatillar generar+aplicar plan: crea producciones, SOLs, conteos y envía emails al equipo. Inconsistente con el modelo de autorización de los otros dos triggers y deja una mutación de inventario/SOL al alcance de roles sin privilegio (atenuado solo por la ventana de 12h de frescura).

**Fix propuesto:** Exigir el mismo guard que los otros triggers (u in ADMIN_USERS, o al menos PLANTA_USERS) antes de lanzar el thread, o limitar el endpoint a refrescar lectura sin aplicar.

<details><summary>Veredicto del verificador</summary>

Confirmado. auto_plan.py:1256-1257 gatea /api/auto-plan/asegurar-actualizado solo con `if 'compras_user' not in session: return 401`, mientras que los dos disparadores equivalentes exigen admin: auto_plan_aplicar (1200: `if u not in ADMIN_USERS: return 403`) y auto_plan_ejecutar_ahora (1228: idem). Los tres lanzan la misma mutación: el endpoint cuestionado arranca ejecutar_auto_plan_diario en thread (1285-1289), que en auto_plan_jobs.py:432-433 llama generar_plan + aplicar_plan(usuario='cron'); aplicar_plan (auto_plan.py:939-948) crea produccion_programada, solicitudes_compra y conteo_ciclico_calendario, y el job envía emails al equipo (484-497). COMPRAS_USERS (config.py:16-36) son los 19 usuarios del staff (incluye operarios de planta luis/mayerlin/camilo, calidad, etc.), no solo ADMIN_USERS={sebastian,alejandro}. Por tanto un usuario no-admin logueado SÍ puede gatillar generar+aplicar plan, lo cual es la inconsistencia de authz reportada. Severidad correcta P2 (no más alta) por mitigaciones reales: (1) ventana de frescura de 12h en 1272 hace que solo dispare si el plan está obsoleto, y el endpoint se auto-invoca en cada carga de /planta, así que normalmente está fresco; (2) la acción es idéntica a lo que el cron ejecuta automáticamente a diario — no permite hacer nada nuevo, solo adelantar el trigger; (3) crea producciones con origen 'auto_plan' (Sugerido), NO toca Fijo, así que no viola la invariante Fijo/Sugerido; (4) sin SQLi/XSS, sin pérdida de datos, sin drift de stock. Es una inconsistencia de modelo de autorización de bajo impacto: corregir alineando el guard a ADMIN_USERS (o PLANTA_USERS) es razonable.

</details>

---

### P2.28 [plan-autoplan/regulatory] aplicar_plan crea produccion_programada y solicitudes_compra sin audit_log
**Ubicación:** `api/blueprints/auto_plan.py:993-1002 y 1089-1096` · confianza alta

**Por qué es bug:** MEMORY/CLAUDE: audit_log es OBLIGATORIO en toda mutación de SOL y de produccion_programada; la falta de audit fue la causa del incidente del 19-may (programación desapareció sin rastro). aplicar_plan inserta N producciones y N SOLs AUTO-XXXX por corrida y solo registra un resumen agregado en auto_plan_runs, que no es audit_log y no permite rastrear qué fila se creó por qué. Otras rutas del mismo dominio (CONFIRMAR_PROYECCION_FIJO en línea 1463, integración B2B) sí auditan; este path automático no.

**Fix propuesto:** Llamar audit_log(c, usuario=usuario, accion='AUTO_PLAN_CREAR_PRODUCCION'/'AUTO_PLAN_CREAR_SOL', tabla=..., registro_id=cur.lastrowid, despues={...}) tras cada INSERT de produccion_programada y de solicitudes_compra dentro de aplicar_plan.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. En api/blueprints/auto_plan.py la función aplicar_plan (def línea 939) inserta en produccion_programada (líneas 993-1002, origen='auto_plan') y en solicitudes_compra (líneas 1089-1096, numero AUTO-XXXX, solicitante 'AUTO-PLAN') SIN llamar audit_log tras ninguno de los dos INSERT. audit_log SÍ está importado (línea 36) y se usa por todo el archivo (8074, 8173, 8456, 9681, 9717, etc.), y la ruta hermana del mismo dominio CONFIRMAR_PROYECCION_FIJO sí audita su INSERT (audit_log en línea 1463) — por tanto es una inconsistencia genuina, no una convención de todo el archivo. El único registro es auto_plan_runs (líneas 1150-1160), que solo guarda contadores agregados y log[:50], no registro_id/despues por fila, así que NO sustituye al audit_log. Esto viola la invariante regulatoria explícita de CLAUDE.md/MEMORY: 'audit_log es obligatorio en toda mutación de SOLs, OCs y produccion_programada'. Matización de severidad: el incidente del 19-may fue por DELETE/cancelación sin rastro; este path es de CREACIÓN, y las filas creadas quedan rastreables por sus propios marcadores (origen='auto_plan', observaciones 'AUTO-PLAN (...)', numero AUTO-XXXX). El riesgo de pérdida de datos es bajo, pero la violación de la invariante de auditoría es real. P2 correcto.

</details>

---

### P2.29 [plan-autoplan/data-correctness] Contexto CMO-IA: query de stock crítico trata 'Ajuste' como Salida
**Ubicación:** `api/blueprints/auto_plan.py:8562-8563` · confianza alta

**Por qué es bug:** Mismo patrón anti-canónico que el bug de _check_mp: cualquier 'Ajuste' o 'Ajuste +' positivo se resta, subestimando el stock. Aquí alimenta el bloque 'stock_critico_top' que se entrega como contexto a Claude (CMO IA), por lo que la IA puede reportar materiales en déficit que en realidad tienen stock por ajustes positivos. Impacto menor que en plan.py (es contexto informativo, no decisión directa de compra), pero sigue siendo lectura incorrecta de stock que viola la invariante.

**Fix propuesto:** Usar el CASE canónico (Entrada/Ajuste +/Ajuste suman; Salida/Ajuste - restan; ELSE 0) o el helper de stock compartido en la subconsulta de stock crítico.

<details><summary>Veredicto del verificador</summary>

Confirmado en api/blueprints/auto_plan.py:8562-8563. El subquery de stock crítico usa SUM(CASE WHEN tipo='Entrada' THEN cantidad ELSE -cantidad END), patrón anti-canónico. El patrón canónico del codebase (programacion.py:1879, 5768, 5969; admin.py:21943 con WHEN tipo='Ajuste' THEN cantidad como delta con signo) es: tipo IN ('Entrada','entrada','ENTRADA','Ajuste +','Ajuste') suma, tipo IN ('Salida','salida','SALIDA','Ajuste -') resta, ELSE 0. En la query reportada, 'Ajuste +' (que SÍ se inserta, ej. animus.py:1341 tipo_mov='Ajuste +' if diferencia>0) cae en ELSE y se RESTA, igual que un 'Ajuste' con delta positivo y las variantes minúsculas 'entrada'/'ENTRADA'. Resultado: subestima el stock de MPs ajustados positivamente. La query alimenta contexto['stock_critico_top'] que se pasa como contexto al LLM (jefe virtual de planta, endpoint live con ANTHROPIC_API_KEY). Viola la invariante de stock=SUM(movimientos) con 'Ajuste' como delta con signo. Impacto: la IA puede listar MPs como bajo mínimo que realmente tienen stock, o incluir/ordenar mal el top-5 crítico. Es contexto informativo entregado al LLM, NO decisión automática de compra ni mutación de stock, por eso P2 (no P1). Confianza alta: el CASE es exacto y los valores de tipo alternativos existen demostrablemente en el mismo codebase.

</details>

---

### P2.30 [programacion/data-correctness] forzar_redescuento en /completar hace UPDATE no atómico y re-descuenta MP ya descontada al iniciar
**Ubicación:** `api/blueprints/programacion.py:6360-6374 (comparar con 5863-5880)` · confianza media

**Por qué es bug:** En _descontar_mp_produccion (L5863) el path forzar usa compare-and-swap atómico (WHERE COALESCE(inventario_descontado_at,'')=prev_at) para prevenir doble descuento en race. En prog_completar_evento el path forzar hace UPDATE incondicional por id (sin CAS) y, como forzar pone mp_ya_descontado=False, ejecuta de nuevo el loop de Salida de MP aunque la producción YA descontó al iniciar. Dos requests forzar paralelos (o un forzar tras descuento en iniciar sin reversión previa) generan Salidas duplicadas -> stock real cae el doble (drift negativo) sin que el flag lo evite. Es admin-only, por eso P2, pero contradice el patrón atómico del propio módulo y puede corromper stock.

**Fix propuesto:** Replicar el compare-and-swap del helper: leer inventario_descontado_at previo y UPDATE ... WHERE id=? AND COALESCE(inventario_descontado_at,'')=prev. Y antes de re-descontar MP en modo forzar, exigir que primero se haya hecho /revertir-completado (que reinyecta las Entradas), o reutilizar _descontar_mp_produccion(forzar=True) en vez de duplicar el loop de Salida aquí.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo el código real. En prog_completar_evento (programacion.py:6276) mp_ya_descontado = bool(descontado_at) and not forzar, así que con forzar=True siempre queda False. El path forzar (6360-6366) hace UPDATE produccion_programada SET inventario_descontado_at WHERE id=? SIN compare-and-swap (a diferencia del helper _descontar_mp_produccion en 5863-5874, que sí lee prev_at y usa WHERE ... COALESCE(inventario_descontado_at,'')=prev — fix documentado como "BUG-6 audit Planta PERFECTA" justamente para impedir doble descuento en forzar paralelo). Luego en 6394 if not mp_ya_descontado: vuelve a ejecutar el loop de INSERT 'Salida' (6403-6409). Dos problemas reales: (1) si admin invoca /completar {forzar_redescuento:true} sobre una producción que YA descontó al /iniciar SIN antes llamar /revertir-completado (que es quien reinyecta las Entradas compensatorias y limpia el flag, 6582-6674), las Salidas originales nunca se revierten y se generan Salidas duplicadas → stock real cae el doble (drift negativo, viola invariante kardex INVIMA). Nada en el código exige que la reversión haya ocurrido antes. (2) Dos requests forzar concurrentes ambos pasan el UPDATE incondicional y ambos descuentan, exactamente el race que el helper de /iniciar ya blindó con CAS y que aquí NO se replicó. Mitigantes que bajan severidad: es admin-only (6245-6246, retorna 403 si no es ADMIN_USER) y el flag forzar_redescuento es acción deliberada cuyo propósito documentado es re-descontar tras revertir. No coincide con ningún falso positivo confirmado. Fix correcto: replicar el CAS del helper (leer prev_at y UPDATE ... WHERE id=? AND COALESCE(inventario_descontado_at,'')=prev) o reutilizar _descontar_mp_produccion(forzar=True) en lugar de duplicar el loop de Salida. P2 confirmado.

</details>

---

### P2.31 [programacion/regulatory] POST /api/programacion/programar crea fila en produccion_programada sin audit_log
**Ubicación:** `api/blueprints/programacion.py:2496-2524` · confianza alta

**Por qué es bug:** MEMORY/CLAUDE.md declaran audit_log OBLIGATORIO en toda mutación de produccion_programada. Este endpoint inserta una producción nueva (mutación) y NO escribe audit_log, a diferencia de cancelar/iniciar/completar/asignar que sí auditan. Deja sin rastro quién creó qué producción y cuándo -el mismo tipo de hueco de trazabilidad que causó la desaparición de programación del 19-may sin evidencia. Además no setea 'origen', dejándolo NULL (Sugerido por defecto), lo cual es aceptable pero la falta de auditoría es la violación.

**Fix propuesto:** Añadir audit_log(c, usuario=session['compras_user'], accion='CREAR_PRODUCCION_PROGRAMADA', tabla='produccion_programada', registro_id=cur.lastrowid, despues={'producto':producto,'fecha':fecha,'lotes':lotes}) antes del commit, igual que en prog_cancelar_evento.

<details><summary>Veredicto del verificador</summary>

Confirmado leyendo programacion.py:2496-2524. prog_crear_evento inserta una fila nueva en produccion_programada (INSERT INTO produccion_programada ... VALUES, línea 2519) y hace conn.commit() en 2523 sin ninguna llamada a audit_log. En contraste, todos los endpoints hermanos del mismo archivo SÍ auditan toda mutación de esa tabla: CANCELAR_PRODUCCION (2591), ASIGNAR_SALA_OPERARIOS (3055), TERMINAR_PRODUCCION (3501), AUTO_CANCELAR_PRODUCCION (4597). El helper audit_log ya está importado en línea 25, así que el fix es trivial. Esto viola la regla dura explícita de CLAUDE.md/MEMORY.md: "audit_log es OBLIGATORIO en toda mutación de produccion_programada" — la misma clase de hueco de trazabilidad citado por la desaparición de la programación del 19-may. No hay trigger DB ni otro mecanismo que cubra este INSERT (solo el grep encontró el INSERT sin audit adyacente). La columna creado_en da timestamp pero no atribución de usuario, así que el rastro de quién creó la producción no existe. Mantengo P2: es una omisión de trazabilidad regulatoria de bajo impacto en un create no-destructivo, no causa drift de stock, pérdida de datos ni crash. El comentario del hallazgo sobre origen NULL es correcto y aceptable (Sugerido por defecto), no es bug en sí.

</details>

---

### P2.32 [rrhh-financiero/regulatory] Incapacidad común: días 1-2 se pagan al 100% por el empleador (debe ser 66.66%), inflando el costo y contradiciendo el resto del cálculo *(verificador bajó de P1)*
**Ubicación:** `api/blueprints/rrhh.py:789-793` · confianza media

**Por qué es bug:** En Colombia, para incapacidad de origen común el empleador asume los días 1-2 pero al mismo porcentaje de la prestación económica (66.66% del salario, decreto 2943/2013 / criterio jurisprudencial), no al 100%. El código liquida los días 1-2 al 100% del salario diario (pct:100, monto = d1*salario_diario). Esto sobreestima el pago del empleador en cada incapacidad común y queda persistido en rh_eventos.pago_empleador, alimentando reportes y descuentos de nómina con cifras legalmente incorrectas.

**Fix propuesto:** Calcular días 1-2 de incapacidad_comun al 66.66%: pago = round(d1 * salario_diario * 0.6666, 0) y pct:66.66. (Verificar política interna de la empresa: algunas pagan 100% por liberalidad; si es intencional, documentarlo explícitamente para que no se trate como bug).

<details><summary>Veredicto del verificador</summary>

Verifiqué el código en api/blueprints/rrhh.py:789-793 dentro de _calcular_pago_incapacidad. Para tipo=='incapacidad_comun' los días 1-2 se liquidan al 100% del salario_diario (pct:100, monto = d1*salario_diario, sumados a pago_empleador), mientras que los días 3-90 se calculan al 66.66% (línea 796). El valor pago_empleador se persiste en rh_eventos (INSERT línea 919-940) y alimenta dashboards/reportes (líneas 1242, 1331+), por lo que el impacto es real sobre cifras financieras.

El reclamo legal tiene base: bajo el Decreto 2943/2013, el empleador asume los 2 primeros días de incapacidad de origen común, y la jurisprudencia/criterio prestacional aplica el auxilio al 66.66% (no al 100% del salario pleno). Por tanto, liquidar los días 1-2 al 100% sobreestima el costo del empleador y es internamente inconsistente con el resto del cálculo (días 3-90 al 66.66%), pese a que el docstring (líneas 769-781) afirma 'Cumple ley colombiana'.

PERO contra el criterio adversarial: el comportamiento está EXPLÍCITAMENTE documentado como intencional en el docstring (línea 771: 'Dias 1-2: 100% empleador'), no es un descuido. Pagar los 2 primeros días al 100% es legalmente permisible como liberalidad del empleador (es más favorable al trabajador, no perjudica a nadie ni viola norma imperativa). No hay corrupción de datos, ni SQLi/XSS/authz, ni crash, ni drift de stock, ni violación de invariante dura del dominio. Es una imprecisión de política/exactitud financiera (sobreestima el costo asumido por la empresa), por lo que lo confirmo como real pero degrado de P1 a P2: conviene aclarar/alinear al 66.66% si se quiere estricto apego legal, o documentar formalmente que es liberalidad, pero no es un bug crítico ni de cumplimiento bloqueante.

</details>

---


## Refutados (falsos positivos descartados por el verificador)

1. **[plan-autoplan]** Auto-clean de tablero-equipo cancela Sugeridas pasadas sin excluir inventario_descontado_at
   - _Verifiqué los DOS filtros del auto-clean en auto_plan.py (SELECT 10122-10131 + UPDATE 10138-10143): cancela solo filas con estado IN ('','programado','planeado','sugerido') AND inicio_real_at IS NULL AND origen NOT IN Fijo AND fecha pasada. El hallazgo es correcto en que NO se filtra inventario_descontado_at, pero rastreé TODAS las rutas que escriben inventario_descontado_at a un valor no-nulo y ninguna deja una fila en estado capturable por este clean:

1) /iniciar (programacion.py: _descontar_mp_produccion 5871/5877 + UPDATE inicio_real_at 3252) setea inventario_descontado_at E inicio_real_at en la MISMA transacción (commit 3291). El guard inicio_real_at IS NULL ya la excluye.
2) /completar (programacion.py 6363/6370 claim + 6453-6459 UPDATE estado='completado') setea inventario_descontado_at junto con estado='completado'. El filtro de estado del SELECT (solo '','programado','planeado','sugerido') ya la excluye. Todo está en un try único con rollback (6354-6498), no hay commit parcial que deje estado activo con descuento.
3) Backfill plan.py:17336-17349 inserta estado='completado', origen='eos_retroactivo' (Fijo) e inicio_real_at set: triple-excluida.
4) La reversión (6667-6674) pone inventario_descontado_at=NULL y estado='programado' — consistente.
5) admin.py:19810-19844 es diagnóstico read-only; reconoce 'PROGRAMADA_DESCONTADA_SIN_TERMINAR' pero esas filas tienen inicio_real_at set.

Por tanto NO existe en el código actual un estado alcanzable (estado activo + inicio_real_at NULL + inventario_descontado_at NOT NULL) que este clean pudiera cancelar. No hay pérdida de vínculo de lote ni descuadre kardex/plan hoy. Es a lo sumo defensa-en-profundidad/hardening recomendable (alinear con el patrón canónico inicio_real_at AND inventario_descontado_at del CONTRACT_programacion.md:147), no un bug P2 de data-loss explotable. Confianza media porque no puedo descartar al 100% rutas futuras o un admin SQL manual, pero por el criterio adversarial de alta confianza, no califica como bug real._
2. **[rrhh-financiero]** descuento_nomina = pago_eps + pago_arl trata el reembolso de EPS/ARL como descuento al empleado, pudiendo descontarle de su pago lo que la EPS/ARL le debe
   - _El hallazgo asume que rh_eventos.descuento_nomina se consume al liquidar la quincena reduciendo el neto del empleado. Verifiqué el código real y eso NO ocurre. La liquidación está en rrhh_nomina (api/blueprints/rrhh.py:216-266): el neto se calcula en la línea 251 (neto = sal_prop + aux_prop + vhe + bonos - desc_salud - desc_pension - otros) donde `otros` (línea 242, xr[5]) proviene EXCLUSIVAMENTE de nomina_registros.otros_descuentos (SELECT en línea 232). Ese campo nomina_registros.otros_descuentos se llena por el endpoint manual /api/rrhh/nomina/guardar (línea 275-276) con el valor que envía el front, no desde eventos. Un grep total en api/ (descuento_nomina / rh_eventos) confirma que solo aparece en: rrhh.py (cálculo+persistencia del evento), rrhh_html.py:848 (display informativo del preview), y los esquemas database.py:4787 / pg_schema.sql:2803. NO existe ningún JOIN ni lectura de rh_eventos hacia la nómina, ni auto-poblado de otros_descuentos desde el evento. Por tanto el descuento_nomina del evento es un valor meramente informativo que nunca reduce el pago real del trabajador; el daño descrito (neto menor al legal en incapacidad/maternidad) no se materializa. La semántica de la etiqueta es discutible (un auxilio EPS/ARL es ingreso a transcribir, no descuento), pero no es un bug de corrección de datos porque no se consume en liquidación. No-bug de alta confianza._
3. **[portal-b2b]** Conversión RFQ→pedido crea pedido 'pendiente' que nunca se integra al plan de producción
   - _Verifiqué portal.py:2238-2284: es correcto que (a) el INSERT omite 'estado' y toma el DEFAULT 'pendiente' (database.py:1681; el CHECK no admite 'borrador'), (b) NO llama _integrar_pedido_b2b_al_plan a diferencia de portal_crear_pedido (portal.py:962-967) y plan.py:832, y (c) el mensaje dice 'creado en borrador' aunque no existe ese estado. Eso es una inconsistencia de UX (palabra 'borrador' incorrecta) y de paridad de flujos. PERO la premisa central del hallazgo —que el pedido queda 'invisible para el calendario de producción' y genera 'drift entre lo prometido y lo planificado'— es FALSA contra el código real. Un pedido_b2b en estado 'pendiente' SÍ es consumido por toda la consolidación de planeación: plan.py:5490-5491 (b2b_por_producto kg), plan.py:10378-10380 (necesidades por producto/cliente), plan.py:2157-2177 (b2b_por_cliente), todas con WHERE estado NOT IN ('despachado','cancelado') que incluye 'pendiente'; y plan.py:2406-2412 lista explícitamente los pedidos 'pendiente' generando alertas de MP faltante. Es decir, el pedido NO es invisible: aparece en necesidades, en los kg B2B consolidados y en alertas. El estado 'pendiente' es justamente el workflow documentado (database.py:1668: 'cliente solicitó → Sebastián cuadra cantidad y fecha'), tras lo cual un admin lo confirma/integra vía B2B_ASIGNAR (plan.py:7084, 7300). El pedido queda auditado (audit_log CONVERTIR_SOLICITUD_A_PEDIDO, portal.py:2272-2277) y la solicitud marcada 'convertida'. No hay pérdida de datos, no hay drift de stock, no hay violación de invariante INVIMA/Fijo-vs-Sugerido, no hay crash. A lo sumo es un nit de UX (mensaje 'borrador' impreciso) y falta de auto-creación de lote dedicado, lo cual el sistema cubre por la consolidación de necesidades + confirmación admin. No califica como bug de data-correctness P2._
4. **[portal-b2b]** Pedido convertido desde RFQ omite el tope de 50.000 uds y 5.000 ml del flujo normal
   - _Verifiqué el código real en portal.py:2185-2284 y plan.py. La premisa del hallazgo es correcta en lo factual (el cap de 50.000 uds existe solo en portal_crear_pedido líneas 875-878 y NO se replica en la ruta de conversión RFQ→pedido), pero el impacto que justifica el SEC-FIX NO se reintroduce por esta ruta, por dos razones decisivas: (1) El SEC-FIX de 22-may importa porque el flujo directo portal_crear_pedido llama _integrar_pedido_b2b_al_plan INMEDIATAMENTE tras el INSERT (portal.py:960-967), inyectando kg_b2b al plan. La ruta de conversión (portal.py:2238-2284) hace SOLO el INSERT en pedidos_b2b + audit_log y NUNCA invoca _integrar_pedido_b2b_al_plan — el pedido queda sin fila en pedidos_b2b_lote. (2) La consolidación de kg_b2b que alimenta el plan (plan.py:578-624, programacion.py:5262) suma desde pedidos_b2b_lote, NO desde pedidos_b2b directamente; un pedido convertido aporta 0 kg al plan canónico. Por tanto un cant_est gigante (≤1e9, ya acotado en creación línea 1987, evitando el overflow original de 2e9→kg=2e15) NO contamina el plan vía esta ruta. Además ml_unidad YA está acotado ≤5000 en la conversión (líneas 2232-2233), cubriendo la mitad ml del cap, y se valida MOQ (línea 2221). El propio hallazgo se cubre con condicional futuro ('Si en el futuro se conecta la integración al plan... se reintroduce'), lo que confirma que es hardening defensivo latente, no un bug con impacto actual de corrección de datos, drift de stock ni contaminación del plan. Nota: estado por defecto es 'pendiente' (database.py:1681), no 'borrador' como dice el mensaje, pero eso es cosmético y no cambia el veredicto. Recomendable añadir el guard de 50.000 por consistencia, pero no cumple el umbral de bug real de alta confianza con impacto._
5. **[db-pg-migraciones]** safe_alter trata "no such table" como benigno: un ALTER sobre tabla con typo se ignora en silencio
   - _El hallazgo describe correctamente la inconsistencia doc-vs-código (el docstring de safe_alter y CLAUDE.md dicen que solo silencia "duplicate column"/"already exists", pero _BENIGN_DDL_ERRORS también incluye "no such table" en api/database.py:96). Sin embargo, no es un bug real con impacto, por dos razones verificadas en el código:

1) El runner real de migraciones NO usa safe_alter. La lista MIGRATIONS se aplica en init_db con un bucle propio (api/database.py:7725-7758) que tiene su PROPIA tupla BENIGN_PATTERNS (7704-7708), también con "no such table". Es decir, los ALTER regulatorios (p.ej. mig 151 coa_url/lote_proveedor, líneas 7335-7338) jamás pasan por safe_alter, así que el fix propuesto sobre safe_alter no afectaría a las migraciones.

2) El ÚNICO call site de safe_alter es api/blueprints/inventario.py:10614, dentro de _init_acondicionamiento(). Las dos tablas destino (acondicionamiento, liberaciones) se crean con CREATE TABLE IF NOT EXISTS en la misma función, inmediatamente antes (líneas 10572 y 10588), y los nombres en los ALTER coinciden exactamente sin typo. Por tanto "no such table" no puede ocurrir legítimamente ahí ni enmascarar una columna no creada.

No existe ningún path demostrable donde una columna/índice regulatorio quede sin crear en silencio vía safe_alter por culpa de "no such table". El comentario "legítimo en DROP IF NOT EXISTS-style code" es engañoso (safe_alter no se usa para DROP) y la mención de "no such table" en el bucle de migraciones es un trade-off conocido y documentado en 7710-7716 (caso mig 92, resuelto ordenando versiones, no quitando el patrón). Eso es a lo sumo un footgun latente / nit de documentación, no un bug de corrección de datos. Severidad real: no-bug._
6. **[db-pg-migraciones]** Migración 40 ausente en MIGRATIONS y orden no monótono (41 seguida de 39); frágil ante el supuesto de continuidad
   - _Refutado. El hecho estructural es cierto (database.py:4603-4607: la mig 41 precede a la 39 y la 40 no existe), pero NO es un bug. (1) El runner run_migrations (database.py:7694-7725) es gap-safe por diseño: arma applied como un set, itera sorted(MIGRATIONS, key=version) y salta con `if version in applied`, usando INSERT OR IGNORE. Nunca asume rango contiguo 1..N, nunca compara MAX(version) vs COUNT, nunca usa range(1,N). (2) Verifiqué por script que NO hay duplicados y que existen CUATRO huecos preexistentes (13, 15, 16, 40), no solo el 40 — los huecos son una propiedad tolerada y de larga data de esta lista append-only, no una anomalía única 'perdida en merge'. (3) Ningún consumidor asume continuidad: plan.py:5865 usa MAX(version) solo para un display diagnóstico, e index.py:288 solo loguea len(MIGRATIONS); el grep por MAX(version)/COUNT/range(1,/contiguous no encontró lógica que se rompa con un hueco. La invariante real es 'append-only, nunca editar el pasado', que se cumple: un número faltante no es una edición. La categoría 'crash' es infundada — nada crashea, no hay pérdida de datos ni drift de stock ni violación INVIMA. Es una observación de housekeeping/riesgo latente hipotético, no un defecto real (el propio hallazgo admite 'el hueco no rompe HOY')._
7. **[db-pg-migraciones]** executemany no aplica rewrite_having_alias ni forzar_date_texto (asimetría con execute)
   - _La asimetría existe literalmente en el código: execute() en api/pg_adapter.py:266-268 aplica rewrite_having_alias() y forzar_date_texto() antes de translate_placeholders(), mientras executemany() en api/pg_adapter.py:315-325 NO los aplica. Eso es cierto. Pero NO tiene impacto real: (1) executemany es para sentencias parametrizadas repetidas (INSERT/UPDATE/DELETE con VALUES); HAVING solo aparece en SELECT, así que rewrite_having_alias jamás aplica a executemany. (2) forzar_date_texto solo importaría en un INSERT...SELECT con date(col) de 1 arg ejecutado vía executemany, patrón que no existe en el repo. (3) Busqué TODOS los call sites de executemany (Grep en todo el repo): solo 4 archivos. El único call site real de la app a través del adapter es api/database.py:8527 — un UPDATE plano (\"UPDATE ordenes_compra SET estado='Revisada' WHERE numero_oc=? AND estado='Borrador'\") sin date() ni HAVING ni INSERT...SELECT. Los otros dos son scripts/smoke_pg_adapter.py (INSERT plano de prueba) y scripts/migrar_datos_a_postgres.py (usa psycopg crudo cur.executemany, NO pasa por el adapter). El path de fallo hipotetizado requiere un call site que no existe en ninguna parte del código. Es un gap de robustez/simetría defensiva, no un bug con impacto — cae en la categoría \"podría mejorarse\" que el criterio pide NO reportar. El fix propuesto es razonable como hardening pero no corrige ningún defecto activo._
8. **[db-pg-migraciones]** PgConnection.execute crea 2 cursores psycopg por llamada y nunca los cierra (fuga por request)
   - _Verifiqué el código real en api/pg_adapter.py. Los hechos base son ciertos: _Cursor crea un segundo cursor _spcur eagerly en __init__ (línea 196), PgConnection.execute() devuelve un _Cursor que no se cierra explícitamente (líneas 394-397). PERO la premisa central del hallazgo (fuga de recursos / acumulación de cientos de cursores y portales server-side) es FALSA: self._conn.cursor() se llama SIN argumento name=, así que son cursores client-side de psycopg3, que NO asignan portal server-side ni recurso libpq — son objetos Python ligeros que bufferean en cliente. No hay fuga server-side. Las conexiones son per-request (g.db) y se cierran en teardown_appcontext (database.py get_db línea 72-86); al cerrarse la conexión, todos los _Cursor/_spcur son recolectados por GC. No hay crecimiento de memoria entre requests ni leak persistente. Además el hallazgo afirma que _spcur 'solo se necesita cuando NO hay autocommit; abrirlo siempre duplica el costo' — esto es engañoso: la conexión por defecto es autocommit=False (línea 379), y en ese modo _ejecutar_guardado envuelve CADA statement (incluidas lecturas) en SAVEPOINT/RELEASE usando _spcur (líneas 221-236), por lo que _spcur SÍ se usa por statement en la conexión transaccional default; solo es redundante en conexiones autocommit (audit_log). El único costo real es una asignación extra de un objeto cursor Python por _Cursor — micro-optimización, sin impacto en corrección, seguridad, datos, stock, INVIMA, ni crashes. No cumple el criterio de bug reportable (data corruption/seguridad/pérdida de datos/drift de stock/invariante regulatoria/500/N+1 severo). Es un nit de eficiencia, explícitamente fuera de alcance._
9. **[perf-n1]** N+1 anidado en endpoint OEE por sala + query SQL absurda para restar fechas
   - _El núcleo del hallazgo (severidad P1) descansa en una afirmación FALSA: que julianday() no existe en PostgreSQL, lanza excepción atrapada por el except, y deja tiempo_real_total=0 corrompiendo el OEE en producción. Esto es incorrecto. EOS define una UDF julianday() en api/pg_functions.sql:108-111 (RETURNS double precision AS SELECT extract(epoch FROM _eos_sqlite_ts(p_args))/86400.0 + 2440587.5) precisamente para emular el julianday() de SQLite. Ese archivo se carga en la BD PG vía cargar_esquema() en scripts/migrar_datos_a_postgres.py:33,49-55 (ARCHIVOS_ESQUEMA incluye pg_functions.sql, ejecutado al bootstrap del esquema PG). La migración a PostgreSQL está marcada COMPLETA y en producción. Por tanto la query SELECT (julianday(?)-julianday(?))*24*60 funciona en ambos motores; no hay excepción, no hay OEE en cero, no hay incorrectitud de datos.\n\nQueda solo la parte de rendimiento: en auto_plan.py:7780-7826 sí existe un patrón N+1 (loop por sala -> query de producciones -> loop por lote con 2 queries: la resta de fechas por round-trip y el takt por LOWER(producto)). Pero las salas son un conjunto fijo y pequeño (areas_planta WHERE tipo='produccion' activas, ~unidades), la ventana es de N días acotada (max 90, default 7) sobre lotes terminados, y es un endpoint de dashboard administrativo interactivo de baja frecuencia, sin pérdida de datos, sin crash, sin drift de stock. No alcanza el umbral de 'N+1 severo' del criterio. La resta de fechas vía SQL es ineficiente (Python la haría gratis) y el takt podría precargarse en dict, pero eso es optimización cosmética, no bug reportable. Veredicto: no-bug (la justificación P1 está refutada y el resto no cumple el bar de severidad)._
10. **[perf-n1]** N+1 en ranking de operarios: 4 queries por operario dentro del loop
   - _El patrón de código existe exactamente como se reporta: api/blueprints/bienestar.py:384-431 itera sobre operarios y lanza 4 queries de agregación por iteración (bienestar_capacitaciones, tareas_operativas, capa_desviaciones, produccion_programada con OR sobre 4 columnas sin índice). En forma es un N+1. PERO el impacto real es nulo: N es minúsculo. La tabla operarios_planta (database.py:5083-5089) sembrada con la crew real abr-2026 tiene 5 filas, y la query filtra es_jefe_produccion=0, dejando ~4 operarios rankeados. Es una planta de cosmética de ~5 personas. Total = ~4×4 = 16 queries en un endpoint /api/bienestar/empleado-trimestral que es un reporte de ranking TRIMESTRAL cargado bajo demanda (no cron, no middleware per-request, no hot path). El criterio del prompt pide explícitamente solo 'N+1 severo' y NO reportar nits de perf; con 4 operarios y un reporte trimestral on-demand no hay problema de rendimiento real, ni corrupción de datos, ni crash, ni violación de invariante. La severidad P1 está claramente sobreestimada; en este dominio no alcanza el umbral de bug reportable._
