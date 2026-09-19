"""Config flow for OpenRouter Voice — API-Key + TTS + STT Modelle.

Die Stimmen-Listen kommen live von der OpenRouter-API (siehe ``voices.py``),
damit die Auswahl auch nach Modell- oder Stimmen-Änderungen beim Provider
stimmt. Die Listen in ``const.TTS_MODELS`` dienen nur als Fallback.
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
    STT_MODELS,
    TTS_MODELS,
)
from .voices import async_get_supported_voices

TTS_MODEL_OPTIONS = {mid: cfg["name"] for mid, cfg in TTS_MODELS.items()}
STT_MODEL_OPTIONS = {mid: cfg["name"] for mid, cfg in STT_MODELS.items()}


def _model_choices_schema() -> dict:
    return {
        vol.Required(CONF_TTS_MODEL, default=DEFAULT_TTS_MODEL): vol.In(
            TTS_MODEL_OPTIONS
        ),
        vol.Required(CONF_STT_MODEL, default=DEFAULT_STT_MODEL): vol.In(
            STT_MODEL_OPTIONS
        ),
    }


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

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

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
                    **_model_choices_schema(),
                }
            ),
            errors=errors,
            description_placeholders={
                "tts_models": "\n".join(
                    f"• `{mid}` — {c['description']}" for mid, c in TTS_MODELS.items()
                ),
                "stt_models": "\n".join(
                    f"• `{mid}` — {c['description']}" for mid, c in STT_MODELS.items()
                ),
            },
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
                "model": TTS_MODEL_OPTIONS.get(model_id, model_id),
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

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        current_tts = self.config_entry.options.get(
            CONF_TTS_MODEL, self.config_entry.data.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        )
        current_stt = self.config_entry.options.get(
            CONF_STT_MODEL, self.config_entry.data.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)
        )
        current_voice = self.config_entry.options.get(
            CONF_VOICE, self.config_entry.data.get(CONF_VOICE, DEFAULT_TTS_VOICE)
        )

        if user_input is not None:
            new_tts = user_input[CONF_TTS_MODEL]
            self._pending = {
                CONF_TTS_MODEL: new_tts,
                CONF_STT_MODEL: user_input.get(CONF_STT_MODEL, current_stt),
            }
            # Modell gewechselt → Stimmen des neuen Modells abfragen
            if new_tts != current_tts:
                return await self.async_step_voice()
            self._pending[CONF_VOICE] = user_input.get(CONF_VOICE, current_voice)
            return self.async_create_entry(title="", data=self._pending)

        voices = await async_get_supported_voices(self.hass, current_tts)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TTS_MODEL, default=current_tts): vol.In(
                        TTS_MODEL_OPTIONS
                    ),
                    vol.Optional(
                        CONF_VOICE,
                        default=current_voice if current_voice in voices else voices[0],
                    ): vol.In(voices),
                    vol.Required(CONF_STT_MODEL, default=current_stt): vol.In(
                        STT_MODEL_OPTIONS
                    ),
                }
            ),
        )

    async def async_step_voice(self, user_input: dict | None = None) -> FlowResult:
        """Zweiter Schritt nach Modellwechsel: Stimme neu wählen."""
        model_id = self._pending.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        voices = await async_get_supported_voices(self.hass, model_id)

        if user_input is not None:
            self._pending[CONF_VOICE] = user_input.get(CONF_VOICE, voices[0])
            return self.async_create_entry(title="", data=self._pending)

        return self.async_show_form(
            step_id="voice",
            data_schema=_voice_schema(voices),
            description_placeholders={
                "model": TTS_MODEL_OPTIONS.get(model_id, model_id),
                "count": str(len(voices)),
            },
        )
