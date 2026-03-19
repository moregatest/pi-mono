# OpenClaw 本地模型整合筆記

**日期**: 2026-03-19
**目標**: 將 pi 使用的本地 Qwen3.5-35B-A3B 模型整合到 OpenClaw Gateway

---

## 背景

pi TUI 已透過 `~/.pi/agent/models.json` 配置 llama-server 作為本地推理引擎。本次將相同的模型配置移植到 OpenClaw，取代預設的 `openai-codex/gpt-5.3-codex`，讓 cron jobs 和一般對話都走本地模型（免費、低延遲）。

## 最終配置

在 `~/.openclaw/openclaw.json` 新增頂層 `models` 區塊：

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

並將 `agents.defaults.model.primary` 改為：
```
llama-server/HauhauCS/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive
```

## pi vs OpenClaw 配置差異

| 項目 | pi (`models.json`) | OpenClaw (`openclaw.json`) |
|------|-------------------|---------------------------|
| api | `openai-completions` | `openai-completions` |
| thinkingFormat | `qwen-chat-template` | `qwen` |
| compat 位置 | provider 層級 | model 層級 |
| merge mode | 無（單一 provider） | `"merge"` 保留 openai-codex |

## 踩坑紀錄

### 1. `api: "openai-responses"` 導致 Jinja template 錯誤

**現象**: llama-server 回傳 500，錯誤訊息 `Unexpected message role.`

**原因**: `openai-responses` API 會送出 Qwen chat template 不認得的 message role（可能是 `developer`）。即使設了 `supportsDeveloperRole: false`，OpenClaw 的 responses API 路徑仍然會產生不相容的 role。

**解法**: 改用 `"openai-completions"`（與 pi 一致），使用標準 chat completions API。

### 2. `compat` 必須放在 model 層級

**現象**: `openclaw config validate` 報錯 `Unrecognized key: "compat"` at provider level。

**原因**: OpenClaw schema 只接受 model 層級的 `compat`，不接受 provider 層級。Pi 的 schema 則是放在 provider 層級。

**解法**: 將 `compat` 物件從 provider 移到 `models[0]` 內。

### 3. `thinkingFormat` 值不同

**現象**: `openclaw config validate` 報錯 `Invalid input (allowed: "openai", "zai", "qwen")`。

**原因**: Pi 使用 `"qwen-chat-template"`，OpenClaw 使用簡寫 `"qwen"`。

**解法**: 改為 `"qwen"`。

### 4. Gateway 自動重啟

**現象**: 修改 `openclaw.json` 後執行 `openclaw agent`，Gateway 回報 `closed (1012): service restart` 然後 fallback 到 embedded model。

**原因**: OpenClaw Gateway 偵測到 config 變更會自動重啟。第一次請求撞上重啟視窗，fallback 到 embedded model 執行完畢後，後續請求正常走本地模型。

**影響**: 僅首次，非持續性問題。

## 驗證結果

```bash
# 配置驗證
openclaw config validate
# → Config valid

# 模型列表確認
openclaw models
# → Default: llama-server/HauhauCS/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive
# → llama-server provider 出現在 auth overview

# 實際對話測試
openclaw agent --agent main --message "回答數字1就好" --json
# → provider: "llama-server"
# → model: "HauhauCS/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive"
# → text: "1"
# → stopReason: "stop"
```

## 注意事項

1. **llama-server 必須先啟動**: OpenClaw 不會自動啟動 llama-server。使用前需手動執行：
   ```bash
   /opt/homebrew/bin/llama-server \
     -m /Users/tung/Codes/aitest/lfm2-tool-test/models/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf \
     --mmproj /Users/tung/Codes/aitest/lfm2-tool-test/models/mmproj-Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf \
     -ngl 99 -fa on -c 131072 -np 1 --port 8081
   ```
2. **Port 8081**: 此機器 port 8080 被 rclone 佔用，必須用 8081
3. **`mode: "merge"`**: openai-codex 仍保留，llama-server 離線時理論上可 fallback
4. **Cron jobs**: 切換後所有 cron jobs 都會走本地模型，注意 llama-server 需持續運行
