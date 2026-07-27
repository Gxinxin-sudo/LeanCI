# Railway 单容器部署手册

核验日期：2026-07-27。本文只说明可复核的操作，不把“构建完成”或“页面能打开”当作正式
链路部署成功。Railway 的界面和策略可能变化，操作前同时核对其官方
[Dockerfile](https://docs.railway.com/builds/dockerfiles)、
[变量](https://docs.railway.com/variables)、
[公网域名](https://docs.railway.com/networking/domains/working-with-domains)、
[健康检查](https://docs.railway.com/deployments/healthchecks)、
[日志](https://docs.railway.com/observability/logs)和
[回滚](https://docs.railway.com/deployments/deployment-actions)文档。

## 部署拓扑与成功判据

Railway 只创建一个 LeanCI 服务和一个公开域名：

```text
Railway HTTPS domain → 0.0.0.0:$PORT FastAPI
                                  ├─ compiled React at /
                                  └─ 127.0.0.1:8080 Paritok Proxy
                                       → Paritok hosted GPU → DeepSeek
```

不得给 `8080` 创建域名、TCP Proxy 或端口映射。`Dockerfile` 不接受 Key 作为 `ARG`，
`.dockerignore` 排除 `.env`，Key 只能由 Railway 运行时变量提供。

只有同时取得以下证据，才能写“Railway 部署成功”：

1. 目标 Git commit 的 Build Logs 显示检测并成功构建根目录 `Dockerfile`；
2. Deploy Logs 依次出现 Paritok 启动、`/health` 就绪、FastAPI 启动和
   `LeanCI container services are ready.`，且没有随后退出；
3. 部署状态为 Active/Success，`GET https://<domain>/api/health` 返回预期 JSON；
4. JSON 中 `status=ok`、`paritok_connected=true`、
   `hosted_gpu_available=true`、`deepseek_called=false`；
5. 静态首页和 `/api/samples` 来自同一域名，公网无法访问 `:8080`；
6. 若要声称正式分析可用，还必须通过本文“生产安全边界”一节的网关验收，并实际运行固定
   样例；仅健康检查不会调用 DeepSeek，也不能证明一次正式分析成功。

## 1. 发布前本地验证

从仓库根目录执行。构建最长 120 秒；若客户端达到时限，记录原始输出并检查 BuildKit 是否仍
在后台构建，不要无界等待。

```powershell
docker build --progress=plain --tag leanci:phase7 .
$env:LEANCI_DOCKER_CLI = (Get-Command docker).Source
.\backend\.venv\Scripts\python.exe scripts\docker_smoke.py
```

`docker_smoke.py` 不读取 `.env`、不调用 DeepSeek，成功时输出 `"status":"passed"`。它验证
镜像没有 Key/`.env`、非 root 用户、React 静态站、联合健康、内部 `/stats`、无 Key 状态 78、
fail-closed 分析，以及 Proxy/FastAPI 任一退出时容器联动退出。

真实三例会产生费用。每条命令只发送一个固定样例、编排层不重试，单条最长 120 秒；开始前
确认本机 `.env` 中两个 Key 有效且 DeepSeek 余额足够：

```powershell
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample python-pytest
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample typescript-build
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample docker-build
```

每条都必须输出 `"status":"passed"`、完全健康的路由、本次容器 `/stats` 差值、固定模型和
`"container_exit_code":0`。脚本只把 `.env` 交给 Docker，不读取或打印变量值；不要把容器
inspect 输出、平台变量页或真实 Key 截图。

## 2. 连接 GitHub 并选择仓库

1. 将本次 commit 推到公开或授权 Railway 访问的 GitHub 仓库；网页部署前先确认 GitHub 上
   没有 `.env`。
2. 登录 Railway Dashboard，选择 **New Project** → **Deploy from GitHub repo**。
3. 首次使用时点击连接 GitHub。只给 Railway GitHub App 授权 LeanCI 所在账户/组织和所需
   仓库，不要无必要授权全部私有仓库。
4. 在仓库列表选择 `LeanCI`，分支选择 `main`。如果仓库看不到，回到 GitHub App 设置检查
   Repository access 后刷新 Railway。
5. 只创建一个 Web 服务；不要把 `docker-compose.yml` 拆成多个 Railway 服务。Compose
   仅供本地使用。

## 3. 明确选择 Dockerfile

仓库根目录保持空白 Root Directory（或显式 `/`）。根目录的 `railway.json` 已固定：

```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "healthcheckPath": "/api/health",
    "healthcheckTimeout": 60
  }
}
```

在 Service → Settings → Build 检查 Builder/Dockerfile Path 与之相符。Railway 默认会检测
名为 `Dockerfile` 的根文件；若界面要求变量覆盖，添加非 Secret
`RAILWAY_DOCKERFILE_PATH=Dockerfile`。Build Logs 应出现 Railway 官方文档所述的
`Using detected Dockerfile` 提示。不要设置自定义 Start Command；镜像的固定
`ENTRYPOINT` 必须作为 PID 1 运行。

## 4. 添加环境变量

打开服务的 **Variables** 标签，逐项添加并 Review/Deploy staged changes。不要上传本机
`.env`，也不要将变量作为 Docker build args。Railway 支持把变量 **Seal**；在变量右侧
三点菜单选择 Seal 后，值不能从 UI/API 读回。

### 必需 Secret

| 变量 | 值 | 处理 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | 新建的 LeanCI 专用 Key | Secret，立即 Seal |
| `PARITOK_API_KEY` | 新建的 LeanCI 专用 Key | Secret，立即 Seal |
| `PROXY_AUTH_SHARED_SECRET` | 密码管理器生成的至少 32 随机字节 | 生产网关 Secret，立即 Seal |

Key 轮换后必须创建新部署并重新检查健康/日志；回滚可能恢复旧变量，回滚前要确认目标部署的
变量版本没有使用已撤销 Key。

### 固定非 Secret

| 变量 | Railway 值 | 说明 |
| --- | --- | --- |
| `LLM_PROVIDER` | `paritok` | 禁止 `direct`/`mock` |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 禁止旧模型名 |
| `ENVIRONMENT` | `production` | 启用生产边界与关闭 API docs |
| `CORS_ALLOWED_ORIGINS` | 首次用 `https://placeholder.invalid` | 生成域名后必须换成精确 HTTPS origin |
| `TRUSTED_PROXY_CIDRS` | 真实认证网关的私网 CIDR | 不得用 `0.0.0.0/0` |
| `DISTRIBUTED_RATE_LIMIT_REQUIRED` | `true` | 表示网关已落实分布式限流，不是实现本身 |
| `DAILY_ANALYSIS_REQUEST_BUDGET` | 经审批的正整数 | UTC 日分析请求硬上限 |
| `DATA_RETENTION_HOURS` | `24` 或更短 | 平台/网关元数据上限 |
| `PRICING_SNAPSHOT_DATE` | `2026-07-26` | 费用估算快照，不是账单 |

不要自己设置 `PORT`；Railway 会注入端口，entrypoint 验证后让 FastAPI 监听
`0.0.0.0:$PORT`。如果为了诊断显式设置 `PORT`，只能使用 1–65535 且不能是内部 `8080`。
所有 Paritok/DeepSeek URL 都保持仓库固定值，不接受部署请求覆盖。

### 生产安全边界：一个 Railway 服务的已知限制

当前 LeanCI 生产模式要求独立 TLS/OIDC 网关先认证用户、移除客户端伪造的内部 Header，再
从 `TRUSTED_PROXY_CIDRS` 注入共享 Secret 和主体；还要求 Redis/网关原子限流与 UTC 日预算。
Railway 的公开域名只提供 TLS 转发，不等同于该认证网关，也没有证据表明它会注入 LeanCI
需要的内部 Header。

因此，**一个直接公开的 Railway LeanCI 服务可以验证镜像、静态站和健康，但正式
`POST /api/analyze` 会按设计返回 401；不能把它宣传为生产分析 Demo。** 不得用以下方式
绕过：

- 不得把 `ENVIRONMENT` 改成 `development` 后直接公开；
- 不得把 `TRUSTED_PROXY_CIDRS` 设为全网；
- 不得把共享 Secret 放进 React、Cookie、URL 或浏览器请求；
- 不得仅把 `DISTRIBUTED_RATE_LIMIT_REQUIRED=true` 当成已经实现 Redis 限流。

要使公开分析安全可用，必须在 LeanCI 前增加符合
[`PRODUCTION_DEPLOYMENT.md`](PRODUCTION_DEPLOYMENT.md) 的认证网关/共享计数器，并让
Railway 容器只接受该网关私网流量。这会超出“仅一个直接公开 Railway 容器”的约束，需要
用户在平台上手工选择架构后再验收。

## 5. 首次部署与日志判读

应用变量后点击 Deploy。Build/Deploy Panel 中点开当前 deployment：

1. **Build Logs**：确认目标 commit、Dockerfile、多阶段前端构建和 Python 依赖安装成功；
2. **Deploy Logs**：确认依次出现：

```text
LeanCI container starting Paritok on 127.0.0.1:8080 and FastAPI on 0.0.0.0:<PORT>.
Paritok process started with PID <pid>.
Paritok /health is ready; starting FastAPI.
FastAPI process started with PID <pid>.
LeanCI container services are ready.
```

Railway 会收集 stdout/stderr。也可在 Observability → Logs 查询，或用有界 CLI 命令：

```powershell
railway logs --latest --lines 100
railway logs --latest --build --lines 100
```

不要用无界 `railway logs` 流式跟随。常见失败与结论：

| 日志 | 原因/操作 |
| --- | --- |
| `Missing required runtime secret variables`，状态 78 | 对应 Secret 未注入；只检查变量名，不打印值 |
| `Paritok process could not be started` | 镜像依赖/可执行文件损坏；回到 Build Logs |
| `Paritok exited during startup with status ...` | Proxy 配置或运行时失败；部署不可接受 |
| `Paritok did not become healthy within 20 seconds` | Proxy 未监听回环 8080；部署不可接受 |
| `FastAPI exited during startup ...` | 多为生产变量校验失败；保留 Pydantic 原始错误并修正变量 |
| `Paritok exited unexpectedly ...` | PID 1 会停止 FastAPI 并让容器非零退出；检查该 deployment |

入口脚本不会打印 Key。若第三方库日志疑似包含认证材料，立即撤销对应 Key，并限制/删除平台
日志；不要复制到 Issue。

## 6. 生成唯一公开域名

服务就绪后进入 Service → Settings → Networking → Public Networking，点击
**Generate Domain**。Railway 服务默认不会自动获得域名。不要创建 TCP Proxy。

取得 `https://<name>.up.railway.app` 后：

1. 把 `CORS_ALLOWED_ORIGINS` 从占位值改为这个精确 origin（无结尾 `/`）；
2. Review staged changes 并重新 Deploy；
3. 确认 Railway 提供的 `RAILWAY_PUBLIC_DOMAIN` 与页面域名一致；
4. React、FastAPI 和所有 `/api/*` 都只使用该域名，不创建第二个前端服务。

## 7. 验证 `/api/health` 并发现 Paritok 未启动

每项探测最多 30 秒：

```powershell
$domain = "https://<Railway 生成的域名>"
$health = Invoke-RestMethod "$domain/api/health" -TimeoutSec 30
$health | Select-Object status,service,paritok_connected,hosted_gpu_available,model,deepseek_called,message
Invoke-WebRequest "$domain/" -TimeoutSec 30 | Select-Object StatusCode
Invoke-RestMethod "$domain/api/samples" -TimeoutSec 30 | Measure-Object
```

联合健康端点不调用 DeepSeek。正常值必须是：

```json
{
  "status": "ok",
  "service": "leanci-api",
  "paritok_connected": true,
  "hosted_gpu_available": true,
  "model": "deepseek-v4-flash",
  "deepseek_called": false
}
```

本地 Proxy 没启动或死亡时，HTTP 为 503 且 `paritok_connected=false`；Docker image
healthcheck 也会失败。若 `paritok_connected=true` 但 `hosted_gpu_available=false`，说明
Proxy 进程存在但正式 hosted 链路不可用，仍不得运行样例。Railway 原生 healthcheck 只在
部署切换时使用，不是持续监控；上线后需另配有界外部监控。

不要给 `8080` 建公网入口来“诊断”。从 Deploy Logs 查 Proxy PID/退出状态；正式统计只在
容器内部由 FastAPI 前后读取，公网不提供 `/stats`。

## 8. 正式样例验收

只有生产网关已实际配置且 `/api/health` 完全正常后，才在页面逐一加载
`python-pytest`、`typescript-build`、`docker-build` 并各运行一次。每次只允许一个分析，
等待不超过 115 秒。记录 request ID、时间、HTTP 状态和返回的本次 stats 差值，不记录请求
正文或 Key。

成功必须满足模型固定、`proxy_requests` 与 `/stats.total_requests` 差值一致、Token 字段
来自同一请求前后 stats、且结果通过严格 Schema。`0→0` 低收益 passthrough 或 hosted
故障不得伪装成 Token 成功。没有网关时保留本项为 `[MANUAL]`，使用本地
`docker_live_verify.py` 结果也不能冒充 Railway 日志验证。

## 9. 回滚

在 Service → Deployments 找到此前**已实际验证**的成功 deployment，点右侧三点菜单 →
Rollback，并确认。Railway 回滚会恢复该部署的 Docker image 和自定义变量；受套餐保留期
限制，过旧部署可能没有 Rollback 选项。

回滚后必须重新做以下检查，不能只看绿色状态：

1. 查看新 rollback deployment 的 Deploy Logs；
2. 核对恢复的变量没有使用已撤销 Key、旧域名或旧价格快照；
3. 重新请求 `/api/health`、首页和 samples；
4. 若正式网关可用，再运行一个固定样例；
5. 若回滚原因是 Key 泄露，不得恢复旧 Key，应先在供应商撤销并创建新部署。

## 10. 需要用户手工保留的证据

- [ ] GitHub App 授权范围与所选仓库/分支；
- [ ] Railway project、service、deployment ID 与 Git commit；
- [ ] Build/Deploy Logs 的无密钥成功片段；
- [ ] 变量名清单和 Secret/Sealed 状态（不要截图值）；
- [ ] 唯一公开域名及 `/api/health` JSON；
- [ ] Paritok 异常时的 HTTP 状态和原始安全日志；
- [ ] 生产网关、分布式限流、日预算和保留策略验收；
- [ ] 三个固定样例的 request ID/stats 证明；
- [ ] 一次回滚演练及回滚后复验结果。

这些网页和账号操作无法由本地 commit 证明，完成前不得在 `TASKS.md` 勾选部署成功。
