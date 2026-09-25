"""Config flow for OpenRouter Voice — API-Key + TTS + STT Modelle.

Die Modell- und Stimmen-Listen kommen live von der OpenRouter-Models-API
(``models.py`` / ``voices.py``), damit die Auswahl immer den aktuellen Stand
des Providers widerspiegelt. Die Kataloge in ``const.py`` dienen nur als
Fallback, falls die API nicht erreichbar ist.
"""

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .const import (
    CONF_STT_MODEL,
    CONF_TTS_MODEL,
    CONF_VOICE,
    DEFAULT_STT_MODEL,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    DOMAIN,
)
from .models import async_get_stt_model_options, async_get_tts_model_options
from .voices import async_get_supported_voices


def _model_schema(
    tts_options: dict[str, str],
    stt_options: dict[str, str],
    tts_default: str,
    stt_default: str,
) -> vol.Schema:
    """Schema mit dynamischen Modell-Dropdowns (aktuelle Werte garantiert enthalten)."""
    return vol.Schema(
        {
            vol.Required(CONF_TTS_MODEL, default=tts_default): vol.In(tts_options),
            vol.Required(CONF_STT_MODEL, default=stt_default): vol.In(stt_options),
        }
    )


def _voice_schema(voices: list[str], default: str | None = None) -> vol.Schema:
    if default not in voices:
        default = voices[0]
    return vol.Schema({vol.Required(CONF_VOICE, default=default): vol.In(voices)})


class OpenRouterVoiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for OpenRouter Voice."""

    VERSION = 1

    def __init__(self) -> None:
        self._api_key: str | None = None
        self._pending: dict = {}
        self._tts_options: dict[str, str] = {}

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        tts_options = await async_get_tts_model_options(
            self.hass, ensure_ids=(DEFAULT_TTS_MODEL,)
        )
        stt_options = await async_get_stt_model_options(
            self.hass, ensure_ids=(DEFAULT_STT_MODEL,)
        )

        self._tts_options = tts_options

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            if not api_key.startswith("sk-or-"):
                errors["api_key"] = "invalid_api_key"
            else:
                self._api_key = api_key
                self._pending = {
                    CONF_TTS_MODEL: user_input[CONF_TTS_MODEL],
                    CONF_STT_MODEL: user_input[CONF_STT_MODEL],
                }
                return await self.async_step_voice()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    **_model_schema(
                        tts_options, stt_options, DEFAULT_TTS_MODEL, DEFAULT_STT_MODEL
                    ).schema,
                }
            ),
            errors=errors,
        )

    async def async_step_voice(self, user_input: dict | None = None) -> FlowResult:
        """Zweiter Schritt: Stimme passend zum gewählten TTS-Modell."""
        model_id = self._pending.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        voices = await async_get_supported_voices(self.hass, model_id)

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="OpenRouter Voice",
                data={
                    CONF_API_KEY: self._api_key,
                    CONF_TTS_MODEL: model_id,
                    CONF_VOICE: user_input.get(CONF_VOICE, voices[0]),
                    CONF_STT_MODEL: self._pending.get(
                        CONF_STT_MODEL, DEFAULT_STT_MODEL
                    ),
                },
            )

        return self.async_show_form(
            step_id="voice",
            data_schema=_voice_schema(voices),
            description_placeholders={
                "model": self._tts_options.get(model_id, model_id),
                "count": str(len(voices)),
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return OpenRouterVoiceOptionsFlow()


class OpenRouterVoiceOptionsFlow(config_entries.OptionsFlow):
    """Options flow — TTS model, voice, and STT model changeable."""

    def __init__(self) -> None:
        self._pending: dict = {}
        self._tts_options: dict[str, str] = {}
        self._current_voice: str | None = None

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        current_tts = self.config_entry.options.get(
            CONF_TTS_MODEL, self.config_entry.data.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        )
        current_stt = self.config_entry.options.get(
            CONF_STT_MODEL, self.config_entry.data.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)
        )
        self._current_voice = self.config_entry.options.get(
            CONF_VOICE, self.config_entry.data.get(CONF_VOICE, DEFAULT_TTS_VOICE)
        )

        tts_options = await async_get_tts_model_options(
            self.hass, ensure_ids=(current_tts, DEFAULT_TTS_MODEL)
        )
        stt_options = await async_get_stt_model_options(
            self.hass, ensure_ids=(current_stt, DEFAULT_STT_MODEL)
        )
        self._tts_options = tts_options

        if user_input is not None:
            self._pending = {
                CONF_TTS_MODEL: user_input[CONF_TTS_MODEL],
                CONF_STT_MODEL: user_input.get(CONF_STT_MODEL, current_stt),
            }
            # Stimmen IMMER im zweiten Schritt — so passt die Liste garantiert
            # zum gewählten Modell (ein Live-Update innerhalb der Maske gibt
            # es in HA-Flows nicht, das alte Inline-Dropdown zeigte die
            # Stimmen des VORHERigen Modells).
            return await self.async_step_voice()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TTS_MODEL, default=current_tts): vol.In(
                        tts_options
                    ),
                    vol.Required(CONF_STT_MODEL, default=current_stt): vol.In(
                        stt_options
                    ),
                }
            ),
        )

    async def async_step_voice(self, user_input: dict | None = None) -> FlowResult:
        """Zweiter Schritt: Stimme passend zum gewählten Modell."""
        model_id = self._pending.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        voices = await async_get_supported_voices(self.hass, model_id)

        if user_input is not None:
            self._pending[CONF_VOICE] = user_input.get(CONF_VOICE, voices[0])
            return self.async_create_entry(title="", data=self._pending)

        return self.async_show_form(
            step_id="voice",
            data_schema=_voice_schema(voices, self._current_voice),
            description_placeholders={
                "model": self._tts_options.get(model_id, model_id),
                "count": str(len(voices)),
            },
        )
