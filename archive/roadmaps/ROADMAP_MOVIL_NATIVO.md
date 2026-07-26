# 📱 Cortex Labs — Roadmap a App Móvil Nativa

**Para:** Sebastián
**Fecha:** Abril 2026
**Pregunta:** ¿Cómo pasamos de "web responsive" a "app real instalable
en App Store y Play Store con UX móvil de primera"?

---

## TL;DR

Hay **3 caminos**. Te recomiendo el #1 (PWA mejorada) AHORA y el #2 (TWA +
Capacitor) en Q4 2026.

| Camino | Tiempo | Costo | UX | Stores | Recomendación |
|---|---|---|---|---|---|
| **1. PWA mejorada** (lo que tenemos) | **Hoy** | $0 | 7/10 | ❌ | ✅ AHORA |
| **2. PWA + TWA Android + Capacitor iOS** | 2-4 semanas | $1.2K USD | 9/10 | ✅✅ | ✅ Q4 2026 |
| **3. Reescribir en React Native** | 6-9 meses | $30-60K USD | 10/10 | ✅✅ | ❌ NO. Sobre-ingeniería. |

---

## 1. Estado actual (lo que ya tenemos)

✅ `manifest.json` con iconos 192/512/maskable
✅ Service Worker (`sw.js`) con cache offline
✅ Meta tags `apple-mobile-web-app-*`
✅ Theme color y status-bar style
✅ Shortcuts en pantalla de inicio (HOY, Compras, Tesorería, Programación)
✅ Display `standalone` (sin barra de Chrome cuando se instala)
✅ Diseño responsive en módulos clave

### Lo que ya pasa hoy:
- Sebastián abre Chrome en el celular → va a `https://inventarios.onrender.com`
- Aparece banner "Agregar a pantalla de inicio"
- Toca "Agregar"
- Se crea ícono **Cortex Labs** en su home screen
- Lo abre y se ve **igual que app nativa**, sin barra de URL
- Funciona offline para las pantallas que ya visitó

### Lo que falta para que sea "real":

| Falta | Severidad | Solución |
|---|---|---|
| No está en App Store ni Play Store | Media | TWA (Android) + Capacitor (iOS) |
| Ícono no es de calidad pro | Baja | Diseñar logo Cortex Labs SVG → 1024x1024 |
| Push notifications nativas | Media | Web Push API + servidor |
| Cámara para OCR facturas en celular | **Alta** | `<input capture>` ya funciona, mejorar UX |
| Modo offline real (no solo cache) | Media | IndexedDB + sync engine |
| UX táctil refinada (gestos, swipes) | Media | iteración por módulo |
| Splash screen | Baja | Generar 8 tamaños iOS + Android |
| Pantallas que **NO** son responsive | Alta | auditar 19 módulos |

---

## 2. Fase 1 — PWA mejorada (HOY, esta semana)

**Objetivo:** que la PWA actual se sienta de verdad como una app, sin todavía
ir a las stores.

### 2.1 Logo Cortex Labs profesional
- Diseñar logo SVG vectorial: símbolo de cerebro + tipografía "Cortex Labs"
- Generar 8 tamaños: 16, 32, 48, 96, 144, 192, 256, 512, 1024
- Variante maskable (zona segura círculo 80%)
- Splash screens iOS (8 sizes) + Android (4 sizes)
- **Costo:** $200-400 USD a un diseñador, o lo hago con IA (Midjourney/Figma)
- **Tiempo:** 2-3 días

### 2.2 Splash screens
- iOS necesita 8 splash screens distintos (iPhone SE, X, 12, 14 Pro Max...)
- Servir desde `<link rel="apple-touch-startup-image">` en cada template
- Tool: <https://www.pwabuilder.com/imageGenerator>

### 2.3 Audit de responsividad
- Probar cada módulo en iPhone 12 (390x844) y Galaxy S22 (360x780)
- Lista de 19 módulos:
  - ✅ HOY, Compras, Solicitudes, Programación (ya móvil)
  - ⚠️ Planta (tablas anchas, requiere scroll horizontal)
  - ⚠️ Calidad, Técnica, Recepción, Empaque
  - ❌ Gerencia financiera (tablas P&L muy anchas)
  - ❌ Centro de notificaciones (modal grande)
- Tarea: por cada módulo no-responsive, refactorizar tablas a "card-list" en mobile

### 2.4 Push notifications
- Web Push API funciona en Android Chrome desde hace años
- iOS Safari las soporta **desde iOS 16.4** (PWA agregada a home screen)
- Implementación:
  - `service worker` registra push subscription
  - Backend Flask guarda subscription en tabla `push_subscriptions(user, endpoint, keys)`
  - Cuando hay alerta crítica → backend dispara `pywebpush.send()` con payload
  - SW recibe → muestra notificación nativa con `self.registration.showNotification()`
- **Esfuerzo:** 1 semana
- **Costo recurrente:** $0

### 2.5 Mejoras UX táctil
- Botones mínimo 44x44 px (iOS HIG) — auditar
- Modal cerrable con swipe-down (gesto natural mobile)
- Pull-to-refresh en listas grandes
- Bottom navigation bar para los módulos top-5 (no top nav)
- Inputs con `inputmode="numeric"` / `inputmode="email"` etc.

### 2.6 Cámara nativa para OCR
- Catalina ya escanea facturas en compras
- En mobile: agregar botón "📷 Tomar foto factura"
- HTML: `<input type="file" accept="image/*" capture="environment">`
- Esto **abre la cámara directa** del celular sin pasar por app foto
- Backend: el endpoint OCR ya existe, solo conectar
- **Esfuerzo:** 2-3 días

**Total Fase 1:** ~3 semanas + $400 USD (diseño)

---

## 3. Fase 2 — TWA Android + Capacitor iOS (Q4 2026)

Para tener la app **realmente en App Store y Play Store**.

### 3.1 ¿Qué es TWA (Trusted Web Activity)?
- Tecnología oficial Google para "envolver" una PWA en APK
- La app es **literalmente Chrome embebido** mostrando tu PWA, pero
  parece app nativa al usuario
- Tamaño APK: ~3 MB (vs 30-100 MB de app nativa)
- **Pasa la review de Play Store** sin problemas (Google lo promueve)
- Acceso a Web Push, geolocation, cámara, todo lo de PWA
- Tool: **Bubblewrap** de Google (CLI gratis)

### 3.2 ¿Qué es Capacitor?
- Sucesor de Cordova/PhoneGap, mantenido por Ionic
- Hace lo mismo que TWA pero también funciona en iOS
- Genera proyecto Xcode + Android Studio que envuelven tu webapp
- Permite añadir plugins nativos (Bluetooth, NFC, biometría) si los necesitas
- **Pasa la review de App Store** (con review humano más estricto)

### 3.3 Estrategia recomendada

**Android:** TWA via Bubblewrap (más liviano, oficial Google)
**iOS:** Capacitor (porque TWA no existe en iOS)

### 3.4 Pasos prácticos

#### Android (Play Store)
1. Comprar dominio "cortexlabs.co" (o usar `app.cortexlabs.co`)
2. Apuntar dominio a Render (DNS CNAME)
3. Configurar HTTPS válido (Render lo da automático)
4. Validar PWA: <https://www.pwabuilder.com/> debe dar score 100
5. Generar APK con Bubblewrap:
   ```bash
   npx @bubblewrap/cli init --manifest=https://app.cortexlabs.co/manifest.json
   npx @bubblewrap/cli build
   ```
6. Crear cuenta Google Play Console: **$25 USD una vez**
7. Subir APK + screenshots + descripciones + privacy policy
8. Review: 2-7 días
9. Listo en Play Store

**Tiempo total:** 1 semana
**Costo:** $25 USD (Google) + dominio (~$15/año) + diseño screenshots

#### iOS (App Store)
1. Cuenta Apple Developer: **$99 USD/año**
2. Mac con Xcode (o renta Mac mini en cloud por ~$30/mes)
3. Capacitor:
   ```bash
   npm install @capacitor/core @capacitor/ios
   npx cap init "Cortex Labs" co.hhagroup.cortexlabs
   npx cap add ios
   npx cap open ios
   ```
4. En Xcode: configurar bundle id, certificados, sign in
5. Subir a App Store Connect
6. **Review humano: 1-3 semanas** (más estricto que Google)
7. Posibles rechazos típicos para PWAs envueltas:
   - "Tu app es solo un wrapper de un sitio web" → mitigar con plugins nativos
     (cámara nativa, push notif, biometría, splash) que hagan diferencia.
   - Solución: agregar plugin `@capacitor/camera`, `@capacitor/push-notifications`,
     `@capacitor/biometric-auth` aunque sea solo para esos features.

**Tiempo total:** 2-3 semanas
**Costo:** $99 USD/año (Apple) + $30/mes Mac cloud opcional + tiempo dev

#### Total Fase 2
- **Tiempo:** 3-4 semanas
- **Costo inicial:** $1.2K USD (Apple + Google + diseño)
- **Costo recurrente:** ~$15 USD/mes (Apple Developer + dominio)

---

## 4. Fase 3 — Reescribir en React Native (NO HACER)

**Por qué la gente cree que necesita esto:**
"Las apps web no son tan buenas como las nativas"

**Por qué NO necesitamos esto:**
1. Cortex Labs es una app de **gestión empresarial**, no un juego ni una
   experiencia gráfica intensa
2. PWA + TWA cubre **el 95%** del UX que necesitamos
3. Reescribir 27.940 líneas implica **6-9 meses dev fulltime** y duplicar mantenimiento
4. Empresas grandes (Netflix, Twitter Lite, Uber Lite, Pinterest) usan PWA
5. Los clientes empresariales **no se descargan tu app desde la store** —
   acceden por web link compartido en Slack/email/WhatsApp

**Cuando SÍ tendría sentido React Native:**
- Si Cortex Labs se transforma en producto **consumer** (poco probable)
- Si necesitamos features muy nativos (Bluetooth de balanzas, ARKit, etc.)
- Si Apple empieza a discriminar PWAs envueltas en App Store severamente

**Conclusión:** quedamos en Fase 2. No hacer Fase 3.

---

## 5. Lo que necesitas saber sobre publicar en stores

### Privacy Policy + Terms
- Apple **exige** ambos URLs en App Store Connect
- Google también
- Plantillas: <https://www.iubenda.com> (~$30 USD/año)
- O escribimos custom con abogado COL ($1-2M COP) — mejor para Habeas Data

### Política Habeas Data Colombia
- Ley 1581 de 2012 obliga a tener política y registrarla en SIC
- Mientras estemos solo en HHA Group no es crítico
- Antes de primer cliente externo → hacerlo

### Screenshots para stores
- Apple: 4 screenshots mínimo (iPhone 6.5", 5.5"), opcional iPad
- Google: mínimo 2, máximo 8 screenshots
- Tienen que mostrar el producto FUNCIONANDO, no mockups
- Recomendación: invertir 1 día capturando screens bonitos en
  iPhone 14 Pro y Galaxy S23

### Descripción de la app
- Apple permite hasta 4000 caracteres
- Google 4000 también
- Keywords ASO: "ERP cosmético", "BPM laboratorio", "cosméticos Colombia"

---

## 6. Cronograma sugerido

### Mayo 2026 — Fase 1 PWA mejorada
- Semana 1-2: logo profesional + splash screens + auditar responsivos
- Semana 3: arreglar 5 módulos no-móviles (Gerencia, Calidad, etc.)
- Semana 4: push notifications + cámara OCR mejorada
- **Hito:** Sebastián y Catalina usan Cortex desde celular, sin frustraciones

### Octubre-Noviembre 2026 — Fase 2 stores
- Semana 1: dominio cortexlabs.co + DNS + HTTPS validar
- Semana 2: TWA Android → Bubblewrap → submit Play Store
- Semana 3-4: Capacitor iOS → Xcode → submit App Store
- **Hito:** "Cortex Labs by HHA Group" disponible en App Store y Play Store

### Diciembre 2026 — Marketing
- Anuncio LinkedIn + WhatsApp Business
- Brochure PDF actualizado con QR a stores
- Pitch a 5 labs cosméticos con "estamos en stores"

---

## 7. Decisiones que necesitamos de Sebastián

1. **¿Diseño logo Cortex Labs en mayo?** ($300-500 USD)
   - Opción a) Diseñador freelance Behance/Dribbble
   - Opción b) Lo hago con IA (Midjourney) y refinas tú
2. **¿Compramos dominio cortexlabs.co?** (~$15 USD/año)
3. **¿Cuenta Apple Developer + Google Play en Q4 2026?** ($25 + $99/año)
4. **¿Quién hace los screenshots y descripciones?**
5. **¿Empezamos Fase 1 esta semana o esperamos?**

---

## 8. Lo más importante

La pregunta no es "¿app nativa o web?". La pregunta es: **¿qué UX necesita
la persona que va a usarla?**

Para Cortex Labs:
- **Sebastián (CEO):** quiere ver KPIs en celular en consultorio, aprobar OCs
  caminando. **PWA actual ya cubre esto al 80%.**
- **Catalina (compras):** quiere escanear facturas con cámara y registrar
  pagos. **Necesita cámara nativa (Fase 1).**
- **Cliente futuro (otro lab CEO):** quiere "ver cómo va la planta hoy"
  en su iPhone. **Necesita app en App Store (Fase 2).**

No reescribimos en React Native. **No tiene sentido para nuestro perfil.**

---

**Siguiente paso:** decir SÍ a Fase 1 esta semana y empezar por el logo.
