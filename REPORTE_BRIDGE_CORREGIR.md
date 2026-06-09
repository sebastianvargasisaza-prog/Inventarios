# 🔧 Bridge MP · mapeos a corregir con el Excel maestro

Audit corazón 9-jun-2026. El sistema resuelve fórmula→bodega vía `mp_formula_bridge`.
Estos mapeos están MAL (la demanda muere o va a la MP equivocada). **NO se autocorrigen**
(adivinar corrompe el kardex). Corregí cada uno en `/admin/formulas-mismapeo` validando
contra el Excel maestro. El guardián los lista en vivo: `GET /api/admin/integridad-bridge`.

## 🔴 PRIORIDAD 1 · INCI equivocado (la demanda va a OTRA MP · descuenta mal el kardex)

| Código fórmula | Es (fórmula) | Apunta MAL a | Acción |
|---|---|---|---|
| `MPACFESO01` | ÁCIDO FERÚLICO (Ferulic Acid) | MP00160 = Etil ascórbico | Crear Ác. Ferúlico (INCI FERULIC ACID) en maestro y re-apuntar · desactivar bridge a MP00160 |
| `MPBETASO01` | BETAINA (Betaine) | MP00214 = Betaglucano | Re-apuntar a **MP00215** (Betaína/BETAINE · ya existe) |

## 🔴 PRIORIDAD 2 · Bridges rotos (destino no existe en maestro · la demanda MUERE)

| Código fórmula | Es (fórmula) | Apunta a (inexistente) | Candidato a CONFIRMAR / acción |
|---|---|---|---|
| `MPACGLSO01` |  | MP00290 | **crear en maestro** (no está) o mapear con Excel |
| `MPACTET3001` | ACETIL TETRAPEPTIDO-3 | MP00170 | **crear en maestro** (no está) o mapear con Excel |
| `MPASTAXLI01` | ASTAXANTINA | MP00218 | **crear en maestro** (no está) o mapear con Excel |
| `MPBIOTSO01` | BIOTINOIL TRIPEPTIDO-1 | MP00193 | **crear en maestro** (no está) o mapear con Excel |
| `MPBISALI01` | BISABOLOL | MPBSBL01 | **crear en maestro** (no está) o mapear con Excel |
| `MPBISOSO01` | BICARBONATO DE SODIO | MP00131 | **crear en maestro** (no está) o mapear con Excel |
| `MPCHITSO01` | CHITOSAN | MP00220 | **crear en maestro** (no está) o mapear con Excel |
| `MPFRSALI01` |  | MP00019 | **crear en maestro** (no está) o mapear con Excel |
| `MPGIWHSO01` |  | MP00271 | **crear en maestro** (no está) o mapear con Excel |
| `MPHIDROLI01` | HIDROXIDO SODIO | MP00066 | ¿`MP00297` (Hidróxido sodio sol. 50%)? confirmar |
| `MPHIDSOLI01` |  | MP00066 | **crear en maestro** (no está) o mapear con Excel |
| `MPKERPEPSO01` | PEPTIDOS HIDROLIZADOS QUERATIN | MP00168 | **crear en maestro** (no está) o mapear con Excel |
| `MPLAGLLI01` |  | MP00070 | **crear en maestro** (no está) o mapear con Excel |
| `MPLEXFESO01` | LEXFEEL WOW | MP00109 | **crear en maestro** (no está) o mapear con Excel |
| `MPMADESAC01` | ACIDO MADECASICO | MP00227 | **crear en maestro** (no está) o mapear con Excel |
| `MPMYRIH16` | MIRISTOIL HEXAPEPTIDO-16 | MP00171 | **crear en maestro** (no está) o mapear con Excel |
| `MPMYRIP17` | MIRISTOIL PENTAPEPTIDO-17 | MP00187 | **crear en maestro** (no está) o mapear con Excel |
| `MPNACISO01` | N-ACETIL-CISTEINA | MP00164 | **crear en maestro** (no está) o mapear con Excel |
| `MPROLISO01` | PROLINA | MP00151 | **crear en maestro** (no está) o mapear con Excel |
| `MPSILICSO01` | SILICA MSS-500 | MP00289 | ¿`MP00112` (Aerosil 200)? confirmar |
| `MPSILILI02` |  | MP00128 | **crear en maestro** (no está) o mapear con Excel |
| `MPTREBOLSO01` | EXTRACTO TREBOL ROJO | MP00241 | **crear en maestro** (no está) o mapear con Excel |
| `MPUPASO001` |  | MP00146 | **crear en maestro** (no está) o mapear con Excel |

## 🔴 PRIORIDAD 3 · Huérfano (ni maestro ni bridge)

| Código fórmula | Es | Acción |
|---|---|---|
| `MPRESVSO01` | RESVERATROL (2 productos) | Crear en maestro (INCI RESVERATROL) + bridge |

## ✅ Ya corregido por código (mig 228)

- `MPALANSO01` (ALANTOINA): MP00085 inexistente → **MP00047** (match exacto).

> Tip: lo más rápido es **subir el Excel maestro completo** (cruce-maestro) para que se
> creen las MPs que faltan, y luego re-cruzar los bridges. Muchos de arriba "no están en
> el maestro" simplemente porque el maestro está incompleto.
