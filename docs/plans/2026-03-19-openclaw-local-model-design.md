# OpenClaw Local Model Integration Design

**Date**: 2026-03-19
**Status**: Implemented & Verified

## Goal

Replace OpenClaw's default embedded model (openai-codex/gpt-5.3-codex) with the local Qwen3.5-35B-A3B model running on llama-server, matching pi's existing local model configuration.

## Current State

- **Pi** (`~/.pi/agent/models.json`): Uses llama-server at `http://127.0.0.1:8081/v1` with Qwen3.5-35B-A3B, contextWindow 131072, maxTokens 65536.
- **OpenClaw** (`~/.openclaw/openclaw.json`): Uses `openai-codex/gpt-5.3-codex` as main agent default. No local model configured.

## Design

### Changes to `~/.openclaw/openclaw.json`

**1. Add top-level `models` block** with `mode: "merge"` to preserve existing openai-codex provider while adding llama-server:

```json
"models": {
  "mode": "merge",
  "providers": {
    "llama-server": {
      "baseUrl": "http://127.0.0.1:8081/v1",
      "apiKey": "local",
      "api": "openai-completions",
      "models": [
        {
          "id": "HauhauCS/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive",
          "name": "Qwen 3.5 35B-A3B (Local)",
          "reasoning": true,
          "input": ["text", "image"],
          "contextWindow": 131072,
          "maxTokens": 65536,
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 },
          "compat": {
            "supportsDeveloperRole": false,
            "supportsReasoningEffort": false,
            "supportsUsageInStreaming": false,
            "thinkingFormat": "qwen"
          }
        }
      ]
    }
  }
}
```

**2. Change `agents.defaults.model.primary`** from `openai-codex/gpt-5.3-codex` to `llama-server/HauhauCS/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive`.

### What stays the same

- `claude` agent (anthropic/claude-opus-4-6 via acpx) — unchanged
- All cron jobs, channels, plugins, skills — unchanged
- openai-codex provider remains available via `mode: "merge"`

## Prerequisites

- llama-server must be running on port 8081 before OpenClaw can use the local model
- Startup command: `/opt/homebrew/bin/llama-server -m <model.gguf> --mmproj <mmproj.gguf> -ngl 99 -fa on -c 131072 -np 1 --port 8081`

## Risks

- `api: "openai-responses"` may not work with llama-server — fallback to `"openai-completions"` if issues arise
- `compat` flags from pi may be ignored by OpenClaw (harmless if so)
- Cron jobs will fail if llama-server is not running (openai-codex should fallback via merge mode)

## Verification

1. `openclaw config validate` — config is valid
2. `openclaw models` — local model appears in list
3. `openclaw agent` — test a simple prompt against the local model
