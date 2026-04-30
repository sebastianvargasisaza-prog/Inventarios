# Resumen de la noche · 30-abr-2026 (mientras dormías)

Trabajé en lo que pediste. **TODO desplegado en Render** (verifica en `/modulos`).

## ✅ Lo que se entregó

### 🌙 Lo de planta que estaba pendiente
- **Centro de Mando con tracking en vivo** — botones "Iniciar producción" / "Terminar" + timer real, KPIs (producciones AHORA, terminadas hoy, cycle time), auto-refresh 30s, eventos en tabla `area_eventos`.
- **Bodegas y Acondicionamiento ahora son asignables** (conteos cíclicos) — Acond, Almacén MP, Almacén PT.
- **CRUD operarios desde la UI** — botón "+ Nuevo operario" en Centro de Mando, sin tocar BD.

### 🔔 Sistema de notificaciones in-app (lo que pediste como base)
- **Tabla `notificaciones_app`** + helper `push_notif()` reutilizable.
- **Widget global 🔔** inyectado en TODAS las páginas (al lado del chat 💬), con badge rojo + dropdown + sonido.
- **Wireado a:**
  - Mensaje de chat → push a miembros del hilo (rojo si fue @mención)
  - Asignación de tarea operativa → push a cada asignado
  - Asignación de capacitación → push al operario
  - Resolución de notif bienestar (jefe aprueba/rechaza) → push al empleado
  - OC rechazada → push al solicitante (no rojo si fue "ya pagada")
  - Lead EOS desde webhook → push a Sebastian

### 💬 Chat flotante (resuelto)
- Antes: el FAB solo abría /chat en pestaña nueva (workaround tras iframe roto).
- Ahora: **panel real desplegable estilo Messenger** — lista de hilos con preview/badge, click abre conversación inline con burbujas, input + botón Enviar, sin recargar página. Auto-refresh 12s. "Abrir completo →" sigue disponible si lo prefieres.

### 📋 Módulo COMPLIANCE (NUEVO en `/compliance`)
3 tabs basados en correos reales que mandaste/recibiste:
- **📅 Cronogramas BPM** — los 5 que vi en Drive (Fumigación, Mantenimiento, Microbiológico, Capacitaciones, Ducha emergencia). Cards con barra de progreso (rojo<50%, amarillo<80%, verde≥80%). Click → modal con historial ejecuciones + "✓ Marcar cumplido" con URL de evidencia.
- **⚠ CAPA / Desviaciones** — código auto DESV-NNN, severidad, fecha objetivo +5d default, alerta roja si >5 días sin respuesta (justo lo que te pasó con DESV-007 Renova C10), botón cerrar pide causa raíz + acción correctiva + preventiva.
- **🔍 Hallazgos** — origen INVIMA/BPM/autoinspección/etc, badge crítico/mayor/menor, días-a-límite (vencido en rojo). **Seedeé con los 2 hallazgos abiertos reales** que vi en tu correo: identificación tuberías aguas (INVIMA, vence 1 may) + Definir área Rechazos (Laura, vence 15 may).
- **KPIs arriba**: cumplimiento BPM promedio, CAPA abiertas/>5d, hallazgos INVIMA pendientes.

### 💼 Módulo COMERCIAL (NUEVO en `/comercial`)
- **🏭 Pipeline Maquila B2B** — Kanban con 8 stages (consulta → NDA → brief → cotización → contrato → producción → ganado/perdido). **Seedeé con tus 3 deals reales**: JGB SA (NDA firmado 29 abr — el que pidió Full Service), ERLENMEYER (en contrato), Fernando Mesa (en producción). Click card → editar, total pipeline activo en header.
- **🚀 EOS Leads** — listado de form submissions con estados (nuevo/contactado/demo agendada/propuesta/cerrado). **Webhook público** `POST /api/eos/leads/webhook` listo para apuntar desde web3forms — cada lead nuevo dispara notif in-app a ti automática.

### 🚦 Semáforo de insumos en /planta
En el modal "Programar Producción" agregué la sección "🚦 Insumos requeridos":
- Lee fórmula del producto + lotes seleccionados → calcula requerido_g por MP.
- Cruza con stock actual de movimientos.
- Muestra ✅/⚠/❌ por MP, lista los problemáticos primero con "falta Xg".
- Header de color: verde (listo) / amarillo (justo) / rojo (déficit).
- Auto-refresca al cambiar lotes.

Resuelve el ciclo del correo "URGENTE confirmación insumos" — ahora lo ves antes de programar.

### 🏆 Empleado destacado trimestral
Tab nuevo en `/bienestar`: **"🏆 Empleado destacado"** con score objetivo:
- 25 pts × capacitación aprobada (max 50)
- nota_promedio × 0.4
- 5 pts × tarea completada (max 30)
- 4 pts × producción terminada (max 30)
- −10 pts × desviación abierta atribuida

Card grande gradient dorado con el #1 + tabla full ranking con medallas 🥇🥈🥉. Picker de Year/Q1-4. Excluye jefes (solo operarios).

### 🔧 Bug-fix email OC rechazada
Tu correo a Jefferson "Ya la pagamos" sobre OC-2026-0096. Ahora cuando rechazas con motivo que contenga "ya pag/pagada/duplicada":
- El sistema **busca el CE asociado** en `comprobantes_pago`.
- Si lo encuentra, el email incluye box verde: "✓ Esta OC ya estaba pagada: CE-XXXX del DD/MM por $N".
- Mensaje cambia de "puedes corregir y reenviar" → "no necesitas reenviar, el pago ya está registrado".
- Notif in-app no marca como urgente (es informativa, no acción).

---

## 📊 Stats finales

| Métrica | Antes | Ahora |
|---|---|---|
| Rutas | 539 | **565** |
| Tablas BD | ~95 | **~106** |
| Migraciones | 58 | **60** |
| Blueprints | 19 | **22** (notif + compliance + comercial) |
| Líneas commit netas | — | ~3,500 |

## 🧾 Commits que pushé esta noche

```
e134256 feat(compras+bienestar): OC rechazada con CE + empleado destacado trimestral
12b0803 feat(comercial): pipeline maquila B2B + webhook EOS leads
4bb5ebe feat(planta): A4 — semaforo de insumos en modal Programar Produccion
119f19e feat(compliance): modulo cronogramas BPM + CAPA + hallazgos INVIMA
8c7782b feat(chat): widget flotante REAL — panel desplegable estilo Messenger
7485e0d feat(notif): sistema unificado de notif in-app + wiring chat/tareas/capac
aaaed07 docs: lista priorizada de sugerencias basada en correo/drive (30-abr)
d749734 feat(planta): CRUD de operarios desde Centro de Mando
587fc50 feat(planta): Centro de Mando live + mig 58 + hardening migraciones
890683e fix(bienestar): renombrar capacitaciones → bienestar_capacitaciones
24dcbda feat(bienestar): modulo notificaciones empleados + capacitacion auto-examen Claude
```

## 🎯 Cómo lo pruebas al despertar

1. Hard refresh (Ctrl+Shift+R) en cualquier página.
2. **Mira la esquina inferior derecha**: ahora hay 2 FABs — 💬 chat + 🔔 notif.
3. Click 💬 → debería abrir el panel real con tus hilos (no más "abre nueva tab").
4. Click 🔔 → ves las notif (probablemente ya con la del lead EOS de prueba que metí).
5. Ve a `/modulos` → 2 tarjetas nuevas: **Compliance** y **Comercial**.
6. En `/planta` → tab "🎯 Centro de Mando" — abajo del plano hay tabla de operarios con botón "+ Nuevo".
7. Programa una producción cualquiera — ahora ves el semáforo de insumos.

## ⏭️ Lo que dejé pendiente para charlar contigo

Cosas de la lista [`docs/SUGERENCIAS_2026_04_30.md`](docs/SUGERENCIAS_2026_04_30.md) que NO toqué porque requieren decisiones tuyas:
- **B2 Cartera B2B con seguimiento** — necesito saber qué workflow exacto quieres (recordatorio cada N días? plantilla de cobro? emails autenticados?).
- **C1 Comunicados internos con acuse de lectura** — quiero confirmar contigo si lo quieres formal con firma digital o solo "leído".
- **C2 SGD versionado con Claude** — es un proyecto en sí mismo (webhook Drive + LLM diff), prefiero que lo hablemos antes de embarcarme.
- **D2 Inspecciones externas** — checklist preparatorio depende de qué entidades visitan (INVIMA, bomberos, etc.).
- **D3 Reuniones operativas** — solapa con `/comunicacion` que ya tienes; mejor ver primero qué falta ahí.

Buenos días cuando despiertes. Todo verde en local — Render debería estar OK también ya que la última corrida de smoke test paso 19/19 endpoints.
