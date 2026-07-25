# Test layout

- `backend/tests/`：FastAPI 契约、错误格式、配置脱敏、严格 Pydantic 模型，以及
  LLM Provider 参数、重试、错误映射和一次 JSON 修复。
- `frontend/src/**/*.test.tsx`：组件状态、交互、API 成功/失败路径和错误边界。

真实 DeepSeek 集成测试只有在本地 `DEEPSEEK_API_KEY` 存在时才运行，否则安全跳过。
FastAPI 应用测试始终使用 Mock，不调用任何外部 AI 服务。
