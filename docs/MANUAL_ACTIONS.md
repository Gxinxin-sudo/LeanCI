# LeanCI 人工操作清单

本文件只记录 Codex 不能或不应代替用户完成的安装、账号、网页、密钥和发布操作。完成后请勾选对应项，但不要把任何密钥粘贴到聊天、Issue、截图或 Git。

## 当前最先需要完成

### 1. 后端 Python 环境（已完成）

- [x] 正式后端环境已修复为 `backend/.venv`，当前解释器为 Python 3.12.13。
- [x] 已强制重装固定依赖，避免旧 Python 3.11 二进制 wheel 残留。
- [x] `paritok[proxy]==1.2.7`、pip 与无费用测试已验证可用。

后续从仓库根目录运行任何后端命令时，必须直接使用：

```powershell
.\backend\.venv\Scripts\python.exe
```

不得依赖终端激活状态、根目录 `.venv` 或 Codex 自带 Python。原 Python 3.11.9 基础解释器
已不在系统中，因此旧虚拟环境无法启动；仓库仍保留
`backend/.venv.python312-backup-20260725` 作为可恢复备份。不要提交任何 `.venv` 内容。

## 开发后续需要

### 2. 安装 Docker Desktop

- [x] 已安装 Docker Desktop 4.83.0，并启动 Linux Engine。
- [x] 已验证 Docker Engine/CLI 29.6.2、Compose 5.3.1 和 Linux `amd64`。
- [x] 已成功运行：

```powershell
docker --version
docker compose version
docker run --rm hello-world
```

如果安装前已经打开当前 PowerShell，它可能还没有继承 Docker CLI 的 PATH。重新打开
PowerShell，或按 [`DOCKER.md`](DOCKER.md) 为当前会话补充路径。

### 3. 注册并确认 Devpost 赛事

- [ ] 打开 [Build with Paritok: The Token-Efficiency Hackathon](https://build-with-paritok.devpost.com/)。
- [ ] 登录或注册 Devpost。
- [ ] 点击 Join hackathon/加入赛事，并确认 LeanCI 所属团队或个人身份。
- [ ] 打开 Overview、Rules、Details/Requirements 页面。
- [ ] 记录页面显示的精确截止时区、必填字段、演示链接、视频、开源和资格要求。
- [ ] 不根据本文猜测视频时长或评审标准；官方页面有变化时，以页面为准并更新项目文档。

### 4. 创建 DeepSeek API Key

- [ ] 打开 [DeepSeek 开放平台 API Keys](https://platform.deepseek.com/api_keys) 并登录。
- [ ] 进入 API Keys 页面，创建一个仅供 LeanCI 使用的新 Key。
- [ ] 创建后立即复制到安全的密码管理器；关闭页面后通常无法再次查看完整 Key。
- [ ] 检查账户余额，确保至少可以运行少量开发请求和双跑 benchmark。
- [ ] 仅当项目根目录还没有 `.env` 时，复制环境示例；已有 `.env` 时不要覆盖：

```powershell
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item ".env.example" ".env"
}
```

- [ ] 用本地文本编辑器打开 `.env`，只填写：

```dotenv
DEEPSEEK_API_KEY=<在本机填写，不要发送给 Codex>
```

- [ ] 保留下列非敏感默认值，不要改成旧模型名：

```dotenv
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
LLM_PROVIDER=paritok
```

- [ ] 确认 `.env` 仍被 Git 忽略：

```powershell
git status --short --ignored
```

不得把 Key 写入 `.env.example`、`paritok.yaml`、README、测试或截图。

- [ ] 从仓库根目录运行独立连接测试：

```powershell
.\backend\.venv\Scripts\python.exe scripts\test_deepseek_connection.py
```

成功时只应看到 `status=success`、`model=deepseek-v4-flash` 和 DeepSeek 实际返回的
`usage`。脚本不会显示模型正文或 Key。若没有填写 Key，则显示 `status=skipped`，
不会把 Mock 当作连接成功。

失败排查：

- 401：Key 无效或已撤销，在 API Keys 页面重新创建；认证失败不会自动重试；
- 402：余额不足，在 DeepSeek 平台检查余额；
- 429：请求过快，等待后再运行；
- 500/503：上游暂时不可用，稍后再试；
- timeout/connection：检查网络、DNS、防火墙和 `DEEPSEEK_BASE_URL`；
- `LLM_OUTPUT_INVALID`：DeepSeek 连续两次没有返回通过严格 Schema 的 JSON，稍后重试。

### 5. 创建 Paritok API Key

- [ ] 打开 [Paritok](https://paritok.com/) 并登录/注册。
- [ ] 进入 Dashboard → API keys。
- [ ] 创建一个 LeanCI 专用 Key，保存到密码管理器。
- [ ] 只在本机 `.env` 中填写：

```dotenv
PARITOK_API_KEY=<在本机填写，不要发送给 Codex>
```

- [ ] 不要把 Key 写入 `paritok.yaml`。该文件只配置 `use_gpu_server: true`，运行时从环境变量读取 Key。
- [ ] 保留 `LLM_PROVIDER=paritok` 和固定 URL，不要改成 Direct 或 Mock。
- [ ] 将非敏感 `PRICING_SNAPSHOT_DATE` 更新为 `2026-07-26`；不要改动或输出 Key。
- [ ] 在终端 1 启动 Paritok Proxy，并保持该终端一直打开：

```powershell
.\scripts\start_paritok.ps1
```

- [ ] 在终端 2 启动单 worker FastAPI：

```powershell
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
```

- [ ] 在新终端完成 Proxy、hosted GPU 和累计 stats 预检：

```powershell
Invoke-RestMethod "http://127.0.0.1:8080/health"
Invoke-RestMethod "http://127.0.0.1:8080/stats"
.\backend\.venv\Scripts\python.exe scripts\test_paritok_connection.py
Invoke-RestMethod "http://127.0.0.1:8000/api/health"
```

如果代理只警告 hosted GPU 不可用但仍返回本地 health OK，不要继续正式分析；LeanCI 必须显示不可用错误。

- [ ] 确认 DeepSeek 余额后，显式批准一次真实付费的长请求验证：

```powershell
.\backend\.venv\Scripts\python.exe scripts\verify_paritok_long_request.py --confirm-cost
```

只有输出 `status=success`、`original_tokens > 5000`、固定模型、stats 验证标记和累计计数时，
才可勾选本项。真实数值必须来自 `/stats` 差值。不要把 `/stats` 中可能出现的
`estimated_cost_saved_usd` 当作 DeepSeek 账单；只使用 LeanCI 返回的带价格快照和免责声明的
估算值。完整步骤见 `docs/PARITOK_VERIFICATION.md`。

### 6. 阶段四真实三案例与录屏

- [x] 2026-07-26 已在用户明确授权后只停止旧 8080 PID 24112，并从主机网络环境以隐藏后台
  方式启动当前工作区 Paritok。新监听 PID 24884；Vite 5173 PID 16884 全程未停止或修改。
- [x] 已依次验证本地 `http://127.0.0.1:8080/health`、认证 hosted GPU 预检、`/stats`，
  以及 `http://127.0.0.1:8000/api/health`；正式模型固定为 `deepseek-v4-flash`。
- [x] 页面 Formal route status 的 FastAPI、Paritok、Hosted GPU 均健康。若以后 hosted GPU
  显示 unavailable，停止操作并稍后重试；不要把本地 Proxy health 当成正式成功。
- [x] 已确认并从仓库根目录分别执行三次显式付费分析；每条命令只运行一个案例，最长等待
  约 110 秒：

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample docker-build
```

- [x] 三例均为 `status=success`、`proxy_requests=1` 且 `original_tokens > 5000`：
  Python `23,906 → 332`，TypeScript `20,542 → 847`，Docker `8,325 → 117`。
- [x] 结果只采用本次 `/stats` 差值；没有采用 Mock、字符估算或 Paritok 的
  `estimated_cost_saved_usd`。
- [x] 已保存并检查以下真实运行状态和三张结果页截图：

```text
http://127.0.0.1:5173/?capture=python-pytest
http://127.0.0.1:5173/?capture=typescript-build
http://127.0.0.1:5173/?capture=docker-build
```

- [ ] `[MANUAL]` 录制视频：先展示首页价值和健康状态，再点一个 Sample、点
  `Analyze failure`，首先停留在
  `Tokens Saved`，然后滚动展示 Root Cause、Evidence、Patch 和 Download Report。
- [ ] `[MANUAL]` 发布前复查截图和视频中没有 `.env`、终端环境变量、API Key、请求头或
  平台密钥页面。

### 7. 阶段五真实 Benchmark（官方 skip 语义已确认并正确收口）

- [x] 2026-07-26 完成一次独立 hosted GPU 预检和 Proxy 启动时的第二次复核；两次均返回
  `gpu_available=true`。
- [x] 在明确费用授权下逐条运行五例。实际总计 10 次模型请求，JSON 修复 0 次、网络重试
  0 次、命令超时 0 次：

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case docker-build
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case dependency-resolution
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case github-actions-environment
```

- [x] 已用严格 Pydantic 模型检查 `benchmarks/results.json` 的 10 行、每例两路消息与
  Schema 哈希、Baseline null 规则、Paritok `/stats` 等式和失败保留规则。
- [x] Paritok 官方已确认：`/stats` 的 `0→0` 表示该请求被 `SKIPPED/passthrough`，不是
  缓存命中或 stats Bug；跳过请求会增加 `total_requests`，但不计入 original/compressed。
- [x] 已临时启用本地官方 trace，并用进程内假上游硬拦截 DeepSeek。第二次有效探测得到
  以下脱敏摘要；本地 trace 已恢复为 disabled，JSONL 被 Git 忽略且不得提交、打印或截图：

  1. `python-pytest`：`13288` Token 块以 `below_refusal_threshold` 跳过；
     `10469→254` Token 块成功压缩。
  2. `typescript-build`：`10600` 与 `9692` Token 块均以
     `below_refusal_threshold` 跳过。
  3. `docker-build`：`7682` Token 块以 `below_refusal_threshold` 跳过；
     `543→77` Token 块成功压缩。
  4. `dependency-resolution`：`11424` 与 `7438` Token 块均以
     `below_refusal_threshold` 跳过。
  5. `github-actions-environment`：`13860` 与 `6356` Token 块均以
     `below_refusal_threshold` 跳过。

- [x] 默认 trace 已关闭；`artifacts/runtime/compress_trace.jsonl` 仅用于本地诊断并被
  Git 忽略。不要提交、打印、截图或复制其完整内容。
- [x] 最终受控真实运行完成：实际模型请求 10 次，JSON 修复 0、网络重试 0、超时 0；
  2 个 `compressed`、3 个 `skipped_low_yield`、0 个 `unavailable`、0 个
  `upstream_failed`。
- [x] 两个 compressed 行为 Python `10,469→254` 与 Docker `543→144`，平均 Token
  节省率 `85.53%`；分母明确为 2，不包含三个低收益跳过。
- [x] 五个质量有效配对为 Baseline `73.00/100`、Paritok `54.00/100`，变化 `-19.00`
  分；所有结构化输出均保留确定性评分和待人工确认字段。

当前只可宣传“2 个 compressed 行平均节省 `85.53%`，3 个低收益案例按设计 passthrough”。
不得宣传这是五例整体平均、所有输入都会压缩、质量保持、生产稳定性或实际账单降低。

阶段五已经完成并冻结；开始阶段六不需要再次运行付费 Benchmark。以后只有在案例、模型、
提示词、价格配置或 Paritok 版本发生有意变更，且用户重新明确授权费用时，才创建新的
Benchmark 运行；不得用新结果静默覆盖本次 10 行验收工件。

## 发布阶段需要

### 8. 阶段六安全部署收口

- [x] 2026-07-27 已完成阶段六 Docker 首次构建和全部无费用容器功能检查。以后需要复现时：

```powershell
cd "C:\Users\xin'xin\Desktop\LeanCI"
docker build --progress=plain --tag leanci:phase6 .
$env:LEANCI_DOCKER_CLI = (Get-Command docker).Source
.\backend\.venv\Scripts\python.exe scripts\docker_smoke.py
```

  成功判据是构建生成 `leanci:phase6`，修正后的脚本输出顶层
  `"status":"passed"`，且无密钥退出码为 78、前端/API 检查通过、正式分析
  `deepseek_called=false`、Proxy/API 退出联动均为非零容器状态。首次下载可能超过两分钟，
  应让 Docker BuildKit 自然完成；不要把任何密钥传给 `docker build`。完整说明见
  [`DOCKER.md`](DOCKER.md)。
- [ ] 按 [`PRODUCTION_DEPLOYMENT.md`](PRODUCTION_DEPLOYMENT.md) 配置生产环境变量：
  `ENVIRONMENT=production`、精确 HTTPS `CORS_ALLOWED_ORIGINS`、
  `TRUSTED_PROXY_CIDRS`、新的 `PROXY_AUTH_SHARED_SECRET`、
  `DISTRIBUTED_RATE_LIMIT_REQUIRED=true` 和已审批的
  `DAILY_ANALYSIS_REQUEST_BUDGET`。不得将共享密钥写入前端、Git 或日志。
- [ ] 在 FastAPI 前配置可信 TLS + OIDC 反向代理/API 网关：它必须先移除浏览器提供的
  `X-LeanCI-Proxy-Auth` / `X-LeanCI-Principal`，认证成功后才重新写入；容器端口和 8080
  均不得直接公网暴露。同步配置 4 MiB body、≤115 秒上游超时、按主体和 IP 的 Redis
  分布式限流，以及 UTC 日原子请求预算；Redis/网关故障必须拒绝分析，不能回退为本地内存。
- [ ] FastAPI 继续只运行一个 Uvicorn worker；在并发锁、限流和 `/stats` 隔离迁移到共享
  事务存储前，不要横向扩容 API worker。
- [ ] 给生产前端文档响应配置与 API 等价的 CSP、防嵌入、`nosniff`、no-referrer 和
  Permissions-Policy 响应头。
- [ ] 逐项落实 `PRODUCTION_DEPLOYMENT.md` 的数据保留表：关闭 body/header/model-output
  日志，网关元数据最长 24 小时，Redis 计数键设置 TTL，平台 trace/backup 最长 7 天；阅读并
  确认 Paritok、DeepSeek、反向代理和托管平台的内容保留政策。只在拥有授权时上传私有源码或
  个人数据，并把真实保留口径写入隐私说明。
- [ ] 公开 GitHub 仓库建立后启用 private vulnerability reporting、secret scanning、
  dependency alerts 和分支保护，并把 `SECURITY.md` 临时私下报告方式替换为私有报告链接。
- [ ] 发布前重新运行全历史密钥扫描和依赖审计；如果怀疑泄露，先在供应商侧撤销 Key，
  不要仅从当前文件删除。

### 9. 创建公开 GitHub 仓库

- [ ] 登录 [GitHub](https://github.com/new)。
- [ ] Repository name 填写 `LeanCI`。
- [ ] Visibility 选择 **Public**。
- [ ] 不勾选初始化 README、`.gitignore` 或 License，因为本地仓库已有这些文件。
- [ ] 创建仓库后复制 HTTPS 地址。
- [ ] 在本地项目目录执行（将地址替换为页面显示的真实地址）：

```powershell
git remote add origin https://github.com/Gxinxin-sudo/LeanCI.git
git push -u origin main
```

- [ ] 刷新 GitHub 页面，确认 `README.md`、`LICENSE` 和源代码可公开访问，且没有 `.env` 或密钥。

### 10. 在 Railway 创建单容器服务

完整逐屏步骤、变量表、日志判据、Paritok 诊断和回滚见
[`DEPLOY_RAILWAY.md`](DEPLOY_RAILWAY.md)；Railway 不可用时只使用
[`DEPLOY_RENDER_FALLBACK.md`](DEPLOY_RENDER_FALLBACK.md)，不要同时公开两个实例。

- [ ] 先完成本地 phase7 镜像：2026-07-27 自动化已启动 Docker Desktop PID `37156`，
  Engine/Compose/Compose config 均正常，但两次 build 都达到 120 秒上限，最终没有
  `leanci:phase7` 镜像。官方 `[proxy]` extra 会拉取 `numpy` 和
  `sentence-transformers`；不要继续无依据重试，也不要改回精简 `paritok`。
- [ ] 在 Docker Desktop 明确显示 Engine healthy 后，从新的 PowerShell 设置 CLI 路径并
  重新执行一次构建；开始前确认没有其他 build，命令不得携带 `.env` 或 build arg：

```powershell
$dockerBin = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin"
$env:Path = "$dockerBin;$env:Path"
docker build --progress=plain --tag leanci:phase7 .
docker image inspect leanci:phase7 --format "{{.Id}} {{.Created}} {{.Size}}"
```

- [ ] 只有 inspect 成功后运行无费用 smoke，并保留顶层 `"status":"passed"`：

```powershell
$env:LEANCI_DOCKER_CLI = (Get-Command docker).Source
.\backend\.venv\Scripts\python.exe scripts\docker_smoke.py
```

- [ ] 确认真实费用和余额后，逐条运行 `docs/DOCKER.md` 的三个
  `docker_live_verify.py --confirm-cost --sample ...` 命令；每条必须核对健康、stats 差值、
  固定模型、编排重试 0 和容器退出码 0。当前自动化没有运行这三条，不能勾选。
- [ ] 将本次已验证 commit 推送到 GitHub，确认仓库没有 `.env` 或 Key。
- [ ] Railway → New Project → Deploy from GitHub repo；连接 GitHub App 时只授权 LeanCI
  所需仓库，选择 `LeanCI`/`main`，只创建一个服务。
- [ ] 保持 Root Directory 为仓库根，确认 `railway.json` 选择根 `Dockerfile`，不设置自定义
  Start Command。
- [ ] 在 Variables 逐项添加并 Seal `DEEPSEEK_API_KEY`、`PARITOK_API_KEY` 和
  `PROXY_AUTH_SHARED_SECRET`；不要上传 `.env` 或把 Secret 变成 build arg。
- [ ] 配置固定 provider/model、production、精确 HTTPS CORS、真实网关私网 CIDR、分布式
  限流声明、经审批 UTC 日预算和保留期。不要自己覆盖 Railway `PORT`，也不要使用 8080。
- [ ] 首次部署只在 Build/Deploy Logs 依次证明 Dockerfile build、Paritok PID、
  Paritok `/health`、FastAPI PID 和 services ready 后才继续；缺 Secret 状态 78、Proxy
  启动退出/20 秒超时或 FastAPI 变量校验失败都算部署失败。
- [ ] Service → Settings → Networking → Public Networking → Generate Domain，只生成一个
  HTTPS 域名，不创建 TCP Proxy；将 CORS 占位 origin 更新为生成的精确域名并重新部署。
- [ ] 在 30 秒超时内访问 `/api/health`，保存无密钥 JSON 证据；必须为 `status=ok`、
  `paritok_connected=true`、`hosted_gpu_available=true`、固定模型和
  `deepseek_called=false`。
- [ ] 确认首页和 `/api/samples` 使用同一域名，公网不能访问 Paritok `8080`。
- [ ] 配置符合 `PRODUCTION_DEPLOYMENT.md` 的 TLS/OIDC 网关、Header 清洗/注入、Redis
  分布式限流与 UTC 日预算，并完成故障拒绝测试。一个直接公开 Railway 容器没有这些能力，
  `/api/analyze` 返回 401 是预期安全行为，不能改用 public development 模式绕过。
- [ ] 生产网关实际通过后，逐一运行 Python/TypeScript/Docker 固定样例并核对本次 stats；
  没有网关或只完成健康检查时不得声称公开 Demo 分析成功。
- [ ] 在 Deployments 选择此前已验证版本演练 Rollback；回滚后重新核对 Key 版本、日志、
  `/api/health`、首页和至少一个获授权样例。
- [ ] 记录 project/service/deployment ID、Git commit、域名、无密钥日志和 request ID；
  不记录变量值、请求正文、模型正文或内部 Header。

以上全部是外部账号/网页操作，本地 commit 无法代做或证明，完成前必须保持 `[MANUAL]`。

### 11. 准备并提交 Devpost 材料

- [ ] 创建清晰的项目一句话说明和完整描述。
- [ ] 录制日志输入、结构化诊断、Diff、Token 面板和 benchmark 的演示。
- [ ] 准备架构图、结果截图、公开仓库和在线 Demo 链接。
- [ ] 在视频或说明中明确 Token 来源、价格估算口径和 baseline 未压缩标签。
- [ ] 按 Devpost 当时显示的要求上传材料并逐项预览。
- [ ] 提交前再次确认没有截图或控制台画面暴露 API Key。

## 密钥泄露应急

如果怀疑密钥进入聊天、Git、日志或截图：

1. 立即在对应平台撤销该 Key；
2. 创建新 Key 并只更新本地/部署环境变量；
3. 停止推送；
4. 检查完整 Git 历史，而不只是当前文件；
5. 在继续发布前记录并完成清理验证。
