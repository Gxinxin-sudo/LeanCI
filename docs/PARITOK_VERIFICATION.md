# Paritok 正式链路验证

## 验证目标

一次成功的 `/api/analyze` 必须同时证明：

1. 本地 Paritok `/health` 可用；
2. 固定 hosted GPU `/test` 在请求前后均可用；
3. 请求前后 `/stats` 计数单调且字段一致；
4. `/stats.total_requests` 差值与本次 Provider 的实际请求尝试次数相同；
5. Provider 身份为 `paritok_deepseek`，且正式结果不采用 DeepSeek `usage` 冒充压缩指标；
6. 模型固定为 `deepseek-v4-flash`。

任一证明失败，分析结果都会被丢弃并返回 503；不会回退到 Direct 或 Mock。

## 连接预检

先按 [Windows 配置](PARITOK_SETUP_WINDOWS.md)启动 Proxy 与 FastAPI，然后运行：

```powershell
Invoke-RestMethod "http://127.0.0.1:8080/health"
Invoke-RestMethod "http://127.0.0.1:8080/stats"
.\backend\.venv\Scripts\python.exe scripts\test_paritok_connection.py
Invoke-RestMethod "http://127.0.0.1:8000/api/health"
```

成功的连接脚本只输出安全 JSON：

- `status: "success"`
- `model: "deepseek-v4-flash"`
- `proxy.status: "ok"` 和代理版本
- `hosted_gpu.available: true`
- `stats` 中的累计 Token 计数

它不调用 DeepSeek，不打印密钥，也不输出 Paritok 的美元估算字段。
Windows 启动脚本会在监听 8080 前执行同一认证预检；失败时直接退出，不允许代理以
未压缩 passthrough 模式继续服务。

## 执行超过 5,000 Token 的真实验证

此步骤会产生一次真实 Paritok/DeepSeek 请求和费用。确认 Proxy、FastAPI、DeepSeek 余额与
两个 Key 后，从仓库根目录显式授权：

```powershell
.\backend\.venv\Scripts\python.exe scripts\verify_paritok_long_request.py --confirm-cost
```

脚本发送约 116,600 字符的惰性 CI 证据，随后只输出分析响应中的安全压缩指标。它以本次
`/stats` 差值为准，只有 `original_tokens > 5000` 才返回 `status: "success"`。不带
`--confirm-cost` 时脚本安全跳过，绝不会发起付费请求。

## 成功时应看到

`compression_stats` 应至少包含：

```json
{
  "available": true,
  "paritok_connected": true,
  "hosted_gpu_available": true,
  "verification": "local_health+hosted_gpu_preflight+stats_delta",
  "proxy_version": "1.0.0",
  "model": "deepseek-v4-flash",
  "proxy_requests": 1,
  "original_tokens": 5001,
  "compressed_tokens": 2500,
  "saved_tokens": 2501,
  "compression_ratio": 0.4999,
  "cumulative": {},
  "cost_estimate": {
    "estimated_input_cost_saved_usd": 0.00035014,
    "input_cache_miss_usd_per_m_tokens": 0.14,
    "pricing_snapshot_date": "2026-07-26",
    "disclaimer": "Estimate from LeanCI's configured DeepSeek price; not an actual bill."
  }
}
```

以上数字只是字段示例，不是预期固定值。真实值必须来自本次请求前后 `/stats` 的差值。
验证重点：

- `original_tokens > 5000`
- `0 <= compressed_tokens <= original_tokens`
- `saved_tokens = original_tokens - compressed_tokens`
- `compression_ratio = compressed_tokens / original_tokens`
- `proxy_requests >= 1`，且与实际请求/一次修复尝试数一致
- `cumulative.total_requests` 随请求增加
- UI 同时显示本次指标、累计统计、模型与费用估算免责声明

## 顺序运行三个固定演示案例

确认健康检查全部通过且 DeepSeek 余额可用后：

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample docker-build
```

脚本只读取 `python-pytest`、`typescript-build` 和 `docker-build` 三个固定 ID，并为每个
案例执行。每条命令只发出一次分析，单次最长等待约 110 秒：

1. 从 FastAPI Sample API 读取固定日志和相关文件；
2. 读取 Paritok `/stats` before；
3. 调用正式 `/api/analyze`；
4. 读取 `/stats` after；
5. 校验外层 delta 与 API 内层 delta 完全一致；
6. 要求 `original_tokens > 5000`、固定模型、所有必需 ground-truth 相关文件和修复关键词；
7. 保存不含 Key、请求头和 Paritok 美元字段的 `examples/<id>/demo_result.json`。

不带 `--confirm-cost` 时不会发送模型请求。任何案例失败都会返回非零状态；不得手动补写
Token 或用 Mock 替代。

### 2026-07-26 真实验证记录

| Sample | Requests | Original | Compressed | Saved | Ratio | Cost saved estimate | Time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `python-pytest` | 1 | 23,906 | 332 | 23,574 | 0.013888 | $0.00330036 | 5,168 ms |
| `typescript-build` | 1 | 20,542 | 847 | 19,695 | 0.041233 | $0.00275730 | 4,674 ms |
| `docker-build` | 1 | 8,325 | 117 | 8,208 | 0.014054 | $0.00114912 | 4,574 ms |

三例均经本地 Paritok Proxy、认证 hosted GPU 和 `deepseek-v4-flash` 完成，内外两层
stats delta 一致，ground truth 文件/修复关键词校验通过。原始 before/after 快照保存在
各自的 `demo_result.json`；页面状态和截图均由这些文件直接加载。

## 费用口径

Paritok `/stats` 可能包含 `estimated_cost_saved_usd`，并可能对未知模型采用默认价格。
LeanCI 会解析后丢弃这个字段，API、UI 和连接脚本都不会把它展示为 DeepSeek 的真实费用。

LeanCI 的金额只按项目配置计算：

```text
estimated_input_cost_saved_usd =
  本次 saved_tokens × DEEPSEEK_INPUT_CACHE_MISS_USD_PER_M / 1,000,000
```

价格快照为 2026-07-26：cache miss 输入 `$0.14/M`、cache hit 输入 `$0.0028/M`、输出
`$0.28/M`。金额明确标注为估算值，不是账单。

## 自动化测试

不产生真实费用的全套检查：

```powershell
.\backend\.venv\Scripts\python.exe -m ruff check backend scripts
.\backend\.venv\Scripts\python.exe -m ruff format --check backend scripts
.\backend\.venv\Scripts\python.exe -m pytest backend\tests
```

真实正式链路集成测试必须显式 opt-in，且 Proxy 已运行：

```powershell
$env:RUN_PARITOK_INTEGRATION = "1"
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_paritok_integration.py -m integration
Remove-Item Env:RUN_PARITOK_INTEGRATION
```

独立 Direct DeepSeek 连接测试仍只用于故障定位/未来未压缩 benchmark，不属于正式分析：

```powershell
$env:RUN_DEEPSEEK_INTEGRATION = "1"
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_deepseek_integration.py -m integration
Remove-Item Env:RUN_DEEPSEEK_INTEGRATION
```
