# LeanCI

**Token-Efficient AI Debugging for Massive CI Logs**

LeanCI 是一个面向长 CI 日志的安全诊断工具。它计划支持 GitHub Actions、pytest、TypeScript Build 和 Docker Build 等日志，以及最多 5 个相关文本文件。正式分析会先通过 Paritok hosted GPU 压缩上下文，再由 DeepSeek 返回严格结构化的根因分析与修复建议。

> 当前状态：阶段二的 DeepSeek 独立连接能力已完成，但没有接入正式分析路径。React 与
> FastAPI 仍只返回确定性 Mock；只有人工运行 `scripts/test_deepseek_connection.py`
> 才会直连 DeepSeek。页面继续显示 `Demo data — Paritok not connected`，Token 指标保持为空。

## 为什么做 LeanCI

CI 失败日志常常包含大量重复安装输出、进度信息和无关上下文。把完整日志直接发送给模型会增加输入 Token、延迟和费用，也可能稀释真正的错误证据。LeanCI 的目标是保留诊断所需的错误、路径和代码上下文，同时透明展示压缩前后 Token。

项目参加 [Build with Paritok: The Token-Efficiency Hackathon](https://build-with-paritok.devpost.com/)。

## 计划功能

- 粘贴最长 2 MiB 的 CI 日志；
- 上传最多 5 个经过严格白名单验证的文本文件；
- GitHub Actions/pytest、TypeScript Build、Docker Build 三个示例；
- Paritok 本地代理与 hosted GPU 健康检查；
- DeepSeek `deepseek-v4-flash` 严格 JSON 分析；
- 问题摘要、根因、可信度、日志证据和相关文件；
- 修改建议、Git Diff、验证命令、风险和缺失信息；
- 本次请求独立的原始/压缩/节省 Token 与压缩率；
- 使用配置价格计算并带快照日期的费用节省估算；
- 用户显式触发的压缩与未压缩 baseline Benchmark；
- 单容器 Docker 部署。

## 固定调用链

当前应用仍只运行本地 Mock 链：

```text
React → FastAPI → deterministic mock response
```

独立连接测试是隔离链路：

```text
scripts/test_deepseek_connection.py
  → DirectDeepSeekProvider（connection_test）
    → DeepSeek OpenAI-compatible API
```

正式集成完成后必须使用以下固定链：

```text
React
  → FastAPI
    → Paritok Proxy (http://127.0.0.1:8080/v1)
      → Paritok hosted GPU
      → DeepSeek (https://api.deepseek.com/chat/completions)
```

正式分析不会在 Paritok 不可用时偷偷直连 DeepSeek。`DirectDeepSeekProvider` 只能用于
本地连接测试、未压缩 benchmark baseline 和故障定位，不能通过 `LLM_PROVIDER` 选为应用模式。
Baseline 只存在于明确标注的 benchmark 路径。

## 技术栈

- 前端：React 19、TypeScript strict、Vite 8、Tailwind CSS 4、Vitest；
- 后端：Python 3.11+、FastAPI、Pydantic、pydantic-settings、官方 OpenAI Python SDK、pytest、ruff；
- AI：Paritok hosted GPU、DeepSeek `deepseek-v4-flash`；
- 部署：Docker 单容器，FastAPI 同时提供 API 和编译后的静态前端。

## 快速开始

### 前置条件

- Node.js `20.19+`、`22.12+` 或更高兼容版本；
- Python `3.11+`；
- PowerShell。

正式后端虚拟环境固定为仓库根目录下的 backend/.venv，并已用 Python 3.11.9 创建。
所有本地后端命令都应从仓库根目录直接调用
.\backend\.venv\Scripts\python.exe；不要依赖 PowerShell 激活状态或 Codex 自带的解释器。

### 安装后端

```powershell
.\backend\.venv\Scripts\python.exe -m pip install --requirement backend\requirements-dev.txt
```

### 安装前端

```powershell
cd frontend
npm ci
cd ..
```

### 启动后端

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

后端地址：

- API：`http://127.0.0.1:8000`
- OpenAPI：`http://127.0.0.1:8000/docs`

### 启动前端

另开一个 PowerShell：

```powershell
cd frontend
npm run dev
```

浏览器访问 `http://127.0.0.1:5173`。Vite 会把 `/api` 请求代理到本地 FastAPI。

依赖安装完成后，也可以在项目根目录运行 `.\scripts\dev.ps1`，分别打开前后端开发终端。

### 运行质量检查

```powershell
.\backend\.venv\Scripts\python.exe -m ruff check backend
.\backend\.venv\Scripts\python.exe -m pytest backend

cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

Mock 应用不需要 `.env` 或任何 API Key。只有运行独立连接测试时，才需要从 `.env.example`
复制本地 `.env`；真实 Key 只能写入被 Git 忽略的本机 `.env`，不要发到 Codex 聊天。

## 当前应用 API

| 方法 | 路径 | 当前行为 |
| --- | --- | --- |
| `GET` | `/api/health` | 返回 FastAPI 的 Demo 健康状态，不探测外部服务 |
| `GET` | `/api/config-status` | 只返回 DeepSeek/Paritok 配置是否存在的布尔值 |
| `POST` | `/api/analyze` | 接收 `{ "log_text": "..." }` 并返回确定性 Mock 结果 |

Mock 分析结果包含 `summary`、`root_cause`、`confidence`、`evidence`、
`relevant_files`、`recommended_changes`、`patch`、`verification_commands`、`risks`、
`missing_information` 和 `compression_stats`。`compression_stats` 中的 Token 数字全部为
`null`，不会伪造 Paritok 数据。

## DeepSeek 独立连接测试

### 1. 创建并保存 Key

在 [DeepSeek 开放平台 API Keys](https://platform.deepseek.com/api_keys) 创建 LeanCI 专用
Key。如果仓库根目录还没有 `.env`，才执行：

```powershell
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item ".env.example" ".env"
}
```

只在本机 `.env` 中填写（变量模板见 [.env.example](.env.example)）：

```dotenv
DEEPSEEK_API_KEY=<在本机填写，不要发送到聊天或提交到 Git>
```

保留以下非敏感配置：

```dotenv
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
LLM_PROVIDER=mock
```

### 2. 运行

从仓库根目录执行：

```powershell
.\backend\.venv\Scripts\python.exe scripts\test_deepseek_connection.py
```

成功时只输出一个 JSON 对象，字段为：

- `status`：`success`；
- `model`：`deepseek-v4-flash`；
- `usage`：DeepSeek 本次实际返回的 prompt、completion、total Token，以及可用时的缓存明细。

脚本不会输出模型正文、提示词、请求头或 API Key。没有 Key 时输出 `status=skipped`、
`usage=null` 并安全退出；失败时 `status` 为稳定错误码，`usage=null`。

### 3. 故障排查

| 状态 | 排查 |
| --- | --- |
| `DEEPSEEK_API_KEY_MISSING` / `skipped` | 确认仓库根目录 `.env` 存在，并只在本机填写 `DEEPSEEK_API_KEY` |
| `DEEPSEEK_AUTHENTICATION_FAILED`（401） | 在 DeepSeek API Keys 页面核对或重新创建 Key；认证失败不会自动重试 |
| `DEEPSEEK_INSUFFICIENT_BALANCE`（402） | 检查 DeepSeek 账户余额并充值 |
| `DEEPSEEK_RATE_LIMITED`（429） | 等待后重试，避免并发运行多个连接测试 |
| `DEEPSEEK_SERVER_ERROR`（500/503） | DeepSeek 暂时不可用；稍后重试 |
| `DEEPSEEK_TIMEOUT` | 检查网络、DNS、防火墙与 `DEEPSEEK_BASE_URL` |
| `LLM_OUTPUT_INVALID` | 上游连续两次未返回符合 Schema 的 JSON；保留错误码并稍后重试 |
| `INVALID_CONFIGURATION` | 对照 `.env.example` 恢复固定 URL、模型名和数值配置 |

连接和可重试上游错误最多额外重试两次；SDK 内置重试被关闭，401/402 不重试。结构化
输出为空、无效 JSON 或缺字段时只允许一次修复请求。

## 配置原则

- 默认模型固定为 `deepseek-v4-flash`；
- 当前 `LLM_PROVIDER=mock`；正式分析就绪后只切换为 `paritok`；
- OpenAI SDK 正式 base URL 固定为本地 Paritok Proxy；
- Paritok 配置使用 `use_gpu_server: true`；
- `DEEPSEEK_API_KEY` 和 `PARITOK_API_KEY` 只来自环境变量；
- 价格通过环境变量配置，并必须带 `PRICING_SNAPSHOT_DATE`；
- 不信任 Paritok 针对未知模型返回的美元估算。

完整非敏感变量见 [.env.example](.env.example)。

Provider 边界包含：

- `MockProvider`：当前应用和无外部费用测试；
- `DirectDeepSeekProvider`：仅连接测试、benchmark baseline、故障定位；
- `ParitokDeepSeekProvider`：未来正式应用的唯一 DeepSeek Provider。

Provider 工厂没有 Direct 模式，也没有从 Paritok 到 Direct 的自动回退。

## Token 与费用口径

- 当前应用没有 Paritok 数据，Token 面板只显示占位符；
- Token 数据来自每次分析前后 Paritok `/stats` 的差值；
- 原始和压缩 Token 指 Paritok 实际介入的上下文范围，不冒充整个供应商账单；
- 美元金额按配置的 DeepSeek 价格估算；
- UI 会显示价格快照日期；
- 估算金额不是实际账单金额；
- Token 节省是主要指标，费用估算仅作辅助。

## Benchmark

MVP 将提供三个有预期根因的内置示例。用户明确确认费用后，LeanCI 会顺序运行：

1. 经过 Paritok 的正式压缩路径；
2. 明确标注为 `baseline_uncompressed` 的 DeepSeek 直连路径。

Benchmark 不接受任意用户 URL、模型或上游地址，也不能被正式分析接口启用。

## 安全

LeanCI 把日志和上传文件视为不可信数据：

- 不执行模型建议或上传内容中的命令；
- 不读取用户指定路径；
- 不抓取用户提供 URL；
- 不接受 ZIP 或二进制文件；
- 不自动应用 Git Diff；
- 不把错误堆栈、环境变量或 API Key 返回给浏览器；
- Paritok 不可用时正式分析失败。

详细设计见 [架构文档](docs/ARCHITECTURE.md)。发现安全问题时，在 `SECURITY.md` 创建后按其中的非公开方式报告；在此之前请勿在公开 Issue 中包含密钥或敏感日志。

## Docker

计划使用多阶段 Docker 构建，并在一个容器中运行：

- 仅对外监听平台 `PORT` 的 FastAPI；
- 仅监听容器 localhost `127.0.0.1:8080` 的 Paritok Proxy；
- 由固定命令的 Python 进程管理器监控两个进程。

Dockerfile 与 Compose 文件将在后续阶段创建。

## 项目文档

- [项目计划](PROJECT_PLAN.md)
- [任务清单](TASKS.md)
- [架构设计](docs/ARCHITECTURE.md)
- [人工操作清单](docs/MANUAL_ACTIONS.md)
- [Agent 工作规范](AGENTS.md)

## 路线图

当前阶段和后续可勾选任务以 [TASKS.md](TASKS.md) 为唯一进度来源。只有经过验证的任务才会标记完成。

## Devpost 演示材料

发布阶段将补充：

- 在线 Demo；
- 公开 GitHub 仓库链接；
- 架构图和产品截图；
- 演示视频；
- 带日期与配置的 benchmark 结果；
- 技术实现、挑战、Token 指标和安全说明。

最终字段和要求以 Devpost 页面为准，不在此猜测视频时长或评审规则。

## License

本项目采用 [Apache License 2.0](LICENSE)。
