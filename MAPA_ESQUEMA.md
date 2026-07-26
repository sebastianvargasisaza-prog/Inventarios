# Mapa del esquema · EOS

> **GENERADO** por `python scripts/generar_mapa_esquema.py` · no editar a mano.
> Sale del esquema REAL (corre las 378 migraciones en una BD temporal), así que no puede
> quedar desactualizado en silencio.

**269 tablas · 3470 columnas · 378 migraciones**

## Tablas del corazón

Si tocás una de estas, leé antes el CONTRACT del módulo dueño.

| Tabla | Qué es | Columnas | Escriben |
|---|---|---:|---|
| `movimientos` | kardex de MATERIA PRIMA · el stock es SUM(movimientos), nunca un cache | 26 | admin, animus, auto_plan_jobs, brd, calidad, compras, database, despachos, gerencia, inventario, programacion |
| `movimientos_mee` | kardex de ENVASES · idem, vía _get_mee_stock | 18 | admin, brd, calidad, compras, database, inventario, inventario_helpers, programacion |
| `formula_headers` | la receta maestra (cabecera) · `activo=0` = descontinuada, NUNCA DELETE | 30 | admin, auto_plan, auto_plan_jobs, brd, database, inventario, mig_121_formulas_data, mig_127_data, plan, portal |
| `formula_items` | la receta: % por MP · `porcentaje` es la verdad, `cantidad_g_por_lote` es derivada | 7 | admin, auto_plan_jobs, brd, database, inventario, mig_121_formulas_data, mig_127_data, plan |
| `produccion_programada` | el plan · `origen` separa lo que fijó el usuario de lo que sugiere la IA | 48 | admin, auto_plan, auto_plan_jobs, brd, database, mig_130_canonicos_data, mig_136_plan_limpio_data, mig_137_plan_denso_data, plan, programacion |
| `mbr_templates` | procedimiento maestro aprobado · INMUTABLE una vez aprobado (mig 109) | 17 | admin, brd, database, mig_121_formulas_data, mig_127_data |
| `mbr_pasos` | los pasos del procedimiento · inmutables si el MBR está aprobado | 11 | brd, database, mig_121_formulas_data, mig_127_data |
| `ebr_ejecuciones` | el legajo de UN lote real · inmutable si está liberado/rechazado (mig 111) | 34 | brd, database, programacion |
| `ebr_pasos_ejecutados` | ejecución paso a paso, con firma · una firma no se borra jamás | 19 | brd, programacion |
| `audit_log` | evidencia Part 11 · inmutable por trigger (mig 105) | 10 | admin, audit_helpers, auto_plan, auto_plan_jobs, calidad, clientes, core, database, inventario, maquila, plan, programacion |
| `e_signatures` | firmas electrónicas con snapshot de identidad | 14 | brd, firmas |
| `ordenes_compra` | las OC · el dinero | 27 | admin, compras, database, gerencia, inventario, plan, programacion |
| `maestro_mps` | maestro de materias primas · la identidad es el CÓDIGO, no el INCI | 16 | admin, auto_plan_jobs, brd, calidad, compras, database, inventario, mig_121_formulas_data, mig_127_data, programacion |
| `maestro_mee` | maestro de envases | 27 | admin, auto_plan_jobs, brd, compras, database, gerencia, inventario, inventario_helpers, programacion, seed_mee |
| `app_settings` | interruptores de negocio (modo inventario, gates, crons) · sin redeploy | 6 | admin, artes, auto_plan, calidad, database, http_helpers, index, inventario, plan, programacion |

## Tablas que escriben 4+ módulos

Acá nace el drift: si cinco módulos escriben la misma tabla, tarde o temprano uno lo
hace con otro criterio. Cada una debería tener UN dueño y que el resto delegue (M3).

| Tabla | Módulos que escriben |
|---|---|
| `audit_log` | admin, audit_helpers, auto_plan, auto_plan_jobs, calidad, clientes, core, database, inventario, maquila, plan, programacion |
| `movimientos` | admin, animus, auto_plan_jobs, brd, calidad, compras, database, despachos, gerencia, inventario, programacion |
| `solicitudes_compra` | admin, auto_plan, auto_plan_jobs, compras, database, gerencia, inventario, marketing, plan, programacion |
| `produccion_programada` | admin, auto_plan, auto_plan_jobs, brd, database, mig_130_canonicos_data, mig_136_plan_limpio_data, mig_137_plan_denso_data, plan, programacion |
| `maestro_mps` | admin, auto_plan_jobs, brd, calidad, compras, database, inventario, mig_121_formulas_data, mig_127_data, programacion |
| `maestro_mee` | admin, auto_plan_jobs, brd, compras, database, gerencia, inventario, inventario_helpers, programacion, seed_mee |
| `formula_headers` | admin, auto_plan, auto_plan_jobs, brd, database, inventario, mig_121_formulas_data, mig_127_data, plan, portal |
| `app_settings` | admin, artes, auto_plan, calidad, database, http_helpers, index, inventario, plan, programacion |
| `movimientos_mee` | admin, brd, calidad, compras, database, inventario, inventario_helpers, programacion |
| `formula_items` | admin, auto_plan_jobs, brd, database, inventario, mig_121_formulas_data, mig_127_data, plan |
| `solicitudes_compra_items` | admin, auto_plan, auto_plan_jobs, compras, inventario, plan, programacion |
| `ordenes_compra_items` | admin, compras, database, gerencia, inventario, plan, programacion |
| `ordenes_compra` | admin, compras, database, gerencia, inventario, plan, programacion |
| `producto_presentaciones` | admin, brd, database, inventario, plan, programacion |
| `calidad_micro_resultados` | calidad, coa_import, database, mig_246_micro_microlab_data, mig_248_micro_fechas_data, programacion |
| `areas_planta` | admin, auto_plan, database, inventario, plan, programacion |
| `stock_pt` | auto_plan_jobs, clientes, inventario, maquila, programacion |
| `sku_producto_map` | admin, auto_plan, database, plan, programacion |
| `sku_mee_config` | admin, auto_plan, auto_plan_jobs, database, programacion |
| `produccion_checklist` | admin, auto_plan, compras, inventario, programacion |
| `mbr_templates` | admin, brd, database, mig_121_formulas_data, mig_127_data |
| `animus_config` | animus, auto_plan_jobs, database, marketing, programacion |
| `users_passwords` | admin, core, database, mfa |
| `sku_planeacion_config` | auto_plan, database, plan, programacion |
| `proveedores` | compras, database, inventario, programacion |
| `producciones` | admin, database, inventario, programacion |
| `pedidos_b2b` | auto_plan_jobs, database, plan, portal |
| `pagos_influencers` | admin, compras, database, marketing |
| `mbr_pasos` | brd, database, mig_121_formulas_data, mig_127_data |
| `flujo_egresos` | compras, database, financiero, rrhh |
| `equipos_planta` | admin, calidad, database, programacion |
| `auto_plan_cron_state` | auto_plan, auto_plan_jobs, database, plan |
| `animus_shopify_orders` | auto_plan_jobs, financiero, marketing, shopify_client |

## Tablas que nadie toca (11)

Ni un INSERT ni un SELECT en todo el código. O son histórico que se conserva a
propósito, o son features muertas. Vale revisarlas antes de que confundan a alguien.

```
animus_instagram_comments, asistente_acciones_log, calendar_eventos_log, maquila_ingredientes, marketing_agentes_feedback, marketing_cmo_acciones, marketing_cmo_plan, marketing_outreach_log, notificaciones_outbox, turnos_operario, usuario_roles
```

## Todas las tablas

### `actividades_sala`

- **Columnas (11):** `id`, `area_id`, `operario_id`, `tipo`, `descripcion`, `produccion_id`, `inicio_at`, `fin_at`, `duracion_min`, `observaciones`, `creado_por`
- **PK:** `id`
- **Escriben:** programacion
- **Leen:** programacion
- **FK:** `produccion_id`→`produccion_programada.id`, `operario_id`→`operarios_planta.id`, `area_id`→`areas_planta.id`

### `acuerdos_calidad`

- **Columnas (14):** `id`, `tercero`, `tipo`, `documento_url`, `version`, `fecha_efectiva`, `fecha_renovacion`, `alcance`, `estado`, `ultima_auditoria`, `responsable`, `observaciones`, `creado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento

### `agent_memory`

- **Columnas (7):** `id`, `key`, `value`, `category`, `created_by`, `created_at`, `updated_at`
- **PK:** `id`
- **Escriben:** admin
- **Leen:** admin

### `alertas`

- **Columnas (7):** `id`, `material_id`, `material_nombre`, `stock_actual`, `stock_minimo`, `fecha`, `estado`
- **PK:** `id`
- **Escriben:** inventario
- **Leen:** inventario

### `alertas_silenciadas`

- **Columnas (8):** `id`, `tipo_alerta`, `codigo_referencia`, `motivo`, `silenciado_por`, `silenciado_at_utc`, `expira_at_utc`, `activo`
- **PK:** `id`
- **Escriben:** inventario
- **Leen:** inventario

### `andon_alertas`

- **Columnas (13):** `id`, `tipo`, `operario`, `produccion_id`, `area_codigo`, `descripcion`, `estado`, `ts_abierta`, `atendida_por`, `ts_atendida`, `resolucion`, `ts_resuelta`, `tenant_id`
- **PK:** `id`
- **Escriben:** auto_plan
- **Leen:** auto_plan, auto_plan_jobs

### `animus_caja_menor`

- **Columnas (10):** `id`, `fecha`, `tipo`, `concepto`, `monto`, `metodo`, `referencia`, `observaciones`, `registrado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** animus
- **Leen:** animus

### `animus_config`

- **Columnas (3):** `clave`, `valor`, `actualizado`
- **PK:** `clave`
- **Escriben:** animus, auto_plan_jobs, database, marketing, programacion
- **Leen:** animus, aseguramiento, auto_plan_jobs, comunicacion, database, hub, inventario, marketing, plan, programacion

### `animus_contenido_generado`

- **Columnas (9):** `id`, `sku`, `tipo`, `plataforma`, `tono`, `contenido`, `usado`, `generado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** animus
- **Leen:** animus

### `animus_conteos_asignados`

- **Columnas (11):** `id`, `sku`, `fecha_asignado`, `asignado_a`, `estado`, `cantidad_fisica`, `cantidad_esperada`, `diferencia`, `motivo_diferencia`, `contado_en`, `creado_en`
- **PK:** `id`
- **Escriben:** animus, auto_plan_jobs
- **Leen:** animus, auto_plan_jobs

### `animus_conteos_ciclicos`

- **Columnas (12):** `id`, `sku`, `producto_nombre`, `fecha_conteo`, `cantidad_shopify`, `cantidad_fisica`, `diferencia`, `explicacion`, `registrado_por`, `fecha_creacion`, `aplicado`, `movimiento_id_ajuste`
- **PK:** `id`
- **Escriben:** animus
- **Leen:** animus

### `animus_ghl_contacts`

- **Columnas (11):** `id`, `ghl_id`, `nombre`, `email`, `telefono`, `etiquetas`, `pipeline_etapa`, `valor_oportunidad`, `fuente`, `creado_en`, `synced_at`
- **PK:** `id`
- **Escriben:** animus, marketing
- **Leen:** animus, marketing

### `animus_ghl_oportunidades`

- **Columnas (9):** `id`, `ghl_id`, `contacto_nombre`, `pipeline`, `etapa`, `valor`, `estado`, `creado_en`, `synced_at`
- **PK:** `id`
- **Escriben:** —
- **Leen:** animus

### `animus_ghl_opportunities`

- **Columnas (15):** `id`, `ghl_id`, `ghl_contact_id`, `ghl_pipeline_id`, `ghl_stage_id`, `nombre`, `pipeline_nombre`, `stage_nombre`, `status`, `monetary_value`, `source`, `assigned_to`, `ghl_created_at`, `ghl_updated_at`, `synced_at`
- **PK:** `id`
- **Escriben:** marketing
- **Leen:** marketing

### `animus_instagram_comments`

- **Columnas (11):** `id`, `comment_id`, `post_id`, `autor_username`, `texto`, `publicado_en`, `sentiment`, `sentiment_score`, `sku_detectado`, `analizado_en`, `synced_at`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —

### `animus_instagram_posts`

- **Columnas (13):** `id`, `instagram_id`, `tipo`, `descripcion`, `url_media`, `url_permalink`, `likes`, `comentarios`, `alcance`, `impresiones`, `guardados`, `publicado_en`, `synced_at`
- **PK:** `id`
- **Escriben:** animus, marketing
- **Leen:** animus, marketing

### `animus_inventario_baseline`

- **Columnas (8):** `id`, `sku`, `descripcion`, `unidades_baseline`, `fecha_baseline`, `creado_por`, `observaciones`, `creado_en`
- **PK:** `id`
- **Escriben:** animus
- **Leen:** admin, animus, auto_plan_jobs

### `animus_inventario_movimientos`

- **Columnas (10):** `id`, `sku`, `tipo`, `cantidad`, `fecha`, `origen`, `referencia`, `motivo`, `usuario`, `creado_en`
- **PK:** `id`
- **Escriben:** animus
- **Leen:** admin, animus, auto_plan_jobs

### `animus_pqr`

- **Columnas (20):** `id`, `codigo`, `canal`, `contacto_nombre`, `contacto_email`, `contacto_telefono`, `ghl_contact_id`, `tipo`, `descripcion`, `prioridad`, `estado`, `asignado_a`, `respuesta`, `respondido_por`, `respondido_en`, `origen_inbox_id`, `creado_por`, `creado_en`, `actualizado_en`, `pedido_numero`
- **PK:** `id`
- **Escriben:** animus, aseguramiento, database
- **Leen:** animus, database

### `animus_shopify_customers`

- **Columnas (12):** `id`, `shopify_id`, `nombre`, `email`, `telefono`, `total_gastado`, `num_pedidos`, `ciudad`, `pais`, `tags`, `creado_en`, `synced_at`
- **PK:** `id`
- **Escriben:** —
- **Leen:** animus

### `animus_shopify_orders`

- **Columnas (21):** `id`, `shopify_id`, `nombre`, `email`, `total`, `moneda`, `estado`, `estado_pago`, `sku_items`, `unidades_total`, `ciudad`, `pais`, `creado_en`, `synced_at`, `discount_codes`, `subtotal`, `total_descuentos`, `flujo_synced`, `flujo_ingreso_id`, `tags`, `customer_tags`
- **PK:** `id`
- **Escriben:** auto_plan_jobs, financiero, marketing, shopify_client
- **Leen:** admin, animus, auto_plan, auto_plan_jobs, financiero, gerencia, hub, index, marketing, plan, programacion

### `app_settings`

- **Columnas (6):** `clave`, `valor`, `descripcion`, `actualizado_at_utc`, `actualizado_por`, `tenant_id`
- **PK:** `clave`
- **Escriben:** admin, artes, auto_plan, calidad, database, http_helpers, index, inventario, plan, programacion
- **Leen:** admin, artes, auto_plan_jobs, brd, calidad, compras, database, index, inventario, plan, programacion

### `area_eventos`

- **Columnas (10):** `id`, `area_id`, `tipo`, `estado_anterior`, `estado_nuevo`, `produccion_id`, `operario_id`, `usuario`, `nota`, `ts`
- **PK:** `id`
- **Escriben:** programacion
- **Leen:** programacion
- **FK:** `operario_id`→`operarios_planta.id`, `produccion_id`→`produccion_programada.id`, `area_id`→`areas_planta.id`

### `areas_planta`

- **Columnas (20):** `id`, `codigo`, `nombre`, `puede_producir`, `puede_envasar`, `marmita_ml`, `especial`, `estado`, `activo`, `orden`, `creado_en`, `tipo`, `requiere_limpieza_profunda`, `ultima_limpieza_profunda`, `zona`, `tenant_id`, `ocup_producto`, `ocup_operario`, `ocup_inicio`, `ocup_fase`
- **PK:** `id`
- **Escriben:** admin, auto_plan, database, inventario, plan, programacion
- **Leen:** admin, auto_plan, auto_plan_jobs, brd, calidad, espagiria, index, inventario, operario, plan, programacion, tecnica

### `artes_etiquetas`

- **Columnas (25):** `id`, `producto_nombre`, `presentacion_codigo`, `mee_codigo`, `tipo`, `version`, `estado`, `solicitado_por`, `solicitado_at`, `solicitud_notas`, `arte_aprobado`, `arte_aprobado_por`, `arte_aprobado_at`, `arte_signature_id`, `inci_revisado`, `drive_url`, `fisica_aprobada`, `fisica_aprobada_por`, `fisica_aprobada_at`, `fisica_signature_id`, `archivo`, `notas`, `rechazo_motivo`, `creado_at`, `empresa`
- **PK:** `id`
- **Escriben:** artes
- **Leen:** artes

### `aseguramiento_kpi_metas`

- **Columnas (12):** `id`, `codigo`, `nombre`, `descripcion`, `unidad`, `direccion`, `meta`, `umbral_amarillo`, `categoria`, `orden`, `activo`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento, database
- **Leen:** aseguramiento

### `asistente_acciones_log`

- **Columnas (8):** `id`, `ts`, `usuario`, `pregunta`, `tool_invocado`, `tool_args`, `tool_resultado`, `exitoso`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —

### `audit_log`

- **Columnas (10):** `id`, `usuario`, `accion`, `tabla`, `registro_id`, `detalle`, `ip`, `fecha`, `antes`, `despues`
- **PK:** `id`
- **Escriben:** admin, audit_helpers, auto_plan, auto_plan_jobs, calidad, clientes, core, database, inventario, maquila, plan, programacion
- **Leen:** admin, aseguramiento, auto_plan, auto_plan_jobs, brd, calidad, core, index, inventario, plan

### `audit_zero_error_runs`

- **Columnas (11):** `id`, `fecha`, `score_global`, `veredicto_global`, `score_real`, `veredicto_real`, `alta`, `media`, `baja`, `detalles_json`, `origen`
- **PK:** `id`
- **Escriben:** auto_plan_jobs
- **Leen:** admin

### `auditorias`

- **Columnas (12):** `id`, `tipo`, `ente_auditado`, `fecha_planeada`, `fecha_ejecutada`, `auditor`, `alcance`, `hallazgos_count`, `no_conformes`, `estado`, `informe_url`, `creado_en`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** aseguramiento, calidad

### `ausencias`

- **Columnas (10):** `id`, `empleado_id`, `tipo`, `fecha_inicio`, `fecha_fin`, `dias`, `estado`, `observaciones`, `aprobado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** rrhh
- **Leen:** hub, rrhh

### `auto_asignacion_log`

- **Columnas (10):** `id`, `produccion_id`, `ejecutado_at`, `ejecutado_por`, `area_asignada`, `tanque_asignado`, `area_envasado_asignada`, `operarios_json`, `score`, `razon`
- **PK:** `id`
- **Escriben:** auto_plan_jobs, programacion
- **Leen:** auto_plan_jobs

### `auto_plan_cron_state`

- **Columnas (8):** `id`, `habilitado`, `activado_por`, `activado_at`, `ultima_ejecucion_at`, `proxima_ejecucion_at`, `errores_consecutivos`, `notas`
- **PK:** `id`
- **Escriben:** auto_plan, auto_plan_jobs, database, plan
- **Leen:** auto_plan, auto_plan_jobs

### `auto_plan_runs`

- **Columnas (12):** `id`, `ejecutado_at`, `ejecutado_por`, `tipo`, `horizonte_dias`, `producciones_creadas`, `compras_creadas`, `alertas_criticas`, `emails_enviados`, `error`, `payload_json`, `duracion_ms`
- **PK:** `id`
- **Escriben:** auto_plan, auto_plan_jobs
- **Leen:** auto_plan, auto_plan_jobs

### `autoplan_decisiones`

- **Columnas (23):** `id`, `cliente`, `producto_nombre`, `fecha_decision`, `horizonte_dias`, `stock_kg`, `velocidad_uds_mes`, `ml_unidad`, `lote_size_kg`, `sugerencia_kg`, `sugerencia_fecha`, `sugerencia_cobertura_dias`, `motivo_ia`, `usuario`, `accion_usuario`, `accion_at`, `kg_real`, `fecha_real`, `comentario_usuario`, `modelo_ia`, `tokens_usados`, `confianza_ia`, `payload_completo`
- **PK:** `id`
- **Escriben:** database, plan
- **Leen:** plan

### `backup_log`

- **Columnas (8):** `id`, `started_at`, `completed_at`, `file_path`, `size_bytes`, `status`, `error`, `triggered_by`
- **PK:** `id`
- **Escriben:** backup
- **Leen:** admin, backup

### `bienestar_capacitaciones`

- **Columnas (16):** `id`, `titulo`, `descripcion`, `material_tipo`, `material_url`, `material_notas`, `asignado_a`, `asignado_por`, `fecha_asignacion`, `fecha_limite`, `estado`, `nota_minima`, `nota_obtenida`, `intentos`, `completada_en`, `creado_en`
- **PK:** `id`
- **Escriben:** bienestar
- **Leen:** bienestar

### `bienestar_capacitaciones_intentos`

- **Columnas (9):** `id`, `capacitacion_id`, `empleado_username`, `preguntas_json`, `respuestas_json`, `evaluacion_json`, `nota`, `iniciado_en`, `terminado_en`
- **PK:** `id`
- **Escriben:** bienestar
- **Leen:** bienestar
- **FK:** `capacitacion_id`→`bienestar_capacitaciones.id`

### `calendar_eventos_log`

- **Columnas (11):** `id`, `evento_id_externo`, `titulo`, `fecha`, `descripcion`, `kg_detectados`, `producto_matcheado`, `score_match`, `estado`, `notas`, `ts_leido`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —

### `calibraciones`

- **Columnas (11):** `id`, `instrumento`, `codigo`, `ubicacion`, `fecha_ultima`, `fecha_proxima`, `responsable`, `empresa`, `estado`, `certificado`, `observaciones`
- **PK:** `id`
- **Escriben:** database
- **Leen:** calidad, database, espagiria, hub

### `calibraciones_instrumentos`

- **Columnas (11):** `id`, `instrumento`, `codigo`, `ubicacion`, `fecha_ultima`, `fecha_proxima`, `responsable`, `empresa`, `estado`, `certificado`, `observaciones`
- **PK:** `id`
- **Escriben:** calidad, database
- **Leen:** calidad

### `calidad_fisicoquimica_resultados`

- **Columnas (20):** `id`, `lote`, `producto_nombre`, `categoria`, `n_referencia`, `fecha_muestreo`, `fecha_analisis`, `parametro`, `metodo`, `resultado`, `unidad`, `valor_referencia`, `estado`, `laboratorio`, `analista`, `archivo_coa_url`, `ebr_id`, `observaciones`, `creado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** calidad, coa_import, database
- **Leen:** calidad, coa_import, database

### `calidad_kpi_metas`

- **Columnas (13):** `id`, `codigo`, `nombre`, `descripcion`, `unidad`, `direccion`, `meta`, `umbral_amarillo`, `categoria`, `orden`, `activo`, `actualizado_por`, `actualizado_at`
- **PK:** `id`
- **Escriben:** calidad, database
- **Leen:** calidad, database

### `calidad_micro_resultados`

- **Columnas (23):** `id`, `lote`, `producto_nombre`, `fecha_muestreo`, `fecha_analisis`, `microorganismo`, `valor`, `valor_texto`, `unidad`, `estado`, `laboratorio`, `analista`, `metodo`, `observaciones`, `oos_id`, `creado_por`, `creado_en`, `envasado_id`, `deadline_resultado`, `archivo_coa_url`, `ebr_id`, `categoria`, `n_referencia`
- **PK:** `id`
- **Escriben:** calidad, coa_import, database, mig_246_micro_microlab_data, mig_248_micro_fechas_data, programacion
- **Leen:** auto_plan, brd, calidad, coa_import, mig_246_micro_microlab_data, programacion

### `calidad_micro_specs`

- **Columnas (10):** `id`, `producto_nombre`, `microorganismo`, `unidad`, `limite_industria`, `meta_lab`, `tipo_limite`, `metodo_referencia`, `activa`, `creado_en`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** calidad

### `calidad_micro_specs_default`

- **Columnas (7):** `id`, `microorganismo`, `unidad`, `limite_industria`, `meta_lab`, `tipo_limite`, `descripcion`
- **PK:** `id`
- **Escriben:** database
- **Leen:** calidad

### `calidad_oos`

- **Columnas (23):** `id`, `codigo`, `origen`, `lote`, `producto`, `parametro`, `valor_obtenido`, `valor_obtenido_texto`, `valor_esperado_texto`, `limite_violado`, `fecha_deteccion`, `fecha_objetivo_cierre`, `fecha_cierre`, `estado`, `accion_inmediata`, `causa_raiz`, `disposicion`, `aprobado_por`, `fecha_aprobacion`, `capa_id`, `creado_por`, `creado_en`, `aprobado_gerencia`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** aseguramiento, brd, calidad, espagiria
- **FK:** `capa_id`→`capa_desviaciones.id`

### `calidad_registros`

- **Columnas (10):** `id`, `fecha`, `tarea_id`, `usuario`, `estado`, `hora_inicio`, `hora_fin`, `valor_registrado`, `observaciones`, `created_at`
- **PK:** `id`
- **Escriben:** calidad, inventario
- **Leen:** calidad

### `calidad_sistema_agua`

- **Columnas (15):** `id`, `fecha`, `hora`, `punto_muestreo`, `tipo_agua`, `ph`, `conductividad_us_cm`, `toc_ppb`, `microorganismos_ufc_ml`, `cloro_residual_ppm`, `temperatura_c`, `estado`, `observaciones`, `operador`, `creado_en`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** auto_plan_jobs, calidad, espagiria

### `calidad_tareas`

- **Columnas (11):** `id`, `nombre`, `categoria`, `hora_objetivo`, `hora_limite`, `responsable`, `procedimiento`, `requiere_valor`, `unidad_valor`, `activa`, `orden`
- **PK:** `id`
- **Escriben:** database
- **Leen:** calidad, database

### `capa_acciones`

- **Columnas (13):** `id`, `nc_id`, `tipo`, `descripcion`, `responsable`, `fecha_compromiso`, `fecha_ejecucion`, `evidencia_url`, `efectiva`, `verificada_por`, `fecha_verificacion`, `estado`, `creado_en`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** aseguramiento, auto_plan_jobs, calidad

### `capa_desviaciones`

- **Columnas (20):** `id`, `codigo`, `tipo`, `titulo`, `descripcion`, `producto_relacionado`, `lote`, `severidad`, `fecha_apertura`, `fecha_objetivo`, `fecha_cierre`, `responsable`, `accion_inmediata`, `causa_raiz`, `accion_correctiva`, `accion_preventiva`, `evidencia_url`, `estado`, `creado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** compliance
- **Leen:** bienestar, compliance

### `capacitaciones`

- **Columnas (9):** `id`, `nombre`, `tipo`, `fecha`, `duracion_horas`, `instructor`, `empresa`, `obligatoria`, `creado_en`
- **PK:** `id`
- **Escriben:** database, rrhh
- **Leen:** database, rrhh

### `capacitaciones_empleados`

- **Columnas (6):** `id`, `capacitacion_id`, `empleado_id`, `completado`, `fecha_completado`, `calificacion`
- **PK:** `id`
- **Escriben:** database, rrhh
- **Leen:** database, rrhh

### `cargos_fijos`

- **Columnas (14):** `id`, `concepto`, `beneficiario`, `categoria`, `monto`, `es_variable`, `dia_corte`, `medio_pago`, `dato_pago`, `banco`, `notas`, `activo`, `creado_por`, `created_at`
- **PK:** `id`
- **Escriben:** compras
- **Leen:** compras

### `cargos_fijos_pagos`

- **Columnas (12):** `id`, `cargo_fijo_id`, `periodo`, `monto`, `fecha_limite`, `estado`, `medio_pago`, `dato_pago`, `referencia_pago`, `pagado_at`, `pagado_por`, `created_at`
- **PK:** `id`
- **Escriben:** compras
- **Leen:** auto_plan_jobs, compras

### `cc_reviews`

- **Columnas (17):** `id`, `mov_id`, `lote`, `codigo_mp`, `coa_ok`, `lote_coincide`, `coa_vigente`, `ficha_ok`, `solubilidad`, `resultado_aql`, `observaciones_aql`, `muestra_retencion`, `observaciones`, `firmante`, `estado_final`, `fecha`, `ip`
- **PK:** `id`
- **Escriben:** inventario
- **Leen:** calidad

### `certificado_analisis_mp`

- **Columnas (40):** `id`, `mov_id`, `lote`, `codigo_mp`, `nombre_mp`, `lote_proveedor`, `cantidad_recibida`, `proveedor`, `fecha_recepcion`, `fecha_analisis`, `aspecto_spec`, `aspecto_result`, `aspecto_cumple`, `aspecto_obs`, `ph_spec`, `ph_result`, `ph_cumple`, `ph_obs`, `densidad_spec`, `densidad_result`, `densidad_cumple`, `densidad_obs`, `solubilidad_spec`, `solubilidad_result`, `solubilidad_cumple`, `solubilidad_obs`, `viscosidad_spec`, `viscosidad_result`, `viscosidad_cumple`, `viscosidad_obs`, `resultado`, `observaciones_generales`, `fecha_vencimiento`, `responsable_analisis`, `realiza_fecha`, `aprobo_por`, `aprobo_fecha`, `creado_por`, `creado_en`, `anulado`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** calidad

### `chat_messages`

- **Columnas (12):** `id`, `thread_id`, `sender`, `contenido`, `tipo_mensaje`, `metadata_json`, `tarea_operativa_id`, `compromiso_id`, `reply_to_id`, `creado_en`, `editado_en`, `eliminado`
- **PK:** `id`
- **Escriben:** chat
- **Leen:** chat

### `chat_reactions`

- **Columnas (5):** `id`, `message_id`, `username`, `emoji`, `creado_en`
- **PK:** `id`
- **Escriben:** chat
- **Leen:** chat

### `chat_thread_members`

- **Columnas (7):** `id`, `thread_id`, `username`, `rol`, `silenciado`, `ultimo_leido_id`, `agregado_en`
- **PK:** `id`
- **Escriben:** chat
- **Leen:** chat

### `chat_threads`

- **Columnas (9):** `id`, `tipo`, `nombre`, `creado_por`, `creado_en`, `ultimo_mensaje_id`, `ultimo_mensaje_en`, `ultimo_mensaje_preview`, `activo`
- **PK:** `id`
- **Escriben:** chat
- **Leen:** chat

### `chat_user_presence`

- **Columnas (6):** `username`, `last_heartbeat`, `estado`, `last_thread_visto`, `display_name`, `avatar_color`
- **PK:** `username`
- **Escriben:** chat
- **Leen:** chat

### `checklist_plantillas`

- **Columnas (10):** `id`, `producto_nombre`, `item_tipo`, `descripcion`, `proveedor_default`, `dias_anticipacion`, `obligatorio`, `orden`, `creado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** database
- **Leen:** programacion

### `clientes`

- **Columnas (24):** `id`, `codigo`, `nombre`, `empresa`, `tipo`, `contacto`, `email`, `telefono`, `nit`, `condiciones_pago`, `descuento_pct`, `activo`, `fecha_creacion`, `observaciones`, `nivel_aliado`, `semaforo`, `fecha_vinculacion`, `ciudad`, `categoria_profesional`, `canal_captacion`, `redes_sociales`, `notas_seguimiento`, `monto_credito_cop`, `dias_credito`
- **PK:** `id`
- **Escriben:** clientes, database
- **Leen:** aseguramiento, auto_plan_jobs, clientes, contabilidad, financiero, gerencia, hub, inventario, maquila, programacion

### `clientes_b2b_envases`

- **Columnas (7):** `id`, `cliente_id`, `envase_codigo`, `envase_descripcion`, `activo`, `notas`, `creado_at`
- **PK:** `id`
- **Escriben:** plan
- **Leen:** plan, portal

### `clientes_b2b_maestro`

- **Columnas (10):** `cliente_id`, `cliente_nombre`, `contacto`, `telefono`, `email`, `activo`, `tipo`, `notas`, `creado_at_utc`, `actualizado_at_utc`
- **PK:** `cliente_id`
- **Escriben:** database, plan
- **Leen:** plan

### `clientes_maquila`

- **Columnas (13):** `id`, `nombre`, `nit_cedula`, `email`, `telefono`, `es_marca_propia`, `empresa_grupo`, `comparte_formula_con`, `margen_seguridad_pct`, `activo`, `notas`, `creado_en`, `actualizado_en`
- **PK:** `id`
- **Escriben:** auto_plan, database
- **Leen:** auto_plan, espagiria, plan

### `coa_resultados`

- **Columnas (17):** `id`, `lote`, `codigo_mp`, `material_nombre`, `parametro`, `unidad`, `valor_obtenido`, `valor_min_spec`, `valor_max_spec`, `conforme`, `metodo_ensayo`, `analista`, `fecha_analisis`, `equipo_id`, `observaciones`, `decision`, `creado_en`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** aseguramiento, calidad

### `cola_liberacion`

- **Columnas (15):** `id`, `envasado_id`, `producto_nombre`, `lote`, `presentacion_etiqueta`, `unidades`, `fecha_envasado`, `fecha_min_liberacion`, `estado`, `micro_resultado_id`, `disposicion`, `aprobado_por`, `aprobado_at`, `notas`, `creado_en`
- **PK:** `id`
- **Escriben:** programacion
- **Leen:** auto_plan, auto_plan_jobs, calidad, index, programacion
- **FK:** `envasado_id`→`produccion_envasado.id`

### `comites_actas`

- **Columnas (11):** `id`, `fecha`, `plataforma`, `titulo`, `asistentes_json`, `transcripcion`, `transcripcion_url`, `parseada`, `tareas_creadas`, `registrado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** comunicacion
- **Leen:** comunicacion, espagiria

### `compras_fast_track_config`

- **Columnas (7):** `id`, `categoria`, `monto_max_cop`, `activo`, `configurado_por`, `configurado_at`, `notas`
- **PK:** `id`
- **Escriben:** compras, database
- **Leen:** compras

### `comprobantes_pago`

- **Columnas (25):** `id`, `numero_ce`, `anio`, `fecha_emision`, `pago_oc_id`, `numero_oc`, `beneficiario_nombre`, `beneficiario_cedula`, `beneficiario_banco`, `beneficiario_cuenta`, `beneficiario_tipo_cta`, `beneficiario_ciudad`, `subtotal`, `iva`, `iva_pct`, `retefuente`, `retefuente_pct`, `retica`, `retica_pct`, `total_pagado`, `medio_pago`, `observaciones`, `pagado_por`, `empresa`, `pdf_archivo`
- **PK:** `id`
- **Escriben:** compras, comprobante_pago
- **Leen:** admin, compras, contabilidad, marketing
- **FK:** `pago_oc_id`→`pagos_oc.id`

### `comprobantes_seq`

- **Columnas (2):** `anio`, `ultimo`
- **PK:** `anio`
- **Escriben:** comprobante_pago
- **Leen:** comprobante_pago

### `compromisos`

- **Columnas (12):** `id`, `descripcion`, `responsable`, `area`, `fecha_limite`, `estado`, `prioridad`, `origen`, `empresa`, `fecha_creacion`, `fecha_cierre`, `notas`
- **PK:** `id`
- **Escriben:** database, hub
- **Leen:** animus, hub

### `config_facturacion`

- **Columnas (4):** `empresa`, `anio`, `tipo`, `siguiente`
- **PK:** `empresa`, `anio`, `tipo`
- **Escriben:** contabilidad
- **Leen:** contabilidad

### `conteo_ciclico_calendario`

- **Columnas (16):** `id`, `fecha`, `material_id`, `material_nombre`, `categoria_abc`, `asignado_a`, `stock_esperado_g`, `stock_real_g`, `diferencia_g`, `estado`, `iniciado_at`, `terminado_at`, `iniciado_por`, `terminado_por`, `notas`, `generado_por`
- **PK:** `id`
- **Escriben:** auto_plan
- **Leen:** auto_plan

### `conteo_ciclico_config`

- **Columnas (8):** `id`, `material_id`, `categoria_abc`, `frecuencia_dias`, `ultimo_conteo_fecha`, `ultimo_conteo_diferencia`, `requiere_validacion`, `actualizado_en`
- **PK:** `id`
- **Escriben:** auto_plan
- **Leen:** auto_plan

### `conteo_items`

- **Columnas (17):** `id`, `conteo_id`, `codigo_mp`, `nombre_mp`, `stock_sistema`, `stock_fisico`, `diferencia`, `lote`, `zona`, `ajuste_aplicado`, `observaciones`, `estanteria`, `causa_diferencia`, `valor_diferencia`, `requiere_gerencia`, `aprobado_gerencia`, `aprobado_gerencia_por`
- **PK:** `id`
- **Escriben:** admin, database, inventario
- **Leen:** database, inventario

### `conteos_fisicos`

- **Columnas (12):** `id`, `numero`, `fecha_inicio`, `fecha_cierre`, `estado`, `responsable`, `observaciones`, `total_items`, `items_diferencia`, `aprobado_por`, `estanteria`, `tipo_conteo`
- **PK:** `id`
- **Escriben:** inventario
- **Leen:** inventario

### `control_cambios`

- **Columnas (36):** `id`, `codigo`, `fecha_solicitud`, `solicitado_por`, `tipo`, `titulo`, `descripcion`, `justificacion`, `impacto_bpm`, `impacto_regulatorio`, `areas_afectadas`, `severidad`, `evaluado_por`, `evaluado_at`, `evaluacion_descripcion`, `aprobado_por`, `aprobado_at`, `aprobacion_observaciones`, `requiere_invima`, `notificacion_invima_at`, `notificacion_invima_ref`, `plan_implementacion`, `fecha_implementacion_propuesta`, `responsable_implementacion`, `implementado_at`, `implementado_por`, `verificacion_post`, `verificado_por`, `verificado_at`, `verificacion_ok`, `estado`, `fecha_cierre`, `cerrado_por`, `observaciones_cierre`, `creado_en`, `actualizado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento, auto_plan_jobs, index

### `control_cambios_eventos`

- **Columnas (8):** `id`, `cambio_id`, `evento_tipo`, `estado_anterior`, `estado_nuevo`, `usuario`, `comentario`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento
- **FK:** `cambio_id`→`control_cambios.id`

### `cotizaciones`

- **Columnas (16):** `id`, `ronda_id`, `proveedor`, `fecha_solicitud`, `fecha_recibida`, `valor_total`, `condiciones`, `descripcion`, `tiempo_entrega_dias`, `ganadora`, `numero_oc`, `archivo`, `creado_por`, `estado`, `codigo_mp`, `cantidad_g`
- **PK:** `id`
- **Escriben:** compras
- **Leen:** compras

### `cron_alerts_sent`

- **Columnas (4):** `tipo_alerta`, `registro_id`, `ultima_notif`, `count_notifs`
- **PK:** `tipo_alerta`, `registro_id`
- **Escriben:** auto_plan_jobs
- **Leen:** auto_plan_jobs

### `cron_jobs_health`

- **Columnas (5):** `job_name`, `errores_consecutivos`, `ultimo_error_at`, `ultimo_error_msg`, `notificado_at`
- **PK:** `job_name`
- **Escriben:** auto_plan_jobs
- **Leen:** auto_plan_jobs

### `cron_jobs_runs`

- **Columnas (7):** `id`, `job_name`, `ejecutado_at`, `duracion_ms`, `ok`, `resultado_json`, `error`
- **PK:** `id`
- **Escriben:** auto_plan, auto_plan_jobs, database
- **Leen:** admin, auto_plan, auto_plan_jobs, database

### `cron_locks`

- **Columnas (3):** `job_name`, `locked_at`, `locked_by`
- **PK:** `job_name`
- **Escriben:** auto_plan_jobs, plan
- **Leen:** auto_plan_jobs, plan

### `cronograma_ejecuciones`

- **Columnas (9):** `id`, `cronograma_id`, `fecha_planeada`, `fecha_real`, `ejecutado_por`, `evidencia_url`, `observaciones`, `estado`, `creado_en`
- **PK:** `id`
- **Escriben:** compliance
- **Leen:** aseguramiento, compliance
- **FK:** `cronograma_id`→`cronogramas_bpm.id`

### `cronogramas_bpm`

- **Columnas (9):** `id`, `codigo`, `nombre`, `descripcion`, `frecuencia`, `ejecuciones_year_objetivo`, `responsable`, `activo`, `creado_en`
- **PK:** `id`
- **Escriben:** database
- **Leen:** aseguramiento, compliance

### `db_health_log`

- **Columnas (7):** `id`, `fecha`, `integrity`, `db_size_kb`, `wal_size_kb`, `error`, `origen`
- **PK:** `id`
- **Escriben:** admin
- **Leen:** admin

### `despachos`

- **Columnas (8):** `id`, `numero`, `numero_pedido`, `cliente_id`, `fecha`, `operador`, `observaciones`, `estado`
- **PK:** `id`
- **Escriben:** clientes, maquila
- **Leen:** aseguramiento, clientes, gerencia, inventario, maquila, programacion

### `despachos_items`

- **Columnas (7):** `id`, `numero_despacho`, `sku`, `descripcion`, `lote_pt`, `cantidad`, `precio_unitario`
- **PK:** `id`
- **Escriben:** clientes, maquila
- **Leen:** aseguramiento, inventario, maquila, programacion

### `despeje_linea_checklist`

- **Columnas (11):** `id`, `area_id`, `area_codigo`, `marcado_por`, `ts`, `item1_sin_etiquetas`, `item2_sin_producto_suelto`, `item3_equipos_lavados`, `item4_registros_archivados`, `item5_sala_vacia`, `observaciones`
- **PK:** `id`
- **Escriben:** auto_plan
- **Leen:** auto_plan, brd

### `desviaciones`

- **Columnas (33):** `id`, `codigo`, `fecha_deteccion`, `hora_deteccion`, `detectado_por`, `tipo`, `area_origen`, `descripcion`, `contencion_inmediata`, `impacto_producto`, `lotes_afectados`, `clasificacion`, `clasificado_por`, `clasificado_at`, `justificacion_clasificacion`, `metodo_investigacion`, `causa_raiz_descripcion`, `investigado_por`, `investigacion_at`, `capa_descripcion`, `capa_responsable`, `capa_fecha_limite`, `capa_implementado_at`, `verificacion_efectividad`, `verificado_at`, `verificado_por`, `efectividad_ok`, `estado`, `fecha_cierre`, `cerrado_por`, `observaciones_cierre`, `creado_en`, `actualizado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento, auto_plan_jobs, brd, espagiria

### `desviaciones_eventos`

- **Columnas (8):** `id`, `desviacion_id`, `evento_tipo`, `estado_anterior`, `estado_nuevo`, `usuario`, `comentario`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento
- **FK:** `desviacion_id`→`desviaciones.id`

### `documentos_regulados`

- **Columnas (20):** `id`, `entidad`, `codigo`, `producto_nombre`, `lote`, `tipo_doc`, `formato`, `titulo`, `url`, `ref_tabla`, `ref_id`, `mov_id`, `firma_id`, `generado_por`, `generado_at`, `anulado`, `r2_key`, `r2_at`, `r2_sha256`, `r2_bytes`
- **PK:** `id`
- **Escriben:** audit_helpers, r2_storage
- **Leen:** calidad, r2_storage

### `e_signatures`

- **Columnas (14):** `id`, `record_table`, `record_id`, `meaning`, `signer_username`, `signer_full_name`, `signer_cedula`, `signer_cargo`, `signed_at_utc`, `ip`, `auth_factor`, `comment`, `record_hash`, `signature_hash`
- **PK:** `id`
- **Escriben:** brd, firmas
- **Leen:** artes, brd, calidad, firmas, inventario

### `ebr_ajustes_mp`

- **Columnas (7):** `id`, `ebr_id`, `material`, `cantidad_g`, `motivo`, `registrado_por`, `registrado_at_utc`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd

### `ebr_artes_codificacion`

- **Columnas (11):** `id`, `ebr_id`, `descripcion`, `codigo_lote`, `codigo_vencimiento`, `aprobado_por`, `aprobado_at_utc`, `e_sign_id`, `creado_por`, `creado_at_utc`, `notas`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd
- **FK:** `ebr_id`→`ebr_ejecuciones.id`

### `ebr_conciliacion_material`

- **Columnas (14):** `id`, `ebr_id`, `tipo`, `material_codigo`, `material_nombre`, `lote_material`, `cant_requerida`, `cant_recibida`, `cant_devuelta`, `cant_utilizada`, `registrado_por`, `registrado_at_utc`, `e_sign_id`, `notas`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd
- **FK:** `ebr_id`→`ebr_ejecuciones.id`

### `ebr_correcciones`

- **Columnas (8):** `id`, `ebr_id`, `campo_afectado`, `motivo`, `descripcion`, `registrado_por`, `registrado_at_utc`, `signature_id`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd

### `ebr_despeje_items`

- **Columnas (11):** `id`, `ebr_id`, `item_idx`, `item_texto`, `cumple`, `observaciones`, `registrado_por`, `registrado_at_utc`, `etapa`, `verificado_por`, `verificado_at_utc`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd
- **FK:** `ebr_id`→`ebr_ejecuciones.id`

### `ebr_despeje_linea`

- **Columnas (11):** `id`, `ebr_id`, `area_limpia`, `sin_producto_anterior`, `equipos_limpios`, `documentacion_ok`, `conforme`, `observaciones`, `realizado_por`, `realizado_at_utc`, `e_sign_id`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd, tecnica
- **FK:** `ebr_id`→`ebr_ejecuciones.id`

### `ebr_ejecuciones`

- **Columnas (34):** `id`, `mbr_template_id`, `mbr_version`, `produccion_id`, `lote`, `estado`, `iniciado_por`, `iniciado_at_utc`, `completado_at_utc`, `liberado_por`, `liberado_at_utc`, `liberado_signature_id`, `rechazado_motivo`, `cantidad_objetivo_g`, `cantidad_real_g`, `yield_pct`, `notas`, `numero_op`, `lote_codigo`, `operario`, `observaciones`, `tiempo_total_min`, `rechazado_at_utc`, `fase`, `densidad_g_ml`, `ml_envasable`, `unidades_teoricas`, `unidades_buenas_real`, `yield_uds_pct`, `area_codigo`, `aprobado_dt_por`, `aprobado_dt_at_utc`, `aprobado_dt_signature_id`, `envases_descontados_at`
- **PK:** `id`
- **Escriben:** brd, database, programacion
- **Leen:** auto_plan, brd, calidad, database, index, operario, plan, portal, programacion, tecnica
- **FK:** `mbr_template_id`→`mbr_templates.id`

### `ebr_envasado_unidades`

- **Columnas (8):** `id`, `ebr_id`, `presentacion_codigo`, `etiqueta`, `volumen_ml`, `unidades`, `registrado_por`, `registrado_at_utc`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd

### `ebr_envase_materiales`

- **Columnas (12):** `id`, `ebr_id`, `lote_envasado`, `material_codigo`, `material_nombre`, `lote_material`, `requerida`, `devuelta`, `utilizada`, `averiada`, `creado_por`, `creado_at`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd

### `ebr_observaciones`

- **Columnas (5):** `id`, `ebr_id`, `descripcion`, `registrado_por`, `registrado_at_utc`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd
- **FK:** `ebr_id`→`ebr_ejecuciones.id`

### `ebr_pasos_ejecutados`

- **Columnas (19):** `id`, `ebr_id`, `mbr_paso_id`, `orden`, `descripcion`, `tipo_paso`, `equipo_requerido`, `requiere_e_sign`, `requiere_qc`, `estado`, `operario_username`, `iniciado_at_utc`, `completado_at_utc`, `observaciones`, `e_sign_id`, `qc_username`, `qc_e_sign_id`, `desviacion_id`, `fase`
- **PK:** `id`
- **Escriben:** brd, programacion
- **Leen:** brd, operario, tecnica
- **FK:** `ebr_id`→`ebr_ejecuciones.id`

### `ebr_pesajes`

- **Columnas (17):** `id`, `ebr_id`, `ebr_paso_id`, `material_id`, `material_nombre`, `cantidad_teorica_g`, `cantidad_real_g`, `delta_g`, `delta_pct`, `lote_mp`, `pesado_por`, `pesado_at_utc`, `e_sign_id`, `notas`, `verificado_por`, `verificado_at_utc`, `verificado_e_sign_id`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** auto_plan, brd
- **FK:** `ebr_id`→`ebr_ejecuciones.id`

### `ebr_precauciones`

- **Columnas (6):** `id`, `ebr_id`, `tipo`, `descripcion`, `registrado_por`, `registrado_at_utc`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd
- **FK:** `ebr_id`→`ebr_ejecuciones.id`

### `ebr_presentaciones_manual`

- **Columnas (11):** `id`, `ebr_id`, `presentacion`, `cliente`, `volumen_ml`, `envase_codigo`, `unidades`, `area`, `lote`, `creado_por`, `creado_at`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd

### `ebr_registros_fisicos`

- **Columnas (8):** `id`, `ebr_id`, `descripcion`, `tipo`, `archivo_nombre`, `archivo_b64`, `registrado_por`, `registrado_at_utc`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd
- **FK:** `ebr_id`→`ebr_ejecuciones.id`

### `email_destinatarios_config`

- **Columnas (11):** `id`, `rol`, `nombre`, `email`, `recibe_resumen_diario`, `recibe_alertas_criticas`, `recibe_compras_aprob`, `recibe_calidad`, `recibe_agenda_personal`, `activo`, `actualizado_en`
- **PK:** `id`
- **Escriben:** auto_plan, database
- **Leen:** auto_plan, auto_plan_jobs

### `empleados`

- **Columnas (25):** `id`, `codigo`, `nombre`, `apellido`, `cedula`, `cargo`, `area`, `empresa`, `tipo_contrato`, `fecha_ingreso`, `fecha_fin_contrato`, `estado`, `salario_base`, `eps`, `afp`, `arl`, `caja_compensacion`, `email`, `telefono`, `nivel_riesgo`, `observaciones`, `creado_en`, `banco`, `numero_cuenta`, `tipo_cuenta`
- **PK:** `id`
- **Escriben:** database, rrhh
- **Leen:** bienestar, contabilidad, database, financiero, gerencia, hub, rrhh

### `empleados_documentos`

- **Columnas (12):** `id`, `empleado_id`, `tipo`, `nombre`, `archivo_url`, `archivo_data`, `mime_type`, `fecha_emision`, `fecha_vencimiento`, `observaciones`, `cargado_por`, `fecha_carga`
- **PK:** `id`
- **Escriben:** rrhh
- **Leen:** rrhh

### `envasado`

- **Columnas (14):** `id`, `produccion_id`, `lote`, `producto`, `presentacion`, `batch_g`, `unidades`, `envase_codigo`, `tapa_codigo`, `operador`, `fecha`, `estado`, `observaciones`, `area_codigo`
- **PK:** `id`
- **Escriben:** inventario
- **Leen:** auto_plan, brd, database, inventario

### `eos_leads`

- **Columnas (12):** `id`, `nombre`, `email`, `telefono`, `empresa`, `mensaje`, `fuente`, `payload_raw`, `estado`, `owner`, `notas`, `creado_en`
- **PK:** `id`
- **Escriben:** comercial
- **Leen:** comercial

### `equipo_limpieza_log`

- **Columnas (13):** `id`, `equipo_codigo`, `lote_anterior`, `lote_siguiente`, `tipo_limpieza`, `operario_username`, `operario_e_sign_id`, `qc_username`, `qc_e_sign_id`, `visual_ok`, `iniciado_at_utc`, `completado_at_utc`, `observaciones`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd

### `equipos_cronograma`

- **Columnas (11):** `id`, `equipo_codigo`, `anio`, `mes`, `tipo_actividad`, `estado`, `fecha_completado`, `completado_por`, `evento_id`, `observaciones`, `creado_en`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** calidad

### `equipos_eventos`

- **Columnas (14):** `id`, `equipo_codigo`, `tipo_evento`, `fecha`, `fecha_proxima`, `estado`, `responsable`, `empresa_externa`, `certificado_url`, `resultado`, `observaciones`, `creado_por`, `creado_en`, `numero_oc`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** aseguramiento, auto_plan_jobs, calidad, espagiria

### `equipos_planta`

- **Columnas (14):** `id`, `codigo`, `nombre`, `area_codigo`, `ubicacion_raw`, `tipo`, `capacidad_raw`, `capacidad_litros`, `capacidad_kg`, `estado_operacional`, `activo`, `notas`, `creado_en`, `actualizado_en`
- **PK:** `id`
- **Escriben:** admin, calidad, database, programacion
- **Leen:** admin, aseguramiento, auto_plan, auto_plan_jobs, calidad, espagiria, programacion

### `especificaciones_mp`

- **Columnas (12):** `id`, `codigo_mp`, `parametro`, `unidad`, `valor_min`, `valor_max`, `metodo_ensayo`, `obligatorio`, `tipo`, `farmacopea_ref`, `creado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** calidad

### `estabilidades`

- **Columnas (14):** `id`, `producto`, `lote_piloto`, `condicion`, `tiempo_dias`, `tiempo_etiqueta`, `fecha_inicio`, `fecha_evaluacion`, `parametros_json`, `conforme`, `observaciones`, `analista`, `estado`, `creado_en`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** calidad

### `estacionalidad_meses`

- **Columnas (4):** `mes`, `mult_auto`, `mult_override`, `actualizado_at`
- **PK:** `mes`
- **Escriben:** database, programacion
- **Leen:** database, programacion

### `evaluaciones`

- **Columnas (13):** `id`, `empleado_id`, `periodo`, `evaluador`, `puntaje_total`, `puntaje_calidad`, `puntaje_asistencia`, `puntaje_actitud`, `puntaje_conocimiento`, `puntaje_productividad`, `comentarios`, `estado`, `creado_en`
- **PK:** `id`
- **Escriben:** database, rrhh
- **Leen:** rrhh

### `facturas`

- **Columnas (19):** `id`, `numero`, `tipo`, `numero_pedido`, `cliente_id`, `cliente_nombre`, `cliente_nit`, `empresa`, `fecha_emision`, `fecha_vencimiento`, `subtotal`, `descuento`, `iva_pct`, `iva_valor`, `total`, `estado`, `notas`, `creado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** contabilidad, maquila
- **Leen:** auto_plan_jobs, contabilidad, maquila

### `facturas_items`

- **Columnas (8):** `id`, `numero_factura`, `sku`, `descripcion`, `cantidad`, `precio_unitario`, `descuento_pct`, `subtotal`
- **PK:** `id`
- **Escriben:** contabilidad, maquila
- **Leen:** contabilidad

### `facturas_pagos`

- **Columnas (8):** `id`, `numero_factura`, `fecha`, `monto`, `medio`, `referencia`, `registrado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** contabilidad
- **Leen:** contabilidad

### `facturas_proveedor`

- **Columnas (21):** `id`, `numero_factura`, `proveedor`, `nit`, `numero_oc`, `fecha_emision`, `fecha_vencimiento`, `subtotal`, `iva`, `iva_pct`, `retefuente`, `retefuente_pct`, `retica`, `retica_pct`, `total`, `estado`, `pdf_adjunto`, `observaciones`, `creado_por`, `created_at`, `empresa`
- **PK:** `id`
- **Escriben:** compras, database
- **Leen:** compras, database, hub

### `facturas_proveedor_pdf`

- **Columnas (2):** `factura_id`, `pdf_adjunto`
- **PK:** `factura_id`
- **Escriben:** compras, database
- **Leen:** compras

### `flujo_config`

- **Columnas (3):** `clave`, `valor`, `descripcion`
- **PK:** `clave`
- **Escriben:** database, financiero
- **Leen:** financiero

### `flujo_egresos`

- **Columnas (11):** `id`, `fecha`, `empresa`, `concepto`, `categoria`, `monto`, `periodo`, `fuente`, `referencia`, `creado_por`, `observaciones`
- **PK:** `id`
- **Escriben:** compras, database, financiero, rrhh
- **Leen:** auto_plan_jobs, compras, contabilidad, database, financiero, gerencia, hub, rrhh

### `flujo_ingresos`

- **Columnas (11):** `id`, `fecha`, `empresa`, `concepto`, `categoria`, `monto`, `periodo`, `fuente`, `referencia`, `creado_por`, `observaciones`
- **PK:** `id`
- **Escriben:** contabilidad, financiero
- **Leen:** auto_plan_jobs, contabilidad, espagiria, financiero, hub

### `formula_headers`

- **Columnas (30):** `id`, `producto_nombre`, `unidad_base_g`, `descripcion`, `fecha_creacion`, `lote_size_kg`, `imagen_url`, `imagen_actualizada_at`, `shopify_id`, `shopify_handle`, `descripcion_html`, `descripcion_plain`, `sku_principal`, `precio_venta`, `peso_g`, `imagenes_extra_json`, `shopify_synced_at`, `volumen_unitario_ml`, `codigo_pt`, `activo`, `tiene_10ml`, `uds_10ml_por_lote`, `tipo_10ml`, `tiene_15ml`, `uds_15ml_por_lote`, `tenant_id`, `producto_canonico`, `variante_label`, `prioridad`, `nombre_generico`
- **PK:** `id`
- **Escriben:** admin, auto_plan, auto_plan_jobs, brd, database, inventario, mig_121_formulas_data, mig_127_data, plan, portal
- **Leen:** admin, auto_plan, auto_plan_jobs, brd, database, index, inventario, mig_121_formulas_data, mig_127_data, plan, portal, programacion

### `formula_items`

- **Columnas (7):** `id`, `producto_nombre`, `material_id`, `material_nombre`, `porcentaje`, `cantidad_g_por_lote`, `incluye_merma`
- **PK:** `id`
- **Escriben:** admin, auto_plan_jobs, brd, database, inventario, mig_121_formulas_data, mig_127_data, plan
- **Leen:** admin, auto_plan, auto_plan_jobs, brd, database, index, inventario, mig_121_formulas_data, mig_127_data, plan, programacion

### `formula_versiones`

- **Columnas (9):** `id`, `producto_nombre`, `version`, `unidad_base_g`, `descripcion`, `items_json`, `creado_at_utc`, `creado_por`, `motivo_cambio`
- **PK:** `id`
- **Escriben:** inventario
- **Leen:** inventario

### `formulas_versiones`

- **Columnas (7):** `id`, `formula_id`, `version_num`, `snapshot_json`, `motivo_cambio`, `creado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** tecnica
- **Leen:** tecnica

### `gerencia_inputs`

- **Columnas (7):** `id`, `periodo`, `saldo_caja`, `ingresos_animus`, `ingresos_maquila`, `notas`, `fecha`
- **PK:** `id`
- **Escriben:** gerencia
- **Leen:** auto_plan_jobs, financiero, gerencia, index

### `hallazgos`

- **Columnas (17):** `id`, `codigo`, `origen`, `titulo`, `descripcion`, `area`, `severidad`, `fecha_deteccion`, `fecha_limite`, `fecha_cierre`, `responsable`, `accion_propuesta`, `evidencia_cierre_url`, `capa_relacionada_id`, `estado`, `creado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** compliance, database
- **Leen:** compliance, index
- **FK:** `capa_relacionada_id`→`capa_desviaciones.id`

### `ipc_estandar_resultados`

- **Columnas (9):** `id`, `ebr_id`, `control_codigo`, `control_nombre`, `valor_texto`, `conforme`, `observaciones`, `medido_por`, `medido_at_utc`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd
- **FK:** `ebr_id`→`ebr_ejecuciones.id`

### `ipc_resultados`

- **Columnas (12):** `id`, `ebr_id`, `ipc_spec_id`, `valor_medido`, `valor_texto`, `conforme`, `medido_por`, `medido_at_utc`, `qc_username`, `qc_e_sign_id`, `notas`, `desviacion_id`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd, tecnica
- **FK:** `ipc_spec_id`→`ipc_specs.id`, `ebr_id`→`ebr_ejecuciones.id`

### `ipc_specs`

- **Columnas (10):** `id`, `mbr_template_id`, `mbr_paso_id`, `parametro`, `unidad`, `valor_min`, `valor_max`, `metodo`, `obligatorio`, `notas`
- **PK:** `id`
- **Escriben:** brd
- **Leen:** brd
- **FK:** `mbr_template_id`→`mbr_templates.id`

### `limpieza_profunda_calendario`

- **Columnas (13):** `id`, `fecha`, `area_codigo`, `estado`, `asignado_a`, `iniciado_at`, `terminado_at`, `iniciado_por`, `terminado_por`, `generado_por`, `razon_asignacion`, `notas`, `creado_en`
- **PK:** `id`
- **Escriben:** auto_plan, programacion
- **Leen:** auto_plan, auto_plan_jobs, programacion

### `maestro_consumibles`

- **Columnas (10):** `id`, `nombre`, `categoria`, `proveedor`, `precio_referencia`, `unidad`, `activo`, `creado_por`, `creado_en`, `tenant_id`
- **PK:** `id`
- **Escriben:** compras
- **Leen:** compras

### `maestro_mee`

- **Columnas (27):** `codigo`, `descripcion`, `categoria`, `proveedor`, `fabricante`, `estado`, `stock_actual`, `stock_minimo`, `unidad`, `fecha_creacion`, `tenant_id`, `nombre_inci`, `material_referencia`, `imagen_url`, `calificado`, `calificado_at`, `calificado_por`, `calificacion_detalle`, `cliente`, `marcacion_tipo`, `marcacion_proveedor`, `volumen_ml`, `precio_referencia`, `zona`, `estanteria`, `posicion`, `medida`
- **PK:** `codigo`
- **Escriben:** admin, auto_plan_jobs, brd, compras, database, gerencia, inventario, inventario_helpers, programacion, seed_mee
- **Leen:** admin, auto_plan, auto_plan_jobs, brd, calidad, compras, database, despachos, gerencia, index, inventario, inventario_helpers, plan, portal, programacion, seed_mee

### `maestro_mps`

- **Columnas (16):** `codigo_mp`, `nombre_inci`, `nombre_comercial`, `tipo`, `proveedor`, `stock_minimo`, `activo`, `precio_referencia`, `unidad_compra`, `lead_time_dias`, `ultima_act_precio`, `proveedor_preferido`, `tipo_material`, `tenant_id`, `controla_stock`, `min_auto`
- **PK:** `codigo_mp`
- **Escriben:** admin, auto_plan_jobs, brd, calidad, compras, database, inventario, mig_121_formulas_data, mig_127_data, programacion
- **Leen:** admin, auto_plan, auto_plan_jobs, brd, calidad, compras, core, database, despachos, espagiria, financiero, gerencia, hub, index, inventario, plan, programacion, seed_mp

### `maquila_ingredientes`

- **Columnas (6):** `id`, `orden_id`, `ingrediente`, `porcentaje`, `precio_mp_kg`, `aporte_kg`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —

### `maquila_ordenes`

- **Columnas (30):** `id`, `numero`, `prospecto_id`, `cliente_nombre`, `producto`, `categoria`, `formato_ml`, `lote_kg`, `unidades_lote`, `costo_mp_kg`, `costo_envase_ud`, `dias_acondicionamiento`, `costo_mo_lote`, `cf_prorateados`, `costo_micro`, `costo_total_lote`, `costo_por_unidad`, `margen`, `precio_ud`, `precio_lote`, `estado`, `fecha_orden`, `fecha_entrega_est`, `fecha_entrega_real`, `facturado`, `monto_facturado`, `fecha_factura`, `observaciones`, `creado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** maquila
- **Leen:** financiero, gerencia, maquila

### `maquila_pedidos`

- **Columnas (18):** `id`, `numero`, `cliente_id`, `cliente_nombre`, `producto_nombre`, `presentacion_id`, `unidades`, `kg_estimados`, `fecha_pedido`, `fecha_entrega_objetivo`, `estado`, `produccion_id`, `precio_unidad`, `valor_total`, `observaciones`, `creado_por`, `creado_en`, `actualizado_en`
- **PK:** `id`
- **Escriben:** auto_plan, espagiria
- **Leen:** auto_plan, espagiria
- **FK:** `produccion_id`→`produccion_programada.id`, `presentacion_id`→`producto_presentaciones.id`, `cliente_id`→`clientes_maquila.id`

### `maquila_pipeline`

- **Columnas (20):** `id`, `empresa`, `contacto_nombre`, `contacto_email`, `contacto_telefono`, `origen`, `stage`, `valor_estimado_cop`, `volumen_estimado_unds`, `producto_descripcion`, `nda_firmado_at`, `brief_recibido_at`, `cotizacion_enviada_at`, `contrato_firmado_at`, `fecha_cierre_estimada`, `owner`, `notas`, `motivo_perdida`, `creado_en`, `actualizado_en`
- **PK:** `id`
- **Escriben:** comercial, database
- **Leen:** comercial

### `maquila_prospectos`

- **Columnas (37):** `id`, `numero_brief`, `fecha`, `kam`, `empresa`, `contacto`, `cargo`, `whatsapp`, `email`, `ciudad`, `canal_origen`, `categoria_producto`, `descripcion_producto`, `claims`, `restricciones`, `estado_formula`, `volumen_lote`, `frecuencia`, `empaque`, `mercado`, `nso`, `presupuesto`, `etapa`, `nivel_recomendado`, `viabilidad`, `riesgos`, `valor_estimado_lote`, `ticket_mes`, `proxima_accion`, `observaciones`, `estado`, `creado_por`, `fecha_creacion`, `es_incubacion`, `nivel_servicio`, `kam_asignado`, `contacto_referido`
- **PK:** `id`
- **Escriben:** database, maquila
- **Leen:** maquila

### `marcacion_ordenes`

- **Columnas (25):** `id`, `base_codigo`, `serigrafiado_codigo`, `producto_nombre`, `metodo`, `proveedor`, `cantidad_enviada`, `cantidad_recibida`, `produccion_id`, `fecha_envio`, `fecha_retorno`, `estado`, `creado_por`, `creado_en`, `liberado_at`, `liberado_por`, `fecha_alistar`, `hora_alistar`, `urgencia`, `chk_arte`, `chk_estado`, `chk_caracteristicas`, `chk_cantidad`, `chk_observaciones`, `chk_rol`
- **PK:** `id`
- **Escriben:** programacion
- **Leen:** programacion

### `marketing_ab_tests`

- **Columnas (13):** `id`, `nombre`, `hipotesis`, `contenido_a_id`, `contenido_b_id`, `metrica_objetivo`, `ganadora`, `ganadora_diff_pct`, `ganadora_calculado_en`, `estado`, `notas`, `creado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** marketing
- **Leen:** marketing
- **FK:** `contenido_b_id`→`marketing_contenido.id`, `contenido_a_id`→`marketing_contenido.id`

### `marketing_ads_campaigns`

- **Columnas (18):** `id`, `platform`, `external_id`, `nombre`, `estado`, `objetivo`, `spend_total`, `impressions`, `clicks`, `conversiones`, `ctr`, `cpc`, `cpm`, `roas`, `fecha_inicio`, `fecha_fin`, `marketing_campana_id`, `synced_at`
- **PK:** `id`
- **Escriben:** marketing
- **Leen:** marketing
- **FK:** `marketing_campana_id`→`marketing_campanas.id`

### `marketing_agentes_feedback`

- **Columnas (7):** `id`, `log_id`, `agente`, `feedback`, `comentario`, `usuario`, `fecha`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —
- **FK:** `log_id`→`marketing_agentes_log.id`

### `marketing_agentes_log`

- **Columnas (6):** `id`, `agente`, `accion`, `resultado`, `fecha`, `ejecutado_por`
- **PK:** `id`
- **Escriben:** animus, marketing
- **Leen:** —

### `marketing_alertas_enviadas`

- **Columnas (9):** `id`, `agente`, `sku`, `tipo_alerta`, `severidad`, `mensaje`, `destinatarios`, `fecha_envio`, `enviado_at`
- **PK:** `id`
- **Escriben:** marketing
- **Leen:** marketing

### `marketing_campana_influencer`

- **Columnas (12):** `id`, `campana_id`, `influencer_id`, `monto_pactado`, `monto_pagado`, `fecha_pago`, `alcance_real`, `impresiones`, `clicks`, `conversiones`, `estado`, `notas`
- **PK:** `id`
- **Escriben:** marketing
- **Leen:** hub, marketing

### `marketing_campanas`

- **Columnas (17):** `id`, `nombre`, `tipo`, `estado`, `presupuesto`, `presupuesto_gastado`, `fecha_inicio`, `fecha_fin`, `sku_objetivo`, `objetivo_unidades`, `resultado_unidades`, `resultado_ventas`, `canal`, `notas`, `creada_por`, `fecha_creacion`, `discount_code`
- **PK:** `id`
- **Escriben:** marketing
- **Leen:** animus, hub, marketing

### `marketing_cmo_acciones`

- **Columnas (12):** `id`, `plan_id`, `tipo`, `prioridad`, `titulo`, `descripcion`, `agente_workflow`, `payload_json`, `estado`, `resultado_ejecucion`, `decidido_por`, `decidido_at`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —
- **FK:** `plan_id`→`marketing_cmo_plan.id`

### `marketing_cmo_plan`

- **Columnas (10):** `id`, `fecha`, `acciones_json`, `estado`, `generado_por`, `snapshot_json`, `aprobado_por`, `aprobado_at`, `notas`, `creado_at`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —

### `marketing_contenido`

- **Columnas (23):** `id`, `campana_id`, `influencer_id`, `tipo`, `plataforma`, `fecha_publicacion`, `estado`, `caption`, `url_publicacion`, `likes`, `comentarios`, `shares`, `guardados`, `alcance`, `impresiones`, `clicks`, `conversiones`, `notas`, `creado_por`, `fecha_creacion`, `sku_objetivo`, `mensaje_principal`, `fecha_programada`
- **PK:** `id`
- **Escriben:** marketing
- **Leen:** marketing

### `marketing_eventos_calendario`

- **Columnas (9):** `id`, `evento`, `fecha`, `color`, `multiplicador`, `activo`, `notas`, `creado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** database, marketing
- **Leen:** marketing

### `marketing_influencers`

- **Columnas (24):** `id`, `nombre`, `red_social`, `usuario_red`, `seguidores`, `engagement_rate`, `nicho`, `tarifa`, `estado`, `email`, `telefono`, `notas`, `fecha_registro`, `banco`, `cuenta_bancaria`, `cedula_nit`, `tipo_cuenta`, `motivo_baja`, `fecha_baja`, `ciudad`, `instagram`, `tipo`, `discount_code`, `ciclo_pago`
- **PK:** `id`
- **Escriben:** admin, database, marketing
- **Leen:** admin, animus, compras, database, hub, marketing

### `marketing_influencers_metrics`

- **Columnas (14):** `id`, `influencer_id`, `fecha`, `seguidores`, `siguiendo`, `posts_total`, `engagement_rate`, `avg_likes`, `avg_comments`, `rank_global`, `grade`, `fuente`, `raw_json`, `creado_en`
- **PK:** `id`
- **Escriben:** marketing
- **Leen:** marketing

### `marketing_metas`

- **Columnas (9):** `id`, `mes`, `revenue_meta`, `pedidos_meta`, `clientes_nuevos_meta`, `notas`, `creada_por`, `fecha_creacion`, `fecha_actualizacion`
- **PK:** `id`
- **Escriben:** marketing
- **Leen:** marketing

### `marketing_outreach_log`

- **Columnas (9):** `id`, `influencer_id`, `sku_objetivo`, `campana_id`, `canal`, `mensaje_preview`, `generado_por`, `usado_en`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —
- **FK:** `influencer_id`→`marketing_influencers.id`

### `marketing_push_alerts_log`

- **Columnas (8):** `id`, `tipo`, `clave_unica`, `destinatario`, `asunto`, `cuerpo_resumen`, `severidad`, `fecha`
- **PK:** `id`
- **Escriben:** marketing
- **Leen:** —

### `mbr_pasos`

- **Columnas (11):** `id`, `mbr_template_id`, `orden`, `fase`, `descripcion`, `tipo_paso`, `equipo_requerido`, `tiempo_estimado_min`, `requiere_e_sign`, `requiere_qc`, `notas`
- **PK:** `id`
- **Escriben:** brd, database, mig_121_formulas_data, mig_127_data
- **Leen:** brd, database, index, mig_121_formulas_data, mig_127_data, programacion
- **FK:** `mbr_template_id`→`mbr_templates.id`

### `mbr_templates`

- **Columnas (17):** `id`, `producto_nombre`, `formula_version_id`, `version`, `estado`, `titulo`, `descripcion`, `lote_size_g`, `tiempo_total_estimado_min`, `creado_por`, `creado_at_utc`, `updated_at_utc`, `aprobado_por`, `aprobado_at_utc`, `aprobado_signature_id`, `obsoleto_at_utc`, `obsoleto_motivo`
- **PK:** `id`
- **Escriben:** admin, brd, database, mig_121_formulas_data, mig_127_data
- **Leen:** admin, brd, calidad, database, index, mig_121_formulas_data, mig_127_data, programacion, tecnica

### `mee_aliases`

- **Columnas (9):** `id`, `alias`, `codigo_mee`, `descripcion_canonical`, `tipo`, `fuente`, `creado_en`, `creado_por`, `activo`
- **PK:** `id`
- **Escriben:** admin, database
- **Leen:** admin, auto_plan_jobs, programacion

### `mee_lead_time_config`

- **Columnas (12):** `mee_codigo`, `proveedor_principal`, `origen`, `lead_time_dias`, `moq_unidades`, `precio_unit`, `disparo_d20`, `aplica`, `notas`, `actualizado_en`, `actualizado_por`, `disparo_post_envasado`
- **PK:** `mee_codigo`
- **Escriben:** auto_plan, database
- **Leen:** auto_plan, auto_plan_jobs, programacion

### `mee_partes`

- **Columnas (6):** `id`, `mee_codigo`, `parte_codigo`, `descripcion`, `cantidad`, `creado_at`
- **PK:** `id`
- **Escriben:** admin, inventario
- **Leen:** admin, inventario, programacion

### `mensajes_internos`

- **Columnas (8):** `id`, `de_usuario`, `a_usuario`, `asunto`, `mensaje`, `fecha`, `leido_at`, `relacionado_tarea_id`
- **PK:** `id`
- **Escriben:** comunicacion
- **Leen:** comunicacion, hub

### `mfa_tokens_usados`

- **Columnas (4):** `id`, `username`, `token_hash`, `usado_at`
- **PK:** `id`
- **Escriben:** mfa
- **Leen:** mfa

### `movimientos`

- **Columnas (26):** `id`, `material_id`, `material_nombre`, `cantidad`, `tipo`, `fecha`, `observaciones`, `lote`, `fecha_vencimiento`, `estanteria`, `posicion`, `proveedor`, `estado_lote`, `operador`, `precio_kg`, `numero_factura`, `numero_oc`, `valor_total`, `zona`, `tenant_id`, `coa_url`, `coa_filename`, `lote_proveedor`, `ficha_seguridad_url`, `produccion_id`, `n_recipientes`
- **PK:** `id`
- **Escriben:** admin, animus, auto_plan_jobs, brd, calidad, compras, database, despachos, gerencia, inventario, programacion
- **Leen:** admin, aseguramiento, auto_plan, auto_plan_jobs, brd, calidad, compras, core, database, despachos, espagiria, financiero, gerencia, hub, index, inventario, inventario_helpers, plan, programacion, seed_mp

### `movimientos_mee`

- **Columnas (18):** `id`, `mee_codigo`, `tipo`, `cantidad`, `unidad`, `lote_ref`, `batch_ref`, `responsable`, `observaciones`, `fecha`, `anulado`, `proveedor`, `zona`, `precio_unitario`, `fecha_vencimiento`, `oc_numero`, `factura_numero`, `estado`
- **PK:** `id`
- **Escriben:** admin, brd, calidad, compras, database, inventario, inventario_helpers, programacion
- **Leen:** admin, auto_plan_jobs, calidad, compras, database, inventario, inventario_helpers, programacion

### `mp_alcanza_snapshots`

- **Columnas (10):** `fecha`, `total_mps`, `comprar_ya_total`, `comprar_1_2_sem_total`, `comprar_1_mes_total`, `ok_total`, `sin_uso_total`, `comprar_ya_codigos`, `creado_en`, `origen`
- **PK:** `fecha`
- **Escriben:** admin
- **Leen:** admin

### `mp_aliases`

- **Columnas (9):** `id`, `alias`, `codigo_mp`, `nombre_inci_canonical`, `tipo`, `fuente`, `creado_en`, `creado_por`, `activo`
- **PK:** `id`
- **Escriben:** database, inventario
- **Leen:** admin, auto_plan_jobs, inventario

### `mp_formula_bridge`

- **Columnas (9):** `id`, `formula_material_id`, `formula_material_nombre`, `bodega_material_id`, `bodega_material_nombre`, `bodega_inci`, `notas`, `activo`, `creado_en`
- **PK:** `id`
- **Escriben:** database, inventario, programacion
- **Leen:** admin, database, index, programacion

### `mp_lead_time_config`

- **Columnas (15):** `id`, `material_id`, `material_nombre`, `proveedor_principal`, `lead_time_dias`, `buffer_dias`, `cobertura_min_dias`, `cobertura_ideal_dias`, `origen`, `es_envase`, `activo`, `actualizado_en`, `n_recepciones`, `moq_g`, `multiplo_g`
- **PK:** `id`
- **Escriben:** admin, auto_plan, compras
- **Leen:** admin, auto_plan, auto_plan_jobs, compras, plan, programacion

### `no_conformidades`

- **Columnas (14):** `id`, `fecha`, `tipo`, `descripcion`, `area`, `responsable`, `lote`, `codigo_mp`, `impacto`, `accion_correctiva`, `estado`, `fecha_cierre`, `cerrado_por`, `creado_por`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** aseguramiento, calidad, espagiria, hub

### `nomina_registros`

- **Columnas (18):** `id`, `periodo`, `empleado_id`, `salario_base`, `dias_trabajados`, `horas_extras`, `valor_horas_extras`, `subsidio_transporte`, `bonificaciones`, `descuento_salud`, `descuento_pension`, `otros_descuentos`, `salario_neto`, `estado`, `aprobado_por`, `aprobado_en`, `pagado_por`, `pagado_en`
- **PK:** `id`
- **Escriben:** rrhh
- **Leen:** contabilidad, database, financiero, gerencia, rrhh

### `notificaciones_app`

- **Columnas (10):** `id`, `destinatario`, `tipo`, `titulo`, `body`, `link`, `remitente`, `importante`, `leido_at`, `creado_en`
- **PK:** `id`
- **Escriben:** notif
- **Leen:** notif

### `notificaciones_empleados`

- **Columnas (15):** `id`, `empleado_username`, `empleado_nombre`, `tipo`, `asunto`, `descripcion`, `fecha_inicio`, `fecha_fin`, `adjunto_url`, `estado`, `notificado_a`, `comentario_jefe`, `resuelto_por`, `resuelto_en`, `creado_en`
- **PK:** `id`
- **Escriben:** bienestar
- **Leen:** bienestar

### `notificaciones_outbox`

- **Columnas (14):** `id`, `destinatario`, `tipo`, `titulo`, `body`, `link`, `remitente`, `importante`, `estado`, `intentos`, `ultimo_error`, `creado_at_utc`, `enviado_at_utc`, `tenant_id`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —

### `oc_recepcion_dedup`

- **Columnas (3):** `recepcion_id`, `numero_oc`, `creado_en`
- **PK:** —
- **Escriben:** compras, inventario, marketing
- **Leen:** —

### `op_counters`

- **Columnas (3):** `year`, `counter`, `updated_at_utc`
- **PK:** `year`
- **Escriben:** brd
- **Leen:** brd

### `operarios_fija_audit`

- **Columnas (5):** `id`, `operario_id`, `valor_anterior`, `valor_nuevo`, `cambiado_at`
- **PK:** `id`
- **Escriben:** database
- **Leen:** —

### `operarios_planta`

- **Columnas (9):** `id`, `nombre`, `apellido`, `rol_predeterminado`, `fija_en_dispensacion`, `es_jefe_produccion`, `activo`, `creado_en`, `tenant_id`
- **PK:** `id`
- **Escriben:** database, programacion
- **Leen:** admin, auto_plan, auto_plan_jobs, bienestar, brd, database, espagiria, inventario, operario, programacion

### `ordenes_compra`

- **Columnas (27):** `id`, `numero_oc`, `fecha`, `estado`, `proveedor`, `valor_total`, `observaciones`, `creado_por`, `fecha_entrega_est`, `categoria`, `remision_code`, `autorizado_por`, `fecha_autorizacion`, `pagado_por`, `fecha_pago`, `fecha_recepcion`, `observaciones_recepcion`, `tiene_discrepancias`, `con_iva`, `valor_sin_iva`, `comprobante_imagen`, `medio_pago`, `recibido_por`, `numero_factura_proveedor`, `centro_costos`, `tenant_id`, `recepcion_parcial`
- **PK:** `id`
- **Escriben:** admin, compras, database, gerencia, inventario, plan, programacion
- **Leen:** admin, aseguramiento, audit_helpers, auto_plan, auto_plan_jobs, compras, database, despachos, espagiria, financiero, gerencia, hub, index, inventario, marketing, plan, programacion

### `ordenes_compra_items`

- **Columnas (12):** `id`, `numero_oc`, `codigo_mp`, `nombre_mp`, `cantidad_g`, `precio_unitario`, `subtotal`, `estado_recepcion`, `notas_recepcion`, `precio_unitario_real`, `cantidad_recibida_g`, `lote_asignado`
- **PK:** `id`
- **Escriben:** admin, compras, database, gerencia, inventario, plan, programacion
- **Leen:** admin, auto_plan_jobs, compras, database, despachos, financiero, gerencia, inventario, plan, programacion

### `ordenes_servicio`

- **Columnas (22):** `numero_os`, `proveedor`, `tipo_servicio`, `producto_final`, `envase_codigo_mee`, `envase_descripcion`, `cantidad_unidades`, `arte_descripcion`, `arte_archivo_url`, `fecha_solicitud`, `fecha_requerida_entrega`, `fecha_real_entrega`, `estado`, `costo_estimado_cop`, `costo_real_cop`, `observaciones`, `creado_por`, `creado_at_utc`, `planta_confirmado_por`, `planta_confirmado_at_utc`, `cancelada_motivo`, `tenant_id`
- **PK:** `numero_os`
- **Escriben:** compras
- **Leen:** compras, programacion

### `ordenes_servicio_eventos`

- **Columnas (7):** `id`, `numero_os`, `estado_anterior`, `estado_nuevo`, `usuario`, `ts_utc`, `observaciones`
- **PK:** `id`
- **Escriben:** compras
- **Leen:** compras

### `pagos_influencers`

- **Columnas (13):** `id`, `influencer_id`, `influencer_nombre`, `valor`, `fecha`, `estado`, `concepto`, `numero_oc`, `created_at`, `fecha_publicacion`, `entregable`, `fecha_contenido`, `vence_pago_at`
- **PK:** `id`
- **Escriben:** admin, compras, database, marketing
- **Leen:** admin, auto_plan_jobs, compras, financiero, hub, marketing

### `pagos_oc`

- **Columnas (11):** `id`, `numero_oc`, `monto`, `medio`, `fecha_pago`, `registrado_por`, `numero_factura_proveedor`, `comprobante_imagen`, `observaciones`, `factura_proveedor_id`, `numero_transaccion`
- **PK:** `id`
- **Escriben:** auto_plan_jobs, compras
- **Leen:** auto_plan_jobs, compras, hub, marketing

### `pedidos`

- **Columnas (16):** `id`, `numero`, `cliente_id`, `fecha`, `fecha_entrega_est`, `estado`, `empresa`, `valor_total`, `observaciones`, `creado_por`, `fecha_despacho`, `numero_factura`, `monto_pagado`, `estado_pago`, `canal_venta`, `descuento_total_cop`
- **PK:** `id`
- **Escriben:** clientes, gerencia, maquila
- **Leen:** aseguramiento, auto_plan_jobs, clientes, contabilidad, espagiria, financiero, gerencia, hub, maquila
- **FK:** `cliente_id`→`clientes.id`

### `pedidos_b2b`

- **Columnas (19):** `id`, `cliente_id`, `cliente_nombre`, `producto_nombre`, `cantidad_uds`, `ml_unidad`, `fecha_estimada`, `estado`, `notas`, `creado_por`, `creado_at_utc`, `actualizado_at_utc`, `tenant_id`, `envase_codigo`, `envase_notas`, `urgencia`, `despachado_at`, `despacho_guia`, `despacho_transportadora`
- **PK:** `id`
- **Escriben:** auto_plan_jobs, database, plan, portal
- **Leen:** database, marketing, plan, portal, programacion

### `pedidos_b2b_lote`

- **Columnas (12):** `id`, `pedido_b2b_id`, `lote_produccion_id`, `kg_aporte`, `unidades_aporte`, `ml_unidad`, `envase_codigo`, `modo`, `cliente_nombre`, `creado_at`, `plan_envasado_uds`, `plan_envasado_notas`
- **PK:** `id`
- **Escriben:** plan, programacion
- **Leen:** auto_plan, brd, plan, programacion

### `pedidos_b2b_recurrentes`

- **Columnas (13):** `id`, `cliente_id`, `cliente_nombre`, `producto_nombre`, `cantidad_uds`, `ml_unidad`, `envase_codigo`, `frecuencia_dias`, `proximo_at`, `activo`, `creado_por`, `creado_at_utc`, `ultimo_generado_at`
- **PK:** `id`
- **Escriben:** auto_plan_jobs, portal
- **Leen:** auto_plan_jobs

### `pedidos_items`

- **Columnas (8):** `id`, `numero_pedido`, `sku`, `descripcion`, `cantidad`, `precio_unitario`, `subtotal`, `lote_pt`
- **PK:** `id`
- **Escriben:** clientes, gerencia
- **Leen:** clientes, contabilidad, gerencia, maquila

### `plan_vmaps_cache`

- **Columnas (3):** `cache_key`, `computed_at`, `payload`
- **PK:** `cache_key`
- **Escriben:** plan
- **Leen:** plan

### `portal_clientes_credenciales`

- **Columnas (10):** `id`, `cliente_id`, `cliente_nombre`, `email`, `password_hash`, `activo`, `creado_por`, `creado_at_utc`, `ultimo_login_at_utc`, `ultimo_login_ip`
- **PK:** `id`
- **Escriben:** plan, portal
- **Leen:** plan, portal

### `portal_pqr`

- **Columnas (13):** `id`, `cliente_id`, `cliente_nombre`, `email_cliente`, `tipo`, `titulo`, `descripcion`, `estado`, `respuesta_admin`, `respondido_por`, `respondido_at_utc`, `creado_at_utc`, `actualizado_at_utc`
- **PK:** `id`
- **Escriben:** portal
- **Leen:** auto_plan_jobs, portal

### `portal_solicitudes`

- **Columnas (23):** `id`, `cliente_id`, `cliente_nombre`, `cliente_email`, `tipo`, `producto_nombre`, `cantidad_estimada`, `unidad`, `envase_preferencia`, `fecha_requerida`, `mensaje`, `adjunto_filename`, `estado`, `respuesta_precio_cop`, `respuesta_lead_time_dias`, `respuesta_moq`, `respuesta_validez_dias`, `respuesta_notas`, `respondido_por`, `respondido_at`, `convertida_pedido_id`, `creada_at`, `actualizada_at`
- **PK:** `id`
- **Escriben:** portal
- **Leen:** portal

### `pqr_inbox`

- **Columnas (30):** `id`, `ghl_message_id`, `ghl_contact_id`, `canal`, `contacto_nombre`, `contacto_email`, `contacto_telefono`, `mensaje`, `recibido_en`, `ia_empresa`, `ia_tipo`, `ia_severidad`, `ia_confianza`, `ia_resumen`, `ia_razon`, `ia_fuente`, `estado`, `destino_empresa`, `destino_tabla`, `destino_id`, `enrutado_por`, `enrutado_en`, `descartado_por`, `motivo_descarte`, `creado_en`, `producto`, `lote`, `pedido_numero`, `ia_clase`, `ia_criticidad`
- **PK:** `id`
- **Escriben:** aseguramiento, database
- **Leen:** aseguramiento, database

### `precio_historico_mp`

- **Columnas (13):** `id`, `codigo_mp`, `nombre_mp`, `proveedor`, `precio_unit_g`, `cantidad_g`, `valor_total`, `fecha`, `fuente`, `sol_numero`, `oc_numero`, `usuario`, `observaciones`
- **PK:** `id`
- **Escriben:** admin, compras
- **Leen:** admin, compras

### `precios_mp_historico`

- **Columnas (9):** `id`, `codigo_mp`, `proveedor`, `precio_kg`, `fecha`, `numero_oc`, `numero_factura`, `origen`, `observaciones`
- **PK:** `id`
- **Escriben:** admin, compras, inventario
- **Leen:** admin, compras, inventario

### `produccion_checklist`

- **Columnas (34):** `id`, `produccion_id`, `produccion_ref`, `producto_nombre`, `fecha_planeada`, `cantidad_kg`, `item_tipo`, `descripcion`, `cantidad_requerida`, `unidad`, `codigo_mp`, `stock_actual`, `deficit`, `estado`, `proveedor`, `solicitud_numero`, `oc_numero`, `fecha_solicitud`, `fecha_eta`, `fecha_recibido`, `responsable`, `observaciones`, `dias_anticipacion`, `actualizado_at`, `actualizado_por`, `fecha_creacion`, `mee_codigo_asignado`, `decoracion_tipo`, `cantidad_unidades`, `solicitud_produccion_id`, `consumido_at`, `consumido_por`, `cantidad_consumida_real`, `consumido_contexto`
- **PK:** `id`
- **Escriben:** admin, auto_plan, compras, inventario, programacion
- **Leen:** admin, auto_plan, inventario, programacion

### `produccion_envasado`

- **Columnas (18):** `id`, `produccion_id`, `producto_nombre`, `lote`, `presentacion_id`, `presentacion_etiqueta`, `unidades_planeadas`, `unidades_envasadas`, `envase_codigo`, `iniciado_at`, `iniciado_por`, `terminado_at`, `terminado_por`, `estado`, `muestra_micro_id`, `notas`, `operario_asignado`, `area_codigo`
- **PK:** `id`
- **Escriben:** admin, programacion
- **Leen:** admin, auto_plan, programacion
- **FK:** `presentacion_id`→`producto_presentaciones.id`, `produccion_id`→`produccion_programada.id`

### `produccion_eventos`

- **Columnas (6):** `id`, `produccion_id`, `tipo`, `detalles`, `usuario`, `fecha_at`
- **PK:** `id`
- **Escriben:** plan
- **Leen:** plan

### `produccion_programada`

- **Columnas (48):** `id`, `producto`, `fecha_programada`, `lotes`, `estado`, `observaciones`, `creado_en`, `gcal_event_id`, `origen`, `cantidad_kg`, `inventario_descontado_at`, `area_id`, `operario_dispensacion_id`, `operario_elaboracion_id`, `operario_envasado_id`, `operario_acondicionamiento_id`, `inicio_real_at`, `fin_real_at`, `area_envasado_id`, `bloqueado_at`, `bloqueado_por`, `semana_workflow_id`, `kg_real`, `unidades_real`, `merma_pct`, `motivo_pausa`, `pausado_at`, `pausado_por`, `etapa_disp_inicio_at`, `etapa_disp_fin_at`, `etapa_elab_inicio_at`, `etapa_elab_fin_at`, `etapa_env_inicio_at`, `etapa_env_fin_at`, `etapa_acond_inicio_at`, `etapa_acond_fin_at`, `granel_aprobado_at`, `granel_aprobado_por`, `granel_aprobado_motivo`, `tenant_id`, `distribucion_resumen`, `envase_codigo_override`, `fija_override_json`, `cadencia_dias`, `presentacion`, `meses_cobertura`, `kg_otro_cliente`, `sku_breakdown_json`
- **PK:** `id`
- **Escriben:** admin, auto_plan, auto_plan_jobs, brd, database, mig_130_canonicos_data, mig_136_plan_limpio_data, mig_137_plan_denso_data, plan, programacion
- **Leen:** admin, auto_plan, auto_plan_jobs, bienestar, brd, calidad, compras, core, database, espagiria, hub, index, inventario, mig_130_canonicos_data, operario, plan, portal, programacion

### `producciones`

- **Columnas (13):** `id`, `producto`, `cantidad`, `fecha`, `estado`, `observaciones`, `operador`, `lote`, `presentacion`, `sop_referencia`, `sop_version`, `formula_snapshot_json`, `costo_estimado_cop`
- **PK:** `id`
- **Escriben:** admin, database, inventario, programacion
- **Leen:** admin, brd, core, database, espagiria, gerencia, hub, inventario, plan, programacion

### `producto_canonico_config`

- **Columnas (8):** `producto_nombre`, `kg_por_lote`, `ml_unidad`, `frecuencia_dias`, `activo`, `actualizado_at`, `actualizado_por`, `notas`
- **PK:** `producto_nombre`
- **Escriben:** database, plan
- **Leen:** database, index, plan

### `producto_fmea`

- **Columnas (15):** `id`, `producto_nombre`, `modo_falla`, `efecto`, `causa`, `severidad`, `ocurrencia`, `deteccion`, `rpn`, `control_actual`, `accion_recomendada`, `responsable`, `estado`, `creado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento

### `producto_formula_alias`

- **Columnas (6):** `id`, `producto_plan`, `producto_formula`, `activo`, `creado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** programacion
- **Leen:** programacion

### `producto_perfil_riesgo`

- **Columnas (10):** `id`, `producto_nombre`, `tiene_pigmento`, `color_descripcion`, `es_acido`, `requiere_asepsia_extra`, `riesgo_arrastre_pct`, `notas`, `actualizado_en`, `requiere_envasado_mismo_dia`
- **PK:** `id`
- **Escriben:** auto_plan, database
- **Leen:** auto_plan, database, plan, programacion

### `producto_presentaciones`

- **Columnas (20):** `id`, `producto_nombre`, `categoria`, `presentacion_codigo`, `etiqueta`, `volumen_ml`, `peso_g`, `envase_codigo`, `factor_g_por_unidad`, `sku_shopify`, `es_default`, `activo`, `notas`, `creado_en`, `actualizado_en`, `ventas_mes_referencia`, `cantidad_fija_uds`, `tapa_codigo`, `caja_codigo`, `etiqueta_codigo`
- **PK:** `id`
- **Escriben:** admin, brd, database, inventario, plan, programacion
- **Leen:** admin, auto_plan, brd, database, espagiria, index, inventario, plan, portal, programacion

### `proveedores`

- **Columnas (25):** `id`, `nombre`, `contacto`, `email`, `telefono`, `categoria`, `condiciones_pago`, `activo`, `fecha_creacion`, `nit`, `id_interno`, `direccion`, `num_cuenta`, `tipo_cuenta`, `banco`, `cert_bancario`, `estado_lpa`, `ultima_evaluacion`, `vencimiento_docs`, `acuerdo_calidad`, `rut`, `camara_comercio`, `concepto_compra`, `motivo_baja`, `fecha_baja`
- **PK:** `id`
- **Escriben:** compras, database, inventario, programacion
- **Leen:** aseguramiento, auto_plan, compras, inventario, programacion

### `proveedores_calificacion`

- **Columnas (16):** `id`, `proveedor`, `criticidad`, `requiere_visita`, `categoria`, `estado`, `cuestionario_url`, `certificaciones`, `fecha_aprobacion`, `fecha_reevaluacion`, `fecha_ultima_visita`, `observaciones`, `evaluado_por`, `actualizado_en`, `creado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento, programacion
- **Leen:** aseguramiento, programacion

### `quejas_clientes`

- **Columnas (42):** `id`, `codigo`, `fecha_recepcion`, `recibido_por`, `canal`, `cliente_nombre`, `cliente_contacto`, `cliente_tipo`, `producto`, `lote`, `fecha_compra`, `establecimiento_compra`, `tipo_queja`, `descripcion`, `impacto_salud`, `severidad`, `triaje_descripcion`, `triaje_por`, `triaje_at`, `requiere_desviacion`, `desviacion_id`, `requiere_recall`, `causa_raiz`, `investigacion_por`, `investigacion_at`, `respuesta_descripcion`, `respuesta_canal`, `respondido_por`, `respondido_at`, `fecha_compromiso`, `cliente_satisfecho`, `accion_correctiva`, `cerrado_por`, `fecha_cierre`, `observaciones_cierre`, `estado`, `creado_en`, `actualizado_en`, `clase_pqrsf`, `criticidad`, `fecha_limite_respuesta`, `acuse_enviado_at`
- **PK:** `id`
- **Escriben:** aseguramiento, database
- **Leen:** aseguramiento, auto_plan_jobs, database, index

### `quejas_clientes_eventos`

- **Columnas (8):** `id`, `queja_id`, `evento_tipo`, `estado_anterior`, `estado_nuevo`, `usuario`, `comentario`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento
- **FK:** `queja_id`→`quejas_clientes.id`

### `quejas_internas`

- **Columnas (11):** `id`, `de_usuario`, `contexto`, `severidad_ia`, `analisis_ia`, `accion_sugerida_ia`, `escalada_a`, `estado`, `fecha`, `fecha_resolucion`, `resolucion`
- **PK:** `id`
- **Escriben:** comunicacion
- **Leen:** comunicacion, hub

### `rate_limit`

- **Columnas (4):** `ip`, `attempts`, `locked_until`, `last_attempt`
- **PK:** `ip`
- **Escriben:** auth, database
- **Leen:** admin, auth, database

### `rate_limit_hits`

- **Columnas (2):** `clave`, `ts`
- **PK:** —
- **Escriben:** comercial
- **Leen:** comercial

### `recall_log`

- **Columnas (9):** `id`, `lote_pt`, `sku`, `motivo`, `total_despachos`, `total_unidades`, `fecha_recall`, `ejecutado_por`, `estado`
- **PK:** `id`
- **Escriben:** maquila
- **Leen:** —

### `recalls`

- **Columnas (38):** `id`, `codigo`, `fecha_inicio`, `iniciado_por`, `origen`, `origen_referencia`, `desviacion_id`, `queja_id`, `producto`, `lotes_afectados`, `cantidad_fabricada`, `cantidad_distribuida`, `motivo`, `riesgo_descripcion`, `clase_recall`, `alcance_geografico`, `clasificado_por`, `clasificado_at`, `justificacion_clasificacion`, `notificacion_invima_at`, `notificacion_invima_ref`, `notificacion_invima_por`, `notificacion_distribuidores_at`, `distribuidores_notificados`, `notificacion_distribuidores_por`, `recoleccion_inicio_at`, `recoleccion_completada_at`, `cantidad_recolectada`, `disposicion_final`, `disposicion_descripcion`, `efectividad_porcentaje`, `efectividad_descripcion`, `estado`, `fecha_cierre`, `cerrado_por`, `observaciones_cierre`, `creado_en`, `actualizado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento, auto_plan_jobs, index

### `recalls_eventos`

- **Columnas (8):** `id`, `recall_id`, `evento_tipo`, `estado_anterior`, `estado_nuevo`, `usuario`, `comentario`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento
- **FK:** `recall_id`→`recalls.id`

### `recepcion_tecnica_doc`

- **Columnas (30):** `id`, `mov_id`, `numero_oc`, `lote`, `tipo_insumo`, `codigo_insumo`, `nombre_insumo`, `lote_proveedor`, `cantidad_recibida`, `proveedor`, `fecha_recepcion`, `numero_remision`, `area_almacenamiento`, `crit_rotulado`, `crit_empaque`, `crit_hoja_seguridad`, `crit_ficha_tecnica`, `crit_coa`, `crit_doc_coincide`, `observaciones`, `resultado`, `fecha_vencimiento`, `realiza_por`, `realiza_fecha`, `aprueba_por`, `aprueba_fecha`, `creado_por`, `creado_en`, `anulado`, `origen`
- **PK:** `id`
- **Escriben:** calidad
- **Leen:** calidad, inventario

### `revision_direccion`

- **Columnas (16):** `id`, `periodo`, `fecha_planeada`, `fecha_ejecutada`, `conducido_por`, `participantes`, `kpis_json`, `fortalezas`, `debilidades`, `decisiones`, `acciones_mejora`, `acta_url`, `estado`, `signature_id`, `creado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento

### `rh_compromisos_mejora`

- **Columnas (20):** `id`, `empleado_id`, `evento_origen_id`, `titulo`, `descripcion`, `tipo`, `plan_accion`, `fecha_compromiso`, `fecha_objetivo`, `estado`, `video_url`, `evidencia_url`, `firma_empleado`, `fecha_firma_empleado`, `verificado_por`, `fecha_verificacion`, `jefe_responsable`, `observaciones`, `creado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** rrhh
- **Leen:** rrhh

### `rh_eventos`

- **Columnas (31):** `id`, `empleado_id`, `tipo`, `fecha_inicio`, `fecha_fin`, `dias`, `descripcion`, `diagnostico`, `cie10`, `entidad_emisora`, `origen`, `motivo`, `severidad`, `jefe_id`, `jefe_nombre`, `area`, `salario_diario_referencia`, `pago_empleador`, `pago_eps`, `pago_arl`, `descuento_nomina`, `calculo_detalle_json`, `documento_url`, `estado`, `aprobado_por`, `fecha_aprobacion`, `observaciones_cierre`, `nomina_registro_id`, `sincronizado_tesoreria`, `registrado_por`, `fecha_registro`
- **PK:** `id`
- **Escriben:** rrhh
- **Leen:** rrhh

### `rol_afinidad_config`

- **Columnas (4):** `id`, `rol_destino`, `rol_predeterminado`, `peso`
- **PK:** `id`
- **Escriben:** database
- **Leen:** auto_plan

### `roles_catalogo`

- **Columnas (5):** `id`, `codigo`, `descripcion`, `activo`, `creado_at_utc`
- **PK:** `id`
- **Escriben:** database
- **Leen:** —

### `rotacion_operarios_state`

- **Columnas (4):** `rol`, `ultimo_operario_id`, `ultimo_asignado_at`, `actualizado_por`
- **PK:** `rol`
- **Escriben:** database, programacion
- **Leen:** programacion

### `rotulos_limpieza`

- **Columnas (21):** `id`, `area_id`, `area_codigo`, `produccion_id`, `producto_elaborar`, `lote_elaborar`, `producto_anterior`, `lote_anterior`, `sanitizante`, `detergente`, `equipos_json`, `estado`, `realizado_por`, `realizado_at`, `verificado_por`, `verificado_at`, `verificado_sign_id`, `despeje_checklist_id`, `observaciones`, `creado_en`, `actualizado_en`
- **PK:** `id`
- **Escriben:** programacion
- **Leen:** calidad, programacion
- **FK:** `area_id`→`areas_planta.id`

### `saldos_proveedor_mov`

- **Columnas (12):** `id`, `proveedor`, `tipo`, `monto`, `origen`, `numero_oc`, `pago_oc_id`, `flujo_egreso_id`, `fecha`, `registrado_por`, `observaciones`, `anulado`
- **PK:** `id`
- **Escriben:** compras
- **Leen:** compras

### `schema_migrations`

- **Columnas (3):** `version`, `applied_at`, `description`
- **PK:** `version`
- **Escriben:** admin, database, index
- **Leen:** admin, core, database, index, plan

### `security_events`

- **Columnas (7):** `id`, `ts`, `event`, `username`, `ip`, `user_agent`, `details`
- **PK:** `id`
- **Escriben:** auth
- **Leen:** admin, core, gerencia

### `sgd_capacitaciones`

- **Columnas (14):** `id`, `sgd_codigo`, `sgd_version`, `persona_username`, `asignado_at`, `leido_at`, `firmado_at`, `firma_hash`, `evaluado`, `nota_evaluacion`, `nota_minima`, `estado`, `fecha_limite`, `asignado_por`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento, espagiria

### `sgd_conflictos`

- **Columnas (9):** `id`, `codigo`, `archivos_detectados`, `temas_detectados`, `estado`, `resolucion`, `resuelto_por`, `resuelto_at`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento

### `sgd_documentos`

- **Columnas (24):** `id`, `codigo`, `area`, `tipo_doc`, `numero`, `subtipo`, `titulo`, `descripcion`, `padre_codigo`, `version_actual`, `archivo_pdf_url`, `archivo_origen`, `fecha_creacion`, `fecha_aprobacion`, `vigente_desde`, `proxima_revision`, `estado`, `elaborado_por`, `revisado_por`, `aprobado_por`, `observaciones`, `creado_por`, `creado_en`, `actualizado_en`
- **PK:** `id`
- **Escriben:** aseguramiento, database, tecnica
- **Leen:** aseguramiento, tecnica

### `sgd_versiones`

- **Columnas (9):** `id`, `codigo`, `version`, `fecha_aprobacion`, `archivo_url`, `archivo_origen`, `motivo_cambio`, `aprobado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento

### `sgsst_items`

- **Columnas (9):** `id`, `categoria`, `descripcion`, `frecuencia`, `ultimo_cumplimiento`, `proximo_vencimiento`, `responsable`, `estado`, `creado_en`
- **PK:** `id`
- **Escriben:** database, rrhh
- **Leen:** database, gerencia, rrhh

### `sign_challenges`

- **Columnas (8):** `token`, `username`, `auth_factor`, `created_at_utc`, `expires_at_utc`, `consumed`, `consumed_at_utc`, `ip`
- **PK:** `token`
- **Escriben:** firmas
- **Leen:** firmas

### `sku_mee_config`

- **Columnas (7):** `id`, `sku_codigo`, `mee_codigo`, `componente_tipo`, `cantidad_por_unidad`, `aplica`, `notas`
- **PK:** `id`
- **Escriben:** admin, auto_plan, auto_plan_jobs, database, programacion
- **Leen:** admin, auto_plan, auto_plan_jobs, brd, core, inventario, programacion

### `sku_planeacion_config`

- **Columnas (26):** `id`, `producto_nombre`, `categoria`, `cadencia_dias`, `cobertura_target_dias`, `cobertura_max_dias`, `cobertura_min_dias`, `merma_pct`, `prioridad`, `presentacion_default_id`, `activo`, `notas`, `actualizado_en`, `alias_calendar`, `estado`, `descontinuado_at`, `descontinuado_por`, `razon_estado`, `volumen_ml_unidad`, `mix_mode`, `kg_objetivo_lote`, `horizonte_dias`, `mix_congelado_json`, `venta_esperada_mes`, `sobreproduccion_deliberada`, `sobreproduccion_motivo`
- **PK:** `id`
- **Escriben:** auto_plan, database, plan, programacion
- **Leen:** auto_plan, auto_plan_jobs, database, plan, programacion
- **FK:** `presentacion_default_id`→`producto_presentaciones.id`

### `sku_precios`

- **Columnas (8):** `id`, `sku`, `descripcion`, `precio_base`, `precio_mayorista`, `unidad`, `empresa`, `activo`
- **PK:** `id`
- **Escriben:** database, financiero
- **Leen:** financiero

### `sku_producto_map`

- **Columnas (6):** `sku`, `producto_nombre`, `activo`, `es_regalo`, `tono_label`, `volumen_ml`
- **PK:** `sku`
- **Escriben:** admin, auto_plan, database, plan, programacion
- **Leen:** admin, auto_plan, auto_plan_jobs, database, index, inventario, plan, programacion

### `solicitudes_compra`

- **Columnas (19):** `id`, `numero`, `fecha`, `estado`, `solicitante`, `urgencia`, `observaciones`, `aprobado_por`, `fecha_aprobacion`, `numero_oc`, `area`, `empresa`, `categoria`, `tipo`, `email_solicitante`, `fecha_requerida`, `valor`, `influencer_id`, `tenant_id`
- **PK:** `id`
- **Escriben:** admin, auto_plan, auto_plan_jobs, compras, database, gerencia, inventario, marketing, plan, programacion
- **Leen:** admin, auto_plan, auto_plan_jobs, compras, core, database, despachos, espagiria, financiero, gerencia, index, inventario, marketing, plan, programacion
- **FK:** `influencer_id`→`marketing_influencers.id`

### `solicitudes_compra_anticipada`

- **Columnas (20):** `id`, `checklist_item_id`, `produccion_id`, `producto_nombre`, `tipo_item`, `mee_codigo`, `descripcion`, `cantidad_unidades`, `decoracion_tipo`, `fecha_objetivo`, `estado`, `decision`, `decidido_por`, `fecha_decision`, `oc_numero`, `tarea_operativa_id`, `proveedor`, `observaciones`, `solicitado_por`, `fecha_creacion`
- **PK:** `id`
- **Escriben:** compras, programacion
- **Leen:** programacion

### `solicitudes_compra_items`

- **Columnas (12):** `id`, `numero`, `codigo_mp`, `nombre_mp`, `cantidad_g`, `unidad`, `justificacion`, `valor_estimado`, `precio_unit_g`, `proveedor_sugerido`, `actualizado_at`, `actualizado_por`
- **PK:** `id`
- **Escriben:** admin, auto_plan, auto_plan_jobs, compras, inventario, plan, programacion
- **Leen:** admin, auto_plan, compras, inventario, plan, programacion

### `solicitudes_produccion`

- **Columnas (11):** `id`, `sku`, `descripcion`, `unidades_solicitadas`, `motivo`, `estado`, `prioridad`, `fecha_solicitud`, `fecha_requerida`, `solicitado_por`, `observaciones`
- **PK:** `id`
- **Escriben:** maquila
- **Leen:** maquila

### `stock_por_entrar`

- **Columnas (3):** `sku`, `uds`, `actualizado_at`
- **PK:** `sku`
- **Escriben:** auto_plan_jobs, programacion
- **Leen:** auto_plan, auto_plan_jobs, plan, programacion

### `stock_pt`

- **Columnas (13):** `id`, `sku`, `descripcion`, `lote_produccion`, `fecha_produccion`, `unidades_inicial`, `unidades_disponible`, `precio_base`, `empresa`, `estado`, `observaciones`, `stock_minimo_ud`, `dias_reposicion`
- **PK:** `id`
- **Escriben:** auto_plan_jobs, clientes, inventario, maquila, programacion
- **Leen:** admin, animus, auto_plan, clientes, gerencia, maquila, marketing, plan, programacion, tecnica

### `tareas_internas`

- **Columnas (14):** `id`, `titulo`, `descripcion`, `estado`, `prioridad`, `area`, `origen`, `origen_ref`, `fecha_compromiso`, `fecha_creacion`, `fecha_completada`, `creado_por`, `reincidente_de_id`, `notas_avance`
- **PK:** `id`
- **Escriben:** comunicacion, hub
- **Leen:** comunicacion, espagiria, hub

### `tareas_operativas`

- **Columnas (17):** `id`, `titulo`, `descripcion`, `tipo`, `producto_relacionado`, `mee_codigo`, `cantidad`, `asignado_a`, `fecha_objetivo`, `estado`, `origen_tipo`, `origen_id`, `creado_por`, `completado_por`, `fecha_creacion`, `fecha_completado`, `observaciones_cierre`
- **PK:** `id`
- **Escriben:** chat, programacion
- **Leen:** bienestar, programacion

### `tareas_raci`

- **Columnas (6):** `id`, `tarea_id`, `usuario`, `rol`, `asignado_por`, `fecha_asignacion`
- **PK:** `id`
- **Escriben:** comunicacion, hub
- **Leen:** comunicacion, espagiria, hub

### `tiempo_objetivo_sku`

- **Columnas (8):** `id`, `producto`, `etapa`, `minutos_objetivo`, `minutos_p50_historico`, `minutos_p90_historico`, `actualizado_at_utc`, `actualizado_por`
- **PK:** `id`
- **Escriben:** auto_plan
- **Leen:** auto_plan

### `turnos_operario`

- **Columnas (11):** `id`, `operario_id`, `operario_nombre`, `fecha`, `turno`, `inicio_at_utc`, `fin_at_utc`, `horas_extra_min`, `ausencia`, `motivo_ausencia`, `tenant_id`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —

### `users_mfa`

- **Columnas (9):** `username`, `secret`, `enabled`, `backup_code_hash`, `created_at`, `enabled_at`, `last_used_at`, `disabled_at`, `secret_enc`
- **PK:** `username`
- **Escriben:** mfa
- **Leen:** admin, auth, firmas, index, mfa
- **FK:** `username`→`users_passwords.username`

### `users_mfa_backup_codes`

- **Columnas (6):** `id`, `username`, `code_hash`, `created_at`, `used_at`, `used_from_ip`
- **PK:** `id`
- **Escriben:** mfa
- **Leen:** mfa
- **FK:** `username`→`users_passwords.username`

### `users_passwords`

- **Columnas (13):** `username`, `password_hash`, `changed_at`, `changed_by`, `activo`, `nombre_completo`, `cargo`, `email`, `roles_csv`, `creado_por`, `creado_at_utc`, `ultimo_login_at_utc`, `baja_motivo`
- **PK:** `username`
- **Escriben:** admin, core, database, mfa
- **Leen:** admin, core, mfa

### `usuario_roles`

- **Columnas (6):** `id`, `usuario`, `rol_codigo`, `asignado_por`, `asignado_at_utc`, `activo`
- **PK:** `id`
- **Escriben:** —
- **Leen:** —

### `usuarios_identidad`

- **Columnas (12):** `id`, `username`, `cedula`, `nombre_completo`, `cargo`, `area`, `email`, `manager_username`, `activo`, `created_at`, `updated_at`, `firma_img`
- **PK:** `id`
- **Escriben:** admin, database, identidad
- **Leen:** admin, brd, database, firmas, identidad, programacion

### `validacion_equipos`

- **Columnas (14):** `id`, `equipo_codigo`, `tipo`, `protocolo_url`, `criterios_aceptacion`, `resultado`, `estado`, `fecha_ejecucion`, `ejecutado_por`, `aprobado_por`, `fecha_revalidacion`, `observaciones`, `creado_por`, `creado_en`
- **PK:** `id`
- **Escriben:** aseguramiento
- **Leen:** aseguramiento

### `ventas_diarias`

- **Columnas (3):** `sku`, `fecha`, `cantidad`
- **PK:** `sku`, `fecha`
- **Escriben:** auto_plan_jobs
- **Leen:** auto_plan, auto_plan_jobs, core, index, plan, programacion

### `volumen_unitario_producto`

- **Columnas (3):** `producto_nombre`, `volumen_ml`, `activo`
- **PK:** `producto_nombre`
- **Escriben:** admin
- **Leen:** admin, core, programacion

### `workflow_lunes_log`

- **Columnas (11):** `id`, `ejecutado_at`, `ejecutado_por`, `fecha_lunes`, `producciones_bloqueadas`, `sincronizadas`, `asignadas`, `limpiezas_creadas`, `email_enviado`, `error`, `payload_json`
- **PK:** `id`
- **Escriben:** auto_plan_jobs
- **Leen:** auto_plan

