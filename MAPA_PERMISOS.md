# Mapa de permisos · EOS

> **GENERADO** por `python scripts/generar_mapa_permisos.py` · no editar a mano.
> Se lee del `url_map` real de Flask, así que no puede quedar desactualizado en silencio.

## Resumen

| Gate | Rutas | Quién entra |
|---|---:|---|
| `AUTENTICADO` | 1017 | cualquier usuario con sesión |
| `ADMIN` | 486 | solo Sebastián y Alejandro |
| `COMPRAS` | 35 | Catalina, Mayra + Admin |
| `PLANTA` | 33 | operarios de planta + Admin |
| `EJECUTOR DE LOTE` | 25 | Planta ∪ Calidad ∪ Admin |
| `FINANZAS` | 22 | contadora / compras + Admin |
| `PÚBLICA` | 18 | sin sesión (a propósito) |
| `CALIDAD+ADMIN` | 12 | Control de Calidad o Dirección |
| `CALIDAD` | 8 | Laura, Yulieth + Admin |
| `ASEGURAMIENTO` | 6 | Miguel + Calidad + Admin |
| `FÓRMULAS (INVIMA)` | 6 | Técnica ∪ Calidad ∪ Aseguramiento ∪ Dirección |
| `PORTAL B2B` | 3 |  |
| `MARKETING` | 1 | equipo de marketing + Admin |
| `RRHH` | 1 | Gloria + asistentes + Admin |
| `TÉCNICA` | 1 | Hernando, Miguel + Admin |

## 🚨 Rutas SIN NINGÚN gate (fuera de /api/)

El hook global de login cubre sólo `/api/`. Una ruta fuera de ese prefijo sin gate propio
la puede abrir cualquiera desde internet. Así estuvieron las 18 rutas `/diag/*` sirviendo
las fórmulas maestras hasta el 25-jul. **Esta lista debería estar vacía o ser sólo páginas
públicas a propósito.**

| Ruta | Métodos | Archivo |
|---|---|---|

_0 rutas._

## ⚠ Rutas que MUTAN y sólo piden estar logueado

No todas son un problema (muchas son acciones que cualquier empleado hace), pero **acá es
donde aparecen los agujeros**: el 25-jul se encontraron dos controles que parecían control
y no lo eran. Si una de estas toca dinero, inventario o un registro regulado, necesita rol.

| Ruta | Métodos | Archivo |
|---|---|---|
| `/api/animus/agentes/<agente>` | POST | animus.py |
| `/api/animus/caja` | POST | animus.py |
| `/api/animus/contenido/<int:cid>/usar` | POST | animus.py |
| `/api/animus/contenido/generar` | POST | animus.py |
| `/api/animus/conteos/<int:conteo_id>/aplicar-ajuste` | POST | animus.py |
| `/api/animus/inv-fisico/baseline` | GET,POST | animus.py |
| `/api/animus/inv-fisico/baseline/sembrar-desde-shopify` | POST | animus.py |
| `/api/animus/inv-fisico/conteo/<int:asig_id>/registrar` | POST | animus.py |
| `/api/animus/inv-fisico/conteo/asignar-hoy` | POST | animus.py |
| `/api/animus/inv-fisico/entrada` | POST | animus.py |
| `/api/animus/inv-fisico/salida` | POST | animus.py |
| `/api/animus/inv-fisico/sync-shopify` | POST | animus.py |
| `/api/animus/inventario-ciclico` | POST | animus.py |
| `/api/animus/pqr` | GET,POST | animus.py |
| `/api/animus/pqr/<int:pid>` | PATCH | animus.py |
| `/api/animus/sync/<platform>` | POST | animus.py |
| `/api/artes/<int:aid>/aprobar-arte` | POST | artes.py |
| `/api/artes/<int:aid>/aprobar-fisica` | POST | artes.py |
| `/api/artes/<int:aid>/rechazar` | POST | artes.py |
| `/api/artes/biblioteca` | GET,POST | artes.py |
| `/api/artes/solicitar` | POST | artes.py |
| `/api/aseguramiento/acuerdos-calidad` | GET,POST | aseguramiento.py |
| `/api/aseguramiento/cambios` | GET,POST | aseguramiento.py |
| `/api/aseguramiento/cambios/<int:cid>/cerrar` | POST | aseguramiento.py |
| `/api/aseguramiento/cambios/<int:cid>/evaluar` | POST | aseguramiento.py |
| `/api/aseguramiento/cambios/<int:cid>/implementar` | POST | aseguramiento.py |
| `/api/aseguramiento/cambios/<int:cid>/notificar-invima` | POST | aseguramiento.py |
| `/api/aseguramiento/capacitaciones/asignar` | POST | aseguramiento.py |
| `/api/aseguramiento/capacitaciones/firmar` | POST | aseguramiento.py |
| `/api/aseguramiento/desviaciones` | GET,POST | aseguramiento.py |
| `/api/aseguramiento/desviaciones/<int:desv_id>/capa` | POST | aseguramiento.py |
| `/api/aseguramiento/desviaciones/<int:desv_id>/cerrar` | POST | aseguramiento.py |
| `/api/aseguramiento/desviaciones/<int:desv_id>/clasificar` | POST | aseguramiento.py |
| `/api/aseguramiento/desviaciones/<int:desv_id>/investigar` | POST | aseguramiento.py |
| `/api/aseguramiento/fmea` | GET,POST | aseguramiento.py |
| `/api/aseguramiento/indicadores/metas/<codigo>` | PATCH | aseguramiento.py |
| `/api/aseguramiento/pqr-inbox/<int:iid>/descartar` | POST | aseguramiento.py |
| `/api/aseguramiento/pqr-inbox/<int:iid>/enrutar` | POST | aseguramiento.py |
| `/api/aseguramiento/proveedores-calificacion` | GET,POST | aseguramiento.py |
| `/api/aseguramiento/quejas` | GET,POST | aseguramiento.py |
| `/api/aseguramiento/quejas/<int:qid>/cerrar` | POST | aseguramiento.py |
| `/api/aseguramiento/quejas/<int:qid>/investigar` | POST | aseguramiento.py |
| `/api/aseguramiento/quejas/<int:qid>/responder` | POST | aseguramiento.py |
| `/api/aseguramiento/quejas/<int:qid>/triaje` | POST | aseguramiento.py |
| `/api/aseguramiento/recalls` | GET,POST | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>/cerrar` | POST | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>/clasificar` | POST | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>/notificar-distribuidores` | POST | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>/notificar-invima` | POST | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>/recoleccion` | POST | aseguramiento.py |
| `/api/aseguramiento/revision-direccion` | GET,POST | aseguramiento.py |
| `/api/aseguramiento/revision-direccion/<int:rid>/ejecutar` | POST | aseguramiento.py |
| `/api/aseguramiento/sgd` | POST | aseguramiento.py |
| `/api/aseguramiento/sgd/<path:codigo>/pdf` | POST | aseguramiento.py |
| `/api/aseguramiento/sgd/conflictos/<int:conflicto_id>/resolver` | POST | aseguramiento.py |
| `/api/aseguramiento/validacion-equipos` | GET,POST | aseguramiento.py |
| `/api/auto-plan/aplicar-aprendizaje` | POST | auto_plan.py |
| `/api/auto-plan/asegurar-actualizado` | POST | auto_plan.py |
| `/api/auto-plan/configs/emails` | GET,POST | auto_plan.py |
| `/api/auto-plan/configs/emails/test` | POST | auto_plan.py |
| `/api/auto-plan/configs/mp` | GET,POST | auto_plan.py |
| `/api/auto-plan/configs/perfil-riesgo` | GET,POST | auto_plan.py |
| `/api/auto-plan/configs/sku/<int:config_id>` | PUT | auto_plan.py |
| `/api/conteo-ciclico/<int:item_id>/registrar` | POST | auto_plan.py |
| `/api/conteo-ciclico/configs` | GET,POST | auto_plan.py |
| `/api/maquila/clientes` | GET,POST | auto_plan.py |
| `/api/maquila/pedidos` | GET,POST | auto_plan.py |
| `/api/maquila/pedidos/<int:pedido_id>` | DELETE | auto_plan.py |
| `/api/maquila/pedidos/<int:pedido_id>/asignar-produccion` | POST | auto_plan.py |
| `/api/planta/accion-rapida` | POST | auto_plan.py |
| `/api/planta/asignar-operarios-bulk` | POST | auto_plan.py |
| `/api/planta/auditor-semanal-enviar` | POST | auto_plan.py |
| `/api/planta/auto-d20-cron` | POST | auto_plan.py |
| `/api/planta/auto-sc-generar` | POST | auto_plan.py |
| `/api/planta/auto-sc-mee-generar` | POST | auto_plan.py |
| `/api/planta/confirmar-proyeccion` | POST | auto_plan.py |
| `/api/planta/desbloquear-produccion/<int:pid>` | POST | auto_plan.py |
| `/api/planta/ejecutar-lunes-7am` | POST | auto_plan.py |
| `/api/planta/forzar-sync-semana` | POST | auto_plan.py |
| `/api/planta/mee-config/<path:codigo>` | PUT | auto_plan.py |
| `/api/planta/normalizar-mee` | POST | auto_plan.py |
| `/api/planta/produccion/<int:prod_id>/aceptar-recomendacion` | POST | auto_plan.py |
| `/api/planta/produccion/<int:prod_id>/asignar-operarios-auto` | POST | auto_plan.py |
| `/api/planta/produccion/<int:prod_id>/editar-lote` | POST | auto_plan.py |
| `/api/planta/produccion/<int:prod_id>/eliminar-y-replanificar` | POST | auto_plan.py |
| `/api/planta/producto-nuevo` | POST | auto_plan.py |
| `/api/planta/reasignar-operarios-conflictos` | POST | auto_plan.py |
| `/api/planta/sc-d20-rapida` | POST | auto_plan.py |
| `/api/planta/sc-etiqueta-rapida` | POST | auto_plan.py |
| `/api/planta/sc-mee-asignar` | POST | auto_plan.py |
| `/api/planta/self-heal` | POST | auto_plan.py |
| `/api/planta/sku-mee-config` | POST | auto_plan.py |
| `/api/planta/sku-mee-config/<int:mid>` | DELETE,PUT | auto_plan.py |
| `/api/planta/sku/<int:sku_id>/estado` | POST | auto_plan.py |
| `/api/planta/sync-shopify-cron` | POST | auto_plan.py |
| `/api/planta/tablero-kanban/<int:pid>/etapa/<rol>/<accion>` | POST | auto_plan.py |
| `/api/planta/tiempos-objetivo` | GET,POST | auto_plan.py |
| `/api/planta/unificar-hermanos-skus` | POST | auto_plan.py |
| `/api/recepcion/ocr-etiqueta` | POST | auto_plan.py |
| `/api/bienestar/capacitaciones` | GET,POST | bienestar.py |
| `/api/bienestar/capacitaciones/<int:cid>/iniciar-examen` | POST | bienestar.py |
| `/api/bienestar/intentos/<int:int_id>/calificar` | POST | bienestar.py |
| `/api/bienestar/notificaciones` | GET,POST | bienestar.py |
| `/api/bienestar/notificaciones/<int:nid>/resolver` | POST | bienestar.py |
| `/api/publico/empleado-reporte` | POST | bienestar.py |
| `/api/brd/cleaning` | POST | brd.py |
| `/api/brd/cleaning/<int:cl_id>/completar` | POST | brd.py |
| `/api/brd/demo-legajo` | POST | brd.py |
| `/api/brd/ebr` | POST | brd.py |
| `/api/brd/legajo-rapido` | POST | brd.py |
| `/api/brd/limpiar-demos` | POST | brd.py |
| `/api/brd/mbr` | POST | brd.py |
| `/api/brd/mbr/<int:mbr_id>` | PATCH | brd.py |
| `/api/brd/mbr/<int:mbr_id>/ipc-specs` | POST | brd.py |
| `/api/brd/mbr/<int:mbr_id>/ipc-specs/<int:spec_id>` | DELETE | brd.py |
| `/api/brd/mbr/<int:mbr_id>/pasos` | POST | brd.py |
| `/api/brd/mbr/<int:mbr_id>/pasos/<int:paso_id>` | PATCH | brd.py |
| `/api/brd/mbr/<int:mbr_id>/pasos/<int:paso_id>` | DELETE | brd.py |
| `/api/calidad/agua/registros` | GET,POST | calidad.py |
| `/api/calidad/archivar-r2` | GET,POST | calidad.py |
| `/api/calidad/auditorias` | GET,POST | calidad.py |
| `/api/calidad/capa` | GET,POST | calidad.py |
| `/api/calidad/capa/<int:cid>` | PATCH | calidad.py |
| `/api/calidad/certificado-analisis` | GET,POST | calidad.py |
| `/api/calidad/coa` | GET,POST | calidad.py |
| `/api/calidad/config/micro-gate` | GET,POST | calidad.py |
| `/api/calidad/cronograma/completar` | POST | calidad.py |
| `/api/calidad/cronograma/iniciar` | POST | calidad.py |
| `/api/calidad/especificaciones` | GET,POST | calidad.py |
| `/api/calidad/especificaciones/<int:eid>` | DELETE,PATCH | calidad.py |
| `/api/calidad/estabilidades` | GET,POST | calidad.py |
| `/api/calidad/fisicoquimica/resultados` | GET,POST | calidad.py |
| `/api/calidad/indicadores/metas/<codigo>` | PATCH | calidad.py |
| `/api/calidad/micro/importar-eml` | POST | calidad.py |
| `/api/calidad/micro/resultados` | GET,POST | calidad.py |
| `/api/calidad/micro/specs` | GET,POST | calidad.py |
| `/api/calidad/no-conformidades` | GET,POST | calidad.py |
| `/api/calidad/recepcion-tecnica` | GET,POST | calidad.py |
| `/api/calidad/reconstruir-expediente` | GET,POST | calidad.py |
| `/api/chat/heartbeat` | POST | chat.py |
| `/api/chat/messages/<int:message_id>` | DELETE,PATCH | chat.py |
| `/api/chat/messages/<int:message_id>/react` | DELETE,POST | chat.py |
| `/api/chat/threads/<int:thread_id>/asignar-tarea` | POST | chat.py |
| `/api/chat/threads/<int:thread_id>/leer` | POST | chat.py |
| `/api/chat/threads/<int:thread_id>/messages` | GET,POST | chat.py |
| `/api/chat/threads/<int:thread_id>/miembros` | POST | chat.py |
| `/api/aliados/<int:cid>` | PATCH | clientes.py |
| `/api/clientes` | GET,POST | clientes.py |
| `/api/clientes/<int:cid>` | GET,PUT | clientes.py |
| `/api/despachos` | GET,POST | clientes.py |
| `/api/pedidos` | GET,POST | clientes.py |
| `/api/stock-pt` | GET,POST | clientes.py |
| `/api/comercial/maquila/<int:mid>` | PATCH | comercial.py |
| `/api/eos/leads/<int:lid>` | PATCH | comercial.py |
| `/api/eos/leads/webhook` | POST | comercial.py |
| `/api/compliance/capa` | GET,POST | compliance.py |
| `/api/compliance/capa/<int:cid>` | PATCH | compliance.py |
| `/api/compliance/cronogramas/<int:cron_id>/ejecuciones` | GET,POST | compliance.py |
| `/api/compliance/ejecuciones/<int:ej_id>/cumplir` | POST | compliance.py |
| `/api/compliance/hallazgos` | GET,POST | compliance.py |
| `/api/compliance/hallazgos/<int:hid>` | PATCH | compliance.py |
| `/api/compras/consumibles` | GET,POST | compras.py |
| `/api/compras/consumibles/<int:cid>` | DELETE,PATCH | compras.py |
| `/api/compras/facturas-proveedor` | POST | compras.py |
| `/api/compras/facturas-proveedor/<int:fid>` | PATCH | compras.py |
| `/api/compras/facturas-proveedor/<int:fid>/pagar` | POST | compras.py |
| `/api/compras/oc/<numero_oc>/rechazar` | POST | compras.py |
| `/api/compras/oc/<numero_oc>/reparar-desde-solicitud` | POST | compras.py |
| `/api/compras/ocr-factura` | POST | compras.py |
| `/api/compras/ordenes-compra/<numero_oc>/aplicar-saldo` | POST | compras.py |
| `/api/compras/ordenes-servicio` | GET,POST | compras.py |
| `/api/compras/proveedor-saldo/registrar` | POST | compras.py |
| `/api/compras/sugerir-mp-bulk` | POST | compras.py |
| `/api/compras/validar-precios-bulk` | POST | compras.py |
| `/api/comprobantes-pago/<int:comp_id>/email` | POST | compras.py |
| `/api/generar-oc-automatica` | POST | compras.py |
| `/api/movimientos-mee` | GET,POST | compras.py |
| `/api/movimientos-mee/lote` | POST | compras.py |
| `/api/ordenes-compra/<numero_oc>/autorizar` | PATCH | compras.py |
| `/api/comunicacion/actas` | GET,POST | comunicacion.py |
| `/api/comunicacion/actas/<int:aid>/parsear` | POST | comunicacion.py |
| `/api/comunicacion/mensajes` | GET,POST | comunicacion.py |
| `/api/comunicacion/mensajes/<int:mid>/leido` | POST | comunicacion.py |
| `/api/comunicacion/quejas/<int:qid>/resolver` | POST | comunicacion.py |
| `/api/comunicacion/tareas` | GET,POST | comunicacion.py |
| `/api/comunicacion/tareas/<int:tid>` | DELETE,GET,PATCH | comunicacion.py |
| `/api/comunicacion/tareas/<int:tid>/asignar-area` | POST | comunicacion.py |
| `/api/comunicacion/tareas/<int:tid>/avance` | POST | comunicacion.py |
| `/api/contabilidad/facturas/<numero>/anular` | PATCH | contabilidad.py |
| `/api/contabilidad/facturas/<numero>/pago` | POST | contabilidad.py |
| `/api/contabilidad/facturas/generar` | POST | contabilidad.py |
| `/api/contabilidad/login` | POST | contabilidad.py |
| `/api/contabilidad/logout` | POST | contabilidad.py |
| `/api/admin/usuarios` | POST | core.py |
| `/api/admin/usuarios/<username>` | PATCH | core.py |
| `/api/admin/usuarios/<username>/reset-password` | POST | core.py |
| `/api/cambiar-password` | POST | core.py |
| `/api/espagiria/pedido-rapido` | POST | espagiria.py |
| `/api/sign/challenge` | POST | firmas.py |
| `/api/compromisos` | GET,POST | hub.py |
| `/api/compromisos/<int:cid>` | PATCH | hub.py |
| `/api/alertas` | GET,POST | inventario.py |
| `/api/alertas/silenciar` | POST | inventario.py |
| `/api/alertas/silenciar/<int:silen_id>` | DELETE | inventario.py |
| `/api/formulas/<path:producto_nombre>/imagen` | DELETE,GET,POST | inventario.py |
| `/api/formulas/<path:producto_nombre>/imagen-shopify-sync` | POST | inventario.py |
| `/api/formulas/duplicar` | POST | inventario.py |
| `/api/formulas/sync-shopify-all` | POST | inventario.py |
| `/api/formulas/sync-shopify-blocking` | POST | inventario.py |
| `/api/formulas/unlock` | POST | inventario.py |
| `/api/liberacion` | GET,POST | inventario.py |
| `/api/liberacion/<int:lid>` | PATCH | inventario.py |
| `/api/lotes/cuarentena/<int:mov_id>/liberar` | POST | inventario.py |
| `/api/maestro-mps/<codigo>/archivar` | PUT | inventario.py |
| `/api/maestro-mps/<codigo>/mee-stock-minimo` | PUT | inventario.py |
| `/api/maestro-mps/<codigo>/proveedor` | PUT | inventario.py |
| `/api/maestro-mps/alias` | DELETE,GET,POST | inventario.py |
| `/api/mee/<codigo>` | DELETE,GET,PUT | inventario.py |
| `/api/mee/<codigo>/ajustar` | POST | inventario.py |
| `/api/mee/<codigo>/proveedor` | PUT | inventario.py |
| `/api/mee/<codigo>/stock-minimo` | PUT | inventario.py |
| `/api/mee/calificar` | POST | inventario.py |
| `/api/mee/cuarentena/<int:mov_id>/<accion>` | POST | inventario.py |
| `/api/mee/import-bulk` | POST | inventario.py |
| `/api/produccion` | GET,POST | inventario.py |
| `/api/produccion/simular` | POST | inventario.py |
| `/api/animus/solicitar-produccion` | POST | maquila.py |
| `/api/animus/solicitudes-produccion/<int:sid>` | PATCH | maquila.py |
| `/api/hub-salida/despachar` | POST | maquila.py |
| `/api/maquila/cotizar` | POST | maquila.py |
| `/api/maquila/ordenes` | GET,POST | maquila.py |
| `/api/maquila/ordenes/<int:oid>` | PATCH | maquila.py |
| `/api/maquila/ordenes/<int:oid>/facturar` | POST | maquila.py |
| `/api/maquila/prospectos` | GET,POST | maquila.py |
| `/api/maquila/prospectos/<int:pid>` | PATCH | maquila.py |
| `/api/stock-pt/<sku>/reorden` | POST | maquila.py |
| `/api/marketing/ab-tests` | GET,POST | marketing.py |
| `/api/marketing/ab-tests/<int:tid>/calcular-ganador` | POST | marketing.py |
| `/api/marketing/ads/sync-meta` | POST | marketing.py |
| `/api/marketing/campana-influencer` | POST | marketing.py |
| `/api/marketing/campana-influencer/<int:rid>` | PUT | marketing.py |
| `/api/marketing/campanas` | GET,POST | marketing.py |
| `/api/marketing/campanas/<int:cid>/generar-cupon` | POST | marketing.py |
| `/api/marketing/contenido` | GET,POST | marketing.py |
| `/api/marketing/contenido/<int:cid>` | DELETE,PUT | marketing.py |
| `/api/marketing/eventos-calendario` | GET,POST | marketing.py |
| `/api/marketing/eventos-calendario/<int:eid>` | DELETE,PUT | marketing.py |
| `/api/marketing/fix-pago-link` | POST | marketing.py |
| `/api/marketing/ig-refresh` | POST | marketing.py |
| `/api/marketing/ig-update-token` | POST | marketing.py |
| `/api/marketing/influencers/<int:iid>/banco` | PUT | marketing.py |
| `/api/marketing/influencers/<int:iid>/dar-baja` | POST | marketing.py |
| `/api/marketing/influencers/<int:iid>/generar-cupon` | POST | marketing.py |
| `/api/marketing/influencers/<int:iid>/refresh-metrics` | POST | marketing.py |
| `/api/marketing/metas` | GET,POST | marketing.py |
| `/api/marketing/pagos-historico-cleanup` | POST | marketing.py |
| `/api/marketing/refresh-all-metrics` | POST | marketing.py |
| `/api/marketing/reporte-ejecutivo-semanal` | GET,POST | marketing.py |
| `/api/marketing/sync/<platform>` | POST | marketing.py |
| `/api/marketing/workflow/aplicar-agente` | POST | marketing.py |
| `/api/mfa/backup-codes/regenerate` | POST | mfa.py |
| `/api/mfa/disable` | POST | mfa.py |
| `/api/mfa/setup` | POST | mfa.py |
| `/api/mfa/verify-setup` | POST | mfa.py |
| `/api/notif/<int:nid>/leer` | POST | notif.py |
| `/api/notif/marcar-todas` | POST | notif.py |
| `/api/admin/b2b/cliente/<cliente_id>/envases` | POST | plan.py |
| `/api/admin/clientes-b2b/migrar-desde-maquila` | POST | plan.py |
| `/api/admin/formulas-reconciliar` | POST | plan.py |
| `/api/admin/formulas/agrupar-canonico` | POST | plan.py |
| `/api/admin/lotes/regenerar-distribucion` | POST | plan.py |
| `/api/admin/sku-producto-map/bulk` | POST | plan.py |
| `/api/admin/sub-skus/<path:sku>` | PATCH | plan.py |
| `/api/clientes-b2b` | POST | plan.py |
| `/api/clientes-b2b/<cliente_id>` | DELETE | plan.py |
| `/api/pedidos-b2b` | POST | plan.py |
| `/api/pedidos-b2b/<int:pid>` | PATCH | plan.py |
| `/api/pedidos-b2b/<int:pid>` | DELETE | plan.py |
| `/api/pedidos-b2b/<int:pid>/asignar-a-animus` | POST | plan.py |
| `/api/pedidos-b2b/<int:pid>/asignar-a-lote/<int:lote_id>` | POST | plan.py |
| `/api/pedidos-b2b/<int:pid>/confirmar` | POST | plan.py |
| `/api/pedidos-b2b/<int:pid>/despachar` | POST | plan.py |
| `/api/plan/acelerador-config` | GET,POST | plan.py |
| `/api/plan/aceptar-adelanto` | POST | plan.py |
| `/api/plan/aplicar-ia-anual` | POST | plan.py |
| `/api/plan/aplicar-ia-bulk` | POST | plan.py |
| `/api/plan/auto-programar-sugeridas` | POST | plan.py |
| `/api/plan/autoplan-ia` | POST | plan.py |
| `/api/plan/autoplan-ia/feedback` | POST | plan.py |
| `/api/plan/backfill-fabricacion` | GET,POST | plan.py |
| `/api/plan/configurar-canonicos` | GET,POST | plan.py |
| `/api/plan/dedup-mismo-dia` | GET,POST | plan.py |
| `/api/plan/dejar-solo-real` | GET,POST | plan.py |
| `/api/plan/eliminar-dia` | GET,POST | plan.py |
| `/api/plan/generar-plan-desde-hoy` | GET,POST | plan.py |
| `/api/plan/generar-plan-perfecto` | POST | plan.py |
| `/api/plan/kg-otro-cliente-cadena` | POST | plan.py |
| `/api/plan/limpiar-duplicados` | POST | plan.py |
| `/api/plan/limpiar-futuro-auto` | POST | plan.py |
| `/api/plan/limpiar-proyeccion` | POST | plan.py |
| `/api/plan/limpiar-sugeridas-futuras` | POST | plan.py |
| `/api/plan/limpiar-todo-calendario` | GET,POST | plan.py |
| `/api/plan/lote/<int:lote_id>/agregar-cliente` | POST | plan.py |
| `/api/plan/pauta-multitono` | GET,POST | plan.py |
| `/api/plan/plan-sugerido/ejecutar` | POST | plan.py |
| `/api/plan/producto-externo` | GET,POST | plan.py |
| `/api/plan/producto/<path:producto>/presentaciones` | POST | plan.py |
| `/api/plan/programar-cadencia-desde-lote/<int:lote_id>` | POST | plan.py |
| `/api/plan/programar-cadencia-producto` | POST | plan.py |
| `/api/plan/programar-canonico` | POST | plan.py |
| `/api/plan/programar-manual` | POST | plan.py |
| `/api/plan/programar-produccion` | POST | plan.py |
| `/api/plan/proximas/<int:pid>/cantidad` | POST | plan.py |
| `/api/plan/proximas/<int:pid>/pausar` | POST | plan.py |
| `/api/plan/proximas/<int:pid>/reactivar` | POST | plan.py |
| `/api/plan/proximas/<int:pid>/reprogramar` | POST | plan.py |
| `/api/plan/proyectar-2anios` | GET,POST | plan.py |
| `/api/plan/reconstruir-plan` | GET,POST | plan.py |
| `/api/plan/recuperar-cancelados-bug` | GET,POST | plan.py |
| `/api/plan/recuperar-semana-19may2026` | GET,POST | plan.py |
| `/api/plan/regenerar-canonicos` | POST | plan.py |
| `/api/plan/registrar-produccion-completada` | POST | plan.py |
| `/api/plan/repartir-sobrecargados` | GET,POST | plan.py |
| `/api/plan/reprogramar-desde-mes` | GET,POST | plan.py |
| `/api/plan/restaurar-a-hora` | GET,POST | plan.py |
| `/api/plan/revertir-hoy` | GET,POST | plan.py |
| `/api/plan/sellar-horizonte` | POST | plan.py |
| `/api/plan/set-volumen` | POST | plan.py |
| `/api/plan/set-volumenes-bulk` | POST | plan.py |
| `/api/plan/solo-manual` | GET,POST | plan.py |
| `/api/admin/portal/catalogo` | GET,POST | portal.py |
| `/api/admin/portal/credenciales` | GET,POST | portal.py |
| `/api/admin/portal/credenciales/<int:cred_id>` | DELETE,PATCH | portal.py |
| `/api/admin/portal/pqr/<int:pqr_id>` | PATCH | portal.py |
| `/api/portal-demo/regenerar` | POST | portal.py |
| `/api/portal/login` | POST | portal.py |
| `/api/portal/pedidos` | POST | portal.py |
| `/api/portal/pedidos/<int:pid>` | PATCH | portal.py |
| `/api/portal/solicitudes` | POST | portal.py |
| `/api/portal/solicitudes/<int:sol_id>/convertir-a-pedido` | POST | portal.py |
| `/api/abastecimiento/solicitar-items` | POST | programacion.py |
| `/api/abastecimiento/vincular-formula` | POST | programacion.py |
| `/api/admin/marcacion-envase` | POST | programacion.py |
| `/api/compras/minimos-envases-aplicar` | POST | programacion.py |
| `/api/compras/solicitudes-produccion/<int:sol_id>/decidir` | POST | programacion.py |
| `/api/planta/aceptar-produccion/<int:produccion_id>` | POST | programacion.py |
| `/api/planta/actividades/<int:act_id>/terminar` | POST | programacion.py |
| `/api/planta/area/liberar-vivo` | POST | programacion.py |
| `/api/planta/area/ocupar-vivo` | POST | programacion.py |
| `/api/planta/areas/<int:area_id>/actividades` | GET,POST | programacion.py |
| `/api/planta/asignar-areas` | POST | programacion.py |
| `/api/planta/auto-asignar-pendientes` | POST | programacion.py |
| `/api/planta/auto-asignar/<int:prod_id>` | POST | programacion.py |
| `/api/planta/envasado/<int:envasado_id>/terminar` | POST | programacion.py |
| `/api/planta/envasado/iniciar` | POST | programacion.py |
| `/api/planta/equipos/<int:eq_id>` | DELETE,GET,PUT | programacion.py |
| `/api/planta/limpiar-db-sin-calendar` | POST | programacion.py |
| `/api/planta/limpieza-profunda/<int:item_id>/completar` | POST | programacion.py |
| `/api/planta/limpieza-profunda/generar` | POST | programacion.py |
| `/api/planta/preflight/<int:produccion_id>/confirmar-limpieza` | POST | programacion.py |
| `/api/planta/presentaciones` | POST | programacion.py |
| `/api/planta/presentaciones/<int:pid>` | DELETE,PUT | programacion.py |
| `/api/planta/presentaciones/bulk-categoria` | POST | programacion.py |
| `/api/planta/simulacro/limpiar` | POST | programacion.py |
| `/api/planta/sugerir-area` | POST | programacion.py |
| `/api/programacion/checklist/generar/<int:produccion_id>` | POST | programacion.py |
| `/api/programacion/checklist/items/<int:item_id>` | PATCH | programacion.py |
| `/api/programacion/checklist/items/<int:item_id>/asignar-mee` | POST | programacion.py |
| `/api/programacion/checklist/items/<int:item_id>/solicitar` | POST | programacion.py |
| `/api/programacion/checklist/items/<int:item_id>/solicitar-produccion` | POST | programacion.py |
| `/api/programacion/decision-produccion` | POST | programacion.py |
| `/api/programacion/estacionalidad-config` | GET,POST | programacion.py |
| `/api/programacion/generar-oc` | POST | programacion.py |
| `/api/programacion/lote/<int:lote_id>/envase-aplicar-default` | POST | programacion.py |
| `/api/programacion/lote/<int:lote_id>/envase-override` | PATCH | programacion.py |
| `/api/programacion/lote/<int:lote_id>/envase-propagar-futuros` | POST | programacion.py |
| `/api/programacion/lote/<int:lote_id>/fija-override` | PATCH | programacion.py |
| `/api/programacion/lote/<int:lote_id>/plan-envasado/<int:pbl_id>` | PATCH | programacion.py |
| `/api/programacion/marcacion-cambiar-envase` | POST | programacion.py |
| `/api/programacion/marcacion-crear-envase` | POST | programacion.py |
| `/api/programacion/marcacion-orden/<int:oid>/liberar` | POST | programacion.py |
| `/api/programacion/marcacion-vincular` | POST | programacion.py |
| `/api/programacion/mp-bridge` | POST | programacion.py |
| `/api/programacion/mp-bridge/<int:bridge_id>` | DELETE | programacion.py |
| `/api/programacion/planificacion/solicitar-bulk` | POST | programacion.py |
| `/api/programacion/por-entrar-manual` | GET,POST | programacion.py |
| `/api/programacion/pres-agregar` | GET,POST | programacion.py |
| `/api/programacion/pres-crear` | GET,POST | programacion.py |
| `/api/programacion/pres-editar` | GET,POST | programacion.py |
| `/api/programacion/pres-eliminar` | GET,POST | programacion.py |
| `/api/programacion/pres-no-aplica` | GET,POST | programacion.py |
| `/api/programacion/pres-quitar` | GET,POST | programacion.py |
| `/api/programacion/pres-set-envase` | GET,POST | programacion.py |
| `/api/programacion/pres-set-fija` | GET,POST | programacion.py |
| `/api/programacion/pres-ventas` | GET,POST | programacion.py |
| `/api/programacion/programar` | POST | programacion.py |
| `/api/programacion/programar/<int:evento_id>` | DELETE | programacion.py |
| `/api/programacion/programar/<int:evento_id>/asignar` | PATCH | programacion.py |
| `/api/programacion/programar/<int:evento_id>/terminar` | POST | programacion.py |
| `/api/programacion/refrescar-ventas-diarias` | GET,POST | programacion.py |
| `/api/programacion/regenerar-oc` | POST | programacion.py |
| `/api/programacion/registrar-stock` | POST | programacion.py |
| `/api/programacion/sku-volumen` | GET,POST | programacion.py |
| `/api/programacion/sync-historico-shopify` | GET,POST | programacion.py |
| `/api/programacion/sync-stock-shopify` | POST | programacion.py |
| `/api/programacion/sync-ventas` | POST | programacion.py |
| `/api/tareas-operativas` | POST | programacion.py |
| `/api/tareas-operativas/<int:tarea_id>/completar` | POST | programacion.py |
| `/api/rrhh/ausencias` | GET,POST | rrhh.py |
| `/api/rrhh/ausencias/<int:aid>` | PATCH | rrhh.py |
| `/api/rrhh/calcular-pago-evento` | POST | rrhh.py |
| `/api/rrhh/capacitaciones` | GET,POST | rrhh.py |
| `/api/rrhh/compromisos-mejora` | GET,POST | rrhh.py |
| `/api/rrhh/compromisos-mejora/<int:cid>/completar` | POST | rrhh.py |
| `/api/rrhh/empleados` | GET,POST | rrhh.py |
| `/api/rrhh/empleados/<int:eid>` | GET,PUT | rrhh.py |
| `/api/rrhh/empleados/<int:emp_id>/documentos` | GET,POST | rrhh.py |
| `/api/rrhh/evaluaciones` | GET,POST | rrhh.py |
| `/api/rrhh/eventos` | GET,POST | rrhh.py |
| `/api/rrhh/eventos/<int:evt_id>/aprobar` | POST | rrhh.py |
| `/api/rrhh/eventos/<int:evt_id>/cerrar` | POST | rrhh.py |
| `/api/rrhh/llamados-atencion` | GET,POST | rrhh.py |
| `/api/rrhh/nomina/guardar` | POST | rrhh.py |
| `/api/rrhh/nomina/importar-excel` | POST | rrhh.py |
| `/api/rrhh/sgsst` | GET,POST | rrhh.py |
| `/api/rrhh/sgsst/<int:sid>` | PATCH | rrhh.py |
| `/api/tecnica/cambios-control/<int:cc_id>/aplicar` | POST | tecnica.py |
| `/api/tecnica/documentos` | GET,POST | tecnica.py |
| `/api/tecnica/documentos/<int:did>/marcar-revisado` | POST | tecnica.py |
| `/api/tecnica/fichas` | GET,POST | tecnica.py |
| `/api/tecnica/formulas` | GET,POST | tecnica.py |
| `/api/tecnica/invima` | GET,POST | tecnica.py |

_432 rutas en esta lista._

## Todas las rutas

| Ruta | Métodos | Gate | Archivo |
|---|---|---|---|
| `/admin` | GET | ADMIN | admin.py |
| `/admin/animus-prioridad` | GET | ADMIN | admin.py |
| `/admin/areas-planta` | GET | AUTENTICADO | admin.py |
| `/admin/audit-inventario` | GET | ADMIN | admin.py |
| `/admin/audit-inventario/limpiar-drift-mee` | POST | ADMIN | admin.py |
| `/admin/auditoria-bodega-mp` | GET | AUTENTICADO | admin.py |
| `/admin/auditoria-catalogo` | GET | ADMIN | admin.py |
| `/admin/auditoria-formulas` | GET | ADMIN | admin.py |
| `/admin/auditoria-kardex` | GET | ADMIN | admin.py |
| `/admin/auditoria-producciones` | GET | ADMIN | admin.py |
| `/admin/auditoria-unidad-base` | GET | ADMIN | admin.py |
| `/admin/backfill-debug` | GET | ADMIN | admin.py |
| `/admin/componentes-anclar` | GET | ADMIN | admin.py |
| `/admin/cruce-maestro` | GET | AUTENTICADO | admin.py |
| `/admin/diagnostico-produccion` | GET | AUTENTICADO | admin.py |
| `/admin/disco-preflight` | GET | AUTENTICADO | admin.py |
| `/admin/envases-kardex-mp` | GET | ADMIN | admin.py |
| `/admin/envases-ml` | GET | ADMIN | admin.py |
| `/admin/envases-verificacion` | GET | ADMIN | admin.py |
| `/admin/equipos-sync` | GET | AUTENTICADO | admin.py |
| `/admin/firmas-usuarios` | GET | ADMIN | admin.py |
| `/admin/formula-preflight` | GET | AUTENTICADO | admin.py |
| `/admin/formulas-mismapeo` | GET | AUTENTICADO | admin.py |
| `/admin/impresos-anclar` | GET | ADMIN | admin.py |
| `/admin/influencers-bulk-import` | POST | ADMIN | admin.py |
| `/admin/influencers-cargar-29abr` | GET,POST | ADMIN | admin.py |
| `/admin/influencers-hoy` | GET | ADMIN | admin.py |
| `/admin/influencers-limpieza` | GET | ADMIN | admin.py |
| `/admin/influencers-limpieza` | POST | ADMIN | admin.py |
| `/admin/influencers-reset-pendientes` | POST | ADMIN | admin.py |
| `/admin/integridad-planta` | GET | ADMIN | admin.py |
| `/admin/inteligencia-operacional` | GET | AUTENTICADO | admin.py |
| `/admin/inventario-envase-import` | GET | ADMIN | admin.py |
| `/admin/limpieza-cero-error` | GET | ADMIN | admin.py |
| `/admin/logo-espagiria` | GET | AUTENTICADO | admin.py |
| `/admin/lotes-stock-atrapado` | GET | AUTENTICADO | admin.py |
| `/admin/maestro-envases` | GET | AUTENTICADO | admin.py |
| `/admin/maestro-inci` | GET | AUTENTICADO | admin.py |
| `/admin/mapear-huerfanos` | GET | ADMIN | admin.py |
| `/admin/mapeo-producto-envase` | GET | ADMIN | admin.py |
| `/admin/mapeo-tonos` | GET | ADMIN | admin.py |
| `/admin/marcacion-envases` | GET | AUTENTICADO | admin.py |
| `/admin/mee-fugas-check` | GET | ADMIN | admin.py |
| `/admin/mees-diagnostico` | GET | ADMIN | admin.py |
| `/admin/migraciones-pg` | GET | ADMIN | admin.py |
| `/admin/mp-alcanza` | GET | ADMIN | admin.py |
| `/admin/mps-duplicados` | GET | AUTENTICADO | admin.py |
| `/admin/mps-inci` | GET | AUTENTICADO | admin.py |
| `/admin/mps-sin-uso` | GET | ADMIN | admin.py |
| `/admin/normalizar-formulas` | GET | ADMIN | admin.py |
| `/admin/producciones-debug` | GET | ADMIN | admin.py |
| `/admin/producciones-sin-formula` | GET | AUTENTICADO | admin.py |
| `/admin/programacion-sku` | GET | ADMIN | admin.py |
| `/admin/purgar-gcal` | GET | AUTENTICADO | admin.py |
| `/admin/r2-check` | GET | AUTENTICADO | admin.py |
| `/admin/realidad-cero-error` | GET | ADMIN | admin.py |
| `/admin/recodificar-envases` | GET | ADMIN | admin.py |
| `/admin/reconciliar-precios` | GET | ADMIN | admin.py |
| `/admin/reportes-invima` | GET | ADMIN | admin.py |
| `/admin/salud-formulas` | GET | AUTENTICADO | admin.py |
| `/admin/schema-doctor` | GET | AUTENTICADO | admin.py |
| `/admin/seguridad-planta` | GET | AUTENTICADO | admin.py |
| `/admin/sku-map` | GET | ADMIN | admin.py |
| `/admin/skus-pendientes` | GET | ADMIN | admin.py |
| `/admin/stock-minimos` | GET | ADMIN | admin.py |
| `/admin/sync-batch-formulas` | GET | ADMIN | admin.py |
| `/admin/tapas-goteros-anclar` | GET | ADMIN | admin.py |
| `/admin/verificar-formulas` | GET | AUTENTICADO | admin.py |
| `/admin/zero-error` | GET | ADMIN | admin.py |
| `/api/admin/agent-memory` | GET,POST | ADMIN | admin.py |
| `/api/admin/ajustar-formula-pct` | POST | ADMIN | admin.py |
| `/api/admin/animus-prioridad-agotamiento` | GET | ADMIN | admin.py |
| `/api/admin/aplicar-correcciones-formulas-batch-2026-04-28` | POST | ADMIN | admin.py |
| `/api/admin/aplicar-migraciones-pg` | GET,POST | ADMIN | admin.py |
| `/api/admin/aplicar-minimos` | POST | ADMIN | admin.py |
| `/api/admin/aplicar-stock-minimos-sugeridos` | POST | ADMIN | admin.py |
| `/api/admin/archivar-mps-sin-uso-bulk` | POST | ADMIN | admin.py |
| `/api/admin/areas-planta` | GET | ADMIN | admin.py |
| `/api/admin/areas-planta/set` | POST | ADMIN | admin.py |
| `/api/admin/asegurar-mp` | POST | ADMIN | admin.py |
| `/api/admin/asignar-operador-bulk` | POST | ADMIN | admin.py |
| `/api/admin/audit-inventario-vs-excel` | POST | ADMIN | admin.py |
| `/api/admin/auditar-minimos` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-bodega-mp` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-catalogo` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-fefo-descuento` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-formulas-completa` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-kardex-drift` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-lotes` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-lotes-nuevos` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-lotes/html` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-mps-nuevas` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-producciones-descuento` | GET | ADMIN | admin.py |
| `/api/admin/auditoria-unidad-base` | GET | ADMIN | admin.py |
| `/api/admin/auto-unir-por-inci` | POST | ADMIN | admin.py |
| `/api/admin/backfill-coa-r2` | POST | ADMIN | admin.py |
| `/api/admin/backup-now` | POST | ADMIN | admin.py |
| `/api/admin/backup/<path:filename>` | GET | ADMIN | admin.py |
| `/api/admin/backups` | GET | ADMIN | admin.py |
| `/api/admin/brd-visibilidad` | GET,POST | ADMIN | admin.py |
| `/api/admin/cambiar-formula` | POST | ADMIN | admin.py |
| `/api/admin/cancelar-produccion-huerfana` | POST | ADMIN | admin.py |
| `/api/admin/completar-info-lote-bulk` | POST | ADMIN | admin.py |
| `/api/admin/componentes-aplicar` | POST | ADMIN | admin.py |
| `/api/admin/componentes-preview` | GET | ADMIN | admin.py |
| `/api/admin/config-status` | GET | ADMIN | admin.py |
| `/api/admin/corregir-formulas` | POST | ADMIN | admin.py |
| `/api/admin/corregir-unidad-base-bulk` | POST | ADMIN | admin.py |
| `/api/admin/crear-mps-faltantes-excel` | POST | ADMIN | admin.py |
| `/api/admin/crear-mps-huerfanas` | POST | ADMIN | admin.py |
| `/api/admin/crear-persona-firma` | POST | ADMIN | admin.py |
| `/api/admin/cron-db-integrity-check` | GET,POST | ADMIN | admin.py |
| `/api/admin/cron-snapshot-mp-alcanza` | GET,POST | ADMIN | admin.py |
| `/api/admin/cruce-maestro` | POST | ADMIN | admin.py |
| `/api/admin/cruce-maestro/archivar-producto` | POST | ADMIN | admin.py |
| `/api/admin/cruce-maestro/pares` | POST | ADMIN | admin.py |
| `/api/admin/cruce-maestro/reapuntar-formula` | POST | ADMIN | admin.py |
| `/api/admin/db-health-historial` | GET | ADMIN | admin.py |
| `/api/admin/debug-calendar-producto` | GET | ADMIN | admin.py |
| `/api/admin/debug-consumo-mp/<codigo_mp>` | GET | ADMIN | admin.py |
| `/api/admin/debug-formula-items` | GET | ADMIN | admin.py |
| `/api/admin/debug-formulas-recientes` | GET | ADMIN | admin.py |
| `/api/admin/debug-ocs-transito` | GET | ADMIN | admin.py |
| `/api/admin/debug-solicitud/<numero>` | GET | ADMIN | admin.py |
| `/api/admin/diag-login/<username>` | GET | ADMIN | admin.py |
| `/api/admin/diag-produccion` | GET | ADMIN | admin.py |
| `/api/admin/diagnosticar-formulas` | GET | ADMIN | admin.py |
| `/api/admin/diagnostico-produccion-global` | GET | ADMIN | admin.py |
| `/api/admin/disco-preflight` | GET | ADMIN | admin.py |
| `/api/admin/ebr-mode` | POST | ADMIN | admin.py |
| `/api/admin/eliminar-formulas-obsoletas` | POST | ADMIN | admin.py |
| `/api/admin/email-alejandro-formulas-faltantes` | GET,POST | ADMIN | admin.py |
| `/api/admin/emergency-restore` | GET,POST | ADMIN | admin.py |
| `/api/admin/envase-crear` | POST | ADMIN | admin.py |
| `/api/admin/envase-ml` | POST | ADMIN | admin.py |
| `/api/admin/envases-kardex-mp` | GET | ADMIN | admin.py |
| `/api/admin/envases-kardex-mp/mover` | POST | ADMIN | admin.py |
| `/api/admin/equipos-sync` | POST | ADMIN | admin.py |
| `/api/admin/exigir-area-limpia` | POST | ADMIN | admin.py |
| `/api/admin/explicar-stock-min/<codigo>` | GET | ADMIN | admin.py |
| `/api/admin/firma-usuario` | POST | ADMIN | admin.py |
| `/api/admin/forensic-trazabilidad` | GET | ADMIN | admin.py |
| `/api/admin/formula-bodega-cruce` | GET | ADMIN | admin.py |
| `/api/admin/formula-duplicados` | GET | ADMIN | admin.py |
| `/api/admin/formula-huerfanos-con-sugerencias` | GET | ADMIN | admin.py |
| `/api/admin/formula-limpiar-duplicados` | POST | ADMIN | admin.py |
| `/api/admin/formula-preflight` | POST | ADMIN | admin.py |
| `/api/admin/formula-remapear-material-id` | POST | ADMIN | admin.py |
| `/api/admin/formulas-mismapeo` | GET | ADMIN | admin.py |
| `/api/admin/gloss-tonos-aplicar` | POST | ADMIN | admin.py |
| `/api/admin/gloss-tonos-preview` | GET | ADMIN | admin.py |
| `/api/admin/health-check-post-reset` | GET | ADMIN | admin.py |
| `/api/admin/health/critical-paths` | GET | ADMIN | admin.py |
| `/api/admin/import-inventario-envase-xlsx` | POST | ADMIN | admin.py |
| `/api/admin/import-mps-nombres-excel` | POST | ADMIN | admin.py |
| `/api/admin/import-pagos-influencers-excel` | POST | ADMIN | admin.py |
| `/api/admin/importar-maestro-inci` | GET,POST | ADMIN | admin.py |
| `/api/admin/impresos-aplicar` | POST | ADMIN | admin.py |
| `/api/admin/impresos-preview` | GET | ADMIN | admin.py |
| `/api/admin/integridad-bridge` | GET | ADMIN | admin.py |
| `/api/admin/inventario-diagnostico-entradas` | GET | ADMIN | admin.py |
| `/api/admin/inventario-health-monitor` | GET | ADMIN | admin.py |
| `/api/admin/inventario-reset-aplicar` | POST | ADMIN | admin.py |
| `/api/admin/inventario-reset-preview` | POST | ADMIN | admin.py |
| `/api/admin/inventario-snapshot-pre-reset` | GET | ADMIN | admin.py |
| `/api/admin/investigar-mee/<codigo>` | GET | ADMIN | admin.py |
| `/api/admin/investigar-mp/<codigo>` | GET | ADMIN | admin.py |
| `/api/admin/io/inicio-labores` | GET | ADMIN | admin.py |
| `/api/admin/io/lead-time-compras` | GET | ADMIN | admin.py |
| `/api/admin/io/productividad-operario` | GET | ADMIN | admin.py |
| `/api/admin/io/tiempos-produccion` | GET | ADMIN | admin.py |
| `/api/admin/limpiar-produccion-zombies` | GET,POST | ADMIN | admin.py |
| `/api/admin/logo-espagiria` | POST | ADMIN | admin.py |
| `/api/admin/lotes-stock-atrapado` | GET,POST | ADMIN | admin.py |
| `/api/admin/maestro-envases-aplicar` | POST | ADMIN | admin.py |
| `/api/admin/maestro-envases-diff` | GET | ADMIN | admin.py |
| `/api/admin/maestro-inci-aplicar` | POST | ADMIN | admin.py |
| `/api/admin/maestro-inci-diff` | POST | ADMIN | admin.py |
| `/api/admin/maestro-mees-list` | GET | ADMIN | admin.py |
| `/api/admin/maestro-mps-unificar-bulk` | POST | ADMIN | admin.py |
| `/api/admin/mapear-envase` | POST | ADMIN | admin.py |
| `/api/admin/mapear-huerfanos-produccion` | GET | ADMIN | admin.py |
| `/api/admin/mapear-huerfanos-produccion/aplicar` | POST | ADMIN | admin.py |
| `/api/admin/marcar-lotes-vencidos` | POST | ADMIN | admin.py |
| `/api/admin/marcar-vencidos-bulk-todos` | POST | ADMIN | admin.py |
| `/api/admin/material-ids-huerfanos` | GET | ADMIN | admin.py |
| `/api/admin/mee-base` | POST | ADMIN | admin.py |
| `/api/admin/mee-fugas-check` | GET | ADMIN | admin.py |
| `/api/admin/mee-imagen` | POST | ADMIN | admin.py |
| `/api/admin/mee-parte` | POST | ADMIN | admin.py |
| `/api/admin/mee-parte/<int:parte_id>` | DELETE | ADMIN | admin.py |
| `/api/admin/mee-shopify-foto` | POST | ADMIN | admin.py |
| `/api/admin/mees-abreviaturas-audit` | GET | ADMIN | admin.py |
| `/api/admin/mees-abreviaturas-fix` | POST | ADMIN | admin.py |
| `/api/admin/mees-diagnostico` | GET | ADMIN | admin.py |
| `/api/admin/mees-huerfanos-audit` | GET | ADMIN | admin.py |
| `/api/admin/mees-huerfanos-fix` | POST | ADMIN | admin.py |
| `/api/admin/mees-mapping-upsert` | POST | ADMIN | admin.py |
| `/api/admin/modo-beta-planta` | POST | ADMIN | admin.py |
| `/api/admin/mp-actualizar-inci` | POST | ADMIN | admin.py |
| `/api/admin/mp-alcanza-historial` | GET | ADMIN | admin.py |
| `/api/admin/mp-alcanza-multi` | GET | ADMIN | admin.py |
| `/api/admin/mp-ficha/<path:codigo>` | GET | ADMIN | admin.py |
| `/api/admin/mp-inspeccionar` | GET | ADMIN | admin.py |
| `/api/admin/mps-abreviaturas-audit` | GET | ADMIN | admin.py |
| `/api/admin/mps-abreviaturas-fix` | POST | ADMIN | admin.py |
| `/api/admin/mps-asignar-proveedor` | POST | ADMIN | admin.py |
| `/api/admin/mps-duplicados-stock` | GET | ADMIN | admin.py |
| `/api/admin/mps-inci-sospechoso` | GET | ADMIN | admin.py |
| `/api/admin/mps-proveedores-status` | GET | ADMIN | admin.py |
| `/api/admin/mps-sin-uso` | GET | ADMIN | admin.py |
| `/api/admin/ocs-revision-limpieza` | GET | ADMIN | admin.py |
| `/api/admin/presentaciones-sku-diagnostico` | GET | ADMIN | admin.py |
| `/api/admin/producciones-inconsistentes` | GET | ADMIN | admin.py |
| `/api/admin/producto-presentaciones` | GET | ADMIN | admin.py |
| `/api/admin/producto-presentaciones-upsert` | POST | ADMIN | admin.py |
| `/api/admin/producto-presentaciones/<int:pid>` | DELETE | ADMIN | admin.py |
| `/api/admin/producto-volumen-upsert` | POST | ADMIN | admin.py |
| `/api/admin/productos-calendar-sin-formula` | GET | ADMIN | admin.py |
| `/api/admin/productos-envase-estado` | GET | ADMIN | admin.py |
| `/api/admin/programacion-vs-calendar` | GET | ADMIN | admin.py |
| `/api/admin/purgar-gcal` | POST | ADMIN | admin.py |
| `/api/admin/r2-check` | GET,POST | ADMIN | admin.py |
| `/api/admin/realidad-cero-error` | GET | ADMIN | admin.py |
| `/api/admin/reconciliar-mee` | POST | ADMIN | admin.py |
| `/api/admin/reconciliar-precios-historico` | GET | ADMIN | admin.py |
| `/api/admin/reconciliar-precios-historico/aplicar` | POST | ADMIN | admin.py |
| `/api/admin/reconciliar-produccion-mp` | POST | ADMIN | admin.py |
| `/api/admin/renombrar-producto` | POST | ADMIN | admin.py |
| `/api/admin/reparar-stock-formula` | POST | ADMIN | admin.py |
| `/api/admin/reset-password` | POST | ADMIN | admin.py |
| `/api/admin/restore-backup` | POST | ADMIN | admin.py |
| `/api/admin/retirar-huerfanos-muertos` | POST | ADMIN | admin.py |
| `/api/admin/revertir-correcciones-formulas-recientes` | POST | ADMIN | admin.py |
| `/api/admin/revertir-formulas-desde-backup` | POST | ADMIN | admin.py |
| `/api/admin/salud-formulas` | GET | ADMIN | admin.py |
| `/api/admin/schema-doctor` | GET,POST | ADMIN | admin.py |
| `/api/admin/security-events` | GET | ADMIN | admin.py |
| `/api/admin/seguridad-planta` | GET | ADMIN | admin.py |
| `/api/admin/sembrar-maestro-desde-excel` | POST | ADMIN | admin.py |
| `/api/admin/sku-map` | GET | ADMIN | admin.py |
| `/api/admin/sku-map` | POST | ADMIN | admin.py |
| `/api/admin/sku-producto-map` | GET,POST | ADMIN | admin.py |
| `/api/admin/stock-mp-diagnostico` | GET | ADMIN | admin.py |
| `/api/admin/sugerir-stock-minimos` | GET | ADMIN | admin.py |
| `/api/admin/sync-formula-batch` | POST | ADMIN | admin.py |
| `/api/admin/sync-influencers-excel` | POST | ADMIN | admin.py |
| `/api/admin/sync-todas-formulas-batch` | GET,POST | ADMIN | admin.py |
| `/api/admin/tapas-goteros-aplicar` | POST | ADMIN | admin.py |
| `/api/admin/tapas-goteros-preview` | GET | ADMIN | admin.py |
| `/api/admin/test-email` | POST | ADMIN | admin.py |
| `/api/admin/tipos-mp-stats` | GET | ADMIN | admin.py |
| `/api/admin/users` | GET | ADMIN | admin.py |
| `/api/admin/validacion-profunda` | GET | ADMIN | admin.py |
| `/api/admin/validar-planta` | GET | ADMIN | admin.py |
| `/api/admin/verificar-formulas-excel` | POST | ADMIN | admin.py |
| `/api/admin/verificar-mps-maestro` | POST | ADMIN | admin.py |
| `/api/admin/zero-error-historial` | GET | ADMIN | admin.py |
| `/api/admin/zero-error/status` | GET | ADMIN | admin.py |
| `/api/programacion/sku-status` | GET | ADMIN | admin.py |
| `/api/reportes/invima/lote/<material_id>/<lote>` | GET | ADMIN | admin.py |
| `/api/reportes/invima/lote/<material_id>/<lote>/pdf` | GET | ADMIN | admin.py |
| `/tesoreria` | GET | FINANZAS | admin.py |
| `/tesoreria/vigilancia-precios` | GET | FINANZAS | admin.py |
| `/api/animus/agentes/<agente>` | POST | AUTENTICADO | animus.py |
| `/api/animus/caja` | GET | AUTENTICADO | animus.py |
| `/api/animus/caja` | POST | AUTENTICADO | animus.py |
| `/api/animus/caja/<int:mov_id>` | DELETE | ADMIN | animus.py |
| `/api/animus/calendario` | GET | AUTENTICADO | animus.py |
| `/api/animus/clientes` | GET | AUTENTICADO | animus.py |
| `/api/animus/comando` | GET | AUTENTICADO | animus.py |
| `/api/animus/config` | GET,POST | ADMIN | animus.py |
| `/api/animus/contenido/<int:cid>/usar` | POST | AUTENTICADO | animus.py |
| `/api/animus/contenido/generar` | POST | AUTENTICADO | animus.py |
| `/api/animus/contenido/historial` | GET | AUTENTICADO | animus.py |
| `/api/animus/conteos/<int:conteo_id>/aplicar-ajuste` | POST | AUTENTICADO | animus.py |
| `/api/animus/instagram` | GET | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/baseline` | GET,POST | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/baseline/sembrar-desde-shopify` | POST | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/conteo/<int:asig_id>/registrar` | POST | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/conteo/asignar-hoy` | POST | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/conteo/historial` | GET | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/conteo/pendientes` | GET | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/diagnostico` | GET | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/entrada` | POST | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/esperado` | GET | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/esperado/<sku>` | GET | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/movimientos` | GET | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/salida` | POST | AUTENTICADO | animus.py |
| `/api/animus/inv-fisico/sync-shopify` | POST | AUTENTICADO | animus.py |
| `/api/animus/inventario-ciclico` | GET | AUTENTICADO | animus.py |
| `/api/animus/inventario-ciclico` | POST | AUTENTICADO | animus.py |
| `/api/animus/inventario-ciclico/skus` | GET | AUTENTICADO | animus.py |
| `/api/animus/pqr` | GET,POST | AUTENTICADO | animus.py |
| `/api/animus/pqr/<int:pid>` | PATCH | AUTENTICADO | animus.py |
| `/api/animus/productos` | GET | AUTENTICADO | animus.py |
| `/api/animus/sync/<platform>` | POST | AUTENTICADO | animus.py |
| `/api/artes` | GET | AUTENTICADO | artes.py |
| `/api/artes/<int:aid>/aprobar-arte` | POST | AUTENTICADO | artes.py |
| `/api/artes/<int:aid>/aprobar-fisica` | POST | AUTENTICADO | artes.py |
| `/api/artes/<int:aid>/rechazar` | POST | AUTENTICADO | artes.py |
| `/api/artes/biblioteca` | GET,POST | AUTENTICADO | artes.py |
| `/api/artes/solicitar` | POST | AUTENTICADO | artes.py |
| `/artes` | GET | AUTENTICADO | artes.py |
| `/api/aseguramiento/acuerdos-calidad` | GET,POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/calibracion` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/calibracion/<path:codigo>/historial` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/calibracion/ocs-sugeridas` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/cambios` | GET,POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/cambios/<int:cid>` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/cambios/<int:cid>/aprobar` | POST | ADMIN | aseguramiento.py |
| `/api/aseguramiento/cambios/<int:cid>/cerrar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/cambios/<int:cid>/evaluar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/cambios/<int:cid>/implementar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/cambios/<int:cid>/notificar-invima` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/capacitaciones/asignar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/capacitaciones/firmar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/capacitaciones/mias` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/dashboard` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/desviaciones` | GET,POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/desviaciones/<int:desv_id>` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/desviaciones/<int:desv_id>/capa` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/desviaciones/<int:desv_id>/cerrar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/desviaciones/<int:desv_id>/clasificar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/desviaciones/<int:desv_id>/investigar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/fmea` | GET,POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/indicadores` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/indicadores/metas/<codigo>` | PATCH | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/mis-tareas` | GET | ADMIN | aseguramiento.py |
| `/api/aseguramiento/pqr-inbox` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/pqr-inbox/<int:iid>/descartar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/pqr-inbox/<int:iid>/enrutar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/pqr-inbox/diagnostico` | GET | ADMIN | aseguramiento.py |
| `/api/aseguramiento/pqr-inbox/ghl-test/<contact_id>` | GET | ADMIN | aseguramiento.py |
| `/api/aseguramiento/proveedores-calificacion` | GET,POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/quejas` | GET,POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/quejas/<int:qid>` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/quejas/<int:qid>/cerrar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/quejas/<int:qid>/investigar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/quejas/<int:qid>/responder` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/quejas/<int:qid>/triaje` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/recalls` | GET,POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>/cerrar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>/clasificar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>/notificar-distribuidores` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>/notificar-invima` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/recalls/<int:rid>/recoleccion` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/reportes/audit-trail` | GET | ADMIN | aseguramiento.py |
| `/api/aseguramiento/reportes/audit-trail/csv` | GET | ADMIN | aseguramiento.py |
| `/api/aseguramiento/reportes/cliente-trazabilidad/<int:cid>` | GET | ADMIN | aseguramiento.py |
| `/api/aseguramiento/reportes/lote-trazabilidad/<path:lote>` | GET | ADMIN | aseguramiento.py |
| `/api/aseguramiento/revision-direccion` | GET,POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/revision-direccion/<int:rid>/ejecutar` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/sgd` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/sgd/<path:codigo>` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/sgd/<path:codigo>/pdf` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/sgd/conflictos` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/sgd/conflictos/<int:conflicto_id>/resolver` | POST | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/sgd/importar` | POST | ADMIN | aseguramiento.py |
| `/api/aseguramiento/sgd/listado` | GET | AUTENTICADO | aseguramiento.py |
| `/api/aseguramiento/validacion-equipos` | GET,POST | AUTENTICADO | aseguramiento.py |
| `/api/pqr/inbound` | POST | PÚBLICA | aseguramiento.py |
| `/api/reportes/audit-trail.csv` | GET | ADMIN | aseguramiento.py |
| `/aseguramiento` | GET | ADMIN | aseguramiento.py |
| `/aseguramiento/calibracion` | GET | AUTENTICADO | aseguramiento.py |
| `/api/auto-plan/aplicar` | POST | ADMIN | auto_plan.py |
| `/api/auto-plan/aplicar-aprendizaje` | POST | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/aprender-historico` | GET | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/asegurar-actualizado` | POST | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/configs/emails` | GET,POST | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/configs/emails/test` | POST | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/configs/mp` | GET,POST | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/configs/perfil-riesgo` | GET,POST | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/configs/sku` | GET | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/configs/sku/<int:config_id>` | PUT | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/cron/state` | GET | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/cron/toggle` | POST | ADMIN | auto_plan.py |
| `/api/auto-plan/ejecutar-ahora` | POST | ADMIN | auto_plan.py |
| `/api/auto-plan/preview` | GET | AUTENTICADO | auto_plan.py |
| `/api/auto-plan/runs` | GET | AUTENTICADO | auto_plan.py |
| `/api/conteo-ciclico/<int:item_id>/registrar` | POST | AUTENTICADO | auto_plan.py |
| `/api/conteo-ciclico/calendario` | GET | AUTENTICADO | auto_plan.py |
| `/api/conteo-ciclico/configs` | GET,POST | AUTENTICADO | auto_plan.py |
| `/api/maquila/clientes` | GET,POST | AUTENTICADO | auto_plan.py |
| `/api/maquila/pedidos` | GET,POST | AUTENTICADO | auto_plan.py |
| `/api/maquila/pedidos/<int:pedido_id>` | DELETE | AUTENTICADO | auto_plan.py |
| `/api/maquila/pedidos/<int:pedido_id>/asignar-produccion` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/accion-rapida` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/alerta-d20-pendientes` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/alerta-etiquetas-pendientes` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/alertas-calendar` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/andon` | GET,POST | ADMIN | auto_plan.py |
| `/api/planta/andon/<int:aid>/resolver` | POST | ADMIN | auto_plan.py |
| `/api/planta/areas/<int:area_id>/marcar-limpia-con-despeje` | POST | ADMIN | auto_plan.py |
| `/api/planta/asignacion-semanal` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/asignar-operarios-bulk` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/auditor-semanal-enviar` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/auditor-semanal-preview` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/auditoria-calendar` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/auditoria-sorpresa-pdf` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/auto-d20-cron` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/auto-sc-generar` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/auto-sc-mee-generar` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/auto-sc-mee-preview` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/auto-sc-mee-status` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/auto-sc-preview` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/auto-sc-status` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/calendar-debug` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/calendar-eventos-plan` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/confirmar-proyeccion` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/cron-jobs-status` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/desbloquear-produccion/<int:pid>` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/detectar-cambios-demanda` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/diagnostico-calendar` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/diagnostico-sku` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/dossier-lote/<lote>` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/ejecutar-lunes-7am` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/estado-solicitudes` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/forecast` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/forecast-black-friday` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/forzar-sync-semana` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/health-check` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/items-por-asignar` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/kanban-eta` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/kpi-cobertura` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/mass-balance/<int:pid>` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/mee-config` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/mee-config/<path:codigo>` | PUT | AUTENTICADO | auto_plan.py |
| `/api/planta/mp-para-lote` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/mp-rolling-forecast` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/normalizar-mee` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/oee` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/plan-largo-shopify` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/plan-semana-shopify` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/plan-semanal-v2` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/plan/exportar` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/pre-produccion-equipo` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/prediccion-demanda` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/produccion/<int:pid>/granel-aprobar` | POST | ADMIN | auto_plan.py |
| `/api/planta/produccion/<int:prod_id>/aceptar-recomendacion` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/produccion/<int:prod_id>/asignar-operarios-auto` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/produccion/<int:prod_id>/editar-lote` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/produccion/<int:prod_id>/eliminar-y-replanificar` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/producto-nuevo` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/reasignar-ia` | POST | ADMIN | auto_plan.py |
| `/api/planta/reasignar-operarios-conflictos` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/recomendaciones` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/reporte-ejecutivo` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/sc-d20-rapida` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/sc-etiqueta-rapida` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/sc-mee-asignar` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/scs-pedidas-resumen` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/self-heal` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/semana-produccion` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/sku-mee-config` | GET | AUTENTICADO | auto_plan.py |
| `/api/planta/sku-mee-config` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/sku-mee-config/<int:mid>` | DELETE,PUT | AUTENTICADO | auto_plan.py |
| `/api/planta/sku/<int:sku_id>/estado` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/sync-shopify-cron` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/tablero-equipo` | GET | PLANTA | auto_plan.py |
| `/api/planta/tablero-kanban` | GET | PLANTA | auto_plan.py |
| `/api/planta/tablero-kanban/<int:pid>/etapa/<rol>/<accion>` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/tiempos-objetivo` | GET,POST | AUTENTICADO | auto_plan.py |
| `/api/planta/tiempos-objetivo/recalcular-historico` | POST | ADMIN | auto_plan.py |
| `/api/planta/unificar-hermanos-skus` | POST | AUTENTICADO | auto_plan.py |
| `/api/planta/validar-hermanos-skus` | GET | AUTENTICADO | auto_plan.py |
| `/api/recepcion/ocr-etiqueta` | POST | AUTENTICADO | auto_plan.py |
| `/planta/despeje-linea` | GET | AUTENTICADO | auto_plan.py |
| `/planta/kanban` | GET | AUTENTICADO | auto_plan.py |
| `/api/bienestar/capacitaciones` | GET,POST | AUTENTICADO | bienestar.py |
| `/api/bienestar/capacitaciones/<int:cid>/iniciar-examen` | POST | AUTENTICADO | bienestar.py |
| `/api/bienestar/empleado-trimestral` | GET | AUTENTICADO | bienestar.py |
| `/api/bienestar/historial/<usuario>` | GET | AUTENTICADO | bienestar.py |
| `/api/bienestar/intentos/<int:int_id>/calificar` | POST | AUTENTICADO | bienestar.py |
| `/api/bienestar/notificaciones` | GET,POST | AUTENTICADO | bienestar.py |
| `/api/bienestar/notificaciones/<int:nid>/resolver` | POST | AUTENTICADO | bienestar.py |
| `/api/publico/empleado-reporte` | POST | AUTENTICADO | bienestar.py |
| `/bienestar` | GET | AUTENTICADO | bienestar.py |
| `/reportar` | GET | PÚBLICA | bienestar.py |
| `/admin/cargar-instructivo` | GET | CALIDAD+ADMIN | brd.py |
| `/admin/planta-demo` | GET | ADMIN | brd.py |
| `/api/admin/planta-demo/crear` | POST | ADMIN | brd.py |
| `/api/brd/analitica-lotes` | GET | ADMIN | brd.py |
| `/api/brd/bandeja-dt` | GET | ADMIN | brd.py |
| `/api/brd/cleaning` | POST | AUTENTICADO | brd.py |
| `/api/brd/cleaning` | GET | AUTENTICADO | brd.py |
| `/api/brd/cleaning/<int:cl_id>/completar` | POST | AUTENTICADO | brd.py |
| `/api/brd/cleaning/<int:cl_id>/validar` | POST | CALIDAD+ADMIN | brd.py |
| `/api/brd/cleaning/equipo/<equipo>/ultima` | GET | AUTENTICADO | brd.py |
| `/api/brd/cuarentena-explicita` | GET | AUTENTICADO | brd.py |
| `/api/brd/dashboard-estados` | GET | AUTENTICADO | brd.py |
| `/api/brd/demo-legajo` | POST | AUTENTICADO | brd.py |
| `/api/brd/ebr` | POST | AUTENTICADO | brd.py |
| `/api/brd/ebr` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/ajustes-mp` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/ajustes-mp` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/aprobar-dt` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/artes` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/artes` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/artes/<int:arte_id>/aprobar` | POST | ADMIN | brd.py |
| `/api/brd/ebr/<int:ebr_id>/asignar-lote-fisico` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/audit` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/cerrar-acondicionamiento` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/cerrar-envasado` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/completar` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/conciliacion-material` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/conciliacion-material` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/correcciones` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/correcciones` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/descartar` | POST | ADMIN | brd.py |
| `/api/brd/ebr/<int:ebr_id>/despeje` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/despeje` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/despeje-item` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/despeje-items` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/despeje-verificar` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/envases-plan` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/firmar-rapido` | POST | ADMIN | brd.py |
| `/api/brd/ebr/<int:ebr_id>/habilitar-envasado` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/ipc-estandar` | GET,POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/ipc-resultados` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/ipc-resultados` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/liberar` | POST | CALIDAD+ADMIN | brd.py |
| `/api/brd/ebr/<int:ebr_id>/material-envase` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/material-envase/<int:row_id>` | DELETE | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/observaciones` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/observaciones` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/pasos/<int:orden>/completar` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/pasos/<int:orden>/iniciar` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/pdf` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/pesajes` | POST | ADMIN | brd.py |
| `/api/brd/ebr/<int:ebr_id>/pesajes` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/pesajes-plan` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/pesajes/<int:pesaje_id>/verificar` | POST | ADMIN | brd.py |
| `/api/brd/ebr/<int:ebr_id>/precauciones` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/precauciones` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/presentacion` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/presentacion/<int:row_id>` | DELETE | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/produccion-id` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/rechazar` | POST | CALIDAD+ADMIN | brd.py |
| `/api/brd/ebr/<int:ebr_id>/reconciliacion` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/registrar-unidades` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/registros-fisicos` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/registros-fisicos` | POST | EJECUTOR DE LOTE | brd.py |
| `/api/brd/ebr/<int:ebr_id>/registros-fisicos/<int:rid>/pdf` | GET | AUTENTICADO | brd.py |
| `/api/brd/ebr/<int:ebr_id>/vista-completa` | GET | ADMIN | brd.py |
| `/api/brd/envase-opciones` | GET | AUTENTICADO | brd.py |
| `/api/brd/legajo-rapido` | POST | AUTENTICADO | brd.py |
| `/api/brd/limpiar-demos` | POST | AUTENTICADO | brd.py |
| `/api/brd/lote/<lote>/fases` | GET | AUTENTICADO | brd.py |
| `/api/brd/mbr` | GET | AUTENTICADO | brd.py |
| `/api/brd/mbr` | POST | AUTENTICADO | brd.py |
| `/api/brd/mbr-desactualizados` | GET | AUTENTICADO | brd.py |
| `/api/brd/mbr/<int:mbr_id>` | GET | AUTENTICADO | brd.py |
| `/api/brd/mbr/<int:mbr_id>` | PATCH | AUTENTICADO | brd.py |
| `/api/brd/mbr/<int:mbr_id>/aprobar` | POST | CALIDAD+ADMIN | brd.py |
| `/api/brd/mbr/<int:mbr_id>/aprobar-rapido` | POST | CALIDAD+ADMIN | brd.py |
| `/api/brd/mbr/<int:mbr_id>/imprimible` | GET | AUTENTICADO | brd.py |
| `/api/brd/mbr/<int:mbr_id>/ipc-specs` | GET | AUTENTICADO | brd.py |
| `/api/brd/mbr/<int:mbr_id>/ipc-specs` | POST | AUTENTICADO | brd.py |
| `/api/brd/mbr/<int:mbr_id>/ipc-specs/<int:spec_id>` | DELETE | AUTENTICADO | brd.py |
| `/api/brd/mbr/<int:mbr_id>/obsoletar` | POST | CALIDAD+ADMIN | brd.py |
| `/api/brd/mbr/<int:mbr_id>/pasos` | POST | AUTENTICADO | brd.py |
| `/api/brd/mbr/<int:mbr_id>/pasos/<int:paso_id>` | PATCH | AUTENTICADO | brd.py |
| `/api/brd/mbr/<int:mbr_id>/pasos/<int:paso_id>` | DELETE | AUTENTICADO | brd.py |
| `/api/brd/mbr/<int:mbr_id>/submit` | POST | ADMIN | brd.py |
| `/api/brd/mbr/aprobar-todas` | POST | CALIDAD+ADMIN | brd.py |
| `/api/brd/mbr/aprobar-todos-instructivos` | GET,POST | CALIDAD+ADMIN | brd.py |
| `/api/brd/mbr/cargar-instructivo` | POST | CALIDAD+ADMIN | brd.py |
| `/api/brd/mbr/cargar-todos-instructivos` | GET,POST | CALIDAD+ADMIN | brd.py |
| `/api/brd/mbr/generar-desde-formula` | POST | ADMIN | brd.py |
| `/api/brd/mbr/generar-todas-desde-formulas` | POST | ADMIN | brd.py |
| `/api/brd/mbr/por-producto` | GET | AUTENTICADO | brd.py |
| `/api/brd/mbr/preparar-aprobado` | POST | ADMIN | brd.py |
| `/api/brd/mbr/sync-procedimiento` | POST | ADMIN | brd.py |
| `/api/brd/mi-trabajo` | GET | AUTENTICADO | brd.py |
| `/api/brd/ordenes-unificadas` | GET | AUTENTICADO | brd.py |
| `/api/brd/revincular-mbr` | POST | CALIDAD+ADMIN | brd.py |
| `/brd` | GET | AUTENTICADO | brd.py |
| `/brd/` | GET | AUTENTICADO | brd.py |
| `/brd/despeje/<int:ebr_id>` | GET | AUTENTICADO | brd.py |
| `/brd/dispensado/<int:ebr_id>` | GET | AUTENTICADO | brd.py |
| `/brd/timeline/<int:ebr_id>` | GET | AUTENTICADO | brd.py |
| `/planta/activar-legajos` | GET | ADMIN | brd.py |
| `/planta/analitica-batch` | GET | AUTENTICADO | brd.py |
| `/planta/bandeja-dt` | GET | AUTENTICADO | brd.py |
| `/planta/instrucciones-acondicionamiento/<int:ebr_id>` | GET | AUTENTICADO | brd.py |
| `/planta/instrucciones-envasado/<int:ebr_id>` | GET | AUTENTICADO | brd.py |
| `/planta/legajo-acondicionamiento/<int:ebr_id>` | GET | AUTENTICADO | brd.py |
| `/planta/legajo-envasado/<int:ebr_id>` | GET | AUTENTICADO | brd.py |
| `/planta/orden/<int:ebr_id>` | GET | AUTENTICADO | brd.py |
| `/planta/ordenes-produccion` | GET | AUTENTICADO | brd.py |
| `/api/calidad/agua/estado-hoy` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/agua/exportar-csv` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/agua/registros` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/agua/tendencia` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/archivar-r2` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/auditorias` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/bandeja` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/calibraciones` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/capa` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/capa/<int:cid>` | PATCH | AUTENTICADO | calidad.py |
| `/api/calidad/certificado-analisis` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/certificado-analisis/imprimible` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/coa` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/coa-pt/<path:lote>/imprimible` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/coa/lote/<path:lote>` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/config/micro-gate` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/cronograma` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/cronograma/completar` | POST | AUTENTICADO | calidad.py |
| `/api/calidad/cronograma/iniciar` | POST | AUTENTICADO | calidad.py |
| `/api/calidad/cronograma/resumen` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/dashboard` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/equipos/<path:codigo>/hoja-vida` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/equipos/<path:codigo>/registrar-evento` | POST | ASEGURAMIENTO | calidad.py |
| `/api/calidad/equipos/cronograma` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/equipos/cronograma/<int:cron_id>/completar` | POST | ASEGURAMIENTO | calidad.py |
| `/api/calidad/equipos/dashboard` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/equipos/importar-cronograma` | POST | ADMIN | calidad.py |
| `/api/calidad/especificaciones` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/especificaciones/<int:eid>` | DELETE,PATCH | AUTENTICADO | calidad.py |
| `/api/calidad/estabilidades` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/expediente-lote` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/fisicoquimica/resultados` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/genealogia-pt/<path:lote>` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/indicadores` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/indicadores/metas/<codigo>` | PATCH | AUTENTICADO | calidad.py |
| `/api/calidad/lotes-planta` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/micro/alertas` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/micro/analisis` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/micro/coa/<path:fname>` | GET | ADMIN | calidad.py |
| `/api/calidad/micro/heatmap` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/micro/importar-eml` | POST | AUTENTICADO | calidad.py |
| `/api/calidad/micro/resultados` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/micro/specs` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/no-conformidades` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/no-conformidades/<int:ncid>/cerrar` | POST | ADMIN | calidad.py |
| `/api/calidad/oos` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/oos/<int:oos_id>` | PATCH | ADMIN | calidad.py |
| `/api/calidad/recepcion-pipeline` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/recepcion-tecnica` | GET,POST | AUTENTICADO | calidad.py |
| `/api/calidad/recepcion-tecnica/imprimible` | GET | AUTENTICADO | calidad.py |
| `/api/calidad/reconstruir-expediente` | GET,POST | AUTENTICADO | calidad.py |
| `/calidad` | GET | CALIDAD | calidad.py |
| `/calidad/expediente` | GET | AUTENTICADO | calidad.py |
| `/calidad/genealogia` | GET | AUTENTICADO | calidad.py |
| `/api/chat/heartbeat` | POST | AUTENTICADO | chat.py |
| `/api/chat/messages/<int:message_id>` | DELETE,PATCH | AUTENTICADO | chat.py |
| `/api/chat/messages/<int:message_id>/react` | DELETE,POST | AUTENTICADO | chat.py |
| `/api/chat/search` | GET | AUTENTICADO | chat.py |
| `/api/chat/threads` | GET,POST | ADMIN | chat.py |
| `/api/chat/threads/<int:thread_id>/asignar-tarea` | POST | AUTENTICADO | chat.py |
| `/api/chat/threads/<int:thread_id>/leer` | POST | AUTENTICADO | chat.py |
| `/api/chat/threads/<int:thread_id>/messages` | GET,POST | AUTENTICADO | chat.py |
| `/api/chat/threads/<int:thread_id>/miembros` | POST | AUTENTICADO | chat.py |
| `/api/chat/unread-summary` | GET | AUTENTICADO | chat.py |
| `/api/chat/users` | GET | AUTENTICADO | chat.py |
| `/api/chat/widget.js` | GET | AUTENTICADO | chat.py |
| `/chat` | GET | AUTENTICADO | chat.py |
| `/api/aliados/<int:cid>` | PATCH | AUTENTICADO | clientes.py |
| `/api/aliados/<int:cid>` | DELETE | ADMIN | clientes.py |
| `/api/aliados/analytics` | GET | AUTENTICADO | clientes.py |
| `/api/aliados/canal-salud` | GET | AUTENTICADO | clientes.py |
| `/api/aliados/scores` | GET | AUTENTICADO | clientes.py |
| `/api/aliados/skus-segmento` | GET | AUTENTICADO | clientes.py |
| `/api/clientes` | GET,POST | AUTENTICADO | clientes.py |
| `/api/clientes/<int:cid>` | GET,PUT | AUTENTICADO | clientes.py |
| `/api/clientes/<int:cid>/ficha360` | GET | AUTENTICADO | clientes.py |
| `/api/clientes/<int:cid>/historial` | GET | AUTENTICADO | clientes.py |
| `/api/clientes/<int:cid>/stats` | GET | AUTENTICADO | clientes.py |
| `/api/clientes/alertas-recompra` | GET | AUTENTICADO | clientes.py |
| `/api/clientes/cartera` | GET | AUTENTICADO | clientes.py |
| `/api/despachos` | GET,POST | AUTENTICADO | clientes.py |
| `/api/pedidos` | GET,POST | AUTENTICADO | clientes.py |
| `/api/pedidos/<numero>` | DELETE,GET,PATCH | ADMIN | clientes.py |
| `/api/stock-pt` | GET,POST | AUTENTICADO | clientes.py |
| `/clientes` | GET | AUTENTICADO | clientes.py |
| `/api/comercial/maquila` | GET,POST | ADMIN | comercial.py |
| `/api/comercial/maquila/<int:mid>` | PATCH | AUTENTICADO | comercial.py |
| `/api/eos/leads` | GET | AUTENTICADO | comercial.py |
| `/api/eos/leads/<int:lid>` | PATCH | AUTENTICADO | comercial.py |
| `/api/eos/leads/webhook` | POST | AUTENTICADO | comercial.py |
| `/comercial` | GET | AUTENTICADO | comercial.py |
| `/api/compliance/capa` | GET,POST | AUTENTICADO | compliance.py |
| `/api/compliance/capa/<int:cid>` | PATCH | AUTENTICADO | compliance.py |
| `/api/compliance/cronogramas` | GET | AUTENTICADO | compliance.py |
| `/api/compliance/cronogramas/<int:cron_id>/ejecuciones` | GET,POST | AUTENTICADO | compliance.py |
| `/api/compliance/ejecuciones/<int:ej_id>/cumplir` | POST | AUTENTICADO | compliance.py |
| `/api/compliance/hallazgos` | GET,POST | AUTENTICADO | compliance.py |
| `/api/compliance/hallazgos/<int:hid>` | PATCH | AUTENTICADO | compliance.py |
| `/api/compliance/kpis` | GET | AUTENTICADO | compliance.py |
| `/compliance` | GET | AUTENTICADO | compliance.py |
| `/api/admin/proveedores-dedup-nombre` | POST | COMPRAS | compras.py |
| `/api/admin/proveedores-duplicados` | GET | AUTENTICADO | compras.py |
| `/api/admin/proveedores-fusionar` | POST | COMPRAS | compras.py |
| `/api/alertas-mee` | GET | AUTENTICADO | compras.py |
| `/api/compras/alertas-vivas` | GET | AUTENTICADO | compras.py |
| `/api/compras/buscar-remision/<remision_code>` | GET | AUTENTICADO | compras.py |
| `/api/compras/cargos-fijos` | GET | AUTENTICADO | compras.py |
| `/api/compras/cargos-fijos` | POST | COMPRAS | compras.py |
| `/api/compras/cargos-fijos/<int:cid>/toggle` | POST | COMPRAS | compras.py |
| `/api/compras/cargos-fijos/pago/<int:pid>/monto` | POST | ADMIN | compras.py |
| `/api/compras/cargos-fijos/pago/<int:pid>/pagar` | POST | ADMIN | compras.py |
| `/api/compras/cash-flow` | GET | AUTENTICADO | compras.py |
| `/api/compras/centros-costos` | GET | AUTENTICADO | compras.py |
| `/api/compras/coa-download/<path:filename>` | GET | AUTENTICADO | compras.py |
| `/api/compras/coa-upload` | POST | ADMIN | compras.py |
| `/api/compras/consolidado-proveedor` | GET | FINANZAS | compras.py |
| `/api/compras/consolidar-auto-pendientes` | POST | COMPRAS | compras.py |
| `/api/compras/consumibles` | GET,POST | AUTENTICADO | compras.py |
| `/api/compras/consumibles/<int:cid>` | DELETE,PATCH | AUTENTICADO | compras.py |
| `/api/compras/consumos/tendencia` | GET | AUTENTICADO | compras.py |
| `/api/compras/cotizaciones/<int:cot_id>` | PATCH | COMPRAS | compras.py |
| `/api/compras/cotizaciones/<int:cot_id>/elegir-ganadora` | POST | COMPRAS | compras.py |
| `/api/compras/cotizaciones/candidatos` | GET | AUTENTICADO | compras.py |
| `/api/compras/cotizaciones/desde-grupo` | POST | COMPRAS | compras.py |
| `/api/compras/cotizaciones/rondas` | POST | COMPRAS | compras.py |
| `/api/compras/cotizaciones/rondas` | GET | AUTENTICADO | compras.py |
| `/api/compras/cotizaciones/rondas/<ronda_id>` | GET | AUTENTICADO | compras.py |
| `/api/compras/dashboard-ejecutivo` | GET | AUTENTICADO | compras.py |
| `/api/compras/dashboard-home` | GET | ADMIN | compras.py |
| `/api/compras/discrepancias` | GET | AUTENTICADO | compras.py |
| `/api/compras/facturas-proveedor` | GET | AUTENTICADO | compras.py |
| `/api/compras/facturas-proveedor` | POST | AUTENTICADO | compras.py |
| `/api/compras/facturas-proveedor/<int:fid>` | GET | AUTENTICADO | compras.py |
| `/api/compras/facturas-proveedor/<int:fid>` | PATCH | AUTENTICADO | compras.py |
| `/api/compras/facturas-proveedor/<int:fid>/pagar` | POST | AUTENTICADO | compras.py |
| `/api/compras/facturas-proveedor/<int:fid>/pdf` | GET | AUTENTICADO | compras.py |
| `/api/compras/fast-track-config` | GET | AUTENTICADO | compras.py |
| `/api/compras/fast-track-config` | POST | ADMIN | compras.py |
| `/api/compras/fast-track-config/<int:config_id>` | DELETE | ADMIN | compras.py |
| `/api/compras/feed-necesidades` | GET | AUTENTICADO | compras.py |
| `/api/compras/influencer/limpiar-no-pagadas` | GET,POST | ADMIN | compras.py |
| `/api/compras/limpiar-solicitudes-planta` | POST | COMPRAS | compras.py |
| `/api/compras/limpiar-y-regenerar-auto-plan` | POST | ADMIN | compras.py |
| `/api/compras/mailbox-facturas` | GET | AUTENTICADO | compras.py |
| `/api/compras/mailbox-facturas/<int:pago_id>/completar` | POST | COMPRAS | compras.py |
| `/api/compras/mailbox-facturas/<int:pago_id>/comprobante` | GET | AUTENTICADO | compras.py |
| `/api/compras/mailbox-facturas/<int:pago_id>/descartar` | POST | COMPRAS | compras.py |
| `/api/compras/oc-desde-solicitudes` | POST | COMPRAS | compras.py |
| `/api/compras/oc/<numero_oc>/rechazar` | POST | AUTENTICADO | compras.py |
| `/api/compras/oc/<numero_oc>/reparar-desde-solicitud` | POST | AUTENTICADO | compras.py |
| `/api/compras/ocr-factura` | POST | AUTENTICADO | compras.py |
| `/api/compras/ocs-atrasadas` | GET | AUTENTICADO | compras.py |
| `/api/compras/ocs-consolidado-excel` | GET | FINANZAS | compras.py |
| `/api/compras/ordenes-compra/<numero_oc>/aplicar-saldo` | POST | AUTENTICADO | compras.py |
| `/api/compras/ordenes-servicio` | GET,POST | AUTENTICADO | compras.py |
| `/api/compras/ordenes-servicio/<numero_os>` | GET | AUTENTICADO | compras.py |
| `/api/compras/ordenes-servicio/<numero_os>/estado` | PATCH | ADMIN | compras.py |
| `/api/compras/pagos` | GET | AUTENTICADO | compras.py |
| `/api/compras/pagos-excel` | GET | AUTENTICADO | compras.py |
| `/api/compras/pagos-kpis` | GET | AUTENTICADO | compras.py |
| `/api/compras/por-pagar` | GET | FINANZAS | compras.py |
| `/api/compras/prediccion-demanda` | GET | AUTENTICADO | compras.py |
| `/api/compras/proveedor-recomendado/<path:codigo_mp>` | GET | COMPRAS | compras.py |
| `/api/compras/proveedor-saldo/registrar` | POST | AUTENTICADO | compras.py |
| `/api/compras/proveedor-scorecard/<nombre_prov>` | GET | AUTENTICADO | compras.py |
| `/api/compras/recepciones-discrepancias` | GET | AUTENTICADO | compras.py |
| `/api/compras/reporte-ejecutivo` | GET | AUTENTICADO | compras.py |
| `/api/compras/roi-proveedores` | GET | AUTENTICADO | compras.py |
| `/api/compras/saldos-favor` | GET | AUTENTICADO | compras.py |
| `/api/compras/solicitudes-agrupadas-por-proveedor` | GET | AUTENTICADO | compras.py |
| `/api/compras/solicitudes/pdf` | GET | AUTENTICADO | compras.py |
| `/api/compras/sugerir-mp-bulk` | POST | AUTENTICADO | compras.py |
| `/api/compras/sugerir-mp/<path:codigo_mp>` | GET | AUTENTICADO | compras.py |
| `/api/compras/trazabilidad-item` | GET | AUTENTICADO | compras.py |
| `/api/compras/trazabilidad-oc/<numero_oc>` | GET | AUTENTICADO | compras.py |
| `/api/compras/validar-precios-bulk` | POST | AUTENTICADO | compras.py |
| `/api/compras/vigilancia-precios` | GET | FINANZAS | compras.py |
| `/api/comprobantes-pago` | GET | COMPRAS | compras.py |
| `/api/comprobantes-pago/<int:comp_id>/email` | POST | AUTENTICADO | compras.py |
| `/api/comprobantes-pago/<int:comp_id>/pdf` | GET | COMPRAS | compras.py |
| `/api/comprobantes-pago/<int:comp_id>/regenerar` | POST | ADMIN | compras.py |
| `/api/comprobantes-pago/oc/<numero_oc>` | GET | AUTENTICADO | compras.py |
| `/api/comprobantes-pago/regenerar-legacy` | POST | ADMIN | compras.py |
| `/api/dashboard-stats` | GET | AUTENTICADO | compras.py |
| `/api/generar-oc-automatica` | POST | AUTENTICADO | compras.py |
| `/api/mee` | GET | COMPRAS | compras.py |
| `/api/mee/<codigo>` | GET,PUT | COMPRAS | compras.py |
| `/api/mee/<codigo>/ajuste` | POST | COMPRAS | compras.py |
| `/api/movimientos-mee` | GET,POST | AUTENTICADO | compras.py |
| `/api/movimientos-mee/lote` | POST | AUTENTICADO | compras.py |
| `/api/ordenes-compra` | GET,POST | COMPRAS | compras.py |
| `/api/ordenes-compra/<numero_oc>` | DELETE,GET,PUT | ADMIN | compras.py |
| `/api/ordenes-compra/<numero_oc>/autorizar` | PATCH | AUTENTICADO | compras.py |
| `/api/ordenes-compra/<numero_oc>/cambiar-proveedor` | POST | COMPRAS | compras.py |
| `/api/ordenes-compra/<numero_oc>/comprobante` | GET | AUTENTICADO | compras.py |
| `/api/ordenes-compra/<numero_oc>/editar` | PATCH | ADMIN | compras.py |
| `/api/ordenes-compra/<numero_oc>/items` | POST | ADMIN | compras.py |
| `/api/ordenes-compra/<numero_oc>/items-precios` | PATCH | COMPRAS | compras.py |
| `/api/ordenes-compra/<numero_oc>/items/<int:item_id>` | DELETE,PATCH | COMPRAS | compras.py |
| `/api/ordenes-compra/<numero_oc>/pagar` | PATCH | MARKETING | compras.py |
| `/api/ordenes-compra/<numero_oc>/pagos` | GET | AUTENTICADO | compras.py |
| `/api/ordenes-compra/<numero_oc>/proveedor` | PATCH | COMPRAS | compras.py |
| `/api/ordenes-compra/<numero_oc>/recibir` | POST | ADMIN | compras.py |
| `/api/ordenes-compra/<numero_oc>/revertir-pago` | POST | ADMIN | compras.py |
| `/api/ordenes-compra/<numero_oc>/revisar` | PATCH | ADMIN | compras.py |
| `/api/planta/ordenes-servicio` | GET | AUTENTICADO | compras.py |
| `/api/precio-historico/<path:codigo_mp>` | GET | AUTENTICADO | compras.py |
| `/api/proveedores-compras` | GET,POST | FINANZAS | compras.py |
| `/api/proveedores-compras/<path:nombre>` | DELETE,PATCH | ADMIN | compras.py |
| `/api/proveedores-compras/<path:nombre>/ficha` | GET | FINANZAS | compras.py |
| `/api/solicitudes-compra` | GET,POST | ADMIN | compras.py |
| `/api/solicitudes-compra/<numero>` | DELETE | ADMIN | compras.py |
| `/api/solicitudes-compra/<numero>` | GET | AUTENTICADO | compras.py |
| `/api/solicitudes-compra/<numero>/aprobar-influencer` | POST | ADMIN | compras.py |
| `/api/solicitudes-compra/<numero>/estado` | PATCH | COMPRAS | compras.py |
| `/api/solicitudes-compra/<numero>/items` | PATCH | COMPRAS | compras.py |
| `/api/solicitudes-compra/<numero>/items/<int:item_id>` | DELETE | COMPRAS | compras.py |
| `/api/solicitudes-compra/<numero>/marcar-recibido-solicitante` | POST | ADMIN | compras.py |
| `/api/solicitudes-compra/<numero>/observaciones` | PUT | COMPRAS | compras.py |
| `/api/solicitudes-compra/<numero>/rechazar` | POST | ADMIN | compras.py |
| `/api/solicitudes-compra/<numero>/split` | POST | COMPRAS | compras.py |
| `/api/solicitudes-compra/mis` | GET | ADMIN | compras.py |
| `/compras/consumos` | GET | AUTENTICADO | compras.py |
| `/compras/discrepancias` | GET | AUTENTICADO | compras.py |
| `/planta/ordenes-servicio` | GET | AUTENTICADO | compras.py |
| `/solicitudes` | GET | AUTENTICADO | compras.py |
| `/api/comunicacion/actas` | GET,POST | AUTENTICADO | comunicacion.py |
| `/api/comunicacion/actas/<int:aid>/parsear` | POST | AUTENTICADO | comunicacion.py |
| `/api/comunicacion/areas` | GET | AUTENTICADO | comunicacion.py |
| `/api/comunicacion/mensajes` | GET,POST | AUTENTICADO | comunicacion.py |
| `/api/comunicacion/mensajes/<int:mid>/leido` | POST | AUTENTICADO | comunicacion.py |
| `/api/comunicacion/mensajes/no-leidos` | GET | AUTENTICADO | comunicacion.py |
| `/api/comunicacion/quejas` | GET,POST | ADMIN | comunicacion.py |
| `/api/comunicacion/quejas/<int:qid>/resolver` | POST | AUTENTICADO | comunicacion.py |
| `/api/comunicacion/tareas` | GET,POST | AUTENTICADO | comunicacion.py |
| `/api/comunicacion/tareas/<int:tid>` | DELETE,GET,PATCH | AUTENTICADO | comunicacion.py |
| `/api/comunicacion/tareas/<int:tid>/asignar-area` | POST | AUTENTICADO | comunicacion.py |
| `/api/comunicacion/tareas/<int:tid>/avance` | POST | AUTENTICADO | comunicacion.py |
| `/comunicacion` | GET | AUTENTICADO | comunicacion.py |
| `/api/contabilidad/export/siigo` | GET | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/facturas` | GET | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/facturas/<numero>/anular` | PATCH | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/facturas/<numero>/pago` | POST | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/facturas/<numero>/pdf` | GET | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/facturas/generar` | POST | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/kpis` | GET | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/login` | POST | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/logout` | POST | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/me` | GET | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/nomina` | GET | AUTENTICADO | contabilidad.py |
| `/api/contabilidad/tesoreria` | GET | AUTENTICADO | contabilidad.py |
| `/contabilidad` | GET | PÚBLICA | contabilidad.py |
| `/` | GET | AUTENTICADO | core.py |
| `/admin/influencers` | GET | ADMIN | core.py |
| `/admin/usuarios` | GET | ADMIN | core.py |
| `/animus` | GET | AUTENTICADO | core.py |
| `/api/admin/usuarios` | GET | AUTENTICADO | core.py |
| `/api/admin/usuarios` | POST | AUTENTICADO | core.py |
| `/api/admin/usuarios/<username>` | PATCH | AUTENTICADO | core.py |
| `/api/admin/usuarios/<username>/reset-password` | POST | AUTENTICADO | core.py |
| `/api/cambiar-password` | POST | AUTENTICADO | core.py |
| `/api/csrf-token` | GET | PÚBLICA | core.py |
| `/api/health/debug` | GET | PÚBLICA | core.py |
| `/asignar-areas` | GET | AUTENTICADO | core.py |
| `/cambiar-password` | GET | AUTENTICADO | core.py |
| `/compras` | GET | ADMIN | core.py |
| `/hub` | GET | AUTENTICADO | core.py |
| `/inventarios` | GET | ADMIN | core.py |
| `/login` | GET,POST | PÚBLICA | core.py |
| `/logout` | GET | PÚBLICA | core.py |
| `/marketing` | GET | AUTENTICADO | core.py |
| `/modulos` | GET | ADMIN | core.py |
| `/planta` | GET | ADMIN | core.py |
| `/planta-app.js` | GET | PÚBLICA | core.py |
| `/planta-core.js` | GET | PÚBLICA | core.py |
| `/programacion-areas` | GET | AUTENTICADO | core.py |
| `/programacion-comparar` | GET | AUTENTICADO | core.py |
| `/api/recepcion/aprobar-lote` | POST | ASEGURAMIENTO | despachos.py |
| `/api/recepcion/detalle/<numero_oc>` | GET | AUTENTICADO | despachos.py |
| `/api/recepcion/lotes-cuarentena` | GET | AUTENTICADO | despachos.py |
| `/api/recepcion/seguimiento` | GET | AUTENTICADO | despachos.py |
| `/api/recepcion/trazabilidad/<path:lote>` | GET | AUTENTICADO | despachos.py |
| `/recepcion` | GET | AUTENTICADO | despachos.py |
| `/api/comunicacion/dashboard` | GET | AUTENTICADO | espagiria.py |
| `/api/espagiria/alertas` | GET | AUTENTICADO | espagiria.py |
| `/api/espagiria/cartera-maquila` | GET | AUTENTICADO | espagiria.py |
| `/api/espagiria/clientes-maquila` | GET | AUTENTICADO | espagiria.py |
| `/api/espagiria/clientes-maquila/<int:cid>/360` | GET | AUTENTICADO | espagiria.py |
| `/api/espagiria/dashboard` | GET | AUTENTICADO | espagiria.py |
| `/api/espagiria/lab/en-vivo` | GET | AUTENTICADO | espagiria.py |
| `/api/espagiria/pedido-rapido` | POST | AUTENTICADO | espagiria.py |
| `/api/espagiria/quick-actions` | GET | AUTENTICADO | espagiria.py |
| `/api/espagiria/resumen-pre-comite` | GET | AUTENTICADO | espagiria.py |
| `/espagiria` | GET | AUTENTICADO | espagiria.py |
| `/api/financiero/ap-aging` | GET | AUTENTICADO | financiero.py |
| `/api/financiero/ar-aging` | GET | AUTENTICADO | financiero.py |
| `/api/financiero/categoria-trend` | GET | ADMIN | financiero.py |
| `/api/financiero/conciliacion-bancaria/preview` | POST | FINANZAS | financiero.py |
| `/api/financiero/config` | GET,POST | ADMIN | financiero.py |
| `/api/financiero/egresos` | GET,POST | ADMIN | financiero.py |
| `/api/financiero/flujo-mensual` | GET | ADMIN | financiero.py |
| `/api/financiero/importar-ocs` | POST | ADMIN | financiero.py |
| `/api/financiero/ingresos` | GET,POST | ADMIN | financiero.py |
| `/api/financiero/kpis` | GET | ADMIN | financiero.py |
| `/api/financiero/limpiar-flujo` | POST | ADMIN | financiero.py |
| `/api/financiero/mes-detalle` | GET | ADMIN | financiero.py |
| `/api/financiero/mom-12-meses` | GET | ADMIN | financiero.py |
| `/api/financiero/pnl` | GET | AUTENTICADO | financiero.py |
| `/api/financiero/pnl-por-empresa` | GET | FINANZAS | financiero.py |
| `/api/financiero/precios-mayorista` | GET | AUTENTICADO | financiero.py |
| `/api/financiero/precios-mayorista/<sku>` | POST | ADMIN | financiero.py |
| `/api/financiero/sync-shopify-ingresos` | POST | ADMIN | financiero.py |
| `/api/financiero/sync-shopify-status` | GET | ADMIN | financiero.py |
| `/api/financiero/working-capital` | GET | AUTENTICADO | financiero.py |
| `/financiero` | GET | ADMIN | financiero.py |
| `/api/sign` | POST | ADMIN | firmas.py |
| `/api/sign/<record_table>/<path:record_id>` | GET | AUTENTICADO | firmas.py |
| `/api/sign/challenge` | POST | AUTENTICADO | firmas.py |
| `/api/admin/cleanup-test-data` | POST | ADMIN | gerencia.py |
| `/api/admin/generate-hash` | POST | ADMIN | gerencia.py |
| `/api/admin/mee-set-stock` | POST | ADMIN | gerencia.py |
| `/api/admin/security-log` | GET | ADMIN | gerencia.py |
| `/api/admin/seed-mee-xlsx` | POST | ADMIN | gerencia.py |
| `/api/gerencia/aliados-feed` | GET | FINANZAS | gerencia.py |
| `/api/gerencia/dashboard-extra` | GET | FINANZAS | gerencia.py |
| `/api/gerencia/flujo-operacional` | GET | FINANZAS | gerencia.py |
| `/api/gerencia/input-manual` | POST | ADMIN | gerencia.py |
| `/api/gerencia/kpis` | GET | FINANZAS | gerencia.py |
| `/gerencia` | GET | ADMIN | gerencia.py |
| `/gerencia-financiero` | GET | FINANZAS | gerencia.py |
| `/api/centro/decisiones` | GET | ADMIN | hub.py |
| `/api/centro/operaciones` | GET | ADMIN | hub.py |
| `/api/compromisos` | GET,POST | AUTENTICADO | hub.py |
| `/api/compromisos/<int:cid>` | PATCH | AUTENTICADO | hub.py |
| `/api/compromisos/migrar-a-tareas` | POST | ADMIN | hub.py |
| `/api/health` | GET | PÚBLICA | hub.py |
| `/api/health` | GET | PÚBLICA | hub.py |
| `/api/hub/alertas` | GET | AUTENTICADO | hub.py |
| `/api/hub/resumen` | GET | FINANZAS | hub.py |
| `/api/ia/analizar-semana` | POST | ADMIN | hub.py |
| `/api/marketing/roi-campanas` | GET | AUTENTICADO | hub.py |
| `/api/notificaciones/centro` | GET | ADMIN | hub.py |
| `/api/notificaciones/count` | GET | AUTENTICADO | hub.py |
| `/api/reporte/semanal-ceo` | GET | ADMIN | hub.py |
| `/centro` | GET | ADMIN | hub.py |
| `/compromisos` | GET | AUTENTICADO | hub.py |
| `/hoy` | GET | ADMIN | hub.py |
| `/manifest.json` | GET | PÚBLICA | hub.py |
| `/sw.js` | GET | PÚBLICA | hub.py |
| `/tesoreria` | GET | ADMIN | hub.py |
| `/api/identidad` | GET | AUTENTICADO | identidad.py |
| `/api/identidad` | POST | ADMIN | identidad.py |
| `/api/identidad/<username>` | GET | AUTENTICADO | identidad.py |
| `/api/identidad/<username>` | PATCH | ADMIN | identidad.py |
| `/admin/system-health` | GET | ADMIN | index.py |
| `/api/admin/health-detailed` | GET | ADMIN | index.py |
| `/api/bandeja-ceo` | GET | ADMIN | index.py |
| `/api/email-status` | GET | ADMIN | index.py |
| `/api/health` | GET | PÚBLICA | index.py |
| `/diag/abastecimiento-mp/<path:codigo>` | GET | ADMIN | index.py |
| `/diag/animus-calc/<path:producto>` | GET | ADMIN | index.py |
| `/diag/azh-mig-status` | GET | ADMIN | index.py |
| `/diag/cadena-producto/<path:producto>` | GET | ADMIN | index.py |
| `/diag/envasado-estado` | GET | ADMIN | index.py |
| `/diag/formula-batch-preview/<path:producto>` | GET | ADMIN | index.py |
| `/diag/formula/<path:producto>` | GET | ADMIN | index.py |
| `/diag/formulas-dump` | GET | ADMIN | index.py |
| `/diag/huerfanos-actuales` | GET | ADMIN | index.py |
| `/diag/maestro-dump` | GET | ADMIN | index.py |
| `/diag/maestro-duplicados-inci` | GET | ADMIN | index.py |
| `/diag/maestro-inci-preview` | GET | ADMIN | index.py |
| `/diag/maestro-mnemonicos` | GET | ADMIN | index.py |
| `/diag/matriz-batch` | GET | ADMIN | index.py |
| `/diag/mbr-producto/<path:producto>` | GET | ADMIN | index.py |
| `/diag/producto-ventas/<path:producto>` | GET | ADMIN | index.py |
| `/diag/productos-sin-sku` | GET | ADMIN | index.py |
| `/diag/sku-buscar` | GET | ADMIN | index.py |
| `/healthz` | GET | PÚBLICA | index.py |
| `/mi-bandeja` | GET | ADMIN | index.py |
| `/admin/conteo-rescate` | GET | CALIDAD | inventario.py |
| `/admin/corregir-colisiones` | GET | ADMIN | inventario.py |
| `/admin/descuento-retroactivo` | GET | ADMIN | inventario.py |
| `/admin/envases-10ml-sueros` | GET | AUTENTICADO | inventario.py |
| `/admin/envases-recatalogo` | GET | AUTENTICADO | inventario.py |
| `/admin/importar-conteo` | GET | ADMIN | inventario.py |
| `/admin/liberar-cuarentena` | GET | ADMIN | inventario.py |
| `/admin/mp-bridges` | GET | ADMIN | inventario.py |
| `/admin/mp-diag` | GET | ADMIN | inventario.py |
| `/admin/normalizar-codigos` | GET | ADMIN | inventario.py |
| `/admin/normalizar-mee` | GET | ADMIN | inventario.py |
| `/admin/precios-sospechosos` | GET | AUTENTICADO | inventario.py |
| `/admin/productos-envases` | GET | AUTENTICADO | inventario.py |
| `/admin/renombrar-codigo-mp` | GET | ADMIN | inventario.py |
| `/admin/reset-inventario` | GET | ADMIN | inventario.py |
| `/api/acondicionamiento` | GET,POST | PLANTA | inventario.py |
| `/api/acondicionamiento/<int:aid>` | PATCH | PLANTA | inventario.py |
| `/api/acondicionamiento/<int:aid>/detalle` | GET | AUTENTICADO | inventario.py |
| `/api/acondicionamiento/pendientes-lib` | GET | AUTENTICADO | inventario.py |
| `/api/admin/anular-movimiento` | POST | ADMIN | inventario.py |
| `/api/admin/auditar-formula-mp-match` | GET | ADMIN | inventario.py |
| `/api/admin/backfill-precios-mp` | POST | ADMIN | inventario.py |
| `/api/admin/crear-envases-10ml-sueros` | POST | ADMIN | inventario.py |
| `/api/admin/cuarentena-lista` | GET | ADMIN | inventario.py |
| `/api/admin/descuento-retro/apply` | POST | ADMIN | inventario.py |
| `/api/admin/descuento-retro/corregir` | POST | ADMIN | inventario.py |
| `/api/admin/descuento-retro/preview` | POST | ADMIN | inventario.py |
| `/api/admin/envases-recatalogo-apply` | POST | ADMIN | inventario.py |
| `/api/admin/formulas/pin` | GET,POST | ADMIN | inventario.py |
| `/api/admin/inci-ambiguos` | GET | ADMIN | inventario.py |
| `/api/admin/liberar-cuarentena-bloque` | POST | ADMIN | inventario.py |
| `/api/admin/maestro-mps-unificar` | POST | ADMIN | inventario.py |
| `/api/admin/mee/diag` | GET | AUTENTICADO | inventario.py |
| `/api/admin/mee/marcar-huerfanos-inactivos` | POST | ADMIN | inventario.py |
| `/api/admin/mee/normalizar-descripciones` | POST | ADMIN | inventario.py |
| `/api/admin/mee/reconciliar-stock-bulk` | POST | ADMIN | inventario.py |
| `/api/admin/mee/unificar-categorias` | POST | ADMIN | inventario.py |
| `/api/admin/mp-bridge-reapuntar` | POST | ADMIN | inventario.py |
| `/api/admin/mp-diag` | GET | ADMIN | inventario.py |
| `/api/admin/mp-reactivar` | POST | ADMIN | inventario.py |
| `/api/admin/normalizar-formulas-mp` | POST | ADMIN | inventario.py |
| `/api/admin/normalizar-lote/apply` | POST | ADMIN | inventario.py |
| `/api/admin/normalizar-lote/preview` | POST | ADMIN | inventario.py |
| `/api/admin/renombrar-mp-apply` | POST | ADMIN | inventario.py |
| `/api/admin/renombrar-mp-preview` | GET | ADMIN | inventario.py |
| `/api/alertas` | GET,POST | AUTENTICADO | inventario.py |
| `/api/alertas-reabastecimiento` | GET | AUTENTICADO | inventario.py |
| `/api/alertas/all` | GET | AUTENTICADO | inventario.py |
| `/api/alertas/silenciar` | POST | AUTENTICADO | inventario.py |
| `/api/alertas/silenciar/<int:silen_id>` | DELETE | AUTENTICADO | inventario.py |
| `/api/analisis-abc` | GET | FINANZAS | inventario.py |
| `/api/consumo-manual` | POST | ADMIN | inventario.py |
| `/api/conteo/<int:conteo_id>/ajustar` | POST | ADMIN | inventario.py |
| `/api/conteo/<int:conteo_id>/cerrar` | POST | PLANTA | inventario.py |
| `/api/conteo/<int:conteo_id>/guardar` | POST | PLANTA | inventario.py |
| `/api/conteo/<int:conteo_id>/items` | GET | AUTENTICADO | inventario.py |
| `/api/conteo/alertas-gerencia` | GET | AUTENTICADO | inventario.py |
| `/api/conteo/estanterias` | GET | AUTENTICADO | inventario.py |
| `/api/conteo/historial` | GET | AUTENTICADO | inventario.py |
| `/api/conteo/iniciar` | POST | PLANTA | inventario.py |
| `/api/conteo/materiales` | GET | AUTENTICADO | inventario.py |
| `/api/conteo/programacion` | GET | AUTENTICADO | inventario.py |
| `/api/conteos` | GET,POST | PLANTA | inventario.py |
| `/api/conteos/<int:cid>` | GET,PATCH | PLANTA | inventario.py |
| `/api/dashboard/insights` | GET | AUTENTICADO | inventario.py |
| `/api/envasado` | GET,POST | PLANTA | inventario.py |
| `/api/envasado/<int:eid>/detalle` | GET | AUTENTICADO | inventario.py |
| `/api/envasado/pendientes-acond` | GET | AUTENTICADO | inventario.py |
| `/api/formula/costo` | POST | FÓRMULAS (INVIMA) | inventario.py |
| `/api/formulas` | GET,POST | ADMIN | inventario.py |
| `/api/formulas/<path:producto_nombre>/codigo-pt` | PATCH | ADMIN | inventario.py |
| `/api/formulas/<path:producto_nombre>/imagen` | DELETE,GET,POST | AUTENTICADO | inventario.py |
| `/api/formulas/<path:producto_nombre>/imagen-shopify-sync` | POST | AUTENTICADO | inventario.py |
| `/api/formulas/<path:producto_nombre>/uso` | GET | AUTENTICADO | inventario.py |
| `/api/formulas/<path:producto_nombre>/versiones` | GET | AUTENTICADO | inventario.py |
| `/api/formulas/<producto_nombre>` | DELETE | ADMIN | inventario.py |
| `/api/formulas/bases-stats` | GET | AUTENTICADO | inventario.py |
| `/api/formulas/catalogo` | GET | AUTENTICADO | inventario.py |
| `/api/formulas/duplicar` | POST | AUTENTICADO | inventario.py |
| `/api/formulas/export-excel` | GET | AUTENTICADO | inventario.py |
| `/api/formulas/import-excel` | POST | ADMIN | inventario.py |
| `/api/formulas/normalizar-base` | POST | ADMIN | inventario.py |
| `/api/formulas/sync-shopify-all` | POST | AUTENTICADO | inventario.py |
| `/api/formulas/sync-shopify-blocking` | POST | AUTENTICADO | inventario.py |
| `/api/formulas/unlock` | POST | AUTENTICADO | inventario.py |
| `/api/imagen-producto/<path:producto_nombre>` | GET | AUTENTICADO | inventario.py |
| `/api/inventario` | GET | AUTENTICADO | inventario.py |
| `/api/inventario/diagnostico-post-incidente` | GET | AUTENTICADO | inventario.py |
| `/api/inventario/importar-conteo/analizar` | POST | ADMIN | inventario.py |
| `/api/inventario/importar-conteo/cargar` | POST | ADMIN | inventario.py |
| `/api/inventario/modo-inventario` | GET,POST | ADMIN | inventario.py |
| `/api/inventario/reset-inventario-cero` | GET,POST | ADMIN | inventario.py |
| `/api/liberacion` | GET,POST | AUTENTICADO | inventario.py |
| `/api/liberacion/<int:lid>` | PATCH | AUTENTICADO | inventario.py |
| `/api/lotes` | GET | AUTENTICADO | inventario.py |
| `/api/lotes/<material_id>/<path:lote>` | DELETE | PLANTA | inventario.py |
| `/api/lotes/<material_id>/<path:lote>/codigo-lote` | PUT | PLANTA | inventario.py |
| `/api/lotes/<material_id>/<path:lote>/fecha-vencimiento` | PUT | PLANTA | inventario.py |
| `/api/lotes/<material_id>/<path:lote>/movimientos` | GET | AUTENTICADO | inventario.py |
| `/api/lotes/<material_id>/<path:lote>/proveedor` | PUT | PLANTA | inventario.py |
| `/api/lotes/<material_id>/<path:lote>/ubicacion` | PUT | PLANTA | inventario.py |
| `/api/lotes/cc-review` | POST | ADMIN | inventario.py |
| `/api/lotes/cuarentena` | GET | AUTENTICADO | inventario.py |
| `/api/lotes/cuarentena/<int:mov_id>/liberar` | POST | AUTENTICADO | inventario.py |
| `/api/lotes/cuarentena/liberar-inventario` | POST | ADMIN | inventario.py |
| `/api/lotes/export-xlsx` | GET | AUTENTICADO | inventario.py |
| `/api/lotes/liberar` | POST | CALIDAD | inventario.py |
| `/api/lotes/retenido` | GET | AUTENTICADO | inventario.py |
| `/api/maestro-mp/<codigo>/precio` | POST | PLANTA | inventario.py |
| `/api/maestro-mps` | GET,POST | PLANTA | inventario.py |
| `/api/maestro-mps/<codigo>` | GET | AUTENTICADO | inventario.py |
| `/api/maestro-mps/<codigo>/archivar` | PUT | AUTENTICADO | inventario.py |
| `/api/maestro-mps/<codigo>/mee-stock-minimo` | PUT | AUTENTICADO | inventario.py |
| `/api/maestro-mps/<codigo>/proveedor` | PUT | AUTENTICADO | inventario.py |
| `/api/maestro-mps/<codigo>/stock-minimo` | PUT | ADMIN | inventario.py |
| `/api/maestro-mps/alias` | DELETE,GET,POST | AUTENTICADO | inventario.py |
| `/api/maestro-mps/buscar-inteligente` | GET | AUTENTICADO | inventario.py |
| `/api/maestro-mps/duplicados-deteccion` | GET | ADMIN | inventario.py |
| `/api/maestro-mps/export-lista-simple` | GET | AUTENTICADO | inventario.py |
| `/api/maestro-mps/next-codigo` | GET | AUTENTICADO | inventario.py |
| `/api/maestro-mps/unificar` | POST | ADMIN | inventario.py |
| `/api/mee` | POST | ASEGURAMIENTO | inventario.py |
| `/api/mee/<codigo>` | DELETE,GET,PUT | AUTENTICADO | inventario.py |
| `/api/mee/<codigo>/ajustar` | POST | AUTENTICADO | inventario.py |
| `/api/mee/<codigo>/historico` | GET | AUTENTICADO | inventario.py |
| `/api/mee/<codigo>/partes` | POST | PLANTA | inventario.py |
| `/api/mee/<codigo>/proveedor` | PUT | AUTENTICADO | inventario.py |
| `/api/mee/<codigo>/stock-minimo` | PUT | AUTENTICADO | inventario.py |
| `/api/mee/alertas` | GET | AUTENTICADO | inventario.py |
| `/api/mee/anular/<int:mov_id>` | POST | PLANTA | inventario.py |
| `/api/mee/calificar` | POST | AUTENTICADO | inventario.py |
| `/api/mee/categorias` | GET | AUTENTICADO | inventario.py |
| `/api/mee/crear-auto` | POST | ASEGURAMIENTO | inventario.py |
| `/api/mee/cuarentena-pendientes` | GET | PLANTA | inventario.py |
| `/api/mee/cuarentena/<int:mov_id>/<accion>` | POST | AUTENTICADO | inventario.py |
| `/api/mee/import-bulk` | POST | AUTENTICADO | inventario.py |
| `/api/mee/movimiento` | POST | ASEGURAMIENTO | inventario.py |
| `/api/mee/movimientos` | GET | AUTENTICADO | inventario.py |
| `/api/mee/partes` | GET | PLANTA | inventario.py |
| `/api/mee/por-calificar` | GET | PLANTA | inventario.py |
| `/api/mee/recalcular-stock` | POST | ADMIN | inventario.py |
| `/api/mee/recodificar` | POST | PLANTA | inventario.py |
| `/api/mee/set-cliente` | POST | PLANTA | inventario.py |
| `/api/mee/set-imagen` | POST | PLANTA | inventario.py |
| `/api/mee/shopify-fotos-bulk` | POST | PLANTA | inventario.py |
| `/api/mee/siguiente-codigo` | GET | PLANTA | inventario.py |
| `/api/mee/stock` | GET | AUTENTICADO | inventario.py |
| `/api/mee/trazabilidad` | GET | AUTENTICADO | inventario.py |
| `/api/mee/ubicaciones` | GET | AUTENTICADO | inventario.py |
| `/api/mee/ubicaciones/agregar` | POST | PLANTA | inventario.py |
| `/api/movimientos` | GET,POST | PLANTA | inventario.py |
| `/api/movimientos/<int:mov_id>` | DELETE | ADMIN | inventario.py |
| `/api/movimientos/<int:mov_id>/anular` | POST | ADMIN | inventario.py |
| `/api/movimientos/recientes` | GET | AUTENTICADO | inventario.py |
| `/api/mp/<codigo>/consumo-historico` | GET | AUTENTICADO | inventario.py |
| `/api/mp/<codigo>/historial-precios` | GET | AUTENTICADO | inventario.py |
| `/api/ordenes-compra/pendientes-recepcion` | GET | AUTENTICADO | inventario.py |
| `/api/planta/alertas-vivas` | GET | AUTENTICADO | inventario.py |
| `/api/planta/auditar-minimos` | GET | AUTENTICADO | inventario.py |
| `/api/planta/kardex/<codigo_mp>` | GET | AUTENTICADO | inventario.py |
| `/api/planta/stock-por-lote/<codigo_mp>` | GET | AUTENTICADO | inventario.py |
| `/api/planta/valoracion-inventario` | GET | AUTENTICADO | inventario.py |
| `/api/produccion` | GET,POST | AUTENTICADO | inventario.py |
| `/api/produccion/<int:pid>/ajustar-cantidad` | POST | ADMIN | inventario.py |
| `/api/produccion/<int:pid>/detalle` | GET | AUTENTICADO | inventario.py |
| `/api/produccion/<int:pid>/rotulo-reimprimir` | GET | AUTENTICADO | inventario.py |
| `/api/produccion/auditar-formulas-huerfanas` | GET | AUTENTICADO | inventario.py |
| `/api/produccion/auto-reparar-formula/<path:producto>` | POST | ADMIN | inventario.py |
| `/api/produccion/auto-reparar-todas` | POST | ADMIN | inventario.py |
| `/api/produccion/diagnose/<path:producto>` | GET | AUTENTICADO | inventario.py |
| `/api/produccion/pendientes-hoy` | GET | AUTENTICADO | inventario.py |
| `/api/produccion/simular` | POST | AUTENTICADO | inventario.py |
| `/api/producciones/sin-envasar` | GET | AUTENTICADO | inventario.py |
| `/api/proveedores-duplicados` | GET | AUTENTICADO | inventario.py |
| `/api/proveedores-unicos` | GET | AUTENTICADO | inventario.py |
| `/api/proveedores-unificar` | POST | PLANTA | inventario.py |
| `/api/recepcion` | POST | CALIDAD | inventario.py |
| `/api/recepcion/<codigo_mp>/precio-historico` | GET | AUTENTICADO | inventario.py |
| `/api/recepcion/<int:mov_id>/anular` | POST | ADMIN | inventario.py |
| `/api/recepcion/lote-info` | GET | AUTENTICADO | inventario.py |
| `/api/recepcion/recientes` | GET | AUTENTICADO | inventario.py |
| `/api/reset-movimientos` | POST | ADMIN | inventario.py |
| `/api/stock` | GET | AUTENTICADO | inventario.py |
| `/api/trazabilidad/lote-mp/<path:lote_mp>` | GET | AUTENTICADO | inventario.py |
| `/api/trazabilidad/lote-pt/<lote_ref>` | GET | AUTENTICADO | inventario.py |
| `/api/trazabilidad/lote/<path:lote>` | GET | AUTENTICADO | inventario.py |
| `/planta/conteo-ciclico` | GET | AUTENTICADO | inventario.py |
| `/rotulo-recepcion-mee/<codigo>/<cantidad_str>` | GET | AUTENTICADO | inventario.py |
| `/rotulo-recepcion/<codigo>/<lote>/<cantidad_str>` | GET | AUTENTICADO | inventario.py |
| `/rotulos/<producto_nombre>/<cantidad_str>` | GET | AUTENTICADO | inventario.py |
| `/scan/<path:codigo>/<path:lote>` | GET | AUTENTICADO | inventario.py |
| `/api/animus/alertas-stock` | GET | AUTENTICADO | maquila.py |
| `/api/animus/solicitar-produccion` | POST | AUTENTICADO | maquila.py |
| `/api/animus/solicitudes-produccion` | GET | AUTENTICADO | maquila.py |
| `/api/animus/solicitudes-produccion/<int:sid>` | PATCH | AUTENTICADO | maquila.py |
| `/api/hub-salida/despachar` | POST | AUTENTICADO | maquila.py |
| `/api/hub-salida/pedido/<numero>` | GET | AUTENTICADO | maquila.py |
| `/api/hub-salida/pedidos-pendientes` | GET | AUTENTICADO | maquila.py |
| `/api/hub-salida/stock/<sku>` | GET | AUTENTICADO | maquila.py |
| `/api/maquila/cotizar` | POST | AUTENTICADO | maquila.py |
| `/api/maquila/kpis` | GET | AUTENTICADO | maquila.py |
| `/api/maquila/ordenes` | GET,POST | AUTENTICADO | maquila.py |
| `/api/maquila/ordenes/<int:oid>` | PATCH | AUTENTICADO | maquila.py |
| `/api/maquila/ordenes/<int:oid>/facturar` | POST | AUTENTICADO | maquila.py |
| `/api/maquila/prospectos` | GET,POST | AUTENTICADO | maquila.py |
| `/api/maquila/prospectos/<int:pid>` | PATCH | AUTENTICADO | maquila.py |
| `/api/recall/ejecutar` | POST | ADMIN | maquila.py |
| `/api/recall/simular/<path:lote_pt>` | GET | AUTENTICADO | maquila.py |
| `/api/stock-pt/<sku>/reorden` | POST | AUTENTICADO | maquila.py |
| `/hub-salida` | GET | AUTENTICADO | maquila.py |
| `/api/marketing/ab-tests` | GET,POST | AUTENTICADO | marketing.py |
| `/api/marketing/ab-tests/<int:tid>/calcular-ganador` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/ads/resumen` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/ads/sync-meta` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/agencia/audit` | GET | FINANZAS | marketing.py |
| `/api/marketing/analytics/influencers` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/analytics/roi` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/analytics/tendencias` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/atribucion` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/atribucion-influencers` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/campana-influencer` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/campana-influencer/<int:rid>` | PUT | AUTENTICADO | marketing.py |
| `/api/marketing/campanas` | GET,POST | AUTENTICADO | marketing.py |
| `/api/marketing/campanas/<int:cid>` | DELETE,GET,PUT | ADMIN | marketing.py |
| `/api/marketing/campanas/<int:cid>/generar-cupon` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/connections` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/contacto-360` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/contenido` | GET,POST | AUTENTICADO | marketing.py |
| `/api/marketing/contenido/<int:cid>` | DELETE,PUT | AUTENTICADO | marketing.py |
| `/api/marketing/contenido/kanban` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/dashboard` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/debug-influencers` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/eventos-calendario` | GET,POST | AUTENTICADO | marketing.py |
| `/api/marketing/eventos-calendario/<int:eid>` | DELETE,PUT | AUTENTICADO | marketing.py |
| `/api/marketing/fix-pago-link` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/ghl-debug` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/ig-debug` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/ig-refresh` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/ig-update-token` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/influencers` | GET,POST | ADMIN | marketing.py |
| `/api/marketing/influencers-panel` | GET | FINANZAS | marketing.py |
| `/api/marketing/influencers/<int:iid>` | DELETE,GET,PUT | ADMIN | marketing.py |
| `/api/marketing/influencers/<int:iid>/banco` | PUT | AUTENTICADO | marketing.py |
| `/api/marketing/influencers/<int:iid>/dar-baja` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/influencers/<int:iid>/generar-cupon` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/influencers/<int:iid>/metrics-history` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/influencers/<int:iid>/refresh-metrics` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/influencers/<int:iid>/solicitar-pago` | POST | ADMIN | marketing.py |
| `/api/marketing/influencers/dedup-merge` | POST | ADMIN | marketing.py |
| `/api/marketing/influencers/duplicados` | GET | ADMIN | marketing.py |
| `/api/marketing/kpis-hoy` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/ltv-clientes` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/meta-progreso` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/metas` | GET,POST | AUTENTICADO | marketing.py |
| `/api/marketing/optimo-publicacion` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/pagos-historico-cleanup` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/pagos-influencer/<int:pid>` | DELETE,PATCH | ADMIN | marketing.py |
| `/api/marketing/pagos-influencer/urgencias` | GET | AUTENTICADO | marketing.py |
| `/api/marketing/pagos-influencers` | GET | FINANZAS | marketing.py |
| `/api/marketing/refresh-all-metrics` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/reporte-ejecutivo-semanal` | GET,POST | AUTENTICADO | marketing.py |
| `/api/marketing/sync/<platform>` | POST | AUTENTICADO | marketing.py |
| `/api/marketing/workflow/aplicar-agente` | POST | AUTENTICADO | marketing.py |
| `/api/admin/mfa-reset/<username>` | POST | ADMIN | mfa.py |
| `/api/mfa/admin-disable` | POST | ADMIN | mfa.py |
| `/api/mfa/backup-codes/regenerate` | POST | AUTENTICADO | mfa.py |
| `/api/mfa/backup-codes/status` | GET | AUTENTICADO | mfa.py |
| `/api/mfa/disable` | POST | AUTENTICADO | mfa.py |
| `/api/mfa/qr` | GET | AUTENTICADO | mfa.py |
| `/api/mfa/setup` | POST | AUTENTICADO | mfa.py |
| `/api/mfa/status` | GET | AUTENTICADO | mfa.py |
| `/api/mfa/verify-setup` | POST | AUTENTICADO | mfa.py |
| `/login/mfa` | GET | PÚBLICA | mfa.py |
| `/login/mfa` | POST | PÚBLICA | mfa.py |
| `/login/mfa-backup` | GET,POST | PÚBLICA | mfa.py |
| `/seguridad` | GET | AUTENTICADO | mfa.py |
| `/seguridad/mfa` | GET | AUTENTICADO | mfa.py |
| `/api/notif/<int:nid>/leer` | POST | AUTENTICADO | notif.py |
| `/api/notif/list` | GET | AUTENTICADO | notif.py |
| `/api/notif/marcar-todas` | POST | AUTENTICADO | notif.py |
| `/api/notif/unread-count` | GET | AUTENTICADO | notif.py |
| `/api/notif/widget.js` | GET | AUTENTICADO | notif.py |
| `/api/operario/mi-dia` | GET | ADMIN | operario.py |
| `/api/planta/mi-dia` | GET | ADMIN | operario.py |
| `/mi-dia` | GET | AUTENTICADO | operario.py |
| `/operario` | GET | AUTENTICADO | operario.py |
| `/admin/calculo-frecuencias` | GET | AUTENTICADO | plan.py |
| `/admin/calendario-simple` | GET | AUTENTICADO | plan.py |
| `/admin/comparar-calendar-necesidades` | GET | AUTENTICADO | plan.py |
| `/admin/configurar-canonicos` | GET | AUTENTICADO | plan.py |
| `/admin/dashboard-plan` | GET | AUTENTICADO | plan.py |
| `/admin/detector-mps-renombre` | GET | AUTENTICADO | plan.py |
| `/admin/diag-familia` | GET | AUTENTICADO | plan.py |
| `/admin/diag-flujo-abast` | GET | COMPRAS | plan.py |
| `/admin/diag-formulas-sospechosas` | GET | COMPRAS | plan.py |
| `/admin/factibilidad-plan` | GET | AUTENTICADO | plan.py |
| `/admin/fusionar-formulas-nf` | GET,POST | COMPRAS | plan.py |
| `/admin/gasto-mps` | GET | AUTENTICADO | plan.py |
| `/admin/limpiar-sols-ocs` | GET,POST | COMPRAS | plan.py |
| `/admin/llenar-calendario` | GET,POST | COMPRAS | plan.py |
| `/admin/mps-buscar` | GET | AUTENTICADO | plan.py |
| `/admin/plan-calendario` | GET | AUTENTICADO | plan.py |
| `/admin/plan-simple` | GET | AUTENTICADO | plan.py |
| `/admin/plan-sugerido` | GET | AUTENTICADO | plan.py |
| `/admin/reconciliar-formulas` | GET | AUTENTICADO | plan.py |
| `/admin/revisar-plan` | GET | AUTENTICADO | plan.py |
| `/admin/sub-skus` | GET | COMPRAS | plan.py |
| `/admin/validar-formulas` | GET | AUTENTICADO | plan.py |
| `/admin/verificar-codigos-mp` | GET | AUTENTICADO | plan.py |
| `/admin/verificar-volumenes` | GET | AUTENTICADO | plan.py |
| `/api/admin/b2b/cliente/<cliente_id>/envases` | GET | AUTENTICADO | plan.py |
| `/api/admin/b2b/cliente/<cliente_id>/envases` | POST | AUTENTICADO | plan.py |
| `/api/admin/b2b/lote/<int:lote_id>/desglose` | GET | AUTENTICADO | plan.py |
| `/api/admin/clientes-b2b/migrar-desde-maquila` | POST | AUTENTICADO | plan.py |
| `/api/admin/consolidar-producto` | POST | ADMIN | plan.py |
| `/api/admin/diag-cobertura-calendario` | GET | AUTENTICADO | plan.py |
| `/api/admin/diag-familia-producto` | GET | AUTENTICADO | plan.py |
| `/api/admin/diagnostico-migracion` | GET | AUTENTICADO | plan.py |
| `/api/admin/diagnostico-migracion-detalle` | GET | AUTENTICADO | plan.py |
| `/api/admin/formula-activar` | POST | ADMIN | plan.py |
| `/api/admin/formula-desactivar` | POST | ADMIN | plan.py |
| `/api/admin/formulas-reconciliar` | POST | AUTENTICADO | plan.py |
| `/api/admin/formulas/agrupar-canonico` | POST | AUTENTICADO | plan.py |
| `/api/admin/formulas/variantes/<path:producto_canonico>` | GET | AUTENTICADO | plan.py |
| `/api/admin/lote-size-fix` | POST | ADMIN | plan.py |
| `/api/admin/lote-size-sospechoso` | GET | AUTENTICADO | plan.py |
| `/api/admin/lotes/regenerar-distribucion` | POST | AUTENTICADO | plan.py |
| `/api/admin/ml-fix` | POST | ADMIN | plan.py |
| `/api/admin/ml-fix-todos-skus` | POST | ADMIN | plan.py |
| `/api/admin/sku-producto-map/bulk` | POST | AUTENTICADO | plan.py |
| `/api/admin/skus-huerfanos-top` | GET | AUTENTICADO | plan.py |
| `/api/admin/sub-skus` | GET | AUTENTICADO | plan.py |
| `/api/admin/sub-skus/<path:sku>` | PATCH | AUTENTICADO | plan.py |
| `/api/b2b/envases-disponibles` | GET | AUTENTICADO | plan.py |
| `/api/clientes-b2b` | GET | AUTENTICADO | plan.py |
| `/api/clientes-b2b` | POST | AUTENTICADO | plan.py |
| `/api/clientes-b2b/<cliente_id>` | DELETE | AUTENTICADO | plan.py |
| `/api/pedidos-b2b` | GET | AUTENTICADO | plan.py |
| `/api/pedidos-b2b` | POST | AUTENTICADO | plan.py |
| `/api/pedidos-b2b/<int:pid>` | PATCH | AUTENTICADO | plan.py |
| `/api/pedidos-b2b/<int:pid>` | DELETE | AUTENTICADO | plan.py |
| `/api/pedidos-b2b/<int:pid>/asignar-a-animus` | POST | AUTENTICADO | plan.py |
| `/api/pedidos-b2b/<int:pid>/asignar-a-lote/<int:lote_id>` | POST | AUTENTICADO | plan.py |
| `/api/pedidos-b2b/<int:pid>/confirmar` | POST | AUTENTICADO | plan.py |
| `/api/pedidos-b2b/<int:pid>/despachar` | POST | AUTENTICADO | plan.py |
| `/api/pedidos-b2b/<int:pid>/diagnostico-match` | GET | AUTENTICADO | plan.py |
| `/api/pedidos-b2b/<int:pid>/match-preview` | GET | AUTENTICADO | plan.py |
| `/api/pedidos-b2b/diagnostico-cliente` | GET | AUTENTICADO | plan.py |
| `/api/plan/acelerador-config` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/aceptar-adelanto` | POST | AUTENTICADO | plan.py |
| `/api/plan/alertas-ia` | GET | AUTENTICADO | plan.py |
| `/api/plan/alertas-ventas` | GET | AUTENTICADO | plan.py |
| `/api/plan/aplicar-ia-anual` | POST | AUTENTICADO | plan.py |
| `/api/plan/aplicar-ia-bulk` | POST | AUTENTICADO | plan.py |
| `/api/plan/auto-programar-sugeridas` | POST | AUTENTICADO | plan.py |
| `/api/plan/autoplan-ia` | POST | AUTENTICADO | plan.py |
| `/api/plan/autoplan-ia/feedback` | POST | AUTENTICADO | plan.py |
| `/api/plan/backfill-fabricacion` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/calculo-frecuencias` | GET | AUTENTICADO | plan.py |
| `/api/plan/check-codigos-mp` | GET | AUTENTICADO | plan.py |
| `/api/plan/cobertura-planeacion` | GET | AUTENTICADO | plan.py |
| `/api/plan/comparar-calendar-necesidades` | GET | AUTENTICADO | plan.py |
| `/api/plan/configurar-canonicos` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/dashboard` | GET | AUTENTICADO | plan.py |
| `/api/plan/debug-origenes` | GET | AUTENTICADO | plan.py |
| `/api/plan/debug-tz` | GET | AUTENTICADO | plan.py |
| `/api/plan/dedup-mismo-dia` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/dejar-solo-real` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/desglose-tonos` | GET | AUTENTICADO | plan.py |
| `/api/plan/detector-mps-renombre` | GET | AUTENTICADO | plan.py |
| `/api/plan/diag-formulas-dump` | GET | FÓRMULAS (INVIMA) | plan.py |
| `/api/plan/diag-lotes-producto` | GET | AUTENTICADO | plan.py |
| `/api/plan/diag-mp/<codigo>` | GET | FÓRMULAS (INVIMA) | plan.py |
| `/api/plan/diag-plan-90d` | GET | AUTENTICADO | plan.py |
| `/api/plan/diag-rescate` | GET | AUTENTICADO | plan.py |
| `/api/plan/diag-sku-ventas` | GET | AUTENTICADO | plan.py |
| `/api/plan/diagnostico-mp` | GET | AUTENTICADO | plan.py |
| `/api/plan/diagnostico-shopify` | GET | AUTENTICADO | plan.py |
| `/api/plan/eliminar-dia` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/estacionalidad-ventas` | GET | AUTENTICADO | plan.py |
| `/api/plan/factibilidad` | GET | AUTENTICADO | plan.py |
| `/api/plan/festivos` | GET | AUTENTICADO | plan.py |
| `/api/plan/gasto-mps` | GET | AUTENTICADO | plan.py |
| `/api/plan/generar-plan-desde-hoy` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/generar-plan-perfecto` | POST | AUTENTICADO | plan.py |
| `/api/plan/health-canonicos` | GET | AUTENTICADO | plan.py |
| `/api/plan/kg-otro-cliente-cadena` | POST | AUTENTICADO | plan.py |
| `/api/plan/limpiar-duplicados` | POST | AUTENTICADO | plan.py |
| `/api/plan/limpiar-futuro-auto` | POST | AUTENTICADO | plan.py |
| `/api/plan/limpiar-proyeccion` | POST | AUTENTICADO | plan.py |
| `/api/plan/limpiar-sugeridas-futuras` | POST | AUTENTICADO | plan.py |
| `/api/plan/limpiar-todo-calendario` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/listar-canonicos` | GET | AUTENTICADO | plan.py |
| `/api/plan/lote/<int:lote_id>/agregar-cliente` | POST | AUTENTICADO | plan.py |
| `/api/plan/lotes-producto` | GET | AUTENTICADO | plan.py |
| `/api/plan/mps-buscar` | GET | AUTENTICADO | plan.py |
| `/api/plan/necesidades` | GET | AUTENTICADO | plan.py |
| `/api/plan/pauta-multitono` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/plan-sugerido` | GET | AUTENTICADO | plan.py |
| `/api/plan/plan-sugerido/ejecutar` | POST | AUTENTICADO | plan.py |
| `/api/plan/producciones-sin-descontar` | GET | AUTENTICADO | plan.py |
| `/api/plan/producto-externo` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/producto/<path:producto>/presentaciones` | GET | AUTENTICADO | plan.py |
| `/api/plan/producto/<path:producto>/presentaciones` | POST | AUTENTICADO | plan.py |
| `/api/plan/programar-cadencia-desde-lote/<int:lote_id>` | POST | AUTENTICADO | plan.py |
| `/api/plan/programar-cadencia-producto` | POST | AUTENTICADO | plan.py |
| `/api/plan/programar-canonico` | POST | AUTENTICADO | plan.py |
| `/api/plan/programar-manual` | POST | AUTENTICADO | plan.py |
| `/api/plan/programar-produccion` | POST | AUTENTICADO | plan.py |
| `/api/plan/proximas` | GET | AUTENTICADO | plan.py |
| `/api/plan/proximas/<int:pid>` | DELETE | ADMIN | plan.py |
| `/api/plan/proximas/<int:pid>/cantidad` | POST | AUTENTICADO | plan.py |
| `/api/plan/proximas/<int:pid>/pausar` | POST | AUTENTICADO | plan.py |
| `/api/plan/proximas/<int:pid>/reactivar` | POST | AUTENTICADO | plan.py |
| `/api/plan/proximas/<int:pid>/reprogramar` | POST | AUTENTICADO | plan.py |
| `/api/plan/proyectar-2anios` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/reconstruir-plan` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/recuperar-cancelados-bug` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/recuperar-semana-19may2026` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/regenerar-canonicos` | POST | AUTENTICADO | plan.py |
| `/api/plan/registrar-produccion-completada` | POST | AUTENTICADO | plan.py |
| `/api/plan/repartir-sobrecargados` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/reprogramar-desde-mes` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/restaurar-a-hora` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/revertir-hoy` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/revisar` | GET | AUTENTICADO | plan.py |
| `/api/plan/salud-cadenas` | GET | AUTENTICADO | plan.py |
| `/api/plan/sellar-horizonte` | POST | AUTENTICADO | plan.py |
| `/api/plan/set-volumen` | POST | AUTENTICADO | plan.py |
| `/api/plan/set-volumenes-bulk` | POST | AUTENTICADO | plan.py |
| `/api/plan/solo-manual` | GET,POST | AUTENTICADO | plan.py |
| `/api/plan/sugerencias-adelanto` | GET | AUTENTICADO | plan.py |
| `/api/plan/sugerir-preview` | GET | AUTENTICADO | plan.py |
| `/api/plan/validar-formulas` | GET | AUTENTICADO | plan.py |
| `/api/plan/verificar-cadenas` | GET | AUTENTICADO | plan.py |
| `/api/plan/verificar-volumenes` | GET | AUTENTICADO | plan.py |
| `/api/produccion/<int:pid>/eventos` | GET | AUTENTICADO | plan.py |
| `/planta/estacionalidad` | GET | AUTENTICADO | plan.py |
| `/admin/clientes-b2b` | GET | ADMIN | portal.py |
| `/admin/clientes-b2b` | GET | ADMIN | portal.py |
| `/admin/portal-demo` | GET | AUTENTICADO | portal.py |
| `/admin/portal-rfq` | GET | AUTENTICADO | portal.py |
| `/api/admin/portal/catalogo` | GET,POST | AUTENTICADO | portal.py |
| `/api/admin/portal/credenciales` | GET,POST | AUTENTICADO | portal.py |
| `/api/admin/portal/credenciales/<int:cred_id>` | DELETE,PATCH | AUTENTICADO | portal.py |
| `/api/admin/portal/pqr` | GET | AUTENTICADO | portal.py |
| `/api/admin/portal/pqr/<int:pqr_id>` | PATCH | AUTENTICADO | portal.py |
| `/api/admin/portal/solicitudes` | GET | ADMIN | portal.py |
| `/api/admin/portal/solicitudes/<int:sol_id>` | PATCH | ADMIN | portal.py |
| `/api/portal-demo/regenerar` | POST | AUTENTICADO | portal.py |
| `/api/portal/badge` | GET | AUTENTICADO | portal.py |
| `/api/portal/login` | POST | AUTENTICADO | portal.py |
| `/api/portal/mis-pedidos` | GET | AUTENTICADO | portal.py |
| `/api/portal/mis-pqr` | GET | AUTENTICADO | portal.py |
| `/api/portal/mis-solicitudes` | GET | AUTENTICADO | portal.py |
| `/api/portal/pedidos` | POST | AUTENTICADO | portal.py |
| `/api/portal/pedidos/<int:pid>` | PATCH | AUTENTICADO | portal.py |
| `/api/portal/pqr` | POST | CALIDAD | portal.py |
| `/api/portal/productos` | GET | AUTENTICADO | portal.py |
| `/api/portal/solicitudes` | POST | AUTENTICADO | portal.py |
| `/api/portal/solicitudes/<int:sol_id>/convertir-a-pedido` | POST | AUTENTICADO | portal.py |
| `/portal` | GET | PORTAL B2B | portal.py |
| `/portal/login` | GET | PORTAL B2B | portal.py |
| `/portal/logout` | GET,POST | PORTAL B2B | portal.py |
| `/api/abastecimiento/consumo-bruto-excel` | GET | AUTENTICADO | programacion.py |
| `/api/abastecimiento/consumo-horizontes` | GET | AUTENTICADO | programacion.py |
| `/api/abastecimiento/envases-cobertura` | GET | AUTENTICADO | programacion.py |
| `/api/abastecimiento/export-excel` | GET | AUTENTICADO | programacion.py |
| `/api/abastecimiento/formulas-activas` | GET | AUTENTICADO | programacion.py |
| `/api/abastecimiento/solicitar-items` | POST | AUTENTICADO | programacion.py |
| `/api/abastecimiento/trail-mp/<codigo_mp>` | GET | AUTENTICADO | programacion.py |
| `/api/abastecimiento/vincular-formula` | POST | AUTENTICADO | programacion.py |
| `/api/admin/marcacion-envase` | POST | AUTENTICADO | programacion.py |
| `/api/checklist/mee-options` | GET | AUTENTICADO | programacion.py |
| `/api/compras/minimos-envases-aplicar` | POST | AUTENTICADO | programacion.py |
| `/api/compras/minimos-envases-sugeridos` | GET | AUTENTICADO | programacion.py |
| `/api/compras/preparacion-envases` | GET | AUTENTICADO | programacion.py |
| `/api/compras/solicitudes-produccion` | GET | AUTENTICADO | programacion.py |
| `/api/compras/solicitudes-produccion/<int:sol_id>/decidir` | POST | AUTENTICADO | programacion.py |
| `/api/inventario/ajuste-manual` | POST | ADMIN | programacion.py |
| `/api/inventario/recalcular-minimos` | GET,POST | ADMIN | programacion.py |
| `/api/planta/aceptar-produccion/<int:produccion_id>` | POST | AUTENTICADO | programacion.py |
| `/api/planta/actividades/<int:act_id>/terminar` | POST | AUTENTICADO | programacion.py |
| `/api/planta/actividades/kpis` | GET | AUTENTICADO | programacion.py |
| `/api/planta/area/liberar-vivo` | POST | AUTENTICADO | programacion.py |
| `/api/planta/area/ocupar-vivo` | POST | AUTENTICADO | programacion.py |
| `/api/planta/areas` | GET | AUTENTICADO | programacion.py |
| `/api/planta/areas/<int:area_id>/actividades` | GET,POST | AUTENTICADO | programacion.py |
| `/api/planta/areas/<int:area_id>/estado` | PATCH | ADMIN | programacion.py |
| `/api/planta/areas/v2` | GET | AUTENTICADO | programacion.py |
| `/api/planta/asignar-areas` | GET | AUTENTICADO | programacion.py |
| `/api/planta/asignar-areas` | POST | AUTENTICADO | programacion.py |
| `/api/planta/auto-asignar-hoy` | POST | ADMIN | programacion.py |
| `/api/planta/auto-asignar-pendientes` | POST | AUTENTICADO | programacion.py |
| `/api/planta/auto-asignar/<int:prod_id>` | POST | AUTENTICADO | programacion.py |
| `/api/planta/blush-tonos` | GET | AUTENTICADO | programacion.py |
| `/api/planta/centro-mando` | GET | PLANTA | programacion.py |
| `/api/planta/cola-liberacion` | GET | AUTENTICADO | programacion.py |
| `/api/planta/cola-liberacion/<int:item_id>/disposicion` | POST | ADMIN | programacion.py |
| `/api/planta/cronograma-areas` | GET | AUTENTICADO | programacion.py |
| `/api/planta/cronograma-comparar-alejandro` | GET | AUTENTICADO | programacion.py |
| `/api/planta/envasado/<int:envasado_id>/terminar` | POST | AUTENTICADO | programacion.py |
| `/api/planta/envasado/iniciar` | POST | AUTENTICADO | programacion.py |
| `/api/planta/envasado/sugerencias` | GET | AUTENTICADO | programacion.py |
| `/api/planta/equipos` | GET | AUTENTICADO | programacion.py |
| `/api/planta/equipos/<int:eq_id>` | DELETE,GET,PUT | AUTENTICADO | programacion.py |
| `/api/planta/estado-salas-vivo` | GET | AUTENTICADO | programacion.py |
| `/api/planta/fabricacion/crear-iniciar` | POST | PLANTA | programacion.py |
| `/api/planta/fabricacion/reactivar-areas` | POST | ADMIN | programacion.py |
| `/api/planta/fabricaciones-recientes` | GET | AUTENTICADO | programacion.py |
| `/api/planta/limpiar-db-sin-calendar` | POST | AUTENTICADO | programacion.py |
| `/api/planta/limpieza-profunda/<int:item_id>/completar` | POST | AUTENTICADO | programacion.py |
| `/api/planta/limpieza-profunda/calendario` | GET | AUTENTICADO | programacion.py |
| `/api/planta/limpieza-profunda/generar` | POST | AUTENTICADO | programacion.py |
| `/api/planta/listo-producir/<path:producto>` | GET | AUTENTICADO | programacion.py |
| `/api/planta/operarios` | GET,POST | ADMIN | programacion.py |
| `/api/planta/operarios/<int:op_id>` | DELETE,PATCH | ADMIN | programacion.py |
| `/api/planta/operarios/historial` | GET | AUTENTICADO | programacion.py |
| `/api/planta/plan-semanal` | GET | AUTENTICADO | programacion.py |
| `/api/planta/plano-fabricacion` | GET | AUTENTICADO | programacion.py |
| `/api/planta/preflight/<int:produccion_id>` | GET | AUTENTICADO | programacion.py |
| `/api/planta/preflight/<int:produccion_id>/confirmar-limpieza` | POST | AUTENTICADO | programacion.py |
| `/api/planta/presentaciones` | GET | AUTENTICADO | programacion.py |
| `/api/planta/presentaciones` | POST | AUTENTICADO | programacion.py |
| `/api/planta/presentaciones/<int:pid>` | DELETE,PUT | AUTENTICADO | programacion.py |
| `/api/planta/presentaciones/bulk-categoria` | POST | AUTENTICADO | programacion.py |
| `/api/planta/presentaciones/productos-disponibles` | GET | AUTENTICADO | programacion.py |
| `/api/planta/rotulo-limpieza/<int:area_id>` | GET | CALIDAD | programacion.py |
| `/api/planta/rotulo-limpieza/<int:area_id>/realizar` | POST | PLANTA | programacion.py |
| `/api/planta/rotulo-limpieza/<int:area_id>/verificar` | POST | CALIDAD | programacion.py |
| `/api/planta/rotulos-limpieza` | GET | AUTENTICADO | programacion.py |
| `/api/planta/simulacro/limpiar` | POST | AUTENTICADO | programacion.py |
| `/api/planta/sugerir-area` | POST | AUTENTICADO | programacion.py |
| `/api/planta/yield-reporte` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/alertas` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/calendario` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/checklist/<int:produccion_id>` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/checklist/backfill` | POST | ADMIN | programacion.py |
| `/api/programacion/checklist/generar/<int:produccion_id>` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/checklist/items/<int:item_id>` | PATCH | AUTENTICADO | programacion.py |
| `/api/programacion/checklist/items/<int:item_id>/asignar-mee` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/checklist/items/<int:item_id>/solicitar` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/checklist/items/<int:item_id>/solicitar-produccion` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/checklist/resumen-calendario` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/checklist/sync-calendar` | POST | ADMIN | programacion.py |
| `/api/programacion/confrontar-calendario-productos` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/debug-calendar` | GET | ADMIN | programacion.py |
| `/api/programacion/debug-calendario` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/debug-mp-check/<producto>` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/debug-mps` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/debug-producto/<path:producto>` | GET | ADMIN | programacion.py |
| `/api/programacion/debug-stock` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/debug-ventas` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/decision-produccion` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/diag-estacionalidad` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/diag-formula-anomalia` | GET | FÓRMULAS (INVIMA) | programacion.py |
| `/api/programacion/diag-inventarios-shopify` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/diag-mp-demanda` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/diag-split-presentacion` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/diag-ventas-anio` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/diagnostico-alias` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/disponibilidad-mp/<path:codigo_mp>` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/envases-lista` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/envases-por-tamano` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/estacionalidad-config` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/generar-oc` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/limpiar-duplicados-producciones` | POST | ADMIN | programacion.py |
| `/api/programacion/lote/<int:lote_id>/envase-aplicar-default` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/lote/<int:lote_id>/envase-override` | PATCH | AUTENTICADO | programacion.py |
| `/api/programacion/lote/<int:lote_id>/envase-propagar-futuros` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/lote/<int:lote_id>/fija-override` | PATCH | AUTENTICADO | programacion.py |
| `/api/programacion/lote/<int:lote_id>/plan-envasado/<int:pbl_id>` | PATCH | AUTENTICADO | programacion.py |
| `/api/programacion/marcacion-arte-pendiente` | GET | ADMIN | programacion.py |
| `/api/programacion/marcacion-cambiar-envase` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/marcacion-catalogos` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/marcacion-crear-envase` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/marcacion-orden/<int:oid>/liberar` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/marcacion-orden/<int:oid>/liberar-checklist` | POST | ADMIN | programacion.py |
| `/api/programacion/marcacion-orden/<int:oid>/recibir` | POST | CALIDAD | programacion.py |
| `/api/programacion/marcacion-orden/enviar` | POST | ADMIN | programacion.py |
| `/api/programacion/marcacion-ordenes` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/marcacion-vincular` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/marcacion-vincular-sugerencias` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/mees-disponibles` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/mp-bridge` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/mp-bridge` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/mp-bridge/<int:bridge_id>` | DELETE | AUTENTICADO | programacion.py |
| `/api/programacion/mp-bridge/unmatched` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/mps-deficit` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/n-alertas` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/planificacion` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/planificacion/checklist-verificacion` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/planificacion/solicitar-bulk` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/por-entrar-manual` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/pres-agregar` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/pres-crear` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/pres-editar` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/pres-eliminar` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/pres-no-aplica` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/pres-quitar` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/pres-set-envase` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/pres-set-fija` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/pres-ventas` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/produccion-programada/<int:evento_id>/borrar` | DELETE | ADMIN | programacion.py |
| `/api/programacion/produccion-programada/listado` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/producciones-faltantes` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/productos` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/programar` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/programar` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/programar/<int:evento_id>` | DELETE | AUTENTICADO | programacion.py |
| `/api/programacion/programar/<int:evento_id>/asignar` | PATCH | AUTENTICADO | programacion.py |
| `/api/programacion/programar/<int:evento_id>/completar` | POST | ADMIN | programacion.py |
| `/api/programacion/programar/<int:evento_id>/composicion-mee` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/programar/<int:evento_id>/iniciar` | POST | ADMIN | programacion.py |
| `/api/programacion/programar/<int:evento_id>/listo-envases` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/programar/<int:evento_id>/revertir-completado` | POST | ADMIN | programacion.py |
| `/api/programacion/programar/<int:evento_id>/terminar` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/programar/<int:pid>/corregir-cantidad` | POST | ADMIN | programacion.py |
| `/api/programacion/que-puedo-producir` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/reconciliar-shopify` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/refrescar-ventas-diarias` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/regenerar-oc` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/registrar-stock` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/resumen` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/serigrafia-cola` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/sku-volumen` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/solicitar-faltantes-bulk` | POST | ADMIN | programacion.py |
| `/api/programacion/split-audit` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/stock-60d` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/sugerencia-produccion` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/sync-historico-shopify` | GET,POST | AUTENTICADO | programacion.py |
| `/api/programacion/sync-salud` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/sync-stock-shopify` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/sync-ventas` | POST | AUTENTICADO | programacion.py |
| `/api/programacion/test-shopify` | GET | AUTENTICADO | programacion.py |
| `/api/programacion/trail-explosion` | GET | FÓRMULAS (INVIMA) | programacion.py |
| `/api/programacion/velocidad` | GET | AUTENTICADO | programacion.py |
| `/api/tareas-operativas` | GET | AUTENTICADO | programacion.py |
| `/api/tareas-operativas` | POST | AUTENTICADO | programacion.py |
| `/api/tareas-operativas/<int:tarea_id>/completar` | POST | AUTENTICADO | programacion.py |
| `/planta/blush-tonos` | GET | AUTENTICADO | programacion.py |
| `/planta/plano` | GET | AUTENTICADO | programacion.py |
| `/planta/plano-imagen.png` | GET | AUTENTICADO | programacion.py |
| `/planta/programar` | GET | AUTENTICADO | programacion.py |
| `/planta/rotulo-estado/<int:area_id>` | GET | AUTENTICADO | programacion.py |
| `/planta/rotulo-limpieza/<int:area_id>/pdf` | GET | AUTENTICADO | programacion.py |
| `/planta/rotulo-limpieza/registro/<int:reg_id>/pdf` | GET | AUTENTICADO | programacion.py |
| `/planta/rotulos-estado` | GET | AUTENTICADO | programacion.py |
| `/planta/rotulos-limpieza` | GET | AUTENTICADO | programacion.py |
| `/planta/trail-explosion` | GET | FÓRMULAS (INVIMA) | programacion.py |
| `/programacion/por-entrar` | GET | AUTENTICADO | programacion.py |
| `/programacion/presentaciones` | GET | AUTENTICADO | programacion.py |
| `/api/rrhh/admin/seed-bancos` | POST | ADMIN | rrhh.py |
| `/api/rrhh/ausencias` | GET,POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/ausencias/<int:aid>` | PATCH | AUTENTICADO | rrhh.py |
| `/api/rrhh/calcular-pago-evento` | POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/capacitaciones` | GET,POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/compromisos-mejora` | GET,POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/compromisos-mejora/<int:cid>/completar` | POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/dashboard` | GET | AUTENTICADO | rrhh.py |
| `/api/rrhh/dashboard-rh-completo` | GET | AUTENTICADO | rrhh.py |
| `/api/rrhh/empleados` | GET,POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/empleados/<int:eid>` | GET,PUT | AUTENTICADO | rrhh.py |
| `/api/rrhh/empleados/<int:emp_id>/documentos` | GET,POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/empleados/<int:emp_id>/timeline` | GET | FINANZAS | rrhh.py |
| `/api/rrhh/evaluaciones` | GET,POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/eventos` | GET,POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/eventos/<int:evt_id>/aprobar` | POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/eventos/<int:evt_id>/cerrar` | POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/llamados-atencion` | GET,POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/nomina/<periodo>` | GET | FINANZAS | rrhh.py |
| `/api/rrhh/nomina/<periodo>/aprobar` | PATCH | ADMIN | rrhh.py |
| `/api/rrhh/nomina/<periodo>/comprobante/<int:eid>` | GET | ADMIN | rrhh.py |
| `/api/rrhh/nomina/<periodo>/export` | GET | AUTENTICADO | rrhh.py |
| `/api/rrhh/nomina/<periodo>/pagar` | PATCH | ADMIN | rrhh.py |
| `/api/rrhh/nomina/guardar` | POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/nomina/importar-excel` | POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/sgsst` | GET,POST | AUTENTICADO | rrhh.py |
| `/api/rrhh/sgsst/<int:sid>` | PATCH | AUTENTICADO | rrhh.py |
| `/rrhh` | GET | RRHH | rrhh.py |
| `/api/tecnica/<entidad>/<int:rid>/versiones` | GET | AUTENTICADO | tecnica.py |
| `/api/tecnica/<entidad>/<int:rid>/versiones/<int:vid>` | GET | AUTENTICADO | tecnica.py |
| `/api/tecnica/cambios-control` | GET,POST | TÉCNICA | tecnica.py |
| `/api/tecnica/cambios-control/<int:cc_id>/aplicar` | POST | AUTENTICADO | tecnica.py |
| `/api/tecnica/cambios-control/<int:cc_id>/aprobar` | POST | ADMIN | tecnica.py |
| `/api/tecnica/dashboard` | GET | AUTENTICADO | tecnica.py |
| `/api/tecnica/documentos` | GET,POST | AUTENTICADO | tecnica.py |
| `/api/tecnica/documentos/<int:did>` | DELETE,PATCH | ADMIN | tecnica.py |
| `/api/tecnica/documentos/<int:did>/marcar-revisado` | POST | AUTENTICADO | tecnica.py |
| `/api/tecnica/documentos/proximos-vencimientos` | GET | AUTENTICADO | tecnica.py |
| `/api/tecnica/fichas` | GET,POST | AUTENTICADO | tecnica.py |
| `/api/tecnica/fichas/<int:fid>` | DELETE,PATCH | ADMIN | tecnica.py |
| `/api/tecnica/formulas` | GET,POST | AUTENTICADO | tecnica.py |
| `/api/tecnica/formulas/<int:fid>` | DELETE,PATCH | ADMIN | tecnica.py |
| `/api/tecnica/formulas/<int:fid>/restaurar/<int:vid>` | POST | ADMIN | tecnica.py |
| `/api/tecnica/formulas/<int:fid>/versiones` | GET | AUTENTICADO | tecnica.py |
| `/api/tecnica/formulas/<int:fid>/versiones/<int:vid>` | GET | AUTENTICADO | tecnica.py |
| `/api/tecnica/invima` | GET,POST | AUTENTICADO | tecnica.py |
| `/api/tecnica/invima/<int:rid>` | DELETE,PATCH | ADMIN | tecnica.py |
| `/api/tecnica/operacion-vivo` | GET | AUTENTICADO | tecnica.py |
| `/api/tecnica/productos-sin-invima` | GET | AUTENTICADO | tecnica.py |
| `/tecnica` | GET | AUTENTICADO | tecnica.py |
