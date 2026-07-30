# 录屏镜头清单

目标成片 `2:50`，硬上限 `2:59`。录制前关闭通知，浏览器缩放设为 100%，隐藏书签栏和账号
头像，不打开 `.env`、Railway Variables、Paritok Dashboard Key 页面或终端环境变量。

| 时间 | 画面 | 操作 | 旁白重点 |
| --- | --- | --- | --- |
| 0:00–0:15 | GitHub README → 首页 | 展示两个 Built with 徽章和产品标题 | 长 CI 日志噪声；Paritok 压缩，DeepSeek 诊断 |
| 0:15–0:35 | 一键 Sample + 长日志 | 选 Python pytest，滚动日志，展示两个文件 | 69.5 KiB；不克隆、不运行，只当证据 |
| 0:35–0:55 | Formal route + loading | 展示三段健康状态；点击 Analyze，或剪到保存 capture | 正式链路不可绕过 Paritok，失败即关闭 |
| 0:55–1:30 | 结果详情 | 根因 → Evidence → Relevant Files → Patch | 运算优先级根因；证据和补丁可复核但不执行 |
| 1:30–1:52 | Token 面板 | 定格 `23,906 → 332`、`23,574`、`98.61%` | 数字来自本请求 `/stats` 差值 |
| 1:52–2:18 | Benchmark 页 | 展示 2 compressed、3 skipped、质量变化 | 85.53% 只属于 2 行；质量变化 -19.00 |
| 2:18–2:36 | README 架构图 | 缓慢移动指针走完整链路 | FastAPI → Proxy → hosted GPU → DeepSeek |
| 2:36–2:50 | GitHub 仓库 | 展示 examples、benchmarks、SECURITY、LICENSE | 公开源码、可复现、Apache 2.0 |

## 录制素材入口

- 首页：`http://127.0.0.1:5173/`
- 保存的真实 Python 结果：`http://127.0.0.1:5173/?capture=python-pytest`
- 保存的真实 TypeScript 结果：`http://127.0.0.1:5173/?capture=typescript-build`
- 保存的真实 Docker 结果：`http://127.0.0.1:5173/?capture=docker-build`
- Benchmark：`http://127.0.0.1:5173/?view=benchmark`
- GitHub：`https://github.com/Gxinxin-sudo/LeanCI`

## 剪辑规则

- 不把保存 capture 冒充“刚刚完成的实时请求”；画面上的 saved real run 标识要保留。
- 不展示或宣称公开 live Demo；当前 Project URL 使用公开仓库。
- 不把三个 demo capture 的 `98%+` 与五例 Benchmark 的 `85.53%` 混为一个平均值。
- 不说“费用降低了多少账单”；只说按价格快照计算的输入费用估算。
- 不使用有版权风险的音乐；最终导出后重新计时并确认 `< 3:00`。
