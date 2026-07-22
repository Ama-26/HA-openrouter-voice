"""TTS platform for OpenRouter Voice — Multi-Modell mit Retry und Diagnostics."""

from __future__ import annotations

import asyncio
import logging
import struct
import time
from typing import Any

from homeassistant.components.tts import (
    TextToSpeechEntity,
    TtsAudioType,
    Voice,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.httpx_client import get_async_client

from .const import (
    CONF_TTS_MODEL,
    CONF_VOICE,
    DEFAULT_TIMEOUT,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    DOMAIN,
    MAX_RETRIES,
    RETRY_BACKOFF,
    TTS_API_URL,
    TTS_MODELS,
    classify_error,
    get_sample_rate,
    get_tts_format,
    get_voices_for_model,
)

_LOGGER = logging.getLogger(__name__)


# ── WAV-Header ───────────────────────────────────────────────────────────

def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000) -> bytes:
    """Wrap raw PCM (16-bit, mono) in a standard WAV header."""
    data_size = len(pcm_data)
    channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, channels, sample_rate,
        byte_rate, block_align, bits_per_sample,
        b"data", data_size,
    )
    return header + pcm_data


# ── Setup ────────────────────────────────────────────────────────────────

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up OpenRouter TTS entity."""
    async_add_entities([OpenRouterTTSEntity(config_entry)])


# ── TTS Entity ───────────────────────────────────────────────────────────

class OpenRouterTTSEntity(TextToSpeechEntity):
    """OpenRouter TTS entity — Multi-Modell mit Retry."""

    _attr_has_entity_name = True
    _attr_name = "Text-to-Speech"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_languages = [
        "de", "en", "fr", "es", "it", "pt", "ja", "ko", "zh",
    ]
    _attr_default_language = "de"
    _attr_supported_options = ["voice"]

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the TTS entity."""
        self._config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_tts_{config_entry.entry_id}"
        self._diagnostics: dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retries": 0,
            "last_error": None,
            "last_error_time": None,
            "total_audio_bytes": 0,
            "last_request_duration_s": None,
        }

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            manufacturer="OpenRouter",
            model="Voice (TTS + STT)",
            name="OpenRouter Voice",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def _current_model(self) -> str:
        return self._config_entry.options.get(
            CONF_TTS_MODEL, self._config_entry.data.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        )

    def async_get_supported_voices(self, language: str) -> list[Voice] | None:
        """Return supported voices for configured model."""
        voices = get_voices_for_model(self._current_model)
        return [Voice(voice_id=v, name=v.capitalize()) for v in voices]

    async def _call_openrouter(
        self, message: str, voice: str, model_id: str
    ) -> bytes:
        """Call OpenRouter TTS API with retry logic. Returns raw PCM data."""
        client = get_async_client(self.hass)
        response_format = get_tts_format(model_id)
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await client.post(
                    TTS_API_URL,
                    json={
                        "model": model_id,
                        "input": message,
                        "voice": voice,
                        "response_format": response_format,
                    },
                    headers={
                        "Authorization": f"Bearer {self._config_entry.data[CONF_API_KEY]}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://home-assistant.io",
                        "X-Title": "Home Assistant",
                    },
                    timeout=DEFAULT_TIMEOUT,
                )

                if response.status_code == 200:
                    pcm_data = response.content
                    if not pcm_data or len(pcm_data) < 50:
                        raise HomeAssistantError(
                            f"TTS response too short ({len(pcm_data)} bytes)"
                        )
                    return pcm_data

                try:
                    err_body = response.json()
                    err_msg = err_body.get("error", {}).get(
                        "message", response.text[:200]
                    )
                except (ValueError, KeyError):
                    err_msg = response.text[:200]

                tts_err = classify_error(response.status_code, err_msg)

                if response.status_code in (401, 403, 400):
                    raise HomeAssistantError(str(tts_err))

                if response.status_code in (429,) or response.status_code >= 500:
                    if attempt < MAX_RETRIES:
                        wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                        _LOGGER.warning(
                            "TTS %s (attempt %d/%d), retry %.1fs",
                            tts_err, attempt, MAX_RETRIES, wait,
                        )
                        self._diagnostics["retries"] += 1
                        await asyncio.sleep(wait)
                        last_error = tts_err
                        continue

                raise HomeAssistantError(str(tts_err))

            except HomeAssistantError:
                raise
            except asyncio.TimeoutError:
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF * (2 ** (attempt - 1))
                    _LOGGER.warning(
                        "TTS timeout (attempt %d/%d), retry %.1fs",
                        attempt, MAX_RETRIES, wait,
                    )
                    self._diagnostics["retries"] += 1
                    await asyncio.sleep(wait)
                    last_error = HomeAssistantError(
                        f"TTS timeout after {DEFAULT_TIMEOUT}s"
                    )
                    continue
                raise HomeAssistantError(
                    f"TTS timeout after {MAX_RETRIES} attempts"
                )
            except Exception as exc:
                _LOGGER.error("TTS error: %s", exc)
                raise HomeAssistantError(f"TTS: {exc}") from exc

        raise last_error or HomeAssistantError(
            f"TTS failed after {MAX_RETRIES} attempts"
        )

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any]
    ) -> TtsAudioType:
        """Generate TTS audio."""
        voice = options.get(
            "voice",
            self._config_entry.options.get(
                CONF_VOICE, self._config_entry.data.get(CONF_VOICE, DEFAULT_TTS_VOICE)
            ),
        )
        model_id = self._current_model
        sample_rate = get_sample_rate(model_id)

        self._diagnostics["total_requests"] += 1
        t0 = time.time()

        _LOGGER.debug("TTS: %s (model=%s, voice=%s)", message[:50], model_id, voice)

        try:
            pcm_data = await self._call_openrouter(message, voice, model_id)
            wav_data = _pcm_to_wav(pcm_data, sample_rate)
            duration = time.time() - t0

            self._diagnostics["successful_requests"] += 1
            self._diagnostics["total_audio_bytes"] += len(wav_data)
            self._diagnostics["last_request_duration_s"] = round(duration, 1)

            _LOGGER.debug(
                "TTS OK: %.1fs, %dB PCM → %dB WAV (%s, %s)",
                duration, len(pcm_data), len(wav_data), model_id, voice,
            )
            return "wav", wav_data

        except HomeAssistantError:
            self._diagnostics["failed_requests"] += 1
            self._diagnostics["last_error"] = "See HA log"
            self._diagnostics["last_error_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
            raise
