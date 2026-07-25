# LeanCI

**Token-Efficient AI Debugging for Massive CI Logs**

LeanCI 是一个可录制演示的真实 CI 故障诊断 MVP：把长日志和少量相关文本文件作为不可信
证据，经本地 Paritok Proxy 与 hosted GPU 压缩，再由 DeepSeek
`deepseek-v4-flash` 返回严格结构化诊断。正式分析不可绕过 Paritok；链路或 `/stats`
证明不可用时会明确失败，不会回退到 Mock，也不会显示推测的 Token。

## 评委最快使用方式

准备三个 PowerShell 终端，全部从仓库根目录
`C:\Users\xin'xin\Desktop\LeanCI` 开始。

终端 1 — 启动 Paritok Proxy，并保持打开：

```powershell
cd "C:\Users\xin'xin\Desktop\LeanCI"
.\scripts\start_paritok.ps1
```

终端 2 — 启动单 worker FastAPI，并保持打开：

```powershell
cd "C:\Users\xin'xin\Desktop\LeanCI"
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app `
  --app-dir backend `
  --host 127.0.0.1 `
  --port 8000 `
  --workers 1
```

终端 3 — 启动前端，并保持打开：

```powershell
cd "C:\Users\xin'xin\Desktop\LeanCI\frontend"
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`：

1. 先确认 Formal route status 中 FastAPI、Paritok、Hosted GPU 均健康；
2. 点击明显的 `Python pytest failure`、`TypeScript build failure` 或
   `Docker build failure` Sample 卡片；
3. 日志和相关文件会一次载入，不克隆仓库，也不运行任何代码；
4. 点击 `Analyze failure`；
5. 成功后首先看到真实 `Tokens Saved`，再看到 Original/Compressed Tokens、压缩比例、
   DeepSeek 输入费用节省估算、Paritok 状态、模型和分析耗时；
6. 向下查看 Summary、Root Cause、Confidence、Evidence、Relevant Files、
   Recommended Changes、Patch、Verification Commands、Risks 和 Missing Information；
7. 可点击 `Copy Patch` 或 `Download Report`。命令和 Patch 始终只是文本。

若 hosted GPU 不可用，页面会显示具体公开错误并保持 fail closed；这不是成功，也不会出现
替代 Token 数字。页面不会展示 API Key。

## 三个固定案例

| Sample | 长日志大小 | 明确根因 | 预期相关文件 |
| --- | ---: | --- | --- |
| Python pytest failure | 69.5 KiB | 重试退避公式的运算优先级使第 4 次结果为 15，而不是上限 16 | `retry.py`、`test_retry.py` |
| TypeScript build failure | 73.9 KiB | `DEPLOY_REGION` 可能为 `undefined`，却被赋给必需的 `string` | `config.ts`、`deploy.ts` |
| Docker build failure | 40.1 KiB | `.dockerignore` 的 `*.json` 从构建上下文排除了包清单 | `Dockerfile`、`.dockerignore` |

每个 `examples/<id>/` 包含 `ci.log`、少量相关文本文件和 `ground_truth.json`。Ground truth
不会提交给模型。输入固定，因此可重复运行；输出必须通过真实 Paritok `/stats` 证明。

## 固定正式链路

```text
React
  → FastAPI POST /api/analyze
    → local /health + hosted /test + /stats before
    → http://127.0.0.1:8080/v1
      → Paritok Proxy
        → Paritok hosted GPU compression
        → https://api.deepseek.com/chat/completions
          → deepseek-v4-flash
    → /stats after + hosted /test
    → strict stats delta and request-count proof
```

- 正式 `/api/analyze` 不接受 Provider、模型、URL 或执行模式参数；
- Paritok、hosted GPU 或 stats 不可用时返回安全 503；
- DeepSeek JSON 空内容或无效 Schema 最多修复一次，修复仍经过 Paritok；
- 分析期间使用进程内锁，Uvicorn 必须保持一个 worker；
- 日志、文件、模型 Patch 和命令都不会被服务器执行。

完整信任边界见 [架构设计](docs/ARCHITECTURE.md)。

## 安全输入限制

前后端实施相同的体验校验，FastAPI 是最终安全边界：

| 项目 | 限制 |
| --- | ---: |
| 整个 HTTP 请求体 | 4 MiB，包含无 `Content-Length` 的分块请求 |
| CI 日志 | 2 MiB UTF-8 |
| 文件数量 | 最多 5 |
| 单文件 | 256 KiB UTF-8 |
| 文件合计 | 1 MiB |

服务端会：

- 清理允许但不规范的文件名；
- 拒绝 `/`、`\`、盘符、路径穿越、重复名称和 Windows 保留名称；
- 只允许源代码、配置、日志和文档文本扩展名；
- 拒绝 ZIP/其他压缩包、Shell/PowerShell、可执行文件、NUL、二进制、无效 UTF-8 和
  不允许的控制字符；
- 只在内存中处理内容，不接受本机路径或用户 URL；
- 用固定 Sample ID 读取仓库资产，不提供任意文件读取接口。

## 安装与本机配置

前置条件：Python 3.11+、Node.js 20.19+/22.12+ 或兼容新版本、Windows PowerShell。

```powershell
cd "C:\Users\xin'xin\Desktop\LeanCI"
.\backend\.venv\Scripts\python.exe -m pip install "paritok[proxy]==1.2.7"
.\backend\.venv\Scripts\python.exe -m pip install --requirement backend\requirements-dev.txt

cd frontend
npm ci
cd ..
```

已有 `.env` 时不要覆盖：

```powershell
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item ".env.example" ".env"
}
```

只在被 Git 忽略的本机 `.env` 中填写 Key。不要把真实值粘贴到终端输出、聊天、测试、
文档、截图、`paritok.yaml` 或 Git：

```dotenv
PARITOK_API_KEY=<仅在本机填写>
DEEPSEEK_API_KEY=<仅在本机填写>
LLM_PROVIDER=paritok
DEEPSEEK_MODEL=deepseek-v4-flash
PRICING_SNAPSHOT_DATE=2026-07-26
```

固定 URL 和完整非敏感环境示例见 [.env.example](.env.example)。

## 健康检查

```powershell
Invoke-RestMethod "http://127.0.0.1:8080/health"
Invoke-RestMethod "http://127.0.0.1:8080/stats"
.\backend\.venv\Scripts\python.exe scripts\test_paritok_connection.py
Invoke-RestMethod "http://127.0.0.1:8000/api/health"
```

本地 Proxy `/health=ok` 只代表代理进程存在；必须同时满足 hosted GPU 可用，正式分析才会
发送。`scripts/start_paritok.ps1` 也会在监听 8080 前执行认证 hosted 预检；预检失败时
代理不会启动，避免 Paritok 1.2.7 自动退回未压缩透传。

## 真实三案例采集与录屏状态

下面三条命令只接受固定 Sample，每条最多等待约 110 秒并执行一次真实
Paritok/DeepSeek 分析，会产生费用：

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample docker-build
```

每次成功必须满足：

- `original_tokens > 5000`；
- API 结果和脚本外层 `/stats` before/after 差值完全一致；
- 模型为 `deepseek-v4-flash`；
- 至少识别一个 ground-truth 相关文件；
- `examples/<id>/demo_result.json` 保存真实结果、脱敏 stats 快照和截图 URL。

不带 `--confirm-cost` 时不会发送请求。采集成功后可直接打开以下录屏状态；页面会清楚标注
这是已保存的真实运行，点击 Analyze 可生成新的 stats：

```text
http://127.0.0.1:5173/?capture=python-pytest
http://127.0.0.1:5173/?capture=typescript-build
http://127.0.0.1:5173/?capture=docker-build
```

2026-07-26 已通过正式链路完成三次真实采集。下表全部是各请求 `/stats` 前后差值，不是
Mock 或字符估算：

| Sample | Original | Compressed | Saved | 节省率 | 输入费用节省估算 | 分析耗时 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Python pytest | 23,906 | 332 | 23,574 | 98.61% | $0.00330036 | 5,168 ms |
| TypeScript build | 20,542 | 847 | 19,695 | 95.88% | $0.00275730 | 4,674 ms |
| Docker build | 8,325 | 117 | 8,208 | 98.59% | $0.00114912 | 4,574 ms |

三次均为 `proxy_requests=1`、模型 `deepseek-v4-flash`、价格快照
`2026-07-26`，并通过必需相关文件和修复关键词校验。可直接查看
[Python 结果截图](artifacts/screenshots/python-pytest-result.png)、
[TypeScript 结果截图](artifacts/screenshots/typescript-build-result.png) 和
[Docker 结果截图](artifacts/screenshots/docker-build-result.png)。

## Token 和费用口径

所有 Token 指标只来自同一锁内、本次请求前后 Paritok `/stats` 累计计数差值：

```text
original_tokens   = after.input_tokens_original - before.input_tokens_original
compressed_tokens = after.input_tokens_compressed - before.input_tokens_compressed
saved_tokens      = after.tokens_saved - before.tokens_saved
compression_ratio = compressed_tokens / original_tokens
```

`/stats.total_requests` 差值必须等于 Provider 实际请求次数，否则结果被丢弃。LeanCI 不用
字符数、DeepSeek usage 或模型正文补造 Token。

Paritok 自带的 `estimated_cost_saved_usd` 被排除。LeanCI 使用 2026-07-26 重新核验的
DeepSeek cache-miss 输入价格估算：

```text
estimated_input_cost_saved_usd =
  saved_tokens × 0.14 / 1,000,000
```

金额是配置估算，不是实际账单。

## API

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| `GET` | `/api/health` | 检查本地 Proxy 与 hosted GPU，不调用 DeepSeek |
| `GET` | `/api/config-status` | 只返回 Key 是否配置、Provider 和模型，不返回 Key |
| `GET` | `/api/samples` | 固定 Sample 元数据 |
| `GET` | `/api/samples/{id}` | 固定日志与相关文本文件 |
| `GET` | `/api/captures/{id}` | 保存的真实运行状态；不存在时 404 |
| `POST` | `/api/analyze` | 唯一正式分析入口 |

请求示例：

```json
{
  "log_text": "CI failure text",
  "files": [
    {
      "name": "config.ts",
      "content": "export const region = process.env.DEPLOY_REGION"
    }
  ]
}
```

错误响应只包含稳定错误码、公开消息和 request ID。页面不会只显示
`Internal Server Error`，也不会暴露环境变量、请求头、密钥、上游正文、堆栈或绝对路径。

## 质量检查

```powershell
cd "C:\Users\xin'xin\Desktop\LeanCI"
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

阶段四最近结果：后端 `92 passed, 2 skipped`；前端 `20 passed`；Ruff、格式、pip check、
lint、TypeScript strict 和 Vite 生产构建通过。两个条件集成测试只有显式设置真实集成环境
变量时才运行。

## 文档

- [项目计划](PROJECT_PLAN.md)
- [任务清单](TASKS.md)
- [固定演示案例](examples/README.md)
- [架构设计](docs/ARCHITECTURE.md)
- [Windows Paritok 设置](docs/PARITOK_SETUP_WINDOWS.md)
- [Paritok 验证](docs/PARITOK_VERIFICATION.md)
- [人工操作清单](docs/MANUAL_ACTIONS.md)
- [Agent 工作规范](AGENTS.md)

## License

[Apache License 2.0](LICENSE)
