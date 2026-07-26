# 固定演示案例

本目录包含五个完全本地、固定、可重复、具有明确正确答案的 CI 失败案例：

| ID | 类型 | 长日志 | 相关文件 | 根因 |
| --- | --- | ---: | ---: | --- |
| `python-pytest` | Python pytest | 69.5 KiB | 3 | 退避公式的运算优先级使第 4 次重试得到 15 而不是上限 16 |
| `typescript-build` | TypeScript build | 73.9 KiB | 3 | `string \| undefined` 被赋给必需的 `string` 配置 |
| `docker-build` | Docker BuildKit | 40.1 KiB | 3 | `.dockerignore` 的 `*.json` 排除了 `package-lock.json` |
| `dependency-resolution` | npm dependency resolution | 63.6 KiB | 2 | React 19 与只接受 React 18 的 peer dependency 冲突 |
| `github-actions-environment` | GitHub Actions environment | 56.2 KiB | 2 | 未设置的仓库变量使 `DEPLOY_ENV` 为空 |

每个目录都包含：

- `ci.log`：真实格式、无密钥、不会被执行的长 CI 日志；
- 少量相关源代码或配置；
- `ground_truth.json`：明确根因、预期相关文件、修复方向和最小原始 Token 要求；
- 阶段四前三例成功完成真实链路采集后生成的 `demo_result.json`：本次分析结果和 Paritok
  `/stats` 前后快照，不包含 Paritok 自带的美元估算，也不包含任何 Key；
- 阶段五五例共同进入固定 Benchmark；结果写入 `benchmarks/`，不把 ground truth 提交给模型。

前端只向模型提交 `ci.log` 和相关文本文件，绝不提交 `ground_truth.json`，避免泄露答案。
Sample 按钮通过固定 ID 加载这些资产；API 不接受调用者提供的文件系统路径。

重新生成确定性日志（只写固定文本，不运行示例代码）：

```powershell
.\backend\.venv\Scripts\python.exe scripts\generate_demo_samples.py
```

在 Proxy、FastAPI 和 hosted GPU 均健康后，显式执行前三例真实付费分析并保存录屏状态。
每条命令只运行一个案例，最长等待约 110 秒：

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample docker-build
```

不带 `--confirm-cost` 时脚本只返回
`skipped:COST_CONFIRMATION_REQUIRED`，不会发送模型请求。

2026-07-26 已完成的真实正式链路采集：

| ID | Original Tokens | Compressed Tokens | Tokens Saved | 节省率 |
| --- | ---: | ---: | ---: | ---: |
| `python-pytest` | 23,906 | 332 | 23,574 | 98.61% |
| `typescript-build` | 20,542 | 847 | 19,695 | 95.88% |
| `docker-build` | 8,325 | 117 | 8,208 | 98.59% |

每个数字都来自对应 `demo_result.json` 内单次请求的 Paritok `/stats` 前后差值。
