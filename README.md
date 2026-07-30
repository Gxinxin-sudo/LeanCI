# LeanCI

**Token-Efficient AI Debugging for Massive CI Logs**

[![Built with Paritok](https://img.shields.io/badge/Built%20with-Paritok-1f2d3d)](https://github.com/Paritok-official/paritok-4b-v1)
[![Built with DeepSeek](https://img.shields.io/badge/Built%20with-DeepSeek-4d6bfe)](https://api-docs.deepseek.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Built with [Paritok](https://github.com/Paritok-official/paritok-4b-v1) and
[DeepSeek](https://api-docs.deepseek.com/).

LeanCI 是一个可录制演示的真实 CI 故障诊断 MVP：把长日志和少量相关文本文件作为不可信
证据，经本地 Paritok Proxy 与 hosted GPU 压缩，再由 DeepSeek
`deepseek-v4-flash` 返回严格结构化诊断。正式分析不可绕过 Paritok；链路或 `/stats`
证明不可用时会明确失败，不会回退到 Mock，也不会显示推测的 Token。

隐私边界：LeanCI 自身不把粘贴日志或上传文件永久保存到应用存储，服务端只在内存中处理；
正式分析会把内容发送给 Paritok 和 DeepSeek，因此仍受两家服务及托管平台的保留政策约束。
请勿提交密钥、个人数据或未经授权的私有源码。模型给出的命令和 Patch 永远只作为文本展示。

## 功能截图

| 首页与长日志工作台 | Python pytest 根因与 Token 证明 |
| --- | --- |
| [![LeanCI 首页](artifacts/screenshots/home.png)](artifacts/screenshots/home.png) | [![Python pytest 分析结果](artifacts/screenshots/python-pytest-result.png)](artifacts/screenshots/python-pytest-result.png) |
| [TypeScript build 结果](artifacts/screenshots/typescript-build-result.png) | [Docker build 结果](artifacts/screenshots/docker-build-result.png) |

移动端验收截图见
[500 px 布局](artifacts/screenshots/mobile-layout-500.png)。提交前需要录制或补拍的画面位置见
[截图清单](docs/submission/SCREENSHOT_CHECKLIST.md)。

## 评委最快使用方式

完成下方“从全新环境安装”后，准备三个 PowerShell 终端，全部从仓库根目录开始。

终端 1 — 启动 Paritok Proxy，并保持打开：

```powershell
.\scripts\start_paritok.ps1
```

终端 2 — 启动单 worker FastAPI，并保持打开：

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app `
  --app-dir backend `
  --host 127.0.0.1 `
  --port 8000 `
  --workers 1
```

终端 3 — 启动前端，并保持打开：

```powershell
cd frontend
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`：

1. 先确认 Formal route status 中 FastAPI、Paritok、Hosted GPU 均健康；
2. 点击任一固定 Sample，包括 pytest、TypeScript、Docker、依赖解析和 GitHub Actions
   环境失败；
3. 日志和相关文件会一次载入，不克隆仓库，也不运行任何代码；
4. 点击 `Analyze failure`；
5. 成功后首先看到真实 `Tokens Saved`，再看到 Original/Compressed Tokens、压缩比例、
   DeepSeek 输入费用节省估算、Paritok 状态、模型和分析耗时；
6. 向下查看 Summary、Root Cause、Confidence、Evidence、Relevant Files、
   Recommended Changes、Patch、Verification Commands、Risks 和 Missing Information；
7. 可点击 `Copy Patch` 或 `Download Report`。命令和 Patch 始终只是文本。

若 hosted GPU 不可用，页面会显示具体公开错误并保持 fail closed；这不是成功，也不会出现
替代 Token 数字。页面不会展示 API Key。

## 五个固定案例

| Sample | 长日志大小 | 明确根因 | 预期相关文件 |
| --- | ---: | --- | --- |
| Python pytest failure | 69.5 KiB | 重试退避公式的运算优先级使第 4 次结果为 15，而不是上限 16 | `retry.py`、`test_retry.py` |
| TypeScript build failure | 73.9 KiB | `DEPLOY_REGION` 可能为 `undefined`，却被赋给必需的 `string` | `config.ts`、`deploy.ts` |
| Docker build failure | 40.1 KiB | `.dockerignore` 的 `*.json` 从构建上下文排除了包清单 | `Dockerfile`、`.dockerignore` |
| Dependency resolution failure | 63.6 KiB | React 19 与只接受 React 18 的 peer dependency 冲突 | `package.json`、`package-lock.json` |
| GitHub Actions environment failure | 56.2 KiB | 仓库变量 `DEPLOY_ENVIRONMENT` 未设置，使 `DEPLOY_ENV` 为空 | `deploy.yml`、`validate_env.py` |

每个 `examples/<id>/` 包含 `ci.log`、少量相关文本文件和 `ground_truth.json`。Ground truth
不会提交给模型。输入固定，因此可重复运行；前三例另保留阶段四真实演示 capture，五例都
用于阶段五 Benchmark。

## 固定正式链路

```mermaid
flowchart LR
    U["Developer<br/>long CI log + text files"] --> R["React UI"]
    R -->|POST /api/analyze| A["FastAPI<br/>strict input + one active analysis"]
    A -->|health + /stats before| P["Local Paritok Proxy<br/>127.0.0.1:8080"]
    P --> G["Paritok hosted GPU<br/>context compression"]
    G --> D["DeepSeek API<br/>deepseek-v4-flash"]
    D --> G --> P --> A
    A -->|/stats after| V["Request-count proof<br/>verified Token delta"]
    V --> S["Strict Pydantic diagnosis<br/>root cause · evidence · patch"]
    S --> R
```

- 正式 `/api/analyze` 不接受 Provider、模型、URL 或执行模式参数；
- Paritok、hosted GPU 或 stats 不可用时返回安全 503；
- DeepSeek JSON 空内容或无效 Schema 最多修复一次，修复仍经过 Paritok；
- 分析期间使用进程内锁，Uvicorn 必须保持一个 worker；
- 同时只接受一个正式分析，额外请求立即返回可重试错误而不进入付费队列；
- 整体分析默认 110 秒超时；API 有内存速率限制、服务端请求 ID 和安全响应头；
- 浏览器来源必须匹配 `CORS_ALLOWED_ORIGINS` 的显式白名单，不支持通配符；
- 生产环境必须经 TLS/OIDC 可信网关认证；分析请求只有来自
  `TRUSTED_PROXY_CIDRS` 且携带网关注入身份时才会被 FastAPI 接受；
- 多实例限流和 UTC 日请求预算必须在网关/Redis 共享存储中原子执行，故障拒绝分析；
- 日志、文件、模型 Patch 和命令都不会被服务器执行。

完整信任边界见 [架构设计](docs/ARCHITECTURE.md) 和
[威胁模型](docs/THREAT_MODEL.md)。

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

## 从全新环境安装

前置条件：Git、Python 3.11+、Node.js 20.19+/22.12+ 或兼容新版本、Windows PowerShell。
Docker 运行只需要 Docker Desktop，不需要本机 Python/Node。以下命令从一个没有
`backend/.venv`、没有 `frontend/node_modules` 的新 clone 开始：

```powershell
git clone https://github.com/Gxinxin-sudo/LeanCI.git
cd LeanCI

python -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install --upgrade pip
.\backend\.venv\Scripts\python.exe -m pip install --requirement backend\requirements-dev.txt

Push-Location frontend
npm ci
Pop-Location
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

开发期如需关联 DeepSeek 空内容/无效 JSON，可显式设置
`SAVE_INVALID_RESPONSE_DEBUG=true`。该功能只在 `runtime/` 内保存错误分类、finish reason、
长度和正文 SHA-256，不保存模型正文、日志或上传内容；生产配置会拒绝启用。

### 环境变量说明

| 变量 | 必需 | 作用与安全边界 |
| --- | --- | --- |
| `PARITOK_API_KEY` | 正式分析必需 | 仅放在本机 `.env` 或托管平台运行时 Secret |
| `DEEPSEEK_API_KEY` | 正式分析必需 | 只传给本地 Paritok Proxy 的固定 DeepSeek 上游 |
| `LLM_PROVIDER` | 是 | 必须为 `paritok`；正式端点拒绝 `mock` 与 `direct` |
| `DEEPSEEK_MODEL` | 是 | 固定为 `deepseek-v4-flash` |
| `CORS_ALLOWED_ORIGINS` | 是 | 逗号分隔的精确浏览器 Origin；生产不允许 `*` |
| `ENVIRONMENT` | 是 | 本地为 `development`；公网必须通过生产配置校验 |
| `TRUSTED_PROXY_CIDRS` | 生产必需 | 仅信任 TLS/OIDC 网关网络，不接受全网 CIDR |
| `PROXY_AUTH_SHARED_SECRET` | 生产必需 | 仅供网关到 FastAPI，绝不能进入浏览器 |
| `DISTRIBUTED_RATE_LIMIT_REQUIRED` | 生产必需 | 公网多实例必须使用共享限流/预算层 |
| `DAILY_ANALYSIS_REQUEST_BUDGET` | 生产必需 | 限制每日付费分析数，`0` 表示未配置 |
| `PRICING_SNAPSHOT_DATE` | 是 | 标识费用估算价格快照；不是账单日期 |

所有固定 URL、超时、输入限制、价格和网关变量见 [.env.example](.env.example)。正式
`POST /api/analyze` 不允许请求方覆盖 Provider、模型、上游 URL 或执行模式。

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

## 公平、可复现的 Benchmark

只读前端页：`http://127.0.0.1:5173/?view=benchmark`。浏览器只读取已保存工件，不提供
付费按钮。

每例固定执行 A `baseline_uncompressed`，再执行 B `paritok`。两路保持相同模型
`deepseek-v4-flash`、首轮消息、系统/用户提示、案例内容、`max_tokens=4096`、thinking
disabled 和 JSON object 配置，并保存相同的 `initial_messages_sha256`。正式
`/api/analyze` 没有 baseline 或 mode 开关。

在 Proxy 与 hosted GPU 均健康后，从仓库根目录逐例运行：

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case docker-build
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case dependency-resolution
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case github-actions-environment
```

每条命令预期 2 次模型请求；每路最多一次 JSON 修复，因此每条上限 4 次；网络重试为 0。
完整五例预期 10 次，全部发生 JSON 修复时硬上限 20 次。不带 `--confirm-cost` 时请求数为
0。一次只跑一个案例，既控制 120 秒命令时限，也便于在余额或上游异常时停止。

输出：

- `benchmarks/results.json`：包含模型分析、确定性评分和人工复核字段；
- `benchmarks/results.csv`：包含要求的平面列；
- `benchmarks/report.md`：完整结果、失败说明、费用口径和复现命令。

固定评分不使用 LLM judge：根因 40、证据 20、相关文件 15、修复方向 15、严格 JSON 10。
失败行和正常跳过行都不删除。Token 平均值只包含状态为 `compressed` 的行；质量变化只
包含 Baseline 与 Paritok 都有严格结构化分析的有效配对，并明确显示配对样本数。

2026-07-26 最终受控验收在 hosted GPU 预检成功后，五例严格按 Baseline → Paritok 顺序
各运行一次。实际发送 10 次模型请求，JSON 修复 0、网络重试 0、超时 0。正式工件保留
全部 10 行：5 个 Baseline 完成；Python 和 Docker 为 `compressed`；TypeScript、依赖解析
和 GitHub Actions 为 `skipped_low_yield`；没有 unavailable 或 upstream_failed。五个固定
Baseline 的实际 prompt usage 均超过 5,000 Token，不再对 Paritok stats delta 施加 5,000
门槛。

当前仅可陈述：在 **2 个 compressed 行**中，平均 Token 节省率为 `85.53%`
（Python `10,469→254`，Docker `543→144`）。质量比较有 5 个有效配对，Baseline 平均
`73.00/100`、Paritok 平均 `54.00/100`，变化 `-19.00` 分。**当前结果不支持“所有日志都会
压缩”“五例平均节省 85.53%”“压缩保持质量”“生产稳定可用”或“降低实际账单”等表述。**

Paritok 官方随后确认：hosted `/stats` 的 `0→0` 表示该请求被 `SKIPPED/passthrough`，
不是缓存命中或 stats Bug；跳过请求只增加 `total_requests`。一次不调用 DeepSeek 的官方
trace 诊断进一步确认消息仍是匹配的 OpenAI tool history，三个原 `0→0` 案例的全部工具块
均以 `below_refusal_threshold` 跳过。这是 Paritok 的预期低收益保护，不是 GPU 不可用、
缓存命中、stats Bug 或正式消息格式错误。Benchmark 将这三个固定、trace 已确认的行标为
`skipped_low_yield`，Token 节省与压缩率为“不适用”；若透传后仍得到有效结构化分析，则
照常按 ground truth 评分。未知输入的正式 FastAPI 仍对无法证明压缩的 `0→0` fail closed。
trace 默认关闭，文件仅保留在 Git 忽略的本地 runtime 目录。

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
2026-07-27 发布复核再次检查了
[DeepSeek 官方价格页](https://api-docs.deepseek.com/quick_start/pricing)，上述
cache hit `$0.0028/M`、cache miss `$0.14/M`、output `$0.28/M` 未变化；冻结工件仍保留
其实际运行时的 `2026-07-26` 快照日期。

## API

| 方法 | 路径 | 行为 |
| --- | --- | --- |
| `GET` | `/api/health` | 检查本地 Proxy 与 hosted GPU，不调用 DeepSeek |
| `GET` | `/api/config-status` | 只返回 Key 是否配置、Provider 和模型，不返回 Key |
| `GET` | `/api/samples` | 固定 Sample 元数据 |
| `GET` | `/api/samples/{id}` | 固定日志与相关文本文件 |
| `GET` | `/api/captures/{id}` | 保存的真实运行状态；不存在时 404 |
| `GET` | `/api/benchmark/results` | 严格读取固定 Benchmark 工件；不触发模型请求 |
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
访问日志只包含 request ID、方法、固定路由标签、状态和耗时，不记录 Header、请求体、查询串、
原始路径或上传内容。

## Docker

Docker 单容器使用编译后的前端、FastAPI 和仅监听容器回环地址的 Paritok Proxy。镜像以
非 root 用户运行，由固定 Python PID 1 监管两个子进程，只公开 FastAPI 的平台 `PORT`。

```powershell
docker build --progress=plain --tag leanci:phase7 .
$env:LEANCI_DOCKER_CLI = (Get-Command docker).Source
.\backend\.venv\Scripts\python.exe scripts\docker_smoke.py
```

镜像先从 PyTorch 官方 CPU 索引固定安装 `torch==2.13.0+cpu`，再解析完整
`paritok[proxy]==1.2.7`，避免 CPU-only Proxy 镜像下载 526.6 MB accelerator wheel。
CPU wheel 本身约 191.8 MB，首次构建在慢速网络下仍可能超过两分钟。冒烟脚本使用测试专用
假凭据，不读取 `.env`、不调用 DeepSeek；它验证无密钥失败、静态站点/API、联合
`/api/health`、内部 `/stats`、镜像密钥边界和任一子进程退出时的容器联动失败。完整构建、
Compose 与故障排查步骤见
[Docker 构建与验证](docs/DOCKER.md)。

三个固定样例的真实容器链路验证会产生费用；一次只运行一例且必须显式确认：

```powershell
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample python-pytest
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample typescript-build
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample docker-build
```

每次成功都必须证明联合健康、本次 `/stats` 差值与 API Token 证明一致、固定模型和容器
SIGTERM 后退出码 0；脚本不打印 `.env` 或 Key。固定案例若被 Paritok 以
`below_refusal_threshold` 低收益跳过，则只有在 HTTP 503
`PARITOK_COMPRESSION_SKIPPED`、内部 stats 精确为 `1/0/0/0`、固定模型和退出码 0 同时
成立时，脚本才以 `analysis_outcome=skipped_low_yield` 通过；不会伪造 Token 或冒充压缩。

2026-07-27 本地 phase7 验收结果：

| Sample | Outcome | Stats delta（requests/original/compressed/saved） | Exit |
| --- | --- | --- | ---: |
| Python pytest | `compressed` | `1 / 10,469 / 254 / 10,215` | 0 |
| TypeScript build | `skipped_low_yield` | `1 / 0 / 0 / 0` | 0 |
| Docker build | `compressed` | `1 / 543 / 144 / 399` | 0 |

镜像 digest 为 `sha256:6825cf7a…f763`，大小 432,331,158 bytes；无费用 smoke 顶层
`status=passed`，没有调用 DeepSeek。三例均通过联合健康检查并固定使用
`deepseek-v4-flash`。

## Railway 部署

根目录 `railway.json` 固定使用多阶段 `Dockerfile` 和 `/api/health`。Railway 只部署一个
服务：React 由 FastAPI 同域托管，FastAPI 监听 `0.0.0.0:$PORT`，Paritok 只监听容器内部
`127.0.0.1:8080`。Key 只作为 Railway 运行时 Secret/Sealed Variables 注入，不能作为
build arg，也不能上传 `.env`。

具体的 GitHub 连接、仓库/服务/Dockerfile 选择、变量分类、公开域名、日志、健康诊断、三例
验收和回滚步骤见 [Railway 单容器部署手册](docs/DEPLOY_RAILWAY.md)；平台不可用时见
[Render 备选部署手册](docs/DEPLOY_RENDER_FALLBACK.md)。

安全限制：一个直接公开的 Railway/Render 服务本身不等于项目要求的 OIDC 认证网关和
Redis/网关分布式预算。生产模式会拒绝没有可信网关注入身份的 `/api/analyze`。不得通过
公开 development 模式、全网可信 CIDR 或浏览器携带共享 Secret 绕过；完整边界见
[生产安全部署手册](docs/PRODUCTION_DEPLOYMENT.md)。

## 安全说明

- 正式分析固定经过 FastAPI → 本地 Paritok Proxy → Paritok hosted GPU → DeepSeek；
  Paritok、hosted 健康或 stats 证明缺失时 fail closed。
- Token 只取同一分析锁内的 `/stats` before/after 差值，并校验请求数；不使用字符估算、
  DeepSeek usage 或模型生成的数字。
- Mock 只存在于隔离测试和浏览器验收中；正式 Provider 工厂会拒绝 Mock 与 Direct。
- 上传只接受受限 UTF-8 文本，服务端执行路径、大小、扩展名和控制字符校验；应用不会运行
  日志、Patch 或模型建议的命令。
- `.env`、Key、请求头、模型正文和上传内容不写入仓库或访问日志；错误响应不暴露堆栈和
  内部绝对路径。
- 公网生产必须位于 TLS/OIDC 网关后，并有共享限流、UTC 日预算和密钥轮换。单个直接公开的
  Railway/Render 容器不满足这一边界。

完整政策见 [SECURITY.md](SECURITY.md) 与 [威胁模型](docs/THREAT_MODEL.md)。

## 已知限制

- 当前没有可公开访问的 live Demo 域名；已验证的 Railway 实例是无公网域名的内部部署，
  不能描述为生产或公开 Demo。Devpost Project URL 可先使用公开仓库与本 README。
- Paritok 会跳过它判断为低收益的块；冻结 Benchmark 中 5 个案例有 3 个
  `skipped_low_yield`，这些行没有 Token 节省率。
- 冻结 Benchmark 只在 2 个实际压缩行上得到 `85.53%` 平均 Token 节省，但 5 个有效质量
  配对的确定性评分变化为 `-19.00` 分；结果不支持普遍质量保持声明。
- `/stats` 是单进程累计计数，因此当前固定一个 Uvicorn worker、一个活跃分析；横向扩容
  前必须把归因锁和限流迁移到共享基础设施。
- LeanCI 不克隆仓库、不抓取用户 URL、不执行代码，也不自动应用 Patch；诊断必须由人复核。
- Token 与美元值是一次受控运行和配置价格的证据，不代表未来输入、生产可靠性或实际账单。

## 演示案例

推荐三分钟视频使用 `python-pytest`：它有 69.5 KiB 长日志、清晰的退避公式根因、日志证据、
相关文件与 Patch，同时保存了真实 `23,906 → 332` Token capture。另两个一键 Sample
展示 TypeScript `undefined` 类型错误与 Docker `.dockerignore` 构建上下文错误。三份
capture 均来自 2026-07-26 正式链路，不是 Mock；重新点击 Analyze 会产生新的真实请求和费用。

完整五例输入、ground truth 和可评审输出见 [examples/](examples/README.md)，录屏顺序见
[RECORDING_SHOT_LIST.md](docs/submission/RECORDING_SHOT_LIST.md)。

## 技术决策

- 用 Paritok 本地 OpenAI-compatible Proxy 保持应用集成简单，同时强制 hosted GPU 预检和
  stats 证明，避免静默未压缩透传。
- 用严格 Pydantic Schema 接收 DeepSeek JSON；空内容或无效 JSON 只允许一次修复请求。
- Baseline 放在独立 benchmark 服务，正式端点不提供 mode 开关，避免绕过 Paritok。
- 用固定案例、首轮消息 SHA-256 和确定性 ground-truth rubric 做可复现比较，不使用
  LLM-as-a-judge。
- Docker 单容器托管编译前端、FastAPI 与 loopback Paritok Proxy；非 root 运行，并由
  Python PID 1 联动监管子进程。

更完整的权衡与数据流见 [架构设计](docs/ARCHITECTURE.md)。

## 未来计划

1. 在公网入口前加入可审计的 TLS/OIDC 网关、Redis 原子限流与 UTC 日预算，再发布 live Demo。
2. 扩大经过人工复核的 CI 故障集，并针对低收益跳过与质量下降迭代分块和提示策略。
3. 将单进程 `/stats` 归因迁移为请求级遥测，使多实例扩容仍能证明每次 Token 差值。
4. 增加 GitHub App 的只读日志导入，但继续禁止自动执行代码、命令或 Patch。
5. 提交结构化 Paritok 反馈与可复现 issue，跟踪 skip 原因、请求级 stats 和生产可观测性。

## 质量检查

```powershell
cd "C:\Users\xin'xin\Desktop\LeanCI"
.\backend\.venv\Scripts\python.exe -m ruff check backend scripts
.\backend\.venv\Scripts\python.exe -m ruff format --check backend scripts
.\backend\.venv\Scripts\python.exe -m pytest backend\tests
.\backend\.venv\Scripts\python.exe -m pip check
.\backend\.venv\Scripts\python.exe scripts\scan_secrets.py
.\backend\.venv\Scripts\python.exe -m pip_audit -r backend\requirements.txt
.\backend\.venv\Scripts\python.exe -m pip_audit -r backend\requirements-container.txt

cd frontend
npm audit --omit=dev --audit-level=high
npm audit --audit-level=high
npm run lint
npm run typecheck
npm test
npm run build
```

阶段六安全与产品验收已增加输入/异常/日志/CORS/限流/并发/超时/提示注入/文本执行边界回归，
并用隔离 Mock 后端检查桌面、390 px 移动端、复制 Patch 和报告下载；该验收不会发送正式模型
请求。阶段五真实 Token/Benchmark 工件保持冻结。最新精确测试计数以当前 Git Commit 和 CI
输出为准。两个条件集成测试只有显式设置真实集成环境变量时才运行；没有单独费用授权时不得
自动发送模型请求。

## 文档

- [项目计划](PROJECT_PLAN.md)
- [任务清单](TASKS.md)
- [贡献指南](CONTRIBUTING.md)
- [固定演示案例](examples/README.md)
- [Benchmark 说明](benchmarks/README.md)
- [固定 Benchmark 报告](benchmarks/report.md)
- [架构设计](docs/ARCHITECTURE.md)
- [安全政策](SECURITY.md)
- [威胁模型](docs/THREAT_MODEL.md)
- [Docker 构建与验证](docs/DOCKER.md)
- [Railway 单容器部署](docs/DEPLOY_RAILWAY.md)
- [Render 备选部署](docs/DEPLOY_RENDER_FALLBACK.md)
- [生产安全部署手册](docs/PRODUCTION_DEPLOYMENT.md)
- [Windows Paritok 设置](docs/PARITOK_SETUP_WINDOWS.md)
- [Paritok 验证](docs/PARITOK_VERIFICATION.md)
- [人工操作清单](docs/MANUAL_ACTIONS.md)
- [Devpost 发布材料](docs/submission/FINAL_SUBMISSION_CHECKLIST.md)
- [Agent 工作规范](AGENTS.md)

## License

[Apache License 2.0](LICENSE)
