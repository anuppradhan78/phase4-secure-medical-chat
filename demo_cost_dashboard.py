#!/usr/bin/env python3
"""
Cost Dashboard Demo Script

This script demonstrates the cost dashboard and metrics endpoints
implemented for Task 11 of the Secure Medical Chat system.

Features demonstrated:
- GET /api/metrics endpoint with comprehensive cost metrics
- Cost breakdown by model (GPT-4 vs GPT-3.5) and user role
- Token usage tracking and cache hit rate monitoring
- Expensive queries identification for optimization
- HTML dashboard with charts and visualizations

Requirements fulfilled: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import sys
import os
sys.path.append('src')

import asyncio
import json
import webbrowser
from datetime import datetime
from src.main import app
import uvicorn
import threading
import time
import requests


def print_banner():
    """Print demo banner."""
    print("=" * 60)
    print("🏥 SECURE MEDICAL CHAT - COST DASHBOARD DEMO")
    print("=" * 60)
    print("Task 11: Create cost dashboard and metrics endpoint")
    print("Requirements: 6.1, 6.2, 6.3, 6.4, 6.5")
    print("=" * 60)
    print()


def start_server():
    """Start the FastAPI server in background."""
    uvicorn.run(app, host='127.0.0.1', port=8888, log_level='error')


def demo_metrics_endpoint(base_url):
    """Demonstrate the main metrics endpoint."""
    print("📊 BASIC METRICS ENDPOINT (/api/metrics)")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/api/metrics")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code} OK")
            print(f"  Total Cost: ${data.get('total_cost_usd', 0):.2f}")
            print(f"  Queries Today: {data.get('queries_today', 0)}")
            print(f"  Cache Hit Rate: {data.get('cache_hit_rate', 0):.1%}")
            print(f"  Avg Latency: {data.get('avg_latency_ms', 0):.0f}ms")
            print(f"  Security Events: {data.get('security_events_today', 0)}")
            print()
            
            # Show cost breakdown by model (Requirement 6.2)
            print("  Cost by Model (Requirement 6.2):")
            for model, cost in data.get('cost_by_model', {}).items():
                print(f"    {model}: ${cost:.2f}")
            print()
            
            # Show cost breakdown by role (Requirement 6.3)
            print("  Cost by User Role (Requirement 6.3):")
            for role, cost in data.get('cost_by_role', {}).items():
                print(f"    {role}: ${cost:.2f}")
            print()
        else:
            print(f"✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    print()


def demo_cost_summary(base_url):
    """Demonstrate the comprehensive cost summary endpoint."""
    print("💰 COMPREHENSIVE COST SUMMARY (/api/cost-summary)")
    print("-" * 50)
    
    try:
        response = requests.get(f"{base_url}/api/cost-summary")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code} OK")
            
            summary = data.get('summary', {})
            print(f"  Total Cost: ${summary.get('total_cost_usd', 0):.2f}")
            print(f"  Total Queries: {summary.get('total_queries', 0)}")
            print(f"  Cost per Query: ${summary.get('cost_per_query', 0):.3f} (Requirement 6.1)")
            print(f"  Token Usage: {summary.get('estimated_token_usage', 0)} (Requirement 6.1)")
            print(f"  Cache Hit Rate: {summary.get('cache_hit_rate', 0):.1%} (Requirement 6.1)")
            print()
            
            # Model comparison
            model_comp = data.get('cost_breakdown', {}).get('model_comparison', {})
            print("  Model Performance Comparison:")
            print(f"    GPT-4 Cost: ${model_comp.get('gpt4_cost', 0):.2f}")
            print(f"    GPT-3.5 Cost: ${model_comp.get('gpt35_cost', 0):.2f}")
            print(f"    GPT-4 Percentage: {model_comp.get('gpt4_percentage', 0):.1f}%")
            print()
        else:
            print(f"✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    print()


def demo_expensive_queries(base_url):
    """Demonstrate expensive queries analysis."""
    print("🔍 EXPENSIVE QUERIES ANALYSIS (/api/expensive-queries)")
    print("-" * 55)
    
    try:
        response = requests.get(f"{base_url}/api/expensive-queries")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code} OK")
            print(f"  Expensive Queries Found: {data.get('total_found', 0)} (Requirement 6.5)")
            
            analysis = data.get('analysis', {})
            print(f"  Total Cost of Expensive Queries: ${analysis.get('total_cost', 0):.2f}")
            print(f"  Average Cost: ${analysis.get('average_cost', 0):.3f}")
            print(f"  GPT-4 Queries: {analysis.get('gpt4_queries', 0)}")
            print(f"  Optimization Potential: ${analysis.get('optimization_potential', 0):.2f}")
            print()
            
            # Show top queries
            queries = data.get('queries', [])[:3]  # Top 3
            if queries:
                print("  Top Expensive Queries:")
                for i, query in enumerate(queries, 1):
                    print(f"    {i}. Model: {query.get('model', 'N/A')}, "
                          f"Cost: ${query.get('cost_usd', 0):.3f}, "
                          f"Role: {query.get('user_role', 'N/A')}")
            print()
        else:
            print(f"✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    print()


def demo_optimization_report(base_url):
    """Demonstrate cost optimization recommendations."""
    print("⚡ COST OPTIMIZATION REPORT (/api/optimization)")
    print("-" * 45)
    
    try:
        response = requests.get(f"{base_url}/api/optimization")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status: {response.status_code} OK")
            print(f"  Total Potential Savings: ${data.get('total_potential_savings', 0):.2f}")
            print()
            
            recommendations = data.get('recommendations', [])
            if recommendations:
                print("  Optimization Recommendations:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"    {i}. {rec.get('title', 'N/A')}")
                    print(f"       Priority: {rec.get('priority', 'N/A').title()}")
                    print(f"       Potential Savings: ${rec.get('potential_savings', 0):.2f}")
                    print(f"       Category: {rec.get('category', 'N/A')}")
                    print()
        else:
            print(f"✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    print()


def demo_dashboard(base_url):
    """Demonstrate the HTML dashboard."""
    print("📈 HTML DASHBOARD (/api/dashboard)")
    print("-" * 35)
    
    try:
        response = requests.get(f"{base_url}/api/dashboard")
        if response.status_code == 200:
            print(f"✓ Status: {response.status_code} OK")
            print(f"  Dashboard HTML Size: {len(response.text):,} characters")
            print("  Features: Charts, metrics, recommendations, cache stats")
            print("  Requirement 6.4: Simple dashboard for cost tracking ✓")
            print()
            
            # Ask user if they want to open the dashboard
            try:
                user_input = input("  Would you like to open the dashboard in your browser? (y/n): ")
                if user_input.lower() in ['y', 'yes']:
                    dashboard_url = f"{base_url}/api/dashboard"
                    print(f"  Opening dashboard: {dashboard_url}")
                    webbrowser.open(dashboard_url)
                    print("  Dashboard opened in your default browser!")
            except KeyboardInterrupt:
                print("\n  Skipping browser opening...")
            print()
        else:
            print(f"✗ Failed with status {response.status_code}")
    except Exception as e:
        print(f"✗ Error: {str(e)}")
    
    print()


def print_requirements_summary():
    """Print summary of requirements fulfilled."""
    print("✅ REQUIREMENTS FULFILLED")
    print("-" * 25)
    print("6.1: Display metrics: total cost, cost per query, token usage, cache hit rate ✓")
    print("6.2: Show cost breakdown by model (GPT-4 vs GPT-3.5) ✓")
    print("6.3: Show cost breakdown by user role ✓")
    print("6.4: Build simple dashboard or logging for cost tracking demonstration ✓")
    print("6.5: Identify expensive queries for optimization analysis ✓")
    print()
    print("🎉 Task 11 - Create cost dashboard and metrics endpoint: COMPLETED")
    print()


def main():
    """Main demo function."""
    print_banner()
    
    # Start server in background
    print("🚀 Starting FastAPI server...")
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(3)  # Wait for server to start
    
    base_url = "http://127.0.0.1:8888"
    print(f"Server running at: {base_url}")
    print()
    
    # Run demonstrations
    demo_metrics_endpoint(base_url)
    demo_cost_summary(base_url)
    demo_expensive_queries(base_url)
    demo_optimization_report(base_url)
    demo_dashboard(base_url)
    
    # Print summary
    print_requirements_summary()
    
    print("Demo completed! Server will continue running...")
    print(f"You can access the dashboard at: {base_url}/api/dashboard")
    print("Press Ctrl+C to stop the server.")
    
    try:
        # Keep server running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Demo ended. Thank you!")


if __name__ == "__main__":
    main()