# Lista de sugerencias — qué más sumar a EOS · 30-abr-2026

Lista basada en escaneo de tu Gmail (últimos 14 días) + Drive (SGD reciente).
Cada idea trae el **disparador** real (qué correo / archivo lo justifica) y el **alcance** estimado.

Marqué con ⭐ las 3 que creo que más palanca te dan vs esfuerzo, según lo que vi.

---

## 🔥 Bloque A — Cierre de brechas operativas reales que viste por correo

### A1 ⭐ Tablero "Cronogramas BPM" con % cumplimiento + alertas
- **Disparador:** Correos del 24 abr y 27 abr — fumigación ASG-PGM-001-C01 en **20% (2 de 10)**, ducha emergencia PRD-PRO-004-C01 en **3 de 12**. Tú mismo lo marcaste como "hallazgo directo en auditoría sanitaria".
- **Hoy:** todos esos cronogramas viven en Excel sueltos en Drive.
- **Qué construir:** 1 tabla `cronogramas_bpm` (codigo, nombre, frecuencia, responsable, % cumplimiento) + tabla `cronograma_ejecuciones` (fecha planeada / real / evidencia foto). Vista en /planta o tab nuevo "BPM".
- **Por qué importa:** te avisa antes de que un INVIMA te lo encuentre.
- **Esfuerzo:** ~3-4h.

### A2 ⭐ Módulo CAPA (Desviaciones / Acción correctiva-preventiva)
- **Disparador:** Hilo "Informe desviación Renova C10 — 5 días sin respuesta - CIERRE" del 29 abr. La DESV-007 se cerró por correo. Hay acta del 14 abr en Drive (`ACTA_REUNION_2026-04-14_Desviacion_Renova_C10.docx`).
- **Hoy:** desviaciones en Word + email; el "5 días sin respuesta" ya pasó por timer manual.
- **Qué construir:** Tabla `capa_desviaciones` (codigo DESV-NNN, lote, producto, descripcion, fecha_apertura, fecha_objetivo, fecha_cierre, responsable, acción, evidencia). Alertas automáticas si > 5 días sin respuesta. Estados: abierta / en_investigación / cerrada.
- **Esfuerzo:** ~3h.

### A3 Tablero de hallazgos abiertos (INVIMA + auditoría interna)
- **Disparador:** "Identificación de tuberías sistema de aguas — entrega vie 1 may" + "Solicitud de Definición Área de Rechazos" + acta auditoría documental (`GED-NOR-001-F04`).
- **Qué construir:** tabla `hallazgos` (origen INVIMA/BPM/auditoría, descripción, fecha límite, responsable, evidencia cierre). Vista de bandera roja en hub. Conecta con CAPA cuando aplica.
- **Esfuerzo:** ~2h.

### A4 Confirmación de insumos lista en /planta (no por correo)
- **Disparador:** Hilo del 28-29 abr "URGENTE — Confirmación insumos producción próximos 20 días" — Catalina respondió por correo con un texto enorme estado por SKU (GELH listo, etc).
- **Hoy:** ya tienes `solicitudes_compra` y producción programada — solo falta una vista cruzada.
- **Qué construir:** En el modal "Programar Producción" mostrar un semáforo por MP/MEE: ✅ stock OK / ⚠️ falta / ❌ déficit, leyendo de inventario actual + SOLs en curso. Catalina marca "✅ listo" desde su tab.
- **Esfuerzo:** ~2h. **Alto valor visible** porque tú mismo escribiste el correo "respuesta inmediata".

### A5 Stock vencido / próximo a vencer + sugerencia de uso
- **Disparador:** Hilo "SUERO DE BHA 10 M.L" — 302 unidades sin movimiento, vencimiento dic 2025 (¡ya vencido!). Daniela tuvo que escribirte 3 veces en abril.
- **Qué construir:** alerta automática en hub HHA "PT con vencimiento ≤ 90 días" + flag `riesgo_vencimiento`. Botón "Asignar a campaña influencer" (ya tienes módulo influencer) o "regalar evento".
- **Esfuerzo:** ~1.5h.

---

## 🟡 Bloque B — Multiplicar lo que ya tienes

### B1 ⭐ Pipeline B2B Maquila (cliente Full Service)
- **Disparador:** Correo del 29 abr — JGB SA (`ylondono@jgb.com.co`) pidió maquila Full Service. Acuerdo de confidencialidad firmado mismo día. Fernando Mesa es tu único cliente B2B activo hoy según memoria.
- **Qué construir:** Módulo "Maquila B2B" — tabla `maquila_pipeline` con stages (consulta → NDA → brief → cotización → contrato → producción). Cada deal vinculado a un cliente. Cuando se cierra → genera la OC interna automática.
- **Esfuerzo:** ~3h. **Bloquea que se te pierda otro JGB.**

### B2 Cartera B2B con seguimiento automático
- **Disparador:** Profamiliar Armenia $5.970.910 + Sebastián Yepes $6.106.411 + Laskin (Natalia gestiona) — 3 hilos abiertos al tiempo, todos con "actualización pendiente".
- **Hoy:** el módulo `clientes` lo tiene en BD pero sin workflow de seguimiento.
- **Qué construir:** vista cartera con score de urgencia (días sin pago × monto), recordatorios automáticos a Valentina/Daniela, log de gestiones realizadas, plantillas de email de cobro.
- **Esfuerzo:** ~3h.

### B3 Form demo EOS → CRM automático
- **Disparador:** Correo del 30 abr "EOS — nueva solicitud de demo" — formulario web web3forms te llegó al correo. Va a empezar a llover si la landing pega.
- **Qué construir:** webhook desde web3forms hacia tu API → crea lead en una tabla `eos_leads` → te llega notificación + tarea "agendar demo". Se conecta con Calendar.
- **Esfuerzo:** ~2h.

### B4 Comprobantes de pago automáticos (ya funciona, ampliar)
- **Disparador:** CE-2026-0008 generado y enviado automáticamente a Cardiomet — buen ejemplo. Pero la OC-2026-0096 fue rechazada con "Ya la pagamos" y Jefferson no entendió por qué.
- **Qué construir:** mejorar el email de rechazo de OC con contexto (ej. "fue pagada el DD/MM con CE-XXXX") y el comprobante adjunto. Cierra el ciclo.
- **Esfuerzo:** ~30 min.

---

## 🟢 Bloque C — Lo que pediste por chat hoy y que no terminé aún

### C1 Comunicados internos formales con acuse de lectura
- **Disparador:** Correo abogados sobre permisos / citas médicas. Gloria respondió "esto deberíamos integrarlo al procedimiento ADMINISTRACIÓN COTIDIANA RECURSO HUMANO".
- **Qué construir:** Módulo `comunicados` — admin crea comunicado (texto + adjunto), se envía a usuarios objetivo, cada usuario debe marcar "Leído y aceptado" al entrar al sistema. Audit trail con timestamp y firma digital.
- **Esfuerzo:** ~2.5h. Cierra brecha legal.

### C2 SGD versionado con Claude (lo que ya hablaste con Gloria)
- **Disparador:** Tu propio correo del 29 abr "Propongo que usemos la IA claude, para que nos versione todo". El SGD ANIMUS ya está estructurado en Drive (`SGD_ANIMUS_LAB` con 11 carpetas numeradas).
- **Qué construir:** integración Drive → tabla `sgd_documentos` con (codigo, version, fecha_revision, responsable, hash_contenido). Cuando se modifica un doc en Drive, se versiona en BD. Claude puede ver "qué cambió entre versiones" y proponer revisión.
- **Esfuerzo:** ~5h (es más complejo, necesita webhook de Drive).

### C3 Manual de funciones por cargo
- **Disparador:** Correo del 29 abr "Manual de funciones" — Gloria a Catalina: "tu cargo aparece como ASISTENTE COMERCIAL" y Catalina lleva tiempo firmando como "Asistente de Compras". Discrepancia documental.
- **Qué construir:** En módulo RRHH, tabla `cargos` con (nombre, descripción, funciones[], vinculado_a usuario). Vista "Mi manual" para cada empleado. Auto-versionado con fecha cambio.
- **Esfuerzo:** ~2h.

---

## 🔵 Bloque D — Calidad de vida del operador (ya casi todo listo, faltan detalles)

### D1 Empleado destacado trimestral (no mensual)
- **Disparador:** Tu correo del 29 abr "me gustaría que la estrategia vuelva mas como trimestral".
- **Qué construir:** En módulo Bienestar, vista "ranking trimestre" con métricas objetivas: % asistencia, capacitaciones aprobadas (ya tienes!), checklists completados, cero desviaciones atribuidas. Auto-cálculo cada trimestre.
- **Esfuerzo:** ~2h.

### D2 Visita autoridad / inspecciones externas
- **Disparador:** "Visita bomberos" pendiente cierre 30 abr en hilo de Luz Adriana. INVIMA visitas también.
- **Qué construir:** Módulo `inspecciones_externas` con checklist preparatorio (qué documentos tener listos, qué áreas revisar). Después de la visita, lista de hallazgos → conecta con A3.
- **Esfuerzo:** ~2h.

### D3 Reuniones operativas (dejaste un patrón claro)
- **Disparador:** Correo del 28 abr "Reporte reunión de operarios lunes" + reunión 4 may con Miguel + reunión semanal con Valentina. Tienes muchas reuniones recurrentes que terminan en correos largos.
- **Qué construir:** Módulo `reuniones` — agendar (con Calendar), agenda predefinida, durante reunión se registran compromisos (con responsable + fecha), al cerrar genera acta automática. Compromisos se sincronizan con módulo /comunicacion (tareas RACI).
- **Esfuerzo:** ~3h.

---

## 📋 Mi recomendación de prioridad para el sprint próximo

Si tuvieras 1 día de trabajo concentrado, yo iría así:

1. **A1 + A2 + A3 juntos** (cronogramas + CAPA + hallazgos) — son el mismo backbone "compliance loop", se hacen en paralelo. ~6-8h. Cierra el flanco INVIMA que parece ser tu mayor preocupación operativa real.

2. **B1 (pipeline maquila)** — JGB literalmente acaba de pedirlo, no querrás perderlo. ~3h.

3. **A4 (semáforo insumos en /planta)** — el correo "respuesta inmediata" muestra que duele cada semana. ~2h.

Total: **~12h de desarrollo** para cubrir lo que cuesta más en operación día a día.

---

## ⚠️ Cosas que NO recomiendo construir aún

- **CRM completo** estilo Salesforce — empieza simple con A4/B1/B2, ya vas viendo qué necesitas.
- **App móvil para operarios** — la PWA web actual ya funciona en celular. Mejor invertir en B1/A1.
- **Otro módulo de compras** — el actual ya tiene mucho.

---

## 🤖 Bug-fixes / pulidos pendientes que vi

- **Email de OC rechazada** debería incluir el motivo de manera más clara y, si fue "ya pagada", linkear el CE.
- **Manual de funciones Catalina** — corregir cargo "ASISTENTE COMERCIAL" → "ASISTENTE DE COMPRAS" en su perfil RRHH (no es bug del código, es dato).
- **Política de bonos** ya está en doc legal pero no formalizada en módulo RH (Daniela Sánchez la mandó 11 feb, tu propio recordatorio).

---

Cuando despiertes me dices cuáles atacamos. Yo me inclino fuerte por **A1+A2+A3 (compliance loop)** porque es lo que te metiste en problemas con INVIMA y es lo que terminas mandando correos urgentes los domingos.
