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
这些字段只来自本例请求前后 `/stats` 差值。`prompt_tokens` 和 `completion_tokens`
单独保存上游 usage，不作为压缩证明。

质量分不由模型产生：

- 根因正确 40；
- 证据正确 20；
- 相关文件正确 15；
- 修复方向正确 15；
- 严格 JSON 完整 10。

确定性规则与 `ground_truth.json` 比对；所有行另保留 `human_review` 字段。失败行得 0 分
并保留，报告不会过滤或只展示最好案例。

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

2026-07-26 的两次 bounded hosted GPU 预检均返回
`failed:PARITOK_GPU_UNAVAILABLE`。因此当前 `results.*` 和 `report.md` 如实保留 10 个
`PREFLIGHT_FAILED` 行，模型请求数为 0，所有 Token 指标为空，结论为“不支持任何 Benchmark
或宣传表述”。hosted GPU 恢复后必须按上面五条命令逐例覆盖这些失败行。
