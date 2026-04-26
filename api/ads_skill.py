"""
ads_skill.py — Motor de Agencia de Ads multi-plataforma.

Carga las skills de claude-ads (api/skills/ads/) en memoria al startup y expone
una sola funcion publica: run_ads_skill(platform, action, payload, api_key).

Combina:
  - SKILL.md principal (orquestador)
  - platforms/<platform>.md (Google, Meta, LinkedIn, TikTok, YouTube, Apple, Microsoft)
  - actions/<action>.md (audit, plan, creative, budget, competitor, landing, test, dna)
  - references/*.md relevantes (benchmarks, copy-frameworks, platform-specs)

Llama a Claude con prompt caching para reutilizar el contexto de skills (~30k tokens)
entre llamadas dentro de la ventana de 5 minutos. Costo estimado: $0.05-0.10 por
audit completo con cache hit.
"""
import json
import os
import urllib.request
import urllib.error
from functools import lru_cache

# ── Paths ─────────────────────────────────────────────────────────────────────
_API_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(_API_DIR, "skills", "ads")

# ── Catalogos validos ─────────────────────────────────────────────────────────
PLATFORMS = {"google", "meta", "linkedin", "tiktok", "youtube", "apple", "microsoft"}
ACTIONS_PLATFORM = {"audit", "plan", "creative", "budget"}
ACTIONS_GLOBAL = {"competitor", "landing", "test", "dna"}

# References que se incluyen siempre (conocimiento transversal)
ALWAYS_INCLUDE_REFS = ["benchmarks.md", "platform-specs.md", "copy-frameworks.md"]

# References especificos por accion (knowledge focalizado)
ACTION_REFS = {
    "audit": ["{platform}-audit.md", "conversion-tracking.md", "compliance.md"],
    "plan": ["budget-allocation.md", "bidding-strategies.md"],
    "creative": ["{platform}-creative-specs.md", "copy-frameworks.md"],
    "budget": ["budget-allocation.md", "bidding-strategies.md", "benchmarks.md"],
    "dna": ["brand-dna-template.md"],
    "test": [],
    "competitor": [],
    "landing": [],
}

# Modelo por defecto: Sonnet 4.6 para analisis serio. Para acciones simples
# (test, dna) puede bajarse a Haiku para abaratar.
MODEL_DEFAULT = "claude-sonnet-4-5"
MODEL_BY_ACTION = {
    "test": "claude-haiku-4-5-20251001",
    "dna": "claude-haiku-4-5-20251001",
}


# ── Carga de archivos en memoria ──────────────────────────────────────────────
def _read(path):
    """Lee un archivo de texto. Devuelve string vacio si no existe."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (FileNotFoundError, OSError):
        return ""


@lru_cache(maxsize=1)
def _orchestrator():
    """SKILL.md principal — solo se lee una vez."""
    return _read(os.path.join(SKILLS_DIR, "SKILL.md"))


@lru_cache(maxsize=32)
def _platform_skill(platform):
    if platform not in PLATFORMS:
        return ""
    return _read(os.path.join(SKILLS_DIR, "platforms", f"{platform}.md"))


@lru_cache(maxsize=32)
def _action_skill(action):
    if action not in (ACTIONS_PLATFORM | ACTIONS_GLOBAL):
        return ""
    return _read(os.path.join(SKILLS_DIR, "actions", f"{action}.md"))


@lru_cache(maxsize=64)
def _reference(name):
    return _read(os.path.join(SKILLS_DIR, "references", name))


# ── Construccion del system prompt ────────────────────────────────────────────
def _build_system_prompt(platform, action):
    """Combina orquestador + platform + action + references relevantes.

    El bloque resultante es estable para una (platform, action) — esto permite
    cachearlo en la API de Anthropic via cache_control.
    """
    parts = [_orchestrator()]

    if platform and platform in PLATFORMS:
        parts.append(f"\n\n# === Platform Context: {platform.upper()} ===\n")
        parts.append(_platform_skill(platform))

    if action:
        parts.append(f"\n\n# === Action: {action.upper()} ===\n")
        parts.append(_action_skill(action))

    refs_to_load = list(ALWAYS_INCLUDE_REFS)
    for ref_template in ACTION_REFS.get(action, []):
        ref_name = ref_template.format(platform=platform or "google")
        if ref_name not in refs_to_load:
            refs_to_load.append(ref_name)

    parts.append("\n\n# === Reference Material ===\n")
    for ref in refs_to_load:
        content = _reference(ref)
        if content:
            parts.append(f"\n## {ref}\n\n{content}\n")

    parts.append(
        "\n\n# === Output Instructions ===\n\n"
        "Responde en ESPAÑOL. Devuelve un reporte en markdown bien estructurado con:\n\n"
        "1. **Resumen ejecutivo** (3-5 lineas, lo mas importante)\n"
        "2. **Score de salud** (0-100) con desglose por categoria si aplica\n"
        "3. **Hallazgos criticos** (top 3-5 con severidad: critical / high / medium / low)\n"
        "4. **Quick wins** (acciones de alto impacto, bajo esfuerzo, primeras 2 semanas)\n"
        "5. **Plan de 30/60/90 dias** con metricas objetivo\n\n"
        "Si no tienes datos suficientes para alguna seccion, dilo explicitamente "
        "y pide el dato faltante en un bloque 'DATOS REQUERIDOS' al inicio.\n\n"
        "Tono: directo, accionable, sin relleno corporativo. Como un consultor "
        "senior de agencia que cobra $300/hora. Usa numeros concretos, fechas, "
        "porcentajes. Evita frases vacias tipo 'aprovechar sinergias'."
    )

    return "".join(parts)


# ── Llamada a la API de Anthropic con prompt caching ──────────────────────────
def _call_anthropic(api_key, model, system_prompt, user_message, max_tokens=2500):
    """Llama a /v1/messages con cache_control en el system prompt.

    Retorna dict con: text, model, input_tokens, output_tokens, cache_read_tokens,
    cache_create_tokens, cost_usd_estimate.
    """
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "system": [
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [{"role": "user", "content": user_message}],
    }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    usage = data.get("usage", {})
    in_tok = usage.get("input_tokens", 0)
    out_tok = usage.get("output_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)

    # Pricing aproximado de claude-sonnet-4-5 / haiku-4-5 (USD per 1M tokens)
    if "haiku" in model:
        in_price, out_price, cache_w_price, cache_r_price = 1.0, 5.0, 1.25, 0.10
    else:
        in_price, out_price, cache_w_price, cache_r_price = 3.0, 15.0, 3.75, 0.30

    cost = (
        in_tok * in_price
        + out_tok * out_price
        + cache_write * cache_w_price
        + cache_read * cache_r_price
    ) / 1_000_000

    return {
        "text": text,
        "model": model,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "cache_read_tokens": cache_read,
        "cache_create_tokens": cache_write,
        "cost_usd_estimate": round(cost, 4),
    }


# ── API publica ───────────────────────────────────────────────────────────────
def run_ads_skill(platform, action, payload, api_key, model=None, business_context=None):
    """Ejecuta una skill de ads.

    Args:
        platform: "google" | "meta" | "linkedin" | "tiktok" | "youtube" | "apple" |
                  "microsoft" | None (para acciones globales como competitor, dna).
        action:   "audit" | "plan" | "creative" | "budget" |
                  "competitor" | "landing" | "test" | "dna".
        payload:  Datos del cliente (CSV pegado, descripcion en texto, metricas, URL).
        api_key:  Clave de Anthropic.
        model:    Override opcional del modelo. Default: Sonnet 4.6 (Haiku para test/dna).
        business_context: Dict opcional con industry, monthly_spend, goal, active_platforms.

    Returns:
        Dict con text, model, tokens, cost, error (si aplica).
    """
    if not api_key:
        return {"error": "anthropic_api_key no configurada en animus_config"}

    if platform and platform not in PLATFORMS:
        return {"error": f"plataforma desconocida: {platform}"}

    valid_actions = ACTIONS_PLATFORM | ACTIONS_GLOBAL
    if action not in valid_actions:
        return {"error": f"accion desconocida: {action}. Validas: {sorted(valid_actions)}"}

    if action in ACTIONS_GLOBAL:
        platform = None

    system_prompt = _build_system_prompt(platform, action)
    if not system_prompt.strip() or len(system_prompt) < 500:
        return {
            "error": "skills no encontradas en api/skills/ads/. "
            "Verifica que el directorio existe en el deploy."
        }

    ctx_lines = []
    if business_context:
        ctx_lines.append("## Contexto del negocio\n")
        for k in ("industry", "monthly_spend_usd", "goal", "active_platforms", "client_name"):
            v = business_context.get(k)
            if v:
                ctx_lines.append(f"- **{k}**: {v}")
        ctx_lines.append("")

    user_msg = "\n".join(ctx_lines) if ctx_lines else ""
    user_msg += f"\n## Datos / Solicitud\n\n{payload}\n\n"
    user_msg += (
        f"## Tarea\n\nEjecuta `{action}`"
        f"{' para ' + platform.upper() if platform else ''}. "
        "Sigue el formato de output indicado en las instrucciones del sistema."
    )

    chosen_model = model or MODEL_BY_ACTION.get(action, MODEL_DEFAULT)

    try:
        result = _call_anthropic(api_key, chosen_model, system_prompt, user_msg)
        result["platform"] = platform
        result["action"] = action
        return result
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = ""
        return {
            "error": f"Anthropic API HTTP {e.code}",
            "detail": err_body[:500],
        }
    except Exception as e:
        return {"error": f"Error llamando a Claude: {type(e).__name__}: {e}"}


def list_capabilities():
    """Lista las capacidades disponibles (para el frontend)."""
    return {
        "platforms": sorted(PLATFORMS),
        "actions_per_platform": sorted(ACTIONS_PLATFORM),
        "actions_global": sorted(ACTIONS_GLOBAL),
        "default_model": MODEL_DEFAULT,
    }
