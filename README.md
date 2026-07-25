# LeanCI

**Token-Efficient AI Debugging for Massive CI Logs**

LeanCI 是一个面向长 CI 日志的安全诊断工具。它计划支持 GitHub Actions、pytest、TypeScript Build 和 Docker Build 等日志，以及最多 5 个相关文本文件。正式分析会先通过 Paritok hosted GPU 压缩上下文，再由 DeepSeek 返回严格结构化的根因分析与修复建议。

> 当前状态：阶段一 Mock 工程骨架已完成。React 界面与 FastAPI 接口可在本地运行，但不会调用 Paritok 或 DeepSeek；页面明确显示 `Demo data — Paritok not connected`，Token 指标保持为空。

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

阶段一仅运行本地 Mock 链：

```text
React → FastAPI → deterministic mock response
```

正式集成完成后必须使用以下固定链：

```text
React
  → FastAPI
    → Paritok Proxy (http://127.0.0.1:8080/v1)
      → Paritok hosted GPU
      → DeepSeek (https://api.deepseek.com/chat/completions)
```

正式分析不会在 Paritok 不可用时偷偷直连 DeepSeek。Baseline 只存在于明确标注的 benchmark 路径。

## 技术栈

- 前端：React 19、TypeScript strict、Vite 8、Tailwind CSS 4、Vitest；
- 后端：Python 3.11+、FastAPI、Pydantic、pydantic-settings、pytest、ruff；
- AI：Paritok hosted GPU、DeepSeek `deepseek-v4-flash`；
- 部署：Docker 单容器，FastAPI 同时提供 API 和编译后的静态前端。

## 快速开始

### 前置条件

- Node.js `20.19+`、`22.12+` 或更高兼容版本；
- Python `3.11+`；
- PowerShell。

当前机器的系统 PATH 还没有可用 Python。阶段一验证使用了 Codex 隔离的 Python 3.12
环境；要获得可复现的普通本地环境，请先完成
[人工操作清单](docs/MANUAL_ACTIONS.md) 中的 Python 安装步骤。

### 安装后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements-dev.txt
cd ..
```

### 安装前端

```powershell
cd frontend
npm ci
cd ..
```

### 启动后端

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
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
cd backend
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest

cd ..\frontend
npm run lint
npm run typecheck
npm test
npm run build
```

阶段一不需要 `.env` 或任何 API Key。进入外部服务集成阶段后，才从 `.env.example`
复制本地 `.env`；真实 Key 只能写入被 Git 忽略的本机 `.env`。

## 阶段一 API

| 方法 | 路径 | 当前行为 |
| --- | --- | --- |
| `GET` | `/api/health` | 返回 FastAPI 的 Demo 健康状态，不探测外部服务 |
| `GET` | `/api/config-status` | 只返回 DeepSeek/Paritok 配置是否存在的布尔值 |
| `POST` | `/api/analyze` | 接收 `{ "log_text": "..." }` 并返回确定性 Mock 结果 |

Mock 分析结果包含 `summary`、`root_cause`、`confidence`、`evidence`、
`relevant_files`、`recommended_changes`、`patch`、`verification_commands`、`risks`、
`missing_information` 和 `compression_stats`。`compression_stats` 中的 Token 数字全部为
`null`，不会伪造 Paritok 数据。

## 配置原则

- 默认模型固定为 `deepseek-v4-flash`；
- OpenAI SDK 正式 base URL 固定为本地 Paritok Proxy；
- Paritok 配置使用 `use_gpu_server: true`；
- `DEEPSEEK_API_KEY` 和 `PARITOK_API_KEY` 只来自环境变量；
- 价格通过环境变量配置，并必须带 `PRICING_SNAPSHOT_DATE`；
- 不信任 Paritok 针对未知模型返回的美元估算。

完整非敏感变量见 [.env.example](.env.example)。

## Token 与费用口径

- 阶段一没有 Paritok 数据，Token 面板只显示占位符；
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
