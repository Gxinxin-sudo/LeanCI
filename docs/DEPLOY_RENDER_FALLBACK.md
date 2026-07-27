# Render Docker 备选部署手册

核验日期：2026-07-27。仅在 Railway 无法使用时采用 Render；不得同时公开两个 LeanCI
实例，因为单实例分析锁和 Paritok `/stats` 隔离不支持横向扩容。操作前核对 Render 官方
[Docker](https://render.com/docs/docker)、
[环境变量](https://render.com/docs/configure-environment-variables)、
[健康检查](https://render.com/docs/health-checks)、
[部署排错](https://render.com/docs/troubleshooting-deploys)和
[回滚](https://render.com/docs/rollbacks)文档。

## 1. 创建一个 Docker Web Service

1. 先完成 [`DEPLOY_RAILWAY.md`](DEPLOY_RAILWAY.md) 的本地 `leanci:phase7` build、
   `docker_smoke.py` 和按需付费的三个 `docker_live_verify.py` 检查。
2. 登录 Render Dashboard，选择 **New +** → **Web Service**。
3. 连接 GitHub；只授权 LeanCI 仓库，然后选择 `LeanCI` 和 `main`。
4. Runtime/Language 选择 **Docker**，不是 Python 或 Node。
5. Root Directory 留空，Dockerfile Path 填 `./Dockerfile`。
6. Docker Command 留空，让镜像固定 `ENTRYPOINT` 作为 PID 1。
7. 只创建一个实例和一个 Web Service；不要另建 Static Site，也不要公开 `8080`。
8. Health Check Path 填 `/api/health`。Render 以 2xx/3xx 为健康，4xx/5xx 为失败，并会
   持续检查运行中的服务。

## 2. 配置端口和变量

在 Environment 页面逐项添加，不要使用 **Add from .env**。Render 会把服务变量同时转换为
Docker build args；本项目 Dockerfile 故意没有任何 Secret `ARG`，不得新增。

Secret：

- `DEEPSEEK_API_KEY`：LeanCI 专用 Key；
- `PARITOK_API_KEY`：LeanCI 专用 Key；
- `PROXY_AUTH_SHARED_SECRET`：至少 32 随机字节，仅供生产认证网关。

非 Secret：

```dotenv
PORT=10000
LLM_PROVIDER=paritok
DEEPSEEK_MODEL=deepseek-v4-flash
ENVIRONMENT=production
CORS_ALLOWED_ORIGINS=https://placeholder.invalid
TRUSTED_PROXY_CIDRS=<真实认证网关的私网 CIDR>
DISTRIBUTED_RATE_LIMIT_REQUIRED=true
DAILY_ANALYSIS_REQUEST_BUDGET=<经审批的正整数>
DATA_RETENTION_HOURS=24
PRICING_SNAPSHOT_DATE=2026-07-26
```

Render Web Service 常用公开端口是 `10000`；entrypoint 会让 FastAPI 监听
`0.0.0.0:$PORT`，Paritok 仍只监听 `127.0.0.1:8080`。首次部署生成
`https://<service>.onrender.com` 后，把 CORS 改成这个精确 origin 并再次 deploy。

## 3. 不可绕过的生产限制

Render 的单个公开 Web Service 与 Railway 一样，不会自动实现 LeanCI 所需的 OIDC Header
注入、可信私网 CIDR、Redis 分布式限流和 UTC 日预算。没有符合
[`PRODUCTION_DEPLOYMENT.md`](PRODUCTION_DEPLOYMENT.md) 的前置网关时，生产
`POST /api/analyze` 会按设计返回 401。

不要改用公开 `ENVIRONMENT=development`、全网可信 CIDR或浏览器共享 Secret。单个直接公开
Render 容器只能证明镜像、静态站、Proxy 和健康链路，不足以证明安全的正式分析 Demo。

## 4. 部署日志与健康验证

点击 **Create Web Service/Deploy**。在 Deploys 页面打开目标 deploy 的 Build Logs 和
runtime logs。必须看到：

```text
Paritok process started with PID <pid>.
Paritok /health is ready; starting FastAPI.
FastAPI process started with PID <pid>.
LeanCI container services are ready.
```

然后在 Settings/Networking 提供的唯一 `onrender.com` 域名验证：

```powershell
$domain = "https://<Render 服务域名>"
$health = Invoke-RestMethod "$domain/api/health" -TimeoutSec 30
$health | Select-Object status,paritok_connected,hosted_gpu_available,model,deepseek_called,message
Invoke-WebRequest "$domain/" -TimeoutSec 30 | Select-Object StatusCode
```

`status=ok`、两个 Paritok 字段为 true、`deepseek_called=false` 才通过无费用预检。本地 Proxy
未启动时 `/api/health` 返回 503；Proxy 存活但 hosted GPU 不可用时 JSON 为 degraded。
查看服务 Logs/Deploys，不要建立 `8080` 公网映射。

Render 会在新实例健康后切流；新 deploy 在平台时限内没有通过健康检查会被取消。平台显示
Live 仍不是三样例成功证据。正式网关配置完成后，按 Railway 文档的样例验收规则逐条运行。

## 5. 回滚

进入服务 **Deploys** 页面，选择近期成功且已验证的 deploy → **Rollback** →
**Rollback to this deploy**。Dashboard 回滚会使用目标 build artifact，并自动关闭
autodeploy，防止最新坏 commit 立即再次部署。

回滚不会恢复所有当前服务设置；域名、实例类型和部分平台配置仍使用当前值。回滚后重新核对
环境变量/Key 状态、Deploy Logs、`/api/health`、首页和网关。修复完成后再从 Settings
重新启用 autodeploy。

## 6. Render 失败时保留的信息

- build/runtime 原始错误和目标 commit；
- 服务监听端口和 health check HTTP 状态；
- entrypoint 最后一个无密钥日志事件；
- 是否是 `paritok_connected=false` 或 `hosted_gpu_available=false`；
- 变量名是否存在（不复制值）；
- rollback 目标 deploy 和复验结果。

达到同一外部操作两次失败后停止猜测性重试，保留错误并回到本地已验证镜像；不要修改固定
模型、URL、Proxy 回环绑定或安全边界来换取绿色部署。
