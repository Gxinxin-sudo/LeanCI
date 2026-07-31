# Verifying the formal Paritok route

A successful formal analysis proves all of the following:

1. Local Paritok `/health` is available.
2. The fixed hosted-GPU `/test` endpoint succeeds before and after the request.
3. Cumulative `/stats` fields are valid and monotonic.
4. The `total_requests` delta equals the provider's actual request attempts.
5. The provider is `paritok_deepseek`; DeepSeek usage is not used as compression
   evidence.
6. The model is `deepseek-v4-flash`.

If any proof fails, LeanCI discards the diagnosis and returns a safe failure. It
never falls back to Direct or Mock.

## Free connection preflight

Start the proxy and FastAPI as described in
[Windows setup](PARITOK_SETUP_WINDOWS.md), then run:

```powershell
Invoke-RestMethod "http://127.0.0.1:8080/health"
Invoke-RestMethod "http://127.0.0.1:8080/stats"
.\backend\.venv\Scripts\python.exe scripts\test_paritok_connection.py
Invoke-RestMethod "http://127.0.0.1:8000/api/health"
```

The connection script outputs sanitized JSON with:

- `status: "success"`
- `model: "deepseek-v4-flash"`
- local proxy status and version
- `hosted_gpu.available: true`
- cumulative token counters

It does not call DeepSeek, print a credential, or expose Paritok's USD estimate.
The Windows startup script performs the same authenticated preflight before it
starts the local proxy.

## Paid long-context verification

This command makes one real Paritok/DeepSeek request and may incur a DeepSeek
charge:

```powershell
.\backend\.venv\Scripts\python.exe scripts\verify_paritok_long_request.py --confirm-cost
```

The script sends fixed, inert CI evidence and prints only safe compression metrics.
Success requires `original_tokens > 5000`. Without `--confirm-cost`, it sends no
model request.

A valid result has this shape:

```json
{
  "available": true,
  "paritok_connected": true,
  "hosted_gpu_available": true,
  "verification": "local_health+hosted_gpu_preflight+stats_delta",
  "model": "deepseek-v4-flash",
  "proxy_requests": 1,
  "original_tokens": 5001,
  "compressed_tokens": 2500,
  "saved_tokens": 2501,
  "compression_ratio": 0.4999,
  "cost_estimate": {
    "estimated_input_cost_saved_usd": 0.00035014,
    "input_cache_miss_usd_per_m_tokens": 0.14,
    "pricing_snapshot_date": "2026-07-31",
    "disclaimer": "Estimate from LeanCI's configured DeepSeek price; not an actual bill."
  }
}
```

The numbers above illustrate fields only. Real values must come from the request's
before/after `/stats` delta. Validate:

- `original_tokens > 5000`
- `0 <= compressed_tokens <= original_tokens`
- `saved_tokens = original_tokens - compressed_tokens`
- `compression_ratio = compressed_tokens / original_tokens`
- `proxy_requests` matches the request count, including an optional repair

## Refresh fixed sample results

These commands make paid requests. Run one case at a time:

```powershell
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample python-pytest
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample typescript-build
.\backend\.venv\Scripts\python.exe scripts\run_demo_samples.py --confirm-cost --sample docker-build
```

For each case the script:

1. loads a fixed sample from FastAPI;
2. reads proxy stats before;
3. calls the formal analysis route;
4. reads proxy stats after;
5. matches the outer delta to the API's inner proof;
6. checks the fixed model, required files, and fix keywords;
7. saves a sanitized `examples/<id>/demo_result.json`.

No ground-truth answer is sent to the model. Without `--confirm-cost`, no request is
made.

## Saved reference observations

The controlled 2026-07-26 runs produced:

| Sample | Requests | Original | Compressed | Saved | Savings | Time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `python-pytest` | 1 | 23,906 | 332 | 23,574 | 98.61% | 5,168 ms |
| `typescript-build` | 1 | 20,542 | 847 | 19,695 | 95.88% | 4,674 ms |
| `docker-build` | 1 | 8,325 | 117 | 8,208 | 98.59% | 4,574 ms |

All values are preserved in their corresponding sanitized result files. They are
historical observations, not expected constants for future requests.

## Cost semantics

LeanCI parses and excludes Paritok's `estimated_cost_saved_usd`. It calculates an
input-only estimate from the configured DeepSeek cache-miss price:

```text
estimated_input_cost_saved_usd =
  saved_tokens * DEEPSEEK_INPUT_CACHE_MISS_USD_PER_M / 1,000,000
```

The current configuration was verified against DeepSeek's official pricing on
2026-07-31: cache-hit input `$0.0028/M`, cache-miss input `$0.14/M`, and output
`$0.28/M`. The displayed amount is not an invoice.

## Automated checks

The default suite is free:

```powershell
.\backend\.venv\Scripts\python.exe -m ruff check backend scripts
.\backend\.venv\Scripts\python.exe -m ruff format --check backend scripts
.\backend\.venv\Scripts\python.exe -m pytest backend\tests
```

Live integration tests are explicit opt-ins:

```powershell
$env:RUN_PARITOK_INTEGRATION = "1"
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_paritok_integration.py -m integration
Remove-Item Env:RUN_PARITOK_INTEGRATION
```

The Direct DeepSeek integration test is for troubleshooting and baseline testing
only. It is not the formal application route.
