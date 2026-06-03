-- Triggers PostgreSQL de EOS · generado por translate_triggers_to_pg.py

CREATE OR REPLACE FUNCTION fn_trg_audit_log_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_log es append-only (Part 11 11.10(e))';
  RETURN OLD;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_audit_log_no_delete
  BEFORE DELETE ON audit_log FOR EACH ROW
  EXECUTE FUNCTION fn_trg_audit_log_no_delete();

CREATE OR REPLACE FUNCTION fn_trg_audit_log_no_update() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'audit_log es append-only (Part 11 11.10(e))';
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_audit_log_no_update
  BEFORE UPDATE ON audit_log FOR EACH ROW
  EXECUTE FUNCTION fn_trg_audit_log_no_update();

CREATE OR REPLACE FUNCTION fn_trg_conteo_stock_fisico_no_negativo() RETURNS trigger AS $$
BEGIN
  IF NEW.stock_fisico IS NOT NULL AND NEW.stock_fisico < 0 THEN
    RAISE EXCEPTION 'stock_fisico no puede ser negativo (lo que cuentas no puede ser negativo)';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_conteo_stock_fisico_no_negativo
  BEFORE INSERT ON conteo_items FOR EACH ROW
  EXECUTE FUNCTION fn_trg_conteo_stock_fisico_no_negativo();

CREATE OR REPLACE FUNCTION fn_trg_ebr_liberado_no_edit() RETURNS trigger AS $$
BEGIN
  IF OLD.estado IN ('liberado', 'rechazado') AND (NEW.estado IS DISTINCT FROM OLD.estado OR NEW.cantidad_real_g IS DISTINCT FROM OLD.cantidad_real_g OR NEW.yield_pct IS DISTINCT FROM OLD.yield_pct OR NEW.liberado_signature_id IS DISTINCT FROM OLD.liberado_signature_id OR NEW.notas IS DISTINCT FROM OLD.notas) THEN
    RAISE EXCEPTION 'EBR liberado/rechazado es inmutable (Part 11 11.10(e))';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_ebr_liberado_no_edit
  BEFORE UPDATE ON ebr_ejecuciones FOR EACH ROW
  EXECUTE FUNCTION fn_trg_ebr_liberado_no_edit();

CREATE OR REPLACE FUNCTION fn_trg_ebr_pasos_liberado_no_delete() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = OLD.ebr_id AND estado IN ('liberado', 'rechazado')) THEN
    RAISE EXCEPTION 'pasos de EBR liberado/rechazado son inmutables · DELETE prohibido';
  END IF;
  RETURN OLD;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_ebr_pasos_liberado_no_delete
  BEFORE DELETE ON ebr_pasos_ejecutados FOR EACH ROW
  EXECUTE FUNCTION fn_trg_ebr_pasos_liberado_no_delete();

CREATE OR REPLACE FUNCTION fn_trg_ebr_pasos_liberado_no_edit() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = NEW.ebr_id AND estado IN ('liberado', 'rechazado')) THEN
    RAISE EXCEPTION 'pasos de EBR liberado/rechazado son inmutables';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_ebr_pasos_liberado_no_edit
  BEFORE UPDATE ON ebr_pasos_ejecutados FOR EACH ROW
  EXECUTE FUNCTION fn_trg_ebr_pasos_liberado_no_edit();

CREATE OR REPLACE FUNCTION fn_trg_esig_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'e_signatures es append-only (Part 11 11.50)';
  RETURN OLD;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_esig_no_delete
  BEFORE DELETE ON e_signatures FOR EACH ROW
  EXECUTE FUNCTION fn_trg_esig_no_delete();

CREATE OR REPLACE FUNCTION fn_trg_esig_no_update() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'e_signatures es append-only (Part 11 11.50)';
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_esig_no_update
  BEFORE UPDATE ON e_signatures FOR EACH ROW
  EXECUTE FUNCTION fn_trg_esig_no_update();

CREATE OR REPLACE FUNCTION fn_trg_fi_material_id_fk() RETURNS trigger AS $$
BEGIN
  IF NEW.material_id IS NOT NULL AND TRIM(NEW.material_id) != '' AND NOT EXISTS ( SELECT 1 FROM maestro_mps WHERE codigo_mp = NEW.material_id AND activo = 1 ) THEN
    RAISE EXCEPTION 'material_id no existe en maestro_mps activo (FK violation)';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_fi_material_id_fk
  BEFORE INSERT ON formula_items FOR EACH ROW
  EXECUTE FUNCTION fn_trg_fi_material_id_fk();

CREATE OR REPLACE FUNCTION fn_trg_fi_material_id_fk_upd() RETURNS trigger AS $$
BEGIN
  IF NEW.material_id IS NOT NULL AND TRIM(NEW.material_id) != '' AND NEW.material_id != OLD.material_id AND NOT EXISTS ( SELECT 1 FROM maestro_mps WHERE codigo_mp = NEW.material_id AND activo = 1 ) THEN
    RAISE EXCEPTION 'UPDATE material_id no existe en maestro_mps activo (FK violation)';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_fi_material_id_fk_upd
  BEFORE UPDATE OF material_id ON formula_items FOR EACH ROW
  EXECUTE FUNCTION fn_trg_fi_material_id_fk_upd();

CREATE OR REPLACE FUNCTION fn_trg_fi_porcentaje_valido() RETURNS trigger AS $$
BEGIN
  IF NEW.porcentaje IS NOT NULL AND (NEW.porcentaje < 0 OR NEW.porcentaje > 100) THEN
    RAISE EXCEPTION 'porcentaje fuera de rango [0,100]';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_fi_porcentaje_valido
  BEFORE INSERT ON formula_items FOR EACH ROW
  EXECUTE FUNCTION fn_trg_fi_porcentaje_valido();

CREATE OR REPLACE FUNCTION fn_trg_fi_porcentaje_valido_upd() RETURNS trigger AS $$
BEGIN
  IF NEW.porcentaje IS NOT NULL AND (NEW.porcentaje < 0 OR NEW.porcentaje > 100) THEN
    RAISE EXCEPTION 'UPDATE porcentaje fuera de rango [0,100]';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_fi_porcentaje_valido_upd
  BEFORE UPDATE OF porcentaje ON formula_items FOR EACH ROW
  EXECUTE FUNCTION fn_trg_fi_porcentaje_valido_upd();

CREATE OR REPLACE FUNCTION fn_trg_ipcres_no_delete_liberado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = OLD.ebr_id AND estado IN ('liberado','rechazado')) THEN
    RAISE EXCEPTION 'IPC resultados de EBR liberado/rechazado son inmutables';
  END IF;
  RETURN OLD;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_ipcres_no_delete_liberado
  BEFORE DELETE ON ipc_resultados FOR EACH ROW
  EXECUTE FUNCTION fn_trg_ipcres_no_delete_liberado();

CREATE OR REPLACE FUNCTION fn_trg_ipcres_no_edit_liberado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = NEW.ebr_id AND estado IN ('liberado','rechazado')) THEN
    RAISE EXCEPTION 'IPC resultados de EBR liberado/rechazado son inmutables';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_ipcres_no_edit_liberado
  BEFORE UPDATE ON ipc_resultados FOR EACH ROW
  EXECUTE FUNCTION fn_trg_ipcres_no_edit_liberado();

CREATE OR REPLACE FUNCTION fn_trg_ipcspec_no_delete_aprobado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM mbr_templates WHERE id = OLD.mbr_template_id AND estado IN ('aprobado','obsoleto')) THEN
    RAISE EXCEPTION 'IPC specs de MBR aprobado son inmutables · DELETE prohibido';
  END IF;
  RETURN OLD;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_ipcspec_no_delete_aprobado
  BEFORE DELETE ON ipc_specs FOR EACH ROW
  EXECUTE FUNCTION fn_trg_ipcspec_no_delete_aprobado();

CREATE OR REPLACE FUNCTION fn_trg_ipcspec_no_edit_aprobado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM mbr_templates WHERE id = NEW.mbr_template_id AND estado IN ('aprobado','obsoleto')) THEN
    RAISE EXCEPTION 'IPC specs de MBR aprobado son inmutables';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_ipcspec_no_edit_aprobado
  BEFORE UPDATE ON ipc_specs FOR EACH ROW
  EXECUTE FUNCTION fn_trg_ipcspec_no_edit_aprobado();

CREATE OR REPLACE FUNCTION fn_trg_ipcspec_no_insert_aprobado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM mbr_templates WHERE id = NEW.mbr_template_id AND estado IN ('aprobado','obsoleto')) THEN
    RAISE EXCEPTION 'IPC specs de MBR aprobado son inmutables · INSERT prohibido';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_ipcspec_no_insert_aprobado
  BEFORE INSERT ON ipc_specs FOR EACH ROW
  EXECUTE FUNCTION fn_trg_ipcspec_no_insert_aprobado();

CREATE OR REPLACE FUNCTION fn_trg_limpieza_no_edit_qc() RETURNS trigger AS $$
BEGIN
  IF OLD.qc_e_sign_id IS NOT NULL AND (NEW.visual_ok IS DISTINCT FROM OLD.visual_ok OR NEW.qc_e_sign_id IS DISTINCT FROM OLD.qc_e_sign_id OR NEW.completado_at_utc IS DISTINCT FROM OLD.completado_at_utc OR NEW.equipo_codigo IS DISTINCT FROM OLD.equipo_codigo) THEN
    RAISE EXCEPTION 'cleaning log validado por QC es inmutable';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_limpieza_no_edit_qc
  BEFORE UPDATE ON equipo_limpieza_log FOR EACH ROW
  EXECUTE FUNCTION fn_trg_limpieza_no_edit_qc();

CREATE OR REPLACE FUNCTION fn_trg_mbr_aprobado_no_edit() RETURNS trigger AS $$
BEGIN
  IF OLD.estado = 'aprobado' AND NEW.estado = 'aprobado' AND (OLD.titulo IS DISTINCT FROM NEW.titulo OR OLD.descripcion IS DISTINCT FROM NEW.descripcion OR OLD.lote_size_g IS DISTINCT FROM NEW.lote_size_g OR OLD.formula_version_id IS DISTINCT FROM NEW.formula_version_id) THEN
    RAISE EXCEPTION 'MBR aprobado es inmutable · obsoletá y crea v+1 (Part 11 11.10(e))';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mbr_aprobado_no_edit
  BEFORE UPDATE ON mbr_templates FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mbr_aprobado_no_edit();

CREATE OR REPLACE FUNCTION fn_trg_mbr_pasos_no_delete_aprobado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM mbr_templates WHERE id = OLD.mbr_template_id AND estado = 'aprobado') THEN
    RAISE EXCEPTION 'pasos de MBR aprobado son inmutables · DELETE prohibido';
  END IF;
  RETURN OLD;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mbr_pasos_no_delete_aprobado
  BEFORE DELETE ON mbr_pasos FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mbr_pasos_no_delete_aprobado();

CREATE OR REPLACE FUNCTION fn_trg_mbr_pasos_no_edit_aprobado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM mbr_templates WHERE id = NEW.mbr_template_id AND estado = 'aprobado') THEN
    RAISE EXCEPTION 'pasos de MBR aprobado son inmutables';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mbr_pasos_no_edit_aprobado
  BEFORE UPDATE ON mbr_pasos FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mbr_pasos_no_edit_aprobado();

CREATE OR REPLACE FUNCTION fn_trg_mbr_pasos_no_insert_aprobado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM mbr_templates WHERE id = NEW.mbr_template_id AND estado = 'aprobado') THEN
    RAISE EXCEPTION 'pasos de MBR aprobado son inmutables · INSERT prohibido';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mbr_pasos_no_insert_aprobado
  BEFORE INSERT ON mbr_pasos FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mbr_pasos_no_insert_aprobado();

CREATE OR REPLACE FUNCTION fn_trg_mbr_templates_updated_at() RETURNS trigger AS $$
BEGIN
  IF NEW.updated_at_utc IS NOT DISTINCT FROM OLD.updated_at_utc THEN
    NEW.updated_at_utc := to_char((now() AT TIME ZONE 'UTC'),'YYYY-MM-DD HH24:MI:SS');
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mbr_templates_updated_at
  BEFORE UPDATE ON mbr_templates FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mbr_templates_updated_at();

CREATE OR REPLACE FUNCTION fn_trg_mov_cantidad_positiva() RETURNS trigger AS $$
BEGIN
  IF NEW.cantidad IS NULL OR NEW.cantidad <= 0 THEN
    RAISE EXCEPTION 'cantidad debe ser > 0 (no NULL ni cero ni negativo)';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mov_cantidad_positiva
  BEFORE INSERT ON movimientos FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mov_cantidad_positiva();

CREATE OR REPLACE FUNCTION fn_trg_mov_material_id_requerido() RETURNS trigger AS $$
BEGIN
  IF NEW.material_id IS NULL OR TRIM(NEW.material_id) = '' THEN
    RAISE EXCEPTION 'material_id requerido (no puede ser vacio)';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mov_material_id_requerido
  BEFORE INSERT ON movimientos FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mov_material_id_requerido();

CREATE OR REPLACE FUNCTION fn_trg_mov_tipo_valido() RETURNS trigger AS $$
BEGIN
  IF NEW.tipo NOT IN ('Entrada','Salida','Ajuste') THEN
    RAISE EXCEPTION 'tipo invalido (debe ser Entrada/Salida/Ajuste)';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mov_tipo_valido
  BEFORE INSERT ON movimientos FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mov_tipo_valido();

CREATE OR REPLACE FUNCTION fn_trg_mps_codigo_requerido() RETURNS trigger AS $$
BEGIN
  IF NEW.codigo_mp IS NULL OR TRIM(NEW.codigo_mp) = '' THEN
    RAISE EXCEPTION 'codigo_mp requerido (no puede ser vacio)';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mps_codigo_requerido
  BEFORE INSERT ON maestro_mps FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mps_codigo_requerido();

CREATE OR REPLACE FUNCTION fn_trg_mps_stock_min_no_negativo() RETURNS trigger AS $$
BEGIN
  IF NEW.stock_minimo IS NOT NULL AND NEW.stock_minimo < 0 THEN
    RAISE EXCEPTION 'stock_minimo no puede ser negativo';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mps_stock_min_no_negativo
  BEFORE INSERT ON maestro_mps FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mps_stock_min_no_negativo();

CREATE OR REPLACE FUNCTION fn_trg_mps_stock_min_no_negativo_upd() RETURNS trigger AS $$
BEGIN
  IF NEW.stock_minimo IS NOT NULL AND NEW.stock_minimo < 0 THEN
    RAISE EXCEPTION 'UPDATE stock_minimo no puede ser negativo';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_mps_stock_min_no_negativo_upd
  BEFORE UPDATE OF stock_minimo ON maestro_mps FOR EACH ROW
  EXECUTE FUNCTION fn_trg_mps_stock_min_no_negativo_upd();

CREATE OR REPLACE FUNCTION fn_trg_op_fija_audit() RETURNS trigger AS $$
BEGIN
  IF OLD.fija_en_dispensacion IS DISTINCT FROM NEW.fija_en_dispensacion THEN
    INSERT INTO operarios_fija_audit (operario_id, valor_anterior, valor_nuevo)
    VALUES (NEW.id, OLD.fija_en_dispensacion, NEW.fija_en_dispensacion);
  END IF;
  RETURN NULL;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_op_fija_audit
  AFTER UPDATE OF fija_en_dispensacion ON operarios_planta FOR EACH ROW
  EXECUTE FUNCTION fn_trg_op_fija_audit();

CREATE OR REPLACE FUNCTION fn_trg_op_fija_no_jefe() RETURNS trigger AS $$
BEGIN
  IF NEW.fija_en_dispensacion = 1 AND COALESCE(NEW.es_jefe_produccion, OLD.es_jefe_produccion, 0) = 1 THEN
    RAISE EXCEPTION 'fija_en_dispensacion=1 incompatible con es_jefe_produccion=1';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_op_fija_no_jefe
  BEFORE UPDATE OF fija_en_dispensacion ON operarios_planta FOR EACH ROW
  EXECUTE FUNCTION fn_trg_op_fija_no_jefe();

CREATE OR REPLACE FUNCTION fn_trg_op_fija_no_jefe_ins() RETURNS trigger AS $$
BEGIN
  IF NEW.fija_en_dispensacion = 1 AND NEW.es_jefe_produccion = 1 THEN
    RAISE EXCEPTION 'fija_en_dispensacion=1 incompatible con es_jefe_produccion=1';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_op_fija_no_jefe_ins
  BEFORE INSERT ON operarios_planta FOR EACH ROW
  EXECUTE FUNCTION fn_trg_op_fija_no_jefe_ins();

CREATE OR REPLACE FUNCTION fn_trg_pedidos_b2b_updated() RETURNS trigger AS $$
BEGIN
  IF NEW.actualizado_at_utc IS NOT DISTINCT FROM OLD.actualizado_at_utc THEN
    NEW.actualizado_at_utc := to_char((now() AT TIME ZONE 'UTC'),'YYYY-MM-DD HH24:MI:SS');
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_pedidos_b2b_updated
  BEFORE UPDATE ON pedidos_b2b FOR EACH ROW
  EXECUTE FUNCTION fn_trg_pedidos_b2b_updated();

CREATE OR REPLACE FUNCTION fn_trg_pesajes_no_delete_liberado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = OLD.ebr_id AND estado IN ('liberado','rechazado')) THEN
    RAISE EXCEPTION 'pesajes de EBR liberado/rechazado son inmutables · DELETE prohibido';
  END IF;
  RETURN OLD;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_pesajes_no_delete_liberado
  BEFORE DELETE ON ebr_pesajes FOR EACH ROW
  EXECUTE FUNCTION fn_trg_pesajes_no_delete_liberado();

CREATE OR REPLACE FUNCTION fn_trg_pesajes_no_edit_liberado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = NEW.ebr_id AND estado IN ('liberado','rechazado')) THEN
    RAISE EXCEPTION 'pesajes de EBR liberado/rechazado son inmutables';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_pesajes_no_edit_liberado
  BEFORE UPDATE ON ebr_pesajes FOR EACH ROW
  EXECUTE FUNCTION fn_trg_pesajes_no_edit_liberado();

CREATE OR REPLACE FUNCTION fn_trg_pp_fija_acond_block() RETURNS trigger AS $$
BEGIN
  IF NEW.operario_acondicionamiento_id IS NOT NULL AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta WHERE id = NEW.operario_acondicionamiento_id) = 1 THEN
    RAISE EXCEPTION 'fija_en_dispensacion: este operario solo puede ir a dispensacion';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_pp_fija_acond_block
  BEFORE UPDATE OF operario_acondicionamiento_id ON produccion_programada FOR EACH ROW
  EXECUTE FUNCTION fn_trg_pp_fija_acond_block();

CREATE OR REPLACE FUNCTION fn_trg_pp_fija_acond_block_ins() RETURNS trigger AS $$
BEGIN
  IF NEW.operario_acondicionamiento_id IS NOT NULL AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta WHERE id = NEW.operario_acondicionamiento_id) = 1 THEN
    RAISE EXCEPTION 'fija_en_dispensacion: este operario solo puede ir a dispensacion';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_pp_fija_acond_block_ins
  BEFORE INSERT ON produccion_programada FOR EACH ROW
  EXECUTE FUNCTION fn_trg_pp_fija_acond_block_ins();

CREATE OR REPLACE FUNCTION fn_trg_pp_fija_elab_block() RETURNS trigger AS $$
BEGIN
  IF NEW.operario_elaboracion_id IS NOT NULL AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta WHERE id = NEW.operario_elaboracion_id) = 1 THEN
    RAISE EXCEPTION 'fija_en_dispensacion: este operario solo puede ir a dispensacion';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_pp_fija_elab_block
  BEFORE UPDATE OF operario_elaboracion_id ON produccion_programada FOR EACH ROW
  EXECUTE FUNCTION fn_trg_pp_fija_elab_block();

CREATE OR REPLACE FUNCTION fn_trg_pp_fija_elab_block_ins() RETURNS trigger AS $$
BEGIN
  IF NEW.operario_elaboracion_id IS NOT NULL AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta WHERE id = NEW.operario_elaboracion_id) = 1 THEN
    RAISE EXCEPTION 'fija_en_dispensacion: este operario solo puede ir a dispensacion';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_pp_fija_elab_block_ins
  BEFORE INSERT ON produccion_programada FOR EACH ROW
  EXECUTE FUNCTION fn_trg_pp_fija_elab_block_ins();

CREATE OR REPLACE FUNCTION fn_trg_pp_fija_env_block() RETURNS trigger AS $$
BEGIN
  IF NEW.operario_envasado_id IS NOT NULL AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta WHERE id = NEW.operario_envasado_id) = 1 THEN
    RAISE EXCEPTION 'fija_en_dispensacion: este operario solo puede ir a dispensacion';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_pp_fija_env_block
  BEFORE UPDATE OF operario_envasado_id ON produccion_programada FOR EACH ROW
  EXECUTE FUNCTION fn_trg_pp_fija_env_block();

CREATE OR REPLACE FUNCTION fn_trg_pp_fija_env_block_ins() RETURNS trigger AS $$
BEGIN
  IF NEW.operario_envasado_id IS NOT NULL AND (SELECT COALESCE(fija_en_dispensacion,0) FROM operarios_planta WHERE id = NEW.operario_envasado_id) = 1 THEN
    RAISE EXCEPTION 'fija_en_dispensacion: este operario solo puede ir a dispensacion';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_pp_fija_env_block_ins
  BEFORE INSERT ON produccion_programada FOR EACH ROW
  EXECUTE FUNCTION fn_trg_pp_fija_env_block_ins();

CREATE OR REPLACE FUNCTION fn_trg_usuarios_identidad_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := to_char(now(),'YYYY-MM-DD HH24:MI:SS');
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_usuarios_identidad_updated_at
  BEFORE UPDATE ON usuarios_identidad FOR EACH ROW
  EXECUTE FUNCTION fn_trg_usuarios_identidad_updated_at();

-- ── Inmutabilidad post-liberación · tablas hijas del EBR (audit 3-jun) ────────
-- Espejo PG de los triggers SQLite de mig 210 (conciliación), 211 (artes) y
-- observaciones. Antes faltaban en pg_triggers.sql → en prod (PG) un legajo
-- liberado/rechazado quedaba MUTABLE en estas tablas a nivel BD.
CREATE OR REPLACE FUNCTION fn_trg_concmat_no_edit_liberado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = NEW.ebr_id AND estado IN ('liberado','rechazado')) THEN
    RAISE EXCEPTION 'Conciliación de material de EBR liberado/rechazado es inmutable';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_concmat_no_edit_liberado
  BEFORE UPDATE ON ebr_conciliacion_material FOR EACH ROW
  EXECUTE FUNCTION fn_trg_concmat_no_edit_liberado();

CREATE OR REPLACE FUNCTION fn_trg_concmat_no_delete_liberado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = OLD.ebr_id AND estado IN ('liberado','rechazado')) THEN
    RAISE EXCEPTION 'Conciliación de material de EBR liberado/rechazado es inmutable · DELETE prohibido';
  END IF;
  RETURN OLD;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_concmat_no_delete_liberado
  BEFORE DELETE ON ebr_conciliacion_material FOR EACH ROW
  EXECUTE FUNCTION fn_trg_concmat_no_delete_liberado();

CREATE OR REPLACE FUNCTION fn_trg_artescod_no_edit_liberado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = NEW.ebr_id AND estado IN ('liberado','rechazado')) THEN
    RAISE EXCEPTION 'Artes/codificación de EBR liberado/rechazado es inmutable';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_artescod_no_edit_liberado
  BEFORE UPDATE ON ebr_artes_codificacion FOR EACH ROW
  EXECUTE FUNCTION fn_trg_artescod_no_edit_liberado();

CREATE OR REPLACE FUNCTION fn_trg_artescod_no_delete_liberado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = OLD.ebr_id AND estado IN ('liberado','rechazado')) THEN
    RAISE EXCEPTION 'Artes/codificación de EBR liberado/rechazado es inmutable · DELETE prohibido';
  END IF;
  RETURN OLD;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_artescod_no_delete_liberado
  BEFORE DELETE ON ebr_artes_codificacion FOR EACH ROW
  EXECUTE FUNCTION fn_trg_artescod_no_delete_liberado();

CREATE OR REPLACE FUNCTION fn_trg_ebrobs_no_edit_liberado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = NEW.ebr_id AND estado IN ('liberado','rechazado')) THEN
    RAISE EXCEPTION 'Observaciones de EBR liberado/rechazado son inmutables';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_ebrobs_no_edit_liberado
  BEFORE UPDATE ON ebr_observaciones FOR EACH ROW
  EXECUTE FUNCTION fn_trg_ebrobs_no_edit_liberado();

CREATE OR REPLACE FUNCTION fn_trg_ebrobs_no_delete_liberado() RETURNS trigger AS $$
BEGIN
  IF EXISTS (SELECT 1 FROM ebr_ejecuciones WHERE id = OLD.ebr_id AND estado IN ('liberado','rechazado')) THEN
    RAISE EXCEPTION 'Observaciones de EBR liberado/rechazado son inmutables · DELETE prohibido';
  END IF;
  RETURN OLD;
END $$ LANGUAGE plpgsql;
CREATE OR REPLACE TRIGGER trg_ebrobs_no_delete_liberado
  BEFORE DELETE ON ebr_observaciones FOR EACH ROW
  EXECUTE FUNCTION fn_trg_ebrobs_no_delete_liberado();
