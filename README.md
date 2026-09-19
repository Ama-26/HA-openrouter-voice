# OpenRouter Voice

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![AI-generated](https://img.shields.io/badge/AI--generated-100%25-blue)](https://github.com/Ama-26/HA-openrouter-voice)

> **⚠️ This integration was created entirely with AI assistance (Claude via Hermes Agent).**
> All code, documentation, and architecture were generated through iterative AI-human collaboration.
> Fully functional and production-tested, but keep this in mind when reviewing.

Home Assistant integration for **Text-to-Speech (TTS)** and **Speech-to-Text (STT)** via the [OpenRouter API](https://openrouter.ai).

## Features

- 🎙️ **TTS** — 3 models: Google Gemini Flash, OpenAI GPT-4o Mini, xAI Grok Voice
- 🎧 **STT** — 3 tiers: 🥇 Best (Deepgram Nova-3), 🥈 Medium (Whisper Large v3), 🥉 Cheap (Qwen3 ASR)
- 🔁 **Auto-Retry** — Exponential backoff for rate limits and server errors
- 📊 **Diagnostics** — Request counts, audio bytes, costs
- ⚙️ **Config Flow** — Full GUI setup, Options flow for model switching
- 🌍 **Multi-language** — German, English, French, Spanish, Japanese, and more
- 🎤 **PCM auto-detect** — Handles raw PCM from devices like Voice PE (auto-adds WAV header)

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. URL: `https://github.com/Ama-26/HA-openrouter-voice`
3. Category: Integration → Add
4. Install "OpenRouter Voice"
5. Restart Home Assistant

### Manual

```bash
cd /config/custom_components
git clone https://github.com/Ama-26/HA-openrouter-voice.git
mv HA-openrouter-voice/custom_components/openrouter_voice .
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
| `google/gemini-3.1-flash-tts-preview` | 30 voices (Zephyr, Puck, Charon, Kore, Fenrir, …) | Fast, natural, multilingual |
| `x-ai/grok-voice-tts-1.0` | eve, ara, rex, sal, leo | Expressive xAI TTS |
| `openai/gpt-4o-mini-tts-2025-12-15` | alloy, echo, fable, nova, onyx, sage, shimmer | ⚠️ Not listed in OpenRouter's current TTS model list |

> **Voice lists are fetched live from the OpenRouter Models API** (`supported_voices`
> per model, cached for one hour). The lists in `const.py` are only a fallback for
> when the API can't be reached. When you pick a different TTS model in the
> options flow, the voice step reloads the matching voices automatically.

### STT (3 Tiers)

| Tier | Model ID | Cost | Notes |
|---|---|---|---|
| 🥇 Best | `deepgram/nova-3` | $0.0043/min | 30+ languages, highest accuracy |
| 🥈 Medium | `openai/whisper-large-v3` | $0.0015/min | 99+ languages, proven reliability |
| 🥉 Cheap | `qwen/qwen3-asr-flash-2026-02-10` | $0.000035/min | 11 languages, 120× cheaper than Nova-3 |

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
