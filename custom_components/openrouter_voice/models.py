"""Live-Abfrage der verfügbaren TTS-/STT-Modelle bei OpenRouter.

Der Modellkatalog ändert sich beim Provider laufend (neue Modelle,
Umbenennungen, Preisupdates). Statt einer fixen Liste in ``const.py`` fragt
der Config-/Options-Flow deshalb die Models-API mit Modality-Filter ab:

- TTS: ``?output_modalities=speech`` (Audio-Ausgabe, ~20 Modelle)
- STT: ``?output_modalities=transcription`` (Transkription, ~24 Modelle)

Achtung: STT-Modelle stehen in der *ungefilterten* Models-API NICHT mit
``input_modalities=['audio']`` erkennbar drin (dort tauchen nur Omni-Chat-
modelle auf) — der Filter-Parameter ist der einzige verlässliche Weg.

Schlägt der Abruf fehl oder liefert nichts Brauchbares, greift der
Fallback-Katalog aus ``const.TTS_MODELS`` / ``const.STT_MODELS`` — der Flow
bleibt damit auch offline bedienbar.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

from .const import DEFAULT_STT_MODEL, DEFAULT_TTS_MODEL, DEFAULT_TIMEOUT, STT_MODELS, TTS_MODELS

_LOGGER = logging.getLogger(__name__)

MODELS_API_URL = "https://openrouter.ai/api/v1/models"


def _ensure_ids(options: dict[str, str], ids: Iterable[str]) -> dict[str, str]:
    """Stellt sicher, dass aktuelle/Default-Modell-IDs immer wählbar bleiben.

    Ist ein gesetztes Modell nicht (mehr) im Live-Katalog, würde das Dropdown
    ohne diesen Eintrag beim Speichern einen Validierungsfehler werfen bzw.
    den aktuellen Wert nicht anzeigen.
    """
    for mid in ids:
        if mid and mid not in options:
            options[mid] = mid
    return options


async def _async_fetch_model_options(
    hass: HomeAssistant, output_modality: str
) -> dict[str, str] | None:
    """Holt {model_id: Anzeigename} für eine Output-Modality von der API."""
    client = get_async_client(hass)
    response = await client.get(
        MODELS_API_URL,
        params={"output_modalities": output_modality},
        timeout=DEFAULT_TIMEOUT,
    )
    if response.status_code != 200:
        _LOGGER.warning("OpenRouter-Models-API: HTTP %s", response.status_code)
        return None
    data = response.json().get("data", [])
    options = {
        m["id"]: (m.get("name") or m["id"])
        for m in data
        if m.get("id") and output_modality in ((m.get("architecture") or {}).get("output_modalities") or [])
    }
    return options or None


async def async_get_tts_model_options(
    hass: HomeAssistant, ensure_ids: Iterable[str] = ()
) -> dict[str, str]:
    """Alle TTS-Modelle (Output-Modality 'speech') → {model_id: Anzeigename}."""
    try:
        options = await _async_fetch_model_options(hass, "speech")
        if options:
            _LOGGER.debug("OpenRouter: %d TTS-Modelle geladen", len(options))
            return _ensure_ids(options, ensure_ids)
        _LOGGER.warning("OpenRouter-Models-API liefert keine Speech-Modelle")
    except Exception as err:  # noqa: BLE001 — Netzfehler dürfen nie den Flow killen
        _LOGGER.warning("OpenRouter-Models-API nicht erreichbar: %s", err)
    _LOGGER.info("TTS-Modelle: nutze Fallback-Katalog (%d Modelle)", len(TTS_MODELS))
    return _ensure_ids(
        {mid: cfg["name"] for mid, cfg in TTS_MODELS.items()},
        (*ensure_ids, DEFAULT_TTS_MODEL),
    )


async def async_get_stt_model_options(
    hass: HomeAssistant, ensure_ids: Iterable[str] = ()
) -> dict[str, str]:
    """Alle STT-Modelle (Output-Modality 'transcription') → {model_id: Anzeigename}."""
    try:
        options = await _async_fetch_model_options(hass, "transcription")
        if options:
            _LOGGER.debug("OpenRouter: %d STT-Modelle geladen", len(options))
            return _ensure_ids(options, ensure_ids)
        _LOGGER.warning("OpenRouter-Models-API liefert keine Transcription-Modelle")
    except Exception as err:  # noqa: BLE001 — Netzfehler dürfen nie den Flow killen
        _LOGGER.warning("OpenRouter-Models-API nicht erreichbar: %s", err)
    _LOGGER.info("STT-Modelle: nutze Fallback-Katalog (%d Modelle)", len(STT_MODELS))
    return _ensure_ids(
        {mid: cfg["name"] for mid, cfg in STT_MODELS.items()},
        (*ensure_ids, DEFAULT_STT_MODEL),
    )
