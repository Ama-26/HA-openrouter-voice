# OpenRouter Voice for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

**TTS + STT via OpenRouter API** — eine Integration für beides.

- 🎙️ **TTS**: Google Gemini, OpenAI, xAI Grok
- 🎧 **STT**: Deepgram Nova 2, OpenAI Whisper (v1 + Large v3)
- 🔁 Auto-Retry, Diagnostics, Config Flow

## Setup

1. HACS → Custom Repository → `https://github.com/Ama-26/openrouter-voice`
2. Integration hinzufügen → API-Key → Modelle wählen
3. Assist Pipeline: TTS + STT auf OpenRouter umstellen

## Models

| TTS | STT |
|---|---|
| Google Gemini Flash TTS | Deepgram Nova 2 |
| OpenAI GPT-4o Mini TTS | OpenAI Whisper v1 |
| xAI Grok Voice TTS | OpenAI Whisper Large v3 |
