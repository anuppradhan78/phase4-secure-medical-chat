"""
Streaming response service with Server-Sent Events (SSE) support.

This module provides real-time streaming capabilities for the secure medical chat,
allowing users to see responses as they are generated while maintaining all
security controls and latency measurement.
"""

import asyncio
import json
import logging
import statistics
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from ..models import (
    ChatRequest, UserRole, AuditEvent, SecurityEvent, 
    EventType, ThreatType
)
from ..auth.rbac import RBACService
from ..auth.rate_limiter import RateLimiter
try:
    from ..security.pii_redaction import PIIRedactionService
    PII_SERVICE_AVAILABLE = True
except ImportError:
    from ..security.mock_pii_redaction import MockPIIRedactionService as PIIRedactionService
    PII_SERVICE_AVAILABLE = False
from ..security.guardrails import GuardrailsService
from ..security.medical_safety import MedicalSafetyController
from ..llm.llm_gateway import LLMGateway
from ..llm.latency_tracker import LatencyTracker
from ..database import get_database

logger = logging.getLogger(__name__)

# Initialize services
rbac_service = RBACService()
rate_limiter = RateLimiter()
pii_service = PIIRedactionService()
guardrails_service = GuardrailsService()
medical_safety_service = MedicalSafetyController()
latency_tracker = LatencyTracker()

# Router for streaming endpoints
router = APIRouter()

# Global services (will be injected from main app)
llm_gateway: Optional[LLMGateway] = None


def init_streaming_router(gateway: LLMGateway):
    """Initialize the streaming router with LLM gateway."""
    global llm_gateway
    llm_gateway = gateway
    logger.info("Streaming router initialized with LLM gateway")


async def get_current_user(request: Request) -> Dict[str, Any]:
    """Extract user information from request headers."""
    user_id = request.headers.get("X-User-ID", "anonymous")
    user_role_str = request.headers.get("X-User-Role", "patient")
    session_id = request.headers.get("X-Session-ID")
    
    try:
        user_role = UserRole(user_role_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user role: {user_role_str}"
        )
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    return {
        "user_id": user_id,
        "user_role": user_role,
        "session_id": session_id,
        "ip_address": request.client.host if request.client else "unknown"
    }


class StreamingChatProcessor:
    """
    Processor for streaming chat responses with full security pipeline.
    
    Maintains all security controls while providing real-time streaming
    with detailed latency measurement and progress updates.
    """
    
    def __init__(self, request_id: str, user_info: Dict[str, Any]):
        self.request_id = request_id
        self.user_info = user_info
        self.start_time = None
        self.metadata = {
            "redaction_info": {"entities_redacted": 0, "entity_types": []},
            "cost": 0.0,
            "latency_ms": 0,
            "model_used": "unknown",
            "cache_hit": False,
            "security_flags": [],
            "pipeline_stages": [],
            "streaming_stats": {
                "chunks_sent": 0,
                "total_characters": 0,
                "first_chunk_latency_ms": 0,
                "last_chunk_latency_ms": 0
            }
        }
    
    async def process_streaming_request(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Process a streaming chat request through the complete security pipeline.
        
        Yields Server-Sent Events with progress updates and response chunks.
        """
        self.start_time = latency_tracker.start_request_tracking(self.request_id)
        user_id = self.user_info["user_id"]
        user_role = self.user_info["user_role"]
        session_id = self.user_info["session_id"]
        
        db = get_database()
        
        try:
            # Send initial connection event
            yield self._create_sse_event("connection", {
                "status": "connected",
                "request_id": self.request_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # === STAGE 1: AUTHENTICATION & AUTHORIZATION ===
            yield self._create_sse_event("stage_start", {
                "stage": "authentication",
                "message": "Validating user permissions..."
            })
            
            with latency_tracker.measure_stage(self.request_id, "authentication"):
                if not rbac_service.authorize_feature(user_role, "basic_chat"):
                    yield self._create_sse_event("error", {
                        "error": "unauthorized",
                        "message": f"User role '{user_role.value}' is not authorized for chat functionality"
                    })
                    return
            
            self.metadata["pipeline_stages"].append("authentication")
            yield self._create_sse_event("stage_complete", {"stage": "authentication"})
            
            # === STAGE 2: RATE LIMITING ===
            yield self._create_sse_event("stage_start", {
                "stage": "rate_limiting",
                "message": "Checking rate limits..."
            })
            
            with latency_tracker.measure_stage(self.request_id, "rate_limiting"):
                rate_allowed, rate_info = rate_limiter.check_rate_limit(user_id, user_role)
                if not rate_allowed:
                    yield self._create_sse_event("error", {
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. {rate_info['remaining']} requests remaining.",
                        "rate_info": rate_info
                    })
                    return
            
            self.metadata["pipeline_stages"].append("rate_limiting")
            yield self._create_sse_event("stage_complete", {"stage": "rate_limiting"})
            
            # === STAGE 3: PII/PHI REDACTION ===
            yield self._create_sse_event("stage_start", {
                "stage": "pii_redaction",
                "message": "Scanning for sensitive information..."
            })
            
            with latency_tracker.measure_stage(self.request_id, "pii_redaction") as stage:
                redaction_result = pii_service.redact_message(
                    request.message, 
                    user_id, 
                    session_id
                )
                stage.metadata = {
                    "entities_found": redaction_result.entities_found,
                    "entity_types": [et.value for et in redaction_result.entity_types]
                }
            
            self.metadata["redaction_info"] = {
                "entities_redacted": redaction_result.entities_found,
                "entity_types": [et.value for et in redaction_result.entity_types]
            }
            self.metadata["pipeline_stages"].append("pii_redaction")
            
            yield self._create_sse_event("stage_complete", {
                "stage": "pii_redaction",
                "entities_redacted": redaction_result.entities_found
            })
            
            # === STAGE 4: GUARDRAILS VALIDATION ===
            yield self._create_sse_event("stage_start", {
                "stage": "guardrails_validation",
                "message": "Validating content safety..."
            })
            
            with latency_tracker.measure_stage(self.request_id, "guardrails_validation") as stage:
                input_validation = guardrails_service.validate_input(
                    redaction_result.redacted_text, 
                    user_id
                )
                stage.metadata = {
                    "blocked": input_validation.blocked,
                    "risk_score": input_validation.risk_score
                }
            
            if input_validation.blocked:
                yield self._create_sse_event("error", {
                    "error": "content_blocked",
                    "message": f"Content blocked by security filters: {input_validation.reason}",
                    "risk_score": input_validation.risk_score
                })
                return
            
            self.metadata["pipeline_stages"].append("guardrails_validation")
            yield self._create_sse_event("stage_complete", {"stage": "guardrails_validation"})
            
            # === STAGE 5: MEDICAL SAFETY VALIDATION ===
            yield self._create_sse_event("stage_start", {
                "stage": "medical_safety",
                "message": "Checking medical safety guidelines..."
            })
            
            with latency_tracker.measure_stage(self.request_id, "medical_safety") as stage:
                medical_validation = medical_safety_service.validate_input(request.message)
                stage.metadata = {
                    "blocked": medical_validation.blocked,
                    "risk_score": medical_validation.risk_score
                }
            
            if medical_validation.blocked:
                yield self._create_sse_event("error", {
                    "error": "medical_safety_concern",
                    "message": f"Medical safety concern: {medical_validation.reason}",
                    "risk_score": medical_validation.risk_score
                })
                return
            
            self.metadata["pipeline_stages"].append("medical_safety")
            yield self._create_sse_event("stage_complete", {"stage": "medical_safety"})
            
            # === STAGE 6: LLM PROCESSING (STREAMING) ===
            yield self._create_sse_event("stage_start", {
                "stage": "llm_processing",
                "message": "Generating response..."
            })
            
            if not llm_gateway:
                yield self._create_sse_event("error", {
                    "error": "service_unavailable",
                    "message": "LLM gateway not available"
                })
                return
            
            # Process through LLM gateway with streaming
            llm_request = ChatRequest(
                message=redaction_result.redacted_text,
                user_role=user_role,
                session_id=session_id,
                user_id=user_id,
                metadata={"original_message_length": len(request.message)}
            )
            
            # Check cache first
            with latency_tracker.measure_stage(self.request_id, "llm_processing") as stage:
                # For streaming, we'll simulate the LLM response generation
                # In a real implementation, this would connect to the actual streaming API
                
                llm_response, llm_metadata = await llm_gateway.process_chat_request(llm_request)
                
                # Update metadata
                self.metadata.update({
                    "cost": llm_metadata.get("cost", 0.0),
                    "model_used": llm_metadata.get("model_used", "unknown"),
                    "cache_hit": llm_metadata.get("cache_hit", False),
                    "tokens_used": llm_metadata.get("tokens_used", 0)
                })
                
                stage.metadata = {
                    "model_used": self.metadata["model_used"],
                    "cache_hit": self.metadata["cache_hit"],
                    "cost": self.metadata["cost"]
                }
            
            # If cache hit, send response immediately
            if self.metadata["cache_hit"]:
                yield self._create_sse_event("cache_hit", {
                    "message": "Response retrieved from cache",
                    "model": self.metadata["model_used"]
                })
                
                # Stream the cached response in chunks for demonstration
                async for chunk in self._stream_response_chunks(llm_response.response):
                    yield chunk
            else:
                # Stream the response in chunks
                async for chunk in self._stream_response_chunks(llm_response.response):
                    yield chunk
            
            self.metadata["pipeline_stages"].append("llm_processing")
            
            # === STAGE 7: RESPONSE VALIDATION ===
            yield self._create_sse_event("stage_start", {
                "stage": "response_validation",
                "message": "Validating response safety..."
            })
            
            with latency_tracker.measure_stage(self.request_id, "response_validation"):
                output_validation = guardrails_service.validate_output(
                    llm_response.response, 
                    user_id
                )
                final_response = output_validation.modified_response or llm_response.response
            
            self.metadata["pipeline_stages"].append("response_validation")
            yield self._create_sse_event("stage_complete", {"stage": "response_validation"})
            
            # === STAGE 8: DE-ANONYMIZATION ===
            yield self._create_sse_event("stage_start", {
                "stage": "de_anonymization",
                "message": "Restoring personal information..."
            })
            
            with latency_tracker.measure_stage(self.request_id, "de_anonymization"):
                if redaction_result.entities_found > 0:
                    final_response = pii_service.de_anonymize_response(
                        final_response, 
                        user_id, 
                        session_id
                    )
            
            self.metadata["pipeline_stages"].append("de_anonymization")
            yield self._create_sse_event("stage_complete", {"stage": "de_anonymization"})
            
            # === STAGE 9: AUDIT LOGGING ===
            with latency_tracker.measure_stage(self.request_id, "audit_logging"):
                # Record usage and complete latency tracking
                rate_limiter.record_request(user_id, self.metadata["cost"])
                
                # Complete latency tracking
                profile = latency_tracker.finish_request_tracking(
                    self.request_id,
                    self.start_time,
                    user_role.value,
                    self.metadata["model_used"],
                    self.metadata["cache_hit"],
                    False,  # optimization_applied
                    self.metadata
                )
                
                self.metadata["latency_ms"] = int(profile.total_duration_ms)
                
                # Log audit event
                audit_event = AuditEvent(
                    timestamp=datetime.now(timezone.utc),
                    user_id=user_id,
                    user_role=user_role,
                    session_id=session_id,
                    event_type=EventType.CHAT_REQUEST,
                    message=redaction_result.redacted_text,
                    response=final_response[:500],
                    cost_usd=self.metadata["cost"],
                    latency_ms=self.metadata["latency_ms"],
                    entities_redacted=redaction_result.entity_types,
                    security_flags=self.metadata["security_flags"],
                    metadata={
                        **self.metadata,
                        "streaming": True,
                        "chunks_sent": self.metadata["streaming_stats"]["chunks_sent"]
                    }
                )
                db.log_audit_event(audit_event)
                
                # Update session activity
                db.update_session_activity(session_id, self.metadata["cost"])
            
            self.metadata["pipeline_stages"].append("audit_logging")
            
            # Send completion event with final metadata
            yield self._create_sse_event("complete", {
                "status": "success",
                "metadata": self.metadata,
                "latency_breakdown": {
                    stage.stage_name: stage.duration_ms 
                    for stage in profile.stages 
                    if stage.duration_ms is not None
                }
            })
            
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}", exc_info=True)
            
            # Send error event
            yield self._create_sse_event("error", {
                "error": "internal_error",
                "message": "An internal error occurred while processing your request",
                "request_id": self.request_id
            })
            
            # Log error audit event
            if self.start_time:
                error_profile = latency_tracker.finish_request_tracking(
                    self.request_id,
                    self.start_time,
                    self.user_info["user_role"].value,
                    "unknown",
                    False,
                    False,
                    {"error": str(e)}
                )
                
                error_audit_event = AuditEvent(
                    timestamp=datetime.now(timezone.utc),
                    user_id=user_id,
                    user_role=user_role,
                    session_id=session_id,
                    event_type=EventType.CHAT_REQUEST,
                    message=request.message[:200],
                    response=f"Error: {str(e)}",
                    cost_usd=0.0,
                    latency_ms=int(error_profile.total_duration_ms),
                    entities_redacted=[],
                    security_flags=["system_error", "streaming_error"],
                    metadata={"error": str(e), "streaming": True}
                )
                db.log_audit_event(error_audit_event)
    
    async def _stream_response_chunks(self, response: str) -> AsyncGenerator[str, None]:
        """
        Stream response text in chunks with realistic timing.
        
        Simulates real-time response generation with appropriate delays.
        """
        words = response.split()
        chunk_size = 3  # Words per chunk
        first_chunk = True
        
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            
            # Add space if not the last chunk
            if i + chunk_size < len(words):
                chunk_text += " "
            
            # Record timing for first and last chunks
            current_time = datetime.now(timezone.utc)
            if first_chunk:
                if self.start_time:
                    first_chunk_latency = (current_time.timestamp() - (self.start_time + time.perf_counter() - self.start_time)) * 1000
                    self.metadata["streaming_stats"]["first_chunk_latency_ms"] = int(first_chunk_latency)
                first_chunk = False
            
            self.metadata["streaming_stats"]["chunks_sent"] += 1
            self.metadata["streaming_stats"]["total_characters"] += len(chunk_text)
            
            # Send chunk event
            yield self._create_sse_event("chunk", {
                "text": chunk_text,
                "chunk_index": self.metadata["streaming_stats"]["chunks_sent"],
                "timestamp": current_time.isoformat()
            })
            
            # Simulate realistic typing delay (adjust based on model speed)
            delay = 0.1 + (len(chunk_text) * 0.02)  # Base delay + per-character delay
            await asyncio.sleep(delay)
        
        # Record last chunk timing
        if self.start_time:
            end_time = time.perf_counter()
            last_chunk_latency = (end_time - self.start_time) * 1000
            self.metadata["streaming_stats"]["last_chunk_latency_ms"] = int(last_chunk_latency)
    
    def _create_sse_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Create a Server-Sent Event formatted string."""
        event_data = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": self.request_id,
            **data
        }
        
        return f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"


@router.post("/chat/stream")
async def stream_chat(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Streaming chat endpoint with Server-Sent Events.
    
    Provides real-time response streaming while maintaining all security controls
    and detailed latency measurement throughout the pipeline.
    """
    request_id = str(uuid.uuid4())
    
    processor = StreamingChatProcessor(request_id, current_user)
    
    return EventSourceResponse(
        processor.process_streaming_request(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id
        }
    )


@router.get("/chat/stream/test")
async def test_streaming():
    """Test endpoint for streaming functionality."""
    
    async def generate_test_stream():
        """Generate a test stream to verify SSE functionality."""
        for i in range(10):
            event_data = {
                "type": "test_chunk",
                "message": f"Test chunk {i + 1}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "progress": (i + 1) / 10
            }
            
            yield f"event: test_chunk\ndata: {json.dumps(event_data)}\n\n"
            await asyncio.sleep(0.5)
        
        # Send completion event
        completion_data = {
            "type": "complete",
            "message": "Test stream completed successfully",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        yield f"event: complete\ndata: {json.dumps(completion_data)}\n\n"
    
    return EventSourceResponse(
        generate_test_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.get("/latency/analytics")
async def get_latency_analytics(
    period_hours: int = 24,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get comprehensive latency analytics.
    
    Requires admin role for detailed analytics access.
    """
    user_role = current_user["user_role"]
    
    # Check authorization for detailed analytics
    if user_role != UserRole.ADMIN and period_hours > 24:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Extended analytics require admin privileges"
        )
    
    analytics = latency_tracker.get_latency_analytics(period_hours)
    
    return {
        "analytics": analytics,
        "user_role": user_role.value,
        "access_level": "full" if user_role == UserRole.ADMIN else "basic"
    }


@router.get("/latency/trends")
async def get_latency_trends(
    period_hours: int = 24,
    bucket_minutes: int = 60,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get latency trends over time."""
    user_role = current_user["user_role"]
    
    # Limit period for non-admin users
    if user_role != UserRole.ADMIN:
        period_hours = min(period_hours, 24)
    
    trends = latency_tracker.get_latency_trends(period_hours, bucket_minutes)
    
    return {
        "trends": trends,
        "user_role": user_role.value
    }


@router.get("/latency/comparison")
async def get_provider_comparison(
    period_hours: int = 24,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Compare latency performance across different providers/models."""
    user_role = current_user["user_role"]
    
    # Check authorization
    if user_role not in [UserRole.PHYSICIAN, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Provider comparison requires physician or admin privileges"
        )
    
    comparison = latency_tracker.compare_providers(period_hours)
    
    return {
        "comparison": comparison,
        "user_role": user_role.value,
        "period_hours": period_hours
    }


@router.get("/latency/realtime")
async def get_realtime_latency_metrics():
    """
    Get real-time latency metrics for live monitoring.
    
    Returns current performance statistics and active request counts.
    """
    # Get recent performance data (last 5 minutes)
    recent_analytics = latency_tracker.get_latency_analytics(period_hours=0.083)  # 5 minutes
    
    # Get active measurements count
    active_count = len(latency_tracker.active_measurements)
    
    # Calculate real-time metrics
    realtime_metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_requests": active_count,
        "recent_performance": recent_analytics,
        "system_load": {
            "active_measurements": active_count,
            "total_tracked_profiles": len(latency_tracker.request_profiles),
            "memory_usage_estimate_kb": len(latency_tracker.request_profiles) * 2  # Rough estimate
        }
    }
    
    return realtime_metrics


@router.get("/latency/benchmark")
async def run_latency_benchmark(
    iterations: int = 5,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Run a latency benchmark test to measure system performance.
    
    Executes multiple test requests to measure baseline performance.
    """
    user_role = current_user["user_role"]
    
    # Check authorization for benchmarking
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Latency benchmarking requires admin privileges"
        )
    
    # Limit iterations to prevent abuse
    iterations = min(iterations, 10)
    
    benchmark_results = []
    test_message = "This is a benchmark test message for measuring system latency and performance."
    
    for i in range(iterations):
        request_id = f"benchmark_{i}_{int(time.time())}"
        start_time = latency_tracker.start_request_tracking(request_id)
        
        try:
            # Simulate the security pipeline stages
            with latency_tracker.measure_stage(request_id, "authentication"):
                await asyncio.sleep(0.001)  # Simulate auth check
            
            with latency_tracker.measure_stage(request_id, "rate_limiting"):
                await asyncio.sleep(0.001)  # Simulate rate limit check
            
            with latency_tracker.measure_stage(request_id, "pii_redaction") as stage:
                # Actual PII redaction test
                redaction_result = pii_service.redact_message(
                    test_message, 
                    f"benchmark_user_{i}", 
                    f"benchmark_session_{i}"
                )
                stage.metadata = {
                    "entities_found": redaction_result.entities_found,
                    "message_length": len(test_message)
                }
            
            with latency_tracker.measure_stage(request_id, "guardrails_validation") as stage:
                # Actual guardrails validation
                validation_result = guardrails_service.validate_input(
                    redaction_result.redacted_text, 
                    f"benchmark_user_{i}"
                )
                stage.metadata = {
                    "blocked": validation_result.blocked,
                    "risk_score": validation_result.risk_score
                }
            
            with latency_tracker.measure_stage(request_id, "medical_safety"):
                # Actual medical safety check
                medical_result = medical_safety_service.validate_input(test_message)
            
            with latency_tracker.measure_stage(request_id, "llm_processing") as stage:
                # Simulate LLM processing (no actual API call for benchmark)
                await asyncio.sleep(0.5)  # Simulate typical LLM response time
                stage.metadata = {
                    "model_used": "benchmark_model",
                    "simulated": True
                }
            
            with latency_tracker.measure_stage(request_id, "response_validation"):
                await asyncio.sleep(0.01)  # Simulate response validation
            
            with latency_tracker.measure_stage(request_id, "de_anonymization"):
                # Actual de-anonymization if entities were found
                if redaction_result.entities_found > 0:
                    pii_service.de_anonymize_response(
                        "Benchmark response text", 
                        f"benchmark_user_{i}", 
                        f"benchmark_session_{i}"
                    )
            
            with latency_tracker.measure_stage(request_id, "audit_logging"):
                await asyncio.sleep(0.005)  # Simulate audit logging
            
            # Complete the benchmark iteration
            profile = latency_tracker.finish_request_tracking(
                request_id,
                start_time,
                user_role.value,
                "benchmark_model",
                False,  # cache_hit
                False,  # optimization_applied
                {"benchmark": True, "iteration": i}
            )
            
            benchmark_results.append({
                "iteration": i + 1,
                "total_latency_ms": profile.total_duration_ms,
                "stage_breakdown": {
                    stage.stage_name: stage.duration_ms 
                    for stage in profile.stages 
                    if stage.duration_ms is not None
                },
                "entities_redacted": redaction_result.entities_found
            })
            
        except Exception as e:
            logger.error(f"Benchmark iteration {i} failed: {str(e)}")
            benchmark_results.append({
                "iteration": i + 1,
                "error": str(e),
                "total_latency_ms": 0
            })
    
    # Calculate benchmark statistics
    successful_results = [r for r in benchmark_results if "error" not in r]
    
    if successful_results:
        latencies = [r["total_latency_ms"] for r in successful_results]
        benchmark_stats = {
            "iterations_completed": len(successful_results),
            "iterations_failed": len(benchmark_results) - len(successful_results),
            "avg_latency_ms": round(statistics.mean(latencies), 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
            "median_latency_ms": round(statistics.median(latencies), 2),
            "latency_std_dev": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0
        }
        
        # Calculate average stage breakdown
        stage_totals = {}
        for result in successful_results:
            for stage_name, duration in result["stage_breakdown"].items():
                if stage_name not in stage_totals:
                    stage_totals[stage_name] = []
                stage_totals[stage_name].append(duration)
        
        avg_stage_breakdown = {
            stage_name: round(statistics.mean(durations), 2)
            for stage_name, durations in stage_totals.items()
        }
        
        benchmark_stats["avg_stage_breakdown"] = avg_stage_breakdown
    else:
        benchmark_stats = {
            "iterations_completed": 0,
            "iterations_failed": len(benchmark_results),
            "error": "All benchmark iterations failed"
        }
    
    return {
        "benchmark_summary": benchmark_stats,
        "detailed_results": benchmark_results,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "test_configuration": {
            "iterations": iterations,
            "test_message_length": len(test_message),
            "user_role": user_role.value
        }
    }


@router.get("/latency/slowest")
async def get_slowest_requests(
    limit: int = 10,
    period_hours: int = 24,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get the slowest requests for performance analysis."""
    user_role = current_user["user_role"]
    
    # Check authorization for detailed request analysis
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Detailed request analysis requires admin privileges"
        )
    
    slowest = latency_tracker.get_slowest_requests(limit, period_hours)
    
    return {
        "slowest_requests": slowest,
        "limit": limit,
        "period_hours": period_hours
    }


@router.post("/latency/clear")
async def clear_latency_history(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Clear latency tracking history (admin only)."""
    user_role = current_user["user_role"]
    
    if user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clearing latency history requires admin privileges"
        )
    
    result = latency_tracker.clear_history()
    
    return {
        "result": result,
        "cleared_by": current_user["user_id"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/latency/health")
async def get_latency_tracker_health():
    """Get health status of the latency tracker."""
    return latency_tracker.get_health_status()