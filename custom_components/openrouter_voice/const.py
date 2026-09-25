"""Constants for OpenRouter Voice — TTS + STT, Multi-Modell, Diagnostics."""

DOMAIN = "openrouter_voice"

# ── Config Keys ──────────────────────────────────────────────────────────

CONF_VOICE = "voice"
CONF_TTS_MODEL = "tts_model"
CONF_STT_MODEL = "stt_model"

# ── API ──────────────────────────────────────────────────────────────────

TTS_API_URL = "https://openrouter.ai/api/v1/audio/speech"
STT_API_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF = 2.0

# ── TTS Models (Fallback-Katalog — der Config-/Options-Flow lädt die
#    Modell-Liste live aus der OpenRouter-Models-API, siehe models.py) ───────

DEFAULT_TTS_MODEL = "google/gemini-3.1-flash-tts-preview"
DEFAULT_TTS_VOICE = "fenrir"

TTS_MODELS: dict[str, dict] = {
    "google/gemini-3.1-flash-tts-preview": {
        "name": "Google Gemini 3.1 Flash TTS",
        # Fallback — die echte Liste kommt live aus der OpenRouter-API (voices.py)
        "voices": [
            "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
            "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
            "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
            "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird",
            "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
        ],
        "format": "pcm",
        "sample_rate": 24000,
        "description": "Schnell, natürlich, mehrsprachig (auch Deutsch)",
    },
    "openai/gpt-4o-mini-tts-2025-12-15": {
        "name": "OpenAI GPT-4o Mini TTS",
        "voices": ["alloy", "echo", "fable", "nova", "onyx", "sage", "shimmer"],
        "format": "pcm",
        "sample_rate": 24000,
        "description": "OpenAI's kompaktes TTS-Modell",
    },
    "x-ai/grok-voice-tts-1.0": {
        "name": "xAI Grok Voice TTS",
        # Fallback — echte IDs: eve, ara, rex, sal, leo (live via voices.py)
        "voices": ["eve", "ara", "rex", "sal", "leo"],
        "format": "pcm",
        "sample_rate": 24000,
        "description": "xAI's Grok Voice — expressive Sprachausgabe",
    },
}

# ── STT Models (Fallback-Katalog, siehe models.py) ───────────────────────

DEFAULT_STT_MODEL = "qwen/qwen3-asr-flash-2026-02-10"  # Default = günstig

STT_MODELS: dict[str, dict] = {
    # ── Tier 1: Beste Qualität ──────────────────────────────────────────
    "deepgram/nova-3": {
        "name": "Deepgram Nova 3 (Beste)",
        "tier": "gut",
        "languages": ["de", "en", "fr", "es", "it", "pt", "nl", "pl", "ru",
                      "ja", "ko", "zh", "hi", "ar", "tr", "sv", "da", "no"],
        "description": "Beste STT-Qualität, 30+ Sprachen, $0.0043/min",
    },
    # ── Tier 2: Mittelklasse ────────────────────────────────────────────
    "openai/whisper-large-v3": {
        "name": "OpenAI Whisper Large v3 (Mittel)",
        "tier": "mittel",
        "languages": ["de", "en", "fr", "es", "it", "pt", "nl", "pl", "ru",
                      "ja", "ko", "zh", "hi", "ar", "tr", "sv", "da", "no"],
        "description": "Bewährt, 99+ Sprachen, $0.0015/min",
    },
    # ── Tier 3: Günstig ─────────────────────────────────────────────────
    "qwen/qwen3-asr-flash-2026-02-10": {
        "name": "Qwen3 ASR Flash (Günstig)",
        "tier": "günstig",
        "languages": ["de", "en", "fr", "es", "it", "pt", "ja", "ko", "zh", "ru", "ar"],
        "description": "120x günstiger als Nova-3, $0.000035/min, 11 Sprachen",
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────

def get_voices_for_model(model_id: str) -> list[str]:
    model_cfg = TTS_MODELS.get(model_id)
    return model_cfg["voices"] if model_cfg else [DEFAULT_TTS_VOICE]


def get_tts_format(model_id: str) -> str:
    model_cfg = TTS_MODELS.get(model_id)
    return model_cfg["format"] if model_cfg else "pcm"


def get_sample_rate(model_id: str) -> int:
    model_cfg = TTS_MODELS.get(model_id)
    return model_cfg["sample_rate"] if model_cfg else 24000


def get_stt_languages(model_id: str) -> list[str]:
    model_cfg = STT_MODELS.get(model_id)
    return model_cfg["languages"] if model_cfg else ["de", "en"]


# ── Error Classification ─────────────────────────────────────────────────

class VoiceError(Exception):
    """Basis-Klasse für Voice-Fehler (TTS + STT)."""

    def __init__(self, message: str, code: str, http_status: int = 0) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class AuthError(VoiceError):
    """API-Key ungültig oder fehlt."""


class RateLimitError(VoiceError):
    """Rate-Limit erreicht."""


class BadRequestError(VoiceError):
    """Ungültige Parameter."""


class ServerError(VoiceError):
    """OpenRouter-Server-Fehler."""


class TimeoutError_(VoiceError):
    """Zeitüberschreitung."""


def classify_error(http_status: int, response_body: str = "") -> VoiceError:
    """Klassifiziert einen HTTP-Fehler."""
    msg = response_body[:200] if response_body else f"HTTP {http_status}"

    if http_status == 401:
        return AuthError(
            "API-Key ungültig. Prüfe deinen OpenRouter API-Key.",
            code="auth_invalid_key", http_status=http_status,
        )
    if http_status == 403:
        return AuthError(
            "Keine Berechtigung. Reicht dein OpenRouter-Guthaben?",
            code="auth_forbidden", http_status=http_status,
        )
    if http_status == 429:
        return RateLimitError(
            "Rate-Limit erreicht. Warte kurz.",
            code="rate_limited", http_status=http_status,
        )
    if http_status == 400:
        return BadRequestError(
            f"Ungültige Anfrage: {msg}", code="bad_request", http_status=http_status,
        )
    if http_status >= 500:
        return ServerError(
            f"OpenRouter-Server-Fehler: {msg}", code="server_error", http_status=http_status,
        )
    return VoiceError(f"Unbekannter Fehler: {msg}", code="unknown", http_status=http_status)
