"""Config flow for OpenRouter Voice — API-Key + TTS + STT Modelle."""

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
    get_voices_for_model,
)

TTS_MODEL_OPTIONS = {mid: cfg["name"] for mid, cfg in TTS_MODELS.items()}
STT_MODEL_OPTIONS = {mid: cfg["name"] for mid, cfg in STT_MODELS.items()}


def _build_user_schema(tts_model: str = DEFAULT_TTS_MODEL) -> vol.Schema:
    voices = get_voices_for_model(tts_model)
    return vol.Schema({
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_TTS_MODEL, default=tts_model): vol.In(TTS_MODEL_OPTIONS),
        vol.Required(CONF_VOICE, default=voices[0]): vol.In(voices),
        vol.Required(CONF_STT_MODEL, default=DEFAULT_STT_MODEL): vol.In(STT_MODEL_OPTIONS),
    })


class OpenRouterVoiceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for OpenRouter Voice."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=_build_user_schema(),
                description_placeholders={
                    "tts_models": "\n".join(
                        f"• `{mid}` — {c['description']}" for mid, c in TTS_MODELS.items()
                    ),
                    "stt_models": "\n".join(
                        f"• `{mid}` — {c['description']}" for mid, c in STT_MODELS.items()
                    ),
                },
            )

        api_key = user_input[CONF_API_KEY]
        if not api_key.startswith("sk-or-"):
            return self.async_show_form(
                step_id="user",
                data_schema=_build_user_schema(
                    user_input.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
                ),
                errors={"api_key": "invalid_api_key"},
            )

        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="OpenRouter Voice",
            data={
                CONF_API_KEY: api_key,
                CONF_TTS_MODEL: user_input.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL),
                CONF_VOICE: user_input.get(CONF_VOICE, DEFAULT_TTS_VOICE),
                CONF_STT_MODEL: user_input.get(CONF_STT_MODEL, DEFAULT_STT_MODEL),
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return OpenRouterVoiceOptionsFlow()


class OpenRouterVoiceOptionsFlow(config_entries.OptionsFlow):
    """Options flow — TTS model, voice, and STT model changeable."""

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_tts = self.config_entry.options.get(
            CONF_TTS_MODEL, self.config_entry.data.get(CONF_TTS_MODEL, DEFAULT_TTS_MODEL)
        )
        current_voices = get_voices_for_model(current_tts)
        current_stt = self.config_entry.options.get(
            CONF_STT_MODEL, self.config_entry.data.get(CONF_STT_MODEL, DEFAULT_STT_MODEL)
        )
        current_voice = self.config_entry.options.get(
            CONF_VOICE, self.config_entry.data.get(CONF_VOICE, DEFAULT_TTS_VOICE)
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_TTS_MODEL, default=current_tts): vol.In(TTS_MODEL_OPTIONS),
                vol.Optional(CONF_VOICE, default=current_voice): vol.In(current_voices),
                vol.Required(CONF_STT_MODEL, default=current_stt): vol.In(STT_MODEL_OPTIONS),
            }),
        )
