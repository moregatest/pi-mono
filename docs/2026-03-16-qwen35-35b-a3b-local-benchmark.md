# Qwen3.5-35B-A3B 本地部署測試報告

**日期**: 2026-03-16
**機器**: MacBook Pro, Apple M4 Max, 64GB RAM
**模型**: HauhauCS/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive (Q4_K_M, 20GB)
**推理引擎**: llama.cpp llama-server (build 8140)
**連接方式**: pi TUI via `~/.pi/agent/models.json`

---

## 硬體環境

| 項目 | 規格 |
|------|------|
| CPU | Apple M4 Max (16 核心, 12 效能 + 4 節能) |
| GPU | M4 Max 整合式 GPU, 49GB 可用顯存 |
| RAM | 64GB 統一記憶體 |
| macOS | Darwin 24.6.0 |

## Context Window 壓力測試

以 `-ngl 99 -fa on -np 1`（全 GPU offload + flash attention + 單 slot）測試不同 context 大小：

| Context Size | KV Cache | 總 RAM 用量 | 狀態 |
|-------------|----------|------------|------|
| 4,096 | ~10 MB | 20.2 GB | OK |
| 8,192 | ~20 MB | 20.2 GB | OK |
| 16,384 | ~40 MB | 20.3 GB | OK |
| 32,768 | ~80 MB | 20.6 GB | OK |
| 65,536 | ~160 MB | 21.2 GB | OK |
| 131,072 (128K) | ~320 MB | 22.5 GB | OK |
| **262,144 (256K)** | **~640 MB** | **25.0 GB** | **OK** |

### 關鍵發現

**模型訓練最大 context 為 262,144 tokens，在 64GB M4 Max 上全部可用。**

KV cache 佔用極低的原因：
1. **MoE 架構** (256 experts, 8 active) — 只有 10/40 層使用 KV cache（其餘為 Mamba SSM 層）
2. **GQA** (Grouped Query Attention) — n_head_kv=2 vs n_head=16, KV 頭只有注意力頭的 1/8
3. **Flash Attention** — 不需要完整 attention matrix 常駐記憶體
4. **Mamba SSM 層** — 使用固定大小的 recurrent state（~63MB），不隨 context 線性增長

## max_tokens 生成測試

| 測試 | max_tokens 設定 | 實際生成 | finish_reason | 說明 |
|------|----------------|---------|---------------|------|
| 簡短回答 | 100 | 10 | stop | 模型自然停止 |
| Thinking 模式 (簡單問題) | 4,096 | 908 | stop | thinking ~700 + answer ~200 |
| 長文生成 (無 thinking) | 8,000 | 1,892 | stop | 模型自然停止 |
| 數字列表 (無 thinking) | 260,000 | 48,894 | stop | 模型自行停在 ~49K tokens |
| JSON 生成 (無 thinking) | 250,000 | >32,643 | (中斷) | 持續生成中，~57 tok/s |
| Thinking 長文 | 32,000 | (進行中) | (中斷) | thinking 佔用大量 tokens |

### 生成速度

| 階段 | 速度 |
|------|------|
| Prompt 處理 | ~216-252 tokens/sec |
| Token 生成 | ~56-57 tokens/sec |

### 實際限制

- **理論上限**: 262,144 - prompt_tokens（即 context window 減去輸入）
- **實際觀察**: 模型在 ~49K tokens 時傾向自然停止（即使 max_tokens 設得更高）
- **Thinking 模式**: reasoning_content 和 content 共享 max_tokens 預算，thinking 會消耗大量 tokens

## Vision (圖片辨識) 測試

需下載額外的 mmproj 檔案 (`mmproj-Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf`, 858MB)，啟動時加上 `--mmproj` 參數。

| 測試項目 | 結果 |
|---------|------|
| 圖片內容描述 | OK — 詳細描述人物、場景、姿勢 |
| 文字辨識 (watermark) | OK — 正確讀出 "123AV.com"、"IPPA 060047" |
| base64 圖片輸入 | OK — 透過 OpenAI vision API 格式 |

## 功能驗證總覽

| 功能 | 狀態 |
|------|------|
| 基本對話 | OK |
| System role | OK |
| Streaming (SSE) | OK |
| Tool calling | OK |
| Thinking mode (reasoning_content) | OK |
| Vision (圖片辨識) | OK (需 mmproj) |
| max_tokens 限制 | OK |

## 最佳配置建議

### llama-server 啟動參數

```bash
/opt/homebrew/bin/llama-server \
  -m /Users/tung/Codes/aitest/lfm2-tool-test/models/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf \
  --mmproj /Users/tung/Codes/aitest/lfm2-tool-test/models/mmproj-Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf \
  -ngl 99 \    # 全部層 offload 到 GPU
  -fa on \     # 啟用 flash attention
  -c 131072 \  # 128K context (平衡 RAM 與實用性)
  -np 1 \      # 單 slot（最大化單次請求的可用 context）
  --port 8081
```

**為何選擇 131072 而非 262144**:
- 262K 可以跑但 RAM 25GB，留給系統的餘裕較小
- 128K 只用 22.5GB，還有 41.5GB 給系統和其他程式
- pi coding agent 實際使用中很少需要超過 128K context
- 如有需要可隨時調高

### pi models.json 配置

```json
{
  "contextWindow": 131072,
  "maxTokens": 65536
}
```

**maxTokens 設為 65536 的理由**:
- 模型實測最大自然生成約 49K tokens
- 留 buffer 給 thinking mode（thinking + answer 共用預算）
- 超過此值模型通常會自行 stop，設更高無實際意義
- 65536 = context 的一半，確保有足夠空間給 prompt

## 注意事項

1. **Port 衝突**: 此機器的 rclone 以 IPv6 wildcard (`*:8080`) 監聽，會攔截所有 8080 連線（含 IPv4）。**必須使用 port 8081**
2. **Thinking 模式冗長**: 此模型的 "Aggressive" finetune 會產生非常長的 thinking（簡單問題也可能 3000+ chars），建議對簡單任務關閉 thinking
3. **Tool calling**: Qwen3.5-35B-A3B 支援 OpenAI 格式的 tool calling，測試通過
4. **模型切換**: llama-server 一次只能載入一個模型，切換需重啟 server

## 檔案位置

| 項目 | 路徑 |
|------|------|
| 模型檔案 | `/Users/tung/Codes/aitest/lfm2-tool-test/models/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf` |
| Vision mmproj | `/Users/tung/Codes/aitest/lfm2-tool-test/models/mmproj-Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf` |
| pi 配置 | `~/.pi/agent/models.json` |
| llama-server | `/opt/homebrew/bin/llama-server` |

## 快速啟動

```bash
# 1. 啟動 llama-server (含 vision)
/opt/homebrew/bin/llama-server \
  -m /Users/tung/Codes/aitest/lfm2-tool-test/models/Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf \
  --mmproj /Users/tung/Codes/aitest/lfm2-tool-test/models/mmproj-Qwen3.5-35B-A3B-Uncensored-HauhauCS-Aggressive-f16.gguf \
  -ngl 99 -fa on -c 131072 -np 1 --port 8081

# 2. 啟動 pi TUI 並選擇本地模型
pi --model "Qwen 3.5"
```
