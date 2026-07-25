# Paritok hosted GPU：Windows PowerShell 配置

本文针对 LeanCI 当前固定依赖 `paritok[proxy]==1.2.7`。配置字段已经对照
[Paritok 官方仓库](https://github.com/Paritok-official/paritok-4b-v1)的 1.2.7
安装包源码与本机安装包验证，不使用旧教程中的参数。

## 1. 安装

从仓库根目录运行：

```powershell
.\backend\.venv\Scripts\python.exe -m pip install "paritok[proxy]==1.2.7"
.\backend\.venv\Scripts\python.exe -m pip install --requirement backend\requirements-dev.txt
```

验证版本和代理命令：

```powershell
.\backend\.venv\Scripts\paritok.exe --version
.\backend\.venv\Scripts\paritok.exe proxy --help
```

## 2. 本机密钥与环境变量

只在被 Git 忽略的仓库根目录 `.env` 中填写真实密钥。不要覆盖已有 `.env`：

```powershell
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item ".env.example" ".env"
}
```

必需配置：

```dotenv
PARITOK_API_KEY=<仅在本机填写>
DEEPSEEK_API_KEY=<仅在本机填写>
LLM_PROVIDER=paritok
DEEPSEEK_MODEL=deepseek-v4-flash
PARITOK_PROXY_BASE_URL=http://127.0.0.1:8080/v1
PARITOK_HEALTH_URL=http://127.0.0.1:8080/health
PARITOK_STATS_URL=http://127.0.0.1:8080/stats
```

`paritok.yaml` 不包含真实 Key。Paritok 1.2.7 会在加载 YAML 后，用进程环境中的
`PARITOK_API_KEY` 覆盖 `gpu_server.api_key`。FastAPI 把 `DEEPSEEK_API_KEY` 作为本地
OpenAI-compatible 请求的 Authorization，Paritok 再将请求转发到固定完整端点。

## 3. 当前 YAML schema

仓库根目录 [paritok.yaml](../paritok.yaml) 使用 1.2.7 的实际字段：

- `use_gpu_server: true`
- `gpu_server.base_url/model/api_key/timeout`
- `compression.min_tokens/max_tokens/refusal_threshold`
- `history.enabled/keep_recent_turns/context_threshold/context_window`
- `tool_discovery.strategy/top_k/k_max/adaptive/mcp_signal_threshold`
- `trace.enabled/path`
- `codex.enabled/model/api_key`
- `shadow_storage`

`tool_discovery.strategy` 固定为 `passthrough`，因为 LeanCI 不接收用户工具目录；这避免下载
可选的 embedding selector，同时不改变 hosted GPU 压缩链。

## 4. 启动顺序

终端 1（必须一直保持打开）：

```powershell
.\scripts\start_paritok.ps1
```

该脚本只从 `.env` 读取 `PARITOK_API_KEY`，不会打印密钥；实际代理命令固定等价于：

```powershell
.\backend\.venv\Scripts\paritok.exe proxy `
  --host 127.0.0.1 `
  --port 8080 `
  --config-file paritok.yaml `
  --openai-url "https://api.deepseek.com/chat/completions" `
  --log-level info
```

不要关闭终端 1。Paritok Proxy 是前台进程，关闭它后正式分析会返回 503。

终端 2：

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app `
  --app-dir backend `
  --host 127.0.0.1 `
  --port 8000 `
  --workers 1
```

必须保持 `--workers 1`。本次 Token 归因依赖一个进程内锁和 `/stats` 前后快照；多 worker
会破坏单次请求的归属证明。

终端 3：

```powershell
cd frontend
npm run dev
```

浏览器访问 `http://127.0.0.1:5173`。

## 5. Linux / Docker

运行环境必须注入 `PARITOK_API_KEY`，然后启动：

```sh
./scripts/start_paritok.sh
```

脚本固定监听 `127.0.0.1:8080`，并固定使用
`https://api.deepseek.com/chat/completions`。Docker 中应由进程管理器同时监管 Proxy 和
单 worker FastAPI；不得把 8080 映射到公网。

## 6. 快速检查

```powershell
Invoke-RestMethod "http://127.0.0.1:8080/health"
Invoke-RestMethod "http://127.0.0.1:8080/stats"
.\backend\.venv\Scripts\python.exe scripts\test_paritok_connection.py
Invoke-RestMethod "http://127.0.0.1:8000/api/health"
```

`/health` 只证明本地代理进程存活。只有连接脚本和 LeanCI `/api/health` 同时确认 hosted
GPU 可用，才允许正式分析。

## 7. 常见错误

| 错误 | 含义与处理 |
| --- | --- |
| `FORMAL_ANALYSIS_REQUIRES_PARITOK` | 将本机 `.env` 的 `LLM_PROVIDER` 改为 `paritok` 并重启 FastAPI |
| `PARITOK_PROXY_UNAVAILABLE` | Proxy 未启动、8080 被占用或本机防火墙拦截 |
| `PARITOK_GPU_UNAVAILABLE` | hosted GPU 不可达或 `PARITOK_API_KEY` 无效；不要继续正式分析 |
| `PARITOK_STATS_UNAVAILABLE` | `/stats` 超时或 schema 不匹配；LeanCI 会丢弃结果，不生成 Token 数字 |
| `PARITOK_ROUTE_NOT_VERIFIED` | stats 请求数与本次 DeepSeek 尝试次数不一致；检查是否有其他客户端共用此 Proxy |
| `DEEPSEEK_AUTHENTICATION_FAILED` | `DEEPSEEK_API_KEY` 无效或已撤销 |
| `DEEPSEEK_INSUFFICIENT_BALANCE` | DeepSeek 余额不足 |
| `DEEPSEEK_TIMEOUT` | DeepSeek 请求超时；API 返回 504 |
| `DEEPSEEK_SERVER_ERROR` | DeepSeek 暂时不可用；API 返回清楚的 502 错误 |
