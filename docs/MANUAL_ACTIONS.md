# LeanCI 人工操作清单

本文件只记录 Codex 不能或不应代替用户完成的安装、账号、网页、密钥和发布操作。完成后请勾选对应项，但不要把任何密钥粘贴到聊天、Issue、截图或 Git。

## 当前最先需要完成

### 1. 安装 Python 3.11.x（Windows）

阶段一后端已经使用 Codex 隔离的 Python 3.12 环境验证通过，但当前系统 PATH 中没有
`python` 或 `py`。仓库根目录还存在一个指向已移除解释器的旧 `.venv`，它没有被修改，
开发脚本也不使用它。为了让普通 PowerShell 和后续阶段稳定可复现，仍需完成以下人工操作。

- [ ] 打开 [Python 官方 Windows 下载页](https://www.python.org/downloads/windows/)。
- [ ] 在 Python 3.11 系列中下载最新的 **Windows installer (64-bit)**。
- [ ] 启动安装器，勾选 **Add python.exe to PATH**。
- [ ] 选择 **Customize installation** 时保留 `pip` 和 Python launcher；安装位置可使用默认值。
- [ ] 安装完成后关闭并重新打开终端或 Codex。
- [ ] 在 PowerShell 中运行：

```powershell
python --version
py -3.11 --version
python -m pip --version
```

预期至少有一种 Python 命令显示 `Python 3.11.x`，且 pip 可用。若 `python` 打开 Microsoft Store，请在 Windows“管理应用执行别名”中关闭 Store 的 `python.exe`/`python3.exe` 别名，再重开终端。

- [ ] 如需清理根目录中损坏的 `.venv`，请在确认路径为本项目后手动删除该单个目录；不要使用批量删除命令。
- [ ] 用已安装的 Python 为后端创建可复现环境并安装锁定依赖：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

若 `backend/.venv` 已存在且仍指向 Codex 运行时，请在确认路径后由你手动删除该目录，再用
系统 Python 重新创建。不要提交任何 `.venv` 内容。

## 开发后续需要

### 2. 安装 Docker Desktop

- [ ] 打开 [Docker Desktop for Windows 官方页面](https://www.docker.com/products/docker-desktop/)。
- [ ] 下载并安装 Docker Desktop。
- [ ] 安装器提示时启用 WSL 2 后端；如系统要求，按提示重启 Windows。
- [ ] 启动 Docker Desktop，等待状态显示 Engine running。
- [ ] 在 PowerShell 中验证：

```powershell
docker --version
docker compose version
docker run --rm hello-world
```

首次阶段不需要 Docker；可在进入 Docker 阶段前完成。

### 3. 注册并确认 Devpost 赛事

- [ ] 打开 [Build with Paritok: The Token-Efficiency Hackathon](https://build-with-paritok.devpost.com/)。
- [ ] 登录或注册 Devpost。
- [ ] 点击 Join hackathon/加入赛事，并确认 LeanCI 所属团队或个人身份。
- [ ] 打开 Overview、Rules、Details/Requirements 页面。
- [ ] 记录页面显示的精确截止时区、必填字段、演示链接、视频、开源和资格要求。
- [ ] 不根据本文猜测视频时长或评审标准；官方页面有变化时，以页面为准并更新项目文档。

### 4. 创建 DeepSeek API Key

- [ ] 打开 [DeepSeek 开放平台](https://platform.deepseek.com/) 并登录。
- [ ] 进入 API Keys 页面，创建一个仅供 LeanCI 使用的新 Key。
- [ ] 创建后立即复制到安全的密码管理器；关闭页面后通常无法再次查看完整 Key。
- [ ] 检查账户余额，确保至少可以运行少量开发请求和双跑 benchmark。
- [ ] 在项目根目录复制环境示例：

```powershell
Copy-Item ".env.example" ".env"
```

- [ ] 用本地文本编辑器打开 `.env`，只填写：

```dotenv
DEEPSEEK_API_KEY=<在本机填写，不要发送给 Codex>
```

- [ ] 确认 `.env` 仍被 Git 忽略：

```powershell
git status --short --ignored
```

不得把 Key 写入 `.env.example`、`paritok.yaml`、README、测试或截图。

### 5. 创建 Paritok API Key

- [ ] 打开 [Paritok](https://paritok.com/) 并登录/注册。
- [ ] 进入 Dashboard → API keys。
- [ ] 创建一个 LeanCI 专用 Key，保存到密码管理器。
- [ ] 只在本机 `.env` 中填写：

```dotenv
PARITOK_API_KEY=<在本机填写，不要发送给 Codex>
```

- [ ] 不要把 Key 写入 `paritok.yaml`。该文件只配置 `use_gpu_server: true`，运行时从环境变量读取 Key。
- [ ] 等 Paritok 阶段代码完成后，按 README 启动代理并检查：

```powershell
Invoke-RestMethod "http://127.0.0.1:8080/health"
Invoke-RestMethod "http://127.0.0.1:8080/stats"
```

如果代理只警告 hosted GPU 不可用但仍返回本地 health OK，不要继续正式分析；LeanCI 必须显示不可用错误。

## 发布阶段需要

### 6. 创建公开 GitHub 仓库

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

### 7. 选择并配置 Docker 托管平台

- [ ] 在 Docker MVP 通过后选择支持单容器、平台 `PORT` 和环境变量的托管平台。
- [ ] 在平台网页中添加 `DEEPSEEK_API_KEY`、`PARITOK_API_KEY` 和 README 列出的非敏感配置。
- [ ] 不把密钥写入 Dockerfile、镜像构建参数、仓库变量文件或公开日志。
- [ ] 确认只暴露 FastAPI 的平台端口；不得公开映射 `8080`。
- [ ] 部署后访问 `/api/health`，确认 FastAPI、本地代理和 hosted GPU 均健康。
- [ ] 使用内置示例完成一次正式分析和一次显式 benchmark。

具体平台与点击步骤将在选择平台后补充，本阶段不假定某一家服务。

### 8. 准备并提交 Devpost 材料

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
