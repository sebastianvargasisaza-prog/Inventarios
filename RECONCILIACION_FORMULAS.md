# 🧬 Reconciliación Fórmulas · App ↔ Excel maestro — VEREDICTO

Fuente de verdad: **FORMULAS_MAESTRO_v2_1 (2).xlsx** (28 productos, 1 hoja/producto, col CÓD. BATCH = código MP).
Maestro MP/INCI: **ACTUALIZAR_INCI_final.xlsx**. Método: determinista (openpyxl + psql eos_dev) + 33 agentes con
verificación adversarial. Los % del Excel son fracción (0.05) = app % (5.0), factor 100x consistente en TODO.

## ✅ Veredicto: las fórmulas maestras están MAYORMENTE PERFECTAS
- **23 de 28 fórmulas del Excel coinciden EXACTO** con la app (mismos códigos + mismos %, sin una sola
  diferencia de porcentaje). Los % están perfectos en el 100% de los ingredientes que cruzan.
- El "ruido" es benigno: el Excel no lista el AGUA como línea (la app sí) y lista trietanolamina al 0% en 3
  productos (no consume, inocuo).

## 🟡 2 fórmulas del Excel a las que la app les FALTAN ingredientes (FIXABLE · códigos ya existen)
1. **BLUSH BALM** — faltan en la app: `MP00127` BM-956 (20.271%), `MPCOCP01` Coco-caprylate (3%),
   `MPBNIT01` Boron nitride (2%) + línea PIGMENTOS CI (7.5%, según tono). Los 3 códigos ya existen en maestro.
2. **LIP SÉRUM VOLUMINIZADOR** — falta `MP00209` PIB-24 **q.s.p. 100%** (relleno · crítico: sin él la fórmula
   no cierra a 100% ni se descuenta el relleno) + PIGMENTOS CI (1.05%). MP00209 existe.

## 🔁 10 productos "solo en app" = DUPLICADOS del Excel (solo nombre distinto · YA usan código canónico)
Mismo producto, otro nombre (doble espacio, "+", tilde, "FORMULA NUEVA"). **Acción: consolidar al nombre del Excel.**

| App | = Excel |
|---|---|
| EMULSION HIDRATANTE  B3+BHA | EMULSIÓN HIDRATANTE B3 BHA |
| ESENCIA DE CENTELLA ASIATICA | ESENCIA CENTELLA ASIÁTICA |
| HYDRA BALANCE | HYDRA-BALANCE |
| LIMPIADOR FACIAL HIDRATANTE | LIMPIADOR HIDRATANTE |
| LIP SERUM VOLUMINIZADOR PEPTIDOS | LIP SÉRUM VOLUMINIZADOR CON PÉPTIDOS |
| SUERO ANTIOXIDANTE RENOVA C10 | SUERO ANTIOXIDANTE RENOVA C |
| SUERO DE NIACINAMIDA 5% FORMULA NUEVA | SUERO NIACINAMIDA 5% |
| SUERO DE VITAMINA C+ FORMULA NUEVA | SUERO VITAMINA C |
| SUERO TRIACTIVE RETINOID NAD | SUERO TRIACTIVE RETINOID + NAD |

⚠ **SUERO TRIACTIVE RETINOID NAD+** (49 ítems, códigos legacy) es OTRA fila del mismo SKU, **reformulada**
(le faltan 3 del Excel, tiene ~12 extra, 9 % distintos). Decisión tuya: ¿es versión nueva intencional o
duplicado a eliminar? El que coincide EXACTO con el Excel es "SUERO TRIACTIVE RETINOID NAD" (40 ítems).

## 🆕 9 productos "solo en app" que NO están en el Excel (decisión tuya)
CREMA DE UREA, EMULSION HIDRATANTE ANTIOXIDANTE, ESENCIA ILUMINADORA, SUERO ANTIOXIDANTE VITAMINA C+B3,
SUERO AZ + B3, Suero RETINAL +, SUERO DE RETINALDEHIDO 0.05%, MAXLASH, SUERO ILUMINADOR AHA+AH.
→ usan códigos legacy y tienen MPs que **mueren** (no cruzan). **Acción: agregarlos al Excel maestro o
confirmar descontinuados.** Antes de producirlos hay que crear/mapear sus MP (ver abajo).

## 🔴 MPs que MUEREN en consumo (no cruzan ni por maestro ni por bridge)
- **3 con fix claro (de los datos):**
  - `ALANTOINA` MPALANSO01 → **MP00047** — ✅ ya corregido (mig 228).
  - `HIDRÓXIDO DE SODIO` MPHIDROLI01/MPHIDSOLI01 → **MP00297** (el bridge apunta a MP00066, ausente).
  - `AGUA` MPAGUAL01 / MPAGUALI02 → **MPAGUALI01** (typos de código).
- **2 con INCI equivocado (corregir con Excel):** ÁCIDO FERÚLICO MPACFESO01→MP00160 (Etil ascórbico) ·
  BETAINA MPBETASO01→MP00214 (Betaglucano · debería ser MP00215).
- **~17 que NO existen en maestro NI Excel** (casi todos en los 9 productos nuevos): bisabolol, bicarbonato,
  chitosan, péptidos queratina, lexfeel, ácido madecásico, miristoil hexa/pentapéptido, N-acetil-cisteína,
  resveratrol, prolina, sílica MSS-500, trébol rojo, astaxantina, biotinoil tripéptido-1, acetil tetrapéptido-3.
  → **crear en maestro con el Excel** (no se adivinan · matching difuso = molécula equivocada).

## Plan de acción
| # | Acción | Quién | Riesgo |
|---|---|---|---|
| 1 | Agregar 3 ingredientes a BLUSH BALM + PIB-24 a LIP SÉRUM (del Excel) | Yo (con tu OK) | bajo · códigos existen |
| 2 | Corregir bridges HIDRÓXIDO SODIO→MP00297 y AGUA→MPAGUALI01 (mig) | Yo | bajo · determinista |
| 3 | Consolidar los 10 nombres duplicados al nombre del Excel | Yo (con tu OK) | medio · renombrado |
| 4 | Decidir SUERO TRIACTIVE NAD+ (nuevo vs duplicado) | Tú | — |
| 5 | Agregar los 9 productos nuevos al Excel o descontinuar + crear sus MP | Tú (Excel) | — |
| 6 | Corregir INCI Ác. Ferúlico / Betaína | Tú (Excel) | — |

**Conclusión:** tus 28 fórmulas maestras están bien (23 perfectas, 2 con ingredientes faltantes fáciles,
3 son el Triactive). El desorden histórico son duplicados de nombre + 9 productos propios que nunca entraron
al Excel. Nada catastrófico — y el consumo de las 23 es exacto.
