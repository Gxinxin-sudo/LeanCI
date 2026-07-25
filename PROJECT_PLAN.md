# LeanCI 项目计划

## 1. 项目目标

LeanCI（Token-Efficient AI Debugging for Massive CI Logs）帮助开发者诊断超长 CI 日志。用户粘贴日志并可上传少量相关文本文件，LeanCI 通过 Paritok hosted GPU 压缩上下文，再由 DeepSeek 输出严格结构化的根因分析、证据、修改建议、Git Diff、验证命令、风险和缺失信息。

项目参加 [Build with Paritok: The Token-Efficiency Hackathon](https://build-with-paritok.devpost.com/)。提交截止时间和最终表单要求必须由用户在 Devpost 页面再次确认。

### 成功标准

- 正式分析始终经过 Paritok；不可用时 fail closed，不产生伪造压缩结果。
- 长日志和最多 5 个文本文件可安全输入，服务端阻止路径穿越、超限、二进制和非白名单文件。
- DeepSeek 返回通过严格 Pydantic 校验的诊断结构，空响应或无效 JSON 最多修复一次。
- UI 清楚展示根因、证据、Diff、验证命令和本次请求独立的 Token 节省数据。
- Benchmark 可显式运行压缩与未压缩双路对比，且不会混入正式分析路径。
- Docker 单容器同时托管编译后的前端、FastAPI 和仅监听 localhost 的 Paritok Proxy。
- README、安全说明、演示材料和公开 GitHub 仓库达到可复现、可评审状态。

## 2. 已验证环境基线（2026-07-25）

以下项目记录仓库初始化时的基线，不代表当前安装状态：

- 工作目录初始为空，尚无应用源代码。
- Node.js `v24.16.0`、npm `11.13.0`、Git `2.53.0.windows.2` 可用。
- Python、Docker、Paritok、pytest、ruff、uv 当前不可用。
- GitHub 账户为 `Gxinxin-sudo`；本地提交使用 GitHub noreply 地址。
- DeepSeek 与 Paritok 密钥及价格环境变量均未设置。
- Windows 中 `rg` 可被发现但无法执行，文件检索需使用 PowerShell 兜底。

当前阶段三环境更新：

- 正式 `backend/.venv` 已使用 Python 3.12.13 修复，并强制重装固定依赖；
- `paritok[proxy]==1.2.7`、pytest、ruff 和 OpenAI SDK 已安装；
- Paritok 当前 YAML schema、Proxy CLI、health/stats 与 hosted GPU 失败透传行为已对照官方源码和本机安装包核验；
- 无费用后端单元/条件集成测试已通过；真实 hosted GPU + DeepSeek 验证保留为 `[MANUAL]`。

## 3. MVP 范围

必须完成：

1. 长 CI 日志粘贴输入；
2. 可选上传最多 5 个文本文件；
3. 文件类型白名单；
4. 文件与请求大小限制；
5. 三个内置示例；
6. Paritok 本地代理与 hosted GPU 健康检查；
7. DeepSeek 严格结构化分析；
8. 根因、可信度和日志证据展示；
9. Git Diff 展示；
10. Token 节省与费用估算面板；
11. 压缩与 baseline Benchmark；
12. 单容器 Docker 部署；
13. 完整 README 和架构/安全文档；
14. Apache 2.0 License；
15. 公开 GitHub 仓库；
16. Devpost 文案、截图、演示视频和可访问 Demo 所需材料。

### 加分功能

- 下载脱敏后的 Markdown/JSON 诊断报告；
- 随仓库发布带日期和环境说明的固定 benchmark 结果；
- 移动端和桌面端响应式体验；
- Diff、证据和验证命令一键复制；
- GitHub Actions 自动测试、构建和密钥扫描；
- 演示页面突出压缩率、节省 Token、延迟和结构化结果稳定性。

### 明确放弃

- 登录注册、数据库和支付；
- GitHub OAuth、私有仓库访问和多用户协作；
- 自动运行用户代码、模型命令、验证命令或 Git Diff；
- 自动部署用户代码；
- 任意 Shell 执行、任意文件读取和用户提供 URL 抓取；
- 将 LeanCI 定位为生产级账单系统或把费用估算称为实际费用。

## 4. 固定技术决策

- 前端：React、TypeScript strict、Vite、Tailwind CSS。
- 后端：Python 3.11+、FastAPI、Pydantic、OpenAI Python SDK、httpx、pytest。
- DeepSeek：`deepseek-v4-flash`、JSON Object、`max_tokens=4096`、关闭 thinking。
- Paritok：实现基线固定 `paritok[proxy]==1.2.7`，`use_gpu_server: true`，密钥仅从 `PARITOK_API_KEY` 读取。
- 正式 OpenAI SDK base URL：`http://127.0.0.1:8080/v1`。
- Paritok 上游：`https://api.deepseek.com/chat/completions`。
- 单实例只允许一个压缩分析进入 stats 快照区间；Uvicorn 固定一个 worker。
- Baseline 代码隔离在 benchmark 服务，正式 `/api/analyze` 没有模式、模型或 URL 开关。
- 当前价格快照：2026-07-25；Token 是主指标，美元估算是辅助指标。

详细数据流、接口、安全控制和故障策略见 `docs/ARCHITECTURE.md`。

## 5. 实施阶段与质量门

### 阶段 0：规划与仓库初始化

- 建立治理、计划、任务、架构、人工操作、README、环境示例、忽略规则和许可证。
- 质量门：文档检查、空密钥检查、暂存差异检查、密钥模式扫描、首次提交后工作区干净。

### 阶段 1：工程脚手架与契约

- 建立后端包、前端 Vite 工程、共享 API 类型、示例和测试目录。
- 固定依赖版本、TypeScript strict、ruff/pytest 和前端测试/构建命令。
- 质量门：后端导入测试、前端类型检查、生产构建和基础 CI 通过。

### 阶段 2：安全输入

- 实现请求体上限、文本文件验证与上传安全；Paritok 正式集成移入阶段三。
- 质量门：路径穿越、超大文件、ZIP/二进制、无效 UTF-8 和控制字符测试通过。

### 阶段 3：正式 Paritok hosted GPU 与 DeepSeek

- 固定 FastAPI → 本地 Proxy → hosted GPU → DeepSeek 路径；实现 health、hosted preflight、
  stats 前后快照、单次 delta、累计统计、请求数证明和 fail-closed 错误。
- 实现不可信 tool 上下文、固定提示词、严格 Schema、一次 JSON 修复重试和安全错误映射。
- 丢弃 Paritok 美元估算；按带日期的项目 DeepSeek 价格生成明确标注的估算值。
- 质量门：Provider/API/stats/并发/故障测试通过；真实超过 5,000 Token 的付费验证由用户显式执行。

### 阶段 4：前端 MVP

- 完成日志输入、文件上传、示例选择、健康状态、结果卡片、Diff、Token/费用面板和错误状态。
- 质量门：类型检查、组件测试、无障碍检查、响应式检查和生产构建通过。

### 阶段 5：Benchmark 与示例

- 建立 GitHub Actions/pytest、TypeScript Build、Docker Build 三个带预期根因的示例。
- 实现用户显式确认后的顺序双跑、使用量和延迟记录、固定结果导出。
- 质量门：baseline 隔离、双跑费用提示、结果 Schema、stats 不串扰和重复运行测试通过。

### 阶段 6：Docker 与端到端验证

- 多阶段构建前端和 Python 运行时；Python PID 1 固定启动并监控 Paritok 与 Uvicorn。
- FastAPI 监听平台 `PORT`，Paritok 仅监听 `127.0.0.1:8080`。
- 质量门：镜像构建、健康检查、代理死亡联动退出、静态站点、API 和无密钥启动失败路径通过。

### 阶段 7：公开发布与 Devpost

- 完善 README、SECURITY、CONTRIBUTING、截图、演示脚本、benchmark 报告和部署说明。
- `[MANUAL]` 创建公开 GitHub 仓库、配置部署密钥、发布 Demo、录制/上传演示并提交 Devpost。
- 质量门：全量测试、Docker smoke test、密钥扫描、公开链接和 Devpost 清单复核通过。

## 6. 主要风险与应对

| 风险 | 应对 |
| --- | --- |
| Paritok 代理存活但 hosted GPU 不可用时会未压缩透传 | 正式请求前检查固定 hosted `/test`，调用后校验 stats；失败即拒绝结果 |
| `/stats` 是进程累计值，容易受并发污染 | 单 worker、进程内锁、前后快照差值和异常差值拒绝 |
| 超过 Paritok 50,000 Token 的单段会跳过 | 按行切成约 40,000 Token 的不可信工具结果块 |
| DeepSeek JSON Output 偶发空内容 | 合理输出上限、严格 Schema、保存脱敏响应、最多一次修复 |
| Paritok 对未知模型的费用默认值不适合 DeepSeek | 忽略 Paritok 美元字段，按环境价格自行估算 |
| 单容器运行两个服务易出现孤儿进程 | Python 固定命令进程管理器监控并终止同容器兄弟进程 |
| 截止时间紧且外部服务可能变化 | 每阶段保持可演示，固定依赖，尽早完成端到端 happy path |

## 7. 官方依据快照

- [Paritok 官方仓库](https://github.com/Paritok-official/paritok-4b-v1)，实现基线 1.2.7。
- [Paritok hosted GPU 策略](https://github.com/Paritok-official/paritok-4b-v1/blob/main/paritok/strategies/gpu_server.py)，当前行为是失败时未压缩透传。
- [DeepSeek 模型与价格](https://api-docs.deepseek.com/quick_start/pricing/)。
- [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/)。
- [DeepSeek Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)。

文档快照日期为 2026-07-25。实现与发布前必须重新检查官方变更。
