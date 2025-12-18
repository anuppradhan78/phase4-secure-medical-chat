#!/usr/bin/env python3
"""
Automated Security Test Runner for Secure Medical Chat.

This script runs comprehensive security tests including:
- PII/PHI detection accuracy testing
- Prompt injection and jailbreak detection
- Guardrails effectiveness validation
- Medical safety controls testing
- Red-team attack scenarios

Usage:
    python run_security_tests.py [--output-dir results] [--verbose]
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from security.security_test_suite import SecurityTestSuite


def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('security_tests.log')
        ]
    )


async def main():
    """Main function to run security tests."""
    parser = argparse.ArgumentParser(description="Run comprehensive security tests")
    parser.add_argument(
        "--output-dir", 
        default="security_test_results",
        help="Directory to save test results (default: security_test_results)"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export detailed results to JSON file"
    )
    parser.add_argument(
        "--config-path",
        default="config/test_data",
        help="Path to test data configuration (default: config/test_data)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    logger.info("🚀 Starting Secure Medical Chat Security Test Suite")
    logger.info(f"📁 Output directory: {output_dir.absolute()}")
    logger.info(f"📋 Test data path: {args.config_path}")
    
    try:
        # Initialize test suite
        logger.info("🔧 Initializing security test suite...")
        test_suite = SecurityTestSuite(config_path=args.config_path)
        
        # Run comprehensive tests
        logger.info("🧪 Running comprehensive security tests...")
        start_time = datetime.now()
        
        report = await test_suite.run_comprehensive_security_tests()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"✅ Security tests completed in {duration:.1f} seconds")
        
        # Print summary to console
        test_suite.print_summary_report(report)
        
        # Export detailed report if requested
        if args.export_json:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = f"security_test_report_{timestamp}.json"
            json_path = output_dir / json_filename
            
            test_suite.export_report(report, str(json_path))
            logger.info(f"📄 Detailed report exported to: {json_path}")
        
        # Generate summary files
        summary_filename = f"security_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        summary_path = output_dir / summary_filename
        
        # Write summary to file
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"Security Test Summary - {report.test_suite_name}\n")
            f.write("=" * 60 + "\n")
            f.write(f"Execution Time: {report.execution_timestamp}\n")
            f.write(f"Total Tests: {report.total_tests}\n")
            f.write(f"Passed: {report.passed_tests}\n")
            f.write(f"Failed: {report.failed_tests}\n")
            f.write(f"Success Rate: {report.success_rate:.1%}\n")
            f.write(f"Total Execution Time: {report.total_execution_time_ms:.1f}ms\n\n")
            
            # Write test type breakdown
            if "by_test_type" in report.summary:
                f.write("Results by Test Type:\n")
                f.write("-" * 30 + "\n")
                for test_type, stats in report.summary["by_test_type"].items():
                    f.write(f"{test_type}: {stats['passed']}/{stats['total']} ({stats['success_rate']:.1%})\n")
                f.write("\n")
            
            # Write security metrics
            if "pii_detection_accuracy" in report.summary:
                pii_stats = report.summary["pii_detection_accuracy"]
                f.write(f"PII Detection Accuracy: {pii_stats['avg_f1_score']:.1%} (target: {pii_stats['target']:.1%})\n")
            
            if "prompt_injection_blocking" in report.summary:
                injection_stats = report.summary["prompt_injection_blocking"]
                f.write(f"Prompt Injection Blocking: {injection_stats['blocking_accuracy']:.1%} (target: {injection_stats['target']:.1%})\n")
            
            # Write recommendations
            if report.recommendations:
                f.write("\nRecommendations:\n")
                f.write("-" * 20 + "\n")
                for i, rec in enumerate(report.recommendations, 1):
                    f.write(f"{i}. {rec}\n")
            
            # Write failed tests
            failed_tests = [r for r in report.test_results if not r.passed]
            if failed_tests:
                f.write(f"\nFailed Tests ({len(failed_tests)}):\n")
                f.write("-" * 20 + "\n")
                for test in failed_tests:
                    f.write(f"- {test.test_name} ({test.test_type})")
                    if test.error_message:
                        f.write(f": {test.error_message}")
                    f.write("\n")
        
        logger.info(f"📄 Summary report saved to: {summary_path}")
        
        # Determine exit code based on results
        critical_failures = 0
        
        # Check critical security metrics
        if "pii_detection_accuracy" in report.summary:
            if not report.summary["pii_detection_accuracy"]["meets_target"]:
                critical_failures += 1
                logger.warning("❌ PII detection accuracy below target threshold")
        
        if "prompt_injection_blocking" in report.summary:
            if not report.summary["prompt_injection_blocking"]["meets_target"]:
                critical_failures += 1
                logger.warning("❌ Prompt injection blocking below target threshold")
        
        # Check for red-team failures
        red_team_failures = sum(1 for r in report.test_results 
                               if r.test_type == "red_team_attack" and not r.passed)
        if red_team_failures > 0:
            critical_failures += 1
            logger.warning(f"❌ {red_team_failures} red-team attacks succeeded")
        
        # Final status
        if critical_failures == 0:
            logger.info("🎉 All critical security tests passed!")
            print(f"\n✅ SUCCESS: Security test suite completed successfully")
            print(f"📊 Results: {report.passed_tests}/{report.total_tests} tests passed ({report.success_rate:.1%})")
            return 0
        else:
            logger.error(f"💥 {critical_failures} critical security issues detected")
            print(f"\n❌ FAILURE: {critical_failures} critical security issues found")
            print(f"📊 Results: {report.passed_tests}/{report.total_tests} tests passed ({report.success_rate:.1%})")
            print("🔍 Review the detailed report for specific issues and recommendations")
            return 1
            
    except Exception as e:
        logger.error(f"💥 Security test suite failed with error: {e}", exc_info=True)
        print(f"\n💥 ERROR: Security test suite failed: {e}")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)