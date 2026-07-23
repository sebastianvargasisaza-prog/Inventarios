# Fórmulas CANÓNICAS tomadas de los BATCH RECORDS reales (producción firmada · Sebastián/Alejandro 22-jul).
# Fuente de verdad para sincronizar formula_items (lo que usa abastecimiento) con lo que REALMENTE se fabrica.
# El Excel y la fórmula vieja de la app driftaron; el batch es lo que producción pesó y Calidad verificó.
# producto (nombre canónico en formula_headers) -> {"lote_kg": base, "op": "...", "items": {codigo: porcentaje}}

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
