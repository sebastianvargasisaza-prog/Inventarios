# Brief · módulo `eos-connect` (puente EOS ↔ GHL)

**Para:** la sesión de Claude Code que mantiene EOS (app.eossuite.com).
**De:** sesión que reposicionó la landing (eossuite.com) el 26-jul-2026.
**Objetivo comercial:** poder entregarle **EOS Suite** a un cliente que no sea nosotros.

---

## 1. Qué se vendió y por qué esto es el bloqueante

La landing ahora vende **EOS Suite** ($1.490.000 COP/mes): la unión de **EOS Comercial**
(CRM + IA sobre GoHighLevel) y **EOS Planta** (este ERP). El argumento de venta son
**8 flujos** que solo existen si las dos capas comparten datos. Están publicados en
https://eossuite.com/suite.html — el flujo 1 marcado como vivo, los otros 7 como
roadmap 2026. **No conviertas los 7 en promesa vencida.**

Hoy el puente existe pero es de una vía y de un solo cliente. Eso es lo que hay que cambiar.

---

## 2. Qué existe hoy (verificado en el repo, 26-jul-2026)

| Pieza | Dónde | Estado |
|---|---|---|
| Webhook entrante desde GHL | `api/blueprints/aseguramiento.py` · `/api/pqr/inbound` | Vivo en producción desde jun-2026 |
| Cliente GHL (solo lectura) | `aseguramiento.py` · `_ghl_token()`, `_ghl_fetch_contact()` | Lee `GET /contacts/{id}` |
| Lecturas de marketing | `api/blueprints/marketing.py` | contacts, pipelines, opportunities |
| Token | `animus_config.ghl_api_key`, fallback `GHL_API_KEY` | Único, global |
| Location | env `GHL_LOCATION_ID` | **Único. Aquí muere el multi-tenant.** |
| IDs de custom fields | constantes `_GHL_CF_*` en `aseguramiento.py` | **Hardcodeados a la subcuenta de ÁNIMUS** |
| Exención de sesión del webhook | `api/auth.py` (lista de rutas exentas) | Ya contemplado |
| Tests | `tests/test_pqr_omnicanal.py` | Token, idempotencia, triaje |

**Los tres huecos:** no hay escritura EOS→GHL · no hay multi-tenant · no hay catálogo
de flujos reusable (el PQR está cableado a mano).

---

## 3. Gotchas de GHL que ya nos costaron caro

Respétalos o vas a repetir los mismos días perdidos.

1. **GHL NO resuelve custom fields de contacto en el payload de un webhook.**
   `{{contact.mi_campo}}` llega vacío siempre; el picker solo expone campos estándar y
   custom values de ubicación. **Patrón obligatorio:** el webhook manda `contact_id`
   (campo estándar, ese sí resuelve) y EOS jala el resto por API. Ya está resuelto así.
2. **Cloudflare bloquea a urllib con Error 1010.** Hay que mandar User-Agent de navegador
   real. Ya está en `_GHL_HEADERS_BASE` — reúsalo, no armes headers nuevos.
3. **Header `Version: 2021-07-28` es obligatorio** en API v2.
4. **Workflows, plantillas de WhatsApp y prompts de Conversation AI NO se tocan por API.**
   Los tokens PIT devuelven 404 en `/conversation-ai/...`. La escalabilidad por cliente
   NO está en código: está en un **snapshot de GHL** que se clona por subcuenta.
   No diseñes nada que asuma que puedes crear workflows programáticamente.
5. **Los IDs de custom field son por location.** Los `_GHL_CF_*` actuales solo sirven para
   ÁNIMUS. En multi-tenant tienen que salir de una tabla de mapeo.
6. **Idempotencia:** el patrón actual es `contact_id + sha1(mensaje)[:12]`. Funciona, mantenlo.
7. Endpoint de agentes es `/conversation-ai/agents/{id}` en plural; el singular da 404.

---

## 4. Diseño propuesto

### 4.1 Extraer el cliente a `api/ghl_client.py`
Hoy la lógica de GHL vive dentro del blueprint de aseguramiento. Sácala a un módulo propio
**sin cambiar comportamiento** — los tests de `test_pqr_omnicanal.py` tienen que seguir
verdes sin tocarlos. Ese es el criterio de éxito de la fase 0.

Superficie mínima:

```python
class GHLClient:
    def __init__(self, cuenta): ...        # cuenta = fila de ghl_cuenta
    def get_contact(self, contact_id): ...
    def upsert_contact_fields(self, contact_id, campos: dict): ...   # PUT /contacts/{id}
    def add_tags(self, contact_id, tags: list): ...
    def remove_tags(self, contact_id, tags: list): ...
    def add_to_workflow(self, contact_id, workflow_id): ...          # dispara automatizaciones
```

`add_to_workflow` es la pieza clave: es como EOS enciende una automatización de GHL sin
poder crear workflows. **Confirma las rutas exactas contra la doc v2 antes de codificar** —
de `GET /contacts/{id}` estamos seguros porque ya corre; de las de escritura, no.

### 4.2 Multi-tenant: tres tablas
Sigue la convención de migraciones del repo (`api/database.py`), no inventes otra.

- **`ghl_cuenta`** — `id, empresa, location_id, token, activo, creado_en`.
  Reemplaza al par `GHL_LOCATION_ID` + `animus_config.ghl_api_key`. Migra ÁNIMUS como
  la primera fila para no romper nada.
- **`ghl_campo_map`** — `id, ghl_cuenta_id, clave_eos, ghl_custom_field_id`.
  Los `_GHL_CF_*` pasan a ser filas de esta tabla (`pqr_mensaje`, `pqr_canal`,
  `pqr_producto`, `pqr_lote`, `pqr_pedido` para ÁNIMUS). Deja los valores actuales como
  seed para que producción no se caiga.
- **`ghl_evento`** — outbox: `id, ghl_cuenta_id, flujo, entidad_tipo, entidad_id, payload,
  estado, intentos, ultimo_error, creado_en, enviado_en`.

### 4.3 Outbox, no llamadas en caliente
**Ninguna escritura a GHL debe salir dentro del request del usuario.** Se inserta una fila
en `ghl_evento` con estado `pendiente` y un worker (cron, como los que ya existen) la drena
con reintentos y backoff. Razones: GHL tiene rate limits, se cae, y una guía de despacho no
se puede perder porque su API tardó. Además el outbox te da auditoría gratis de todo lo que
EOS le dijo a GHL — que es exactamente lo que un cliente enterprise va a pedir.

### 4.4 Flujos declarativos
Cada uno de los 8 flujos debería ser una entrada de catálogo (evento disparador + qué campos
escribe + qué workflow dispara), no una función suelta. Si el flujo 2 termina siendo 200
líneas cableadas en el blueprint de despachos, fallamos otra vez.

---

## 5. Los 8 flujos (los que se vendieron)

| # | Flujo | Dirección | Estado |
|---|---|---|---|
| 1 | Queja WhatsApp → módulo de calidad con lote | GHL → EOS | **Vivo** |
| 2 | La IA responde con el despacho real (estado, transportadora, guía, lote) | EOS → GHL | Por hacer |
| 3 | Lote liberado en calidad → aviso de disponible | EOS → GHL | Por hacer |
| 4 | Cartera vencida → secuencia de cobro | EOS → GHL | Por hacer |
| 5 | Ciclo de recompra → mensaje de reposición | EOS → GHL | Por hacer |
| 6 | Oportunidad ganada → pedido con déficit de MP calculado | GHL → EOS | Por hacer |
| 7 | Lote próximo a vencer → campaña de rotación | EOS → GHL | Por hacer |
| 8 | Despacho entregado → solicitud de reseña | EOS → GHL | Por hacer |

**Empieza por el 2.** Es el de mayor retorno y menor riesgo: hoy la IA contesta "déjame
consultar" o peor, y ya hay historial de que responde con datos de otra clienta cuando el
email viene vacío. Escribir estado/guía/lote en los custom fields del contacto la arregla
sin que ella tenga que llamar a ninguna API.

---

## 6. Seguridad y no-negociables

- El token por cuenta **nunca** en código ni en logs. La escritura amplifica el daño de una
  fuga: un token robado ahora puede mandarle mensajes a los clientes del cliente.
- Todo lo que EOS escriba a GHL queda en `ghl_evento`. Sin excepciones silenciosas.
- El webhook entrante mantiene su secreto (`PQR_WEBHOOK_SECRET`) y su exención de sesión.
- Aísla por `ghl_cuenta_id` en cada consulta. Un cliente escribiéndole a los contactos de
  otro es el incidente que cierra la empresa.
- Tests: el repo tiene ~400 archivos de prueba. Nada de esto entra sin cobertura de
  idempotencia, reintentos, y aislamiento entre cuentas.

## 7. Lo que NO hay que hacer

- No crear workflows, plantillas ni prompts por API (imposible, ver §3.4).
- No hardcodear IDs de custom field nunca más.
- No llamar a GHL desde el hilo del request.
- No prender el flujo 3 (aviso de disponible) hasta que el inventario del cliente esté al
  día: avisar "ya hay stock" con datos sucios es peor que no avisar.

---

## 8. Fases

0. Extraer `ghl_client.py` sin cambio de comportamiento. Tests actuales verdes.
1. Multi-tenant: tablas + mapa de campos. ÁNIMUS migrado como cuenta 1. PQR sigue igual.
2. Escritura + outbox + worker con reintentos.
3. Flujo 2 end-to-end (el que arregla a la IA respondiendo pedidos).
4. Flujos 3 a 8.
5. Snapshot de GHL clonable + checklist de onboarding de cliente nuevo.

Al terminar cada fase, avísale a Sebastián qué flujo quedó vivo para que lo mueva de
"2026" a "En producción" en https://eossuite.com/suite.html.
