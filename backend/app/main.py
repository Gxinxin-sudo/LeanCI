"""FastAPI application entry point; application analysis remains mock-only."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.errors import AppError, attach_request_id, error_responses, register_error_handlers
from app.mock_analysis import build_mock_analysis
from app.models import (
    DEMO_NOTICE,
    AnalysisResult,
    AnalyzeRequest,
    ConfigStatusResponse,
    HealthResponse,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application instance with injectable validated settings."""

    active_settings = settings or get_settings()
    application = FastAPI(
        title=active_settings.app_name,
        version="0.1.0",
        description=(
            "LeanCI mock application API. DeepSeek is available only through the "
            "separate connection-test script."
        ),
    )
    application.middleware("http")(attach_request_id)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(application)

    @application.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="leanci-api",
            mode="demo",
            paritok_connected=False,
            deepseek_called=False,
            message=DEMO_NOTICE,
        )

    @application.get("/api/config-status", response_model=ConfigStatusResponse)
    async def config_status() -> ConfigStatusResponse:
        return ConfigStatusResponse(
            deepseek_api_key_configured=active_settings.deepseek_api_key_configured,
            paritok_api_key_configured=active_settings.paritok_api_key_configured,
        )

    @application.post(
        "/api/analyze",
        response_model=AnalysisResult,
        responses=error_responses(),
    )
    async def analyze(payload: AnalyzeRequest) -> AnalysisResult:
        if not payload.log_text.strip():
            raise AppError(
                status_code=422,
                code="EMPTY_LOG",
                message="Paste a CI log before starting analysis.",
            )
        if len(payload.log_text) > active_settings.max_log_characters:
            raise AppError(
                status_code=413,
                code="LOG_TOO_LARGE",
                message="The CI log exceeds the configured character limit.",
            )
        return build_mock_analysis()

    return application


app = create_app()
