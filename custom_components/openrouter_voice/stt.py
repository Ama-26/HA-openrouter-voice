"""STT platform for OpenRouter Voice — Speech-to-Text via OpenRouter API.

Uses `async_process_audio_stream` (streaming Audio) for HA 2025+.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    CONF_STT_MODEL,
    DEFAULT_STT_MODEL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAX_RETRIES,
    RETRY_BACKOFF,
    STT_API_URL,
    STT_MODELS,
    classify_error,
    get_stt_languages,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up OpenRouter STT entity."""
    async_add_entities([OpenRouterSTTEntity(config_entry)])


class OpenRouterSTTEntity(SpeechToTextEntity):
    """OpenRouter STT entity — Multi-Modell mit Retry."""

    _attr_has_entity_name = True
    _attr_name = "Speech-to-Text"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the STT entity."""
        self._config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_stt_{config_entry.entry_id}"
        self._diagnostics: dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries": 0,
            "last_error": None,
            "last_error_time": None,
            "total_audio_seconds": 0.0,
            "total_cost": 0.0,
        }

    @property
    def _stt_model(self) -> str:
        return self._config_entry.options.get(
            CONF_STT_MODEL, self._config_entry.data.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)
        )

    # ── Properties (returned from memory) ────────────────────────────────

    @property
    def supported_languages(self) -> list[str]:
        return get_stt_languages(self._stt_model)

    @property
    def supported_formats(self) -> list[AudioFormats]:
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        return [AudioSampleRates.SAMPLERATE_16000, AudioSampleRates.SAMPLERATE_24000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        return [AudioChannels.CHANNEL_MONO]

    # ── Core method ──────────────────────────────────────────────────────

    async def async_process_audio_stream(
        self,
        metadata: SpeechMetadata,
        stream: AsyncIterable[bytes],
    ) -> SpeechResult:
        """Process audio stream, send to OpenRouter, return transcribed text."""
        self._diagnostics["total_requests"] += 1
        t0 = time.time()

        # Collect streaming audio chunks into single bytes
        audio_chunks: list[bytes] = []
        async for chunk in stream:
            audio_chunks.append(chunk)
        wav_data = b"".join(audio_chunks)

        if not wav_data:
            return SpeechResult(None, SpeechResultState.ERROR)

        try:
            text = await self._call_openrouter_stt(wav_data)
        except HomeAssistantError as exc:
            self._diagnostics["failed_requests"] += 1
            self._diagnostics["last_error"] = str(exc)
            self._diagnostics["last_error_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _LOGGER.warning("OpenRouter STT failed: %s", exc)
            return SpeechResult(None, SpeechResultState.ERROR)

        duration = time.time() - t0
        self._diagnostics["successful_requests"] += 1
        _LOGGER.debug("STT OK: %.1fs → '%s'", duration, text[:80])

        return SpeechResult(text=text, result=SpeechResultState.SUCCESS)

    async def _call_openrouter_stt(self, wav_data: bytes) -> str:
        """Send WAV audio to OpenRouter STT API (base64 JSON path).

        Returns transcribed text. Raises HomeAssistantError on failure.
        """
        client = get_async_client(self.hass)
        api_key: str = self._config_entry.data[CONF_API_KEY]
        model_id = self._stt_model
        b64_audio = base64.b64encode(wav_data).decode("ascii")
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await client.post(
                    STT_API_URL,
                    json={
                        "model": model_id,
                        "input_audio": {
                            "data": b64_audio,
                            "format": "wav",
                        },
                    },
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://home-assistant.io",
                        "X-Title": "Home Assistant",
                    },
                    timeout=DEFAULT_TIMEOUT,
                )

                if response.status_code == 200:
                    result = response.json()
                    text: str = result.get("text", "").strip()
                    usage = result.get("usage", {})
                    if "seconds" in usage:
                        self._diagnostics["total_audio_seconds"] += usage["seconds"]
                    if "cost" in usage:
                        self._diagnostics["total_cost"] += usage["cost"]
                    return text if text else ""

                # ── Error handling ──────────────────────────────────────
                try:
                    err_body = response.json()
                    err_msg = err_body.get("error", {}).get("message", response.text[:200])
                except (ValueError, KeyError):
                    err_msg = response.text[:200]

                voice_err = classify_error(response.status_code, err_msg)

                if response.status_code in (401, 403, 400):
                    raise HomeAssistantError(str(voice_err))

                if response.status_code in (429,) or response.status_code >= 500:
                    if attempt < MAX_RETRIES:
                        wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                        _LOGGER.warning(
                            "STT %s (attempt %d/%d), retry %.1fs",
                            voice_err, attempt, MAX_RETRIES, wait,
                        )
                        self._diagnostics["retries"] += 1
                        await asyncio.sleep(wait)
                        last_error = voice_err
                        continue

                raise HomeAssistantError(str(voice_err))

            except HomeAssistantError:
                raise
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                    _LOGGER.warning("STT timeout (attempt %d/%d)", attempt, MAX_RETRIES)
                    self._diagnostics["retries"] += 1
                    await asyncio.sleep(wait)
                    last_error = HomeAssistantError(f"STT timeout after {DEFAULT_TIMEOUT}s")
                    continue
                raise HomeAssistantError(f"STT timeout after {MAX_RETRIES} attempts")
            except Exception as exc:
                _LOGGER.error("STT unexpected error: %s", exc)
                raise HomeAssistantError(f"STT: {exc}") from exc

        raise last_error or HomeAssistantError(f"STT failed after {MAX_RETRIES} attempts")
