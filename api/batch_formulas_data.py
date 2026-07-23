# Fórmulas CANÓNICAS tomadas de los BATCH RECORDS reales (producción firmada · Sebastián/Alejandro 22-jul).
# Fuente de verdad para sincronizar formula_items (lo que usa abastecimiento) con lo que REALMENTE se fabrica.
# El Excel y la fórmula vieja de la app driftaron; el batch es lo que producción pesó y Calidad verificó.
# producto (nombre canónico en formula_headers) -> {"lote_kg": base, "op": "...", "items": {codigo: porcentaje}}

# Pistas para crear en el maestro un código base/vehículo que un batch usa y que falta
# (típicamente el agua). controla_stock=0 = agua infinita (no genera demanda de compra · mig 218).
# codigo -> {inci, comercial, controla_stock}
MAESTRO_HINTS = {
    "MP00286": {"inci": "AQUA", "comercial": "Agua Desionizada", "controla_stock": 0},
}

# Instructivo de fabricación (paso a paso) tomado del batch record firmado. producto -> [pasos].
# Se carga en el MBR vía /api/brd/mbr/cargar-instructivo (respeta inmutabilidad: MBR aprobado -> versión
# nueva en borrador que Calidad aprueba con e-firma). El % de MP sigue saliendo de la fórmula (sección 3).
BATCH_INSTRUCTIVOS = {
    "SUERO TRIACTIVE RETINOID NAD": [
        "Paso 1. Se realizará por fases, cuidando en cada una los puntos críticos. Dispensar en beakers separados y rotulados por fases los grupos de materias primas; las cantidades en gramos las indica la orden de producción y el formato de dispensación.",
        "Paso 2. Fase A1 (base gel acuosa): calentar el agua a 40°C y disolver la alantoína; luego adicionar el Carbopol 940 y el EZ-4U homogeneizando con el agitador D-500 hasta formar un gel.",
        "Paso 3. Tomar pH y llevarlo al rango 5.65-5.75 con TEA. Disolver en Agua 20%: alantoína, Carbopol 940 y EZ-4U; ajustar el pH con TEA. Registrar TEA (mL) y pH final.",
        "Paso 4. Fase A2: agregar el agua, mezclar y dejar hidratando a temperatura ambiente ~1 hora. Agua 5%, AH 1500 kDa, AH 50 kDa, AH 300 kDa, PDRN.",
        "Paso 5. Fase A3: homogenizar los activos en el agua hasta solución transparente, sin calentar. Agua 10%, Niacinamida, N-Acetil glucosamina, D-Panthenol, Ectoin.",
        "Paso 6. Homogenizar toda la fase acuosa (A1+A2+A3) formando un gel viscoso. Fase S: disolver en calentamiento bajo, máximo 40°C: Propanediol y Capryloyl Salicylic Acid.",
        "Paso 7. Fase B0: disolver en caliente 50-55°C hasta solución aceitosa libre de partículas extrañas. Polyaquol LW, Dicaprylyl carbonate, Cetyl Alcohol, Tinogard TT, Cetyl Tranexamate Mesylate (CTM).",
        "Paso 8. Bajar la temperatura de B0 a ~45°C y homogeneizar con la Fase S; mantener a temperatura controlada ~40°C para evitar separación o cristalización.",
        "Paso 9. Fase B1 (fase oleosa semifría): homogeneizar los activos en lo posible sin calor.",
        "Paso 10. No calentar a más de 35°C. PEG-12 Dimeticone, Ceramide NP, Hydroxypinacolone Retinoate, Bakuchiol, Ácido madecásico, Apigenina.",
        "Paso 11. Añadir la fase B1 a la mezcla de B0 y S.",
        "Paso 12. Fase B2 (antioxidantes y texturizantes): añadir a la mezcla anterior formando una emulsión fluida. En esta fase solo usar la MITAD del Boron Nitride.",
        "Paso 13. La otra mitad del Boron Nitride se reserva para el complejo retinal. Tetrahexyldecyl ascorbato, Tocopherol, Boron Nitride, Extracto de Romero.",
        "Paso 14. Fase Complejo Retinal: preparar una mezcla 70:30 de Propanediol y agua; con ella humectar ligeramente el retinal hasta pasta espesa amarilla, luego añadir la Beta-ciclodextrina y encapsular la pasta.",
        "Paso 15. Añadir la otra mitad del Boron Nitride e integrar hasta obtener un polvo homogéneo tono beige. Retinal, Beta-ciclodextrina (1.1:1 molar), Propanediol, Agua.",
        "Paso 16. Añadir el complejo retinal a la fase oleosa. A partir de aquí NO usar agitador ni homogeneizador mecánico en ninguna fase, para no romper el complejo ni la emulsión.",
        "Paso 17. Fase C0 (conservantes y cofactores): añadir a la fase gel acuosa y homogeneizar muy bien. Biosure FE, NAD+, NMN 0.05%, Epi-On.",
        "Paso 18. Homogeneizar la fase oleosa con la fase gel acuosa mezclando en forma circular, evitando airear en exceso, hasta formar el emulgel.",
        "Paso 19. Fase C1 (péptidos y quelantes): dispensar al final. Homogeneizar lo más posible en el hexanediol y agregar a la mezcla ya finalizada con movimientos circulares, evitando airear y cuidando la dispersión.",
        "Paso 20. Ajustar el pH final si es necesario al rango 5.65-5.75. 1,2-Hexanediol, Disodium EDTA, Sodium Phytate, todos los péptidos y el SYN-AKE. Controles en proceso: densidad ~1.011 g/mL a 25°C, pH ~5.71.",
    ],
}

BATCH_FORMULAS = {
    "SUERO TRIACTIVE RETINOID NAD": {
        "op": "OP-2026-94", "lote": "261881", "lote_kg": 12,
        "items": {
            "MP00235": 0.5, "MP00262": 1.0, "MP00079": 0.35, "MP00274": 0.115, "MP00123": 0.3,
            "MP00239": 0.05, "MP00132": 1.7, "MP00178": 0.003, "MP00149": 0.5, "MP00240": 2.0,
            "MP00159": 0.005, "MP00063": 0.1, "MP00223": 0.01, "MP00172": 0.005, "MP00201": 0.5,
            "MP00236": 0.05, "MP00184": 1.5, "MP00234": 0.01, "MP00261": 0.035, "MP00179": 0.01,
            "MP00245": 0.5, "MP00264": 0.153, "MP00006": 0.4, "MP00116": 2.0, "MP00286": 70.913,
            "MP00040": 4.0, "MP00242": 0.05, "MP00103": 0.5, "MP00177": 0.001, "MP00157": 0.05,
            "MP00246": 0.25, "MP00043": 4.5, "MP00142": 0.05, "MP00287": 0.05, "MP00200": 0.2,
            "MP00173": 0.03, "MP00068": 0.95, "MP00288": 0.5, "MP00163": 0.3, "MP00174": 0.005,
            "MP00275": 0.05, "MP00226": 0.15, "MP00250": 0.005, "MP00046": 0.15, "MP00148": 5.0,
            "MP00047": 0.5,
        },
    },
}
