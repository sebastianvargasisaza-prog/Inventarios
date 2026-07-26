# Borrador para Hernando (WhatsApp) · normalización de códigos MyBatch

> Contexto: estamos alineando los códigos de materia prima entre MyBatch y EOS.
> En EOS los códigos ya están bien; estos 3 ajustes son para que MyBatch quede consistente.

---

**Hola Hernando, 3 ajustes en MyBatch para dejar los códigos parejos con EOS:**

**1) Centella asiática** — usar solo 2 códigos según el grado:
- `MP00176` = Centella triterpenes 80%
- `MP00185` = Asiaticoside 95%
- Reemplazar los códigos viejos: `MP00252`, `MP00181`, `MP00102` → **MP00176** · y `MP00141` → **MP00185**

**2) Carbopol** — son 2 grados, no 3:
- `MP00200` = Carbopol 940
- `MP00296` = el 2º grado
- Eliminar `MP00008` y usar `MP00296` en su lugar
- (Pregunta menor cuando puedas: ¿qué grado exacto es el MP00296? 980 NF / 934 / etc. · es solo para la etiqueta, no urge)

**3) Beauty Sensoft / Ethylhexylglycerin** — están cruzados en el batch:
- `MP00030` = Beauty Sensoft (Propyl Heptyl Caprylate)
- `MP00301` = Ethylhexylglycerin
- Hoy el batch los tiene al revés (usa MP00301 para el Beauty Sensoft y MP00302 para el Ethylhexyl) · corregir para que queden como arriba.

Gracias! Con eso quedan parejos.

---

## Notas internas (no van en el WhatsApp)
- Pigmentos: diferido (son blends · MP00305/MP00306 · se resuelve después).
- En EOS el remapeo lo hacemos nosotros; esto es solo para que MyBatch no siga generando códigos cruzados a futuro.
- Verificado contra datos reales de prod (maestro + fórmulas + batch) el 24-jul.
