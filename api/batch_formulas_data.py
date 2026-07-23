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
    "GEL HIDRATANTE": [
        "Paso 1. Dispensación: verificar limpieza del área y utensilios. Pesar MP generales; pesar los activos de baja dosis (Ectoína, Pantenol) en balanza analítica.",
        "Paso 2. Dispersar los polímeros (sin neutralizar) en el 80% del agua desionizada a temperatura ambiente. Agregar glicerina. Agitar a 200-300 rpm hasta incorporación; subir a 400-500 rpm.",
        "Paso 3. Mezclar 10-15 min (sistema fluido y ligeramente opaco = normal). Espolvorear el Carbomer en lluvia fina. Mezclar 15-20 min a 400 rpm. NO agregar TEA todavía (los polímeros quedan dispersos sin gelificar).",
        "Paso 4. Conservantes: bajo agitación (300 rpm) agregar Phenoxyethanol, Ethylhexylglycerin y 1,2-Hexanediol. Mezclar 5 min hasta homogeneidad.",
        "Paso 5. Verificación: aspecto de dispersión fluida, homogénea, sin grumos. Si persisten grumos, continuar agitación 1-2 h antes de avanzar.",
        "Paso 6. Fase oleosa: con agitación a 300-400 rpm, agregar los oleosos uno a uno en hilo fino: Propylheptyl Caprylate, Dicaprylyl Carbonate, Phenyl Trimethicone, PEG-12 Dimethicone, Ceramide NP, Tocoferol.",
        "Paso 7. Activos hidrosolubles: en recipiente auxiliar disolver en agua desionizada Niacinamida (disolución completa), Ectoína, Pantenol, Centella Extract y PDRN.",
        "Paso 8. Ácido Hialurónico 300 kDa: hidratar en agua desionizada fría, agitar suave con varilla 10-15 min (no usar calor). Incorporar al tanque bajo agitación suave (200-300 rpm).",
        "Paso 9. Neutralización y formación del gel: reducir agitación a 200 rpm. Agregar Trietanolamina 85% esperando ~2 min entre adiciones. Observar la gelificación progresiva.",
        "Paso 10. Medir pH tras cada adición. Objetivo 6.0-6.3; detener al alcanzarlo. Registrar TEA total. Agitar 5 min a 300 rpm y verificar gel homogéneo.",
    ],
    "Suero Exfoliante BHA 2%": [
        "Paso 1. En el vaso principal cargar la mayor parte del agua (~53%) a 20-25°C con agitación constante.",
        "Paso 2. Espolvorear los polímeros lentamente y uno a uno bajo agitación, dejando dispersar/hidratar cada uno antes del siguiente: Carbómero, Goma xantana y las cadenas de HA.",
        "Paso 3. Calentar a 40-45°C (si se requiere) hasta dispersión homogénea, translúcida y sin grumos.",
        "Paso 4. Incorporar en orden: Disodium EDTA (quelante) primero, luego Salicilato de betaína, Ácido tranexámico, N-Acetyl-Glucosamine, Glycinamide, Ectoína y Zinc PCA.",
        "Paso 5. NO neutralizar aún (el carbómero permanece sin espesar hasta el ajuste final de pH). Reservar para adición en frío el Glutatión y el Epi-On (oxidable/termolábil). Mantener ≤45°C.",
        "Paso 6. Con la base a 40-45°C, incorporar el PEG-12 Dimethicone bajo agitación hasta homogeneización total.",
        "Paso 7. Fase B (co-solventes): en vaso auxiliar combinar Ethoxydiglycol, DMI, Propanediol y Propilenglicol; añadir agua. Calentar a 50-55°C con agitación.",
        "Paso 8. Añadir el Ácido salicílico y disolver por completo; luego el LHA (Capryloyl Salicylic Acid). Agitar hasta solución límpida sin cristales.",
        "Paso 9. Incorporar Gluconolactona y Ácido succínico; disolver totalmente.",
        "Paso 10. Dosificar el NaOH 10% y la Trietanolamina bajo agitación (neutralizan los salicílicos formando sales solubles y elevando el pH).",
        "Paso 11. Fase C (silimarina): calentar 5% de agua a 70°C, añadir Silymarin Extract y agitar 5-10 min. Filtrar en caliente (~70°C) por membrana 0.45 µm.",
        "Paso 12. Enfriar el filtrado a ≤40°C y reservar. Si aparece precipitado, mantener a ~40°C e incorporar de inmediato.",
        "Paso 13. Fase E (vehículo péptido): mezclar agua con 1,2-Hexanediol a 25-30°C; pesar el Myristoyl Nonapeptide-3 en balanza analítica e incorporar, disolviendo con agitación suave.",
        "Paso 14. Asegurar la base A (con activos y Fase S) a ≤40°C. Bajo agitación moderada incorporar lentamente la Fase B (~40°C, ya pre-neutralizada) sobre la base A.",
        "Paso 15. Incorporar en frío (≤40°C, minimizando aireación): Glutatión, Epi-On y el filtrado de silimarina atemperado. Homogeneizar.",
        "Paso 16. Verificar pH del lote combinado (debe acercarse a 4.55-4.60); afinar si es necesario.",
        "Paso 17. Incorporar la Fase E (vehículo péptido) a 25-30°C con agitación suave. Verificar pH. STOP si pH > 4.70: corregir con micro-dosis de Ácido succínico antes de continuar.",
        "Paso 18. Con el lote a <35°C, añadir el BioSure FE y homogeneizar 10 min.",
        "Paso 19. Aforar con el agua remanente. Homogeneizar 10-15 min a baja velocidad minimizando la aireación (reposo o vacío suave para desairear).",
        "Paso 20. Registrar lecturas finales: aspecto, pH (4.55-4.60) y viscosidad (1400-1800 cP).",
    ],
    "BOOSTER TENSOR": [
        "Paso 1. FASE A1 (gel base Carbopol): cargar el agua de la Fase A1 (15%). Dispersar el Carbopol en lluvia (800-1000 rpm). Hidratar 10-15 min hasta dispersión completa. Añadir Disodium EDTA.",
        "Paso 2. FASE A2 (film + hidratación + espículas): disolver el Pullulan completamente (30-35°C, 15% del agua). Espolvorear el HA y dejar hidratar 20-30 min. Pre-humectar las espículas.",
        "Paso 3. Incorporar las espículas en lluvia (300-400 rpm). Verificar suspensión homogénea.",
        "Paso 4. FASE A3 (tixotropía, Aerosil): crear vórtice moderado. Dispersar el Aerosil lentamente en 15% del agua. Homogeneizar hasta suspensión uniforme.",
        "Paso 5. UNIÓN DE FASES POLIMÉRICAS: incorporar Fase A2 sobre Fase A1 y mezclar 5-10 min. Añadir Fase A3 lentamente (700-900 rpm). Mezclar hasta sistema homogéneo.",
        "Paso 6. NEUTRALIZACIÓN: neutralizar gradualmente con Trietanolamina hasta pH 6.0 ± 0.1. Evitar sobre-neutralización.",
        "Paso 7. FASE B (glicoles + péptidos): disolver los péptidos en DMI + Ethoxydiglycol + agua. Mantener temperatura <35°C. Incorporar al gel neutralizado.",
        "Paso 8. FASE D (activos finales): disolver Niacinamida, Betaína y 1,2-Hexanediol en agua. Añadir Epi-On suavemente. Incorporar al lote.",
        "Paso 9. FASE E (sensorial): añadir el PEG-12 Dimethicone. Mezclar hasta homogeneidad completa.",
        "Paso 10. FASE F (conservación): añadir Phenoxyethanol + Ethylhexylglycerin. Ajustar con agua c.s.",
        "Paso 11. CONTROLES FINALES: pH 6.0 ± 0.1. Apariencia gel fluido translúcido, sin grumos ni sedimentación. Desairear 30-60 min antes de envasar.",
    ],
    "AZ HIBRID CLEAR": [
        "Paso 1. Dividir el agua desionizada en partes (20%, 30%, 30%, 20%).",
        "Paso 2. En el recipiente 1, adicionar el 20% del agua desionizada y calentar hasta 65°C.",
        "Paso 3. Al alcanzar 65°C, adicionar con agitación constante: EDTA disódico, Azeloil diglicinato de potasio, Niacinamida, Ácido tranexámico, Fosfato/Fitato de sodio.",
        "Paso 4. Seguir con Betaína, Terpenos solubles 80%, Fitato de sodio, Acetyl tetrapeptide-40 y Vitamina E en polvo (esta última se adiciona de último).",
        "Paso 5. Observación: adicionar uno por uno hasta total disolución; no adicionar una MP si la anterior no se ha disuelto completamente.",
        "Paso 6. En el recipiente 2, adicionar 30% del propilenglicol y calentar a 70°C. Al alcanzar, adicionar con agitación: ácido azelaico y ácido capriloil salicílico.",
        "Paso 7. En el recipiente 3, adicionar 20% del propilenglicol y dispersar el HA 50 kDa y el HA 300 kDa. Una vez dispersado, adicionar 20% del agua.",
        "Paso 8. En el recipiente 4, adicionar 30% del propilenglicol y dispersar el Carbopol. Luego adicionar con batidora de mano el 30% del agua desionizada.",
        "Paso 9. En el recipiente 5, adicionar el propilenglicol restante y dispersar la Goma Xantan. Luego adicionar con batidora el agua desionizada restante.",
        "Paso 10. Con las premezclas homogéneas, verificar que el recipiente 1 esté a 65°C. Registrar temperatura real. Luego adicionar con agitación el recipiente 2 sobre el 1.",
        "Paso 11. A la premezcla 1 adicionar con agitación constante el recipiente 3 y finalmente el 4 y el 5.",
        "Paso 12. Esperar a que la premezcla esté a 40°C. Adicionar: Trietanolamina, Hidróxido de sodio, Epi-On, 1,2-Hexanediol y Gransil.",
        "Paso 13. Dejar el producto en agitación constante 20 min. Registrar tiempo real. Ajustar pH final según especificación.",
    ],
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
    # NOTA: estos 4 guardan los CÓDIGOS RAW del batch (para que la matriz muestre las inconsistencias).
    # Gel Hidratante y otros repiten los códigos errados de Emulsión (MP00301/302/300/252) · se remapean
    # al canónico en la normalización final consolidada, NO ahora.
    "GEL HIDRATANTE": {
        "op": "OP-2026-85", "lote": "", "lote_kg": 80,
        "items": {
            "MP00296": 0.25, "MP00127": 1.75, "MP00123": 0.2, "MP00302": 0.4, "MP00223": 0.03,
            "MP00252": 0.03, "MP00195": 2.0, "MP00236": 0.05, "MP00184": 1.0, "MP00245": 0.3,
            "MP00006": 0.4, "MP00021": 0.9, "MP00286": 84.69, "MP00078": 0.3, "MP00040": 2.0,
            "MP00301": 3.0, "MP00157": 0.1, "MP00300": 0.5, "MP00226": 0.1, "MP00148": 2.0,
        },
    },
    "Suero Exfoliante BHA 2%": {
        "op": "OP-2026-69", "lote": "", "lote_kg": 45,
        "items": {
            "MP00296": 0.2, "MP00262": 1.0, "MP00123": 0.9, "MP00273": 0.1, "MP00270": 1.0,
            "MP00263": 0.1, "MP00121": 9.5, "MP00252": 0.05, "MP00145": 0.05, "MP00210": 1.45,
            "MP00184": 2.0, "MP00167": 3.0, "MP00245": 0.5, "MP00259": 2.0, "MP00256": 2.0,
            "MP00116": 0.5, "MP00286": 67.249, "MP00073": 0.1, "MP00231": 0.5, "MP00157": 0.05,
            "MP00246": 0.45, "MP00043": 4.5, "MP00260": 0.3, "MP00297": 0.9, "MP00142": 0.05,
            "MP00068": 1.0, "MP00283": 0.3, "MP00226": 0.1, "MP00250": 0.002, "MP00046": 0.05,
            "MP00277": 0.1,
        },
    },
    "BOOSTER TENSOR": {
        "op": "OP-2026-95", "lote": "", "lote_kg": 15,
        "items": {
            "MP00123": 0.1, "MP00056": 0.3, "MP00223": 0.03, "MP00184": 1.5, "MP00155": 0.03,
            "MP00179": 0.03, "MP00245": 0.5, "MP00259": 2.0, "MP00256": 1.0, "MP00116": 1.0,
            "MP00286": 89.689, "MP00177": 0.003, "MP00248": 0.06, "MP00298": 0.3, "MP00215": 0.1,
            "MP00200": 0.15, "MP00068": 0.95, "MP00163": 0.2, "MP00174": 0.005, "MP00250": 0.003,
            "MP00046": 0.05, "MP00148": 2.0,
        },
    },
    "AZ HIBRID CLEAR": {
        "op": "OP-2026-90", "lote": "", "lote_kg": 28,
        "items": {
            "MP00169": 2.0, "MP00296": 0.2, "MP00123": 1.25, "MP00239": 0.03, "MP00178": 0.003,
            "MP00102": 0.05, "MP00121": 20.0, "MP00236": 0.05, "MP00221": 6.0, "MP00167": 3.0,
            "MP00245": 0.5, "MP00286": 48.817, "MP00073": 0.1, "MP00244": 5.0, "MP00072": 0.8,
            "MP00295": 4.0, "MP00215": 0.05, "MP00157": 0.05, "MP00246": 0.5, "MP00297": 0.9,
            "MP00068": 1.0, "MP00163": 0.05, "MP00283": 0.5, "MP00226": 0.1, "MP00046": 0.05,
            "MP00148": 5.0,
        },
    },
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
