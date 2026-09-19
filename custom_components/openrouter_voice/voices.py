"""Live-Abfrage der unterstützten Stimmen bei OpenRouter.

Die Stimmen-Listen ändern sich, wenn Provider neue Stimmen ergänzen (oder
umbenennen). Deshalb werden sie zur Laufzeit über die Models-API geholt und
eine Stunde lang gecacht. Schlägt der Abruf fehl, greifen die Fallback-Listen
aus ``const.TTS_MODELS``.
"""

from __future__ import annotations

import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

from .const import DEFAULT_TIMEOUT, get_voices_for_model

_LOGGER = logging.getLogger(__name__)

MODELS_API_URL = "https://openrouter.ai/api/v1/models?output_modalities=speech"
CACHE_TTL = 3600  # Sekunden

# model_id -> (timestamp, voices)
_cache: dict[str, tuple[float, list[str]]] = {}


async def async_get_supported_voices(
    hass: HomeAssistant, model_id: str
) -> list[str]:
    """Stimmen für ein TTS-Modell — live von OpenRouter, sonst Fallback."""
    now = time.monotonic()
    cached = _cache.get(model_id)
    if cached is not None and now - cached[0] < CACHE_TTL:
        return cached[1]

    voices = await _async_fetch_voices(hass, model_id)
    if voices:
        _cache[model_id] = (now, voices)
        _LOGGER.debug(
            "OpenRouter: %d Stimmen für %s geladen", len(voices), model_id
        )
        return voices

    _LOGGER.warning(
        "OpenRouter-Stimmen für %s nicht abrufbar — nutze Fallback-Liste", model_id
    )
    return get_voices_for_model(model_id)


async def _async_fetch_voices(
    hass: HomeAssistant, model_id: str
) -> list[str] | None:
    """Holt die Stimmen-Liste aus der OpenRouter-Models-API."""
    try:
        client = get_async_client(hass)
        response = await client.get(MODELS_API_URL, timeout=DEFAULT_TIMEOUT)
        if response.status_code != 200:
            _LOGGER.warning(
                "OpenRouter-Models-API: HTTP %s", response.status_code
            )
            return None
        payload = response.json()
    except Exception as err:  # noqa: BLE001 — Netzfehler dürfen nie den Flow killen
        _LOGGER.warning("OpenRouter-Models-API nicht erreichbar: %s", err)
        return None

    for model in payload.get("data", []):
        if model.get("id") == model_id:
            voices = model.get("supported_voices")
            if voices:
                return [str(v) for v in voices]
            _LOGGER.warning(
                "Modell %s liefert keine supported_voices", model_id
            )
            return None

    _LOGGER.warning("Modell %s nicht in der TTS-Liste von OpenRouter", model_id)
    return None


def invalidate_voice_cache() -> None:
    """Cache leeren (z. B. wenn der Nutzer die Modelle neu laden will)."""
    _cache.clear()
