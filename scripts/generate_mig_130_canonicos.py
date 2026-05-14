"""Genera mig 130 · programa canónicos para 12 meses respetando reglas.

Sebastián 14-may-2026: paso 5/6. Frecuencias confirmadas:
- LIMP BHA 2%: 200kg cada 45d
- LKJ: 90kg cada 60d
- LIMP HIDRATANTE: 100kg cada 60d
- EMUL LIMPIADORA: 100kg cada 60d
- GEL HIDRATANTE: 58kg cada 45d
- HYDRAPEPTIDE: 50kg cada 60d (lanzamiento)
- SAH: 90kg cada 90d

Respeta:
- Solo Lun-Vie
- Skip festivos colombianos
- Lotes >50kg ocupan el día solos
- Próximo lote = última_producción_real + frecuencia
"""
from datetime import date, timedelta

# Configuración: producto, kg/lote, freq_dias, ultima_produccion_fecha
CANONICOS = [
    {"producto": "LIMPIADOR FACIAL BHA 2%",       "kg": 200, "freq": 45, "ultima": "2026-04-28"},
    {"producto": "LIMPIADOR ILUMINADOR ACIDO KOJICO", "kg": 90, "freq": 60, "ultima": "2026-04-15"},
    {"producto": "LIMPIADOR FACIAL HIDRATANTE",  "kg": 100, "freq": 60, "ultima": None},
    {"producto": "EMULSION LIMPIADORA",          "kg": 100, "freq": 60, "ultima": "2026-04-22"},
    {"producto": "GEL HIDRATANTE",                "kg": 58,  "freq": 45, "ultima": "2026-05-05"},
    {"producto": "HYDRAPEPTIDE",                  "kg": 50,  "freq": 60, "ultima": None},
    {"producto": "SUERO HIDRATANTE AH 1.5%",     "kg": 90,  "freq": 90, "ultima": "2026-04-30"},
]

# Festivos colombianos 2026-2027 hardcoded (los que afectan horizonte)
FESTIVOS = {
    date(2026, 5, 18),  # Ascensión
    date(2026, 6, 8),   # Corpus Christi
    date(2026, 6, 15),  # Sagrado Corazón
    date(2026, 6, 29),  # S Pedro y Pablo
    date(2026, 7, 20),  # Independencia
    date(2026, 8, 7),   # Boyacá
    date(2026, 8, 17),  # Asunción
    date(2026, 10, 12), # Raza
    date(2026, 11, 2),  # Todos Santos
    date(2026, 11, 16), # Indep Cartagena
    date(2026, 12, 8),  # Inmaculada
    date(2026, 12, 25), # Navidad
    date(2027, 1, 1),   # Año Nuevo
    date(2027, 1, 11),  # Reyes movido
    date(2027, 3, 22),  # San José movido
    date(2027, 3, 25),  # Jueves Santo
    date(2027, 3, 26),  # Viernes Santo
    date(2027, 5, 1),   # Trabajo
    date(2027, 5, 10),  # Ascensión movido
}


def proxima_fecha_habil(fecha_obj):
    """Devuelve próxima fecha Lun-Vie no festivo."""
    cur = fecha_obj
    for _ in range(20):  # max 20 días lookahead
        if cur.weekday() < 5 and cur not in FESTIVOS:
            return cur
        cur = cur + timedelta(days=1)
    return cur


def sql_quote(s):
    if s is None:
        return 'NULL'
    return "'" + str(s).replace("'", "''") + "'"


def main():
    hoy = date(2026, 5, 14)
    horizon_end = hoy + timedelta(days=365)

    statements = []
    statements.append("-- mig 130 · canónicos 12 meses con frecuencias confirmadas Sebastián")
    statements.append("-- Generado por scripts/generate_mig_130_canonicos.py")

    total_lotes = 0

    for cfg in CANONICOS:
        producto = cfg["producto"]
        kg = cfg["kg"]
        freq = cfg["freq"]
        ultima_str = cfg["ultima"]

        # Punto de partida: si hay última real, próximo = última + freq.
        # Si no, próximo lunes hábil desde hoy.
        if ultima_str:
            base = date.fromisoformat(ultima_str) + timedelta(days=freq)
        else:
            base = hoy + timedelta(days=(7 - hoy.weekday()) % 7 or 7)

        cur = proxima_fecha_habil(base)
        slot = 1

        while cur <= horizon_end:
            marker = f"CANON_MIG130_{producto.replace(' ', '_')[:25]}_{slot:02d}"
            statements.append(
                f"INSERT INTO produccion_programada "
                f"(producto, fecha_programada, cantidad_kg, estado, origen, lotes, observaciones) "
                f"SELECT {sql_quote(producto)}, '{cur.isoformat()}', {kg}, "
                f"'programado', 'eos_canonico', 1, "
                f"'Canónico mig130 · {kg}kg cada {freq}d · slot {slot}' "
                f"WHERE NOT EXISTS ("
                f"SELECT 1 FROM produccion_programada "
                f"WHERE observaciones LIKE '%{marker}%')"
            )
            # Update con marker (después del insert)
            statements.append(
                f"UPDATE produccion_programada "
                f"SET observaciones = observaciones || ' · {marker}' "
                f"WHERE producto = {sql_quote(producto)} "
                f"AND fecha_programada = '{cur.isoformat()}' "
                f"AND origen = 'eos_canonico' "
                f"AND observaciones LIKE 'Canónico mig130 · {kg}kg cada {freq}d · slot {slot}'"
            )
            total_lotes += 1
            slot += 1
            cur = proxima_fecha_habil(cur + timedelta(days=freq))

    output = "api/mig_130_canonicos_data.py"
    with open(output, 'w', encoding='utf-8') as f:
        f.write('"""Datos para mig 130 · canónicos 12 meses.\n')
        f.write('Generado por scripts/generate_mig_130_canonicos.py · Sebastián 14-may-2026.\n')
        f.write('NO editar a mano · regenerar si cambian frecuencias.\n')
        f.write('"""\n\n')
        f.write('STATEMENTS = [\n')
        for stmt in statements:
            if stmt.startswith('--'):
                f.write(f'    # {stmt[2:].strip()}\n')
            else:
                f.write(f'    """{stmt}""",\n')
        f.write(']\n')

    print(f"✓ Generado: {output}")
    print(f"  Total productos: {len(CANONICOS)}")
    print(f"  Total lotes próximos 365d: {total_lotes}")


if __name__ == '__main__':
    main()
