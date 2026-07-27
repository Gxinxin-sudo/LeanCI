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
- 无费用后端单元/条件集成测试已通过；真实 hosted GPU + DeepSeek 三案例验证已于
  2026-07-26 在用户显式费用授权后完成。

阶段四实现更新（2026-07-26）：

- 安全输入已扩展为 4 MiB 请求体、2 MiB 日志、最多 5 个 UTF-8 文本文件；
- 五个固定长日志案例及 `ground_truth.json` 已内置，前端可一键加载；
- 深色开发者工作台已覆盖健康、忙碌、失败、重试、完整诊断、复制和下载报告；
- Token 主指标仍只显示真实 `/stats` 差值；hosted GPU 不可用时 UI 明确降级且不发送分析；
- 三个固定样例的真实 Original/Compressed Token 分别为 `23,906/332`、
  `20,542/847`、`8,325/117`，均通过独立 stats delta 与 ground truth 校验；
- 阶段四无费用质量门为后端 `92 passed, 2 skipped`、前端 `20 passed`，lint、
  strict typecheck 和生产构建通过。

阶段五最终验收（2026-07-26）：

- 五个固定案例均按 `baseline_uncompressed` → `paritok` 顺序完成唯一一次最终真实双跑，
  保留全部 10 行；首轮消息哈希逐例一致，模型固定为 `deepseek-v4-flash`，
  `max_tokens=4096`、thinking disabled、JSON object，网络重试为 0；
- 实际模型请求 10 次，JSON 修复 0、网络重试 0、超时 0；2 行实际压缩、3 行因官方
  `below_refusal_threshold` 正常跳过低收益压缩，无 unavailable 或 upstream failure；
- Token 平均仅以 2 个 `compressed` 行为分母，平均节省率 `85.53%`；三个
  `skipped_low_yield` 行的压缩 Token 字段为 `null`，不是 0% 节省、缓存命中或故障；
- 质量比较仅使用两路都有严格结构化输出的 5 个配对：Baseline `73.00/100`、
  Paritok `54.00/100`，变化 `-19.00` 分，因此不得宣传普遍质量保持；
- 固定工件、报告、前端只读页、确定性评分、人工复核字段、费用场景及回归测试均已收口。
  发布工件记录的价格快照日为 `2026-07-25`；美元数仅为 DeepSeek 配置估算，不是实际账单。

阶段六 Docker 实现更新（2026-07-27）：

- Docker Desktop、Linux Engine、Compose 和 `hello-world` 已验证可用；
- 多阶段 Dockerfile、非 root 运行时、固定 Python PID 1、平台 `PORT`、回环 Paritok、
  静态前端托管、本地 Compose 和无费用容器冒烟脚本已实现；
- `leanci:phase6` 镜像已生成；容器依赖审计、Compose 展开、Dockerfile 静态检查、容器
  边界单元测试、镜像/上下文密钥检查、无密钥状态 78、静态/API、fail-closed 分析和
  Proxy/FastAPI 退出联动均已通过；
- 三条镜像构建客户端命令达到 120 秒上限后，BuildKit 最终完成镜像。完整冒烟的三次受控
  运行依次暴露并修复响应头大小写、slim 镜像无 `kill` 二进制和同端口释放竞态；达到
  外部预检重试上限后，缺失的 API 退出路径改为无外部请求的定向容器检查并通过。

阶段七 Railway 发布准备（2026-07-27）：

- 在阶段六单容器基础上显式安装 `paritok[proxy]`，联合 `/api/health`、Docker 运行时
  `PORT` healthcheck、entrypoint 启动/退出日志和三例容器 stats 对账脚本已实现；
- 根目录 Railway 配置、Railway 逐步部署手册和 Render fallback 手册已创建；所有平台
  Key 仍只允许以运行时 Secret 注入，`.env` 不进入 build context；
- 本地受控构建已把 `[proxy]` extra 的 526.6 MB accelerator wheel 替换为 PyTorch 官方
  固定 191.8 MB CPU wheel；当前网络仍无法在 120 秒 Agent 上限内完成。Docker/buildx
  客户端已逐个清理，phase7 镜像/smoke/三例仍需人工长构建后验证；
- 一个直接公开的平台容器无法替代阶段六要求的 OIDC 可信网关和分布式限流/日预算；平台
  部署、公开域名、生产分析、回滚和三例远端验收保持 `[MANUAL]`，不得预先声称成功。

## 3. MVP 范围

必须完成：

1. 长 CI 日志粘贴输入；
2. 可选上传最多 5 个文本文件；
3. 文件类型白名单；
4. 文件与请求大小限制；
5. 五个内置示例；
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
- 当前价格快照：2026-07-26；Token 是主指标，美元估算是辅助指标。

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

- 建立 pytest、TypeScript、Docker、依赖解析、GitHub Actions 环境五个带预期根因的示例。
- 实现用户显式确认后的 Baseline → Paritok 顺序双跑、使用量和延迟记录、确定性质量评分、
  失败保留和固定 JSON/CSV/Markdown 导出。
- 质量门：baseline 隔离、双跑费用提示、同提示哈希、结果 Schema、stats 不串扰、失败恢复
  和重复运行测试通过；外部链路不可用时发布明确失败工件，不生成宣传结论。

### 阶段 6：安全审计、产品验收与 Docker

- 从安全工程师、黑客松评委和普通用户三个角度完成密钥/历史、输入、提示注入、执行边界、
  错误/日志、网络、并发、隐私、下载/复制、桌面和移动端审计。
- 增加请求 ID、安全响应头、显式 CORS 白名单、基础速率限制、单分析并发拒绝和全链路超时；
  创建 `SECURITY.md` 与威胁模型，并把密钥/依赖审计接入 CI。
- 隔离 Mock 浏览器验收不得调用正式模型；阶段五的真实 Token 工件保持冻结。
- 多阶段构建前端和 Python 运行时；Python PID 1 固定启动并监控 Paritok 与 Uvicorn。
- FastAPI 监听平台 `PORT`，Paritok 仅监听 `127.0.0.1:8080`。
- 质量门：安全回归、密钥历史扫描、依赖审计、全量测试、隔离浏览器验收，以及后续镜像构建、
  健康检查、代理死亡联动退出、静态站点、API 和无密钥启动失败路径通过。

### 阶段 7：公开发布与 Devpost

- 完善 README、SECURITY、CONTRIBUTING、截图、演示脚本、benchmark 报告和部署说明。
- `[MANUAL]` 创建公开 GitHub 仓库、配置部署密钥、发布 Demo、录制/上传演示并提交 Devpost。
- 质量门：全量测试、Docker smoke test、密钥扫描、公开链接和 Devpost 清单复核通过。

## 6. 主要风险与应对

| 风险 | 应对 |
| --- | --- |
| Paritok 代理存活但 hosted GPU 不可用时会未压缩透传 | 正式请求前检查固定 hosted `/test`，调用后校验 stats；失败即拒绝结果 |
| `/stats` 是进程累计值，容易受并发污染 | 单 worker、进程内锁、前后快照差值和异常差值拒绝 |
| hosted GPU 对大分块可能回显原文 | 按行切成实测可压缩的约 12,000 字节不可信工具结果块 |
| DeepSeek JSON Output 偶发空内容 | 合理输出上限、严格 Schema、保存脱敏响应、最多一次修复 |
| Paritok 对未知模型的费用默认值不适合 DeepSeek | 忽略 Paritok 美元字段，按环境价格自行估算 |
| 无认证公网入口遭滥用或产生费用 | 单请求并发、基础内存限流和整体超时；公网前增加网关身份、分布式配额和预算限制 |
| 上传内容被误认为只在本机处理 | 页面说明内容会发送到 Paritok/DeepSeek，LeanCI 自身不永久保存但外部保留政策仍适用 |
| 单容器运行两个服务易出现孤儿进程 | Python 固定命令进程管理器监控并终止同容器兄弟进程 |
| 截止时间紧且外部服务可能变化 | 每阶段保持可演示，固定依赖，尽早完成端到端 happy path |

## 7. 官方依据快照

- [Paritok 官方仓库](https://github.com/Paritok-official/paritok-4b-v1)，实现基线 1.2.7。
- [Paritok hosted GPU 策略](https://github.com/Paritok-official/paritok-4b-v1/blob/main/paritok/strategies/gpu_server.py)，当前行为是失败时未压缩透传。
- [DeepSeek 模型与价格](https://api-docs.deepseek.com/quick_start/pricing/)。
- [DeepSeek JSON Output](https://api-docs.deepseek.com/guides/json_mode/)。
- [DeepSeek Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)。

文档与价格最近核验日期为 2026-07-26。实现与发布前必须重新检查官方变更。
