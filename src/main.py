"""
Main FastAPI application for Secure Medical Chat with Guardrails.

This module sets up the FastAPI application with all security layers,
authentication, and monitoring capabilities.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import routers (will be implemented in tasks)
# from src.api.chat import router as chat_router
# from src.api.metrics import router as metrics_router
# from src.api.admin import router as admin_router

app = FastAPI(
    title="Secure Medical Chat API",
    description="A proof-of-concept conversational AI for healthcare with security, privacy, and optimization patterns",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "message": "Secure Medical Chat API",
        "version": "1.0.0",
        "status": "active",
        "features": [
            "PII/PHI Redaction with Microsoft Presidio",
            "Prompt Injection Defense with NeMo Guardrails",
            "Cost Optimization with Helicone",
            "Role-Based Access Control",
            "Comprehensive Audit Logging"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "secure-medical-chat"}

# Include routers (will be uncommented as they are implemented)
# app.include_router(chat_router, prefix="/api", tags=["chat"])
# app.include_router(metrics_router, prefix="/api", tags=["metrics"])
# app.include_router(admin_router, prefix="/api", tags=["admin"])

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )