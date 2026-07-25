"""FastAPI application entry point with a fail-closed Paritok analysis path."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.analysis import AnalysisService
from app.body_limit import RequestBodyLimitMiddleware
from app.config import Settings, get_settings
from app.errors import AppError, attach_request_id, error_responses, register_error_handlers
from app.models import (
    MAX_REQUEST_BYTES,
    AnalysisResult,
    AnalyzeRequest,
    CapturedSampleResult,
    ConfigStatusResponse,
    HealthResponse,
    SamplePayload,
    SampleSummary,
)
from app.paritok import ParitokClient
from app.samples import (
    SampleCaptureNotFoundError,
    SampleNotFoundError,
    list_samples,
    load_sample,
    load_sample_capture,
)


def create_app(
    settings: Settings | None = None,
    *,
    analysis_service: AnalysisService | None = None,
) -> FastAPI:
    """Create an application instance with injectable validated settings."""

    active_settings = settings or get_settings()
    managed_paritok_client: ParitokClient | None = None
    if analysis_service is None:
        managed_paritok_client = ParitokClient(active_settings)
        analysis_service = AnalysisService(active_settings, managed_paritok_client)

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        yield
        if managed_paritok_client is not None:
            await managed_paritok_client.aclose()

    application = FastAPI(
        title=active_settings.app_name,
        version="0.1.0",
        description=(
            "LeanCI formal analysis API. Requests fail closed unless the local "
            "Paritok Proxy and hosted GPU are verified."
        ),
        lifespan=lifespan,
    )
    application.middleware("http")(attach_request_id)
    application.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_bytes=MAX_REQUEST_BYTES,
    )
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
        return await analysis_service.health()

    @application.get("/api/config-status", response_model=ConfigStatusResponse)
    async def config_status() -> ConfigStatusResponse:
        return ConfigStatusResponse(
            deepseek_api_key_configured=active_settings.deepseek_api_key_configured,
            paritok_api_key_configured=active_settings.paritok_api_key_configured,
            llm_provider=active_settings.llm_provider,
            model=active_settings.deepseek_model,
        )

    @application.get("/api/samples", response_model=list[SampleSummary])
    async def samples() -> list[SampleSummary]:
        return list_samples()

    @application.get("/api/samples/{sample_id}", response_model=SamplePayload)
    async def sample(sample_id: str) -> SamplePayload:
        try:
            return load_sample(sample_id)
        except SampleNotFoundError as exc:
            raise AppError(
                status_code=404,
                code="SAMPLE_NOT_FOUND",
                message="The requested bundled sample does not exist.",
            ) from exc

    @application.get(
        "/api/captures/{sample_id}",
        response_model=CapturedSampleResult,
    )
    async def capture(sample_id: str) -> CapturedSampleResult:
        try:
            return load_sample_capture(sample_id)
        except (SampleNotFoundError, SampleCaptureNotFoundError) as exc:
            raise AppError(
                status_code=404,
                code="CAPTURE_NOT_FOUND",
                message="No saved real-run capture exists for this sample.",
            ) from exc

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
        return await analysis_service.analyze(payload.to_untrusted_context())

    return application


app = create_app()
