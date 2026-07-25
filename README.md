# LeanCI

**Token-Efficient AI Debugging for Massive CI Logs**

LeanCI 是一个面向长 CI 日志的安全诊断工具。它计划支持 GitHub Actions、pytest、TypeScript Build 和 Docker Build 等日志，以及最多 5 个相关文本文件。正式分析会先通过 Paritok hosted GPU 压缩上下文，再由 DeepSeek 返回严格结构化的根因分析与修复建议。

> 当前状态：项目规划与仓库初始化阶段。应用代码、在线 Demo 和 benchmark 结果尚未实现。

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

```text
React
  → FastAPI
    → Paritok Proxy (http://127.0.0.1:8080/v1)
      → Paritok hosted GPU
      → DeepSeek (https://api.deepseek.com/chat/completions)
```

正式分析不会在 Paritok 不可用时偷偷直连 DeepSeek。Baseline 只存在于明确标注的 benchmark 路径。

## 技术栈

- 前端：React、TypeScript、Vite、Tailwind CSS；
- 后端：Python 3.11+、FastAPI、Pydantic、OpenAI Python SDK、httpx、pytest；
- AI：Paritok hosted GPU、DeepSeek `deepseek-v4-flash`；
- 部署：Docker 单容器，FastAPI 同时提供 API 和编译后的静态前端。

## 快速开始

应用脚手架尚未创建，当前不能运行 LeanCI。请先完成：

1. 阅读 [人工操作清单](docs/MANUAL_ACTIONS.md) 并安装 Python 3.11.x；
2. 不要创建或提交真实 `.env`；
3. 进入下一阶段后按照届时更新的命令安装后端和前端依赖。

未来本地配置会从示例开始：

```powershell
Copy-Item ".env.example" ".env"
```

真实 Key 只写入本机 `.env`，不得发送给 Codex 或提交 Git。

## 配置原则

- 默认模型固定为 `deepseek-v4-flash`；
- OpenAI SDK 正式 base URL 固定为本地 Paritok Proxy；
- Paritok 配置使用 `use_gpu_server: true`；
- `DEEPSEEK_API_KEY` 和 `PARITOK_API_KEY` 只来自环境变量；
- 价格通过环境变量配置，并必须带 `PRICING_SNAPSHOT_DATE`；
- 不信任 Paritok 针对未知模型返回的美元估算。

完整非敏感变量见 [.env.example](.env.example)。

## Token 与费用口径

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
