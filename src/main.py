"""
Main FastAPI application for Secure Medical Chat with Guardrails.

This module sets up the FastAPI application with all security layers,
authentication, and monitoring capabilities.
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .llm.mock_llm_gateway import MockLLMGateway

try:
    from .llm.llm_gateway import LLMGateway
    from .llm.helicone_client import HeliconeConfig
    LLM_GATEWAY_AVAILABLE = True
except ImportError:
    LLMGateway = MockLLMGateway
    HeliconeConfig = None
    LLM_GATEWAY_AVAILABLE = False
from .api.metrics import router as metrics_router, init_metrics_router
from .api.chat import router as chat_router, init_chat_router
from .api.dashboard import router as dashboard_router, init_dashboard_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global LLM Gateway instance
llm_gateway: LLMGateway = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    global llm_gateway
    
    # Startup
    logger.info("Starting Secure Medical Chat API...")
    
    try:
        if LLM_GATEWAY_AVAILABLE and os.getenv("HELICONE_API_KEY"):
            # Initialize Helicone configuration
            helicone_config = HeliconeConfig(
                api_key=os.getenv("HELICONE_API_KEY"),
                enable_caching=os.getenv("HELICONE_ENABLE_CACHING", "true").lower() == "true",
                cache_ttl_seconds=int(os.getenv("HELICONE_CACHE_TTL", "86400")),
                enable_cost_tracking=True
            )
            logger.info("Helicone configuration loaded")
            
            # Initialize LLM Gateway
            llm_gateway = LLMGateway(
                helicone_config=helicone_config,
                db_path=os.getenv("DATABASE_PATH", "data/secure_chat.db")
            )
        else:
            # Use mock gateway
            llm_gateway = MockLLMGateway()
            if not os.getenv("HELICONE_API_KEY"):
                logger.warning("HELICONE_API_KEY not found - using mock LLM Gateway with sample data")
            else:
                logger.warning("Using mock LLM Gateway - external services not available")
        
        # Initialize API routers
        init_metrics_router(llm_gateway)
        init_chat_router(llm_gateway)
        init_dashboard_router(llm_gateway)
        
        logger.info("LLM Gateway initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize LLM Gateway: {str(e)}")
        # Use mock gateway as fallback
        llm_gateway = MockLLMGateway()
        init_metrics_router(llm_gateway)
        init_chat_router(llm_gateway)
        init_dashboard_router(llm_gateway)
        logger.warning("Using mock LLM Gateway as fallback")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Secure Medical Chat API...")
    if llm_gateway:
        # Perform any cleanup if needed
        pass


app = FastAPI(
    title="Secure Medical Chat API",
    description="A proof-of-concept conversational AI for healthcare with security, privacy, and optimization patterns",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
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
    basic_health = {"status": "healthy", "service": "secure-medical-chat"}
    
    # Add LLM Gateway health if available
    if llm_gateway:
        try:
            gateway_health = await llm_gateway.health_check()
            basic_health["llm_gateway"] = gateway_health["overall"]
            basic_health["cost_tracking"] = gateway_health["cost_tracker"]
        except Exception as e:
            basic_health["llm_gateway"] = f"error: {str(e)}"
    
    return basic_health

# Include routers
app.include_router(metrics_router, prefix="/api", tags=["metrics", "cost-tracking"])
app.include_router(chat_router, prefix="/api", tags=["chat", "security"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard", "visualization"])

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )