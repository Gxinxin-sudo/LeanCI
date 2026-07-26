# LeanCI 任务清单

说明：

- `[MANUAL]` 表示必须由用户在网页、账号或本机安装界面中完成。
- 只有实际完成并验证的任务才能勾选。
- 每个阶段结束前必须完成相应测试、文档更新和安全检查。

## 阶段 0：规划与仓库初始化

- [x] 检查初始目录与 Git 状态
- [x] 检查 Python、Node.js、npm、Git 和 Docker 可用性
- [x] 核对 Paritok 1.2.7 与 DeepSeek 当前官方文档
- [x] 初始化 `main` 分支和本地 GitHub noreply 身份
- [x] 创建 `AGENTS.md`
- [x] 创建 `PROJECT_PLAN.md`
- [x] 创建 `TASKS.md`
- [x] 创建 `docs/ARCHITECTURE.md`
- [x] 创建 `docs/MANUAL_ACTIONS.md`
- [x] 创建 `README.md` 骨架
- [x] 创建 `.gitignore` 和无密钥 `.env.example`
- [x] 添加 Apache 2.0 `LICENSE`
- [x] 运行暂存差异、空白错误和密钥模式检查
- [x] 创建首次 Git Commit 并确认工作区干净

## 阶段 1：工程脚手架

- [x] 使用已安装的 Python 3.11.9 创建唯一正式后端环境 `backend/.venv`；后续命令固定使用 `./backend/.venv/Scripts/python.exe`
- [x] 建立 FastAPI 包结构、依赖锁定和开发命令
- [x] 建立 React + TypeScript strict + Vite + Tailwind 前端
- [x] 建立 `examples/`、`benchmarks/`、`scripts/` 和 `tests/`
- [x] 定义分析结果、Token 指标、错误响应和公开配置 Schema
- [x] 创建 Demo-only `GET /api/health`、`GET /api/config-status` 和 Mock `POST /api/analyze`
- [x] 创建日志输入、Load Sample、Analyze Failure、完整结果和 Token 占位界面
- [x] 覆盖 loading、empty、success、error 状态与前端错误边界
- [x] 配置 pytest、ruff、前端 lint、类型检查、测试和构建
- [x] 添加基础 GitHub Actions 工作流
- [x] 运行后端测试/lint、前端 lint/类型检查/测试和生产构建
- [x] 更新 README、架构、人工操作和任务状态

## 阶段 2：安全输入与 Paritok

### 本轮增量：DeepSeek 独立连接（不接入正式分析）

- [x] 安装并固定官方 OpenAI Python SDK `2.46.0`
- [x] 固定 `deepseek-v4-flash`，拒绝 `deepseek-chat` 和 `deepseek-reasoner`
- [x] 实现统一 `MockProvider`、`DirectDeepSeekProvider` 和 `ParitokDeepSeekProvider`
- [x] 限制 Direct 只能用于连接测试、未压缩 baseline 和故障定位
- [x] 保持 FastAPI `/api/analyze` 与 `LLM_PROVIDER=mock`，不启用生产直连或自动回退
- [x] 创建只输出状态、模型和实际 usage 的 `scripts/test_deepseek_connection.py`
- [x] 实现固定安全提示词、不可信数据边界、JSON Object 和禁用 thinking
- [x] 实现严格 Pydantic 输出校验与空内容/无效 JSON/缺字段的一次修复
- [x] 实现 timeout、有限网络重试、401/402 不重试和安全错误映射
- [x] 添加 Mock、参数、修复、错误、重试和无 Key 跳过测试
- [x] 运行后端 Ruff/格式/pytest/pip check 和前端 lint/类型检查/测试/生产构建
- [x] 更新 `.env.example`、README、架构、人工操作和任务状态
- [ ] `[MANUAL]` 在 DeepSeek 开放平台创建 Key、检查余额并完成一次真实连接测试

### 安全输入剩余工作

- [x] 实现 4 MiB 请求体硬上限（含无 `Content-Length` 的分块请求）
- [x] 实现 2 MiB 日志、5 文件、单文件 256 KiB、合计 1 MiB 限制
- [x] 实现文件名、扩展名、UTF-8、NUL 和控制字符校验
- [x] 保证上传内容只在内存中处理
- [x] 测试路径穿越、超限、ZIP、二进制、无效 UTF-8 和控制字符

## 阶段 3：正式 Paritok hosted GPU 与 DeepSeek

- [x] 对照 Paritok 官方仓库与本机安装包核验 `paritok[proxy]==1.2.7` schema 和 CLI
- [x] 安装并固定 `paritok[proxy]==1.2.7`
- [x] 创建无密钥 `paritok.yaml`，启用 `use_gpu_server: true`
- [x] 创建 Windows PowerShell 与 Linux/Docker Proxy 启动脚本
- [x] 固定本地 base URL 和完整 DeepSeek `/chat/completions` 上游端点
- [x] 固定 `deepseek-v4-flash`，正式接口不接受模型或 URL 覆盖
- [x] 实现本地 `/health`、`/stats` 和固定 hosted `/test` 客户端与独立超时
- [x] 实现分析前后 stats 快照、严格 delta、请求次数匹配和累计统计
- [x] 返回本次原始/压缩/节省 Token、压缩比例、累计统计、Paritok 状态和模型
- [x] 丢弃 Paritok `estimated_cost_saved_usd`，使用项目 DeepSeek 价格与快照日期估算
- [x] 实现单 worker 分析锁，测试并发请求不会污染单次 Token 指标
- [x] 实现正式接口只经过 Paritok；Proxy、hosted GPU 或 stats 不可用时 503
- [x] 实现 DeepSeek 认证、余额、限流、服务错误和超时的安全公开错误
- [x] 实现不可信 CI 证据的惰性历史 tool 结果，使 Paritok 实际压缩
- [x] 使用保守 UTF-8 字节上限分块，且不把预分块计数冒充 Token 指标
- [x] 实现 JSON Object、`max_tokens=4096` 和禁用 thinking
- [x] 定义并验证问题摘要、根因、可信度、证据、文件、建议、Diff、命令、风险和缺失信息
- [ ] 实现空内容/无效 JSON 的脱敏调试保存
- [x] 实现且只实现一次 JSON 修复重试，并让修复仍经过 Paritok
- [x] 实现安全错误分类，不泄露请求头、环境变量或内部路径
- [x] 测试有效 JSON、空内容、截断、无效 Schema 和第二次失败
- [x] 测试日志中的恶意指令不能覆盖系统提示词
- [x] 测试任何模型命令都不会被执行
- [x] 创建 `scripts/test_paritok_connection.py`
- [x] 创建显式费用确认的超过 5,000 Token 验证脚本
- [x] 添加客户端、服务、Provider、API、并发和条件真实集成测试
- [x] 创建 Windows 设置、正式验证文档，更新 README、架构图和人工操作
- [x] `[MANUAL]` 配置两个真实 Key，启动 Proxy，并完成超过 5,000 Token 的真实验证（2026-07-26 已验证）

## 阶段 4：前端 MVP

- [x] 实现日志粘贴、字符/大小提示和清空操作
- [x] 实现最多 5 个文件的上传、删除和客户端预检查
- [x] 实现三个内置示例选择
- [x] 实现 Paritok/服务健康状态
- [x] 实现提交、忙碌、失败和重试体验
- [x] 展示摘要、根因、可信度、证据和相关文件
- [x] 展示建议、Git Diff、验证命令、风险和缺失信息
- [x] 展示 Token 主指标和费用估算免责声明
- [x] 实现复制 Diff、证据和命令，并下载 Markdown 报告
- [x] 完成响应式和基础无障碍体验
- [x] 运行组件测试、类型检查和生产构建
- [x] 经正式 Paritok → hosted GPU → DeepSeek 链路真实运行三个固定样例
- [x] 核验每例独立 `/stats` 差值、`original_tokens > 5000` 和 ground truth 必需文件/修复方向
- [x] 保存三个 `demo_result.json`、可直接载入的 capture 状态和结果页截图
- [x] 更新 README、架构和任务状态

## 阶段 5：示例与 Benchmark

- [x] 创建固定 Python pytest 示例及 `ground_truth.json`
- [x] 创建固定 TypeScript Build 示例及 `ground_truth.json`
- [x] 创建固定 Docker Build 示例及 `ground_truth.json`
- [x] 创建固定依赖解析失败示例及严格 `ground_truth.json`
- [x] 创建固定 GitHub Actions 环境失败示例及严格 `ground_truth.json`
- [x] 限制 live benchmark 只能使用五个内置示例
- [x] 要求 `--confirm-cost` 并明确每例预期 2 次、最多 4 次模型调用
- [x] 固定顺序为未压缩 Baseline → Paritok，首轮消息哈希必须一致
- [x] 为两路结果记录 JSON 有效性、质量分、使用量、延迟和 cache hit/miss 价格场景
- [x] 确保 baseline 代码无法被 `/api/analyze` 调用
- [x] 导出带日期、模型、配置和失败行的 `results.json`、`results.csv`、`report.md`
- [x] 实现根因 40、证据 20、文件 15、修复方向 15、JSON 10 的确定性评分和人工复核字段
- [x] 测试重复运行、错误恢复、费用提示、同提示、stats 隔离和失败保留
- [x] 创建只读 Benchmark 前端页并展示平均 Token 节省、质量变化和全部失败
- [x] 更新 README、架构和任务状态
- [x] 在明确费用授权后依次完成五例真实双跑；2026-07-26 两次 hosted 检查成功，实际
  发送 10 次模型请求、0 次 JSON 修复、0 次网络重试，固定工件保留全部 10 行
- [x] `[MANUAL]` Paritok 官方确认 `/stats` 的 `0→0` 是 `SKIPPED/passthrough`，不是缓存
  命中或 stats Bug；跳过请求只增加 `total_requests`
- [x] 临时启用且隔离官方 trace，以无 DeepSeek 假上游完成五例 tool-message 诊断；三个
  原 `0→0` 案例的确切 reason 均为 `below_refusal_threshold`
- [x] 将三个 trace 已确认的低收益 `0→0` Benchmark 行标记为 `compression_skipped`，
  Token/质量均为不适用；未知正式分析仍 fail closed，且不伪造 Token
- [x] 仅对实际压缩且 `/stats` delta 有效的行计算 Token 平均值；5,000 门槛只适用于
  实际压缩块，正常跳过不计为 0% 节省或质量 0
- [x] 保留 Python DeepSeek timeout 和 Docker 5,000 Token 验收失败；报告与前端排除
  skipped 行后，质量变化正确显示为不适用
- [x] trace 默认关闭且诊断 JSONL 保持 Git 忽略；不提交 trace 内容

## 阶段 6：Docker 与端到端验证

- [ ] `[MANUAL]` 安装并启动 Docker Desktop
- [ ] 创建前端构建 + Python 运行时的多阶段 Dockerfile
- [ ] 创建固定命令的 Python 双进程管理脚本
- [ ] FastAPI 监听平台 `PORT`
- [ ] Paritok 只监听 `127.0.0.1:8080`
- [ ] 创建本地开发 `docker-compose.yml`
- [ ] 验证缺少密钥时安全失败
- [ ] 验证代理或 FastAPI 退出时容器联动退出
- [ ] 构建镜像并运行 API、静态站点和分析 smoke test
- [ ] 扫描镜像与构建上下文中的密钥
- [ ] 更新 README、架构和任务状态

## 阶段 7：安全、开源与 Devpost

- [ ] 创建 `SECURITY.md` 和 `CONTRIBUTING.md`
- [ ] 完成全量 pytest、ruff、前端测试、类型检查和构建
- [ ] 完成 Docker 端到端测试
- [ ] 完成密钥、依赖和错误响应安全检查
- [ ] 完善 README 快速开始、部署、Benchmark 和截图
- [ ] `[MANUAL]` 注册/加入 Devpost 项目并确认官方规则
- [ ] `[MANUAL]` 创建 DeepSeek API Key 并确保余额可用
- [ ] `[MANUAL]` 创建 Paritok API Key
- [ ] `[MANUAL]` 创建公开 GitHub `LeanCI` 仓库
- [ ] `[MANUAL]` 选择部署平台并配置环境变量
- [ ] `[MANUAL]` 验证公开 Demo URL
- [ ] `[MANUAL]` 录制和上传演示视频
- [ ] `[MANUAL]` 填写并提交 Devpost 材料
- [ ] 发布前复核所有链接、声明、价格快照和提交要求
