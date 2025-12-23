"""
Production-ready FastAPI application with OpenTelemetry observability.

This application includes:
- OpenTelemetry tracing and metrics
- Comprehensive health checks
- CORS support
- Structured error handling
- Request ID tracking
- Streaming response support
"""

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Validate critical environment variables
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY environment variable is not set. "
        "Please add it to your .env file or set it in your environment."
    )

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import logging
from datetime import datetime
import uuid

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# Application routers
from routers import prompt_router


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra fields in .env that aren't defined here
    )
    
    app_name: str = "fastapi-starter"
    app_version: str = "1.0.0"
    environment: str = "development"
    
    # CORS settings
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # OpenTelemetry settings
    otel_enabled: bool = True
    otel_exporter_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "fastapi-app"


settings = Settings()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    service: str
    version: str
    dependencies: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    request_id: str
    timestamp: str


# ============================================================================
# OPENTELEMETRY SETUP
# ============================================================================

def setup_telemetry() -> None:
    """Configure OpenTelemetry tracing and metrics."""
    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled")
        return
    
    # Create resource with service information
    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "service.version": settings.app_version,
        "deployment.environment": settings.environment,
    })
    
    # Setup tracing
    trace_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)
    
    # Setup metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=settings.otel_exporter_endpoint)
    )
    metric_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(metric_provider)
    
    logger.info(f"OpenTelemetry initialized: {settings.otel_exporter_endpoint}")


# Get tracer and meter for custom instrumentation
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Custom metrics
request_counter = meter.create_counter(
    "api_requests_total",
    description="Total number of API requests",
    unit="1"
)

error_counter = meter.create_counter(
    "api_errors_total",
    description="Total number of API errors",
    unit="1"
)


# ============================================================================
# DEPENDENCY CHECKS
# ============================================================================

async def check_database() -> dict:
    """
    Check database connectivity.
    
    Replace this with your actual database check:
    Example: await db.execute("SELECT 1")
    """
    # Simulated check - implement your actual database check
    return {"status": "healthy", "latency_ms": 5}


async def check_cache() -> dict:
    """
    Check cache connectivity.
    
    Replace this with your actual cache check:
    Example: await redis.ping()
    """
    # Simulated check - implement your actual cache check
    return {"status": "healthy", "latency_ms": 2}


# ============================================================================
# APPLICATION LIFESPAN
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for handling startup and shutdown events.
    
    Startup tasks:
    - Initialize OpenTelemetry
    - Connect to databases
    - Initialize cache connections
    - Load configuration
    - Warm up ML models
    
    Shutdown tasks:
    - Close database connections
    - Close cache connections
    - Flush metrics/traces
    - Clean up resources
    """
    # ===== STARTUP =====
    logger.info(f"Starting {settings.app_name} v{settings.app_version} ({settings.environment})")
    
    # Verify OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        logger.info(f"OpenAI API key loaded (length: {len(api_key)} chars)")
    else:
        logger.error("OpenAI API key NOT loaded - prompt generation will fail!")
    
    # Initialize OpenTelemetry
    setup_telemetry()
    
    # Add your startup logic here:
    # - Database connection pools
    # - Cache connections (Redis, etc.)
    # - Load ML models
    # - Initialize external service clients
    # Example:
    # app.state.db = await init_database()
    # app.state.redis = await init_redis()
    
    logger.info("Application startup complete")
    
    yield
    
    # ===== SHUTDOWN =====
    logger.info("Initiating graceful shutdown...")
    
    # Add your shutdown logic here:
    # - Close database connections
    # - Close cache connections
    # - Flush metrics/traces
    # - Save state if needed
    # Example:
    # await app.state.db.close()
    # await app.state.redis.close()
    
    logger.info("Application shutdown complete")


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    description="Production-ready FastAPI with OpenTelemetry observability",
    version=settings.app_version,
    lifespan=lifespan,
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Instrument FastAPI with OpenTelemetry
if settings.otel_enabled:
    FastAPIInstrumentor.instrument_app(app)


# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

# Include the prompt generation router
app.include_router(prompt_router)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, 
    exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors with detailed logging."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        "Validation error",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "errors": exc.errors()
        }
    )
    
    error_counter.add(1, {"error_type": "validation", "path": request.url.path})
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation Error",
            message="Invalid request parameters",
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request, 
    exc: Exception
) -> JSONResponse:
    """Handle all uncaught exceptions with proper logging and user-friendly messages."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    # Log full error details internally
    logger.error(
        "Unhandled exception",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error": str(exc)
        },
        exc_info=True
    )
    
    error_counter.add(1, {"error_type": "internal", "path": request.url.path})
    
    # Return generic error to client (don't expose internal details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An unexpected error occurred. Please contact support with the request ID.",
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat()
        ).model_dump()
    )


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get(
    "/",
    tags=["Root"],
    summary="API information",
    description="Root endpoint with API details and available endpoints"
)
async def root(request: Request) -> dict:
    """Root endpoint with API information."""
    request_counter.add(1, {"endpoint": "/", "method": "GET"})
    
    return {
        "service": settings.otel_service_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "health": "/health",
            "readiness": "/ready",
            "liveness": "/alive",
            "prompt": "/prompt",
            "docs": "/docs",
            "openapi": "/openapi.json"
        },
        "request_id": getattr(request.state, "request_id", None)
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Health check with dependency status",
    description="Returns health status of the application and its dependencies"
)
async def health_check(request: Request) -> JSONResponse:
    """
    Comprehensive health check endpoint.
    
    Returns:
        200 if all dependencies are healthy
        503 if any critical dependency is unhealthy
    """
    with tracer.start_as_current_span("health_check") as span:
        dependencies = {}
        overall_status = "healthy"
        
        # Check database
        try:
            dependencies["database"] = await check_database()
        except Exception as e:
            dependencies["database"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "degraded"
            span.set_attribute("db.healthy", False)
            logger.error(f"Database health check failed: {str(e)}")
        
        # Check cache
        try:
            dependencies["cache"] = await check_cache()
        except Exception as e:
            dependencies["cache"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "degraded"
            span.set_attribute("cache.healthy", False)
            logger.error(f"Cache health check failed: {str(e)}")
        
        # Determine HTTP status code
        status_code = (
            status.HTTP_200_OK if overall_status == "healthy" 
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        
        response = HealthResponse(
            status=overall_status,
            timestamp=datetime.utcnow().isoformat(),
            service=settings.otel_service_name,
            version=settings.app_version,
            dependencies=dependencies
        )
        
        span.set_attribute("health.status", overall_status)
        request_counter.add(1, {"endpoint": "/health", "status": overall_status})
        
        return JSONResponse(content=response.model_dump(), status_code=status_code)


@app.get(
    "/ready",
    tags=["Health"],
    summary="Readiness probe",
    description="Quick check if app can accept traffic (for Kubernetes)"
)
async def readiness_check() -> dict:
    """
    Lightweight readiness check for container orchestration.
    Used by Kubernetes to determine if the pod can receive traffic.
    """
    return {"ready": True, "timestamp": datetime.utcnow().isoformat()}


@app.get(
    "/alive",
    tags=["Health"],
    summary="Liveness probe",
    description="Minimal check if app is running (for Kubernetes)"
)
async def liveness_check() -> dict:
    """
    Minimal liveness check for container orchestration.
    Used by Kubernetes to determine if the pod should be restarted.
    """
    return {"alive": True, "timestamp": datetime.utcnow().isoformat()}


@app.get(
    "/stream-example",
    tags=["Examples"],
    summary="Example streaming endpoint",
    description="Demonstrates streaming response with OpenTelemetry tracing"
)
async def stream_example() -> StreamingResponse:
    """
    Example streaming endpoint with OpenTelemetry tracing.
    
    This demonstrates how to implement Server-Sent Events (SSE)
    or other streaming responses with proper tracing.
    """
    async def generate_stream():
        with tracer.start_as_current_span("stream_generation"):
            for i in range(5):
                with tracer.start_as_current_span(f"stream_chunk_{i}"):
                    yield f"data: Message {i + 1}\n\n"
                    # In production, you might:
                    # - Stream database query results
                    # - Stream AI/LLM responses
                    # - Stream real-time events
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level="info",
        access_log=True
    )