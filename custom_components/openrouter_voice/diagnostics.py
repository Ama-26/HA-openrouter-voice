"""Diagnostics support for OpenRouter Voice."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .const import DOMAIN, STT_MODELS, TTS_MODELS

REDACT = {CONF_API_KEY}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    entities: dict[str, Any] = {}
    for state in hass.states.async_all():
        if state.entity_id.startswith(("tts.openrouter", "stt.openrouter")):
            entities[state.entity_id] = {
                "state": state.state,
                "attributes": state.attributes,
            }

    return async_redact_data(
        {
            "entry_id": config_entry.entry_id,
            "data": async_redact_data(config_entry.data, REDACT),
            "options": config_entry.options,
            "version": config_entry.version,
            "tts_models": {
                mid: {"name": c["name"], "voices": c["voices"], "format": c["format"]}
                for mid, c in TTS_MODELS.items()
            },
            "stt_models": {
                mid: {"name": c["name"], "languages": c["languages"]}
                for mid, c in STT_MODELS.items()
            },
            "entities": entities,
        },
        REDACT,
    )
