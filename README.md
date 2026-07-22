# OpenRouter Voice

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for **Text-to-Speech (TTS)** and **Speech-to-Text (STT)** via the [OpenRouter API](https://openrouter.ai).

## Features

- 🎙️ **TTS** — 3 models: Google Gemini Flash TTS, OpenAI TTS, xAI Grok Voice
- 🎧 **STT** — 3 models: Deepgram Nova 2, OpenAI Whisper, Whisper Large v3
- 🔁 **Auto-Retry** — Exponential backoff for rate limits and server errors
- 📊 **Diagnostics** — Request counts, audio bytes, costs
- ⚙️ **Config Flow** — Full GUI setup, Options flow for model switching
- 🌍 **Multi-language** — German, English, French, Spanish, Japanese, and more

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. URL: `https://github.com/Ama-26/openrouter-voice`
3. Category: Integration → Add
4. Install "OpenRouter Voice"
5. Restart Home Assistant

### Manual

```bash
cd /config/custom_components
git clone https://github.com/Ama-26/openrouter-voice.git
mv openrouter-voice/custom_components/openrouter_voice .
# Restart HA
```

## Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search "OpenRouter Voice"
3. Enter your [OpenRouter API Key](https://openrouter.ai/keys) (`sk-or-...`)
4. Select TTS model, voice, and STT model
5. Done!

## Supported Models

### TTS

| Model ID | Voices | Notes |
|---|---|---|
| `google/gemini-3.1-flash-tts-preview` | fenrir, aoede, charon, kore, puck, zephyr | Fast, natural, multilingual |
| `openai/gpt-4o-mini-tts-2025-12-15` | alloy, echo, fable, nova, onyx, sage, shimmer | OpenAI's compact TTS |
| `x-ai/grok-voice-tts-1.0` | male_01, female_01, male_02, female_02 | Expressive xAI TTS |

### STT

| Model ID | Languages | Notes |
|---|---|---|
| `deepgram/nova-2` | de, en, fr, es, it, pt, nl, pl, ru, ja, ko, zh, hi, ar, tr, sv, da, no | Best quality, low latency |
| `openai/whisper-1` | de, en, fr, es, it, pt, nl, pl, ru, ja, ko, zh, ar, sv | OpenAI's ASR model |
| `openai/whisper-large-v3` | Full multi-language | Highest accuracy |

## Using with Assist

After setup, your models appear in:

- **TTS**: Settings → Voice Assistants → Assist Pipeline → Text-to-Speech
- **STT**: Settings → Voice Assistants → Assist Pipeline → Speech-to-Text

## Troubleshooting

**"API-Key ungültig"**: Your key must start with `sk-or-`. Get one at [openrouter.ai/keys](https://openrouter.ai/keys).

**"Rate-Limit erreicht"**: The integration auto-retries with backoff. If persistent, check your OpenRouter quota.

**STT returns empty**: The model may not support the audio format. Debug via HA Logs (filter for "openrouter_voice").

## License

MIT
