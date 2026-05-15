"""mig 136 · plan limpio canónico · Sebastián 14-may-2026.
Solo eos_canonico · cancela todo lo demás antes."""

STATEMENTS = [
    # Paso 1 · cancelar TODO activo (excepto eos_retroactivo)
    """UPDATE produccion_programada
       SET estado = 'cancelado',
           observaciones = COALESCE(observaciones,'') ||
             ' · CANCELADO_PLAN_LIMPIO_MIG136_' || datetime('now','-5 hours')
       WHERE estado IN ('pendiente','programado','esperando_recurso')
         AND fin_real_at IS NULL
         AND inicio_real_at IS NULL
         AND origen != 'eos_retroactivo'
         AND COALESCE(observaciones,'') NOT LIKE '%CANCELADO_PLAN_LIMPIO_MIG136%'""",
    # Paso 2 · insertar canónicos limpios
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL BHA 2%', '2026-06-12', 200, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 200kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL BHA 2%', '2026-07-27', 200, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 200kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL BHA 2%', '2026-09-10', 200, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 200kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL BHA 2%', '2026-10-26', 200, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 200kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL BHA 2%', '2026-12-10', 200, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 200kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL BHA 2%', '2027-01-25', 200, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 200kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL BHA 2%', '2027-03-11', 200, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 200kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL BHA 2%', '2027-04-26', 200, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 200kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('GEL HIDRATANTE', '2026-06-19', 58, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 58kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('GEL HIDRATANTE', '2026-08-03', 58, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 58kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('GEL HIDRATANTE', '2026-09-17', 58, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 58kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('GEL HIDRATANTE', '2026-11-03', 58, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 58kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('GEL HIDRATANTE', '2026-12-18', 58, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 58kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('GEL HIDRATANTE', '2027-02-01', 58, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 58kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('GEL HIDRATANTE', '2027-03-18', 58, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 58kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('GEL HIDRATANTE', '2027-05-03', 58, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 58kg cada 45d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR ILUMINADOR ACIDO KOJICO', '2026-06-16', 90, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 90kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR ILUMINADOR ACIDO KOJICO', '2026-08-18', 90, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 90kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR ILUMINADOR ACIDO KOJICO', '2026-10-19', 90, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 90kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR ILUMINADOR ACIDO KOJICO', '2026-12-21', 90, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 90kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR ILUMINADOR ACIDO KOJICO', '2027-02-19', 90, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 90kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR ILUMINADOR ACIDO KOJICO', '2027-04-20', 90, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 90kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL HIDRATANTE', '2026-05-19', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL HIDRATANTE', '2026-07-21', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL HIDRATANTE', '2026-09-21', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL HIDRATANTE', '2026-11-20', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL HIDRATANTE', '2027-01-19', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('LIMPIADOR FACIAL HIDRATANTE', '2027-03-23', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('EMULSION LIMPIADORA', '2026-06-22', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('EMULSION LIMPIADORA', '2026-08-21', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('EMULSION LIMPIADORA', '2026-10-20', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('EMULSION LIMPIADORA', '2026-12-22', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('EMULSION LIMPIADORA', '2027-02-22', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('EMULSION LIMPIADORA', '2027-04-23', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('SUERO HIDRATANTE AH 1.5%', '2026-07-29', 90, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 90kg cada 90d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('SUERO HIDRATANTE AH 1.5%', '2026-10-27', 90, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 90kg cada 90d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('SUERO HIDRATANTE AH 1.5%', '2027-01-26', 90, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 90kg cada 90d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('SUERO HIDRATANTE AH 1.5%', '2027-04-27', 90, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 90kg cada 90d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('SUERO ILUMINADOR TRX', '2026-05-20', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 90d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('SUERO ILUMINADOR TRX', '2026-08-19', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 90d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('SUERO ILUMINADOR TRX', '2026-11-17', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 90d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('SUERO ILUMINADOR TRX', '2027-02-15', 100, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 100kg cada 90d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('HYDRAPEPTIDE', '2026-05-21', 50, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 50kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('HYDRAPEPTIDE', '2026-07-22', 50, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 50kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('HYDRAPEPTIDE', '2026-09-22', 50, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 50kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('HYDRAPEPTIDE', '2026-11-23', 50, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 50kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('HYDRAPEPTIDE', '2027-01-22', 50, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 50kg cada 60d')""",
    """INSERT INTO produccion_programada (producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) VALUES ('HYDRAPEPTIDE', '2027-03-24', 50, 'programado', 'eos_canonico', 1, 'Plan-limpio mig 136 · 50kg cada 60d')""",
]
