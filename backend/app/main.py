import os
import time
from collections import defaultdict
from typing import Dict, List
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

from app.api.routes import api_router
from app.api.sse import sse_router
from app.validation.validators import ValidationErrorResponse

# Security configurations
MAX_BODY_SIZE_BYTES = 2 * 1024 * 1024  # 2MB
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app = FastAPI(
    title="Multi-Agent Network Fault Diagnosis System",
    description="Campus Network Telemetry Diagnostic System powered by collaborative specialized agents",
    version="1.0.0",
)

# In-memory sliding-window rate limiter
_request_counts: Dict[str, List[float]] = defaultdict(list)


# Middleware 1: Security Headers & Body Size Limit & Rate Limiting
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # 1. Rate Limiting Check
    if not request.url.path.startswith("/docs") and not request.url.path.startswith("/openapi"):
        timestamps = _request_counts[client_ip]
        # Purge records older than 60s
        _request_counts[client_ip] = [t for t in timestamps if now - t < 60.0]
        if len(_request_counts[client_ip]) >= RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={
                    "error": True,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down.",
                },
            )
        _request_counts[client_ip].append(now)

    # 2. Body Size Limit Check
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE_BYTES:
        return JSONResponse(
            status_code=413,
            content={
                "error": True,
                "error_code": "PAYLOAD_TOO_LARGE",
                "message": f"Payload exceeds limit of {MAX_BODY_SIZE_BYTES // (1024*1024)}MB",
            },
        )

    # Execute request
    response: Response = await call_next(request)

    # 3. Security Response Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self';"
    )

    return response


# Strict CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Global validation error handler
@app.exception_handler(ValidationErrorResponse)
async def validation_error_handler(request: Request, exc: ValidationErrorResponse):
    return JSONResponse(
        status_code=400,
        content=exc.to_dict(),
    )


# General fallback exception handler (no stack trace leak)
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An internal diagnostic server error occurred.",
        },
    )


# Include API routes
app.include_router(api_router, prefix="/api")
app.include_router(sse_router)


@app.get("/")
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "The Signal Room — Multi-Agent Network Fault Diagnosis System",
        "version": "1.0.0",
        "active_agents": [
            "performance_agent",
            "infrastructure_agent",
            "connectivity_agent",
            "correlation_agent",
            "reporting_agent",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=True)
