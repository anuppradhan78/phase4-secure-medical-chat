"""
Main FastAPI application for Secure Medical Chat with Guardrails.

This module sets up the FastAPI application with all security layers,
authentication, and monitoring capabilities using environment-based configuration.
"""

import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .config import AppConfig, ConfigurationError
from .startup_config import validate_startup_configuration
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
from .api.streaming import router as streaming_router, init_streaming_router
from .api.security_testing import router as security_testing_router, init_security_testing_router
from .api.admin import router as admin_router, init_admin_router

# Global configuration and LLM Gateway instances
app_config: AppConfig = None
llm_gateway: LLMGateway = None

def setup_logging(config: AppConfig):
    """Configure logging based on application configuration."""
    logging.basicConfig(
        level=getattr(logging, config.log_level.value),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('secure_medical_chat.log') if config.environment.value == 'production' else logging.NullHandler()
        ]
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown with configuration validation."""
    global app_config, llm_gateway
    
    # Validate configuration on startup
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting Secure Medical Chat API...")
    
    try:
        # Validate startup configuration
        success, config = validate_startup_configuration()
        if not success:
            logger.error("❌ Configuration validation failed. Cannot start application.")
            raise ConfigurationError("Configuration validation failed")
        
        app_config = config
        
        # Setup logging based on configuration
        setup_logging(app_config)
        logger = logging.getLogger(__name__)  # Get logger with new config
        
        logger.info(f"✅ Configuration loaded for {app_config.environment.value} environment")
        logger.info(f"🔧 LLM Provider: {app_config.llm.provider.value}")
        logger.info(f"💰 Daily Cost Limit: ${app_config.cost.daily_limit}")
        logger.info(f"🔒 Security Features: PII={app_config.security.enable_pii_redaction}, "
                   f"Guardrails={app_config.security.enable_guardrails}")
        
        # Initialize LLM Gateway based on configuration
        if LLM_GATEWAY_AVAILABLE and app_config.cost.helicone_api_key:
            # Initialize Helicone configuration from app config
            helicone_config = HeliconeConfig(
                api_key=app_config.cost.helicone_api_key,
                enable_caching=app_config.cost.enable_response_cache,
                cache_ttl_seconds=app_config.cost.cache_ttl_hours * 3600,
                enable_cost_tracking=app_config.cost.enable_cost_tracking
            )
            logger.info("✅ Helicone configuration loaded from app config")
            
            # Initialize LLM Gateway
            db_path = app_config.database.url.replace("sqlite:///", "")
            llm_gateway = LLMGateway(
                helicone_config=helicone_config,
                db_path=db_path
            )
            logger.info("✅ Real LLM Gateway initialized")
        else:
            # Use mock gateway
            llm_gateway = MockLLMGateway()
            if not app_config.cost.helicone_api_key:
                logger.warning("⚠️  HELICONE_API_KEY not configured - using mock LLM Gateway")
            else:
                logger.warning("⚠️  Using mock LLM Gateway - external services not available")
        
        # Initialize API routers with configuration
        init_metrics_router(llm_gateway)
        init_chat_router(llm_gateway)
        init_dashboard_router(llm_gateway)
        init_streaming_router(llm_gateway)
        init_security_testing_router()
        init_admin_router(llm_gateway)
        
        logger.info("✅ All API routers initialized successfully")
        logger.info("🎉 Secure Medical Chat API startup completed!")
        
    except ConfigurationError as e:
        logger.error(f"❌ Configuration error during startup: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error during startup: {str(e)}")
        # Use mock gateway as fallback
        llm_gateway = MockLLMGateway()
        init_metrics_router(llm_gateway)
        init_chat_router(llm_gateway)
        init_dashboard_router(llm_gateway)
        init_streaming_router(llm_gateway)
        init_security_testing_router()
        init_admin_router(llm_gateway)
        logger.warning("⚠️  Using mock LLM Gateway as fallback due to startup error")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Secure Medical Chat API...")
    if llm_gateway:
        # Perform any cleanup if needed
        logger.info("🧹 Cleaning up LLM Gateway resources...")
    logger.info("✅ Shutdown completed")


app = FastAPI(
    title="Secure Medical Chat API",
    description="""
    A proof-of-concept conversational AI for healthcare demonstrating critical security, privacy, and optimization patterns.
    
    ## Features
    
    * **PII/PHI Redaction** - Microsoft Presidio integration for protecting sensitive information
    * **Prompt Injection Defense** - NeMo Guardrails and Llama-Guard-3 for security
    * **Cost Optimization** - Helicone proxy with intelligent model routing and caching
    * **Role-Based Access Control** - Patient, Physician, and Admin roles with different capabilities
    * **Comprehensive Audit Logging** - Full audit trail of all system interactions
    * **Medical Safety Controls** - Specialized safety checks for healthcare applications
    
    ## Authentication
    
    This API uses header-based authentication for demonstration purposes:
    - `X-User-ID`: User identifier
    - `X-User-Role`: User role (patient, physician, admin)
    - `X-Session-ID`: Session identifier (optional)
    
    ## User Roles
    
    * **Patient** - Basic health information access (10 queries/hour, GPT-3.5 only)
    * **Physician** - Advanced medical AI features (100 queries/hour, GPT-3.5 & GPT-4)
    * **Admin** - Full system access including metrics and logs (1000 queries/hour, all models)
    
    ## Security Pipeline
    
    Every request goes through a comprehensive security pipeline:
    1. Authentication & Authorization
    2. Rate Limiting
    3. PII/PHI Redaction
    4. Guardrails Validation
    5. Medical Safety Checks
    6. LLM Processing
    7. Response Validation
    8. De-anonymization
    9. Audit Logging
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "Secure Medical Chat API",
        "url": "https://github.com/your-org/secure-medical-chat",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
)

# CORS middleware - will be configured based on environment in startup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure based on app_config.environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint providing API information with configuration details."""
    global app_config
    
    base_info = {
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
    
    # Add configuration summary if available
    if app_config:
        base_info["configuration"] = {
            "environment": app_config.environment.value,
            "llm_provider": app_config.llm.provider.value,
            "default_model": app_config.llm.default_model,
            "security_features": {
                "pii_redaction": app_config.security.enable_pii_redaction,
                "guardrails": app_config.security.enable_guardrails,
                "medical_disclaimers": app_config.security.enable_medical_disclaimers
            },
            "cost_tracking": app_config.cost.enable_cost_tracking,
            "daily_cost_limit": app_config.cost.daily_limit
        }
    
    return base_info

@app.get("/health")
async def health_check():
    """Health check endpoint with configuration status."""
    global app_config
    
    basic_health = {
        "status": "healthy", 
        "service": "secure-medical-chat",
        "timestamp": "2024-12-18T00:00:00Z"
    }
    
    # Add configuration status
    if app_config:
        basic_health["configuration"] = {
            "status": "loaded",
            "environment": app_config.environment.value,
            "security_enabled": app_config.security.enable_pii_redaction and app_config.security.enable_guardrails
        }
    else:
        basic_health["configuration"] = {"status": "not_loaded"}
    
    # Add LLM Gateway health if available
    if llm_gateway:
        try:
            gateway_health = await llm_gateway.health_check()
            basic_health["llm_gateway"] = gateway_health["overall"]
            basic_health["cost_tracking"] = gateway_health["cost_tracker"]
        except Exception as e:
            basic_health["llm_gateway"] = f"error: {str(e)}"
    else:
        basic_health["llm_gateway"] = "not_initialized"
    
    return basic_health

@app.get("/api/config")
async def get_config_info():
    """Get current configuration information (non-sensitive data only)."""
    global app_config
    
    if not app_config:
        raise HTTPException(status_code=503, detail="Configuration not loaded")
    
    from .config import config_manager
    return config_manager.get_config_summary()

# Include routers
app.include_router(metrics_router, prefix="/api", tags=["metrics", "cost-tracking"])
app.include_router(chat_router, prefix="/api", tags=["chat", "security"])
app.include_router(dashboard_router, prefix="/api", tags=["dashboard", "visualization"])
app.include_router(streaming_router, prefix="/api", tags=["streaming", "latency", "sse"])
app.include_router(security_testing_router, prefix="/api", tags=["security", "testing", "red-team"])
app.include_router(admin_router, prefix="/api", tags=["admin", "monitoring", "system-management"])

if __name__ == "__main__":
    # Load configuration to get host and port settings
    try:
        from .config import load_config
        config = load_config()
        
        uvicorn.run(
            "src.main:app",
            host=config.host,
            port=config.port,
            reload=config.debug,
            log_level=config.log_level.value.lower()
        )
    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        print("💡 Please check your .env file and ensure all required variables are set")
        sys.exit(1)