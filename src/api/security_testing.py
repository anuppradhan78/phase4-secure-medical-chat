"""
Security Testing API endpoints.

This module provides API endpoints for running security tests and accessing
security test reports through the web interface.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse

from ..models import UserRole
from ..security.security_test_suite import SecurityTestSuite, SecurityTestReport
from ..auth.rbac import RBACService

logger = logging.getLogger(__name__)

# Initialize services
rbac_service = RBACService()

# Router for security testing endpoints
router = APIRouter()

# Global test suite instance
security_test_suite: Optional[SecurityTestSuite] = None
latest_test_report: Optional[SecurityTestReport] = None
test_in_progress: bool = False


def init_security_testing_router():
    """Initialize the security testing router."""
    global security_test_suite
    try:
        security_test_suite = SecurityTestSuite()
        logger.info("Security testing router initialized")
    except Exception as e:
        logger.error(f"Failed to initialize security test suite: {e}")
        security_test_suite = None


async def get_current_user_admin(request) -> Dict[str, Any]:
    """Get current user and verify admin privileges."""
    # In a real implementation, this would extract from JWT/session
    user_role = request.headers.get("X-User-Role", "patient")
    user_id = request.headers.get("X-User-ID", "anonymous")
    
    try:
        role = UserRole(user_role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user role: {user_role}"
        )
    
    # Only admin users can access security testing
    if role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security testing requires admin privileges"
        )
    
    return {
        "user_id": user_id,
        "user_role": role
    }


@router.get("/security/test/status")
async def get_security_test_status():
    """Get the current status of security testing."""
    global test_in_progress, latest_test_report
    
    status_info = {
        "test_suite_available": security_test_suite is not None,
        "test_in_progress": test_in_progress,
        "latest_report_available": latest_test_report is not None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if latest_test_report:
        status_info["latest_report_summary"] = {
            "execution_timestamp": latest_test_report.execution_timestamp.isoformat(),
            "total_tests": latest_test_report.total_tests,
            "passed_tests": latest_test_report.passed_tests,
            "success_rate": latest_test_report.success_rate
        }
    
    return status_info


@router.post("/security/test/run")
async def run_security_tests(
    background_tasks: BackgroundTasks,
    request,
    test_categories: Optional[str] = None
):
    """
    Run comprehensive security tests.
    
    Args:
        test_categories: Comma-separated list of test categories to run
                        (pii, injection, guardrails, safety, redteam, edge)
    """
    global test_in_progress
    
    # Verify admin access
    await get_current_user_admin(request)
    
    if not security_test_suite:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security test suite not available"
        )
    
    if test_in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Security tests are already running"
        )
    
    # Start tests in background
    background_tasks.add_task(run_security_tests_background, test_categories)
    
    return {
        "message": "Security tests started",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


async def run_security_tests_background(test_categories: Optional[str] = None):
    """Run security tests in the background."""
    global test_in_progress, latest_test_report
    
    test_in_progress = True
    logger.info("Starting background security tests")
    
    try:
        # Run comprehensive tests
        report = await security_test_suite.run_comprehensive_security_tests()
        latest_test_report = report
        
        logger.info(f"Security tests completed: {report.passed_tests}/{report.total_tests} passed")
        
    except Exception as e:
        logger.error(f"Security tests failed: {e}", exc_info=True)
        
    finally:
        test_in_progress = False


@router.get("/security/test/report")
async def get_security_test_report(request):
    """Get the latest security test report."""
    # Verify admin access
    await get_current_user_admin(request)
    
    if not latest_test_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No security test report available"
        )
    
    # Convert report to JSON-serializable format
    report_data = {
        "test_suite_name": latest_test_report.test_suite_name,
        "execution_timestamp": latest_test_report.execution_timestamp.isoformat(),
        "total_tests": latest_test_report.total_tests,
        "passed_tests": latest_test_report.passed_tests,
        "failed_tests": latest_test_report.failed_tests,
        "success_rate": latest_test_report.success_rate,
        "total_execution_time_ms": latest_test_report.total_execution_time_ms,
        "summary": latest_test_report.summary,
        "recommendations": latest_test_report.recommendations
    }
    
    return report_data


@router.get("/security/test/report/detailed")
async def get_detailed_security_test_report(request):
    """Get the detailed security test report including individual test results."""
    # Verify admin access
    await get_current_user_admin(request)
    
    if not latest_test_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No security test report available"
        )
    
    # Convert full report to JSON-serializable format
    detailed_results = []
    for result in latest_test_report.test_results:
        result_data = {
            "test_name": result.test_name,
            "test_type": result.test_type,
            "input_data": result.input_data,
            "expected_result": str(result.expected_result),
            "actual_result": str(result.actual_result),
            "passed": result.passed,
            "execution_time_ms": result.execution_time_ms,
            "error_message": result.error_message,
            "metadata": result.metadata
        }
        detailed_results.append(result_data)
    
    report_data = {
        "test_suite_name": latest_test_report.test_suite_name,
        "execution_timestamp": latest_test_report.execution_timestamp.isoformat(),
        "total_tests": latest_test_report.total_tests,
        "passed_tests": latest_test_report.passed_tests,
        "failed_tests": latest_test_report.failed_tests,
        "success_rate": latest_test_report.success_rate,
        "total_execution_time_ms": latest_test_report.total_execution_time_ms,
        "summary": latest_test_report.summary,
        "recommendations": latest_test_report.recommendations,
        "test_results": detailed_results
    }
    
    return report_data


@router.get("/security/test/report/failures")
async def get_security_test_failures(request):
    """Get only the failed security tests for focused analysis."""
    # Verify admin access
    await get_current_user_admin(request)
    
    if not latest_test_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No security test report available"
        )
    
    # Filter for failed tests only
    failed_tests = []
    for result in latest_test_report.test_results:
        if not result.passed:
            failed_test = {
                "test_name": result.test_name,
                "test_type": result.test_type,
                "input_data": result.input_data,
                "expected_result": str(result.expected_result),
                "actual_result": str(result.actual_result),
                "execution_time_ms": result.execution_time_ms,
                "error_message": result.error_message,
                "metadata": result.metadata
            }
            failed_tests.append(failed_test)
    
    return {
        "total_failed_tests": len(failed_tests),
        "failed_tests": failed_tests,
        "execution_timestamp": latest_test_report.execution_timestamp.isoformat(),
        "recommendations": latest_test_report.recommendations
    }


@router.post("/security/test/validate-input")
async def validate_input_security(
    request,
    test_input: str,
    user_role: str = "patient"
):
    """
    Test a specific input against all security controls.
    
    Useful for interactive security testing and validation.
    """
    # Verify admin access
    await get_current_user_admin(request)
    
    if not security_test_suite:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security test suite not available"
        )
    
    try:
        # Test input against all security layers
        start_time = datetime.now()
        
        # PII/PHI detection
        pii_result = security_test_suite.pii_service.redact_message(
            test_input, 
            "security_test_user", 
            "security_test_session"
        )
        
        # Guardrails validation
        guardrails_result = security_test_suite.guardrails_service.validate_input(
            test_input, 
            "security_test_user"
        )
        
        # Medical safety validation
        medical_safety_result = security_test_suite.medical_safety_service.validate_input(
            test_input
        )
        
        end_time = datetime.now()
        execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Compile results
        validation_result = {
            "input": test_input[:200] + "..." if len(test_input) > 200 else test_input,
            "execution_time_ms": execution_time_ms,
            "pii_detection": {
                "entities_found": pii_result.entities_found,
                "entity_types": [et.value for et in pii_result.entity_types],
                "redacted_text": pii_result.redacted_text[:200] + "..." if len(pii_result.redacted_text) > 200 else pii_result.redacted_text
            },
            "guardrails": {
                "blocked": guardrails_result.blocked,
                "reason": guardrails_result.reason,
                "risk_score": guardrails_result.risk_score
            },
            "medical_safety": {
                "blocked": medical_safety_result.blocked,
                "reason": medical_safety_result.reason,
                "risk_score": medical_safety_result.risk_score,
                "metadata": getattr(medical_safety_result, 'metadata', {})
            },
            "overall_assessment": {
                "blocked": guardrails_result.blocked or medical_safety_result.blocked,
                "max_risk_score": max(guardrails_result.risk_score, medical_safety_result.risk_score),
                "security_layers_triggered": sum([
                    pii_result.entities_found > 0,
                    guardrails_result.blocked,
                    medical_safety_result.blocked
                ])
            }
        }
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Input validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Security validation failed: {str(e)}"
        )


@router.get("/security/test/metrics")
async def get_security_metrics(request):
    """Get security testing metrics and statistics."""
    # Verify admin access
    await get_current_user_admin(request)
    
    if not latest_test_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No security test report available"
        )
    
    # Calculate additional metrics
    test_results = latest_test_report.test_results
    
    metrics = {
        "overall_metrics": {
            "total_tests": latest_test_report.total_tests,
            "success_rate": latest_test_report.success_rate,
            "avg_execution_time_ms": sum(r.execution_time_ms for r in test_results) / len(test_results) if test_results else 0
        },
        "security_effectiveness": {},
        "performance_metrics": {
            "fastest_test_ms": min(r.execution_time_ms for r in test_results) if test_results else 0,
            "slowest_test_ms": max(r.execution_time_ms for r in test_results) if test_results else 0,
            "total_execution_time_ms": latest_test_report.total_execution_time_ms
        },
        "test_coverage": {
            "test_types": list(set(r.test_type for r in test_results)),
            "total_test_types": len(set(r.test_type for r in test_results))
        }
    }
    
    # Add specific security metrics from summary
    if "pii_detection_accuracy" in latest_test_report.summary:
        metrics["security_effectiveness"]["pii_detection"] = latest_test_report.summary["pii_detection_accuracy"]
    
    if "prompt_injection_blocking" in latest_test_report.summary:
        metrics["security_effectiveness"]["prompt_injection_blocking"] = latest_test_report.summary["prompt_injection_blocking"]
    
    return metrics


@router.get("/security/test/health")
async def get_security_testing_health():
    """Get health status of security testing components."""
    health_status = {
        "security_test_suite": "available" if security_test_suite else "unavailable",
        "test_in_progress": test_in_progress,
        "latest_report_age_hours": None,
        "components": {}
    }
    
    if latest_test_report:
        age = datetime.now(timezone.utc) - latest_test_report.execution_timestamp
        health_status["latest_report_age_hours"] = age.total_seconds() / 3600
    
    # Check component health
    if security_test_suite:
        try:
            # Test PII service
            test_result = security_test_suite.pii_service.redact_message("test", "health_check", "health_check")
            health_status["components"]["pii_service"] = "healthy"
        except Exception as e:
            health_status["components"]["pii_service"] = f"error: {str(e)}"
        
        try:
            # Test guardrails service
            guard_result = security_test_suite.guardrails_service.validate_input("test", "health_check")
            health_status["components"]["guardrails_service"] = "healthy"
        except Exception as e:
            health_status["components"]["guardrails_service"] = f"error: {str(e)}"
        
        try:
            # Test medical safety service
            safety_result = security_test_suite.medical_safety_service.validate_input("test")
            health_status["components"]["medical_safety_service"] = "healthy"
        except Exception as e:
            health_status["components"]["medical_safety_service"] = f"error: {str(e)}"
    
    return health_status