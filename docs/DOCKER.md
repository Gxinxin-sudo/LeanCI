# Docker 构建与验证

LeanCI 的单容器镜像同时包含编译后的 React 前端、FastAPI 和本地 Paritok Proxy：

```text
浏览器 → FastAPI + 静态前端（平台 PORT）
                 ↓
        Paritok Proxy（仅 127.0.0.1:8080）
                 ↓
          Paritok hosted GPU → DeepSeek
```

容器以固定非 root 用户 `10001:10001` 运行。Python 脚本是 PID 1，以固定参数启动一个
Paritok Proxy 和一个 Uvicorn worker；任一子进程退出时，它会停止另一个进程并让容器
失败退出。镜像只声明 FastAPI 的 `8000/tcp`，不会公开 Paritok 的 8080。

## 前提

- Docker Desktop 已启动并显示 Engine running；
- 仓库根目录存在 Git 忽略的 `.env`；
- `.env` 只在运行容器时注入，不能复制进镜像或作为构建参数传入；
- `DEEPSEEK_API_KEY` 和 `PARITOK_API_KEY` 必须同时存在；
- `LLM_PROVIDER` 必须保持 `paritok`；
- `PORT` 必须为 `1..65535`，且不能是内部 Proxy 使用的 `8080`。

如果 Docker Desktop 是在当前 PowerShell 启动后安装的，请重新打开 PowerShell。也可以
只为当前会话补充 Docker CLI 路径：

```powershell
$dockerBin = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin"
$env:Path = "$dockerBin;$env:Path"
docker version
docker compose version
```

## 构建

在仓库根目录执行：

```powershell
docker build --progress=plain --tag leanci:phase7 .
```

构建使用多阶段 Dockerfile，并通过 BuildKit pip 缓存保存已下载的依赖。首次构建需要下载
Node/Python 基础镜像和 Python 包，在较慢网络下可能明显超过两分钟；不要把任何密钥作为
`--build-arg` 传入。

## 无费用容器冒烟测试

镜像成功后执行：

```powershell
$env:LEANCI_DOCKER_CLI = (Get-Command docker).Source
.\backend\.venv\Scripts\python.exe scripts\docker_smoke.py
```

脚本使用固定的测试专用假凭据，不读取 `.env`，不会调用 DeepSeek。它逐项验证：

- 镜像以非 root 用户运行、入口点固定、只暴露 8000，镜像历史和配置没有密钥模式；
- 镜像内不存在 `/app/.env`；
- 缺少密钥时以配置错误状态 `78` 安全退出，且不输出密钥值；
- 静态前端、配置状态、五个 Sample 和 10 行固定 Benchmark 工件可读取；
- `/api/health` 同时检查 FastAPI、本地 Paritok Proxy 和 hosted GPU；本地 Proxy
  断开时返回 503，镜像 healthcheck 使用运行时 `PORT` 检查该端点；
- 容器内部 `/stats` 可读且不会从公网暴露；
- 假凭据的正式分析在 DeepSeek 前 fail closed，且不返回伪造 Token；
- 分别终止 Proxy 和 FastAPI 时，PID 1 会停止兄弟进程并让容器非零退出。

成功时只输出一行 JSON，顶层为 `"status":"passed"`。脚本拒绝覆盖同名已有容器，只清理
自己创建的三个明确名称容器。

## 真实三例与干净退出

下列命令会调用 Paritok hosted GPU 和 DeepSeek，并可能产生费用。一次只运行一例，编排层
重试为 0，每条命令必须在 120 秒内完成：

```powershell
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample python-pytest
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample typescript-build
.\backend\.venv\Scripts\python.exe scripts\docker_live_verify.py --confirm-cost --sample docker-build
```

脚本通过 Docker `--env-file` 把被 Git 忽略的 `.env` 交给容器，不读取或打印值。每次请求前后
都从容器内部读取 Paritok `/stats`，并严格匹配 API 返回的请求数、原始/压缩/节省 Token。
最后向固定 Python PID 1 发送 SIGTERM，验证 Proxy 与 FastAPI 退出后容器状态为 0，再删除
该次脚本创建的单个明确容器。

Railway 的具体部署与日志判据见 [`DEPLOY_RAILWAY.md`](DEPLOY_RAILWAY.md)，Render 备选见
[`DEPLOY_RENDER_FALLBACK.md`](DEPLOY_RENDER_FALLBACK.md)。

## 本地 Compose

需要用本机 `.env` 启动完整容器时：

```powershell
docker compose up --build --detach
docker compose ps
Invoke-WebRequest "http://127.0.0.1:8000/"
Invoke-RestMethod "http://127.0.0.1:8000/api/config-status"
docker compose down
```

`docker-compose.yml` 只把 FastAPI 绑定到主机回环地址，不映射 8080，并启用
`no-new-privileges` 与全部 capability drop。上面的首页和配置检查不会发起模型请求；
不要在未明确授权费用时点击正式分析或运行 Benchmark。

如 `.env` 中设置了非默认 `PORT`，把示例 URL 的 8000 改为该值。公网部署还必须配置
TLS 网关、身份/滥用控制、分布式限流和费用配额、精确 CORS 白名单以及真实数据保留政策。

## 2026-07-27 验证状态

- Docker Desktop 4.83.0、Docker Engine/CLI 29.6.2、Compose 5.3.1 和 Linux
  `amd64` Engine 已确认可用；
- `hello-world` 已成功运行；
- Compose 配置展开、Dockerfile BuildKit 静态检查、容器边界单元测试和容器依赖审计通过；
- 自动化环境的每条构建命令必须在 120 秒内结束。三条首次构建客户端命令在 pip 依赖层
  完成前达到该上限，但 Docker BuildKit 随后完成并生成了 `leanci:phase6`；
- 镜像配置/历史、镜像内无 `.env`、非 root/端口/入口点、无密钥状态 78、静态前端、
  API、五个 Sample、10 行 Benchmark、假凭据 fail-closed 分析和 Proxy/FastAPI 退出
  联动均已在真实容器验证；DeepSeek 未被调用；
- 完整脚本运行依次发现了响应头键大小写、slim 镜像没有独立 `kill` 命令、同一主机端口
  释放竞态三个测试工具问题，均已修复并有单元回归。达到两次外部预检重试上限后没有再跑
  第四次完整脚本；最后缺失的 FastAPI 退出断言改用独立端口 18087 定向执行并通过。

### 阶段七镜像的当前状态

2026-07-27 当前会话已重新启动 Docker Desktop PID `37156`，Engine 29.6.2
`linux/amd64` 和 Compose 5.3.1 在 30 秒健康检查内可用，Compose 配置有效且固定测试容器名
均未占用。`paritok[proxy]==1.2.7` 官方元数据会额外安装 `numpy`、
`sentence-transformers` 及其完整 ML 依赖链。

前两次 `leanci:phase7` 构建客户端达到 120 秒上限时，执行工具只终止了父会话，实际留下
Docker CLI PID `47448`、`40624`。随后使用明确 PID 和 Git 忽略的
`runtime/phase7-build-controlled.*.log` 做了一次受控诊断；PID `28152` 的日志证明 pip
正在下载完整 extra：

- `numpy` 16.7 MB 用时约 21 秒；
- `transformers` 11.6 MB 用时约 22 秒；
- `scipy` 35.3 MB 用时约 88 秒；
- 随后开始下载 `torch-2.13.0` 的 526.6 MB Linux wheel。

当前网络速度仅约 0.2–1.2 MB/s，因此完整 extra 不可能在本项目的 120 秒 Agent 构建上限内
完成。三个明确 Docker build PID 已逐一核对命令行后终止；没有按名称批量停止进程，没有
清理 BuildKit 缓存。Docker Desktop `buildx history` 仍显示三个 `Running` 记录，但删除时
均返回 `lease ... not found`，且对应客户端 PID 已不存在；这些是无 lease 的历史幽灵记录，
不是可接受的完成证据。最终 `docker image inspect leanci:phase7` 仍返回不存在。

因此本轮没有运行 phase7 `docker_smoke.py` 或三个真实容器样例，也没有可报告的 phase7
容器 PID、端口、stats 或退出状态。阶段六 `leanci:phase6` 的历史成功不能替代当前镜像
证据。后续人工继续时必须从本节“构建”命令重新开始，并在 Docker Desktop 的 Builds 页面
观察完整日志。不要同时启动第二个 build；成功 inspect 新镜像后依次运行无费用 smoke 和
三个单例脚本。不得省略 `[proxy]` extra、使用假 wheel、把超时或阶段六结果改写为阶段七
成功。
