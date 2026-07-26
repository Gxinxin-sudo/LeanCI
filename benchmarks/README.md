# Benchmarks

本目录保存五个固定案例的可审计 Benchmark 工件：

- `results.json`：严格结构化行、原始模型分析、确定性评分和人工复核字段；
- `results.csv`：适合表格审阅的平面字段；
- `report.md`：汇总、完整失败表、费用口径和可复现命令。

## 公平性约束

每例固定顺序为 `baseline_uncompressed` → `paritok`。两路首轮请求使用相同
`deepseek-v4-flash`、系统提示、用户提示、`max_tokens=4096`、thinking disabled、
JSON object 配置和案例内容，`initial_messages_sha256` 必须一致。唯一对比变量是请求是否
经过 Paritok。

Baseline 不经过 Paritok，因此 `original_tokens`、`compressed_tokens`、`tokens_saved`
和 `compression_ratio` 必须为 `null`，不能用 DeepSeek usage 或字符数冒充。Paritok
这些字段只在本例请求前后 `/stats` 差值证明实际发生压缩时保存。官方 trace 已确认的
`below_refusal_threshold` 低收益透传标为 `compression_skipped`，这些 Token 字段和
质量字段均为 `null`（不适用）。`prompt_tokens` 和 `completion_tokens` 单独保存上游
usage，不作为压缩证明。

质量分不由模型产生：

- 根因正确 40；
- 证据正确 20；
- 相关文件正确 15；
- 修复方向正确 15；
- 严格 JSON 完整 10。

确定性规则与 `ground_truth.json` 比对；所有行另保留 `human_review` 字段。失败行得 0 分
并保留，正常跳过行不评分，报告不会过滤或只展示最好案例。

## 运行

先启动 Paritok Proxy，并完成无费用 hosted GPU 预检。每条命令预期发出 2 次模型请求；
两路各允许一次 JSON 修复，因此每条硬上限 4 次；网络重试为 0。为满足 120 秒命令上限，
一次只运行一个案例：

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case docker-build
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case dependency-resolution
.\backend\.venv\Scripts\python.exe scripts\run_benchmark.py --confirm-cost --case github-actions-environment
```

不带 `--confirm-cost` 时模型请求数为 0。一次五例完整成功运行预期 10 次模型请求，所有
JSON 都需修复时最多 20 次。

## 当前固定工件

2026-07-26 真实运行发出 10 次模型请求，0 次 JSON 修复、0 次网络重试和 0 次命令超时。
工件保留全部 10 行：5 个 Baseline 成功，3 个 Paritok 行因官方
`below_refusal_threshold` 正常跳过，2 个 Paritok 行有有效压缩差值。Python 行同时保留
DeepSeek 上游超时；Docker 行保留实际压缩块未达到 5,000 Token 验收门槛的失败。

只在 2 个实际压缩行上计算出的平均 Token 节省率为 `91.70%`。skipped 行不进入 Token
或质量平均值；没有成功 Paritok 分析可比较，因此质量变化为不适用。该结果不能外推为
五例整体平均、普遍质量保持、生产稳定性或实际账单节省。
