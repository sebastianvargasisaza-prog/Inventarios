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
    "LIMPIADOR FACIAL BHA 2%": [
        "Paso 1. En un recipiente, adicionar con agitación constante y a temperatura ambiente el 100% del agua desionizada y la Centella Asiática (Premezcla 1).",
        "Paso 2. Una vez homogénea, adicionar la Goma Xanthan usando la hélice de dispersión. Mantener en agitación constante hasta completa homogeneidad.",
        "Paso 3. En otro recipiente, adicionar Propilenglicol (100%) y calentar a ~70°C. Con agitación constante, adicionar el Ácido Salicílico hasta completa disolución. Registrar temperatura real.",
        "Paso 4. Una vez disuelto el ácido salicílico, adicionar lentamente y con agitación constante el Polietilenglicol 400 (PEG-400). (Premezcla 2)",
        "Paso 5. En un recipiente, preparar los tensoactivos y el aceite de árbol de té: adicionar con agitación constante AOS-40, Probetaína (Cocamidopropyl Betaine) y Aceite de árbol de té. (Premezcla 3)",
        "Paso 6. Adicionar poco a poco y con agitación constante la Premezcla 2 sobre la Premezcla 3, usando la hélice antiespuma. (Premezcla 4)",
        "Paso 7. Una vez homogéneas y a temperatura ambiente, adicionar la Premezcla 4 sobre la Premezcla 1. Dejar ~20 minutos en agitación constante. Registrar tiempo real.",
        "Paso 8. Adicionar el Fenoxietanol y seguir agitando 5 minutos más. Registrar tiempo real.",
        "Paso 9. Finalmente adicionar la Trietanolamina. Agitar 20 minutos a velocidad constante de ~1000 RPM hasta mezcla homogénea. Registrar RPM real.",
        "Paso 10. Apagar el agitador hasta que la mezcla quede totalmente uniforme. Controles en proceso: densidad ~0.995 g/mL a 25°C, viscosidad.",
    ],
    "EMULSION HIDRATANTE ILUMINADORA": [
        "Paso 1. PREPARACIÓN FASE A: pesar el agua desionizada en el homogeneizador o en un tanque de capacidad adecuada. Reservar 10% del agua aparte para dilución de activos.",
        "Paso 2. Encender agitador a 400-450 rpm. Tamizar el EZ-4U sobre el agua bajo agitación constante, agregando lentamente en zona de máxima agitación. No agregar en zonas sin movimiento (forma grumos difíciles de dispersar).",
        "Paso 3. Agitar durante 10-15 minutos hasta dispersión completamente homogénea. No deben verse partículas secas ni grumos.",
        "Paso 4. En recipiente aparte: dispersar Ácido Hialurónico 300 kDa en agua fría bajo agitación suave. Agitar hasta solución uniforme. No usar calor.",
        "Paso 5. Disolver N-Acetilglucosamina y Niacinamida en agua. Agitar hasta disolución completa.",
        "Paso 6. Incorporar al homogeneizador en orden: solución de HA, solución NAG + Niacinamida, Propanediol, EDTA Disódico.",
        "Paso 7. Agitar 10 min a 300 rpm hasta fase acuosa uniforme y homogénea.",
        "Paso 8. ADICIÓN PEG-12 AL HOMOGENEIZADOR: reducir agitación a 200 rpm, agregar PEG-12 Dimeticona directamente al homogeneizador y agitar 5 minutos hasta incorporación completa y homogénea.",
        "Paso 9. CRÍTICO: la PEG-12 Dimeticona DEBE estar en el homogeneizador ANTES de agregar la Fase B. Su presencia durante la emulsificación actúa como co-emulsionante, reduce el tamaño de gota y produce una emulsión más blanca y estable.",
        "Paso 10. PREPARACIÓN FASE B: en recipiente auxiliar de acero inoxidable, pesar en orden: Dicaprylyl Carbonate, Propylheptyl Caprylate, Coco-Caprylate, Alcohol cetílico, Cetyl Tranexamate Mesylate (CTM).",
        "Paso 11. Calentar bajo agitación constante hasta 65-70°C. Mantener temperatura y agitación hasta que el CTM esté COMPLETAMENTE DISUELTO y la mezcla sea TRANSPARENTE. Registrar temperatura real.",
        "Paso 12. CRÍTICO: no avanzar si persiste turbidez o partículas sólidas. Si después de 15 min a 70°C el CTM no disuelve completamente, aumentar a 75°C y agitar 10 min más.",
        "Paso 13. Sin retirar del calor, agregar en orden: PolyAquol LW, Tetrahexyldecyl Ascorbate, Aceite de Cacay, Ceramida NP, Vitamina E, Tinogard TT, 4-Butilresorcinol.",
        "Paso 14. Retirar del calor. Enfriar a 40-45°C bajo agitación suave.",
        "Paso 15. EMULSIFICACIÓN: aumentar agitación del homogeneizador a 300-400 rpm. Agregar la Fase B sobre el homogeneizador (Fase A + PEG-12) de forma LENTA Y CONTINUA, en hilo fino, bajo agitación constante. NUNCA agregar Fase A sobre Fase B.",
        "Paso 16. Continuar agitando 15 minutos hasta emulsión homogénea y uniforme.",
        "Paso 17. OPCIONAL (si la emulsión presenta aspecto translúcido o gelatinoso): activar el rotor-estátor del homogeneizador durante 1-2 minutos. Reduce el tamaño de gota y produce emulsión más blanca y estable.",
        "Paso 18. Reducir agitación a 150-200 rpm. Agregar Fenil Trimeticona (Silicona BM 956) directamente al homogeneizador. Agitar 10 minutos hasta incorporación completa y uniforme. Verificar ausencia de separación o acumulación superficial.",
        "Paso 19. ADICIÓN FASE C (ACTIVOS): verificar temperatura del batch < 35°C antes de iniciar. Disolver Glicinamida HCl en el agua reservada, agitar hasta disolución completa y agregar al homogeneizador.",
        "Paso 20. Oligopéptido-68: pesada directa en balanza analítica, disolver en agua y agregar al homogeneizador.",
        "Paso 21. Disolver Extracto de Regaliz en 50 g del agua reservada y agregar al homogeneizador. Agitar 10 minutos a 200 rpm hasta homogeneidad.",
        "Paso 22. FASE D Y AJUSTE DE pH: agregar Phenoxyethanol bajo agitación 200 rpm, luego Ethylhexylglycerin (agitar 3 min), luego 1,2-Hexanediol (agitar 5 min). Ajustar pH al final con Trietanolamina 85%. Controles en proceso: pH ~5.7 a 25°C, densidad ~1.005 g/mL.",
    ],
    "CONTORNO DE CAFEINA": [
        "Paso 1. Dividir el agua desionizada en 2 partes (50% y 50%).",
        "Paso 2. En el recipiente 1 adicionar el 50% del agua desionizada y, con agitación constante, adicionar las siguientes materias primas: Ácido tranexámico, Gluconolactona, Alantoína, Sorbato de Potasio, Benzoato de sodio, Aloe Vera, Centella Asiática.",
        "Paso 3. Seguir con: Acetyl Tetrapeptido-5, Adenosina, Ácido láctico, Vitamina E y Glicerina.",
        "Paso 4. Observación: adicionar uno por uno hasta total disolución; no adicionar una materia prima si la anterior no se ha disuelto completamente. Controles en proceso: densidad ~1.044 g/mL a 25°C, pH ~5.64 (se ajusta con Trietanolamina).",
        "NOTA: instructivo del batch digital marcado como INCOMPLETO por producción (Evelin Obeso). Faltan por ubicar en pasos: cafeína anhidra, dimethicone, propilenglicol, phenoxyethanol, ácido hialurónico 1500/50 kD. Completar con Alejandro/Producción antes de dar por cerrado.",
    ],
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
    "LIMPIADOR FACIAL BHA 2%": {
        # Batch OP-2026-96 · 200kg · lote 261901. 12 mat, 100%. Todos los códigos NUMÉRICOS.
        # Centella = MP00181 (extract plano, NO triterpenes MP00176). Árbol de té MP00085.
        "op": "OP-2026-96", "lote": "261901", "lote_kg": 200,
        "items": {
            "MP00123": 1.9, "MP00121": 10.0, "MP00195": 10.0, "MP00080": 2.0, "MP00210": 2.0,
            "MP00021": 1.0, "MP00286": 63.0, "MP00073": 1.0, "MP00212": 4.0, "MP00181": 0.05,
            "MP00294": 5.0, "MP00085": 0.05,
        },
    },
    "EMULSION HIDRATANTE ILUMINADORA": {
        # Fórmula del batch OP-2026-88 (28 mat, 100%) CON CÓDIGOS CANÓNICOS (remapeados vs Excel Alejandro
        # v8_2 · 23-jul). El batch usó códigos errados que en el maestro son OTRO material:
        #   MP00301 Propylheptyl Caprylate -> MP00030 (batch MP00301 = Ethylhexylglycerin en maestro)
        #   MP00302 Ethylhexylglycerin     -> MPEHGL01
        #   MP00303 Coco-Caprylate         -> MPCOCP01 (batch MP00303 = Ethylhexylglycerin en maestro)
        #   MP00300 Ceramide NP            -> MP00103 (batch MP00300 = SODIUM COCOYL GLYCINATE en maestro · ¡peligroso!)
        # Cacay MP00291 se deja (en la app SÍ es cacay). VitE MP00079 polvo (batch) · grado a confirmar Alejandro.
        "op": "OP-2026-88", "lote": "261832", "lote_kg": 35,
        "items": {
            "MP00127": 1.75, "MP00262": 2.0, "MP00079": 0.3, "MP00123": 0.1, "MP00132": 2.0,
            "MP00149": 0.3, "MP00240": 3.0, "MPEHGL01": 0.4, "MP00063": 0.1, "MP00201": 1.0,
            "MPCOCP01": 1.0, "MP00184": 1.5, "MP00291": 0.5, "MP00245": 0.3, "MP00006": 0.5,
            "MP00021": 0.9, "MP00286": 66.139, "MP00040": 6.0, "MP00030": 3.0, "MP00231": 0.5,
            "MP00177": 0.001, "MP00120": 0.01, "MP00157": 0.1, "MP00304": 0.2, "MP00043": 3.0,
            "MP00103": 0.3, "MP00046": 0.1, "MP00148": 5.0,
        },
    },
    "CONTORNO DE CAFEINA": {
        "op": "OP-2026-11", "lote": "", "lote_kg": 10,
        "items": {
            "MP00217": 0.05, "MP00270": 1.0, "MP00293": 0.3, "MP00138": 0.3, "MP00152": 0.1,
            "MP00121": 5.0, "MP00252": 0.05, "MP00195": 3.0, "MP00045": 0.3, "MP00069": 1.5,
            "MP00167": 3.0, "MP00021": 1.0, "MP00286": 82.57, "MP00078": 0.5, "MP00202": 0.3,
            "MP00142": 0.2, "MP00175": 0.03, "MP00163": 0.3, "MP00047": 0.5,
        },
    },
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
