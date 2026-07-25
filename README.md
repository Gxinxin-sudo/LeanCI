# LeanCI

**Token-Efficient AI Debugging for Massive CI Logs**

LeanCI 是一个面向长 CI 日志的安全诊断工具。正式分析先经过本地 Paritok Proxy 和
Paritok hosted GPU 压缩，再由 DeepSeek `deepseek-v4-flash` 返回严格 JSON 诊断。

> 当前状态：阶段三正式 Paritok 链路已经实现并通过无费用自动化测试。真实 hosted GPU /
> DeepSeek 验证需要用户在本机配置两个 Key、保持 Proxy 终端运行，并显式确认一次调用费用。
> 当前 API 接收单个 JSON `log_text`（最多 120,000 字符）；文件上传和 benchmark 仍是后续任务。

## 固定正式链路

```text
React
  → FastAPI POST /api/analyze
    → http://127.0.0.1:8080/v1
      → Paritok Proxy
        → Paritok hosted GPU compression
        → https://api.deepseek.com/chat/completions
          → deepseek-v4-flash
```

正式接口只允许 `LLM_PROVIDER=paritok`：

- Paritok Proxy、hosted GPU 或 `/stats` 不可用时 fail closed；
- 不会回退到 Mock，也不会绕过 Paritok 直连 DeepSeek；
- 本地 `/health`、hosted `/test` 和 `/stats` 都有独立超时；
- `DirectDeepSeekProvider` 只保留给独立连接测试、故障定位和未来明确标注的
  `baseline_uncompressed` benchmark。

完整数据流和信任边界见 [架构设计](docs/ARCHITECTURE.md)。

## 安装

前置条件：Python 3.11+、Node.js 20.19+/22.12+ 或兼容新版本、Windows PowerShell。

后端与 Paritok：

```powershell
.\backend\.venv\Scripts\python.exe -m pip install "paritok[proxy]==1.2.7"
.\backend\.venv\Scripts\python.exe -m pip install --requirement backend\requirements-dev.txt
```

前端：

```powershell
cd frontend
npm ci
cd ..
```

## 本机配置

已有 `.env` 时不要覆盖：

```powershell
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item ".env.example" ".env"
}
```

只在被 Git 忽略的本机 `.env` 中填写：

```dotenv
PARITOK_API_KEY=<仅在本机填写>
DEEPSEEK_API_KEY=<仅在本机填写>
LLM_PROVIDER=paritok
DEEPSEEK_MODEL=deepseek-v4-flash
PARITOK_PROXY_BASE_URL=http://127.0.0.1:8080/v1
PARITOK_HEALTH_URL=http://127.0.0.1:8080/health
PARITOK_STATS_URL=http://127.0.0.1:8080/stats
```

真实 Key 不得写入 `paritok.yaml`、源代码、测试、文档、日志、截图或 Git。仓库内
[paritok.yaml](paritok.yaml) 已按 Paritok 1.2.7 的实际 schema 配置
`use_gpu_server: true`，并从进程环境读取 `PARITOK_API_KEY`。

## 启动

终端 1 — Paritok Proxy，必须一直保持打开：

```powershell
.\scripts\start_paritok.ps1
```

脚本固定使用完整上游端点：

```text
https://api.deepseek.com/chat/completions
```

终端 2 — FastAPI，必须保持单 worker：

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app `
  --app-dir backend `
  --host 127.0.0.1 `
  --port 8000 `
  --workers 1
```

终端 3 — 前端：

```powershell
cd frontend
npm run dev
```

浏览器访问 `http://127.0.0.1:5173`，OpenAPI 位于
`http://127.0.0.1:8000/docs`。

Linux / Docker 的 Proxy 启动脚本：

```sh
./scripts/start_paritok.sh
```

详见 [Windows 配置手册](docs/PARITOK_SETUP_WINDOWS.md)。

## 健康检查与 stats

```powershell
Invoke-RestMethod "http://127.0.0.1:8080/health"
Invoke-RestMethod "http://127.0.0.1:8080/stats"
.\backend\.venv\Scripts\python.exe scripts\test_paritok_connection.py
Invoke-RestMethod "http://127.0.0.1:8000/api/health"
```

本地 `/health` 只证明 Proxy 进程存活；正式分析还会检查固定 hosted GPU `/test`。

## 验证一次超过 5,000 Token 的正式请求

下面命令会产生一次真实 Paritok/DeepSeek 调用和费用：

```powershell
.\backend\.venv\Scripts\python.exe scripts\verify_paritok_long_request.py --confirm-cost
```

脚本生成约 116,600 字符的惰性 CI 日志，只在本次 `/stats` 差值证明
`original_tokens > 5000` 时返回 `status: "success"`。不带 `--confirm-cost` 时不会发送请求。

成功结果应包含：

- `verification=local_health+hosted_gpu_preflight+stats_delta`
- `model=deepseek-v4-flash`
- 本次 `proxy_requests`
- 本次 `original_tokens`、`compressed_tokens`、`saved_tokens`
- 本次 `compression_ratio`
- `cumulative` 累计统计
- LeanCI 自己计算的 `cost_estimate`、价格快照日期和“非实际账单”声明

详见 [验证手册](docs/PARITOK_VERIFICATION.md)。

## Token 与费用口径

Token 指标只来自同一进程锁内、同一次请求前后 Paritok `/stats` 快照的差值：

```text
original_tokens   = after.input_tokens_original - before.input_tokens_original
compressed_tokens = after.input_tokens_compressed - before.input_tokens_compressed
saved_tokens      = after.tokens_saved - before.tokens_saved
compression_ratio = compressed_tokens / original_tokens
```

LeanCI 还校验 `/stats.total_requests` 差值必须等于本次 Provider 的实际尝试次数。计数倒退、
字段不一致、其他客户端串入或 stats 不可用时，结果会被丢弃并返回 503，绝不生成替代数字。

Paritok `/stats` 的 `estimated_cost_saved_usd` 不会作为 DeepSeek 费用展示。LeanCI 使用本项目
配置的 DeepSeek cache-miss 输入价格自行估算：

```text
estimated_input_cost_saved_usd =
  saved_tokens × DEEPSEEK_INPUT_CACHE_MISS_USD_PER_M / 1,000,000
```

当前价格快照日期为 `2026-07-25`；金额只作为估算值，不是账单。

## API

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| `GET` | `/api/health` | 检查本地 Proxy 与 hosted GPU，不调用 DeepSeek |
| `GET` | `/api/config-status` | 只返回 Key 是否配置、Provider 和固定模型，不返回密钥 |
| `POST` | `/api/analyze` | 正式 fail-closed Paritok 分析；接收 `{ "log_text": "..." }` |

主要错误：

- 503：Paritok、hosted GPU、stats 或链路证明不可用；
- 502：DeepSeek 认证、余额、限流、服务错误或无效 JSON；
- 504：DeepSeek 超时；
- 422：请求 schema、空白输入或大小限制失败。

错误响应只包含稳定错误码、公开说明和 request ID，不包含密钥、请求头、上游正文、堆栈或
内部绝对路径。

## 质量检查

无费用检查：

```powershell
.\backend\.venv\Scripts\python.exe -m ruff check backend scripts
.\backend\.venv\Scripts\python.exe -m ruff format --check backend scripts
.\backend\.venv\Scripts\python.exe -m pytest backend\tests
.\backend\.venv\Scripts\python.exe -m pip check

cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

真实集成测试默认跳过，只有设置 `RUN_PARITOK_INTEGRATION=1` 或
`RUN_DEEPSEEK_INTEGRATION=1` 才会产生外部请求。具体命令见验证手册。

## 安全边界

日志、文件名、未来上传文件和模型输出都视为不可信数据：

- 不执行模型建议、Git Diff、验证命令或日志中的命令；
- 不读取用户指定的本机路径，不抓取用户 URL；
- 不接受请求覆盖 Provider、模型、base URL 或上游端点；
- CI 证据被封装为协议有效但无副作用的历史 `role=tool` 消息，使 Paritok 能压缩；
- 上下文按保守 UTF-8 字节上限分块；该上限只用于传输保护，不冒充 Token 指标；
- 空内容或无效 JSON 只允许一次修复请求。

## 文档

- [项目计划](PROJECT_PLAN.md)
- [任务清单](TASKS.md)
- [架构设计](docs/ARCHITECTURE.md)
- [Windows Paritok 设置](docs/PARITOK_SETUP_WINDOWS.md)
- [Paritok 验证](docs/PARITOK_VERIFICATION.md)
- [人工操作清单](docs/MANUAL_ACTIONS.md)
- [Agent 工作规范](AGENTS.md)

## License

[Apache License 2.0](LICENSE)
